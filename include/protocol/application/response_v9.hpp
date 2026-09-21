#pragma once

// The version-nine response encoder, over the version-two frame.
//
// The response layout is version one's: `status:u16 || message:blob`, then the
// kind's success payload when the status is zero. What version nine changes is
// four of the seven success payloads and the status space:
//
//   - kinds 1 and 7 report the durable **timestamp** beside the height, because
//     the durable head is two scalars and a root;
//   - kind 5 answers a `decision:u8` rather than an `accept:Boolean`, so the byte
//     says which of eight outcomes produced the vote;
//   - kind 6 carries version nine's receipts, whose version octets are `9`; and
//   - statuses `7` and `8` exist, for a decided block whose stamp fails C1 or C2.
//
// **Statuses `7` and `8` are reachable only from kind 6, and that is a signature
// rather than a check.** `encode_timestamp_failure_v9` takes no kind: it writes
// a finalize response or nothing. Kind 5 reports the same two conditions as
// decisions `2` and `3` under a status of zero, because there the correct answer
// is a vote and here it is a halt — so an encoder that could write status `7`
// for kind 5 would be an encoder that could turn a peer's bad stamp into this
// machine stopping.

#include "protocol/application/application_v9.hpp"
#include "protocol/application/wire_v2.hpp"

#include <cstdint>
#include <variant>

namespace protocol::application {

using SuccessResponseV9 =
    std::variant<ApplicationInfoV9, protocol::v9::Hash, TransactionResult,
                 PreparedProposal, ProposalDecision, FinalizedBlockV9,
                 CommittedHeadV9>;

EncodedFrameResult encode_success_response_v9(MessageKind kind,
                                              std::uint64_t request_id,
                                              const SuccessResponseV9& response);
// Statuses `1` through `6`, version one's, for any kind.
EncodedFrameResult encode_error_response_v9(MessageKind kind,
                                            std::uint64_t request_id,
                                            ApplicationError error);
// Statuses `7` and `8`, for kind 6 and nothing else.
EncodedFrameResult encode_timestamp_failure_v9(std::uint64_t request_id,
                                               TimestampFailureV9 failure);

}  // namespace protocol::application
