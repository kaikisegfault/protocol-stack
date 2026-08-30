// The cycle assignment record: the one economy value whose width follows from
// its own contents, and the permission count derived from the same records.
//
// They share a file because they read the same bytes for the same reason. The
// record is the only state entry a snapshot stores verbatim rather than
// decoding into fields, so the round trip is exact and the mint reads the same
// octets after a restart that it read before one — and `assigned_permissions`,
// which no state entry holds, is summed back out of those octets rather than
// trusted from the payload.

#include "snapshot_v7_internal.hpp"

#include <bit>

namespace protocol::storage::snapshot_v7 {
namespace {

// Bits set at or above `bitmap_bits` are pad. `bitmap()` never sets one, so a
// record carrying one is not a record any chain wrote — and it would be read as
// an accrued seat by the mint's own walk, because `bit_is_set` bounds itself by
// the packed width rather than by the recorded bit count.
bool padding_is_clear(std::span<const std::uint8_t> packed,
                      std::uint32_t bitmap_bits) {
  const auto whole = static_cast<std::size_t>(bitmap_bits) / 8;
  if (whole >= packed.size()) return true;
  const auto used = static_cast<unsigned>(bitmap_bits % 8);
  const auto mask = static_cast<std::uint8_t>(0xFFU >> used);
  if ((packed[whole] & mask) != 0) return false;
  for (std::size_t index = whole + 1; index < packed.size(); ++index) {
    if (packed[index] != 0) return false;
  }
  return true;
}

std::uint32_t population(std::span<const std::uint8_t> packed) {
  std::uint32_t count = 0;
  for (const auto octet : packed) {
    count += static_cast<std::uint32_t>(std::popcount(octet));
  }
  return count;
}

}  // namespace

bool apply_cycle_assignment(Rebuild& rebuild, std::span<const std::uint8_t> key,
                            std::span<const std::uint8_t> value) {
  const auto window = read_u64(key, 1);
  if (!window) return false;
  const auto record = v7::decode_cycle_assignment_value(value);
  if (!record) return false;
  if (record->bitmap_bits > v7::kFounderSeatCapacity ||
      record->in_scope_count > v7::kFounderSeatCapacity) {
    return false;
  }
  if (!padding_is_clear(record->accrued_bitmap, record->bitmap_bits) ||
      !padding_is_clear(record->winner_bitmap, record->bitmap_bits)) {
    return false;
  }
  // The record commits to the winner count and to the bitmap it was built from,
  // so the two are one fact written twice.
  if (population(record->winner_bitmap) != record->winner_count) return false;
  // The contributing set is the accrued seats plus the reallocated ones, and it
  // is drawn from the in-scope set.
  const auto accrued = population(record->accrued_bitmap);
  if (accrued > record->in_scope_count) return false;
  if (record->reallocated_count > record->in_scope_count - accrued) return false;
  // The share is a function of the winner count alone, which makes it derivable
  // rather than merely bounded.
  const auto split = v7::split_permission(record->winner_count);
  if (record->share_per_winner_atomic != split.share[v7::kFounderOperatorChannel]) {
    return false;
  }
  rebuild.ledger.assignments.emplace(*window, v7::Bytes(value.begin(), value.end()));
  return true;
}

// `assigned_permissions` is re-derived, never read. It is not a state entry, so
// nothing in the root commits to it; a payload that carried it could disagree
// with the records it sits beside, and the channel identity is stated over
// exactly this figure. An adversary who edits a state can recompute its root and
// reseal its digest, so the conservation gate is the only one left to refuse
// them — and that gate is only as good as the figure it is stated over.
//
// A cycle's contributing count is its accrued seats plus its reallocated ones,
// and the record commits to both.
std::optional<std::uint64_t> derive_assigned_permissions(const v7::Ledger& ledger) {
  std::uint64_t assigned = 0;
  for (const auto& [window, value] : ledger.assignments) {
    (void)window;
    const auto record = v7::decode_cycle_assignment_value(value);
    if (!record) return std::nullopt;
    std::uint32_t contributing = record->reallocated_count;
    for (const auto octet : record->accrued_bitmap) {
      contributing += static_cast<std::uint32_t>(std::popcount(octet));
    }
    if (contributing > v7::kMaxU64 - assigned) return std::nullopt;
    assigned += contributing;
  }
  return assigned;
}

}  // namespace protocol::storage::snapshot_v7
