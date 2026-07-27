#pragma once

#include "protocol/v1/types.hpp"

#include <cstddef>
#include <cstdint>
#include <span>
#include <variant>
#include <vector>

namespace protocol::application {

inline constexpr std::size_t kWireHeaderSize = 20;
inline constexpr std::size_t kMaximumWirePayload = 33'554'432;

enum class WireDirection : std::uint8_t {
  request = 0,
  response = 1,
};

enum class MessageKind : std::uint8_t {
  info = 1,
  init_chain = 2,
  check_transaction = 3,
  prepare_proposal = 4,
  process_proposal = 5,
  finalize_block = 6,
  commit = 7,
};

enum class WireError : std::uint8_t {
  invalid_frame = 1,
  unsupported_version = 2,
  invalid_direction = 3,
  unknown_kind = 4,
  invalid_request_id = 5,
  resource_limit = 6,
  invalid_payload = 7,
};

struct FrameHeader {
  WireDirection direction;
  MessageKind kind;
  std::uint64_t request_id;
  std::uint32_t payload_size;

  bool operator==(const FrameHeader&) const = default;
};

struct Frame {
  FrameHeader header;
  protocol::v1::Bytes payload;

  bool operator==(const Frame&) const = default;
};

struct EmptyRequest {
  bool operator==(const EmptyRequest&) const = default;
};

struct InitChainRequest {
  protocol::v1::ChainId chain_id;
  std::uint64_t initial_height;
  protocol::v1::Bytes app_state;

  bool operator==(const InitChainRequest&) const = default;
};

struct CheckTransactionRequest {
  protocol::v1::Bytes transaction;

  bool operator==(const CheckTransactionRequest&) const = default;
};

struct PrepareProposalRequest {
  std::int64_t maximum_transaction_bytes;
  std::vector<protocol::v1::Bytes> transactions;

  bool operator==(const PrepareProposalRequest&) const = default;
};

struct BlockRequest {
  std::uint64_t height;
  std::vector<protocol::v1::Bytes> transactions;

  bool operator==(const BlockRequest&) const = default;
};

using RequestPayload = std::variant<
    EmptyRequest,
    InitChainRequest,
    CheckTransactionRequest,
    PrepareProposalRequest,
    BlockRequest>;

struct DecodedRequest {
  MessageKind kind;
  std::uint64_t request_id;
  RequestPayload payload;

  bool operator==(const DecodedRequest&) const = default;
};

using HeaderResult = std::variant<FrameHeader, WireError>;
using FrameResult = std::variant<Frame, WireError>;
using RequestResult = std::variant<DecodedRequest, WireError>;
using EncodedFrameResult =
    std::variant<protocol::v1::Bytes, WireError>;

HeaderResult decode_frame_header(
    std::span<const std::uint8_t> header) noexcept;
FrameResult decode_frame(std::span<const std::uint8_t> bytes);
RequestResult decode_request_frame(
    std::span<const std::uint8_t> bytes);
EncodedFrameResult encode_frame(const Frame& frame);

}  // namespace protocol::application
