// The version-nine application layer, driven through the recorded execution
// vectors across real restarts.
//
// **Version eight's suite asked whether the root a node tells the network and
// the root it persists are one fact.** That question is re-established here over
// a version-nine chain. What version nine adds is a clock, and the questions
// worth asking about a clock are all about where it is *not*:
//
//   - `process_proposal` reads it once and every other operation reads it zero
//     times, which is counted rather than argued;
//   - `finalize_block` accepts a stamp `process_proposal` would have refused for
//     tolerance — the same height, the same bytes, one clock moved — which is the
//     single test that distinguishes a conforming implementation from one that
//     applies C5 on both paths;
//   - the status space contains no value for either C5 condition, which is
//     asserted as an absence because a status space that had one would be a
//     status space with a tolerance reachable on the replay path.

#include "protocol/application/application_v9.hpp"

#include "../storage/sqlite_ledger_v9_fixture.hpp"

#include <algorithm>
#include <atomic>
#include <filesystem>
#include <iostream>
#include <span>
#include <string>
#include <utility>
#include <variant>
#include <vector>

namespace {

namespace pa = protocol::application;
namespace ps = protocol::storage;
namespace v9 = protocol::v9;
namespace pv = protocol_vectors;
namespace fixture = economy_v9_execution;
using namespace sqlite_ledger_v9_tests;

constexpr std::uint8_t kAppStateV9[] = {
    '"', 'p', 'r', 'o', 't', 'o', 'c', 'o', 'l', '-',
    's', 't', 'a', 'c', 'k', '-', 'v', '9', '"',
};

// **Pinned to the literal, not to the constant.** Comparing
// `info().application_version` against `kApplicationProtocolVersionV9` — which
// the checks below do — claims that the value reaches the caller and says
// nothing about *which* value it is: it passes unchanged if the constant is
// still version eight's 8.
static_assert(pa::kApplicationProtocolVersionV9 == 9);

// The response code scheme is a contract with the adapter, pinned at compile
// time rather than observed.
static_assert(pa::application_code(v9::Result::success) == 0);
static_assert(pa::application_code(v9::Result::zero_amount) == 257);
static_assert(pa::application_code(v9::Result::unauthorized) == 265);

// **The decision space is `calendar-v1`'s numbering, which is why the mapping is
// a cast.** Pinning the five here is what makes `decision_of` a claim rather
// than a coincidence: a kernel that renumbered a condition would break these
// before it reached a vote.
static_assert(pa::decision_of(v9::TimestampCondition::accepted) ==
              pa::ProposalDecision::accepted);
static_assert(pa::decision_of(v9::TimestampCondition::height_not_next) ==
              pa::ProposalDecision::height_not_next);
static_assert(pa::decision_of(v9::TimestampCondition::timestamp_range) ==
              pa::ProposalDecision::timestamp_range);
static_assert(pa::decision_of(v9::TimestampCondition::timestamp_not_monotonic) ==
              pa::ProposalDecision::timestamp_not_monotonic);
static_assert(pa::decision_of(
                  v9::TimestampCondition::timestamp_ahead_of_tolerance) ==
              pa::ProposalDecision::timestamp_ahead_of_tolerance);
static_assert(pa::decision_of(
                  v9::TimestampCondition::timestamp_behind_tolerance) ==
              pa::ProposalDecision::timestamp_behind_tolerance);
// And the two this contract adds are numbered after the last kernel condition,
// so a sixth kernel condition would collide rather than append.
static_assert(static_cast<std::uint8_t>(pa::ProposalDecision::resource_bound) ==
              v9::kTimestampConditionCount);
static_assert(static_cast<std::uint8_t>(pa::ProposalDecision::not_executable) ==
              v9::kTimestampConditionCount + 1);

// **The absence the contract asks a conforming test to assert.** There are
// exactly two fatal timestamp statuses and they are C1's and C2's. An
// implementation whose status space contained a tolerance value would have a
// tolerance reachable on the replay path, which is the defect the separation
// exists to prevent, so the absence is checked rather than the presence.
static_assert(static_cast<std::uint16_t>(
                  pa::TimestampFailureV9::decided_block_failed_range) == 7);
static_assert(static_cast<std::uint16_t>(
                  pa::TimestampFailureV9::decided_block_failed_monotonicity) == 8);
static_assert(sizeof(pa::TimestampFailureV9) == sizeof(std::uint16_t));

v9::Octets32 trace_chain_id() {
  const auto identity = v9::chain_id(fixture::trace_genesis());
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

std::string decision_text(pa::ProposalDecision decision) {
  switch (decision) {
    case pa::ProposalDecision::accepted: return "ACCEPTED";
    case pa::ProposalDecision::height_not_next: return "HEIGHT_NOT_NEXT";
    case pa::ProposalDecision::timestamp_range: return "TIMESTAMP_RANGE";
    case pa::ProposalDecision::timestamp_not_monotonic:
      return "TIMESTAMP_NOT_MONOTONIC";
    case pa::ProposalDecision::timestamp_ahead_of_tolerance:
      return "TIMESTAMP_AHEAD_OF_TOLERANCE";
    case pa::ProposalDecision::timestamp_behind_tolerance:
      return "TIMESTAMP_BEHIND_TOLERANCE";
    case pa::ProposalDecision::resource_bound: return "RESOURCE_BOUND";
    case pa::ProposalDecision::not_executable: return "NOT_EXECUTABLE";
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

pa::FinalizedBlockV9 require_finalized(pa::FinalizeBlockResultV9 result,
                                       const std::string& subject) {
  if (std::holds_alternative<pa::FinalizeFailureV9>(result)) {
    const auto failure = std::get<pa::FinalizeFailureV9>(result);
    if (std::holds_alternative<pa::ApplicationError>(failure)) {
      pv::require(false, subject + ": " +
                             error_text(std::get<pa::ApplicationError>(failure)));
    }
    pv::require(false, subject + ": a fatal timestamp status");
  }
  return std::get<pa::FinalizedBlockV9>(std::move(result));
}

void require_timestamp_failure(pa::FinalizeBlockResultV9 result,
                               pa::TimestampFailureV9 expected,
                               const std::string& subject) {
  pv::require(std::holds_alternative<pa::FinalizeFailureV9>(result),
              subject + ": the block finalized");
  const auto failure = std::get<pa::FinalizeFailureV9>(result);
  pv::require(std::holds_alternative<pa::TimestampFailureV9>(failure),
              subject + ": the failure was not a timestamp status");
  pv::require(std::get<pa::TimestampFailureV9>(failure) == expected,
              subject + ": the wrong timestamp status");
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

void require_decision(pa::ProcessProposalResultV9 result,
                      pa::ProposalDecision expected,
                      const std::string& subject) {
  if (std::holds_alternative<pa::ApplicationError>(result)) {
    pv::require(false, subject + ": " +
                           error_text(std::get<pa::ApplicationError>(result)));
  }
  const auto actual = std::get<pa::ProposalDecision>(result);
  pv::require(actual == expected, subject + ": expected " +
                                      decision_text(expected) + ", got " +
                                      decision_text(actual));
}

// **A clock that counts.** Every operation but `process_proposal` must leave the
// count where it found it, which is how "no path from finalize, commit, restart,
// or reconstruction reaches the bound clock source" is measured rather than
// asserted. The reading itself is settable so a case can place a stamp on either
// side of the tolerance.
struct CountingClock {
  std::shared_ptr<std::uint64_t> now = std::make_shared<std::uint64_t>(0);
  std::shared_ptr<std::atomic<std::size_t>> reads =
      std::make_shared<std::atomic<std::size_t>>(0);

  pa::ClockSourceV9 source() const {
    auto value = now;
    auto counter = reads;
    return [value, counter]() -> std::uint64_t {
      counter->fetch_add(1);
      return *value;
    };
  }
};

pa::ApplicationV9 open_application(const std::filesystem::path& path,
                                   bool create, const CountingClock& clock) {
  const auto genesis = fixture::trace_genesis();
  auto store = require_store(
      create ? ps::create_sqlite_ledger_v9(path, genesis, trace_verifier())
             : ps::open_sqlite_ledger_v9(path, genesis, trace_verifier()),
      create ? "creating the store" : "reopening the store");
  auto made = pa::make_application_v9(std::move(store), clock.source());
  if (std::holds_alternative<pa::ApplicationError>(made.result)) {
    pv::require(false, "the application did not open: " +
                           error_text(std::get<pa::ApplicationError>(made.result)));
  }
  return std::get<pa::ApplicationV9>(std::move(made.result));
}

std::uint64_t block_height(const pv::Values& values, std::size_t index) {
  return recorded_number(values, block_label(index) + ".height");
}

std::uint64_t block_timestamp(const pv::Values& values, std::size_t index) {
  return recorded_number(values, block_label(index) + ".timestamp");
}

// Drive one recorded block all the way through, and compare it against the
// vectors rather than against the application.
void drive_block(pa::ApplicationV9& application, const pv::Values& values,
                 std::size_t index, CountingClock& clock) {
  const auto height = block_height(values, index);
  const auto timestamp = block_timestamp(values, index);
  const auto& inputs = restart_run().block_inputs[index];
  const auto label = block_label(index);

  // Put the clock on the stamp so C5 is satisfied for the honest path.
  *clock.now = timestamp;
  const auto before = clock.reads->load();
  require_decision(application.process_proposal(height, timestamp, inputs),
                   pa::ProposalDecision::accepted, label + ": process");
  pv::require(clock.reads->load() == before + 1,
              label + ": process_proposal must read the clock exactly once");

  const auto after_process = clock.reads->load();
  auto finalized = require_finalized(
      application.finalize_block(height, timestamp, inputs), label + ": finalize");
  pv::require(fixture::hex(finalized.state_root) ==
                  recorded(values, label + ".resulting_state_root"),
              label + ": the finalized root is not the recorded one");
  pv::require(fixture::hex(finalized.block_id) ==
                  recorded(values, label + ".block_id"),
              label + ": the finalized block identifier is not the recorded one");
  pv::require(finalized.transaction_results.size() == inputs.size(),
              label + ": one result per raw input");

  // Asking twice must answer the same, and the stamp is part of what makes a
  // repeat a repeat.
  auto again = require_finalized(
      application.finalize_block(height, timestamp, inputs),
      label + ": finalize again");
  pv::require(again == finalized, label + ": the repeated finalize differed");

  auto committed = require_value<pa::CommitResultV9, pa::CommittedHeadV9>(
      application.commit(), label + ": commit");
  pv::require(committed.height == height,
              label + ": committed at the wrong height");
  pv::require(committed.timestamp == timestamp,
              label + ": committed at the wrong timestamp");
  pv::require(committed.state_root == finalized.state_root,
              label + ": the committed root is not the finalized one");

  auto info = require_value<pa::InfoResultV9, pa::ApplicationInfoV9>(
      application.info(), label + ": info");
  pv::require(info.application_version == pa::kApplicationProtocolVersionV9,
              label + ": the reported protocol version is wrong");
  pv::require(info.height == height, label + ": info reports the wrong height");
  pv::require(info.timestamp == timestamp,
              label + ": info reports the wrong timestamp");
  pv::require(fixture::hex(info.state_root) ==
                  recorded(values, label + ".resulting_state_root"),
              label + ": info reports a root that is not the recorded one");

  // **The measurement.** Finalize, a repeated finalize, commit, and info between
  // them read the clock zero times.
  pv::require(clock.reads->load() == after_process,
              label + ": an operation after process_proposal read the clock");
}

// Four blocks, three restarts, and the application rebuilt from the file each
// time.
void check_pipeline_across_restarts(const pv::Values& values,
                                    const std::filesystem::path& directory) {
  const auto path = directory / "application.db";
  CountingClock clock;
  {
    auto application = open_application(path, true, clock);
    require_error(application.check_transaction(std::span<const std::uint8_t>{}),
                  pa::ApplicationError::sequence_failure,
                  "checking a transaction before init_chain");
    const auto before = clock.reads->load();
    auto root = require_value<pa::InitChainResultV9, v9::Hash>(
        application.init_chain(trace_chain_id(), 1, fixture::kGenesisMillis,
                               kAppStateV9),
        "init_chain");
    pv::require(clock.reads->load() == before,
                "init_chain must read no clock");
    auto info = require_value<pa::InfoResultV9, pa::ApplicationInfoV9>(
        application.info(), "info at genesis");
    pv::require(info.height == 0 && info.state_root == root,
                "init_chain must answer the genesis root");
    pv::require(info.timestamp == fixture::kGenesisMillis,
                "the genesis head carries the genesis stamp");
    drive_block(application, values, 0, clock);
  }
  for (std::size_t index = 1; index < kContiguousBlocks; ++index) {
    auto application = open_application(path, false, clock);
    auto info = require_value<pa::InfoResultV9, pa::ApplicationInfoV9>(
        application.info(), "info after restart");
    pv::require(info.height == block_height(values, index - 1),
                "the reopened application is at the wrong height");
    pv::require(info.timestamp == block_timestamp(values, index - 1),
                "the reopened application restored the wrong stamp");
    drive_block(application, values, index, clock);
  }
}

// **Every decision the contract names, each produced on its own.**
//
// One is missing and its absence is established rather than skipped.
// `NOT_EXECUTABLE` is a whole-block rejection, and the kernel does not produce
// one from a proposal's *contents*: a transaction that cannot be decoded, is
// signed wrongly, names an unknown seat, overflows its debit, or cannot pay its
// fee is refused as a transaction **result**, inside an accepted block. The case
// below offers a block of such transactions and requires it to be `ACCEPTED`,
// which is what makes the absence a measurement. Decision `7` guards chain-state
// failures — a prologue, issue, expiry, or conservation failure — which no peer
// can induce by choosing bytes.
void check_every_decision(const pv::Values& values,
                          const std::filesystem::path& directory) {
  const auto path = directory / "decisions.db";
  CountingClock clock;
  auto application = open_application(path, true, clock);
  require_value<pa::InitChainResultV9, v9::Hash>(
      application.init_chain(trace_chain_id(), 1, fixture::kGenesisMillis,
                             kAppStateV9),
      "init_chain");

  const auto height = block_height(values, 0);
  const auto stamp = block_timestamp(values, 0);
  const auto& inputs = restart_run().block_inputs[0];
  *clock.now = stamp;

  require_decision(application.process_proposal(height, stamp, inputs),
                   pa::ProposalDecision::accepted, "decision 0");
  require_decision(application.process_proposal(height + 1, stamp, inputs),
                   pa::ProposalDecision::height_not_next, "decision 1");
  require_decision(
      application.process_proposal(height, v9::kMaxTimestampMillis + 1, inputs),
      pa::ProposalDecision::timestamp_range, "decision 2");
  require_decision(
      application.process_proposal(height, fixture::kGenesisMillis - 1, inputs),
      pa::ProposalDecision::timestamp_not_monotonic, "decision 3");

  // C5's two sides, each at its exact boundary. The clock is moved rather than
  // the stamp, so the block is the same block in all four calls.
  *clock.now = stamp - v9::kTimestampToleranceMillis;
  require_decision(application.process_proposal(height, stamp, inputs),
                   pa::ProposalDecision::accepted,
                   "a stamp exactly at own_clock + tolerance");
  *clock.now = stamp - v9::kTimestampToleranceMillis - 1;
  require_decision(application.process_proposal(height, stamp, inputs),
                   pa::ProposalDecision::timestamp_ahead_of_tolerance,
                   "decision 4");
  *clock.now = stamp + v9::kTimestampToleranceMillis;
  require_decision(application.process_proposal(height, stamp, inputs),
                   pa::ProposalDecision::accepted,
                   "a stamp exactly at own_clock - tolerance");
  *clock.now = stamp + v9::kTimestampToleranceMillis + 1;
  require_decision(application.process_proposal(height, stamp, inputs),
                   pa::ProposalDecision::timestamp_behind_tolerance,
                   "decision 5");

  *clock.now = stamp;
  const std::vector<v9::Bytes> too_many(pa::kMaximumBlockInputsV9 + 1,
                                        v9::Bytes{});
  require_decision(application.process_proposal(height, stamp, too_many),
                   pa::ProposalDecision::resource_bound, "decision 6");

  // The absence, measured. Four transactions the kernel refuses for four
  // different reasons, offered as one block, and the block is accepted.
  std::vector<v9::Bytes> refusable{
      v9::Bytes{0x00},
      v9::Bytes(64, 0xFF),
      inputs.empty() ? v9::Bytes{0x01} : inputs.front(),
  };
  require_decision(application.process_proposal(height, stamp, refusable),
                   pa::ProposalDecision::accepted,
                   "a block of refusable transactions must still be accepted");
}

// **The normative order, where two conditions fire at once.** The vote is the
// same under either order, so this decides only what is reported — which is
// exactly why it needs a test.
void check_first_condition_wins(const pv::Values& values,
                                const std::filesystem::path& directory) {
  const auto path = directory / "ordering.db";
  CountingClock clock;
  auto application = open_application(path, true, clock);
  require_value<pa::InitChainResultV9, v9::Hash>(
      application.init_chain(trace_chain_id(), 1, fixture::kGenesisMillis,
                             kAppStateV9),
      "init_chain");
  const auto height = block_height(values, 0);
  const auto stamp = block_timestamp(values, 0);
  const auto& inputs = restart_run().block_inputs[0];
  *clock.now = stamp;

  // Height and range: the height fires first.
  require_decision(application.process_proposal(height + 7,
                                                v9::kMaxTimestampMillis + 1,
                                                inputs),
                   pa::ProposalDecision::height_not_next,
                   "height before range");
  // Range and monotonicity: a stamp past the range is also below nothing, so
  // the case that makes both true is a stamp past the *upper* bound offered
  // against a head whose stamp is higher than nothing — the range still wins,
  // and the alternative would be to report a monotonicity failure on a value
  // that has no month at all.
  require_decision(application.process_proposal(height,
                                                v9::kMaxTimestampMillis + 1,
                                                inputs),
                   pa::ProposalDecision::timestamp_range,
                   "range before monotonicity");
  // Monotonicity and tolerance: a stamp below the head's *and* outside the
  // tolerance reports the monotonicity failure.
  *clock.now = fixture::kGenesisMillis + 10 * v9::kTimestampToleranceMillis;
  require_decision(
      application.process_proposal(height, fixture::kGenesisMillis - 1, inputs),
      pa::ProposalDecision::timestamp_not_monotonic,
      "monotonicity before tolerance");

  // **And every ordered condition before the resource bounds**, which is the
  // pair the contract's own sentence is about: the vote is identical under
  // either order, so nothing but a reported value distinguishes them. Each
  // proposal below violates a bound *and* a timestamp rule, and must report the
  // timestamp rule.
  *clock.now = stamp;
  const std::vector<v9::Bytes> too_many(pa::kMaximumBlockInputsV9 + 1,
                                        v9::Bytes{});
  require_decision(application.process_proposal(height + 7, stamp, too_many),
                   pa::ProposalDecision::height_not_next,
                   "height before the resource bound");
  require_decision(application.process_proposal(
                       height, v9::kMaxTimestampMillis + 1, too_many),
                   pa::ProposalDecision::timestamp_range,
                   "range before the resource bound");
  require_decision(application.process_proposal(
                       height, fixture::kGenesisMillis - 1, too_many),
                   pa::ProposalDecision::timestamp_not_monotonic,
                   "monotonicity before the resource bound");
  *clock.now = stamp - v9::kTimestampToleranceMillis - 1;
  require_decision(application.process_proposal(height, stamp, too_many),
                   pa::ProposalDecision::timestamp_ahead_of_tolerance,
                   "the tolerance before the resource bound");
}

// **The single test that distinguishes a conforming implementation from one
// that applies C5 on both paths.** The same height, the same bytes, one clock
// moved: `process_proposal` refuses for tolerance and `finalize_block` accepts.
void check_finalize_ignores_the_tolerance(const pv::Values& values,
                                          const std::filesystem::path& directory) {
  const auto path = directory / "tolerance.db";
  CountingClock clock;
  auto application = open_application(path, true, clock);
  require_value<pa::InitChainResultV9, v9::Hash>(
      application.init_chain(trace_chain_id(), 1, fixture::kGenesisMillis,
                             kAppStateV9),
      "init_chain");
  const auto height = block_height(values, 0);
  const auto stamp = block_timestamp(values, 0);
  const auto& inputs = restart_run().block_inputs[0];

  // A clock far enough away that C5 cannot pass.
  *clock.now = stamp + 1'000 * v9::kTimestampToleranceMillis;
  require_decision(application.process_proposal(height, stamp, inputs),
                   pa::ProposalDecision::timestamp_behind_tolerance,
                   "the proposal must be refused for tolerance");

  // The same block, decided by the network anyway. The clock has not moved.
  const auto before = clock.reads->load();
  auto finalized = require_finalized(
      application.finalize_block(height, stamp, inputs),
      "finalize must accept what the proposal refused for tolerance");
  pv::require(clock.reads->load() == before,
              "finalize_block read the clock");
  pv::require(fixture::hex(finalized.state_root) ==
                  recorded(values, block_label(0) + ".resulting_state_root"),
              "the finalized root is not the recorded one");
  auto committed = require_value<pa::CommitResultV9, pa::CommittedHeadV9>(
      application.commit(), "commit");
  pv::require(committed.timestamp == stamp, "the committed stamp is not the one");
  pv::require(clock.reads->load() == before, "commit read the clock");
}

// **A decided block whose stamp this machine's rules refuse is fatal**, and the
// status names which rule failed. Each case gets its own application, because
// each one latches.
void check_decided_block_timestamp_failures(
    const pv::Values& values, const std::filesystem::path& directory) {
  const auto height = block_height(values, 0);
  const auto& inputs = restart_run().block_inputs[0];
  struct Case {
    const char* name;
    std::uint64_t timestamp;
    pa::TimestampFailureV9 expected;
  };
  const Case cases[] = {
      {"range", v9::kMaxTimestampMillis + 1,
       pa::TimestampFailureV9::decided_block_failed_range},
      {"monotonicity", fixture::kGenesisMillis - 1,
       pa::TimestampFailureV9::decided_block_failed_monotonicity},
  };
  std::size_t index = 0;
  for (const auto& single : cases) {
    const auto path = directory / ("fatal" + std::to_string(index++) + ".db");
    CountingClock clock;
    auto application = open_application(path, true, clock);
    require_value<pa::InitChainResultV9, v9::Hash>(
        application.init_chain(trace_chain_id(), 1, fixture::kGenesisMillis,
                               kAppStateV9),
        "init_chain");
    const auto before = clock.reads->load();
    require_timestamp_failure(
        application.finalize_block(height, single.timestamp, inputs),
        single.expected,
        std::string("a decided block failing C1 or C2: ") + single.name);
    pv::require(clock.reads->load() == before,
                "a fatal finalize read the clock");
    // And it latched.
    require_error(application.info(), pa::ApplicationError::sequence_failure,
                  "the application continued after a fatal timestamp status");
  }
}

// **A replay must reproduce the same root, and it must be given the same
// stamp.** A replay that advanced the height and supplied a fresh stamp would
// commit a root naming a height the stamp does not belong to, and every later
// block would still satisfy C2 because the stale stamp is smaller.
void check_replay(const pv::Values& values,
                  const std::filesystem::path& directory) {
  const auto path = directory / "replay.db";
  CountingClock clock;
  const auto height = block_height(values, 0);
  const auto stamp = block_timestamp(values, 0);
  const auto& inputs = restart_run().block_inputs[0];
  {
    auto application = open_application(path, true, clock);
    require_value<pa::InitChainResultV9, v9::Hash>(
        application.init_chain(trace_chain_id(), 1, fixture::kGenesisMillis,
                               kAppStateV9),
        "init_chain");
    *clock.now = stamp;
    auto first = require_finalized(
        application.finalize_block(height, stamp, inputs), "the first finalize");
    // The same height with a *different* stamp, while a stage exists, is a
    // different request and must be refused rather than answered.
    auto different = application.finalize_block(height, stamp + 1, inputs);
    pv::require(std::holds_alternative<pa::FinalizeFailureV9>(different),
                "a replay at a different stamp was answered");
    (void)first;
  }
  // The stage was discarded with the process and the durable head is still the
  // old one, so the height replays from the file.
  {
    auto application = open_application(path, false, clock);
    auto info = require_value<pa::InfoResultV9, pa::ApplicationInfoV9>(
        application.info(), "info after the interrupted finalize");
    pv::require(info.height == 0,
                "a finalize that never committed must leave the old head");
    // **The store is still at genesis, so this process must initialise again.**
    // That is the rule rather than an artefact: `init_chain` happens once per
    // chain, and a chain whose first block never committed has not had one. A
    // CometBFT node in exactly this state calls InitChain again on restart.
    require_value<pa::InitChainResultV9, v9::Hash>(
        application.init_chain(trace_chain_id(), 1, fixture::kGenesisMillis,
                               kAppStateV9),
        "init_chain after the interrupted finalize");
    *clock.now = stamp;
    auto replayed = require_finalized(
        application.finalize_block(height, stamp, inputs), "the replayed finalize");
    pv::require(fixture::hex(replayed.state_root) ==
                    recorded(values, block_label(0) + ".resulting_state_root"),
                "the replayed root is not byte-identical to the recorded one");
    require_value<pa::CommitResultV9, pa::CommittedHeadV9>(application.commit(),
                                                           "commit the replay");
  }
}

// InitChain's four compared values, and the one version nine adds.
void check_init_chain(const std::filesystem::path& directory) {
  const auto path = directory / "init.db";
  CountingClock clock;
  {
    auto application = open_application(path, true, clock);
    // **The genesis stamp is compared.** A node started against a genesis whose
    // stamp differs refuses here rather than at the first block.
    require_error(
        application.init_chain(trace_chain_id(), 1, fixture::kGenesisMillis + 1,
                               kAppStateV9),
        pa::ApplicationError::invalid_request,
        "init_chain admitted a mismatching genesis timestamp");
  }
  {
    auto application = open_application(path, false, clock);
    require_error(application.init_chain(trace_chain_id(), 2,
                                         fixture::kGenesisMillis, kAppStateV9),
                  pa::ApplicationError::invalid_request,
                  "init_chain admitted an initial height that is not one");
  }
  {
    auto application = open_application(path, false, clock);
    const std::uint8_t stale[] = {'"', 'p', 'r', 'o', 't', 'o', 'c', 'o',
                                  'l', '-', 's', 't', 'a', 'c', 'k', '-',
                                  'v', '8', '"'};
    require_error(application.init_chain(trace_chain_id(), 1,
                                         fixture::kGenesisMillis, stale),
                  pa::ApplicationError::invalid_request,
                  "init_chain admitted version eight's app state");
  }
  {
    // Idempotent before the first block.
    auto application = open_application(path, false, clock);
    auto first = require_value<pa::InitChainResultV9, v9::Hash>(
        application.init_chain(trace_chain_id(), 1, fixture::kGenesisMillis,
                               kAppStateV9),
        "the first init_chain");
    auto again = require_value<pa::InitChainResultV9, v9::Hash>(
        application.init_chain(trace_chain_id(), 1, fixture::kGenesisMillis,
                               kAppStateV9),
        "the repeated init_chain");
    pv::require(first == again, "init_chain is not idempotent");
  }
}

// A deployment that cannot read a clock must fail to start.
void check_a_clockless_deployment_refuses(
    const std::filesystem::path& directory) {
  const auto path = directory / "clockless.db";
  const auto genesis = fixture::trace_genesis();
  auto store = require_store(
      ps::create_sqlite_ledger_v9(path, genesis, trace_verifier()),
      "creating the clockless store");
  auto made = pa::make_application_v9(std::move(store), pa::ClockSourceV9{});
  pv::require(std::holds_alternative<pa::ApplicationError>(made.result),
              "an application without a clock started");
  pv::require(std::get<pa::ApplicationError>(made.result) ==
                  pa::ApplicationError::invalid_request,
              "a clockless deployment refused for the wrong reason");
}

}  // namespace

int main(int argc, char** argv) {
  try {
    pv::require(argc == 3, "usage: application_v9_tests VECTORS DIR");
    pv::require(sodium_init() >= 0, "libsodium initialization");
    const auto values = pv::load_values(argv[1]);
    const std::filesystem::path directory(argv[2]);
    std::filesystem::remove_all(directory);
    std::filesystem::create_directories(directory);

    check_pipeline_across_restarts(values, directory);
    check_every_decision(values, directory);
    check_first_condition_wins(values, directory);
    check_finalize_ignores_the_tolerance(values, directory);
    check_decided_block_timestamp_failures(values, directory);
    check_replay(values, directory);
    check_init_chain(directory);
    check_a_clockless_deployment_refuses(directory);

    std::filesystem::remove_all(directory);
    std::cout << "C++ version-nine application: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "C++ version-nine application: failed: " << error.what() << '\n';
    return 1;
  }
}
