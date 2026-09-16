// A version-nine chain runs in C++, and the unreferred pool pays somebody.
//
// This is requirement 11 for what a chain *does*: the C++ implementation and the
// independent Python model must reproduce
// `test-vectors/economy-transition-v9-execution.txt` exactly — the same months
// closed at the same heights, the same winners, the same claims, the same
// receipt bytes, the same header, and the same block identifier.
//
// **Every vector in that file is consulted and there is nothing to defer**, so
// this target's coverage guard is one rule rather than a table: a recorded key
// this run never read is a failure.
//
// It also consults the two sections of `test-vectors/economy-transition-v9.txt`
// the codec target defers here — `attribution.` and `kind22.is_confirmable_mint`
// — because both need something the codec has no access to: a window's month is
// written at its opening height and read two windows later, and whether a mint
// requires a confirmation is a predicate over an escrow's stored posture.

#include "economy_v9_execution_fixture.hpp"

#include <iostream>
#include <string>

namespace economy_v9_execution {

void verify_coverage(const pv::Values& values) {
  for (const auto& [key, value] : values) {
    (void)value;
    const std::string& name = key;
    pv::require(consulted().contains(name),
                "vector " + name + " was never consulted");
  }
}

}  // namespace economy_v9_execution

int main(int argc, char** argv) {
  namespace fixture = economy_v9_execution;
  namespace pv = protocol_vectors;
  try {
    pv::require(argc == 3,
                "usage: economy_v9_execution_tests EXECUTION_VECTORS "
                "CONTRACT_VECTORS");
    pv::require(sodium_init() >= 0, "libsodium initialization");
    const auto values = pv::load_values(argv[1]);
    const auto contract = pv::load_values(argv[2]);

    fixture::verify_scenarios(values);
    fixture::verify_orderings(values);
    fixture::verify_single_pass(values);
    fixture::verify_coverage(values);

    fixture::verify_contract_sections(contract);

    std::cout << "C++ economy transition v9 execution: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "C++ economy transition v9 execution: failed: " << error.what()
              << '\n';
    return 1;
  }
}
