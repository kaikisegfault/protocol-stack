#pragma once

// What the three version-nine snapshot translation units share: the bounded
// readers, the partially rebuilt ledger, and the entry points that turn one
// economy entry into ledger state.
//
// The split is by subject and it is version eight's. `snapshot_v9.cpp` owns the
// framing — the prefix, the two ordered sections, the digest, and the three
// restore gates. `snapshot_v9_entries.cpp` owns the value decoders, one per
// entry kind, plus the four kinds version nine adds.
// `snapshot_v9_assignments.cpp` owns the one variable-width record and the
// permission count summed back out of the same octets.

#include "protocol/storage/snapshot_v9.hpp"

#include "../v1/encoding.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>
#include <vector>

namespace protocol::storage::snapshot_v9 {

namespace v9 = protocol::v9;

using protocol::v1::internal::read_fixed;
using protocol::v1::internal::read_u16;
using protocol::v1::internal::read_u32;
using protocol::v1::internal::read_u64;

struct Rebuild {
  v9::Ledger ledger;
  // Every seat identifier a seat-keyed entry named, checked against the seat
  // table once the whole payload is in. It cannot be checked as each entry
  // arrives without depending on kind 1 sorting first, which is true and is not
  // a fact a value decoder should rest on.
  //
  // **It is `referenced_seats` and not version eight's `uptime_seats`**, because
  // version nine gives it two more sources: kinds 21 and 22 name a seat for the
  // same reason kinds 18 and 19 do, and all four sort after kind 1. A name that
  // said "uptime" would have been wrong the moment the monthly figure used it.
  std::vector<std::uint32_t> referenced_seats;
  std::array<bool, v9::kChannelCount> channel_seen{};
  bool recovery_pool_seen = false;
  bool verifier_key_seen = false;
  bool unreferred_pool_seen = false;
  bool verified_user_counter_seen = false;
  // Version nine's addition to the fixed set. Genesis writes the cursor and no
  // transition removes it, so a payload without one describes a chain that never
  // opened. Window zero's month entry is genesis's too but is **not** fixed —
  // every assignment deletes one — so it has no flag here and its retention is
  // the kernel invariant's business.
  bool settlement_cursor_seen = false;
};

// Apply one economy entry. `false` for an entry no conforming transition could
// have written, which includes every width the contract fixes and every field
// combination the conservation invariants forbid.
//
// The caller has already established that keys strictly increase, so no kind
// needs its own duplicate check.
[[nodiscard]] bool apply_entry(Rebuild& rebuild, const v9::EconomyEntry& entry);

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
// records in `snapshot_v9_assignments.cpp`.
[[nodiscard]] bool apply_cycle_assignment(Rebuild& rebuild,
                                          std::span<const std::uint8_t> key,
                                          std::span<const std::uint8_t> value);
// `nullopt` when a recorded assignment will not decode or the sum leaves `u64`.
std::optional<std::uint64_t> derive_assigned_permissions(const v9::Ledger& ledger);

// Every fixed entry present, every uptime entry naming a seat the chain sold,
// and `assigned_permissions` re-derived from the assignment records rather than
// read from the payload.
[[nodiscard]] bool complete(Rebuild& rebuild);

}  // namespace protocol::storage::snapshot_v9
