// One value decoder per economy entry kind, each the exact inverse of the
// encoder in `src/v7/economy_state.cpp`.
//
// **Each fails closed on a value no transition could have written**, not merely
// on the wrong width. A seat carrying a referrer identity while its flag is
// clear, an unactivated seat with a nonzero activation height, an identity whose
// next escrow index is below its live count, a balance that minted more than it
// accrued, an exempt slot mask naming a slot past the twenty-fourth: each is a
// state the conservation invariants forbid, and each has exactly one encoding a
// transition produces. Refusing them here is free — a snapshot is node-local, so
// a rule stricter than the kernel's own decoder changes no accepted state.

#include "snapshot_v7_internal.hpp"

#include <bit>
#include <optional>

namespace protocol::storage::snapshot_v7 {
namespace {

// A flag octet a transition wrote is 0 or 1. Any other value is a third boolean
// no encoder produces.
std::optional<bool> read_flag(std::span<const std::uint8_t> value,
                              std::size_t offset) {
  if (offset >= value.size()) return std::nullopt;
  if (value[offset] > 1) return std::nullopt;
  return value[offset] == 1;
}

bool all_zero(std::span<const std::uint8_t> value) {
  for (const auto octet : value) {
    if (octet != 0) return false;
  }
  return true;
}

// Bits set at or above `bitmap_bits` are pad. `bitmap()` never sets one, so a
// record carrying one is not a record any chain wrote — and it would be read as
// an accrued seat by the mint's own walk, because `bit_is_set` bounds itself by
// the packed width rather than by the recorded bit count.
bool padding_is_clear(std::span<const std::uint8_t> packed,
                      std::uint32_t bitmap_bits) {
  const auto whole = static_cast<std::size_t>(bitmap_bits) / 8;
  if (whole >= packed.size()) return true;
  const auto used = static_cast<unsigned>(bitmap_bits % 8);
  const auto mask = static_cast<std::uint8_t>(0xFFU >> used);
  if ((packed[whole] & mask) != 0) return false;
  for (std::size_t index = whole + 1; index < packed.size(); ++index) {
    if (packed[index] != 0) return false;
  }
  return true;
}

std::uint32_t population(std::span<const std::uint8_t> packed) {
  std::uint32_t count = 0;
  for (const auto octet : packed) {
    count += static_cast<std::uint32_t>(std::popcount(octet));
  }
  return count;
}

bool apply_seat(Rebuild& rebuild, std::span<const std::uint8_t> key,
                std::span<const std::uint8_t> value) {
  const auto seat_id = read_u32(key, 1);
  if (!seat_id || *seat_id > v7::kMaxSeatId) return false;
  const auto identity = read_fixed<32>(value, 0);
  const auto has_referrer = read_flag(value, 32);
  const auto referrer = read_fixed<32>(value, 33);
  const auto activated = read_flag(value, 65);
  const auto activation_height = read_u64(value, 66);
  const auto mark = read_u64(value, 74);
  if (!identity || !has_referrer || !referrer || !activated ||
      !activation_height || !mark) {
    return false;
  }
  // Both zeroed fields are written as zero by `seat_value` when their flag is
  // clear, so a nonzero one is a field the encoder cannot have produced.
  if (!*has_referrer && !all_zero(*referrer)) return false;
  if (!*activated && *activation_height != 0) return false;

  v7::SeatRecord seat;
  seat.hub_identity_hash = *identity;
  seat.has_referrer = *has_referrer;
  if (*has_referrer) seat.referrer_hub_identity = *referrer;
  seat.is_activated = *activated;
  seat.activation_height = *activation_height;
  seat.minted_through_window = *mark;
  rebuild.ledger.seats.emplace(*seat_id, seat);
  return true;
}

bool apply_channel(Rebuild& rebuild, std::span<const std::uint8_t> key,
                   std::span<const std::uint8_t> value) {
  if (key.size() != 2 || key[1] >= v7::kChannelCount) return false;
  const auto index = static_cast<std::size_t>(key[1]);
  const auto issued = read_u64(value, 0);
  const auto outstanding = read_u64(value, 8);
  if (!issued || !outstanding) return false;
  rebuild.ledger.channel_issued[index] = *issued;
  rebuild.ledger.channel_outstanding[index] = *outstanding;
  rebuild.channel_seen[index] = true;
  return true;
}

// The one variable-width value, and the only entry whose bytes are stored rather
// than decoded into fields: `Ledger::assignments` holds the record as written,
// so the round trip is exact and the mint reads the same octets it read before
// the restart.
bool apply_cycle_assignment(Rebuild& rebuild, std::span<const std::uint8_t> key,
                            std::span<const std::uint8_t> value) {
  const auto window = read_u64(key, 1);
  if (!window) return false;
  const auto record = v7::decode_cycle_assignment_value(value);
  if (!record) return false;
  if (record->bitmap_bits > v7::kFounderSeatCapacity ||
      record->in_scope_count > v7::kFounderSeatCapacity) {
    return false;
  }
  if (!padding_is_clear(record->accrued_bitmap, record->bitmap_bits) ||
      !padding_is_clear(record->winner_bitmap, record->bitmap_bits)) {
    return false;
  }
  // The record commits to the winner count and to the bitmap it was built from,
  // so the two are one fact written twice.
  if (population(record->winner_bitmap) != record->winner_count) return false;
  // The contributing set is the accrued seats plus the reallocated ones, and it
  // is drawn from the in-scope set.
  const auto accrued = population(record->accrued_bitmap);
  if (accrued > record->in_scope_count) return false;
  if (record->reallocated_count > record->in_scope_count - accrued) return false;
  // The share is a function of the winner count alone, which makes it derivable
  // rather than merely bounded.
  const auto split = v7::split_permission(record->winner_count);
  if (record->share_per_winner_atomic != split.share[v7::kFounderOperatorChannel]) {
    return false;
  }
  rebuild.ledger.assignments.emplace(*window, v7::Bytes(value.begin(), value.end()));
  return true;
}

bool apply_referral_balance(Rebuild& rebuild, std::span<const std::uint8_t> key,
                            std::span<const std::uint8_t> value) {
  const auto identity = read_fixed<32>(key, 1);
  const auto accrued = read_u64(value, 0);
  const auto minted = read_u64(value, 8);
  const auto collected = read_u64(value, 16);
  if (!identity || !accrued || !minted || !collected) return false;
  if (*minted > *accrued) return false;
  rebuild.ledger.referral.emplace(
      *identity, v7::ReferralBalance{*accrued, *minted, *collected});
  return true;
}

bool apply_direct_decision(Rebuild& rebuild, std::span<const std::uint8_t> key,
                           std::span<const std::uint8_t> value) {
  const auto decision = read_fixed<32>(key, 1);
  if (!decision || !value.empty()) return false;
  rebuild.ledger.decisions.insert(*decision);
  return true;
}

bool apply_typed_custody(Rebuild& rebuild, std::span<const std::uint8_t> key,
                         std::span<const std::uint8_t> value) {
  // The four institutional legs are channels 1 through 4, and every one of them
  // credits the singleton beneficiary. The Founder operator's leg credits an
  // account balance and writes no custody entry at all.
  if (key.size() != 34 || key[1] == 0 || key[1] > 4) return false;
  const auto beneficiary = read_fixed<32>(key, 2);
  const auto amount = read_u64(value, 0);
  if (!beneficiary || !all_zero(*beneficiary) || !amount) return false;
  rebuild.ledger.custody.emplace(key[1], *amount);
  return true;
}

bool apply_verifier_key(Rebuild& rebuild, std::span<const std::uint8_t> value) {
  const auto key = read_fixed<32>(value, 0);
  // The prefix has already been matched against the expected parameters, so a
  // disagreement here is a payload that carries two different chains' keys.
  if (!key || *key != rebuild.ledger.verifier_key) return false;
  rebuild.verifier_key_seen = true;
  return true;
}

bool apply_hub_identity(Rebuild& rebuild, std::span<const std::uint8_t> key,
                        std::span<const std::uint8_t> value) {
  const auto hash = read_fixed<32>(key, 1);
  const auto public_key = read_fixed<32>(value, 0);
  const auto registered = read_u64(value, 32);
  const auto next_index = read_u32(value, 40);
  const auto escrow_count = read_u32(value, 44);
  const auto seat_count = read_u32(value, 48);
  if (!hash || !public_key || !registered || !next_index || !escrow_count ||
      !seat_count) {
    return false;
  }
  // A registration writes index 1 and count 1, an escrow creation raises both,
  // and a deletion lowers only the count. The index therefore never decreases
  // and never falls below the live count.
  if (*next_index < 1 || *next_index < *escrow_count) return false;
  if (*seat_count > v7::kMaxSeatsPerIdentity) return false;

  v7::HubIdentityRecord identity;
  identity.hub_public_key = *public_key;
  identity.registered_at_height = *registered;
  identity.next_escrow_index = *next_index;
  identity.escrow_count = *escrow_count;
  identity.seat_count = *seat_count;
  rebuild.ledger.registry.identities.emplace(*hash, identity);
  return true;
}

bool apply_unreferred_pool(Rebuild& rebuild, std::span<const std::uint8_t> value) {
  const auto accrued = read_u64(value, 0);
  const auto minted = read_u64(value, 8);
  if (!accrued || !minted || *minted > *accrued) return false;
  rebuild.ledger.pool_accrued = *accrued;
  rebuild.ledger.pool_minted = *minted;
  rebuild.unreferred_pool_seen = true;
  return true;
}

bool apply_escrow(Rebuild& rebuild, std::span<const std::uint8_t> key,
                  std::span<const std::uint8_t> value) {
  const auto escrow = read_fixed<32>(key, 1);
  const auto owner = read_fixed<32>(value, 0);
  const auto confirmation = read_flag(value, 32);
  const auto minimum = read_u64(value, 33);
  const auto mask = read_u32(value, 41);
  const auto signers = read_u32(value, 45);
  if (!escrow || !owner || !confirmation || !minimum || !mask || !signers) {
    return false;
  }
  if (*mask > v7::kMaxExemptSlotMask) return false;
  if (*signers > v7::kMaxSignersPerEscrow) return false;

  v7::EscrowRecord record;
  record.owner_hub_identity = *owner;
  record.posture.requires_confirmation = *confirmation;
  record.posture.min_amount_atomic = *minimum;
  record.posture.exempt_slot_mask = *mask;
  record.signer_count = *signers;
  rebuild.ledger.registry.escrows.emplace(*escrow, record);
  return true;
}

bool apply_signer(Rebuild& rebuild, std::span<const std::uint8_t> key,
                  std::span<const std::uint8_t> value) {
  const auto identifier = read_fixed<32>(key, 1);
  const auto escrow = read_fixed<32>(value, 0);
  if (!identifier || !escrow) return false;
  rebuild.ledger.registry.signers.emplace(*identifier, *escrow);
  return true;
}

bool apply_enrollment(Rebuild& rebuild, std::span<const std::uint8_t> key,
                      std::span<const std::uint8_t> value) {
  const auto identity = read_fixed<32>(key, 1);
  const auto enrolled_at = read_u64(value, 0);
  const auto mark = read_u64(value, 8);
  const auto issued = read_u64(value, 16);
  if (!identity || !enrolled_at || !mark || !issued) return false;
  rebuild.ledger.registry.enrollments.emplace(
      *identity, v7::EnrollmentRecord{*enrolled_at, *mark, *issued});
  return true;
}

bool apply_verified_user_counter(Rebuild& rebuild,
                                 std::span<const std::uint8_t> value) {
  const auto enrolled = read_u64(value, 0);
  // Enrollment stops at the founder-directed population, so no transition ever
  // writes a counter above it.
  if (!enrolled || *enrolled > v7::kVerifiedUserPopulation) return false;
  rebuild.ledger.registry.enrolled_count = *enrolled;
  rebuild.verified_user_counter_seen = true;
  return true;
}

bool apply_recovery_pool(Rebuild& rebuild, std::span<const std::uint8_t> value) {
  const auto legs = v7::decode_recovery_pool_value(value);
  if (!legs) return false;
  rebuild.ledger.pool = *legs;
  rebuild.recovery_pool_seen = true;
  return true;
}

}  // namespace

bool apply_entry(Rebuild& rebuild, const v7::EconomyEntry& entry) {
  if (entry.key.empty()) return false;
  const auto kind = entry.key.front();
  if (!v7::is_entry_kind(kind)) return false;
  const auto key_width = v7::entry_key_bytes(kind);
  if (!key_width || entry.key.size() != *key_width) return false;
  // `nullopt` is the cycle assignment, whose width follows from its own recorded
  // bit count and is checked by its decoder.
  const auto value_width = v7::entry_value_bytes(kind);
  if (value_width && entry.value.size() != *value_width) return false;

  const std::span<const std::uint8_t> key{entry.key};
  const std::span<const std::uint8_t> value{entry.value};
  switch (static_cast<v7::Entry>(kind)) {
    case v7::Entry::seat:
      return apply_seat(rebuild, key, value);
    case v7::Entry::channel:
      return apply_channel(rebuild, key, value);
    case v7::Entry::cycle_assignment:
      return apply_cycle_assignment(rebuild, key, value);
    case v7::Entry::referral_balance:
      return apply_referral_balance(rebuild, key, value);
    case v7::Entry::direct_decision:
      return apply_direct_decision(rebuild, key, value);
    case v7::Entry::typed_custody:
      return apply_typed_custody(rebuild, key, value);
    case v7::Entry::verifier_key:
      return apply_verifier_key(rebuild, value);
    case v7::Entry::hub_identity:
      return apply_hub_identity(rebuild, key, value);
    case v7::Entry::unreferred_pool:
      return apply_unreferred_pool(rebuild, value);
    case v7::Entry::escrow:
      return apply_escrow(rebuild, key, value);
    case v7::Entry::signer:
      return apply_signer(rebuild, key, value);
    case v7::Entry::verified_user_enrollment:
      return apply_enrollment(rebuild, key, value);
    case v7::Entry::verified_user_counter:
      return apply_verified_user_counter(rebuild, value);
    case v7::Entry::recovery_pool:
      return apply_recovery_pool(rebuild, value);
  }
  return false;
}

bool complete(Rebuild& rebuild) {
  for (const auto seen : rebuild.channel_seen) {
    if (!seen) return false;
  }
  if (!rebuild.recovery_pool_seen || !rebuild.verifier_key_seen ||
      !rebuild.unreferred_pool_seen || !rebuild.verified_user_counter_seen) {
    return false;
  }

  // `assigned_permissions` is re-derived, never read. It is not a state entry,
  // so nothing in the root commits to it; a payload that carried it could
  // disagree with the records it sits beside, and the channel identity is stated
  // over exactly this figure. A cycle's contributing count is its accrued seats
  // plus its reallocated ones, and the record commits to both.
  std::uint64_t assigned = 0;
  for (const auto& [window, value] : rebuild.ledger.assignments) {
    (void)window;
    const auto record = v7::decode_cycle_assignment_value(value);
    if (!record) return false;
    std::uint32_t contributing = record->reallocated_count;
    for (const auto octet : record->accrued_bitmap) {
      contributing += static_cast<std::uint32_t>(std::popcount(octet));
    }
    if (contributing > v7::kMaxU64 - assigned) return false;
    assigned += contributing;
  }
  rebuild.ledger.assigned_permissions = assigned;
  return true;
}

}  // namespace protocol::storage::snapshot_v7
