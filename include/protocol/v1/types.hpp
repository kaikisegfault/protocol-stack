#pragma once

#include <array>
#include <compare>
#include <cstddef>
#include <cstdint>
#include <map>
#include <utility>
#include <variant>
#include <vector>

namespace protocol::v1 {

using Bytes = std::vector<std::uint8_t>;
using Hash = std::array<std::uint8_t, 32>;

template <typename Tag>
class TaggedHash {
 public:
  TaggedHash() = default;
  explicit TaggedHash(Hash value) noexcept : value_(std::move(value)) {}

  auto begin() noexcept { return value_.begin(); }
  auto begin() const noexcept { return value_.begin(); }
  auto end() noexcept { return value_.end(); }
  auto end() const noexcept { return value_.end(); }
  std::uint8_t* data() noexcept { return value_.data(); }
  const std::uint8_t* data() const noexcept { return value_.data(); }
  constexpr std::size_t size() const noexcept { return value_.size(); }

  auto operator<=>(const TaggedHash&) const = default;

 private:
  Hash value_{};
};

struct AccountIdTag;
struct ChainIdTag;
struct TransactionIdTag;
struct StateRootTag;
struct TransactionRootTag;
struct BlockIdTag;

using AccountId = TaggedHash<AccountIdTag>;
using ChainId = TaggedHash<ChainIdTag>;
using TransactionId = TaggedHash<TransactionIdTag>;
using StateRoot = TaggedHash<StateRootTag>;
using TransactionRoot = TaggedHash<TransactionRootTag>;
using BlockId = TaggedHash<BlockIdTag>;

struct Account {
  std::uint64_t balance;
  std::uint64_t nonce;

  auto operator<=>(const Account&) const = default;
};

struct Parameters {
  ChainId chain_id;
  std::uint64_t supply_limit;
  std::uint64_t total_supply;
  std::uint64_t fixed_fee;

  bool operator==(const Parameters&) const = default;
};

struct State {
  Parameters parameters;
  std::uint64_t height;
  std::uint64_t fee_pool;
  std::map<AccountId, Account> accounts;

  bool operator==(const State&) const = default;
};

enum class AdmissionError : std::uint8_t {
  malformed_transaction = 1,
  wrong_chain = 2,
  invalid_signature = 3,
};

enum class GenesisError : std::uint8_t {
  malformed = 1,
  unsupported_network = 2,
  invalid_parameters = 3,
  invalid_accounts = 4,
  invalid_supply = 5,
};

enum class TransferResult : std::uint8_t {
  success = 0,
  zero_amount = 1,
  fee_limit_too_low = 2,
  expired = 3,
  sender_not_found = 4,
  nonce_exhausted = 5,
  nonce_mismatch = 6,
  debit_overflow = 7,
  insufficient_balance = 8,
};

struct Transfer {
  AccountId sender_id;
  TransactionId transaction_id;
  std::uint64_t nonce;
  AccountId recipient;
  std::uint64_t amount;
  std::uint64_t fee_limit;
  std::uint64_t valid_until;
};

using Admission = std::variant<Transfer, AdmissionError>;

struct Receipt {
  TransactionId transaction_id;
  TransferResult result;
  std::uint64_t fee_charged;

  bool operator==(const Receipt&) const = default;
};

}  // namespace protocol::v1
