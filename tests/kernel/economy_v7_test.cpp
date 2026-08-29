// The version-six codec, checked against the recorded vectors.
//
// This is requirement 11 for the surface the codec covers: the C++
// implementation and the independent Python model must reproduce one fixed
// file. Nothing here derives a second set of expected values — every assertion
// compares against `test-vectors/economy-transition-v6.txt`, with three
// deliberate exceptions, and each is a check against a *third* source rather
// than a second opinion of that file:
//
//   * the kind-1 identity and the signer derivation, against
//     `test-vectors/protocol-primitives-v1.txt`, because both are accepted M1
//     artifacts version six claims to preserve;
//   * the accounts tree, against the same file, because it is version one's
//     construction entry for entry; and
//   * the two cycle-assignment records, against
//     `test-vectors/economy-transition-v3.txt`, because version six's
//     settlement is version three's imported rather than reimplemented.
//
// The checks are split by subject across four translation units, the way the
// Python verifier for the same file is. This one is the entry point.

#include "economy_v7_fixture.hpp"

#include <iostream>

int main(int argc, char** argv) {
  namespace fixture = economy_v7_fixture;
  namespace pv = protocol_vectors;
  try {
    pv::require(argc == 5,
                "usage: economy_v7_tests V6_VECTORS PRIMITIVES V3_VECTORS MANIFEST");
    pv::require(sodium_init() >= 0, "libsodium initialization");
    const auto values = pv::load_values(argv[1]);
    const auto primitives = pv::load_values(argv[2]);
    const auto version_three = pv::load_values(argv[3]);
    const auto manifest = pv::load_values(argv[4]);

    fixture::verify_encoding(values, primitives);
    fixture::verify_identity(values, primitives);
    fixture::verify_state(values, primitives, version_three, manifest);
    fixture::verify_settlement(values, version_three);

    std::cout << "C++ economy transition v6 codec: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "C++ economy transition v6 codec: failed: " << error.what() << '\n';
    return 1;
  }
}
