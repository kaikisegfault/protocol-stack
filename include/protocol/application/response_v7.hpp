#pragma once

// The version-seven response encoder.
//
// **The frame format is version one's and is reused unchanged.** The 20-octet
// header, the seven message kinds, the six wire errors, and the five request
// payloads carry no version-seven meaning — a height, a transaction list, a byte
// budget, an app state — so a second frame format would be a second place for a
// framing rule to be wrong.
//
// What differs is the three responses whose contents are version-seven's: the
// finalized block carries a block identifier version one's does not, and its
// per-transaction receipts are version seven's fifty-six octets rather than
// version one's forty-seven.

#include "protocol/application/application_v7.hpp"
#include "protocol/application/wire_v1.hpp"

#include <cstdint>
#include <variant>

namespace protocol::application {

using SuccessResponseV7 =
    std::variant<ApplicationInfoV7, protocol::v7::Hash, TransactionResult,
                 PreparedProposal, bool, FinalizedBlockV7, CommittedHeadV7>;

EncodedFrameResult encode_success_response_v7(MessageKind kind,
                                              std::uint64_t request_id,
                                              const SuccessResponseV7& response);
EncodedFrameResult encode_error_response_v7(MessageKind kind,
                                            std::uint64_t request_id,
                                            ApplicationError error);

}  // namespace protocol::application
