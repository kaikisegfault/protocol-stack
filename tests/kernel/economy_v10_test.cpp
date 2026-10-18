// The version-ten codec, checked against the recorded vectors.
//
// This is requirement 9 for the surface the codec covers: the C++
// implementation and the independent Python model must reproduce one fixed
// file.
//
// **`test-vectors/economy-transition-v10.txt` holds 107 vectors and this target
// reproduces the ones a codec can reach.** The rest describe the Python
// package's own surface, or what a genesis writes to a ledger, which is the
// execution slice's. The coverage guard below names every one of them and what
// owes it, so the slice boundary is a check rather than a description.
//
// **Four carried files, because version ten records only what version ten
// changes.** The surface it inherits stays fixed by the files that accepted it:
// `test-vectors/economy-transition-v9.txt` fixes the kind and four entries
// version nine added, its chain identity, its roots, and its header;
// `economy-transition-v8.txt` the two kinds, two entries, and twelve codes
// version eight added; `economy-transition-v7.txt` the entry table version eight
// carried; and `economy-transition-v6.txt` the envelope table, the first
// thirty-three codes, and the bytes version one accepted for a transfer.
// Re-recording any of them under a version-ten name would produce a file that
// agrees with the first and says nothing.
//
// Two further files are read as third sources: the manifest, because the supply
// limit and the manifest digest are founder-directed figures rather than
// derived ones, and `test-vectors/protocol-primitives-v1.txt`, because the
// accounts tree inside the state root is version one's construction entry for
// entry.
//
// The checks are split by subject across three translation units — version,
// state, kinds. This one is the entry point and the coverage guard.

#include "economy_v10_carried.hpp"

#include <array>
#include <iostream>
#include <string_view>

namespace {

namespace pv = protocol_vectors;

// Every recorded vector this target does not consult, with what owes it. A
// prefix covers a whole section; an exact key covers one.
//
// **Each entry must match at least one unconsulted key**, so an entry that stops
// applying — because a later slice consulted its keys, or because the section
// was renamed — fails here instead of lingering as a stale exemption. That is
// the half of the guard that keeps the boundary honest; the other half is that a
// key matching no entry and consulted by nothing fails too.
enum class Match { prefix, exact };

struct Deferred {
  std::string_view pattern;
  Match match;
  std::string_view owed_to;
};

constexpr std::array<Deferred, 2> kDeferred{{
    // The partition of version nine's Python surface into carried, revised,
    // withdrawn, and replaced. It is a claim about
    // `simulation/economy_transition_v10` and is checked by that package's own
    // verifier; this kernel's equivalent is that every inherited width, scheme,
    // and name is pinned against the accepted file that recorded it.
    {"carryover.", Match::prefix, "tools/economy-transition-v10-vectors/verify.py"},
    // What genesis writes is the ledger's, because `open_ledger` is what writes
    // it; this target builds the sixteen entries by hand to take roots over, and
    // asking that list whether it holds a registry entry would be vacuous.
    {"genesis.writes_no_registry_entry", Match::exact, "economy_v10_execution_tests"},
}};

}  // namespace

namespace economy_v10_fixture {

void verify_coverage(const pv::Values& values) {
  std::array<bool, kDeferred.size()> matched{};
  for (const auto& [key, value] : values) {
    (void)value;
    // Copied out of the structured binding because C++20 does not permit a
    // lambda to capture one, and the two compilers disagree about it.
    const std::string& name = key;
    if (consulted().contains(name)) continue;
    bool excused = false;
    for (std::size_t index = 0; index < kDeferred.size(); ++index) {
      const auto& entry = kDeferred[index];
      const bool hit = entry.match == Match::prefix
                           ? name.rfind(entry.pattern, 0) == 0
                           : name == entry.pattern;
      if (!hit) continue;
      matched[index] = true;
      excused = true;
      break;
    }
    pv::require(excused, "vector " + name +
                             " was never consulted and is owed to nobody");
  }
  for (std::size_t index = 0; index < kDeferred.size(); ++index) {
    pv::require(matched[index],
                "the deferral of " + std::string(kDeferred[index].pattern) +
                    " to " + std::string(kDeferred[index].owed_to) +
                    " matches no unconsulted vector");
  }
}

}  // namespace economy_v10_fixture

int main(int argc, char** argv) {
  namespace fixture = economy_v10_fixture;
  try {
    pv::require(argc == 8,
                "usage: economy_v10_codec_tests V10_VECTORS MANIFEST V9_VECTORS "
                "V8_VECTORS V7_VECTORS V6_VECTORS PRIMITIVES");
    pv::require(sodium_init() >= 0, "libsodium initialization");
    const auto values = pv::load_values(argv[1]);
    const auto manifest = pv::load_values(argv[2]);
    const auto nine = pv::load_values(argv[3]);
    const auto eight = pv::load_values(argv[4]);
    const auto seven = pv::load_values(argv[5]);
    const auto six = pv::load_values(argv[6]);
    const auto primitives = pv::load_values(argv[7]);
    const fixture::Carried carried{six, seven, eight, nine};

    // The one guard that belongs to no vector group and to the port itself:
    // `src/v10/`'s tree is version nine's copied, so it is required to
    // reproduce the accepted M1 accounts tree root over the accepted M1
    // accounts. A tree that drifted in the copy would still produce
    // self-consistent version-ten roots and would fail here.
    fixture::verify_accounts_tree(primitives);

    fixture::verify_version(values, carried, manifest);
    fixture::verify_state(values, carried);
    fixture::verify_kinds(values, carried);
    fixture::verify_coverage(values);

    std::cout << "C++ economy transition v10 codec: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "C++ economy transition v10 codec: failed: " << error.what()
              << '\n';
    return 1;
  }
}
