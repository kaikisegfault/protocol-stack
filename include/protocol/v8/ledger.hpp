#pragma once

// The version-eight ledger state and the transitions that run against it.
//
// `protocol/v8/economy.hpp` declares the codec: what a transaction *is* and what
// a state entry *encodes to*. This header declares what a transaction *does*.
// Every entry point here reads or writes a `Ledger`, which is the seam the codec
// deliberately does not have — `decode_signed` returns an `Envelope` and nothing
// more, so the acting escrow, the stored posture, and the nonce sequence all
// live on this side.
//
// A version-eight state is a version-one state — chain identity, supply limit,
// fixed fee, height, fee pool, and the ordered account map — plus one ordered
// economy map. The account map is keyed by escrow identifier and there is no
// second copy of a balance, which is what makes the first structural invariant
// checkable by comparing two key sets.
//
// **Version eight adds two entry kinds and one genesis field to that state, and
// four steps to the block.** Value movement, the registry, the fee, the
// settlement, the recovery pool, the mint walk, and both conservation
// identities are version seven's unchanged, which is why almost every
// declaration below is version seven's declaration.
//
// **No cryptography is performed here.** A `SignatureVerifier` is supplied by the
// caller, so the transition layer never chooses a verification rule and a test
// can exercise every `UNAUTHORIZED` path against a recorded table. Production
// supplies `ed25519_verifier()`, which is the version-one kernel's strict check.

#include "protocol/v8/economy.hpp"

#include <array>
#include <cstdint>
#include <functional>
#include <map>
#include <optional>
#include <set>
#include <span>
#include <string_view>
#include <vector>

namespace protocol::v8 {

// The version-one account entry, reused rather than restated: an escrow's
// balance and nonce are version-one fields keyed by the escrow identifier.
using Account = protocol::v1::Account;
// Version one's three admission codes, unchanged in meaning and number. They
// live in a different namespace from `Result` on purpose: admission `1` is
// `MALFORMED_TRANSACTION` and result `1` is `ZERO_AMOUNT`.
using AdmissionError = protocol::v1::AdmissionError;

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

// One measured seat's inputs for one cycle. **Three fields, not five.** Which
// seat, its uptime, and whether it is inside its own 731 issuance cycles are
// what a measurement establishes; the collection mark and the recorded referrer
// are seat-entry fields the block reads from the chain. ADR 0055 records why: if
// a measurement could supply a different mark, a cycle could set an accrued bit
// in a window the seat's own mint can no longer reach, and the bit would be
// unclaimable while `outstanding` still counted it.
//
// **Under version eight the three-field shape is structural rather than
// disciplined.** Version seven took this from a caller, so the rule was a
// promise the kernel kept; version eight derives it, so a measurement cannot
// supply the other two fields even by accident. There is no `UptimeSchedule`
// type here for the same reason: nothing supplies a schedule any more.
struct SeatCycle {
  std::uint32_t seat_id = 0;
  std::uint64_t uptime_seconds = 0;
  bool in_span = false;
};

// `cycle-boundary-v1`'s scope rules, read from it rather than restated as
// independent figures. A seat activated inside a window cannot have evidence for
// the whole window, so its first cycle opens at the next full one.
//
// `kIssuanceCyclesPerSeat` is the founder-directed 731 of
// `founder-economy-manifest-v3`'s seat schedule. It coincides numerically with
// `kVerifiedUserCycles` and is a different figure: one bounds how long a seat
// generates permissions, the other how long a verified user collects.
inline constexpr std::uint64_t kIssuanceCyclesPerSeat = 731;

// The founder-directed activity threshold: 18 hours of cumulative fully
// operational uptime per cycle, read from the accepted manifest layer and
// checked by the kernel tests against `test-vectors/economy-transition-v3.txt`.
//
// It is declared here rather than kept file-private in the assignment, because
// version eight's containment invariant is stated over it too and a second copy
// would be a second figure. Version eight's own vectors reach it from two
// further directions — a perfect seat after a maximal six-slot dispute, and a
// widened cap of seven slots producing 61,200 seconds and an invariant failure
// by name.
inline constexpr std::uint64_t kActivityThresholdSeconds = 64'800;

std::uint64_t first_cycle_window(std::uint64_t activation_height);
bool seat_in_scope(std::uint64_t activation_height, std::uint64_t cycle_window);
bool seat_in_span(std::uint64_t activation_height, std::uint64_t cycle_window);

// Every in-scope seat of `cycle_window`, in ascending seat order, derived from
// the seat table and the window records rather than supplied.
//
// **Record completeness is structural.** The seat set comes from the chain, so a
// seat cannot be omitted, and a seat with no window record is present with a
// full credit rather than absent — because a slot bit begins set and evidence
// only ever removes credit. A purchased but unactivated seat has no activation
// height and is in no window's scope.
std::vector<SeatCycle> derive_schedule(const Ledger& ledger,
                                       std::uint64_t cycle_window);
// The seconds one window record is worth: whole hours by construction, because
// a slot is credited or it is not.
std::uint64_t seat_uptime_seconds(const SeatWindowRecord& record);

// One seat's record for one window, with **an absent record read as a fully
// credited seat** — a slot bit begins set and evidence only ever removes credit,
// so a machine that answers every challenge writes nothing at all.
//
// `nullopt` is a record in state that will not decode, which is an invariant
// failure rather than an absence: every record here was written by this kernel.
std::optional<SeatWindowRecord> seat_window_record(const Ledger& ledger,
                                                   std::uint64_t cycle_window,
                                                   std::uint32_t seat_id);

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
  // A genesis field bound into the chain identity rather than a state entry,
  // exactly as `supply_limit` and `verifier_key` are, so it lives beside them
  // here and appears in no economy key. It is separate from `verifier_key`
  // because whoever attests HUB identities should not thereby acquire the power
  // to void a machine's uptime; ADR 0048's per-machine attestation registry
  // replaces it in a later transition version.
  Octets32 dispute_authority_key{};
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
  // **Every kind-18 and kind-19 entry, raw, and nothing else.**
  //
  // This is the one surface on this ledger held as encoded bytes rather than as
  // a typed map, and the choice is deliberate. The two transitions version eight
  // adds read and write exactly the key space the state root commits to, so
  // holding it raw makes them *the* implementation rather than a sibling of one.
  // A typed shadow would be a second encoding of the same entries with nothing
  // keeping the two equal, which is the failure mode ADR 0026, ADR 0029, and
  // ADR 0046 each record.
  //
  // Ordered by key, so the projection appends it to the economy map without
  // sorting and the three steps that walk a prefix — the prologue's deletion,
  // the issue step, and the expiry step — all walk it in the same order.
  std::map<Bytes, Bytes> uptime;
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

// One open challenge, named by the pair that is its key.
struct ChallengeRef {
  std::uint64_t challenge_height = 0;
  std::uint32_t seat_id = 0;

  bool operator==(const ChallengeRef&) const = default;
};

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
  // The root the header commits to, carried out of the block so that a caller
  // storing it beside the header is not a second derivation of it. It is the
  // tree over the admitted identifiers in admission order, which is the same
  // order `executed` is in.
  Hash transaction_root{};
  Bytes header;
  Hash block_id{};
  std::uint32_t atomic_failures = 0;
  // The window this block's prologue assigned, when it opened one, and the
  // outcome it derived. The record commits to what a cycle absorbed rather than
  // to what it left behind, so the derivation is carried out of the block for a
  // caller that needs the two seat sets or the pool the cycle leaves.
  std::optional<std::uint64_t> assigned_window;
  std::optional<Assignment> assignment;
  // The three the carrier adds, in ascending order and carried rather than
  // re-derived: which seats the issue step audited, which challenges the expiry
  // step resolved, and which of those cost the seat a slot. A challenge is
  // named by its own height and seat, because that pair is its key.
  std::vector<std::uint32_t> issued;
  std::vector<ChallengeRef> expired;
  std::vector<ChallengeRef> lost_slots;
};

// The three demonstration flags, and none of them is a configuration option a
// chain has. Each exists so a trace can run a rejected reading against the
// accepted one on identical inputs; a conforming implementation is the default
// of all three.
struct BlockOrder {
  // **The cycle assignment is a prologue**, which ADR 0045 derived for version
  // six and every version since inherits: the last assigned window at any
  // height `h` is `window_of_height(h) - 2`, so at the first height of window
  // `w + 2` window `w`'s record must already be in state when the block's
  // transactions run. Under version seven the other reading is not merely
  // expensive but unconstructible — the window's permissions enter
  // `outstanding` with the only seat that could have claimed them already
  // marked past them, so the backing identity fails and the block is rejected
  // whole.
  bool assignment_is_prologue = true;
  // **The expiry step follows the transactions, and that ordering is
  // observable.** A response arriving in block `c + kResponseDeadlineBlocks` is
  // counted; expiring first would discard the last admissible response to every
  // challenge and shorten the deadline to nineteen blocks without saying so.
  bool expire_before_transactions = false;
  // **The prologue precedes the issue step, and at the accepted lag of two
  // windows that is unobservable** — which ADR 0064 records as a finding rather
  // than a defect. A challenge issued at height `h` belongs to
  // `window_of_height(h)` and its expiry clears a bit in that window or the one
  // before, while the prologue deletes records for
  // `window_of_height(h) - kAssignmentLagWindows`. Those windows are always
  // disjoint, so both orderings commit to the same state root. A later version
  // that shortened the lag to one window would make the ordering load-bearing.
  bool issue_before_prologue = false;
};

// Execute one block against `ledger`, advancing it to `h + 1`.
//
// **Version eight's block runs at every height and version seven's does not.**
// The issue step audits every in-scope seat and the expiry step resolves the
// audits `kResponseDeadlineBlocks` later, so a block with no transactions still
// writes state. There is no `UptimeSchedule` parameter: the prologue derives
// the schedule from the seat table and the window records, so a node cannot be
// handed a different answer than its peers computed.
//
// `nullopt` is the whole-block rejection `ledger-transition-v1` defines — an
// internal invariant failure, a height error, or a resource-bound violation —
// and it restores the pre-block state exactly. Ordinary transaction results
// never reject a block, because a refusal is a result rather than a failure.
std::optional<BlockOutcome> execute_block(Ledger& ledger,
                                          std::span<const Bytes> raw_inputs,
                                          const SignatureVerifier& verify,
                                          const BlockOrder& order = {});

// A responder is offered the seats a challenge was just issued to at `height`
// and returns the raw inputs for the *next* height.
//
// It takes that shape because **selection is not knowable until the block that
// performs it has run**: a caller cannot pre-compute which of its own machines
// will be audited, which is the property that makes the audit unpredictable in
// the first place.
using Responder = std::function<std::vector<Bytes>(
    std::uint64_t height, std::span<const std::uint32_t> issued)>;

// Every height up to `target_height`, mostly with no transaction offered.
//
// **This does not stand in for anything.** It runs the issue step and the expiry
// step at every height, because under version eight a block with no transactions
// still audits every in-scope seat. Two kinds of height run the whole block
// transition instead — one that opens a window, and one the responder has raw
// inputs for — so the prologue, the conservation check, and the header are never
// skipped; those outcomes are returned so a caller can record them.
//
// The beacon at a quiet height is computed from `state_root_frame`, which is the
// same preimage `state_root` is defined through with only the height varying.
// Nothing but the two steps can change the state at a quiet height, so the frame
// is rebuilt exactly when one of them writes. The run therefore commits the same
// roots as calling `execute_block` with no inputs at every height, at a fraction
// of the cost — which matters: the recorded scenarios run about 1.35 million
// heights between their recorded blocks.
//
// `nullopt` is the same whole-block rejection `execute_block` returns, and it
// leaves the ledger where the failing height found it.
struct QuietRun {
  std::uint64_t heights = 0;
  std::vector<BlockOutcome> recorded;
};

std::optional<QuietRun> run_quiet_heights(Ledger& ledger,
                                          std::uint64_t target_height,
                                          const SignatureVerifier& verify,
                                          const Responder& respond = nullptr);

}  // namespace protocol::v8
