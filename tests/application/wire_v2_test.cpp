// The version-two frame codec.
//
// **The case this suite exists for is the cross-version pair**, because it is
// the one version two was created to make possible. Version seven changed the
// finalize response's shape and left the protocol version at `1`, so a reader of
// the older shape refuses the newer one at the *result count*, as a generic
// protocol failure, on the first block. Here a version-one frame presented to
// version two's decoder and a version-two frame presented to version one's are
// both refused as `unsupported_version`, at the header, on the first frame.
//
// Everything else is version one's suite re-established against the two payloads
// that gained a stamp: the frozen header bytes with `2` in them, a round trip
// per kind, and the truncation, trailing-byte, bound, and hostile-count cases.

#include "protocol/application/application_v1.hpp"
#include "protocol/application/wire_v1.hpp"
#include "protocol/application/wire_v2.hpp"

#include "../../tools/protocol-vectors/vector_common.hpp"

#include <cstddef>
#include <cstdint>
#include <exception>
#include <iostream>
#include <string_view>
#include <utility>
#include <variant>
#include <vector>

namespace pa = protocol::application;
namespace p = protocol::v1;
namespace pv = protocol_vectors;

namespace {

// A stamp inside `calendar-v1`'s range, chosen so that no octet of it is zero
// and a decoder that dropped or transposed a byte changes the value.
constexpr std::uint64_t kStamp = 1'768'435'290'000;

void append_u32(p::Bytes& bytes, std::uint32_t value) {
  for (int shift = 24; shift >= 0; shift -= 8) {
    bytes.push_back(static_cast<std::uint8_t>(value >> shift));
  }
}

void append_u64(p::Bytes& bytes, std::uint64_t value) {
  pv::append_u64(bytes, value);
}

void append_blob(p::Bytes& bytes, const p::Bytes& value) {
  append_u32(bytes, static_cast<std::uint32_t>(value.size()));
  bytes.insert(bytes.end(), value.begin(), value.end());
}

void append_transactions(p::Bytes& bytes,
                         const std::vector<p::Bytes>& transactions) {
  append_u32(bytes, static_cast<std::uint32_t>(transactions.size()));
  for (const auto& transaction : transactions) append_blob(bytes, transaction);
}

p::Bytes frame_bytes(pa::MessageKind kind, std::uint64_t request_id,
                     p::Bytes payload = {},
                     pa::WireDirection direction = pa::WireDirection::request) {
  const pa::Frame frame{
      pa::FrameHeader{direction, kind, request_id,
                      static_cast<std::uint32_t>(payload.size())},
      std::move(payload),
  };
  auto encoded = pa::encode_frame_v2(frame);
  pv::require(std::holds_alternative<p::Bytes>(encoded), "encode frame");
  return std::get<p::Bytes>(std::move(encoded));
}

template <typename Expected, typename Result>
Expected take(Result result, std::string_view message) {
  pv::require(std::holds_alternative<Expected>(result), message);
  return std::get<Expected>(std::move(result));
}

template <typename Result>
void require_error(Result result, pa::WireError expected,
                   std::string_view message) {
  pv::require(std::holds_alternative<pa::WireError>(result) &&
                  std::get<pa::WireError>(result) == expected,
              message);
}

p::Hash counting_chain() {
  p::Hash raw{};
  for (std::size_t index = 0; index < raw.size(); ++index) {
    raw[index] = static_cast<std::uint8_t>(index);
  }
  return raw;
}

void verify_header_and_frame() {
  // The frozen bytes, with the version octets reading 2 where version one's
  // read 1. This is the figure the whole slice moves, so it is pinned as bytes
  // rather than compared against the constant that produced it.
  const p::Bytes expected{
      'P', 'S', 'A', 'P', 0, 2, 0, 1,
      0,   0,   0,   0,   0, 0, 0, 1,
      0,   0,   0,   0,
  };
  const auto encoded = frame_bytes(pa::MessageKind::info, 1);
  pv::require(encoded == expected, "frozen Info frame bytes");
  pv::require(encoded[5] == pa::kWireVersionV2,
              "the encoded version octet is version two's");
  pv::require(take<pa::FrameHeader>(pa::decode_frame_header_v2(encoded),
                                    "decode header") ==
                  pa::FrameHeader{pa::WireDirection::request,
                                  pa::MessageKind::info, 1, 0},
              "decoded header fields");
  pv::require(
      take<pa::Frame>(pa::decode_frame_v2(encoded), "decode frame") ==
          pa::Frame{pa::FrameHeader{pa::WireDirection::request,
                                    pa::MessageKind::info, 1, 0},
                    {}},
      "decoded frame fields");
  // The header is still 20 octets: version two moves the value in the field, not
  // the field.
  pv::require(encoded.size() == pa::kWireHeaderSize, "the header is 20 octets");
}

// **The pair this version exists for.** Each decoder refuses the other's frame
// at the header, under the name of the actual fault, before a payload is read.
void verify_the_versions_refuse_each_other() {
  const auto version_two = frame_bytes(pa::MessageKind::info, 1);
  require_error(pa::decode_frame_header(version_two),
                pa::WireError::unsupported_version,
                "version one's decoder admitted a version-two frame");
  require_error(pa::decode_request_frame(version_two),
                pa::WireError::unsupported_version,
                "version one's request decoder admitted a version-two frame");

  const pa::Frame frame{
      pa::FrameHeader{pa::WireDirection::request, pa::MessageKind::info, 1, 0},
      {}};
  auto version_one = pa::encode_frame(frame);
  pv::require(std::holds_alternative<p::Bytes>(version_one),
              "encode a version-one frame");
  const auto one = std::get<p::Bytes>(std::move(version_one));
  pv::require(one[5] == 1, "the version-one frame carries version one");
  require_error(pa::decode_frame_header_v2(one),
                pa::WireError::unsupported_version,
                "version two's decoder admitted a version-one frame");
  require_error(pa::decode_request_frame_v2(one),
                pa::WireError::unsupported_version,
                "version two's request decoder admitted a version-one frame");

  // And the refusal is the header's rather than a payload's: a version-one
  // finalize frame carrying a whole well-formed version-one block body is still
  // refused on its sixth octet.
  p::Bytes body;
  append_u64(body, 4);
  append_transactions(body, {p::Bytes{1, 2, 3}});
  const pa::Frame block{
      pa::FrameHeader{pa::WireDirection::request, pa::MessageKind::finalize_block,
                      9, static_cast<std::uint32_t>(body.size())},
      body};
  auto encoded_block = pa::encode_frame(block);
  pv::require(std::holds_alternative<p::Bytes>(encoded_block),
              "encode a version-one finalize frame");
  require_error(
      pa::decode_request_frame_v2(std::get<p::Bytes>(std::move(encoded_block))),
      pa::WireError::unsupported_version,
      "a version-one block body reached version two's payload decoder");
}

void verify_request_payloads() {
  {
    const auto request = take<pa::DecodedRequestV2>(
        pa::decode_request_frame_v2(frame_bytes(pa::MessageKind::commit, 7)),
        "decode Commit");
    pv::require(request.kind == pa::MessageKind::commit &&
                    request.request_id == 7 &&
                    std::holds_alternative<pa::EmptyRequest>(request.payload),
                "Commit request fields");
  }
  {
    const auto request = take<pa::DecodedRequestV2>(
        pa::decode_request_frame_v2(frame_bytes(pa::MessageKind::info, 3)),
        "decode Info");
    pv::require(std::holds_alternative<pa::EmptyRequest>(request.payload),
                "Info request fields");
  }
  {
    // Kind 2, with the stamp between the height and the one variable-length
    // field. A decoder that read them in the other order produces a different
    // app state and a different stamp, so the order is pinned by the value.
    const auto raw_chain = counting_chain();
    const p::Bytes app_state{'"', 'v', '9', '"'};
    p::Bytes payload(raw_chain.begin(), raw_chain.end());
    append_u64(payload, 1);
    append_u64(payload, kStamp);
    append_blob(payload, app_state);
    const auto request = take<pa::DecodedRequestV2>(
        pa::decode_request_frame_v2(
            frame_bytes(pa::MessageKind::init_chain, 9, payload)),
        "decode InitChain");
    pv::require(std::get<pa::InitChainRequestV2>(request.payload) ==
                    pa::InitChainRequestV2{p::ChainId{raw_chain}, 1, kStamp,
                                           app_state},
                "InitChain payload");
  }
  {
    const p::Bytes transaction{1, 2, 3};
    p::Bytes payload;
    append_blob(payload, transaction);
    const auto request = take<pa::DecodedRequestV2>(
        pa::decode_request_frame_v2(
            frame_bytes(pa::MessageKind::check_transaction, 4, payload)),
        "decode CheckTx");
    pv::require(std::get<pa::CheckTransactionRequest>(request.payload) ==
                    pa::CheckTransactionRequest{transaction},
                "CheckTx payload");
  }
  {
    // Kind 4 is version one's unchanged, and it is checked here precisely
    // because it is: a port that added a stamp to every block-shaped payload
    // would have added one to PrepareProposal too.
    const std::vector<p::Bytes> transactions{{1}, {2, 3}};
    p::Bytes payload;
    append_u64(payload, static_cast<std::uint64_t>(-1));
    append_transactions(payload, transactions);
    const auto request = take<pa::DecodedRequestV2>(
        pa::decode_request_frame_v2(
            frame_bytes(pa::MessageKind::prepare_proposal, 5, payload)),
        "decode PrepareProposal");
    const auto prepared =
        std::get<pa::PrepareProposalRequest>(request.payload);
    pv::require(prepared.maximum_transaction_bytes == -1 &&
                    prepared.transactions == transactions,
                "PrepareProposal payload");
  }
  for (const auto kind :
       {pa::MessageKind::process_proposal, pa::MessageKind::finalize_block}) {
    const std::vector<p::Bytes> transactions{{7, 8}, {9}};
    p::Bytes payload;
    append_u64(payload, 4);
    append_u64(payload, kStamp);
    append_transactions(payload, transactions);
    const auto request = take<pa::DecodedRequestV2>(
        pa::decode_request_frame_v2(frame_bytes(kind, 11, payload)),
        "decode a block request");
    pv::require(std::get<pa::BlockRequestV2>(request.payload) ==
                    pa::BlockRequestV2{4, kStamp, transactions},
                "block request payload");
  }
  {
    // A zero stamp is a value, not an absence. `std::optional` holding zero is
    // engaged, and a decoder that tested the value rather than the engagement
    // would refuse this frame.
    const std::vector<p::Bytes> none;
    p::Bytes payload;
    append_u64(payload, 1);
    append_u64(payload, 0);
    append_transactions(payload, none);
    const auto request = take<pa::DecodedRequestV2>(
        pa::decode_request_frame_v2(
            frame_bytes(pa::MessageKind::process_proposal, 12, payload)),
        "decode a block request at stamp zero");
    pv::require(std::get<pa::BlockRequestV2>(request.payload) ==
                    pa::BlockRequestV2{1, 0, none},
                "a zero stamp decodes as zero");
  }
}

void verify_frame_rejections() {
  {
    auto bytes = frame_bytes(pa::MessageKind::info, 1);
    bytes[0] = 'X';
    require_error(pa::decode_frame_header_v2(bytes),
                  pa::WireError::invalid_frame, "bad magic accepted");
  }
  {
    auto bytes = frame_bytes(pa::MessageKind::info, 1);
    bytes[5] = 3;
    require_error(pa::decode_frame_header_v2(bytes),
                  pa::WireError::unsupported_version, "version three accepted");
  }
  {
    auto bytes = frame_bytes(pa::MessageKind::info, 1);
    bytes[6] = 2;
    require_error(pa::decode_frame_header_v2(bytes),
                  pa::WireError::invalid_direction, "bad direction accepted");
  }
  {
    auto bytes = frame_bytes(pa::MessageKind::info, 1);
    bytes[7] = 8;
    require_error(pa::decode_frame_header_v2(bytes),
                  pa::WireError::unknown_kind, "kind eight accepted");
  }
  {
    auto bytes = frame_bytes(pa::MessageKind::info, 1);
    bytes[7] = 0;
    require_error(pa::decode_frame_header_v2(bytes),
                  pa::WireError::unknown_kind, "kind zero accepted");
  }
  {
    auto bytes = frame_bytes(pa::MessageKind::info, 1);
    for (std::size_t index = 8; index < 16; ++index) bytes[index] = 0;
    require_error(pa::decode_frame_header_v2(bytes),
                  pa::WireError::invalid_request_id, "request id zero accepted");
  }
  {
    auto bytes = frame_bytes(pa::MessageKind::info, 1);
    bytes[16] = 0xFF;
    require_error(pa::decode_frame_header_v2(bytes),
                  pa::WireError::resource_limit, "oversized payload accepted");
  }
  {
    auto bytes = frame_bytes(pa::MessageKind::info, 1);
    bytes.pop_back();
    require_error(pa::decode_frame_v2(bytes), pa::WireError::invalid_frame,
                  "short frame accepted");
  }
  {
    auto bytes = frame_bytes(pa::MessageKind::info, 1);
    bytes.push_back(0);
    require_error(pa::decode_frame_v2(bytes), pa::WireError::invalid_frame,
                  "trailing frame byte accepted");
  }
  {
    const auto bytes = frame_bytes(pa::MessageKind::info, 1, {},
                                   pa::WireDirection::response);
    require_error(pa::decode_request_frame_v2(bytes),
                  pa::WireError::invalid_direction,
                  "a response frame decoded as a request");
  }
  {
    const pa::Frame frame{
        pa::FrameHeader{pa::WireDirection::request, pa::MessageKind::info, 0, 0},
        {}};
    require_error(pa::encode_frame_v2(frame), pa::WireError::invalid_frame,
                  "encoded a frame with request id zero");
  }
  {
    const pa::Frame frame{
        pa::FrameHeader{pa::WireDirection::request, pa::MessageKind::info, 1, 1},
        {}};
    require_error(pa::encode_frame_v2(frame), pa::WireError::invalid_frame,
                  "encoded a frame whose declared size is not its payload's");
  }
}

// Truncation at every field of the two changed payloads, plus the bounds and the
// hostile counts. **Each block case is truncated one octet into the stamp**,
// which is the field version two added and therefore the one a decoder could
// omit while still reading a well-formed version-one payload.
void verify_payload_rejections() {
  {
    const auto raw_chain = counting_chain();
    p::Bytes payload(raw_chain.begin(), raw_chain.end());
    require_error(pa::decode_request_frame_v2(
                      frame_bytes(pa::MessageKind::init_chain, 1, payload)),
                  pa::WireError::invalid_payload,
                  "InitChain without a height accepted");
    append_u64(payload, 1);
    require_error(pa::decode_request_frame_v2(
                      frame_bytes(pa::MessageKind::init_chain, 1, payload)),
                  pa::WireError::invalid_payload,
                  "InitChain without a genesis stamp accepted");
    payload.push_back(0);
    require_error(pa::decode_request_frame_v2(
                      frame_bytes(pa::MessageKind::init_chain, 1, payload)),
                  pa::WireError::invalid_payload,
                  "InitChain with a partial genesis stamp accepted");
  }
  {
    // The whole of version one's InitChain payload, which version two must
    // refuse: its app-state blob is read as the top four octets of a stamp and
    // the frame then ends early.
    const auto raw_chain = counting_chain();
    p::Bytes payload(raw_chain.begin(), raw_chain.end());
    append_u64(payload, 1);
    append_blob(payload, p::Bytes{'"', 'v', '1', '"'});
    require_error(pa::decode_request_frame_v2(
                      frame_bytes(pa::MessageKind::init_chain, 1, payload)),
                  pa::WireError::invalid_payload,
                  "a version-one InitChain payload accepted");
  }
  {
    const auto raw_chain = counting_chain();
    p::Bytes payload(raw_chain.begin(), raw_chain.end());
    append_u64(payload, 1);
    append_u64(payload, kStamp);
    append_blob(payload, p::Bytes(4'097, 'x'));
    require_error(pa::decode_request_frame_v2(
                      frame_bytes(pa::MessageKind::init_chain, 1, payload)),
                  pa::WireError::resource_limit,
                  "oversized app state accepted");
  }
  {
    p::Bytes payload;
    append_u64(payload, 4);
    require_error(pa::decode_request_frame_v2(frame_bytes(
                      pa::MessageKind::process_proposal, 1, payload)),
                  pa::WireError::invalid_payload,
                  "a block request without a stamp accepted");
    payload.push_back(0);
    require_error(pa::decode_request_frame_v2(frame_bytes(
                      pa::MessageKind::finalize_block, 1, payload)),
                  pa::WireError::invalid_payload,
                  "a block request with a partial stamp accepted");
  }
  {
    // Version one's block payload exactly: a height and a transaction list with
    // no stamp between them. The count is read as the stamp's top four octets.
    p::Bytes payload;
    append_u64(payload, 4);
    append_transactions(payload, {p::Bytes{1, 2, 3}});
    require_error(pa::decode_request_frame_v2(frame_bytes(
                      pa::MessageKind::finalize_block, 1, payload)),
                  pa::WireError::invalid_payload,
                  "a version-one block payload accepted");
  }
  {
    p::Bytes payload;
    append_u64(payload, 4);
    append_u64(payload, kStamp);
    append_u32(payload, static_cast<std::uint32_t>(pa::kMaximumBlockInputsV2 + 1));
    require_error(pa::decode_request_frame_v2(frame_bytes(
                      pa::MessageKind::process_proposal, 1, payload)),
                  pa::WireError::resource_limit,
                  "a raw count past the kernel's bound accepted");
  }
  {
    p::Bytes payload;
    append_u64(payload, 4);
    append_u64(payload, kStamp);
    append_u32(payload, 1);
    append_u32(payload, 0xFFFFFFFF);
    require_error(pa::decode_request_frame_v2(frame_bytes(
                      pa::MessageKind::process_proposal, 1, payload)),
                  pa::WireError::resource_limit,
                  "a hostile transaction length accepted");
  }
  {
    p::Bytes payload;
    append_u64(payload, 4);
    append_u64(payload, kStamp);
    append_u32(payload, 1);
    append_u32(payload, 3);
    payload.push_back(1);
    require_error(pa::decode_request_frame_v2(frame_bytes(
                      pa::MessageKind::process_proposal, 1, payload)),
                  pa::WireError::invalid_payload, "truncated blob accepted");
  }
  {
    // Trailing bytes after a complete payload, which the frame's own length
    // admits and only the decoder's exhaustion check refuses.
    p::Bytes payload;
    append_u64(payload, 4);
    append_u64(payload, kStamp);
    append_transactions(payload, {});
    payload.push_back(0);
    require_error(pa::decode_request_frame_v2(frame_bytes(
                      pa::MessageKind::finalize_block, 1, payload)),
                  pa::WireError::invalid_payload,
                  "a trailing payload byte accepted");
  }
  {
    auto nonempty = frame_bytes(pa::MessageKind::info, 1, {0});
    require_error(pa::decode_request_frame_v2(nonempty),
                  pa::WireError::invalid_payload, "nonempty Info accepted");
  }
  {
    auto nonempty = frame_bytes(pa::MessageKind::commit, 1, {0});
    require_error(pa::decode_request_frame_v2(nonempty),
                  pa::WireError::invalid_payload, "nonempty Commit accepted");
  }
}

}  // namespace

int main() {
  try {
    verify_header_and_frame();
    verify_the_versions_refuse_each_other();
    verify_request_payloads();
    verify_frame_rejections();
    verify_payload_rejections();
    std::cout << "Application wire v2 tests: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "Application wire v2 tests: failed: " << error.what() << '\n';
    return 1;
  }
}
