#pragma once

// The shared fixture behind the version-nine codec checks.
//
// The checks are split by subject exactly as the Python verifier for the same
// vector file is — version, state, clock, kinds — so each translation unit reads
// as one argument. What lives here is only what more than one of them needs: the
// recorded fixture's constants, the accessors that make a missing vector key a
// failure rather than a default, and the sixteen economy entries genesis writes.
//
// **Nothing in the fixture is founder-directed.** The keys and the network
// identifier are arbitrary octets chosen to be distinguishable in a hex dump,
// the genesis timestamp is the accepted payout fixture's rather than a second
// one, and every founder figure the checks touch is read from an accepted vector
// file rather than restated here.

#include "protocol/v9/economy.hpp"

#include "../../tools/protocol-vectors/vector_common.hpp"

#include <cstdint>
#include <set>
#include <span>
#include <string>
#include <vector>

namespace economy_v9_fixture {

namespace pv = protocol_vectors;
namespace v9 = protocol::v9;

inline v9::Octets32 repeated(std::uint8_t octet) {
  v9::Octets32 value{};
  value.fill(octet);
  return value;
}

inline v9::Octets32 ascending(std::uint8_t first) {
  v9::Octets32 value{};
  for (std::size_t index = 0; index < value.size(); ++index) {
    value[index] = static_cast<std::uint8_t>(first + index);
  }
  return value;
}

inline v9::Octets32 from_hex(const std::string& hex) {
  const auto bytes = pv::hex_decode(hex);
  pv::require(bytes.size() == 32, "expected 32 octets");
  v9::Octets32 value{};
  std::copy(bytes.begin(), bytes.end(), value.begin());
  return value;
}

inline std::string hex(std::span<const std::uint8_t> bytes) {
  static constexpr char digits[] = "0123456789abcdef";
  std::string out;
  out.reserve(bytes.size() * 2);
  for (const auto octet : bytes) {
    out.push_back(digits[octet >> 4U]);
    out.push_back(digits[octet & 0x0FU]);
  }
  return out;
}

inline std::string hex(const v9::Hash& value) {
  return hex(std::span<const std::uint8_t>(value.data(), value.size()));
}

inline std::string hex(const v9::Bytes& value) {
  return hex(std::span<const std::uint8_t>(value.data(), value.size()));
}

// Every vector key this target consults. A key in a section the target claims
// but never reads is the vacuous case `docs/engineering/verification.md`
// forbids — the file would gain a vector and nothing here would notice — so the
// entry point compares this set against the file's own keys.
inline std::set<std::string>& consulted() {
  static std::set<std::string> keys;
  return keys;
}

// A missing key is a failure rather than a skip, for the same reason.
inline const std::string& expect_text(const pv::Values& values,
                                      const std::string& key) {
  const auto found = values.find(key);
  pv::require(found != values.end(), "vector file records no " + key);
  consulted().insert(key);
  return found->second;
}

// A value that is not a number names itself rather than throwing `stoull`,
// which says nothing about which vector was misread.
inline std::uint64_t expect_number(const pv::Values& values,
                                   const std::string& key) {
  const auto& text = expect_text(values, key);
  try {
    return std::stoull(text);
  } catch (const std::exception&) {
    throw std::runtime_error(key + " is not a number: " + text);
  }
}

inline std::size_t expect_size(const pv::Values& values, const std::string& key) {
  return static_cast<std::size_t>(expect_number(values, key));
}

inline void expect_true(const pv::Values& values, const std::string& key) {
  pv::require(expect_text(values, key) == "true", "the vectors record " + key);
}

// The recorded fixture, which is `simulation/economy_transition_v9/scenario.py`.
// The genesis timestamp is the accepted `simulation/unreferred_pool` fixture's,
// bound rather than restated: a second genesis timestamp here would be a second
// opinion about which month a window belongs to. It sits six hours off a day
// boundary so that a window straddles a month boundary.
inline constexpr std::uint32_t kNetworkId = 9;
inline constexpr std::uint64_t kSupplyLimit = 5'699'395'010'000'000'000ULL;
inline constexpr std::uint64_t kFixedTransferFee = 1'000;
inline constexpr std::uint64_t kGenesisMillis = 1'772'172'000'000ULL;
// The commit target `calendar-v1` names, which is the fixture's block spacing.
inline constexpr std::uint64_t kMillisPerBlock = 3'000;
// The height the recorded roots are taken at. Nothing derives it: a root is a
// function of the state, and what the vectors fix is that the eight predecessor
// constructions over one state reach eight different digests.
inline constexpr std::uint64_t kRootHeight = 12;

inline const v9::Octets32 kVerifierKey = repeated(0xA1);
inline const v9::Octets32 kDisputeAuthorityKey = repeated(0xD8);

// The recorded header's fields, chosen to be distinguishable in a hex dump.
inline constexpr std::uint64_t kHeaderHeight = 4;
inline constexpr std::uint32_t kHeaderTransactionCount = 2;

inline std::uint64_t timestamp_of_height(std::uint64_t height) {
  return kGenesisMillis + height * kMillisPerBlock;
}

inline v9::Genesis fixture_genesis(const v9::Octets32& manifest_digest) {
  v9::Genesis genesis;
  genesis.network_id = kNetworkId;
  genesis.genesis_timestamp = kGenesisMillis;
  genesis.supply_limit = kSupplyLimit;
  genesis.fixed_transfer_fee = kFixedTransferFee;
  genesis.manifest_digest = manifest_digest;
  genesis.verifier_key = kVerifierKey;
  genesis.dispute_authority_key = kDisputeAuthorityKey;
  return genesis;
}

// The ten channels, the empty recovery pool, and the two singletons version
// eight wrote, plus version nine's two. The pool is the fourteenth and is
// rewidened; the settlement cursor and window zero's month are the two version
// nine adds, both at the genesis month.
//
// **Window zero's opening height is genesis.** Height zero is never a block —
// `ledger-transition-v1` starts a chain at height one — so writing its month
// here is the general rule reaching the one height that is a genesis rather than
// a block, not a special case.
inline std::vector<v9::EconomyEntry> genesis_economy(std::uint32_t genesis_month) {
  std::vector<v9::EconomyEntry> entries;
  for (std::uint8_t channel = 0; channel < 10; ++channel) {
    entries.push_back({v9::channel_key(channel), v9::channel_value(0, 0)});
  }
  entries.push_back({v9::recovery_pool_key(), v9::recovery_pool_value({})});
  entries.push_back(
      {v9::verifier_key_key(), v9::verifier_key_value(kVerifierKey)});
  entries.push_back(
      {v9::verified_user_counter_key(), v9::verified_user_counter_value(0)});
  const auto pool = v9::unreferred_pool_value({});
  pv::require(pool.has_value(), "the empty pool must encode");
  entries.push_back({v9::unreferred_pool_key(), *pool});
  const auto cursor = v9::settlement_cursor_value(genesis_month);
  pv::require(cursor.has_value(), "the genesis cursor must encode");
  entries.push_back({v9::settlement_cursor_key(), *cursor});
  const auto month = v9::window_month_value(genesis_month);
  pv::require(month.has_value(), "window zero's month must encode");
  entries.push_back({v9::window_month_key(0), *month});
  return entries;
}

// The three accounts `protocol-primitives-v1` records, read from that file
// rather than restated, so the accounts tree inside the state root is checked
// against a third source.
inline std::vector<v9::AccountEntry> accepted_accounts(const pv::Values& primitives) {
  std::vector<v9::AccountEntry> accounts;
  for (int index = 0; index < 3; ++index) {
    const auto entry = primitives.at("state.account" + std::to_string(index));
    v9::AccountEntry account;
    account.account_id = from_hex(entry.substr(0, 64));
    account.balance = std::stoull(entry.substr(64, 16), nullptr, 16);
    account.nonce = std::stoull(entry.substr(80, 16), nullptr, 16);
    accounts.push_back(account);
  }
  return accounts;
}

// The port's own guard, belonging to no vector group: `src/v9/`'s tree is
// version eight's copied, so it is required to reproduce the accepted M1
// accounts tree root over the accepted M1 accounts. A tree that drifted in the
// copy would still produce self-consistent version-nine roots and would fail
// here.
void verify_accounts_tree(const pv::Values& primitives);

// The four check groups, one per translation unit. `values` is always version
// nine's own file; `carried_eight` and `carried_six` are the accepted files that
// fix the surface version nine inherits, so an inherited width or name is
// compared against the file that accepted it rather than re-recorded under a
// version-nine name.
void verify_version(const pv::Values& values, const pv::Values& carried_eight,
                    const pv::Values& manifest, const pv::Values& primitives);
void verify_state(const pv::Values& values, const pv::Values& carried_eight);
// `calendar` is `test-vectors/calendar-v1.txt`, read as a third source: those
// vectors were recorded by driving the accepted calendar model rather than
// version nine's, so reproducing them is agreement with the specification this
// version binds rather than with its own restatement of it.
void verify_clock(const pv::Values& values, const pv::Values& calendar);
void verify_kinds(const pv::Values& values, const pv::Values& carried_six);
// Every recorded vector is either consulted above or named as owed to a later
// slice. A key in neither set fails, and a deferred entry that matches nothing
// fails too, so the slice boundary is checkable rather than described.
void verify_coverage(const pv::Values& values);

}  // namespace economy_v9_fixture
