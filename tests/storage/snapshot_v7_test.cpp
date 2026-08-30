// The version-seven state snapshot, checked against the recorded execution
// scenarios and against every value rule its decoders enforce.
//
// This is the first artifact in the repository that lets a version-seven state
// leave memory. Requirement 13 — adversarial four-node scenarios through restart
// and recovery — cannot begin until a state can be written down and read back,
// and "read back" has to mean the same state rather than a similar one.
//
// The checks are split by subject across three translation units. This one is
// the entry point.

#include "snapshot_v7_fixture.hpp"

#include <iostream>

int main(int argc, char** argv) {
  namespace tests = snapshot_v7_tests;
  namespace pv = protocol_vectors;
  try {
    pv::require(argc == 2, "usage: storage_snapshot_v7_tests EXECUTION_VECTORS");
    pv::require(sodium_init() >= 0, "libsodium initialization");
    const auto values = pv::load_values(argv[1]);

    tests::verify_round_trips(values);
    tests::verify_framing_refusals();
    tests::verify_entry_refusals();

    std::cout << "C++ version-seven state snapshot: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "C++ version-seven state snapshot: failed: " << error.what()
              << '\n';
    return 1;
  }
}
