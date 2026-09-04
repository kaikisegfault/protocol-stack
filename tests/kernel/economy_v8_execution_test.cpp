// The version-eight ledger and its transitions, checked against the recorded
// execution vectors and the 62 contract vectors a ledger is needed for.
//
// This is requirement 11 for execution: the C++ implementation and the
// independent Python model must reproduce one fixed file. Nothing here derives a
// second set of expected values — the kernel runs the recorded scenarios and
// every assertion compares against
// `test-vectors/economy-transition-v8-execution.txt`, with the deliberate
// exceptions the derived checks name, and each of those reaches a *third* source
// rather than a second opinion of that file.
//
// **Two files, because the contract's 183 vectors split.** 121 are reproducible
// by a codec and `economy_v8_codec_tests` reproduces them; the other 62 need a
// ledger — kind 20's positive control and its nine ordered refusals, kind 21's
// and its ten, the schedule derivation, the settlement claim, expiry, and
// containment — and those are this target's.
//
// The checks are split by subject across four translation units, the way the
// Python verifier for the same file is. This one is the entry point.

#include "economy_v8_execution_fixture.hpp"

#include <iostream>

int main(int argc, char** argv) {
  namespace fixture = economy_v8_execution;
  namespace pv = protocol_vectors;
  try {
    pv::require(argc == 5,
                "usage: economy_v8_execution_tests EXECUTION CONTRACT PRIMITIVES "
                "LEDGER");
    pv::require(sodium_init() >= 0, "libsodium initialization");
    const auto values = pv::load_values(argv[1]);
    const auto contract = pv::load_values(argv[2]);
    const auto primitives = pv::load_values(argv[3]);
    const auto ledger_vectors = pv::load_values(argv[4]);

    fixture::verify_scenarios(values);
    fixture::verify_derivations(values, primitives, ledger_vectors);
    fixture::verify_coverage(values);
    fixture::verify_transitions(contract);

    std::cout << "C++ economy transition v8 execution: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "C++ economy transition v8 execution: failed: " << error.what()
              << '\n';
    return 1;
  }
}
