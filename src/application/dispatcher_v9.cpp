// One decoded version-two request to one encoded response frame.
//
// Version eight's dispatcher with three differences, each carried by a type:
// the block and init-chain requests carry a stamp, the proposal answer is a
// `ProposalDecision` rather than a Boolean, and a finalize can fail in a way no
// other operation can. **That last one is the only branch here that is not a
// straight call and an encode**, because `FinalizeFailureV9` is the one result
// with two error types, and each has its own encoder.
//
// The chain identity is converted exactly as version eight's is: the wire decodes
// a tagged `protocol::v1::ChainId`, the application takes an `Octets32`, and the
// conversion is explicit here rather than made implicit by loosening either type.

#include "protocol/application/dispatcher_v9.hpp"

#include "protocol/application/response_v9.hpp"

#include <algorithm>
#include <utility>
#include <variant>

namespace protocol::application {
namespace {

namespace v9 = protocol::v9;

template <typename Success, typename Result>
EncodedFrameResult encode_result(MessageKind kind, std::uint64_t request_id,
                                 Result result) {
  if (std::holds_alternative<ApplicationError>(result)) {
    return encode_error_response_v9(kind, request_id,
                                    std::get<ApplicationError>(result));
  }
  return encode_success_response_v9(
      kind, request_id, SuccessResponseV9{std::get<Success>(std::move(result))});
}

// A decided block this machine's rules refuse for its stamp is status `7` or
// `8`; any other finalize failure is one of version one's six.
EncodedFrameResult encode_finalize(std::uint64_t request_id,
                                   FinalizeBlockResultV9 result) {
  if (auto* block = std::get_if<FinalizedBlockV9>(&result)) {
    return encode_success_response_v9(MessageKind::finalize_block, request_id,
                                      SuccessResponseV9{std::move(*block)});
  }
  const auto& failure = std::get<FinalizeFailureV9>(result);
  if (const auto* stamp = std::get_if<TimestampFailureV9>(&failure)) {
    return encode_timestamp_failure_v9(request_id, *stamp);
  }
  return encode_error_response_v9(MessageKind::finalize_block, request_id,
                                  std::get<ApplicationError>(failure));
}

EncodedFrameResult invalid_payload(const DecodedRequestV2& request) {
  return encode_error_response_v9(request.kind, request.request_id,
                                  ApplicationError::invalid_request);
}

v9::Octets32 chain_id_of(const protocol::v1::ChainId& tagged) {
  v9::Octets32 value{};
  std::copy(tagged.begin(), tagged.end(), value.begin());
  return value;
}

}  // namespace

EncodedFrameResult dispatch_request_v9(ApplicationV9& application,
                                       const DecodedRequestV2& request) {
  switch (request.kind) {
    case MessageKind::info:
      if (!std::holds_alternative<EmptyRequest>(request.payload)) {
        return invalid_payload(request);
      }
      return encode_result<ApplicationInfoV9>(request.kind, request.request_id,
                                              application.info());
    case MessageKind::init_chain: {
      const auto* value = std::get_if<InitChainRequestV2>(&request.payload);
      if (value == nullptr) return invalid_payload(request);
      return encode_result<v9::Hash>(
          request.kind, request.request_id,
          application.init_chain(chain_id_of(value->chain_id),
                                 value->initial_height,
                                 value->genesis_timestamp, value->app_state));
    }
    case MessageKind::check_transaction: {
      const auto* value = std::get_if<CheckTransactionRequest>(&request.payload);
      if (value == nullptr) return invalid_payload(request);
      return encode_result<TransactionResult>(
          request.kind, request.request_id,
          application.check_transaction(value->transaction));
    }
    case MessageKind::prepare_proposal: {
      const auto* value = std::get_if<PrepareProposalRequest>(&request.payload);
      if (value == nullptr) return invalid_payload(request);
      return encode_result<PreparedProposal>(
          request.kind, request.request_id,
          application.prepare_proposal(value->maximum_transaction_bytes,
                                       value->transactions));
    }
    case MessageKind::process_proposal: {
      const auto* value = std::get_if<BlockRequestV2>(&request.payload);
      if (value == nullptr) return invalid_payload(request);
      return encode_result<ProposalDecision>(
          request.kind, request.request_id,
          application.process_proposal(value->height, value->timestamp,
                                       value->transactions));
    }
    case MessageKind::finalize_block: {
      const auto* value = std::get_if<BlockRequestV2>(&request.payload);
      if (value == nullptr) return invalid_payload(request);
      return encode_finalize(
          request.request_id,
          application.finalize_block(value->height, value->timestamp,
                                     value->transactions));
    }
    case MessageKind::commit:
      if (!std::holds_alternative<EmptyRequest>(request.payload)) {
        return invalid_payload(request);
      }
      return encode_result<CommittedHeadV9>(request.kind, request.request_id,
                                            application.commit());
  }
  return invalid_payload(request);
}

}  // namespace protocol::application
