#pragma once

// The version-six ledger state and the transitions that run against it.
//
// `protocol/v6/economy.hpp` declares the codec: what a transaction *is* and what
// a state entry *encodes to*. This header declares what a transaction *does*.
// Every entry point here reads or writes a `Ledger`, which is the seam the codec
// deliberately does not have — `decode_signed` returns an `Envelope` and nothing
// more, so the acting escrow, the stored posture, and the nonce sequence all
// live on this side.
//
// A version-six state is a version-one state — chain identity, supply limit,
// fixed fee, height, fee pool, and the ordered account map — plus one ordered
// economy map. The account map is keyed by escrow identifier and there is no
// second copy of a balance, which is what makes the first structural invariant
// checkable by comparing two key sets.
//
// **No cryptography is performed here.** A `SignatureVerifier` is supplied by the
// caller, so the transition layer never chooses a verification rule and a test
// can exercise every `UNAUTHORIZED` path against a recorded table. Production
// supplies `ed25519_verifier()`, which is the version-one kernel's strict check.

#include "protocol/v6/economy.hpp"

#include <array>
#include <cstdint>
#include <functional>
#include <map>
#include <optional>
#include <set>
#include <span>
#include <string_view>
#include <vector>

namespace protocol::v6 {

// The version-one account entry, reused rather than restated: an escrow's
// balance and nonce are version-one fields keyed by the escrow identifier.
using Account = protocol::v1::Account;
// Version one's three admission codes, unchanged in meaning and number. They
// live in a different namespace from `Result` on purpose: admission `1` is
// `MALFORMED_TRANSACTION` and result `1` is `ZERO_AMOUNT`.
using AdmissionError = protocol::v1::AdmissionError;

inline constexpr std::size_t kChannelCount = 10;
inline constexpr std::uint64_t kMaxU64 = ~std::uint64_t{0};

// The accepted manifest's ten channel caps and five base-permission legs, as the
// kernel needs them at execution. Both tables are founder-directed figures the
// tests check against `test-vectors/founder-economy-manifest-v2.txt` rather than
// against themselves.
std::uint64_t channel_cap(std::uint8_t channel_index);
std::uint64_t base_permission_leg(std::uint8_t channel_index);
// The referral leg, whose channel takes no carry, checked against
// `test-vectors/economy-transition-v3.txt`.
inline constexpr std::uint8_t kReferralChannel = 7;
inline constexpr std::uint8_t kFounderOperatorChannel = 0;
inline constexpr std::uint64_t kReferralLegAtomic = 3'420'000'000;

struct ReferralBalance {
  std::uint64_t accrued_atomic = 0;
  std::uint64_t minted_atomic = 0;
  std::uint64_t collected_through_window = 0;
};

// Identities, escrows, signers, enrollments, and the account map. Every key in
// the account map is an escrow, which is the structural invariant this whole
// version exists to establish.
struct Registry {
  std::map<Octets32, HubIdentityRecord> identities;
  std::map<Octets32, EscrowRecord> escrows;
  // signer identifier to the one escrow it may act on.
  std::map<Octets32, Octets32> signers;
  std::map<Octets32, EnrollmentRecord> enrollments;
  std::map<Octets32, Account> accounts;
  std::uint64_t enrolled_count = 0;
};

// One node's complete canonical state at a height.
//
// `assigned_permissions` is not a state entry. It is the running count of base
// permissions the chain has assigned, which the carry identity is stated over,
// and it is derivable by summing every assignment record's in-span count. It is
// carried so the identity can be checked after every block without re-walking
// the whole assignment history.
struct Ledger {
  Octets32 chain_id{};
  std::uint64_t supply_limit = 0;
  std::uint64_t fixed_fee = 0;
  Octets32 verifier_key{};
  std::uint64_t height = 0;
  std::uint64_t total_supply = 0;
  std::uint64_t fee_pool = 0;
  Registry registry;
  std::array<std::uint64_t, kChannelCount> channel_issued{};
  std::array<std::uint64_t, kChannelCount> channel_outstanding{};
  std::array<std::uint64_t, kChannelCount> carry{};
  std::map<std::uint8_t, std::uint64_t> custody;
  std::map<std::uint32_t, SeatRecord> seats;
  std::map<Octets32, ReferralBalance> referral;
  std::uint64_t pool_accrued = 0;
  std::uint64_t pool_minted = 0;
  std::set<Octets32> decisions;
  // A finalised cycle window to its encoded assignment record.
  std::map<std::uint64_t, Bytes> assignments;
  std::uint64_t assigned_permissions = 0;
};

// Height zero, zero supply, zero accounts, and the fixed tables written: the ten
// channels, the ten carries, the verifier key, the empty unreferred pool, and
// the verified-user counter at zero. Every other entry arrives through a
// transition. `nullopt` for genesis bytes no conforming deployment could produce.
std::optional<Ledger> open_ledger(const Genesis& genesis);

// The canonical maps this state commits to, in the shapes the roots take.
std::vector<EconomyEntry> economy_entries(const Ledger& ledger);
std::vector<AccountEntry> account_entries(const Ledger& ledger);
std::optional<Hash> ledger_state_root(const Ledger& ledger);

// Every conservation and structural equality, each checked as an equality
// because a bound would admit a defect that lost a term. An empty result is a
// state some sequence of conforming transitions could have produced.
std::vector<std::string_view> conservation_failures(const Ledger& ledger);

using SignatureVerifier =
    std::function<bool(std::span<const std::uint8_t> public_key,
                       std::span<const std::uint8_t> message,
                       std::span<const std::uint8_t> signature)>;

// The production verifier: the version-one kernel's strict Ed25519 check.
SignatureVerifier ed25519_verifier();

// One raw input's admission outcome. A failure produces no receipt, performs no
// state read or write, and never enters the ordered transaction root.
struct Admitted {
  std::optional<AdmissionError> error;
  DecodedTransaction transaction;
  Hash transaction_id{};

  bool admitted() const { return !error.has_value(); }
};

Admitted admit(std::span<const std::uint8_t> raw, const Octets32& chain_id,
               const SignatureVerifier& verify);

// One executed transaction's result, before it becomes a receipt.
struct Outcome {
  Result result = Result::success;
  std::uint64_t issued_atomic = 0;
  std::uint64_t fee_charged = 0;

  bool succeeded() const { return result == Result::success; }
};

// Resolve the acting escrow, apply the shared envelope checks, then the kind's
// own conditions. Every non-success result performs no state write and charges
// no fee; the transitions validate completely before writing, so atomicity is
// structural rather than enforced by a rollback.
//
// `nullopt` is an invariant failure rather than a transaction result — a debit
// below zero, a monetary value leaving `u64`, a channel issuing more than it
// accrued. No conforming sequence reaches one, and `ledger-transition-v1`
// rejects the whole block when one does, which is why it is not a `Result`.
std::optional<Outcome> execute(Ledger& ledger, const Envelope& envelope,
                               const SignatureVerifier& verify);

Receipt receipt_for(const Hash& transaction_id, const Envelope& envelope,
                    const Outcome& outcome);

struct ExecutedTransaction {
  Hash transaction_id{};
  std::uint8_t kind = 0;
  Outcome outcome;
  Receipt receipt;
};

// Version one's ordered transaction tree, duplicates included.
Hash transaction_root(std::span<const Hash> admitted_ids);

inline constexpr std::size_t kBlockHeaderBytes = 146;
inline constexpr std::uint16_t kBlockHeaderSchemaVersion = 1;
inline constexpr std::string_view kBlockIdLabel = "protocol-stack:v1:block-id";
inline constexpr std::string_view kTransactionTreePrefix = "protocol-stack:v1:tx";
inline constexpr std::size_t kMaxRawInputs = 65'535;
inline constexpr std::size_t kMaxAdmitted = 65'535;

// The 146-byte application block header, inherited from version one unchanged.
// Version six re-versions genesis, the receipt, and the state root explicitly
// and says nothing about the header, so version one's schema version governs.
std::optional<Bytes> block_header(const Octets32& chain_id, std::uint64_t height,
                                  const Hash& previous_state_root,
                                  const Hash& transaction_root_value,
                                  const Hash& resulting_state_root,
                                  std::uint32_t transaction_count);

struct BlockOutcome {
  std::uint64_t height = 0;
  Hash previous_state_root{};
  Hash resulting_state_root{};
  std::vector<Admitted> admissions;
  std::vector<ExecutedTransaction> executed;
  Bytes header;
  Hash block_id{};
  std::uint32_t atomic_failures = 0;
};

// Execute one block against `ledger`, advancing it to `h + 1`.
//
// `nullopt` is the whole-block rejection `ledger-transition-v1` defines — an
// internal invariant failure, a height error, or a resource-bound violation —
// and it restores the pre-block state exactly. Ordinary transaction results
// never reject a block, because a refusal is a result rather than a failure.
std::optional<BlockOutcome> execute_block(Ledger& ledger,
                                          std::span<const Bytes> raw_inputs,
                                          const SignatureVerifier& verify);

}  // namespace protocol::v6
