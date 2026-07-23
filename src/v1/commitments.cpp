#include "commitments.hpp"

#include "protocol/v1/crypto.hpp"

#include <limits>
#include <span>
#include <string_view>
#include <vector>

namespace protocol::v1::internal {
namespace {

void append(Bytes& target, std::span<const std::uint8_t> value) {
  target.insert(target.end(), value.begin(), value.end());
}

void append_u16(Bytes& target, std::uint16_t value) {
  target.push_back(static_cast<std::uint8_t>(value >> 8U));
  target.push_back(static_cast<std::uint8_t>(value));
}

void append_u32(Bytes& target, std::uint32_t value) {
  for (int shift = 24; shift >= 0; shift -= 8) {
    target.push_back(static_cast<std::uint8_t>(value >> shift));
  }
}

void append_u64(Bytes& target, std::uint64_t value) {
  for (int shift = 56; shift >= 0; shift -= 8) {
    target.push_back(static_cast<std::uint8_t>(value >> shift));
  }
}

std::size_t merkle_split(std::size_t count) {
  std::size_t split = 1;
  while (split < count - split) split <<= 1U;
  return split;
}

template <typename Tag>
std::span<const std::uint8_t> item_bytes(const TaggedHash<Tag>& value) {
  return {value.data(), value.size()};
}

std::span<const std::uint8_t> item_bytes(const Bytes& value) {
  return {value.data(), value.size()};
}

template <typename Item>
Hash merkle(std::span<const Item> items, std::string_view empty_label,
            std::string_view leaf_label, std::string_view node_label) {
  if (items.empty()) return protocol::v1::hash(empty_label);
  if (items.size() == 1) {
    return protocol::v1::hash(leaf_label, item_bytes(items.front()));
  }
  const auto split = merkle_split(items.size());
  const auto left =
      merkle(items.first(split), empty_label, leaf_label, node_label);
  const auto right =
      merkle(items.subspan(split), empty_label, leaf_label, node_label);
  Bytes children;
  children.reserve(left.size() + right.size());
  append(children, left);
  append(children, right);
  return protocol::v1::hash(node_label, children);
}

Bytes account_entry(const AccountId& identifier, const Account& account) {
  Bytes entry;
  entry.reserve(48);
  append(entry, identifier);
  append_u64(entry, account.balance);
  append_u64(entry, account.nonce);
  return entry;
}

bool valid_result(TransferResult result) {
  return static_cast<std::uint8_t>(result) <=
         static_cast<std::uint8_t>(TransferResult::insufficient_balance);
}

}  // namespace

StateCommitment state_root(const State& state) {
  const auto& parameters = state.parameters;
  if (parameters.supply_limit == 0 || parameters.total_supply == 0 ||
      parameters.fixed_fee == 0 ||
      parameters.total_supply > parameters.supply_limit) {
    return StateError::invalid_parameters;
  }

  auto conserved_supply = state.fee_pool;
  std::vector<Bytes> entries;
  entries.reserve(state.accounts.size());
  for (const auto& [identifier, account] : state.accounts) {
    if (account.balance >
        std::numeric_limits<std::uint64_t>::max() - conserved_supply) {
      return StateError::supply_overflow;
    }
    conserved_supply += account.balance;
    entries.push_back(account_entry(identifier, account));
  }
  if (conserved_supply != parameters.total_supply) {
    return StateError::supply_mismatch;
  }

  const auto accounts_root =
      merkle<Bytes>(entries, "protocol-stack:v1:state-empty",
                    "protocol-stack:v1:state-leaf",
                    "protocol-stack:v1:state-node");
  Bytes payload;
  payload.reserve(106);
  append_u16(payload, 1);
  append(payload, parameters.chain_id);
  append_u64(payload, state.height);
  append_u64(payload, parameters.supply_limit);
  append_u64(payload, parameters.total_supply);
  append_u64(payload, state.fee_pool);
  if constexpr (sizeof(std::size_t) > sizeof(std::uint64_t)) {
    if (entries.size() > std::numeric_limits<std::uint64_t>::max()) {
      return StateError::invalid_parameters;
    }
  }
  append_u64(payload, static_cast<std::uint64_t>(entries.size()));
  append(payload, accounts_root);
  return StateRoot(
      protocol::v1::hash("protocol-stack:v1:state-root", payload));
}

TransactionRoot transaction_root(
    std::span<const TransactionId> transaction_ids) {
  return TransactionRoot(
      merkle<TransactionId>(transaction_ids, "protocol-stack:v1:tx-empty",
                            "protocol-stack:v1:tx-leaf",
                            "protocol-stack:v1:tx-node"));
}

std::optional<Bytes> encode_receipt(const Receipt& receipt,
                                    std::uint64_t fixed_fee) {
  if (!valid_result(receipt.result)) return std::nullopt;
  const bool success = receipt.result == TransferResult::success;
  if ((success && receipt.fee_charged != fixed_fee) ||
      (!success && receipt.fee_charged != 0)) {
    return std::nullopt;
  }

  Bytes encoded{'P', 'S', 'R', 'C'};
  encoded.reserve(47);
  append_u16(encoded, 1);
  append(encoded, receipt.transaction_id);
  encoded.push_back(static_cast<std::uint8_t>(receipt.result));
  append_u64(encoded, receipt.fee_charged);
  return encoded;
}

Bytes encode_block_header(const ChainId& chain_id, std::uint64_t height,
                          const StateRoot& previous_state_root,
                          const TransactionRoot& transaction_root_value,
                          const StateRoot& resulting_state_root,
                          std::uint32_t transaction_count) {
  Bytes encoded{'P', 'S', 'B', 'L'};
  encoded.reserve(146);
  append_u16(encoded, 1);
  append(encoded, chain_id);
  append_u64(encoded, height);
  append(encoded, previous_state_root);
  append(encoded, transaction_root_value);
  append(encoded, resulting_state_root);
  append_u32(encoded, transaction_count);
  return encoded;
}

std::optional<BlockId> block_id(std::span<const std::uint8_t> header) {
  constexpr std::size_t kHeaderSize = 146;
  if (header.size() != kHeaderSize || header[0] != 'P' ||
      header[1] != 'S' || header[2] != 'B' || header[3] != 'L' ||
      header[4] != 0 || header[5] != 1) {
    return std::nullopt;
  }
  return BlockId(protocol::v1::hash("protocol-stack:v1:block-id", header));
}

}  // namespace protocol::v1::internal
