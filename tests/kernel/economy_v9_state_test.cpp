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
// **The cross-version claims are executed rather than asserted.** Version eight
// is still compiled, so "a version-eight decoder refuses a version-nine entry"
// is checked by handing the entry to version eight's own tree and requiring it
// to refuse, not by comparing two width tables.

#include "economy_v9_fixture.hpp"

#include "protocol/v8/economy.hpp"

#include <string>

namespace economy_v9_fixture {
namespace {

namespace v8 = protocol::v8;

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

void verify_widths(const pv::Values& values, const pv::Values& carried_eight) {
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
    pv::require(!v8::is_entry_kind(kind),
                "version eight never assigned this entry kind");
  }

  const auto pool = static_cast<std::uint8_t>(v9::Entry::unreferred_pool);
  const auto widened = v9::entry_value_bytes(pool);
  pv::require(widened.has_value(), "the pool value is a fixed width");
  pv::require(expect_size(values, "state.unreferred_pool.value_bytes") == *widened,
              "the pool value is 24 octets");
  // Version eight's width comes from the file that accepted it and from the
  // kernel still compiling it, rather than from a figure this file restates.
  const auto carried = v8::entry_value_bytes(pool);
  pv::require(carried.has_value(), "version eight's pool value is fixed too");
  pv::require(
      expect_size(values, "state.unreferred_pool.value_bytes_in_version_eight") ==
          *carried,
      "version eight's pool value is 16 octets");
  pv::require(*widened == *carried + 8, "the pool value grew by one u64");
  (void)carried_eight;

  std::size_t assigned = 0;
  for (std::uint16_t kind = 0; kind <= 255; ++kind) {
    if (v9::is_entry_kind(static_cast<std::uint8_t>(kind))) ++assigned;
  }
  pv::require(expect_size(values, "state.entry_kind_count") == assigned,
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

// Version eight's tree is asked to accept each version-nine entry and required
// to refuse it. Handing it the entry is what makes the boundary behaviour rather
// than a sentence about lengths: a width table can agree with itself.
void verify_cross_version(const pv::Values& values) {
  const auto month = fixture_window_month();
  const auto refused = [](const v9::Bytes& key, const v9::Bytes& value) {
    std::vector<v8::EconomyEntry> entries;
    entries.push_back({v8::Bytes(key.begin(), key.end()),
                       v8::Bytes(value.begin(), value.end())});
    pv::require(!v8::economy_root(entries),
                "version eight refuses the entry rather than hashing it");
  };

  refused(v9::window_month_key(kFixtureWindow), *v9::window_month_value(month));
  expect_true(values, "state.version_eight_refuses_the_window_month");

  refused(*v9::monthly_figure_key(month, kFixtureSeat),
          *v9::monthly_figure_value(kFixtureFigureSeconds));
  expect_true(values, "state.version_eight_refuses_the_monthly_figure");

  refused(v9::monthly_claim_key(kFixtureSeat),
          *v9::monthly_claim_value({kFixtureClaimAccrued, 0}));
  expect_true(values, "state.version_eight_refuses_the_monthly_claim");

  refused(v9::settlement_cursor_key(), *v9::settlement_cursor_value(month));
  expect_true(values, "state.version_eight_refuses_the_settlement_cursor");

  // The pool is the one entry whose *kind* version eight knows, so this is the
  // width refusal rather than the unknown-kind refusal, and it is the reason the
  // widening is a version rather than an edit.
  const auto widened =
      *v9::unreferred_pool_value({kFixturePoolAccrued, kFixturePoolPayable, 0});
  const auto pool_key = v9::unreferred_pool_key();
  pv::require(v8::is_entry_kind(pool_key.front()),
              "version eight knows the pool's kind");
  refused(pool_key, widened);
  expect_true(values, "state.version_eight_refuses_the_widened_pool");

  // And the converse, which the specification states and nothing else here
  // reaches: a version-eight pool value is not a version-nine one.
  const auto narrow = v8::unreferred_pool_value(1, 0);
  pv::require(!v9::decode_unreferred_pool_value(
                  v9::Bytes(narrow.begin(), narrow.end())),
              "version nine refuses version eight's pool value by width");
}

}  // namespace

void verify_state(const pv::Values& values, const pv::Values& carried_eight) {
  verify_widths(values, carried_eight);
  verify_encodings(values);
  verify_refusals(values);
  verify_cross_version(values);
}

}  // namespace economy_v9_fixture
