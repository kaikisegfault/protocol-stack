// Every recorded execution vector for the four scenarios, compared against what
// the kernel derives.
//
// Nothing here derives a second set of expected values. The kernel runs the
// scenarios and every assertion compares its result against
// `test-vectors/economy-transition-v8-execution.txt`, which is requirement 11
// for execution: the C++ implementation and the independent Python model must
// reproduce one fixed file. A missing key is a failure rather than a skip, and
// a recorded key nothing here reads fails the coverage check.

#include "economy_v8_execution_fixture.hpp"

#include <array>
#include <set>
#include <string_view>

namespace economy_v8_execution {
namespace {

std::string result_name(v8::Result result) {
  const auto name = v8::result_code_name(static_cast<std::uint8_t>(result));
  pv::require(name.has_value(), "every produced result is inside the code space");
  return std::string(*name);
}

void check_blocks(const pv::Values& values, const Scenario& scenario) {
  const auto& name = scenario.name;
  for (std::size_t index = 0; index < scenario.blocks.size(); ++index) {
    const auto& block = scenario.blocks[index];
    const auto prefix = name + ".block" + std::to_string(index);
    agree(values, prefix + ".height", block.height);
    agree(values, prefix + ".raw_input_count", scenario.raw_inputs[index]);
    agree(values, prefix + ".admitted_count", block.executed.size());
    agree(values, prefix + ".resulting_state_root", hex(block.resulting_state_root));
    agree(values, prefix + ".header", hex(block.header));
    agree(values, prefix + ".block_id", hex(block.block_id));

    std::vector<Hash> admitted_ids;
    for (const auto& executed : block.executed) {
      admitted_ids.push_back(executed.transaction_id);
    }
    agree(values, prefix + ".transaction_root",
          hex(v8::transaction_root(admitted_ids)));

    if (!block.assigned_window) continue;
    agree(values, prefix + ".assigned_window", *block.assigned_window);
    // `uptime-measurement-v1` finalises window `w` at the first height of
    // `w + 2`, so that is where `w`'s record is written and no earlier. Checking
    // the height against the window rather than reading the recorded number back
    // is what makes the prologue's placement a derivation.
    pv::require(block.height == (*block.assigned_window + v8::kAssignmentLagWindows) *
                                    v8::kCycleBlocks,
                name + ": a record was written away from its own boundary");
    expect_true(values,
                prefix + ".the_record_is_written_at_the_first_height_of_w_plus_two");
  }
}

void check_steps(const pv::Values& values, const Scenario& scenario) {
  const auto& name = scenario.name;
  for (std::size_t index = 0; index < scenario.blocks.size(); ++index) {
    const auto& block = scenario.blocks[index];
    const auto& labels = scenario.labels[index];
    pv::require(labels.size() == block.executed.size(),
                name + ": every admitted transaction carries a label");
    for (std::size_t position = 0; position < labels.size(); ++position) {
      const auto& executed = block.executed[position];
      const auto key = name + "." + labels[position];
      // A scenario records a step's result name, its numeric code, or its
      // receipt, and not always all three; each is claimed only where the file
      // records it, and the coverage check is what stops one being dropped.
      if (values.contains(key + ".result")) {
        agree(values, key + ".result", result_name(executed.outcome.result));
      }
      agree(values, key + ".result_code",
            static_cast<std::uint64_t>(executed.receipt.result_code));
      if (!values.contains(key + ".receipt")) continue;
      const auto encoded = v8::encode_receipt(executed.receipt);
      pv::require(encoded.has_value(), key + ": the receipt must encode");
      agree(values, key + ".receipt", hex(*encoded));
    }
  }
}

// A block that follows its predecessor by one height must open on exactly the
// root its predecessor committed. A segment boundary is a run of quiet heights
// the scenario does not record, so those pairs are excluded by the height test.
//
// **This is derived rather than recorded**, because the accepted file states it
// through the headers: a header carries the previous root, so a chain that
// broke here would already have failed `check_blocks`. It is checked anyway,
// because that argument is one an implementation could stop satisfying without
// any recorded value moving.
void check_chaining(const Scenario& scenario) {
  const auto& name = scenario.name;
  std::size_t consecutive = 0;
  for (std::size_t index = 1; index < scenario.blocks.size(); ++index) {
    const auto& earlier = scenario.blocks[index - 1];
    const auto& later = scenario.blocks[index];
    pv::require(later.height > earlier.height,
                name + ": heights must never decrease");
    if (later.height != earlier.height + 1) continue;
    ++consecutive;
    pv::require(later.previous_state_root == earlier.resulting_state_root,
                name + ": a block did not open on its predecessor's root");
  }
  // An `all()` over an empty set establishes nothing, so the count is required
  // to be nonzero and a fixture that lost its last consecutive pair fails here.
  pv::require(consecutive > 0, name + ": no consecutive block pair to chain");
}

void check_state(const pv::Values& values, const Scenario& scenario) {
  const auto& name = scenario.name;
  const auto& ledger = scenario.ledger;
  agree(values, name + ".total_supply", ledger.total_supply);
  agree(values, name + ".fee_pool", ledger.fee_pool);
  agree(values, name + ".economy_entry_count", v8::economy_entries(ledger).size());

  pv::require(v8::conservation_failures(ledger).empty(),
              name + ": the final state must be conserved");
  expect_true(values, name + ".state_is_conserved");

  const auto& registry = ledger.registry;
  bool matched = registry.accounts.size() == registry.escrows.size();
  for (const auto& [escrow, account] : registry.accounts) {
    (void)account;
    matched = matched && registry.escrows.contains(escrow);
  }
  pv::require(matched, name + ": every account must be an escrow");

  const auto root = v8::ledger_state_root(ledger);
  pv::require(root.has_value(), name + ": the final state must commit a root");
  agree(values, name + ".final_state_root", hex(*root));
}

void check_admissions(const pv::Values& values, const Scenario& scenario) {
  const auto& name = scenario.name;
  agree(values, name + ".block_count", scenario.blocks.size());
  agree(values, name + ".heights_run_between_recorded_blocks",
        scenario.skipped_blocks);
  for (const auto& [label, code] : scenario.rejected) {
    agree(values, name + "." + label + ".admission_code",
          static_cast<std::uint64_t>(code));
  }
  std::size_t offered = 0;
  std::size_t executed = 0;
  for (std::size_t index = 0; index < scenario.blocks.size(); ++index) {
    offered += scenario.raw_inputs[index];
    executed += scenario.blocks[index].executed.size();
  }
  // **No version-eight scenario offers an input that fails admission**, so this
  // is stated as the equality that would break if one appeared unrecorded,
  // rather than as a subtraction over an empty set. An admission failure
  // produces no receipt and never enters the transaction root, so it would show
  // up here as an executed count below the offered one with nothing recorded to
  // account for the difference.
  pv::require(offered - executed == scenario.rejected.size(),
              name + ": an admission failure produces no receipt");
  pv::require(offered == executed && scenario.rejected.empty(),
              name + ": no recorded scenario offers an inadmissible input");
  expect_true(values, name + ".admission_failures_produce_no_receipt");
}

// Every figure the scenario recorded at a named point, compared against the
// vector of the same name. A note nothing records fails here, and a recorded
// vector no note produces fails the coverage check.
void check_notes(const pv::Values& values, const Scenario& scenario) {
  for (const auto& [name, value] : scenario.notes) {
    agree(values, scenario.name + "." + name, value);
  }
}

// The same inputs, executed twice from the same genesis, commit to the same
// block identifiers and the same final root. Determinism is the sixth
// constitutional invariant and it is checked by re-running rather than asserted.
//
// **Version eight adds a third claim to it**, and it is the one the carrier
// makes necessary: the two runs must audit the same heights. Selection is a
// digest over a state root, so a kernel whose issue step read anything outside
// the state would still reproduce every block identifier while auditing a
// different set of heights in between.
void check_determinism(const pv::Values& values, const Scenario& first,
                       const Scenario& second) {
  pv::require(first.blocks.size() == second.blocks.size(),
              first.name + ": a re-run produced a different block count");
  bool identical = true;
  for (std::size_t index = 0; index < first.blocks.size(); ++index) {
    identical = identical && first.blocks[index].block_id ==
                                 second.blocks[index].block_id;
  }
  pv::require(identical, first.name + ": a re-run produced a different block ID");
  expect_true(values, "determinism." + first.name + "_reproduces_every_block_id");

  const auto left = v8::ledger_state_root(first.ledger);
  const auto right = v8::ledger_state_root(second.ledger);
  pv::require(left.has_value() && right.has_value() && *left == *right,
              first.name + ": a re-run produced a different final root");
  expect_true(values,
              "determinism." + first.name + "_reproduces_the_final_state_root");

  pv::require(first.audit_blocks.size() == second.audit_blocks.size(),
              first.name + ": a re-run audited a different number of heights");
  bool same_heights = true;
  for (std::size_t index = 0; index < first.audit_blocks.size(); ++index) {
    same_heights = same_heights && first.audit_blocks[index].height ==
                                       second.audit_blocks[index].height &&
                   first.audit_blocks[index].issued ==
                       second.audit_blocks[index].issued;
  }
  pv::require(same_heights, first.name + ": a re-run audited different heights");
  expect_true(values, "determinism." + first.name + "_audits_the_same_heights_twice");
}

void check_scenario(const pv::Values& values, const Scenario& scenario) {
  check_admissions(values, scenario);
  check_blocks(values, scenario);
  check_steps(values, scenario);
  check_chaining(scenario);
  check_state(values, scenario);
  check_notes(values, scenario);
}

constexpr std::array<std::string_view, 8> kClaimedSections{
    "construction.", "genesis.",  "receipt.",  "measured.",
    "disputed.",     "deadline.", "carried.",  "coverage.",
};

}  // namespace

void verify_coverage(const pv::Values& values) {
  for (const auto& [key, value] : values) {
    (void)value;
    // Copied out of the structured binding because C++20 does not permit a
    // lambda to capture one, and the two compilers disagree about it.
    const std::string& name = key;
    const auto matches = [&name](std::string_view prefix) {
      return name.rfind(prefix, 0) == 0;
    };
    pv::require(std::any_of(kClaimedSections.begin(), kClaimedSections.end(),
                            matches) ||
                    name.rfind("determinism.", 0) == 0,
                "vector " + key + " is in no known section");
    pv::require(consulted().contains(key), "vector " + key + " was never consulted");
  }
}

void verify_scenarios(const pv::Values& values) {
  // Every kind any scenario executed. A kind a trace never executes has no
  // recorded version-eight state root and no recorded version-eight receipt,
  // whatever an earlier version's file fixes about its bytes.
  std::set<std::uint8_t> executed_kinds;

  // Each scenario is run twice from the same genesis, and the second run is the
  // determinism evidence rather than a second opinion.
  const auto run_twice = [&](Scenario (*build)(Signatures&)) {
    Signatures first_signatures;
    const auto first = build(first_signatures);
    check_scenario(values, first);
    for (const auto& block : first.blocks) {
      for (const auto& executed : block.executed) executed_kinds.insert(executed.kind);
    }
    for (const auto& block : first.audit_blocks) {
      for (const auto& executed : block.executed) executed_kinds.insert(executed.kind);
    }
    Signatures second_signatures;
    const auto second = build(second_signatures);
    check_determinism(values, first, second);
  };

  run_twice(measured_scenario);
  run_twice(disputed_scenario);
  run_twice(deadline_scenario);
  run_twice(carried_scenario);

  agree(values, "coverage.kinds_executed", executed_kinds.size());
  std::size_t admitted_kinds = 0;
  for (std::uint16_t kind = 0; kind <= 0xFF; ++kind) {
    const auto number = static_cast<std::uint8_t>(kind);
    if (!v8::is_transaction_kind(number)) continue;
    ++admitted_kinds;
    pv::require(executed_kinds.contains(number),
                "kind " + std::to_string(kind) + " is never executed");
  }
  pv::require(executed_kinds.size() == admitted_kinds,
              "every kind version eight admits is executed and no other");
  expect_true(values, "coverage.every_kind_version_eight_admits_is_executed");
  pv::require(
      executed_kinds.contains(static_cast<std::uint8_t>(v8::Kind::challenge_response)) &&
          executed_kinds.contains(static_cast<std::uint8_t>(v8::Kind::file_dispute)),
      "the two kinds version eight adds are executed");
  expect_true(values, "coverage.the_two_kinds_version_eight_adds_are_among_them");
}

}  // namespace economy_v8_execution
