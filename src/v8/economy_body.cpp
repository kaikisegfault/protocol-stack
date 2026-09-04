// The sixteen kind bodies, projected into named fields and back.
//
// `decode_signed` judges a body's width and its two canonical-shape rules; this
// reads the fields out of a body it has already accepted. The two halves are
// written against each other on purpose: `encode_body(kind, *decode_body(kind,
// raw)) == raw` for every accepted body, which is the round-trip the fuzz target
// asserts over the envelope and is what makes "canonical" checkable here too.

#include "economy_internal.hpp"

namespace protocol::v8 {
namespace {

namespace i = protocol::v8::internal;

bool read32(std::span<const std::uint8_t> body, std::size_t offset,
            Octets32& target) {
  if (offset + target.size() > body.size()) return false;
  return i::copy32(body.subspan(offset, target.size()), target);
}

bool read_signature(std::span<const std::uint8_t> body, std::size_t offset,
                    Bytes& target) {
  if (offset + kSignatureBytes > body.size()) return false;
  const auto field = body.subspan(offset, kSignatureBytes);
  target.assign(field.begin(), field.end());
  return true;
}

// A canonical bool is `0` or `1` and nothing else. Kind 17's flag is checked at
// admission; kind 2's is too, and both are re-read here rather than assumed,
// because this function is also reached by `encode_body`'s round trip.
bool read_flag(std::span<const std::uint8_t> body, std::size_t offset,
               bool& target) {
  const auto octet = i::read_u8(body, offset);
  if (!octet || *octet > 1) return false;
  target = *octet == 1;
  return true;
}

void append_flag(Bytes& target, bool value) {
  i::append_u8(target, value ? 1 : 0);
}

bool append_signature(Bytes& target, const Bytes& signature) {
  if (signature.size() != kSignatureBytes) return false;
  i::append(target, signature);
  return true;
}

// Kind 20's answer is the one body field that is neither a key, an identifier,
// nor a signature. It is opaque octets of a fixed width, because the predicate
// that would judge it is the challenge's content and that is founder-reserved.
bool read_answer(std::span<const std::uint8_t> body, std::size_t offset,
                 Bytes& target) {
  if (offset + kAnswerBytes > body.size()) return false;
  const auto field = body.subspan(offset, kAnswerBytes);
  target.assign(field.begin(), field.end());
  return true;
}

}  // namespace

std::optional<Body> decode_body(std::uint8_t kind,
                                std::span<const std::uint8_t> body) {
  const auto width = body_bytes(kind);
  if (!width || body.size() != *width) return std::nullopt;

  Body fields;
  const auto amount = [&](std::size_t offset) {
    const auto value = i::read_u64(body, offset);
    if (value) fields.amount_atomic = *value;
    return value.has_value();
  };
  switch (static_cast<Kind>(kind)) {
    case Kind::native_transfer:
      return read32(body, 0, fields.recipient_escrow_id) && amount(32)
                 ? std::optional(fields)
                 : std::nullopt;
    case Kind::native_transfer_verified:
      return read32(body, 0, fields.recipient_escrow_id) && amount(32) &&
                     read_signature(body, 40, fields.hub_signature)
                 ? std::optional(fields)
                 : std::nullopt;
    case Kind::purchase_seat: {
      const auto seat = i::read_u32(body, 0);
      if (!seat || !read_flag(body, 4, fields.has_referrer)) return std::nullopt;
      fields.seat_id = *seat;
      return read32(body, 5, fields.referrer_escrow_id) &&
                     read_signature(body, 37, fields.hub_signature)
                 ? std::optional(fields)
                 : std::nullopt;
    }
    case Kind::activate_seat: {
      const auto seat = i::read_u32(body, 0);
      if (!seat) return std::nullopt;
      fields.seat_id = *seat;
      return read_signature(body, 4, fields.hub_signature) ? std::optional(fields)
                                                           : std::nullopt;
    }
    case Kind::mint_node: {
      const auto seat = i::read_u32(body, 0);
      if (!seat) return std::nullopt;
      fields.seat_id = *seat;
      return read32(body, 4, fields.destination_escrow_id) &&
                     read_signature(body, 36, fields.hub_signature)
                 ? std::optional(fields)
                 : std::nullopt;
    }
    case Kind::mint_referral:
    case Kind::mint_verified_user:
      return read32(body, 0, fields.destination_escrow_id) &&
                     read_signature(body, 32, fields.hub_signature)
                 ? std::optional(fields)
                 : std::nullopt;
    case Kind::direct_issue: {
      const auto channel = i::read_u8(body, 0);
      if (!channel) return std::nullopt;
      fields.channel_id = *channel;
      return read32(body, 1, fields.decision_id) &&
                     read32(body, 33, fields.beneficiary_escrow_id) && amount(65) &&
                     read32(body, 73, fields.authorization)
                 ? std::optional(fields)
                 : std::nullopt;
    }
    case Kind::hub_register:
      return read32(body, 0, fields.hub_identity_hash) &&
                     read32(body, 32, fields.first_signer_public_key) &&
                     read_signature(body, 64, fields.verifier_signature)
                 ? std::optional(fields)
                 : std::nullopt;
    case Kind::escrow_create:
      return read32(body, 0, fields.hub_identity_hash) &&
                     read32(body, 32, fields.fee_escrow_id)
                 ? std::optional(fields)
                 : std::nullopt;
    case Kind::escrow_delete:
      return read32(body, 0, fields.hub_identity_hash) &&
                     read32(body, 32, fields.target_escrow_id) &&
                     read32(body, 64, fields.fee_escrow_id)
                 ? std::optional(fields)
                 : std::nullopt;
    case Kind::signer_add:
      return read32(body, 0, fields.hub_identity_hash) &&
                     read32(body, 32, fields.escrow_id) &&
                     read32(body, 64, fields.signer_public_key)
                 ? std::optional(fields)
                 : std::nullopt;
    case Kind::signer_revoke:
      return read32(body, 0, fields.hub_identity_hash) &&
                     read32(body, 32, fields.escrow_id) &&
                     read32(body, 64, fields.signer_id)
                 ? std::optional(fields)
                 : std::nullopt;
    case Kind::set_security_posture: {
      const auto minimum = i::read_u64(body, 1);
      const auto mask = i::read_u32(body, 9);
      if (!read_flag(body, 0, fields.requires_confirmation) || !minimum || !mask) {
        return std::nullopt;
      }
      fields.min_amount_atomic = *minimum;
      fields.exempt_slot_mask = *mask;
      return read_signature(body, 13, fields.hub_signature) ? std::optional(fields)
                                                            : std::nullopt;
    }
    case Kind::challenge_response: {
      const auto seat = i::read_u32(body, 0);
      const auto height = i::read_u64(body, 4);
      if (!seat || !height) return std::nullopt;
      fields.seat_id = *seat;
      fields.challenge_height = *height;
      return read_answer(body, 12, fields.answer) ? std::optional(fields)
                                                  : std::nullopt;
    }
    case Kind::file_dispute: {
      const auto seat = i::read_u32(body, 0);
      const auto window = i::read_u64(body, 4);
      const auto slot = i::read_u8(body, 12);
      const auto reason = i::read_u8(body, 13);
      if (!seat || !window || !slot || !reason) return std::nullopt;
      fields.seat_id = *seat;
      fields.cycle_window = *window;
      // The slot index and the reason code are bounded numeric fields rather
      // than shape rules, so an out-of-range slot decodes here and is refused
      // at execution as `SLOT_RANGE`. The reason code carries no protocol
      // effect at all and is bound into the signed message so that a relayer
      // cannot alter the stated reason of a decision it did not make.
      fields.slot_index = *slot;
      fields.reason_code = *reason;
      return read_signature(body, 14, fields.authority_signature)
                 ? std::optional(fields)
                 : std::nullopt;
    }
  }
  return std::nullopt;
}

Bytes encode_body(std::uint8_t kind, const Body& fields) {
  Bytes raw;
  const auto width = body_bytes(kind);
  if (!width) return raw;
  raw.reserve(*width);
  switch (static_cast<Kind>(kind)) {
    case Kind::native_transfer:
      i::append(raw, fields.recipient_escrow_id);
      i::append_u64(raw, fields.amount_atomic);
      break;
    case Kind::native_transfer_verified:
      i::append(raw, fields.recipient_escrow_id);
      i::append_u64(raw, fields.amount_atomic);
      if (!append_signature(raw, fields.hub_signature)) return {};
      break;
    case Kind::purchase_seat:
      i::append_u32(raw, fields.seat_id);
      append_flag(raw, fields.has_referrer);
      i::append(raw, fields.referrer_escrow_id);
      if (!append_signature(raw, fields.hub_signature)) return {};
      break;
    case Kind::activate_seat:
      i::append_u32(raw, fields.seat_id);
      if (!append_signature(raw, fields.hub_signature)) return {};
      break;
    case Kind::mint_node:
      i::append_u32(raw, fields.seat_id);
      i::append(raw, fields.destination_escrow_id);
      if (!append_signature(raw, fields.hub_signature)) return {};
      break;
    case Kind::mint_referral:
    case Kind::mint_verified_user:
      i::append(raw, fields.destination_escrow_id);
      if (!append_signature(raw, fields.hub_signature)) return {};
      break;
    case Kind::direct_issue:
      i::append_u8(raw, fields.channel_id);
      i::append(raw, fields.decision_id);
      i::append(raw, fields.beneficiary_escrow_id);
      i::append_u64(raw, fields.amount_atomic);
      i::append(raw, fields.authorization);
      break;
    case Kind::hub_register:
      i::append(raw, fields.hub_identity_hash);
      i::append(raw, fields.first_signer_public_key);
      if (!append_signature(raw, fields.verifier_signature)) return {};
      break;
    case Kind::escrow_create:
      i::append(raw, fields.hub_identity_hash);
      i::append(raw, fields.fee_escrow_id);
      break;
    case Kind::escrow_delete:
      i::append(raw, fields.hub_identity_hash);
      i::append(raw, fields.target_escrow_id);
      i::append(raw, fields.fee_escrow_id);
      break;
    case Kind::signer_add:
      i::append(raw, fields.hub_identity_hash);
      i::append(raw, fields.escrow_id);
      i::append(raw, fields.signer_public_key);
      break;
    case Kind::signer_revoke:
      i::append(raw, fields.hub_identity_hash);
      i::append(raw, fields.escrow_id);
      i::append(raw, fields.signer_id);
      break;
    case Kind::set_security_posture:
      append_flag(raw, fields.requires_confirmation);
      i::append_u64(raw, fields.min_amount_atomic);
      i::append_u32(raw, fields.exempt_slot_mask);
      if (!append_signature(raw, fields.hub_signature)) return {};
      break;
    case Kind::challenge_response:
      i::append_u32(raw, fields.seat_id);
      i::append_u64(raw, fields.challenge_height);
      if (fields.answer.size() != kAnswerBytes) return {};
      i::append(raw, fields.answer);
      break;
    case Kind::file_dispute:
      i::append_u32(raw, fields.seat_id);
      i::append_u64(raw, fields.cycle_window);
      i::append_u8(raw, fields.slot_index);
      i::append_u8(raw, fields.reason_code);
      if (!append_signature(raw, fields.authority_signature)) return {};
      break;
  }
  return raw.size() == *width ? raw : Bytes{};
}

}  // namespace protocol::v8
