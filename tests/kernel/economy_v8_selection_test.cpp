// Challenge selection: its preimage, its excluded tail, and its rate.
//
// The recorded rate is over a fixed beacon and a fixed seat range, so it is a
// property of a stated sample rather than a claim about every beacon. What is
// claimed absolutely is the rule: the preimage's shape, the excluded tail of
// every slot, and that the height, the seat, and the beacon are each bound.
//
// **This is deliberately not `uptime-measurement-v1`'s preimage.** That model
// digests an RFC 8785 JSON object, and a consensus kernel that canonicalised
// JSON to decide who is audited would put a parser on the most adversarial path
// the pipeline has. The two therefore select different heights for the same
// beacon, and every property the accepted specification argues from is a
// property of the rule rather than of the byte layout.

#include "economy_v8_fixture.hpp"

namespace economy_v8_fixture {
namespace {

std::uint64_t expect_selection(std::uint32_t seat_id, std::uint64_t height) {
  const auto value = v8::selection_value(kBeacon, seat_id, height);
  pv::require(value.has_value(), "the selection value derives");
  return *value;
}

void verify_preimage(const pv::Values& values) {
  const auto preimage = v8::selection_preimage(kBeacon, kProbeSeat, kChallengeHeight);
  pv::require(preimage.has_value(), "the selection preimage derives");
  pv::require(hex(*preimage) == expect_text(values, "selection.preimage"),
              "the recorded selection preimage");
  pv::require(preimage->size() == expect_size(values, "selection.preimage_bytes"),
              "the selection preimage width");
  pv::require(preimage->size() == v8::kSelectionPreimageBytes, "and the constant");

  const auto value = expect_selection(kProbeSeat, kChallengeHeight);
  pv::require(std::to_string(value) == expect_text(values, "selection.value"),
              "the recorded selection value");

  // A beacon that is not 32 octets is not a beacon.
  pv::require(!v8::selection_preimage(v8::Bytes(31, 0), kProbeSeat, kChallengeHeight)
                   .has_value(),
              "a short beacon");

  // The height is bound even though the beacon already varies with it, so a
  // selection value is unique to one height and cannot be presented as
  // belonging to another.
  pv::require(value != expect_selection(kProbeSeat, kChallengeHeight + 1),
              "the height is bound");
  expect_true(values, "selection.binds_the_height");
  pv::require(value != expect_selection(kProbeSeat + 1, kChallengeHeight),
              "the seat is bound");
  expect_true(values, "selection.binds_the_seat");
  const auto zero_beacon = v8::selection_value(v8::Bytes(32, 0), kProbeSeat,
                                               kChallengeHeight);
  pv::require(zero_beacon && *zero_beacon != value, "the beacon is bound");
  expect_true(values, "selection.binds_the_beacon");
}

void verify_exclusion(const pv::Values& values) {
  const auto window_start = v8::kCycleBlocks * kMeasuredWindow;
  const auto last = window_start + v8::kSlotBlocks - 1;
  const auto boundary = last - v8::kResponseDeadlineBlocks;

  std::uint64_t challengeable = 0;
  for (auto height = window_start; height <= last; ++height) {
    if (v8::is_challengeable_height(height)) ++challengeable;
  }
  pv::require(challengeable ==
                  expect_number(values, "selection.challengeable_heights_per_slot"),
              "the challengeable heights of a slot");
  pv::require(challengeable == v8::kChallengeableHeightsPerSlot, "and the constant");

  pv::require(v8::is_challengeable_height(boundary),
              "the last challengeable height of a slot");
  expect_true(values, "selection.last_challengeable_height_of_a_slot_is_challengeable");
  pv::require(!v8::is_challengeable_height(boundary + 1), "the next height");
  expect_true(values, "selection.the_next_height_is_excluded");
  pv::require(!v8::is_challengeable_height(last), "the slot's last height");
  expect_true(values, "selection.the_slot_s_last_height_is_excluded");

  for (std::uint32_t seat = 0; seat < kSampleSeats; ++seat) {
    const auto selected = v8::is_selected(kBeacon, seat, last);
    pv::require(selected && !*selected, "an excluded height selected somebody");
  }
  expect_true(values, "selection.an_excluded_height_selects_nobody");

  // `is_selected` refuses an excluded height *before* deriving a digest, so
  // that the pipeline pays its stated cost at 1,180 heights of every 1,200
  // rather than at all 1,200. The beacon's width is still judged first, which
  // is what stops that short-circuit from silently weakening the refusal.
  pv::require(!v8::is_selected(v8::Bytes(31, 0), kProbeSeat, last).has_value(),
              "a short beacon at an excluded height");
  pv::require(!v8::is_selected(v8::Bytes(31, 0), kProbeSeat, boundary).has_value(),
              "a short beacon at a challengeable height");

  // A challenge and its deadline never straddle a slot boundary, which is what
  // makes the expiry step's window arithmetic exact.
  for (auto height = window_start; height <= boundary; ++height) {
    pv::require(v8::slot_of(height) ==
                    v8::slot_of(height + v8::kResponseDeadlineBlocks),
                "a challenge and its deadline are in different slots");
  }
  expect_true(values, "selection.a_challenge_and_its_deadline_share_a_slot");
  // `slot_last_height` is what both facts are derived through, so it is checked
  // against its own definition at both ends of the slot.
  pv::require(v8::slot_last_height(window_start) == last, "the slot's last height");
  pv::require(v8::slot_last_height(last) == last, "read from inside the slot");
}

// One challenge per slot in expectation, over a recorded sample. The whole
// sample is evaluated — 400 seats at 1,200 heights — because the recorded count
// is the claim and a sampled sample would not reproduce it.
void verify_rate(const pv::Values& values) {
  const auto window_start = v8::kCycleBlocks * kMeasuredWindow;
  std::uint64_t selected = 0;
  for (std::uint64_t offset = 0; offset < v8::kSlotBlocks; ++offset) {
    for (std::uint32_t seat = 0; seat < kSampleSeats; ++seat) {
      const auto hit = v8::is_selected(kBeacon, seat, window_start + offset);
      pv::require(hit.has_value(), "the selection predicate derives");
      if (*hit) ++selected;
    }
  }
  pv::require(kSampleSeats == expect_number(values, "selection.sample.seats"),
              "the recorded sample size");
  pv::require(selected == expect_number(values, "selection.sample.selected_in_one_slot"),
              "the recorded number selected in one slot");
  pv::require(std::max(selected, std::uint64_t{kSampleSeats}) -
                      std::min(selected, std::uint64_t{kSampleSeats}) <=
                  kSampleSeats / 2,
              "the sample is within half of one challenge per seat");
  expect_true(values, "selection.sample.is_within_half_of_one_per_seat");

  pv::require(v8::kChallengePeriodBlocks ==
                  expect_number(values, "selection.period_equals_the_slot"),
              "the challenge period");
  pv::require(v8::kChallengePeriodBlocks == v8::kSlotBlocks,
              "the period is the slot length");
  expect_true(values, "selection.period_is_the_slot_length");
}

}  // namespace

void verify_selection(const pv::Values& values) {
  verify_preimage(values);
  verify_exclusion(values);
  verify_rate(values);
}

}  // namespace economy_v8_fixture
