#pragma once

// The shared fixture behind the version-ten execution checks.
//
// **This target records what version ten changes about what a chain does, and
// nothing else**: who may sign a registration, what an approval signs, how long
// it lives, and what the registry step counts. Everything version ten carries is
// fixed by version nine's execution vectors, which version nine's kernel
// reproduces until the deletion ADR 0104 enumerates.
//
// **Two fixtures produce the vectors, and both are rebuilt here exactly.** The
// chain is `simulation/economy_transition_v10/trace.py`, a chain of blocks at
// ninety seconds a block. The population is `population.py`, 101 machines driven
// through version nine's evidence harness: transactions executed one at a time at
// heights the run sets, windows opened through `open_window`, and a closed
// window's kind-19 records supplied. No recorded chain of blocks reaches the
// launch key's retirement or a founder's limit.
//
// **No signature is computed anywhere.** A stand-in is an eight-octet counter
// padded to 64 octets, recorded against the exact key and message it authorizes,
// so a signature presented over any other message is absent from the table. A
// transaction identifier is a digest over the signed bytes, so every builder
// below issues its signatures in the model's order: a body's own before the
// envelope's, because a body must be complete before the envelope holding it can
// be encoded.
//
// **No version-ten test includes `protocol/v9/`** (ADR 0104). The one
// version-nine construction the chain offers, a purchase approved the way
// version nine approved one, is built from the label version six's accepted
// vectors record, and the receipt boundary is read from version nine's file.

#include "protocol/v10/ledger.hpp"

#include "../../tools/protocol-vectors/vector_common.hpp"

#include <array>
#include <cstdint>
#include <map>
#include <optional>
#include <set>
#include <span>
#include <string>
#include <vector>

namespace economy_v10_execution {

namespace pv = protocol_vectors;
namespace v10 = protocol::v10;

using Bytes = v10::Bytes;
using Hash = v10::Hash;
using Octets32 = v10::Octets32;

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

// **Returned by value.** A reference into the map bound at a call site that
// passed a temporary key is GCC 13's `-Wdangling-reference`, which failed both
// GCC presets in M3.18b and again in M4.3d, so the accessor removes the question.
inline std::string expect_text(const pv::Values& values, const std::string& key) {
  const auto found = values.find(key);
  pv::require(found != values.end(), "vector file records no " + key);
  consulted().insert(key);
  return found->second;
}

inline std::uint64_t expect_number(const pv::Values& values,
                                   const std::string& key) {
  const auto text = expect_text(values, key);
  try {
    return std::stoull(text);
  } catch (const std::exception&) {
    throw std::runtime_error(key + " is not a number: " + text);
  }
}

inline void agree(const pv::Values& values, const std::string& key,
                  const std::string& derived) {
  const auto recorded = expect_text(values, key);
  pv::require(recorded == derived,
              key + ": derived " + derived + ", recorded " + recorded);
}

inline void agree(const pv::Values& values, const std::string& key,
                  std::uint64_t derived) {
  agree(values, key, std::to_string(derived));
}

// A recorded boolean is a claim, so it is consulted only where the check beside
// it established the claim.
inline void expect_claim(const pv::Values& values, const std::string& key,
                         bool established) {
  pv::require(established, "the claim " + key + " does not hold here");
  pv::require(expect_text(values, key) == "true", "the vectors record " + key);
}

// --- the recorded fixture ---------------------------------------------------

inline constexpr std::uint64_t kSupplyLimit = 5'699'395'010'000'000'000;
inline constexpr std::uint64_t kFixedFee = 1'000;
inline constexpr std::uint32_t kNetworkId = 10;
inline constexpr std::string_view kManifestDigestHex =
    "af153c99adf7c49e5a92563946cf0e60dfd7a58785462530988f661aa68faaa7";

inline const Octets32 kLaunchKey = repeated(0x55);
inline const Octets32 kDisputeAuthorityKey = repeated(0xD8);
inline const Octets32 kBuildAuthorityKey = repeated(0xB4);
inline const Octets32 kBuildDigest = repeated(0x33);

// Far beyond any height a run reaches, for a transaction with no HUB proof.
inline constexpr std::uint64_t kFar = 10'000'000'000;
inline constexpr std::uint64_t kLifetime = v10::kApprovalLifetimeBlocks;

// Version nine's trace rate: ninety seconds a block, so a window is thirty days
// and every window opens in a month of its own, which brings a monthly
// settlement inside four windows and is what lets kind 22 be approved at all.
// 2026-01-15T00:00:00Z.
inline constexpr std::uint64_t kMillisPerBlock = 90'000;
inline constexpr std::uint64_t kGenesisMillis = 1'768'435'200'000;

inline std::uint64_t timestamp_of_height(std::uint64_t height) {
  return kGenesisMillis + height * kMillisPerBlock;
}

v10::Genesis trace_genesis();
v10::Ledger open_trace_ledger();

struct Person {
  Octets32 identity{};
  Octets32 hub_key{};
  Octets32 signer_key{};

  Hash escrow() const { return v10::escrow_id(identity, 0); }
};

// Version seven's two people, octet for octet.
inline const Person kAlice{repeated(0xA1), repeated(0xA2), repeated(0xA3)};
inline const Person kBob{repeated(0xB1), repeated(0xB2), repeated(0xB3)};

// Three distinct 32-octet values for any index a run reaches.
inline Person person(std::uint32_t index) {
  Person who;
  Octets32* fields[] = {&who.identity, &who.hub_key, &who.signer_key};
  const std::uint8_t leads[] = {0x41, 0x4B, 0x53};
  for (std::size_t field = 0; field < 3; ++field) {
    auto& value = *fields[field];
    value.fill(0);
    value[0] = leads[field];
    for (std::size_t octet = 0; octet < 4; ++octet) {
      value[1 + octet] = static_cast<std::uint8_t>(index >> (24 - 8 * octet));
    }
  }
  return who;
}

// A seat's machine key. A later generation is a replacement key.
inline Octets32 machine_key(std::uint32_t seat_id, std::uint8_t generation = 0) {
  Octets32 value{};
  value[0] = static_cast<std::uint8_t>(0xC0 + generation);
  for (std::size_t octet = 0; octet < 4; ++octet) {
    value[1 + octet] = static_cast<std::uint8_t>(seat_id >> (24 - 8 * octet));
  }
  return value;
}

// A recorded signature table. Verification is exact-match lookup on
// `(public key, message)`, and a pair signed twice receives its first token.
class Signatures {
 public:
  Bytes sign(const Octets32& public_key, std::span<const std::uint8_t> message) {
    const auto key = entry_key(public_key, message);
    const auto found = table_.find(key);
    if (found != table_.end()) return found->second;
    const auto issued = static_cast<std::uint64_t>(table_.size());
    Bytes token(v10::kSignatureBytes, 0);
    for (int shift = 56, index = 0; shift >= 0; shift -= 8, ++index) {
      token[static_cast<std::size_t>(index)] =
          static_cast<std::uint8_t>(issued >> shift);
    }
    table_.emplace(key, token);
    return token;
  }

  bool verifies(const Octets32& public_key, std::span<const std::uint8_t> message,
                std::span<const std::uint8_t> signature) const {
    const auto found = table_.find(entry_key(public_key, message));
    if (found == table_.end()) return false;
    return std::equal(found->second.begin(), found->second.end(),
                      signature.begin(), signature.end());
  }

  v10::SignatureVerifier verifier() const {
    return [this](std::span<const std::uint8_t> public_key,
                  std::span<const std::uint8_t> message,
                  std::span<const std::uint8_t> signature) {
      Octets32 key{};
      if (public_key.size() != key.size()) return false;
      std::copy(public_key.begin(), public_key.end(), key.begin());
      return verifies(key, message, signature);
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

// Signed version-ten transactions against one ledger's chain identity, the
// model's `fixture.Builder` field for field.
//
// **A builder takes the height the transaction will execute at**, because every
// transaction that carries a HUB proof must expire within one slot of it. A
// transaction with no HUB proof uses `kFar`, so a run shows the rule does not
// reach it.
class Builder {
 public:
  Builder(Signatures& signatures, const v10::Ledger& ledger)
      : signatures_(&signatures), ledger_(&ledger) {}

  v10::Envelope transaction(v10::Kind kind, const Octets32& authority,
                            std::uint64_t nonce, const v10::Body& body,
                            std::uint64_t valid_until) const;
  Bytes sign(const v10::Envelope& envelope) const;
  // The version-ten approval: the whole transaction with its HUB field zero,
  // signed by `hub_key`, and the signature placed in the field.
  v10::Envelope approve(v10::Envelope draft, const Octets32& hub_key) const;
  Bytes approved(const Person& who, v10::Kind kind, std::uint64_t nonce,
                 v10::Body body, std::uint64_t valid_until,
                 const std::optional<Octets32>& hub_key = std::nullopt) const;

  // `signed_seat` is the seat the attester's message names, when a run presents
  // a signature made for one seat under another's identifier.
  Bytes registration(const Person& who, std::uint32_t attester_seat,
                     const Octets32& attester_key, std::uint64_t valid_until,
                     std::optional<std::uint32_t> signed_seat = std::nullopt) const;
  Bytes purchase(const Person& who, std::uint32_t seat_id, std::uint64_t nonce,
                 std::uint64_t valid_until,
                 const Person* referrer = nullptr) const;
  // A purchase approved the way version nine approved one, over version six's
  // purchase message under the label its accepted vectors record.
  Bytes version_nine_purchase(const Person& who, std::uint32_t seat_id,
                              std::uint64_t nonce, std::uint64_t valid_until,
                              std::string_view purchase_label) const;
  Bytes activation(const Person& who, std::uint32_t seat_id, std::uint64_t nonce,
                   std::uint64_t valid_until) const;
  Bytes machine_registration(const Person& who, std::uint32_t seat_id,
                             const Octets32& key, std::uint64_t nonce,
                             std::uint64_t valid_until,
                             const Octets32& attester = kBuildAuthorityKey,
                             const std::optional<Octets32>& hub_key = std::nullopt,
                             bool approve_it = true) const;
  Bytes posture(const Person& who, std::uint64_t nonce, bool requires_confirmation,
                std::uint64_t valid_until, bool approve_it) const;
  Bytes transfer(const Person& who, const Person& recipient, std::uint64_t amount,
                 std::uint64_t nonce) const;
  Bytes confirmed_transfer(const Person& who, const Person& recipient,
                           std::uint64_t amount, std::uint64_t nonce,
                           std::uint64_t valid_until) const;
  Bytes signer_add(const Person& who, const Octets32& signer_key,
                   std::uint64_t nonce, std::uint64_t valid_until) const;
  Bytes mint(const Person& who, v10::Kind kind, std::uint64_t nonce,
             std::uint64_t valid_until,
             std::optional<std::uint32_t> seat_id = std::nullopt) const;
  Bytes response(const Person& who, std::uint32_t seat_id,
                 std::uint64_t challenge_height, std::uint64_t nonce) const;
  // The same transaction under another nonce, its HUB field carried over: how a
  // published approval is re-presented, with the signer signing a new envelope.
  Bytes reused(const Bytes& raw, std::uint64_t nonce) const;

 private:
  Signatures* signatures_;
  const v10::Ledger* ledger_;
};

inline std::uint64_t nonce_of(const v10::Ledger& ledger, const Octets32& escrow) {
  const auto account = ledger.registry.accounts.find(escrow);
  return account == ledger.registry.accounts.end() ? 0 : account->second.nonce;
}

// The name a result code carries in the vectors.
std::string result_name(v10::Result result);

// One raw input and the label the vectors record its outcome under.
struct Step {
  std::string label;
  Bytes raw;
};

// One machine answering the challenges a quiet run issues it, or none, and its
// log. It answers nothing at a height where the run will stop, because the
// answer would belong to a block the run does not execute.
struct ResponderLog {
  std::vector<std::uint64_t> challenged;
  std::vector<std::uint64_t> answered;
  std::vector<std::uint64_t> left_at_a_stop;
};

// The recorded chain. Every executed step's result, receipt, raw bytes, and
// height is kept by label, and the blocks by name where the vectors read one.
struct Chain {
  v10::Ledger ledger;
  std::vector<v10::BlockOutcome> blocks;
  std::vector<std::vector<std::string>> labels;
  std::vector<v10::BlockOutcome> audit_blocks;
  std::map<std::string, Bytes> raw;
  std::map<std::string, std::uint64_t> heights;
  std::map<std::uint32_t, std::uint64_t> marks_after_the_first_assignment;
  std::optional<v10::BlockOutcome> first_assignment;
  std::optional<v10::BlockOutcome> second_assignment;
  ResponderLog alice;
  ResponderLog bob;
  std::uint64_t skipped_blocks = 0;

  std::map<std::string, v10::ExecutedTransaction> executed() const;
};

Chain chain_scenario(Signatures& signatures, std::string_view purchase_label);

// Five heights contiguous from genesis, the model's `restart_scenario`, for a
// layer that replays blocks one at a time. The chain above jumps to the
// activation height, which a store, an application, or a transport has no way to
// follow. The fifth block registers both machines through kind 23, whose
// attestation verifies against the build authority key no root commits to.
struct Restart {
  v10::Ledger ledger;
  std::vector<v10::BlockOutcome> blocks;
  std::vector<std::vector<std::string>> labels;
  std::map<std::string, Bytes> raw;
  // The run's one refusal: the condition C2 reported for a stamp one
  // millisecond below the predecessor's, and the root the rejected block left.
  v10::TimestampCondition refused_below_the_predecessor =
      v10::TimestampCondition::accepted;
  bool refusal_rejected_the_block = false;
  Hash root_after_the_refusal{};
};

Restart restart_scenario(Signatures& signatures);
// The heights whose stamp each restart block carries. The third repeats its
// predecessor's, which C2 admits because the rule is non-decreasing.
inline constexpr std::array<std::uint64_t, 5> kRestartStampHeights{1, 2, 2, 4, 5};

// One chain driven a transaction and a window at a time, the model's
// `population.Harness`.
struct Harness {
  Signatures signatures;
  v10::Ledger ledger;
  std::map<std::string, std::string> results;
  std::map<std::string, Bytes> receipts;
  std::map<std::uint64_t, v10::BlockOutcome> windows;
  std::uint32_t count_after_the_thousandth = 0;
  // Registrations each machine attested that the kernel accepted, by window and
  // seat. No state holds a per-machine count any more (ADR 0107), so this is
  // what evidences how a founder's registrations were spread.
  std::map<std::pair<std::uint64_t, std::uint32_t>, std::uint64_t> attested;
  // Observed rather than assumed: the keys whose mark is 0 straight after the
  // window-0 assignment, which is what the count's exclusion is about.
  std::optional<std::uint64_t> unmarked_at_the_window_0_assignment;
};

inline constexpr std::uint32_t kMachines = 101;
// One founder holds every seat but the last, and the last is another founder's,
// whose machine still signs while the first founder's are full.
inline const Person kPopulationFounder = person(0);
inline const Person kOtherFounder = person(3);
inline constexpr std::uint32_t kOtherFounderSeat = kMachines - 1;
// The window whose opening assigns window 31, the first cycle a seat that never
// collects cannot hold, and the window whose opening assigns the first cycle
// past a seat's 731.
inline constexpr std::uint64_t kCapRunWindow = 33;
inline constexpr std::uint64_t kSpanRunWindow = v10::kIssuanceCyclesPerSeat + 3;

Harness cutoff_run();
Harness span_run();

// The check groups, one per subject.
void verify_genesis(const pv::Values& values);
void verify_chain(const pv::Values& values, const Chain& chain,
                  const Signatures& signatures, const pv::Values& version_nine);
void verify_population(const pv::Values& values, const Harness& cutoff,
                       const Harness& span);
void verify_invariants(const pv::Values& values, const Harness& cutoff);
// The restart run's commitments and its one refusal, which the layers above the
// kernel replay block by block.
void verify_restart_run(const pv::Values& values);
// The one contract vector the codec target defers here.
void verify_contract_sections(const pv::Values& contract);
// Three rules no recorded vector reaches, each found by a mutation probe the
// vectors let pass, and `open_window`'s own refusals.
void verify_lifetime_order();
void verify_unmarked_machine_in_window_two();
void verify_open_window_refusals();

}  // namespace economy_v10_execution
