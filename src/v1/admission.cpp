#include "protocol/v1/admission.hpp"

#include "protocol/v1/crypto.hpp"

#include <algorithm>
#include <array>
#include <limits>

namespace protocol::v1 {
namespace {

constexpr std::size_t kUnsignedSize = 136;
constexpr std::size_t kSignedSize = 200;

bool valid_shape(std::span<const std::uint8_t> raw) {
  constexpr std::array<std::uint8_t, 4> magic{'P', 'S', 'T', 'X'};
  return raw.size() == kSignedSize &&
         std::equal(magic.begin(), magic.end(), raw.begin()) &&
         raw[4] == 0 && raw[5] == 1 && raw[6] == 1 && raw[39] == 1;
}

Hash fixed_32(std::span<const std::uint8_t> raw, std::size_t offset) {
  Hash result{};
  std::copy_n(raw.begin() + offset, result.size(), result.begin());
  return result;
}

std::uint64_t read_u64(std::span<const std::uint8_t> raw,
                       std::size_t offset) {
  std::uint64_t result = 0;
  for (std::size_t index = 0; index < 8; ++index) {
    result = (result << 8U) | raw[offset + index];
  }
  return result;
}

Hash sender_id(std::span<const std::uint8_t> public_key) {
  Bytes payload{1};
  payload.insert(payload.end(), public_key.begin(), public_key.end());
  return hash("protocol-stack:v1:account", payload);
}

Bytes signing_message(std::span<const std::uint8_t> unsigned_transaction) {
  constexpr std::string_view label = "protocol-stack:v1:tx-sign";
  Bytes message{static_cast<std::uint8_t>(label.size())};
  message.insert(message.end(), label.begin(), label.end());
  message.insert(message.end(), unsigned_transaction.begin(),
                 unsigned_transaction.end());
  return message;
}

}  // namespace

Admission admit_transfer(std::span<const std::uint8_t> raw,
                         const Hash& expected_chain_id) {
  if (!valid_shape(raw)) return AdmissionError::malformed_transaction;
  if (fixed_32(raw, 7) != expected_chain_id) {
    return AdmissionError::wrong_chain;
  }
  const auto public_key = raw.subspan(40, 32);
  const auto message = signing_message(raw.first(kUnsignedSize));
  if (!strict_ed25519_verify(public_key, message, raw.subspan(136, 64))) {
    return AdmissionError::invalid_signature;
  }
  return Transfer{
      sender_id(public_key),
      hash("protocol-stack:v1:tx-id", raw),
      read_u64(raw, 72),
      fixed_32(raw, 80),
      read_u64(raw, 112),
      read_u64(raw, 120),
      read_u64(raw, 128),
  };
}

}  // namespace protocol::v1
