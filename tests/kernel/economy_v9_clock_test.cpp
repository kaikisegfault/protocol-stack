// `calendar-v1`'s figures and its five ordered rules, checked against the
// recorded vectors.
//
// **The proposals are the recorded fixture's, in its order, and the order
// matters**: a head advances only on an acceptance, so the two refusals that
// follow the accepted prefix are refused against a head the earlier proposals
// placed. Running them in any other order would test different comparisons while
// still producing five condition names.
//
// **The replay evidence is the point of the whole section.** An accepted chain
// is re-run through the entry point that takes no clock, and separately through
// the one that does with a clock ten tolerances stale. The first must agree
// height for height and the second must refuse every height — which is what "a
// machine that re-applied C5 on replay would reject the chain's own past" means
// as a check rather than as a warning.

#include "economy_v9_fixture.hpp"

#include <algorithm>
#include <array>
#include <set>
#include <string>
#include <utility>
#include <vector>

namespace economy_v9_fixture {
namespace {

using v9::TimestampCondition;

constexpr std::uint64_t kMillis = 1'000;

struct Proposal {
  std::uint64_t height;
  std::uint64_t timestamp;
  std::uint64_t observed_clock;
  const char* label;
};

// `simulation/economy_transition_v9/scenario.py`'s proposals. A machine's own
// clock is written as the proposed timestamp plus an offset, because C5 is about
// the distance between the two and not about either value.
std::array<Proposal, 11> proposals() {
  const auto at = timestamp_of_height;
  const auto tolerance = v9::kTimestampToleranceMillis;
  return {{
      {1, at(1), at(1), "accepts_the_first_block"},
      // Two consecutive blocks may carry the same millisecond: C2 is
      // non-decreasing rather than strictly increasing, because a chain catching
      // up after a halt produces blocks faster than one a second.
      {2, at(1), at(1), "accepts_an_equal_timestamp"},
      {3, at(3), at(3), "accepts_a_later_timestamp"},
      {5, at(4), at(4), "refuses_a_height_that_is_not_next"},
      {4, v9::kMaxTimestampMillis + 1, at(4), "refuses_a_timestamp_above_the_range"},
      {4, at(3) - kMillis, at(3), "refuses_a_timestamp_below_its_predecessor"},
      {4, kGenesisMillis - kMillis, kGenesisMillis,
       "refuses_a_timestamp_below_genesis_after_a_reset"},
      {4, at(4) + tolerance + 1, at(4), "refuses_a_timestamp_ahead_of_the_tolerance"},
      {4, at(4), at(4) + tolerance + 1, "refuses_a_timestamp_behind_the_tolerance"},
      {4, at(4) + tolerance, at(4), "accepts_at_the_ahead_boundary"},
      // Exactly one tolerance behind the observing machine's clock, and equal to
      // its predecessor rather than below it: the two rules are separate, and a
      // case that failed C2 would test nothing about C5.
      {5, at(4) + tolerance, at(4) + 2 * tolerance, "accepts_at_the_behind_boundary"},
  }};
}

void verify_figures(const pv::Values& values) {
  pv::require(expect_number(values, "clock.millis_per_day") == v9::kMillisPerDay,
              "the day is 86,400,000 milliseconds");
  pv::require(
      expect_number(values, "clock.min_timestamp_millis") == v9::kMinTimestampMillis,
      "the range starts at the epoch");
  pv::require(
      expect_number(values, "clock.max_timestamp_millis") == v9::kMaxTimestampMillis,
      "the range ends at the last millisecond of 9999");
  pv::require(expect_number(values, "clock.max_month_index") == v9::kMaxMonthIndex,
              "the last month index is December 9999's");
  pv::require(expect_number(values, "clock.tolerance_millis") ==
                  v9::kTimestampToleranceMillis,
              "the tolerance is sixty seconds");

  // **The bound and the index agree at the boundary**, derived rather than
  // asserted: the last accepted millisecond must fall in the last month index,
  // and one more must have no month at all.
  const auto last = v9::month_index(v9::kMaxTimestampMillis);
  pv::require(last.has_value() && *last == v9::kMaxMonthIndex,
              "the last millisecond belongs to the last month");
  pv::require(!v9::month_index(v9::kMaxTimestampMillis + 1),
              "a millisecond past the range has no month");
  const auto first = v9::month_index(v9::kMinTimestampMillis);
  pv::require(first.has_value() && *first == 0, "the epoch month is index zero");

  // The tolerance is a consensus parameter of this version rather than a
  // deployment option, so it appears in no genesis field. That is checked
  // against the encoded genesis: a machine could not configure a value the bytes
  // do not carry.
  const auto genesis = fixture_genesis(v9::Octets32{});
  const auto encoded = v9::encode_genesis(genesis);
  pv::require(encoded.has_value(), "the fixture genesis encodes");
  pv::require(encoded->size() == v9::kGenesisPrefixBytes,
              "the genesis is its declared width");
  v9::Bytes needle;
  for (int shift = 56; shift >= 0; shift -= 8) {
    needle.push_back(
        static_cast<std::uint8_t>(v9::kTimestampToleranceMillis >> shift));
  }
  pv::require(std::search(encoded->begin(), encoded->end(), needle.begin(),
                          needle.end()) == encoded->end(),
              "the tolerance appears nowhere in the genesis bytes");
  expect_true(values, "clock.tolerance_is_not_a_genesis_field");
}

void verify_rules(const pv::Values& values) {
  v9::Head head{0, kGenesisMillis};
  std::vector<std::pair<std::uint64_t, std::uint64_t>> accepted;
  std::set<std::string> reached;

  for (const auto& proposal : proposals()) {
    const auto outcome = v9::accept_timestamp(head, proposal.height,
                                              proposal.timestamp,
                                              proposal.observed_clock);
    const auto name = v9::timestamp_condition_name(outcome);
    pv::require(!name.empty(), "every outcome has a name");
    reached.insert(std::string(name));
    pv::require(expect_text(values, "timestamp." + std::string(proposal.label)) ==
                    name,
                std::string("the recorded outcome of ") + proposal.label);
    if (outcome == TimestampCondition::accepted) {
      accepted.emplace_back(proposal.height, proposal.timestamp);
      head = v9::Head{proposal.height, proposal.timestamp};
    }
  }

  // Counted rather than assumed, so a later scenario cannot lose coverage of a
  // condition while still passing every vector above.
  for (std::uint8_t ordinal = 0; ordinal < v9::kTimestampConditionCount;
       ++ordinal) {
    const auto name = v9::timestamp_condition_name(
        static_cast<TimestampCondition>(ordinal));
    pv::require(reached.contains(std::string(name)),
                "the proposals reach " + std::string(name));
  }
  expect_true(values, "timestamp.every_condition_is_reached");
  pv::require(expect_size(values, "timestamp.conditions_reached") == reached.size(),
              "the recorded number of conditions is reached");

  // The clockless replay. There is no argument to `replay_timestamp` that could
  // make it check a tolerance, which is the structural half of the separation;
  // this is the behavioural half.
  v9::Head replayed{0, kGenesisMillis};
  for (const auto& [height, timestamp] : accepted) {
    const auto outcome = v9::replay_timestamp(replayed, height, timestamp);
    pv::require(outcome == TimestampCondition::accepted,
                "a replaying machine accepts every height it accepted before");
    replayed = v9::Head{height, timestamp};
  }
  pv::require(!accepted.empty(), "the chain accepted something to replay");
  pv::require(expect_number(values, "replay.head_height") == replayed.height,
              "the replayed head is at the recorded height");
  pv::require(expect_number(values, "replay.head_timestamp") == replayed.timestamp,
              "the replayed head carries the recorded timestamp");
  pv::require(expect_size(values, "replay.accepted_height_count") == accepted.size(),
              "the recorded number of heights was accepted");
  pv::require(replayed.height == accepted.back().first &&
                  replayed.timestamp == accepted.back().second,
              "replay agrees with the chain height for height");

  // The same accepted chain through the path that reads a clock, with a reading
  // ten tolerances stale. Every height must be refused: that is what makes C5's
  // absence from the replay path load-bearing rather than tidy.
  const auto stale = kGenesisMillis - 10 * v9::kTimestampToleranceMillis;
  v9::Head walking{0, kGenesisMillis};
  std::size_t survivors = 0;
  for (const auto& [height, timestamp] : accepted) {
    if (v9::accept_timestamp(walking, height, timestamp, stale) ==
        TimestampCondition::accepted) {
      ++survivors;
    }
    walking = v9::Head{height, timestamp};
  }
  pv::require(survivors == 0, "a stale clock rejects the chain's own past");
  expect_true(values, "replay.a_stale_clock_would_reject_the_chains_own_past");

  // One property of the split that no single proposal shows: the deterministic
  // prefix of `accept_timestamp` is exactly `replay_timestamp`, so no clock
  // reading can change which of the first three conditions fires. A machine that
  // let a clock influence a deterministic refusal would fork on replay.
  for (const auto& proposal : proposals()) {
    const auto without = v9::replay_timestamp(v9::Head{0, kGenesisMillis},
                                              proposal.height, proposal.timestamp);
    if (without == TimestampCondition::accepted) continue;
    for (const auto clock : {std::uint64_t{0}, proposal.observed_clock,
                             v9::kMaxTimestampMillis}) {
      pv::require(v9::accept_timestamp(v9::Head{0, kGenesisMillis},
                                       proposal.height, proposal.timestamp,
                                       clock) == without,
                  "a clock reading cannot change a deterministic refusal");
    }
  }
}

// The agreement claim, checked against the accepted `calendar-v1` file rather
// than against version nine's own restatement of it.
//
// **This is a third source and not a second opinion.** `economy-transition-v9`'s
// vectors were recorded by driving the Python model; these were recorded by
// driving `calendar-v1`'s. A C++ derivation that reproduces the second has
// agreed with the specification the first binds, which is what the claim says.
void verify_against_the_calendar(const pv::Values& values,
                                 const pv::Values& calendar) {
  const auto figure = [&calendar](const std::string& key) {
    const auto found = calendar.find(key);
    pv::require(found != calendar.end(), "calendar-v1 records no " + key);
    return std::stoull(found->second);
  };

  pv::require(figure("constants.millis_per_day") == v9::kMillisPerDay &&
                  figure("constants.min_timestamp_millis") ==
                      v9::kMinTimestampMillis &&
                  figure("constants.max_timestamp_millis") ==
                      v9::kMaxTimestampMillis &&
                  figure("constants.max_month_index") == v9::kMaxMonthIndex &&
                  figure("constants.tolerance_millis") ==
                      v9::kTimestampToleranceMillis &&
                  figure("constants.min_calendar_year") == v9::kMinCalendarYear &&
                  figure("constants.max_calendar_year") == v9::kMaxCalendarYear &&
                  figure("constants.months_per_year") == v9::kMonthsPerYear,
              "every clock figure is the accepted calendar's");

  // Each recorded derivation, including both sides of three month boundaries,
  // two leap-year Februaries, the century that is not a leap year, and the last
  // millisecond the calendar defines.
  static const char* const cases[] = {
      "epoch",
      "epoch_month_last_milli",
      "second_month_first_milli",
      "common_year_february_last",
      "common_year_march_first",
      "leap_year_february_29",
      "century_leap_february_29",
      "century_common_february_28",
      "century_common_march_first",
      "year_end",
      "year_start",
      "range_end",
  };
  for (const auto* name : cases) {
    const std::string prefix = std::string("derivation.") + name + ".";
    const auto timestamp = figure(prefix + "timestamp");
    const auto index = v9::month_index(timestamp);
    pv::require(index.has_value(), "an accepted timestamp has a month");
    pv::require(*index == figure(prefix + "month_index"),
                std::string("the month index of ") + name);
    // The year and the calendar month follow from the index by the relation the
    // index is defined through, so reproducing them checks the anchor as well as
    // the arithmetic.
    pv::require(v9::kMinCalendarYear + *index / v9::kMonthsPerYear ==
                    figure(prefix + "year"),
                std::string("the year of ") + name);
    pv::require(*index % v9::kMonthsPerYear + 1 == figure(prefix + "month"),
                std::string("the calendar month of ") + name);
    // And the timestamp must fall inside the month it names, which is what ties
    // the forward derivation to the two inverse ones.
    const auto start = v9::month_start_millis(*index);
    const auto end = v9::month_end_millis(*index);
    pv::require(start.has_value() && end.has_value(), "the month has both edges");
    pv::require(*start <= timestamp && timestamp <= *end,
                std::string("the timestamp falls inside its month, for ") + name);
  }

  // The leap rule in full rather than the abbreviation of it: 2000 is a leap
  // year and 2100 is not, and an implementation that tested only 2024 would
  // agree with the abbreviation and be wrong twice a century. February's length
  // is derived from the two month edges rather than from a table.
  const auto february_days = [&](std::uint32_t year) {
    const auto index = (year - v9::kMinCalendarYear) * v9::kMonthsPerYear + 1;
    const auto start = v9::month_start_millis(index);
    const auto end = v9::month_end_millis(index);
    pv::require(start.has_value() && end.has_value(), "February has both edges");
    return (*end + 1 - *start) / v9::kMillisPerDay;
  };
  for (const std::uint32_t year : {1970U, 2000U, 2024U, 2026U, 2100U}) {
    pv::require(february_days(year) ==
                    figure("leap.february_days_" + std::to_string(year)),
                "February's length in " + std::to_string(year));
  }

  // The ordered conditions, read out of the accepted file as a list and required
  // to be this kernel's order exactly. A reordering would still name five
  // conditions.
  const auto order = calendar.find("coverage.rejection_order");
  pv::require(order != calendar.end(), "calendar-v1 records the rejection order");
  std::string expected;
  for (std::uint8_t ordinal = 1; ordinal < v9::kTimestampConditionCount;
       ++ordinal) {
    if (ordinal > 1) expected += ',';
    expected += v9::timestamp_condition_name(
        static_cast<TimestampCondition>(ordinal));
  }
  pv::require(expected == order->second,
              "the condition order is the accepted calendar's");

  // The three ordering claims, each produced by an input that violates two rules
  // at once so the reported condition distinguishes the order rather than
  // describing it.
  const v9::Head head{4, timestamp_of_height(4)};
  const auto reported = [&](std::uint64_t height, std::uint64_t timestamp,
                            std::uint64_t clock) {
    return std::string(v9::timestamp_condition_name(
        v9::accept_timestamp(head, height, timestamp, clock)));
  };
  const auto agrees = [&](const std::string& key, const std::string& outcome) {
    const auto found = calendar.find(key);
    pv::require(found != calendar.end(), "calendar-v1 records no " + key);
    pv::require(found->second == outcome, key + " is " + outcome);
  };
  // A wrong height and an out-of-range timestamp together.
  agrees("rejection.order_height_before_range",
         reported(9, v9::kMaxTimestampMillis + 1, head.timestamp));
  // The right height, an out-of-range timestamp, and one below the predecessor.
  agrees("rejection.order_range_before_monotonic",
         reported(5, v9::kMaxTimestampMillis + 1, head.timestamp));
  // The right height, an in-range timestamp below the predecessor, and a clock
  // the tolerance would also refuse.
  agrees("rejection.order_monotonic_before_tolerance",
         reported(5, head.timestamp - v9::kMillisPerDay, head.timestamp));
  // Genesis is the same comparison as every other height, which is why the head
  // carries height zero and the genesis timestamp rather than a special rule.
  agrees("genesis.first_block_equal_to_genesis",
         std::string(v9::timestamp_condition_name(v9::accept_timestamp(
             v9::Head{0, kGenesisMillis}, 1, kGenesisMillis, kGenesisMillis))));
  agrees("genesis.first_block_below_genesis",
         std::string(v9::timestamp_condition_name(
             v9::accept_timestamp(v9::Head{0, kGenesisMillis}, 1,
                                  kGenesisMillis - 1, kGenesisMillis))));

  expect_true(values, "timestamp.agrees_with_calendar_v1");
}

}  // namespace

void verify_clock(const pv::Values& values, const pv::Values& calendar) {
  verify_figures(values);
  verify_rules(values);
  verify_against_the_calendar(values, calendar);
}

}  // namespace economy_v9_fixture
