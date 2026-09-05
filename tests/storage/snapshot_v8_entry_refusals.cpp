// One refusal per value rule, each a payload whose only defect is the field
// under test.
//
// Every case here is refused by the entry decoder, which runs before either root
// gate, so each fails with a subject — "this seat entry is impossible" — rather
// than as a digest that disagrees. That is the whole reason the decoders are
// stricter than a width check: a root mismatch tells a reader that something is
// wrong and nothing about what.

#include "snapshot_v8_fixture.hpp"

#include <algorithm>
#include <bit>
#include <variant>

namespace snapshot_v8_tests {
namespace {

// `measured` carries every entry kind version seven's rules are stated over —
// the seat, the channel, the assignment record, the referral balance, the
// custody legs, the identity, and the escrow — where version seven needed two
// scenarios to reach them all. `deadline` is the only one that retains both
// uptime kinds at once, so it is where version eight's own rules are checked.
struct Fixtures {
  ps::SnapshotParametersV8 measured_parameters;
  Payload measured;
  ps::SnapshotParametersV8 deadline_parameters;
  Payload deadline;
};

Fixtures build() {
  Fixtures built;
  fixture::Signatures measured_signatures;
  const auto measured = fixture::measured_scenario(measured_signatures);
  built.measured_parameters = ps::snapshot_parameters(measured.ledger);
  built.measured = payload_of(measured.ledger);
  fixture::Signatures deadline_signatures;
  const auto deadline = fixture::deadline_scenario(deadline_signatures);
  built.deadline_parameters = ps::snapshot_parameters(deadline.ledger);
  built.deadline = payload_of(deadline.ledger);
  return built;
}

void check_seat(const Payload& base, const ps::SnapshotParametersV8& parameters) {
  auto phantom_referrer = base;
  auto& seat = entry_of(phantom_referrer, v8::Entry::seat);
  pv::require(seat.value[32] == 0, "the fixture's first seat has no referrer");
  seat.value[33] = 0x01;
  require_refusal(phantom_referrer, parameters, ps::SnapshotV8Error::invalid_state,
                  "a seat carrying a referrer while its flag is clear");

  auto phantom_activation = base;
  auto& unactivated = entry_of(phantom_activation, v8::Entry::seat);
  pv::require(unactivated.value[65] == 1, "the fixture's first seat is activated");
  unactivated.value[65] = 0;
  require_refusal(phantom_activation, parameters, ps::SnapshotV8Error::invalid_state,
                  "an unactivated seat with an activation height");

  auto third_boolean = base;
  entry_of(third_boolean, v8::Entry::seat).value[32] = 2;
  require_refusal(third_boolean, parameters, ps::SnapshotV8Error::invalid_state,
                  "a seat flag that is neither zero nor one");

  auto past_capacity = base;
  poke_u32(last_of(past_capacity, v8::Entry::seat).key, 1, v8::kFounderSeatCapacity);
  require_refusal(past_capacity, parameters, ps::SnapshotV8Error::invalid_state,
                  "a seat past the founder capacity");
}

void check_channel_and_pools(const Payload& base,
                             const ps::SnapshotParametersV8& parameters) {
  // An eleventh channel is *added* rather than an existing one renamed: renaming
  // leaves the manifest's tenth channel absent, and the presence check refuses
  // that — so the first attempt passed while proving nothing about the index
  // bound. The bound guards a write into a ten-element array, so it is worth
  // isolating.
  auto undefined_channel = base;
  const auto last_channel = std::find_if(
      undefined_channel.economy.rbegin(), undefined_channel.economy.rend(),
      [](const v8::EconomyEntry& entry) {
        return !entry.key.empty() &&
               entry.key.front() == static_cast<std::uint8_t>(v8::Entry::channel);
      });
  pv::require(last_channel != undefined_channel.economy.rend(),
              "the fixture carries a channel entry");
  auto eleventh = *last_channel;
  eleventh.key[1] = static_cast<std::uint8_t>(v8::kChannelCount);
  undefined_channel.economy.insert(last_channel.base(), eleventh);
  require_refusal(undefined_channel, parameters, ps::SnapshotV8Error::invalid_state,
                  "a channel index no manifest defines");

  auto no_pool = base;
  no_pool.economy.erase(find_entry(no_pool, v8::Entry::recovery_pool));
  require_refusal(no_pool, parameters, ps::SnapshotV8Error::invalid_state,
                  "a payload with no recovery pool entry");

  auto no_channel = base;
  no_channel.economy.erase(find_entry(no_channel, v8::Entry::channel));
  require_refusal(no_channel, parameters, ps::SnapshotV8Error::invalid_state,
                  "a payload missing a channel entry");

  auto overdrawn = base;
  auto& unreferred = entry_of(overdrawn, v8::Entry::unreferred_pool);
  poke_u64(unreferred.value, 8, ~std::uint64_t{0});
  require_refusal(overdrawn, parameters, ps::SnapshotV8Error::invalid_state,
                  "an unreferred pool that minted more than it accrued");

  auto over_population = base;
  poke_u64(entry_of(over_population, v8::Entry::verified_user_counter).value, 0,
           v8::kVerifiedUserPopulation + 1);
  require_refusal(over_population, parameters, ps::SnapshotV8Error::invalid_state,
                  "more enrolled identities than the population admits");

  auto other_key = base;
  entry_of(other_key, v8::Entry::verifier_key).value[0] ^= 0xFF;
  require_refusal(other_key, parameters, ps::SnapshotV8Error::invalid_state,
                  "a verifier key entry that disagrees with the prefix");
}

void check_identity_and_escrow(const Payload& base,
                               const ps::SnapshotParametersV8& parameters) {
  auto reissued_index = base;
  auto& identity = entry_of(reissued_index, v8::Entry::hub_identity);
  poke_u32(identity.value, 44, 2);
  poke_u32(identity.value, 40, 1);
  require_refusal(reissued_index, parameters, ps::SnapshotV8Error::invalid_state,
                  "an identity whose next index is below its live count");

  auto too_many_seats = base;
  poke_u32(entry_of(too_many_seats, v8::Entry::hub_identity).value, 48,
           v8::kMaxSeatsPerIdentity + 1);
  require_refusal(too_many_seats, parameters, ps::SnapshotV8Error::invalid_state,
                  "an identity holding more seats than the limit");

  auto impossible_slot = base;
  poke_u32(entry_of(impossible_slot, v8::Entry::escrow).value, 41,
           v8::kMaxExemptSlotMask + 1);
  require_refusal(impossible_slot, parameters, ps::SnapshotV8Error::invalid_state,
                  "an exempt slot mask naming a slot past the twenty-fourth");

  auto too_many_signers = base;
  poke_u32(entry_of(too_many_signers, v8::Entry::escrow).value, 45,
           v8::kMaxSignersPerEscrow + 1);
  require_refusal(too_many_signers, parameters, ps::SnapshotV8Error::invalid_state,
                  "an escrow holding more signers than the limit");

  auto third_boolean = base;
  entry_of(third_boolean, v8::Entry::escrow).value[32] = 2;
  require_refusal(third_boolean, parameters, ps::SnapshotV8Error::invalid_state,
                  "an escrow posture flag that is neither zero nor one");
}

void check_custody(const Payload& base, const ps::SnapshotParametersV8& parameters) {
  auto named_beneficiary = base;
  entry_of(named_beneficiary, v8::Entry::typed_custody).key[2] = 0x01;
  require_refusal(named_beneficiary, parameters, ps::SnapshotV8Error::invalid_state,
                  "a custody entry naming a beneficiary no leg credits");

  auto unknown_kind = base;
  last_of(unknown_kind, v8::Entry::typed_custody).key[1] = 5;
  require_refusal(unknown_kind, parameters, ps::SnapshotV8Error::invalid_state,
                  "a custody entry of a kind no leg writes");
}

// The record is the one value whose width follows from its own contents, and the
// one the mint's walk reads directly, so each rule is checked in isolation: the
// mutation that tests the bit count also fixes the share, and the one that tests
// the share leaves the count alone.
void check_cycle_assignment(const Payload& base,
                            const ps::SnapshotParametersV8& parameters) {
  // Each pad case compensates the counts the extra bit would otherwise break,
  // so the pad rule is the only rule left to refuse it. A first attempt set the
  // bit and nothing else, and it was caught by the contributing bound instead —
  // which is a passing test that establishes nothing about padding.
  auto padded = base;
  auto& record = entry_of(padded, v8::Entry::cycle_assignment);
  pv::require(record.value.size() == v8::kCycleAssignmentFixedBytes + 2,
              "the fixture's first record carries one octet per bitmap");
  const auto original = v8::decode_cycle_assignment_value(record.value);
  pv::require(original.has_value(), "the fixture's first record decodes");
  pv::require(original->bitmap_bits <= 7,
              "the fixture's first record leaves a pad bit to set");
  record.value[v8::kCycleAssignmentFixedBytes] |= 0x01;
  poke_u32(record.value, 16, original->in_scope_count + 1);
  require_refusal(padded, parameters, ps::SnapshotV8Error::invalid_state,
                  "an accrued bitmap with a bit set past its own count");

  auto padded_winners = base;
  auto& winner_record = entry_of(padded_winners, v8::Entry::cycle_assignment);
  winner_record.value[v8::kCycleAssignmentFixedBytes + 1] |= 0x01;
  const auto widened = original->winner_count + 1;
  poke_u32(winner_record.value, 12, widened);
  poke_u64(winner_record.value, 0,
           v8::split_permission(widened).share[v8::kFounderOperatorChannel]);
  require_refusal(padded_winners, parameters, ps::SnapshotV8Error::invalid_state,
                  "a winner bitmap with a bit set past its own count");

  auto miscounted = base;
  auto& winners = entry_of(miscounted, v8::Entry::cycle_assignment);
  const auto packed = winners.value[v8::kCycleAssignmentFixedBytes + 1];
  const auto claimed =
      static_cast<std::uint32_t>(std::popcount(packed)) + 1;
  poke_u32(winners.value, 12, claimed);
  poke_u64(winners.value, 0,
           v8::split_permission(claimed).share[v8::kFounderOperatorChannel]);
  require_refusal(miscounted, parameters, ps::SnapshotV8Error::invalid_state,
                  "an assignment record whose winner count is not its bitmap");

  auto overpaid = base;
  auto& share = entry_of(overpaid, v8::Entry::cycle_assignment);
  const auto current = v8::decode_cycle_assignment_value(share.value);
  pv::require(current.has_value(), "the fixture's first record decodes");
  poke_u64(share.value, 0, current->share_per_winner_atomic + 1);
  require_refusal(overpaid, parameters, ps::SnapshotV8Error::invalid_state,
                  "an assignment record paying a share its winner count forbids");

  auto over_scope = base;
  auto& scope = entry_of(over_scope, v8::Entry::cycle_assignment);
  const auto decoded = v8::decode_cycle_assignment_value(scope.value);
  pv::require(decoded.has_value(), "the fixture's first record decodes");
  poke_u32(scope.value, 8, decoded->in_scope_count + 1);
  require_refusal(over_scope, parameters, ps::SnapshotV8Error::invalid_state,
                  "an assignment record contributing more seats than it measured");
}

// The two entry kinds version eight adds. Every case here is refused before any
// root is taken, so a reader is told which rule the entry broke rather than that
// a digest disagrees — which is the whole reason these decoders are stricter than
// a width check.
//
// The retention rule and the deadline rule are **not** here. Those are properties
// of where an entry sits in a state rather than of its own octets, so the
// conservation gate is what refuses them and `snapshot_v8_refusals.cpp` is where
// they are checked.
void check_uptime(const Payload& base, const ps::SnapshotParametersV8& parameters) {
  auto third_state = base;
  auto& challenge = last_of(third_state, v8::Entry::open_challenge);
  pv::require(challenge.value.size() == 1, "an open challenge value is one octet");
  challenge.value[0] = 2;
  require_refusal(third_state, parameters, ps::SnapshotV8Error::invalid_state,
                  "an open challenge state that is neither zero nor one");

  // The pad rule version eight states outright, where version seven states none
  // for its own bitmap (ADR 0056). Both halves are checked, because a decoder
  // that masked one and not the other would pass a test that only set the first.
  auto padded_credit = base;
  auto& credited = last_of(padded_credit, v8::Entry::seat_window);
  const auto record = v8::decode_seat_window_value(credited.value);
  pv::require(record.has_value(), "the fixture's window record decodes");
  poke_u32(credited.value, 0, record->credited | (1U << v8::kSlotsPerWindow));
  require_refusal(padded_credit, parameters, ps::SnapshotV8Error::invalid_state,
                  "a credited bitmap with a pad bit set");

  auto padded_dispute = base;
  auto& disputed = last_of(padded_dispute, v8::Entry::seat_window);
  poke_u32(disputed.value, 4, record->disputed | (1U << v8::kSlotsPerWindow));
  require_refusal(padded_dispute, parameters, ps::SnapshotV8Error::invalid_state,
                  "a disputed bitmap with a pad bit set");

  // A dispute may only void a slot the seat was credited for, so `disputed` is a
  // subset of `credited` in every record a transition writes.
  auto phantom_dispute = base;
  auto& subset = last_of(phantom_dispute, v8::Entry::seat_window);
  const auto uncredited = (~record->credited) & v8::kSlotBitmapMask;
  pv::require(uncredited != 0, "the fixture's window record lost a slot");
  poke_u32(subset.value, 4, record->disputed | uncredited);
  require_refusal(phantom_dispute, parameters, ps::SnapshotV8Error::invalid_state,
                  "a dispute of a slot the seat was never credited for");

  // **The last three are resealed, and that is what makes them worth having.**
  // The cases above are also refused by an invariant a step later, so what the
  // decoder buys there is a named subject. These three are not: each survives
  // both root gates by construction once resealed, and the conservation
  // invariants say nothing about either of them — so without the decoder rule a
  // restore would accept the payload outright. The refusal below is the only
  // one there is.

  // The version-eight rule with no version-seven ancestor. A record is created
  // by a dispute setting a bit or an expiry clearing one, so neither writer can
  // leave a fully credited, undisputed window behind — that state is what a
  // chain records by writing nothing at all, and carrying it would make one
  // state representable two ways under one root.
  auto absent_reading = base;
  auto& full = last_of(absent_reading, v8::Entry::seat_window);
  const auto empty = v8::seat_window_value(v8::full_seat_window());
  pv::require(empty.has_value(), "the absent-record reading encodes");
  full.value = *empty;
  reseal(absent_reading);
  require_refusal(absent_reading, parameters, ps::SnapshotV8Error::invalid_state,
                  "a window record equal to the absent-record reading");

  // Both writers resolve the seat from the seat table before they write, so an
  // uptime entry naming a seat the chain never sold is unreachable. It is
  // checked once the payload is in rather than as the entry arrives, so the two
  // kinds are checked separately: a rule applied to one and not the other would
  // pass a test that only moved a window record.
  auto unsold_window = base;
  poke_u32(last_of(unsold_window, v8::Entry::seat_window).key, 9,
           v8::kMaxSeatId);
  reseal(unsold_window);
  require_refusal(unsold_window, parameters, ps::SnapshotV8Error::invalid_state,
                  "a window record naming a seat the chain never sold");

  auto unsold_challenge = base;
  poke_u32(last_of(unsold_challenge, v8::Entry::open_challenge).key, 9,
           v8::kMaxSeatId);
  reseal(unsold_challenge);
  require_refusal(unsold_challenge, parameters, ps::SnapshotV8Error::invalid_state,
                  "an open challenge naming a seat the chain never sold");
}

void check_referral(const Payload& base, const ps::SnapshotParametersV8& parameters) {
  auto overdrawn = base;
  auto& balance = entry_of(overdrawn, v8::Entry::referral_balance);
  poke_u64(balance.value, 8, ~std::uint64_t{0});
  require_refusal(overdrawn, parameters, ps::SnapshotV8Error::invalid_state,
                  "a referral balance that minted more than it accrued");
}

}  // namespace

void verify_entry_refusals() {
  const auto fixtures = build();
  for (const auto* pair : {&fixtures.measured, &fixtures.deadline}) {
    const auto parameters = pair == &fixtures.measured
                                ? fixtures.measured_parameters
                                : fixtures.deadline_parameters;
    const auto decoded = ps::decode_snapshot_v8(pair->encode(), parameters);
    pv::require(std::holds_alternative<ps::DecodedSnapshotV8>(decoded),
                "each refusal fixture's own payload must restore");
  }
  check_seat(fixtures.measured, fixtures.measured_parameters);
  check_channel_and_pools(fixtures.measured, fixtures.measured_parameters);
  check_identity_and_escrow(fixtures.measured, fixtures.measured_parameters);
  check_custody(fixtures.measured, fixtures.measured_parameters);
  check_cycle_assignment(fixtures.measured, fixtures.measured_parameters);
  check_referral(fixtures.measured, fixtures.measured_parameters);
  check_uptime(fixtures.deadline, fixtures.deadline_parameters);
}

}  // namespace snapshot_v8_tests
