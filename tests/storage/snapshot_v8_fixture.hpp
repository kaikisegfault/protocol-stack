#pragma once

// A version-eight snapshot payload taken apart, so a test can put exactly one
// field back wrong and re-encode it with a valid digest.
//
// The builder is not a second parser. It is assembled from the same three
// kernel projections the encoder uses — `account_entries`, `economy_entries`,
// and `ledger_state_root` — and every test first requires its bytes to equal
// `encode_snapshot_v8`'s for the same ledger. A rebuilder that drifted would
// therefore fail before it was ever used to construct a refusal, which is what
// keeps a negative case about the decoder rather than about the fixture.

#include "protocol/storage/snapshot_v8.hpp"

#include "../kernel/economy_v8_execution_fixture.hpp"

#include <array>
#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace snapshot_v8_tests {

namespace ps = protocol::storage;
namespace v8 = protocol::v8;
namespace pv = protocol_vectors;
namespace fixture = economy_v8_execution;

struct Payload {
  std::array<std::uint8_t, 4> magic{'P', 'S', 'S', 'N'};
  std::uint16_t version = 8;
  v8::Octets32 chain_id{};
  std::uint64_t height = 0;
  std::uint64_t supply_limit = 0;
  std::uint64_t total_supply = 0;
  std::uint64_t fee_pool = 0;
  std::uint64_t fixed_fee = 0;
  v8::Octets32 verifier_key{};
  v8::Octets32 dispute_authority_key{};
  std::vector<v8::AccountEntry> accounts;
  std::vector<v8::EconomyEntry> economy;
  v8::Hash state_root{};
  // Set only by a test that needs a payload to lie about how much it carries.
  std::optional<std::uint64_t> declared_account_count;
  std::optional<std::uint64_t> declared_economy_count;

  v8::Bytes encode() const;
};

Payload payload_of(const v8::Ledger& ledger);

// The entry the tests reach for by kind, so a mutation names its subject rather
// than an index into a list that a later scenario change would move.
v8::EconomyEntry& entry_of(Payload& payload, v8::Entry kind);
// The last entry of a kind, which is the one a key mutation can move without
// disturbing the strict order the payload is also required to be in.
v8::EconomyEntry& last_of(Payload& payload, v8::Entry kind);
std::vector<v8::EconomyEntry>::iterator find_entry(Payload& payload,
                                                   v8::Entry kind);

std::string error_name(ps::SnapshotV8Error error);

// Decode `payload` and require the exact error. A decode that succeeds, or that
// fails for a different reason, is a failure with both names in the message.
void require_refusal(const Payload& payload,
                     const ps::SnapshotParametersV8& parameters,
                     ps::SnapshotV8Error expected, const std::string& subject);

// Recompute the payload's claimed root from its own summary, accounts, and
// entries, so a mutated payload is internally consistent and reaches the gate
// under test rather than stopping at the one before it. A tampered snapshot that
// bothered to reseal itself is the adversary the conservation gate exists for.
void reseal(Payload& payload);

// Write `value` big-endian into an entry's value at `offset`.
void poke_u64(v8::Bytes& value, std::size_t offset, std::uint64_t number);
void poke_u32(v8::Bytes& value, std::size_t offset, std::uint32_t number);

// The four recorded scenarios and the refusals, each its own translation unit.
void verify_round_trips(const pv::Values& values);
void verify_framing_refusals();
void verify_entry_refusals();

}  // namespace snapshot_v8_tests
