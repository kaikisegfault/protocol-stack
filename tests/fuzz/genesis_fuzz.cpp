#include "protocol/v1/ledger.hpp"

#include "../../tools/protocol-vectors/vector_common.hpp"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <span>
#include <variant>

namespace pv = protocol_vectors;
namespace p = protocol::v1;

namespace {

p::Bytes minimal_genesis() {
  p::Bytes encoded{'P', 'S', 'G', 'N', 0, 1, 0, 0, 0, 1};
  pv::append_u64(encoded, 1'000);
  pv::append_u64(encoded, 1'000);
  pv::append_u64(encoded, 1);
  pv::append_u64(encoded, 0);
  encoded.insert(encoded.end(), {0, 0, 0, 1});
  encoded.push_back(1);
  encoded.resize(encoded.size() + 31);
  pv::append_u64(encoded, 1'000);
  pv::append_u64(encoded, 0);
  return encoded;
}

void require_deterministic(std::span<const std::uint8_t> input,
                           bool require_success = false) {
  auto first = p::load_genesis(input).result;
  auto second = p::load_genesis(input).result;
  if (first.index() != second.index()) std::abort();
  if (const auto* first_error = std::get_if<p::GenesisError>(&first)) {
    if (require_success) std::abort();
    const auto* second_error = std::get_if<p::GenesisError>(&second);
    if (second_error == nullptr || *first_error != *second_error) {
      std::abort();
    }
    return;
  }
  const auto& first_ledger = std::get<p::Ledger>(first);
  const auto& second_ledger = std::get<p::Ledger>(second);
  const auto first_root = first_ledger.current_state_root();
  const auto second_root = second_ledger.current_state_root();
  if (!std::holds_alternative<p::StateRoot>(first_root) ||
      !std::holds_alternative<p::StateRoot>(second_root) ||
      first_ledger.state() != second_ledger.state() ||
      first_root != second_root) {
    std::abort();
  }
}

}  // namespace

extern "C" int LLVMFuzzerTestOneInput(const std::uint8_t* data,
                                      std::size_t size) {
  const std::span<const std::uint8_t> input{data, size};
  require_deterministic(input);

  const auto baseline = minimal_genesis();
  require_deterministic(baseline, true);
  auto structured = baseline;
  constexpr std::size_t kMaximumMutations = 256;
  const auto mutations =
      std::min(size / 2, kMaximumMutations);
  for (std::size_t index = 0; index < mutations; ++index) {
    const auto offset = static_cast<std::size_t>(data[index * 2]) %
                        structured.size();
    structured[offset] = data[index * 2 + 1];
  }
  require_deterministic(structured);
  return 0;
}
