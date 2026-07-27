#include "protocol/application/response_v1.hpp"

#include <algorithm>
#include <array>
#include <limits>
#include <span>

namespace protocol::application {
namespace {

using protocol::v1::Bytes;
constexpr std::array<std::uint8_t, 6> kReceiptPrefix{
    'P', 'S', 'R', 'C', 0, 1};

static_assert(
    static_cast<std::uint16_t>(ApplicationError::invalid_request) == 1);
static_assert(
    static_cast<std::uint16_t>(ApplicationError::unsupported) == 2);
static_assert(
    static_cast<std::uint16_t>(ApplicationError::sequence_failure) == 3);
static_assert(
    static_cast<std::uint16_t>(ApplicationError::kernel_failure) == 4);
static_assert(
    static_cast<std::uint16_t>(ApplicationError::storage_failure) == 5);
static_assert(
    static_cast<std::uint16_t>(ApplicationError::internal_failure) == 6);

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

bool append_blob(Bytes& output, std::span<const std::uint8_t> bytes) {
  if (bytes.size() > std::numeric_limits<std::uint32_t>::max()) {
    return false;
  }
  append_u32(output, static_cast<std::uint32_t>(bytes.size()));
  output.insert(output.end(), bytes.begin(), bytes.end());
  return output.size() <= kMaximumWirePayload;
}

bool append_transactions(
    Bytes& output,
    std::span<const Bytes> transactions) {
  if (transactions.size() > kMaximumBlockInputs) return false;
  append_u32(output, static_cast<std::uint32_t>(transactions.size()));
  std::size_t total = 0;
  for (const auto& transaction : transactions) {
    if (transaction.size() > kMaximumTransactionBytes ||
        transaction.size() > kMaximumBlockBytes - total ||
        !append_blob(output, transaction)) {
      return false;
    }
    total += transaction.size();
  }
  return true;
}

template <typename Hash>
void append_hash(Bytes& output, const Hash& hash) {
  output.insert(output.end(), hash.begin(), hash.end());
}

bool append_info(Bytes& output, const ApplicationInfo& info) {
  append_u64(output, info.application_version);
  append_u64(output, info.height);
  append_hash(output, info.state_root);
  return true;
}

bool append_check(Bytes& output, const TransactionResult& result) {
  if (result.code > 3 || !result.data.empty()) return false;
  append_u32(output, result.code);
  return true;
}

bool valid_finalize_result(const TransactionResult& result) {
  if (result.code >= 1 && result.code <= 3) {
    return result.data.empty();
  }
  if (result.data.size() != 47 ||
      !std::equal(
          kReceiptPrefix.begin(), kReceiptPrefix.end(),
          result.data.begin())) {
    return false;
  }
  const auto raw_result = result.data[38];
  if (raw_result >
      static_cast<std::uint8_t>(
          protocol::v1::TransferResult::insufficient_balance)) {
    return false;
  }
  return result.code == application_code(
                            static_cast<protocol::v1::TransferResult>(
                                raw_result));
}

bool append_finalize(Bytes& output, const FinalizedBlock& block) {
  if (block.transaction_results.size() > kMaximumBlockInputs) {
    return false;
  }
  append_hash(output, block.state_root);
  append_u32(
      output,
      static_cast<std::uint32_t>(block.transaction_results.size()));
  for (const auto& result : block.transaction_results) {
    if (!valid_finalize_result(result)) return false;
    append_u32(output, result.code);
    if (!append_blob(output, result.data)) return false;
  }
  return true;
}

bool append_success(
    MessageKind kind,
    const SuccessResponse& response,
    Bytes& output) {
  switch (kind) {
    case MessageKind::info:
      if (const auto* value = std::get_if<ApplicationInfo>(&response)) {
        return append_info(output, *value);
      }
      break;
    case MessageKind::init_chain:
      if (const auto* value =
              std::get_if<protocol::v1::StateRoot>(&response)) {
        append_hash(output, *value);
        return true;
      }
      break;
    case MessageKind::check_transaction:
      if (const auto* value =
              std::get_if<TransactionResult>(&response)) {
        return append_check(output, *value);
      }
      break;
    case MessageKind::prepare_proposal:
      if (const auto* value =
              std::get_if<PreparedProposal>(&response)) {
        return append_transactions(output, value->transactions);
      }
      break;
    case MessageKind::process_proposal:
      if (const auto* value = std::get_if<bool>(&response)) {
        output.push_back(*value ? 1U : 0U);
        return true;
      }
      break;
    case MessageKind::finalize_block:
      if (const auto* value = std::get_if<FinalizedBlock>(&response)) {
        return append_finalize(output, *value);
      }
      break;
    case MessageKind::commit:
      if (const auto* value = std::get_if<CommittedHead>(&response)) {
        append_u64(output, value->height);
        append_hash(output, value->state_root);
        return true;
      }
      break;
  }
  return false;
}

EncodedFrameResult frame_response(
    MessageKind kind,
    std::uint64_t request_id,
    Bytes payload) {
  if (payload.size() > kMaximumWirePayload) {
    return WireError::resource_limit;
  }
  return encode_frame(Frame{
      FrameHeader{
          WireDirection::response,
          kind,
          request_id,
          static_cast<std::uint32_t>(payload.size()),
      },
      std::move(payload),
  });
}

}  // namespace

EncodedFrameResult encode_success_response(
    MessageKind kind,
    std::uint64_t request_id,
    const SuccessResponse& response) {
  Bytes payload;
  payload.reserve(54);
  append_u16(payload, 0);
  append_u32(payload, 0);
  if (!append_success(kind, response, payload)) {
    return WireError::invalid_payload;
  }
  return frame_response(kind, request_id, std::move(payload));
}

EncodedFrameResult encode_error_response(
    MessageKind kind,
    std::uint64_t request_id,
    ApplicationError error) {
  const auto status = static_cast<std::uint16_t>(error);
  if (status == 0 ||
      status > static_cast<std::uint16_t>(
                   ApplicationError::internal_failure)) {
    return WireError::invalid_payload;
  }
  Bytes payload;
  payload.reserve(6);
  append_u16(payload, status);
  append_u32(payload, 0);
  return frame_response(kind, request_id, std::move(payload));
}

}  // namespace protocol::application
