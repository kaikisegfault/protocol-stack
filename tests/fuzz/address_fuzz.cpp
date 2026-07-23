#include "protocol/v1/address.hpp"

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <string>
#include <string_view>

namespace p = protocol::v1;

namespace {

constexpr std::size_t kMaximumRawSize = 256;
constexpr std::size_t kMaximumMutations = 256;
constexpr std::string_view kHrpCharacters =
    "abcdefghijklmnopqrstuvwxyz0123456789";

void require_deterministic(std::string_view address,
                           std::string_view hrp) {
  const auto first = p::decode_address(address, hrp);
  const auto second = p::decode_address(address, hrp);
  if (first != second) std::abort();
}

std::string_view selected_hrp(const std::uint8_t* data, std::size_t size,
                              std::array<char, 20>& storage) {
  if (size == 0) return "psdev";
  const auto length = static_cast<std::size_t>(data[0] % storage.size()) + 1;
  for (std::size_t index = 0; index < length; ++index) {
    storage[index] =
        kHrpCharacters[data[index % size] % kHrpCharacters.size()];
  }
  return {storage.data(), length};
}

p::AccountId selected_account(const std::uint8_t* data, std::size_t size) {
  p::Hash identifier{};
  const auto copied = std::min(size, identifier.size());
  if (copied != 0) {
    std::copy_n(data, copied, identifier.begin());
  }
  return p::AccountId{identifier};
}

std::string require_valid_round_trip(const p::AccountId& account_id,
                                     std::string_view hrp) {
  const auto first_encoding = p::encode_address(account_id, hrp);
  const auto second_encoding = p::encode_address(account_id, hrp);
  if (!first_encoding || first_encoding != second_encoding) std::abort();

  require_deterministic(*first_encoding, hrp);
  const auto decoded = p::decode_address(*first_encoding, hrp);
  if (!decoded || *decoded != account_id) std::abort();

  const auto canonical = p::encode_address(*decoded, hrp);
  if (!canonical || *canonical != *first_encoding) std::abort();
  return *first_encoding;
}

}  // namespace

extern "C" int LLVMFuzzerTestOneInput(const std::uint8_t* data,
                                      std::size_t size) {
  const auto bounded_size = std::min(size, kMaximumRawSize);
  const char* characters =
      bounded_size == 0 ? "" : reinterpret_cast<const char*>(data);
  std::array<char, 20> hrp_storage{};
  const auto hrp = selected_hrp(data, bounded_size, hrp_storage);
  require_deterministic({characters, bounded_size}, hrp);

  auto structured =
      require_valid_round_trip(selected_account(data, bounded_size), hrp);
  const auto mutations =
      std::min(bounded_size / 2, kMaximumMutations);
  for (std::size_t index = 0; index < mutations; ++index) {
    const auto offset = static_cast<std::size_t>(data[index * 2]) %
                        structured.size();
    structured[offset] = static_cast<char>(data[index * 2 + 1]);
  }
  require_deterministic(structured, hrp);
  return 0;
}
