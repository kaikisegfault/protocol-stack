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
#include <concepts>

namespace economy_v8_execution {
namespace {

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

}  // namespace economy_v8_execution
