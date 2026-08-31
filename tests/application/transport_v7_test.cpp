// The version-seven transport: request frames in, response frames out.
//
// **This is the last layer before the socket, and it is checked against bytes
// rather than against objects.** Every request is built as the octets an adapter
// would send, decoded by the shared version-one wire, dispatched, and the
// response taken apart from its own octets — so what is verified is the thing a
// Go adapter will actually read.
//
// The `carried` scenario's four contiguous blocks are driven through the whole
// frame pipeline and every block must reproduce its **recorded**
// `resulting_state_root` and `block_id`, read back out of the response payload.

#include "protocol/application/dispatcher_v7.hpp"
#include "protocol/application/response_v7.hpp"
#include "protocol/application/wire_v1.hpp"

#include "../storage/sqlite_ledger_v7_fixture.hpp"

#include "protocol/application/unix_server_v1.hpp"

#include <algorithm>
#include <array>
#include <cerrno>
#include <cstdint>
#include <cstring>
#include <exception>
#include <filesystem>
#include <iostream>
#include <span>
#include <string>
#include <sys/socket.h>
#include <sys/un.h>
#include <thread>
#include <unistd.h>
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
using Bytes = v7::Bytes;

constexpr std::uint8_t kAppStateV7[] = {
    '"', 'p', 'r', 'o', 't', 'o', 'c', 'o', 'l', '-',
    's', 't', 'a', 'c', 'k', '-', 'v', '7', '"',
};
constexpr std::array<std::uint8_t, 4> kMagic{'P', 'S', 'A', 'P'};
constexpr std::size_t kHeaderSize = 20;
constexpr std::size_t kStatusSize = 6;

void append_u16(Bytes& output, std::uint16_t value) {
  output.push_back(static_cast<std::uint8_t>(value >> 8U));
  output.push_back(static_cast<std::uint8_t>(value));
}

void append_u32(Bytes& output, std::uint32_t value) {
  for (int shift = 24; shift >= 0; shift -= 8) {
    output.push_back(static_cast<std::uint8_t>(value >> shift));
  }
}

void append_u64(Bytes& output, std::uint64_t value) {
  for (int shift = 56; shift >= 0; shift -= 8) {
    output.push_back(static_cast<std::uint8_t>(value >> shift));
  }
}

void append_blob(Bytes& output, std::span<const std::uint8_t> bytes) {
  append_u32(output, static_cast<std::uint32_t>(bytes.size()));
  output.insert(output.end(), bytes.begin(), bytes.end());
}

void append_transactions(Bytes& output, std::span<const Bytes> transactions) {
  append_u32(output, static_cast<std::uint32_t>(transactions.size()));
  for (const auto& transaction : transactions) append_blob(output, transaction);
}

// The exact octets an adapter would put on the socket.
Bytes request_frame(pa::MessageKind kind, std::uint64_t request_id,
                    const Bytes& payload) {
  Bytes frame;
  frame.insert(frame.end(), kMagic.begin(), kMagic.end());
  append_u16(frame, 1);
  frame.push_back(static_cast<std::uint8_t>(pa::WireDirection::request));
  frame.push_back(static_cast<std::uint8_t>(kind));
  append_u64(frame, request_id);
  append_u32(frame, static_cast<std::uint32_t>(payload.size()));
  frame.insert(frame.end(), payload.begin(), payload.end());
  return frame;
}

// A reader over a response payload, walking the octets the way an adapter must
// and refusing to finish with anything left over.
class Reader {
 public:
  explicit Reader(std::span<const std::uint8_t> bytes) : bytes_(bytes) {}

  std::uint32_t u32() {
    pv::require(offset_ + 4 <= bytes_.size(), "the payload has four more octets");
    std::uint32_t value = 0;
    for (std::size_t index = 0; index < 4; ++index) {
      value = (value << 8U) | bytes_[offset_ + index];
    }
    offset_ += 4;
    return value;
  }

  std::uint64_t u64() {
    pv::require(offset_ + 8 <= bytes_.size(), "the payload has eight more octets");
    std::uint64_t value = 0;
    for (std::size_t index = 0; index < 8; ++index) {
      value = (value << 8U) | bytes_[offset_ + index];
    }
    offset_ += 8;
    return value;
  }

  std::uint8_t u8() {
    pv::require(offset_ < bytes_.size(), "the payload has one more octet");
    return bytes_[offset_++];
  }

  v7::Octets32 hash() {
    pv::require(offset_ + 32 <= bytes_.size(), "the payload has a hash left");
    v7::Octets32 value{};
    const auto begin = bytes_.begin() + static_cast<std::ptrdiff_t>(offset_);
    std::copy(begin, begin + 32, value.begin());
    offset_ += 32;
    return value;
  }

  Bytes blob() {
    const auto size = u32();
    pv::require(offset_ + size <= bytes_.size(), "the payload has the blob");
    const auto begin = bytes_.begin() + static_cast<std::ptrdiff_t>(offset_);
    Bytes value(begin, begin + static_cast<std::ptrdiff_t>(size));
    offset_ += size;
    return value;
  }

  void require_finished(const std::string& subject) const {
    pv::require(offset_ == bytes_.size(),
                subject + ": the response payload has trailing octets");
  }

 private:
  std::span<const std::uint8_t> bytes_;
  std::size_t offset_ = 0;
};

struct Response {
  std::uint16_t status = 0;
  Bytes body;
};

// Dispatch one request frame **once** and take the response frame apart,
// checking the header an adapter would check: the magic, the wire version, the
// direction, the kind it asked about, the identifier it chose, and a declared
// payload size that matches what actually arrived.
Response exchange(pa::ApplicationV7& application, pa::MessageKind kind,
                  std::uint64_t request_id, const Bytes& payload,
                  const std::string& subject) {
  const auto frame = request_frame(kind, request_id, payload);
  auto decoded = pa::decode_request_frame(frame);
  pv::require(std::holds_alternative<pa::DecodedRequest>(decoded),
              subject + ": the request frame did not decode");
  auto encoded = pa::dispatch_request_v7(
      application, std::get<pa::DecodedRequest>(std::move(decoded)));
  pv::require(std::holds_alternative<Bytes>(encoded),
              subject + ": the response did not encode");
  const auto response = std::get<Bytes>(std::move(encoded));

  pv::require(response.size() >= kHeaderSize + kStatusSize,
              subject + ": the response is shorter than a header and a status");
  pv::require(std::equal(kMagic.begin(), kMagic.end(), response.begin()),
              subject + ": the response carries the wrong magic");
  pv::require(response[4] == 0 && response[5] == 1,
              subject + ": the response carries the wrong wire version");
  pv::require(
      response[6] == static_cast<std::uint8_t>(pa::WireDirection::response),
      subject + ": the response is not marked as one");
  pv::require(response[7] == static_cast<std::uint8_t>(kind),
              subject + ": the response answers a different kind");
  Reader header(std::span<const std::uint8_t>(response).subspan(8, 12));
  pv::require(header.u64() == request_id,
              subject + ": the response answers a different request");
  pv::require(header.u32() == response.size() - kHeaderSize,
              subject + ": the declared payload size is not the payload's");

  const auto payload_bytes =
      std::span<const std::uint8_t>(response).subspan(kHeaderSize);
  Response result;
  result.status =
      static_cast<std::uint16_t>((payload_bytes[0] << 8U) | payload_bytes[1]);
  pv::require(payload_bytes[2] == 0 && payload_bytes[3] == 0 &&
                  payload_bytes[4] == 0 && payload_bytes[5] == 0,
              subject + ": the reserved field is not zero");
  result.body.assign(payload_bytes.begin() + kStatusSize, payload_bytes.end());
  return result;
}

Response require_ok(pa::ApplicationV7& application, pa::MessageKind kind,
                    std::uint64_t request_id, const Bytes& payload,
                    const std::string& subject) {
  auto response = exchange(application, kind, request_id, payload, subject);
  pv::require(response.status == 0,
              subject + ": the application answered status " +
                  std::to_string(response.status));
  return response;
}

Bytes empty_payload() { return Bytes{}; }

Bytes init_chain_payload(const v7::Octets32& chain_id, std::uint64_t height,
                         std::span<const std::uint8_t> app_state) {
  Bytes payload;
  payload.insert(payload.end(), chain_id.begin(), chain_id.end());
  append_u64(payload, height);
  append_blob(payload, app_state);
  return payload;
}

Bytes block_payload(std::uint64_t height, std::span<const Bytes> transactions) {
  Bytes payload;
  append_u64(payload, height);
  append_transactions(payload, transactions);
  return payload;
}

v7::Octets32 trace_chain_id() {
  const auto identity = v7::chain_id(fixture::trace_genesis());
  pv::require(identity.has_value(), "the trace genesis has a chain identity");
  return *identity;
}

pa::ApplicationV7 open_application(const std::filesystem::path& path,
                                   bool create) {
  const auto genesis = fixture::trace_genesis();
  auto store = require_store(
      create ? ps::create_sqlite_ledger_v7(path, genesis, trace_verifier())
             : ps::open_sqlite_ledger_v7(path, genesis, trace_verifier()),
      create ? "creating the store" : "reopening the store");
  auto made = pa::make_application_v7(std::move(store));
  pv::require(std::holds_alternative<pa::ApplicationV7>(made.result),
              "the application did not open");
  return std::get<pa::ApplicationV7>(std::move(made.result));
}

// Every block, over the wire, against the vectors.
void check_pipeline(const pv::Values& values,
                    const std::filesystem::path& directory) {
  const auto& scenario = carried_scenario();
  auto application = open_application(directory / "transport.db", true);
  std::uint64_t request_id = 1;

  auto init = require_ok(application, pa::MessageKind::init_chain, request_id++,
                         init_chain_payload(trace_chain_id(), 1, kAppStateV7),
                         "init_chain");
  Reader init_reader(init.body);
  (void)init_reader.hash();
  init_reader.require_finished("init_chain");

  for (std::size_t index = 0; index < kContiguousBlocks; ++index) {
    const auto height = scenario.blocks[index].height;
    const auto& inputs = scenario.block_inputs[index];
    const auto label = "carried.block" + std::to_string(index);

    auto proposed =
        require_ok(application, pa::MessageKind::process_proposal, request_id++,
                   block_payload(height, inputs), label + ": process_proposal");
    Reader proposal_reader(proposed.body);
    pv::require(proposal_reader.u8() == 1,
                label + ": the proposal was voted against over the wire");
    proposal_reader.require_finished(label + ": process_proposal");

    // A proposal at a height this chain cannot be at must come back as a vote
    // against — status zero, body zero — rather than as an error. Without this
    // the dispatcher could ignore what the application answered and every
    // framed proposal above would still pass.
    auto refused_proposal = require_ok(
        application, pa::MessageKind::process_proposal, request_id++,
        block_payload(height + 1, inputs), label + ": a proposal ahead");
    Reader refused_reader(refused_proposal.body);
    pv::require(refused_reader.u8() == 0,
                label + ": a proposal ahead of the head was not voted against");
    refused_reader.require_finished(label + ": a proposal ahead");

    auto finalized =
        require_ok(application, pa::MessageKind::finalize_block, request_id++,
                   block_payload(height, inputs), label + ": finalize_block");
    Reader finalize_reader(finalized.body);
    const auto root = finalize_reader.hash();
    const auto block_id = finalize_reader.hash();
    pv::require(fixture::hex(root) ==
                    recorded(values, label + ".resulting_state_root"),
                label + ": the framed root is not the recorded one");
    pv::require(fixture::hex(block_id) == recorded(values, label + ".block_id"),
                label + ": the framed block identifier is not the recorded one");
    const auto result_count = finalize_reader.u32();
    pv::require(result_count == scenario.raw_inputs[index],
                label + ": the framed response has one result per raw input");
    for (std::uint32_t result = 0; result < result_count; ++result) {
      const auto code = finalize_reader.u32();
      const auto receipt = finalize_reader.blob();
      // Every admitted input carries a version-seven receipt whose own result
      // byte produces the code beside it. The encoder refuses any other pair,
      // so reading it back here is checking that it wrote what it validated.
      if (code >= 1 && code <= 3) {
        pv::require(receipt.empty(),
                    label + ": a refused admission carried a receipt");
        continue;
      }
      pv::require(receipt.size() == v7::kReceiptBytes,
                  label + ": an admitted input's receipt is the wrong size");
      const auto decoded = v7::decode_receipt(receipt);
      pv::require(decoded.has_value(),
                  label + ": an admitted input's receipt does not decode");
      pv::require(code == pa::application_code(
                              static_cast<v7::Result>(decoded->result_code)),
                  label + ": the framed code is not the receipt's own");
    }
    finalize_reader.require_finished(label + ": finalize_block");

    auto committed = require_ok(application, pa::MessageKind::commit,
                                request_id++, empty_payload(),
                                label + ": commit");
    Reader commit_reader(committed.body);
    pv::require(commit_reader.u64() == height,
                label + ": the framed commit is at the wrong height");
    pv::require(fixture::hex(commit_reader.hash()) ==
                    recorded(values, label + ".resulting_state_root"),
                label + ": the framed commit root is not the recorded one");
    commit_reader.require_finished(label + ": commit");

    auto info = require_ok(application, pa::MessageKind::info, request_id++,
                           empty_payload(), label + ": info");
    Reader info_reader(info.body);
    pv::require(info_reader.u64() == pa::kApplicationProtocolVersionV7,
                label + ": the framed protocol version is wrong");
    pv::require(info_reader.u64() == height,
                label + ": the framed height is wrong");
    pv::require(fixture::hex(info_reader.hash()) ==
                    recorded(values, label + ".resulting_state_root"),
                label + ": the framed info root is not the recorded one");
    info_reader.require_finished(label + ": info");
  }
}

// The mempool and proposal-building halves, which never reach a block.
void check_read_only_operations(const std::filesystem::path& directory) {
  const auto& scenario = carried_scenario();
  auto application = open_application(directory / "read-only.db", true);
  std::uint64_t request_id = 1;
  (void)require_ok(application, pa::MessageKind::init_chain, request_id++,
                   init_chain_payload(trace_chain_id(), 1, kAppStateV7),
                   "init_chain");

  Bytes accepted;
  append_blob(accepted, scenario.block_inputs[0][0]);
  auto admitted = require_ok(application, pa::MessageKind::check_transaction,
                             request_id++, accepted, "check_transaction");
  Reader admitted_reader(admitted.body);
  pv::require(admitted_reader.u32() == 0,
              "a recorded transaction must be admitted over the wire");
  admitted_reader.require_finished("check_transaction");

  Bytes rubbish;
  append_blob(rubbish, Bytes(8, 0x00));
  auto refused = require_ok(application, pa::MessageKind::check_transaction,
                            request_id++, rubbish, "check_transaction rubbish");
  Reader refused_reader(refused.body);
  pv::require(refused_reader.u32() ==
                  pa::application_code(
                      v7::AdmissionError::malformed_transaction),
              "rubbish must be refused as malformed over the wire");
  refused_reader.require_finished("check_transaction rubbish");

  Bytes prepare;
  append_u64(prepare, 1'000'000);
  append_transactions(prepare, scenario.block_inputs[0]);
  auto prepared = require_ok(application, pa::MessageKind::prepare_proposal,
                             request_id++, prepare, "prepare_proposal");
  Reader prepared_reader(prepared.body);
  const auto count = prepared_reader.u32();
  pv::require(count == scenario.block_inputs[0].size(),
              "a proposal within budget must be exactly what arrived");
  for (std::uint32_t index = 0; index < count; ++index) {
    pv::require(prepared_reader.blob() == scenario.block_inputs[0][index],
                "a prepared proposal must keep the order it was handed");
  }
  prepared_reader.require_finished("prepare_proposal");
}

// What the transport must refuse. An application error becomes a status in a
// well-formed response frame; a malformed *frame* never reaches the application
// at all.
void check_transport_refusals(const std::filesystem::path& directory) {
  const auto& scenario = carried_scenario();
  auto application = open_application(directory / "transport-refusals.db", true);

  // Committing before the chain is initialised is a sequence failure, and it
  // comes back as a status rather than as a broken frame.
  auto premature = exchange(application, pa::MessageKind::commit, 1,
                            empty_payload(), "commit before init_chain");
  pv::require(premature.status ==
                  static_cast<std::uint16_t>(
                      pa::ApplicationError::sequence_failure),
              "committing before init_chain must answer sequence_failure");
  pv::require(premature.body.empty(),
              "an error response carries no body");

  // A payload of the wrong shape for its kind is refused as an invalid request
  // by the wire itself, before the application is asked anything.
  auto wrong_shape =
      pa::decode_request_frame(request_frame(pa::MessageKind::commit, 2,
                                             block_payload(1, scenario.block_inputs[0])));
  pv::require(std::holds_alternative<pa::WireError>(wrong_shape),
              "a commit carrying a block payload must not decode");

  // A truncated frame, an unknown kind, and a zero request identifier are the
  // three header refusals an adapter can produce by accident.
  auto truncated = request_frame(pa::MessageKind::info, 3, empty_payload());
  truncated.pop_back();
  pv::require(std::holds_alternative<pa::WireError>(
                  pa::decode_request_frame(truncated)),
              "a truncated frame must not decode");
  auto unknown = request_frame(pa::MessageKind::info, 4, empty_payload());
  unknown[7] = 0;
  pv::require(std::holds_alternative<pa::WireError>(
                  pa::decode_request_frame(unknown)),
              "an unknown kind must not decode");
  auto zero_id = request_frame(pa::MessageKind::info, 0, empty_payload());
  pv::require(std::holds_alternative<pa::WireError>(
                  pa::decode_request_frame(zero_id)),
              "a zero request identifier must not decode");
}

// The encoder is the last place a disagreement between a declared code and its
// receipt can be caught, so it must refuse one rather than write it.
void check_encoder_refusals() {
  pa::FinalizedBlockV7 block;
  block.transaction_results.push_back(
      pa::TransactionResult{pa::application_code(v7::Result::success),
                            Bytes(v7::kReceiptBytes, 0x00)});
  pv::require(
      std::holds_alternative<pa::WireError>(pa::encode_success_response_v7(
          pa::MessageKind::finalize_block, 1, pa::SuccessResponseV7{block})),
      "a receipt without the version-seven prefix must not be written");

  pa::FinalizedBlockV7 mismatched;
  v7::Receipt receipt;
  receipt.kind = 1;
  receipt.result_code = static_cast<std::uint8_t>(v7::Result::unauthorized);
  auto encoded = v7::encode_receipt(receipt);
  pv::require(encoded.has_value(), "the probe receipt encodes");
  mismatched.transaction_results.push_back(pa::TransactionResult{
      pa::application_code(v7::Result::success), *encoded});
  pv::require(
      std::holds_alternative<pa::WireError>(pa::encode_success_response_v7(
          pa::MessageKind::finalize_block, 1,
          pa::SuccessResponseV7{mismatched})),
      "a code that disagrees with its receipt must not be written");

  // A mempool answer carrying a receipt is the same class of disagreement: it
  // would say the application executed something to answer a question about a
  // height nobody proposed.
  pv::require(
      std::holds_alternative<pa::WireError>(pa::encode_success_response_v7(
          pa::MessageKind::check_transaction, 1,
          pa::SuccessResponseV7{pa::TransactionResult{0, Bytes{1, 2, 3}}})),
      "a mempool answer carrying a receipt must not be written");

  // And a response of the wrong type for its kind is refused rather than
  // silently encoded as whatever happens to fit.
  pv::require(
      std::holds_alternative<pa::WireError>(pa::encode_success_response_v7(
          pa::MessageKind::commit, 1, pa::SuccessResponseV7{true})),
      "a response of the wrong type for its kind must not be written");
}

// The same frames over a real socket, which is the only thing that exercises
// the version-seven overload of `serve_connection`. The connection loop itself
// is version one's, shared rather than copied, so what this adds is that the
// decoded request reaches the *version-seven* dispatcher and its answer comes
// back down the same socket.
class ClientSocket {
 public:
  explicit ClientSocket(const std::filesystem::path& path) {
    descriptor_ = ::socket(AF_UNIX, SOCK_STREAM, 0);
    pv::require(descriptor_ >= 0, "the client socket opens");
    sockaddr_un address{};
    address.sun_family = AF_UNIX;
    pv::require(path.native().size() < sizeof(address.sun_path),
                "the socket pathname fits in sun_path");
    std::memcpy(address.sun_path, path.c_str(), path.native().size() + 1);
    pv::require(::connect(descriptor_,
                          reinterpret_cast<const sockaddr*>(&address),
                          sizeof(address)) == 0,
                "the client connects");
  }
  ~ClientSocket() {
    if (descriptor_ >= 0) (void)::close(descriptor_);
  }
  ClientSocket(const ClientSocket&) = delete;
  ClientSocket& operator=(const ClientSocket&) = delete;

  void close_now() {
    if (descriptor_ >= 0) (void)::close(descriptor_);
    descriptor_ = -1;
  }

  void write_all(std::span<const std::uint8_t> bytes) const {
    std::size_t offset = 0;
    while (offset < bytes.size()) {
      const auto count = ::send(descriptor_, bytes.data() + offset,
                                bytes.size() - offset, MSG_NOSIGNAL);
      if (count > 0) {
        offset += static_cast<std::size_t>(count);
        continue;
      }
      if (count < 0 && errno == EINTR) continue;
      pv::require(false, "the client wrote its frame");
    }
  }

  void read_all(std::span<std::uint8_t> bytes) const {
    std::size_t offset = 0;
    while (offset < bytes.size()) {
      const auto count =
          ::recv(descriptor_, bytes.data() + offset, bytes.size() - offset, 0);
      if (count > 0) {
        offset += static_cast<std::size_t>(count);
        continue;
      }
      if (count < 0 && errno == EINTR) continue;
      pv::require(false, "the client read its frame");
    }
  }

  Bytes exchange_frame(const Bytes& request) const {
    write_all(request);
    Bytes header(kHeaderSize);
    read_all(header);
    auto decoded = pa::decode_frame_header(header);
    pv::require(std::holds_alternative<pa::FrameHeader>(decoded),
                "the response header decodes");
    const auto fields = std::get<pa::FrameHeader>(decoded);
    Bytes frame = header;
    frame.resize(kHeaderSize + fields.payload_size);
    read_all(std::span<std::uint8_t>(frame).subspan(kHeaderSize));
    return frame;
  }

 private:
  int descriptor_ = -1;
};

Bytes framed_body(const Bytes& frame, pa::MessageKind kind,
                  std::uint64_t request_id, const std::string& subject) {
  pv::require(frame.size() >= kHeaderSize + kStatusSize,
              subject + ": the framed response is too short");
  pv::require(frame[7] == static_cast<std::uint8_t>(kind),
              subject + ": the framed response answers a different kind");
  auto header = std::span<const std::uint8_t>(frame).subspan(8, 8);
  std::uint64_t answered = 0;
  for (const auto octet : header) answered = (answered << 8U) | octet;
  pv::require(answered == request_id,
              subject + ": the framed response answers a different request");
  const auto payload = std::span<const std::uint8_t>(frame).subspan(kHeaderSize);
  pv::require(payload[0] == 0 && payload[1] == 0,
              subject + ": the framed response carries a status");
  return Bytes(payload.begin() + kStatusSize, payload.end());
}

void check_over_a_socket(const pv::Values& values,
                         const std::filesystem::path& directory) {
  const auto& scenario = carried_scenario();
  auto application = open_application(directory / "socket.db", true);
  const auto socket_path = directory / "s";
  auto made = pa::make_unix_socket_server_v1(socket_path);
  pv::require(std::holds_alternative<pa::UnixSocketServerV1>(made.result),
              "the Unix socket server binds");
  auto server = std::get<pa::UnixSocketServerV1>(std::move(made.result));

  pa::ServeConnectionResult served;
  std::thread worker([&] { served = server.serve_connection(application); });
  // A failure inside the client block must be reported rather than abort the
  // process: an unjoined `std::thread` calls `std::terminate`, and the server
  // returns only once the client's socket is closed — which the destructor does
  // as the exception leaves the block.
  std::exception_ptr failure;
  try {
    ClientSocket client(socket_path);
    auto init = framed_body(
        client.exchange_frame(request_frame(
            pa::MessageKind::init_chain, 1,
            init_chain_payload(trace_chain_id(), 1, kAppStateV7))),
        pa::MessageKind::init_chain, 1, "init_chain over the socket");
    Reader init_reader(init);
    (void)init_reader.hash();
    init_reader.require_finished("init_chain over the socket");

    const auto& inputs = scenario.block_inputs[0];
    auto proposed = framed_body(
        client.exchange_frame(request_frame(pa::MessageKind::process_proposal, 2,
                                            block_payload(1, inputs))),
        pa::MessageKind::process_proposal, 2, "process_proposal over the socket");
    Reader proposal_reader(proposed);
    pv::require(proposal_reader.u8() == 1,
                "the proposal was voted against over the socket");
    proposal_reader.require_finished("process_proposal over the socket");

    auto finalized = framed_body(
        client.exchange_frame(request_frame(pa::MessageKind::finalize_block, 3,
                                            block_payload(1, inputs))),
        pa::MessageKind::finalize_block, 3, "finalize_block over the socket");
    Reader finalize_reader(finalized);
    pv::require(fixture::hex(finalize_reader.hash()) ==
                    recorded(values, "carried.block0.resulting_state_root"),
                "the socket's root is not the recorded one");
    pv::require(fixture::hex(finalize_reader.hash()) ==
                    recorded(values, "carried.block0.block_id"),
                "the socket's block identifier is not the recorded one");

    auto committed = framed_body(
        client.exchange_frame(
            request_frame(pa::MessageKind::commit, 4, empty_payload())),
        pa::MessageKind::commit, 4, "commit over the socket");
    Reader commit_reader(committed);
    pv::require(commit_reader.u64() == 1,
                "the socket's commit is at the wrong height");
    pv::require(fixture::hex(commit_reader.hash()) ==
                    recorded(values, "carried.block0.resulting_state_root"),
                "the socket's commit root is not the recorded one");
    commit_reader.require_finished("commit over the socket");
    client.close_now();
  } catch (...) {
    failure = std::current_exception();
  }
  worker.join();
  if (failure) std::rethrow_exception(failure);
  // A client that closes cleanly ends the connection without an error, which is
  // what an adapter restarting looks like from this side.
  pv::require(std::holds_alternative<std::monostate>(served),
              "a clean disconnect must not be an error");
}

}  // namespace

int main(int argc, char** argv) {
  try {
    pv::require(argc == 3, "usage: application_transport_v7_tests VECTORS DIR");
    pv::require(sodium_init() >= 0, "libsodium initialization");
    const auto values = pv::load_values(argv[1]);
    const std::filesystem::path directory(argv[2]);
    std::filesystem::remove_all(directory);
    std::filesystem::create_directories(directory);

    check_pipeline(values, directory);
    check_over_a_socket(values, directory);
    check_read_only_operations(directory);
    check_transport_refusals(directory);
    check_encoder_refusals();
    std::filesystem::remove_all(directory);

    std::cout << "C++ version-seven transport: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "C++ version-seven transport: failed: " << error.what() << '\n';
    return 1;
  }
}
