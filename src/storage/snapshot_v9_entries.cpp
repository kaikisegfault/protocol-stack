// One value decoder per fixed-width economy entry kind, each the exact inverse
// of the encoder in `src/v9/economy_state.cpp` and `src/v9/economy_calendar.cpp`,
// plus the dispatch every kind arrives through. The one variable-width value is
// `snapshot_v9_assignments.cpp`.
//
// **The uptime carrier's two kinds are the exception and store their bytes.**
// `Ledger::uptime` is one raw key-to-value map, so decoding them into fields
// here would be a second encoding of the key space the two version-eight
// transitions write. They are still *checked* — the value must decode, and the
// two states no writer produces are refused — but what is stored is what
// arrived.
//
// **The four kinds version nine adds are decoded into fields**, because version
// nine holds them as typed maps: nothing in this version reads that raw key
// space, the settlement is arithmetic over decoded figures, and ADR 0078 records
// the choice. Which side reads the key space is the whole of the difference
// between these four and the two above.
//
// **Each fails closed on a value no transition could have written**, not merely
// on the wrong width. A seat carrying a referrer identity while its flag is
// clear, an unactivated seat with a nonzero activation height, an identity whose
// next escrow index is below its live count, a balance that minted more than it
// accrued, an exempt slot mask naming a slot past the twenty-fourth, a monthly
// figure of zero seconds, a claim that minted more than it accrued: each is a
// state the conservation invariants forbid, and each has exactly one encoding a
// transition produces. Refusing them here is free — a snapshot is node-local, so
// a rule stricter than the kernel's own decoder changes no accepted state.
//
// **The four new value decoders are the kernel's own**, called rather than
// reimplemented. Each already refuses what its encoder would refuse to write —
// a month index past the calendar, a zero figure, a claim minting more than it
// accrued — so calling them is what keeps the snapshot and the invariant that
// re-reads these entries after the restore from disagreeing about any of it.

#include "snapshot_v9_internal.hpp"

#include <algorithm>
#include <optional>
#include <utility>

namespace protocol::storage::snapshot_v9 {
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

bool apply_seat(Rebuild& rebuild, std::span<const std::uint8_t> key,
                std::span<const std::uint8_t> value) {
  const auto seat_id = read_u32(key, 1);
  if (!seat_id || *seat_id > v9::kMaxSeatId) return false;
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

  v9::SeatRecord seat;
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
  if (key.size() != 2 || key[1] >= v9::kChannelCount) return false;
  const auto index = static_cast<std::size_t>(key[1]);
  const auto issued = read_u64(value, 0);
  const auto outstanding = read_u64(value, 8);
  if (!issued || !outstanding) return false;
  rebuild.ledger.channel_issued[index] = *issued;
  rebuild.ledger.channel_outstanding[index] = *outstanding;
  rebuild.channel_seen[index] = true;
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
      *identity, v9::ReferralBalance{*accrued, *minted, *collected});
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
  if (*seat_count > v9::kMaxSeatsPerIdentity) return false;

  v9::HubIdentityRecord identity;
  identity.hub_public_key = *public_key;
  identity.registered_at_height = *registered;
  identity.next_escrow_index = *next_index;
  identity.escrow_count = *escrow_count;
  identity.seat_count = *seat_count;
  rebuild.ledger.registry.identities.emplace(*hash, identity);
  return true;
}

// Version nine's widened kind 12: three quantities where version eight held two.
//
// **`payable` is between the other two and the value is 24 octets**, so no
// version-eight payload decodes here and no version-nine payload decodes there —
// the width settles it before the field order has to. The kernel's decoder is
// called rather than the fields read inline, because it already enforces the
// encoder's own rule and a second copy of that rule is the thing this project
// has repeatedly paid for.
bool apply_unreferred_pool(Rebuild& rebuild, std::span<const std::uint8_t> value) {
  const auto pool = v9::decode_unreferred_pool_value(value);
  if (!pool) return false;
  rebuild.ledger.pool_accrued = pool->accrued_atomic;
  rebuild.ledger.pool_payable = pool->payable_atomic;
  rebuild.ledger.pool_minted = pool->minted_atomic;
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
  if (*mask > v9::kMaxExemptSlotMask) return false;
  if (*signers > v9::kMaxSignersPerEscrow) return false;

  v9::EscrowRecord record;
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
      *identity, v9::EnrollmentRecord{*enrolled_at, *mark, *issued});
  return true;
}

bool apply_verified_user_counter(Rebuild& rebuild,
                                 std::span<const std::uint8_t> value) {
  const auto enrolled = read_u64(value, 0);
  // Enrollment stops at the founder-directed population, so no transition ever
  // writes a counter above it.
  if (!enrolled || *enrolled > v9::kVerifiedUserPopulation) return false;
  rebuild.ledger.registry.enrolled_count = *enrolled;
  rebuild.verified_user_counter_seen = true;
  return true;
}

// The uptime carrier's two kinds share a 13-octet key whose last four octets are
// the seat identifier, so both arrive here. The identifier is required to name a
// seat the payload carries, which `complete` checks once the whole economy
// section is in.
//
// **There is no separate `kMaxSeatId` bound**, on the shape of the seat entry's
// own, because every seat the chain sold is already inside it: an identifier
// past the capacity fails the existence check too. Two rules where one fires is
// a rule no test can isolate, and this project has twice paid for a probe caught
// by a different rule than the one it named.
bool store_uptime_entry(Rebuild& rebuild, std::span<const std::uint8_t> key,
                        std::span<const std::uint8_t> value) {
  const auto seat_id = read_u32(key, 9);
  if (!seat_id) return false;
  rebuild.referenced_seats.push_back(*seat_id);
  rebuild.ledger.uptime.emplace(v9::Bytes(key.begin(), key.end()),
                                v9::Bytes(value.begin(), value.end()));
  return true;
}

bool apply_recovery_pool(Rebuild& rebuild, std::span<const std::uint8_t> value) {
  const auto legs = v9::decode_recovery_pool_value(value);
  if (!legs) return false;
  rebuild.ledger.pool = *legs;
  rebuild.recovery_pool_seen = true;
  return true;
}

// --- the four kinds version nine adds ---------------------------------------

// Kind 20. The window is unbounded here on purpose: which windows may hold an
// entry is a statement about the head's height, not about this entry, and the
// kernel's retention invariant states it over the whole state at gate 3. A bound
// here would be a second rule firing on the same payloads.
bool apply_window_month(Rebuild& rebuild, std::span<const std::uint8_t> key,
                        std::span<const std::uint8_t> value) {
  const auto window = read_u64(key, 1);
  if (!window) return false;
  const auto month = v9::decode_window_month_value(value);
  if (!month) return false;
  rebuild.ledger.window_months.emplace(*window, *month);
  return true;
}

// Kind 21. **The key is rebuilt and compared rather than merely read.** The
// value decoder bounds the seconds and knows nothing about the month, and the
// month lives in the key; `monthly_figure_key` is the one function that says
// which months a key may name, so asking it is how the bound reaches this entry.
//
// Gate 3 would catch an out-of-range month too, because the cursor's month is
// bounded by its own decoder and every figure must equal it — but it would catch
// it as an unconserved state rather than as a bad entry. A parse error names its
// subject; a failed invariant names a whole payload.
bool apply_monthly_figure(Rebuild& rebuild, std::span<const std::uint8_t> key,
                          std::span<const std::uint8_t> value) {
  const auto month = read_u32(key, 1);
  const auto seat_id = read_u32(key, 5);
  if (!month || !seat_id) return false;
  const auto expected = v9::monthly_figure_key(*month, *seat_id);
  if (!expected || !std::ranges::equal(*expected, key)) return false;
  const auto seconds = v9::decode_monthly_figure_value(value);
  if (!seconds) return false;
  rebuild.ledger.figures.emplace(std::pair{*month, *seat_id}, *seconds);
  // The accumulate step derives its seats from the seat table, so a figure
  // naming a seat the chain never sold is a state no transition produced.
  rebuild.referenced_seats.push_back(*seat_id);
  return true;
}

// Kind 22. A claim is a running balance keyed by the seat, so its identifier
// goes through the same existence check an uptime entry's does. The value
// decoder already refuses a zero `accrued` and a `minted` above it.
bool apply_monthly_claim(Rebuild& rebuild, std::span<const std::uint8_t> key,
                         std::span<const std::uint8_t> value) {
  const auto seat_id = read_u32(key, 1);
  if (!seat_id) return false;
  const auto claim = v9::decode_monthly_claim_value(value);
  if (!claim) return false;
  rebuild.ledger.claims.emplace(*seat_id, *claim);
  rebuild.referenced_seats.push_back(*seat_id);
  return true;
}

// Kind 23. The singleton that says which month is accumulating. Genesis writes
// it and no transition removes it, so its absence is a chain that never opened.
bool apply_settlement_cursor(Rebuild& rebuild,
                             std::span<const std::uint8_t> value) {
  const auto month = v9::decode_settlement_cursor_value(value);
  if (!month) return false;
  rebuild.ledger.accumulating_month = *month;
  rebuild.settlement_cursor_seen = true;
  return true;
}

}  // namespace

bool apply_entry(Rebuild& rebuild, const v9::EconomyEntry& entry) {
  if (entry.key.empty()) return false;
  const auto kind = entry.key.front();
  if (!v9::is_entry_kind(kind)) return false;
  const auto key_width = v9::entry_key_bytes(kind);
  if (!key_width || entry.key.size() != *key_width) return false;
  // `nullopt` is the cycle assignment, whose width follows from its own recorded
  // bit count and is checked by its decoder.
  const auto value_width = v9::entry_value_bytes(kind);
  if (value_width && entry.value.size() != *value_width) return false;

  const std::span<const std::uint8_t> key{entry.key};
  const std::span<const std::uint8_t> value{entry.value};
  switch (static_cast<v9::Entry>(kind)) {
    case v9::Entry::seat:
      return apply_seat(rebuild, key, value);
    case v9::Entry::channel:
      return apply_channel(rebuild, key, value);
    case v9::Entry::cycle_assignment:
      return apply_cycle_assignment(rebuild, key, value);
    case v9::Entry::referral_balance:
      return apply_referral_balance(rebuild, key, value);
    case v9::Entry::direct_decision:
      return apply_direct_decision(rebuild, key, value);
    case v9::Entry::typed_custody:
      return apply_typed_custody(rebuild, key, value);
    case v9::Entry::verifier_key:
      return apply_verifier_key(rebuild, value);
    case v9::Entry::hub_identity:
      return apply_hub_identity(rebuild, key, value);
    case v9::Entry::unreferred_pool:
      return apply_unreferred_pool(rebuild, value);
    case v9::Entry::escrow:
      return apply_escrow(rebuild, key, value);
    case v9::Entry::signer:
      return apply_signer(rebuild, key, value);
    case v9::Entry::verified_user_enrollment:
      return apply_enrollment(rebuild, key, value);
    case v9::Entry::verified_user_counter:
      return apply_verified_user_counter(rebuild, value);
    case v9::Entry::recovery_pool:
      return apply_recovery_pool(rebuild, value);
    case v9::Entry::open_challenge:
      return apply_open_challenge(rebuild, key, value);
    case v9::Entry::seat_window:
      return apply_seat_window(rebuild, key, value);
    case v9::Entry::window_month:
      return apply_window_month(rebuild, key, value);
    case v9::Entry::monthly_uptime_figure:
      return apply_monthly_figure(rebuild, key, value);
    case v9::Entry::monthly_pool_claim:
      return apply_monthly_claim(rebuild, key, value);
    case v9::Entry::settlement_cursor:
      return apply_settlement_cursor(rebuild, value);
  }
  return false;
}

// The two kinds version eight added. Each checks its value and stores the
// entry's own bytes.
bool apply_open_challenge(Rebuild& rebuild, std::span<const std::uint8_t> key,
                          std::span<const std::uint8_t> value) {
  // `0` or `1`; the decoder is the kernel's, so the snapshot and the invariant
  // that re-reads this entry after the restore cannot disagree about it.
  if (!v9::decode_open_challenge_value(value)) return false;
  return store_uptime_entry(rebuild, key, value);
}

bool apply_seat_window(Rebuild& rebuild, std::span<const std::uint8_t> key,
                       std::span<const std::uint8_t> value) {
  // The pad rule and the subset rule, which version eight states outright where
  // version seven states neither for its own bitmap (ADR 0056).
  const auto record = v9::decode_seat_window_value(value);
  if (!record) return false;
  // **The absent-record reading is not a record any chain wrote.** A record
  // comes into existence one of two ways: a dispute sets a bit in `disputed`,
  // or an expiry clears one in `credited`. Neither can leave a fully credited,
  // undisputed window behind, so this value is exactly the state a chain
  // records by writing nothing at all — and carrying it would make the same
  // state representable two ways under one root.
  if (*record == v9::full_seat_window()) return false;
  return store_uptime_entry(rebuild, key, value);
}

bool complete(Rebuild& rebuild) {
  for (const auto seen : rebuild.channel_seen) {
    if (!seen) return false;
  }
  if (!rebuild.recovery_pool_seen || !rebuild.verifier_key_seen ||
      !rebuild.unreferred_pool_seen || !rebuild.verified_user_counter_seen ||
      !rebuild.settlement_cursor_seen) {
    return false;
  }

  // Every writer of a seat-keyed entry resolves the seat from the seat table
  // before it writes, so an entry naming a seat the chain never sold is a state
  // no transition could have produced. It is checked here rather than as each
  // entry arrives, so no value decoder has to depend on kind 1 sorting first —
  // which matters more under version nine, where kinds 21 and 22 join 18 and 19
  // in naming a seat and all four sort after it.
  for (const auto seat_id : rebuild.referenced_seats) {
    if (!rebuild.ledger.seats.contains(seat_id)) return false;
  }

  const auto assigned = derive_assigned_permissions(rebuild.ledger);
  if (!assigned) return false;
  rebuild.ledger.assigned_permissions = *assigned;
  return true;
}

}  // namespace protocol::storage::snapshot_v9
