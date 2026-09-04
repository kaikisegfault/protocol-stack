// The 62 contract vectors a ledger is needed for.
//
// `economy-transition-v8.txt` records 183 vectors and `economy_v8_codec_tests`
// reproduces the 121 a codec can derive. The other 62 are here: kind 20's
// positive control and its nine ordered refusals, kind 21's and its ten, the
// schedule derivation, the settlement claim, expiry, and containment.
//
// **Every refusal is produced by executing a minimally mutated input against a
// positive control that is accepted unmutated**, and the control is checked
// beside them so a suite that stopped accepting anything would fail rather than
// look complete. Every mutation is aimed: a probe that trips a *different*
// condition than the one it names has proved nothing about the condition it
// names, so each body below disturbs one field and compensates whatever else
// that disturbs.
//
// **The transitions are reached through `execute`**, which is the public entry a
// block uses, so version seven's shared envelope checks run first exactly as
// they do on a chain. The accepted Python model calls them directly; reaching
// them this way is strictly stronger, because a condition that could only be
// reached with the envelope checks bypassed would fail here.

#include "economy_v8_execution_fixture.hpp"

#include <algorithm>
#include <array>
#include <bit>
#include <string_view>

namespace economy_v8_execution {
namespace {

// The fixture's own constants, distinct from the recorded trace's so that a
// reader cannot mistake one for the other.
constexpr std::uint32_t kActiveSeat = 1;
constexpr std::uint32_t kLateSeat = 2;
constexpr std::uint32_t kUnactivatedSeat = 3;
constexpr std::uint32_t kSecondSeat = 4;
constexpr std::uint64_t kActiveActivation = 100;
constexpr std::uint64_t kLateActivation = v8::kCycleBlocks + 100;
constexpr std::uint64_t kProbeWindow = 1;
// One height inside window 1, slot 0, comfortably before the excluded tail.
constexpr std::uint64_t kProbeChallengeHeight = v8::kCycleBlocks + 40;
constexpr std::uint64_t kProbeResponseHeight = kProbeChallengeHeight + 1;
constexpr std::uint64_t kProbeBalance = 1'000'000;

const Octets32 kHolderIdentity = repeated(0x11);
const Octets32 kStrangerIdentity = repeated(0x22);
const Octets32 kHolderKey = repeated(0x13);
const Octets32 kStrangerKey = repeated(0x23);

// A chain with two identities, an escrow each, and three seats: one activated
// early enough to be in scope for window 1, one activated inside it, and one
// never activated at all.
struct Fixture {
  v8::Ledger ledger;
  Octets32 holder_escrow{};
  Octets32 stranger_escrow{};
};

void add_identity(v8::Ledger& ledger, const Octets32& identity,
                  const Octets32& key, const Octets32& signer_public_key,
                  Octets32& escrow_out) {
  v8::HubIdentityRecord record;
  record.hub_public_key = key;
  ledger.registry.identities[identity] = record;
  const auto escrow = v8::escrow_id(identity, 0);
  v8::EscrowRecord entry;
  entry.owner_hub_identity = identity;
  entry.posture.requires_confirmation = false;
  entry.signer_count = 1;
  ledger.registry.escrows[escrow] = entry;
  protocol::v1::Account account;
  account.balance = kProbeBalance;
  ledger.registry.accounts[escrow] = account;
  ledger.registry.signers[v8::signer_id(signer_public_key)] = escrow;
  escrow_out = escrow;
}

Fixture make_fixture(std::uint64_t height) {
  Fixture fixture;
  auto opened = v8::open_ledger(trace_genesis());
  pv::require(opened.has_value(), "the probe genesis opens a ledger");
  fixture.ledger = std::move(*opened);
  fixture.ledger.height = height;
  add_identity(fixture.ledger, kHolderIdentity, kHolderKey, kAliceSignerKey,
               fixture.holder_escrow);
  add_identity(fixture.ledger, kStrangerIdentity, kStrangerKey, kBobSignerKey,
               fixture.stranger_escrow);

  const auto seat = [&](std::uint32_t id, std::uint64_t activation, bool active) {
    v8::SeatRecord record;
    record.hub_identity_hash = kHolderIdentity;
    record.is_activated = active;
    record.activation_height = active ? activation : 0;
    fixture.ledger.seats[id] = record;
  };
  seat(kActiveSeat, kActiveActivation, true);
  seat(kLateSeat, kLateActivation, true);
  seat(kUnactivatedSeat, 0, false);
  return fixture;
}

std::string execute_response(Signatures& signatures, v8::Ledger& ledger,
                             const Octets32& signer_key, const Octets32& escrow,
                             std::uint32_t seat_id,
                             std::uint64_t challenge_height) {
  const auto nonce = ledger.registry.accounts.at(escrow).nonce + 1;
  const auto raw = response_input(signatures, ledger, signer_key, seat_id,
                                  challenge_height, nonce);
  const auto decoded = v8::decode_signed(raw);
  pv::require(decoded.has_value(), "the probe response is admitted");
  const auto outcome = v8::execute(ledger, decoded->envelope, signatures.verifier());
  pv::require(outcome.has_value(), "the probe response produces a result");
  const auto name = v8::result_code_name(static_cast<std::uint8_t>(outcome->result));
  pv::require(name.has_value(), "the result code has a name");
  return std::string(*name);
}

std::string execute_dispute(Signatures& signatures, v8::Ledger& ledger,
                            std::uint32_t seat_id, std::uint64_t cycle_window,
                            std::uint8_t slot_index,
                            const Octets32& authority = kDisputeAuthorityKey,
                            const std::uint8_t* signed_slot = nullptr) {
  const auto nonce = ledger.registry.accounts.at(v8::escrow_id(kHolderIdentity, 0))
                         .nonce + 1;
  const auto raw =
      dispute_input(signatures, ledger, kAliceSignerKey, seat_id, cycle_window,
                    slot_index, nonce, authority, kReasonCode, signed_slot);
  const auto decoded = v8::decode_signed(raw);
  pv::require(decoded.has_value(), "the probe dispute is admitted");
  const auto outcome = v8::execute(ledger, decoded->envelope, signatures.verifier());
  pv::require(outcome.has_value(), "the probe dispute produces a result");
  const auto name = v8::result_code_name(static_cast<std::uint8_t>(outcome->result));
  pv::require(name.has_value(), "the result code has a name");
  return std::string(*name);
}

// One outstanding challenge, written with the public codec so the fixture and
// the issue step agree on the key by construction.
void issue(v8::Ledger& ledger, std::uint64_t height, std::uint32_t seat_id) {
  const auto value = v8::open_challenge_value(v8::kChallengeOutstanding);
  pv::require(value.has_value(), "an outstanding challenge encodes");
  ledger.uptime[v8::open_challenge_key(height, seat_id)] = *value;
}

void check_response(const pv::Values& contract) {
  Signatures signatures;
  auto fixture = make_fixture(kProbeResponseHeight);
  issue(fixture.ledger, kProbeChallengeHeight, kActiveSeat);
  pv::require(execute_response(signatures, fixture.ledger, kAliceSignerKey,
                               fixture.holder_escrow, kActiveSeat,
                               kProbeChallengeHeight) == "SUCCESS",
              "the control response is accepted");
  expect_true(contract, "kind20.control.is_accepted");
  const auto answered = v8::decode_open_challenge_value(
      fixture.ledger.uptime.at(
          v8::open_challenge_key(kProbeChallengeHeight, kActiveSeat)));
  pv::require(answered.has_value(), "the entry decodes after the response");
  agree(contract, "kind20.control.marks_the_challenge_answered",
        static_cast<std::uint64_t>(*answered));
  // No credited slot is added, because a slot bit is already set and only
  // expiry or a dispute ever clears one.
  pv::require(std::none_of(fixture.ledger.uptime.begin(),
                           fixture.ledger.uptime.end(),
                           [](const auto& entry) {
                             return entry.first.front() ==
                                    static_cast<std::uint8_t>(v8::Entry::seat_window);
                           }),
              "an accepted response writes no window record");
  expect_true(contract, "kind20.control.writes_no_window_record");

  // Each refusal on its own copy of the control, so nothing a previous probe
  // wrote can be what refuses the next one.
  const auto refuse = [&](std::uint32_t seat_id, std::uint64_t challenge_height,
                          std::uint64_t height, bool issued, bool twice,
                          bool stranger) {
    Signatures local;
    auto probe = make_fixture(height);
    if (issued) issue(probe.ledger, challenge_height, seat_id);
    const auto& escrow = stranger ? probe.stranger_escrow : probe.holder_escrow;
    const auto& key = stranger ? kBobSignerKey : kAliceSignerKey;
    if (twice) {
      execute_response(local, probe.ledger, key, escrow, seat_id, challenge_height);
    }
    return execute_response(local, probe.ledger, key, escrow, seat_id,
                            challenge_height);
  };
  const auto control_height = kProbeResponseHeight;
  pv::require(refuse(v8::kMaxSeatId + 1, kProbeChallengeHeight, control_height,
                     true, false, false) == "CYCLE_RANGE",
              "a seat above the capacity");
  expect_true(contract, "kind20.refuses.cycle_range");
  pv::require(refuse(900, kProbeChallengeHeight, control_height, true, false,
                     false) == "SEAT_NOT_PURCHASED",
              "a seat the chain has not sold");
  expect_true(contract, "kind20.refuses.seat_not_purchased");
  pv::require(refuse(kUnactivatedSeat, kProbeChallengeHeight, control_height, true,
                     false, false) == "SEAT_NOT_ACTIVATED",
              "a seat nobody runs");
  expect_true(contract, "kind20.refuses.seat_not_activated");
  pv::require(refuse(kActiveSeat, kProbeChallengeHeight, control_height, true,
                     false, true) == "UNAUTHORIZED",
              "an escrow the seat's identity does not own");
  expect_true(contract, "kind20.refuses.unauthorized");
  pv::require(refuse(kLateSeat, kProbeChallengeHeight, control_height, true, false,
                     false) == "SEAT_NOT_IN_SCOPE",
              "a seat activated inside the executing window");
  expect_true(contract, "kind20.refuses.seat_not_in_scope");
  pv::require(refuse(kActiveSeat, control_height, control_height, true, false,
                     false) == "CHALLENGE_NOT_OPEN",
              "a challenge height at the executing height");
  expect_true(contract, "kind20.refuses.challenge_not_open_for_the_current_height");
  pv::require(refuse(kActiveSeat, kProbeChallengeHeight - v8::kSlotBlocks,
                     control_height, true, false, false) == "CHALLENGE_NOT_OPEN",
              "a challenge height in an earlier slot");
  expect_true(contract, "kind20.refuses.challenge_not_open_across_a_slot");
  pv::require(refuse(kActiveSeat, kProbeChallengeHeight, control_height, false,
                     false, false) == "CHALLENGE_NOT_ISSUED",
              "a challenge the chain never issued");
  expect_true(contract, "kind20.refuses.challenge_not_issued");
  pv::require(refuse(kActiveSeat, kProbeChallengeHeight, control_height, true,
                     true, false) == "RESPONSE_REPLAY",
              "a second response to one challenge");
  expect_true(contract, "kind20.refuses.response_replay");

  // The deadline boundary, and the reordering it forces.
  const auto deadline = kProbeChallengeHeight + v8::kResponseDeadlineBlocks;
  pv::require(refuse(kActiveSeat, kProbeChallengeHeight, deadline, true, false,
                     false) == "SUCCESS",
              "a response at the deadline");
  expect_true(contract, "kind20.accepts_at_the_deadline");
  pv::require(refuse(kActiveSeat, kProbeChallengeHeight, deadline + 1, true, false,
                     false) == "RESPONSE_TOO_LATE",
              "a response one height past the deadline");
  expect_true(contract, "kind20.refuses_one_height_past_the_deadline");
  // **Condition 7 precedes condition 8**, so a response past the deadline is
  // reported late even when the entry is gone — which it always is, because the
  // expiry step deleted it. Reporting `CHALLENGE_NOT_ISSUED` there would say a
  // challenge that *was* issued never was.
  pv::require(refuse(kActiveSeat, kProbeChallengeHeight, deadline + 1, false,
                     false, false) == "RESPONSE_TOO_LATE",
              "a late response with no entry left to find");
  expect_true(contract,
              "kind20.reports_late_rather_than_unissued_when_the_entry_is_gone");
  agree(contract, "kind20.deadline_blocks", v8::kResponseDeadlineBlocks);
}

void check_dispute(const pv::Values& contract) {
  // Window 1 is disputable exactly while the executing height is inside
  // window 2.
  const auto height = v8::kCycleBlocks * (kProbeWindow + 1) + 5;
  Signatures signatures;
  auto fixture = make_fixture(height);
  pv::require(execute_dispute(signatures, fixture.ledger, kActiveSeat, kProbeWindow,
                              0) == "SUCCESS",
              "the control dispute is accepted");
  expect_true(contract, "kind21.control.is_accepted");
  const auto record =
      v8::seat_window_record(fixture.ledger, kProbeWindow, kActiveSeat);
  pv::require(record.has_value(), "the record decodes after the dispute");
  agree(contract, "kind21.control.credited_is_unchanged", record->credited);
  agree(contract, "kind21.control.disputed_bit", record->disputed);
  agree(contract, "kind21.control.uptime_seconds_after",
        v8::uptime_seconds(*record));

  const auto refuse = [&](std::uint32_t seat_id, std::uint64_t window,
                          std::uint8_t slot, const Octets32& authority,
                          const std::uint8_t* signed_slot, bool prefill) {
    Signatures local;
    auto probe = make_fixture(height);
    if (prefill) {
      // Six disputes already filed, which is the founder-directed cap.
      for (std::uint8_t taken = 0; taken < v8::kDisputeCapSlotsPerSeat; ++taken) {
        pv::require(execute_dispute(local, probe.ledger, kActiveSeat, kProbeWindow,
                                    taken) == "SUCCESS",
                    "a filling dispute is accepted");
      }
    }
    return execute_dispute(local, probe.ledger, seat_id, window, slot, authority,
                           signed_slot);
  };
  constexpr std::uint8_t kOtherSlot = 1;
  pv::require(refuse(kActiveSeat, kProbeWindow, 0, kForeignAuthorityKey,
                     nullptr, false) == "UNAUTHORIZED_DISPUTE",
              "a key the chain does not recognise");
  expect_true(contract, "kind21.refuses.unauthorized_dispute");
  // A signature is over one slot and one reason, so presenting it for another
  // is simply absent from the table.
  pv::require(refuse(kActiveSeat, kProbeWindow, 0, kDisputeAuthorityKey,
                     &kOtherSlot, false) == "UNAUTHORIZED_DISPUTE",
              "a signature over another slot");
  expect_true(contract, "kind21.refuses.a_signature_over_another_slot");
  pv::require(refuse(v8::kMaxSeatId + 1, kProbeWindow, 0, kDisputeAuthorityKey,
                     nullptr, false) == "CYCLE_RANGE",
              "a seat above the capacity");
  expect_true(contract, "kind21.refuses.cycle_range");
  pv::require(refuse(900, kProbeWindow, 0, kDisputeAuthorityKey, nullptr,
                     false) == "SEAT_NOT_PURCHASED",
              "a seat the chain has not sold");
  expect_true(contract, "kind21.refuses.seat_not_purchased");
  pv::require(refuse(kActiveSeat, kProbeWindow,
                     static_cast<std::uint8_t>(v8::kMaxSlotIndex + 1),
                     kDisputeAuthorityKey, nullptr, false) == "SLOT_RANGE",
              "a slot beyond the window");
  expect_true(contract, "kind21.refuses.slot_range");
  pv::require(refuse(kActiveSeat, kProbeWindow + 1, 0, kDisputeAuthorityKey,
                     nullptr, false) == "WINDOW_NOT_CLOSED",
              "a window the executing height is still inside");
  expect_true(contract, "kind21.refuses.window_not_closed");
  pv::require(refuse(kActiveSeat, kProbeWindow - 1, 0, kDisputeAuthorityKey,
                     nullptr, false) == "DISPUTE_WINDOW_CLOSED",
              "a window whose dispute window has passed");
  expect_true(contract, "kind21.refuses.dispute_window_closed");
  pv::require(refuse(kLateSeat, kProbeWindow, 0, kDisputeAuthorityKey, nullptr,
                     false) == "SEAT_NOT_IN_SCOPE",
              "a seat activated inside the disputed window");
  expect_true(contract, "kind21.refuses.seat_not_in_scope");

  // A replay and an uncredited slot both need a record already written, so both
  // run against the control's own state rather than a fresh one.
  Signatures replay_signatures;
  auto replayed = make_fixture(height);
  pv::require(execute_dispute(replay_signatures, replayed.ledger, kActiveSeat,
                              kProbeWindow, 0) == "SUCCESS",
              "the first dispute is accepted");
  pv::require(execute_dispute(replay_signatures, replayed.ledger, kActiveSeat,
                              kProbeWindow, 0) == "DISPUTE_REPLAY",
              "a slot already voided");
  expect_true(contract, "kind21.refuses.dispute_replay");

  Signatures uncredited_signatures;
  auto uncredited = make_fixture(height);
  auto lost = v8::full_seat_window();
  lost.credited &= ~1U;
  const auto value = v8::seat_window_value(lost);
  pv::require(value.has_value(), "the probe record encodes");
  uncredited.ledger.uptime[v8::seat_window_key(kProbeWindow, kActiveSeat)] = *value;
  pv::require(execute_dispute(uncredited_signatures, uncredited.ledger, kActiveSeat,
                              kProbeWindow, 0) == "DISPUTE_SLOT_NOT_CREDITED",
              "a slot the seat was never credited for");
  expect_true(contract, "kind21.refuses.dispute_slot_not_credited");

  pv::require(refuse(kActiveSeat, kProbeWindow,
                     static_cast<std::uint8_t>(v8::kDisputeCapSlotsPerSeat),
                     kDisputeAuthorityKey, nullptr, true) ==
                  "DISPUTE_CAP_EXCEEDED",
              "a seventh dispute against one seat");
  expect_true(contract, "kind21.refuses.dispute_cap_exceeded");
}

// Expiry: the accepted model's slot-close sweep, made incremental.
//
// **The expiry step is reached through `execute_block`**, which is the only way
// a chain reaches it, so this needs a ledger a block will accept. The seat is
// deliberately left *unactivated*: expiry does not read scope, so the sweep runs
// exactly as it would otherwise, while the issue step selects nobody and cannot
// add a challenge this fixture did not write.
v8::Ledger expiry_ledger() {
  auto opened = v8::open_ledger(trace_genesis());
  pv::require(opened.has_value(), "the expiry genesis opens a ledger");
  auto ledger = std::move(*opened);
  v8::HubIdentityRecord identity;
  identity.hub_public_key = kHolderKey;
  identity.seat_count = 1;
  ledger.registry.identities[kHolderIdentity] = identity;
  const auto escrow = v8::escrow_id(kHolderIdentity, 0);
  v8::EscrowRecord entry;
  entry.owner_hub_identity = kHolderIdentity;
  ledger.registry.escrows[escrow] = entry;
  ledger.registry.accounts[escrow] = protocol::v1::Account{};
  v8::SeatRecord seat;
  seat.hub_identity_hash = kHolderIdentity;
  ledger.seats[kActiveSeat] = seat;
  pv::require(v8::conservation_failures(ledger).empty(),
              "the expiry fixture must open conserved");
  return ledger;
}

// The containment theorem at its boundary, over the encoded state.
void check_containment(const pv::Values& contract) {
  const auto height = v8::kCycleBlocks * (kProbeWindow + 1) + 5;
  Signatures signatures;
  auto fixture = make_fixture(height);
  for (std::uint8_t slot = 0; slot < v8::kDisputeCapSlotsPerSeat; ++slot) {
    pv::require(execute_dispute(signatures, fixture.ledger, kActiveSeat,
                                kProbeWindow, slot) == "SUCCESS",
                "a maximal dispute is accepted");
  }
  const auto record =
      v8::seat_window_record(fixture.ledger, kProbeWindow, kActiveSeat);
  pv::require(record.has_value(), "the maximally disputed record decodes");
  agree(contract, "containment.maximal_dispute.uptime_seconds",
        v8::uptime_seconds(*record));
  agree(contract, "containment.activity_threshold_seconds",
        v8::kActivityThresholdSeconds);
  pv::require(v8::uptime_seconds(*record) >= v8::kActivityThresholdSeconds,
              "a perfect seat still meets its cycle after a maximal dispute");
  expect_true(contract, "containment.a_perfect_seat_still_meets_its_cycle");
  // The cap *is* the grace allowance: the threshold is exactly the seconds
  // left after the cap is exhausted, so one more voided slot would fail a
  // machine that was fully operational.
  pv::require(v8::uptime_seconds(*record) == v8::kActivityThresholdSeconds &&
                  (v8::kSlotsPerWindow - v8::kDisputeCapSlotsPerSeat) *
                          v8::kSlotSeconds ==
                      v8::kActivityThresholdSeconds,
              "the cap is the founder-directed grace allowance");
  expect_true(contract, "containment.the_cap_is_the_grace_allowance");
  pv::require(execute_dispute(signatures, fixture.ledger, kActiveSeat, kProbeWindow,
                              static_cast<std::uint8_t>(
                                  v8::kDisputeCapSlotsPerSeat)) ==
                  "DISPUTE_CAP_EXCEEDED",
              "the seventh dispute is refused");
  expect_true(contract, "containment.the_seventh_dispute_is_refused");

  // **The invariants name the rule, and that is checked rather than assumed.**
  // A seventh voided slot is refused by the transition above, so the state it
  // would produce is unreachable on-chain; written directly it must be refused
  // by the two invariants that exist for it, and each must say which one it is.
  // A cap widened to seven would leave a perfect seat at 61,200 seconds, which
  // is below the founder-directed threshold, so this is the containment theorem
  // failing in the one way the contract says it must not.
  auto over_cap = v8::full_seat_window();
  over_cap.disputed = (1U << (v8::kDisputeCapSlotsPerSeat + 1)) - 1U;
  const auto encoded = v8::seat_window_value(over_cap);
  pv::require(encoded.has_value(), "an over-cap record still encodes");
  pv::require(v8::uptime_seconds(over_cap) < v8::kActivityThresholdSeconds,
              "a seventh voided slot falls below the threshold");
  auto broken = expiry_ledger();
  broken.height = v8::kCycleBlocks * kProbeWindow;
  broken.uptime[v8::seat_window_key(kProbeWindow, kActiveSeat)] = *encoded;
  const auto failures = v8::conservation_failures(broken);
  const auto reports = [&](std::string_view rule) {
    return std::find(failures.begin(), failures.end(), rule) != failures.end();
  };
  pv::require(reports("a seat window record exceeds the dispute cap"),
              "the cap invariant reports by name");
  pv::require(reports("a maximal dispute failed a fully credited seat"),
              "the containment invariant reports by name");
}

// The two retention invariants, which no recorded scenario can reach because
// the steps that write these entries cannot produce the states they forbid.
//
// **A state no transition can reach is exactly what an invariant is for**, so
// each is checked by writing the forbidden state directly and requiring the
// invariant to name the rule it broke. Without this, an implementation could
// delete either check and every recorded vector would still pass.
void check_retention() {
  const auto names = [](const v8::Ledger& ledger, std::string_view rule) {
    const auto failures = v8::conservation_failures(ledger);
    return std::find(failures.begin(), failures.end(), rule) != failures.end();
  };

  // Invariant 2: the pipeline retains no challenge whose deadline has passed.
  // The expiry step deletes one at `challenge_height + kResponseDeadlineBlocks`,
  // so a chain still holding one at the height after that is a chain whose
  // expiry step did not run.
  auto stale = expiry_ledger();
  stale.height = kProbeChallengeHeight + v8::kResponseDeadlineBlocks + 1;
  issue(stale, kProbeChallengeHeight, kActiveSeat);
  pv::require(names(stale, "an open challenge outlived its response deadline"),
              "the deadline invariant reports by name");
  // And a challenge for a height the chain has not reached, which is the same
  // rule from the other side.
  auto ahead = expiry_ledger();
  ahead.height = kProbeChallengeHeight - 1;
  issue(ahead, kProbeChallengeHeight, kActiveSeat);
  pv::require(names(ahead, "an open challenge outlived its response deadline"),
              "the deadline invariant refuses a challenge from the future");
  // The positive control, at the last height the entry is still retained.
  // **That height is `c + kResponseDeadlineBlocks - 1` and not `c + 20`**,
  // because the invariant runs at the *end* of a block and the expiry step at
  // `c + 20` has already deleted the entry by then: the retained range is
  // `[h - 19, h]`, so the entry's last block is the one before its deadline's.
  auto live = expiry_ledger();
  live.height = kProbeChallengeHeight + v8::kResponseDeadlineBlocks - 1;
  issue(live, kProbeChallengeHeight, kActiveSeat);
  pv::require(v8::conservation_failures(live).empty(),
              "a challenge inside its deadline window is accepted");

  // Invariant 5: exactly two windows are retained at every height, which is
  // what the prologue's unconditional deletion is for. A record three windows
  // back is one the prologue failed to delete.
  const auto record = v8::seat_window_value(v8::full_seat_window());
  pv::require(record.has_value(), "the retention probe's record encodes");
  auto outlived = expiry_ledger();
  outlived.height = v8::kCycleBlocks * (kProbeWindow + 2);
  outlived.uptime[v8::seat_window_key(kProbeWindow, kActiveSeat)] = *record;
  pv::require(names(outlived, "a seat window record outlived its retention"),
              "the retention invariant reports by name");
  // A record for a window the chain has not reached fails the same rule.
  auto early = expiry_ledger();
  early.height = v8::kCycleBlocks * kProbeWindow;
  early.uptime[v8::seat_window_key(kProbeWindow + 1, kActiveSeat)] = *record;
  pv::require(names(early, "a seat window record outlived its retention"),
              "the retention invariant refuses a record from the future");
  // The positive control, at both ends of the retained pair.
  for (const auto window : {kProbeWindow, kProbeWindow + 1}) {
    auto retained = expiry_ledger();
    retained.height = v8::kCycleBlocks * (kProbeWindow + 1);
    retained.uptime[v8::seat_window_key(window, kActiveSeat)] = *record;
    pv::require(v8::conservation_failures(retained).empty(),
                "a record inside the retained pair is accepted");
  }

  // Invariants 1 and 3, over values the codec would refuse to produce. The
  // uptime map holds raw octets, so a value no encoder would write can be put
  // there directly — which is the only way to reach these two, and the reason
  // they are invariants rather than only decoder rules.
  auto bad_state = expiry_ledger();
  bad_state.height = kProbeChallengeHeight;
  bad_state.uptime[v8::open_challenge_key(kProbeChallengeHeight, kActiveSeat)] =
      v8::Bytes{2};
  pv::require(names(bad_state, "an open challenge state is neither zero nor one"),
              "the open challenge state invariant reports by name");

  auto bad_record = expiry_ledger();
  bad_record.height = v8::kCycleBlocks * kProbeWindow;
  // A pad bit set in `credited`, which `seat_window_value` refuses to encode.
  bad_record.uptime[v8::seat_window_key(kProbeWindow, kActiveSeat)] =
      v8::Bytes{0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00};
  pv::require(names(bad_record, "a seat window record does not decode"),
              "the record decoding invariant reports by name");

  // And the absent-record rule the schedule rests on, read from the accessor
  // every caller uses rather than from a derivation that defaults around it.
  auto empty = expiry_ledger();
  const auto absent = v8::seat_window_record(empty, kProbeWindow, kActiveSeat);
  pv::require(absent.has_value() && absent->credited == v8::kSlotBitmapMask &&
                  absent->disputed == 0,
              "an absent record reads as a fully credited seat");

  // **A quiet height is gated too**, which no recorded scenario can show
  // because the issue step and the expiry step only ever write conforming
  // state. It is checked by starting a run from a state that already breaks an
  // invariant: the run must refuse rather than carry it forward. Without this
  // the gate could be deleted and every recorded vector would still pass.
  Signatures signatures;
  auto poisoned = expiry_ledger();
  poisoned.height = v8::kCycleBlocks * kProbeWindow + 10;
  auto over_cap = v8::full_seat_window();
  over_cap.disputed = (1U << (v8::kDisputeCapSlotsPerSeat + 1)) - 1U;
  const auto encoded = v8::seat_window_value(over_cap);
  pv::require(encoded.has_value(), "the poisoned record encodes");
  poisoned.uptime[v8::seat_window_key(kProbeWindow, kActiveSeat)] = *encoded;
  pv::require(!v8::run_quiet_heights(poisoned, poisoned.height + 1,
                                     signatures.verifier())
                   .has_value(),
              "a quiet height refuses a state that breaks an uptime invariant");
  // The positive control on the same shape, so the refusal is about the record
  // rather than about the run.
  auto clean = expiry_ledger();
  clean.height = poisoned.height;
  pv::require(v8::run_quiet_heights(clean, clean.height + 1,
                                    signatures.verifier())
                  .has_value(),
              "a quiet height on a conforming state runs");
}

// Run the block at `challenge_height + kResponseDeadlineBlocks`, which is the
// height whose expiry step resolves that challenge.
void expire_at(v8::Ledger& ledger, const Signatures& signatures,
               std::uint64_t challenge_height) {
  ledger.height = challenge_height + v8::kResponseDeadlineBlocks - 1;
  const auto block = v8::execute_block(ledger, {}, signatures.verifier());
  pv::require(block.has_value(), "the expiry block executes");
}

void check_expiry(const pv::Values& contract) {
  Signatures signatures;
  auto ledger = expiry_ledger();
  // One challenge in each of three different slots, so an answered one and an
  // unanswered one cannot be confused for each other by sharing a slot.
  std::vector<std::uint64_t> heights;
  for (std::uint32_t slot = 0; slot < 3; ++slot) {
    heights.push_back(kProbeChallengeHeight + slot * v8::kSlotBlocks);
  }
  // **Each challenge is written just before its own expiry block**, not all
  // three up front: invariant 2 requires every retained challenge's height to be
  // inside the deadline window, so a chain holding a challenge for a height it
  // has not reached is one the block gate rejects — which is the invariant doing
  // its job rather than an obstacle.
  const auto answered = v8::open_challenge_value(v8::kChallengeAnswered);
  pv::require(answered.has_value(), "an answered challenge encodes");
  for (const auto height : heights) {
    issue(ledger, height, kActiveSeat);
    // The first is answered, the second and third are not.
    if (height == heights.front()) {
      ledger.uptime[v8::open_challenge_key(height, kActiveSeat)] = *answered;
    }
    expire_at(ledger, signatures, height);
  }

  pv::require(std::none_of(ledger.uptime.begin(), ledger.uptime.end(),
                           [](const auto& entry) {
                             return entry.first.front() ==
                                    static_cast<std::uint8_t>(v8::Entry::open_challenge);
                           }),
              "expiry deletes every resolved challenge");
  expect_true(contract, "expiry.deletes_every_resolved_challenge");
  const auto record = v8::seat_window_record(ledger, kProbeWindow, kActiveSeat);
  pv::require(record.has_value(), "the swept record decodes");
  agree(contract, "expiry.credited_after_two_unanswered", record->credited);
  agree(contract, "expiry.disputed_stays_empty", record->disputed);
  agree(contract, "expiry.uptime_seconds_after", v8::uptime_seconds(*record));
  pv::require((record->credited >> v8::slot_of(heights.front()) & 1U) == 1U,
              "an answered challenge costs no slot");
  expect_true(contract, "expiry.an_answered_challenge_costs_no_slot");
  agree(contract, "expiry.slots_lost",
        v8::kSlotsPerWindow - v8::credited_slots(*record));

  // A slot is lost once however many challenges in it went unanswered, because
  // the bit is already clear the second time.
  Signatures twice_signatures;
  auto twice = expiry_ledger();
  for (const auto height : {kProbeChallengeHeight, kProbeChallengeHeight + 5}) {
    issue(twice, height, kActiveSeat);
    expire_at(twice, twice_signatures, height);
  }
  const auto once = v8::seat_window_record(twice, kProbeWindow, kActiveSeat);
  pv::require(once.has_value(), "the twice-swept record decodes");
  agree(contract, "expiry.two_losses_in_one_slot_cost_one_slot",
        v8::credited_slots(*once));
}

// The schedule is derived from state, and it is complete.
void check_schedule(const pv::Values& contract) {
  auto fixture = make_fixture(0);
  // A seat that lost its first three slots, so the derivation has something to
  // read rather than only an absence to default.
  auto lost = v8::full_seat_window();
  lost.credited &= ~0b111U;
  const auto value = v8::seat_window_value(lost);
  pv::require(value.has_value(), "the probe record encodes");
  fixture.ledger.seats.erase(kUnactivatedSeat);
  fixture.ledger.uptime[v8::seat_window_key(kProbeWindow, kActiveSeat)] = *value;

  const auto measured = v8::derive_schedule(fixture.ledger, kProbeWindow);
  agree(contract, "schedule.in_scope_count", measured.size());
  pv::require(std::none_of(measured.begin(), measured.end(),
                           [](const auto& seat) { return seat.seat_id == kLateSeat; }),
              "a seat activated inside the window is omitted");
  expect_true(contract, "schedule.omits_a_seat_activated_inside_the_window");
  pv::require(!measured.empty(), "the schedule names a seat");
  agree(contract, "schedule.seat_id", measured.front().seat_id);
  agree(contract, "schedule.uptime_seconds", measured.front().uptime_seconds);
  pv::require(measured.front().in_span, "the measured seat is in span");
  expect_true(contract, "schedule.in_span");

  // A seat with no record is present with a full credit rather than absent,
  // which is what makes record completeness structural.
  auto without = fixture.ledger;
  without.uptime.clear();
  const auto absent = v8::derive_schedule(without, kProbeWindow);
  pv::require(!absent.empty(), "the absent-record schedule names a seat");
  agree(contract, "schedule.absent_record_uptime_seconds",
        absent.front().uptime_seconds);
  pv::require(absent.size() == measured.size(),
              "an absent record is not an omission");
  expect_true(contract, "schedule.absent_record_is_not_an_omission");

  // A seat past its own 731 cycles is in scope and out of span: it is still
  // measured and it no longer generates permissions.
  auto beyond = without;
  beyond.seats.erase(kLateSeat);
  const auto late_window =
      v8::first_cycle_window(kActiveActivation) + v8::kIssuanceCyclesPerSeat;
  const auto past = v8::derive_schedule(beyond, late_window);
  agree(contract, "schedule.past_span.in_scope_count", past.size());
  pv::require(!past.empty() && !past.front().in_span, "the seat is out of span");
  expect_true(contract, "schedule.past_span.is_out_of_span");
  const auto inside = v8::derive_schedule(beyond, late_window - 1);
  pv::require(!inside.empty() && inside.front().in_span,
              "the last window of the span is in span");
  expect_true(contract, "schedule.last_window_of_the_span_is_in_span");
}

// The claim the whole carrier rests on: **a derived schedule settles exactly as
// a supplied one does**, checked against version seven's own encoding.
void check_settlement(const pv::Values& contract) {
  auto fixture = make_fixture(0);
  fixture.ledger.seats.erase(kUnactivatedSeat);
  auto lost = v8::full_seat_window();
  lost.credited &= ~0b111U;
  const auto value = v8::seat_window_value(lost);
  pv::require(value.has_value(), "the probe record encodes");
  fixture.ledger.uptime[v8::seat_window_key(kProbeWindow, kActiveSeat)] = *value;
  // A second in-scope seat with no record at all, so the settlement has one
  // seat that lost slots and one that lost none.
  v8::SeatRecord second;
  second.hub_identity_hash = kHolderIdentity;
  second.is_activated = true;
  second.activation_height = kActiveActivation;
  fixture.ledger.seats[kSecondSeat] = second;

  const auto measured = v8::derive_schedule(fixture.ledger, kProbeWindow);
  agree(contract, "settlement.measured_seats", measured.size());
  // What a version-seven caller would have supplied, stated here from the
  // specification's arithmetic rather than taken from the derivation under
  // test: comparing the derivation to itself would establish nothing.
  const std::vector<v8::SeatCycle> supplied{
      {kActiveSeat, (v8::kSlotsPerWindow - 3) * v8::kSlotSeconds, true},
      {kSecondSeat, v8::kSlotsPerWindow * v8::kSlotSeconds, true}};
  bool identical = measured.size() == supplied.size();
  for (std::size_t index = 0; identical && index < supplied.size(); ++index) {
    identical = measured[index].seat_id == supplied[index].seat_id &&
                measured[index].uptime_seconds == supplied[index].uptime_seconds &&
                measured[index].in_span == supplied[index].in_span;
  }
  pv::require(identical, "the derived schedule is the supplied one");
  expect_true(contract, "settlement.derived_schedule_equals_the_supplied_one");

  const auto assignment =
      v8::derive_assignment(fixture.ledger, kProbeWindow, supplied);
  pv::require(assignment.has_value(), "the assignment derives");
  agree(contract, "settlement.in_scope_count", assignment->in_scope_count);
  const auto record = v8::assignment_value(*assignment);
  pv::require(record.has_value(), "the assignment record encodes");
  agree(contract, "settlement.record_key",
        hex(v8::cycle_assignment_key(kProbeWindow)));
  agree(contract, "settlement.record_value", hex(*record));
  agree(contract, "settlement.record_fixed_bytes",
        record->size() - 2 * v8::bitmap_bytes(assignment->bitmap_bits));
  pv::require(assignment->winners == std::vector<std::uint32_t>{kSecondSeat},
              "the winner is the seat with no lost slot");
  expect_true(contract, "settlement.the_winner_is_the_seat_with_no_lost_slot");
  agree(contract, "settlement.both_seats_contribute",
        assignment->contributing_count == 2 ? "true" : "false");
  // The record is version seven's encoding under version seven's key: the
  // carrier changed where the measurement comes from and nothing about what is
  // written down.
  auto expected_key = v8::Bytes{static_cast<std::uint8_t>(v8::Entry::cycle_assignment)};
  for (int shift = 56; shift >= 0; shift -= 8) {
    expected_key.push_back(static_cast<std::uint8_t>(kProbeWindow >> shift));
  }
  pv::require(v8::cycle_assignment_key(kProbeWindow) == expected_key,
              "the record is version seven's encoding");
  expect_true(contract, "settlement.the_record_is_version_seven_s_encoding");
}

}  // namespace

void verify_transitions(const pv::Values& contract) {
  check_response(contract);
  check_dispute(contract);
  check_containment(contract);
  check_expiry(contract);
  check_schedule(contract);
  check_settlement(contract);
  check_retention();

  // **Every contract vector a ledger is needed for, and exactly those.** The
  // other 121 are `economy_v8_codec_tests`'s, so this claims the six groups
  // rather than the whole file — and a vector the file gains in one of them
  // fails here rather than passing unnoticed.
  static constexpr std::array<std::string_view, 6> kLedgerGroups{
      "kind20.", "kind21.", "schedule.", "settlement.", "expiry.", "containment.",
  };
  std::size_t claimed = 0;
  for (const auto& [key, value] : contract) {
    (void)value;
    const std::string& name = key;
    const auto matches = [&name](std::string_view prefix) {
      return name.rfind(prefix, 0) == 0;
    };
    if (!std::any_of(kLedgerGroups.begin(), kLedgerGroups.end(), matches)) continue;
    ++claimed;
    pv::require(consulted().contains(key),
                "contract vector " + key + " was never consulted");
  }
  pv::require(claimed == 62,
              "the ledger half of the contract file is 62 vectors, not " +
                  std::to_string(claimed));
}

}  // namespace economy_v8_execution
