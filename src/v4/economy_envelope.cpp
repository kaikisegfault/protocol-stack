#include "economy_internal.hpp"

#include "protocol/v1/crypto.hpp"

#include <algorithm>

namespace protocol::v4 {
namespace {

namespace i = protocol::v4::internal;

constexpr std::array<std::uint8_t, 4> kTransactionMagic{'P', 'S', 'T', 'X'};

// Offsets inside a kind-2 body, which is the only body with a canonical-bool
// field and therefore the only one admission judges beyond its width.
constexpr std::size_t kPurchaseHasReferrer = 36;
constexpr std::size_t kPurchaseReferrer = 37;
// Offsets inside a kind-8 body, whose signature field must be zero when the
// transaction enables protection.
constexpr std::size_t kSetBiometricEnable = 4;
constexpr std::size_t kSetBiometricSignature = 5;

bool all_zero(std::span<const std::uint8_t> value) {
  return std::all_of(value.begin(), value.end(),
                     [](std::uint8_t octet) { return octet == 0; });
}

// The two shape rules that live in a body rather than in a length. Both are
// non-minimal representations: a second encoding of "no referrer", and a
// signature field on a transaction that carries no signature.
bool body_shape_is_canonical(std::uint8_t kind, std::span<const std::uint8_t> body) {
  if (kind == static_cast<std::uint8_t>(Kind::purchase_seat)) {
    const auto flag = body[kPurchaseHasReferrer];
    if (flag > 1) return false;
    if (flag == 0 && !all_zero(body.subspan(kPurchaseReferrer, 32))) return false;
    return true;
  }
  if (kind == static_cast<std::uint8_t>(Kind::set_mint_biometric)) {
    const auto flag = body[kSetBiometricEnable];
    if (flag > 1) return false;
    if (flag == 1 && !all_zero(body.subspan(kSetBiometricSignature, 64))) return false;
    return true;
  }
  return true;
}

}  // namespace

Bytes encode_unsigned(const Envelope& envelope) {
  Bytes raw;
  raw.reserve(kHeaderBytes + envelope.body.size() + kTrailerBytes);
  i::append(raw, std::span<const std::uint8_t>(kTransactionMagic));
  i::append_u16(raw, kEnvelopeSchemaVersion);
  i::append_u8(raw, envelope.kind);
  i::append(raw, envelope.chain_id);
  i::append_u8(raw, kSignatureScheme);
  i::append(raw, envelope.sender_public_key);
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
  message.push_back(static_cast<std::uint8_t>(kSignLabel.size()));
  message.insert(message.end(), kSignLabel.begin(), kSignLabel.end());
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

  const auto kind = raw[6];
  const auto expected = signed_bytes(kind);
  if (!expected) return std::nullopt;
  if (raw[39] != kSignatureScheme) return std::nullopt;
  if (raw.size() != *expected) return std::nullopt;

  const auto width = *body_bytes(kind);
  const auto body = raw.subspan(kHeaderBytes, width);
  if (!body_shape_is_canonical(kind, body)) return std::nullopt;

  DecodedTransaction decoded;
  decoded.envelope.kind = kind;
  if (!i::copy32(raw.subspan(7, 32), decoded.envelope.chain_id)) return std::nullopt;
  if (!i::copy32(raw.subspan(40, 32), decoded.envelope.sender_public_key)) {
    return std::nullopt;
  }
  const auto nonce = i::read_u64(raw, 72);
  if (!nonce) return std::nullopt;
  decoded.envelope.nonce = *nonce;
  decoded.envelope.body.assign(body.begin(), body.end());

  const auto trailer = kHeaderBytes + width;
  const auto fee_limit = i::read_u64(raw, trailer);
  const auto valid_until = i::read_u64(raw, trailer + 8);
  if (!fee_limit || !valid_until) return std::nullopt;
  decoded.envelope.fee_limit = *fee_limit;
  decoded.envelope.valid_until_height = *valid_until;

  const auto signature = raw.subspan(raw.size() - kSignatureBytes);
  decoded.signature.assign(signature.begin(), signature.end());
  return decoded;
}

}  // namespace protocol::v4
