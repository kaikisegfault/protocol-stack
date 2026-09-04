#pragma once

// The shared fixture behind the version-eight codec checks.
//
// The checks are split by subject exactly as the Python verifier for the same
// vector file is — `version_checks`, `state_checks`, `selection_checks` — so
// each translation unit reads as one argument. What lives here is only what
// more than one of them needs: the recorded fixture's constants, the accessors
// that make a missing vector key a failure rather than a default, and the
// fourteen economy entries genesis writes.
//
// **Nothing in the fixture is founder-directed.** The keys and the network
// identifier are arbitrary octets chosen to be distinguishable in a hex dump,
// and every founder figure the checks touch is read from an accepted vector
// file rather than restated here.

#include "protocol/v8/economy.hpp"

#include "../../tools/protocol-vectors/vector_common.hpp"

#include <cstdint>
#include <span>
#include <string>
#include <vector>

namespace economy_v8_fixture {

namespace pv = protocol_vectors;
namespace v8 = protocol::v8;

inline v8::Octets32 repeated(std::uint8_t octet) {
  v8::Octets32 value{};
  value.fill(octet);
  return value;
}

inline v8::Octets32 ascending(std::uint8_t first) {
  v8::Octets32 value{};
  for (std::size_t index = 0; index < value.size(); ++index) {
    value[index] = static_cast<std::uint8_t>(first + index);
  }
  return value;
}

inline v8::Octets32 from_hex(const std::string& hex) {
  const auto bytes = pv::hex_decode(hex);
  pv::require(bytes.size() == 32, "expected 32 octets");
  v8::Octets32 value{};
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

inline std::string hex(const v8::Hash& value) {
  return hex(std::span<const std::uint8_t>(value.data(), value.size()));
}

// A missing key is a failure rather than a skip, because a check that can
// quietly not run is the vacuous kind `docs/engineering/verification.md`
// forbids.
inline std::uint64_t expect_number(const pv::Values& values,
                                   const std::string& key) {
  const auto found = values.find(key);
  pv::require(found != values.end(), "vector file records no " + key);
  return std::stoull(found->second);
}

inline std::size_t expect_size(const pv::Values& values, const std::string& key) {
  return static_cast<std::size_t>(expect_number(values, key));
}

inline const std::string& expect_text(const pv::Values& values,
                                      const std::string& key) {
  const auto found = values.find(key);
  pv::require(found != values.end(), "vector file records no " + key);
  return found->second;
}

inline void expect_true(const pv::Values& values, const std::string& key) {
  pv::require(expect_text(values, key) == "true", "the vectors record " + key);
}

inline constexpr std::uint32_t kNetworkId = 8;
inline constexpr std::uint64_t kSupplyLimit = 5'699'395'010'000'000'000ULL;
inline constexpr std::uint64_t kFixedTransferFee = 1'000;
inline constexpr std::uint64_t kRootHeight = 12;

inline const v8::Octets32 kVerifierKey = repeated(0xA1);
inline const v8::Octets32 kDisputeAuthorityKey = repeated(0xD8);
inline const v8::Octets32 kBeacon = ascending(0);

// Window 1, slot 0, comfortably before the excluded tail of the slot.
inline constexpr std::uint64_t kMeasuredWindow = 1;
inline constexpr std::uint64_t kChallengeHeight = v8::kCycleBlocks + 40;
inline constexpr std::uint32_t kProbeSeat = 7;
// The sampling rate is a property of a stated sample rather than a claim about
// every beacon, so the sample is fixed and recorded.
inline constexpr std::uint32_t kSampleSeats = 400;

// The recorded fixture's genesis. The manifest digest is read from the accepted
// manifest file rather than restated, so a founder figure lives in exactly one
// place.
inline v8::Genesis fixture_genesis(const v8::Octets32& manifest_digest) {
  v8::Genesis genesis;
  genesis.network_id = kNetworkId;
  genesis.supply_limit = kSupplyLimit;
  genesis.fixed_transfer_fee = kFixedTransferFee;
  genesis.manifest_digest = manifest_digest;
  genesis.verifier_key = kVerifierKey;
  genesis.dispute_authority_key = kDisputeAuthorityKey;
  return genesis;
}

// The ten channels, the empty recovery pool, and the three singletons genesis
// writes: version seven's fourteen, unchanged. The dispute authority key is a
// genesis field bound into the chain identity rather than a state entry,
// exactly as `network_id` and `supply_limit` are, so version eight's two entry
// kinds are absent at genesis and the check below requires it.
inline std::vector<v8::EconomyEntry> genesis_economy(
    const v8::Octets32& verifier_key = kVerifierKey) {
  std::vector<v8::EconomyEntry> entries;
  for (std::uint8_t channel = 0; channel < 10; ++channel) {
    entries.push_back({v8::channel_key(channel), v8::channel_value(0, 0)});
  }
  entries.push_back({v8::recovery_pool_key(), v8::recovery_pool_value({})});
  entries.push_back({v8::verifier_key_key(), v8::verifier_key_value(verifier_key)});
  entries.push_back({v8::unreferred_pool_key(), v8::unreferred_pool_value(0, 0)});
  entries.push_back(
      {v8::verified_user_counter_key(), v8::verified_user_counter_value(0)});
  return entries;
}

// The four check groups, one per translation unit. `values` is always version
// eight's own file; `carried_seven` and `carried_six` are the accepted files
// that fix the surface version eight inherits, so an inherited width or name is
// compared against the file that accepted it rather than re-recorded under a
// version-eight name.
// The three accounts `protocol-primitives-v1` records, read from that file
// rather than restated, so the accounts tree is checked against a third source.
inline std::vector<v8::AccountEntry> accepted_accounts(const pv::Values& primitives) {
  std::vector<v8::AccountEntry> accounts;
  for (int index = 0; index < 3; ++index) {
    const auto entry = primitives.at("state.account" + std::to_string(index));
    v8::AccountEntry account;
    account.account_id = from_hex(entry.substr(0, 64));
    account.balance = std::stoull(entry.substr(64, 16), nullptr, 16);
    account.nonce = std::stoull(entry.substr(80, 16), nullptr, 16);
    accounts.push_back(account);
  }
  return accounts;
}

void verify_accounts_tree(const pv::Values& primitives);
void verify_version(const pv::Values& values, const pv::Values& carried_seven,
                    const pv::Values& manifest, const pv::Values& primitives);
void verify_state(const pv::Values& values, const pv::Values& carried_seven);
void verify_kinds(const pv::Values& values, const pv::Values& carried_six);
void verify_selection(const pv::Values& values);

}  // namespace economy_v8_fixture
