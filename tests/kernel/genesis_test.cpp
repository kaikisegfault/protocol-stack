#include "../../src/v1/genesis.hpp"
#include "../../tools/protocol-vectors/vector_common.hpp"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <limits>
#include <string>
#include <string_view>
#include <utility>
#include <variant>
#include <vector>

namespace pv = protocol_vectors;
namespace p = protocol::v1;

namespace {

constexpr std::size_t kGenesisPrefixSize = 46;
constexpr std::size_t kAccountSize = 48;
constexpr std::uint32_t kMaximumAccounts = 21'844;

struct GenesisAccount {
  p::AccountId identifier;
  std::uint64_t balance;
  std::uint64_t nonce;
};

void append_u32(p::Bytes& target, std::uint32_t value) {
  for (int shift = 24; shift >= 0; shift -= 8) {
    target.push_back(static_cast<std::uint8_t>(value >> shift));
  }
}

template <typename Tagged>
void append_hash(p::Bytes& target, const Tagged& value) {
  target.insert(target.end(), value.begin(), value.end());
}

p::AccountId identifier(std::uint64_t value) {
  p::Hash result{};
  for (std::size_t index = 0; index < 8; ++index) {
    result[result.size() - 1 - index] =
        static_cast<std::uint8_t>(value >> (index * 8U));
  }
  return p::AccountId{result};
}

p::Bytes genesis_prefix(std::uint64_t supply_limit,
                        std::uint64_t total_supply,
                        std::uint64_t fixed_fee,
                        std::uint64_t initial_fee_pool,
                        std::uint32_t account_count) {
  p::Bytes encoded{'P', 'S', 'G', 'N'};
  pv::append_u16(encoded, 1);
  append_u32(encoded, 1);
  pv::append_u64(encoded, supply_limit);
  pv::append_u64(encoded, total_supply);
  pv::append_u64(encoded, fixed_fee);
  pv::append_u64(encoded, initial_fee_pool);
  append_u32(encoded, account_count);
  pv::require(encoded.size() == kGenesisPrefixSize, "genesis prefix size");
  return encoded;
}

p::Bytes encode_genesis(std::uint64_t supply_limit,
                        std::uint64_t total_supply,
                        std::uint64_t fixed_fee,
                        std::uint64_t initial_fee_pool,
                        const std::vector<GenesisAccount>& accounts) {
  auto encoded = genesis_prefix(
      supply_limit, total_supply, fixed_fee, initial_fee_pool,
      static_cast<std::uint32_t>(accounts.size()));
  for (const auto& account : accounts) {
    append_hash(encoded, account.identifier);
    pv::append_u64(encoded, account.balance);
    pv::append_u64(encoded, account.nonce);
  }
  return encoded;
}

const p::State& require_state(const p::internal::GenesisDecode& decoded,
                              std::string_view message) {
  pv::require(std::holds_alternative<p::State>(decoded), message);
  return std::get<p::State>(decoded);
}

void require_error(const p::Bytes& encoded, p::GenesisError expected,
                   std::string_view message) {
  const auto decoded = p::internal::decode_genesis(encoded);
  pv::require(std::holds_alternative<p::GenesisError>(decoded), message);
  pv::require(std::get<p::GenesisError>(decoded) == expected, message);
}

void zero_field(p::Bytes& encoded, std::size_t offset) {
  std::fill_n(encoded.begin() + offset, 8, 0);
}

void verify_frozen_genesis(const pv::Values& values) {
  const auto encoded = pv::hex_decode(values.at("genesis"));
  const auto decoded = p::internal::decode_genesis(encoded);
  const auto& state = require_state(decoded, "frozen genesis rejected");
  p::Hash expected_chain_bytes{};
  const auto chain_bytes = pv::hex_decode(values.at("chain_id"));
  pv::require(chain_bytes.size() == expected_chain_bytes.size(),
              "frozen chain ID size");
  std::copy(chain_bytes.begin(), chain_bytes.end(),
            expected_chain_bytes.begin());
  const p::ChainId expected_chain{expected_chain_bytes};
  pv::require(state.parameters.chain_id == expected_chain, "frozen chain ID");
  pv::require(
      state.parameters.supply_limit == std::stoull(values.at("supply_limit")),
      "frozen supply limit");
  pv::require(
      state.parameters.total_supply == std::stoull(values.at("total_supply")),
      "frozen total supply");
  pv::require(
      state.parameters.fixed_fee == std::stoull(values.at("fixed_fee")),
      "frozen fixed fee");
  pv::require(state.height == 0, "genesis height");
  pv::require(state.fee_pool == pv::read_u64(encoded, 34),
              "genesis fee pool");
  pv::require(state.accounts.size() == 2, "frozen account count");

  std::size_t index = 0;
  for (const auto& [account_id, account] : state.accounts) {
    p::Bytes entry;
    append_hash(entry, account_id);
    pv::append_u64(entry, account.balance);
    pv::append_u64(entry, account.nonce);
    pv::require(
        entry == pv::hex_decode(
                     values.at("genesis.account" + std::to_string(index))),
        "frozen account");
    ++index;
  }
}

void verify_header_and_parameter_rejection(const pv::Values& values) {
  const auto frozen = pv::hex_decode(values.at("genesis"));
  auto malformed = frozen;
  malformed[0] = 'X';
  require_error(malformed, p::GenesisError::malformed, "genesis magic");
  malformed = frozen;
  malformed[5] = 2;
  require_error(malformed, p::GenesisError::malformed, "genesis version");
  malformed = frozen;
  malformed[9] = 2;
  require_error(malformed, p::GenesisError::unsupported_network,
                "genesis network");
  malformed = frozen;
  malformed.pop_back();
  require_error(malformed, p::GenesisError::malformed,
                "truncated genesis account");
  malformed = frozen;
  malformed.resize(kGenesisPrefixSize - 1);
  require_error(malformed, p::GenesisError::malformed,
                "truncated genesis prefix");
  malformed = frozen;
  malformed.push_back(0);
  require_error(malformed, p::GenesisError::malformed, "trailing genesis");

  for (const auto offset : {std::size_t{10}, std::size_t{18},
                            std::size_t{26}}) {
    malformed = frozen;
    zero_field(malformed, offset);
    require_error(malformed, p::GenesisError::invalid_parameters,
                  "zero genesis parameter");
  }
  require_error(encode_genesis(1, 2, 1, 0, {{identifier(1), 2, 0}}),
                p::GenesisError::invalid_supply, "supply exceeds limit");
}

void verify_account_rejection() {
  require_error(genesis_prefix(1, 1, 1, 0, 0),
                p::GenesisError::invalid_accounts, "zero account count");
  require_error(genesis_prefix(1, 1, 1, 0, kMaximumAccounts + 1),
                p::GenesisError::invalid_accounts,
                "oversized account count rejected before length");
  require_error(
      encode_genesis(2, 2, 1, 0,
                     {{identifier(1), 1, 0}, {identifier(1), 1, 0}}),
      p::GenesisError::invalid_accounts, "duplicate account IDs");
  require_error(
      encode_genesis(2, 2, 1, 0,
                     {{identifier(2), 1, 0}, {identifier(1), 1, 0}}),
      p::GenesisError::invalid_accounts, "unordered account IDs");
  require_error(encode_genesis(1, 1, 1, 0, {{identifier(1), 0, 0}}),
                p::GenesisError::invalid_accounts, "zero account balance");
  require_error(encode_genesis(1, 1, 1, 0, {{identifier(1), 1, 1}}),
                p::GenesisError::invalid_accounts, "nonzero account nonce");
}

void verify_supply_and_pool() {
  const auto maximum = std::numeric_limits<std::uint64_t>::max();
  const auto ceiling = encode_genesis(
      maximum, maximum, 1, maximum - 1,
      {{identifier(1), 1, 0}});
  const auto ceiling_decoded = p::internal::decode_genesis(ceiling);
  const auto& ceiling_state =
      require_state(ceiling_decoded, "u64 supply ceiling rejected");
  pv::require(ceiling_state.fee_pool == maximum - 1 &&
                  ceiling_state.accounts.begin()->second.balance == 1,
              "u64 supply ceiling");

  require_error(
      encode_genesis(maximum, maximum, 1, maximum,
                     {{identifier(1), 1, 0}}),
      p::GenesisError::invalid_supply, "genesis sum overflow");
  require_error(encode_genesis(2, 2, 1, 0, {{identifier(1), 1, 0}}),
                p::GenesisError::invalid_supply, "genesis sum mismatch");
  require_error(
      encode_genesis(10, 5, 1, 3,
                     {{identifier(1), 1, 0}, {identifier(2), 2, 0}}),
      p::GenesisError::invalid_supply, "initial fee pool sum mismatch");

  const auto encoded =
      encode_genesis(10, 6, 1, 3,
                     {{identifier(1), 1, 0}, {identifier(2), 2, 0}});
  const auto decoded = p::internal::decode_genesis(encoded);
  const auto& state = require_state(decoded, "initial fee pool rejected");
  pv::require(state.fee_pool == 3 && state.accounts.size() == 2,
              "initial fee pool state");
}

void verify_maximum_account_count() {
  std::vector<GenesisAccount> accounts;
  accounts.reserve(kMaximumAccounts);
  for (std::uint32_t index = 1; index <= kMaximumAccounts; ++index) {
    accounts.push_back(GenesisAccount{identifier(index), 1, 0});
  }
  const auto encoded =
      encode_genesis(kMaximumAccounts, kMaximumAccounts, 1, 0, accounts);
  pv::require(encoded.size() ==
                  kGenesisPrefixSize +
                      static_cast<std::size_t>(kMaximumAccounts) * kAccountSize,
              "maximum genesis byte length");
  const auto decoded = p::internal::decode_genesis(encoded);
  const auto& state = require_state(decoded, "maximum genesis rejected");
  pv::require(state.accounts.size() == kMaximumAccounts,
              "maximum genesis account count");
}

}  // namespace

int main(int argc, char** argv) {
  try {
    pv::require(argc == 2, "usage: kernel_genesis_test VECTOR_FILE");
    const auto values = pv::load_values(argv[1]);
    verify_frozen_genesis(values);
    verify_header_and_parameter_rejection(values);
    verify_account_rejection();
    verify_supply_and_pool();
    verify_maximum_account_count();
    std::cout << "Kernel genesis tests: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "Kernel genesis tests: failed: " << error.what() << '\n';
    return 1;
  }
}
