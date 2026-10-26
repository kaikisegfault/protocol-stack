// The version-ten state snapshot, checked against the recorded execution
// fixtures and against every value rule its decoders enforce.
//
// It is what lets a version-ten state leave memory, which is why ADR 0104
// places it third in the migration: the machine keys, their inverse, the
// retirement, the founder counts, and the build authority key all have to be
// writable before a store, an application, or a node can hold one.
//
// The checks are split by subject across five translation units. This one is
// the entry point, and builds the three fixtures once, because the population
// alone executes more than a thousand registrations.

#include "snapshot_v10_fixture.hpp"

#include <iostream>

int main(int argc, char** argv) {
  namespace tests = snapshot_v10_tests;
  namespace pv = protocol_vectors;
  try {
    pv::require(argc == 3,
                "usage: storage_snapshot_v10_tests EXECUTION_VECTORS V6_VECTORS");
    pv::require(sodium_init() >= 0, "libsodium initialization");
    const auto values = pv::load_values(argv[1]);
    const auto six = pv::load_values(argv[2]);

    tests::Fixtures fixtures;
    fixtures.chain = tests::fixture::chain_scenario(fixtures.chain_signatures,
                                                    six.at("hub.purchase.label"));
    fixtures.cutoff = tests::fixture::cutoff_run();
    fixtures.span = tests::fixture::span_run();

    tests::verify_round_trips(values, fixtures);
    tests::verify_framing_refusals(fixtures);
    tests::verify_registry_refusals(fixtures);
    tests::verify_entry_refusals(fixtures);
    tests::verify_inherited_refusals(fixtures);

    std::cout << "C++ version-ten state snapshot: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "C++ version-ten state snapshot: failed: " << error.what()
              << '\n';
    return 1;
  }
}
