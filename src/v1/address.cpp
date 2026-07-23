#include "protocol/v1/address.hpp"

#include <algorithm>
#include <array>
#include <cstdint>
#include <span>
#include <string>
#include <string_view>
#include <vector>

namespace protocol::v1 {
namespace {

constexpr std::string_view kCharset =
    "qpzry9x8gf2tvdw0s3jn54khce6mua7l";
constexpr std::uint32_t kBech32mConstant = 0x2bc830a3U;
constexpr std::array<std::uint32_t, 5> kGenerators{
    0x3b6a57b2U,
    0x26508e6dU,
    0x1ea119faU,
    0x3d4233ddU,
    0x2a1462b3U,
};

bool valid_hrp(std::string_view hrp) {
  return !hrp.empty() && hrp.size() <= 20 &&
         std::all_of(hrp.begin(), hrp.end(), [](char character) {
           return (character >= 'a' && character <= 'z') ||
                  (character >= '0' && character <= '9');
         });
}

std::vector<std::uint8_t> expand_hrp(std::string_view hrp) {
  std::vector<std::uint8_t> expanded;
  expanded.reserve(hrp.size() * 2 + 1);
  for (const char character : hrp) {
    expanded.push_back(static_cast<std::uint8_t>(character) >> 5U);
  }
  expanded.push_back(0);
  for (const char character : hrp) {
    expanded.push_back(static_cast<std::uint8_t>(character) & 31U);
  }
  return expanded;
}

std::uint32_t polymod(std::span<const std::uint8_t> values) {
  std::uint32_t checksum = 1;
  for (const auto value : values) {
    const auto top = checksum >> 25U;
    checksum = ((checksum & 0x1ffffffU) << 5U) ^ value;
    for (std::size_t index = 0; index < kGenerators.size(); ++index) {
      if (((top >> index) & 1U) != 0U) checksum ^= kGenerators[index];
    }
  }
  return checksum;
}

std::vector<std::uint8_t> to_base32(
    std::span<const std::uint8_t> payload) {
  std::vector<std::uint8_t> encoded;
  encoded.reserve((payload.size() * 8 + 4) / 5);
  std::uint32_t accumulator = 0;
  unsigned bit_count = 0;
  for (const auto value : payload) {
    accumulator = ((accumulator << 8U) | value) & 0xfffU;
    bit_count += 8;
    while (bit_count >= 5) {
      bit_count -= 5;
      encoded.push_back(
          static_cast<std::uint8_t>((accumulator >> bit_count) & 31U));
    }
  }
  if (bit_count != 0) {
    encoded.push_back(
        static_cast<std::uint8_t>((accumulator << (5 - bit_count)) & 31U));
  }
  return encoded;
}

bool from_base32(std::span<const std::uint8_t> encoded, Bytes& payload) {
  payload.clear();
  payload.reserve(encoded.size() * 5 / 8);
  std::uint32_t accumulator = 0;
  unsigned bit_count = 0;
  for (const auto value : encoded) {
    if (value > 31) return false;
    accumulator = ((accumulator << 5U) | value) & 0xfffU;
    bit_count += 5;
    if (bit_count >= 8) {
      bit_count -= 8;
      payload.push_back(
          static_cast<std::uint8_t>((accumulator >> bit_count) & 0xffU));
    }
  }
  if (bit_count >= 5) return false;
  return bit_count == 0 ||
         ((accumulator << (8 - bit_count)) & 0xffU) == 0;
}

void append_checksum(std::string_view hrp,
                     std::vector<std::uint8_t>& data) {
  auto values = expand_hrp(hrp);
  values.insert(values.end(), data.begin(), data.end());
  values.resize(values.size() + 6, 0);
  const auto checksum = polymod(values) ^ kBech32mConstant;
  for (int index = 0; index < 6; ++index) {
    data.push_back(static_cast<std::uint8_t>(
        (checksum >> (5 * (5 - index))) & 31U));
  }
}

bool valid_checksum(std::string_view hrp,
                    std::span<const std::uint8_t> data) {
  auto values = expand_hrp(hrp);
  values.insert(values.end(), data.begin(), data.end());
  return polymod(values) == kBech32mConstant;
}

std::optional<std::vector<std::uint8_t>> decode_characters(
    std::string_view encoded) {
  std::vector<std::uint8_t> values;
  values.reserve(encoded.size());
  for (const char character : encoded) {
    const auto position = kCharset.find(character);
    if (position == std::string_view::npos) return std::nullopt;
    values.push_back(static_cast<std::uint8_t>(position));
  }
  return values;
}

}  // namespace

std::optional<std::string> encode_address(const AccountId& account_id,
                                          std::string_view hrp) {
  if (!valid_hrp(hrp)) return std::nullopt;

  Bytes payload{1};
  payload.insert(payload.end(), account_id.begin(), account_id.end());
  auto data = to_base32(payload);
  append_checksum(hrp, data);

  std::string address(hrp);
  address.reserve(hrp.size() + 1 + data.size());
  address.push_back('1');
  for (const auto value : data) address.push_back(kCharset[value]);
  if (address.size() > 90) return std::nullopt;
  return address;
}

std::optional<AccountId> decode_address(std::string_view address,
                                        std::string_view expected_hrp) {
  if (!valid_hrp(expected_hrp)) return std::nullopt;
  if (address.empty() || address.size() > 90) {
    return std::nullopt;
  }

  const auto separator = address.rfind('1');
  if (separator == std::string_view::npos || separator == 0 ||
      separator > 20 || address.size() - separator - 1 < 6) {
    return std::nullopt;
  }
  const auto embedded_hrp = address.substr(0, separator);
  if (!valid_hrp(embedded_hrp)) return std::nullopt;

  const auto encoded = decode_characters(address.substr(separator + 1));
  if (!encoded) return std::nullopt;
  if (!valid_checksum(embedded_hrp, *encoded)) {
    return std::nullopt;
  }
  if (embedded_hrp != expected_hrp) return std::nullopt;

  constexpr std::size_t kChecksumSize = 6;
  Bytes payload;
  if (!from_base32(
          std::span<const std::uint8_t>(*encoded)
              .first(encoded->size() - kChecksumSize),
          payload) ||
      payload.size() != 33 || payload.front() != 1) {
    return std::nullopt;
  }

  Hash identifier{};
  std::copy(payload.begin() + 1, payload.end(), identifier.begin());
  const AccountId account_id(identifier);
  const auto canonical = encode_address(account_id, expected_hrp);
  if (!canonical || *canonical != address) return std::nullopt;
  return account_id;
}

}  // namespace protocol::v1
