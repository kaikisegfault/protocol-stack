// The version-eight response encoder.
//
// **Every response is validated on the way out, not merely serialised.** A
// receipt whose declared result code and encoded result byte disagree, a check
// result carrying a receipt it should not have, a finalized block with more
// results than the block could have held — each is refused as
// `invalid_payload` rather than written. The adapter on the other side has no
// way to tell a wrong answer from a right one, so the last place a disagreement
// can be caught is here.

#include "protocol/application/response_v8.hpp"

#include <algorithm>
#include <array>
#include <limits>
#include <span>
#include <utility>

namespace protocol::application {
namespace {

namespace v8 = protocol::v8;
using v8::Bytes;

// Version eight's receipt: `PSRC`, the receipt version, the transaction
// identifier, the kind, the result code, the fee, and the issued amount.
//
// **The version octets are derived from `kReceiptVersion` rather than written
// out**, which version seven's encoder does not do. A literal there is a figure
// that moves with the version while looking like framing — and unlike the
// store's column widths it is compared against the kernel's own receipts on
// every finalized block, so a stale value is not a weaker refusal but a
// response that will not encode at all. Deriving it is what makes the
// `static_assert` below cover the prefix rather than stand beside a second copy
// of the same number.
constexpr std::array<std::uint8_t, 6> kReceiptPrefixV8{
    'P', 'S', 'R', 'C',
    static_cast<std::uint8_t>(v8::kReceiptVersion >> 8U),
    static_cast<std::uint8_t>(v8::kReceiptVersion & 0xFFU),
};
constexpr std::size_t kReceiptResultOffsetV8 = 39;

static_assert(v8::kReceiptBytes == 56);
static_assert(v8::kReceiptVersion == 8);
static_assert(static_cast<std::uint16_t>(ApplicationError::invalid_request) == 1);
static_assert(static_cast<std::uint16_t>(ApplicationError::internal_failure) == 6);

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
  if (bytes.size() > std::numeric_limits<std::uint32_t>::max()) return false;
  append_u32(output, static_cast<std::uint32_t>(bytes.size()));
  output.insert(output.end(), bytes.begin(), bytes.end());
  return output.size() <= kMaximumWirePayload;
}

bool append_transactions(Bytes& output, std::span<const Bytes> transactions) {
  if (transactions.size() > kMaximumBlockInputsV8) return false;
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

void append_hash(Bytes& output, const v8::Octets32& hash) {
  output.insert(output.end(), hash.begin(), hash.end());
}

bool append_info(Bytes& output, const ApplicationInfoV8& info) {
  append_u64(output, info.application_version);
  append_u64(output, info.height);
  append_hash(output, info.state_root);
  return true;
}

// A mempool answer is an admission code and nothing else. A receipt here would
// mean the application had executed something to answer a question about a
// height nobody has proposed.
bool append_check(Bytes& output, const TransactionResult& result) {
  if (result.code > 3 || !result.data.empty()) return false;
  append_u32(output, result.code);
  return true;
}

// The declared code and the encoded receipt must be the same fact. A rejected
// admission carries its small code and no receipt; anything else must be a
// version-eight receipt whose own result byte produces exactly the declared
// code.
bool valid_finalize_result(const TransactionResult& result) {
  if (result.code >= 1 && result.code <= 3) return result.data.empty();
  if (result.data.size() != v8::kReceiptBytes ||
      !std::equal(kReceiptPrefixV8.begin(), kReceiptPrefixV8.end(),
                  result.data.begin())) {
    return false;
  }
  const auto raw_result = result.data[kReceiptResultOffsetV8];
  if (raw_result >= v8::kResultCodeCount) return false;
  return result.code == application_code(static_cast<v8::Result>(raw_result));
}

bool append_finalize(Bytes& output, const FinalizedBlockV8& block) {
  if (block.transaction_results.size() > kMaximumBlockInputsV8) return false;
  append_hash(output, block.state_root);
  // Version one's finalized block has no identifier to report. Every version
  // since seven does, and an adapter that could not name the block it just
  // executed could not tell a peer which one it agreed to.
  append_hash(output, block.block_id);
  append_u32(output,
             static_cast<std::uint32_t>(block.transaction_results.size()));
  for (const auto& result : block.transaction_results) {
    if (!valid_finalize_result(result)) return false;
    append_u32(output, result.code);
    if (!append_blob(output, result.data)) return false;
  }
  return true;
}

bool append_success(MessageKind kind, const SuccessResponseV8& response,
                    Bytes& output) {
  switch (kind) {
    case MessageKind::info:
      if (const auto* value = std::get_if<ApplicationInfoV8>(&response)) {
        return append_info(output, *value);
      }
      break;
    case MessageKind::init_chain:
      if (const auto* value = std::get_if<v8::Hash>(&response)) {
        append_hash(output, *value);
        return true;
      }
      break;
    case MessageKind::check_transaction:
      if (const auto* value = std::get_if<TransactionResult>(&response)) {
        return append_check(output, *value);
      }
      break;
    case MessageKind::prepare_proposal:
      if (const auto* value = std::get_if<PreparedProposal>(&response)) {
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
      if (const auto* value = std::get_if<FinalizedBlockV8>(&response)) {
        return append_finalize(output, *value);
      }
      break;
    case MessageKind::commit:
      if (const auto* value = std::get_if<CommittedHeadV8>(&response)) {
        append_u64(output, value->height);
        append_hash(output, value->state_root);
        return true;
      }
      break;
  }
  return false;
}

EncodedFrameResult frame_response(MessageKind kind, std::uint64_t request_id,
                                  Bytes payload) {
  if (payload.size() > kMaximumWirePayload) return WireError::resource_limit;
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

EncodedFrameResult encode_success_response_v8(
    MessageKind kind, std::uint64_t request_id,
    const SuccessResponseV8& response) {
  Bytes payload;
  payload.reserve(86);
  append_u16(payload, 0);
  append_u32(payload, 0);
  if (!append_success(kind, response, payload)) {
    return WireError::invalid_payload;
  }
  return frame_response(kind, request_id, std::move(payload));
}

EncodedFrameResult encode_error_response_v8(MessageKind kind,
                                            std::uint64_t request_id,
                                            ApplicationError error) {
  const auto status = static_cast<std::uint16_t>(error);
  if (status == 0 ||
      status > static_cast<std::uint16_t>(ApplicationError::internal_failure)) {
    return WireError::invalid_payload;
  }
  Bytes payload;
  payload.reserve(6);
  append_u16(payload, status);
  append_u32(payload, 0);
  return frame_response(kind, request_id, std::move(payload));
}

}  // namespace protocol::application
