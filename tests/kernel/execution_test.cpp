#include "protocol/v1/admission.hpp"

#include "../../src/v1/execution.hpp"
#include "../../tools/protocol-vectors/vector_common.hpp"

#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>
#include <iterator>
#include <limits>
#include <map>
#include <string>
#include <string_view>
#include <utility>
#include <variant>
#include <vector>

namespace pv = protocol_vectors;
namespace p = protocol::v1;

namespace {

constexpr std::uint64_t kBlockHeight = 1;

p::Hash hash_value(const pv::Bytes& bytes, std::size_t offset = 0) {
  pv::require(offset + 32 <= bytes.size(), "hash size");
  p::Hash result{};
  std::copy_n(bytes.begin() + offset, result.size(), result.begin());
  return result;
}

void append_hash(pv::Bytes& target, const p::Hash& value) {
  target.insert(target.end(), value.begin(), value.end());
}

std::pair<p::Hash, p::Account> decode_account(std::string_view encoded) {
  const auto bytes = pv::hex_decode(encoded);
  pv::require(bytes.size() == 48, "account entry size");
  return {
      hash_value(bytes),
      p::Account{pv::read_u64(bytes, 32), pv::read_u64(bytes, 40)},
  };
}

p::State initial_state(const pv::Values& values) {
  std::map<p::Hash, p::Account> accounts;
  for (std::size_t index = 0;; ++index) {
    const auto entry = values.find("genesis.account" + std::to_string(index));
    if (entry == values.end()) break;
    pv::require(accounts.emplace(decode_account(entry->second)).second,
                "duplicate genesis account");
  }
  pv::require(!accounts.empty(), "missing genesis accounts");
  const auto genesis = pv::hex_decode(values.at("genesis"));
  pv::require(genesis.size() >= 42, "truncated genesis");
  return p::State{
      p::Parameters{
          hash_value(pv::hex_decode(values.at("chain_id"))),
          std::stoull(values.at("supply_limit")),
          std::stoull(values.at("total_supply")),
          std::stoull(values.at("fixed_fee")),
      },
      0,
      pv::read_u64(genesis, 34),
      std::move(accounts),
  };
}

pv::Bytes state_bytes(const p::State& state) {
  pv::Bytes result;
  append_hash(result, state.parameters.chain_id);
  pv::append_u64(result, state.parameters.supply_limit);
  pv::append_u64(result, state.parameters.total_supply);
  pv::append_u64(result, state.parameters.fixed_fee);
  pv::append_u64(result, state.height);
  pv::append_u64(result, state.fee_pool);
  pv::append_u64(result, state.accounts.size());
  for (const auto& [identifier, account] : state.accounts) {
    append_hash(result, identifier);
    pv::append_u64(result, account.balance);
    pv::append_u64(result, account.nonce);
  }
  return result;
}

void require_conservation(const p::State& state) {
  auto sum = state.fee_pool;
  for (const auto& [identifier, account] : state.accounts) {
    static_cast<void>(identifier);
    pv::require(
        account.balance <= std::numeric_limits<std::uint64_t>::max() - sum,
        "conservation sum overflow");
    sum += account.balance;
  }
  pv::require(sum == state.parameters.total_supply, "supply conservation");
  pv::require(state.parameters.total_supply <= state.parameters.supply_limit,
              "supply limit");
}

void verify_receipt(const p::Receipt& receipt, const p::Transfer& transfer,
                    const pv::Values& values, std::size_t receipt_index) {
  const auto key = "receipt" + std::to_string(receipt_index);
  const auto expected_bytes = pv::hex_decode(values.at(key));
  pv::require(expected_bytes.size() == 47, "receipt vector size");
  const auto expected_code = std::stoull(values.at(key + ".result"));
  pv::require(expected_bytes[38] == expected_code, "receipt result vector");
  pv::require(receipt.transaction_id == transfer.transaction_id,
              "receipt transaction ID");
  pv::require(receipt.transaction_id == hash_value(expected_bytes, 6),
              "receipt transaction ID vector");
  pv::require(static_cast<std::uint8_t>(receipt.result) == expected_code,
              "transfer result");
  pv::require(receipt.fee_charged == pv::read_u64(expected_bytes, 39),
              "receipt fee vector");
  const auto expected_fee =
      receipt.result == p::TransferResult::success
          ? values.at("fixed_fee")
          : std::string("0");
  pv::require(receipt.fee_charged == std::stoull(expected_fee),
              "receipt fee");
}

void verify_success(const p::State& before, const p::State& after,
                    const p::Transfer& transfer) {
  const auto fixed_fee = before.parameters.fixed_fee;
  const auto sender_before = before.accounts.at(transfer.sender_id);
  const auto sender_after = after.accounts.at(transfer.sender_id);
  pv::require(after.fee_pool == before.fee_pool + fixed_fee,
              "successful fee routing");
  pv::require(sender_after.nonce == transfer.nonce,
              "successful nonce advancement");
  if (transfer.sender_id == transfer.recipient) {
    pv::require(sender_after.balance == sender_before.balance - fixed_fee,
                "self-transfer balance");
    pv::require(after.accounts.size() == before.accounts.size(),
                "self-transfer account count");
    return;
  }

  const auto recipient_before = before.accounts.find(transfer.recipient);
  const auto recipient_after = after.accounts.find(transfer.recipient);
  pv::require(recipient_after != after.accounts.end(), "recipient exists");
  pv::require(sender_after.balance ==
                  sender_before.balance - transfer.amount - fixed_fee,
              "sender debit");
  if (recipient_before == before.accounts.end()) {
    pv::require(recipient_after->second ==
                    p::Account{transfer.amount, 0},
                "created recipient");
    pv::require(after.accounts.size() == before.accounts.size() + 1,
                "recipient creation count");
  } else {
    pv::require(recipient_after->second.balance ==
                    recipient_before->second.balance + transfer.amount,
                "recipient credit");
    pv::require(recipient_after->second.nonce ==
                    recipient_before->second.nonce,
                "recipient nonce");
  }
}

void verify_final_state(const p::State& state, const pv::Values& values) {
  pv::require(state.height == 0, "single transfer does not advance height");
  pv::require(state.fee_pool == std::stoull(values.at("fee_pool")),
              "final fee pool");
  pv::require(state.accounts.size() ==
                  std::stoull(values.at("final_account_count")),
              "final account count");
  std::size_t index = 0;
  for (const auto& [identifier, account] : state.accounts) {
    pv::Bytes entry;
    append_hash(entry, identifier);
    pv::append_u64(entry, account.balance);
    pv::append_u64(entry, account.nonce);
    pv::require(
        entry == pv::hex_decode(
                     values.at("final.account" + std::to_string(index))),
        "final account entry");
    ++index;
  }
  require_conservation(state);
}

void verify_nonce_exhaustion(const pv::Values& values,
                             std::array<bool, 9>& results_seen) {
  auto state = initial_state(values);
  auto sender = state.accounts.begin();
  const auto recipient = std::next(sender);
  sender->second.nonce = std::numeric_limits<std::uint64_t>::max();
  const p::Transfer transfer{
      sender->first,
      p::Hash{},
      0,
      recipient->first,
      1,
      state.parameters.fixed_fee,
      kBlockHeight,
  };
  const auto before = state_bytes(state);
  const auto execution =
      p::internal::execute_transfer(transfer, state, kBlockHeight);
  pv::require(std::holds_alternative<p::Receipt>(execution),
              "nonce exhaustion receipt");
  const auto& receipt = std::get<p::Receipt>(execution);
  pv::require(receipt.result == p::TransferResult::nonce_exhausted,
              "nonce exhaustion result");
  pv::require(receipt.fee_charged == 0, "nonce exhaustion fee");
  pv::require(state_bytes(state) == before, "nonce exhaustion atomicity");
  require_conservation(state);
  results_seen[static_cast<std::size_t>(
      p::TransferResult::nonce_exhausted)] = true;
}

void require_execution_error(const p::internal::Execution& execution,
                             p::internal::ExecutionError expected,
                             std::string_view message) {
  pv::require(std::holds_alternative<p::internal::ExecutionError>(execution),
              message);
  pv::require(std::get<p::internal::ExecutionError>(execution) == expected,
              message);
}

void verify_internal_overflow_atomicity(const pv::Values& values) {
  auto recipient_state = initial_state(values);
  auto sender = recipient_state.accounts.begin();
  auto recipient = std::next(sender);
  sender->second = p::Account{recipient_state.parameters.fixed_fee + 1, 0};
  recipient->second.balance = std::numeric_limits<std::uint64_t>::max();
  const p::Transfer recipient_overflow{
      sender->first,
      p::Hash{},
      1,
      recipient->first,
      1,
      recipient_state.parameters.fixed_fee,
      kBlockHeight,
  };
  const auto recipient_before = state_bytes(recipient_state);
  require_execution_error(
      p::internal::execute_transfer(recipient_overflow, recipient_state,
                                    kBlockHeight),
      p::internal::ExecutionError::recipient_balance_overflow,
      "recipient overflow error");
  pv::require(state_bytes(recipient_state) == recipient_before,
              "recipient overflow atomicity");

  auto fee_state = initial_state(values);
  fee_state.fee_pool = std::numeric_limits<std::uint64_t>::max();
  const auto fee_sender = fee_state.accounts.begin();
  const p::Transfer fee_overflow{
      fee_sender->first,
      p::Hash{},
      1,
      fee_sender->first,
      1,
      fee_state.parameters.fixed_fee,
      kBlockHeight,
  };
  const auto fee_before = state_bytes(fee_state);
  require_execution_error(
      p::internal::execute_transfer(fee_overflow, fee_state, kBlockHeight),
      p::internal::ExecutionError::fee_pool_overflow,
      "fee-pool overflow error");
  pv::require(state_bytes(fee_state) == fee_before,
              "fee-pool overflow atomicity");
}

void verify_frozen_sequence(const pv::Values& values) {
  auto state = initial_state(values);
  require_conservation(state);
  std::array<bool, 9> results_seen{};
  bool saw_self_transfer = false;
  bool saw_recipient_creation = false;
  std::size_t receipt_index = 0;
  const auto raw_count = std::stoull(values.at("raw_count"));
  for (std::size_t raw_index = 0; raw_index < raw_count; ++raw_index) {
    const auto key = "raw" + std::to_string(raw_index);
    const auto admission =
        p::admit_transfer(pv::hex_decode(values.at(key)),
                          state.parameters.chain_id);
    const auto expected_admission = std::stoull(values.at(key + ".admission"));
    if (expected_admission != 0) {
      pv::require(std::holds_alternative<p::AdmissionError>(admission),
                  "expected admission failure");
      continue;
    }
    pv::require(std::holds_alternative<p::Transfer>(admission),
                "expected admitted transfer");
    const auto& transfer = std::get<p::Transfer>(admission);
    const auto before = state;
    const auto before_bytes = state_bytes(state);
    const auto recipient_missing =
        state.accounts.find(transfer.recipient) == state.accounts.end();
    const auto execution =
        p::internal::execute_transfer(transfer, state, kBlockHeight);
    pv::require(std::holds_alternative<p::Receipt>(execution),
                "frozen transfer receipt");
    const auto& receipt = std::get<p::Receipt>(execution);
    verify_receipt(receipt, transfer, values, receipt_index);
    const auto result_index = static_cast<std::size_t>(receipt.result);
    pv::require(result_index < results_seen.size(), "known transfer result");
    results_seen[result_index] = true;
    if (receipt.result == p::TransferResult::success) {
      verify_success(before, state, transfer);
      saw_self_transfer |= transfer.sender_id == transfer.recipient;
      saw_recipient_creation |=
          transfer.sender_id != transfer.recipient && recipient_missing;
    } else {
      pv::require(state_bytes(state) == before_bytes,
                  "failed transfer atomicity");
    }
    require_conservation(state);
    ++receipt_index;
  }

  pv::require(receipt_index == std::stoull(values.at("admitted_count")),
              "admitted receipt count");
  verify_nonce_exhaustion(values, results_seen);
  pv::require(std::all_of(results_seen.begin(), results_seen.end(),
                          [](bool seen) { return seen; }),
              "all transfer results covered");
  pv::require(saw_self_transfer, "self-transfer covered");
  pv::require(saw_recipient_creation, "recipient creation covered");
  verify_final_state(state, values);
}

}  // namespace

int main(int argc, char** argv) {
  try {
    pv::require(argc == 2, "usage: kernel_execution_test VECTOR_FILE");
    pv::require(sodium_init() >= 0, "libsodium initialization");
    const auto values = pv::load_values(argv[1]);
    verify_frozen_sequence(values);
    verify_internal_overflow_atomicity(values);
    std::cout << "Kernel execution vectors: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "Kernel execution vectors: failed: " << error.what() << '\n';
    return 1;
  }
}
