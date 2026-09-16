#pragma once

// The shared fixture behind the version-nine execution checks.
//
// **This trace records what version nine changes and nothing else.** The
// measurement, the winner rule, the mint walk, and every carried transaction are
// fixed by `test-vectors/economy-transition-v8-execution.txt`, so nothing here
// re-records them; what it records is **what a month is worth**.
//
// **The chain runs at ninety seconds a block and that is a fixture choice with a
// reason.** At the commit target a window is exactly one day, so a month is
// about thirty windows and 864,000 heights — more than a recorded trace can run.
// At ninety seconds a window is exactly thirty days, so each window opens in a
// new month and a settlement is reachable in three. Nothing in the contract
// bounds the block rate from above, which `economy-transition-v9` states
// outright, and a seat's figure is `credited_slots * kSlotSeconds`, a function of
// **heights** — so a slower chain changes when a month closes and changes
// nothing about what a machine earned.
//
// **No signature is computed anywhere.** A stand-in is an eight-octet counter
// padded to 64 octets, recorded against the exact key and message it authorizes,
// so a signature presented over any other message is simply absent from the
// table. That is the property every message-binding claim in the contract rests
// on.

#include "protocol/v9/ledger.hpp"

#include "../../tools/protocol-vectors/vector_common.hpp"

#include <cstdint>
#include <map>
#include <set>
#include <span>
#include <string>
#include <vector>

namespace economy_v9_execution {

namespace pv = protocol_vectors;
namespace v9 = protocol::v9;

using Bytes = v9::Bytes;
using Hash = v9::Hash;
using Octets32 = v9::Octets32;

inline Octets32 repeated(std::uint8_t octet) {
  Octets32 value{};
  value.fill(octet);
  return value;
}

inline Octets32 from_hex(const std::string& hex) {
  const auto bytes = pv::hex_decode(hex);
  pv::require(bytes.size() == 32, "expected 32 octets");
  Octets32 value{};
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

inline std::string hex(const Hash& value) {
  return hex(std::span<const std::uint8_t>(value.data(), value.size()));
}

inline std::string hex(const Bytes& value) {
  return hex(std::span<const std::uint8_t>(value.data(), value.size()));
}

// Every vector key this target consults. A key in a section the target claims
// but never reads is the vacuous case `docs/engineering/verification.md` forbids,
// so the entry point compares this set against the file's own keys.
inline std::set<std::string>& consulted() {
  static std::set<std::string> keys;
  return keys;
}

inline const std::string& expect_text(const pv::Values& values,
                                      const std::string& key) {
  const auto found = values.find(key);
  pv::require(found != values.end(), "vector file records no " + key);
  consulted().insert(key);
  return found->second;
}

inline std::uint64_t expect_number(const pv::Values& values,
                                   const std::string& key) {
  const auto& text = expect_text(values, key);
  try {
    return std::stoull(text);
  } catch (const std::exception&) {
    throw std::runtime_error(key + " is not a number: " + text);
  }
}

inline void expect_true(const pv::Values& values, const std::string& key) {
  pv::require(expect_text(values, key) == "true", "the vectors record " + key);
}

inline void agree(const pv::Values& values, const std::string& key,
                  const std::string& derived) {
  pv::require(expect_text(values, key) == derived,
              key + ": derived " + derived + ", recorded " +
                  values.find(key)->second);
}

inline void agree(const pv::Values& values, const std::string& key,
                  std::uint64_t derived) {
  agree(values, key, std::to_string(derived));
}

// --- the recorded fixture's constants ---------------------------------------

inline constexpr std::uint64_t kSupplyLimit = 5'699'395'010'000'000'000;
inline constexpr std::uint64_t kFixedFee = 1'000;
inline constexpr std::uint32_t kNetworkId = 9;
// Version nine's own builders bind this expiry height: the two seat
// transactions, the challenge response, and kind 22.
inline constexpr std::uint64_t kValidUntil = 10'000'000'000;
// **Every builder inherited from version six carries version six's own expiry
// default**, and the split is deliberate rather than untidy: a fixture that
// constructs an unchanged envelope is not a place to keep a second copy of one,
// and the bytes a transaction commits to include the height it expires at.
// Unifying the two produces identical state roots and different transaction
// roots, which is exactly how it fails.
inline constexpr std::uint64_t kInheritedValidUntil = 10'000'000;

inline constexpr std::string_view kManifestDigestHex =
    "af153c99adf7c49e5a92563946cf0e60dfd7a58785462530988f661aa68faaa7";

inline const Octets32 kVerifierKey = repeated(0x55);
inline const Octets32 kDisputeAuthorityKey = repeated(0xD8);
inline const Octets32 kAliceIdentity = repeated(0xA1);
inline const Octets32 kAliceKey = repeated(0xA2);
inline const Octets32 kAliceSignerKey = repeated(0xA3);
inline const Octets32 kBobIdentity = repeated(0xB1);
inline const Octets32 kBobKey = repeated(0xB2);
inline const Octets32 kBobSignerKey = repeated(0xB3);

inline const Hash kAliceEscrow = v9::escrow_id(kAliceIdentity, 0);
inline const Hash kBobEscrow = v9::escrow_id(kBobIdentity, 0);

inline constexpr std::uint32_t kAliceSeat = 0;
inline constexpr std::uint32_t kBobSeat = 1;

// Ninety seconds a block, so a window of 28,800 heights is exactly thirty days.
inline constexpr std::uint64_t kMillisPerBlock = 90'000;
// 2026-01-15T00:00:00Z. A mid-month genesis, so window 0 opens in January,
// window 1 in February, window 2 in March, and so on: each window opens in a
// month of its own, which is what makes a settlement reachable inside three.
inline constexpr std::uint64_t kGenesisMillis = 1'768'435'200'000;

// Both seats activate near the end of window 0, so window 1 is the first window
// either is in scope for.
inline constexpr std::uint64_t kActivationHeight = v9::kCycleBlocks - 10;
inline constexpr std::uint64_t kMeasuredWindow = 1;
// Window 1's assignment is due at the first height of window 3, and that is the
// block in which February closes and the pool first pays.
inline constexpr std::uint64_t kSettlementHeight =
    (kMeasuredWindow + v9::kAssignmentLagWindows + 1) * v9::kCycleBlocks;
// The halt sits between window 2's opening and window 3's, so window 3 opens
// three months later than it otherwise would and its assignment closes one month
// while skipping three. The jump shows up one assignment after the window that
// carries it, so the halted chain runs one window past the settled one.
inline constexpr std::uint64_t kHaltHeight = 2 * v9::kCycleBlocks + 1;
inline constexpr std::uint64_t kHaltMillis = 90ULL * 86'400'000ULL;
inline constexpr std::uint64_t kHaltedTargetHeight =
    kSettlementHeight + v9::kCycleBlocks;

inline std::uint64_t timestamp_of_height(std::uint64_t height) {
  return kGenesisMillis + height * kMillisPerBlock;
}

// A halt is a discontinuity in this function and nothing else. Heights stay
// consecutive, because a network that is down produces no heights at all and
// resumes at the one it stopped at; what moves is the wall.
inline std::uint64_t halted_timestamp_of_height(std::uint64_t height) {
  const auto stamp = timestamp_of_height(height);
  return height >= kHaltHeight ? stamp + kHaltMillis : stamp;
}

// A recorded signature table. Verification is exact-match lookup on
// `(public key, message)`.
class Signatures {
 public:
  Bytes sign(const Octets32& public_key, std::span<const std::uint8_t> message) {
    const auto key = entry_key(public_key, message);
    const auto found = table_.find(key);
    if (found != table_.end()) return found->second;
    const auto issued = static_cast<std::uint64_t>(table_.size());
    Bytes token(v9::kSignatureBytes, 0);
    for (int shift = 56, index = 0; shift >= 0; shift -= 8, ++index) {
      token[static_cast<std::size_t>(index)] =
          static_cast<std::uint8_t>(issued >> shift);
    }
    table_.emplace(key, token);
    return token;
  }

  v9::SignatureVerifier verifier() const {
    return [this](std::span<const std::uint8_t> public_key,
                  std::span<const std::uint8_t> message,
                  std::span<const std::uint8_t> signature) {
      Octets32 key{};
      if (public_key.size() != key.size()) return false;
      std::copy(public_key.begin(), public_key.end(), key.begin());
      const auto found = table_.find(entry_key(key, message));
      if (found == table_.end()) return false;
      return std::equal(found->second.begin(), found->second.end(),
                        signature.begin(), signature.end());
    };
  }

 private:
  static Bytes entry_key(const Octets32& public_key,
                         std::span<const std::uint8_t> message) {
    Bytes key(public_key.begin(), public_key.end());
    key.insert(key.end(), message.begin(), message.end());
    return key;
  }

  std::map<Bytes, Bytes> table_;
};

// One raw input and the label the vectors record its outcome under.
struct Step {
  std::string label;
  Bytes raw;
};

struct Scenario {
  std::string name;
  v9::Ledger ledger;
  std::vector<v9::BlockOutcome> blocks;
  std::vector<std::vector<std::string>> labels;
  // The blocks a quiet run executed because they opened a window or carried an
  // input, kept apart from `blocks` so a scenario can count the audits without
  // the setup segment.
  std::vector<v9::BlockOutcome> audit_blocks;
  std::uint64_t quiet_heights = 0;
  std::uint64_t skipped_blocks = 0;
  std::uint64_t alice_challenged = 0;
  std::uint64_t alice_answered = 0;
  std::uint64_t bob_challenged = 0;
  std::uint64_t bob_answered = 0;
  // The root and the stamp the setup shorthand leaves behind, read before the
  // next block consumes them. They are the only observable consequence of the
  // shorthand carrying the timestamp: the block that follows sets its own.
  Hash root_after_the_shorthand{};
  std::uint64_t timestamp_after_the_shorthand = 0;
};

v9::Genesis trace_genesis();
v9::Ledger open_trace_ledger();

Bytes build(Signatures& signatures, const v9::Ledger& ledger, std::uint8_t kind,
            const Octets32& authority, std::uint64_t nonce, const v9::Body& body,
            std::uint64_t valid_until = kValidUntil,
            std::uint64_t fee_limit = kFixedFee);

Bytes register_input(Signatures& signatures, const v9::Ledger& ledger,
                     const Octets32& identity, const Octets32& hub_key,
                     const Octets32& signer_key);
// **An unreferred seat, which is the whole point of this trace.** A referred
// seat routes its referral leg to its referrer; an unreferred one routes it to
// the pool, so every unit the pool holds here is one the chain created for a
// machine nobody referred.
Bytes purchase_input(Signatures& signatures, const v9::Ledger& ledger,
                     const Octets32& identity, const Octets32& hub_key,
                     const Octets32& signer_key, std::uint32_t seat_id,
                     std::uint64_t nonce);
Bytes activate_input(Signatures& signatures, const v9::Ledger& ledger,
                     const Octets32& identity, const Octets32& hub_key,
                     const Octets32& signer_key, std::uint32_t seat_id,
                     std::uint64_t nonce);
Bytes response_input(Signatures& signatures, const v9::Ledger& ledger,
                     const Octets32& signer_key, std::uint32_t seat_id,
                     std::uint64_t challenge_height, std::uint64_t nonce);
// Kind 22, with the destination's posture confirmation it requires. A default
// posture requires one above its minimum amount and a month's pool is far above
// it, so the mint carries a real HUB signature over version six's `mint-confirm`
// message. `confirm = false` presents the 64 zero octets instead, which against
// a posture that requires one is `BIOMETRIC_REQUIRED`.
Bytes pool_mint_input(Signatures& signatures, const v9::Ledger& ledger,
                      const Octets32& identity, const Octets32& hub_key,
                      const Octets32& signer_key, std::uint32_t seat_id,
                      const Octets32& destination, std::uint64_t nonce,
                      bool confirm = true);

// Execute one block of steps and record what the vectors compare against.
//
// The result is a reference into the scenario's own block list, which a later
// `run` may reallocate, so a caller that keeps it past the next block must take
// a copy.
const v9::BlockOutcome& run(Scenario& scenario, const Signatures& signatures,
                            std::uint64_t timestamp,
                            const std::vector<Step>& steps,
                            const v9::BlockOrder& order = {});

Scenario settled_scenario(Signatures& signatures);
// A second chain of the same shape, run to a chosen height. **Rebuilt rather
// than copied**, because a copy taken from a recorded run would share whatever
// that run had already decided; a chain built the same way from genesis is the
// same chain and is reached independently.
Scenario rebuilt_chain_to(Signatures& signatures, std::uint64_t height);
Scenario halted_scenario(Signatures& signatures);

void verify_scenarios(const pv::Values& values);
// The two orderings ADR 0078 distinguishes, each run on a copy of the same
// block so the accepted reading and the rejected one are compared on identical
// inputs.
void verify_orderings(const pv::Values& values);
// The single pass against an explicit per-index loop over the same state. No
// invariant over a single accepted state separates the two, so what distinguishes
// them is a scenario.
void verify_single_pass(const pv::Values& values);
// The contract file's sections a chain is needed for, which the codec target
// defers to this one by name.
void verify_contract_sections(const pv::Values& contract);
void verify_coverage(const pv::Values& values);

}  // namespace economy_v9_execution
