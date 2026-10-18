#pragma once

// The shared fixture behind the version-ten codec checks.
//
// The checks are split by subject across three translation units — version,
// state, kinds — so each reads as one argument. What lives here is only what
// more than one of them needs: the recorded fixture's constants, the accessors
// that make a missing vector key a failure rather than a default, and the
// sixteen economy entries genesis writes.
//
// **The fixture is the recording's, octet for octet.** Every key, identity,
// signature, and figure below is
// `tools/economy-transition-v10-vectors/verify.py`'s, chosen there to be
// distinguishable in a hex dump. The two founder-directed figures a genesis
// carries, the supply limit and the manifest digest, are read from
// `test-vectors/founder-economy-manifest-v3.txt` rather than restated, so a
// recorded genesis can only be reproduced by reading the accepted manifest.

#include "protocol/v10/economy.hpp"

#include "../../tools/protocol-vectors/vector_common.hpp"

#include <algorithm>
#include <cstdint>
#include <set>
#include <span>
#include <string>
#include <vector>

namespace economy_v10_fixture {

namespace pv = protocol_vectors;
namespace v10 = protocol::v10;

inline v10::Octets32 repeated(std::uint8_t octet) {
  v10::Octets32 value{};
  value.fill(octet);
  return value;
}

inline v10::Octets32 ascending(std::uint8_t first) {
  v10::Octets32 value{};
  for (std::size_t index = 0; index < value.size(); ++index) {
    value[index] = static_cast<std::uint8_t>(first + index);
  }
  return value;
}

inline v10::Octets32 from_hex(const std::string& hex) {
  const auto bytes = pv::hex_decode(hex);
  pv::require(bytes.size() == 32, "expected 32 octets");
  v10::Octets32 value{};
  std::copy(bytes.begin(), bytes.end(), value.begin());
  return value;
}

inline v10::Bytes bytes_from_hex(const std::string& hex) {
  const auto bytes = pv::hex_decode(hex);
  return v10::Bytes(bytes.begin(), bytes.end());
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

inline std::string hex(const v10::Hash& value) {
  return hex(std::span<const std::uint8_t>(value.data(), value.size()));
}

inline std::string hex(const v10::Bytes& value) {
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

// A recorded boolean is a claim, so it is consulted only where the check beside
// it established the claim; this is the form for a claim this target computed.
inline void expect_claim(const pv::Values& values, const std::string& key,
                         bool established) {
  pv::require(established, "the claim " + key + " does not hold here");
  expect_true(values, key);
}

// --- the recorded genesis ---------------------------------------------------

inline constexpr std::uint32_t kNetworkId = 10;
inline constexpr std::uint64_t kGenesisMillis = 1'768'435'200'000ULL;
inline constexpr std::uint64_t kFixedTransferFee = 1'000;
inline const v10::Octets32 kLaunchKey = repeated(0x55);
inline const v10::Octets32 kDisputeAuthorityKey = repeated(0xD8);
inline const v10::Octets32 kBuildAuthorityKey = repeated(0xB4);

inline v10::Genesis fixture_genesis(const pv::Values& manifest) {
  v10::Genesis genesis;
  genesis.network_id = kNetworkId;
  genesis.genesis_timestamp = kGenesisMillis;
  genesis.supply_limit =
      std::stoull(manifest.at("denomination.maximum_supply_atomic"));
  genesis.fixed_transfer_fee = kFixedTransferFee;
  genesis.manifest_digest = from_hex(manifest.at("manifest_digest"));
  genesis.launch_key = kLaunchKey;
  genesis.dispute_authority_key = kDisputeAuthorityKey;
  genesis.build_authority_key = kBuildAuthorityKey;
  return genesis;
}

// Version nine's sixteen, built through this codec: the ten channels, the empty
// recovery pool, entry kind 8 holding the launch key, the verified-user counter,
// the empty unreferred pool, the settlement cursor, and window zero's month,
// both at the genesis month. The ledger slice writes the same sixteen from a
// genesis; this list is what the root non-collisions are taken over.
inline std::vector<v10::EconomyEntry> genesis_economy(const v10::Genesis& genesis) {
  const auto month = v10::month_index(genesis.genesis_timestamp);
  pv::require(month.has_value(), "the genesis timestamp has a month");
  std::vector<v10::EconomyEntry> entries;
  for (std::size_t channel = 0; channel < v10::kChannelCount; ++channel) {
    entries.push_back({v10::channel_key(static_cast<std::uint8_t>(channel)),
                       v10::channel_value(0, 0)});
  }
  entries.push_back({v10::recovery_pool_key(), v10::recovery_pool_value({})});
  entries.push_back(
      {v10::verifier_key_key(), v10::verifier_key_value(genesis.launch_key)});
  entries.push_back(
      {v10::verified_user_counter_key(), v10::verified_user_counter_value(0)});
  const auto pool = v10::unreferred_pool_value({});
  pv::require(pool.has_value(), "the empty pool must encode");
  entries.push_back({v10::unreferred_pool_key(), *pool});
  const auto cursor = v10::settlement_cursor_value(*month);
  pv::require(cursor.has_value(), "the genesis cursor must encode");
  entries.push_back({v10::settlement_cursor_key(), *cursor});
  const auto window_month = v10::window_month_value(*month);
  pv::require(window_month.has_value(), "window zero's month must encode");
  entries.push_back({v10::window_month_key(0), *window_month});
  return entries;
}

// --- the recorded transactions ----------------------------------------------

inline const v10::Octets32 kChain = repeated(0x0C);
inline const v10::Octets32 kIdentity = repeated(0xA1);
inline const v10::Octets32 kHubKey = repeated(0x01);
inline const v10::Octets32 kFirstSigner = repeated(0x11);
inline const v10::Octets32 kSigner = repeated(0x12);
inline const v10::Octets32 kMachineKey = repeated(0x22);
inline const v10::Octets32 kBuildDigest = repeated(0x33);
inline const v10::Octets32 kRecipient = repeated(0xB1);
inline const v10::Bytes kSignature = v10::Bytes(64, 0x5A);
inline const v10::Bytes kNoSignature = v10::Bytes(64, 0);
inline constexpr std::uint32_t kSeat = 7;
inline constexpr std::uint64_t kValidUntil = 1'200;
inline constexpr std::uint64_t kSignerNonce = 4;

// The accepted predecessor files, defined in `economy_v10_carried.hpp`.
struct Carried;

// The port's own guard, belonging to no vector group: `src/v10/`'s tree is
// version nine's copied, so it is required to reproduce the accepted M1
// accounts tree root over the accepted M1 accounts.
void verify_accounts_tree(const pv::Values& primitives);

// The three check groups, one per translation unit. `values` is always version
// ten's own file; `carried` holds the accepted files that fix the surface
// version ten inherits, so an inherited width, name, or digest is compared
// against the file that accepted it rather than against the live version-nine
// kernel, which a later slice deletes.
void verify_version(const pv::Values& values, const Carried& carried,
                    const pv::Values& manifest);
void verify_state(const pv::Values& values, const Carried& carried);
void verify_kinds(const pv::Values& values, const Carried& carried);
// Every recorded vector is either consulted above or named as owed elsewhere. A
// key in neither set fails, and a deferral that matches nothing fails too, so
// the slice boundary is checkable rather than described.
void verify_coverage(const pv::Values& values);

}  // namespace economy_v10_fixture
