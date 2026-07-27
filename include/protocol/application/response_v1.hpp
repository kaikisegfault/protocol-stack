#pragma once

#include "protocol/application/application_v1.hpp"
#include "protocol/application/wire_v1.hpp"

#include <variant>

namespace protocol::application {

using SuccessResponse = std::variant<
    ApplicationInfo,
    protocol::v1::StateRoot,
    TransactionResult,
    PreparedProposal,
    bool,
    FinalizedBlock,
    CommittedHead>;

EncodedFrameResult encode_success_response(
    MessageKind kind,
    std::uint64_t request_id,
    const SuccessResponse& response);
EncodedFrameResult encode_error_response(
    MessageKind kind,
    std::uint64_t request_id,
    ApplicationError error);

}  // namespace protocol::application
