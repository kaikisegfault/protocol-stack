// The version-seven economy state surface: one entry kind retired, one added,
// one record extended, and the storage those three changes cost.
//
// Every width here is compared against `test-vectors/economy-transition-v7.txt`,
// which derives its own side from the specification's field tables rather than
// from the model's encoders, so a width that moved in the kernel alone fails.

#include "economy_v7_fixture.hpp"

namespace economy_v7_fixture {
namespace {

// The fourteen assigned entry kinds, and the three that are permanently not.
constexpr std::uint8_t kAssigned[] = {1, 2, 3, 4, 5, 6, 8, 10, 12, 13, 14, 15, 16, 17};
constexpr std::uint8_t kRetired[] = {7, 9, 11};

void verify_entry_kinds(const pv::Values& values) {
  pv::require(std::size(kAssigned) == expect_size(values, "state.entry_kind_count"),
              "fourteen assigned entry kinds");
  pv::require(expect_text(values, "state.retired_entry_kinds") == "7,9,11",
              "the three retired entry kinds");

  for (const auto kind : kAssigned) {
    const auto prefix = "state.kind" + std::to_string(kind) + ".";
    const auto key_width = v7::entry_key_bytes(kind);
    pv::require(key_width.has_value(), "an assigned entry kind has a key width");
    pv::require(*key_width == expect_size(values, prefix + "key_bytes"),
                "entry key width");
    const auto value_width = v7::entry_value_bytes(kind);
    if (kind == static_cast<std::uint8_t>(v7::Entry::cycle_assignment)) {
      // The one variable-width value: its width follows from its own recorded
      // bit count rather than from a table, so the table declines to answer.
      pv::require(!value_width.has_value(),
                  "the cycle assignment is the one variable-width value");
      continue;
    }
    pv::require(value_width.has_value(), "a fixed-width value");
    pv::require(*value_width == expect_size(values, prefix + "value_bytes"),
                "entry value width");
  }

  for (const auto kind : kRetired) {
    pv::require(v7::is_retired_entry_kind(kind) && !v7::is_entry_kind(kind),
                "a retired entry kind is not an entry kind");
  }
  // Entry kind 7 is version seven's own retirement, and it is the one a reader
  // most plausibly associates with a live meaning: it held the ten per-channel
  // carries in every version from two through six.
  expect_true(values, "state.carry_entry_is_retired");
  expect_true(values, "state.carry_entry_is_not_assigned");
  expect_true(values, "state.retired_kinds_are_never_reused");
  pv::require(!v7::is_entry_kind(0) && !v7::is_entry_kind(18),
              "the assigned entry range is closed at both ends");
}

void verify_recovery_pool(const pv::Values& values) {
  pv::require(expect_number(values, "state.recovery_pool.kind") ==
                  static_cast<std::uint8_t>(v7::Entry::recovery_pool),
              "the recovery pool's entry kind");
  pv::require(expect_text(values, "state.recovery_pool.legs") == "0,1,2,3,4",
              "the five Founder Node legs, in the accepted manifest's order");

  const auto key = v7::recovery_pool_key();
  pv::require(key.size() == expect_size(values, "state.recovery_pool.key_bytes"),
              "the recovery pool key width");
  pv::require(hex(key) == expect_text(values, "state.recovery_pool.key_hex"),
              "the recovery pool key");
  const auto empty = v7::recovery_pool_value({});
  pv::require(empty.size() == expect_size(values, "state.recovery_pool.value_bytes"),
              "the recovery pool value width");
  pv::require(key.size() + empty.size() ==
                  expect_size(values, "state.recovery_pool.entry_bytes"),
              "the recovery pool entry width");

  // The five legs are distinguishable in the bytes, so a transposition is a
  // different value rather than one that happens to encode the same.
  v7::RecoveryPool distinct{};
  for (std::size_t index = 0; index < v7::kRecoveryPoolLegs; ++index) {
    distinct[index] = std::uint64_t{1} << (8 * index);
  }
  const auto ordered = v7::recovery_pool_value(distinct);
  pv::require(hex(ordered) ==
                  expect_text(values, "state.recovery_pool.ordered_value_hex"),
              "the ordered recovery pool value");
  const auto decoded = v7::decode_recovery_pool_value(ordered);
  pv::require(decoded.has_value() && *decoded == distinct,
              "the recovery pool value round trips");
  expect_true(values, "state.recovery_pool.value_round_trips");

  auto swapped = distinct;
  std::swap(swapped[0], swapped[1]);
  pv::require(v7::recovery_pool_value(swapped) != ordered,
              "two transposed legs encode differently");
  expect_true(values, "state.recovery_pool.transposed_legs_encode_differently");

  pv::require(!v7::decode_recovery_pool_value(
                   std::span<const std::uint8_t>(ordered.data(), ordered.size() - 1))
                   .has_value(),
              "a short recovery pool value is refused");
  expect_true(values, "state.recovery_pool.a_short_value_is_refused");
}

// A record with one bit of bitmap, carrying the tool's own fixture figures, so
// the recorded value_hex is a constraint on every field offset at once.
v7::CycleAssignment fixture_record(std::uint32_t winner_count,
                                   const v7::RecoveryPool& absorbed) {
  v7::CycleAssignment record;
  record.share_per_winner_atomic = winner_count == 0 ? 0 : 11;
  record.reallocated_count = 2;
  record.winner_count = winner_count;
  record.in_scope_count = 4;
  record.bitmap_bits = 8;
  record.pool_absorbed = absorbed;
  record.accrued_bitmap = winner_count == 0 ? v7::Bytes{0x00} : v7::Bytes{0x81};
  record.winner_bitmap = winner_count == 0 ? v7::Bytes{0x00} : v7::Bytes{0x41};
  return record;
}

void verify_cycle_assignment(const pv::Values& values) {
  pv::require(v7::kCycleAssignmentFixedBytes ==
                  expect_size(values, "state.cycle_assignment.fixed_value_bytes"),
              "the extended fixed part");
  pv::require(v7::kCycleAssignmentFixedBytes == 24 + 8 * v7::kRecoveryPoolLegs,
              "which is version three's twenty-four plus the five legs");
  expect_true(values, "state.cycle_assignment.fixed_value_bytes_grew_by_five_legs");

  v7::RecoveryPool absorbed{};
  for (std::size_t index = 0; index < v7::kRecoveryPoolLegs; ++index) {
    absorbed[index] = 100 + index;
  }
  const auto value = v7::cycle_assignment_value(fixture_record(3, absorbed));
  pv::require(value.has_value(), "the extended record encodes");
  pv::require(value->size() ==
                  expect_size(values, "state.cycle_assignment.value_bytes_at_eight_bits"),
              "the record width at eight bits");
  pv::require(hex(*value) == expect_text(values, "state.cycle_assignment.value_hex"),
              "the extended record's bytes");

  // The five new fields sit after `bitmap_bits`, so every fixed-width field
  // stays contiguous ahead of the variable-length tail. Reading each recorded
  // offset out of the encoded bytes is what checks that rather than asserting it.
  for (std::size_t index = 0; index < v7::kRecoveryPoolLegs; ++index) {
    const auto offset = expect_size(
        values, "state.cycle_assignment.offset.pool_absorbed_atomic_" +
                    std::to_string(index));
    pv::require(offset == 24 + 8 * index, "the absorbed field offsets");
    std::uint64_t read = 0;
    for (std::size_t octet = 0; octet < 8; ++octet) {
      read = (read << 8U) | (*value)[offset + octet];
    }
    pv::require(read == absorbed[index], "each absorbed amount sits at its offset");
  }

  const auto decoded = v7::decode_cycle_assignment_value(*value);
  pv::require(decoded.has_value() && decoded->pool_absorbed == absorbed,
              "the extended record round trips");
  expect_true(values, "state.cycle_assignment.round_trips");

  // A cycle with no winner absorbs nothing, so a record carrying a nonzero
  // absorbed amount at a zero winner count describes value divided by nobody.
  // Both directions refuse it: the encoder refuses to write a state entry no
  // settlement could produce, and the decoder refuses to read one off a wire the
  // encoder does not control.
  pv::require(!v7::cycle_assignment_value(fixture_record(0, absorbed)).has_value(),
              "an absorbed amount with no winner is refused by the encoder");
  expect_true(values, "state.cycle_assignment.absorbed_without_a_winner_is_refused");
  const auto zeroed = v7::cycle_assignment_value(fixture_record(0, {}));
  pv::require(zeroed.has_value() &&
                  zeroed->size() == v7::kCycleAssignmentFixedBytes + 2,
              "no winner and no absorption is accepted");
  expect_true(values, "state.cycle_assignment.no_winner_and_no_absorption_is_accepted");

  auto mutated = *value;
  for (std::size_t octet = 0; octet < 4; ++octet) mutated[12 + octet] = 0;
  pv::require(!v7::decode_cycle_assignment_value(mutated).has_value(),
              "a decoded absorption with no winner is refused");
  expect_true(values,
              "state.cycle_assignment.a_decoded_absorption_without_a_winner_is_refused");
}

void verify_entry_shapes(const pv::Values& values) {
  // Shapes no transition could have written, each refused rather than hashed,
  // because a root cannot signal any of them.
  v7::Bytes carry_key{7, 0};
  pv::require(!v7::economy_root({{carry_key, v7::Bytes(8, 0)}}).has_value(),
              "a retired kind in the map is refused");
  expect_true(values, "state.a_retired_kind_in_the_map_is_refused");
  pv::require(!v7::economy_root({{{200}, {}}}).has_value(),
              "an unassigned kind in the map is refused");
  expect_true(values, "state.an_unassigned_kind_in_the_map_is_refused");
  pv::require(!v7::economy_root({{v7::recovery_pool_key(), v7::Bytes(39, 0)}})
                   .has_value(),
              "a pool value of the wrong width is refused");
  expect_true(values, "state.a_pool_value_of_the_wrong_width_is_refused");

  const v7::EconomyEntry pool{v7::recovery_pool_key(), v7::recovery_pool_value({})};
  pv::require(v7::economy_root({pool}).has_value(), "a well-formed entry hashes");
  pv::require(!v7::economy_root({pool, pool}).has_value(), "a duplicated key");
}

void verify_storage(const pv::Values& values) {
  auto entry = [](v7::Entry kind) {
    const auto number = static_cast<std::uint8_t>(kind);
    return *v7::entry_key_bytes(number) + *v7::entry_value_bytes(number);
  };
  // Ten entries of two key octets and eight value octets leave; one entry of one
  // key octet and forty value octets arrives.
  const std::size_t removed = 10 * (2 + 8);
  const auto added = entry(v7::Entry::recovery_pool);
  pv::require(removed == expect_size(values, "storage.carry_bytes_removed"),
              "the carry entries removed");
  pv::require(added == expect_size(values, "storage.recovery_pool_bytes_added"),
              "the recovery pool entry added");
  pv::require(removed - added ==
                  expect_size(values, "storage.fixed_entry_bytes_saved"),
              "the fixed entry bytes saved");

  const auto record =
      *v7::entry_key_bytes(static_cast<std::uint8_t>(v7::Entry::cycle_assignment)) +
      v7::kCycleAssignmentFixedBytes +
      2 * v7::bitmap_bytes(v7::kFounderSeatCapacity);
  pv::require(record ==
                  expect_size(values, "storage.cycle_assignment_bytes_at_capacity"),
              "a cycle assignment at the seat capacity");
  const auto growth = 8 * v7::kRecoveryPoolLegs;
  pv::require(growth ==
                  expect_size(values, "storage.cycle_assignment_growth_at_capacity"),
              "what the five absorbed amounts add to every record");
  pv::require(growth * 500 < record - growth,
              "the growth is under one part in five hundred");
  expect_true(values,
              "storage.cycle_assignment_growth_is_under_one_part_in_five_hundred");
}

}  // namespace

void verify_state(const pv::Values& values) {
  verify_entry_kinds(values);
  verify_recovery_pool(values);
  verify_cycle_assignment(values);
  verify_entry_shapes(values);
  verify_storage(values);
}

}  // namespace economy_v7_fixture
