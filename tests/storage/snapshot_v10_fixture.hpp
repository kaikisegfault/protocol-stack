#pragma once

// A version-ten snapshot payload taken apart, so a test can put exactly one
// field back wrong and re-encode it with a valid digest.
//
// The builder is not a second parser. It is assembled from the same three
// kernel projections the encoder uses — `account_entries`, `economy_entries`,
// and `ledger_state_root` — and every test first requires its bytes to equal
// `encode_snapshot_v10`'s for the same ledger. A rebuilder that drifted would
// therefore fail before it was ever used to construct a refusal, which is what
// keeps a negative case about the decoder rather than about the fixture.
//
// **The three keys sit in genesis's order here, as they do in the payload**:
// the launch key, the dispute authority key, and the build authority key.
//
// **The fixtures are the kernel execution suite's own**, reused rather than
// restated, and **no test here includes `protocol/v9/`** (ADR 0104): the chain
// of blocks from `economy_v10_trace.cpp`, and the 101-machine, two-founder
// population and the one-machine span run from `economy_v10_population.cpp`.
// The execution vectors record each one's final root, so a restored ledger is
// checked against figures a model that knows nothing about snapshots produced.
// The chain is built from version six's purchase label, which its version-nine
// approval was signed under, so the suite reads version six's accepted vectors
// for that one value as the execution target does.

#include "protocol/storage/snapshot_v10.hpp"

#include "../kernel/economy_v10_execution_fixture.hpp"

#include <array>
#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace snapshot_v10_tests {

namespace ps = protocol::storage;
namespace v10 = protocol::v10;
namespace pv = protocol_vectors;
namespace fixture = economy_v10_execution;

struct Payload {
  std::array<std::uint8_t, 4> magic{'P', 'S', 'S', 'N'};
  std::uint16_t version = 10;
  v10::Octets32 chain_id{};
  std::uint64_t height = 0;
  std::uint64_t timestamp = 0;
  std::uint64_t supply_limit = 0;
  std::uint64_t total_supply = 0;
  std::uint64_t fee_pool = 0;
  std::uint64_t fixed_fee = 0;
  v10::Octets32 launch_key{};
  v10::Octets32 dispute_authority_key{};
  v10::Octets32 build_authority_key{};
  std::vector<v10::AccountEntry> accounts;
  std::vector<v10::EconomyEntry> economy;
  v10::Hash state_root{};
  // Set only by a test that needs a payload to lie about how much it carries.
  std::optional<std::uint64_t> declared_account_count;
  std::optional<std::uint64_t> declared_economy_count;

  v10::Bytes encode() const;
};

Payload payload_of(const v10::Ledger& ledger);

// The entry the tests reach for by kind, so a mutation names its subject rather
// than an index into a list that a later scenario change would move.
v10::EconomyEntry& entry_of(Payload& payload, v10::Entry kind);
// The last entry of a kind, which is the one a key mutation can move without
// disturbing the strict order the payload is also required to be in.
v10::EconomyEntry& last_of(Payload& payload, v10::Entry kind);
std::vector<v10::EconomyEntry>::iterator find_entry(Payload& payload,
                                                    v10::Entry kind);
// Remove every entry of a kind, for the cases about a fixed entry's absence.
void erase_kind(Payload& payload, v10::Entry kind);

std::string error_name(ps::SnapshotV10Error error);

// Decode `payload` and require the exact error. A decode that succeeds, or that
// fails for a different reason, is a failure with both names in the message.
void require_refusal(const Payload& payload,
                     const ps::SnapshotParametersV10& parameters,
                     ps::SnapshotV10Error expected, const std::string& subject);
void require_restores(const Payload& payload,
                      const ps::SnapshotParametersV10& parameters,
                      const std::string& subject);

// Recompute the payload's claimed root from its own summary, accounts, and
// entries, so a mutated payload is internally consistent and reaches the gate
// under test rather than stopping at the one before it. A tampered snapshot that
// bothered to reseal itself is the adversary the conservation gate exists for.
void reseal(Payload& payload);

// Write `value` big-endian into an entry's value at `offset`, and read it back
// for a case that changes a field relative to what the chain wrote.
void poke_u64(v10::Bytes& value, std::size_t offset, std::uint64_t number);
void poke_u32(v10::Bytes& value, std::size_t offset, std::uint32_t number);
std::uint64_t peek_u64(const v10::Bytes& value, std::size_t offset);

// Every ledger the checks read, built once, because the population alone
// executes more than a thousand registrations. The chain's signature table is
// kept beside it, because the round trip signs one more transaction against
// each ledger and the recorded table is what verifies it.
struct Fixtures {
  fixture::Signatures chain_signatures;
  fixture::Chain chain;
  fixture::Harness cutoff;
  fixture::Harness span;
};

// The recorded fixtures and the refusals, each its own translation unit.
void verify_round_trips(const pv::Values& values, Fixtures& fixtures);
void verify_framing_refusals(const Fixtures& fixtures);
void verify_registry_refusals(const Fixtures& fixtures);
void verify_entry_refusals(const Fixtures& fixtures);
void verify_inherited_refusals(const Fixtures& fixtures);

}  // namespace snapshot_v10_tests
