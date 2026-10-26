#pragma once

// What the four version-ten snapshot translation units share: the bounded
// readers, the partially rebuilt ledger, and the entry points that turn one
// economy entry into ledger state.
//
// The split is by subject and it is version nine's, with one unit added.
// `snapshot_v10.cpp` owns the framing — the prefix, the two ordered sections,
// the digest, and the three restore gates. `snapshot_v10_entries.cpp` owns the
// value decoders version nine had, one per entry kind, and the dispatch every
// kind arrives through. `snapshot_v10_assignments.cpp` owns the one
// variable-width record and the permission count summed back out of the same
// octets. **`snapshot_v10_registry.cpp` owns everything version ten adds**: the
// four registry entries and what one height can show about the retirement. It
// is the kernel's own split, where `economy_registry.cpp` holds the whole of
// what version ten adds to the codec, so a reader can audit the addition
// without reading the port.

#include "protocol/storage/snapshot_v10.hpp"

#include "../v1/encoding.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>
#include <vector>

namespace protocol::storage::snapshot_v10 {

namespace v10 = protocol::v10;

using protocol::v1::internal::read_fixed;
using protocol::v1::internal::read_u16;
using protocol::v1::internal::read_u32;
using protocol::v1::internal::read_u64;

struct Rebuild {
  v10::Ledger ledger;
  // Every seat identifier a seat-keyed entry named, checked against the seat
  // table once the whole payload is in. It cannot be checked as each entry
  // arrives without depending on kind 1 sorting first, which is true and is not
  // a fact a value decoder should rest on.
  //
  // **Version ten's machine keys do not add to it.** Invariant 1 holds every
  // machine key to a purchased and activated seat at gate 3, so a second rule
  // here would fire on the same payloads, and a rule that never fires alone is
  // one no test can isolate.
  std::vector<std::uint32_t> referenced_seats;
  std::array<bool, v10::kChannelCount> channel_seen{};
  bool recovery_pool_seen = false;
  // Entry kind 8, which keeps the name version six gave it and holds the launch
  // key, the same key in a narrower role.
  bool launch_key_seen = false;
  bool unreferred_pool_seen = false;
  bool verified_user_counter_seen = false;
  // Version nine's addition to the fixed set. Genesis writes the cursor and no
  // transition removes it, so a payload without one describes a chain that never
  // opened. Window zero's month entry is genesis's too but is **not** fixed —
  // every assignment deletes one — so it has no flag here and its retention is
  // the kernel invariant's business.
  //
  // **Version ten adds nothing to the fixed set.** Genesis writes none of the
  // four registry entries, and the retirement is present or absent by design.
  bool settlement_cursor_seen = false;
};

// Apply one economy entry. `false` for an entry no conforming transition could
// have written, which includes every width the contract fixes and every field
// combination the conservation invariants forbid.
//
// The caller has already established that keys strictly increase, so no kind
// needs its own duplicate check.
[[nodiscard]] bool apply_entry(Rebuild& rebuild, const v10::EconomyEntry& entry);

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
// records in `snapshot_v10_assignments.cpp`.
[[nodiscard]] bool apply_cycle_assignment(Rebuild& rebuild,
                                          std::span<const std::uint8_t> key,
                                          std::span<const std::uint8_t> value);
// `nullopt` when a recorded assignment will not decode or the sum leaves `u64`.
std::optional<std::uint64_t> derive_assigned_permissions(const v10::Ledger& ledger);

// The four kinds version ten adds, each through the kernel's own value decoder,
// in `snapshot_v10_registry.cpp`.
[[nodiscard]] bool apply_machine_key(Rebuild& rebuild,
                                     std::span<const std::uint8_t> key,
                                     std::span<const std::uint8_t> value);
[[nodiscard]] bool apply_launch_retirement(Rebuild& rebuild,
                                           std::span<const std::uint8_t> value);
[[nodiscard]] bool apply_machine_key_owner(Rebuild& rebuild,
                                           std::span<const std::uint8_t> key,
                                           std::span<const std::uint8_t> value);
[[nodiscard]] bool apply_founder_registrations(Rebuild& rebuild,
                                               std::span<const std::uint8_t> key,
                                               std::span<const std::uint8_t> value);

// What one height can show about the launch key's retirement, which invariant
// 7 states across two: a retirement is present whenever the head's own count
// says the cutoff was reached, present only when enough machines were ever
// marked to reach it, and written at an assignment the head has reached.
// `false` for a state that breaks any of the three.
[[nodiscard]] bool retirement_is_reachable(const v10::Ledger& ledger);

// Every fixed entry present, every uptime entry naming a seat the chain sold,
// the retirement one height can account for, and `assigned_permissions`
// re-derived from the assignment records rather than read from the payload.
[[nodiscard]] bool complete(Rebuild& rebuild);

}  // namespace protocol::storage::snapshot_v10
