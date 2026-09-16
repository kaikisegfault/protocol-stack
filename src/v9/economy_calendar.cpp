// The calendar, the monthly settlement's four state entries, and the block
// header.
//
// **Everything version nine adds to the codec is in this one translation
// unit**, so the difference between version eight's codec and version nine's is
// a file rather than a diff spread across eleven. The other eleven sources are
// version eight's codec with three identifiers rebound and the enumerated edits
// its own changes force — a widened pool value, a genesis field, a kind in two
// tables, a timestamp in the root — which is what makes the port auditable while
// both kernels are compiled. It is the shape `economy_uptime.cpp` established
// for version eight.
//
// What is *not* here is what the entries mean to a block: which month closes,
// who competes, what each winner receives, and the six-step prologue that runs
// the settlement. Those read state and are the ledger's.
//
// **Nothing here reads a clock.** Every derivation is a pure function of a
// millisecond count that a block already carries by the time it is asked about,
// which is `calendar-v1`'s central rule and the whole reason the field exists.
// The one function about civil time — C5 — takes the reading as a parameter and
// is never reachable from execution.

#include "economy_internal.hpp"

#include "protocol/v1/crypto.hpp"

#include <array>
#include <limits>
#include <string>

namespace protocol::v9 {
namespace {

namespace i = protocol::v9::internal;

constexpr std::array<std::uint8_t, 4> kBlockMagic{'P', 'S', 'B', 'L'};

// Days in the 400-year Gregorian cycle, and the offset that moves the era's
// internal 0000-03-01 origin to 1970-01-01.
constexpr std::int64_t kDaysPerEra = 146'097;
constexpr std::int64_t kDaysFromEraOriginToEpoch = 719'468;

// The proleptic Gregorian day index of a date, counted from 1970-01-01, and its
// exact inverse. This is the standard closed-form pair: no table, no loop, and
// no floating point.
//
// **The March-based shifted year is what removes the leap-year case.** February
// moves to the end of the year, so its variable length never falls in the middle
// of the day-of-year formula and the formula needs no branch for it at all.
struct CivilDate {
  std::int64_t year = 0;
  std::uint32_t month = 0;
  std::uint32_t day = 0;
};

std::int64_t days_from_civil(std::int64_t year, std::uint32_t month,
                             std::uint32_t day) {
  const std::int64_t shifted_year = year - (month <= 2 ? 1 : 0);
  const std::int64_t era =
      (shifted_year >= 0 ? shifted_year : shifted_year - 399) / 400;
  const std::int64_t year_of_era = shifted_year - era * 400;
  const std::int64_t shifted_month =
      static_cast<std::int64_t>(month) + (month > 2 ? -3 : 9);
  const std::int64_t day_of_year =
      (153 * shifted_month + 2) / 5 + static_cast<std::int64_t>(day) - 1;
  const std::int64_t day_of_era = year_of_era * 365 + year_of_era / 4 -
                                 year_of_era / 100 + day_of_year;
  return era * kDaysPerEra + day_of_era - kDaysFromEraOriginToEpoch;
}

CivilDate civil_from_days(std::int64_t day_index) {
  const std::int64_t shifted = day_index + kDaysFromEraOriginToEpoch;
  const std::int64_t era = (shifted >= 0 ? shifted : shifted - kDaysPerEra + 1) /
                           kDaysPerEra;
  const std::int64_t day_of_era = shifted - era * kDaysPerEra;
  const std::int64_t year_of_era =
      (day_of_era - day_of_era / 1'460 + day_of_era / 36'524 -
       day_of_era / 146'096) /
      365;
  const std::int64_t year = year_of_era + era * 400;
  const std::int64_t day_of_year =
      day_of_era - (365 * year_of_era + year_of_era / 4 - year_of_era / 100);
  const std::int64_t shifted_month = (5 * day_of_year + 2) / 153;
  const std::int64_t day = day_of_year - (153 * shifted_month + 2) / 5 + 1;
  const std::int64_t month = shifted_month + (shifted_month < 10 ? 3 : -9);

  CivilDate date;
  date.year = year + (month <= 2 ? 1 : 0);
  date.month = static_cast<std::uint32_t>(month);
  date.day = static_cast<std::uint32_t>(day);
  return date;
}

bool month_in_range(std::uint32_t index) { return index <= kMaxMonthIndex; }

// A key or value carrying a month index above the accepted range is refused
// wherever one appears, which is what makes every derivation that reads one
// total: such an index has no first millisecond and no last, so admitting one
// would hand an undefined case to arithmetic downstream.
std::optional<Bytes> month_value(std::uint32_t index) {
  if (!month_in_range(index)) return std::nullopt;
  Bytes value;
  i::append_u32(value, index);
  return value;
}

std::optional<std::uint32_t> decode_month_value(
    std::span<const std::uint8_t> raw, Entry entry) {
  const auto width = entry_value_bytes(static_cast<std::uint8_t>(entry));
  if (!width || raw.size() != *width) return std::nullopt;
  const auto index = i::read_u32(raw, 0);
  if (!index || !month_in_range(*index)) return std::nullopt;
  return *index;
}

}  // namespace

// --- the timestamp rules ----------------------------------------------------

bool timestamp_in_range(std::uint64_t timestamp) {
  return timestamp >= kMinTimestampMillis && timestamp <= kMaxTimestampMillis;
}

std::string_view timestamp_condition_name(TimestampCondition condition) {
  switch (condition) {
    case TimestampCondition::accepted:
      return "ACCEPTED";
    case TimestampCondition::height_not_next:
      return "HEIGHT_NOT_NEXT";
    case TimestampCondition::timestamp_range:
      return "TIMESTAMP_RANGE";
    case TimestampCondition::timestamp_not_monotonic:
      return "TIMESTAMP_NOT_MONOTONIC";
    case TimestampCondition::timestamp_ahead_of_tolerance:
      return "TIMESTAMP_AHEAD_OF_TOLERANCE";
    case TimestampCondition::timestamp_behind_tolerance:
      return "TIMESTAMP_BEHIND_TOLERANCE";
  }
  return {};
}

// **C2 permits equality.** Two blocks may carry the same millisecond — a chain
// committing faster than its clock's resolution has not gone backwards — so the
// comparison is `<` rather than `<=`, and a vector records the accepted equal
// pair.
TimestampCondition replay_timestamp(const Head& head, std::uint64_t height,
                                    std::uint64_t timestamp) {
  if (head.height == std::numeric_limits<std::uint64_t>::max() ||
      height != head.height + 1) {
    return TimestampCondition::height_not_next;
  }
  if (!timestamp_in_range(timestamp)) return TimestampCondition::timestamp_range;
  if (timestamp < head.timestamp) {
    return TimestampCondition::timestamp_not_monotonic;
  }
  return TimestampCondition::accepted;
}

// The one function in this kernel that is handed a clock reading, and it is
// handed one rather than taking one: nothing here can read a clock, and
// `replay_timestamp` above has no parameter that could make it check this.
//
// **Both comparisons are guarded subtractions rather than
// `timestamp > clock + tolerance`.** The sum is the shape that wraps when a
// reading sits near the `u64` bound, and a wrapped comparison accepts exactly
// the values the rule exists to refuse.
TimestampCondition accept_timestamp(const Head& head, std::uint64_t height,
                                    std::uint64_t timestamp,
                                    std::uint64_t observed_clock_millis) {
  const auto deterministic = replay_timestamp(head, height, timestamp);
  if (deterministic != TimestampCondition::accepted) return deterministic;
  if (timestamp > observed_clock_millis) {
    if (timestamp - observed_clock_millis > kTimestampToleranceMillis) {
      return TimestampCondition::timestamp_ahead_of_tolerance;
    }
  } else if (observed_clock_millis - timestamp > kTimestampToleranceMillis) {
    return TimestampCondition::timestamp_behind_tolerance;
  }
  return TimestampCondition::accepted;
}

// --- the calendar -----------------------------------------------------------

std::optional<std::uint32_t> month_index(std::uint64_t timestamp) {
  if (!timestamp_in_range(timestamp)) return std::nullopt;
  // Exact because `kMillisPerDay` is a constant rather than a measurement: no
  // leap second is represented, so every day is the same length.
  const auto day = static_cast<std::int64_t>(timestamp / kMillisPerDay);
  const CivilDate date = civil_from_days(day);
  const auto index =
      (date.year - static_cast<std::int64_t>(kMinCalendarYear)) *
          static_cast<std::int64_t>(kMonthsPerYear) +
      static_cast<std::int64_t>(date.month) - 1;
  if (index < 0 || index > static_cast<std::int64_t>(kMaxMonthIndex)) {
    return std::nullopt;
  }
  return static_cast<std::uint32_t>(index);
}

// `kMaxMonthIndex + 1` is accepted here and is the single value this derivation
// computes outside the accepted timestamp range: it is the exclusive end of
// December 9999, which is what `month_end_millis` subtracts one from. That is
// why the accepted range ends at the last millisecond of 9999 rather than at the
// `u64` bound — the one-past-the-end value has to be representable.
std::optional<std::uint64_t> month_start_millis(std::uint32_t index) {
  if (index > kMaxMonthIndex + 1U) return std::nullopt;
  const std::int64_t year =
      static_cast<std::int64_t>(kMinCalendarYear) + index / kMonthsPerYear;
  const std::uint32_t month = index % kMonthsPerYear + 1U;
  const std::int64_t day = days_from_civil(year, month, 1);
  if (day < 0) return std::nullopt;
  return static_cast<std::uint64_t>(day) * kMillisPerDay;
}

std::optional<std::uint64_t> month_end_millis(std::uint32_t index) {
  if (!month_in_range(index)) return std::nullopt;
  const auto next = month_start_millis(index + 1U);
  if (!next) return std::nullopt;
  return *next - 1U;
}

// Window `w` opens at height `w * kCycleBlocks`. Window 0's opening height is 0,
// which no chain ever has — `ledger-transition-v1` starts a chain at height 1 —
// so genesis is its opening height and writes its month. That is the general
// rule reaching the one height that is a genesis rather than a block, not a
// special case.
std::uint64_t window_opening_height(std::uint64_t cycle_window) {
  return cycle_window * kCycleBlocks;
}

// --- kind 20, the window month ----------------------------------------------

Bytes window_month_key(std::uint64_t cycle_window) {
  auto key = i::key_prefix(Entry::window_month);
  i::append_u64(key, cycle_window);
  return key;
}

std::optional<Bytes> window_month_value(std::uint32_t month_index) {
  return month_value(month_index);
}

std::optional<std::uint32_t> decode_window_month_value(
    std::span<const std::uint8_t> raw) {
  return decode_month_value(raw, Entry::window_month);
}

// --- kind 21, the monthly uptime figure -------------------------------------

// The month is in the key even though exactly one month ever accumulates. The
// key could have been the seat alone, four octets shorter, with the cursor
// saying which month the figures belong to. It is not, for the reason version
// eight put the window in a seat window record's key while retaining only two:
// a stale entry from another month is then visibly wrong rather than silently
// counted, and the invariant that catches it can be stated over the state
// instead of over the history that produced it.
std::optional<Bytes> monthly_figure_key(std::uint32_t month_index,
                                        std::uint32_t seat_id) {
  if (!month_in_range(month_index)) return std::nullopt;
  auto key = i::key_prefix(Entry::monthly_uptime_figure);
  i::append_u32(key, month_index);
  i::append_u32(key, seat_id);
  return key;
}

// Accumulated seconds, nonzero. A zero figure is a second encoding of absence,
// which `protocol-primitives-v1` forbids everywhere, and admitting one would be
// the difference between writing as many entries as ran and writing 100,000
// every window.
std::optional<Bytes> monthly_figure_value(std::uint64_t uptime_seconds) {
  if (uptime_seconds == 0) return std::nullopt;
  Bytes value;
  i::append_u64(value, uptime_seconds);
  return value;
}

std::optional<std::uint64_t> decode_monthly_figure_value(
    std::span<const std::uint8_t> raw) {
  const auto width =
      entry_value_bytes(static_cast<std::uint8_t>(Entry::monthly_uptime_figure));
  if (!width || raw.size() != *width) return std::nullopt;
  const auto seconds = i::read_u64(raw, 0);
  if (!seconds || *seconds == 0) return std::nullopt;
  return *seconds;
}

// --- kind 22, the monthly pool claim ----------------------------------------

Bytes monthly_claim_key(std::uint32_t seat_id) {
  auto key = i::key_prefix(Entry::monthly_pool_claim);
  i::append_u32(key, seat_id);
  return key;
}

// A claim is a balance and a balance of zero is absence, so a settlement whose
// share rounds to zero writes no entry at all. The entry survives being emptied,
// exactly as a referral balance does: the pair is the audit trail of what a
// machine earned and what it took.
std::optional<Bytes> monthly_claim_value(const MonthlyClaim& claim) {
  if (claim.accrued_atomic == 0) return std::nullopt;
  if (claim.minted_atomic > claim.accrued_atomic) return std::nullopt;
  Bytes value;
  i::append_u64(value, claim.accrued_atomic);
  i::append_u64(value, claim.minted_atomic);
  return value;
}

std::optional<MonthlyClaim> decode_monthly_claim_value(
    std::span<const std::uint8_t> raw) {
  const auto width =
      entry_value_bytes(static_cast<std::uint8_t>(Entry::monthly_pool_claim));
  if (!width || raw.size() != *width) return std::nullopt;
  const auto accrued = i::read_u64(raw, 0);
  const auto minted = i::read_u64(raw, 8);
  if (!accrued || !minted) return std::nullopt;
  const MonthlyClaim claim{*accrued, *minted};
  // Checked against the encoder's own rule rather than against a second copy of
  // it: a value the encoder would refuse to write is not one a decoder may open.
  if (!monthly_claim_value(claim)) return std::nullopt;
  return claim;
}

// --- kind 23, the settlement cursor -----------------------------------------

Bytes settlement_cursor_key() {
  return i::key_prefix(Entry::settlement_cursor);
}

std::optional<Bytes> settlement_cursor_value(std::uint32_t accumulating_month) {
  return month_value(accumulating_month);
}

std::optional<std::uint32_t> decode_settlement_cursor_value(
    std::span<const std::uint8_t> raw) {
  return decode_month_value(raw, Entry::settlement_cursor);
}

// --- the block header -------------------------------------------------------

std::optional<Bytes> block_header(const Octets32& chain_id, std::uint64_t height,
                                  std::uint64_t timestamp,
                                  const Hash& previous_state_root,
                                  const Hash& transaction_root_value,
                                  const Hash& resulting_state_root,
                                  std::uint32_t transaction_count) {
  if (!timestamp_in_range(timestamp)) return std::nullopt;
  Bytes raw;
  raw.reserve(kBlockHeaderBytes);
  i::append(raw, std::span<const std::uint8_t>(kBlockMagic));
  i::append_u16(raw, kBlockHeaderSchemaVersion);
  i::append(raw, chain_id);
  i::append_u64(raw, height);
  i::append_u64(raw, timestamp);
  i::append(raw, previous_state_root);
  i::append(raw, transaction_root_value);
  i::append(raw, resulting_state_root);
  i::append_u32(raw, transaction_count);
  if (raw.size() != kBlockHeaderBytes) return std::nullopt;
  return raw;
}

std::optional<Hash> block_id(std::span<const std::uint8_t> header) {
  if (header.size() != kBlockHeaderBytes) return std::nullopt;
  return protocol::v1::hash(kBlockIdLabel, header);
}

std::optional<Hash> predecessor_block_id(std::span<const std::uint8_t> header) {
  if (header.size() != kBlockHeaderBytes) return std::nullopt;
  return protocol::v1::hash("protocol-stack:v1:block-id", header);
}

}  // namespace protocol::v9
