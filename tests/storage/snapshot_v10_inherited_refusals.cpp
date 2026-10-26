// The value rules version eight wrote, one case per rule, carried to version
// ten.
//
// **This is version eight's sweep, moved a second time.** ADR 0092 moved it
// from `storage_snapshot_v8_tests` into version nine's suite when version
// eight's stack was deleted, and ADR 0104's last step will delete version
// nine's, so each case is carried across with its reasoning, rebound to a
// version-ten fixture.
//
// Two fixtures carry every kind these cases mutate. The version-ten chain
// holds the seat, the channel, the assignment record, the identity, the
// escrow, a window record, a referral balance, and the four custody legs. The
// same chain run forward through quiet heights, with no machine answering, to
// the first height that issues a challenge holds an open challenge beside its
// window record.
//
// **The referral balance and the custody entries are the chain's own**, where
// version nine's suite had to insert them because its trace wrote neither. So
// each refusal mutates an entry a block wrote, and each is paired with a
// control: the same entry changed lawfully in shape, resealed, which gets past
// every decoder and stops at gate 3 because no block wrote that amount. The
// control is what makes the refusal the decoder rule's rather than a refusal
// of an entry out of place.

#include "snapshot_v10_fixture.hpp"

#include <algorithm>
#include <bit>
#include <string>
#include <utility>
#include <variant>

namespace snapshot_v10_tests {
namespace {

void check_seat(const Payload& base, const ps::SnapshotParametersV10& parameters) {
  auto phantom_referrer = base;
  auto& seat = entry_of(phantom_referrer, v10::Entry::seat);
  pv::require(seat.value[32] == 0, "the fixture's first seat has no referrer");
  seat.value[33] = 0x01;
  require_refusal(phantom_referrer, parameters, ps::SnapshotV10Error::invalid_state,
                  "a seat carrying a referrer while its flag is clear");

  auto phantom_activation = base;
  auto& unactivated = entry_of(phantom_activation, v10::Entry::seat);
  pv::require(unactivated.value[65] == 1, "the fixture's first seat is activated");
  unactivated.value[65] = 0;
  require_refusal(phantom_activation, parameters, ps::SnapshotV10Error::invalid_state,
                  "an unactivated seat with an activation height");
}

void check_channels(const Payload& base,
                    const ps::SnapshotParametersV10& parameters) {
  // An eleventh channel is *added* rather than an existing one renamed:
  // renaming leaves the manifest's tenth channel absent, and the presence check
  // refuses that too, so a rename can pass without the index bound ever being
  // reached. The bound guards a write into a ten-element array, so it is worth
  // isolating.
  auto undefined_channel = base;
  const auto last_channel = std::find_if(
      undefined_channel.economy.rbegin(), undefined_channel.economy.rend(),
      [](const v10::EconomyEntry& entry) {
        return !entry.key.empty() &&
               entry.key.front() == static_cast<std::uint8_t>(v10::Entry::channel);
      });
  pv::require(last_channel != undefined_channel.economy.rend(),
              "the fixture carries a channel entry");
  auto eleventh = *last_channel;
  eleventh.key[1] = static_cast<std::uint8_t>(v10::kChannelCount);
  undefined_channel.economy.insert(last_channel.base(), eleventh);
  require_refusal(undefined_channel, parameters, ps::SnapshotV10Error::invalid_state,
                  "an eleventh channel");

  auto no_channel = base;
  no_channel.economy.erase(find_entry(no_channel, v10::Entry::channel));
  require_refusal(no_channel, parameters, ps::SnapshotV10Error::invalid_state,
                  "a payload missing a channel entry");
}

void check_identity_and_escrow(const Payload& base,
                               const ps::SnapshotParametersV10& parameters) {
  auto too_many_seats = base;
  poke_u32(entry_of(too_many_seats, v10::Entry::hub_identity).value, 48,
           v10::kMaxSeatsPerIdentity + 1);
  require_refusal(too_many_seats, parameters, ps::SnapshotV10Error::invalid_state,
                  "an identity holding more seats than the limit");

  auto impossible_slot = base;
  poke_u32(entry_of(impossible_slot, v10::Entry::escrow).value, 41,
           v10::kMaxExemptSlotMask + 1);
  require_refusal(impossible_slot, parameters, ps::SnapshotV10Error::invalid_state,
                  "an exempt slot mask naming a slot past the twenty-fourth");

  auto too_many_signers = base;
  poke_u32(entry_of(too_many_signers, v10::Entry::escrow).value, 45,
           v10::kMaxSignersPerEscrow + 1);
  require_refusal(too_many_signers, parameters, ps::SnapshotV10Error::invalid_state,
                  "an escrow holding more signers than the limit");

  auto third_boolean = base;
  entry_of(third_boolean, v10::Entry::escrow).value[32] = 2;
  require_refusal(third_boolean, parameters, ps::SnapshotV10Error::invalid_state,
                  "an escrow posture flag that is neither zero nor one");
}

// The record is the one value whose width follows from its own contents, and
// the one the mint's walk reads directly, so each rule is checked in isolation:
// the mutation that tests the bit count also fixes the share, and the one that
// tests the share leaves the count alone.
void check_cycle_assignment(const Payload& base,
                            const ps::SnapshotParametersV10& parameters) {
  // Each pad case compensates the counts the extra bit would otherwise break,
  // so the pad rule is the only rule left to refuse it. Version eight's first
  // attempt set the bit and nothing else, and it was caught by the contributing
  // bound instead — a passing test that establishes nothing about padding.
  auto padded = base;
  auto& record = entry_of(padded, v10::Entry::cycle_assignment);
  pv::require(record.value.size() == v10::kCycleAssignmentFixedBytes + 2,
              "the fixture's first record carries one octet per bitmap");
  const auto original = v10::decode_cycle_assignment_value(record.value);
  pv::require(original.has_value(), "the fixture's first record decodes");
  pv::require(original->bitmap_bits <= 7,
              "the fixture's first record leaves a pad bit to set");
  record.value[v10::kCycleAssignmentFixedBytes] |= 0x01;
  poke_u32(record.value, 16, original->in_scope_count + 1);
  require_refusal(padded, parameters, ps::SnapshotV10Error::invalid_state,
                  "an accrued bitmap with a bit set past its own count");

  auto padded_winners = base;
  auto& winner_record = entry_of(padded_winners, v10::Entry::cycle_assignment);
  winner_record.value[v10::kCycleAssignmentFixedBytes + 1] |= 0x01;
  const auto widened = original->winner_count + 1;
  poke_u32(winner_record.value, 12, widened);
  poke_u64(winner_record.value, 0,
           v10::split_permission(widened).share[v10::kFounderOperatorChannel]);
  require_refusal(padded_winners, parameters, ps::SnapshotV10Error::invalid_state,
                  "a winner bitmap with a bit set past its own count");

  auto miscounted = base;
  auto& winners = entry_of(miscounted, v10::Entry::cycle_assignment);
  const auto packed = winners.value[v10::kCycleAssignmentFixedBytes + 1];
  const auto claimed = static_cast<std::uint32_t>(std::popcount(packed)) + 1;
  poke_u32(winners.value, 12, claimed);
  poke_u64(winners.value, 0,
           v10::split_permission(claimed).share[v10::kFounderOperatorChannel]);
  require_refusal(miscounted, parameters, ps::SnapshotV10Error::invalid_state,
                  "an assignment record whose winner count is not its bitmap");

  auto overpaid = base;
  auto& share = entry_of(overpaid, v10::Entry::cycle_assignment);
  poke_u64(share.value, 0, original->share_per_winner_atomic + 1);
  require_refusal(overpaid, parameters, ps::SnapshotV10Error::invalid_state,
                  "an assignment record paying a share its winner count forbids");

  auto over_scope = base;
  auto& scope = entry_of(over_scope, v10::Entry::cycle_assignment);
  poke_u32(scope.value, 8, original->in_scope_count + 1);
  require_refusal(over_scope, parameters, ps::SnapshotV10Error::invalid_state,
                  "an assignment record contributing more seats than it measured");
}

// The two kinds version eight added. The retention rule and the deadline rule
// are **not** here: they are properties of where an entry sits in a state rather
// than of its own octets, so the conservation gate refuses them.
void check_uptime(const Payload& base, const ps::SnapshotParametersV10& parameters) {
  auto third_state = base;
  auto& challenge = last_of(third_state, v10::Entry::open_challenge);
  pv::require(challenge.value.size() == 1, "an open challenge value is one octet");
  challenge.value[0] = 2;
  require_refusal(third_state, parameters, ps::SnapshotV10Error::invalid_state,
                  "an open challenge state that is neither zero nor one");

  // Both halves of the pad rule are checked, because a decoder that masked one
  // and not the other would pass a test that only set the first.
  auto padded_credit = base;
  auto& credited = last_of(padded_credit, v10::Entry::seat_window);
  const auto record = v10::decode_seat_window_value(credited.value);
  pv::require(record.has_value(), "the fixture's window record decodes");
  poke_u32(credited.value, 0, record->credited | (1U << v10::kSlotsPerWindow));
  require_refusal(padded_credit, parameters, ps::SnapshotV10Error::invalid_state,
                  "a credited bitmap with a pad bit set");

  auto padded_dispute = base;
  auto& disputed = last_of(padded_dispute, v10::Entry::seat_window);
  poke_u32(disputed.value, 4, record->disputed | (1U << v10::kSlotsPerWindow));
  require_refusal(padded_dispute, parameters, ps::SnapshotV10Error::invalid_state,
                  "a disputed bitmap with a pad bit set");

  // A dispute may only void a slot the seat was credited for.
  auto phantom_dispute = base;
  auto& subset = last_of(phantom_dispute, v10::Entry::seat_window);
  const auto uncredited = (~record->credited) & v10::kSlotBitmapMask;
  pv::require(uncredited != 0, "the fixture's window record lost a slot");
  poke_u32(subset.value, 4, record->disputed | uncredited);
  require_refusal(phantom_dispute, parameters, ps::SnapshotV10Error::invalid_state,
                  "a dispute of a slot the seat was never credited for");

  // **The last three are resealed, and that is what makes them worth having.**
  // Each survives both root gates by construction once resealed and the
  // conservation invariants say nothing about it, so without the decoder rule a
  // restore would accept the payload outright.
  //
  // A fully credited, undisputed window is what a chain records by writing
  // nothing at all, so carrying it would make one state representable two ways
  // under one root.
  auto absent_reading = base;
  auto& full = last_of(absent_reading, v10::Entry::seat_window);
  const auto empty = v10::seat_window_value(v10::full_seat_window());
  pv::require(empty.has_value(), "the absent-record reading encodes");
  full.value = *empty;
  reseal(absent_reading);
  require_refusal(absent_reading, parameters, ps::SnapshotV10Error::invalid_state,
                  "a window record equal to the absent-record reading");

  // Both writers resolve the seat from the seat table before they write, so an
  // uptime entry naming a seat the chain never sold is unreachable. The two
  // kinds are checked separately: a rule applied to one and not the other would
  // pass a test that only moved a window record.
  auto unsold_window = base;
  poke_u32(last_of(unsold_window, v10::Entry::seat_window).key, 9, v10::kMaxSeatId);
  reseal(unsold_window);
  require_refusal(unsold_window, parameters, ps::SnapshotV10Error::invalid_state,
                  "a window record naming a seat the chain never sold");

  auto unsold_challenge = base;
  poke_u32(last_of(unsold_challenge, v10::Entry::open_challenge).key, 9,
           v10::kMaxSeatId);
  reseal(unsold_challenge);
  require_refusal(unsold_challenge, parameters, ps::SnapshotV10Error::invalid_state,
                  "an open challenge naming a seat the chain never sold");
}

// The lawful twin of a refusal gets past every decoder and stops at gate 3,
// because no block wrote it: so the refusal beside it is the decoder's.
void require_control(const Payload& payload,
                     const ps::SnapshotParametersV10& parameters,
                     const std::string& subject) {
  require_refusal(payload, parameters, ps::SnapshotV10Error::not_conserved,
                  subject + ", with a lawful value");
}

// The chain's one referral balance, which Bob's seat accrues to Alice. The
// version-nine rules of its own are here too: it belongs to an identity some
// seat refers from, and it is never zero (ADR 0093).
void check_referral(const Payload& base,
                    const ps::SnapshotParametersV10& parameters) {
  {
    // The control: one more unit accrued and not minted is a balance owing what
    // the referral channel never counted, so gate 3 is where it must stop.
    auto payload = base;
    auto& value = entry_of(payload, v10::Entry::referral_balance).value;
    poke_u64(value, 0, peek_u64(value, 0) + 1);
    reseal(payload);
    require_control(payload, parameters, "a referral balance");
  }
  {
    auto payload = base;
    auto& value = entry_of(payload, v10::Entry::referral_balance).value;
    poke_u64(value, 8, peek_u64(value, 0) + 1);
    require_refusal(payload, parameters, ps::SnapshotV10Error::invalid_state,
                    "a referral balance that minted more than it accrued");
  }
  {
    // A balance is created by accruing a whole leg to it, so zero is absence.
    auto payload = base;
    auto& value = entry_of(payload, v10::Entry::referral_balance).value;
    poke_u64(value, 0, 0);
    poke_u64(value, 8, 0);
    require_refusal(payload, parameters, ps::SnapshotV10Error::invalid_state,
                    "a referral balance that accrued nothing");
  }
  {
    // **The same balance with nobody referring from it.** The referring seat's
    // flag and field are cleared together, as a seat with no referrer writes
    // them, so the seat is lawful and the balance is what is orphaned. Gate 3
    // cannot see an orphan that owes nothing, so this is `complete`'s rule.
    auto payload = base;
    const auto& balance = entry_of(payload, v10::Entry::referral_balance);
    const v10::Bytes referrer(balance.key.begin() + 1, balance.key.end());
    bool cleared = false;
    for (auto& entry : payload.economy) {
      if (entry.key.front() != static_cast<std::uint8_t>(v10::Entry::seat) ||
          entry.value[32] != 1 ||
          !std::equal(referrer.begin(), referrer.end(), entry.value.begin() + 33)) {
        continue;
      }
      entry.value[32] = 0;
      std::fill(entry.value.begin() + 33, entry.value.begin() + 65, 0);
      cleared = true;
    }
    pv::require(cleared, "a seat of the chain refers from the balance's owner");
    require_refusal(payload, parameters, ps::SnapshotV10Error::invalid_state,
                    "a referral balance no seat's referrer owns");
  }
}

// The four institutional legs are channels 1 through 4 and every one credits
// the singleton beneficiary, which is the zero identifier. The chain's mints
// wrote all four, and the cases change the **last**, so a key mutation that
// makes it larger keeps the strict order the section is required to be in.
void check_custody(const Payload& base,
                   const ps::SnapshotParametersV10& parameters) {
  {
    auto payload = base;
    auto& value = last_of(payload, v10::Entry::typed_custody).value;
    poke_u64(value, 0, peek_u64(value, 0) + 5);
    reseal(payload);
    require_control(payload, parameters, "a custody entry");
  }
  {
    auto payload = base;
    last_of(payload, v10::Entry::typed_custody).key[2] = 1;
    require_refusal(payload, parameters, ps::SnapshotV10Error::invalid_state,
                    "a custody entry naming a beneficiary no leg credits");
  }
  {
    auto payload = base;
    auto& entry = last_of(payload, v10::Entry::typed_custody);
    pv::require(entry.key[1] == 4, "the chain's last custody leg is channel 4");
    entry.key[1] = 5;
    require_refusal(payload, parameters, ps::SnapshotV10Error::invalid_state,
                    "a custody entry of a kind no leg writes");
  }
}

struct Fixture {
  ps::SnapshotParametersV10 parameters;
  Payload payload;
};

Fixture fixture_of(const v10::Ledger& ledger) {
  Fixture built{ps::snapshot_parameters(ledger), payload_of(ledger)};
  const auto decoded = ps::decode_snapshot_v10(built.payload.encode(),
                                              built.parameters);
  pv::require(std::holds_alternative<ps::DecodedSnapshotV10>(decoded),
              "each refusal fixture's own payload must restore");
  return built;
}

// The chain run forward with nobody answering, to the first height whose block
// issues a challenge, which is left open beside the window record the chain
// already holds. Bounded by one window, because every in-scope seat is audited
// in every window.
v10::Ledger audited_ledger(const Fixtures& fixtures) {
  auto ledger = fixtures.chain.ledger;
  const auto verify = fixtures.chain_signatures.verifier();
  const auto limit = ledger.height + v10::kCycleBlocks;
  const auto open = [&ledger] {
    return std::any_of(ledger.uptime.begin(), ledger.uptime.end(),
                       [](const auto& entry) {
                         return entry.first.front() ==
                                static_cast<std::uint8_t>(v10::Entry::open_challenge);
                       });
  };
  while (!open()) {
    pv::require(ledger.height < limit, "a quiet window issues a challenge");
    const auto run = v10::run_quiet_heights(
        ledger, ledger.height + 1,
        [](std::uint64_t height) { return fixture::timestamp_of_height(height); },
        verify);
    pv::require(run.has_value(), "a quiet height executes");
  }
  return ledger;
}

}  // namespace

void verify_inherited_refusals(const Fixtures& fixtures) {
  const auto settled = fixture_of(fixtures.chain.ledger);
  const auto audited = fixture_of(audited_ledger(fixtures));
  for (const auto kind : {v10::Entry::open_challenge, v10::Entry::seat_window}) {
    auto payload = audited.payload;
    pv::require(find_entry(payload, kind) != payload.economy.end(),
                "the audited fixture carries both uptime kinds");
  }

  check_seat(settled.payload, settled.parameters);
  check_channels(settled.payload, settled.parameters);
  check_identity_and_escrow(settled.payload, settled.parameters);
  check_cycle_assignment(settled.payload, settled.parameters);
  check_uptime(audited.payload, audited.parameters);
  check_referral(settled.payload, settled.parameters);
  check_custody(settled.payload, settled.parameters);
}

}  // namespace snapshot_v10_tests
