#pragma once

#include <cstdint>
#include <fstream>
#include <map>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

extern "C" {
int crypto_hash_sha256(unsigned char* output, const unsigned char* input,
                       unsigned long long input_size);
}

namespace protocol_vectors {

using Bytes = std::vector<unsigned char>;
using Values = std::map<std::string, std::string>;

inline void require(bool condition, std::string_view message) {
  if (!condition) {
    throw std::runtime_error(std::string(message));
  }
}

inline Bytes hex_decode(std::string_view value) {
  require(value.size() % 2 == 0, "odd-length hex");
  auto nibble = [](char c) -> unsigned char {
    if (c >= '0' && c <= '9') return static_cast<unsigned char>(c - '0');
    if (c >= 'a' && c <= 'f') return static_cast<unsigned char>(c - 'a' + 10);
    throw std::runtime_error("non-canonical hex");
  };
  Bytes result;
  result.reserve(value.size() / 2);
  for (std::size_t i = 0; i < value.size(); i += 2) {
    result.push_back(static_cast<unsigned char>(
        (nibble(value[i]) << 4U) | nibble(value[i + 1])));
  }
  return result;
}

inline Bytes ascii(std::string_view value) {
  return Bytes(value.begin(), value.end());
}

inline void append(Bytes& target, const Bytes& source) {
  target.insert(target.end(), source.begin(), source.end());
}

inline void append_u16(Bytes& target, std::uint16_t value) {
  target.push_back(static_cast<unsigned char>(value >> 8U));
  target.push_back(static_cast<unsigned char>(value));
}

inline void append_u64(Bytes& target, std::uint64_t value) {
  for (int shift = 56; shift >= 0; shift -= 8) {
    target.push_back(static_cast<unsigned char>(value >> shift));
  }
}

inline std::uint64_t read_u64(const Bytes& value, std::size_t offset) {
  require(offset + 8 <= value.size(), "truncated u64");
  std::uint64_t result = 0;
  for (std::size_t i = 0; i < 8; ++i) {
    result = (result << 8U) | value[offset + i];
  }
  return result;
}

inline Bytes domain(std::string_view label) {
  require(label.size() < 256, "domain label too long");
  Bytes result{static_cast<unsigned char>(label.size())};
  append(result, ascii(label));
  return result;
}

inline Bytes sha256(const Bytes& input) {
  Bytes result(32);
  require(crypto_hash_sha256(result.data(), input.data(), input.size()) == 0,
          "libsodium SHA-256 failure");
  return result;
}

inline Bytes hash(std::string_view label, const Bytes& payload = {}) {
  auto input = domain(label);
  append(input, payload);
  return sha256(input);
}

inline Bytes merkle_range(const std::vector<Bytes>& items, std::size_t begin,
                          std::size_t end, std::string_view prefix) {
  const auto count = end - begin;
  require(count > 0, "empty Merkle range");
  const std::string base = "protocol-stack:v1:" + std::string(prefix);
  if (count == 1) return hash(base + "-leaf", items[begin]);
  std::size_t split = 1;
  while ((split << 1U) < count) split <<= 1U;
  auto children = merkle_range(items, begin, begin + split, prefix);
  append(children, merkle_range(items, begin + split, end, prefix));
  return hash(base + "-node", children);
}

inline Bytes merkle(const std::vector<Bytes>& items, std::string_view prefix) {
  if (items.empty()) {
    return hash("protocol-stack:v1:" + std::string(prefix) + "-empty");
  }
  return merkle_range(items, 0, items.size(), prefix);
}

inline std::vector<unsigned char> convert_bits(const Bytes& input) {
  std::uint32_t accumulator = 0;
  int bit_count = 0;
  std::vector<unsigned char> output;
  for (const auto value : input) {
    accumulator = (accumulator << 8U) | value;
    bit_count += 8;
    while (bit_count >= 5) {
      bit_count -= 5;
      output.push_back(
          static_cast<unsigned char>((accumulator >> bit_count) & 31U));
    }
  }
  if (bit_count != 0) {
    output.push_back(
        static_cast<unsigned char>((accumulator << (5 - bit_count)) & 31U));
  }
  return output;
}

inline std::uint32_t bech32_polymod(
    const std::vector<unsigned char>& values) {
  constexpr std::uint32_t generators[] = {
      0x3b6a57b2U, 0x26508e6dU, 0x1ea119faU, 0x3d4233ddU, 0x2a1462b3U};
  std::uint32_t checksum = 1;
  for (const auto value : values) {
    const auto top = checksum >> 25U;
    checksum = ((checksum & 0x1ffffffU) << 5U) ^ value;
    for (std::size_t i = 0; i < 5; ++i) {
      if (((top >> i) & 1U) != 0U) checksum ^= generators[i];
    }
  }
  return checksum;
}

inline std::vector<unsigned char> hrp_expand(std::string_view hrp) {
  std::vector<unsigned char> result;
  for (const auto c : hrp) result.push_back(static_cast<unsigned char>(c >> 5));
  result.push_back(0);
  for (const auto c : hrp) result.push_back(static_cast<unsigned char>(c & 31));
  return result;
}

inline std::string bech32m(std::string_view hrp, const Bytes& payload) {
  static constexpr std::string_view charset =
      "qpzry9x8gf2tvdw0s3jn54khce6mua7l";
  auto data = convert_bits(payload);
  auto values = hrp_expand(hrp);
  values.insert(values.end(), data.begin(), data.end());
  values.resize(values.size() + 6, 0);
  const auto checksum = bech32_polymod(values) ^ 0x2bc830a3U;
  std::string result(hrp);
  result.push_back('1');
  for (const auto value : data) result.push_back(charset[value]);
  for (int i = 0; i < 6; ++i) {
    result.push_back(charset[(checksum >> (5 * (5 - i))) & 31U]);
  }
  return result;
}

inline bool valid_bech32m(std::string_view address, std::string_view hrp) {
  static constexpr std::string_view charset =
      "qpzry9x8gf2tvdw0s3jn54khce6mua7l";
  if (address.size() > 90 ||
      address.substr(0, hrp.size() + 1) != std::string(hrp) + "1") {
    return false;
  }
  std::vector<unsigned char> data;
  for (const auto c : address.substr(hrp.size() + 1)) {
    const auto position = charset.find(c);
    if (position == std::string_view::npos) return false;
    data.push_back(static_cast<unsigned char>(position));
  }
  auto values = hrp_expand(hrp);
  values.insert(values.end(), data.begin(), data.end());
  return data.size() >= 6 && bech32_polymod(values) == 0x2bc830a3U;
}

inline Values load_values(const std::string& path) {
  std::ifstream input(path);
  require(input.good(), "cannot open vector file");
  Values values;
  std::string line;
  while (std::getline(input, line)) {
    if (line.empty() || line.front() == '#') continue;
    const auto separator = line.find('=');
    require(separator != std::string::npos, "malformed vector line");
    require(values.emplace(line.substr(0, separator),
                           line.substr(separator + 1))
                .second,
            "duplicate vector key");
  }
  return values;
}

}  // namespace protocol_vectors
