#pragma once

#include "protocol/v1/types.hpp"

#include <variant>

namespace protocol::v1::internal {

enum class ExecutionError : std::uint8_t {
  recipient_balance_overflow = 1,
  fee_pool_overflow = 2,
};

using Execution = std::variant<Receipt, ExecutionError>;

Execution execute_transfer(const Transfer& transfer, State& state,
                           std::uint64_t block_height);

}  // namespace protocol::v1::internal
