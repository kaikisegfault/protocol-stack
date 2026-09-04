// The economy tree, the version-eight state root, and the one variable-width
// value the tree has to size for itself.
//
// The roots are fallible because an entry no transition could have written is
// refused rather than hashed: a hash cannot signal an unknown kind, a wrong
// width, or a duplicated key, and the specification forbids all three.

#include "economy_internal.hpp"

#include "protocol/v1/crypto.hpp"

#include <algorithm>
#include <string>

namespace protocol::v8 {
namespace {

namespace i = protocol::v8::internal;

// The accepted RFC 9162 shape: split the ordered leaves at the largest power of
// two strictly less than the count, recurse, and hash the two child roots. No
// leaf is duplicated and no padding leaf is inserted.
//
// The version-one kernel holds this construction in a file-private helper, so it
// is restated here rather than shared. What keeps the two equal is not a comment
// but a check: `accounts_root` below is required to reproduce the accepted
// `protocol-primitives-v1` accounts tree root, which the version-one kernel also
// produces, so a divergence in either fails against the same recorded bytes.
//
// Three trees run through it under three prefixes — the economy tree, the
// accounts tree, and version one's ordered transaction tree — so no caller holds
// a second opinion about the shape, and each is pinned by a different accepted
// vector file.
std::size_t merkle_split(std::size_t count) {
  std::size_t split = 1;
  while (split < count - split) split <<= 1U;
  return split;
}

struct TreeLabels {
  std::string empty;
  std::string leaf;
  std::string node;
};

TreeLabels tree_labels(std::string_view prefix) {
  return {std::string(prefix) + "-empty", std::string(prefix) + "-leaf",
          std::string(prefix) + "-node"};
}

// The labels are built once and passed down rather than rebuilt at every node,
// which matters at the seat capacity: a 100,000-leaf tree would otherwise
// allocate three strings per interior node.
Hash merkle(std::span<const Bytes> leaves, const TreeLabels& labels) {
  if (leaves.empty()) return protocol::v1::hash(labels.empty);
  if (leaves.size() == 1) return protocol::v1::hash(labels.leaf, leaves.front());
  const auto split = merkle_split(leaves.size());
  const auto left = merkle(leaves.first(split), labels);
  const auto right = merkle(leaves.subspan(split), labels);
  Bytes children;
  children.reserve(left.size() + right.size());
  i::append(children, left);
  i::append(children, right);
  return protocol::v1::hash(labels.node, children);
}

// An entry no transition could have written: an unknown or retired kind, a key
// or value of the wrong width, or a cycle assignment whose length disagrees
// with its own recorded bit count. The specification forbids all of them, and a
// hash cannot signal any, which is why the root is fallible.
//
// **Version eight's two entries are checked by content and not only by width**,
// because both carry a value whose width admits states the contract forbids: an
// open challenge is `0` or `1` and nothing else, and a window record's pad bits
// must be clear with `disputed` a subset of `credited`. A width check alone
// would let a root be taken over a state no transition could reach.
bool entry_shape_is_valid(const EconomyEntry& entry) {
  if (entry.key.empty()) return false;
  const auto kind = entry.key.front();
  if (!is_entry_kind(kind)) return false;
  const auto key_width = entry_key_bytes(kind);
  if (!key_width || entry.key.size() != *key_width) return false;
  const auto value_width = entry_value_bytes(kind);
  if (!value_width) return decode_cycle_assignment_value(entry.value).has_value();
  if (entry.value.size() != *value_width) return false;
  if (kind == static_cast<std::uint8_t>(Entry::open_challenge)) {
    return decode_open_challenge_value(entry.value).has_value();
  }
  if (kind == static_cast<std::uint8_t>(Entry::seat_window)) {
    return decode_seat_window_value(entry.value).has_value();
  }
  return true;
}

}  // namespace

namespace internal {

Hash merkle_root(std::span<const Bytes> leaves, std::string_view prefix) {
  return merkle(leaves, tree_labels(prefix));
}

}  // namespace internal

std::size_t bitmap_bytes(std::uint32_t bitmap_bits) {
  return (static_cast<std::size_t>(bitmap_bits) + 7) / 8;
}

std::optional<Bytes> bitmap(std::span<const std::uint32_t> seat_ids,
                            std::uint32_t bitmap_bits) {
  Bytes packed(bitmap_bytes(bitmap_bits), 0);
  for (const auto seat_id : seat_ids) {
    if (seat_id >= bitmap_bits) return std::nullopt;
    packed[seat_id / 8] |= static_cast<std::uint8_t>(0x80U >> (seat_id % 8));
  }
  return packed;
}

bool bit_is_set(std::span<const std::uint8_t> packed, std::uint32_t seat_id) {
  const std::size_t index = seat_id / 8;
  if (index >= packed.size()) return false;
  return (packed[index] & static_cast<std::uint8_t>(0x80U >> (seat_id % 8))) != 0;
}

// A cycle with no winner absorbs nothing, so a record carrying a nonzero
// absorbed amount at a zero winner count describes value divided by nobody.
// **Both directions refuse it**, and that is deliberate rather than duplicated:
// the encoder refuses to write a state entry no settlement could produce, and
// the decoder refuses to read one off a wire the encoder does not control.
bool absorbed_is_representable(std::uint32_t winner_count,
                               const RecoveryPool& absorbed) {
  if (winner_count != 0) return true;
  for (const auto amount : absorbed) {
    if (amount != 0) return false;
  }
  return true;
}

std::optional<Bytes> cycle_assignment_value(const CycleAssignment& assignment) {
  const auto width = bitmap_bytes(assignment.bitmap_bits);
  if (assignment.accrued_bitmap.size() != width ||
      assignment.winner_bitmap.size() != width) {
    return std::nullopt;
  }
  if (!absorbed_is_representable(assignment.winner_count,
                                 assignment.pool_absorbed)) {
    return std::nullopt;
  }
  Bytes value;
  value.reserve(kCycleAssignmentFixedBytes + 2 * width);
  i::append_u64(value, assignment.share_per_winner_atomic);
  i::append_u32(value, assignment.reallocated_count);
  i::append_u32(value, assignment.winner_count);
  i::append_u32(value, assignment.in_scope_count);
  i::append_u32(value, assignment.bitmap_bits);
  for (const auto amount : assignment.pool_absorbed) i::append_u64(value, amount);
  i::append(value, assignment.accrued_bitmap);
  i::append(value, assignment.winner_bitmap);
  return value;
}

std::optional<CycleAssignment> decode_cycle_assignment_value(
    std::span<const std::uint8_t> raw) {
  constexpr std::size_t kFixed = kCycleAssignmentFixedBytes;
  if (raw.size() < kFixed) return std::nullopt;
  CycleAssignment assignment;
  const auto share = i::read_u64(raw, 0);
  const auto reallocated = i::read_u32(raw, 8);
  const auto winners = i::read_u32(raw, 12);
  const auto in_scope = i::read_u32(raw, 16);
  const auto bits = i::read_u32(raw, 20);
  if (!share || !reallocated || !winners || !in_scope || !bits) return std::nullopt;
  RecoveryPool absorbed{};
  for (std::size_t index = 0; index < kRecoveryPoolLegs; ++index) {
    const auto amount = i::read_u64(raw, 24 + 8 * index);
    if (!amount) return std::nullopt;
    absorbed[index] = *amount;
  }
  if (!absorbed_is_representable(*winners, absorbed)) return std::nullopt;
  const auto width = bitmap_bytes(*bits);
  if (raw.size() != kFixed + 2 * width) return std::nullopt;
  assignment.share_per_winner_atomic = *share;
  assignment.reallocated_count = *reallocated;
  assignment.winner_count = *winners;
  assignment.in_scope_count = *in_scope;
  assignment.bitmap_bits = *bits;
  assignment.pool_absorbed = absorbed;
  const auto accrued = raw.subspan(kFixed, width);
  const auto winner = raw.subspan(kFixed + width, width);
  assignment.accrued_bitmap.assign(accrued.begin(), accrued.end());
  assignment.winner_bitmap.assign(winner.begin(), winner.end());
  return assignment;
}

std::optional<Hash> economy_root(std::vector<EconomyEntry> entries) {
  std::sort(entries.begin(), entries.end(),
            [](const EconomyEntry& left, const EconomyEntry& right) {
              return left.key < right.key;
            });
  std::vector<Bytes> leaves;
  leaves.reserve(entries.size());
  for (std::size_t index = 0; index < entries.size(); ++index) {
    const auto& entry = entries[index];
    if (!entry_shape_is_valid(entry)) return std::nullopt;
    if (index > 0 && entries[index - 1].key == entry.key) return std::nullopt;
    Bytes leaf;
    leaf.reserve(8 + entry.key.size() + entry.value.size());
    i::append_length_prefixed(leaf, entry.key);
    i::append_length_prefixed(leaf, entry.value);
    leaves.push_back(std::move(leaf));
  }
  return merkle(leaves, tree_labels(kEconomyTreePrefix));
}

Hash accounts_root(std::span<const AccountEntry> accounts) {
  std::vector<Bytes> leaves;
  leaves.reserve(accounts.size());
  for (const auto& account : accounts) {
    Bytes leaf;
    leaf.reserve(kAccountEntryBytes);
    i::append(leaf, account.account_id);
    i::append_u64(leaf, account.balance);
    i::append_u64(leaf, account.nonce);
    leaves.push_back(std::move(leaf));
  }
  return merkle(leaves, tree_labels(kAccountsTreePrefix));
}

std::optional<StateRootFrame> state_root_frame(
    const StateSummary& summary, std::span<const AccountEntry> accounts,
    std::vector<EconomyEntry> economy) {
  const auto economy_count = economy.size();
  const auto economy_hash = economy_root(std::move(economy));
  if (!economy_hash) return std::nullopt;
  const auto accounts_hash = accounts_root(accounts);

  StateRootFrame frame;
  i::append_u16(frame.head, kStateRootSchemaVersion);
  i::append(frame.head, summary.chain_id);
  i::append_u64(frame.tail, summary.supply_limit);
  i::append_u64(frame.tail, summary.total_supply);
  i::append_u64(frame.tail, summary.fee_pool_balance);
  i::append_u64(frame.tail, static_cast<std::uint64_t>(accounts.size()));
  i::append(frame.tail, accounts_hash);
  i::append_u64(frame.tail, static_cast<std::uint64_t>(economy_count));
  i::append(frame.tail, *economy_hash);
  return frame;
}

Hash state_root_from_frame(const StateRootFrame& frame, std::uint64_t height) {
  Bytes payload;
  payload.reserve(frame.head.size() + 8 + frame.tail.size());
  i::append(payload, frame.head);
  i::append_u64(payload, height);
  i::append(payload, frame.tail);
  return protocol::v1::hash(kStateRootLabel, payload);
}

// Defined through the two above rather than beside them, so the fast path and
// the ordinary path are the same preimage by construction.
std::optional<Hash> state_root(const StateSummary& summary,
                               std::span<const AccountEntry> accounts,
                               std::vector<EconomyEntry> economy) {
  const auto frame = state_root_frame(summary, accounts, std::move(economy));
  if (!frame) return std::nullopt;
  return state_root_from_frame(*frame, summary.height);
}

// An earlier version's root over the same inputs, so that each of the seven
// non-collisions is a claim about two derived digests rather than about two
// strings. Distinct labels are strings rather than a chain: refusing one
// collision implies nothing about another, so version eight must prove seven.
//
// **Version one's preimage has no economy half at all**, which is why it is
// written out rather than folded into the loop: it ends at the accounts root,
// and a version-one root over an empty economy is not the same object as a
// version-two root over one.
std::optional<Hash> predecessor_state_root(std::uint16_t version,
                                           const StateSummary& summary,
                                           std::span<const AccountEntry> accounts,
                                           std::vector<EconomyEntry> economy) {
  if (version < 1 || version > 7) return std::nullopt;
  const auto label = "protocol-stack:v" + std::to_string(version) + ":state-root";

  Bytes payload;
  i::append_u16(payload, version);
  i::append(payload, summary.chain_id);
  i::append_u64(payload, summary.height);
  i::append_u64(payload, summary.supply_limit);
  i::append_u64(payload, summary.total_supply);
  i::append_u64(payload, summary.fee_pool_balance);
  i::append_u64(payload, static_cast<std::uint64_t>(accounts.size()));
  i::append(payload, accounts_root(accounts));
  if (version == 1) return protocol::v1::hash(label, payload);

  const auto economy_count = economy.size();
  const auto prefix = "protocol-stack:v" + std::to_string(version) + ":economy";
  std::sort(economy.begin(), economy.end(),
            [](const EconomyEntry& left, const EconomyEntry& right) {
              return left.key < right.key;
            });
  std::vector<Bytes> leaves;
  leaves.reserve(economy_count);
  for (const auto& entry : economy) {
    Bytes leaf;
    leaf.reserve(8 + entry.key.size() + entry.value.size());
    i::append_length_prefixed(leaf, entry.key);
    i::append_length_prefixed(leaf, entry.value);
    leaves.push_back(std::move(leaf));
  }
  i::append_u64(payload, static_cast<std::uint64_t>(economy_count));
  i::append(payload, merkle(leaves, tree_labels(prefix)));
  return protocol::v1::hash(label, payload);
}

}  // namespace protocol::v8
