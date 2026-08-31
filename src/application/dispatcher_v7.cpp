// One decoded request to one encoded response frame.
//
// The request payloads are version one's, because their shapes carry no
// version-seven meaning. **One conversion is real**: `InitChainRequest` carries
// a `protocol::v1::ChainId`, which is a tagged type and therefore distinct from
// version seven's `Octets32` even though both are thirty-two octets. It is
// converted explicitly here rather than by loosening either type, because the
// tag is what stops a state root being passed where a chain identity belongs.

#include "protocol/application/dispatcher_v7.hpp"

#include "protocol/application/response_v7.hpp"

#include <algorithm>
#include <utility>
#include <variant>

namespace protocol::application {
namespace {

namespace v7 = protocol::v7;

template <typename Success, typename Result>
EncodedFrameResult encode_result(MessageKind kind, std::uint64_t request_id,
                                 Result result) {
  if (std::holds_alternative<ApplicationError>(result)) {
    return encode_error_response_v7(kind, request_id,
                                    std::get<ApplicationError>(result));
  }
  return encode_success_response_v7(
      kind, request_id, SuccessResponseV7{std::get<Success>(std::move(result))});
}

EncodedFrameResult invalid_payload(const DecodedRequest& request) {
  return encode_error_response_v7(request.kind, request.request_id,
                                  ApplicationError::invalid_request);
}

v7::Octets32 chain_id_of(const protocol::v1::ChainId& tagged) {
  v7::Octets32 value{};
  std::copy(tagged.begin(), tagged.end(), value.begin());
  return value;
}

}  // namespace

EncodedFrameResult dispatch_request_v7(ApplicationV7& application,
                                       const DecodedRequest& request) {
  switch (request.kind) {
    case MessageKind::info:
      if (!std::holds_alternative<EmptyRequest>(request.payload)) {
        return invalid_payload(request);
      }
      return encode_result<ApplicationInfoV7>(request.kind, request.request_id,
                                              application.info());
    case MessageKind::init_chain: {
      const auto* value = std::get_if<InitChainRequest>(&request.payload);
      if (value == nullptr) return invalid_payload(request);
      return encode_result<v7::Hash>(
          request.kind, request.request_id,
          application.init_chain(chain_id_of(value->chain_id),
                                 value->initial_height, value->app_state));
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
      const auto* value = std::get_if<BlockRequest>(&request.payload);
      if (value == nullptr) return invalid_payload(request);
      return encode_result<bool>(
          request.kind, request.request_id,
          application.process_proposal(value->height, value->transactions));
    }
    case MessageKind::finalize_block: {
      const auto* value = std::get_if<BlockRequest>(&request.payload);
      if (value == nullptr) return invalid_payload(request);
      return encode_result<FinalizedBlockV7>(
          request.kind, request.request_id,
          application.finalize_block(value->height, value->transactions));
    }
    case MessageKind::commit:
      if (!std::holds_alternative<EmptyRequest>(request.payload)) {
        return invalid_payload(request);
      }
      return encode_result<CommittedHeadV7>(request.kind, request.request_id,
                                            application.commit());
  }
  return invalid_payload(request);
}

}  // namespace protocol::application
