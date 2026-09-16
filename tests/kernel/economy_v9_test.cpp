// The version-nine codec, checked against the recorded vectors.
//
// This is requirement 11 for the surface the codec covers: the C++
// implementation and the independent Python model must reproduce fixed files.
//
// **`test-vectors/economy-transition-v9.txt` holds 239 vectors and this target
// reproduces the ones a codec can reach.** The rest need a ledger — the monthly
// settlement, the window months a chain writes, and the arithmetic over them —
// or describe the Python package's own surface. The coverage guard below names
// every one of them and what owes it, so the slice boundary is a check rather
// than a description.
//
// **Two carried files, because version nine records only what version nine
// changes.**
// The surface it inherits stays fixed by the file that accepted it:
// `test-vectors/economy-transition-v8.txt` fixes the 142-octet genesis prefix
// and the version-eight identity this one is measured against, and
// `test-vectors/economy-transition-v6.txt` fixes kind 4's body, which kind 22
// reuses. Re-recording either under a version-nine name would produce a file
// that agrees with the first and says nothing.
//
// Two further files are read as *third* sources rather than as second opinions:
// `test-vectors/calendar-v1.txt`, because the calendar is an accepted
// specification with its own recorded derivations and this kernel must reach
// them, and `test-vectors/protocol-primitives-v1.txt`, because the accounts tree
// inside the state root is version one's construction entry for entry. The
// manifest digest comes from `test-vectors/founder-economy-manifest-v3.txt`,
// because it is a founder-directed figure rather than a derived one.
//
// The checks are split by subject across four translation units — version,
// state, clock, kinds. This one is the entry point and the coverage guard.

#include "economy_v9_fixture.hpp"

#include <algorithm>
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
enum class Match { prefix, exact, contains };

struct Deferred {
  std::string_view pattern;
  Match match;
  std::string_view owed_to;
};

constexpr std::array<Deferred, 6> kDeferred{{
    // A window's month is written at its opening height and read two windows
    // later, so every attribution vector needs a chain that has executed both.
    {"attribution.", Match::prefix, "economy_v9_execution_tests"},
    // **The settlement machine's own recording, and not a chain's.** These
    // vectors are a run over a *sampled* window sequence — 0, 1, 2, 3, 4, 33,
    // 63, 155 — which is legitimate for a fixture about arithmetic and is
    // something no chain can produce: heights are consecutive and the prologue
    // runs at every window-opening height. `economy-transition-v9` says so
    // outright. The C++ kernel has no settlement machine separate from its
    // chain, so what it reproduces is the same rules over a real chain, in
    // `test-vectors/economy-transition-v9-execution.txt`.
    {"settlement.", Match::prefix,
     "tools/economy-transition-v9-vectors/verify.py, over a sampled window "
     "sequence no chain can produce"},
    // The classification of version eight's Python surface into carried,
    // revised, and added. It is a claim about `simulation/economy_transition_v9`
    // and is checked by that package's own verifier; the C++ kernel's equivalent
    // is that every inherited width here is pinned against the accepted file
    // that recorded it.
    {"carryover.", Match::prefix, "tools/economy-transition-v9-vectors/verify.py"},
    // Whether a mint requires a HUB confirmation is a predicate over an
    // escrow's *stored* posture, so the set of confirmable kinds is applied by
    // the transition and not declared by the codec. The sibling claim this
    // target does reach is `kind22.is_issuing_kind`, because a receipt is a
    // codec artifact and `receipt_is_consistent` is the predicate that decides
    // it.
    {"kind22.is_confirmable_mint", Match::exact, "economy_v9_execution_tests"},
    // **Unrepresentable rather than deferred.** A timestamp below the accepted
    // range means a negative millisecond count, and this kernel carries a
    // timestamp in a `std::uint64_t`, so there is no input that reaches the
    // refusal. The Python model can express one and does; recording the case
    // here would mean constructing a value the type forbids.
    {"genesis.refuses_a_timestamp_below_the_range", Match::exact,
     "no u64 input can reach it"},
    // Each predecessor's empty economy tree root, pinned against the file that
    // accepted it. This kernel computes one only inside
    // `predecessor_state_root`, which has no per-version accessor and needs
    // none: what pins that construction here is
    // `root.version_eight_reproduces_its_accepted_root`, a digest somebody else
    // recorded over a whole state rather than over one subtree.
    {"_empty_economy_root_reproduced", Match::contains,
     "tools/economy-transition-v9-vectors/verify.py"},
}};

}  // namespace

namespace economy_v9_fixture {

void verify_coverage(const pv::Values& values) {
  namespace fixture = economy_v9_fixture;
  std::array<bool, kDeferred.size()> matched{};
  for (const auto& [key, value] : values) {
    (void)value;
    // Copied out of the structured binding because C++20 does not permit a
    // lambda to capture one, and the two compilers disagree about it.
    const std::string& name = key;
    if (fixture::consulted().contains(name)) continue;
    bool excused = false;
    for (std::size_t index = 0; index < kDeferred.size(); ++index) {
      const auto& entry = kDeferred[index];
      bool hit = false;
      switch (entry.match) {
        case Match::prefix:
          hit = name.rfind(entry.pattern, 0) == 0;
          break;
        case Match::exact:
          hit = name == entry.pattern;
          break;
        case Match::contains:
          hit = name.find(entry.pattern) != std::string::npos;
          break;
      }
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

}  // namespace

int main(int argc, char** argv) {
  namespace fixture = economy_v9_fixture;
  try {
    pv::require(argc == 7,
                "usage: economy_v9_codec_tests V9_VECTORS MANIFEST V8_VECTORS "
                "V6_VECTORS CALENDAR PRIMITIVES");
    pv::require(sodium_init() >= 0, "libsodium initialization");
    const auto values = pv::load_values(argv[1]);
    const auto manifest = pv::load_values(argv[2]);
    const auto carried_eight = pv::load_values(argv[3]);
    const auto carried_six = pv::load_values(argv[4]);
    const auto calendar = pv::load_values(argv[5]);
    const auto primitives = pv::load_values(argv[6]);

    // The one guard that belongs to no vector group and to the port itself:
    // `src/v9/`'s tree is version eight's copied, so it is required to reproduce
    // the accepted M1 accounts tree root over the accepted M1 accounts. A tree
    // that drifted in the copy would still produce self-consistent version-nine
    // roots and would fail here.
    fixture::verify_accounts_tree(primitives);

    fixture::verify_version(values, carried_eight, manifest, primitives);
    fixture::verify_state(values, carried_eight);
    fixture::verify_clock(values, calendar);
    fixture::verify_kinds(values, carried_six);
    fixture::verify_coverage(values);

    std::cout << "C++ economy transition v9 codec: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "C++ economy transition v9 codec: failed: " << error.what()
              << '\n';
    return 1;
  }
}
