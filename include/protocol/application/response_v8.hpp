#pragma once

// The version-eight response encoder.
//
// **The frame format is version one's and is reused unchanged.** The 20-octet
// header, the seven message kinds, the six wire errors, and the five request
// payloads carry no version-eight meaning — a height, a transaction list, a byte
// budget, an app state — so a second frame format would be a second place for a
// framing rule to be wrong.
//
// What differs is the three responses whose contents are version-eight's: the
// finalized block carries a block identifier version one's does not, and its
// per-transaction receipts are version eight's fifty-six octets rather than
// version one's forty-seven.

#include "protocol/application/application_v8.hpp"
#include "protocol/application/wire_v1.hpp"

#include <cstdint>
#include <variant>

namespace protocol::application {

using SuccessResponseV8 =
    std::variant<ApplicationInfoV8, protocol::v8::Hash, TransactionResult,
                 PreparedProposal, bool, FinalizedBlockV8, CommittedHeadV8>;

EncodedFrameResult encode_success_response_v8(MessageKind kind,
                                              std::uint64_t request_id,
                                              const SuccessResponseV8& response);
EncodedFrameResult encode_error_response_v8(MessageKind kind,
                                            std::uint64_t request_id,
                                            ApplicationError error);

}  // namespace protocol::application
