#include "economy_internal.hpp"

#include "protocol/v1/crypto.hpp"

#include <algorithm>
#include <string>

namespace protocol::v4 {
namespace {

namespace i = protocol::v4::internal;

// The accepted RFC 9162 shape: split the ordered leaves at the largest power of
// two strictly less than the count, recurse, and hash the two child roots. No
// leaf is duplicated and no padding leaf is inserted.
//
// The version-one kernel holds this construction in a file-private helper, so it
// is restated here rather than shared. What keeps the two equal is not a comment
// but a check: `accounts_root` below is required to reproduce the accepted
// `protocol-primitives-v1` accounts tree root, which the version-one kernel also
// produces, so a divergence in either fails against the same recorded bytes.
std::size_t merkle_split(std::size_t count) {
  std::size_t split = 1;
  while (split < count - split) split <<= 1U;
  return split;
}

Hash merkle(std::span<const Bytes> leaves, std::string_view prefix) {
  const std::string empty_label = std::string(prefix) + "-empty";
  if (leaves.empty()) return protocol::v1::hash(empty_label);
  const std::string leaf_label = std::string(prefix) + "-leaf";
  if (leaves.size() == 1) {
    return protocol::v1::hash(leaf_label, leaves.front());
  }
  const auto split = merkle_split(leaves.size());
  const auto left = merkle(leaves.first(split), prefix);
  const auto right = merkle(leaves.subspan(split), prefix);
  Bytes children;
  children.reserve(left.size() + right.size());
  i::append(children, std::span<const std::uint8_t>(left.data(), left.size()));
  i::append(children, std::span<const std::uint8_t>(right.data(), right.size()));
  return protocol::v1::hash(std::string(prefix) + "-node", children);
}

Bytes with_prefix(Entry entry, std::span<const std::uint8_t> tail) {
  auto key = i::key_prefix(entry);
  i::append(key, tail);
  return key;
}

}  // namespace

Bytes seat_key(std::uint32_t seat_id) {
  auto key = i::key_prefix(Entry::seat);
  i::append_u32(key, seat_id);
  return key;
}

Bytes channel_key(std::uint8_t channel_index) {
  auto key = i::key_prefix(Entry::channel);
  i::append_u8(key, channel_index);
  return key;
}

Bytes cycle_assignment_key(std::uint64_t cycle_window) {
  auto key = i::key_prefix(Entry::cycle_assignment);
  i::append_u64(key, cycle_window);
  return key;
}

Bytes referral_balance_key(std::span<const std::uint8_t> hub_identity_hash) {
  return with_prefix(Entry::referral_balance, hub_identity_hash);
}

Bytes direct_decision_key(std::span<const std::uint8_t> decision_id) {
  return with_prefix(Entry::direct_decision, decision_id);
}

Bytes typed_custody_key(std::uint8_t beneficiary_kind,
                        std::span<const std::uint8_t> beneficiary_id) {
  auto key = i::key_prefix(Entry::typed_custody);
  i::append_u8(key, beneficiary_kind);
  i::append(key, beneficiary_id);
  return key;
}

Bytes carry_key(std::uint8_t channel_index) {
  auto key = i::key_prefix(Entry::carry);
  i::append_u8(key, channel_index);
  return key;
}

Bytes verifier_key_key() { return i::key_prefix(Entry::verifier_key); }

Bytes seat_manager_key(std::uint32_t seat_id,
                       std::span<const std::uint8_t> manager_account_id) {
  auto key = i::key_prefix(Entry::seat_manager);
  i::append_u32(key, seat_id);
  i::append(key, manager_account_id);
  return key;
}

Bytes hub_identity_key(std::span<const std::uint8_t> hub_identity_hash) {
  return with_prefix(Entry::hub_identity, hub_identity_hash);
}

Bytes hub_address_key(std::span<const std::uint8_t> account_id) {
  return with_prefix(Entry::hub_address, account_id);
}

Bytes unreferred_pool_key() { return i::key_prefix(Entry::unreferred_pool); }

Bytes seat_value(const SeatRecord& seat) {
  Bytes value;
  value.reserve(119);
  i::append(value, seat.hub_identity_hash);
  i::append(value, seat.purchaser_account_id);
  i::append_u8(value, seat.has_referrer ? 1 : 0);
  if (seat.has_referrer) {
    i::append(value, seat.referrer_hub_identity);
  } else {
    value.insert(value.end(), 32, 0);
  }
  i::append_u8(value, seat.is_activated ? 1 : 0);
  i::append_u64(value, seat.is_activated ? seat.activation_height : 0);
  i::append_u64(value, seat.minted_through_window);
  i::append_u8(value, seat.mint_requires_biometric ? 1 : 0);
  i::append_u32(value, seat.manager_count);
  return value;
}

Bytes channel_value(std::uint64_t issued_atomic, std::uint64_t outstanding_atomic) {
  Bytes value;
  i::append_u64(value, issued_atomic);
  i::append_u64(value, outstanding_atomic);
  return value;
}

Bytes referral_balance_value(std::uint64_t accrued_atomic,
                             std::uint64_t minted_atomic,
                             std::uint64_t collected_through_window) {
  Bytes value;
  i::append_u64(value, accrued_atomic);
  i::append_u64(value, minted_atomic);
  i::append_u64(value, collected_through_window);
  return value;
}

Bytes unreferred_pool_value(std::uint64_t accrued_atomic,
                            std::uint64_t minted_atomic) {
  Bytes value;
  i::append_u64(value, accrued_atomic);
  i::append_u64(value, minted_atomic);
  return value;
}

Bytes typed_custody_value(std::uint64_t amount_atomic) {
  Bytes value;
  i::append_u64(value, amount_atomic);
  return value;
}

Bytes carry_value(std::uint64_t carry_atomic) {
  Bytes value;
  i::append_u64(value, carry_atomic);
  return value;
}

Bytes verifier_key_value(std::span<const std::uint8_t> public_key) {
  return Bytes(public_key.begin(), public_key.end());
}

Bytes hub_identity_value(const HubIdentityRecord& identity) {
  Bytes value;
  value.reserve(48);
  i::append(value, identity.hub_public_key);
  i::append_u64(value, identity.registered_at_height);
  i::append_u32(value, identity.address_count);
  i::append_u32(value, identity.seat_count);
  return value;
}

Bytes hub_address_value(std::span<const std::uint8_t> hub_identity_hash) {
  return Bytes(hub_identity_hash.begin(), hub_identity_hash.end());
}

std::size_t bitmap_bytes(std::uint32_t bitmap_bits) {
  return (static_cast<std::size_t>(bitmap_bits) + 7) / 8;
}

Bytes bitmap(std::span<const std::uint32_t> seat_ids, std::uint32_t bitmap_bits) {
  Bytes packed(bitmap_bytes(bitmap_bits), 0);
  for (const auto seat_id : seat_ids) {
    if (seat_id >= bitmap_bits) return {};
    packed[seat_id / 8] |= static_cast<std::uint8_t>(0x80U >> (seat_id % 8));
  }
  return packed;
}

bool bit_is_set(std::span<const std::uint8_t> packed, std::uint32_t seat_id) {
  const std::size_t index = seat_id / 8;
  if (index >= packed.size()) return false;
  return (packed[index] & static_cast<std::uint8_t>(0x80U >> (seat_id % 8))) != 0;
}

Bytes cycle_assignment_value(const CycleAssignment& assignment) {
  const auto width = bitmap_bytes(assignment.bitmap_bits);
  if (assignment.accrued_bitmap.size() != width ||
      assignment.winner_bitmap.size() != width) {
    return {};
  }
  Bytes value;
  value.reserve(24 + 2 * width);
  i::append_u64(value, assignment.share_per_winner_atomic);
  i::append_u32(value, assignment.reallocated_count);
  i::append_u32(value, assignment.winner_count);
  i::append_u32(value, assignment.in_scope_count);
  i::append_u32(value, assignment.bitmap_bits);
  i::append(value, assignment.accrued_bitmap);
  i::append(value, assignment.winner_bitmap);
  return value;
}

std::optional<CycleAssignment> decode_cycle_assignment_value(
    std::span<const std::uint8_t> raw) {
  constexpr std::size_t kFixed = 24;
  if (raw.size() < kFixed) return std::nullopt;
  CycleAssignment assignment;
  const auto share = i::read_u64(raw, 0);
  const auto reallocated = i::read_u32(raw, 8);
  const auto winners = i::read_u32(raw, 12);
  const auto in_scope = i::read_u32(raw, 16);
  const auto bits = i::read_u32(raw, 20);
  if (!share || !reallocated || !winners || !in_scope || !bits) return std::nullopt;
  const auto width = bitmap_bytes(*bits);
  if (raw.size() != kFixed + 2 * width) return std::nullopt;
  assignment.share_per_winner_atomic = *share;
  assignment.reallocated_count = *reallocated;
  assignment.winner_count = *winners;
  assignment.in_scope_count = *in_scope;
  assignment.bitmap_bits = *bits;
  const auto accrued = raw.subspan(kFixed, width);
  const auto winner = raw.subspan(kFixed + width, width);
  assignment.accrued_bitmap.assign(accrued.begin(), accrued.end());
  assignment.winner_bitmap.assign(winner.begin(), winner.end());
  return assignment;
}

Hash economy_root(std::vector<EconomyEntry> entries) {
  std::sort(entries.begin(), entries.end(),
            [](const EconomyEntry& left, const EconomyEntry& right) {
              return left.key < right.key;
            });
  std::vector<Bytes> leaves;
  leaves.reserve(entries.size());
  for (const auto& entry : entries) {
    Bytes leaf;
    leaf.reserve(8 + entry.key.size() + entry.value.size());
    i::append_length_prefixed(leaf, entry.key);
    i::append_length_prefixed(leaf, entry.value);
    leaves.push_back(std::move(leaf));
  }
  return merkle(leaves, kEconomyTreePrefix);
}

Hash accounts_root(std::span<const AccountEntry> accounts) {
  std::vector<Bytes> leaves;
  leaves.reserve(accounts.size());
  for (const auto& account : accounts) {
    Bytes leaf;
    leaf.reserve(48);
    i::append(leaf, account.account_id);
    i::append_u64(leaf, account.balance);
    i::append_u64(leaf, account.nonce);
    leaves.push_back(std::move(leaf));
  }
  return merkle(leaves, kAccountsTreePrefix);
}

Hash state_root(const StateSummary& summary, std::span<const AccountEntry> accounts,
                std::vector<EconomyEntry> economy) {
  const auto economy_count = economy.size();
  const auto economy_hash = economy_root(std::move(economy));
  const auto accounts_hash = accounts_root(accounts);

  Bytes payload;
  i::append_u16(payload, kStateRootSchemaVersion);
  i::append(payload, summary.chain_id);
  i::append_u64(payload, summary.height);
  i::append_u64(payload, summary.supply_limit);
  i::append_u64(payload, summary.total_supply);
  i::append_u64(payload, summary.fee_pool_balance);
  i::append_u64(payload, static_cast<std::uint64_t>(accounts.size()));
  i::append(payload, std::span<const std::uint8_t>(accounts_hash.data(),
                                                   accounts_hash.size()));
  i::append_u64(payload, static_cast<std::uint64_t>(economy_count));
  i::append(payload,
            std::span<const std::uint8_t>(economy_hash.data(), economy_hash.size()));
  return protocol::v1::hash(kStateRootLabel, payload);
}

}  // namespace protocol::v4
