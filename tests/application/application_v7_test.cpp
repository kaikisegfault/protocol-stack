// The version-seven application layer, driven through the recorded execution
// vectors across real restarts.
//
// **The question this asks that M3.13b's could not** is whether the root a node
// *tells the network* at `finalize_block` and the root it *persists* at `commit`
// are one fact. The store's own tests apply blocks directly; nothing went
// through the staged-then-replayed path, and nothing was asked to survive a
// process ending between two blocks of a chain while a proposal pipeline drove
// it.
//
// The `carried` scenario's four contiguous blocks are driven as
// `process_proposal` → `finalize_block` → `commit`, with the application and its
// store **destroyed and reopened between every pair**, and every block must
// reproduce its *recorded* `block_id` and `resulting_state_root`.

#include "protocol/application/application_v7.hpp"

#include "../storage/sqlite_ledger_v7_fixture.hpp"

#include <algorithm>
#include <filesystem>
#include <span>
#include <iostream>
#include <string>
#include <utility>
#include <variant>
#include <vector>

namespace {

namespace pa = protocol::application;
namespace ps = protocol::storage;
namespace v7 = protocol::v7;
namespace pv = protocol_vectors;
namespace fixture = economy_v7_execution;
using namespace sqlite_ledger_v7_tests;

constexpr std::uint8_t kAppStateV7[] = {
    '"', 'p', 'r', 'o', 't', 'o', 'c', 'o', 'l', '-',
    's', 't', 'a', 'c', 'k', '-', 'v', '7', '"',
};

// The response code scheme is a contract with the adapter, so it is pinned at
// compile time rather than observed. An admission failure keeps its own small
// number; an execution result is offset, so the two can never be confused.
static_assert(pa::application_code(v7::AdmissionError::malformed_transaction) ==
              1);
static_assert(pa::application_code(v7::AdmissionError::wrong_chain) == 2);
static_assert(pa::application_code(v7::AdmissionError::invalid_signature) == 3);
static_assert(pa::application_code(v7::Result::success) == 0);
static_assert(pa::application_code(v7::Result::zero_amount) == 257);
static_assert(pa::application_code(v7::Result::unauthorized) == 265);
static_assert(pa::application_code(v7::Result::not_enrolled) == 288);

// The chain identity the recorded trace runs under, derived from the genesis
// rather than restated, so a fixture change cannot leave the two disagreeing.
v7::Octets32 trace_chain_id() {
  const auto identity = v7::chain_id(fixture::trace_genesis());
  pv::require(identity.has_value(), "the trace genesis has a chain identity");
  return *identity;
}

std::string error_text(pa::ApplicationError error) {
  switch (error) {
    case pa::ApplicationError::invalid_request: return "invalid_request";
    case pa::ApplicationError::unsupported: return "unsupported";
    case pa::ApplicationError::sequence_failure: return "sequence_failure";
    case pa::ApplicationError::kernel_failure: return "kernel_failure";
    case pa::ApplicationError::storage_failure: return "storage_failure";
    case pa::ApplicationError::internal_failure: return "internal_failure";
  }
  return "unknown";
}

template <typename Result, typename Value>
Value require_value(Result result, const std::string& subject) {
  if (std::holds_alternative<pa::ApplicationError>(result)) {
    pv::require(false, subject + ": " +
                           error_text(std::get<pa::ApplicationError>(result)));
  }
  return std::get<Value>(std::move(result));
}

template <typename Result>
void require_error(const Result& result, pa::ApplicationError expected,
                   const std::string& subject) {
  pv::require(std::holds_alternative<pa::ApplicationError>(result),
              subject + ": the call succeeded");
  const auto actual = std::get<pa::ApplicationError>(result);
  pv::require(actual == expected, subject + ": expected " +
                                      error_text(expected) + ", got " +
                                      error_text(actual));
}

pa::ApplicationV7 open_application(const std::filesystem::path& path,
                                   bool create) {
  const auto genesis = fixture::trace_genesis();
  auto store = require_store(
      create ? ps::create_sqlite_ledger_v7(path, genesis, trace_verifier())
             : ps::open_sqlite_ledger_v7(path, genesis, trace_verifier()),
      create ? "creating the store" : "reopening the store");
  auto made = pa::make_application_v7(std::move(store));
  if (std::holds_alternative<pa::ApplicationError>(made.result)) {
    pv::require(false, "the application did not open: " +
                           error_text(std::get<pa::ApplicationError>(
                               made.result)));
  }
  return std::get<pa::ApplicationV7>(std::move(made.result));
}

// Drive one recorded block all the way through, and compare it against the
// vectors rather than against the application.
void drive_block(pa::ApplicationV7& application, const pv::Values& values,
                 std::size_t index) {
  const auto& scenario = carried_scenario();
  const auto height = scenario.blocks[index].height;
  const auto& inputs = scenario.block_inputs[index];
  const auto label = "carried.block" + std::to_string(index);

  auto processed = application.process_proposal(height, inputs);
  pv::require(std::holds_alternative<bool>(processed) &&
                  std::get<bool>(processed),
              label + ": the proposal was not accepted");

  auto finalized = require_value<pa::FinalizeBlockResultV7, pa::FinalizedBlockV7>(
      application.finalize_block(height, inputs), label + ": finalize");
  pv::require(fixture::hex(finalized.state_root) ==
                  recorded(values, label + ".resulting_state_root"),
              label + ": the finalized root is not the recorded one");
  pv::require(fixture::hex(finalized.block_id) ==
                  recorded(values, label + ".block_id"),
              label + ": the finalized block identifier is not the recorded one");
  pv::require(finalized.transaction_results.size() ==
                  scenario.raw_inputs[index],
              label + ": one result per raw input");

  // Asking twice must answer the same, because CometBFT may and a second
  // execution that disagreed with the first is exactly what this layer must not
  // hide.
  auto again = require_value<pa::FinalizeBlockResultV7, pa::FinalizedBlockV7>(
      application.finalize_block(height, inputs), label + ": finalize again");
  pv::require(again == finalized, label + ": the repeated finalize differed");

  auto committed = require_value<pa::CommitResultV7, pa::CommittedHeadV7>(
      application.commit(), label + ": commit");
  pv::require(committed.height == height, label + ": committed at the wrong height");
  pv::require(committed.state_root == finalized.state_root,
              label + ": the committed root is not the finalized one");

  auto info = require_value<pa::InfoResultV7, pa::ApplicationInfoV7>(
      application.info(), label + ": info");
  pv::require(info.application_version == pa::kApplicationProtocolVersionV7,
              label + ": the reported protocol version is wrong");
  pv::require(info.height == height, label + ": info reports the wrong height");
  pv::require(fixture::hex(info.state_root) ==
                  recorded(values, label + ".resulting_state_root"),
              label + ": info reports a root that is not the recorded one");
}

// Four blocks, three restarts, and the application rebuilt from the file each
// time. Nothing after the first block is finalized against a head that stayed in
// memory.
void check_pipeline_across_restarts(const pv::Values& values,
                                    const std::filesystem::path& directory) {
  const auto path = directory / "application.db";
  {
    auto application = open_application(path, true);
    // A store at genesis is not ready until the chain is initialised.
    require_error(application.check_transaction(std::span<const std::uint8_t>{}),
                  pa::ApplicationError::sequence_failure,
                  "checking a transaction before init_chain");
    auto root = require_value<pa::InitChainResultV7, v7::Hash>(
        application.init_chain(trace_chain_id(), 1,
                               kAppStateV7),
        "init_chain");
    auto info = require_value<pa::InfoResultV7, pa::ApplicationInfoV7>(
        application.info(), "info at genesis");
    pv::require(info.height == 0 && info.state_root == root,
                "init_chain must answer the genesis root");
    drive_block(application, values, 0);
  }
  for (std::size_t index = 1; index < kContiguousBlocks; ++index) {
    auto application = open_application(path, false);
    // A store past genesis was initialised by a previous process: `init_chain`
    // happens once in a chain's life, not once per process.
    auto info = require_value<pa::InfoResultV7, pa::ApplicationInfoV7>(
        application.info(), "info after restart");
    pv::require(info.height == index,
                "the reopened application is at the wrong height");
    drive_block(application, values, index);
  }
  {
    auto application = open_application(path, false);
    auto info = require_value<pa::InfoResultV7, pa::ApplicationInfoV7>(
        application.info(), "the final info");
    pv::require(fixture::hex(info.state_root) ==
                    recorded(values, "carried.block" +
                                         std::to_string(kContiguousBlocks - 1) +
                                         ".resulting_state_root"),
                "the final durable root is not the recorded one");
  }
}

// **A raw input the kernel refuses at admission must be invisible to
// consensus.** It performs no state read or write, produces no receipt, and
// never enters the ordered transaction root — so a recorded block with one
// appended must reproduce the *same* recorded root and the *same* recorded block
// identifier, and differ only by one more result row.
//
// That is what makes this a test of the response's order rather than of its
// length: none of the recorded blocks contains a rejected admission, so without
// it a `finalize_result` that simply dropped rejected inputs would pass
// everything else here.
void check_rejected_input_is_invisible(const pv::Values& values,
                                       const std::filesystem::path& directory) {
  const auto& scenario = carried_scenario();
  auto application = open_application(directory / "rejected-input.db", true);
  (void)application.init_chain(trace_chain_id(), 1, kAppStateV7);

  auto inputs = scenario.block_inputs[0];
  const auto admitted_count = inputs.size();
  // Eight zero octets are not a transaction under any version.
  inputs.push_back(v7::Bytes(8, 0x00));

  auto processed = application.process_proposal(1, inputs);
  pv::require(std::holds_alternative<bool>(processed) &&
                  std::get<bool>(processed),
              "a block whose last input is malformed is still a valid block");

  auto finalized = require_value<pa::FinalizeBlockResultV7, pa::FinalizedBlockV7>(
      application.finalize_block(1, inputs), "finalize with a rejected input");
  pv::require(fixture::hex(finalized.state_root) ==
                  recorded(values, "carried.block0.resulting_state_root"),
              "a rejected input must not change the state root");
  pv::require(fixture::hex(finalized.block_id) ==
                  recorded(values, "carried.block0.block_id"),
              "a rejected input must not change the block identifier");
  pv::require(finalized.transaction_results.size() == admitted_count + 1,
              "there must be one result per raw input, rejected ones included");
  const auto& refused = finalized.transaction_results.back();
  pv::require(refused.code ==
                  pa::application_code(v7::AdmissionError::malformed_transaction),
              "the rejected input's result must carry its admission code");
  pv::require(refused.data.empty(),
              "a rejected input produces no receipt");
  for (std::size_t index = 0; index < admitted_count; ++index) {
    const auto& result = finalized.transaction_results[index];
    pv::require(result.code < 256U || !result.data.empty(),
                "an admitted input's result must carry its receipt");
  }

  auto committed = require_value<pa::CommitResultV7, pa::CommittedHeadV7>(
      application.commit(), "commit with a rejected input");
  pv::require(fixture::hex(committed.state_root) ==
                  recorded(values, "carried.block0.resulting_state_root"),
              "the committed root must be the recorded one");
}

void check_init_chain_refusals(const std::filesystem::path& directory) {
  const auto chain_id = trace_chain_id();
  {
    auto application = open_application(directory / "init-chain.db", true);
    auto other = chain_id;
    other[0] ^= 0x01;
    require_error(application.init_chain(other, 1, kAppStateV7),
                  pa::ApplicationError::invalid_request,
                  "init_chain under another chain identity");
    // And the refusal latches: an application that was asked to join the wrong
    // chain does not get a second chance at the right one.
    require_error(application.init_chain(chain_id, 1, kAppStateV7),
                  pa::ApplicationError::sequence_failure,
                  "init_chain after a refusal");
    require_error(application.info(), pa::ApplicationError::sequence_failure,
                  "info after a refusal");
  }
  {
    auto application = open_application(directory / "init-height.db", true);
    require_error(application.init_chain(chain_id, 2, kAppStateV7),
                  pa::ApplicationError::invalid_request,
                  "init_chain at an initial height that is not one");
  }
  {
    auto application = open_application(directory / "init-state.db", true);
    constexpr std::uint8_t kVersionOneState[] = {
        '"', 'p', 'r', 'o', 't', 'o', 'c', 'o', 'l', '-',
        's', 't', 'a', 'c', 'k', '-', 'v', '1', '"',
    };
    require_error(application.init_chain(chain_id, 1, kVersionOneState),
                  pa::ApplicationError::invalid_request,
                  "init_chain with version one's app state");
  }
}

void check_sequence_refusals(const std::filesystem::path& directory) {
  const auto chain_id = trace_chain_id();
  const auto& scenario = carried_scenario();
  {
    // Committing without finalizing is the sequence violation that matters
    // most: it is the one that would persist a block the network was never told
    // about.
    auto application = open_application(directory / "commit-first.db", true);
    (void)application.init_chain(chain_id, 1, kAppStateV7);
    require_error(application.commit(), pa::ApplicationError::sequence_failure,
                  "committing with nothing staged");
    require_error(application.commit(), pa::ApplicationError::sequence_failure,
                  "committing after the latch");
  }
  {
    auto application = open_application(directory / "finalize-height.db", true);
    (void)application.init_chain(chain_id, 1, kAppStateV7);
    require_error(application.finalize_block(2, scenario.block_inputs[0]),
                  pa::ApplicationError::sequence_failure,
                  "finalizing a block this chain cannot be at");
  }
  {
    auto application = open_application(directory / "finalize-twice.db", true);
    (void)application.init_chain(chain_id, 1, kAppStateV7);
    (void)application.finalize_block(1, scenario.block_inputs[0]);
    // Staged already, and a different block. Two answers for one height is the
    // condition this layer exists to refuse.
    require_error(application.finalize_block(1, scenario.block_inputs[1]),
                  pa::ApplicationError::sequence_failure,
                  "finalizing a second, different block at one height");
  }
  {
    auto application = open_application(directory / "propose-staged.db", true);
    (void)application.init_chain(chain_id, 1, kAppStateV7);
    (void)application.finalize_block(1, scenario.block_inputs[0]);
    require_error(application.process_proposal(2, scenario.block_inputs[1]),
                  pa::ApplicationError::sequence_failure,
                  "processing a proposal while a block is staged");
    require_error(application.prepare_proposal(1024, scenario.block_inputs[1]),
                  pa::ApplicationError::sequence_failure,
                  "preparing a proposal while a block is staged");
  }
}

void check_proposal_refusals(const std::filesystem::path& directory) {
  const auto chain_id = trace_chain_id();
  const auto& scenario = carried_scenario();
  auto application = open_application(directory / "proposals.db", true);
  (void)application.init_chain(chain_id, 1, kAppStateV7);

  // A proposal is voted against, not errored on: refusing a peer's block is an
  // ordinary answer and must not latch this node terminal.
  for (const std::uint64_t height : {std::uint64_t{0}, std::uint64_t{2}}) {
    auto processed = application.process_proposal(height, scenario.block_inputs[0]);
    pv::require(std::holds_alternative<bool>(processed) &&
                    !std::get<bool>(processed),
                "a proposal away from the next height must be voted against");
  }
  const std::vector<v7::Bytes> too_many(pa::kMaximumBlockInputsV7 + 1,
                                        v7::Bytes{});
  auto oversized = application.process_proposal(1, too_many);
  pv::require(std::holds_alternative<bool>(oversized) &&
                  !std::get<bool>(oversized),
              "a proposal past the input bound must be voted against");
  // ... and the node is still usable afterwards, which is the half a refusal
  // alone does not show.
  auto processed = application.process_proposal(1, scenario.block_inputs[0]);
  pv::require(std::holds_alternative<bool>(processed) &&
                  std::get<bool>(processed),
              "a refused proposal must not disable the node");

  // `prepare_proposal` keeps the order it was handed and stops at the byte
  // budget rather than reordering or dropping from the middle.
  auto prepared =
      require_value<pa::PrepareProposalResultV7, pa::PreparedProposal>(
          application.prepare_proposal(1'000'000, scenario.block_inputs[0]),
          "preparing a proposal");
  pv::require(prepared.transactions == scenario.block_inputs[0],
              "a proposal within budget must be exactly what arrived");
  auto truncated =
      require_value<pa::PrepareProposalResultV7, pa::PreparedProposal>(
          application.prepare_proposal(
              static_cast<std::int64_t>(scenario.block_inputs[0][0].size()),
              scenario.block_inputs[0]),
          "preparing a proposal at a one-transaction budget");
  pv::require(truncated.transactions.size() == 1 &&
                  truncated.transactions[0] == scenario.block_inputs[0][0],
              "a budget of one transaction must yield the first one");
  require_error(application.prepare_proposal(-1, scenario.block_inputs[0]),
                pa::ApplicationError::invalid_request,
                "preparing a proposal with a negative budget");
}

void check_transaction_admission(const std::filesystem::path& directory) {
  const auto chain_id = trace_chain_id();
  const auto& scenario = carried_scenario();
  auto application = open_application(directory / "mempool.db", true);
  (void)application.init_chain(chain_id, 1, kAppStateV7);

  auto accepted =
      require_value<pa::TransactionCheckResultV7, pa::TransactionResult>(
          application.check_transaction(scenario.block_inputs[0][0]),
          "checking a recorded transaction");
  pv::require(accepted.code == 0 && accepted.data.empty(),
              "a recorded transaction must be admitted with no receipt");

  const v7::Bytes rubbish(8, 0x00);
  auto refused =
      require_value<pa::TransactionCheckResultV7, pa::TransactionResult>(
          application.check_transaction(rubbish), "checking rubbish");
  pv::require(refused.code ==
                  pa::application_code(v7::AdmissionError::malformed_transaction),
              "rubbish must be refused as malformed");

  // An admission refusal is a mempool answer, not a fault: the node keeps going.
  auto still =
      require_value<pa::TransactionCheckResultV7, pa::TransactionResult>(
          application.check_transaction(scenario.block_inputs[0][0]),
          "checking after a refusal");
  pv::require(still.code == 0, "a refused transaction must not disable the node");
}

}  // namespace

int main(int argc, char** argv) {
  try {
    pv::require(argc == 3, "usage: application_v7_tests VECTORS DIR");
    pv::require(sodium_init() >= 0, "libsodium initialization");
    const auto values = pv::load_values(argv[1]);
    const std::filesystem::path directory(argv[2]);
    std::filesystem::remove_all(directory);
    std::filesystem::create_directories(directory);

    check_pipeline_across_restarts(values, directory);
    check_rejected_input_is_invisible(values, directory);
    check_init_chain_refusals(directory);
    check_sequence_refusals(directory);
    check_proposal_refusals(directory);
    check_transaction_admission(directory);
    std::filesystem::remove_all(directory);

    std::cout << "C++ version-seven application: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "C++ version-seven application: failed: " << error.what()
              << '\n';
    return 1;
  }
}
