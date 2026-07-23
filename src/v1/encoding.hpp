#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>

namespace protocol::v1::internal {

template <std::size_t Size>
std::optional<std::array<std::uint8_t, Size>> read_fixed(
    std::span<const std::uint8_t> input, std::size_t offset) {
  if (offset > input.size() || Size > input.size() - offset) {
    return std::nullopt;
  }
  std::array<std::uint8_t, Size> result{};
  for (std::size_t index = 0; index < Size; ++index) {
    result[index] = input[offset + index];
  }
  return result;
}

inline std::optional<std::uint16_t> read_u16(
    std::span<const std::uint8_t> input, std::size_t offset) {
  if (offset > input.size() || 2 > input.size() - offset) {
    return std::nullopt;
  }
  return static_cast<std::uint16_t>(
      (static_cast<std::uint16_t>(input[offset]) << 8U) |
      static_cast<std::uint16_t>(input[offset + 1]));
}

inline std::optional<std::uint32_t> read_u32(
    std::span<const std::uint8_t> input, std::size_t offset) {
  if (offset > input.size() || 4 > input.size() - offset) {
    return std::nullopt;
  }
  std::uint32_t result = 0;
  for (std::size_t index = 0; index < 4; ++index) {
    result = (result << 8U) | input[offset + index];
  }
  return result;
}

inline std::optional<std::uint64_t> read_u64(
    std::span<const std::uint8_t> input, std::size_t offset) {
  if (offset > input.size() || 8 > input.size() - offset) {
    return std::nullopt;
  }
  std::uint64_t result = 0;
  for (std::size_t index = 0; index < 8; ++index) {
    result = (result << 8U) | input[offset + index];
  }
  return result;
}

}  // namespace protocol::v1::internal
