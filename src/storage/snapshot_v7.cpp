// The version-seven snapshot's framing: the prefix, the two ordered sections,
// the digest, and the three gates a restore must pass.
//
// **The payload is the state root's own inputs and nothing else** — the summary,
// the ordered account map, and the ordered economy map — plus the two genesis
// parameters a restored ledger needs in order to keep executing rather than
// merely to verify: the fixed fee and the ecosystem verifier key.
//
// **Ordering is checked on the way in.** Account identifiers must strictly
// increase and economy keys must strictly increase, because both trees are over
// ordered sets: a payload that repeated or reordered one could not produce the
// root it claims, and catching it at the parse is cheaper than at the root and
// names its subject.

#include "snapshot_v7_internal.hpp"

#include "protocol/v1/crypto.hpp"

#include <algorithm>
#include <cstddef>
#include <limits>
#include <optional>
#include <string_view>
#include <utility>
#include <variant>
#include <vector>

namespace protocol::storage {
namespace {

using snapshot_v7::read_fixed;
using snapshot_v7::read_u16;
using snapshot_v7::read_u32;
using snapshot_v7::read_u64;
namespace v7 = protocol::v7;

// The magic is version one's. A snapshot family with one magic and a version
// field is what the version field is for: version one's decoder reads these
// bytes, recognises the family, and reports an unsupported version rather than
// malformed input.
constexpr std::array<std::uint8_t, 4> kMagic{'P', 'S', 'S', 'N'};
constexpr std::uint16_t kVersion = 7;
constexpr std::size_t kPrefixSize = 126;
constexpr std::size_t kAccountSize = v7::kAccountEntryBytes;
constexpr std::size_t kRootSize = 32;
constexpr std::size_t kDigestSize = 32;
constexpr std::size_t kFixedSize = kPrefixSize + kRootSize + kDigestSize;
constexpr std::string_view kDigestDomain = "protocol-stack:storage:snapshot-v7";

void append(v7::Bytes& target, std::span<const std::uint8_t> bytes) {
  target.insert(target.end(), bytes.begin(), bytes.end());
}

void append_u16(v7::Bytes& target, std::uint16_t value) {
  target.push_back(static_cast<std::uint8_t>(value >> 8U));
  target.push_back(static_cast<std::uint8_t>(value));
}

void append_u32(v7::Bytes& target, std::uint32_t value) {
  for (int shift = 24; shift >= 0; shift -= 8) {
    target.push_back(static_cast<std::uint8_t>(value >> shift));
  }
}

void append_u64(v7::Bytes& target, std::uint64_t value) {
  for (int shift = 56; shift >= 0; shift -= 8) {
    target.push_back(static_cast<std::uint8_t>(value >> shift));
  }
}

// The accepted `bytes(x)` primitive, which is also the shape the economy tree's
// leaf preimage uses for both halves. The economy section is therefore the
// concatenation of the leaves the root is taken over, in the same order.
void append_length_prefixed(v7::Bytes& target,
                            std::span<const std::uint8_t> bytes) {
  append_u32(target, static_cast<std::uint32_t>(bytes.size()));
  append(target, bytes);
}

[[nodiscard]] bool add_size(std::size_t& total, std::size_t amount) {
  if (amount > std::numeric_limits<std::size_t>::max() - total) return false;
  total += amount;
  return true;
}

// Every field the payload restates about the whole state, read back rather than
// recomputed, so gate 2 compares the payload against itself where gate 1
// compares the rebuilt ledger against the payload.
struct Prefix {
  v7::StateSummary summary;
  std::uint64_t fixed_fee = 0;
  v7::Octets32 verifier_key{};
  std::uint64_t account_count = 0;
  std::uint64_t economy_count = 0;
};

std::optional<Prefix> read_prefix(std::span<const std::uint8_t> payload) {
  Prefix prefix;
  const auto chain_id = read_fixed<32>(payload, 6);
  const auto height = read_u64(payload, 38);
  const auto supply_limit = read_u64(payload, 46);
  const auto total_supply = read_u64(payload, 54);
  const auto fee_pool = read_u64(payload, 62);
  const auto fixed_fee = read_u64(payload, 70);
  const auto verifier_key = read_fixed<32>(payload, 78);
  const auto account_count = read_u64(payload, 110);
  const auto economy_count = read_u64(payload, 118);
  if (!chain_id || !height || !supply_limit || !total_supply || !fee_pool ||
      !fixed_fee || !verifier_key || !account_count || !economy_count) {
    return std::nullopt;
  }
  prefix.summary.chain_id = *chain_id;
  prefix.summary.height = *height;
  prefix.summary.supply_limit = *supply_limit;
  prefix.summary.total_supply = *total_supply;
  prefix.summary.fee_pool_balance = *fee_pool;
  prefix.fixed_fee = *fixed_fee;
  prefix.verifier_key = *verifier_key;
  prefix.account_count = *account_count;
  prefix.economy_count = *economy_count;
  return prefix;
}

// Strictly increasing identifiers, decoded into the shape the accounts tree
// takes. A repeated or reordered identifier is refused rather than hashed.
std::optional<std::vector<v7::AccountEntry>> read_accounts(
    std::span<const std::uint8_t> payload, std::size_t& offset,
    std::size_t count) {
  std::vector<v7::AccountEntry> accounts;
  accounts.reserve(count);
  for (std::size_t index = 0; index < count; ++index) {
    const auto account_id = read_fixed<32>(payload, offset);
    const auto balance = read_u64(payload, offset + 32);
    const auto nonce = read_u64(payload, offset + 40);
    if (!account_id || !balance || !nonce) return std::nullopt;
    if (index > 0 && !(accounts.back().account_id < *account_id)) {
      return std::nullopt;
    }
    accounts.push_back(v7::AccountEntry{*account_id, *balance, *nonce});
    offset += kAccountSize;
  }
  return accounts;
}

std::optional<std::vector<v7::EconomyEntry>> read_economy(
    std::span<const std::uint8_t> section, std::size_t& offset,
    std::size_t count) {
  std::vector<v7::EconomyEntry> entries;
  entries.reserve(count);
  for (std::size_t index = 0; index < count; ++index) {
    v7::EconomyEntry entry;
    for (auto* field : {&entry.key, &entry.value}) {
      // The reader bounds the length prefix against the section, so `offset`
      // never passes its end and the width below cannot underflow.
      const auto width = read_u32(section, offset);
      if (!width) return std::nullopt;
      offset += 4;
      const auto span = static_cast<std::size_t>(*width);
      if (span > section.size() - offset) return std::nullopt;
      field->assign(section.begin() + static_cast<std::ptrdiff_t>(offset),
                    section.begin() + static_cast<std::ptrdiff_t>(offset + span));
      offset += span;
    }
    if (index > 0 && !(entries.back().key < entry.key)) return std::nullopt;
    entries.push_back(std::move(entry));
  }
  return entries;
}

}  // namespace

SnapshotParametersV7 snapshot_parameters(const v7::Ledger& ledger) {
  return SnapshotParametersV7{ledger.chain_id, ledger.supply_limit,
                              ledger.fixed_fee, ledger.verifier_key};
}

SnapshotV7EncodeResult encode_snapshot_v7(const v7::Ledger& ledger) {
  const auto root = v7::ledger_state_root(ledger);
  if (!root) return SnapshotV7Error::invalid_state;
  const auto accounts = v7::account_entries(ledger);
  const auto economy = v7::economy_entries(ledger);

  std::size_t size = kFixedSize;
  if (!add_size(size, accounts.size() * kAccountSize)) {
    return SnapshotV7Error::size_overflow;
  }
  for (const auto& entry : economy) {
    if (!add_size(size, 8) || !add_size(size, entry.key.size()) ||
        !add_size(size, entry.value.size())) {
      return SnapshotV7Error::size_overflow;
    }
  }
  v7::Bytes payload;
  if (payload.max_size() < size) return SnapshotV7Error::size_overflow;
  payload.reserve(size);

  append(payload, kMagic);
  append_u16(payload, kVersion);
  append(payload, std::span<const std::uint8_t>(ledger.chain_id));
  append_u64(payload, ledger.height);
  append_u64(payload, ledger.supply_limit);
  append_u64(payload, ledger.total_supply);
  append_u64(payload, ledger.fee_pool);
  append_u64(payload, ledger.fixed_fee);
  append(payload, std::span<const std::uint8_t>(ledger.verifier_key));
  append_u64(payload, static_cast<std::uint64_t>(accounts.size()));
  append_u64(payload, static_cast<std::uint64_t>(economy.size()));
  // The decoder reads every prefix field at a literal offset, so a field added
  // or removed above would leave those offsets reading the wrong octets while
  // the total-size check below still passed. `encode_genesis` guards its own
  // prefix the same way and for the same reason.
  if (payload.size() != kPrefixSize) return SnapshotV7Error::size_overflow;
  for (const auto& account : accounts) {
    append(payload, std::span<const std::uint8_t>(account.account_id));
    append_u64(payload, account.balance);
    append_u64(payload, account.nonce);
  }
  // `economy_entries` builds its entries in key order by construction, but the
  // root sorts before it hashes and this section is required to be ordered, so
  // the order is established here rather than assumed of the projection.
  auto ordered = economy;
  std::sort(ordered.begin(), ordered.end(),
            [](const v7::EconomyEntry& left, const v7::EconomyEntry& right) {
              return left.key < right.key;
            });
  for (const auto& entry : ordered) {
    append_length_prefixed(payload, entry.key);
    append_length_prefixed(payload, entry.value);
  }
  append(payload, std::span<const std::uint8_t>(*root));
  const auto digest = protocol::v1::hash(kDigestDomain, payload);
  append(payload, digest);
  if (payload.size() != size) return SnapshotV7Error::size_overflow;
  return EncodedSnapshotV7{std::move(payload), *root, digest};
}

SnapshotV7DecodeResult decode_snapshot_v7(
    std::span<const std::uint8_t> payload,
    const SnapshotParametersV7& expected_parameters) {
  if (payload.size() < kFixedSize ||
      !std::equal(kMagic.begin(), kMagic.end(), payload.begin())) {
    return SnapshotV7Error::malformed;
  }
  const auto version = read_u16(payload, 4);
  if (!version || *version != kVersion) {
    return SnapshotV7Error::unsupported_version;
  }

  const auto encoded_digest = read_fixed<32>(payload, payload.size() - kDigestSize);
  if (!encoded_digest) return SnapshotV7Error::malformed;
  const auto computed_digest = protocol::v1::hash(
      kDigestDomain, payload.first(payload.size() - kDigestSize));
  if (computed_digest != *encoded_digest) return SnapshotV7Error::digest_mismatch;

  const auto prefix = read_prefix(payload);
  if (!prefix) return SnapshotV7Error::malformed;
  const SnapshotParametersV7 parameters{prefix->summary.chain_id,
                                        prefix->summary.supply_limit,
                                        prefix->fixed_fee, prefix->verifier_key};
  if (parameters != expected_parameters) {
    return SnapshotV7Error::immutable_parameters_mismatch;
  }

  // The two counts are bounded by the payload before either is used as a length,
  // so a declared count larger than the bytes present is refused rather than
  // reserved for.
  const auto body = payload.size() - kFixedSize;
  if (prefix->account_count > body / kAccountSize) {
    return SnapshotV7Error::size_overflow;
  }
  // Each economy entry costs at least its two length prefixes.
  if (prefix->economy_count > body / 8) return SnapshotV7Error::size_overflow;

  const auto limit = payload.size() - kRootSize - kDigestSize;
  std::size_t offset = kPrefixSize;
  const auto section = payload.first(limit);
  const auto accounts = read_accounts(
      section, offset, static_cast<std::size_t>(prefix->account_count));
  if (!accounts) return SnapshotV7Error::malformed;
  const auto economy = read_economy(
      section, offset, static_cast<std::size_t>(prefix->economy_count));
  if (!economy) return SnapshotV7Error::malformed;
  // Every octet between the prefix and the root belongs to a section. A payload
  // with a tail nothing reads could carry two different states under one digest.
  if (offset != limit) return SnapshotV7Error::malformed;
  const auto state_root = read_fixed<32>(payload, limit);
  if (!state_root) return SnapshotV7Error::malformed;

  snapshot_v7::Rebuild rebuild;
  rebuild.ledger.chain_id = parameters.chain_id;
  rebuild.ledger.supply_limit = parameters.supply_limit;
  rebuild.ledger.fixed_fee = parameters.fixed_fee;
  rebuild.ledger.verifier_key = parameters.verifier_key;
  rebuild.ledger.height = prefix->summary.height;
  rebuild.ledger.total_supply = prefix->summary.total_supply;
  rebuild.ledger.fee_pool = prefix->summary.fee_pool_balance;
  for (const auto& account : *accounts) {
    rebuild.ledger.registry.accounts.emplace(
        account.account_id, v7::Account{account.balance, account.nonce});
  }
  for (const auto& entry : *economy) {
    if (!snapshot_v7::apply_entry(rebuild, entry)) {
      return SnapshotV7Error::invalid_state;
    }
  }
  if (!snapshot_v7::complete(rebuild)) return SnapshotV7Error::invalid_state;

  // Gate 1. The rebuilt ledger's own projection must reproduce the payload's
  // root, which is what makes the reconstruction lossless rather than plausible.
  const auto restored_root = v7::ledger_state_root(rebuild.ledger);
  if (!restored_root || *restored_root != *state_root) {
    return SnapshotV7Error::state_root_mismatch;
  }
  // Gate 2. The payload's own entries must produce the same root, which is a
  // different claim: it fails where the rebuild silently dropped an entry the
  // projection then wrote back with a default.
  const auto payload_root = v7::state_root(prefix->summary, *accounts, *economy);
  if (!payload_root || *payload_root != *state_root) {
    return SnapshotV7Error::payload_root_mismatch;
  }
  // Gate 3. A restore hands back a state some sequence of blocks could have
  // produced, or it hands back nothing.
  if (!v7::conservation_failures(rebuild.ledger).empty()) {
    return SnapshotV7Error::not_conserved;
  }
  return DecodedSnapshotV7{std::move(rebuild.ledger), *state_root, *encoded_digest};
}

}  // namespace protocol::storage
