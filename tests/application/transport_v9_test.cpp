// The version-nine transport: version-two request frames in, version-two
// response frames out.
//
// **It is checked against bytes rather than against objects**, which is version
// eight's rule: every request is built as the octets an adapter would send,
// decoded by `wire_v2`, dispatched, and the response taken apart from its own
// octets, so what is verified is what a Go adapter will actually read.
//
// What version nine adds is a clock and a timestamp, and the questions worth
// asking of a transport about them are narrow:
//
//   - does the stamp reach the application from the frame and come back out of
//     it, in the three responses that report the durable head;
//   - does a decision arrive as its own byte under status zero, and a statement
//     about this machine as a status rather than a decision;
//   - do statuses `7` and `8` arrive on kind 6 and nowhere else; and
//   - does any frame but a proposal reach the bound clock, counted over the wire.
//
// **Two decisions cannot arrive over the wire, and each absence is measured
// rather than skipped.** `NOT_EXECUTABLE` guards chain-state failures no peer can
// induce by choosing bytes, which `application_v9_test.cpp` establishes.
// `RESOURCE_BOUND` guards three bounds the frame decoder enforces first, so the
// frame carrying such a proposal is refused before it is dispatched; the case
// below builds those frames and requires the refusal. Both bytes are proved by
// the encoder on its own.

#include "protocol/application/dispatcher_v9.hpp"
#include "protocol/application/response_v9.hpp"
#include "protocol/application/wire_v2.hpp"

#include "transport_v9_support.hpp"

#include <array>
#include <cstdint>
#include <filesystem>
#include <iostream>
#include <span>
#include <string>
#include <utility>
#include <variant>
#include <vector>

namespace {

using namespace transport_v9_tests;

// The octets of a finalize response, and the checks every one of them owes: the
// recorded root and block identifier, one result per raw input, and a
// version-nine receipt behind every admitted input whose own result byte
// produces the code beside it.
Bytes require_finalized_block(const Response& response, const pv::Values& values,
                              std::size_t index, const std::string& label) {
  Reader reader(response.body);
  pv::require(fixture::hex(reader.hash()) ==
                  recorded(values, label + ".resulting_state_root"),
              label + ": the framed root is not the recorded one");
  pv::require(fixture::hex(reader.hash()) == recorded(values, label + ".block_id"),
              label + ": the framed block identifier is not the recorded one");
  const auto count = reader.u32();
  pv::require(count == restart_run().block_inputs[index].size(),
              label + ": the framed response has one result per raw input");
  for (std::uint32_t result = 0; result < count; ++result) {
    const auto code = reader.u32();
    const auto receipt = reader.blob();
    if (code >= 1 && code <= 3) {
      pv::require(receipt.empty(), label + ": a refused admission carried a receipt");
      continue;
    }
    const auto decoded = v9::decode_receipt(receipt);
    pv::require(decoded.has_value(),
                label + ": an admitted input's receipt does not decode as version nine's");
    pv::require(code == pa::application_code(
                            static_cast<v9::Result>(decoded->result_code)),
                label + ": the framed code is not the receipt's own");
  }
  reader.require_finished(label + ": finalize_block");
  return response.body;
}

void require_head(const Bytes& body, std::uint64_t height, std::uint64_t timestamp,
                  const std::string& root, bool with_version,
                  const std::string& subject) {
  Reader reader(body);
  if (with_version) {
    pv::require(reader.u64() == 9, subject + ": the framed protocol version is not 9");
  }
  pv::require(reader.u64() == height, subject + ": the framed height is wrong");
  pv::require(reader.u64() == timestamp, subject + ": the framed stamp is wrong");
  pv::require(fixture::hex(reader.hash()) == root,
              subject + ": the framed root is not the recorded one");
  reader.require_finished(subject);
}

// Every block, over the wire, against the vectors — with the clock counted.
void check_pipeline(const pv::Values& values, const std::filesystem::path& directory) {
  CountingClock clock;
  auto application = open_application(directory / "transport.db", true, clock);
  std::uint64_t id = 1;

  auto init = require_ok(application, pa::MessageKind::init_chain, id++,
                         init_chain_payload(fixture::kGenesisMillis), "init_chain");
  Reader init_reader(init.body);
  const auto genesis_root = fixture::hex(init_reader.hash());
  init_reader.require_finished("init_chain");
  require_head(require_ok(application, pa::MessageKind::info, id++, {}, "info").body,
               0, fixture::kGenesisMillis, genesis_root, true, "info at genesis");

  for (std::size_t index = 0; index < kContiguousBlocks; ++index) {
    const auto label = block_label(index);
    const auto height = recorded_number(values, label + ".height");
    const auto stamp = recorded_number(values, label + ".timestamp");
    const auto root = recorded(values, label + ".resulting_state_root");
    const auto& inputs = restart_run().block_inputs[index];
    *clock.now = stamp;
    const auto before = clock.reads->load();

    require_decision(application, id++, block_payload(height, stamp, inputs),
                     pa::ProposalDecision::accepted, label + ": proposal");
    // A proposal this chain cannot take must come back as a vote against —
    // status zero, its own byte — rather than as an error. Without this the
    // dispatcher could ignore what the application answered.
    require_decision(application, id++, block_payload(height + 1, stamp, inputs),
                     pa::ProposalDecision::height_not_next, label + ": ahead");
    pv::require(clock.reads->load() == before + 2,
                label + ": each decided proposal frame reads the clock once");
    const auto after_proposals = clock.reads->load();

    const auto finalize_payload = block_payload(height, stamp, inputs);
    const auto body = require_finalized_block(
        require_ok(application, pa::MessageKind::finalize_block, id++,
                   finalize_payload, label + ": finalize"),
        values, index, label);
    // A byte-identical request is owed a byte-identical answer, and the stamp is
    // part of what makes the request identical.
    pv::require(require_ok(application, pa::MessageKind::finalize_block, id++,
                           finalize_payload, label + ": finalize again")
                        .body == body,
                label + ": the repeated finalize answered different octets");
    // A proposal while a block is staged describes this machine, not the
    // proposal: a status, not a decision, and no clock is read to say so.
    require_status(application, pa::MessageKind::process_proposal, id++,
                   block_payload(height + 1, stamp, inputs), 3,
                   label + ": a proposal while staged");

    require_head(require_ok(application, pa::MessageKind::commit, id++, {},
                            label + ": commit").body,
                 height, stamp, root, false, label + ": commit");
    require_head(require_ok(application, pa::MessageKind::info, id++, {},
                            label + ": info").body,
                 height, stamp, root, true, label + ": info");
    pv::require(clock.reads->load() == after_proposals,
                label + ": a frame other than a decided proposal read the clock");
  }
}

// The mempool and proposal-building halves, whose payloads version two did not
// change and whose dispatch is nonetheless new code.
void check_read_only_operations(const std::filesystem::path& directory) {
  CountingClock clock;
  auto application = open_application(directory / "read-only.db", true, clock);
  std::uint64_t id = 1;
  const auto& inputs = restart_run().block_inputs[0];

  require_status(application, pa::MessageKind::check_transaction, id++,
                 transaction_payload(inputs.front()), 3,
                 "check_transaction before init_chain");
  (void)require_ok(application, pa::MessageKind::init_chain, id++,
                   init_chain_payload(fixture::kGenesisMillis), "init_chain");

  Reader admitted(require_ok(application, pa::MessageKind::check_transaction, id++,
                             transaction_payload(inputs.front()),
                             "check_transaction").body);
  pv::require(admitted.u32() == 0, "a recorded transaction is admitted over the wire");
  admitted.require_finished("check_transaction");

  Reader refused(require_ok(application, pa::MessageKind::check_transaction, id++,
                            transaction_payload(Bytes(8, 0x00)),
                            "check_transaction rubbish").body);
  pv::require(refused.u32() == pa::application_code(
                                   v9::AdmissionError::malformed_transaction),
              "rubbish is refused as malformed over the wire");
  refused.require_finished("check_transaction rubbish");

  Bytes prepare;
  append_u64(prepare, 1'000'000);
  append_transactions(prepare, inputs);
  Reader prepared(require_ok(application, pa::MessageKind::prepare_proposal, id++,
                             prepare, "prepare_proposal").body);
  const auto count = prepared.u32();
  pv::require(count == inputs.size(), "a proposal within budget is what arrived");
  for (std::uint32_t index = 0; index < count; ++index) {
    pv::require(prepared.blob() == inputs[index],
                "a prepared proposal keeps the order it was handed");
  }
  prepared.require_finished("prepare_proposal");
  pv::require(clock.reads->load() == 0, "a read-only frame read the clock");
}

// Decisions `0` through `5` from the application, each on its own, each read as
// a byte under status zero — and `6` refused before it could be asked.
void check_decisions(const pv::Values& values, const std::filesystem::path& directory) {
  CountingClock clock;
  auto application = open_application(directory / "decisions.db", true, clock);
  std::uint64_t id = 1;
  (void)require_ok(application, pa::MessageKind::init_chain, id++,
                   init_chain_payload(fixture::kGenesisMillis), "init_chain");
  const auto height = recorded_number(values, block_label(0) + ".height");
  const auto stamp = recorded_number(values, block_label(0) + ".timestamp");
  const auto& inputs = restart_run().block_inputs[0];
  const auto propose = [&](std::uint64_t at, std::uint64_t when,
                           pa::ProposalDecision expected, const std::string& name) {
    require_decision(application, id++, block_payload(at, when, inputs), expected,
                     name);
  };

  *clock.now = stamp;
  propose(height, stamp, pa::ProposalDecision::accepted, "decision 0");
  propose(height + 1, stamp, pa::ProposalDecision::height_not_next, "decision 1");
  propose(height, v9::kMaxTimestampMillis + 1,
          pa::ProposalDecision::timestamp_range, "decision 2");
  propose(height, fixture::kGenesisMillis - 1,
          pa::ProposalDecision::timestamp_not_monotonic, "decision 3");
  *clock.now = stamp - v9::kTimestampToleranceMillis - 1;
  propose(height, stamp, pa::ProposalDecision::timestamp_ahead_of_tolerance,
          "decision 4");
  *clock.now = stamp + v9::kTimestampToleranceMillis + 1;
  propose(height, stamp, pa::ProposalDecision::timestamp_behind_tolerance,
          "decision 5");

  // **`RESOURCE_BOUND` over the wire, measured as an absence.** The decoder
  // enforces the raw count, the input length, and the checked total before any
  // dispatch, so the frame is refused as a resource limit and the application is
  // never asked. The count case is a header alone: the decoder must refuse it
  // before it reads, let alone allocates, a single input.
  const auto reads = clock.reads->load();
  Bytes too_many;
  append_u64(too_many, height);
  append_u64(too_many, stamp);
  append_u32(too_many, static_cast<std::uint32_t>(pa::kMaximumBlockInputsV2 + 1));
  Bytes too_long;
  append_u64(too_long, height);
  append_u64(too_long, stamp);
  append_u32(too_long, 1);
  append_u32(too_long, static_cast<std::uint32_t>(pa::kMaximumTransactionBytes + 1));
  for (const auto& payload : {too_many, too_long}) {
    const auto decoded = pa::decode_request_frame_v2(
        request_frame(pa::MessageKind::process_proposal, id++, payload));
    pv::require(std::holds_alternative<pa::WireError>(decoded) &&
                    std::get<pa::WireError>(decoded) == pa::WireError::resource_limit,
                "a proposal over a block bound reached the dispatcher");
  }
  pv::require(clock.reads->load() == reads, "a refused frame reached the clock");
}

// Statuses from the application: `1` and `3` for any kind, `7` and `8` on kind 6.
// Each fatal case gets its own application, because each one latches.
void check_statuses(const pv::Values& values, const std::filesystem::path& directory) {
  const auto height = recorded_number(values, block_label(0) + ".height");
  const auto& inputs = restart_run().block_inputs[0];
  {
    CountingClock clock;
    auto application = open_application(directory / "status-3.db", true, clock);
    require_status(application, pa::MessageKind::commit, 1, {}, 3,
                   "commit before init_chain");
  }
  {
    CountingClock clock;
    auto application = open_application(directory / "status-1.db", true, clock);
    require_status(application, pa::MessageKind::init_chain, 1,
                   init_chain_payload(fixture::kGenesisMillis + 1), 1,
                   "init_chain with a genesis stamp that is not this chain's");
  }
  const std::array<std::pair<std::uint64_t, std::uint16_t>, 2> fatal{{
      {v9::kMaxTimestampMillis + 1, 7},
      {fixture::kGenesisMillis - 1, 8},
  }};
  for (const auto& [stamp, status] : fatal) {
    const auto name = "a decided block answering status " + std::to_string(status);
    CountingClock clock;
    auto application = open_application(
        directory / ("status-" + std::to_string(status) + ".db"), true, clock);
    (void)require_ok(application, pa::MessageKind::init_chain, 1,
                     init_chain_payload(fixture::kGenesisMillis), name);
    require_status(application, pa::MessageKind::finalize_block, 2,
                   block_payload(height, stamp, inputs), status, name);
    require_status(application, pa::MessageKind::info, 3, {}, 3,
                   name + ": the application continued");
    pv::require(clock.reads->load() == 0, name + ": a fatal finalize read the clock");
  }
}

// **A replay must be given the same stamp, and then it answers the same
// octets.** A finalize at the staged height with a different stamp is a
// different request and is refused; after a restart the height replays from the
// file with its own stamp and the whole finalize body is byte-identical.
void check_replay(const pv::Values& values, const std::filesystem::path& directory) {
  const auto path = directory / "replay.db";
  const auto height = recorded_number(values, block_label(0) + ".height");
  const auto stamp = recorded_number(values, block_label(0) + ".timestamp");
  const auto payload = block_payload(height, stamp, restart_run().block_inputs[0]);
  CountingClock clock;
  Bytes first;
  {
    auto application = open_application(path, true, clock);
    (void)require_ok(application, pa::MessageKind::init_chain, 1,
                     init_chain_payload(fixture::kGenesisMillis), "init_chain");
    first = require_finalized_block(
        require_ok(application, pa::MessageKind::finalize_block, 2, payload,
                   "the first finalize"),
        values, 0, block_label(0));
    require_status(application, pa::MessageKind::finalize_block, 3,
                   block_payload(height, stamp + 1, restart_run().block_inputs[0]),
                   3, "a finalize at the staged height with a fresh stamp");
  }
  auto application = open_application(path, false, clock);
  (void)require_ok(application, pa::MessageKind::init_chain, 1,
                   init_chain_payload(fixture::kGenesisMillis),
                   "init_chain after the interrupted finalize");
  pv::require(require_ok(application, pa::MessageKind::finalize_block, 2, payload,
                         "the replayed finalize").body == first,
              "the replayed finalize answered different octets");
  require_head(require_ok(application, pa::MessageKind::commit, 3, {},
                          "commit the replay").body,
               height, stamp, recorded(values, block_label(0) + ".resulting_state_root"),
               false, "commit the replay");
}

}  // namespace

int main(int argc, char** argv) {
  try {
    pv::require(argc == 3, "usage: application_transport_v9_tests VECTORS DIR");
    pv::require(sodium_init() >= 0, "libsodium initialization");
    const auto values = pv::load_values(argv[1]);
    const std::filesystem::path directory(argv[2]);
    std::filesystem::remove_all(directory);
    std::filesystem::create_directories(directory);

    check_pipeline(values, directory);
    check_read_only_operations(directory);
    check_decisions(values, directory);
    check_statuses(values, directory);
    check_replay(values, directory);
    check_encoder();
    check_over_a_socket(values, directory);
    std::filesystem::remove_all(directory);

    std::cout << "C++ version-nine transport: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "C++ version-nine transport: failed: " << error.what() << '\n';
    return 1;
  }
}
