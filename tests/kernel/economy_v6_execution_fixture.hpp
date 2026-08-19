#pragma once

// The shared fixture behind the version-six execution checks.
//
// The kernel must reproduce `test-vectors/economy-transition-v6-execution.txt`,
// which records six scenarios executed against a real state. Reproducing a
// recorded outcome means rebuilding the exact transactions that produced it, so
// this header holds the trace's constants, its recorded signature table, and the
// builders the scenarios share — the C++ counterpart of
// `simulation/economy_transition_v6/trace.py`.
//
// **No signature is computed anywhere.** A stand-in is an eight-octet counter
// padded to 64 octets, recorded against the exact key and message it authorizes,
// so a signature presented over any other message is simply absent from the
// table. The one real signature in the trace is the accepted version-one
// transfer's, adopted from `test-vectors/protocol-primitives-v1.txt`. The
// counter is issued in the order the model issues it, because a transaction ID
// is a digest over the signature bytes and a different order would produce a
// different receipt.

#include "protocol/v6/ledger.hpp"

#include "../../tools/protocol-vectors/vector_common.hpp"

#include <algorithm>
#include <cstdint>
#include <map>
#include <set>
#include <string>
#include <vector>

namespace economy_v6_execution {

namespace pv = protocol_vectors;
namespace v6 = protocol::v6;

using v6::Bytes;
using v6::Hash;
using v6::Octets32;

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
inline constexpr std::uint32_t kNetworkId = 6;
inline constexpr std::uint64_t kValidUntil = 10'000'000;
inline constexpr std::uint64_t kPostureMinimum = 1'000'000;
inline constexpr std::uint64_t kTransferAmount = 1'000'000;
inline constexpr std::uint64_t kCollectionHeight = 40 * v6::kCycleBlocks;
inline constexpr std::uint64_t kAssignedWindow = 200;
inline constexpr std::uint64_t kActivationHeight =
    (kAssignedWindow - 1) * v6::kCycleBlocks + 10;

inline const Octets32 kVerifierKey = repeated(0x55);
inline const Octets32 kAliceIdentity = repeated(0xA1);
inline const Octets32 kAliceKey = repeated(0xA2);
inline const Octets32 kAliceSignerKey = repeated(0xA3);
inline const Octets32 kBobIdentity = repeated(0xB1);
inline const Octets32 kBobKey = repeated(0xB2);
inline const Octets32 kBobSignerKey = repeated(0xB3);
inline const Octets32 kCarolIdentity = repeated(0xE1);
inline const Octets32 kCarolKey = repeated(0xE2);
inline const Octets32 kMariaIdentity = repeated(0xC1);
inline const Octets32 kMariaKey = repeated(0xC2);
inline const Octets32 kMariaLostSignerKey = repeated(0xC3);
inline const Octets32 kMariaNewSignerKey = repeated(0xC4);
inline const Octets32 kDaveIdentity = repeated(0xD1);
inline const Octets32 kDaveKey = repeated(0xD2);
inline const Octets32 kDaveSignerKey = repeated(0xD3);

// The accepted version-one transfer, from `test-vectors/protocol-primitives-v1`.
inline const Octets32 kAcceptedChainId = ascending(0);
inline const Octets32 kAcceptedRecipient = ascending(0x20);
inline const Octets32 kAcceptedIdentity = repeated(0xF1);
inline const Octets32 kAcceptedHubKey = repeated(0xF2);
inline constexpr std::uint64_t kAcceptedNonce = 1;
inline constexpr std::uint64_t kAcceptedAmount = 1'000'000;
inline constexpr std::uint64_t kAcceptedFeeLimit = 1'000;
inline constexpr std::uint64_t kAcceptedValidUntil = 42;

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
    Bytes token(v6::kSignatureBytes, 0);
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

  v6::SignatureVerifier verifier() const {
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
  v6::Ledger ledger;
  std::vector<v6::BlockOutcome> blocks;
  std::vector<std::vector<std::string>> labels;
  std::map<std::string, std::uint8_t> rejected;
  std::vector<std::size_t> raw_inputs;
  std::uint64_t skipped_blocks = 0;
};

v6::Genesis trace_genesis();
v6::Ledger open_trace_ledger(const Octets32* chain_id = nullptr);

// Build one signed transaction the way the model does: the envelope signature is
// issued after every signature its body carries, because the body is complete
// before the envelope that contains it can be encoded.
Bytes build(Signatures& signatures, const v6::Ledger& ledger, std::uint8_t kind,
            const Octets32& authority, std::uint64_t nonce, const v6::Body& body,
            std::uint64_t valid_until = kValidUntil,
            std::uint64_t fee_limit = kFixedFee);

Bytes register_input(Signatures& signatures, const v6::Ledger& ledger,
                     const Octets32& identity, const Octets32& hub_key,
                     const Octets32& signer_key,
                     std::uint64_t valid_until = kValidUntil);
Bytes transfer_input(Signatures& signatures, const v6::Ledger& ledger,
                     const Octets32& signer_key, std::uint64_t nonce,
                     const Octets32& recipient, std::uint64_t amount);
Bytes confirmed_transfer_input(Signatures& signatures, const v6::Ledger& ledger,
                              std::uint64_t nonce, const Octets32& recipient,
                              std::uint64_t amount, const Octets32& identity,
                              const Octets32& hub_key,
                              const Octets32& signer_key,
                              const Octets32& escrow);
Bytes verified_user_mint_input(Signatures& signatures, const v6::Ledger& ledger,
                               const Octets32& identity, std::uint64_t nonce,
                               const Octets32& destination,
                               const Octets32& hub_key,
                               const Octets32& signer_key);
Bytes posture_input(Signatures& signatures, const v6::Ledger& ledger,
                    std::uint64_t nonce, const v6::Posture& posture, bool signed_,
                    const Octets32& identity, const Octets32& hub_key,
                    const Octets32& signer_key, const Octets32& escrow,
                    std::uint64_t valid_until = kValidUntil);

// Execute one block of steps and record what the vectors compare against.
const v6::BlockOutcome& run(Scenario& scenario, const Signatures& signatures,
                            const std::vector<Step>& steps);
// Stand in for a run of empty blocks between two segments of a trace: an empty
// block advances height and commits the empty transaction root, so a run of them
// changes height and nothing else.
void advance_to(Scenario& scenario, std::uint64_t height);

Scenario registration_scenario(Signatures& signatures);
Scenario millionth_scenario(Signatures& signatures);
Scenario recovery_scenario(Signatures& signatures);
Scenario compatibility_scenario(Signatures& signatures, const pv::Values& primitives);
Scenario posture_scenario(Signatures& signatures);

void verify_scenarios(const pv::Values& values, const pv::Values& primitives);
// Every vector whose section this kernel claims must have been consulted. The
// three sections it does not claim belong to the boundary block, whose four seat
// transitions read a cycle assignment this kernel does not yet derive.
void verify_coverage(const pv::Values& values);
void verify_derivations(const pv::Values& values, const pv::Values& primitives,
                        const pv::Values& ledger_vectors,
                        const pv::Values& manifest, const pv::Values& version_three);

}  // namespace economy_v6_execution
