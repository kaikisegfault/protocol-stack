// The version-nine state snapshot, checked against the recorded execution
// scenarios and against every value rule its decoders enforce.
//
// It is what lets a version-nine state leave memory, which is why ADR 0065
// places it third in a stack migration: the four entry kinds version nine adds,
// its widened pool value, and the head's timestamp all have to be writable
// before a store, an application, or a node can hold one.
//
// The checks are split by subject across three translation units. This one is
// the entry point.

#include "snapshot_v9_fixture.hpp"

#include <iostream>

int main(int argc, char** argv) {
  namespace tests = snapshot_v9_tests;
  namespace pv = protocol_vectors;
  try {
    pv::require(argc == 2, "usage: storage_snapshot_v9_tests EXECUTION_VECTORS");
    pv::require(sodium_init() >= 0, "libsodium initialization");
    const auto values = pv::load_values(argv[1]);

    tests::verify_round_trips(values);
    tests::verify_framing_refusals();
    tests::verify_entry_refusals();

    std::cout << "C++ version-nine state snapshot: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "C++ version-nine state snapshot: failed: " << error.what()
              << '\n';
    return 1;
  }
}
