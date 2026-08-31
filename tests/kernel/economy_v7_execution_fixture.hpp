#pragma once

// The shared fixture behind the version-seven execution checks.
//
// The kernel must reproduce `test-vectors/economy-transition-v7-execution.txt`,
// which records five scenarios executed against a real state. Reproducing a
// recorded outcome means rebuilding the exact transactions that produced it, so
// this header holds the trace's constants, its recorded signature table, and the
// builders the scenarios share — the C++ counterpart of
// `simulation/economy_transition_v7/trace.py`.
//
// **No signature is computed anywhere.** A stand-in is an eight-octet counter
// padded to 64 octets, recorded against the exact key and message it authorizes,
// so a signature presented over any other message is simply absent from the
// table. The one real signature in the trace is the accepted version-one
// transfer's, adopted from `test-vectors/protocol-primitives-v1.txt`. The
// counter is issued in the order the model issues it, because a transaction ID
// is a digest over the signature bytes and a different order would produce a
// different receipt.

#include "protocol/v7/ledger.hpp"

#include "../../tools/protocol-vectors/vector_common.hpp"

#include <algorithm>
#include <cstdint>
#include <map>
#include <set>
#include <string>
#include <vector>

namespace economy_v7_execution {

namespace pv = protocol_vectors;
namespace v7 = protocol::v7;

using v7::Bytes;
using v7::Hash;
using v7::Octets32;

inline Octets32 repeated(std::uint8_t octet) {
  Octets32 value{};
  value.fill(octet);
  return value;
}

inline Octets32 ascending(std::uint8_t first) {
  Octets32 value{};
  for (std::size_t index = 0; index < value.size(); ++index) {
    value[index] = static_cast<std::uint8_t>(first + index);
  }
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

// Every vector key this test consults. A key in a section the test claims but
// never reads is the vacuous case `docs/engineering/verification.md` forbids —
// the file would gain a vector and nothing here would notice — so the entry
// point compares this set against the file's own keys.
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

inline std::uint64_t expect_number(const pv::Values& values,
                                   const std::string& key) {
  return std::stoull(expect_text(values, key));
}

inline void expect_true(const pv::Values& values, const std::string& key) {
  pv::require(expect_text(values, key) == "true", "the vectors record " + key);
}

inline void agree(const pv::Values& values, const std::string& key,
                  const std::string& derived) {
  pv::require(expect_text(values, key) == derived,
              key + ": derived " + derived + ", recorded " +
                  expect_text(values, key));
}

inline void agree(const pv::Values& values, const std::string& key,
                  std::uint64_t derived) {
  agree(values, key, std::to_string(derived));
}

// --- the recorded fixture's constants ---------------------------------

inline constexpr std::uint64_t kSupplyLimit = 5'699'395'010'000'000'000;
inline constexpr std::uint64_t kFixedFee = 1'000;
inline constexpr std::uint32_t kNetworkId = 7;
// Version seven's own builders bind this expiry height.
inline constexpr std::uint64_t kValidUntil = 10'000'000'000;
// **Three builders are version six's, imported rather than restated**, and they
// carry version six's own expiry default rather than version seven's: a fixture
// that constructs an unchanged envelope is not a place to keep a second copy of
// one, and the bytes a transaction commits to include the height it expires at.
inline constexpr std::uint64_t kInheritedValidUntil = 10'000'000;
inline constexpr std::uint64_t kPostureMinimum = 1'000'000;
inline constexpr std::uint64_t kTransferAmount = 1'000'000;

// The version-three manifest version seven binds, whose digest is inside every
// chain identity these scenarios derive.
inline constexpr std::string_view kManifestDigestHex =
    "af153c99adf7c49e5a92563946cf0e60dfd7a58785462530988f661aa68faaa7";

inline const Octets32 kVerifierKey = repeated(0x55);
inline const Octets32 kAliceIdentity = repeated(0xA1);
inline const Octets32 kAliceKey = repeated(0xA2);
inline const Octets32 kAliceSignerKey = repeated(0xA3);
inline const Octets32 kFreshSignerKey = repeated(0xA4);
inline const Octets32 kBobIdentity = repeated(0xB1);
inline const Octets32 kBobKey = repeated(0xB2);
inline const Octets32 kBobSignerKey = repeated(0xB3);
inline const Octets32 kCarolIdentity = repeated(0xE1);
inline const Octets32 kCarolKey = repeated(0xE2);
inline const Octets32 kCarolSignerKey = repeated(0xE3);

// Values only the transition checks use. Those derive their own expectations,
// because they reach rejection conditions no recorded scenario does and there is
// no vector to compare against.
inline const Octets32 kAliceSecondSignerKey = repeated(0xA5);
inline const Octets32 kMariaIdentity = repeated(0xC1);
inline const Octets32 kMariaKey = repeated(0xC2);
inline const Octets32 kMariaNewSignerKey = repeated(0xC4);
inline const Octets32 kDecisionId = repeated(0x11);

inline const Hash kAliceEscrow = v7::escrow_id(kAliceIdentity, 0);
inline const Hash kAliceSecondEscrow = v7::escrow_id(kAliceIdentity, 1);
inline const Hash kBobEscrow = v7::escrow_id(kBobIdentity, 0);
inline const Hash kCarolEscrow = v7::escrow_id(kCarolIdentity, 0);

// The accepted version-one transfer's recipient, which is deliberately not a
// registered escrow in any of these scenarios.
inline const Octets32 kAcceptedRecipient = ascending(0x20);

inline constexpr std::uint32_t kAliceSeat = 0;
inline constexpr std::uint32_t kBobSeat = 1;
inline constexpr std::uint32_t kCarolSeat = 2;

// Scenarios one and two. Window 200 is the cycle nobody wins and window 201 is
// the cycle that absorbs what window 200 left behind.
inline constexpr std::uint64_t kDeadWindow = 200;
inline constexpr std::uint64_t kWonWindow = kDeadWindow + 1;
// Scenario three, on its own chain, far enough from the first two that a reader
// cannot mistake one schedule for the other.
inline constexpr std::uint64_t kStrandedWindow = 300;
inline constexpr std::uint64_t kDrainedWindow = kStrandedWindow + 1;
// Scenario five.
inline constexpr std::uint64_t kReferredWindow = 400;

inline constexpr std::uint64_t kMetUptimeSeconds = 72'000;
inline constexpr std::uint64_t kFailedUptimeSeconds = 7'200;

// Thirty windows is the verified-user cap, so a collection at this height
// forfeits the ten older windows and collects the most recent thirty.
inline constexpr std::uint64_t kCollectionHeight = 40 * v7::kCycleBlocks;

// The height at which `window`'s assignment is due: the first of `w + 2`.
inline constexpr std::uint64_t boundary_height(std::uint64_t window) {
  return (window + v7::kAssignmentLagWindows) * v7::kCycleBlocks;
}

// A height inside the window before `first_window`, so the mark a seat's
// activation writes is that one and its first collectable cycle is
// `first_window`.
inline constexpr std::uint64_t activation_height(std::uint64_t first_window) {
  return (first_window - 1) * v7::kCycleBlocks + 10;
}

// A recorded signature table. Verification is exact-match lookup on
// `(public key, message)`, which is the property every message-binding claim in
// the contract rests on: a signature over a different message is absent and
// therefore invalid.
class Signatures {
 public:
  Bytes sign(const Octets32& public_key, std::span<const std::uint8_t> message) {
    const auto key = entry_key(public_key, message);
    const auto found = table_.find(key);
    if (found != table_.end()) return found->second;
    // The counter is the number of pairs the table already holds, adopted ones
    // included. An adopted signature therefore consumes a number even though it
    // was not issued, which is what keeps this table's stand-ins byte-identical
    // to the model's.
    const auto issued = static_cast<std::uint64_t>(table_.size());
    Bytes token(v7::kSignatureBytes, 0);
    for (int shift = 56, index = 0; shift >= 0; shift -= 8, ++index) {
      token[static_cast<std::size_t>(index)] =
          static_cast<std::uint8_t>(issued >> shift);
    }
    table_.emplace(key, token);
    return token;
  }

  // Record a signature this fixture did not choose — the accepted one.
  Bytes adopt(const Octets32& public_key, std::span<const std::uint8_t> message,
              const Bytes& signature) {
    table_[entry_key(public_key, message)] = signature;
    return signature;
  }

  v7::SignatureVerifier verifier() const {
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

// One raw input and the label the vectors record its outcome under. `admits` is
// false for an input the trace offers in order to be refused at admission: such
// an input produces no receipt and never enters the transaction root.
struct Step {
  std::string label;
  Bytes raw;
  bool admits = true;
};

struct Scenario {
  std::string name;
  v7::Ledger ledger;
  std::vector<v7::BlockOutcome> blocks;
  std::vector<std::vector<std::string>> labels;
  std::map<std::string, std::uint8_t> rejected;
  std::vector<std::size_t> raw_inputs;
  // The exact bytes each block was executed over, retained so a caller outside
  // this fixture can execute the same block somewhere else. The storage tests
  // replay a scenario's contiguous run through a real database and require the
  // recorded roots, which is a question the counts above cannot be asked.
  std::vector<std::vector<Bytes>> block_inputs;
  std::uint64_t skipped_blocks = 0;
  // The figures the vectors record at named points of a scenario, keyed by the
  // vector's own name without its scenario prefix. Every one is compared, so a
  // note this fixture stops recording fails the coverage check rather than
  // disappearing quietly.
  std::map<std::string, std::string> notes;
};

v7::Genesis trace_genesis();
v7::Ledger open_trace_ledger(const Octets32* chain_id = nullptr);

// Build one signed transaction the way the model does: the envelope signature is
// issued after every signature its body carries, because the body is complete
// before the envelope that contains it can be encoded.
Bytes build(Signatures& signatures, const v7::Ledger& ledger, std::uint8_t kind,
            const Octets32& authority, std::uint64_t nonce, const v7::Body& body,
            std::uint64_t valid_until = kValidUntil,
            std::uint64_t fee_limit = kFixedFee);

Bytes register_input(Signatures& signatures, const v7::Ledger& ledger,
                     const Octets32& identity, const Octets32& hub_key,
                     const Octets32& signer_key,
                     std::uint64_t valid_until = kValidUntil);
Bytes transfer_input(Signatures& signatures, const v7::Ledger& ledger,
                     const Octets32& signer_key, std::uint64_t nonce,
                     const Octets32& recipient, std::uint64_t amount);
Bytes confirmed_transfer_input(Signatures& signatures, const v7::Ledger& ledger,
                              std::uint64_t nonce, const Octets32& recipient,
                              std::uint64_t amount, const Octets32& identity,
                              const Octets32& hub_key,
                              const Octets32& signer_key,
                              const Octets32& escrow,
                              std::uint64_t valid_until = kInheritedValidUntil);
Bytes verified_user_mint_input(Signatures& signatures, const v7::Ledger& ledger,
                               const Octets32& identity, std::uint64_t nonce,
                               const Octets32& destination,
                               const Octets32& hub_key,
                               const Octets32& signer_key,
                               std::uint64_t valid_until = kInheritedValidUntil);
Bytes posture_input(Signatures& signatures, const v7::Ledger& ledger,
                    std::uint64_t nonce, const v7::Posture& posture, bool signed_,
                    const Octets32& identity, const Octets32& hub_key,
                    const Octets32& signer_key, const Octets32& escrow,
                    std::uint64_t valid_until = kInheritedValidUntil);
// The four seat transactions, which version seven is the first kernel to run.
Bytes purchase_input(Signatures& signatures, const v7::Ledger& ledger,
                     const Octets32& identity, const Octets32& hub_key,
                     const Octets32& signer_key, std::uint32_t seat_id,
                     std::uint64_t nonce, const Octets32* referrer = nullptr);
Bytes activate_input(Signatures& signatures, const v7::Ledger& ledger,
                     const Octets32& identity, const Octets32& hub_key,
                     const Octets32& signer_key, std::uint32_t seat_id,
                     std::uint64_t nonce);
Bytes node_mint_input(Signatures& signatures, const v7::Ledger& ledger,
                      const Octets32& identity, const Octets32& hub_key,
                      const Octets32& signer_key, std::uint32_t seat_id,
                      const Octets32& destination, std::uint64_t nonce);
Bytes referral_mint_input(Signatures& signatures, const v7::Ledger& ledger,
                          const Octets32& identity, const Octets32& hub_key,
                          const Octets32& signer_key,
                          const Octets32& destination, std::uint64_t nonce);

// Execute one block of steps and record what the vectors compare against.
//
// The result is a reference into the scenario's own block list, which a later
// `run` may reallocate, so **a caller that keeps it past the next block must
// take a copy**. GCC 13's `-Wdangling-reference` says so at every call site and
// it is right to: the scenarios bind by value for exactly that reason.
//
// `assignment_is_prologue` is false only where the boundary scenario runs the
// ordering version six rejected by argument. It is not a configuration option a
// chain has.
const v7::BlockOutcome& run(Scenario& scenario, const Signatures& signatures,
                            const std::vector<Step>& steps,
                            const v7::UptimeSchedule* uptime = nullptr,
                            bool assignment_is_prologue = true);
// Stand in for a run of empty blocks between two segments of a trace: an empty
// block advances height and commits the empty transaction root, so a run of them
// changes height and nothing else.
void advance_to(Scenario& scenario, std::uint64_t height);
// Advance to the block before the one at which `window`'s assignment is due.
void advance_to_boundary(Scenario& scenario, std::uint64_t window);

Scenario pool_scenario(Signatures& signatures);
Scenario boundary_scenario(Signatures& signatures);
Scenario permanence_scenario(Signatures& signatures);
Scenario carried_scenario(Signatures& signatures);
Scenario referral_scenario(Signatures& signatures);

void verify_scenarios(const pv::Values& values);
// Every recorded vector must have been consulted. Version six's execution checks
// named three exempt sections because the four seat transitions and the
// settlement were unwritten; this slice wrote them, so nothing is exempt.
void verify_coverage(const pv::Values& values);
// The rejection conditions no recorded scenario reaches. These derive their own
// expectations, because there is no vector to compare against; they are kept in
// their own translation unit so the two kinds of evidence never blur.
void verify_transitions();
void verify_derivations(const pv::Values& values, const pv::Values& primitives,
                        const pv::Values& ledger_vectors,
                        const pv::Values& manifest, const pv::Values& version_three);

}  // namespace economy_v7_execution
