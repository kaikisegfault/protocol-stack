// Every recorded execution vector for the five scenarios, compared against what
// the kernel derives.
//
// Nothing here derives a second set of expected values. The kernel runs the
// scenarios and every assertion compares its result against
// `test-vectors/economy-transition-v6-execution.txt`, which is requirement 11
// for execution: the C++ implementation and the independent Python model must
// reproduce one fixed file. A missing key is a failure rather than a skip.

#include "economy_v6_execution_fixture.hpp"

#include <array>
#include <string_view>

namespace economy_v6_execution {
namespace {

std::string result_name(v6::Result result) {
  const auto name = v6::result_code_name(static_cast<std::uint8_t>(result));
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
    agree(values, prefix + ".transaction_root", hex(v6::transaction_root(admitted_ids)));
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
      agree(values, key + ".result", result_name(executed.outcome.result));
      agree(values, key + ".result_code",
            static_cast<std::uint64_t>(executed.receipt.result_code));
      const auto encoded = v6::encode_receipt(executed.receipt);
      pv::require(encoded.has_value(), key + ": the receipt must encode");
      agree(values, key + ".receipt", hex(*encoded));
    }
  }
}

// A block that follows its predecessor by one height must open on exactly the
// root its predecessor committed. A segment boundary is a run of empty blocks the
// trace does not execute, so those pairs are excluded by the height test.
void check_chaining(const pv::Values& values, const Scenario& scenario) {
  const auto& name = scenario.name;
  std::size_t consecutive = 0;
  bool chained = true;
  bool increasing = true;
  for (std::size_t index = 1; index < scenario.blocks.size(); ++index) {
    const auto& earlier = scenario.blocks[index - 1];
    const auto& later = scenario.blocks[index];
    increasing = increasing && later.height > earlier.height;
    if (later.height != earlier.height + 1) continue;
    ++consecutive;
    chained = chained && later.previous_state_root == earlier.resulting_state_root;
  }
  // An `all()` over an empty set establishes nothing, so the count is compared
  // rather than only the property, and a fixture that lost its last consecutive
  // pair fails here.
  pv::require(consecutive > 0, name + ": no consecutive block pair to chain");
  agree(values, name + ".consecutive_block_pairs", consecutive);
  pv::require(chained, name + ": a block did not open on its predecessor's root");
  expect_true(values, name + ".every_consecutive_block_opens_on_its_predecessor_root");
  pv::require(increasing, name + ": heights must never decrease");
  expect_true(values, name + ".heights_never_decrease");
}

void check_state(const pv::Values& values, const Scenario& scenario) {
  const auto& name = scenario.name;
  const auto& ledger = scenario.ledger;
  agree(values, name + ".total_supply", ledger.total_supply);
  agree(values, name + ".fee_pool", ledger.fee_pool);
  agree(values, name + ".economy_entry_count", v6::economy_entries(ledger).size());

  pv::require(v6::conservation_failures(ledger).empty(),
              name + ": the final state must be conserved");
  expect_true(values, name + ".state_is_conserved");

  const auto& registry = ledger.registry;
  bool matched = registry.accounts.size() == registry.escrows.size();
  for (const auto& [escrow, account] : registry.accounts) {
    (void)account;
    matched = matched && registry.escrows.contains(escrow);
  }
  pv::require(matched, name + ": every account must be an escrow");
  expect_true(values, name + ".every_account_is_an_escrow");

  std::uint64_t failures = 0;
  for (const auto& block : scenario.blocks) failures += block.atomic_failures;
  agree(values, name + ".refusals_checked_for_atomicity", failures);
  pv::require(failures >= 1, name + ": at least one refusal must be checked");
  expect_true(values, name + ".every_refusal_left_the_state_root_unchanged");

  const auto root = v6::ledger_state_root(ledger);
  pv::require(root.has_value(), name + ": the final state must commit a root");
  agree(values, name + ".final_state_root", hex(*root));
}

void check_admissions(const pv::Values& values, const Scenario& scenario) {
  const auto& name = scenario.name;
  agree(values, name + ".block_count", scenario.blocks.size());
  agree(values, name + ".blocks_skipped_between_segments", scenario.skipped_blocks);
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
  pv::require(offered - executed == scenario.rejected.size(),
              name + ": an admission failure produces no receipt");
  expect_true(values, name + ".admission_failures_produce_no_receipt");
}

void check_balance(const pv::Values& values, const Scenario& scenario,
                   const std::string& label, const Octets32& identity) {
  const auto escrow = v6::escrow_id(identity, 0);
  const auto found = scenario.ledger.registry.accounts.find(escrow);
  pv::require(found != scenario.ledger.registry.accounts.end(),
              scenario.name + ": " + label + " holds no escrow");
  agree(values, scenario.name + "." + label, found->second.balance);
}

void check_scenario(const pv::Values& values, const Scenario& scenario) {
  check_admissions(values, scenario);
  check_blocks(values, scenario);
  check_steps(values, scenario);
  check_chaining(values, scenario);
  check_state(values, scenario);
}

// The sections whose every vector this kernel must reproduce. The three it omits
// — `block`, `cycle`, and `ordering` — are the boundary block and the settlement
// it derives, which is the next slice; naming them here rather than skipping
// silently is what makes the boundary itself checkable.
constexpr std::array<std::string_view, 9> kClaimedSections{
    "construction.", "genesis.",       "registration.",
    "millionth.",    "recovery.",      "compatibility.",
    "posture.",      "derived.",       "determinism.",
};
constexpr std::array<std::string_view, 3> kDeferredSections{"block.", "cycle.",
                                                            "ordering."};

}  // namespace

void verify_coverage(const pv::Values& values) {
  std::size_t deferred = 0;
  for (const auto& [key, value] : values) {
    (void)value;
    // Copied out of the structured binding because C++20 does not permit a
    // lambda to capture one, and the two compilers disagree about it.
    const std::string& name = key;
    const auto matches = [&name](std::string_view prefix) {
      return name.rfind(prefix, 0) == 0;
    };
    if (std::any_of(kDeferredSections.begin(), kDeferredSections.end(), matches)) {
      ++deferred;
      continue;
    }
    pv::require(std::any_of(kClaimedSections.begin(), kClaimedSections.end(), matches),
                "vector " + key + " is in no known section");
    pv::require(consulted().contains(key), "vector " + key + " was never consulted");
  }
  // An empty deferred set would mean the boundary block's vectors had vanished
  // rather than that this kernel had grown to reproduce them.
  pv::require(deferred > 0, "the deferred sections must still record vectors");
}

void verify_scenarios(const pv::Values& values, const pv::Values& primitives) {
  {
    Signatures signatures;
    const auto scenario = registration_scenario(signatures);
    check_scenario(values, scenario);
    check_balance(values, scenario, "alice_balance", kAliceIdentity);
    check_balance(values, scenario, "bob_balance", kBobIdentity);
  }
  {
    Signatures signatures;
    const auto scenario = millionth_scenario(signatures);
    check_scenario(values, scenario);
    check_balance(values, scenario, "alice_balance", kAliceIdentity);
    check_balance(values, scenario, "dave_balance", kDaveIdentity);
  }
  {
    Signatures signatures;
    const auto scenario = recovery_scenario(signatures);
    check_scenario(values, scenario);
    check_balance(values, scenario, "maria_balance", kMariaIdentity);
    check_balance(values, scenario, "bob_balance", kBobIdentity);
  }
  {
    Signatures signatures;
    const auto scenario = compatibility_scenario(signatures, primitives);
    check_scenario(values, scenario);
    check_balance(values, scenario, "sender_balance", kAcceptedIdentity);
    check_balance(values, scenario, "bob_balance", kBobIdentity);
  }
  {
    Signatures signatures;
    const auto scenario = posture_scenario(signatures);
    check_scenario(values, scenario);
    check_balance(values, scenario, "alice_balance", kAliceIdentity);
    check_balance(values, scenario, "bob_balance", kBobIdentity);
  }
}

}  // namespace economy_v6_execution
