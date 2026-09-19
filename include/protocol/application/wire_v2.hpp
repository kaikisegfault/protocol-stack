#pragma once

// The version-two local application frame.
//
// **This is the first version of this protocol to change its own version
// field.** Version seven added a block identifier to the finalized-block
// response and version eight kept it, while the protocol version stayed at `1`
// and no contract document recorded the change — so a version-one reader paired
// with a version-eight writer refuses the finalize response at the *result
// count*, as a generic protocol failure, on the first block. The refusal is real
// and both decoders are correct about it; what was missing is that the one field
// whose job is to announce a shape change did not announce one.
// [`consensus-application-v2`](../../../docs/specifications/consensus-application-v2.md)
// closes that, and this module is where the closing happens: the version becomes
// `2`, and the refusal moves to the header, on the first frame, under the name
// of the actual fault.
//
// **Everything that did not change is version one's and is shared rather than
// copied.** The 20-octet header, the magic, the direction and request-id rules,
// the payload cap, the seven message kinds, and the seven wire errors are
// declared once in `wire_v1.hpp` and used from here. A second declaration of any
// of them would be a second place for a framing rule to be wrong, which is the
// argument `response_v8.hpp` already makes about this same frame.
//
// **What version two changes is two request payloads**, and both change for one
// reason: version nine's blocks carry a timestamp, so the operations that name a
// block have to carry one too.

#include "protocol/application/wire_v1.hpp"
#include "protocol/v9/ledger.hpp"

#include <cstdint>
#include <span>
#include <variant>
#include <vector>

namespace protocol::application {

// The accepted protocol version of this frame. Declared here rather than only in
// the translation unit so that a test can state the figure it is pinning.
inline constexpr std::uint16_t kWireVersionV2 = 2;

// The raw-input bound is the kernel's own, derived rather than restated. Version
// one's `kMaximumBlockInputs` is the same number today; deriving it is what makes
// a version that moved the kernel bound a build failure here rather than a
// transport that accepts a block the kernel will refuse.
inline constexpr std::size_t kMaximumBlockInputsV2 = protocol::v9::kMaxRawInputs;

// Kind 2. **`genesis_timestamp` precedes `app_state`** because every fixed-width
// field precedes the one variable-length field, which is version one's own
// layout rule and is what lets a decoder bound the frame before it allocates.
struct InitChainRequestV2 {
  protocol::v1::ChainId chain_id;
  std::uint64_t initial_height = 0;
  std::uint64_t genesis_timestamp = 0;
  protocol::v1::Bytes app_state;

  bool operator==(const InitChainRequestV2&) const = default;
};

// Kinds 5 and 6. The stamp follows the height because the two are the block's
// identity in the same order the durable head reports them.
struct BlockRequestV2 {
  std::uint64_t height = 0;
  std::uint64_t timestamp = 0;
  std::vector<protocol::v1::Bytes> transactions;

  bool operator==(const BlockRequestV2&) const = default;
};

// Kinds 1 and 7 take no request payload, kind 3 and kind 4 are version one's
// unchanged, so those three alternatives are version one's own types rather than
// re-declared ones: a second `CheckTransactionRequest` would be a second thing
// to keep in step for no version-two reason.
using RequestPayloadV2 =
    std::variant<EmptyRequest, InitChainRequestV2, CheckTransactionRequest,
                 PrepareProposalRequest, BlockRequestV2>;

struct DecodedRequestV2 {
  MessageKind kind;
  std::uint64_t request_id;
  RequestPayloadV2 payload;

  bool operator==(const DecodedRequestV2&) const = default;
};

using RequestResultV2 = std::variant<DecodedRequestV2, WireError>;

// The header codec. It differs from version one's in exactly one comparison —
// the accepted version — which is why it is a function of its own rather than a
// parameter added to version one's: version one and version eight are delivered
// and frozen, and neither should gain a way to accept a frame it did not accept
// before.
HeaderResult decode_frame_header_v2(
    std::span<const std::uint8_t> header) noexcept;
FrameResult decode_frame_v2(std::span<const std::uint8_t> bytes);
RequestResultV2 decode_request_frame_v2(std::span<const std::uint8_t> bytes);
EncodedFrameResult encode_frame_v2(const Frame& frame);

}  // namespace protocol::application
