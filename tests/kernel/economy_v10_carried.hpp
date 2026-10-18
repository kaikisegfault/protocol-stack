#pragma once

// Version nine's surface, reconstructed from the accepted files that recorded
// it.
//
// **The version-nine kernel still compiles beside this one, and this suite
// does not link against it.** ADR 0092 found nineteen cross-version checks that
// the version-nine suite had executed against the live version-eight kernel,
// and each had to be re-pinned when that kernel was deleted: a pin against a
// live kernel dies with the kernel, and a pin against an accepted file does not.
// The version-nine deletion that ends this migration (ADR 0104) therefore costs
// these checks nothing.
//
// Version nine's surface is version six's envelope table and first thirty-three
// codes, version seven's entry table, the two kinds, two entries, and twelve
// codes version eight's file adds, and the kind, four entries, and widened pool
// version nine's file adds. Each reconstructed table is compared with version
// ten's own, which must equal it plus exactly what version ten adds, so an
// assignment a predecessor made and this reconstruction missed fails there.

#include "economy_v10_fixture.hpp"

#include <map>
#include <optional>
#include <set>
#include <string>

namespace economy_v10_fixture {

struct Carried {
  const pv::Values& six;    // economy-transition-v6.txt
  const pv::Values& seven;  // economy-transition-v7.txt
  const pv::Values& eight;  // economy-transition-v8.txt
  const pv::Values& nine;   // economy-transition-v9.txt
};

// Every `N` of a `<prefix>N<suffix>` key, with `N` decimal.
inline std::set<std::uint8_t> numbered_keys(const pv::Values& values,
                                            const std::string& prefix,
                                            const std::string& suffix) {
  std::set<std::uint8_t> found;
  for (const auto& [key, value] : values) {
    (void)value;
    if (key.size() <= prefix.size() + suffix.size() || !key.starts_with(prefix) ||
        !key.ends_with(suffix)) {
      continue;
    }
    const auto digits =
        key.substr(prefix.size(), key.size() - prefix.size() - suffix.size());
    if (digits.find_first_not_of("0123456789") != std::string::npos) continue;
    const auto number = std::stoul(digits);
    pv::require(number <= 255, "a recorded kind number fits in an octet");
    found.insert(static_cast<std::uint8_t>(number));
  }
  return found;
}

inline std::uint8_t recorded_octet(const pv::Values& values,
                                   const std::string& key) {
  const auto number = std::stoul(values.at(key));
  pv::require(number <= 255, key + " fits in an octet");
  return static_cast<std::uint8_t>(number);
}

inline std::size_t recorded_size(const pv::Values& values, const std::string& key) {
  return static_cast<std::size_t>(std::stoull(values.at(key)));
}

struct RecordedKind {
  std::size_t body_bytes = 0;
  std::uint8_t scheme = 0;
};

// Version six's fourteen transaction kinds, version eight's two, and version
// nine's one, with the body width and scheme each file recorded.
inline std::map<std::uint8_t, RecordedKind> version_nine_kinds(
    const Carried& carried) {
  std::map<std::uint8_t, RecordedKind> kinds;
  for (const auto kind : numbered_keys(carried.six, "envelope.kind", ".name")) {
    const auto prefix = "envelope.kind" + std::to_string(kind);
    kinds[kind] = {recorded_size(carried.six, prefix + ".body_bytes"),
                   recorded_octet(carried.six, prefix + ".scheme")};
  }
  pv::require(kinds.size() == recorded_size(carried.six, "envelope.kind_count"),
              "every kind version six counted is named in its file");
  pv::require(carried.eight.at("kind.both_are_scheme_one") == "true",
              "version eight records both of its kinds as scheme 1");
  for (const char* name : {"kind.challenge_response", "kind.file_dispute"}) {
    const auto kind = recorded_octet(carried.eight, name);
    const auto added =
        kinds.emplace(kind, RecordedKind{recorded_size(carried.eight,
                                                       std::string(name) +
                                                           ".body_bytes"),
                                         v10::kSchemeSigner});
    pv::require(added.second, "version eight's kinds were never assigned before it");
  }
  const auto pool = recorded_octet(carried.nine, "kind22.transaction_kind");
  const auto added = kinds.emplace(
      pool, RecordedKind{recorded_size(carried.nine, "kind22.body_bytes"),
                         recorded_octet(carried.nine, "kind22.scheme")});
  pv::require(added.second, "version nine's kind was never assigned before it");
  pv::require(kinds.size() ==
                  recorded_size(carried.nine, "kind22.transaction_kind_count"),
              "the reconstruction holds the seventeen kinds version nine counted");
  return kinds;
}

struct RecordedEntry {
  std::size_t key_bytes = 0;
  // Absent for the cycle assignment, whose width follows from its bit count.
  std::optional<std::size_t> value_bytes;
};

// Version seven's fourteen entry kinds, version eight's two, and version nine's
// four, with the widened pool value version nine's file records.
inline std::map<std::uint8_t, RecordedEntry> version_nine_entries(
    const Carried& carried) {
  std::map<std::uint8_t, RecordedEntry> entries;
  for (const auto kind : numbered_keys(carried.seven, "state.kind", ".name")) {
    const auto prefix = "state.kind" + std::to_string(kind);
    RecordedEntry entry{recorded_size(carried.seven, prefix + ".key_bytes"), {}};
    if (carried.seven.contains(prefix + ".value_bytes")) {
      entry.value_bytes = recorded_size(carried.seven, prefix + ".value_bytes");
    }
    entries[kind] = entry;
  }
  pv::require(
      entries.size() == recorded_size(carried.seven, "state.entry_kind_count"),
      "every entry kind version seven counted is named in its file");
  const auto add = [&entries](const pv::Values& file, const std::string& prefix) {
    const auto kind = recorded_octet(file, prefix + ".kind");
    const auto added = entries.emplace(
        kind, RecordedEntry{recorded_size(file, prefix + ".key_bytes"),
                            recorded_size(file, prefix + ".value_bytes")});
    pv::require(added.second, "a later version's entry kind was never assigned before it");
  };
  add(carried.eight, "state.open_challenge");
  add(carried.eight, "state.seat_window");
  for (const char* prefix : {"state.window_month", "state.monthly_figure",
                             "state.monthly_claim", "state.settlement_cursor"}) {
    add(carried.nine, prefix);
  }
  // The one carried entry version nine widened, checked against both files'
  // records of it before the widening is applied.
  const auto pool = static_cast<std::uint8_t>(v10::Entry::unreferred_pool);
  pv::require(carried.seven.at("state.kind" + std::to_string(pool) + ".name") ==
                  "unreferred_pool",
              "version seven's table names the pool's kind");
  pv::require(entries.at(pool).value_bytes ==
                  recorded_size(carried.nine,
                                "state.unreferred_pool.value_bytes_in_version_eight"),
              "version nine's file records the pool's earlier width");
  entries.at(pool).value_bytes =
      recorded_size(carried.nine, "state.unreferred_pool.value_bytes");
  pv::require(entries.size() == recorded_size(carried.nine, "state.entry_kind_count"),
              "the reconstruction holds the twenty entry kinds version nine counted");
  return entries;
}

// Codes 0 through 32 are named in version six's file and 33 through 44 in
// version eight's; version nine's file records that it added none.
inline std::vector<std::string> version_nine_codes(const Carried& carried) {
  const auto six = recorded_size(carried.six, "codes.count");
  const auto count = recorded_size(carried.eight, "result.code_count");
  pv::require(recorded_size(carried.nine, "codes.count") == count &&
                  carried.nine.at("codes.unchanged_from_version_eight") == "true",
              "version nine's file records version eight's code space unchanged");
  std::vector<std::string> names;
  for (std::size_t code = 0; code < count; ++code) {
    names.push_back(code < six
                        ? carried.six.at("codes.code" + std::to_string(code))
                        : carried.eight.at("result.added." + std::to_string(code)));
  }
  return names;
}

}  // namespace economy_v10_fixture
