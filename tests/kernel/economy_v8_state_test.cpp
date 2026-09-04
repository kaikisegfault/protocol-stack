// The two state entries version eight adds: their numbers, their widths, their
// keys, and everything a decoder refuses.
//
// Every refusal here is produced by a live call rather than asserted, which is
// what makes the pad rule a property of the kernel rather than of a comment.
// **The pad rule is version eight's own**: ADR 0056 records that version seven
// does not state it for the cycle assignment's bitmap, so the assignment
// record's older laxity is deliberately left alone and this record's is not.

#include "economy_v8_fixture.hpp"

namespace economy_v8_fixture {
namespace {

constexpr std::uint8_t kOpenChallenge = 18;
constexpr std::uint8_t kSeatWindow = 19;
// Version seven's fourteen assigned entry kinds and its three retired numbers,
// neither of which contains 18 or 19.
constexpr std::uint8_t kCarried[] = {1, 2, 3, 4, 5, 6, 8, 10, 12, 13, 14, 15, 16, 17};
constexpr std::uint8_t kRetired[] = {7, 9, 11};

void verify_entry_space(const pv::Values& values, const pv::Values& carried) {
  pv::require(expect_number(values, "state.open_challenge.kind") == kOpenChallenge,
              "the open challenge entry kind");
  pv::require(expect_number(values, "state.seat_window.kind") == kSeatWindow,
              "the seat window entry kind");

  for (const auto kind : {kOpenChallenge, kSeatWindow}) {
    const std::string name =
        kind == kOpenChallenge ? "open_challenge" : "seat_window";
    const auto key_width = v8::entry_key_bytes(kind);
    const auto value_width = v8::entry_value_bytes(kind);
    pv::require(key_width && value_width, "the added entry kind is assigned");
    pv::require(*key_width == expect_size(values, "state." + name + ".key_bytes"),
                "the added entry's key width");
    pv::require(*value_width == expect_size(values, "state." + name + ".value_bytes"),
                "the added entry's value width");
  }

  pv::require(hex(v8::open_challenge_key(29'000, kProbeSeat)) ==
                  expect_text(values, "state.open_challenge.key"),
              "the recorded open challenge key");
  pv::require(hex(v8::seat_window_key(1, kProbeSeat)) ==
                  expect_text(values, "state.seat_window.key"),
              "the recorded seat window key");

  // Neither number was ever assigned, which is checked against version seven's
  // own accepted file rather than against this kernel's opinion of it: the file
  // records fourteen assigned kinds and the three retired numbers, and 18 and
  // 19 are in neither list.
  pv::require(expect_size(carried, "state.entry_kind_count") == std::size(kCarried),
              "version seven's assigned entry kind count");
  pv::require(expect_text(carried, "state.retired_entry_kinds") == "7,9,11",
              "version seven's three retired entry kinds");
  for (const auto kind : kCarried) {
    pv::require(kind != kOpenChallenge && kind != kSeatWindow,
                "an added kind reuses an assigned one");
    // And the carried widths did not move under the copy.
    const auto prefix = "state.kind" + std::to_string(kind) + ".";
    const auto key_width = v8::entry_key_bytes(kind);
    pv::require(key_width && *key_width == expect_size(carried, prefix + "key_bytes"),
                "a carried entry key width moved");
  }
  for (const auto kind : kRetired) {
    pv::require(kind != kOpenChallenge && kind != kSeatWindow,
                "an added kind reuses a retired one");
    pv::require(!v8::is_entry_kind(kind), "a retired entry kind is assigned");
    pv::require(v8::is_retired_entry_kind(kind), "a retired entry kind is retired");
  }
  expect_true(values, "state.neither_kind_was_ever_assigned");
  expect_true(values, "state.no_retired_entry_kind_is_reused");
}

// A helper that turns a refusal into a value, so a probe that made a refusal
// disappear fails a check rather than crashing the run.
bool refuses_window(std::uint32_t credited, std::uint32_t disputed) {
  return !v8::seat_window_value({credited, disputed}).has_value();
}

void verify_entry_refusals(const pv::Values& values) {
  pv::require(!v8::decode_open_challenge_value(v8::Bytes{2}).has_value(),
              "an open challenge state of two");
  expect_true(values, "state.open_challenge.refuses_state_two");
  for (const std::uint8_t state : {v8::kChallengeOutstanding, v8::kChallengeAnswered}) {
    const auto decoded = v8::decode_open_challenge_value(v8::Bytes{state});
    pv::require(decoded && *decoded == state, "an accepted open challenge state");
  }
  expect_true(values, "state.open_challenge.accepts_zero_and_one");

  const std::uint32_t pad_bit = 1U << v8::kSlotsPerWindow;
  pv::require(refuses_window(pad_bit, 0), "a credited pad bit");
  expect_true(values, "state.seat_window.refuses_a_credited_pad_bit");
  pv::require(refuses_window(v8::kSlotBitmapMask, pad_bit), "a disputed pad bit");
  expect_true(values, "state.seat_window.refuses_a_disputed_pad_bit");
  pv::require(refuses_window(0b1110, 0b0001), "a dispute of an uncredited slot");
  expect_true(values, "state.seat_window.refuses_a_dispute_of_an_uncredited_slot");
  pv::require(!v8::decode_seat_window_value(v8::Bytes(7, 0)).has_value(),
              "a seat window value one octet short");
  expect_true(values, "state.seat_window.refuses_a_short_value");

  // The same three rules on the way back in, because a decoder that trusted the
  // encoder would accept a record written by something else.
  const auto pad_value = v8::Bytes{0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00};
  pv::require(!v8::decode_seat_window_value(pad_value).has_value(),
              "a decoded credited pad bit");

  // The economy tree refuses the same entries, which is a separate claim: a
  // width check alone would let a root be taken over a state no transition
  // could reach.
  auto rooted = [](v8::Bytes key, v8::Bytes value) {
    return v8::economy_root({{std::move(key), std::move(value)}}).has_value();
  };
  auto short_key = v8::Bytes{kOpenChallenge};
  short_key.resize(12, 0);
  pv::require(!rooted(short_key, v8::Bytes{0}), "a wrong-width key");
  expect_true(values, "state.entry_shape.refuses_a_wrong_width_key");
  auto retired_key = v8::Bytes{7};
  retired_key.resize(9, 0);
  pv::require(!rooted(retired_key, v8::Bytes(8, 0)), "a retired entry kind");
  expect_true(values, "state.entry_shape.refuses_a_retired_kind");
  pv::require(!rooted(v8::open_challenge_key(1, 1), v8::Bytes{2}),
              "an open challenge value of two");
  expect_true(values, "state.entry_shape.checks_the_open_challenge_value");
  // The positive control, so the three refusals above are about their subjects
  // rather than about the tree refusing everything.
  pv::require(rooted(v8::open_challenge_key(1, 1), v8::Bytes{1}),
              "a well-formed open challenge entry");
}

void verify_absent_record(const pv::Values& values) {
  const auto absent = v8::full_seat_window();
  pv::require(absent.credited == expect_number(values, "state.seat_window.absent_reads_credited"),
              "an absent record reads as fully credited");
  pv::require(absent.disputed == 0, "and with nothing disputed");
  pv::require(v8::uptime_seconds(absent) ==
                  expect_number(values, "state.seat_window.absent_uptime_seconds"),
              "an absent record's uptime");
  pv::require(v8::credited_slots(absent) == v8::kSlotsPerWindow,
              "an absent record is a full window");
  expect_true(values, "state.seat_window.absent_is_a_full_window");

  const auto value = v8::seat_window_value(absent);
  pv::require(value.has_value(), "a full record encodes");
  pv::require(hex(*value) ==
                  expect_text(values, "state.seat_window.value_of_a_full_record"),
              "the recorded value of a full record");
  const auto decoded = v8::decode_seat_window_value(*value);
  pv::require(decoded && *decoded == absent, "and it round-trips");
}

// A dispute subtracts, and the subtraction is the codec's arithmetic rather
// than the ledger's.
//
// **Every record above has an empty `disputed` bitmap**, so nothing there
// distinguishes `popcount(credited & ~disputed)` from `popcount(credited)`. The
// figures the two disagree about are recorded in the containment and kind-21
// vector groups, which need a ledger and are M3.13o's; what belongs here is the
// arithmetic itself, derived from this version's own constants.
void verify_disputed_record() {
  auto record = v8::full_seat_window();
  record.disputed = 1U;
  pv::require(v8::credited_slots(record) == v8::kSlotsPerWindow - 1,
              "one dispute costs one slot");
  pv::require(v8::uptime_seconds(record) ==
                  (v8::kSlotsPerWindow - 1) * v8::kSlotSeconds,
              "and one slot of seconds");
  // `credited` is not edited by a dispute, which is what keeps the containment
  // argument checkable against the seat's own evidence.
  pv::require(record.credited == v8::kSlotBitmapMask, "credited is unchanged");

  const auto value = v8::seat_window_value(record);
  pv::require(value.has_value(), "a disputed record encodes");
  const auto decoded = v8::decode_seat_window_value(*value);
  pv::require(decoded && *decoded == record, "and it round-trips");

  // The containment boundary, stated as arithmetic: a seat credited for every
  // slot still meets its cycle after a maximal dispute, because the cap is the
  // founder-directed grace allowance. The figure itself is
  // `test-vectors/economy-transition-v3.txt`'s activity threshold and the
  // ledger's to assert against a chain.
  auto maximal = v8::full_seat_window();
  maximal.disputed = (1U << v8::kDisputeCapSlotsPerSeat) - 1U;
  pv::require(v8::credited_slots(maximal) ==
                  v8::kSlotsPerWindow - v8::kDisputeCapSlotsPerSeat,
              "a maximal dispute costs exactly the cap");
  pv::require(v8::uptime_seconds(maximal) ==
                  (v8::kSlotsPerWindow - v8::kDisputeCapSlotsPerSeat) * v8::kSlotSeconds,
              "and the seconds follow from the slots");

  // A slot may be voided once. The cap counts bits, so a record already holding
  // the cap and one more is representable and the ledger refuses it; what the
  // codec fixes is that the bits are distinct positions.
  auto overlapping = v8::full_seat_window();
  overlapping.disputed = 0b11U;
  pv::require(v8::credited_slots(overlapping) == v8::kSlotsPerWindow - 2,
              "two disputed slots cost two");
}

}  // namespace

void verify_state(const pv::Values& values, const pv::Values& carried_seven) {
  verify_entry_space(values, carried_seven);
  verify_entry_refusals(values);
  verify_absent_record(values);
  verify_disputed_record();
}

}  // namespace economy_v8_fixture
