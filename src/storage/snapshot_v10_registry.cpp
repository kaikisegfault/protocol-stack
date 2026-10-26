// Everything version ten adds to the snapshot: the four registry entries, and
// the one rule a restore needs because invariant 7 is about two heights.
//
// **The four are decoded into typed fields**, as version nine's four are,
// because version ten holds them as typed maps and nothing reads their raw key
// space. Kinds 10 and 23 and the registry step read `machine_keys`,
// `machine_key_owners`, `launch_retired_at`, and `founder_registrations`
// directly, and the projection is where they become entries. So this unit is
// the projection's inverse for them, and the round trip compares each map whole.
//
// **Every value rule is the kernel's**, called rather than restated (ADR 0080,
// decision 4). `decode_machine_key_value` refuses a key written at height 0,
// `decode_launch_retirement_value` a retirement at height 0, and
// `decode_founder_registrations_value` a count of 0 or one above the limit,
// each by asking its encoder. So the snapshot, the root's shape check, and
// invariant 6 cannot disagree about any of them.
//
// **Every cross-entry rule but one is gate 3's.** Invariants 1 to 6 and 8 hold
// each machine key to an activated seat, the owner entries to the exact inverse,
// no key to two seats, every mark and every founder count to the head's window,
// and every founder count to someone who owns a machine. `conservation_failures`
// states each over the whole state, so a second statement here would be a second
// rule firing on the same payloads. That is why no registry kind adds to
// `referenced_seats`. The one rule this unit states itself is the retirement's,
// below, because the invariant that protects the retirement is the one gate 3
// cannot run.

#include "snapshot_v10_internal.hpp"

namespace protocol::storage::snapshot_v10 {

// Kind 24. The seat is the key's and is not checked here: invariant 1 holds it
// to a purchased and activated seat at gate 3.
bool apply_machine_key(Rebuild& rebuild, std::span<const std::uint8_t> key,
                       std::span<const std::uint8_t> value) {
  const auto seat_id = read_u32(key, 1);
  if (!seat_id) return false;
  const auto entry = v10::decode_machine_key_value(value);
  if (!entry) return false;
  rebuild.ledger.machine_keys.emplace(*seat_id, *entry);
  return true;
}

// Kind 25, present or absent. Its key is one octet, so the strict key order the
// section is read in already admits at most one.
bool apply_launch_retirement(Rebuild& rebuild,
                             std::span<const std::uint8_t> value) {
  const auto height = v10::decode_launch_retirement_value(value);
  if (!height) return false;
  rebuild.ledger.launch_retired_at = *height;
  return true;
}

// Kind 26. Its value is any seat identifier the width admits, and invariant 2
// requires it to name the seat whose entry holds this key.
bool apply_machine_key_owner(Rebuild& rebuild, std::span<const std::uint8_t> key,
                             std::span<const std::uint8_t> value) {
  const auto machine_public_key = read_fixed<32>(key, 1);
  const auto seat_id = v10::decode_machine_key_owner_value(value);
  if (!machine_public_key || !seat_id) return false;
  rebuild.ledger.machine_key_owners.emplace(*machine_public_key, *seat_id);
  return true;
}

// Kind 27, keyed by the founder's identity. Invariants 5 and 8 hold the window
// to the head's and the identity to someone who owns a machine, at gate 3.
bool apply_founder_registrations(Rebuild& rebuild,
                                 std::span<const std::uint8_t> key,
                                 std::span<const std::uint8_t> value) {
  const auto founder = read_fixed<32>(key, 1);
  const auto count = v10::decode_founder_registrations_value(value);
  if (!founder || !count) return false;
  rebuild.ledger.founder_registrations.emplace(*founder, *count);
  return true;
}

// **Invariant 7 is the registry's one invariant a restore cannot run.** It says
// a retirement, once present, is present at every later height with the same
// value. That compares two heights, and a snapshot holds one. So a resealed
// payload that dropped the entry would pass all three gates, and the node that
// restored it would let the launch key sign again: ADR 0100's "for good",
// undone by a file.
//
// One height can still say three things about the retirement, and each follows
// from how the registry step writes it.
//
// - **It is present when the head's own count reached the cutoff.** Between
//   assignments no transition makes a machine active, because a new key starts
//   unmarked and a replacement keeps its seat's mark. So the machines active at
//   the head are exactly the ones the latest registry step counted. If there
//   were 100, that step wrote the retirement, and nothing removes it.
// - **It is present only when 100 machines were ever marked.** The step writes
//   it when at least 100 keys carry the due window's mark, and no key is ever
//   removed and no mark ever returns to 0. So at every later height at least
//   100 keys carry a nonzero mark.
// - **Its height is an assignment at or below the head.** Only a registry step
//   writes it, and the step runs at the first height of window `w + 2`, the
//   height that assigns window `w`. That `w` is at least 1, because a mark of 0
//   is never counted (ADR 0103), so no assignment of window 0 can retire.
//
// **This is the one guard a seeded launch has.** A node restoring alone from a
// tampered payload holds a root its peers do not, and stops at the next block.
// But every replica of a seeded network restores the same payload and takes its
// root as the engine's `app_hash` (ADR 0097), so no peer disagrees, and the
// launch key would sign on the whole network.
//
// **What one height cannot show is a retirement dropped after the count fell
// below the cutoff**, because a chain that never retired could be in the same
// state. That stays a two-height fact. Only the root exposes it, compared with
// the root of the chain the payload claims to come from, which is what a seeded
// launch must obtain from that chain rather than from the payload.
bool retirement_is_reachable(const v10::Ledger& ledger) {
  std::uint64_t active = 0;
  std::uint64_t marked = 0;
  for (const auto& [seat_id, entry] : ledger.machine_keys) {
    // The kernel's own reading of an active machine, so the count here is the
    // registry step's rather than a second statement of it.
    if (v10::machine_active(ledger, seat_id)) active += 1;
    if (entry.last_met_window != 0) marked += 1;
  }
  if (!ledger.launch_retired_at) {
    return active < v10::kLaunchRetirementActiveMachines;
  }
  const auto retired = *ledger.launch_retired_at;
  // The window the retiring step assigned, read through the kernel's own
  // derivation, which is defined at every height and is the due window only at
  // the first height of a window.
  const auto due = v10::last_assigned_window(retired);
  if (retired % v10::kCycleBlocks != 0 || !due || *due == 0) return false;
  if (retired > ledger.height) return false;
  return marked >= v10::kLaunchRetirementActiveMachines;
}

}  // namespace protocol::storage::snapshot_v10
