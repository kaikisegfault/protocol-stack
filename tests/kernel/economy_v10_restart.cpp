// The restart run: `simulation/economy_transition_v10/trace.py`'s
// `restart_scenario`, rebuilt, and checked against the vectors it recorded.
//
// **The kernel reproduces the run before anything replays it**, so a store or
// an application that later disagrees with these figures is the layer at fault
// rather than the fixture. The stamps are checked against the fixture's own
// table as well as against the vectors, because the third block's repeated
// stamp is one of the run's two reasons to exist and a vector alone would not
// say so. The other is the fifth block, the first a layer reopened without the
// build authority key would refuse.

#include "economy_v10_execution_fixture.hpp"

#include <utility>

namespace economy_v10_execution {
namespace {

std::uint64_t stamp(std::size_t index) {
  return timestamp_of_height(kRestartStampHeights[index]);
}

// One block at the next height and the given stamp, every step admitted.
void run(Restart& restart, const Signatures& signatures, std::uint64_t timestamp,
         std::vector<Step> steps) {
  std::vector<Bytes> raw;
  std::vector<std::string> labels;
  for (auto& step : steps) {
    raw.push_back(step.raw);
    labels.push_back(step.label);
    restart.raw[step.label] = std::move(step.raw);
  }
  auto block = v10::execute_block(restart.ledger, timestamp, raw,
                                  signatures.verifier());
  pv::require(block.has_value(), "every restart block must execute");
  pv::require(block->executed.size() == labels.size(),
              "every restart step is admitted");
  restart.blocks.push_back(std::move(*block));
  restart.labels.push_back(std::move(labels));
}

}  // namespace

Restart restart_scenario(Signatures& signatures) {
  Restart restart;
  restart.ledger = open_trace_ledger();
  auto& ledger = restart.ledger;
  const Builder build(signatures, ledger);
  constexpr std::uint32_t kAliceSeat = 0;
  constexpr std::uint32_t kBobSeat = 1;

  auto v = 1 + kLifetime;
  run(restart, signatures, stamp(0),
      {{"alice_registers",
        build.registration(kAlice, v10::kLaunchAttester, kLaunchKey, v)},
       {"bob_registers",
        build.registration(kBob, v10::kLaunchAttester, kLaunchKey, v)}});
  v = 2 + kLifetime;
  run(restart, signatures, stamp(1),
      {{"seat_0_purchased", build.purchase(kAlice, kAliceSeat, 1, v)},
       {"seat_1_purchased", build.purchase(kBob, kBobSeat, 1, v)}});

  // Height 3 is offered a stamp one millisecond below its predecessor's first.
  // The kernel's rejection carries no reason, so the condition is read from the
  // replay rule the block runs as its step 0, and the rejection from the block.
  const auto below = stamp(1) - 1;
  restart.refused_below_the_predecessor = v10::replay_timestamp(
      v10::Head{ledger.height, ledger.timestamp}, ledger.height + 1, below);
  restart.refusal_rejected_the_block =
      !v10::execute_block(ledger, below, {}, signatures.verifier()).has_value();
  const auto root = v10::ledger_state_root(ledger);
  pv::require(root.has_value(), "the refused block leaves a committable state");
  restart.root_after_the_refusal = *root;

  run(restart, signatures, stamp(2), {});
  v = 4 + kLifetime;
  run(restart, signatures, stamp(3),
      {{"seat_0_activated", build.activation(kAlice, kAliceSeat, 2, v)},
       {"seat_1_activated", build.activation(kBob, kBobSeat, 2, v)}});
  v = 5 + kLifetime;
  run(restart, signatures, stamp(4),
      {{"seat_0_machine_registered",
        build.machine_registration(kAlice, kAliceSeat, machine_key(kAliceSeat), 3, v)},
       {"seat_1_machine_registered",
        build.machine_registration(kBob, kBobSeat, machine_key(kBobSeat), 3, v)}});
  return restart;
}

void verify_restart_run(const pv::Values& values) {
  Signatures signatures;
  const auto restart = restart_scenario(signatures);
  agree(values, "restart.block_count",
        static_cast<std::uint64_t>(restart.blocks.size()));
  pv::require(restart.blocks.size() == kRestartStampHeights.size(),
              "one stamp per restart block");
  for (std::size_t index = 0; index < restart.blocks.size(); ++index) {
    const auto& block = restart.blocks[index];
    const auto key = "restart.block" + std::to_string(index);
    agree(values, key + ".height", block.height);
    pv::require(block.height == index + 1, "the restart run is contiguous");
    agree(values, key + ".timestamp", block.timestamp);
    pv::require(block.timestamp == stamp(index),
                "each restart block carries its fixture stamp");
    agree(values, key + ".admitted_count",
          static_cast<std::uint64_t>(block.executed.size()));
    agree(values, key + ".transaction_root", hex(block.transaction_root));
    agree(values, key + ".header", hex(block.header));
    agree(values, key + ".block_id", hex(block.block_id));
    agree(values, key + ".resulting_state_root", hex(block.resulting_state_root));
  }
  pv::require(restart.blocks[2].timestamp == restart.blocks[1].timestamp,
              "the third block repeats its predecessor's stamp");

  for (std::size_t block = 0; block < restart.labels.size(); ++block) {
    for (std::size_t step = 0; step < restart.labels[block].size(); ++step) {
      const auto& executed = restart.blocks[block].executed.at(step);
      agree(values, "restart." + restart.labels[block][step] + ".result",
            result_name(executed.outcome.result));
    }
  }
  pv::require(restart.ledger.machine_keys.size() == 2,
              "the fifth block registers both machines");

  agree(values, "restart.below_the_predecessors_stamp.refusal",
        std::string(v10::timestamp_condition_name(
            restart.refused_below_the_predecessor)));
  pv::require(restart.refusal_rejected_the_block,
              "the block carrying the earlier stamp is rejected whole");
  expect_claim(values,
               "restart.below_the_predecessors_stamp.leaves_the_head_where_it_was",
               restart.root_after_the_refusal ==
                   restart.blocks[1].resulting_state_root);
}

}  // namespace economy_v10_execution
