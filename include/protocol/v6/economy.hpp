#pragma once

// The canonical byte and derivation surface of `economy-transition-v6`.
//
// This header declares the codec: the transaction envelope with its two
// authorization schemes, the fourteen bodies and the five retired kind numbers,
// the six HUB messages, the escrow and signer derivations, the per-escrow
// security posture and its two predicates, the economy state key space, the
// economy tree and the version-six state root, genesis and chain identity, the
// receipt, the bounded mint walk, and the verified-user arithmetic.
//
// It performs no state transition and reads no ledger, which is why every entry
// point here is a pure function of its arguments. Whether an operation requires
// a biometric confirmation is a predicate over an escrow's *stored* posture, so
// the predicate is declared here and the escrow it reads is not: supplying the
// posture is the caller's, which is the shape ADR 0045 records for why that rule
// cannot live at admission.
//
// Decode failures are `std::nullopt` rather than exceptions, matching the
// version-one kernel: admission is defined to judge shape and nothing else, so
// a refusal carries no reason beyond "these bytes are not a transaction".

#include "protocol/v1/types.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>
#include <string_view>
#include <vector>

namespace protocol::v6 {

using Bytes = protocol::v1::Bytes;
using Hash = protocol::v1::Hash;
using Octets32 = std::array<std::uint8_t, 32>;

// The envelope is version one's, unchanged: the header is the accepted
// transfer's first 80 bytes and the trailer its last 16, so kind 1's body is
// what remains and the accepted transfer bytes survive a sixth version.
inline constexpr std::size_t kHeaderBytes = 80;
inline constexpr std::size_t kTrailerBytes = 16;
inline constexpr std::size_t kSignatureBytes = 64;
inline constexpr std::uint16_t kEnvelopeSchemaVersion = 1;
inline constexpr std::uint16_t kReceiptVersion = 6;
inline constexpr std::uint16_t kGenesisSchemaVersion = 6;
inline constexpr std::uint16_t kStateRootSchemaVersion = 6;
inline constexpr std::size_t kReceiptBytes = 56;
inline constexpr std::size_t kGenesisPrefixBytes = 110;
inline constexpr std::size_t kAccountEntryBytes = 48;
inline constexpr std::size_t kMaxObjectBytes = 1'048'576;
inline constexpr std::size_t kMaxGenesisAccounts =
    (kMaxObjectBytes - kGenesisPrefixBytes) / kAccountEntryBytes;

// Scheme 1 names a signer key and resolves the escrow it is assigned to;
// scheme 2 names an identity's HUB key and the body names the escrow. Both
// verify the envelope signature against the header key, so admission still
// reads no state, and a kind fixes its scheme.
inline constexpr std::uint8_t kSchemeSigner = 1;
inline constexpr std::uint8_t kSchemeIdentity = 2;

inline constexpr std::uint32_t kFounderSeatCapacity = 100'000;
inline constexpr std::uint32_t kMaxSeatId = kFounderSeatCapacity - 1;
inline constexpr std::uint32_t kMaxSeatsPerIdentity = 1'000;
inline constexpr std::uint32_t kMaxSignersPerEscrow = 16;

// The accepted window grid. A slot is one hour and a window has 24 of them, so
// the posture's "time windows" are block heights and never a clock.
inline constexpr std::uint64_t kCycleBlocks = 28'800;
inline constexpr std::uint64_t kSlotBlocks = 1'200;
inline constexpr std::uint32_t kSlotsPerWindow = 24;
inline constexpr std::uint32_t kMaxExemptSlotMask = (1U << kSlotsPerWindow) - 1U;

inline constexpr std::uint64_t kMintAccumulationCap = 30;
inline constexpr std::uint64_t kAssignmentLagWindows = 2;

// Channel 8. The population and the period are founder-directed and the rate
// follows from them and the accepted cap with no remainder.
inline constexpr std::uint8_t kVerifiedUserChannel = 8;
inline constexpr std::uint64_t kVerifiedUserPopulation = 1'000'000;
inline constexpr std::uint64_t kVerifiedUserCycles = 731;
inline constexpr std::uint64_t kVerifiedUserChannelCapAtomic = 125'001'000'000'000'000;
inline constexpr std::uint64_t kVerifiedUserDailyAtomic = 171'000'000;

// One flat space extending version four's contiguously: codes 0 through 25 keep
// their exact version-four meanings and 0 through 8 their version-one meanings.
inline constexpr std::uint8_t kResultCodeCount = 33;
inline constexpr std::uint8_t kSuccessResultCode = 0;

// The three channels whose eligibility predicate is still reserved. Channel 8
// has left the set, because ADR 0042 decided both its eligibility and its rate.
inline constexpr std::array<std::uint8_t, 3> kDirectIssueChannels{5, 6, 9};

enum class Result : std::uint8_t {
  success = 0,
  zero_amount = 1,
  fee_limit_too_low = 2,
  expired = 3,
  sender_not_found = 4,
  nonce_exhausted = 5,
  nonce_mismatch = 6,
  debit_overflow = 7,
  insufficient_balance = 8,
  unauthorized = 9,
  cycle_range = 10,
  invalid_referrer = 11,
  replay = 12,
  seat_not_activated = 13,
  seat_not_purchased = 14,
  nothing_to_mint = 15,
  invalid_channel = 16,
  missing_research_input = 17,
  invalid_research_input = 18,
  not_eligible = 19,
  channel_cap = 20,
  not_hub_verified = 21,
  biometric_required = 22,
  manager_limit = 23,
  seat_limit = 24,
  address_limit = 25,
  signer_not_found = 26,
  recipient_not_registered = 27,
  escrow_not_found = 28,
  escrow_not_owned = 29,
  escrow_not_empty = 30,
  signer_limit = 31,
  not_enrolled = 32,
};

// Three codes are frozen and unreachable in version six, and each lost its
// subject rather than its meaning: `SENDER_NOT_FOUND` because an escrow that
// resolves always exists, `MANAGER_LIMIT` because a seat has no managers, and
// `ADDRESS_LIMIT` because an identity's addresses are escrows it creates rather
// than accounts it links. They keep their numbers because renumbering a frozen
// code space is the compatibility break the space exists to prevent.
inline constexpr std::array<std::uint8_t, 3> kFrozenUnreachableCodes{4, 23, 25};

// `nullopt` for a number outside the space, which is what makes the space's
// contiguity checkable rather than asserted.
std::optional<std::string_view> result_code_name(std::uint8_t code);

// The version-one labels, deliberately not re-versioned: re-versioning would
// destroy the kind-1 byte identity for separation the preimage already carries.
inline constexpr std::string_view kSignLabel = "protocol-stack:v1:tx-sign";
inline constexpr std::string_view kTransactionIdLabel = "protocol-stack:v1:tx-id";
inline constexpr std::string_view kAccountLabel = "protocol-stack:v1:account";
inline constexpr std::string_view kAccountsTreePrefix = "protocol-stack:v1:state";
inline constexpr std::string_view kEscrowLabel = "protocol-stack:v6:escrow";
inline constexpr std::string_view kChainIdLabel = "protocol-stack:v6:chain-id";
inline constexpr std::string_view kStateRootLabel = "protocol-stack:v6:state-root";
inline constexpr std::string_view kEconomyTreePrefix = "protocol-stack:v6:economy";

enum class Kind : std::uint8_t {
  native_transfer = 1,
  purchase_seat = 2,
  activate_seat = 3,
  mint_node = 4,
  mint_referral = 5,
  direct_issue = 6,
  hub_register = 10,
  escrow_create = 13,
  escrow_delete = 14,
  signer_add = 15,
  signer_revoke = 16,
  set_security_posture = 17,
  mint_verified_user = 18,
  native_transfer_verified = 19,
};

enum class Entry : std::uint8_t {
  seat = 1,
  channel = 2,
  cycle_assignment = 3,
  referral_balance = 4,
  direct_decision = 5,
  typed_custody = 6,
  carry = 7,
  verifier_key = 8,
  hub_identity = 10,
  unreferred_pool = 12,
  escrow = 13,
  signer = 14,
  verified_user_enrollment = 15,
  verified_user_counter = 16,
};

// Kinds 7, 8, 9, 11, and 12 and entry kinds 9 and 11 are retired and
// permanently unassigned: each lost its subject, and assigning a new meaning to
// a number a reader associates with an accepted contract is the cheapest way to
// create an auditing mistake.
bool is_transaction_kind(std::uint8_t kind);
bool is_retired_kind(std::uint8_t kind);
bool is_entry_kind(std::uint8_t entry_kind);
bool is_retired_entry_kind(std::uint8_t entry_kind);

// Every kind is fixed-length. Kinds 5, 14, 15, 16, and 18 share a 96-octet body
// and no other pair collides, so a decoder dispatches on the kind byte.
std::optional<std::size_t> body_bytes(std::uint8_t kind);
std::optional<std::size_t> unsigned_bytes(std::uint8_t kind);
std::optional<std::size_t> signed_bytes(std::uint8_t kind);
// The one scheme the kind permits; any other is `MALFORMED_TRANSACTION`.
std::optional<std::uint8_t> kind_scheme(std::uint8_t kind);

std::optional<std::size_t> entry_key_bytes(std::uint8_t entry_kind);
// `nullopt` for an unknown or retired kind, and for the one variable-width
// value — the cycle assignment, whose width follows from its recorded bit
// count. `is_entry_kind` distinguishes the two.
std::optional<std::size_t> entry_value_bytes(std::uint8_t entry_kind);

struct Envelope {
  std::uint8_t kind = 0;
  Octets32 chain_id{};
  // Scheme 1 or 2. It is carried rather than derived from the kind so that a
  // transaction naming a scheme its kind forbids is representable and can be
  // shown to be refused.
  std::uint8_t scheme = kSchemeSigner;
  Octets32 authority_public_key{};
  std::uint64_t nonce = 0;
  Bytes body;
  std::uint64_t fee_limit = 0;
  std::uint64_t valid_until_height = 0;
};

struct DecodedTransaction {
  Envelope envelope;
  Bytes signature;
};

Bytes encode_unsigned(const Envelope& envelope);
Bytes encode_signed(const Envelope& envelope, std::span<const std::uint8_t> signature);
Bytes signing_message(std::span<const std::uint8_t> unsigned_transaction);
Hash transaction_id(std::span<const std::uint8_t> signed_transaction);

// Admission step 1. Shape only: no state is read and no value is judged, so a
// bounded numeric field outside its range decodes here and is refused at
// execution. The one rule the specification places here and this cannot hold is
// the zero-confirmation field, whose predicate reads a stored posture; ADR 0045
// records that it is refused at execution instead.
std::optional<DecodedTransaction> decode_signed(std::span<const std::uint8_t> raw);

// The named fields of a decoded body, one flat record across all fourteen kinds.
// Which fields a kind defines follows from the kind byte, and a field its kind
// does not define keeps its default: one record checked field by field against
// the specification's tables is auditable in a way a variant is not, and every
// body is fixed-width so nothing is ambiguous about where a field sits.
//
// `decode_signed` has already refused a body of the wrong width for its kind, so
// this is a projection rather than a second admission step; it still refuses a
// mismatched width, because a reader that trusted its caller would be one place
// for a bound to go unchecked.
struct Body {
  Octets32 recipient_escrow_id{};       // kinds 1, 19
  std::uint64_t amount_atomic = 0;      // kinds 1, 19, 6
  Bytes hub_signature;                  // kinds 2, 3, 4, 5, 17, 18, 19
  std::uint32_t seat_id = 0;            // kinds 2, 3, 4
  bool has_referrer = false;            // kind 2
  Octets32 referrer_escrow_id{};        // kind 2
  Octets32 destination_escrow_id{};     // kinds 4, 5, 18
  std::uint8_t channel_id = 0;          // kind 6
  Octets32 decision_id{};               // kind 6
  Octets32 beneficiary_escrow_id{};     // kind 6
  Octets32 authorization{};             // kind 6
  Octets32 hub_identity_hash{};         // kinds 10, 13, 14, 15, 16
  Octets32 first_signer_public_key{};   // kind 10
  Bytes verifier_signature;             // kind 10
  Octets32 fee_escrow_id{};             // kinds 13, 14
  Octets32 target_escrow_id{};          // kind 14
  Octets32 escrow_id{};                 // kinds 15, 16
  Octets32 signer_public_key{};         // kind 15
  Octets32 signer_id{};                 // kind 16
  bool requires_confirmation = false;   // kind 17
  std::uint64_t min_amount_atomic = 0;  // kind 17
  std::uint32_t exempt_slot_mask = 0;   // kind 17
};

std::optional<Body> decode_body(std::uint8_t kind, std::span<const std::uint8_t> body);
Bytes encode_body(std::uint8_t kind, const Body& body);

// The six HUB messages. Five verify against the acting identity's recorded
// public key; only the registration verifies against the ecosystem verifier
// key. Every one binds the identity, so a signature by one person's key is
// never presentable as another's.
Bytes registration_message(std::span<const std::uint8_t> chain_id,
                           std::span<const std::uint8_t> hub_identity_hash,
                           std::span<const std::uint8_t> hub_public_key,
                           std::span<const std::uint8_t> first_signer_public_key,
                           std::uint64_t valid_until_height);
Bytes purchase_message(std::span<const std::uint8_t> chain_id,
                       std::span<const std::uint8_t> hub_identity_hash,
                       std::uint32_t seat_id, std::uint64_t valid_until_height);
Bytes activation_message(std::span<const std::uint8_t> chain_id,
                         std::span<const std::uint8_t> hub_identity_hash,
                         std::uint32_t seat_id, std::uint64_t valid_until_height);
// Binds the kind and the destination, which is what stops a confirmation
// obtained for one mint being replayed onto a different one. Kinds 5 and 18
// carry no seat, so their `seat_id` term is zero and the kind byte separates
// them.
Bytes mint_message(std::span<const std::uint8_t> chain_id,
                   std::span<const std::uint8_t> hub_identity_hash,
                   std::uint8_t transaction_kind, std::uint32_t seat_id,
                   std::span<const std::uint8_t> destination_escrow_id,
                   std::uint64_t valid_until_height);
struct Posture;
Bytes posture_relax_message(std::span<const std::uint8_t> chain_id,
                            std::span<const std::uint8_t> hub_identity_hash,
                            std::span<const std::uint8_t> escrow_id,
                            const Posture& proposed,
                            std::uint64_t valid_until_height);
Bytes transfer_confirm_message(std::span<const std::uint8_t> chain_id,
                               std::span<const std::uint8_t> hub_identity_hash,
                               std::span<const std::uint8_t> escrow_id,
                               std::span<const std::uint8_t> recipient_escrow_id,
                               std::uint64_t amount,
                               std::uint64_t valid_until_height);

// An escrow holds no key, so its identifier is derived from the identity and an
// index that never decreases rather than from a public key. A wallet computes
// its own identifiers offline, and a deleted escrow's identifier is never
// reissued.
Hash escrow_id(std::span<const std::uint8_t> hub_identity_hash,
               std::uint32_t escrow_index);
// The accepted version-one account derivation with its subject moved from an
// account to a signer, which is what a public-key hash is. It is the version-one
// kernel's own implementation rather than a second copy of it.
Hash signer_id(std::span<const std::uint8_t> ed25519_public_key);

// The default a newly created escrow takes: confirmation on for every financial
// operation, which is what the constitution directs.
struct Posture {
  bool requires_confirmation = true;
  std::uint64_t min_amount_atomic = 0;
  std::uint32_t exempt_slot_mask = 0;

  bool operator==(const Posture&) const = default;
};

std::uint32_t slot_of(std::uint64_t height);
bool requires_confirmation(const Posture& posture, std::uint64_t amount,
                           std::uint64_t height);
// A chain cannot read intent, so the direction of a change is derived from the
// two stored postures. Each of the three disjuncts is checked independently, so
// a change that tightens one field and relaxes another is a relaxation.
bool relaxes(const Posture& current, const Posture& proposed);

// State keys. Each is one discriminator octet followed by fixed-width
// big-endian fields, so unsigned lexicographic order is total.
Bytes seat_key(std::uint32_t seat_id);
Bytes channel_key(std::uint8_t channel_index);
Bytes cycle_assignment_key(std::uint64_t cycle_window);
Bytes referral_balance_key(std::span<const std::uint8_t> hub_identity_hash);
Bytes direct_decision_key(std::span<const std::uint8_t> decision_id);
Bytes typed_custody_key(std::uint8_t beneficiary_kind,
                        std::span<const std::uint8_t> beneficiary_id);
Bytes carry_key(std::uint8_t channel_index);
Bytes verifier_key_key();
Bytes hub_identity_key(std::span<const std::uint8_t> hub_identity_hash);
Bytes unreferred_pool_key();
Bytes escrow_key(std::span<const std::uint8_t> escrow_id);
Bytes signer_key(std::span<const std::uint8_t> signer_id);
Bytes verified_user_key(std::span<const std::uint8_t> hub_identity_hash);
Bytes verified_user_counter_key();

// 82 bytes. The purchaser account, the biometric flag, and the manager count
// are gone with the concepts they served: a seat is owned by an identity and
// read through it, and it has no address at all.
struct SeatRecord {
  Octets32 hub_identity_hash{};
  bool has_referrer = false;
  Octets32 referrer_hub_identity{};
  bool is_activated = false;
  std::uint64_t activation_height = 0;
  std::uint64_t minted_through_window = 0;
};

// 52 bytes. `next_escrow_index` and `escrow_count` are separate on purpose: the
// index never decreases so an identifier is never reissued, and the count falls
// on deletion so the live figure is exact.
struct HubIdentityRecord {
  Octets32 hub_public_key{};
  std::uint64_t registered_at_height = 0;
  std::uint32_t next_escrow_index = 1;
  std::uint32_t escrow_count = 1;
  std::uint32_t seat_count = 0;
};

// 49 bytes. The balance and the nonce are not here: they are the version-one
// account entry keyed by the same 32 octets, which is what makes a version-six
// state a version-one state plus an economy map.
struct EscrowRecord {
  Octets32 owner_hub_identity{};
  Posture posture;
  std::uint32_t signer_count = 0;
};

// 24 bytes, written only for an identity that registered while fewer than
// 1,000,000 were enrolled.
struct EnrollmentRecord {
  std::uint64_t enrolled_at_height = 0;
  std::uint64_t minted_through_window = 0;
  std::uint64_t issued_atomic = 0;
};

// The record the chain writes when a cycle is finalised, unchanged from version
// three. The two bitmaps are indexed by seat identifier, most significant bit
// first, and carry no length prefixes: both widths follow from `bitmap_bits`.
struct CycleAssignment {
  std::uint64_t share_per_winner_atomic = 0;
  std::uint32_t reallocated_count = 0;
  std::uint32_t winner_count = 0;
  std::uint32_t in_scope_count = 0;
  std::uint32_t bitmap_bits = 0;
  Bytes accrued_bitmap;
  Bytes winner_bitmap;
};

Bytes seat_value(const SeatRecord& seat);
Bytes channel_value(std::uint64_t issued_atomic, std::uint64_t outstanding_atomic);
Bytes referral_balance_value(std::uint64_t accrued_atomic,
                             std::uint64_t minted_atomic,
                             std::uint64_t collected_through_window);
Bytes unreferred_pool_value(std::uint64_t accrued_atomic, std::uint64_t minted_atomic);
Bytes typed_custody_value(std::uint64_t amount_atomic);
Bytes carry_value(std::uint64_t carry_atomic);
Bytes verifier_key_value(std::span<const std::uint8_t> public_key);
Bytes hub_identity_value(const HubIdentityRecord& identity);
Bytes escrow_value(const EscrowRecord& escrow);
Bytes signer_value(std::span<const std::uint8_t> escrow_id);
Bytes verified_user_value(const EnrollmentRecord& enrollment);
Bytes verified_user_counter_value(std::uint64_t enrolled_count);
std::optional<Bytes> cycle_assignment_value(const CycleAssignment& assignment);
std::optional<CycleAssignment> decode_cycle_assignment_value(
    std::span<const std::uint8_t> raw);

std::size_t bitmap_bytes(std::uint32_t bitmap_bits);
// `nullopt` when a seat identifier lies outside the bit count, which no
// conforming assignment can produce: the count is the highest in-scope seat
// identifier plus one.
std::optional<Bytes> bitmap(std::span<const std::uint32_t> seat_ids,
                            std::uint32_t bitmap_bits);
bool bit_is_set(std::span<const std::uint8_t> packed, std::uint32_t seat_id);

struct EconomyEntry {
  Bytes key;
  Bytes value;
};

struct AccountEntry {
  Octets32 account_id{};
  std::uint64_t balance = 0;
  std::uint64_t nonce = 0;
};

// Sorted by unsigned lexicographic key; a leaf preimage uses the accepted
// length-prefixed `bytes` primitive for both halves. `nullopt` when an entry is
// one no transition could have written — an unknown or retired kind, a key or
// value of the wrong width, or a duplicated key, all of which the specification
// forbids and none of which a hash can signal.
std::optional<Hash> economy_root(std::vector<EconomyEntry> entries);
Hash accounts_root(std::span<const AccountEntry> accounts);

struct StateSummary {
  Octets32 chain_id{};
  std::uint64_t height = 0;
  std::uint64_t supply_limit = 0;
  std::uint64_t total_supply = 0;
  std::uint64_t fee_pool_balance = 0;
};

std::optional<Hash> state_root(const StateSummary& summary,
                               std::span<const AccountEntry> accounts,
                               std::vector<EconomyEntry> economy);

// Version six is the first version to require zero genesis accounts rather than
// merely to expect it: an account with no escrow entry has no identity behind
// it, which the structural invariant forbids. The field and the inherited
// 21,843 bound are retained for layout compatibility and are unreachable.
struct Genesis {
  std::uint32_t network_id = 0;
  std::uint64_t supply_limit = 0;
  std::uint64_t fixed_transfer_fee = 0;
  Octets32 manifest_digest{};
  Octets32 verifier_key{};
  std::uint64_t total_supply = 0;
  std::uint64_t initial_fee_pool = 0;
  std::uint32_t account_count = 0;
};

std::optional<Bytes> encode_genesis(const Genesis& genesis);
std::optional<Hash> chain_id(const Genesis& genesis);

struct Receipt {
  Octets32 transaction_id{};
  std::uint8_t kind = 0;
  std::uint8_t result_code = 0;
  std::uint64_t fee_charged = 0;
  std::uint64_t issued_atomic = 0;
};

bool receipt_is_consistent(const Receipt& receipt);
std::optional<Bytes> encode_receipt(const Receipt& receipt);
std::optional<Receipt> decode_receipt(std::span<const std::uint8_t> raw);

// The bounded mint walk, unchanged from version three: `(mark, min(last, mark +
// 30)]`. `nullopt` is the empty range, which is what `NOTHING_TO_MINT` means —
// ADR 0045's third derived rule, and the reason a mark can never decrease.
struct WalkRange {
  std::uint64_t first_window = 0;
  std::uint64_t last_window = 0;
};

std::optional<WalkRange> walk_range(std::uint64_t mark,
                                    std::optional<std::uint64_t> last_assigned);
// `window_of_height(h) - 2`, or nothing while the chain is younger than that.
// `uptime-measurement-v1` finalises window `w` at the first height of `w + 2`,
// so that is where `w`'s assignment executes and no earlier. It is arithmetic on
// the executing height alone, which is what makes it the same for every
// transaction in a block.
std::optional<std::uint64_t> last_assigned_window(std::uint64_t height);
bool accrues(std::uint64_t cycle_window, std::uint64_t mark);
std::uint64_t window_of_height(std::uint64_t height);

// The verified-user collection a kind-18 mint would make. The cap forfeits at
// `window_start`: a person who has not collected for forty days collects the
// most recent thirty windows and the older ten are never issued.
struct VerifiedUserCollection {
  std::uint64_t window_start = 0;
  std::uint64_t collectable_end = 0;
  std::uint64_t count = 0;
  std::uint64_t amount_atomic = 0;
};

VerifiedUserCollection verified_user_collection(std::uint64_t minted_through_window,
                                                std::uint64_t enrolled_window,
                                                std::uint64_t height);
// The rate the three founder-supplied figures determine, `nullopt` when the cap
// does not divide by the population and the period without remainder.
std::optional<std::uint64_t> verified_user_daily_atomic();
std::uint64_t verified_user_remainder_at(std::uint64_t cycles);

}  // namespace protocol::v6
