// The value rules version nine inherits, one case per rule.
//
// **This is version eight's sweep, moved here when ADR 0092 deleted it.**
// `snapshot_v9_entry_refusals.cpp` samples the inherited rules to show the port
// kept them, and until then `storage_snapshot_v8_tests` held the full set over
// the same decoders' originals. A deletion that went by filename would have
// left every rule below with no snapshot-level check at all, so each case is
// carried across with its reasoning, rebound to a version-nine fixture.
//
// Two fixtures carry every inherited kind a version-nine chain writes:
// `settled` for the seat, the channel, the assignment record, the identity, and
// the escrow, and the same chain rebuilt to its first audit height for both
// uptime kinds. That rebuild is what version eight's `deadline` scenario was
// here: the one state that holds an open challenge and a window record at once.
//
// **Two inherited kinds no version-nine chain writes**, because the trace buys
// every seat without a referrer and issues nothing directly: the referral
// balance and the typed custody entry. Each is inserted, and each refusal is
// paired with a control that inserts the same entry lawfully and requires the
// restore either to succeed or to get *past* the decoder and fail at gate 3.
// The control is what makes the refusal the decoder rule's: without it, an
// inserted entry refused for being out of place would pass a test about its
// value. The referral balance also carries version nine's two rules of its own,
// that it belongs to an identity some seat refers from and is never zero.

#include "snapshot_v9_fixture.hpp"

#include <algorithm>
#include <bit>
#include <string>
#include <utility>
#include <variant>

namespace snapshot_v9_tests {
namespace {

void check_seat(const Payload& base, const ps::SnapshotParametersV9& parameters) {
  auto phantom_referrer = base;
  auto& seat = entry_of(phantom_referrer, v9::Entry::seat);
  pv::require(seat.value[32] == 0, "the fixture's first seat has no referrer");
  seat.value[33] = 0x01;
  require_refusal(phantom_referrer, parameters, ps::SnapshotV9Error::invalid_state,
                  "a seat carrying a referrer while its flag is clear");

  auto phantom_activation = base;
  auto& unactivated = entry_of(phantom_activation, v9::Entry::seat);
  pv::require(unactivated.value[65] == 1, "the fixture's first seat is activated");
  unactivated.value[65] = 0;
  require_refusal(phantom_activation, parameters, ps::SnapshotV9Error::invalid_state,
                  "an unactivated seat with an activation height");
}

void check_channels(const Payload& base,
                    const ps::SnapshotParametersV9& parameters) {
  // An eleventh channel is *added* rather than an existing one renamed:
  // renaming leaves the manifest's tenth channel absent, and the presence check
  // refuses that too, so a rename can pass without the index bound ever being
  // reached. The bound guards a write into a ten-element array, so it is worth
  // isolating.
  auto undefined_channel = base;
  const auto last_channel = std::find_if(
      undefined_channel.economy.rbegin(), undefined_channel.economy.rend(),
      [](const v9::EconomyEntry& entry) {
        return !entry.key.empty() &&
               entry.key.front() == static_cast<std::uint8_t>(v9::Entry::channel);
      });
  pv::require(last_channel != undefined_channel.economy.rend(),
              "the fixture carries a channel entry");
  auto eleventh = *last_channel;
  eleventh.key[1] = static_cast<std::uint8_t>(v9::kChannelCount);
  undefined_channel.economy.insert(last_channel.base(), eleventh);
  require_refusal(undefined_channel, parameters, ps::SnapshotV9Error::invalid_state,
                  "an eleventh channel");

  auto no_channel = base;
  no_channel.economy.erase(find_entry(no_channel, v9::Entry::channel));
  require_refusal(no_channel, parameters, ps::SnapshotV9Error::invalid_state,
                  "a payload missing a channel entry");
}

void check_identity_and_escrow(const Payload& base,
                               const ps::SnapshotParametersV9& parameters) {
  auto too_many_seats = base;
  poke_u32(entry_of(too_many_seats, v9::Entry::hub_identity).value, 48,
           v9::kMaxSeatsPerIdentity + 1);
  require_refusal(too_many_seats, parameters, ps::SnapshotV9Error::invalid_state,
                  "an identity holding more seats than the limit");

  auto impossible_slot = base;
  poke_u32(entry_of(impossible_slot, v9::Entry::escrow).value, 41,
           v9::kMaxExemptSlotMask + 1);
  require_refusal(impossible_slot, parameters, ps::SnapshotV9Error::invalid_state,
                  "an exempt slot mask naming a slot past the twenty-fourth");

  auto too_many_signers = base;
  poke_u32(entry_of(too_many_signers, v9::Entry::escrow).value, 45,
           v9::kMaxSignersPerEscrow + 1);
  require_refusal(too_many_signers, parameters, ps::SnapshotV9Error::invalid_state,
                  "an escrow holding more signers than the limit");

  auto third_boolean = base;
  entry_of(third_boolean, v9::Entry::escrow).value[32] = 2;
  require_refusal(third_boolean, parameters, ps::SnapshotV9Error::invalid_state,
                  "an escrow posture flag that is neither zero nor one");
}

// The record is the one value whose width follows from its own contents, and
// the one the mint's walk reads directly, so each rule is checked in isolation:
// the mutation that tests the bit count also fixes the share, and the one that
// tests the share leaves the count alone.
void check_cycle_assignment(const Payload& base,
                            const ps::SnapshotParametersV9& parameters) {
  // Each pad case compensates the counts the extra bit would otherwise break,
  // so the pad rule is the only rule left to refuse it. Version eight's first
  // attempt set the bit and nothing else, and it was caught by the contributing
  // bound instead — a passing test that establishes nothing about padding.
  auto padded = base;
  auto& record = entry_of(padded, v9::Entry::cycle_assignment);
  pv::require(record.value.size() == v9::kCycleAssignmentFixedBytes + 2,
              "the fixture's first record carries one octet per bitmap");
  const auto original = v9::decode_cycle_assignment_value(record.value);
  pv::require(original.has_value(), "the fixture's first record decodes");
  pv::require(original->bitmap_bits <= 7,
              "the fixture's first record leaves a pad bit to set");
  record.value[v9::kCycleAssignmentFixedBytes] |= 0x01;
  poke_u32(record.value, 16, original->in_scope_count + 1);
  require_refusal(padded, parameters, ps::SnapshotV9Error::invalid_state,
                  "an accrued bitmap with a bit set past its own count");

  auto padded_winners = base;
  auto& winner_record = entry_of(padded_winners, v9::Entry::cycle_assignment);
  winner_record.value[v9::kCycleAssignmentFixedBytes + 1] |= 0x01;
  const auto widened = original->winner_count + 1;
  poke_u32(winner_record.value, 12, widened);
  poke_u64(winner_record.value, 0,
           v9::split_permission(widened).share[v9::kFounderOperatorChannel]);
  require_refusal(padded_winners, parameters, ps::SnapshotV9Error::invalid_state,
                  "a winner bitmap with a bit set past its own count");

  auto miscounted = base;
  auto& winners = entry_of(miscounted, v9::Entry::cycle_assignment);
  const auto packed = winners.value[v9::kCycleAssignmentFixedBytes + 1];
  const auto claimed = static_cast<std::uint32_t>(std::popcount(packed)) + 1;
  poke_u32(winners.value, 12, claimed);
  poke_u64(winners.value, 0,
           v9::split_permission(claimed).share[v9::kFounderOperatorChannel]);
  require_refusal(miscounted, parameters, ps::SnapshotV9Error::invalid_state,
                  "an assignment record whose winner count is not its bitmap");

  auto overpaid = base;
  auto& share = entry_of(overpaid, v9::Entry::cycle_assignment);
  poke_u64(share.value, 0, original->share_per_winner_atomic + 1);
  require_refusal(overpaid, parameters, ps::SnapshotV9Error::invalid_state,
                  "an assignment record paying a share its winner count forbids");

  auto over_scope = base;
  auto& scope = entry_of(over_scope, v9::Entry::cycle_assignment);
  poke_u32(scope.value, 8, original->in_scope_count + 1);
  require_refusal(over_scope, parameters, ps::SnapshotV9Error::invalid_state,
                  "an assignment record contributing more seats than it measured");
}

// The two kinds version eight added. The retention rule and the deadline rule
// are **not** here: they are properties of where an entry sits in a state rather
// than of its own octets, so the conservation gate refuses them.
void check_uptime(const Payload& base, const ps::SnapshotParametersV9& parameters) {
  auto third_state = base;
  auto& challenge = last_of(third_state, v9::Entry::open_challenge);
  pv::require(challenge.value.size() == 1, "an open challenge value is one octet");
  challenge.value[0] = 2;
  require_refusal(third_state, parameters, ps::SnapshotV9Error::invalid_state,
                  "an open challenge state that is neither zero nor one");

  // Both halves of the pad rule are checked, because a decoder that masked one
  // and not the other would pass a test that only set the first.
  auto padded_credit = base;
  auto& credited = last_of(padded_credit, v9::Entry::seat_window);
  const auto record = v9::decode_seat_window_value(credited.value);
  pv::require(record.has_value(), "the fixture's window record decodes");
  poke_u32(credited.value, 0, record->credited | (1U << v9::kSlotsPerWindow));
  require_refusal(padded_credit, parameters, ps::SnapshotV9Error::invalid_state,
                  "a credited bitmap with a pad bit set");

  auto padded_dispute = base;
  auto& disputed = last_of(padded_dispute, v9::Entry::seat_window);
  poke_u32(disputed.value, 4, record->disputed | (1U << v9::kSlotsPerWindow));
  require_refusal(padded_dispute, parameters, ps::SnapshotV9Error::invalid_state,
                  "a disputed bitmap with a pad bit set");

  // A dispute may only void a slot the seat was credited for.
  auto phantom_dispute = base;
  auto& subset = last_of(phantom_dispute, v9::Entry::seat_window);
  const auto uncredited = (~record->credited) & v9::kSlotBitmapMask;
  pv::require(uncredited != 0, "the fixture's window record lost a slot");
  poke_u32(subset.value, 4, record->disputed | uncredited);
  require_refusal(phantom_dispute, parameters, ps::SnapshotV9Error::invalid_state,
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
  auto& full = last_of(absent_reading, v9::Entry::seat_window);
  const auto empty = v9::seat_window_value(v9::full_seat_window());
  pv::require(empty.has_value(), "the absent-record reading encodes");
  full.value = *empty;
  reseal(absent_reading);
  require_refusal(absent_reading, parameters, ps::SnapshotV9Error::invalid_state,
                  "a window record equal to the absent-record reading");

  // Both writers resolve the seat from the seat table before they write, so an
  // uptime entry naming a seat the chain never sold is unreachable. The two
  // kinds are checked separately: a rule applied to one and not the other would
  // pass a test that only moved a window record.
  auto unsold_window = base;
  poke_u32(last_of(unsold_window, v9::Entry::seat_window).key, 9, v9::kMaxSeatId);
  reseal(unsold_window);
  require_refusal(unsold_window, parameters, ps::SnapshotV9Error::invalid_state,
                  "a window record naming a seat the chain never sold");

  auto unsold_challenge = base;
  poke_u32(last_of(unsold_challenge, v9::Entry::open_challenge).key, 9,
           v9::kMaxSeatId);
  reseal(unsold_challenge);
  require_refusal(unsold_challenge, parameters, ps::SnapshotV9Error::invalid_state,
                  "an open challenge naming a seat the chain never sold");
}

// Insert `entry` where the strict key order puts it, then reseal, so the only
// thing wrong with the payload is whatever the entry itself carries.
Payload with_entry(const Payload& base, v9::EconomyEntry entry) {
  auto payload = base;
  const auto position = std::lower_bound(
      payload.economy.begin(), payload.economy.end(), entry,
      [](const v9::EconomyEntry& left, const v9::EconomyEntry& right) {
        return left.key < right.key;
      });
  pv::require(position == payload.economy.end() || position->key != entry.key,
              "an inserted entry must not replace one the chain wrote");
  payload.economy.insert(position, std::move(entry));
  reseal(payload);
  return payload;
}

// The lawful twin of a refusal gets past every decoder and stops at gate 3,
// because no block wrote it: so the refusal beside it is the decoder's.
void require_control(const Payload& payload,
                     const ps::SnapshotParametersV9& parameters,
                     const std::string& subject) {
  require_refusal(payload, parameters, ps::SnapshotV9Error::not_conserved,
                  subject + ", with a lawful value");
}

void require_restores(const Payload& payload,
                      const ps::SnapshotParametersV9& parameters,
                      const std::string& subject) {
  const auto decoded = ps::decode_snapshot_v9(payload.encode(), parameters);
  pv::require(std::holds_alternative<ps::DecodedSnapshotV9>(decoded),
              subject + " must restore");
}

// **The fixture's last seat is given a referrer**, because no version-nine chain
// writes one: the trace buys every seat without. The referrer is a registered
// identity other than the seat's owner, since a purchase refuses to refer
// oneself, and the payload is resealed and required to restore before any case
// uses it. Every lawful balance below is keyed to that identity; the orphan is
// the same entry on the payload where no seat names it.
void check_referral(const Payload& base,
                    const ps::SnapshotParametersV9& parameters) {
  auto referred = base;
  auto& seat = last_of(referred, v9::Entry::seat);
  pv::require(seat.value[32] == 0, "the fixture's last seat has no referrer");
  const v9::Bytes owner(seat.value.begin(), seat.value.begin() + 32);
  v9::Bytes referrer;
  for (const auto& entry : referred.economy) {
    if (entry.key.front() != static_cast<std::uint8_t>(v9::Entry::hub_identity)) {
      continue;
    }
    const v9::Bytes identity(entry.key.begin() + 1, entry.key.end());
    if (identity != owner) referrer = identity;
  }
  pv::require(referrer.size() == 32, "a second registered identity exists");
  seat.value[32] = 1;
  std::copy(referrer.begin(), referrer.end(), seat.value.begin() + 33);
  reseal(referred);
  require_restores(referred, parameters, "a seat naming another identity");

  const auto referral = [&referrer](std::uint64_t accrued, std::uint64_t minted) {
    v9::EconomyEntry entry;
    entry.key = {static_cast<std::uint8_t>(v9::Entry::referral_balance)};
    entry.key.insert(entry.key.end(), referrer.begin(), referrer.end());
    entry.value = v9::referral_balance_value(accrued, minted, 0);
    return entry;
  };

  // **A balance its referrer owns restores, and the same balance with nobody
  // referring from it does not** (ADR 0093). The pair differs in the seat's
  // flag and nothing else, and the balance owes nothing, which is exactly what
  // gate 3 cannot see: it sums what balances owe.
  require_restores(with_entry(referred, referral(10, 10)), parameters,
                   "a fully minted balance its referrer owns");
  require_refusal(with_entry(base, referral(10, 10)), parameters,
                  ps::SnapshotV9Error::invalid_state,
                  "a referral balance no seat's referrer owns");
  // A balance is created by accruing a whole leg to it, so zero is absence.
  require_refusal(with_entry(referred, referral(0, 0)), parameters,
                  ps::SnapshotV9Error::invalid_state,
                  "a referral balance that accrued nothing");

  // The inherited rule, over a balance the referrer owns so that nothing but
  // the value is wrong. Its control owes ten units that the referral channel
  // never counted, so gate 3 is where it must stop.
  require_control(with_entry(referred, referral(10, 0)), parameters,
                  "a referral balance");
  require_refusal(with_entry(referred, referral(10, 11)), parameters,
                  ps::SnapshotV9Error::invalid_state,
                  "a referral balance that minted more than it accrued");
}

void check_custody(const Payload& base,
                   const ps::SnapshotParametersV9& parameters) {
  // The four institutional legs are channels 1 through 4 and every one credits
  // the singleton beneficiary, which is the zero identifier.
  const auto custody = [](std::uint8_t leg, std::uint8_t beneficiary) {
    v9::EconomyEntry entry;
    entry.key = {static_cast<std::uint8_t>(v9::Entry::typed_custody), leg};
    entry.key.resize(34, 0);
    entry.key[2] = beneficiary;
    entry.value = v9::typed_custody_value(5);
    return entry;
  };
  require_control(with_entry(base, custody(1, 0)), parameters, "a custody entry");
  require_refusal(with_entry(base, custody(1, 1)), parameters,
                  ps::SnapshotV9Error::invalid_state,
                  "a custody entry naming a beneficiary no leg credits");
  require_refusal(with_entry(base, custody(5, 0)), parameters,
                  ps::SnapshotV9Error::invalid_state,
                  "a custody entry of a kind no leg writes");
}

struct Fixture {
  ps::SnapshotParametersV9 parameters;
  Payload payload;
};

Fixture fixture_of(const v9::Ledger& ledger) {
  Fixture built{ps::snapshot_parameters(ledger), payload_of(ledger)};
  const auto decoded = ps::decode_snapshot_v9(built.payload.encode(),
                                              built.parameters);
  pv::require(std::holds_alternative<ps::DecodedSnapshotV9>(decoded),
              "each refusal fixture's own payload must restore");
  return built;
}

}  // namespace

void verify_inherited_refusals() {
  fixture::Signatures settled_signatures;
  const auto settled_chain = fixture::settled_scenario(settled_signatures);
  const auto settled = fixture_of(settled_chain.ledger);

  // The first audit after the setup segment is where the first challenge is
  // issued, so the chain rebuilt to that height holds it open beside the window
  // record an earlier lost slot left.
  pv::require(settled_chain.audit_blocks.size() > 1,
              "the settled chain audits more than its first height");
  fixture::Signatures audited_signatures;
  const auto audited_chain = fixture::rebuilt_chain_to(
      audited_signatures, settled_chain.audit_blocks[1].height);
  const auto audited = fixture_of(audited_chain.ledger);
  for (const auto kind : {v9::Entry::open_challenge, v9::Entry::seat_window}) {
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

}  // namespace snapshot_v9_tests
