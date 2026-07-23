#include "genesis.hpp"

#include "encoding.hpp"
#include "protocol/v1/crypto.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <map>
#include <optional>
#include <utility>

namespace protocol::v1::internal {
namespace {

constexpr std::size_t kGenesisPrefixSize = 46;
constexpr std::size_t kAccountSize = 48;
constexpr std::uint32_t kMaximumGenesisAccounts = 21'844;
constexpr std::array<std::uint8_t, 4> kGenesisMagic{'P', 'S', 'G', 'N'};

struct GenesisFields {
  std::uint64_t supply_limit;
  std::uint64_t total_supply;
  std::uint64_t fixed_fee;
  std::uint64_t initial_fee_pool;
  std::uint32_t account_count;
};

std::variant<GenesisFields, GenesisError> decode_fields(
    std::span<const std::uint8_t> canonical_genesis) {
  if (canonical_genesis.size() < kGenesisPrefixSize) {
    return GenesisError::malformed;
  }
  const auto magic = read_fixed<4>(canonical_genesis, 0);
  const auto version = read_u16(canonical_genesis, 4);
  const auto network = read_u32(canonical_genesis, 6);
  const auto supply_limit = read_u64(canonical_genesis, 10);
  const auto total_supply = read_u64(canonical_genesis, 18);
  const auto fixed_fee = read_u64(canonical_genesis, 26);
  const auto initial_fee_pool = read_u64(canonical_genesis, 34);
  const auto account_count = read_u32(canonical_genesis, 42);
  if (!magic || !version || !network || !supply_limit || !total_supply ||
      !fixed_fee || !initial_fee_pool || !account_count) {
    return GenesisError::malformed;
  }
  if (*magic != kGenesisMagic || *version != 1) {
    return GenesisError::malformed;
  }
  if (*network != 1) {
    return GenesisError::unsupported_network;
  }
  if (*supply_limit == 0 || *total_supply == 0 || *fixed_fee == 0) {
    return GenesisError::invalid_parameters;
  }
  if (*total_supply > *supply_limit) {
    return GenesisError::invalid_supply;
  }
  if (*account_count == 0 || *account_count > kMaximumGenesisAccounts) {
    return GenesisError::invalid_accounts;
  }
  return GenesisFields{*supply_limit, *total_supply, *fixed_fee,
                       *initial_fee_pool, *account_count};
}

std::optional<GenesisError> validate_accounts(
    std::span<const std::uint8_t> canonical_genesis,
    const GenesisFields& fields) {
  std::optional<AccountId> previous_identifier;
  std::uint64_t conserved_supply = fields.initial_fee_pool;
  for (std::size_t index = 0; index < fields.account_count; ++index) {
    const auto offset = kGenesisPrefixSize + index * kAccountSize;
    const auto raw_identifier = read_fixed<32>(canonical_genesis, offset);
    const auto balance = read_u64(canonical_genesis, offset + 32);
    const auto nonce = read_u64(canonical_genesis, offset + 40);
    if (!raw_identifier || !balance || !nonce) {
      return GenesisError::malformed;
    }
    const AccountId identifier(*raw_identifier);
    if (*balance == 0 || *nonce != 0 ||
        (previous_identifier && !(*previous_identifier < identifier))) {
      return GenesisError::invalid_accounts;
    }
    if (*balance >
        std::numeric_limits<std::uint64_t>::max() - conserved_supply) {
      return GenesisError::invalid_supply;
    }
    conserved_supply += *balance;
    previous_identifier = identifier;
  }
  if (conserved_supply != fields.total_supply) {
    return GenesisError::invalid_supply;
  }
  return std::nullopt;
}

std::map<AccountId, Account> decode_accounts(
    std::span<const std::uint8_t> canonical_genesis,
    std::uint32_t account_count) {
  std::map<AccountId, Account> accounts;
  for (std::size_t index = 0; index < account_count; ++index) {
    const auto offset = kGenesisPrefixSize + index * kAccountSize;
    const AccountId identifier(*read_fixed<32>(canonical_genesis, offset));
    const auto balance = *read_u64(canonical_genesis, offset + 32);
    const auto nonce = *read_u64(canonical_genesis, offset + 40);
    accounts.emplace(identifier, Account{balance, nonce});
  }
  return accounts;
}

}  // namespace

GenesisDecode decode_genesis(
    std::span<const std::uint8_t> canonical_genesis) {
  const auto decoded_fields = decode_fields(canonical_genesis);
  if (std::holds_alternative<GenesisError>(decoded_fields)) {
    return std::get<GenesisError>(decoded_fields);
  }
  const auto fields = std::get<GenesisFields>(decoded_fields);
  const auto expected_size =
      kGenesisPrefixSize +
      static_cast<std::size_t>(fields.account_count) * kAccountSize;
  if (canonical_genesis.size() != expected_size) {
    return GenesisError::malformed;
  }
  const auto account_error = validate_accounts(canonical_genesis, fields);
  if (account_error) {
    return *account_error;
  }
  auto accounts = decode_accounts(canonical_genesis, fields.account_count);
  return State{
      Parameters{
          ChainId(hash("protocol-stack:v1:chain-id", canonical_genesis)),
          fields.supply_limit,
          fields.total_supply,
          fields.fixed_fee,
      },
      0,
      fields.initial_fee_pool,
      std::move(accounts),
  };
}

}  // namespace protocol::v1::internal
