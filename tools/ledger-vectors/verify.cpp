#include "../protocol-vectors/vector_common.hpp"

#include <algorithm>
#include <cstdint>
#include <iostream>
#include <limits>
#include <map>
#include <optional>
#include <string>
#include <utility>
#include <vector>

namespace pv = protocol_vectors;

constexpr std::uint64_t kSupplyLimit = 1'000'000'000'000'000'000ULL;
constexpr std::uint64_t kFixedFee = 1'000;
constexpr std::uint64_t kBlockHeight = 1;

struct Account {
  std::uint64_t balance;
  std::uint64_t nonce;
};

struct Transaction {
  pv::Bytes sender_id;
  pv::Bytes transaction_id;
  std::uint64_t nonce;
  pv::Bytes recipient;
  std::uint64_t amount;
  std::uint64_t fee_limit;
  std::uint64_t valid_until;
};

using Accounts = std::map<pv::Bytes, Account>;

pv::Bytes slice(const pv::Bytes& value, std::size_t begin, std::size_t end) {
  pv::require(begin <= end && end <= value.size(), "invalid byte slice");
  return pv::Bytes(value.begin() + begin, value.begin() + end);
}

void append_u32(pv::Bytes& target, std::uint32_t value) {
  for (int shift = 24; shift >= 0; shift -= 8) {
    target.push_back(static_cast<unsigned char>(value >> shift));
  }
}

pv::Bytes account_id(const pv::Bytes& public_key) {
  pv::Bytes payload{1};
  pv::append(payload, public_key);
  return pv::hash("protocol-stack:v1:account", payload);
}

std::vector<pv::Bytes> account_entries(const Accounts& accounts) {
  std::vector<pv::Bytes> entries;
  entries.reserve(accounts.size());
  for (const auto& [identifier, account] : accounts) {
    auto entry = identifier;
    pv::append_u64(entry, account.balance);
    pv::append_u64(entry, account.nonce);
    entries.push_back(std::move(entry));
  }
  return entries;
}

pv::Bytes state_root(const pv::Bytes& chain_id, const Accounts& accounts,
                     std::uint64_t height, std::uint64_t fee_pool,
                     std::uint64_t total_supply) {
  std::uint64_t sum = fee_pool;
  for (const auto& [identifier, account] : accounts) {
    pv::require(identifier.size() == 32, "account ID size");
    pv::require(sum <= std::numeric_limits<std::uint64_t>::max() -
                           account.balance,
                "supply addition overflow");
    sum += account.balance;
  }
  pv::require(sum == total_supply && total_supply <= kSupplyLimit,
              "supply conservation");
  const auto entries = account_entries(accounts);
  pv::Bytes payload;
  pv::append_u16(payload, 1);
  pv::append(payload, chain_id);
  pv::append_u64(payload, height);
  pv::append_u64(payload, kSupplyLimit);
  pv::append_u64(payload, total_supply);
  pv::append_u64(payload, fee_pool);
  pv::append_u64(payload, entries.size());
  pv::append(payload, pv::merkle(entries, "state"));
  return pv::hash("protocol-stack:v1:state-root", payload);
}

pv::Bytes genesis_bytes(const Accounts& accounts,
                        std::uint64_t total_supply) {
  auto result = pv::ascii("PSGN");
  pv::append_u16(result, 1);
  append_u32(result, 1);
  pv::append_u64(result, kSupplyLimit);
  pv::append_u64(result, total_supply);
  pv::append_u64(result, kFixedFee);
  pv::append_u64(result, 0);
  append_u32(result, static_cast<std::uint32_t>(accounts.size()));
  for (const auto& entry : account_entries(accounts)) {
    pv::require(pv::read_u64(entry, 32) > 0 &&
                    pv::read_u64(entry, 40) == 0,
                "invalid genesis account");
    pv::append(result, entry);
  }
  return result;
}

std::pair<unsigned char, std::optional<Transaction>> admit(
    const pv::Bytes& raw, const pv::Bytes& chain_id) {
  if (raw.size() != 200 ||
      !std::equal(raw.begin(), raw.begin() + std::min<std::size_t>(4, raw.size()),
                  "PSTX") ||
      raw[4] != 0 || raw[5] != 1 || raw[6] != 1 || raw[39] != 1) {
    return {1, std::nullopt};
  }
  if (slice(raw, 7, 39) != chain_id) return {2, std::nullopt};
  const auto public_key = slice(raw, 40, 72);
  auto message = pv::domain("protocol-stack:v1:tx-sign");
  const auto unsigned_transaction = slice(raw, 0, 136);
  pv::append(message, unsigned_transaction);
  if (crypto_sign_verify_detached(raw.data() + 136, message.data(),
                                  message.size(), public_key.data()) != 0) {
    return {3, std::nullopt};
  }
  return {
      0,
      Transaction{
          account_id(public_key),
          pv::hash("protocol-stack:v1:tx-id", raw),
          pv::read_u64(raw, 72),
          slice(raw, 80, 112),
          pv::read_u64(raw, 112),
          pv::read_u64(raw, 120),
          pv::read_u64(raw, 128),
      },
  };
}

unsigned char execute(const Transaction& transaction, Accounts& accounts,
                      std::uint64_t& fee_pool) {
  if (transaction.amount == 0) return 1;
  if (transaction.fee_limit < kFixedFee) return 2;
  if (transaction.valid_until < kBlockHeight) return 3;
  const auto sender_it = accounts.find(transaction.sender_id);
  if (sender_it == accounts.end()) return 4;
  Account& sender = sender_it->second;
  if (sender.nonce == std::numeric_limits<std::uint64_t>::max()) return 5;
  if (transaction.nonce != sender.nonce + 1) return 6;
  if (transaction.amount >
      std::numeric_limits<std::uint64_t>::max() - kFixedFee) {
    return 7;
  }
  const auto debit = transaction.amount + kFixedFee;
  if (sender.balance < debit) return 8;

  if (transaction.sender_id == transaction.recipient) {
    sender.balance -= kFixedFee;
  } else {
    const auto recipient_it = accounts.find(transaction.recipient);
    const auto recipient_balance =
        recipient_it == accounts.end() ? 0 : recipient_it->second.balance;
    pv::require(
        recipient_balance <= std::numeric_limits<std::uint64_t>::max() -
                                 transaction.amount,
        "recipient invariant");
    sender.balance -= debit;
    if (recipient_it == accounts.end()) {
      accounts.emplace(transaction.recipient,
                       Account{transaction.amount, 0});
    } else {
      recipient_it->second.balance += transaction.amount;
    }
  }
  sender.nonce = transaction.nonce;
  pv::require(fee_pool <=
                  std::numeric_limits<std::uint64_t>::max() - kFixedFee,
              "fee pool invariant");
  fee_pool += kFixedFee;
  return 0;
}

pv::Bytes receipt(const pv::Bytes& transaction_id, unsigned char result) {
  auto encoded = pv::ascii("PSRC");
  pv::append_u16(encoded, 1);
  pv::append(encoded, transaction_id);
  encoded.push_back(result);
  pv::append_u64(encoded, result == 0 ? kFixedFee : 0);
  pv::require(encoded.size() == 47, "receipt size");
  return encoded;
}

Accounts load_genesis_accounts(const pv::Values& values) {
  Accounts accounts;
  for (std::size_t index = 0; index < 2; ++index) {
    const auto entry =
        pv::hex_decode(values.at("genesis.account" + std::to_string(index)));
    pv::require(entry.size() == 48, "genesis entry size");
    accounts.emplace(slice(entry, 0, 32),
                     Account{pv::read_u64(entry, 32),
                             pv::read_u64(entry, 40)});
  }
  pv::require(accounts.size() == 2, "duplicate genesis account");
  return accounts;
}

void verify_vectors(const pv::Values& values) {
  pv::require(std::stoull(values.at("supply_limit")) == kSupplyLimit,
              "supply limit");
  pv::require(std::stoull(values.at("fixed_fee")) == kFixedFee, "fixed fee");
  const auto total_supply = std::stoull(values.at("total_supply"));
  auto accounts = load_genesis_accounts(values);
  const auto genesis = genesis_bytes(accounts, total_supply);
  pv::require(genesis == pv::hex_decode(values.at("genesis")),
              "canonical genesis");
  const auto chain_id = pv::hash("protocol-stack:v1:chain-id", genesis);
  pv::require(chain_id == pv::hex_decode(values.at("chain_id")), "chain ID");
  const auto previous_root =
      state_root(chain_id, accounts, 0, 0, total_supply);
  pv::require(previous_root ==
                  pv::hex_decode(values.at("previous_state_root")),
              "previous state root");

  std::uint64_t fee_pool = 0;
  std::vector<pv::Bytes> transaction_ids;
  std::size_t receipt_index = 0;
  const auto raw_count = std::stoull(values.at("raw_count"));
  for (std::size_t raw_index = 0; raw_index < raw_count; ++raw_index) {
    const auto key = "raw" + std::to_string(raw_index);
    const auto raw = pv::hex_decode(values.at(key));
    const auto [admission, transaction] = admit(raw, chain_id);
    pv::require(
        admission == std::stoull(values.at(key + ".admission")),
        "admission result");
    if (!transaction) continue;
    const auto result = execute(*transaction, accounts, fee_pool);
    const auto receipt_key = "receipt" + std::to_string(receipt_index);
    pv::require(
        result == std::stoull(values.at(receipt_key + ".result")),
        "execution result");
    pv::require(receipt(transaction->transaction_id, result) ==
                    pv::hex_decode(values.at(receipt_key)),
                "receipt bytes");
    transaction_ids.push_back(transaction->transaction_id);
    ++receipt_index;
  }
  pv::require(receipt_index == std::stoull(values.at("admitted_count")),
              "admitted count");
  pv::require(fee_pool == std::stoull(values.at("fee_pool")), "fee pool");

  const auto transaction_root = pv::merkle(transaction_ids, "tx");
  const auto resulting_root =
      state_root(chain_id, accounts, kBlockHeight, fee_pool, total_supply);
  pv::require(transaction_root ==
                  pv::hex_decode(values.at("transaction_root")),
              "transaction root");
  pv::require(resulting_root ==
                  pv::hex_decode(values.at("resulting_state_root")),
              "resulting state root");
  const auto entries = account_entries(accounts);
  pv::require(entries.size() ==
                  std::stoull(values.at("final_account_count")),
              "final account count");
  for (std::size_t index = 0; index < entries.size(); ++index) {
    pv::require(entries[index] ==
                    pv::hex_decode(values.at("final.account" +
                                             std::to_string(index))),
                "final account entry");
  }

  auto header = pv::ascii("PSBL");
  pv::append_u16(header, 1);
  pv::append(header, chain_id);
  pv::append_u64(header, kBlockHeight);
  pv::append(header, previous_root);
  pv::append(header, transaction_root);
  pv::append(header, resulting_root);
  append_u32(header, static_cast<std::uint32_t>(transaction_ids.size()));
  pv::require(header == pv::hex_decode(values.at("block_header")),
              "block header");
  pv::require(pv::hash("protocol-stack:v1:block-id", header) ==
                  pv::hex_decode(values.at("block_id")),
              "block ID");

  Accounts boundary_accounts{
      {accounts.rbegin()->first,
       Account{5'000, std::numeric_limits<std::uint64_t>::max()}}};
  const Transaction boundary_transaction{
      accounts.rbegin()->first,
      pv::Bytes(32),
      std::numeric_limits<std::uint64_t>::max(),
      accounts.begin()->first,
      1,
      kFixedFee,
      1,
  };
  std::uint64_t boundary_pool = 0;
  const auto boundary_result =
      execute(boundary_transaction, boundary_accounts, boundary_pool);
  pv::require(
      boundary_result ==
              std::stoull(values.at("boundary.nonce_exhausted.result")) &&
          boundary_pool == 0 &&
          boundary_accounts.begin()->second.balance == 5'000 &&
          boundary_accounts.begin()->second.nonce ==
              std::numeric_limits<std::uint64_t>::max(),
      "nonce exhaustion atomicity");
}

int main(int argc, char** argv) {
  try {
    pv::require(argc == 2, "usage: ledger_vectors VECTOR_FILE");
    pv::require(sodium_init() >= 0, "libsodium initialization");
    verify_vectors(pv::load_values(argv[1]));
    std::cout << "C++ ledger transition vectors: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "C++ ledger transition vectors: failed: " << error.what()
              << '\n';
    return 1;
  }
}
