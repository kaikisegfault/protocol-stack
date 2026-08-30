#pragma once

// A version-seven snapshot payload taken apart, so a test can put exactly one
// field back wrong and re-encode it with a valid digest.
//
// The builder is not a second parser. It is assembled from the same three
// kernel projections the encoder uses — `account_entries`, `economy_entries`,
// and `ledger_state_root` — and every test first requires its bytes to equal
// `encode_snapshot_v7`'s for the same ledger. A rebuilder that drifted would
// therefore fail before it was ever used to construct a refusal, which is what
// keeps a negative case about the decoder rather than about the fixture.

#include "protocol/storage/snapshot_v7.hpp"

#include "../kernel/economy_v7_execution_fixture.hpp"

#include <array>
#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace snapshot_v7_tests {

namespace ps = protocol::storage;
namespace v7 = protocol::v7;
namespace pv = protocol_vectors;
namespace fixture = economy_v7_execution;

struct Payload {
  std::array<std::uint8_t, 4> magic{'P', 'S', 'S', 'N'};
  std::uint16_t version = 7;
  v7::Octets32 chain_id{};
  std::uint64_t height = 0;
  std::uint64_t supply_limit = 0;
  std::uint64_t total_supply = 0;
  std::uint64_t fee_pool = 0;
  std::uint64_t fixed_fee = 0;
  v7::Octets32 verifier_key{};
  std::vector<v7::AccountEntry> accounts;
  std::vector<v7::EconomyEntry> economy;
  v7::Hash state_root{};
  // Set only by a test that needs a payload to lie about how much it carries.
  std::optional<std::uint64_t> declared_account_count;
  std::optional<std::uint64_t> declared_economy_count;

  v7::Bytes encode() const;
};

Payload payload_of(const v7::Ledger& ledger);

// The entry the tests reach for by kind, so a mutation names its subject rather
// than an index into a list that a later scenario change would move.
v7::EconomyEntry& entry_of(Payload& payload, v7::Entry kind);
std::vector<v7::EconomyEntry>::iterator find_entry(Payload& payload,
                                                   v7::Entry kind);

std::string error_name(ps::SnapshotV7Error error);

// Decode `payload` and require the exact error. A decode that succeeds, or that
// fails for a different reason, is a failure with both names in the message.
void require_refusal(const Payload& payload,
                     const ps::SnapshotParametersV7& parameters,
                     ps::SnapshotV7Error expected, const std::string& subject);

// Recompute the payload's claimed root from its own summary, accounts, and
// entries, so a mutated payload is internally consistent and reaches the gate
// under test rather than stopping at the one before it. A tampered snapshot that
// bothered to reseal itself is the adversary the conservation gate exists for.
void reseal(Payload& payload);

// Write `value` big-endian into an entry's value at `offset`.
void poke_u64(v7::Bytes& value, std::size_t offset, std::uint64_t number);
void poke_u32(v7::Bytes& value, std::size_t offset, std::uint32_t number);

// The five recorded scenarios and the refusals, each its own translation unit.
void verify_round_trips(const pv::Values& values);
void verify_framing_refusals();
void verify_entry_refusals();

}  // namespace snapshot_v7_tests
