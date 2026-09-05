#pragma once

// What the three version-eight snapshot translation units share: the bounded
// readers, the partially rebuilt ledger, and the entry points that turn one
// economy entry into ledger state.
//
// The split is by subject. `snapshot_v8.cpp` owns the framing — the prefix, the
// two ordered sections, the digest, and the three restore gates.
// `snapshot_v8_entries.cpp` owns the value decoders, one per entry kind, each
// the exact inverse of the encoder version six accepted and versions seven and
// eight carry unchanged, plus the two kinds version eight adds.
// `snapshot_v8_assignments.cpp` owns the one variable-width record and the
// permission count summed back out of the same octets.

#include "protocol/storage/snapshot_v8.hpp"

#include "../v1/encoding.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>
#include <vector>

namespace protocol::storage::snapshot_v8 {

namespace v8 = protocol::v8;

using protocol::v1::internal::read_fixed;
using protocol::v1::internal::read_u16;
using protocol::v1::internal::read_u32;
using protocol::v1::internal::read_u64;

// The fourteen entries genesis writes and no transition ever removes: the ten
// channels, the recovery pool, the verifier key, the unreferred pool, and the
// verified-user counter. A payload missing one describes a chain that never
// opened, and the roots would catch it a step later; naming it here makes the
// failure a parse error with a subject rather than a digest that disagrees.
inline constexpr std::size_t kFixedEntryCount = v8::kChannelCount + 4;

struct Rebuild {
  v8::Ledger ledger;
  // Every seat identifier an uptime entry named, checked against the seat table
  // once the whole payload is in. It cannot be checked as each entry arrives
  // without depending on kind 1 sorting before kinds 18 and 19, which is true
  // and is not a fact a value decoder should rest on.
  std::vector<std::uint32_t> uptime_seats;
  std::array<bool, v8::kChannelCount> channel_seen{};
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
[[nodiscard]] bool apply_entry(Rebuild& rebuild, const v8::EconomyEntry& entry);

// The uptime carrier's two entry kinds, stored raw for the reason
// `Ledger::uptime` holds them raw: this projection is a copy rather than a
// re-encoding, so the two version-eight transitions remain the implementation of
// that key space rather than a sibling of one.
//
// `false` for a value no transition could have written, which includes the two
// rules version eight states outright — a pad bit set, and a dispute of an
// uncredited slot — and the absent-record reading, which no writer produces.
[[nodiscard]] bool apply_open_challenge(Rebuild& rebuild,
                                        std::span<const std::uint8_t> key,
                                        std::span<const std::uint8_t> value);
[[nodiscard]] bool apply_seat_window(Rebuild& rebuild,
                                     std::span<const std::uint8_t> key,
                                     std::span<const std::uint8_t> value);

// The one variable-width value, defined beside the figure derived from the same
// records in `snapshot_v8_assignments.cpp`.
[[nodiscard]] bool apply_cycle_assignment(Rebuild& rebuild,
                                          std::span<const std::uint8_t> key,
                                          std::span<const std::uint8_t> value);
// `nullopt` when a recorded assignment will not decode or the sum leaves `u64`.
std::optional<std::uint64_t> derive_assigned_permissions(const v8::Ledger& ledger);

// Every fixed entry present, every uptime entry naming a seat the chain sold,
// and `assigned_permissions` re-derived from the assignment records rather than
// read from the payload.
[[nodiscard]] bool complete(Rebuild& rebuild);

}  // namespace protocol::storage::snapshot_v8
