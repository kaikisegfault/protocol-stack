#pragma once

// Version eight's surface, reconstructed from the accepted files that recorded
// it.
//
// **The version-eight kernel is deleted (ADR 0092), so these files are the only
// record of version eight left to C++.** Every cross-version check this suite
// used to execute against `protocol::v8` is pinned here instead, which is the
// rule ADR 0070 recorded: a pin against a live kernel dies with the kernel, and
// a pin against an accepted file does not. The claims only an implementation
// can answer — that version eight *refuses* a version-nine artifact — are owed to
// `tools/economy-transition-v9-vectors/verify.py`, which runs them against the
// version-eight Python model, and the coverage guard names them.
//
// Version eight's surface is version six's envelope table and result codes,
// version seven's entry table, and the additions version eight's own two files
// record. **Version seven assigned no transaction kind and no result code, and
// nothing here assumes it.** Each reconstructed table is compared with version
// nine's own, which must equal it plus exactly what version nine adds, so an
// assignment a predecessor made and this reconstruction missed fails there.

#include "economy_v9_fixture.hpp"

#include <set>
#include <string>

namespace economy_v9_fixture {

struct Carried {
  const pv::Values& six;              // economy-transition-v6.txt
  const pv::Values& seven;            // economy-transition-v7.txt
  const pv::Values& eight;            // economy-transition-v8.txt
  const pv::Values& eight_execution;  // economy-transition-v8-execution.txt
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

// Version six's fourteen transaction kinds and version eight's two.
inline std::set<std::uint8_t> version_eight_transaction_kinds(
    const Carried& carried) {
  auto kinds = numbered_keys(carried.six, "envelope.kind", ".name");
  pv::require(kinds.size() == std::stoull(carried.six.at("envelope.kind_count")),
              "every kind version six counted is named in its file");
  for (const char* key : {"kind.challenge_response", "kind.file_dispute"}) {
    pv::require(kinds.insert(recorded_octet(carried.eight, key)).second,
                "version eight's two kinds were never assigned before it");
  }
  return kinds;
}

// Version seven's fourteen entry kinds and version eight's two.
inline std::set<std::uint8_t> version_eight_entry_kinds(const Carried& carried) {
  auto kinds = numbered_keys(carried.seven, "state.kind", ".name");
  pv::require(
      kinds.size() == std::stoull(carried.seven.at("state.entry_kind_count")),
      "every entry kind version seven counted is named in its file");
  for (const char* key : {"state.open_challenge.kind", "state.seat_window.kind"}) {
    pv::require(kinds.insert(recorded_octet(carried.eight, key)).second,
                "version eight's two entry kinds were never assigned before it");
  }
  return kinds;
}

// An entry kind's widths as version seven's table records them, which version
// eight carried unchanged for every kind it did not add.
inline std::size_t version_seven_width(const Carried& carried, std::uint8_t kind,
                                       const std::string& which) {
  return std::stoull(carried.seven.at("state.kind" + std::to_string(kind) + "." +
                                      which));
}

// Codes 0 through 32 are named in version six's file and 33 through 44 in
// version eight's, and the two together must be the space version eight
// counted, contiguous from zero.
inline std::size_t version_eight_code_count(const Carried& carried) {
  const auto six = std::stoull(carried.six.at("codes.count"));
  const auto added = numbered_keys(carried.eight, "result.added.", "");
  const auto count = std::stoull(carried.eight.at("result.code_count"));
  pv::require(!added.empty() && *added.begin() == six &&
                  *added.rbegin() + 1U == count && six + added.size() == count,
              "version eight's codes extend version six's contiguously");
  return count;
}

inline std::string version_eight_code_name(const Carried& carried,
                                           std::uint8_t code) {
  if (code < std::stoull(carried.six.at("codes.count"))) {
    return carried.six.at("codes.code" + std::to_string(code));
  }
  return carried.eight.at("result.added." + std::to_string(code));
}

}  // namespace economy_v9_fixture
