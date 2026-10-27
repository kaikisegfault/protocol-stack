// The version-ten application layer, driven through the recorded execution
// vectors across real restarts.
//
// **Version eight's suite asked whether the root a node tells the network and
// the root it persists are one fact.** That question is re-established here over
// a version-ten chain. Version nine's suite added a clock, and its questions
// are carried whole, because version ten's application is version nine's
// rebound (ADR 0110). They are all about where the clock is *not*:
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
//
// **Version ten adds two questions.** The restart run's fifth block registers
// both machines through kind 23, whose attestation verifies against the build
// authority key no root commits to. So it succeeds only if that key reached an
// application reopened just before it. And a result version ten adds must reach
// the adapter at the top of the range, as code `305`.

#include "protocol/application/application_v10.hpp"

#include "../storage/sqlite_ledger_v10_fixture.hpp"

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
namespace v10 = protocol::v10;
namespace pv = protocol_vectors;
namespace fixture = economy_v10_execution;
using namespace sqlite_ledger_v10_tests;

constexpr std::uint8_t kAppStateV10[] = {
    '"', 'p', 'r', 'o', 't', 'o', 'c', 'o', 'l', '-',
    's', 't', 'a', 'c', 'k', '-', 'v', '1', '0', '"',
};

// **Pinned to the literal, not to the constant.** Comparing
// `info().application_version` against `kApplicationProtocolVersionV10` — which
// the checks below do — claims that the value reaches the caller and says
// nothing about *which* value it is: it passes unchanged if the constant is
// still version nine's 9.
static_assert(pa::kApplicationProtocolVersionV10 == 10);

// The response code scheme is a contract with the adapter, pinned at compile
// time rather than observed.
static_assert(pa::application_code(v10::Result::success) == 0);
static_assert(pa::application_code(v10::Result::zero_amount) == 257);
static_assert(pa::application_code(v10::Result::unauthorized) == 265);
// The five version ten adds, which `consensus-application-v3` maps to `301`
// through `305`. The last is the top of the range.
static_assert(pa::application_code(v10::Result::launch_key_retired) == 301);
static_assert(pa::application_code(v10::Result::machine_key_not_found) == 302);
static_assert(pa::application_code(v10::Result::machine_not_active) == 303);
static_assert(pa::application_code(v10::Result::registration_limit) == 304);
static_assert(pa::application_code(v10::Result::approval_lifetime_exceeded) ==
              305);
static_assert(v10::kResultCodeCount == 50);

// **The decision space is `calendar-v1`'s numbering, which is why the mapping is
// a cast.** Pinning the five here is what makes `decision_of` a claim rather
// than a coincidence: a kernel that renumbered a condition would break these
// before it reached a vote.
static_assert(pa::decision_of(v10::TimestampCondition::accepted) ==
              pa::ProposalDecisionV10::accepted);
static_assert(pa::decision_of(v10::TimestampCondition::height_not_next) ==
              pa::ProposalDecisionV10::height_not_next);
static_assert(pa::decision_of(v10::TimestampCondition::timestamp_range) ==
              pa::ProposalDecisionV10::timestamp_range);
static_assert(pa::decision_of(v10::TimestampCondition::timestamp_not_monotonic) ==
              pa::ProposalDecisionV10::timestamp_not_monotonic);
static_assert(pa::decision_of(
                  v10::TimestampCondition::timestamp_ahead_of_tolerance) ==
              pa::ProposalDecisionV10::timestamp_ahead_of_tolerance);
static_assert(pa::decision_of(
                  v10::TimestampCondition::timestamp_behind_tolerance) ==
              pa::ProposalDecisionV10::timestamp_behind_tolerance);
// And the two this contract adds are numbered after the last kernel condition,
// so a sixth kernel condition would collide rather than append.
static_assert(static_cast<std::uint8_t>(pa::ProposalDecisionV10::resource_bound) ==
              v10::kTimestampConditionCount);
static_assert(static_cast<std::uint8_t>(pa::ProposalDecisionV10::not_executable) ==
              v10::kTimestampConditionCount + 1);

// **The absence the contract asks a conforming test to assert.** There are
// exactly two fatal timestamp statuses and they are C1's and C2's. An
// implementation whose status space contained a tolerance value would have a
// tolerance reachable on the replay path, which is the defect the separation
// exists to prevent, so the absence is checked rather than the presence.
static_assert(static_cast<std::uint16_t>(
                  pa::TimestampFailureV10::decided_block_failed_range) == 7);
static_assert(static_cast<std::uint16_t>(
                  pa::TimestampFailureV10::decided_block_failed_monotonicity) == 8);
static_assert(sizeof(pa::TimestampFailureV10) == sizeof(std::uint16_t));

v10::Octets32 trace_chain_id() {
  const auto identity = v10::chain_id(fixture::trace_genesis());
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

std::string decision_text(pa::ProposalDecisionV10 decision) {
  switch (decision) {
    case pa::ProposalDecisionV10::accepted: return "ACCEPTED";
    case pa::ProposalDecisionV10::height_not_next: return "HEIGHT_NOT_NEXT";
    case pa::ProposalDecisionV10::timestamp_range: return "TIMESTAMP_RANGE";
    case pa::ProposalDecisionV10::timestamp_not_monotonic:
      return "TIMESTAMP_NOT_MONOTONIC";
    case pa::ProposalDecisionV10::timestamp_ahead_of_tolerance:
      return "TIMESTAMP_AHEAD_OF_TOLERANCE";
    case pa::ProposalDecisionV10::timestamp_behind_tolerance:
      return "TIMESTAMP_BEHIND_TOLERANCE";
    case pa::ProposalDecisionV10::resource_bound: return "RESOURCE_BOUND";
    case pa::ProposalDecisionV10::not_executable: return "NOT_EXECUTABLE";
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

pa::FinalizedBlockV10 require_finalized(pa::FinalizeBlockResultV10 result,
                                       const std::string& subject) {
  if (std::holds_alternative<pa::FinalizeFailureV10>(result)) {
    const auto failure = std::get<pa::FinalizeFailureV10>(result);
    if (std::holds_alternative<pa::ApplicationError>(failure)) {
      pv::require(false, subject + ": " +
                             error_text(std::get<pa::ApplicationError>(failure)));
    }
    pv::require(false, subject + ": a fatal timestamp status");
  }
  return std::get<pa::FinalizedBlockV10>(std::move(result));
}

void require_timestamp_failure(pa::FinalizeBlockResultV10 result,
                               pa::TimestampFailureV10 expected,
                               const std::string& subject) {
  pv::require(std::holds_alternative<pa::FinalizeFailureV10>(result),
              subject + ": the block finalized");
  const auto failure = std::get<pa::FinalizeFailureV10>(result);
  pv::require(std::holds_alternative<pa::TimestampFailureV10>(failure),
              subject + ": the failure was not a timestamp status");
  pv::require(std::get<pa::TimestampFailureV10>(failure) == expected,
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

void require_decision(pa::ProcessProposalResultV10 result,
                      pa::ProposalDecisionV10 expected,
                      const std::string& subject) {
  if (std::holds_alternative<pa::ApplicationError>(result)) {
    pv::require(false, subject + ": " +
                           error_text(std::get<pa::ApplicationError>(result)));
  }
  const auto actual = std::get<pa::ProposalDecisionV10>(result);
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

  pa::ClockSourceV10 source() const {
    auto value = now;
    auto counter = reads;
    return [value, counter]() -> std::uint64_t {
      counter->fetch_add(1);
      return *value;
    };
  }
};

pa::ApplicationV10 open_application(const std::filesystem::path& path,
                                   bool create, const CountingClock& clock) {
  const auto genesis = fixture::trace_genesis();
  auto store = require_store(
      create ? ps::create_sqlite_ledger_v10(path, genesis, trace_verifier())
             : ps::open_sqlite_ledger_v10(path, genesis, trace_verifier()),
      create ? "creating the store" : "reopening the store");
  auto made = pa::make_application_v10(std::move(store), clock.source());
  if (std::holds_alternative<pa::ApplicationError>(made.result)) {
    pv::require(false, "the application did not open: " +
                           error_text(std::get<pa::ApplicationError>(made.result)));
  }
  return std::get<pa::ApplicationV10>(std::move(made.result));
}

std::uint64_t block_height(const pv::Values& values, std::size_t index) {
  return recorded_number(values, block_label(index) + ".height");
}

std::uint64_t block_timestamp(const pv::Values& values, std::size_t index) {
  return recorded_number(values, block_label(index) + ".timestamp");
}

// Drive one recorded block all the way through, and compare it against the
// vectors rather than against the application.
void drive_block(pa::ApplicationV10& application, const pv::Values& values,
                 std::size_t index, CountingClock& clock) {
  const auto height = block_height(values, index);
  const auto timestamp = block_timestamp(values, index);
  const auto& inputs = restart_run().block_inputs[index];
  const auto label = block_label(index);

  // Put the clock on the stamp so C5 is satisfied for the honest path.
  *clock.now = timestamp;
  const auto before = clock.reads->load();
  require_decision(application.process_proposal(height, timestamp, inputs),
                   pa::ProposalDecisionV10::accepted, label + ": process");
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
  // **Each result is the one the model recorded for its step.** The root already
  // implies it, and the codes say which step: in the fifth block they are the
  // two kind-23 registrations, through an application reopened just before it.
  const auto& steps = restart_run().labels[index];
  for (std::size_t input = 0; input < inputs.size(); ++input) {
    const auto step = "restart." + steps[input];
    const auto& result = finalized.transaction_results[input];
    pv::require(recorded(values, step + ".result") == "SUCCESS",
                step + ": the run records a success for every step");
    const auto receipt = v10::decode_receipt(result.data);
    pv::require(result.code == 0 && receipt.has_value() &&
                    receipt->result_code == 0,
                step + ": the application did not answer a version-ten success");
  }

  // Asking twice must answer the same, and the stamp is part of what makes a
  // repeat a repeat.
  auto again = require_finalized(
      application.finalize_block(height, timestamp, inputs),
      label + ": finalize again");
  pv::require(again == finalized, label + ": the repeated finalize differed");

  auto committed = require_value<pa::CommitResultV10, pa::CommittedHeadV10>(
      application.commit(), label + ": commit");
  pv::require(committed.height == height,
              label + ": committed at the wrong height");
  pv::require(committed.timestamp == timestamp,
              label + ": committed at the wrong timestamp");
  pv::require(committed.state_root == finalized.state_root,
              label + ": the committed root is not the finalized one");

  auto info = require_value<pa::InfoResultV10, pa::ApplicationInfoV10>(
      application.info(), label + ": info");
  pv::require(info.application_version == pa::kApplicationProtocolVersionV10,
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

// Five blocks, four restarts, and the application rebuilt from the file each
// time. The fifth block is the kind-23 one, applied by a reopened application.
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
    auto root = require_value<pa::InitChainResultV10, v10::Hash>(
        application.init_chain(trace_chain_id(), 1, fixture::kGenesisMillis,
                               kAppStateV10),
        "init_chain");
    pv::require(clock.reads->load() == before,
                "init_chain must read no clock");
    auto info = require_value<pa::InfoResultV10, pa::ApplicationInfoV10>(
        application.info(), "info at genesis");
    pv::require(info.height == 0 && info.state_root == root,
                "init_chain must answer the genesis root");
    pv::require(info.timestamp == fixture::kGenesisMillis,
                "the genesis head carries the genesis stamp");
    drive_block(application, values, 0, clock);
  }
  for (std::size_t index = 1; index < kContiguousBlocks; ++index) {
    auto application = open_application(path, false, clock);
    auto info = require_value<pa::InfoResultV10, pa::ApplicationInfoV10>(
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
  require_value<pa::InitChainResultV10, v10::Hash>(
      application.init_chain(trace_chain_id(), 1, fixture::kGenesisMillis,
                             kAppStateV10),
      "init_chain");

  const auto height = block_height(values, 0);
  const auto stamp = block_timestamp(values, 0);
  const auto& inputs = restart_run().block_inputs[0];
  *clock.now = stamp;

  require_decision(application.process_proposal(height, stamp, inputs),
                   pa::ProposalDecisionV10::accepted, "decision 0");
  require_decision(application.process_proposal(height + 1, stamp, inputs),
                   pa::ProposalDecisionV10::height_not_next, "decision 1");
  require_decision(
      application.process_proposal(height, v10::kMaxTimestampMillis + 1, inputs),
      pa::ProposalDecisionV10::timestamp_range, "decision 2");
  require_decision(
      application.process_proposal(height, fixture::kGenesisMillis - 1, inputs),
      pa::ProposalDecisionV10::timestamp_not_monotonic, "decision 3");

  // C5's two sides, each at its exact boundary. The clock is moved rather than
  // the stamp, so the block is the same block in all four calls.
  *clock.now = stamp - v10::kTimestampToleranceMillis;
  require_decision(application.process_proposal(height, stamp, inputs),
                   pa::ProposalDecisionV10::accepted,
                   "a stamp exactly at own_clock + tolerance");
  *clock.now = stamp - v10::kTimestampToleranceMillis - 1;
  require_decision(application.process_proposal(height, stamp, inputs),
                   pa::ProposalDecisionV10::timestamp_ahead_of_tolerance,
                   "decision 4");
  *clock.now = stamp + v10::kTimestampToleranceMillis;
  require_decision(application.process_proposal(height, stamp, inputs),
                   pa::ProposalDecisionV10::accepted,
                   "a stamp exactly at own_clock - tolerance");
  *clock.now = stamp + v10::kTimestampToleranceMillis + 1;
  require_decision(application.process_proposal(height, stamp, inputs),
                   pa::ProposalDecisionV10::timestamp_behind_tolerance,
                   "decision 5");

  *clock.now = stamp;
  const std::vector<v10::Bytes> too_many(pa::kMaximumBlockInputsV10 + 1,
                                        v10::Bytes{});
  require_decision(application.process_proposal(height, stamp, too_many),
                   pa::ProposalDecisionV10::resource_bound, "decision 6");

  // The absence, measured. Four transactions the kernel refuses for four
  // different reasons, offered as one block, and the block is accepted.
  std::vector<v10::Bytes> refusable{
      v10::Bytes{0x00},
      v10::Bytes(64, 0xFF),
      inputs.empty() ? v10::Bytes{0x01} : inputs.front(),
  };
  require_decision(application.process_proposal(height, stamp, refusable),
                   pa::ProposalDecisionV10::accepted,
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
  require_value<pa::InitChainResultV10, v10::Hash>(
      application.init_chain(trace_chain_id(), 1, fixture::kGenesisMillis,
                             kAppStateV10),
      "init_chain");
  const auto height = block_height(values, 0);
  const auto stamp = block_timestamp(values, 0);
  const auto& inputs = restart_run().block_inputs[0];
  *clock.now = stamp;

  // Height and range: the height fires first.
  require_decision(application.process_proposal(height + 7,
                                                v10::kMaxTimestampMillis + 1,
                                                inputs),
                   pa::ProposalDecisionV10::height_not_next,
                   "height before range");
  // Range and monotonicity: a stamp past the range is also below nothing, so
  // the case that makes both true is a stamp past the *upper* bound offered
  // against a head whose stamp is higher than nothing — the range still wins,
  // and the alternative would be to report a monotonicity failure on a value
  // that has no month at all.
  require_decision(application.process_proposal(height,
                                                v10::kMaxTimestampMillis + 1,
                                                inputs),
                   pa::ProposalDecisionV10::timestamp_range,
                   "range before monotonicity");
  // Monotonicity and tolerance: a stamp below the head's *and* outside the
  // tolerance reports the monotonicity failure.
  *clock.now = fixture::kGenesisMillis + 10 * v10::kTimestampToleranceMillis;
  require_decision(
      application.process_proposal(height, fixture::kGenesisMillis - 1, inputs),
      pa::ProposalDecisionV10::timestamp_not_monotonic,
      "monotonicity before tolerance");

  // **And every ordered condition before the resource bounds**, which is the
  // pair the contract's own sentence is about: the vote is identical under
  // either order, so nothing but a reported value distinguishes them. Each
  // proposal below violates a bound *and* a timestamp rule, and must report the
  // timestamp rule.
  *clock.now = stamp;
  const std::vector<v10::Bytes> too_many(pa::kMaximumBlockInputsV10 + 1,
                                        v10::Bytes{});
  require_decision(application.process_proposal(height + 7, stamp, too_many),
                   pa::ProposalDecisionV10::height_not_next,
                   "height before the resource bound");
  require_decision(application.process_proposal(
                       height, v10::kMaxTimestampMillis + 1, too_many),
                   pa::ProposalDecisionV10::timestamp_range,
                   "range before the resource bound");
  require_decision(application.process_proposal(
                       height, fixture::kGenesisMillis - 1, too_many),
                   pa::ProposalDecisionV10::timestamp_not_monotonic,
                   "monotonicity before the resource bound");
  *clock.now = stamp - v10::kTimestampToleranceMillis - 1;
  require_decision(application.process_proposal(height, stamp, too_many),
                   pa::ProposalDecisionV10::timestamp_ahead_of_tolerance,
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
  require_value<pa::InitChainResultV10, v10::Hash>(
      application.init_chain(trace_chain_id(), 1, fixture::kGenesisMillis,
                             kAppStateV10),
      "init_chain");
  const auto height = block_height(values, 0);
  const auto stamp = block_timestamp(values, 0);
  const auto& inputs = restart_run().block_inputs[0];

  // A clock far enough away that C5 cannot pass.
  *clock.now = stamp + 1'000 * v10::kTimestampToleranceMillis;
  require_decision(application.process_proposal(height, stamp, inputs),
                   pa::ProposalDecisionV10::timestamp_behind_tolerance,
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
  auto committed = require_value<pa::CommitResultV10, pa::CommittedHeadV10>(
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
    pa::TimestampFailureV10 expected;
  };
  const Case cases[] = {
      {"range", v10::kMaxTimestampMillis + 1,
       pa::TimestampFailureV10::decided_block_failed_range},
      {"monotonicity", fixture::kGenesisMillis - 1,
       pa::TimestampFailureV10::decided_block_failed_monotonicity},
  };
  std::size_t index = 0;
  for (const auto& single : cases) {
    const auto path = directory / ("fatal" + std::to_string(index++) + ".db");
    CountingClock clock;
    auto application = open_application(path, true, clock);
    require_value<pa::InitChainResultV10, v10::Hash>(
        application.init_chain(trace_chain_id(), 1, fixture::kGenesisMillis,
                               kAppStateV10),
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
    require_value<pa::InitChainResultV10, v10::Hash>(
        application.init_chain(trace_chain_id(), 1, fixture::kGenesisMillis,
                               kAppStateV10),
        "init_chain");
    *clock.now = stamp;
    auto first = require_finalized(
        application.finalize_block(height, stamp, inputs), "the first finalize");
    // The same height with a *different* stamp, while a stage exists, is a
    // different request and must be refused rather than answered.
    auto different = application.finalize_block(height, stamp + 1, inputs);
    pv::require(std::holds_alternative<pa::FinalizeFailureV10>(different),
                "a replay at a different stamp was answered");
    (void)first;
  }
  // The stage was discarded with the process and the durable head is still the
  // old one, so the height replays from the file.
  {
    auto application = open_application(path, false, clock);
    auto info = require_value<pa::InfoResultV10, pa::ApplicationInfoV10>(
        application.info(), "info after the interrupted finalize");
    pv::require(info.height == 0,
                "a finalize that never committed must leave the old head");
    // **The store is still at genesis, so this process must initialise again.**
    // That is the rule rather than an artefact: `init_chain` happens once per
    // chain, and a chain whose first block never committed has not had one. A
    // CometBFT node in exactly this state calls InitChain again on restart.
    require_value<pa::InitChainResultV10, v10::Hash>(
        application.init_chain(trace_chain_id(), 1, fixture::kGenesisMillis,
                               kAppStateV10),
        "init_chain after the interrupted finalize");
    *clock.now = stamp;
    auto replayed = require_finalized(
        application.finalize_block(height, stamp, inputs), "the replayed finalize");
    pv::require(fixture::hex(replayed.state_root) ==
                    recorded(values, block_label(0) + ".resulting_state_root"),
                "the replayed root is not byte-identical to the recorded one");
    require_value<pa::CommitResultV10, pa::CommittedHeadV10>(application.commit(),
                                                           "commit the replay");
  }
}

// InitChain's four compared values, and the one version ten adds.
void check_init_chain(const std::filesystem::path& directory) {
  const auto path = directory / "init.db";
  CountingClock clock;
  {
    auto application = open_application(path, true, clock);
    // **The genesis stamp is compared.** A node started against a genesis whose
    // stamp differs refuses here rather than at the first block.
    require_error(
        application.init_chain(trace_chain_id(), 1, fixture::kGenesisMillis + 1,
                               kAppStateV10),
        pa::ApplicationError::invalid_request,
        "init_chain admitted a mismatching genesis timestamp");
  }
  {
    auto application = open_application(path, false, clock);
    require_error(application.init_chain(trace_chain_id(), 2,
                                         fixture::kGenesisMillis, kAppStateV10),
                  pa::ApplicationError::invalid_request,
                  "init_chain admitted an initial height that is not one");
  }
  {
    auto application = open_application(path, false, clock);
    const std::uint8_t stale[] = {'"', 'p', 'r', 'o', 't', 'o', 'c', 'o',
                                  'l', '-', 's', 't', 'a', 'c', 'k', '-',
                                  'v', '9', '"'};
    require_error(application.init_chain(trace_chain_id(), 1,
                                         fixture::kGenesisMillis, stale),
                  pa::ApplicationError::invalid_request,
                  "init_chain admitted version nine's app state");
  }
  {
    // Idempotent before the first block.
    auto application = open_application(path, false, clock);
    auto first = require_value<pa::InitChainResultV10, v10::Hash>(
        application.init_chain(trace_chain_id(), 1, fixture::kGenesisMillis,
                               kAppStateV10),
        "the first init_chain");
    auto again = require_value<pa::InitChainResultV10, v10::Hash>(
        application.init_chain(trace_chain_id(), 1, fixture::kGenesisMillis,
                               kAppStateV10),
        "the repeated init_chain");
    pv::require(first == again, "init_chain is not idempotent");
  }
}

// **A result version ten adds, at the top of the range, end to end.** The
// restart run records no refused transaction, so this offers the first block's
// inputs and one registration more, approved one block past its lifetime. The
// kernel refuses it as `APPROVAL_LIFETIME_EXCEEDED`, result `49`, and the
// application must answer `305` with a version-ten receipt carrying `49`.
//
// It signs under a table of its own, because the trace's table holds only the
// run's signatures. The run's bytes are unchanged, because a table issues its
// tokens in the order it is asked, and that is checked rather than assumed. The
// root is the kernel's for the same block, since no vector records this one.
void check_the_top_of_the_range(const pv::Values& values,
                                const std::filesystem::path& directory) {
  fixture::Signatures signatures;
  const auto run = fixture::restart_scenario(signatures);
  pv::require(run.block_inputs[0] == restart_run().block_inputs[0],
              "a table of its own signs the run's first block identically");
  const auto genesis = fixture::trace_genesis();
  const auto height = block_height(values, 0);
  const auto stamp = block_timestamp(values, 0);
  auto inputs = run.block_inputs[0];
  {
    const auto ledger = fixture::open_trace_ledger();
    const fixture::Builder build(signatures, ledger);
    inputs.push_back(build.registration(fixture::person(7), v10::kLaunchAttester,
                                        fixture::kLaunchKey,
                                        height + fixture::kLifetime + 1));
  }
  auto expected = fixture::open_trace_ledger();
  const auto executed =
      v10::execute_block(expected, stamp, inputs, signatures.verifier());
  pv::require(executed.has_value(), "the kernel executes the widened block");

  CountingClock clock;
  auto store = require_store(
      ps::create_sqlite_ledger_v10(directory / "range.db", genesis,
                                   signatures.verifier()),
      "creating the range store");
  auto made = pa::make_application_v10(std::move(store), clock.source());
  pv::require(std::holds_alternative<pa::ApplicationV10>(made.result),
              "the range application did not open");
  auto application = std::get<pa::ApplicationV10>(std::move(made.result));
  require_value<pa::InitChainResultV10, v10::Hash>(
      application.init_chain(trace_chain_id(), 1, fixture::kGenesisMillis,
                             kAppStateV10),
      "init_chain");
  *clock.now = stamp;
  require_decision(application.process_proposal(height, stamp, inputs),
                   pa::ProposalDecisionV10::accepted,
                   "a block carrying one refusable registration");
  auto finalized = require_finalized(
      application.finalize_block(height, stamp, inputs), "the widened finalize");
  pv::require(finalized.state_root == executed->resulting_state_root,
              "the widened block's root is not the kernel's");
  pv::require(finalized.transaction_results.size() == 3,
              "one result per raw input in the widened block");
  for (std::size_t input = 0; input < 2; ++input) {
    pv::require(finalized.transaction_results[input].code == 0,
                "the run's own registrations still succeed beside the late one");
  }
  const auto& late = finalized.transaction_results[2];
  pv::require(late.code == 305, "a lifetime refusal is not code 305: " +
                                    std::to_string(late.code));
  const auto receipt = v10::decode_receipt(late.data);
  pv::require(receipt.has_value(),
              "code 305 does not carry a version-ten receipt");
  pv::require(receipt->result_code ==
                  static_cast<std::uint8_t>(
                      v10::Result::approval_lifetime_exceeded),
              "the receipt behind code 305 does not carry result 49");
  require_value<pa::CommitResultV10, pa::CommittedHeadV10>(application.commit(),
                                                           "commit");
}

// A deployment that cannot read a clock must fail to start.
void check_a_clockless_deployment_refuses(
    const std::filesystem::path& directory) {
  const auto path = directory / "clockless.db";
  const auto genesis = fixture::trace_genesis();
  auto store = require_store(
      ps::create_sqlite_ledger_v10(path, genesis, trace_verifier()),
      "creating the clockless store");
  auto made = pa::make_application_v10(std::move(store), pa::ClockSourceV10{});
  pv::require(std::holds_alternative<pa::ApplicationError>(made.result),
              "an application without a clock started");
  pv::require(std::get<pa::ApplicationError>(made.result) ==
                  pa::ApplicationError::invalid_request,
              "a clockless deployment refused for the wrong reason");
}

}  // namespace

int main(int argc, char** argv) {
  try {
    pv::require(argc == 3, "usage: application_v10_tests VECTORS DIR");
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
    check_the_top_of_the_range(values, directory);
    check_a_clockless_deployment_refuses(directory);

    std::filesystem::remove_all(directory);
    std::cout << "C++ version-ten application: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "C++ version-ten application: failed: " << error.what() << '\n';
    return 1;
  }
}
