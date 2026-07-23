#pragma once

#include <array>
#include <compare>
#include <cstdint>
#include <map>
#include <variant>
#include <vector>

namespace protocol::v1 {

using Bytes = std::vector<std::uint8_t>;
using Hash = std::array<std::uint8_t, 32>;

struct Account {
  std::uint64_t balance;
  std::uint64_t nonce;

  auto operator<=>(const Account&) const = default;
};

struct Parameters {
  Hash chain_id;
  std::uint64_t supply_limit;
  std::uint64_t total_supply;
  std::uint64_t fixed_fee;
};

struct State {
  Parameters parameters;
  std::uint64_t height;
  std::uint64_t fee_pool;
  std::map<Hash, Account> accounts;
};

enum class AdmissionError : std::uint8_t {
  malformed_transaction = 1,
  wrong_chain = 2,
  invalid_signature = 3,
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
  Hash sender_id;
  Hash transaction_id;
  std::uint64_t nonce;
  Hash recipient;
  std::uint64_t amount;
  std::uint64_t fee_limit;
  std::uint64_t valid_until;
};

using Admission = std::variant<Transfer, AdmissionError>;

struct Receipt {
  Hash transaction_id;
  TransferResult result;
  std::uint64_t fee_charged;
};

}  // namespace protocol::v1
