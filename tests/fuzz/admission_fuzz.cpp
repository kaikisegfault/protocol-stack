#include "protocol/v1/admission.hpp"

#include <sodium.h>

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <span>
#include <string_view>
#include <variant>

namespace p = protocol::v1;

namespace {

p::ChainId selected_chain(std::span<const std::uint8_t> input) {
  p::Hash bytes{};
  if (input.size() == 200 && (input.back() & 1U) != 0) {
    std::copy_n(input.begin() + 7, bytes.size(), bytes.begin());
  }
  return p::ChainId{bytes};
}

void require_deterministic(std::span<const std::uint8_t> input,
                           const p::ChainId& chain_id) {
  const auto first = p::admit_transfer(input, chain_id);
  const auto second = p::admit_transfer(input, chain_id);
  if (first.index() != second.index()) std::abort();
  if (const auto* first_error = std::get_if<p::AdmissionError>(&first)) {
    const auto* second_error = std::get_if<p::AdmissionError>(&second);
    if (second_error == nullptr || *first_error != *second_error) {
      std::abort();
    }
    return;
  }
  const auto& first_transfer = std::get<p::Transfer>(first);
  const auto& second_transfer = std::get<p::Transfer>(second);
  if (first_transfer.sender_id != second_transfer.sender_id ||
      first_transfer.transaction_id != second_transfer.transaction_id ||
      first_transfer.nonce != second_transfer.nonce ||
      first_transfer.recipient != second_transfer.recipient ||
      first_transfer.amount != second_transfer.amount ||
      first_transfer.fee_limit != second_transfer.fee_limit ||
      first_transfer.valid_until != second_transfer.valid_until) {
    std::abort();
  }
}

void require_valid_structured(std::span<const std::uint8_t> input) {
  std::array<std::uint8_t, crypto_sign_SEEDBYTES> seed{};
  std::copy_n(input.begin(), std::min(input.size(), seed.size()),
              seed.begin());
  std::array<std::uint8_t, crypto_sign_PUBLICKEYBYTES> public_key{};
  std::array<std::uint8_t, crypto_sign_SECRETKEYBYTES> secret_key{};
  if (sodium_init() < 0 ||
      crypto_sign_seed_keypair(public_key.data(), secret_key.data(),
                               seed.data()) != 0) {
    std::abort();
  }

  p::Bytes shaped(200);
  const auto copied = std::min(input.size(), shaped.size());
  if (copied != 0) {
    std::copy_n(input.begin(), copied, shaped.begin());
  }
  shaped[0] = 'P';
  shaped[1] = 'S';
  shaped[2] = 'T';
  shaped[3] = 'X';
  shaped[4] = 0;
  shaped[5] = 1;
  shaped[6] = 1;
  shaped[39] = 1;
  std::copy(public_key.begin(), public_key.end(), shaped.begin() + 40);

  constexpr std::string_view label = "protocol-stack:v1:tx-sign";
  p::Bytes message{static_cast<std::uint8_t>(label.size())};
  message.insert(message.end(), label.begin(), label.end());
  message.insert(message.end(), shaped.begin(), shaped.begin() + 136);
  unsigned long long signature_size = 0;
  if (crypto_sign_detached(shaped.data() + 136, &signature_size,
                           message.data(), message.size(),
                           secret_key.data()) != 0 ||
      signature_size != crypto_sign_BYTES) {
    std::abort();
  }

  p::Hash chain_bytes{};
  std::copy_n(shaped.begin() + 7, chain_bytes.size(),
              chain_bytes.begin());
  const p::ChainId chain_id{chain_bytes};
  require_deterministic(shaped, chain_id);
  const auto admission =
      p::admit_transfer(shaped, chain_id);
  if (!std::holds_alternative<p::Transfer>(admission)) std::abort();
}

}  // namespace

extern "C" int LLVMFuzzerTestOneInput(const std::uint8_t* data,
                                      std::size_t size) {
  const std::span<const std::uint8_t> input{data, size};
  require_deterministic(input, selected_chain(input));
  require_valid_structured(input);
  return 0;
}
