#include "execution.hpp"

#include <limits>

namespace protocol::v1::internal {
namespace {

Receipt receipt(const Transfer& transfer, TransferResult result,
                std::uint64_t fee) {
  return Receipt{transfer.transaction_id, result, fee};
}

Execution failure(const Transfer& transfer, TransferResult result) {
  return receipt(transfer, result, 0);
}

}  // namespace

Execution execute_transfer(const Transfer& transfer, State& state,
                           std::uint64_t block_height) {
  const auto fixed_fee = state.parameters.fixed_fee;
  if (transfer.amount == 0) {
    return failure(transfer, TransferResult::zero_amount);
  }
  if (transfer.fee_limit < fixed_fee) {
    return failure(transfer, TransferResult::fee_limit_too_low);
  }
  if (transfer.valid_until < block_height) {
    return failure(transfer, TransferResult::expired);
  }

  const auto sender_it = state.accounts.find(transfer.sender_id);
  if (sender_it == state.accounts.end()) {
    return failure(transfer, TransferResult::sender_not_found);
  }
  const auto& sender = sender_it->second;
  if (sender.nonce == std::numeric_limits<std::uint64_t>::max()) {
    return failure(transfer, TransferResult::nonce_exhausted);
  }
  if (transfer.nonce != sender.nonce + 1) {
    return failure(transfer, TransferResult::nonce_mismatch);
  }
  if (transfer.amount >
      std::numeric_limits<std::uint64_t>::max() - fixed_fee) {
    return failure(transfer, TransferResult::debit_overflow);
  }

  const auto debit = transfer.amount + fixed_fee;
  if (sender.balance < debit) {
    return failure(transfer, TransferResult::insufficient_balance);
  }

  const bool self_transfer = transfer.sender_id == transfer.recipient;
  const auto recipient_it = state.accounts.find(transfer.recipient);
  if (!self_transfer && recipient_it != state.accounts.end() &&
      recipient_it->second.balance >
          std::numeric_limits<std::uint64_t>::max() - transfer.amount) {
    return ExecutionError::recipient_balance_overflow;
  }
  if (state.fee_pool >
      std::numeric_limits<std::uint64_t>::max() - fixed_fee) {
    return ExecutionError::fee_pool_overflow;
  }

  if (self_transfer) {
    sender_it->second.balance -= fixed_fee;
  } else {
    if (recipient_it == state.accounts.end()) {
      state.accounts.emplace(transfer.recipient, Account{transfer.amount, 0});
    } else {
      recipient_it->second.balance += transfer.amount;
    }
    sender_it->second.balance -= debit;
  }
  sender_it->second.nonce = transfer.nonce;
  state.fee_pool += fixed_fee;
  return receipt(transfer, TransferResult::success, fixed_fee);
}

}  // namespace protocol::v1::internal
