#pragma once

// What the two version-seven snapshot translation units share: the bounded
// readers, the partially rebuilt ledger, and the two entry points that turn one
// economy entry into ledger state.
//
// The split is by subject. `snapshot_v7.cpp` owns the framing — the prefix, the
// two ordered sections, the digest, and the three restore gates.
// `snapshot_v7_entries.cpp` owns the value decoders, one per entry kind, each
// the exact inverse of the encoder version six accepted and version seven
// carries unchanged.

#include "protocol/storage/snapshot_v7.hpp"

#include "../v1/encoding.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <span>

namespace protocol::storage::snapshot_v7 {

namespace v7 = protocol::v7;

using protocol::v1::internal::read_fixed;
using protocol::v1::internal::read_u16;
using protocol::v1::internal::read_u32;
using protocol::v1::internal::read_u64;

// The fourteen entries genesis writes and no transition ever removes: the ten
// channels, the recovery pool, the verifier key, the unreferred pool, and the
// verified-user counter. A payload missing one describes a chain that never
// opened, and the roots would catch it a step later; naming it here makes the
// failure a parse error with a subject rather than a digest that disagrees.
inline constexpr std::size_t kFixedEntryCount = v7::kChannelCount + 4;

struct Rebuild {
  v7::Ledger ledger;
  std::array<bool, v7::kChannelCount> channel_seen{};
  bool recovery_pool_seen = false;
  bool verifier_key_seen = false;
  bool unreferred_pool_seen = false;
  bool verified_user_counter_seen = false;
};

// Apply one economy entry. `false` for an entry no conforming transition could
// have written, which includes every width the contract fixes and every field
// combination the conservation invariants forbid.
//
// The caller has already established that keys strictly increase, so no kind
// needs its own duplicate check.
[[nodiscard]] bool apply_entry(Rebuild& rebuild, const v7::EconomyEntry& entry);

// Every fixed entry present, and `assigned_permissions` re-derived from the
// assignment records rather than read from the payload.
[[nodiscard]] bool complete(Rebuild& rebuild);

}  // namespace protocol::storage::snapshot_v7
