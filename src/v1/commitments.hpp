#pragma once

#include "protocol/v1/types.hpp"

#include <cstdint>
#include <optional>
#include <span>
#include <variant>

namespace protocol::v1::internal {

enum class StateError : std::uint8_t {
  invalid_parameters = 1,
  supply_overflow = 2,
  supply_mismatch = 3,
};

using StateCommitment = std::variant<StateRoot, StateError>;

StateCommitment state_root(const State& state);

TransactionRoot transaction_root(
    std::span<const TransactionId> transaction_ids);

std::optional<Bytes> encode_receipt(const Receipt& receipt,
                                    std::uint64_t fixed_fee);

Bytes encode_block_header(const ChainId& chain_id, std::uint64_t height,
                          const StateRoot& previous_state_root,
                          const TransactionRoot& transaction_root,
                          const StateRoot& resulting_state_root,
                          std::uint32_t transaction_count);

std::optional<BlockId> block_id(std::span<const std::uint8_t> header);

}  // namespace protocol::v1::internal
