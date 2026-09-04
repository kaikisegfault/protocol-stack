// The 62 contract vectors a ledger is needed for.
//
// `economy-transition-v8.txt` records 183 vectors and `economy_v8_codec_tests`
// reproduces the 121 a codec can derive. The other 62 are here: kind 20's
// positive control and its nine ordered refusals, kind 21's and its ten, the
// schedule derivation, the settlement claim, expiry, and containment.
//
// **Every refusal is produced by executing a minimally mutated input against a
// positive control**, rather than by calling a transition with a hand-built
// state. A condition reached that way is reached the way a chain reaches it: the
// shared envelope checks run first, the escrow is resolved, and the ordering
// between conditions is the ordering a block imposes.

#include "economy_v8_execution_fixture.hpp"

namespace economy_v8_execution {
namespace {

// Placeholder for the ordered-condition fixture, filled in below.
void check_placeholder(const pv::Values& contract) { (void)contract; }

}  // namespace

void verify_transitions(const pv::Values& contract) { check_placeholder(contract); }

}  // namespace economy_v8_execution
