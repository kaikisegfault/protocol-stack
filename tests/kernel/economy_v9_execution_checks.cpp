// What the two recorded chains did, compared against the recorded vectors.
//
// **The orderings are the part that needs a scenario rather than an invariant.**
// One of the two ADR 0078 distinguishes is observable and one is not, and
// neither claim can be checked against a single accepted state: what separates
// the accepted reading from the rejected one is a run. So each is executed twice
// from the same pre-block state, on identical inputs, and the two resulting
// roots are compared — which is also why a vector records the *equality* for the
// unobservable pair rather than a difference it does not have.

#include "economy_v9_execution_fixture.hpp"

#include <algorithm>
#include <array>
#include <string>
#include <string_view>

namespace economy_v9_execution {
namespace {

std::string join(std::span<const std::uint32_t> values) {
  std::string out;
  for (const auto value : values) {
    if (!out.empty()) out.push_back(',');
    out += std::to_string(value);
  }
  return out;
}

// Every month this chain closed, with the block that closed it.
struct ClosedRecord {
  std::uint64_t height = 0;
  std::uint32_t due_month = 0;
  v9::Settlement settlement;
  std::vector<std::uint32_t> skipped;
};

std::vector<ClosedRecord> settlements_of(const Scenario& scenario) {
  std::vector<ClosedRecord> closed;
  const auto collect = [&closed](const std::vector<v9::BlockOutcome>& blocks) {
    for (const auto& block : blocks) {
      if (!block.settled) continue;
      pv::require(block.due_month.has_value(),
                  "a settling block read the assigned window's month");
      closed.push_back({block.height, *block.due_month, *block.settled,
                        block.skipped_months});
    }
  };
  collect(scenario.blocks);
  collect(scenario.audit_blocks);
  std::sort(closed.begin(), closed.end(),
            [](const ClosedRecord& left, const ClosedRecord& right) {
              return left.height < right.height;
            });
  return closed;
}

// The pool's three quantities and the two identities over them, read off the
// state the run left rather than accumulated alongside it.
void check_pool(const pv::Values& values, const std::string& prefix,
                const Scenario& scenario) {
  const auto& ledger = scenario.ledger;
  agree(values, prefix + ".pool_accrued", ledger.pool_accrued);
  agree(values, prefix + ".pool_payable", ledger.pool_payable);
  agree(values, prefix + ".pool_minted", ledger.pool_minted);

  std::uint64_t assigned = 0;
  std::uint64_t minted = 0;
  for (const auto& [seat_id, claim] : ledger.claims) {
    (void)seat_id;
    assigned += claim.accrued_atomic;
    minted += claim.minted_atomic;
  }
  agree(values, prefix + ".claims_assigned", assigned);
  agree(values, prefix + ".claims_minted", minted);
  pv::require(ledger.pool_accrued == ledger.pool_payable + assigned,
              "every unit received is undistributed or owed to a named winner");
  expect_true(values, prefix + ".accrued_equals_payable_plus_assigned");
  pv::require(ledger.pool_minted == minted,
              "the pool's minted is the claims' minted total");
  expect_true(values, prefix + ".minted_equals_the_claims_minted");
  agree(values, prefix + ".conservation_failures",
        static_cast<std::uint64_t>(v9::conservation_failures(ledger).size()));

  // The pool's accrued total against the legs the assignments actually wrote,
  // which is a second source for it: the run's own assignment records rather
  // than the field the settlement reads.
  std::uint64_t legs = 0;
  std::uint64_t windows = 0;
  const auto sum = [&legs, &windows](const std::vector<v9::BlockOutcome>& blocks) {
    for (const auto& block : blocks) {
      if (!block.assignment) continue;
      if (block.assignment->unreferred_accrual == 0) continue;
      legs += block.assignment->unreferred_accrual;
      windows += 1;
    }
  };
  sum(scenario.blocks);
  sum(scenario.audit_blocks);
  agree(values, prefix + ".pool_accrued_is_the_unreferred_legs", legs);
  agree(values, prefix + ".windows_that_accrued", windows);
  pv::require(legs == ledger.pool_accrued,
              "the pool holds exactly what the assignments accrued to it");
}

void check_settlements(const pv::Values& values, const std::string& prefix,
                       const Scenario& scenario) {
  const auto closed = settlements_of(scenario);
  agree(values, prefix + ".settlements", static_cast<std::uint64_t>(closed.size()));
  for (const auto& record : closed) {
    const auto month = prefix + ".month_" + std::to_string(record.settlement.month);
    agree(values, month + ".settled_at_height", record.height);
    agree(values, month + ".month_of_the_assigned_window", record.due_month);
    agree(values, month + ".candidate_count", record.settlement.candidate_count);
    agree(values, month + ".best_figure", record.settlement.best_figure);
    agree(values, month + ".winners", join(record.settlement.winners));
    agree(values, month + ".payable_before", record.settlement.payable_before);
    agree(values, month + ".share", record.settlement.share);
    agree(values, month + ".remainder", record.settlement.remainder);
    agree(values, month + ".assigned", record.settlement.assigned);
    agree(values, month + ".skipped_months", join(record.skipped));
  }
}

// **A pointer rather than a reference, and the label is a view rather than a
// string.** GCC's `-Wdangling-reference` cannot tell that a reference returned
// from a call carrying a temporary argument does not come from that temporary,
// and it is right to warn: the version-eight fixture records the same shape at
// every one of its call sites. Returning a pointer removes the question, and
// taking a view removes the temporary that raised it.
const v9::BlockOutcome* block_labelled(const Scenario& scenario,
                                       std::string_view label,
                                       std::size_t& index) {
  for (std::size_t block = 0; block < scenario.labels.size(); ++block) {
    for (std::size_t step = 0; step < scenario.labels[block].size(); ++step) {
      if (scenario.labels[block][step] == label) {
        index = step;
        return &scenario.blocks[block];
      }
    }
  }
  throw std::runtime_error("no recorded block carries the step " +
                           std::string(label));
}

void check_mint(const pv::Values& values, const Scenario& scenario) {
  static constexpr std::array<std::string_view, 4> kLabels{
      "an_unconfirmed_mint_is_refused", "winner_mints_the_pool",
      "a_second_mint_collects_nothing",
      "a_stranger_cannot_mint_another_seats_award"};
  const v9::ExecutedTransaction* success = nullptr;
  for (const auto label : kLabels) {
    std::size_t index = 0;
    const auto* block = block_labelled(scenario, label, index);
    pv::require(index < block->executed.size(), "the step was executed");
    const auto& executed = block->executed[index];
    const auto name = v9::result_code_name(static_cast<std::uint8_t>(executed.outcome.result));
    pv::require(name.has_value(), "every result has a name");
    agree(values, "mint." + std::string(label), std::string(*name));
    if (executed.outcome.succeeded()) success = &executed;
    // **The refusal is what establishes kind 22 is a confirmable mint.** A mint
    // presenting 64 zero octets against a destination whose posture requires a
    // confirmation is refused by name, which is a property of the transition
    // rather than of a table the codec could declare.
    if (label == "an_unconfirmed_mint_is_refused") {
      pv::require(executed.outcome.result == v9::Result::biometric_required,
                  "an unconfirmed kind-22 mint is refused for the confirmation");
    }
  }
  pv::require(success != nullptr, "one mint succeeded");

  const auto encoded = v9::encode_receipt(success->receipt);
  pv::require(encoded.has_value(), "the receipt must encode");
  agree(values, "mint.receipt", hex(*encoded));
  agree(values, "mint.receipt_version", v9::kReceiptVersion);
  agree(values, "mint.issued_atomic", success->outcome.issued_atomic);
  agree(values, "mint.fee_charged", success->outcome.fee_charged);

  const auto winner = static_cast<std::uint32_t>(expect_number(values, "mint.winner_seat"));
  const auto claim = scenario.ledger.claims.find(winner);
  pv::require(claim != scenario.ledger.claims.end(),
              "the claim survives being emptied");
  pv::require(claim->second.accrued_atomic == claim->second.minted_atomic &&
                  claim->second.accrued_atomic != 0,
              "the claim is emptied and kept, which is the audit trail of what "
              "a machine earned and what it took");
  expect_true(values, "mint.the_claim_is_emptied_and_kept");

  // The units leave the referral channel's outstanding for its issued, which is
  // what makes version six's channel identity hold across the settlement.
  pv::require(scenario.ledger.channel_issued[v9::kReferralChannel] ==
                  success->outcome.issued_atomic,
              "the referral channel issued exactly what the mint took");
  expect_true(values, "mint.the_referral_channel_issued_it");
}

void check_calendar(const pv::Values& values, const Scenario& scenario) {
  // Every window this chain opened, and the month it opened in. The month is
  // read out of the recorded block rather than recomputed here, and the stamp
  // is the one that block carried.
  std::uint64_t opened = 0;
  for (const auto& block : scenario.audit_blocks) {
    if (!block.opened_window || *block.opened_window == 0) continue;
    opened += 1;
    const auto window = "calendar.window_" + std::to_string(*block.opened_window);
    const auto month = v9::month_index(block.timestamp);
    pv::require(month.has_value(), "an accepted stamp has a month");
    agree(values, window + ".month", *month);
    agree(values, window + ".opening_timestamp", block.timestamp);
    pv::require(block.timestamp == timestamp_of_height(
                                       v9::window_opening_height(*block.opened_window)),
                "a window's stamp is its opening height's");
  }
  agree(values, "calendar.windows_opened", opened);

  // Measured over the run rather than asserted: two entries are live at the end,
  // the open window's and its predecessor's.
  agree(values, "calendar.live_window_months",
        static_cast<std::uint64_t>(scenario.ledger.window_months.size()));
  const auto open = v9::window_of_height(scenario.ledger.height);
  pv::require(scenario.ledger.window_months.contains(open) &&
                  (open == 0 || scenario.ledger.window_months.contains(open - 1)),
              "the live entries are the open window's and its predecessor's");
  expect_true(values,
              "calendar.live_window_months_are_the_open_window_and_its_predecessor");
  pv::require(scenario.ledger.window_months.size() == v9::kLiveWindowMonths,
              "the measured count is the declared one");
}

void check_shorthand(const pv::Values& values, const Scenario& scenario) {
  agree(values, "shorthand.timestamp", scenario.timestamp_after_the_shorthand);
  agree(values, "shorthand.height", kActivationHeight - 1);
  agree(values, "shorthand.skipped_blocks", scenario.skipped_blocks);
  agree(values, "shorthand.root", hex(scenario.root_after_the_shorthand));
  // The block that follows it commits to that root as its predecessor, which is
  // the only place the shorthand's stamp is observable: the next block sets its
  // own.
  const auto& next = scenario.blocks.at(2);
  pv::require(next.previous_state_root == scenario.root_after_the_shorthand,
              "the first block after the shorthand carries that root");
  expect_true(values, "shorthand.the_first_block_after_it_carries_that_root");
}

void check_audit(const pv::Values& values, const Scenario& scenario) {
  agree(values, "audit.alice_challenged", scenario.alice_challenged);
  agree(values, "audit.alice_answered", scenario.alice_answered);
  pv::require(scenario.alice_challenged == scenario.alice_answered &&
                  scenario.alice_challenged > 0,
              "Alice answered every challenge she was issued");
  expect_true(values, "audit.alice_answered_every_challenge");
  agree(values, "audit.bob_challenged", scenario.bob_challenged);
  agree(values, "audit.bob_answered", scenario.bob_answered);
  pv::require(scenario.bob_answered == 0 && scenario.bob_challenged > 0,
              "Bob answered none of his");
  expect_true(values, "audit.bob_answered_none");
  agree(values, "audit.quiet_heights", scenario.quiet_heights);
}

void check_block(const pv::Values& values, const Scenario& scenario) {
  const auto& settlement = scenario.audit_blocks.back();
  agree(values, "block.header", hex(settlement.header));
  agree(values, "block.header_bytes",
        static_cast<std::uint64_t>(settlement.header.size()));
  agree(values, "block.block_id", hex(settlement.block_id));
  agree(values, "block.timestamp", settlement.timestamp);
  agree(values, "block.height", settlement.height);
  agree(values, "block.transaction_root", hex(settlement.transaction_root));
  pv::require(settlement.header.size() == v9::kBlockHeaderBytes,
              "the header is version nine's width");
}

void check_genesis(const pv::Values& values) {
  const auto genesis = trace_genesis();
  const auto encoded = v9::encode_genesis(genesis);
  pv::require(encoded.has_value(), "the trace genesis encodes");
  agree(values, "genesis.bytes", hex(*encoded));
  const auto identity = v9::chain_id(genesis);
  pv::require(identity.has_value(), "the trace genesis has an identity");
  agree(values, "genesis.chain_id", hex(*identity));
  agree(values, "genesis.timestamp", kGenesisMillis);
  const auto month = v9::month_index(kGenesisMillis);
  pv::require(month.has_value(), "the genesis stamp has a month");
  agree(values, "genesis.month", *month);
  agree(values, "genesis.millis_per_block", kMillisPerBlock);
}

}  // namespace

void verify_orderings(const pv::Values& values) {
  Signatures accepted_signatures;
  const auto accepted = settled_scenario(accepted_signatures);
  const auto& settlement = accepted.audit_blocks.back();
  agree(values, "ordering.accepted_root", hex(settlement.resulting_state_root));

  // Each rejected order is run on a chain rebuilt to the height before the
  // settlement, so the accepted reading and the rejected one are executed on
  // identical inputs rather than compared through two different histories.
  const auto root_under = [](const v9::BlockOrder& order) {
    Signatures signatures;
    auto rebuilt = rebuilt_chain_to(signatures, kSettlementHeight - 1);
    auto block = v9::execute_block(rebuilt.ledger, timestamp_of_height(kSettlementHeight),
                                   {}, signatures.verifier(), order);
    pv::require(block.has_value(), "the rebuilt settlement block must execute");
    return block->resulting_state_root;
  };

  v9::BlockOrder accrual_first;
  accrual_first.settle_before_accrual = false;
  pv::require(root_under(accrual_first) != settlement.resulting_state_root,
              "letting the accrual land first pays the closing month one window "
              "of its successor's accrual, and the root says so");
  expect_true(values, "ordering.accrual_before_the_settlement_reaches_a_different_root");

  v9::BlockOrder deletion_first;
  deletion_first.delete_before_accumulate = true;
  pv::require(root_under(deletion_first) == settlement.resulting_state_root,
              "the deletion before the accumulation reaches the same root, "
              "because the seat sequence is derived once before either step");
  expect_true(values, "ordering.deletion_before_the_accumulation_reaches_the_same_root");
}

void verify_single_pass(const pv::Values& values) {
  Signatures signatures;
  const auto halted = halted_scenario(signatures);
  const v9::BlockOutcome* jumped = nullptr;
  for (const auto& block : halted.audit_blocks) {
    if (!block.skipped_months.empty()) jumped = &block;
  }
  pv::require(jumped != nullptr, "the halt produced a settlement that skipped months");
  pv::require(jumped->settled.has_value(), "and it closed a month");

  agree(values, "single_pass.height", jumped->height);
  agree(values, "single_pass.settled_month", jumped->settled->month);
  agree(values, "single_pass.skipped_months", join(jumped->skipped_months));
  agree(values, "single_pass.months_the_halt_crossed",
        static_cast<std::uint64_t>(jumped->skipped_months.size()) + 1);

  // **The single pass against an explicit per-index loop over the same inputs.**
  // No invariant over a single accepted state separates the two, because they
  // agree on every state both produce; what distinguishes them is this.
  const auto closing = jumped->settled->month;
  const auto due = closing + static_cast<std::uint32_t>(jumped->skipped_months.size()) + 1;
  const auto payable = jumped->settled->payable_before;
  const std::vector<std::uint32_t> candidates{kAliceSeat, kBobSeat};
  const std::map<std::uint32_t, std::uint64_t> figures{
      {kAliceSeat, jumped->settled->best_figure}};

  std::uint64_t looped_payable = payable;
  std::map<std::uint32_t, std::uint64_t> looped_claims;
  for (std::uint32_t month = closing; month < due; ++month) {
    // An empty month has no window attributed to it, so it has no last window
    // and no candidate set to read against: its pass is a no-op.
    const auto month_candidates =
        month == closing ? candidates : std::vector<std::uint32_t>{};
    const auto month_figures =
        month == closing ? figures : std::map<std::uint32_t, std::uint64_t>{};
    const auto step = v9::settle_month(month, month_candidates, month_figures,
                                       looped_payable);
    pv::require(step.has_value(), "every pass of the loop settles");
    if (step->share != 0) {
      for (const auto seat : step->winners) looped_claims[seat] += step->share;
    }
    looped_payable = step->remainder;
  }

  const auto single = v9::settle_month(closing, candidates, figures, payable);
  pv::require(single.has_value(), "the single pass settles");
  std::map<std::uint32_t, std::uint64_t> single_claims;
  if (single->share != 0) {
    for (const auto seat : single->winners) single_claims[seat] += single->share;
  }
  pv::require(looped_payable == single->remainder && looped_claims == single_claims,
              "the loop and the single pass agree on the balance and the claims");
  expect_true(values, "single_pass.equals_the_loop");
}

// **The kernel reproduces the restart run before anything replays it**, so a
// store or an application that later disagrees with these figures is the layer
// at fault rather than the fixture. The stamps are checked against the fixture's
// own table as well as against the vectors, because the third block's repeated
// stamp is the run's reason to exist and a vector alone would not say so.
void verify_restart_run(const pv::Values& values) {
  Signatures signatures;
  const auto scenario = restart_scenario(signatures);
  agree(values, "restart.block_count",
        static_cast<std::uint64_t>(scenario.blocks.size()));
  pv::require(scenario.blocks.size() == kRestartStampHeights.size(),
              "one stamp per restart block");
  for (std::size_t index = 0; index < scenario.blocks.size(); ++index) {
    const auto& block = scenario.blocks[index];
    const auto key = "restart.block" + std::to_string(index);
    agree(values, key + ".height", block.height);
    pv::require(block.height == index + 1, "the restart run is contiguous");
    agree(values, key + ".timestamp", block.timestamp);
    pv::require(block.timestamp == timestamp_of_height(kRestartStampHeights[index]),
                "each restart block carries its fixture stamp");
    agree(values, key + ".admitted_count",
          static_cast<std::uint64_t>(block.executed.size()));
    agree(values, key + ".transaction_root", hex(block.transaction_root));
    agree(values, key + ".header", hex(block.header));
    agree(values, key + ".block_id", hex(block.block_id));
    agree(values, key + ".resulting_state_root", hex(block.resulting_state_root));
  }
  pv::require(scenario.blocks[2].timestamp == scenario.blocks[1].timestamp,
              "the third block repeats its predecessor's stamp");

  for (std::size_t block = 0; block < scenario.labels.size(); ++block) {
    for (std::size_t step = 0; step < scenario.labels[block].size(); ++step) {
      const auto& executed = scenario.blocks[block].executed.at(step);
      const auto name = v9::result_code_name(
          static_cast<std::uint8_t>(executed.outcome.result));
      pv::require(name.has_value(), "every result has a name");
      agree(values, "restart." + scenario.labels[block][step] + ".result",
            std::string(*name));
    }
  }

  agree(values, "restart.below_the_predecessors_stamp.refusal",
        std::string(v9::timestamp_condition_name(
            scenario.refused_below_the_predecessor)));
  pv::require(scenario.refusal_rejected_the_block,
              "the block carrying the earlier stamp is rejected whole");
  pv::require(scenario.root_after_the_refusal ==
                  scenario.blocks[1].resulting_state_root,
              "the rejected block leaves the head where block 2 left it");
  expect_true(values,
              "restart.below_the_predecessors_stamp.leaves_the_head_where_it_was");
}

// The contract file's calendar-over-a-chain section, which the codec target
// defers here because a window's month is written at its opening height and read
// two windows later.
//
// **The fixture is the contract file's own and not this trace's**, which is why
// the window indices are read out of the recorded keys rather than restated: a
// sampled window sequence is legitimate for a fixture about arithmetic and is
// not a claim about a chain, and this kernel's calendar must reach the same
// months over it.
void verify_contract_sections(const pv::Values& contract) {
  static constexpr std::uint64_t kContractGenesisMillis = 1'772'172'000'000;
  static constexpr std::uint64_t kContractMillisPerBlock = 3'000;
  const auto stamp = [](std::uint64_t height) {
    return kContractGenesisMillis + height * kContractMillisPerBlock;
  };

  std::uint64_t straddling = 0;
  for (const auto& [key, value] : contract) {
    (void)value;
    const std::string& name = key;
    if (name.rfind("attribution.window_", 0) != 0) continue;
    const auto tail = name.substr(std::string("attribution.window_").size());
    const auto dot = tail.find('.');
    if (dot == std::string::npos || tail.substr(0, dot) == "zero") continue;
    const auto window = std::stoull(tail.substr(0, dot));
    const auto field = tail.substr(dot + 1);
    if (field == "month") {
      const auto month = v9::month_index(stamp(v9::window_opening_height(window)));
      pv::require(month.has_value(), "a window's opening stamp has a month");
      agree(contract, name, *month);
    } else if (field == "straddles") {
      // A window straddles when its last height falls in a later month than its
      // first, which is the case the two rules disagree about.
      const auto first = v9::month_index(stamp(v9::window_opening_height(window)));
      const auto last =
          v9::month_index(stamp(v9::window_opening_height(window + 1) - 1));
      pv::require(first.has_value() && last.has_value(), "both ends have months");
      pv::require(*last != *first, "the window straddles a month boundary");
      expect_true(contract, name);
      straddling += 1;
    } else if (field == "month_under_the_rejected_rule") {
      const auto last =
          v9::month_index(stamp(v9::window_opening_height(window + 1) - 1));
      pv::require(last.has_value(), "the last height has a month");
      agree(contract, name, *last);
    } else if (field == "the_two_rules_disagree") {
      const auto first = v9::month_index(stamp(v9::window_opening_height(window)));
      const auto last =
          v9::month_index(stamp(v9::window_opening_height(window + 1) - 1));
      pv::require(first.has_value() && last.has_value(), "both ends have months");
      pv::require(*first != *last,
                  "the accepted rule and the rejected one are distinguishable");
      expect_true(contract, name);
    }
  }
  agree(contract, "attribution.straddling_windows", straddling);

  // **Whether kind 22 is a confirmable mint is a property of the transition**,
  // so the codec target defers it here: the scenario above presents a mint with
  // 64 zero octets against a destination whose posture requires a confirmation
  // and it is refused by name.
  expect_true(contract, "kind22.is_confirmable_mint");

  // Window zero's month is genesis's, because height zero is never a block.
  const auto genesis_month = v9::month_index(kContractGenesisMillis);
  pv::require(genesis_month.has_value(), "the genesis stamp has a month");
  agree(contract, "attribution.window_zero_month", *genesis_month);
  pv::require(v9::window_opening_height(0) == 0, "window zero opens at height zero");

  // No seat is ever in scope for window 0, because `first_cycle_window` is at
  // least 1 for every activation height there is. Checked at the boundary rather
  // than sampled: the height that opens window 1 is the last one that could put
  // a seat in scope for window 0 if the rule were `>=` instead of `>`.
  for (const std::uint64_t activation :
       {std::uint64_t{0}, std::uint64_t{1}, v9::kCycleBlocks - 1, v9::kCycleBlocks}) {
    pv::require(v9::first_cycle_window(activation) >= 1,
                "a seat's first cycle window is at least one");
    pv::require(!v9::seat_in_scope(activation, 0),
                "no seat is in scope for window zero");
  }
  expect_true(contract, "attribution.no_seat_is_in_scope_at_window_zero");
}

// The settlement arithmetic no recorded scenario reaches.
//
// **These derive their own expectations, because no vector records them**, and
// they are kept in their own function precisely so a reader never has to wonder
// which kind of evidence an assertion carries. They exist because two mutation
// probes against this kernel *passed*: the recorded chains produce no nonzero
// remainder and no month in which a candidate ran nothing wins, so discarding a
// carry and deriving the candidate set from the figures both changed no recorded
// value. A fixture that cannot see a rule is not evidence for it.
void verify_derived_settlements() {
  const std::vector<std::uint32_t> three{1, 2, 3};

  // **A remainder stays in the pool and is distributed with the next month that
  // pays.** Seven units across three equal winners assigns six and carries one.
  const std::map<std::uint32_t, std::uint64_t> tied{{1, 100}, {2, 100}, {3, 100}};
  const auto split = v9::settle_month(10, three, tied, 7);
  pv::require(split.has_value(), "an exact tie settles");
  pv::require(split->winners == three, "an exact tie shares equally");
  pv::require(split->share == 2 && split->assigned == 6 && split->remainder == 1,
              "the integer remainder is carried rather than dropped");

  // **A share of zero carries the whole balance and writes no claim**, because a
  // claim is a balance and a balance of zero is absence. In the zero-best month
  // that is the difference between up to 100,000 entries recording that nobody
  // was paid and none.
  const auto starved = v9::settle_month(10, three, tied, 2);
  pv::require(starved.has_value(), "a balance below the winner count settles");
  pv::require(starved->share == 0 && starved->assigned == 0 &&
                  starved->remainder == 2,
              "a zero share carries the whole balance");
  pv::require(starved->winners == three,
              "the winners are still the winners; there is nothing to collect");

  // **A zero-best month pays every candidate.** ADR 0075 declined a duty gate
  // and ADR 0076 declined an accumulation-cap filter, so a month in which no
  // in-scope seat was credited for a single slot splits the balance across every
  // in-scope seat. It is reachable, it is not an error, and it is not filtered.
  const auto zero_best = v9::settle_month(10, three, {}, 30);
  pv::require(zero_best.has_value(), "a zero-best month settles");
  pv::require(zero_best->best_figure == 0 && zero_best->winners == three &&
                  zero_best->share == 10,
              "every candidate ties at zero and shares");

  // **The candidate set is the seat table's and not the figures'.** A candidate
  // that ran nothing is still a candidate, which is the whole reason zero-figure
  // candidates exist; deriving the set from the figures would silently exclude
  // it.
  const std::map<std::uint32_t, std::uint64_t> one_ran{{1, 100}};
  const auto uneven = v9::settle_month(10, three, one_ran, 30);
  pv::require(uneven.has_value(), "an uneven month settles");
  pv::require(uneven->candidate_count == 3, "all three competed");
  pv::require(uneven->winners == std::vector<std::uint32_t>{1} &&
                  uneven->share == 30,
              "the one that ran takes the month");

  // **The empty-candidate case is a safety net rather than an operational
  // path.** With nothing accumulated it carries the balance; with uptime
  // accumulated and nobody to pay it is an invariant failure, because an accrual
  // implies a seat was in span and in-span implies in-scope by construction.
  const auto no_candidates = v9::settle_month(10, {}, {}, 30);
  pv::require(no_candidates.has_value() && no_candidates->remainder == 30 &&
                  no_candidates->carried(),
              "with no candidate the balance carries untouched");
  pv::require(!v9::settle_month(10, {}, one_ran, 30),
              "a month that accumulated uptime and has nobody to pay is a "
              "broken derivation rather than a carried month");
}

// A hand-built ledger holding exactly what a settlement reads, so `close_month`
// and the two functions it calls can be exercised on inputs no recorded chain
// produces.
//
// **It is asserted to be conserved before anything is settled against it**, so a
// fixture that was itself impossible could not make a settlement look correct.
v9::Ledger settlement_fixture(std::uint32_t cursor,
                              const std::vector<std::uint32_t>& seats,
                              const std::map<std::uint32_t, std::uint64_t>& figures,
                              std::uint64_t payable) {
  auto ledger = open_trace_ledger();
  for (const auto seat_id : seats) {
    v9::SeatRecord seat;
    seat.hub_identity_hash = kAliceIdentity;
    seat.is_activated = true;
    seat.activation_height = kActivationHeight;
    ledger.seats.emplace(seat_id, seat);
  }
  ledger.accumulating_month = cursor;
  for (const auto& [seat_id, seconds] : figures) {
    ledger.figures.emplace(std::pair{cursor, seat_id}, seconds);
  }
  ledger.pool_accrued = payable;
  ledger.pool_payable = payable;
  pv::require(v9::pool_failures({ledger.pool_accrued, ledger.pool_payable,
                                 ledger.pool_minted},
                                ledger.claims)
                  .empty(),
              "the settlement fixture is a conserved state before it settles");
  return ledger;
}

// What `close_month` writes, which the pure ranking above does not reach: the
// claims, the carried balance, the deletion, and the candidate set it derives
// from the seat table.
void verify_derived_closes() {
  const std::vector<std::uint32_t> three{1, 2, 3};
  const std::map<std::uint32_t, std::uint64_t> tied{{1, 100}, {2, 100}, {3, 100}};

  // **The remainder is carried and not discarded.** Seven across three equal
  // winners assigns six and leaves one payable for the next month that pays.
  {
    auto ledger = settlement_fixture(10, three, tied, 7);
    const auto closed = v9::close_month(ledger, 11, 5);
    pv::require(closed.has_value() && closed->settled.has_value(), "the month closes");
    pv::require(ledger.pool_payable == 1, "the remainder stays in the pool");
    pv::require(ledger.claims.size() == 3, "each winner holds a claim");
    for (const auto& [seat_id, claim] : ledger.claims) {
      (void)seat_id;
      pv::require(claim.accrued_atomic == 2 && claim.minted_atomic == 0,
                  "each winner is owed its share and has taken none");
    }
    pv::require(ledger.figures.empty(), "the closed month's figures are deleted");
    pv::require(v9::pool_failures({ledger.pool_accrued, ledger.pool_payable,
                                   ledger.pool_minted},
                                  ledger.claims)
                    .empty(),
                "the pool is conserved across the settlement");
  }

  // **A zero share writes no claim entry at all**, which is a rule rather than
  // an optimisation: a claim is a balance and a balance of zero is absence.
  {
    auto ledger = settlement_fixture(10, three, tied, 2);
    const auto closed = v9::close_month(ledger, 11, 5);
    pv::require(closed.has_value() && closed->settled.has_value(), "the month closes");
    pv::require(closed->settled->share == 0 && closed->settled->winners.size() == 3,
                "the winners are still the winners");
    pv::require(ledger.claims.empty(), "and none of them holds a claim of zero");
    pv::require(ledger.pool_payable == 2, "the whole balance carries");
  }

  // **A candidate that ran nothing is still a candidate**, which is the whole
  // reason zero-figure candidates exist. Deriving the set from the figures
  // instead would silently exclude it and hand the month to the one that ran.
  {
    auto ledger = settlement_fixture(10, three, {{1, 100}}, 30);
    pv::require(v9::settlement_candidates(ledger, 5) == three,
                "the candidate set is the seat table's");
    const auto closed = v9::close_month(ledger, 11, 5);
    pv::require(closed.has_value() && closed->settled.has_value(), "the month closes");
    pv::require(closed->settled->candidate_count == 3, "all three competed");
    pv::require(closed->settled->winners == std::vector<std::uint32_t>{1},
                "and the one that ran took it");
  }

  // A seat activated after the closing month's last window is not a candidate
  // for it, which is the other side of the same rule.
  {
    auto ledger = settlement_fixture(10, three, tied, 30);
    ledger.seats.at(3).activation_height = 10 * v9::kCycleBlocks;
    pv::require(v9::settlement_candidates(ledger, 5) ==
                    std::vector<std::uint32_t>{1, 2},
                "a seat whose first cycle window is past the month is excluded");
  }

  // **When the months are equal nothing closes**, which is every assignment but
  // roughly one a month, and the balance is untouched.
  {
    auto ledger = settlement_fixture(10, three, tied, 30);
    const auto closed = v9::close_month(ledger, 10, 5);
    pv::require(closed.has_value() && !closed->settled.has_value(),
                "nothing closes when the assigned window is in the open month");
    pv::require(ledger.pool_payable == 30 && ledger.claims.empty(),
                "and the balance is untouched");
    pv::require(ledger.figures.size() == 3, "and the figures keep accumulating");
  }

  // **A due month behind the cursor is a whole-block rejection.** There is no
  // correct way to continue from a corrupted cursor or a corrupted month entry.
  {
    auto ledger = settlement_fixture(10, three, tied, 30);
    pv::require(!v9::close_month(ledger, 9, 5),
                "a month behind the cursor rejects the block");
  }
}

void verify_scenarios(const pv::Values& values) {
  verify_derived_settlements();
  verify_derived_closes();
  check_genesis(values);

  Signatures settled_signatures;
  const auto settled = settled_scenario(settled_signatures);
  check_calendar(values, settled);
  check_shorthand(values, settled);
  check_audit(values, settled);
  check_settlements(values, "settled", settled);
  check_pool(values, "settled", settled);
  check_mint(values, settled);
  check_block(values, settled);

  Signatures halted_signatures;
  const auto halted = halted_scenario(halted_signatures);
  check_settlements(values, "halted", halted);
  check_pool(values, "halted", halted);
}

}  // namespace economy_v9_execution
