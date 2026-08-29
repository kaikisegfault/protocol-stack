// The economy state key space and its value encodings.
//
// A key is one discriminator octet followed by fixed-width big-endian fields,
// so unsigned lexicographic order over the keys is total and no two entry kinds
// can collide. The trees and roots built over these entries are
// `economy_tree.cpp`, and the shape rules that decide which of them a
// transition could have written live there with the root that needs them.

#include "economy_internal.hpp"

namespace protocol::v7 {
namespace {

namespace i = protocol::v7::internal;

Bytes with_prefix(Entry entry, std::span<const std::uint8_t> tail) {
  auto key = i::key_prefix(entry);
  i::append(key, tail);
  return key;
}

}  // namespace

Bytes seat_key(std::uint32_t seat_id) {
  auto key = i::key_prefix(Entry::seat);
  i::append_u32(key, seat_id);
  return key;
}

Bytes channel_key(std::uint8_t channel_index) {
  auto key = i::key_prefix(Entry::channel);
  i::append_u8(key, channel_index);
  return key;
}

Bytes cycle_assignment_key(std::uint64_t cycle_window) {
  auto key = i::key_prefix(Entry::cycle_assignment);
  i::append_u64(key, cycle_window);
  return key;
}

Bytes referral_balance_key(std::span<const std::uint8_t> hub_identity_hash) {
  return with_prefix(Entry::referral_balance, hub_identity_hash);
}

Bytes direct_decision_key(std::span<const std::uint8_t> decision_id) {
  return with_prefix(Entry::direct_decision, decision_id);
}

Bytes typed_custody_key(std::uint8_t beneficiary_kind,
                        std::span<const std::uint8_t> beneficiary_id) {
  auto key = i::key_prefix(Entry::typed_custody);
  i::append_u8(key, beneficiary_kind);
  i::append(key, beneficiary_id);
  return key;
}

Bytes carry_key(std::uint8_t channel_index) {
  auto key = i::key_prefix(Entry::carry);
  i::append_u8(key, channel_index);
  return key;
}

Bytes verifier_key_key() { return i::key_prefix(Entry::verifier_key); }

Bytes hub_identity_key(std::span<const std::uint8_t> hub_identity_hash) {
  return with_prefix(Entry::hub_identity, hub_identity_hash);
}

Bytes unreferred_pool_key() { return i::key_prefix(Entry::unreferred_pool); }

Bytes escrow_key(std::span<const std::uint8_t> escrow_id) {
  return with_prefix(Entry::escrow, escrow_id);
}

Bytes signer_key(std::span<const std::uint8_t> signer_id) {
  return with_prefix(Entry::signer, signer_id);
}

Bytes verified_user_key(std::span<const std::uint8_t> hub_identity_hash) {
  return with_prefix(Entry::verified_user_enrollment, hub_identity_hash);
}

Bytes verified_user_counter_key() {
  return i::key_prefix(Entry::verified_user_counter);
}

Bytes seat_value(const SeatRecord& seat) {
  Bytes value;
  value.reserve(82);
  i::append(value, seat.hub_identity_hash);
  i::append_u8(value, seat.has_referrer ? 1 : 0);
  if (seat.has_referrer) {
    i::append(value, seat.referrer_hub_identity);
  } else {
    value.insert(value.end(), 32, 0);
  }
  i::append_u8(value, seat.is_activated ? 1 : 0);
  i::append_u64(value, seat.is_activated ? seat.activation_height : 0);
  i::append_u64(value, seat.minted_through_window);
  return value;
}

Bytes channel_value(std::uint64_t issued_atomic, std::uint64_t outstanding_atomic) {
  Bytes value;
  i::append_u64(value, issued_atomic);
  i::append_u64(value, outstanding_atomic);
  return value;
}

Bytes referral_balance_value(std::uint64_t accrued_atomic,
                             std::uint64_t minted_atomic,
                             std::uint64_t collected_through_window) {
  Bytes value;
  i::append_u64(value, accrued_atomic);
  i::append_u64(value, minted_atomic);
  i::append_u64(value, collected_through_window);
  return value;
}

Bytes unreferred_pool_value(std::uint64_t accrued_atomic,
                            std::uint64_t minted_atomic) {
  Bytes value;
  i::append_u64(value, accrued_atomic);
  i::append_u64(value, minted_atomic);
  return value;
}

Bytes typed_custody_value(std::uint64_t amount_atomic) {
  Bytes value;
  i::append_u64(value, amount_atomic);
  return value;
}

Bytes carry_value(std::uint64_t carry_atomic) {
  Bytes value;
  i::append_u64(value, carry_atomic);
  return value;
}

Bytes verifier_key_value(std::span<const std::uint8_t> public_key) {
  return Bytes(public_key.begin(), public_key.end());
}

Bytes hub_identity_value(const HubIdentityRecord& identity) {
  Bytes value;
  value.reserve(52);
  i::append(value, identity.hub_public_key);
  i::append_u64(value, identity.registered_at_height);
  i::append_u32(value, identity.next_escrow_index);
  i::append_u32(value, identity.escrow_count);
  i::append_u32(value, identity.seat_count);
  return value;
}

Bytes escrow_value(const EscrowRecord& escrow) {
  Bytes value;
  value.reserve(49);
  i::append(value, escrow.owner_hub_identity);
  i::append_u8(value, escrow.posture.requires_confirmation ? 1 : 0);
  i::append_u64(value, escrow.posture.min_amount_atomic);
  i::append_u32(value, escrow.posture.exempt_slot_mask);
  i::append_u32(value, escrow.signer_count);
  return value;
}

Bytes signer_value(std::span<const std::uint8_t> escrow_id) {
  return Bytes(escrow_id.begin(), escrow_id.end());
}

Bytes verified_user_value(const EnrollmentRecord& enrollment) {
  Bytes value;
  value.reserve(24);
  i::append_u64(value, enrollment.enrolled_at_height);
  i::append_u64(value, enrollment.minted_through_window);
  i::append_u64(value, enrollment.issued_atomic);
  return value;
}

Bytes verified_user_counter_value(std::uint64_t enrolled_count) {
  Bytes value;
  i::append_u64(value, enrolled_count);
  return value;
}

}  // namespace protocol::v7
