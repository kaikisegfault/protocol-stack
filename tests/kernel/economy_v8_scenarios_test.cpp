// The four recorded version-eight scenarios, executed against a real state.
//
// Version eight changes no settlement and no carried transaction, so this trace
// does not re-record what `test-vectors/economy-transition-v7-execution.txt`
// already fixes about the recovery pool, the winner rule, or the mint walk. It
// records what version eight changes, which is **where the measurement comes
// from**.
//
// **A window is 28,800 heights and this trace runs every one of them.** Under
// version eight a block with no transactions still audits every in-scope seat,
// so there is no honest shorthand for the stretch between two interesting
// blocks. `advance_to` is used exactly once per chain and only before any
// activation, which is the one stretch where a block with no transactions
// really does change height and nothing else: no seat is in scope, so the issue
// step selects nobody.

#include "economy_v8_execution_fixture.hpp"

#include <algorithm>
#include <bit>
#include <concepts>

namespace economy_v8_execution {
namespace {

std::uint64_t nonce_of_ledger(const v8::Ledger& ledger, const Octets32& escrow) {
  const auto entry = ledger.registry.accounts.find(escrow);
  return entry == ledger.registry.accounts.end() ? 0 : entry->second.nonce;
}

std::uint64_t nonce_of(const v8::Ledger& ledger, const Octets32& escrow) {
  const auto entry = ledger.registry.accounts.find(escrow);
  return entry == ledger.registry.accounts.end() ? 0 : entry->second.nonce;
}

std::uint64_t balance_of(const v8::Ledger& ledger, const Octets32& escrow) {
  const auto entry = ledger.registry.accounts.find(escrow);
  return entry == ledger.registry.accounts.end() ? 0 : entry->second.balance;
}

// What one labelled step's transaction issued, found by its position among the
// block's admitted labels.
std::uint64_t issued_by(const v8::BlockOutcome& block, const std::string& label,
                        const Scenario& scenario) {
  const auto& labels = scenario.labels.back();
  for (std::size_t index = 0; index < labels.size(); ++index) {
    if (labels[index] != label) continue;
    pv::require(index < block.executed.size(),
                scenario.name + ": " + label + " has an executed row");
    return block.executed[index].outcome.issued_atomic;
  }
  pv::require(false, scenario.name + ": no step labelled " + label);
  return 0;
}

// A seat set in the shape the vectors record it: `[0]`, `[0, 1]`, `[]`.
std::string seat_list(std::span<const std::uint32_t> seats) {
  std::string out = "[";
  for (std::size_t index = 0; index < seats.size(); ++index) {
    if (index > 0) out += ", ";
    out += std::to_string(seats[index]);
  }
  return out + "]";
}

// How many kind-20 transactions succeeded across a run of audited heights.
//
// Counted from the executed rows rather than from the responder's own log,
// because the log records what was *offered* and this records what the chain
// accepted. A trace that offered a response the chain refused would show the two
// disagreeing, which is the only way a scenario can notice it.
std::uint64_t accepted_responses(const std::vector<v8::BlockOutcome>& blocks) {
  std::uint64_t count = 0;
  for (const auto& block : blocks) {
    for (const auto& entry : block.executed) {
      if (entry.kind == static_cast<std::uint8_t>(v8::Kind::challenge_response) &&
          entry.outcome.succeeded()) {
        ++count;
      }
    }
  }
  return count;
}

// Every fee a challenge response paid. The founder answer makes it zero.
std::uint64_t response_fees(const std::vector<v8::BlockOutcome>& blocks) {
  std::uint64_t total = 0;
  for (const auto& block : blocks) {
    for (const auto& entry : block.executed) {
      if (entry.kind == static_cast<std::uint8_t>(v8::Kind::challenge_response)) {
        total += entry.outcome.fee_charged;
      }
    }
  }
  return total;
}

// Every `(window, seat)` a seat window record exists for, and every
// `(height, seat)` an open challenge exists for.
std::set<std::pair<std::uint64_t, std::uint32_t>> uptime_keys(
    const v8::Ledger& ledger, v8::Entry kind) {
  std::set<std::pair<std::uint64_t, std::uint32_t>> keys;
  for (const auto& [key, value] : ledger.uptime) {
    (void)value;
    if (key.empty() || key.front() != static_cast<std::uint8_t>(kind)) continue;
    std::uint64_t first = 0;
    for (std::size_t index = 1; index < 9; ++index) {
      first = (first << 8U) | key[index];
    }
    std::uint32_t seat = 0;
    for (std::size_t index = 9; index < 13; ++index) {
      seat = (seat << 8U) | key[index];
    }
    keys.emplace(first, seat);
  }
  return keys;
}

// Two overloads with distinct names rather than one on `bool`, because an
// integral argument converts to `bool` and the wrong overload would record
// "true" where the vectors expect a count.
template <typename Number>
  requires std::integral<Number> && (!std::same_as<Number, bool>)
void note(Scenario& scenario, const std::string& key, Number value) {
  scenario.notes[key] = std::to_string(static_cast<std::uint64_t>(value));
}

void note_true(Scenario& scenario, const std::string& key, bool value) {
  scenario.notes[key] = value ? "true" : "false";
}

// Run every height to `target`, with both machines answering what they are
// issued. The two logs are the evidence a scenario states its claims from.
std::uint64_t quiet_run(Scenario& scenario, const Signatures& signatures,
                        std::uint64_t target, Responder& alice, Responder& bob) {
  auto both = [&alice, &bob](std::uint64_t height,
                             std::span<const std::uint32_t> issued) {
    auto inputs = alice(height, issued);
    for (auto& raw : bob(height, issued)) inputs.push_back(std::move(raw));
    return inputs;
  };
  v8::Responder respond = both;
  auto run_result = v8::run_quiet_heights(scenario.ledger, target,
                                          signatures.verifier(), respond);
  pv::require(run_result.has_value(), scenario.name + ": a quiet run was rejected");
  for (auto& block : run_result->recorded) {
    scenario.audit_blocks.push_back(std::move(block));
  }
  return run_result->heights;
}

// Run to the assignment height and return window one's winner set.
std::vector<std::uint32_t> finish_window(Scenario& scenario,
                                         const Signatures& signatures,
                                         Responder& alice, Responder& bob) {
  scenario.skipped_blocks +=
      quiet_run(scenario, signatures, kAssignmentHeight - 1, alice, bob);
  const auto block = run(scenario, signatures, {});
  pv::require(block.assignment.has_value(),
              scenario.name + ": the assignment block derives an assignment");
  return block.assignment->winners;
}

// What one branch of the deadline scenario reports.
struct Branch {
  std::uint64_t height = 0;
  std::string result;
  std::uint32_t credited_before = 0;
  std::uint32_t credited_after = 0;
  bool challenge_survives = false;
};

// Answer one challenge on a copy of the chain, and report what happened.
//
// **The copy is the point**: all three readings run against the identical state,
// so the only thing that differs between them is the height the response is
// offered at and the order the block runs its steps in.
Branch branch(Signatures& signatures, const v8::Ledger& source,
              std::uint64_t challenge_height, std::uint64_t quiet_until,
              std::uint64_t respond_at, bool expire_first) {
  auto copy = source;
  const auto quiet =
      v8::run_quiet_heights(copy, quiet_until, signatures.verifier());
  pv::require(quiet.has_value(), "deadline: a branch's quiet run was rejected");

  const auto window = v8::window_of_height(challenge_height);
  const auto before = v8::seat_window_record(copy, window, kAliceSeat);
  const auto raw = response_input(signatures, copy, kAliceSignerKey, kAliceSeat,
                                  challenge_height,
                                  nonce_of_ledger(copy, kAliceEscrow) + 1);
  v8::BlockOrder order;
  order.expire_before_transactions = expire_first;
  const std::vector<Bytes> inputs{raw};
  const auto block = v8::execute_block(copy, inputs, signatures.verifier(), order);
  pv::require(block.has_value(), "deadline: a branch's block was rejected");
  pv::require(block->height == respond_at, "deadline: a branch ran at its height");
  pv::require(block->executed.size() == 1, "deadline: the response is admitted");
  const auto after = v8::seat_window_record(copy, window, kAliceSeat);
  pv::require(before.has_value() && after.has_value(),
              "deadline: both records decode");

  Branch report;
  report.height = block->height;
  const auto name = v8::result_code_name(
      static_cast<std::uint8_t>(block->executed.front().outcome.result));
  pv::require(name.has_value(), "deadline: the result code has a name");
  report.result = std::string(*name);
  report.credited_before = v8::credited_slots(*before);
  report.credited_after = v8::credited_slots(*after);
  report.challenge_survives =
      copy.uptime.contains(v8::open_challenge_key(challenge_height, kAliceSeat));
  return report;
}

// Register both people, sell each a seat, and activate the seats that run.
//
// `spare_seat` sells Bob a second seat and never activates it: a purchased,
// unactivated seat has no activation height, so it is in no window's scope and
// the issue step must never audit it — and a chain with no such seat cannot tell
// whether the issue step checks activation at all, because an unactivated seat's
// default activation height of zero puts it inside every window.
Scenario seated_chain(Signatures& signatures, const std::string& name,
                      bool referred, bool spare_seat) {
  Scenario scenario;
  scenario.name = name;
  scenario.ledger = open_trace_ledger();
  auto& ledger = scenario.ledger;

  run(scenario, signatures,
      {{"alice_registers",
        register_input(signatures, ledger, kAliceIdentity, kAliceKey,
                       kAliceSignerKey)},
       {"bob_registers",
        register_input(signatures, ledger, kBobIdentity, kBobKey, kBobSignerKey)}});

  std::vector<Step> purchases{
      {"alice_purchases",
       purchase_input(signatures, ledger, kAliceIdentity, kAliceKey,
                      kAliceSignerKey, kAliceSeat, 1)},
      {"bob_purchases",
       purchase_input(signatures, ledger, kBobIdentity, kBobKey, kBobSignerKey,
                      kBobSeat, 1, referred ? &kAliceEscrow : nullptr)}};
  if (spare_seat) {
    purchases.push_back(
        {"bob_purchases_a_seat_he_never_runs",
         purchase_input(signatures, ledger, kBobIdentity, kBobKey, kBobSignerKey,
                        kSpareSeat, 2)});
  }
  run(scenario, signatures, purchases);

  advance_to(scenario, kActivationHeight - 1);
  run(scenario, signatures,
      {{"alice_activates",
        activate_input(signatures, ledger, kAliceIdentity, kAliceKey,
                       kAliceSignerKey, kAliceSeat, 2)},
       {"bob_activates",
        activate_input(signatures, ledger, kBobIdentity, kBobKey, kBobSignerKey,
                       kBobSeat, spare_seat ? 3 : 2)}});
  return scenario;
}

}  // namespace

// --- scenario one: a window the chain measured itself ----------------------
//
// Alice answers every audit, Bob answers none, and the chain pays Alice.
//
// **Bob's window record is the whole point**: it exists only because he lost
// challenges, it holds one cleared bit per slot he was audited in and missed,
// and nothing anywhere had to be told he was offline. Alice's record does not
// exist at all, which is the same statement in the other direction — a machine
// that answers everything writes nothing, so the storage the pipeline adds is
// proportional to failure rather than to population.
Scenario measured_scenario(Signatures& signatures) {
  auto scenario = seated_chain(signatures, "measured", true, true);
  auto& ledger = scenario.ledger;

  Responder alice(signatures, ledger, kAliceSeat, kAliceEscrow, kAliceSignerKey);
  Responder bob(signatures, ledger, kBobSeat, kBobEscrow, kBobSignerKey, true);
  auto both = [&alice, &bob](std::uint64_t height,
                             std::span<const std::uint32_t> issued) {
    auto inputs = alice(height, issued);
    for (auto& raw : bob(height, issued)) inputs.push_back(std::move(raw));
    return inputs;
  };
  v8::Responder respond = both;
  auto run_result = v8::run_quiet_heights(ledger, kAssignmentHeight - 1,
                                          signatures.verifier(), respond);
  pv::require(run_result.has_value(), "measured: the quiet run was rejected");
  scenario.skipped_blocks += run_result->heights;
  scenario.audit_blocks = run_result->recorded;

  note(scenario, "heights_executed", run_result->heights);
  note(scenario, "blocks_carrying_a_response",
       static_cast<std::uint64_t>(scenario.audit_blocks.size()));
  note(scenario, "alice_challenges_issued", alice.challenged.size());
  note(scenario, "alice_challenges_answered", alice.answered.size());
  note_true(scenario, "alice_answered_every_challenge",
            alice.challenged.size() == alice.answered.size());
  const auto accepted = accepted_responses(scenario.audit_blocks);
  note(scenario, "responses_accepted", accepted);
  // The log records what was *offered* and this records what the chain
  // accepted, so a response the chain refused would show the two disagreeing.
  note_true(scenario, "every_offered_response_was_accepted",
            accepted == alice.answered.size());
  note_true(scenario, "responses_charged_no_fee",
            response_fees(scenario.audit_blocks) == 0);

  const auto records = uptime_keys(ledger, v8::Entry::seat_window);
  const auto bob_record =
      v8::seat_window_record(ledger, kMeasuredWindow, kBobSeat);
  pv::require(bob_record.has_value(), "measured: bob's window record decodes");
  note_true(scenario, "a_machine_that_answers_everything_writes_no_record",
            records.count({kMeasuredWindow, kAliceSeat}) == 0);
  note(scenario, "bob_credited_slots", v8::credited_slots(*bob_record));
  note(scenario, "bob_lost_slots",
       v8::kSlotsPerWindow - v8::credited_slots(*bob_record));
  note(scenario, "bob_challenges_issued", bob.challenged.size());
  note(scenario, "bob_uptime_seconds", v8::uptime_seconds(*bob_record));
  note_true(scenario, "bob_failed_the_cycle",
            v8::uptime_seconds(*bob_record) < v8::kActivityThresholdSeconds);

  const auto challenges = uptime_keys(ledger, v8::Entry::open_challenge);
  const bool spare_untouched =
      std::none_of(records.begin(), records.end(),
                   [](const auto& key) { return key.second == kSpareSeat; }) &&
      std::none_of(challenges.begin(), challenges.end(),
                   [](const auto& key) { return key.second == kSpareSeat; });
  note_true(scenario, "an_unactivated_seat_is_never_audited", spare_untouched);
  const auto schedule = v8::derive_schedule(ledger, kMeasuredWindow);
  note_true(scenario, "an_unactivated_seat_is_not_in_the_derived_schedule",
            std::none_of(schedule.begin(), schedule.end(),
                         [](const auto& seat) {
                           return seat.seat_id == kSpareSeat;
                         }));

  // The window record read from the other side: every slot Bob lost is a slot he
  // was audited in and did not answer, derived from his own log rather than from
  // the bitmap the chain wrote.
  std::set<std::uint32_t> audited;
  for (const auto height : bob.challenged) {
    if (v8::window_of_height(height) == kMeasuredWindow) {
      audited.insert(v8::slot_of(height));
    }
  }
  std::set<std::uint32_t> cleared;
  for (std::uint32_t slot = 0; slot < v8::kSlotsPerWindow; ++slot) {
    if (((bob_record->credited >> slot) & 1U) == 0U) cleared.insert(slot);
  }
  note_true(scenario, "bob_lost_exactly_the_slots_he_was_audited_in",
       audited == cleared);

  // Selection excludes the final `kResponseDeadlineBlocks` heights of a slot, so
  // a challenge and its expiry are always inside one slot. Checked over every
  // challenge this chain actually issued rather than argued from the exclusion.
  bool same_slot = true;
  for (const auto* log : {&alice.challenged, &bob.challenged}) {
    for (const auto height : *log) {
      const auto later = height + v8::kResponseDeadlineBlocks;
      same_slot = same_slot && v8::window_of_height(height) ==
                                   v8::window_of_height(later) &&
                  v8::slot_of(height) == v8::slot_of(later);
    }
  }
  note_true(scenario, "every_challenge_expired_inside_its_own_slot", same_slot);

  // The prologue precedes the issue step, and at the accepted lag of two windows
  // the alternative commits to the same root: a challenge issued at this height
  // belongs to window `w + 2` and the prologue deletes window `w`'s records, so
  // the two steps provably cannot touch the same entry. Recorded as an equality
  // rather than asserted, because a version that shortened the lag would make it
  // false here first.
  auto alternative = ledger;
  v8::BlockOrder swapped_order;
  swapped_order.issue_before_prologue = true;
  const auto swapped = v8::execute_block(alternative, {}, signatures.verifier(),
                                         swapped_order);
  pv::require(swapped.has_value(), "measured: the swapped ordering executes");

  const auto assignment_block = run(scenario, signatures, {});
  note_true(scenario, "issuing_before_the_prologue_commits_the_same_root",
            swapped->resulting_state_root ==
                assignment_block.resulting_state_root);
  note_true(scenario, "issuing_before_the_prologue_assigns_the_same_window",
            swapped->assigned_window == assignment_block.assigned_window);
  pv::require(assignment_block.assigned_window.has_value(),
              "measured: the assignment block assigns a window");
  note(scenario, "assigned_window", *assignment_block.assigned_window);
  // Why the two orderings agree, stated as the arithmetic rather than as the
  // equality above: a challenge issued at this height belongs to the executing
  // window and the prologue deletes the window two before it, so the two steps
  // provably cannot touch the same entry.
  note_true(scenario, "the_two_steps_touch_windows_two_apart",
            v8::window_of_height(ledger.height) - *assignment_block.assigned_window ==
                v8::kAssignmentLagWindows);

  const auto assignment = ledger.assignments.find(kMeasuredWindow);
  pv::require(assignment != ledger.assignments.end(),
              "measured: window one's record is written");
  pv::require(assignment_block.assignment.has_value(),
              "measured: the derivation is carried out of the block");
  note(scenario, "reallocated_count",
       assignment_block.assignment->reallocated_count);
  scenario.notes["winner_set"] = seat_list(assignment_block.assignment->winners);
  scenario.notes["accrued_set"] = seat_list(assignment_block.assignment->accrued);

  const auto after = uptime_keys(ledger, v8::Entry::seat_window);
  note_true(scenario, "the_due_window_records_were_deleted_by_the_prologue",
            std::none_of(after.begin(), after.end(), [](const auto& key) {
              return key.first == kMeasuredWindow;
            }));
  const auto executing = v8::window_of_height(ledger.height);
  note_true(scenario,
            "retained_windows_are_inside_the_executing_window_and_the_one_before",
            std::all_of(after.begin(), after.end(),
                        [executing](const auto& key) {
                          return key.first <= executing &&
                                 key.first + 1 >= executing;
                        }));

  const auto alice_nonce = nonce_of(ledger, kAliceEscrow);
  run(scenario, signatures,
      {{"alice_mints_her_measured_cycle",
        node_mint_input(signatures, ledger, kAliceIdentity, kAliceKey,
                        kAliceSignerKey, kAliceSeat, kAliceEscrow,
                        alice_nonce + 1)},
       // A machine that failed its measured cycle mints successfully and
       // receives nothing. That is what a failed cycle looks like from the
       // operator's side: the walk runs, finds no accrued bit, issues zero, and
       // advances the mark — so the second attempt has nothing left to walk.
       {"bob_mints_and_receives_nothing",
        node_mint_input(signatures, ledger, kBobIdentity, kBobKey, kBobSignerKey,
                        kBobSeat, kBobEscrow, nonce_of(ledger, kBobEscrow) + 1)},
       {"bob_mints_again",
        node_mint_input(signatures, ledger, kBobIdentity, kBobKey, kBobSignerKey,
                        kBobSeat, kBobEscrow, nonce_of(ledger, kBobEscrow) + 2)},
       {"alice_mints_her_referral_leg",
        referral_mint_input(signatures, ledger, kAliceIdentity, kAliceKey,
                            kAliceSignerKey, kAliceEscrow, alice_nonce + 2)}});

  // What the two mints *issued*, taken from their own receipts rather than from
  // a balance: a balance is issuance less the fees the escrow has paid since
  // genesis, so reading one would make this figure depend on every unrelated
  // transaction the scenario happens to run.
  const auto& mints = scenario.blocks.back();
  note(scenario, "alice_minted_atomic",
       issued_by(mints, "alice_mints_her_measured_cycle", scenario));
  note(scenario, "alice_referral_atomic",
       issued_by(mints, "alice_mints_her_referral_leg", scenario));
  // Alice's own seat has no referrer, so its referral leg accrues to the
  // unreferred pool instead of to a person.
  note(scenario, "unreferred_pool_atomic", ledger.pool_accrued);
  note(scenario, "assigned_permissions", ledger.assigned_permissions);
  note_true(scenario, "the_recovery_pool_is_empty_after_the_mint",
            ledger.pool == v8::RecoveryPool{});
  return scenario;
}

// --- scenario two: a dispute that moves the winner set ---------------------
//
// Two perfect machines, six voided slots, and a winner set that moves.
//
// **The counterfactual is run from a copy of the very ledger the dispute block
// executed against**, so the two chains are identical up to that block by
// construction rather than by a fixture stated twice.
Scenario disputed_scenario(Signatures& signatures) {
  auto scenario = seated_chain(signatures, "disputed", false, false);
  auto& ledger = scenario.ledger;

  Responder alice(signatures, ledger, kAliceSeat, kAliceEscrow, kAliceSignerKey);
  Responder bob(signatures, ledger, kBobSeat, kBobEscrow, kBobSignerKey);
  scenario.skipped_blocks +=
      quiet_run(scenario, signatures, kDisputeHeight - 1, alice, bob);

  note(scenario, "alice_challenges_issued", alice.challenged.size());
  note(scenario, "bob_challenges_issued", bob.challenged.size());
  note_true(scenario, "both_machines_were_perfect_before_the_dispute",
            uptime_keys(ledger, v8::Entry::seat_window).empty());
  note_true(scenario, "responses_charged_no_fee",
            response_fees(scenario.audit_blocks) == 0);

  // The counterfactual forks here, before the dispute block, from the live
  // ledger rather than from a second construction of one.
  auto counterfactual = ledger;

  const auto nonce = nonce_of(ledger, kBobEscrow);
  std::vector<Step> steps;
  for (std::uint8_t slot = 0; slot < v8::kDisputeCapSlotsPerSeat; ++slot) {
    steps.push_back({"dispute_voids_alice_slot_" + std::to_string(slot),
                     dispute_input(signatures, ledger, kBobSignerKey, kAliceSeat,
                                   kMeasuredWindow, slot, nonce + slot + 1)});
  }
  const auto next = nonce + v8::kDisputeCapSlotsPerSeat + 1;
  // Four refusals, each offered at the same nonce because the first of them
  // fails and a failed transaction advances nothing.
  steps.push_back({"dispute_past_the_cap",
                   dispute_input(signatures, ledger, kBobSignerKey, kAliceSeat,
                                 kMeasuredWindow,
                                 static_cast<std::uint8_t>(
                                     v8::kDisputeCapSlotsPerSeat),
                                 next)});
  steps.push_back({"dispute_replayed_on_a_voided_slot",
                   dispute_input(signatures, ledger, kBobSignerKey, kAliceSeat,
                                 kMeasuredWindow, 0, next)});
  steps.push_back({"dispute_from_an_unrecognised_authority",
                   dispute_input(signatures, ledger, kBobSignerKey, kAliceSeat,
                                 kMeasuredWindow,
                                 static_cast<std::uint8_t>(
                                     v8::kDisputeCapSlotsPerSeat),
                                 next, kForeignAuthorityKey)});
  steps.push_back({"dispute_of_a_window_still_open",
                   dispute_input(signatures, ledger, kBobSignerKey, kAliceSeat,
                                 kMeasuredWindow + 1, 0, next)});
  const auto dispute_block = run(scenario, signatures, steps);
  note(scenario, "accepted_disputes",
       static_cast<std::uint64_t>(std::count_if(
           dispute_block.executed.begin(), dispute_block.executed.end(),
           [](const auto& entry) { return entry.outcome.succeeded(); })));

  const auto record =
      v8::seat_window_record(ledger, kMeasuredWindow, kAliceSeat);
  pv::require(record.has_value(), "disputed: alice's record decodes");
  note_true(scenario,
            "the_accepted_disputes_fill_the_founder_directed_grace_allowance",
            std::popcount(record->disputed) == v8::kDisputeCapSlotsPerSeat);
  // A dispute sets a bit in `disputed` and never clears one in `credited`, so
  // the record keeps what the seat's own evidence said.
  note_true(scenario, "a_dispute_does_not_clear_a_credited_bit",
            record->credited == v8::kSlotBitmapMask);
  note(scenario, "alice_final_slots", v8::credited_slots(*record));
  note(scenario, "alice_uptime_seconds", v8::uptime_seconds(*record));
  note_true(scenario,
            "a_maximal_dispute_leaves_a_perfect_seat_at_the_threshold",
            v8::uptime_seconds(*record) == v8::kActivityThresholdSeconds);
  note_true(scenario, "alice_still_meets_her_cycle",
            v8::uptime_seconds(*record) >= v8::kActivityThresholdSeconds);

  const auto with_dispute = finish_window(scenario, signatures, alice, bob);
  scenario.notes["winners_with_the_dispute"] = seat_list(with_dispute);

  // The same chain from the fork, with no dispute filed. Each branch gets
  // responders bound to its own ledger, which is what `fork` exists for: the
  // branch that filed six disputes from Bob's escrow has a different nonce
  // sequence from the branch that filed none.
  Scenario quiet;
  quiet.name = "counterfactual";
  quiet.ledger = std::move(counterfactual);
  auto forked_alice = alice.fork(quiet.ledger);
  auto forked_bob = bob.fork(quiet.ledger);
  const auto without_dispute =
      finish_window(quiet, signatures, forked_alice, forked_bob);
  scenario.notes["winners_without_the_dispute"] = seat_list(without_dispute);
  note_true(scenario, "the_dispute_moved_the_winner_set",
            with_dispute != without_dispute);
  // A maximal dispute costs a seat its place in the winner set and nothing
  // else: it still meets its cycle, so it still accrues.
  note_true(scenario, "the_disputed_seat_lost_only_its_place_in_the_winner_set",
            std::find(without_dispute.begin(), without_dispute.end(), kAliceSeat) !=
                    without_dispute.end() &&
                std::find(with_dispute.begin(), with_dispute.end(), kAliceSeat) ==
                    with_dispute.end() &&
                v8::uptime_seconds(*record) >= v8::kActivityThresholdSeconds);
  return scenario;
}

// --- scenario three: the deadline, from both sides of it -------------------
//
// The one execution ordering a chain can observe, run three ways on identical
// copies of one chain.
//
// The expiry step follows the transactions, so a response arriving in block
// `c + kResponseDeadlineBlocks` is the last admissible one. This scenario
// **waits for a real challenge** — selection is not knowable in advance, which
// is the point of it — copies the chain at that height, and runs the same
// response under three conditions:
//
//   * at `c + 20` under the accepted order: accepted;
//   * at `c + 21`: `RESPONSE_TOO_LATE`, with the entry already gone, which is
//     why condition 7 precedes condition 8;
//   * at `c + 20` with the expiry step moved ahead of the transactions:
//     `CHALLENGE_NOT_ISSUED`, **and the seat loses the slot it had just
//     proved**.
//
// The third is what "expiring first would shorten the deadline to nineteen
// blocks without saying so" costs, stated as a result code and a cleared bit
// rather than as a sentence.
Scenario deadline_scenario(Signatures& signatures) {
  auto scenario = seated_chain(signatures, "deadline", false, false);
  auto& ledger = scenario.ledger;

  // A machine that logs its audits and answers none, run one height at a time
  // until the chain audits it. Nothing here can predict the height.
  Responder watcher(signatures, ledger, kAliceSeat, kAliceEscrow, kAliceSignerKey,
                    true);
  while (watcher.challenged.empty()) {
    v8::Responder respond = [&watcher](std::uint64_t height,
                                       std::span<const std::uint32_t> issued) {
      return watcher(height, issued);
    };
    const auto step = v8::run_quiet_heights(ledger, ledger.height + 1,
                                            signatures.verifier(), respond);
    pv::require(step.has_value(), "deadline: the wait was rejected");
    // **Counted apart from `skipped_blocks` on purpose.** That figure is what
    // `heights_run_between_recorded_blocks` records, and for this scenario the
    // accepted file records only the setup's shorthand; the wait for a real
    // challenge is its own quantity and is checked against the challenge height
    // below rather than folded into a figure that would then mean two things.
    scenario.quiet_heights += step->heights;
    for (auto& block : step->recorded) scenario.audit_blocks.push_back(std::move(block));
  }
  const auto challenge_height = watcher.challenged.front();
  // The wait is exactly the heights run since the seats were activated, which
  // is what makes the counter above a derivation rather than a tally.
  pv::require(scenario.quiet_heights == challenge_height - kActivationHeight,
              "deadline: the wait is the heights since activation");
  note(scenario, "challenge_height", challenge_height);
  note(scenario, "challenge_slot", v8::slot_of(challenge_height));
  note_true(scenario, "the_challenge_was_issued_at_a_challengeable_height",
            v8::is_challengeable_height(challenge_height));

  // Offered in the very block that issued it. Condition 6 precedes condition 8,
  // so the report is that the challenge is not open rather than that it was
  // never issued — which it was, in this same block, one step earlier.
  const auto same_block =
      run(scenario, signatures,
          {{"response_in_the_issuing_block",
            response_input(signatures, ledger, kAliceSignerKey, kAliceSeat,
                           ledger.height + 1,
                           nonce_of(ledger, kAliceEscrow) + 1)}});
  pv::require(same_block.executed.size() == 1,
              "deadline: the same-block response is admitted");
  note_true(scenario, "a_response_in_the_issuing_block_is_not_open",
            same_block.executed.front().outcome.result ==
                v8::Result::challenge_not_open);

  const auto deadline = challenge_height + v8::kResponseDeadlineBlocks;
  const auto on_time =
      branch(signatures, ledger, challenge_height, deadline - 1, deadline, false);
  note(scenario, "response_height_at_the_deadline", on_time.height);
  scenario.notes["response_at_the_deadline_result"] = on_time.result;
  note_true(scenario, "response_at_the_deadline_is_accepted",
            on_time.result == "SUCCESS");
  note_true(scenario, "the_seat_keeps_every_slot_when_it_answers_in_time",
            on_time.credited_after == v8::kSlotsPerWindow);

  const auto late =
      branch(signatures, ledger, challenge_height, deadline, deadline + 1, false);
  note(scenario, "response_height_one_past_the_deadline", late.height);
  scenario.notes["response_one_height_late_result"] = late.result;
  note_true(scenario, "response_one_height_late_is_refused",
            late.result == "RESPONSE_TOO_LATE");
  note_true(scenario, "the_slot_was_already_lost_one_height_past_the_deadline",
            late.credited_before == v8::kSlotsPerWindow - 1);
  // The entry is gone by then, which is exactly why condition 7 precedes
  // condition 8: checking issuance first would report that a challenge which
  // *was* issued never was.
  note_true(scenario, "the_late_response_finds_no_open_challenge",
            !late.challenge_survives);

  const auto rejected =
      branch(signatures, ledger, challenge_height, deadline - 1, deadline, true);
  note_true(scenario, "expiring_before_the_transactions_refuses_the_same_response",
            rejected.result == "CHALLENGE_NOT_ISSUED");
  note_true(scenario, "expiring_before_the_transactions_costs_the_seat_a_slot",
            rejected.credited_after == v8::kSlotsPerWindow - 1);
  note_true(scenario, "the_accepted_order_costs_the_same_seat_nothing",
            on_time.credited_after == v8::kSlotsPerWindow &&
                rejected.credited_after < on_time.credited_after);
  return scenario;
}

// --- scenario four: the kinds version eight does not change ----------------
//
// Every transaction version eight leaves alone, executed under version eight.
//
// **The bytes are version six's and the commitments are not.** A registration
// under version eight is byte-for-byte a registration under version six, and it
// lands in a version-eight state and produces a version-eight receipt. Version
// seven's own execution vectors record neither, because they record
// version-seven roots and version-seven receipts, and version eight re-versions
// both.
Scenario carried_scenario(Signatures& signatures) {
  Scenario scenario;
  scenario.name = "carried";
  scenario.ledger = open_trace_ledger();
  auto& ledger = scenario.ledger;

  run(scenario, signatures,
      {{"alice_registers",
        register_input(signatures, ledger, kAliceIdentity, kAliceKey,
                       kAliceSignerKey, kValidUntil)},
       {"bob_registers",
        register_input(signatures, ledger, kBobIdentity, kBobKey, kBobSignerKey,
                       kValidUntil)}});

  // Kinds 1, 19, and 6. The default posture requires a confirmation at every
  // amount, so the unconfirmed transfer is refused and the confirmed one is not;
  // a refusal advances no nonce, which is why the confirmed transfer reuses 1.
  v8::Body direct;
  direct.channel_id = 5;
  direct.beneficiary_escrow_id = kAliceEscrow;
  direct.amount_atomic = 1;
  run(scenario, signatures,
      {{"alice_transfers_unconfirmed",
        transfer_input(signatures, ledger, kAliceSignerKey, 1, kBobEscrow,
                       kTransferAmount)},
       {"alice_transfers_confirmed",
        confirmed_transfer_input(signatures, ledger, 1, kBobEscrow,
                                 kTransferAmount, kAliceIdentity, kAliceKey,
                                 kAliceSignerKey, kAliceEscrow)},
       {"alice_transfers_to_an_unregistered_recipient",
        confirmed_transfer_input(signatures, ledger, 2, kAcceptedRecipient,
                                 kTransferAmount, kAliceIdentity, kAliceKey,
                                 kAliceSignerKey, kAliceEscrow)},
       {"alice_attempts_a_direct_issue",
        build(signatures, ledger, static_cast<std::uint8_t>(v8::Kind::direct_issue),
              kAliceSignerKey, 2, direct)}});

  // Kinds 13, 14, 15, and 16 — the four an identity performs with no signer at
  // all, which is the recovery architecture ADR 0040 exists for.
  v8::Body create;
  create.hub_identity_hash = kAliceIdentity;
  create.fee_escrow_id = kAliceEscrow;
  v8::Body remove;
  remove.hub_identity_hash = kAliceIdentity;
  remove.fee_escrow_id = kAliceEscrow;
  remove.target_escrow_id = kAliceSecondEscrow;
  v8::Body add_signer;
  add_signer.hub_identity_hash = kAliceIdentity;
  add_signer.escrow_id = kAliceEscrow;
  add_signer.signer_public_key = kFreshSignerKey;
  v8::Body revoke_signer;
  revoke_signer.hub_identity_hash = kAliceIdentity;
  revoke_signer.escrow_id = kAliceEscrow;
  revoke_signer.signer_id = v8::signer_id(kFreshSignerKey);
  run(scenario, signatures,
      {{"alice_creates_a_second_escrow",
        build(signatures, ledger,
              static_cast<std::uint8_t>(v8::Kind::escrow_create), kAliceKey, 2,
              create)},
       {"alice_deletes_the_second_escrow",
        build(signatures, ledger,
              static_cast<std::uint8_t>(v8::Kind::escrow_delete), kAliceKey, 3,
              remove)},
       {"alice_assigns_a_fresh_signer",
        build(signatures, ledger, static_cast<std::uint8_t>(v8::Kind::signer_add),
              kAliceKey, 4, add_signer)},
       {"alice_revokes_the_fresh_signer",
        build(signatures, ledger,
              static_cast<std::uint8_t>(v8::Kind::signer_revoke), kAliceKey, 5,
              revoke_signer)}});

  // Kind 17, in both directions. The opening posture is the strictest one the
  // contract admits, so the first change can only be a relaxation — and a
  // relaxation is exactly what the HUB signature is required for.
  v8::Posture relaxed;
  relaxed.requires_confirmation = true;
  relaxed.min_amount_atomic = kPostureMinimum;
  v8::Posture tightened;
  tightened.requires_confirmation = true;
  const auto change = [&](std::uint64_t nonce, const v8::Posture& posture,
                          bool signed_) {
    return posture_input(signatures, ledger, nonce, posture, signed_,
                         kAliceIdentity, kAliceKey, kAliceSignerKey, kAliceEscrow);
  };
  run(scenario, signatures,
      {{"alice_relaxes_without_a_signature", change(6, relaxed, false)},
       {"alice_relaxes_her_posture", change(6, relaxed, true)},
       {"alice_tightens_her_posture", change(7, tightened, false)},
       {"alice_repeats_the_posture_she_holds", change(8, tightened, false)}});

  // Kind 18, forty windows after enrolment: thirty are collectable and the ten
  // older ones are forfeited. **No seat is activated on this chain**, so the
  // shorthand is exact here for the same reason it is in the other scenarios'
  // setup: the issue step has nobody in scope to select.
  advance_to(scenario, kCollectionHeight - 1);
  run(scenario, signatures,
      {{"alice_collects_thirty_windows",
        verified_user_mint_input(signatures, ledger, kAliceIdentity, 8,
                                 kAliceEscrow, kAliceKey, kAliceSignerKey)},
       {"alice_collects_again_immediately",
        verified_user_mint_input(signatures, ledger, kAliceIdentity, 9,
                                 kAliceEscrow, kAliceKey, kAliceSignerKey)}});

  // A chain that sells no seat writes no uptime state at all, which is the
  // carrier's cost stated from the other side: it is proportional to seats
  // measured, and this chain measures none. Checked rather than recorded,
  // because the accepted file states it through the roots.
  pv::require(ledger.uptime.empty(),
              "carried: a chain with no seat writes no uptime state");
  pv::require(!ledger.registry.escrows.contains(kAliceSecondEscrow) &&
                  !ledger.registry.signers.contains(v8::signer_id(kFreshSignerKey)),
              "carried: a deleted escrow and a revoked signer leave no entry");
  return scenario;
}

}  // namespace economy_v8_execution
