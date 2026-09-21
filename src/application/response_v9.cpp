// The version-nine response encoder.
//
// **Every response is validated on the way out, not merely serialised**, which
// is version eight's rule unchanged: the adapter on the other side has no way to
// tell a wrong answer from a right one, so the last place a disagreement can be
// caught is here. Version nine adds two things to refuse — a decision byte
// outside the eight the contract names, and a timestamp status arriving through
// the `ApplicationError` path — and one thing to refuse differently: a receipt
// is version nine's only if its version octets say `9`, so a version-eight
// receipt framed as a version-nine answer is refused rather than written.

#include "protocol/application/response_v9.hpp"

#include <algorithm>
#include <array>
#include <limits>
#include <span>
#include <utility>

namespace protocol::application {
namespace {

namespace v9 = protocol::v9;
using v9::Bytes;

// Version nine's receipt: `PSRC`, the receipt version, the transaction
// identifier, the kind, the result code, the fee, and the issued amount. The
// layout is version eight's with the version field at `9`, so the result byte is
// at the same offset.
//
// The version octets are derived from `kReceiptVersion` rather than written out,
// for the reason `response_v8.cpp` records: a literal here moves with the version
// while looking like framing, and the `static_assert` below covers the prefix
// only if the prefix is computed from the constant it asserts.
constexpr std::array<std::uint8_t, 6> kReceiptPrefixV9{
    'P', 'S', 'R', 'C',
    static_cast<std::uint8_t>(v9::kReceiptVersion >> 8U),
    static_cast<std::uint8_t>(v9::kReceiptVersion & 0xFFU),
};
constexpr std::size_t kReceiptResultOffsetV9 = 39;

static_assert(v9::kReceiptBytes == 56);
static_assert(v9::kReceiptVersion == 9);
static_assert(static_cast<std::uint16_t>(ApplicationError::invalid_request) == 1);
static_assert(static_cast<std::uint16_t>(ApplicationError::internal_failure) == 6);
// The two timestamp statuses follow version one's six directly. A gap or an
// overlap would put a C1 failure under a meaning version one already assigned.
static_assert(static_cast<std::uint16_t>(
                  TimestampFailureV9::decided_block_failed_range) == 7);
static_assert(static_cast<std::uint16_t>(
                  TimestampFailureV9::decided_block_failed_monotonicity) == 8);
static_assert(static_cast<std::uint8_t>(ProposalDecision::not_executable) == 7);

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
  if (transactions.size() > kMaximumBlockInputsV9) return false;
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

void append_hash(Bytes& output, const v9::Octets32& hash) {
  output.insert(output.end(), hash.begin(), hash.end());
}

// The durable head is two scalars and a root, and Info and Commit report all
// three in the order the head holds them.
void append_info(Bytes& output, const ApplicationInfoV9& info) {
  append_u64(output, info.application_version);
  append_u64(output, info.height);
  append_u64(output, info.timestamp);
  append_hash(output, info.state_root);
}

void append_commit(Bytes& output, const CommittedHeadV9& head) {
  append_u64(output, head.height);
  append_u64(output, head.timestamp);
  append_hash(output, head.state_root);
}

// A mempool answer is an admission code and nothing else. A receipt here would
// mean the application had executed something to answer a question about a
// height nobody has proposed.
bool append_check(Bytes& output, const TransactionResult& result) {
  if (result.code > 3 || !result.data.empty()) return false;
  append_u32(output, result.code);
  return true;
}

// **A decision outside the eight is refused rather than written.** The enum
// cannot hold one unless something cast it there, and the adapter votes REJECT
// on every nonzero byte — so a stray value would still vote the right way and
// would report an outcome the contract does not name. That is the silent kind of
// wrong, which is why it is caught here rather than left to the vote.
bool append_decision(Bytes& output, ProposalDecision decision) {
  const auto raw = static_cast<std::uint8_t>(decision);
  if (raw > static_cast<std::uint8_t>(ProposalDecision::not_executable)) {
    return false;
  }
  output.push_back(raw);
  return true;
}

// The declared code and the encoded receipt must be the same fact. A rejected
// admission carries its small code and no receipt; anything else must be a
// version-nine receipt whose own result byte produces exactly the declared code.
bool valid_finalize_result(const TransactionResult& result) {
  if (result.code >= 1 && result.code <= 3) return result.data.empty();
  if (result.data.size() != v9::kReceiptBytes ||
      !std::equal(kReceiptPrefixV9.begin(), kReceiptPrefixV9.end(),
                  result.data.begin())) {
    return false;
  }
  const auto raw_result = result.data[kReceiptResultOffsetV9];
  if (raw_result >= v9::kResultCodeCount) return false;
  return result.code == application_code(static_cast<v9::Result>(raw_result));
}

bool append_finalize(Bytes& output, const FinalizedBlockV9& block) {
  if (block.transaction_results.size() > kMaximumBlockInputsV9) return false;
  append_hash(output, block.state_root);
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

bool append_success(MessageKind kind, const SuccessResponseV9& response,
                    Bytes& output) {
  switch (kind) {
    case MessageKind::info:
      if (const auto* value = std::get_if<ApplicationInfoV9>(&response)) {
        append_info(output, *value);
        return true;
      }
      break;
    case MessageKind::init_chain:
      if (const auto* value = std::get_if<v9::Hash>(&response)) {
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
      if (const auto* value = std::get_if<ProposalDecision>(&response)) {
        return append_decision(output, *value);
      }
      break;
    case MessageKind::finalize_block:
      if (const auto* value = std::get_if<FinalizedBlockV9>(&response)) {
        return append_finalize(output, *value);
      }
      break;
    case MessageKind::commit:
      if (const auto* value = std::get_if<CommittedHeadV9>(&response)) {
        append_commit(output, *value);
        return true;
      }
      break;
  }
  return false;
}

EncodedFrameResult frame_response(MessageKind kind, std::uint64_t request_id,
                                  Bytes payload) {
  if (payload.size() > kMaximumWirePayload) return WireError::resource_limit;
  return encode_frame_v2(Frame{
      FrameHeader{
          WireDirection::response,
          kind,
          request_id,
          static_cast<std::uint32_t>(payload.size()),
      },
      std::move(payload),
  });
}

// A nonzero status and an empty diagnostic. The contract permits a diagnostic
// and this encoder writes none, as version eight's does: diagnostics are
// operational only, and the bridge never places one in a consensus result.
EncodedFrameResult frame_status(MessageKind kind, std::uint64_t request_id,
                                std::uint16_t status) {
  Bytes payload;
  payload.reserve(6);
  append_u16(payload, status);
  append_u32(payload, 0);
  return frame_response(kind, request_id, std::move(payload));
}

}  // namespace

EncodedFrameResult encode_success_response_v9(
    MessageKind kind, std::uint64_t request_id,
    const SuccessResponseV9& response) {
  Bytes payload;
  payload.reserve(86);
  append_u16(payload, 0);
  append_u32(payload, 0);
  if (!append_success(kind, response, payload)) {
    return WireError::invalid_payload;
  }
  return frame_response(kind, request_id, std::move(payload));
}

// **Version one's six and no more.** A `7` or `8` cast into an
// `ApplicationError` would otherwise reach kind 5 through this path, which is
// exactly the path the separate function below exists to close.
EncodedFrameResult encode_error_response_v9(MessageKind kind,
                                            std::uint64_t request_id,
                                            ApplicationError error) {
  const auto status = static_cast<std::uint16_t>(error);
  if (status == 0 ||
      status > static_cast<std::uint16_t>(ApplicationError::internal_failure)) {
    return WireError::invalid_payload;
  }
  return frame_status(kind, request_id, status);
}

EncodedFrameResult encode_timestamp_failure_v9(std::uint64_t request_id,
                                               TimestampFailureV9 failure) {
  const auto status = static_cast<std::uint16_t>(failure);
  if (failure != TimestampFailureV9::decided_block_failed_range &&
      failure != TimestampFailureV9::decided_block_failed_monotonicity) {
    return WireError::invalid_payload;
  }
  return frame_status(MessageKind::finalize_block, request_id, status);
}

}  // namespace protocol::application
