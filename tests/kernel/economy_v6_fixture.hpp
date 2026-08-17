#pragma once

// The shared fixture behind the version-six codec checks.
//
// The checks are split by subject exactly as the Python verifier for the same
// vector file is — `encoding_checks`, `registry_checks`, `state_checks` — so
// each translation unit reads as one argument. What lives here is only what
// more than one of them needs: the recorded fixture's constants, the accessors
// that make a missing vector key a failure rather than a default, and the two
// economy sets whose roots the vectors fix.

#include "protocol/v6/economy.hpp"

#include "../../tools/protocol-vectors/vector_common.hpp"

#include <algorithm>
#include <cstdint>
#include <span>
#include <string>
#include <vector>

namespace economy_v6_fixture {

namespace pv = protocol_vectors;
namespace v6 = protocol::v6;

inline v6::Octets32 repeated(std::uint8_t octet) {
  v6::Octets32 value{};
  value.fill(octet);
  return value;
}

inline v6::Octets32 ascending(std::uint8_t first) {
  v6::Octets32 value{};
  for (std::size_t index = 0; index < value.size(); ++index) {
    value[index] = static_cast<std::uint8_t>(first + index);
  }
  return value;
}

inline v6::Octets32 from_hex(const std::string& hex) {
  const auto bytes = pv::hex_decode(hex);
  pv::require(bytes.size() == 32, "expected 32 octets");
  v6::Octets32 value{};
  std::copy(bytes.begin(), bytes.end(), value.begin());
  return value;
}

inline v6::Octets32 to_octets(const v6::Hash& value) {
  v6::Octets32 result{};
  std::copy(value.begin(), value.end(), result.begin());
  return result;
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

inline std::string hex(const v6::Hash& value) {
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

// The checked-in fixture's constants, restated. They are repeated or ascending
// octets by design, so restating them is transcription rather than derivation,
// and every value they feed is compared against the recorded file.
inline const v6::Octets32 kChainId = ascending(0);
inline const v6::Octets32 kUnregisteredRecipient = ascending(0x20);
inline const v6::Octets32 kAliceIdentity = repeated(0xA1);
inline const v6::Octets32 kAliceKey = repeated(0xA2);
inline const v6::Octets32 kAliceSignerKey = repeated(0xA3);
inline const v6::Octets32 kAliceSecondSignerKey = repeated(0xA4);
inline const v6::Octets32 kBobIdentity = repeated(0xB1);
inline const v6::Octets32 kBobKey = repeated(0xB2);
inline const v6::Octets32 kBobSignerKey = repeated(0xB3);
inline const v6::Octets32 kMariaIdentity = repeated(0xC1);
inline const v6::Octets32 kMariaKey = repeated(0xC2);
inline const v6::Octets32 kMariaNewSignerKey = repeated(0xC4);
inline const v6::Octets32 kVerifierKey = repeated(0x55);
inline const v6::Octets32 kDecisionId = repeated(0x11);
inline const v6::Octets32 kSingletonBeneficiary = repeated(0x00);

inline constexpr std::uint64_t kFeeLimit = 1'000;
inline constexpr std::uint64_t kValidUntil = 42;
inline constexpr std::uint64_t kRegistrationHeight = 5 * v6::kCycleBlocks;
inline constexpr std::uint64_t kEnrolledWindow = 5;
inline constexpr std::uint64_t kCurrentMark = 199;
inline constexpr std::uint64_t kCycleWindow = 200;
inline constexpr std::uint64_t kOutageWindow = 201;
inline constexpr std::uint64_t kSeatActivationHeight = 7 * v6::kCycleBlocks;
inline constexpr std::uint64_t kReferralLegAtomic = 3'420'000'000;
inline constexpr std::uint64_t kMaximumSupplyAtomic = 5'699'395'010'000'000'000ULL;

inline const v6::Hash kAliceFirstEscrow = v6::escrow_id(kAliceIdentity, 0);
inline const v6::Hash kAliceSecondEscrow = v6::escrow_id(kAliceIdentity, 1);
inline const v6::Hash kAliceThirdEscrow = v6::escrow_id(kAliceIdentity, 2);
inline const v6::Hash kBobEscrow = v6::escrow_id(kBobIdentity, 0);
inline const v6::Hash kMariaEscrow = v6::escrow_id(kMariaIdentity, 0);

// The accepted version-one transfer, expressed as a version-six kind 1. Its
// recipient is the value the accepted vectors record, which is deliberately not
// a registered escrow in this fixture.
inline v6::Envelope transfer_envelope(const v6::Octets32& recipient,
                                      std::uint64_t amount) {
  v6::Envelope envelope;
  envelope.kind = static_cast<std::uint8_t>(v6::Kind::native_transfer);
  envelope.chain_id = kChainId;
  envelope.scheme = v6::kSchemeSigner;
  envelope.nonce = 1;
  envelope.fee_limit = kFeeLimit;
  envelope.valid_until_height = kValidUntil;
  envelope.body.insert(envelope.body.end(), recipient.begin(), recipient.end());
  for (int shift = 56; shift >= 0; shift -= 8) {
    envelope.body.push_back(static_cast<std::uint8_t>(amount >> shift));
  }
  return envelope;
}

// A well-formed envelope of any kind, with the one scheme its kind permits and
// the two fields a registration is required to leave at zero.
inline v6::Envelope body_envelope(v6::Kind kind, std::uint8_t fill = 0) {
  const auto number = static_cast<std::uint8_t>(kind);
  const bool registration = kind == v6::Kind::hub_register;
  v6::Envelope envelope;
  envelope.kind = number;
  envelope.chain_id = kChainId;
  envelope.scheme = *v6::kind_scheme(number);
  envelope.nonce = registration ? 0 : 1;
  envelope.fee_limit = registration ? 0 : kFeeLimit;
  envelope.valid_until_height = kValidUntil;
  envelope.body.assign(*v6::body_bytes(number), fill);
  return envelope;
}

// The ten channels, the ten carries, and the three singletons genesis writes.
// Writing the fixed tables explicitly is what keeps an absent entry unambiguous
// rather than making absence an implicit zero default.
inline std::vector<v6::EconomyEntry> genesis_economy() {
  std::vector<v6::EconomyEntry> entries;
  for (std::uint8_t channel = 0; channel < 10; ++channel) {
    entries.push_back({v6::channel_key(channel), v6::channel_value(0, 0)});
    entries.push_back({v6::carry_key(channel), v6::carry_value(0)});
  }
  entries.push_back({v6::verifier_key_key(), v6::verifier_key_value(kVerifierKey)});
  entries.push_back({v6::unreferred_pool_key(), v6::unreferred_pool_value(0, 0)});
  entries.push_back(
      {v6::verified_user_counter_key(), v6::verified_user_counter_value(0)});
  return entries;
}

// The registry fixture, transcribed from the recorded scenario: Alice with
// three escrow indexes of which one is deleted and two signers on her first,
// Bob with one of each, and Maria who has lost every signer she held and
// recovered by assigning a new one with her identity alone.
inline void append_registry(std::vector<v6::EconomyEntry>& entries) {
  auto identity = [&](const v6::Octets32& hash, const v6::Octets32& key,
                      std::uint64_t height, std::uint32_t next_index,
                      std::uint32_t live, std::uint32_t seats) {
    v6::HubIdentityRecord record;
    record.hub_public_key = key;
    record.registered_at_height = height;
    record.next_escrow_index = next_index;
    record.escrow_count = live;
    record.seat_count = seats;
    entries.push_back({v6::hub_identity_key(hash), v6::hub_identity_value(record)});
  };
  auto escrow = [&](const v6::Hash& identifier, const v6::Octets32& owner,
                    const v6::Posture& posture, std::uint32_t signers) {
    v6::EscrowRecord record;
    record.owner_hub_identity = owner;
    record.posture = posture;
    record.signer_count = signers;
    entries.push_back({v6::escrow_key(identifier), v6::escrow_value(record)});
  };
  auto signer = [&](const v6::Octets32& key, const v6::Hash& assigned) {
    entries.push_back({v6::signer_key(v6::signer_id(key)), v6::signer_value(assigned)});
  };
  auto enrollment = [&](const v6::Octets32& hash, std::uint64_t height) {
    v6::EnrollmentRecord record;
    record.enrolled_at_height = height;
    record.minted_through_window = v6::window_of_height(height);
    record.issued_atomic = v6::kVerifiedUserDailyAtomic;
    entries.push_back({v6::verified_user_key(hash), v6::verified_user_value(record)});
  };

  // Alice's index reached 3 and her live count fell to 2, which is what shows a
  // deleted identifier is never reissued.
  identity(kAliceIdentity, kAliceKey, kRegistrationHeight, 3, 2, 1);
  identity(kBobIdentity, kBobKey, kRegistrationHeight + 1, 1, 1, 0);
  identity(kMariaIdentity, kMariaKey, kRegistrationHeight + 2, 1, 1, 0);

  v6::Posture relaxed_minimum;
  relaxed_minimum.min_amount_atomic = 100'000'000;
  escrow(kAliceFirstEscrow, kAliceIdentity, v6::Posture{}, 2);
  // An escrow with no signer at all is reachable, because kind 13 creates one
  // and kind 15 is what assigns a signer to it.
  escrow(kAliceSecondEscrow, kAliceIdentity, relaxed_minimum, 0);
  escrow(kBobEscrow, kBobIdentity, v6::Posture{}, 1);
  escrow(kMariaEscrow, kMariaIdentity, v6::Posture{}, 1);

  signer(kAliceSignerKey, kAliceFirstEscrow);
  signer(kAliceSecondSignerKey, kAliceFirstEscrow);
  signer(kBobSignerKey, kBobEscrow);
  // Maria's lost signer is revoked and absent; her new one is the whole of the
  // recovery path.
  signer(kMariaNewSignerKey, kMariaEscrow);

  enrollment(kAliceIdentity, kRegistrationHeight);
  enrollment(kBobIdentity, kRegistrationHeight + 1);
  enrollment(kMariaIdentity, kRegistrationHeight + 2);
}

// One entry of every assigned kind, so one recorded root constrains all
// fourteen value encodings rather than five.
inline std::vector<v6::EconomyEntry> populated_economy(
    const pv::Values& version_three) {
  auto entries = genesis_economy();
  // The registry's counter supersedes genesis's zero rather than sitting beside
  // it, so the entry is replaced in place and the set stays a map.
  std::erase_if(entries, [](const v6::EconomyEntry& entry) {
    return entry.key == v6::verified_user_counter_key();
  });
  append_registry(entries);
  entries.push_back(
      {v6::verified_user_counter_key(), v6::verified_user_counter_value(3)});

  v6::SeatRecord activated;
  activated.hub_identity_hash = kAliceIdentity;
  activated.has_referrer = true;
  activated.referrer_hub_identity = kBobIdentity;
  activated.is_activated = true;
  activated.activation_height = kSeatActivationHeight;
  activated.minted_through_window = kCurrentMark;
  entries.push_back({v6::seat_key(0), v6::seat_value(activated)});

  v6::SeatRecord purchased;
  purchased.hub_identity_hash = kAliceIdentity;
  entries.push_back({v6::seat_key(v6::kMaxSeatId), v6::seat_value(purchased)});

  entries.push_back({v6::referral_balance_key(kBobIdentity),
                     v6::referral_balance_value(kReferralLegAtomic * 3,
                                                kReferralLegAtomic, kCurrentMark)});
  entries.push_back({v6::direct_decision_key(kDecisionId), {}});
  entries.push_back({v6::typed_custody_key(1, kSingletonBeneficiary),
                     v6::typed_custody_value(17'100'000'000)});

  // The settlement is version three's, imported rather than reimplemented, so
  // the two records it wrote for this population are taken from version three's
  // own accepted file and required to be the bytes version six carries.
  entries.push_back({v6::cycle_assignment_key(kCycleWindow),
                     pv::hex_decode(version_three.at("cycle.assignment_value_hex"))});
  entries.push_back({v6::cycle_assignment_key(kOutageWindow),
                     pv::hex_decode(version_three.at("outage.assignment_value_hex"))});
  return entries;
}

// The three accounts `protocol-primitives-v1` records, read from that file
// rather than restated, so the accounts tree is checked against a third source.
inline std::vector<v6::AccountEntry> accepted_accounts(const pv::Values& primitives) {
  std::vector<v6::AccountEntry> accounts;
  for (int index = 0; index < 3; ++index) {
    const auto entry = primitives.at("state.account" + std::to_string(index));
    v6::AccountEntry account;
    account.account_id = from_hex(entry.substr(0, 64));
    account.balance = std::stoull(entry.substr(64, 16), nullptr, 16);
    account.nonce = std::stoull(entry.substr(80, 16), nullptr, 16);
    accounts.push_back(account);
  }
  return accounts;
}

// The four check groups, one per translation unit.
void verify_encoding(const pv::Values& values, const pv::Values& primitives);
void verify_identity(const pv::Values& values, const pv::Values& primitives);
void verify_state(const pv::Values& values, const pv::Values& primitives,
                  const pv::Values& version_three, const pv::Values& manifest);
void verify_settlement(const pv::Values& values, const pv::Values& version_three);

}  // namespace economy_v6_fixture
