// The version-six ledger and its transitions, checked against the recorded
// execution vectors.
//
// This is requirement 11 for execution: the C++ implementation and the
// independent Python model must reproduce one fixed file. Nothing here derives a
// second set of expected values — the kernel runs the recorded scenarios and
// every assertion compares against
// `test-vectors/economy-transition-v6-execution.txt`, with the deliberate
// exceptions the derived checks name, and each of those reaches a *third* source
// rather than a second opinion of that file.
//
// The checks are split by subject across three translation units, the way the
// Python verifier for the same file is. This one is the entry point.

#include "economy_v6_execution_fixture.hpp"

#include <iostream>

int main(int argc, char** argv) {
  namespace fixture = economy_v6_execution;
  namespace pv = protocol_vectors;
  try {
    pv::require(argc == 6,
                "usage: economy_v6_execution_tests EXECUTION PRIMITIVES LEDGER "
                "MANIFEST V3_VECTORS");
    pv::require(sodium_init() >= 0, "libsodium initialization");
    const auto values = pv::load_values(argv[1]);
    const auto primitives = pv::load_values(argv[2]);
    const auto ledger_vectors = pv::load_values(argv[3]);
    const auto manifest = pv::load_values(argv[4]);
    const auto version_three = pv::load_values(argv[5]);

    fixture::verify_scenarios(values, primitives);
    fixture::verify_derivations(values, primitives, ledger_vectors, manifest,
                                version_three);
    fixture::verify_coverage(values);

    std::cout << "C++ economy transition v6 execution: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "C++ economy transition v6 execution: failed: " << error.what()
              << '\n';
    return 1;
  }
}
