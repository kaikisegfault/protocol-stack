// The four entry kinds version ten adds, checked against the recorded vectors.
//
// **The refusals are the substance here rather than the encodings.** A key and
// a value of the right width is what any implementation gets right; what
// distinguishes a conforming one is that a machine key written at height zero,
// a founder count of zero or above the founder limit, and a retirement at height
// zero are all refused, because each is a state no transition writes, and a
// zero count or retirement would be a second encoding of absence.
//
// **The entry table is pinned to the files that accepted version nine's.** It
// must equal that table plus exactly entry kinds 24 to 27, with every carried
// width the one its accepting file recorded, so a width the port moved by
// accident fails here by kind number.

#include "economy_v10_carried.hpp"

#include <set>
#include <string>

namespace economy_v10_fixture {
namespace {

v10::MachineKey fixture_machine_key(std::uint64_t height) {
  v10::MachineKey entry;
  entry.machine_public_key = kMachineKey;
  entry.build_digest = kBuildDigest;
  entry.registered_at_height = height;
  entry.last_met_window = 5;
  return entry;
}

// The octets of a machine key at `height`, built by hand: the encoder refuses a
// zero height, so the only way to hand the decoder one is to build it directly.
v10::Bytes machine_key_octets(std::uint64_t height) {
  v10::Bytes value(kMachineKey.begin(), kMachineKey.end());
  value.insert(value.end(), kBuildDigest.begin(), kBuildDigest.end());
  pv::append_u64(value, height);
  pv::append_u64(value, 5);
  return value;
}

v10::FounderRegistrations fixture_founder(std::uint32_t count) {
  v10::FounderRegistrations entry;
  entry.registration_window = 6;
  entry.registrations_in_window = count;
  return entry;
}

// The octets of a founder count in window 6, built by hand for the same reason:
// the encoder refuses a count of zero or above the limit.
v10::Bytes founder_octets(std::uint32_t count) {
  v10::Bytes value;
  pv::append_u64(value, 6);
  for (int shift = 24; shift >= 0; shift -= 8) {
    value.push_back(static_cast<std::uint8_t>(count >> shift));
  }
  return value;
}

void verify_widths(const pv::Values& values, const Carried& carried) {
  struct Declared {
    v10::Entry entry;
    const char* name;
  };
  const Declared declared[] = {
      {v10::Entry::machine_key, "machine_key"},
      {v10::Entry::launch_retirement, "launch_retirement"},
      {v10::Entry::machine_key_owner, "machine_key_owner"},
      {v10::Entry::founder_registrations, "founder_registrations"},
  };
  auto expected = version_nine_entries(carried);
  for (const auto& item : declared) {
    const auto kind = static_cast<std::uint8_t>(item.entry);
    const auto prefix = "widths.entry_" + std::to_string(kind);
    pv::require(expect_text(values, prefix + "_name") == item.name,
                "the entry kind's number carries its recorded name");
    pv::require(v10::is_entry_kind(kind) && !v10::is_retired_entry_kind(kind),
                "the kind is assigned and reuses no retired number");
    const auto key_bytes = v10::entry_key_bytes(kind);
    const auto value_bytes = v10::entry_value_bytes(kind);
    pv::require(key_bytes == expect_size(values, prefix + "_key"),
                "the key width is the recorded one");
    pv::require(value_bytes == expect_size(values, prefix + "_value"),
                "the value width is the recorded one");
    pv::require(expected.emplace(kind, RecordedEntry{*key_bytes, *value_bytes}).second,
                "version nine never assigned this entry kind");
  }
  // **Version ten's table is version nine's plus the four, exactly**, every
  // carried width included.
  std::size_t assigned = 0;
  for (std::uint16_t number = 0; number <= 255; ++number) {
    const auto kind = static_cast<std::uint8_t>(number);
    if (!v10::is_entry_kind(kind)) {
      pv::require(!expected.contains(kind), "every recorded entry kind is assigned");
      continue;
    }
    ++assigned;
    const auto found = expected.find(kind);
    pv::require(found != expected.end(),
                "entry kind " + std::to_string(number) + " is recorded somewhere");
    pv::require(v10::entry_key_bytes(kind) == found->second.key_bytes &&
                    v10::entry_value_bytes(kind) == found->second.value_bytes,
                "entry kind " + std::to_string(number) +
                    " keeps the widths its accepting file recorded");
  }
  pv::require(assigned == expected.size() && assigned == 24,
              "twenty-four entry kinds are assigned");
}

void verify_encodings(const pv::Values& values) {
  pv::require(hex(v10::machine_key_key(kSeat)) ==
                  expect_text(values, "state.machine_key_key"),
              "the machine-key key is the recorded one");
  const auto fixture = fixture_machine_key(3);
  const auto value = v10::machine_key_value(fixture);
  pv::require(value.has_value() &&
                  hex(*value) == expect_text(values, "state.machine_key_value"),
              "the machine-key value is the recorded one");
  pv::require(*value == machine_key_octets(3),
              "the value is laid out in the specification's field order");
  pv::require(hex(v10::launch_retirement_key()) ==
                  expect_text(values, "state.launch_retirement_key"),
              "the retirement key is the recorded one");
  const auto retirement = v10::launch_retirement_value(86'401);
  pv::require(retirement.has_value() &&
                  hex(*retirement) == expect_text(values, "state.launch_retirement_value"),
              "the retirement value is the recorded one");
  pv::require(hex(v10::machine_key_owner_key(kMachineKey)) ==
                  expect_text(values, "state.machine_key_owner_key"),
              "the owner key is the recorded one");
  pv::require(hex(v10::machine_key_owner_value(kSeat)) ==
                  expect_text(values, "state.machine_key_owner_value"),
              "the owner value is the recorded one");
  const auto owner = v10::decode_machine_key_owner_value(
      v10::machine_key_owner_value(kSeat));
  pv::require(owner == kSeat, "the owner value round-trips");
  pv::require(hex(v10::founder_registrations_key(kIdentity)) ==
                  expect_text(values, "state.founder_registrations_key"),
              "the founder key is the recorded one");
  const auto founder = v10::founder_registrations_value(fixture_founder(999));
  pv::require(founder.has_value() &&
                  hex(*founder) ==
                      expect_text(values, "state.founder_registrations_value"),
              "the founder value is the recorded one");
  pv::require(*founder == founder_octets(999),
              "the founder value is laid out in the specification's field order");
}

void verify_refusals(const pv::Values& values) {
  const auto fixture = fixture_machine_key(3);
  expect_claim(values, "state.machine_key_round_trips",
               v10::decode_machine_key_value(*v10::machine_key_value(fixture)) ==
                   fixture);
  const auto founder = fixture_founder(999);
  expect_claim(values, "state.founder_registrations_round_trips",
               v10::decode_founder_registrations_value(
                   *v10::founder_registrations_value(founder)) == founder);

  const auto limit = v10::kFounderRegistrationsPerWindow;
  const auto at_limit = v10::decode_founder_registrations_value(founder_octets(limit));
  expect_claim(values, "state.founder_registrations_admits_the_limit",
               at_limit.has_value() && at_limit->registrations_in_window == limit);
  expect_claim(values, "state.founder_registrations_refuses_a_count_above_the_limit",
               !v10::decode_founder_registrations_value(founder_octets(limit + 1)) &&
                   !v10::founder_registrations_value(fixture_founder(limit + 1)));
  expect_claim(values, "state.founder_registrations_refuses_a_zero_count",
               !v10::decode_founder_registrations_value(founder_octets(0)) &&
                   !v10::founder_registrations_value(fixture_founder(0)));
  expect_claim(values, "state.machine_key_refuses_a_zero_height",
               !v10::decode_machine_key_value(machine_key_octets(0)) &&
                   !v10::machine_key_value(fixture_machine_key(0)));
  expect_claim(values, "state.launch_retirement_refuses_zero",
               !v10::decode_launch_retirement_value(v10::Bytes(8, 0)) &&
                   !v10::launch_retirement_value(0));
  // The root is where a state's shape is judged, so the short value is handed
  // to it rather than to the decoder alone.
  expect_claim(values, "state.entry_shape_refuses_a_short_owner_value",
               !v10::economy_root(
                   {{v10::machine_key_owner_key(kMachineKey), v10::Bytes(3, 0)}}));

  // **The tree's content checks are version ten's edit to a carried file**, so
  // each is reached through the root and not only through the decoder: a root
  // over a value the decoder refuses is not taken.
  pv::require(v10::economy_root({{v10::machine_key_key(kSeat), *v10::machine_key_value(
                                                                    fixture)}})
                  .has_value(),
              "a written machine key has a root");
  pv::require(!v10::economy_root(
                  {{v10::machine_key_key(kSeat), machine_key_octets(0)}}),
              "a machine key at height zero has no root");
  pv::require(v10::economy_root({{v10::founder_registrations_key(kIdentity),
                                  *v10::founder_registrations_value(founder)}})
                  .has_value(),
              "a written founder count has a root");
  pv::require(!v10::economy_root({{v10::founder_registrations_key(kIdentity),
                                   founder_octets(limit + 1)}}),
              "a founder count over the limit has no root");
  pv::require(!v10::economy_root({{v10::founder_registrations_key(kIdentity),
                                   founder_octets(0)}}),
              "a founder count of zero has no root");
  pv::require(!v10::economy_root({{v10::launch_retirement_key(), v10::Bytes(8, 0)}}),
              "a retirement at height zero has no root");
  pv::require(v10::economy_root({{v10::launch_retirement_key(),
                                  *v10::launch_retirement_value(86'401)}})
                  .has_value(),
              "a written retirement has a root");
}

}  // namespace

void verify_state(const pv::Values& values, const Carried& carried) {
  verify_widths(values, carried);
  verify_encodings(values);
  verify_refusals(values);
}

}  // namespace economy_v10_fixture
