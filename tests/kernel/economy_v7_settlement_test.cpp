// Channel 8's arithmetic, the bounded mint walk, and the cycle-assignment
// record.
//
// The assignment record is checked against
// `test-vectors/economy-transition-v3.txt`, because version six's settlement is
// version three's imported rather than reimplemented and the specification
// requires the record written for the same population to be byte-identical.

#include "economy_v7_fixture.hpp"

namespace economy_v7_fixture {
namespace {

void verify_verified_user(const pv::Values& values) {
  const auto daily = v7::verified_user_daily_atomic();
  pv::require(daily.has_value(), "the rate divides exactly");
  pv::require(*daily == expect_number(values, "verified_user.daily_atomic"),
              "the derived daily rate");
  pv::require(*daily == v7::kVerifiedUserDailyAtomic, "and the declared constant");
  pv::require(v7::kVerifiedUserChannel ==
                      expect_number(values, "verified_user.channel_id") &&
                  v7::kVerifiedUserPopulation ==
                      expect_number(values, "verified_user.population") &&
                  v7::kVerifiedUserCycles ==
                      expect_number(values, "verified_user.cycles") &&
                  v7::kVerifiedUserChannelCapAtomic ==
                      expect_number(values, "verified_user.channel_cap_atomic"),
              "the three founder-supplied figures and the accepted cap");
  expect_true(values, "verified_user.the_rate_reproduces_the_accepted_cap");

  // 731 is the period the figures fix rather than a choice: 730 leaves a
  // remainder and 731 leaves none.
  pv::require(v7::verified_user_remainder_at(730) ==
                  expect_number(values,
                                "verified_user.channel_cap_remainder_at_730_cycles"),
              "the remainder a 730-cycle period leaves");
  pv::require(v7::verified_user_remainder_at(v7::kVerifiedUserCycles) == 0,
              "a 731-cycle period leaves none");
  expect_true(values, "verified_user.a_730_cycle_period_leaves_a_remainder");
  expect_true(values, "verified_user.a_731_cycle_period_leaves_none");

  const auto maximum = v7::kVerifiedUserCycles * v7::kVerifiedUserDailyAtomic;
  pv::require(maximum ==
                  expect_number(values, "verified_user.maximum_per_identity_atomic"),
              "the per-identity maximum");
  pv::require(v7::kVerifiedUserDailyAtomic ==
                  expect_number(values, "verified_user.airdrop_atomic"),
              "day one is the entry airdrop");

  const auto enrolled = kEnrolledWindow;
  pv::require(v7::window_of_height(kRegistrationHeight) ==
                  expect_number(values, "verified_user.enrolled_window"),
              "the enrolment window");
  pv::require(enrolled + v7::kVerifiedUserCycles - 1 ==
                  expect_number(values, "verified_user.last_window"),
              "the last collectable window");

  struct Case {
    const char* prefix;
    std::uint64_t height;
  };
  const Case cases[] = {
      {"verified_user.the_day_after_enrollment.", 6 * v7::kCycleBlocks},
      {"verified_user.at_the_cap.", 36 * v7::kCycleBlocks},
      {"verified_user.one_window_past_the_cap.", 37 * v7::kCycleBlocks},
      {"verified_user.ten_windows_past_the_cap.", 46 * v7::kCycleBlocks},
      {"verified_user.long_past_the_period.", 1'000 * v7::kCycleBlocks},
  };
  for (const auto& [prefix, height] : cases) {
    const auto collection = v7::verified_user_collection(enrolled, enrolled, height);
    const std::string key = prefix;
    pv::require(collection.window_start == expect_number(values, key + "window_start"),
                "the collection's first window");
    pv::require(collection.collectable_end ==
                    expect_number(values, key + "collectable_end"),
                "the collection's last window");
    pv::require(collection.count == expect_number(values, key + "count"),
                "the collected count");
    pv::require(collection.amount_atomic ==
                    expect_number(values, key + "amount_atomic"),
                "the collected amount");
  }

  // Forty windows of neglect: the most recent thirty are collected and the
  // older ten are never issued, because the mark advances past them. That is
  // what makes the forfeiture permanent rather than deferred.
  const auto forfeiting =
      v7::verified_user_collection(enrolled, enrolled, 46 * v7::kCycleBlocks);
  pv::require(forfeiting.window_start - enrolled ==
                  expect_number(values, "verified_user.forfeited_windows_after_forty"),
              "the forfeited window count");
  pv::require(forfeiting.count == v7::kMintAccumulationCap,
              "a forfeiting mint collects exactly the cap");
  const auto later = v7::verified_user_collection(forfeiting.collectable_end, enrolled,
                                                  1'000 * v7::kCycleBlocks);
  pv::require(later.window_start >= forfeiting.collectable_end,
              "the forfeited windows are not collectable later");
  for (const auto* key : {"verified_user.a_forfeiting_mint_collects_exactly_the_cap",
                          "verified_user.the_mark_advances_past_the_forfeited_windows",
                          "verified_user.the_forfeited_windows_are_not_collectable_later"}) {
    expect_true(values, key);
  }

  // A person who collects at least every thirty windows loses nothing, and the
  // total is the airdrop plus 730 daily permissions to the atomic unit.
  std::uint64_t issued = v7::kVerifiedUserDailyAtomic;
  std::uint64_t mark = enrolled;
  const auto period_end = enrolled + v7::kVerifiedUserCycles - 1;
  while (true) {
    const auto target = std::min(mark + v7::kMintAccumulationCap, period_end);
    const auto collection =
        v7::verified_user_collection(mark, enrolled, (target + 1) * v7::kCycleBlocks);
    if (collection.count == 0) break;
    issued += collection.amount_atomic;
    mark = collection.collectable_end;
  }
  pv::require(
      issued == expect_number(
                    values, "verified_user.a_complete_period_issues_the_full_allocation"),
      "a complete period issues the full allocation");
  pv::require(issued == maximum, "and that is the per-identity maximum");
  pv::require(v7::verified_user_collection(mark, enrolled, 5'000 * v7::kCycleBlocks)
                      .count ==
                  expect_number(values,
                                "verified_user.nothing_is_collectable_after_the_period"),
              "nothing is collectable after the period");
  expect_true(values, "verified_user.issuance_stays_within_the_cap");
  pv::require(issued <= v7::kVerifiedUserChannelCapAtomic / v7::kVerifiedUserPopulation,
              "one identity's issuance stays within its share of the cap");

  // Channel 8 has left the reserved direct-issue set, because ADR 0042 decided
  // both its eligibility and its rate.
  std::string derived;
  for (const auto channel : v7::kDirectIssueChannels) {
    if (!derived.empty()) derived.push_back(',');
    derived += std::to_string(channel);
  }
  pv::require(derived == expect_text(values,
                                     "verified_user.reserved_direct_issue_channels"),
              "the three reserved channels");
  pv::require(std::find(v7::kDirectIssueChannels.begin(),
                        v7::kDirectIssueChannels.end(),
                        v7::kVerifiedUserChannel) == v7::kDirectIssueChannels.end(),
              "channel 8 is not among them");
  expect_true(values, "verified_user.channel_eight_left_the_reserved_direct_issue_set");
}

void verify_walk(const pv::Values& values) {
  pv::require(v7::kMintAccumulationCap ==
                      expect_number(values, "settlement.assignment_cap_windows") &&
                  v7::kAssignmentLagWindows ==
                      expect_number(values, "settlement.assignment_lag_windows"),
              "the cap and the lag");

  pv::require(v7::accrues(kCurrentMark + v7::kMintAccumulationCap, kCurrentMark),
              "a window within the cap accrues");
  pv::require(!v7::accrues(kCurrentMark + v7::kMintAccumulationCap + 1, kCurrentMark),
              "a window beyond the cap does not");
  expect_true(values, "settlement.a_window_within_the_cap_accrues");
  expect_true(values, "settlement.a_window_beyond_the_cap_does_not_accrue");

  const auto range = v7::walk_range(kCurrentMark, kCurrentMark + 100);
  pv::require(range.has_value(), "the walk range derives");
  pv::require(range->first_window ==
                  expect_number(values, "settlement.walk_first_window"),
              "the walk's first window");
  pv::require(range->last_window ==
                  expect_number(values, "settlement.walk_last_window"),
              "the walk's last window");

  // ADR 0045's third derived rule: `NOTHING_TO_MINT` is the empty range rather
  // than the literal equality, so a mark can never decrease. A seat activated
  // in window `w` holds mark `w` while the last assigned window is `w - 2`, and
  // the literal reading would let that mint lower its own mark by two — which
  // destroys the exactness argument the whole accumulation cap rests on.
  pv::require(!v7::walk_range(kCurrentMark, kCurrentMark).has_value(),
              "a mark at the last assigned window walks nothing");
  pv::require(!v7::walk_range(kCurrentMark, std::nullopt).has_value(),
              "no window assigned yet walks nothing");
  pv::require(!v7::walk_range(kCurrentMark + 2, kCurrentMark).has_value(),
              "a mark above the last assigned window walks nothing");
  expect_true(values, "settlement.a_mark_at_the_last_assigned_window_walks_nothing");
  pv::require(v7::walk_range(kCurrentMark, kCurrentMark + 1)->last_window ==
                  kCurrentMark + 1,
              "a short range is closed at the last assigned window");
}

void verify_cycle_assignment(const pv::Values& values,
                             const pv::Values& version_three) {
  // Reconstructed from the recorded population rather than round-tripped, so a
  // packing error is caught rather than preserved: the bitmaps are indexed by
  // seat identifier with the most significant bit first, and the record carries
  // no bitmap length prefixes because both widths follow from `bitmap_bits`.
  constexpr std::uint32_t kBits = 24;
  const std::uint32_t accrued_seats[] = {0, 4, 15};
  const std::uint32_t winner_seats[] = {0, 4, 23};

  v7::CycleAssignment assignment;
  assignment.share_per_winner_atomic = 11'400'000'000ULL;
  assignment.reallocated_count = 2;
  assignment.winner_count = 3;
  assignment.in_scope_count = 6;
  assignment.bitmap_bits = kBits;
  const auto accrued_bits = v7::bitmap(accrued_seats, kBits);
  const auto winner_bits = v7::bitmap(winner_seats, kBits);
  pv::require(accrued_bits && winner_bits, "the bitmaps pack");
  assignment.accrued_bitmap = *accrued_bits;
  assignment.winner_bitmap = *winner_bits;

  const std::uint32_t beyond[] = {kBits};
  pv::require(!v7::bitmap(beyond, kBits).has_value(),
              "a seat outside the bit count cannot be packed");

  const auto value = v7::cycle_assignment_value(assignment);
  pv::require(value.has_value(), "the record encodes");
  pv::require(hex(*value) == version_three.at("cycle.assignment_value_hex"),
              "the record is byte-identical to version three's");
  pv::require(hex(v7::cycle_assignment_key(kCycleWindow)) ==
                  version_three.at("cycle.assignment_key"),
              "and so is its key");
  pv::require(expect_size(values, "state.entry3.key_bytes") ==
                  v7::cycle_assignment_key(kCycleWindow).size(),
              "the assignment key width");

  auto mismatched = assignment;
  mismatched.winner_bitmap.pop_back();
  pv::require(!v7::cycle_assignment_value(mismatched).has_value(),
              "a bitmap of the wrong width is refused");

  const auto decoded = v7::decode_cycle_assignment_value(*value);
  pv::require(decoded.has_value(), "the record decodes");
  pv::require(decoded->winner_count == 3 && decoded->reallocated_count == 2 &&
                  decoded->in_scope_count == 6 && decoded->bitmap_bits == kBits,
              "the decoded counts are the encoded ones");
  for (const auto seat : winner_seats) {
    pv::require(v7::bit_is_set(decoded->winner_bitmap, seat), "a winner bit is set");
  }
  for (const auto seat : accrued_seats) {
    pv::require(v7::bit_is_set(decoded->accrued_bitmap, seat), "an accrued bit is set");
  }
  pv::require(!v7::bit_is_set(decoded->accrued_bitmap, 23),
              "a seat may win without accruing");
  pv::require(!v7::bit_is_set(decoded->winner_bitmap, 15),
              "a seat may accrue without winning");
  auto short_record = *value;
  short_record.pop_back();
  pv::require(!v7::decode_cycle_assignment_value(short_record).has_value(),
              "a record whose length disagrees with its bit count is refused");

  // The total-outage cycle: no seat met it, so the winner set is empty and the
  // whole permission carries.
  v7::CycleAssignment outage;
  outage.in_scope_count = 6;
  outage.reallocated_count = 5;
  outage.bitmap_bits = kBits;
  outage.accrued_bitmap = *v7::bitmap({}, kBits);
  outage.winner_bitmap = *v7::bitmap({}, kBits);
  const auto outage_value = v7::cycle_assignment_value(outage);
  pv::require(outage_value.has_value(), "the empty-winner record encodes");
  pv::require(hex(*outage_value) == version_three.at("outage.assignment_value_hex"),
              "the empty-winner record is version three's");
  pv::require(hex(v7::cycle_assignment_key(kOutageWindow)) ==
                  version_three.at("outage.assignment_key"),
              "and so is its key");
}

}  // namespace

void verify_settlement(const pv::Values& values, const pv::Values& version_three) {
  verify_verified_user(values);
  verify_walk(values);
  verify_cycle_assignment(values, version_three);
}

}  // namespace economy_v7_fixture
