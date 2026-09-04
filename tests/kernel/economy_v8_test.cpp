// The version-eight codec, checked against the recorded vectors.
//
// This is requirement 11 for the surface the codec covers: the C++
// implementation and the independent Python model must reproduce fixed files.
//
// **`test-vectors/economy-transition-v8.txt` holds 183 vectors and this target
// reproduces 121 of them.** The split is the one ADR 0065 records: 121 are
// derivable from the codec alone — the labels, the genesis field table, the
// seven non-collisions, the two entry kinds and their refusals, the two
// transaction kinds and their admission rules, the result-code space, and
// challenge selection — and 62 need a ledger, because they are what the four
// ordered block steps and the two transitions do. Those are M3.13o's, and this
// file asserts nothing about them.
//
// **Three files, because version eight records only what version eight
// changes.** The surface it inherits stays fixed by the file that accepted it:
// `test-vectors/economy-transition-v7.txt` fixes the state key space and the
// version-seven genesis this one is measured against, and
// `test-vectors/economy-transition-v6.txt` fixes the envelope, the fourteen
// carried bodies, and the thirty-three carried result codes. Re-recording
// either under a version-eight name would produce a file that agrees with the
// first and says nothing.
//
// Two further files are read as *third* sources rather than as second opinions:
// `test-vectors/founder-economy-manifest-v3.txt`, because the manifest digest
// and the referral leg are founder-directed figures rather than derived ones,
// and `test-vectors/protocol-primitives-v1.txt`, because the accounts tree
// inside the state root is version one's construction entry for entry.
//
// The checks are split by subject across four translation units. This one is
// the entry point.

#include "economy_v8_fixture.hpp"

#include <iostream>

int main(int argc, char** argv) {
  namespace fixture = economy_v8_fixture;
  namespace pv = protocol_vectors;
  try {
    pv::require(argc == 6,
                "usage: economy_v8_codec_tests V8_VECTORS MANIFEST V7_VECTORS "
                "V6_VECTORS PRIMITIVES");
    pv::require(sodium_init() >= 0, "libsodium initialization");
    const auto values = pv::load_values(argv[1]);
    const auto manifest = pv::load_values(argv[2]);
    const auto carried_seven = pv::load_values(argv[3]);
    const auto carried_six = pv::load_values(argv[4]);
    const auto primitives = pv::load_values(argv[5]);

    // The one guard that belongs to no vector group and to the port itself:
    // `src/v8/`'s tree is version seven's copied, so it is required to
    // reproduce the accepted M1 accounts tree root over the accepted M1
    // accounts. A tree that drifted in the copy would still produce
    // self-consistent version-eight roots and would fail here.
    fixture::verify_accounts_tree(primitives);

    fixture::verify_version(values, carried_seven, manifest, primitives);
    fixture::verify_state(values, carried_seven);
    fixture::verify_kinds(values, carried_six);
    fixture::verify_selection(values);

    std::cout << "C++ economy transition v8 codec: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "C++ economy transition v8 codec: failed: " << error.what() << '\n';
    return 1;
  }
}
