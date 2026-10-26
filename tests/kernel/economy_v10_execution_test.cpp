// A version-ten chain runs in C++: the registry admits people, an approval is
// used once, and the launch key retires for good.
//
// This is requirement 9 for what a version-ten chain *does*: the C++ kernel and
// the independent Python model must reproduce
// `test-vectors/economy-transition-v10-execution.txt` exactly — the same
// refusals in the same order, the same marks and counts, the same retirement
// height, the same receipt bytes, the same headers, and the same roots.
//
// **Every vector in that file is consulted and there is nothing to defer**, so
// this target's coverage guard is one rule rather than a table: a recorded key
// this run never read is a failure.
//
// It also consults `genesis.writes_no_registry_entry` in the contract file,
// which the codec target defers here because `open_ledger` is what writes a
// genesis. Two accepted predecessor files are read and no predecessor kernel is
// linked (ADR 0104): version six's, for the purchase label a version-nine
// approval was signed under, and version nine's, for the receipt version a
// version-nine decoder requires.

#include "economy_v10_execution_fixture.hpp"

#include <iostream>
#include <string>

namespace economy_v10_execution {
namespace {

void verify_coverage(const pv::Values& values) {
  for (const auto& [key, value] : values) {
    (void)value;
    const std::string name = key;
    pv::require(consulted().contains(name), "vector " + name + " was never consulted");
  }
}

}  // namespace
}  // namespace economy_v10_execution

int main(int argc, char** argv) {
  namespace fixture = economy_v10_execution;
  namespace pv = protocol_vectors;
  try {
    pv::require(argc == 5,
                "usage: economy_v10_execution_tests EXECUTION_VECTORS "
                "CONTRACT_VECTORS V9_VECTORS V6_VECTORS");
    pv::require(sodium_init() >= 0, "libsodium initialization");
    const auto values = pv::load_values(argv[1]);
    const auto contract = pv::load_values(argv[2]);
    const auto nine = pv::load_values(argv[3]);
    const auto six = pv::load_values(argv[4]);

    fixture::verify_genesis(values);
    fixture::Signatures signatures;
    const auto chain = fixture::chain_scenario(signatures, six.at("hub.purchase.label"));
    fixture::verify_chain(values, chain, signatures, nine);
    const auto cutoff = fixture::cutoff_run();
    const auto span = fixture::span_run();
    fixture::verify_population(values, cutoff, span);
    fixture::verify_invariants(values, cutoff);
    fixture::verify_restart_run(values);
    fixture::verify_coverage(values);

    fixture::verify_contract_sections(contract);
    fixture::verify_lifetime_order();
    fixture::verify_unmarked_machine_in_window_two();
    fixture::verify_open_window_refusals();

    std::cout << "C++ economy transition v10 execution: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "C++ economy transition v10 execution: failed: " << error.what()
              << '\n';
    return 1;
  }
}
