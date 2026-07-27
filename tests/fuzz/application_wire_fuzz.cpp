#include "protocol/application/wire_v1.hpp"

#include <cstddef>
#include <cstdint>
#include <span>
#include <utility>
#include <variant>

namespace pa = protocol::application;
namespace pv1 = protocol::v1;

namespace {

const pv1::Bytes& valid_frame() {
  static const auto bytes = [] {
    auto encoded = pa::encode_frame(pa::Frame{
        pa::FrameHeader{
            pa::WireDirection::request,
            pa::MessageKind::info,
            1,
            0,
        },
        {},
    });
    if (!std::holds_alternative<pv1::Bytes>(encoded)) {
      __builtin_trap();
    }
    return std::get<pv1::Bytes>(std::move(encoded));
  }();
  return bytes;
}

void require_valid_seed() {
  if (!std::holds_alternative<pa::DecodedRequest>(
          pa::decode_request_frame(valid_frame()))) {
    __builtin_trap();
  }
}

}  // namespace

extern "C" int LLVMFuzzerTestOneInput(
    const std::uint8_t* data,
    std::size_t size) {
  const auto input = std::span<const std::uint8_t>(data, size);
  (void)pa::decode_frame(input);
  (void)pa::decode_request_frame(input);
  if (size >= pa::kWireHeaderSize) {
    (void)pa::decode_frame_header(input.first(pa::kWireHeaderSize));
  }
  require_valid_seed();

  if (size != 0) {
    auto structured = valid_frame();
    const auto index =
        static_cast<std::size_t>(data[0]) % structured.size();
    structured[index] ^= data[size - 1];
    (void)pa::decode_request_frame(structured);
  }
  return 0;
}
