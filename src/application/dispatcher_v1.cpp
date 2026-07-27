#include "protocol/application/dispatcher_v1.hpp"

#include "protocol/application/response_v1.hpp"

#include <utility>
#include <variant>

namespace protocol::application {
namespace {

template <typename Success, typename Result>
EncodedFrameResult encode_result(
    MessageKind kind,
    std::uint64_t request_id,
    Result result) {
  if (std::holds_alternative<ApplicationError>(result)) {
    return encode_error_response(
        kind, request_id, std::get<ApplicationError>(result));
  }
  return encode_success_response(
      kind, request_id,
      SuccessResponse{std::get<Success>(std::move(result))});
}

EncodedFrameResult invalid_payload(const DecodedRequest& request) {
  return encode_error_response(
      request.kind, request.request_id,
      ApplicationError::invalid_request);
}

}  // namespace

EncodedFrameResult dispatch_request(
    ApplicationV1& application,
    const DecodedRequest& request) {
  switch (request.kind) {
    case MessageKind::info:
      if (!std::holds_alternative<EmptyRequest>(request.payload)) {
        return invalid_payload(request);
      }
      return encode_result<ApplicationInfo>(
          request.kind, request.request_id, application.info());
    case MessageKind::init_chain: {
      const auto* value =
          std::get_if<InitChainRequest>(&request.payload);
      if (value == nullptr) return invalid_payload(request);
      return encode_result<protocol::v1::StateRoot>(
          request.kind, request.request_id,
          application.init_chain(
              value->chain_id, value->initial_height, value->app_state));
    }
    case MessageKind::check_transaction: {
      const auto* value =
          std::get_if<CheckTransactionRequest>(&request.payload);
      if (value == nullptr) return invalid_payload(request);
      return encode_result<TransactionResult>(
          request.kind, request.request_id,
          application.check_transaction(value->transaction));
    }
    case MessageKind::prepare_proposal: {
      const auto* value =
          std::get_if<PrepareProposalRequest>(&request.payload);
      if (value == nullptr) return invalid_payload(request);
      return encode_result<PreparedProposal>(
          request.kind, request.request_id,
          application.prepare_proposal(
              value->maximum_transaction_bytes, value->transactions));
    }
    case MessageKind::process_proposal: {
      const auto* value = std::get_if<BlockRequest>(&request.payload);
      if (value == nullptr) return invalid_payload(request);
      return encode_result<bool>(
          request.kind, request.request_id,
          application.process_proposal(
              value->height, value->transactions));
    }
    case MessageKind::finalize_block: {
      const auto* value = std::get_if<BlockRequest>(&request.payload);
      if (value == nullptr) return invalid_payload(request);
      return encode_result<FinalizedBlock>(
          request.kind, request.request_id,
          application.finalize_block(
              value->height, value->transactions));
    }
    case MessageKind::commit:
      if (!std::holds_alternative<EmptyRequest>(request.payload)) {
        return invalid_payload(request);
      }
      return encode_result<CommittedHead>(
          request.kind, request.request_id, application.commit());
  }
  return invalid_payload(request);
}

}  // namespace protocol::application
