#include "economy_internal.hpp"

#include "protocol/v1/crypto.hpp"

#include <algorithm>
#include <array>

namespace protocol::v6 {
namespace {

namespace i = protocol::v6::internal;

constexpr std::array<std::uint8_t, 4> kTransactionMagic{'P', 'S', 'T', 'X'};

// Offsets inside a kind-2 body: the canonical-bool flag and the referrer field
// whose absence has exactly one encoding.
constexpr std::size_t kPurchaseHasReferrer = 4;
constexpr std::size_t kPurchaseReferrer = 5;
// Offsets inside a kind-17 body: the canonical-bool flag and the slot mask,
// whose high 8 bits must be zero because a window has 24 slots.
constexpr std::size_t kPostureRequiresConfirmation = 0;
constexpr std::size_t kPostureExemptSlotMask = 9;

// The shape rules that live in a body rather than in a length. Each is a
// non-minimal or out-of-range representation `protocol-primitives-v1` forbids,
// and each is decidable from the bytes alone.
//
// The rule this deliberately does not enforce is the specification's
// requirement that an unrequested confirmation field be 64 zero octets. Whether
// a confirmation is required is a predicate over the escrow's stored posture,
// and admission reads no state; ADR 0045 records that it is refused at
// execution with `UNAUTHORIZED` instead, and why the code the specification
// names does not exist in the space that could return it.
bool body_shape_is_canonical(std::uint8_t kind, std::span<const std::uint8_t> body) {
  if (kind == static_cast<std::uint8_t>(Kind::purchase_seat)) {
    const auto flag = body[kPurchaseHasReferrer];
    if (flag > 1) return false;
    return flag != 0 || i::all_zero(body.subspan(kPurchaseReferrer, 32));
  }
  if (kind == static_cast<std::uint8_t>(Kind::set_security_posture)) {
    if (body[kPostureRequiresConfirmation] > 1) return false;
    const auto mask = i::read_u32(body, kPostureExemptSlotMask);
    return mask.has_value() && *mask <= kMaxExemptSlotMask;
  }
  return true;
}

// A registration has no escrow yet, so it has no nonce sequence to advance and
// nothing to charge. Both fields are required to be zero rather than merely
// ignored, so one registration has exactly one encoding.
bool envelope_shape_is_canonical(std::uint8_t kind, std::uint64_t nonce,
                                 std::uint64_t fee_limit) {
  if (kind != static_cast<std::uint8_t>(Kind::hub_register)) return true;
  return nonce == 0 && fee_limit == 0;
}

}  // namespace

Bytes encode_unsigned(const Envelope& envelope) {
  Bytes raw;
  raw.reserve(kHeaderBytes + envelope.body.size() + kTrailerBytes);
  i::append(raw, std::span<const std::uint8_t>(kTransactionMagic));
  i::append_u16(raw, kEnvelopeSchemaVersion);
  i::append_u8(raw, envelope.kind);
  i::append(raw, envelope.chain_id);
  i::append_u8(raw, envelope.scheme);
  i::append(raw, envelope.authority_public_key);
  i::append_u64(raw, envelope.nonce);
  i::append(raw, envelope.body);
  i::append_u64(raw, envelope.fee_limit);
  i::append_u64(raw, envelope.valid_until_height);
  return raw;
}

Bytes encode_signed(const Envelope& envelope,
                    std::span<const std::uint8_t> signature) {
  auto raw = encode_unsigned(envelope);
  i::append(raw, signature);
  return raw;
}

Bytes signing_message(std::span<const std::uint8_t> unsigned_transaction) {
  Bytes message;
  i::append_domain(message, kSignLabel);
  i::append(message, unsigned_transaction);
  return message;
}

Hash transaction_id(std::span<const std::uint8_t> signed_transaction) {
  return protocol::v1::hash(kTransactionIdLabel, signed_transaction);
}

std::optional<DecodedTransaction> decode_signed(std::span<const std::uint8_t> raw) {
  if (raw.size() < kHeaderBytes + kTrailerBytes + kSignatureBytes) {
    return std::nullopt;
  }
  if (!std::equal(kTransactionMagic.begin(), kTransactionMagic.end(), raw.begin())) {
    return std::nullopt;
  }
  const auto schema = i::read_u16(raw, 4);
  if (!schema || *schema != kEnvelopeSchemaVersion) return std::nullopt;

  // A retired or never-assigned kind has no width, so it is refused here
  // together with every other unknown number.
  const auto kind = raw[6];
  const auto expected = signed_bytes(kind);
  if (!expected || raw.size() != *expected) return std::nullopt;

  // The scheme byte must be one the kind permits. An unknown scheme and a
  // scheme this kind forbids are the same refusal, so no transaction is
  // ambiguous about which rule authorizes it.
  const auto scheme = *kind_scheme(kind);
  if (raw[39] != scheme) return std::nullopt;

  const auto width = *body_bytes(kind);
  const auto body = raw.subspan(kHeaderBytes, width);
  if (!body_shape_is_canonical(kind, body)) return std::nullopt;

  const auto nonce = i::read_u64(raw, 72);
  const auto trailer = kHeaderBytes + width;
  const auto fee_limit = i::read_u64(raw, trailer);
  const auto valid_until = i::read_u64(raw, trailer + 8);
  if (!nonce || !fee_limit || !valid_until) return std::nullopt;
  if (!envelope_shape_is_canonical(kind, *nonce, *fee_limit)) return std::nullopt;

  DecodedTransaction decoded;
  decoded.envelope.kind = kind;
  if (!i::copy32(raw.subspan(7, 32), decoded.envelope.chain_id)) return std::nullopt;
  decoded.envelope.scheme = scheme;
  if (!i::copy32(raw.subspan(40, 32), decoded.envelope.authority_public_key)) {
    return std::nullopt;
  }
  decoded.envelope.nonce = *nonce;
  decoded.envelope.body.assign(body.begin(), body.end());
  decoded.envelope.fee_limit = *fee_limit;
  decoded.envelope.valid_until_height = *valid_until;

  const auto signature = raw.subspan(raw.size() - kSignatureBytes);
  decoded.signature.assign(signature.begin(), signature.end());
  return decoded;
}

}  // namespace protocol::v6
