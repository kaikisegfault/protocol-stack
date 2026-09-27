// The four entry kinds version nine adds and the one value it widens, checked
// against the recorded vectors.
//
// **The refusals are the substance here rather than the encodings.** A key and a
// value of the right width is what any implementation gets right; what
// distinguishes a conforming one is that a zero figure, a zero claim, a month
// above the calendar bound, and a pool that has assigned more than it accrued
// are all refused, because each would give one fact two encodings or record a
// state no conforming settlement can reach.
//
// **The cross-version claims are pinned to the files that accepted version
// eight.** Its kernel is deleted (ADR 0092), so "a version-eight decoder refuses
// a version-nine entry" is no longer something this suite can execute; the
// verifier that still can, against the version-eight Python model, is named in
// the coverage guard. What stays here is the half version nine owns: its entry
// table is version eight's recorded one plus exactly four kinds, and it refuses
// version eight's pool value by width.

#include "economy_v9_carried.hpp"

#include <set>
#include <string>

namespace economy_v9_fixture {
namespace {

// The recorded fixture's settlement figures. They are magnitudes rather than
// founder-directed values — what the vectors fix is the encoding, and the
// arithmetic that produced them is the ledger slice's — so they are stated here
// and compared against the recorded bytes.
constexpr std::uint64_t kFixtureWindow = 4;
constexpr std::uint32_t kFixtureSeat = 2;
constexpr std::uint64_t kFixtureFigureSeconds = 216'000;
constexpr std::uint64_t kFixtureClaimAccrued = 9'120'000'000;
constexpr std::uint64_t kFixturePoolAccrued = 23'940'000'001;
constexpr std::uint64_t kFixturePoolPayable = 3'420'000'001;
constexpr std::uint32_t kFixtureCursorMonth = 679;

// The month the recorded window belongs to, derived through this kernel's own
// calendar from the height that window opens at, rather than restated. The
// recorded key and value below then have to agree with a derivation instead of
// with a literal beside them.
std::uint32_t fixture_window_month() {
  const auto opening = v9::window_opening_height(kFixtureWindow);
  const auto month = v9::month_index(timestamp_of_height(opening));
  pv::require(month.has_value(), "the window's opening height has a month");
  return *month;
}

void verify_widths(const pv::Values& values, const Carried& carried) {
  auto expected = version_eight_entry_kinds(carried);
  struct Declared {
    const char* prefix;
    v9::Entry entry;
    std::size_t key_bytes;
    std::size_t value_bytes;
  };
  const Declared declared[] = {
      {"state.window_month", v9::Entry::window_month, 9, 4},
      {"state.monthly_figure", v9::Entry::monthly_uptime_figure, 9, 8},
      {"state.monthly_claim", v9::Entry::monthly_pool_claim, 5, 16},
      {"state.settlement_cursor", v9::Entry::settlement_cursor, 1, 4},
  };
  for (const auto& item : declared) {
    const auto kind = static_cast<std::uint8_t>(item.entry);
    pv::require(expect_number(values, std::string(item.prefix) + ".kind") == kind,
                "the entry kind is the recorded one");
    pv::require(v9::is_entry_kind(kind), "the kind is assigned in version nine");
    pv::require(!v9::is_retired_entry_kind(kind),
                "no version-nine entry kind reuses a retired number");
    const auto key_bytes = v9::entry_key_bytes(kind);
    const auto value_bytes = v9::entry_value_bytes(kind);
    pv::require(key_bytes.has_value() && value_bytes.has_value(),
                "both widths are fixed");
    pv::require(
        expect_size(values, std::string(item.prefix) + ".key_bytes") == *key_bytes,
        "the key width is the recorded one");
    pv::require(*key_bytes == item.key_bytes, "the key width is its field sum");
    pv::require(expect_size(values, std::string(item.prefix) + ".value_bytes") ==
                    *value_bytes,
                "the value width is the recorded one");
    pv::require(*value_bytes == item.value_bytes,
                "the value width is its field sum");
    // Version eight assigned none of these numbers, so each extends the space
    // rather than reinterpreting it.
    pv::require(expected.insert(kind).second,
                "version eight never assigned this entry kind");
  }

  const auto pool = static_cast<std::uint8_t>(v9::Entry::unreferred_pool);
  const auto widened = v9::entry_value_bytes(pool);
  pv::require(widened.has_value(), "the pool value is a fixed width");
  pv::require(expect_size(values, "state.unreferred_pool.value_bytes") == *widened,
              "the pool value is 24 octets");
  // Version eight's width is version seven's, which the file that accepted it
  // records under the pool's own name, rather than a figure this file restates.
  pv::require(carried.seven.at("state.kind" + std::to_string(pool) + ".name") ==
                  "unreferred_pool",
              "version seven's table names the pool's kind");
  const auto narrow = version_seven_width(carried, pool, "value_bytes");
  pv::require(
      expect_size(values, "state.unreferred_pool.value_bytes_in_version_eight") ==
          narrow,
      "version eight's pool value is 16 octets");
  pv::require(*widened == narrow + 8, "the pool value grew by one u64");

  // **Version nine's table is version eight's plus the four above, exactly.** A
  // kind either side has and the other lacks fails here by number, so the four
  // being new is checked against the whole recorded table rather than one entry
  // at a time.
  std::set<std::uint8_t> assigned;
  for (std::uint16_t kind = 0; kind <= 255; ++kind) {
    if (v9::is_entry_kind(static_cast<std::uint8_t>(kind))) {
      assigned.insert(static_cast<std::uint8_t>(kind));
    }
  }
  pv::require(assigned == expected,
              "version nine assigns version eight's entry kinds and four more");
  pv::require(expect_size(values, "state.entry_kind_count") == assigned.size(),
              "twenty entry kinds are assigned");

  pv::require(expect_size(values, "state.live_window_months") ==
                  v9::kLiveWindowMonths,
              "two window-month entries are live");
  // The larger figure `unreferred-pool-payout-v1` sized for, kept so the
  // difference is visible rather than a silent disagreement: that document
  // counts the open window and the two inside the assignment lag, and version
  // nine deletes the oldest in the same prologue that assigns it.
  pv::require(expect_size(values, "state.live_window_months_sized_by_the_payout_spec") ==
                  v9::kLiveWindowMonths + 1,
              "the payout specification sized it at three");
}

void verify_encodings(const pv::Values& values) {
  const auto month = fixture_window_month();

  const auto window_key = v9::window_month_key(kFixtureWindow);
  pv::require(hex(window_key) == expect_text(values, "state.window_month.key"),
              "the window month key is the recorded one");
  const auto window_value = v9::window_month_value(month);
  pv::require(window_value.has_value(), "a month in range encodes");
  pv::require(hex(*window_value) == expect_text(values, "state.window_month.value"),
              "the window month value is the derived month");
  const auto decoded_month = v9::decode_window_month_value(*window_value);
  pv::require(decoded_month.has_value() && *decoded_month == month,
              "the window month round-trips");

  const auto figure_key = v9::monthly_figure_key(month, kFixtureSeat);
  pv::require(figure_key.has_value(), "a month in range makes a key");
  pv::require(hex(*figure_key) == expect_text(values, "state.monthly_figure.key"),
              "the monthly figure key is the recorded one");
  const auto figure_value = v9::monthly_figure_value(kFixtureFigureSeconds);
  pv::require(figure_value.has_value(), "a nonzero figure encodes");
  pv::require(
      hex(*figure_value) == expect_text(values, "state.monthly_figure.value"),
      "the monthly figure value is the recorded one");
  const auto decoded_figure = v9::decode_monthly_figure_value(*figure_value);
  pv::require(decoded_figure.has_value() && *decoded_figure == kFixtureFigureSeconds,
              "the monthly figure round-trips");

  const auto claim_key = v9::monthly_claim_key(kFixtureSeat);
  pv::require(hex(claim_key) == expect_text(values, "state.monthly_claim.key"),
              "the monthly claim key is the recorded one");
  const auto claim_value = v9::monthly_claim_value({kFixtureClaimAccrued, 0});
  pv::require(claim_value.has_value(), "a nonzero claim encodes");
  pv::require(hex(*claim_value) == expect_text(values, "state.monthly_claim.value"),
              "the monthly claim value is the recorded one");
  const auto decoded_claim = v9::decode_monthly_claim_value(*claim_value);
  pv::require(decoded_claim.has_value() &&
                  decoded_claim->accrued_atomic == kFixtureClaimAccrued &&
                  decoded_claim->minted_atomic == 0,
              "the monthly claim round-trips");

  pv::require(hex(v9::settlement_cursor_key()) ==
                  expect_text(values, "state.settlement_cursor.key"),
              "the settlement cursor key is one octet");
  const auto cursor_value = v9::settlement_cursor_value(kFixtureCursorMonth);
  pv::require(cursor_value.has_value(), "a month in range encodes");
  pv::require(hex(*cursor_value) ==
                  expect_text(values, "state.settlement_cursor.value"),
              "the settlement cursor value is the recorded one");
  const auto decoded_cursor = v9::decode_settlement_cursor_value(*cursor_value);
  pv::require(decoded_cursor.has_value() && *decoded_cursor == kFixtureCursorMonth,
              "the settlement cursor round-trips");

  const auto pool_value =
      v9::unreferred_pool_value({kFixturePoolAccrued, kFixturePoolPayable, 0});
  pv::require(pool_value.has_value(), "a conserved pool encodes");
  pv::require(hex(*pool_value) == expect_text(values, "state.unreferred_pool.value"),
              "the widened pool value is the recorded one");
  const auto decoded_pool = v9::decode_unreferred_pool_value(*pool_value);
  pv::require(decoded_pool.has_value() &&
                  decoded_pool->accrued_atomic == kFixturePoolAccrued &&
                  decoded_pool->payable_atomic == kFixturePoolPayable &&
                  decoded_pool->minted_atomic == 0,
              "the widened pool value round-trips");
}

void verify_refusals(const pv::Values& values) {
  // A zero is absence in two of the four new values, and both ends of each
  // codec say so: an encoder refuses to write one and a decoder refuses to open
  // one, so neither direction can introduce a second encoding of absence.
  pv::require(!v9::monthly_figure_value(0), "a zero figure is not encodable");
  pv::require(!v9::decode_monthly_figure_value(v9::Bytes(8, 0)),
              "a zero figure is not decodable");
  expect_true(values, "state.refuses_a_figure_of_zero");

  pv::require(!v9::monthly_claim_value({0, 0}), "a zero claim is not encodable");
  pv::require(!v9::decode_monthly_claim_value(v9::Bytes(16, 0)),
              "a zero claim is not decodable");
  expect_true(values, "state.refuses_a_claim_of_zero");

  pv::require(!v9::monthly_claim_value({10, 11}),
              "a claim cannot mint more than it accrued");
  const auto overminted = *v9::monthly_claim_value({11, 11});
  auto mutated = overminted;
  mutated.back() = 12;
  pv::require(!v9::decode_monthly_claim_value(mutated),
              "a decoder refuses an over-minted claim");
  expect_true(values, "state.refuses_a_claim_minting_more_than_it_accrued");

  const auto above = v9::kMaxMonthIndex + 1U;
  pv::require(!v9::window_month_value(above),
              "a month above the calendar bound is not encodable");
  v9::Bytes raw_above;
  for (int shift = 24; shift >= 0; shift -= 8) {
    raw_above.push_back(static_cast<std::uint8_t>(above >> shift));
  }
  pv::require(!v9::decode_window_month_value(raw_above),
              "a month above the calendar bound is not decodable");
  expect_true(values, "state.refuses_a_month_above_the_calendar_bound");

  pv::require(!v9::settlement_cursor_value(above),
              "a cursor above the calendar bound is not encodable");
  pv::require(!v9::decode_settlement_cursor_value(raw_above),
              "a cursor above the calendar bound is not decodable");
  expect_true(values, "state.refuses_a_cursor_above_the_calendar_bound");

  pv::require(!v9::monthly_figure_key(above, kFixtureSeat),
              "a figure key above the calendar bound is refused");
  // The bound holds at the boundary from both sides, so the refusal is the
  // rule's and not an off-by-one.
  pv::require(v9::monthly_figure_key(v9::kMaxMonthIndex, kFixtureSeat).has_value(),
              "the last representable month still makes a key");
  expect_true(values, "state.refuses_a_figure_key_above_the_calendar_bound");

  pv::require(!v9::unreferred_pool_value({10, 11, 0}),
              "a pool cannot owe more than it accrued");
  expect_true(values, "state.refuses_a_pool_payable_above_accrued");
  pv::require(!v9::unreferred_pool_value({10, 4, 7}),
              "a pool cannot mint more than it assigned");
  pv::require(v9::unreferred_pool_value({10, 4, 6}).has_value(),
              "assigning exactly what was minted is conserved");
  expect_true(values, "state.refuses_a_pool_minting_more_than_it_assigned");
}

// **One direction of the boundary survives the version-eight kernel.** Version
// eight refusing each version-nine entry went with the only C++ that could
// refuse it; the five `state.version_eight_refuses_*` vectors are owed to the
// verifier that still runs version eight's Python model. This is the direction
// that matters to a chain running version nine: a version-eight pool value,
// written out as the literal version seven's table fixes rather than produced by
// a sibling encoder, is refused by width, and a positive control of the same
// quantities at version nine's width is accepted, so the refusal is about the
// width rather than the numbers.
void verify_cross_version(const Carried& carried) {
  const auto pool = static_cast<std::uint8_t>(v9::Entry::unreferred_pool);
  const auto narrow_width = version_seven_width(carried, pool, "value_bytes");
  // `accrued` 1, `minted` 0: two big-endian u64s, version eight's layout.
  v9::Bytes narrow(narrow_width, 0);
  narrow[7] = 1;
  pv::require(!v9::decode_unreferred_pool_value(narrow),
              "version nine refuses version eight's pool value by width");
  const auto control = v9::unreferred_pool_value({1, 0, 0});
  pv::require(control.has_value() &&
                  v9::decode_unreferred_pool_value(*control).has_value(),
              "the same quantities at version nine's width are accepted");
  pv::require(control->size() == narrow.size() + 8,
              "and the two differ by exactly the inserted field");
}

}  // namespace

void verify_state(const pv::Values& values, const Carried& carried) {
  verify_widths(values, carried);
  verify_encodings(values);
  verify_refusals(values);
  verify_cross_version(carried);
}

}  // namespace economy_v9_fixture
