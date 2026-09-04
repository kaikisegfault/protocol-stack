// The uptime carrier's codec: two state entries and challenge selection.
//
// **Everything version eight adds to the economy state and its derivations is
// in this one translation unit**, so the difference between version seven's
// codec and version eight's is one file rather than a diff spread across nine.
// The rest of `src/v8/` is version seven's codec with three identifiers
// rebound, which is what makes the migration auditable while both kernels are
// compiled.
//
// What is *not* here is what the entries mean to a block: the issue step, the
// expiry step, the schedule the prologue derives, and the two transitions that
// write these values. Those read state and are the ledger's.

#include "economy_internal.hpp"

#include "protocol/v1/crypto.hpp"

#include <bit>

namespace protocol::v8 {
namespace {

namespace i = protocol::v8::internal;

// A bitmap's upper eight bits are pad and a decoder that finds one set refuses
// the value. This is the rule ADR 0056 records version seven as *not* stating
// for the cycle assignment's bitmap; version eight states it outright for the
// window record, so the kernel enforces it here while leaving the assignment
// record's older laxity exactly as version seven accepted it.
bool bitmap_is_canonical(std::uint32_t value) {
  return (value & ~kSlotBitmapMask) == 0U;
}

// A dispute may only void a slot the seat was credited for, so `disputed` is
// always a subset of `credited`. Checking it in the codec is what makes the
// containment argument an argument about the encoded state rather than about
// the transition that happened to write it.
bool record_is_canonical(const SeatWindowRecord& record) {
  if (!bitmap_is_canonical(record.credited)) return false;
  if (!bitmap_is_canonical(record.disputed)) return false;
  return (record.disputed & ~record.credited) == 0U;
}

}  // namespace

Bytes open_challenge_key(std::uint64_t challenge_height, std::uint32_t seat_id) {
  auto key = i::key_prefix(Entry::open_challenge);
  i::append_u64(key, challenge_height);
  i::append_u32(key, seat_id);
  return key;
}

Bytes seat_window_key(std::uint64_t cycle_window, std::uint32_t seat_id) {
  auto key = i::key_prefix(Entry::seat_window);
  i::append_u64(key, cycle_window);
  i::append_u32(key, seat_id);
  return key;
}

std::optional<Bytes> open_challenge_value(std::uint8_t state) {
  if (state != kChallengeOutstanding && state != kChallengeAnswered) {
    return std::nullopt;
  }
  return Bytes{state};
}

std::optional<std::uint8_t> decode_open_challenge_value(
    std::span<const std::uint8_t> raw) {
  const auto width = entry_value_bytes(static_cast<std::uint8_t>(Entry::open_challenge));
  if (!width || raw.size() != *width) return std::nullopt;
  if (raw[0] != kChallengeOutstanding && raw[0] != kChallengeAnswered) {
    return std::nullopt;
  }
  return raw[0];
}

// A slot bit begins set and evidence only ever removes credit, so a machine
// that answers every challenge writes no record at all and an absent record is
// a fully credited window rather than an empty one. The storage the pipeline
// adds is therefore proportional to failure rather than to population.
SeatWindowRecord full_seat_window() {
  return SeatWindowRecord{kSlotBitmapMask, 0};
}

std::optional<Bytes> seat_window_value(const SeatWindowRecord& record) {
  if (!record_is_canonical(record)) return std::nullopt;
  Bytes value;
  value.reserve(8);
  i::append_u32(value, record.credited);
  i::append_u32(value, record.disputed);
  return value;
}

std::optional<SeatWindowRecord> decode_seat_window_value(
    std::span<const std::uint8_t> raw) {
  const auto width = entry_value_bytes(static_cast<std::uint8_t>(Entry::seat_window));
  if (!width || raw.size() != *width) return std::nullopt;
  const auto credited = i::read_u32(raw, 0);
  const auto disputed = i::read_u32(raw, 4);
  if (!credited || !disputed) return std::nullopt;
  const SeatWindowRecord record{*credited, *disputed};
  if (!record_is_canonical(record)) return std::nullopt;
  return record;
}

// `popcount(credited & ~disputed)`. A dispute sets a bit in `disputed` and
// never clears one in `credited`, so the record keeps what the seat's own
// evidence said and the final credit is derived from both halves.
std::uint32_t credited_slots(const SeatWindowRecord& record) {
  return static_cast<std::uint32_t>(
      std::popcount(record.credited & ~record.disputed & kSlotBitmapMask));
}

std::uint64_t uptime_seconds(const SeatWindowRecord& record) {
  return credited_slots(record) * kSlotSeconds;
}

std::uint64_t slot_last_height(std::uint64_t height) {
  const auto window_start = (height / kCycleBlocks) * kCycleBlocks;
  return window_start + (slot_of(height) + 1) * kSlotBlocks - 1;
}

// The final `kResponseDeadlineBlocks` heights of every slot issue nothing, so
// an open challenge never crosses a slot boundary and the expiry step at
// `challenge_height + kResponseDeadlineBlocks` is always inside the same slot.
bool is_challengeable_height(std::uint64_t height) {
  return height <= slot_last_height(height) - kResponseDeadlineBlocks;
}

// `beacon:32 || u32_be(seat_id) || u64_be(height)`.
//
// **The height is bound even though the beacon already varies with it**, so a
// selection value is unique to one height and cannot be presented as belonging
// to another.
//
// This is deliberately not `uptime-measurement-v1`'s preimage. That model
// digests an RFC 8785 JSON object, and a consensus kernel that canonicalised
// JSON to decide who is audited would put a parser on the most adversarial path
// the pipeline has. The two therefore select different heights for the same
// beacon, and what they share is the rule rather than the byte layout.
std::optional<Bytes> selection_preimage(std::span<const std::uint8_t> beacon,
                                        std::uint32_t seat_id,
                                        std::uint64_t height) {
  if (beacon.size() != 32) return std::nullopt;
  Bytes preimage;
  preimage.reserve(kSelectionPreimageBytes);
  i::append(preimage, beacon);
  i::append_u32(preimage, seat_id);
  i::append_u64(preimage, height);
  if (preimage.size() != kSelectionPreimageBytes) return std::nullopt;
  return preimage;
}

// The digest truncated to its first eight octets, read big-endian.
//
// Truncating biases selection by less than one part in 2^54: `2^64 mod 1200` is
// 1,216, so 1,216 of the 1,200 residues occur once more often than the rest
// over the full range. Reducing the whole 256-bit digest instead would require
// big-integer arithmetic on a consensus path to remove a bias no observer could
// measure.
std::optional<std::uint64_t> selection_value(std::span<const std::uint8_t> beacon,
                                             std::uint32_t seat_id,
                                             std::uint64_t height) {
  const auto preimage = selection_preimage(beacon, seat_id, height);
  if (!preimage) return std::nullopt;
  const auto digest = protocol::v1::hash(kChallengeLabel, *preimage);
  std::uint64_t value = 0;
  for (std::size_t index = 0; index < kSelectionDigestBytes; ++index) {
    value = (value << 8U) | digest[index];
  }
  return value;
}

// Every in-scope seat is selected or not independently at every height, which
// is what makes a challenge unpredictable until one block before it must be
// answered. A formulation that selected a residue class in one digest would be
// cheaper and would correlate the fate of every seat in the class.
std::optional<bool> is_selected(std::span<const std::uint8_t> beacon,
                                std::uint32_t seat_id, std::uint64_t height) {
  const auto value = selection_value(beacon, seat_id, height);
  if (!value) return std::nullopt;
  if (!is_challengeable_height(height)) return false;
  return *value % kChallengePeriodBlocks == 0;
}

}  // namespace protocol::v8
