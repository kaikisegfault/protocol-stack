// The version-seven codec, checked against the recorded vectors.
//
// This is requirement 11 for the surface the codec covers: the C++
// implementation and the independent Python model must reproduce fixed files.
//
// **Two files, because version seven records only what version seven changes.**
// `test-vectors/economy-transition-v7.txt` fixes the four re-versioned
// constructions, the state key space, the recovery pool record, the extended
// cycle assignment record, version-seven genesis, the settlement, and both
// conservation identities. Everything else — the envelope, the fourteen bodies,
// admission, the six HUB messages, the result-code space, the escrow and signer
// derivations, the registry, and the security posture — is version six's,
// unchanged, and stays fixed by `test-vectors/economy-transition-v6.txt`, which
// is the file that accepted it. Re-recording it under a version-seven name would
// produce a second file that agrees with the first and says nothing.
//
// Nothing here derives a second set of expected values, with these deliberate
// exceptions, each a check against a *third* source rather than a second opinion
// of either file:
//
//   * the kind-1 identity and the signer derivation, against
//     `test-vectors/protocol-primitives-v1.txt`, because both are accepted M1
//     artifacts version seven still claims to preserve;
//   * the accounts tree, against the same file, because it is version one's
//     construction entry for entry;
//   * the ten channel caps and five base permission legs, against
//     `test-vectors/founder-economy-manifest-v3.txt`, because they are
//     founder-directed figures rather than derived ones; and
//   * the imported half of the settlement, against
//     `test-vectors/economy-transition-v3.txt`, because version seven's
//     settlement is version three's with steps 5 through 7 replaced.
//
// The checks are split by subject across five translation units. This one is the
// entry point.

#include "economy_v7_fixture.hpp"

#include <iostream>

int main(int argc, char** argv) {
  namespace fixture = economy_v7_fixture;
  namespace pv = protocol_vectors;
  try {
    pv::require(argc == 6,
                "usage: economy_v7_codec_tests V7_VECTORS PRIMITIVES V3_VECTORS "
                "MANIFEST V6_VECTORS");
    pv::require(sodium_init() >= 0, "libsodium initialization");
    const auto values = pv::load_values(argv[1]);
    const auto primitives = pv::load_values(argv[2]);
    const auto version_three = pv::load_values(argv[3]);
    const auto manifest = pv::load_values(argv[4]);
    const auto carried = pv::load_values(argv[5]);

    fixture::verify_encoding(carried, primitives);
    fixture::verify_identity(carried, primitives);
    fixture::verify_version(values, carried, manifest);
    fixture::verify_state(values);
    fixture::verify_settlement(values, version_three, manifest);

    std::cout << "C++ economy transition v7 codec: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "C++ economy transition v7 codec: failed: " << error.what() << '\n';
    return 1;
  }
}
