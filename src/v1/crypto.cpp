#include "protocol/v1/crypto.hpp"

#include <sodium.h>

#include <limits>
#include <stdexcept>

namespace protocol::v1 {
namespace {

Bytes domain(std::string_view label) {
  if (label.size() > std::numeric_limits<std::uint8_t>::max()) {
    throw std::invalid_argument("domain label exceeds u8");
  }
  Bytes encoded{static_cast<std::uint8_t>(label.size())};
  encoded.insert(encoded.end(), label.begin(), label.end());
  return encoded;
}

void require_sodium() {
  static const int initialization_result = sodium_init();
  if (initialization_result < 0) {
    throw std::runtime_error("libsodium initialization failure");
  }
}

}  // namespace

Hash hash(std::string_view domain_label,
          std::span<const std::uint8_t> payload) {
  require_sodium();
  auto input = domain(domain_label);
  input.insert(input.end(), payload.begin(), payload.end());
  Hash output{};
  if (crypto_hash_sha256(output.data(), input.data(), input.size()) != 0) {
    throw std::runtime_error("libsodium SHA-256 failure");
  }
  return output;
}

bool strict_ed25519_verify(std::span<const std::uint8_t> public_key,
                           std::span<const std::uint8_t> message,
                           std::span<const std::uint8_t> signature) {
  require_sodium();
  if (public_key.size() != crypto_sign_PUBLICKEYBYTES ||
      signature.size() != crypto_sign_BYTES) {
    return false;
  }
  return crypto_sign_verify_detached(signature.data(), message.data(),
                                     message.size(), public_key.data()) == 0;
}

}  // namespace protocol::v1
