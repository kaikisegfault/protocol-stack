#pragma once

// The version-seven ledger state and the transitions that run against it.
//
// `protocol/v7/economy.hpp` declares the codec: what a transaction *is* and what
// a state entry *encodes to*. This header declares what a transaction *does*.
// Every entry point here reads or writes a `Ledger`, which is the seam the codec
// deliberately does not have — `decode_signed` returns an `Envelope` and nothing
// more, so the acting escrow, the stored posture, and the nonce sequence all
// live on this side.
//
// A version-seven state is a version-one state — chain identity, supply limit,
// fixed fee, height, fee pool, and the ordered account map — plus one ordered
// economy map. The account map is keyed by escrow identifier and there is no
// second copy of a balance, which is what makes the first structural invariant
// checkable by comparing two key sets.
//
// **No cryptography is performed here.** A `SignatureVerifier` is supplied by the
// caller, so the transition layer never chooses a verification rule and a test
// can exercise every `UNAUTHORIZED` path against a recorded table. Production
// supplies `ed25519_verifier()`, which is the version-one kernel's strict check.

#include "protocol/v7/economy.hpp"

#include <array>
#include <cstdint>
#include <functional>
#include <map>
#include <optional>
#include <set>
#include <span>
#include <string_view>
#include <vector>

namespace protocol::v7 {

// The version-one account entry, reused rather than restated: an escrow's
// balance and nonce are version-one fields keyed by the escrow identifier.
using Account = protocol::v1::Account;
// Version one's three admission codes, unchanged in meaning and number. They
// live in a different namespace from `Result` on purpose: admission `1` is
// `MALFORMED_TRANSACTION` and result `1` is `ZERO_AMOUNT`.
using AdmissionError = protocol::v1::AdmissionError;

inline constexpr std::size_t kChannelCount = 10;
inline constexpr std::uint64_t kMaxU64 = ~std::uint64_t{0};

// The two settlement derivations below read a whole state, and the state is
// declared after them because it is the larger subject; an incomplete type is
// all a reference needs.
struct Ledger;

// The accepted manifest's ten channel caps and five base-permission legs, as the
// kernel needs them at execution. Both tables are founder-directed figures the
// tests check against `test-vectors/founder-economy-manifest-v3.txt` rather than
// against themselves. ADR 0053's manifest renames channel 9 and moves no figure,
// so every value is version two's and the binding still moves: the accepted
// contract a version reads is part of what that version is.
std::uint64_t channel_cap(std::uint8_t channel_index);
std::uint64_t base_permission_leg(std::uint8_t channel_index);
// The referral leg, whose channel has no winner split and therefore no
// remainder, checked against `test-vectors/economy-transition-v3.txt`.
inline constexpr std::uint8_t kReferralChannel = 7;
inline constexpr std::uint8_t kFounderOperatorChannel = 0;
inline constexpr std::uint64_t kReferralLegAtomic = 3'420'000'000;

// Divide every leg of one reallocated permission among the winners. Every leg
// is divided rather than only the operator leg, because the whole permission
// moves to the winners and the escrows and System Creator are paid at the
// winner's mint. At a zero winner count the share is zero and the remainder is
// the whole leg, which is what makes a cycle nobody wins contribute its whole
// base permission to the recovery pool.
struct PermissionSplit {
  RecoveryPool share{};
  RecoveryPool remainder{};
};

PermissionSplit split_permission(std::uint32_t winner_count);

// What one kind-4 mint takes, before it is written.
struct Collection {
  RecoveryPool per_channel{};
  std::uint64_t windows_walked = 0;
  std::vector<std::uint64_t> accrued_windows;
  std::vector<std::uint64_t> won_windows;

  std::uint64_t total_atomic() const;
  // The leg that credits the signing seat holder's own account balance.
  std::uint64_t operator_atomic() const { return per_channel[kFounderOperatorChannel]; }
};

// The bounded mint walk over the recorded assignments: version three's walk with
// one term added, because a winner also takes that cycle's pool share. A window
// with no record contributes nothing, so an absent record and a record with both
// bits clear are the same fact.
//
// `nullopt` is an invariant failure rather than an empty collection: a recorded
// assignment that will not decode, or an amount leaving `u64`.
std::optional<Collection> collect_node(const Ledger& ledger, std::uint32_t seat_id,
                                       std::uint64_t mark,
                                       std::optional<std::uint64_t> last_assigned);

// What the recorded assignments still owe every seat from its own mark, which is
// the `claimable` term of the backing identity.
//
// **It is `collect_node` run once per seat**, against the same records, rather
// than a second walk written beside it. A second walk would be a second
// implementation of the contract's most load-bearing derivation, and the backing
// identity — which is the whole point of version seven — would then be checking
// the kernel against itself rather than against the mint.
std::optional<RecoveryPool> claimable(const Ledger& ledger);

// One measured seat's inputs for one cycle, as `uptime-measurement-v1` supplies
// them. **Three fields, not five.** Which seat, its uptime, and whether it is
// inside its own 731 issuance cycles are what a measurement establishes; the
// collection mark and the recorded referrer are seat-entry fields, and version
// seven's block execution reads both from the chain and ignores whatever a
// caller might have supplied. ADR 0055 records why: if a measurement could
// supply a different mark, a cycle could set an accrued bit in a window the
// seat's own mint can no longer reach, and the bit would be unclaimable while
// `outstanding` still counted it.
struct SeatCycle {
  std::uint32_t seat_id = 0;
  std::uint64_t uptime_seconds = 0;
  bool in_span = false;
};

// A finalised cycle window to the seats `uptime-measurement-v1` measured in it.
using UptimeSchedule = std::map<std::uint64_t, std::vector<SeatCycle>>;

// One cycle's derived outcome, before it is encoded and written.
//
// Every pool quantity is carried separately because each answers a different
// question. `pool_before` is what the cycle found, `pool_absorbed` is what it
// took and is the only one the record commits to, and `pool_after` is what the
// next cycle finds.
struct Assignment {
  std::uint64_t cycle_window = 0;
  std::vector<std::uint32_t> accrued;
  std::vector<std::uint32_t> winners;
  std::uint32_t reallocated_count = 0;
  // The contributing count: the in-span seats, which is what the channel
  // identity's `assigned_cycle_permissions` accumulates.
  std::uint32_t contributing_count = 0;
  // The eligible count: every measured seat that met the cycle and is under the
  // accumulation cap, in span or not. It is the candidate set the winner
  // derivation ranks, and it is carried because the record does not commit to
  // it — the two sets are only distinguishable before the record is written.
  std::uint32_t eligible_count = 0;
  std::uint32_t in_scope_count = 0;
  std::uint32_t bitmap_bits = 0;
  std::uint64_t share_per_winner_atomic = 0;
  RecoveryPool pool_before{};
  RecoveryPool pool_absorbed{};
  RecoveryPool pool_after{};
  std::map<Octets32, std::uint64_t> referral_accruals;
  std::uint64_t unreferred_accrual = 0;
};

// Steps 1 through 8 of one window's assignment, in the specified order.
// `nullopt` is a whole-block rejection: a measurement naming a seat the chain
// has not sold, a seat measured twice, or an amount leaving `u64`.
std::optional<Assignment> derive_assignment(const Ledger& ledger,
                                            std::uint64_t cycle_window,
                                            std::span<const SeatCycle> measured);
// The one record the chain writes when a cycle is finalised.
std::optional<Bytes> assignment_value(const Assignment& assignment);
// Write the record, the outstanding it adds, the pool it leaves behind, and the
// referral accruals. `false` is a whole-block rejection.
bool apply_assignment(Ledger& ledger, const Assignment& assignment);

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
// permissions the chain has assigned, which the channel identity is stated over,
// and it is derivable by summing every assignment record's contributing count.
// It is carried so both identities can be checked after every block without
// re-walking the whole assignment history.
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
  // The recovery pool, which is a state entry. It is not the unreferred referral
  // pool, which is `pool_accrued` and `pool_minted` and is version three's; the
  // two are unrelated and share nothing but a word.
  RecoveryPool pool{};
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
// channels, the empty recovery pool, the verifier key, the empty unreferred
// pool, and the verified-user counter at zero — fourteen entries where version
// six wrote twenty-three. Every other entry arrives through a transition.
// `nullopt` for genesis bytes no conforming deployment could produce.
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
  // The window this block's prologue assigned, when it opened one, and the
  // outcome it derived. The record commits to what a cycle absorbed rather than
  // to what it left behind, so the derivation is carried out of the block for a
  // caller that needs the two seat sets or the pool the cycle leaves.
  std::optional<std::uint64_t> assigned_window;
  std::optional<Assignment> assignment;
};

// Execute one block against `ledger`, advancing it to `h + 1`.
//
// **The cycle assignment is a prologue**, which ADR 0045 derived for version six
// and version seven inherits: the last assigned window at any height `h` is
// `window_of_height(h) - 2`, so at the first height of window `w + 2` window
// `w`'s record must already be in state when the block's transactions run.
//
// `assignment_is_prologue` exists so a trace can run the rejected reading
// against the accepted one on identical inputs. **It is not a configuration
// option a chain has**; a conforming implementation writes the record first, and
// under version seven the other reading is not merely expensive but
// unconstructible — the window's permissions enter `outstanding` with the only
// seat that could have claimed them already marked past them, so the backing
// identity fails and the block is rejected whole.
//
// `nullopt` is the whole-block rejection `ledger-transition-v1` defines — an
// internal invariant failure, a height error, or a resource-bound violation —
// and it restores the pre-block state exactly. Ordinary transaction results
// never reject a block, because a refusal is a result rather than a failure.
std::optional<BlockOutcome> execute_block(Ledger& ledger,
                                          std::span<const Bytes> raw_inputs,
                                          const SignatureVerifier& verify,
                                          const UptimeSchedule* uptime = nullptr,
                                          bool assignment_is_prologue = true);

}  // namespace protocol::v7
