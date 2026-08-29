#pragma once

// Byte-appending helpers shared by the version-six codec translation units.
//
// Every field in this contract is fixed-width big-endian, so these functions are
// the whole encoding vocabulary. Reads reuse the version-one kernel's bounded
// readers rather than restating them, because a second set of bounds checks is a
// second place for one to be wrong.

#include "protocol/v7/economy.hpp"

#include "../v1/encoding.hpp"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <span>
#include <string_view>

namespace protocol::v7::internal {

inline void append_u8(Bytes& target, std::uint8_t value) {
  target.push_back(value);
}

inline void append_u16(Bytes& target, std::uint16_t value) {
  target.push_back(static_cast<std::uint8_t>(value >> 8U));
  target.push_back(static_cast<std::uint8_t>(value));
}

inline void append_u32(Bytes& target, std::uint32_t value) {
  for (int shift = 24; shift >= 0; shift -= 8) {
    target.push_back(static_cast<std::uint8_t>(value >> shift));
  }
}

inline void append_u64(Bytes& target, std::uint64_t value) {
  for (int shift = 56; shift >= 0; shift -= 8) {
    target.push_back(static_cast<std::uint8_t>(value >> shift));
  }
}

inline void append(Bytes& target, std::span<const std::uint8_t> source) {
  target.insert(target.end(), source.begin(), source.end());
}

// `Hash` and `Octets32` are the same 32-octet array, so this one overload
// covers a chain identifier, an escrow identifier, a key, and a digest alike.
inline void append(Bytes& target, const Octets32& source) {
  target.insert(target.end(), source.begin(), source.end());
}

// `bytes(x)` from `protocol-primitives-v1`: a `u32` length and that many
// octets, which is what makes the boundary between an economy key and its value
// explicit rather than inferred from the entry kind.
inline void append_length_prefixed(Bytes& target,
                                   std::span<const std::uint8_t> source) {
  append_u32(target, static_cast<std::uint32_t>(source.size()));
  append(target, source);
}

// Each message opens with its domain label, length-prefixed, exactly as
// `protocol-primitives-v1` defines `D(label)`.
inline void append_domain(Bytes& target, std::string_view label) {
  target.push_back(static_cast<std::uint8_t>(label.size()));
  target.insert(target.end(), label.begin(), label.end());
}

inline bool copy32(std::span<const std::uint8_t> source, Octets32& target) {
  if (source.size() != target.size()) return false;
  std::copy(source.begin(), source.end(), target.begin());
  return true;
}

inline bool all_zero(std::span<const std::uint8_t> value) {
  return std::all_of(value.begin(), value.end(),
                     [](std::uint8_t octet) { return octet == 0; });
}

inline std::optional<std::uint8_t> read_u8(std::span<const std::uint8_t> input,
                                           std::size_t offset) {
  if (offset >= input.size()) return std::nullopt;
  return input[offset];
}

using protocol::v1::internal::read_u16;
using protocol::v1::internal::read_u32;
using protocol::v1::internal::read_u64;

// The accepted RFC 9162 ordered tree, parameterised by domain prefix. One
// implementation serves the economy tree, the accounts tree, and version one's
// ordered transaction tree, and each is pinned by a different accepted vector
// file. Defined in `economy_tree.cpp` beside the roots that need it.
Hash merkle_root(std::span<const Bytes> leaves, std::string_view prefix);

// Every discriminator octet, as a one-byte prefix on its key.
inline Bytes key_prefix(Entry entry) {
  return Bytes{static_cast<std::uint8_t>(entry)};
}

}  // namespace protocol::v7::internal
