#include "protocol/application/application_v1.hpp"
#include "protocol/application/wire_v1.hpp"

#include "../../tools/protocol-vectors/vector_common.hpp"

#include <algorithm>
#include <bit>
#include <cstddef>
#include <cstdint>
#include <exception>
#include <iostream>
#include <span>
#include <string_view>
#include <utility>
#include <variant>
#include <vector>

namespace pa = protocol::application;
namespace p = protocol::v1;
namespace pv = protocol_vectors;

namespace {

void append_u32(p::Bytes& bytes, std::uint32_t value) {
  for (int shift = 24; shift >= 0; shift -= 8) {
    bytes.push_back(static_cast<std::uint8_t>(value >> shift));
  }
}

void append_u64(p::Bytes& bytes, std::uint64_t value) {
  pv::append_u64(bytes, value);
}

void append_blob(p::Bytes& bytes, const p::Bytes& value) {
  append_u32(bytes, static_cast<std::uint32_t>(value.size()));
  bytes.insert(bytes.end(), value.begin(), value.end());
}

void append_transactions(
    p::Bytes& bytes,
    const std::vector<p::Bytes>& transactions) {
  append_u32(
      bytes, static_cast<std::uint32_t>(transactions.size()));
  for (const auto& transaction : transactions) {
    append_blob(bytes, transaction);
  }
}

p::Bytes frame_bytes(
    pa::MessageKind kind,
    std::uint64_t request_id,
    p::Bytes payload = {},
    pa::WireDirection direction = pa::WireDirection::request) {
  const pa::Frame frame{
      pa::FrameHeader{
          direction, kind, request_id,
          static_cast<std::uint32_t>(payload.size())},
      std::move(payload),
  };
  auto encoded = pa::encode_frame(frame);
  pv::require(
      std::holds_alternative<p::Bytes>(encoded), "encode frame");
  return std::get<p::Bytes>(std::move(encoded));
}

template <typename Expected, typename Result>
Expected take(Result result, std::string_view message) {
  pv::require(std::holds_alternative<Expected>(result), message);
  return std::get<Expected>(std::move(result));
}

template <typename Result>
void require_error(
    Result result,
    pa::WireError expected,
    std::string_view message) {
  pv::require(
      std::holds_alternative<pa::WireError>(result) &&
          std::get<pa::WireError>(result) == expected,
      message);
}

void verify_header_and_frame() {
  const p::Bytes expected{
      'P', 'S', 'A', 'P', 0, 1, 0, 1,
      0,   0,   0,   0,   0, 0, 0, 1,
      0,   0,   0,   0,
  };
  const auto encoded = frame_bytes(pa::MessageKind::info, 1);
  pv::require(encoded == expected, "frozen Info frame bytes");
  pv::require(
      take<pa::FrameHeader>(
          pa::decode_frame_header(encoded), "decode header") ==
          pa::FrameHeader{
              pa::WireDirection::request, pa::MessageKind::info, 1, 0},
      "decoded header fields");
  pv::require(
      take<pa::Frame>(pa::decode_frame(encoded), "decode frame") ==
          pa::Frame{
              pa::FrameHeader{
                  pa::WireDirection::request,
                  pa::MessageKind::info, 1, 0},
              {}},
      "decoded frame fields");
}

void verify_request_payloads() {
  {
    const auto request = take<pa::DecodedRequest>(
        pa::decode_request_frame(
            frame_bytes(pa::MessageKind::commit, 7)),
        "decode Commit");
    pv::require(
        request.kind == pa::MessageKind::commit &&
            request.request_id == 7 &&
            std::holds_alternative<pa::EmptyRequest>(request.payload),
        "Commit request fields");
  }
  {
    p::Hash raw_chain{};
    for (std::size_t index = 0; index < raw_chain.size(); ++index) {
      raw_chain[index] = static_cast<std::uint8_t>(index);
    }
    const p::Bytes app_state{'"', 'v', '1', '"'};
    p::Bytes payload(raw_chain.begin(), raw_chain.end());
    append_u64(payload, 1);
    append_blob(payload, app_state);
    const auto request = take<pa::DecodedRequest>(
        pa::decode_request_frame(
            frame_bytes(pa::MessageKind::init_chain, 9, payload)),
        "decode InitChain");
    pv::require(
        std::get<pa::InitChainRequest>(request.payload) ==
            pa::InitChainRequest{p::ChainId{raw_chain}, 1, app_state},
        "InitChain payload");
  }
  {
    const p::Bytes transaction{1, 2, 3};
    p::Bytes payload;
    append_blob(payload, transaction);
    const auto request = take<pa::DecodedRequest>(
        pa::decode_request_frame(frame_bytes(
            pa::MessageKind::check_transaction, 10, payload)),
        "decode CheckTx");
    pv::require(
        std::get<pa::CheckTransactionRequest>(request.payload) ==
            pa::CheckTransactionRequest{transaction},
        "CheckTx payload");
  }
  {
    const std::vector<p::Bytes> transactions{{1}, {2, 3}};
    p::Bytes payload;
    append_u64(
        payload, std::bit_cast<std::uint64_t>(
                     static_cast<std::int64_t>(400)));
    append_transactions(payload, transactions);
    const auto request = take<pa::DecodedRequest>(
        pa::decode_request_frame(frame_bytes(
            pa::MessageKind::prepare_proposal, 11, payload)),
        "decode PrepareProposal");
    pv::require(
        std::get<pa::PrepareProposalRequest>(request.payload) ==
            pa::PrepareProposalRequest{400, transactions},
        "PrepareProposal payload");
  }
  for (const auto kind : {
           pa::MessageKind::process_proposal,
           pa::MessageKind::finalize_block}) {
    const std::vector<p::Bytes> transactions{{4, 5}, {}};
    p::Bytes payload;
    append_u64(payload, 3);
    append_transactions(payload, transactions);
    const auto request = take<pa::DecodedRequest>(
        pa::decode_request_frame(frame_bytes(kind, 12, payload)),
        "decode block request");
    pv::require(
        std::get<pa::BlockRequest>(request.payload) ==
            pa::BlockRequest{3, transactions},
        "block request payload");
  }
}

void verify_frame_rejections() {
  const auto valid = frame_bytes(pa::MessageKind::info, 1);
  for (std::size_t size = 0; size < valid.size(); ++size) {
    require_error(
        pa::decode_request_frame(
            std::span<const std::uint8_t>(valid).first(size)),
        pa::WireError::invalid_frame, "truncated frame accepted");
  }

  auto trailing = valid;
  trailing.push_back(0);
  require_error(
      pa::decode_request_frame(trailing), pa::WireError::invalid_frame,
      "trailing frame byte accepted");
  auto magic = valid;
  magic[0] ^= 1U;
  require_error(
      pa::decode_request_frame(magic), pa::WireError::invalid_frame,
      "wrong magic accepted");
  auto version = valid;
  version[5] = 2;
  require_error(
      pa::decode_request_frame(version),
      pa::WireError::unsupported_version, "wrong version accepted");
  auto direction = valid;
  direction[6] = 2;
  require_error(
      pa::decode_request_frame(direction),
      pa::WireError::invalid_direction, "unknown direction accepted");
  auto response = valid;
  response[6] = 1;
  require_error(
      pa::decode_request_frame(response),
      pa::WireError::invalid_direction, "response accepted as request");
  auto kind = valid;
  kind[7] = 8;
  require_error(
      pa::decode_request_frame(kind), pa::WireError::unknown_kind,
      "unknown kind accepted");
  auto identifier = valid;
  std::fill(identifier.begin() + 8, identifier.begin() + 16, 0);
  require_error(
      pa::decode_request_frame(identifier),
      pa::WireError::invalid_request_id, "zero request ID accepted");
  auto payload_limit = valid;
  payload_limit[16] = 2;
  payload_limit[17] = 0;
  payload_limit[18] = 0;
  payload_limit[19] = 1;
  require_error(
      pa::decode_frame_header(payload_limit),
      pa::WireError::resource_limit, "oversized payload accepted");
}

void verify_payload_rejections() {
  {
    p::Bytes payload;
    append_u32(
        payload,
        static_cast<std::uint32_t>(
            pa::kMaximumTransactionBytes + 1));
    require_error(
        pa::decode_request_frame(frame_bytes(
            pa::MessageKind::check_transaction, 1, payload)),
        pa::WireError::resource_limit, "oversized transaction accepted");
  }
  {
    p::Bytes payload;
    append_u64(payload, 1);
    append_u32(
        payload,
        static_cast<std::uint32_t>(
            pa::kMaximumBlockInputs + 1));
    require_error(
        pa::decode_request_frame(frame_bytes(
            pa::MessageKind::finalize_block, 1, payload)),
        pa::WireError::resource_limit, "hostile count accepted");
  }
  {
    auto payload = p::Bytes(32);
    append_u64(payload, 1);
    append_u32(payload, 4'097);
    require_error(
        pa::decode_request_frame(frame_bytes(
            pa::MessageKind::init_chain, 1, payload)),
        pa::WireError::resource_limit, "oversized app state accepted");
  }
  {
    auto nonempty = frame_bytes(pa::MessageKind::info, 1, {0});
    require_error(
        pa::decode_request_frame(nonempty),
        pa::WireError::invalid_payload, "nonempty Info accepted");
  }
  {
    p::Bytes payload;
    append_u64(payload, 1);
    append_u32(payload, 1);
    append_u32(payload, 3);
    payload.push_back(1);
    require_error(
        pa::decode_request_frame(frame_bytes(
            pa::MessageKind::process_proposal, 1, payload)),
        pa::WireError::invalid_payload, "truncated blob accepted");
  }
}

}  // namespace

int main() {
  try {
    verify_header_and_frame();
    verify_request_payloads();
    verify_frame_rejections();
    verify_payload_rejections();
    std::cout << "Application wire v1 tests: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "Application wire v1 tests: failed: "
              << error.what() << '\n';
    return 1;
  }
}
