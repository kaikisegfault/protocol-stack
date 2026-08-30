// One refusal per value rule, each a payload whose only defect is the field
// under test.
//
// Every case here is refused by the entry decoder, which runs before either root
// gate, so each fails with a subject — "this seat entry is impossible" — rather
// than as a digest that disagrees. That is the whole reason the decoders are
// stricter than a width check: a root mismatch tells a reader that something is
// wrong and nothing about what.

#include "snapshot_v7_fixture.hpp"

#include <bit>
#include <variant>

namespace snapshot_v7_tests {
namespace {

struct Fixtures {
  ps::SnapshotParametersV7 pool_parameters;
  Payload pool;
  ps::SnapshotParametersV7 referral_parameters;
  Payload referral;
};

Fixtures build() {
  Fixtures built;
  fixture::Signatures pool_signatures;
  const auto pool = fixture::pool_scenario(pool_signatures);
  built.pool_parameters = ps::snapshot_parameters(pool.ledger);
  built.pool = payload_of(pool.ledger);
  fixture::Signatures referral_signatures;
  const auto referral = fixture::referral_scenario(referral_signatures);
  built.referral_parameters = ps::snapshot_parameters(referral.ledger);
  built.referral = payload_of(referral.ledger);
  return built;
}

// The last entry of a kind, which is the one a key mutation can move without
// disturbing the strict order the payload is also required to be in.
v7::EconomyEntry& last_of(Payload& payload, v7::Entry kind) {
  const auto discriminator = static_cast<std::uint8_t>(kind);
  v7::EconomyEntry* found = nullptr;
  for (auto& entry : payload.economy) {
    if (!entry.key.empty() && entry.key.front() == discriminator) found = &entry;
  }
  pv::require(found != nullptr, "the fixture carries an entry of kind " +
                                    std::to_string(static_cast<unsigned>(kind)));
  return *found;
}

void check_seat(const Payload& base, const ps::SnapshotParametersV7& parameters) {
  auto phantom_referrer = base;
  auto& seat = entry_of(phantom_referrer, v7::Entry::seat);
  pv::require(seat.value[32] == 0, "the fixture's first seat has no referrer");
  seat.value[33] = 0x01;
  require_refusal(phantom_referrer, parameters, ps::SnapshotV7Error::invalid_state,
                  "a seat carrying a referrer while its flag is clear");

  auto phantom_activation = base;
  auto& unactivated = entry_of(phantom_activation, v7::Entry::seat);
  pv::require(unactivated.value[65] == 1, "the fixture's first seat is activated");
  unactivated.value[65] = 0;
  require_refusal(phantom_activation, parameters, ps::SnapshotV7Error::invalid_state,
                  "an unactivated seat with an activation height");

  auto third_boolean = base;
  entry_of(third_boolean, v7::Entry::seat).value[32] = 2;
  require_refusal(third_boolean, parameters, ps::SnapshotV7Error::invalid_state,
                  "a seat flag that is neither zero nor one");

  auto past_capacity = base;
  poke_u32(last_of(past_capacity, v7::Entry::seat).key, 1, v7::kFounderSeatCapacity);
  require_refusal(past_capacity, parameters, ps::SnapshotV7Error::invalid_state,
                  "a seat past the founder capacity");
}

void check_channel_and_pools(const Payload& base,
                             const ps::SnapshotParametersV7& parameters) {
  auto undefined_channel = base;
  last_of(undefined_channel, v7::Entry::channel).key[1] =
      static_cast<std::uint8_t>(v7::kChannelCount);
  require_refusal(undefined_channel, parameters, ps::SnapshotV7Error::invalid_state,
                  "a channel index no manifest defines");

  auto no_pool = base;
  no_pool.economy.erase(find_entry(no_pool, v7::Entry::recovery_pool));
  require_refusal(no_pool, parameters, ps::SnapshotV7Error::invalid_state,
                  "a payload with no recovery pool entry");

  auto no_channel = base;
  no_channel.economy.erase(find_entry(no_channel, v7::Entry::channel));
  require_refusal(no_channel, parameters, ps::SnapshotV7Error::invalid_state,
                  "a payload missing a channel entry");

  auto overdrawn = base;
  auto& unreferred = entry_of(overdrawn, v7::Entry::unreferred_pool);
  poke_u64(unreferred.value, 8, ~std::uint64_t{0});
  require_refusal(overdrawn, parameters, ps::SnapshotV7Error::invalid_state,
                  "an unreferred pool that minted more than it accrued");

  auto over_population = base;
  poke_u64(entry_of(over_population, v7::Entry::verified_user_counter).value, 0,
           v7::kVerifiedUserPopulation + 1);
  require_refusal(over_population, parameters, ps::SnapshotV7Error::invalid_state,
                  "more enrolled identities than the population admits");

  auto other_key = base;
  entry_of(other_key, v7::Entry::verifier_key).value[0] ^= 0xFF;
  require_refusal(other_key, parameters, ps::SnapshotV7Error::invalid_state,
                  "a verifier key entry that disagrees with the prefix");
}

void check_identity_and_escrow(const Payload& base,
                               const ps::SnapshotParametersV7& parameters) {
  auto reissued_index = base;
  auto& identity = entry_of(reissued_index, v7::Entry::hub_identity);
  poke_u32(identity.value, 44, 2);
  poke_u32(identity.value, 40, 1);
  require_refusal(reissued_index, parameters, ps::SnapshotV7Error::invalid_state,
                  "an identity whose next index is below its live count");

  auto too_many_seats = base;
  poke_u32(entry_of(too_many_seats, v7::Entry::hub_identity).value, 48,
           v7::kMaxSeatsPerIdentity + 1);
  require_refusal(too_many_seats, parameters, ps::SnapshotV7Error::invalid_state,
                  "an identity holding more seats than the limit");

  auto impossible_slot = base;
  poke_u32(entry_of(impossible_slot, v7::Entry::escrow).value, 41,
           v7::kMaxExemptSlotMask + 1);
  require_refusal(impossible_slot, parameters, ps::SnapshotV7Error::invalid_state,
                  "an exempt slot mask naming a slot past the twenty-fourth");

  auto too_many_signers = base;
  poke_u32(entry_of(too_many_signers, v7::Entry::escrow).value, 45,
           v7::kMaxSignersPerEscrow + 1);
  require_refusal(too_many_signers, parameters, ps::SnapshotV7Error::invalid_state,
                  "an escrow holding more signers than the limit");

  auto third_boolean = base;
  entry_of(third_boolean, v7::Entry::escrow).value[32] = 2;
  require_refusal(third_boolean, parameters, ps::SnapshotV7Error::invalid_state,
                  "an escrow posture flag that is neither zero nor one");
}

void check_custody(const Payload& base, const ps::SnapshotParametersV7& parameters) {
  auto named_beneficiary = base;
  entry_of(named_beneficiary, v7::Entry::typed_custody).key[2] = 0x01;
  require_refusal(named_beneficiary, parameters, ps::SnapshotV7Error::invalid_state,
                  "a custody entry naming a beneficiary no leg credits");

  auto unknown_kind = base;
  last_of(unknown_kind, v7::Entry::typed_custody).key[1] = 5;
  require_refusal(unknown_kind, parameters, ps::SnapshotV7Error::invalid_state,
                  "a custody entry of a kind no leg writes");
}

// The record is the one value whose width follows from its own contents, and the
// one the mint's walk reads directly, so each rule is checked in isolation: the
// mutation that tests the bit count also fixes the share, and the one that tests
// the share leaves the count alone.
void check_cycle_assignment(const Payload& base,
                            const ps::SnapshotParametersV7& parameters) {
  // Each pad case compensates the counts the extra bit would otherwise break,
  // so the pad rule is the only rule left to refuse it. A first attempt set the
  // bit and nothing else, and it was caught by the contributing bound instead —
  // which is a passing test that establishes nothing about padding.
  auto padded = base;
  auto& record = entry_of(padded, v7::Entry::cycle_assignment);
  pv::require(record.value.size() == v7::kCycleAssignmentFixedBytes + 2,
              "the fixture's first record carries one octet per bitmap");
  const auto original = v7::decode_cycle_assignment_value(record.value);
  pv::require(original.has_value(), "the fixture's first record decodes");
  pv::require(original->bitmap_bits <= 7,
              "the fixture's first record leaves a pad bit to set");
  record.value[v7::kCycleAssignmentFixedBytes] |= 0x01;
  poke_u32(record.value, 16, original->in_scope_count + 1);
  require_refusal(padded, parameters, ps::SnapshotV7Error::invalid_state,
                  "an accrued bitmap with a bit set past its own count");

  auto padded_winners = base;
  auto& winner_record = entry_of(padded_winners, v7::Entry::cycle_assignment);
  winner_record.value[v7::kCycleAssignmentFixedBytes + 1] |= 0x01;
  const auto widened = original->winner_count + 1;
  poke_u32(winner_record.value, 12, widened);
  poke_u64(winner_record.value, 0,
           v7::split_permission(widened).share[v7::kFounderOperatorChannel]);
  require_refusal(padded_winners, parameters, ps::SnapshotV7Error::invalid_state,
                  "a winner bitmap with a bit set past its own count");

  auto miscounted = base;
  auto& winners = entry_of(miscounted, v7::Entry::cycle_assignment);
  const auto packed = winners.value[v7::kCycleAssignmentFixedBytes + 1];
  const auto claimed =
      static_cast<std::uint32_t>(std::popcount(packed)) + 1;
  poke_u32(winners.value, 12, claimed);
  poke_u64(winners.value, 0,
           v7::split_permission(claimed).share[v7::kFounderOperatorChannel]);
  require_refusal(miscounted, parameters, ps::SnapshotV7Error::invalid_state,
                  "an assignment record whose winner count is not its bitmap");

  auto overpaid = base;
  auto& share = entry_of(overpaid, v7::Entry::cycle_assignment);
  const auto current = v7::decode_cycle_assignment_value(share.value);
  pv::require(current.has_value(), "the fixture's first record decodes");
  poke_u64(share.value, 0, current->share_per_winner_atomic + 1);
  require_refusal(overpaid, parameters, ps::SnapshotV7Error::invalid_state,
                  "an assignment record paying a share its winner count forbids");

  auto over_scope = base;
  auto& scope = entry_of(over_scope, v7::Entry::cycle_assignment);
  const auto decoded = v7::decode_cycle_assignment_value(scope.value);
  pv::require(decoded.has_value(), "the fixture's first record decodes");
  poke_u32(scope.value, 8, decoded->in_scope_count + 1);
  require_refusal(over_scope, parameters, ps::SnapshotV7Error::invalid_state,
                  "an assignment record contributing more seats than it measured");
}

void check_referral(const Payload& base, const ps::SnapshotParametersV7& parameters) {
  auto overdrawn = base;
  auto& balance = entry_of(overdrawn, v7::Entry::referral_balance);
  poke_u64(balance.value, 8, ~std::uint64_t{0});
  require_refusal(overdrawn, parameters, ps::SnapshotV7Error::invalid_state,
                  "a referral balance that minted more than it accrued");
}

}  // namespace

void verify_entry_refusals() {
  const auto fixtures = build();
  for (const auto* pair : {&fixtures.pool, &fixtures.referral}) {
    const auto parameters = pair == &fixtures.pool ? fixtures.pool_parameters
                                                   : fixtures.referral_parameters;
    const auto decoded = ps::decode_snapshot_v7(pair->encode(), parameters);
    pv::require(std::holds_alternative<ps::DecodedSnapshotV7>(decoded),
                "each refusal fixture's own payload must restore");
  }
  check_seat(fixtures.pool, fixtures.pool_parameters);
  check_channel_and_pools(fixtures.pool, fixtures.pool_parameters);
  check_identity_and_escrow(fixtures.pool, fixtures.pool_parameters);
  check_custody(fixtures.pool, fixtures.pool_parameters);
  check_cycle_assignment(fixtures.pool, fixtures.pool_parameters);
  check_referral(fixtures.referral, fixtures.referral_parameters);
}

}  // namespace snapshot_v7_tests
