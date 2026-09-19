// The version-two frame decoder against raw and structured input.
//
// Version one's target is kept and this one is added rather than replacing it:
// both decoders are live while the migration runs, and the two differ by exactly
// one comparison, so a mutation that walks the version octet is the interesting
// one and it is only interesting against a decoder that would otherwise have
// accepted the frame.
//
// The structured half flips one octet of a valid version-two frame, which is
// what reaches the payload decoders at all — a purely random buffer almost never
// gets past the magic.

#include "protocol/application/wire_v2.hpp"

#include <cstddef>
#include <cstdint>
#include <span>
#include <utility>
#include <variant>

namespace pa = protocol::application;
namespace pv1 = protocol::v1;

namespace {

// A block request, rather than version one's empty Info frame: it is the payload
// that gained a field, so it is the one whose decoder has something to get
// wrong.
const pv1::Bytes& valid_frame() {
  static const auto bytes = [] {
    pv1::Bytes payload;
    for (int shift = 56; shift >= 0; shift -= 8) {
      payload.push_back(static_cast<std::uint8_t>(4ULL >> shift));
    }
    for (int shift = 56; shift >= 0; shift -= 8) {
      payload.push_back(
          static_cast<std::uint8_t>(1'768'435'290'000ULL >> shift));
    }
    // One transaction of three octets.
    payload.insert(payload.end(), {0, 0, 0, 1, 0, 0, 0, 3, 1, 2, 3});
    const auto size = static_cast<std::uint32_t>(payload.size());
    auto encoded = pa::encode_frame_v2(pa::Frame{
        pa::FrameHeader{
            pa::WireDirection::request,
            pa::MessageKind::finalize_block,
            1,
            size,
        },
        std::move(payload),
    });
    if (!std::holds_alternative<pv1::Bytes>(encoded)) {
      __builtin_trap();
    }
    return std::get<pv1::Bytes>(std::move(encoded));
  }();
  return bytes;
}

void require_valid_seed() {
  if (!std::holds_alternative<pa::DecodedRequestV2>(
          pa::decode_request_frame_v2(valid_frame()))) {
    __builtin_trap();
  }
}

}  // namespace

extern "C" int LLVMFuzzerTestOneInput(const std::uint8_t* data,
                                      std::size_t size) {
  const auto input = std::span<const std::uint8_t>(data, size);
  (void)pa::decode_frame_v2(input);
  (void)pa::decode_request_frame_v2(input);
  if (size >= pa::kWireHeaderSize) {
    (void)pa::decode_frame_header_v2(input.first(pa::kWireHeaderSize));
  }
  require_valid_seed();

  if (size != 0) {
    auto structured = valid_frame();
    const auto index = static_cast<std::size_t>(data[0]) % structured.size();
    structured[index] ^= data[size - 1];
    (void)pa::decode_request_frame_v2(structured);
  }
  return 0;
}
