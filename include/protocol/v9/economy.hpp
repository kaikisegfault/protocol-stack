#pragma once

// The canonical byte and derivation surface of `economy-transition-v9`.
//
// This header declares the codec: the transaction envelope with its two
// authorization schemes, the seventeen bodies and the five retired kind
// numbers, the six HUB messages and the dispute message, challenge selection,
// the escrow and signer derivations, the per-escrow security posture and its two
// predicates, the economy state key space, the economy tree and the version-nine
// state root, the block header, genesis and chain identity, the receipt, the
// bounded mint walk, the verified-user arithmetic, and the calendar.
//
// **Version nine is version eight with a clock and a monthly settlement**, and
// the codec's whole share of it is here: one transaction kind, four state entry
// kinds, one widened value, one header field, one genesis field, and
// `calendar-v1`'s derivation from a millisecond count to a calendar month.
// Version nine adds no result code, because kind 22 reuses kind 4's ladder
// exactly. What the settlement *does* — which month closes, who competes, what
// each winner receives, and the six-step prologue that runs it — reads state and
// is the ledger's, and is not declared here.
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

namespace protocol::v9 {

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
inline constexpr std::uint16_t kReceiptVersion = 9;
inline constexpr std::uint16_t kGenesisSchemaVersion = 9;
inline constexpr std::uint16_t kStateRootSchemaVersion = 9;
inline constexpr std::size_t kReceiptBytes = 56;
inline constexpr std::size_t kDisputeAuthorityKeyBytes = 32;
inline constexpr std::size_t kGenesisTimestampBytes = 8;
// Eight octets wider than version eight's, because genesis gains a timestamp.
// **The account bound does not move**: 48-octet account entries absorb eight
// more prefix octets without crossing an entry boundary, so the 21,842 that
// version eight's wider prefix produced is version nine's too. It stays
// unreachable, since zero genesis accounts is required rather than expected.
inline constexpr std::size_t kGenesisPrefixBytes =
    110 + kDisputeAuthorityKeyBytes + kGenesisTimestampBytes;
inline constexpr std::size_t kAccountEntryBytes = 48;
inline constexpr std::size_t kMaxObjectBytes = 1'048'576;
inline constexpr std::size_t kMaxGenesisAccounts =
    (kMaxObjectBytes - kGenesisPrefixBytes) / kAccountEntryBytes;
static_assert(kGenesisPrefixBytes == 150,
              "version nine's genesis prefix is 150 octets");
static_assert(kMaxGenesisAccounts == 21'842,
              "the wider prefix must leave the account bound where version "
              "eight's did");

// The application block header, which version nine is the first version to
// change: version one's 146 octets with `timestamp:u64` inserted after the
// height, which moves every later offset.
//
// **Appending would have kept every existing offset identical**, and that is a
// hazard rather than a benefit: a decoder that read the length loosely would
// parse a version-nine header as a version-one header with eight trailing octets
// and agree with itself about every field. Moving the offsets makes a
// mis-versioned decode produce a chain ID mismatch at the first comparison.
//
// It is declared with the state keys and the genesis bytes rather than beside
// block execution because it is a canonical encoding: what a block header *is*
// belongs to the codec, and what a block *does* belongs to the ledger.
inline constexpr std::size_t kTimestampBytes = 8;
inline constexpr std::size_t kBlockHeaderBytes = 146 + kTimestampBytes;
inline constexpr std::uint16_t kBlockHeaderSchemaVersion = 9;
inline constexpr std::size_t kBlockTimestampOffset = 46;

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
// One definition for both users of the grid's width: the posture's exempt-slot
// mask and the window record's two bitmaps index the same 24 slots, so a change
// to the grid cannot move one and leave the other behind.
inline constexpr std::uint32_t kSlotBitmapMask = (1U << kSlotsPerWindow) - 1U;
inline constexpr std::uint32_t kMaxExemptSlotMask = kSlotBitmapMask;

inline constexpr std::uint64_t kMintAccumulationCap = 30;
inline constexpr std::uint64_t kAssignmentLagWindows = 2;

// --- the clock, read from `calendar-v1` rather than restated ----------------
//
// The unit is the millisecond and the epoch is 1970-01-01T00:00:00Z. The range
// ends at the last millisecond of the year 9999, which is where `calendar-v1`
// stops defining the calendar: a correct machine's stamp must be within the
// tolerance of civil time, so once civil time passes it no acceptable stamp
// exists and the chain stops producing blocks. That is a bound rather than a
// defect — it is 7,973 years away, and every derivation here is total inside it.
inline constexpr std::uint64_t kMillisPerSecond = 1'000;
inline constexpr std::uint64_t kSecondsPerDay = 86'400;
inline constexpr std::uint64_t kMillisPerDay = kSecondsPerDay * kMillisPerSecond;
inline constexpr std::uint64_t kMinTimestampMillis = 0;
inline constexpr std::uint64_t kMaxTimestampMillis = 253'402'300'799'999;
inline constexpr std::uint32_t kMinCalendarYear = 1'970;
inline constexpr std::uint32_t kMaxCalendarYear = 9'999;
inline constexpr std::uint32_t kMonthsPerYear = 12;
inline constexpr std::uint32_t kMaxMonthIndex =
    (kMaxCalendarYear - kMinCalendarYear) * kMonthsPerYear + 11;

// **A consensus parameter of this version and not a deployment option.** Two
// machines applying different tolerances disagree about which blocks are
// acceptable, which is a fork, so it appears in no genesis field and no
// configuration file — exactly as `kCycleBlocks` does not.
inline constexpr std::uint64_t kTimestampToleranceSeconds = 60;
inline constexpr std::uint64_t kTimestampToleranceMillis =
    kTimestampToleranceSeconds * kMillisPerSecond;

// `uptime-measurement-v1`'s figures, read from it rather than restated as
// independent ones. A slot is an hour of the same grid the posture already
// uses, so the carrier introduces no second notion of time.
inline constexpr std::uint64_t kSlotSeconds = 3'600;
inline constexpr std::uint64_t kResponseDeadlineBlocks = 20;
// One challenge per slot in expectation, which is why the period is the slot.
inline constexpr std::uint64_t kChallengePeriodBlocks = kSlotBlocks;
// The final `kResponseDeadlineBlocks` heights of every slot issue nothing, so
// no challenge and its deadline ever straddle a slot boundary.
inline constexpr std::uint64_t kChallengeableHeightsPerSlot =
    kSlotBlocks - kResponseDeadlineBlocks;
inline constexpr std::uint32_t kDisputeCapSlotsPerSeat = 6;
// The bound on kind 21's slot field. The codec decodes an out-of-range slot
// rather than refusing it, because a bounded numeric field is a value and not a
// shape; the ledger reports `SLOT_RANGE`.
inline constexpr std::uint8_t kMaxSlotIndex =
    static_cast<std::uint8_t>(kSlotsPerWindow - 1);
// The answer is opaque to version eight: the predicate that decides whether one
// is *correct* is the challenge's content, which `uptime-measurement-v1`
// reserves to the founder. Version eight instantiates it as the weakest
// predicate available — an answer of the defined width is accepted — so the
// codec fixes the width and nothing else.
inline constexpr std::size_t kAnswerBytes = 32;
// The digest is truncated to eight octets before the reduction, which biases
// selection by less than one part in 2^54 and keeps big-integer arithmetic off
// the consensus path.
inline constexpr std::size_t kSelectionDigestBytes = 8;
inline constexpr std::size_t kSelectionPreimageBytes = 32 + 4 + 8;

// The accepted manifest's ten issuance channels. It sits with the codec rather
// than with the ledger that holds ten balances, because it bounds a channel
// *key* before it bounds a channel *balance*: a reader handed an economy entry
// has to refuse a channel index no manifest defines before anything downstream
// can hold a figure for it.
inline constexpr std::size_t kChannelCount = 10;

// Channel 8. The population and the period are founder-directed and the rate
// follows from them and the accepted cap with no remainder.
inline constexpr std::uint8_t kVerifiedUserChannel = 8;
inline constexpr std::uint64_t kVerifiedUserPopulation = 1'000'000;
inline constexpr std::uint64_t kVerifiedUserCycles = 731;
inline constexpr std::uint64_t kVerifiedUserChannelCapAtomic = 125'001'000'000'000'000;
inline constexpr std::uint64_t kVerifiedUserDailyAtomic = 171'000'000;

// One flat space extending version seven's contiguously: codes 0 through 32
// keep their exact version-seven meanings and 0 through 8 their version-one
// meanings. Twelve are added and none is renumbered.
inline constexpr std::uint8_t kResultCodeCount = 45;
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
  // The twelve version eight adds, for its two kinds.
  seat_not_in_scope = 33,
  challenge_not_issued = 34,
  challenge_not_open = 35,
  response_too_late = 36,
  response_replay = 37,
  unauthorized_dispute = 38,
  slot_range = 39,
  window_not_closed = 40,
  dispute_window_closed = 41,
  dispute_replay = 42,
  dispute_slot_not_credited = 43,
  dispute_cap_exceeded = 44,
};

// Three codes are frozen and unreachable, and each lost its subject rather than
// its meaning: `SENDER_NOT_FOUND` because an escrow that resolves always
// exists, `MANAGER_LIMIT` because a seat has no managers, and `ADDRESS_LIMIT`
// because an identity's addresses are escrows it creates rather than accounts
// it links. They keep their numbers because renumbering a frozen code space is
// the compatibility break the space exists to prevent.
//
// **The array does not grow in version eight.** The fee exemption makes
// `FEE_LIMIT_TOO_LOW`, `DEBIT_OVERFLOW`, and `INSUFFICIENT_BALANCE` unreachable
// **for kind 20 only**, and every other kind still produces all three, so they
// are unreachable for one subject rather than frozen. That distinction is the
// ledger's to enforce and not the codec's.
inline constexpr std::array<std::uint8_t, 3> kFrozenUnreachableCodes{4, 23, 25};

// `nullopt` for a number outside the space, which is what makes the space's
// contiguity checkable rather than asserted.
std::optional<std::string_view> result_code_name(std::uint8_t code);

// **Every label keeps the version that accepted it.** A label names the artifact
// it derives, and none of the artifacts version eight leaves alone — an account,
// an escrow, a signed transaction, a HUB message — changed. Re-versioning the
// two signing labels would additionally destroy the kind-1 byte identity, which
// every version since two has declined to do.
//
// A version-seven signature is nonetheless not replayable here, because every
// signed message binds `chain_id` and the chain identity is derived over genesis
// bytes whose schema version, length, and label all differ.
inline constexpr std::string_view kSignLabel = "protocol-stack:v1:tx-sign";
inline constexpr std::string_view kTransactionIdLabel = "protocol-stack:v1:tx-id";
inline constexpr std::string_view kAccountLabel = "protocol-stack:v1:account";
inline constexpr std::string_view kAccountsTreePrefix = "protocol-stack:v1:state";
inline constexpr std::string_view kEscrowLabel = "protocol-stack:v6:escrow";
// The four constructions version nine re-versions, and the only four. The block
// identifier moves for the first time since version one, because version nine is
// the first version to change the bytes it is taken over; version eight kept
// version one's label for the reason it kept every other inherited one.
inline constexpr std::string_view kChainIdLabel = "protocol-stack:v9:chain-id";
inline constexpr std::string_view kStateRootLabel = "protocol-stack:v9:state-root";
inline constexpr std::string_view kEconomyTreePrefix = "protocol-stack:v9:economy";
inline constexpr std::string_view kBlockIdLabel = "protocol-stack:v9:block-id";
// Version one's ordered transaction tree, which version nine does not touch.
inline constexpr std::string_view kTransactionTreePrefix = "protocol-stack:v1:tx";
// The two labels version eight added, kept because both derive artifacts that
// did not change.
inline constexpr std::string_view kChallengeLabel = "protocol-stack:v8:challenge";
inline constexpr std::string_view kDisputeLabel = "protocol-stack:v8:dispute";

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
  challenge_response = 20,
  file_dispute = 21,
  mint_monthly_pool = 22,
};

enum class Entry : std::uint8_t {
  seat = 1,
  channel = 2,
  cycle_assignment = 3,
  referral_balance = 4,
  direct_decision = 5,
  typed_custody = 6,
  verifier_key = 8,
  hub_identity = 10,
  unreferred_pool = 12,
  escrow = 13,
  signer = 14,
  verified_user_enrollment = 15,
  verified_user_counter = 16,
  recovery_pool = 17,
  open_challenge = 18,
  seat_window = 19,
  window_month = 20,
  monthly_uptime_figure = 21,
  monthly_pool_claim = 22,
  settlement_cursor = 23,
};

// Kinds 7, 8, 9, 11, and 12 and entry kinds 7, 9, and 11 are retired and
// permanently unassigned: each lost its subject, and assigning a new meaning to
// a number a reader associates with an accepted contract is the cheapest way to
// create an auditing mistake. Entry kind 7 held the ten per-channel carries and
// is version seven's own retirement.
//
// **Neither 20 nor 21 nor entry kind 18 nor 19 was ever assigned**, so version
// eight extended both spaces without reusing anything, and neither was 22 nor
// entry kinds 20 through 23, so version nine does the same. Note that the two
// spaces collide numerically — `native_transfer` and `seat` are both 1,
// `mint_verified_user` and `open_challenge` are both 18, and `mint_monthly_pool`
// and `monthly_pool_claim` are both 22 — so enumerate a kind through
// `kind_scheme` or `body_bytes` rather than by reversing a name table.
bool is_transaction_kind(std::uint8_t kind);
bool is_retired_kind(std::uint8_t kind);
bool is_entry_kind(std::uint8_t entry_kind);
bool is_retired_entry_kind(std::uint8_t entry_kind);

// Every kind is fixed-length. Kinds 5, 14, 15, 16, and 18 share a 96-octet body,
// and kinds 4 and 22 share a 100-octet one because kind 22's body *is* kind 4's;
// no other pair collides, so a decoder dispatches on the kind byte. Kind 20's
// body is 44 octets and kind 21's is 78, and neither width is shared.
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

// The named fields of a decoded body, one flat record across all sixteen kinds.
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
  Bytes hub_signature;                  // kinds 2, 3, 4, 5, 17, 18, 19, 22
  std::uint32_t seat_id = 0;            // kinds 2, 3, 4, 20, 21, 22
  bool has_referrer = false;            // kind 2
  Octets32 referrer_escrow_id{};        // kind 2
  Octets32 destination_escrow_id{};     // kinds 4, 5, 18, 22
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
  std::uint64_t challenge_height = 0;   // kind 20
  Bytes answer;                         // kind 20
  std::uint64_t cycle_window = 0;       // kind 21
  std::uint8_t slot_index = 0;          // kind 21
  std::uint8_t reason_code = 0;         // kind 21
  Bytes authority_signature;            // kind 21
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
//
// **Kind 22 reuses it and version nine adds no label.** Version six's message
// binds `u8(transaction_kind)` precisely so a confirmation obtained for one mint
// cannot be presented for another, and the kind byte separates 22 from 4, 5, and
// 18 with no further construction.
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

// The seventh signed construction and the only one that is not a HUB message.
// The dispute authority signs the body while an ordinary signer carries the
// transaction and pays its fee, which is kind 10's pattern: it keeps the
// ecosystem AI without a chain account, a nonce sequence, a balance, or a fee
// obligation, none of which any accepted document gives it.
Bytes dispute_message(std::span<const std::uint8_t> chain_id, std::uint32_t seat_id,
                      std::uint64_t cycle_window, std::uint8_t slot_index,
                      std::uint8_t reason_code, std::uint64_t valid_until_height);

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
Bytes recovery_pool_key();
Bytes verifier_key_key();
Bytes hub_identity_key(std::span<const std::uint8_t> hub_identity_hash);
Bytes unreferred_pool_key();
Bytes escrow_key(std::span<const std::uint8_t> escrow_id);
Bytes signer_key(std::span<const std::uint8_t> signer_id);
Bytes verified_user_key(std::span<const std::uint8_t> hub_identity_hash);
Bytes verified_user_counter_key();
// The two version eight adds, 13 octets each. Note that the entry-kind numbers
// collide with transaction-kind numbers — 18 is both `mint_verified_user` and
// `open_challenge` — so a reader enumerating one space must not reverse the
// other's name table.
Bytes open_challenge_key(std::uint64_t challenge_height, std::uint32_t seat_id);
Bytes seat_window_key(std::uint64_t cycle_window, std::uint32_t seat_id);
// The four version nine adds. `monthly_figure_key` and `monthly_claim_key`
// refuse a month index above `kMaxMonthIndex`, which is what makes every
// derivation that reads one total: such an index has no first millisecond and no
// last, so a key that carried one would hand an undefined case to arithmetic
// downstream.
Bytes window_month_key(std::uint64_t cycle_window);
std::optional<Bytes> monthly_figure_key(std::uint32_t month_index,
                                        std::uint32_t seat_id);
Bytes monthly_claim_key(std::uint32_t seat_id);
Bytes settlement_cursor_key();

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
// account entry keyed by the same 32 octets, which is what makes a version-eight
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

// The recovery pool's five legs, in the accepted manifest's channel order 0
// through 4. **Exactly one such entry exists on any chain**, written at genesis
// with all five legs zero and updated by the assignment prologue.
//
// The five are separate because they have five different destinations — the
// Founder operator's own escrow and four typed custody kinds — and five
// different channel caps and identities. A single total could not say which
// channel a recovered unit belongs to. The ten channels that are not Founder
// Node legs have no pool term, because they have no base permission and
// therefore no remainder.
inline constexpr std::size_t kRecoveryPoolLegs = 5;
using RecoveryPool = std::array<std::uint64_t, kRecoveryPoolLegs>;

// The record the chain writes when a cycle is finalised: version three's, with
// the five amounts that cycle absorbed from the recovery pool appended to its
// fixed part. The two bitmaps are indexed by seat identifier, most significant
// bit first, and carry no length prefixes: both widths follow from
// `bitmap_bits`.
//
// **The record states what the cycle took from the pool, not what a winner
// receives.** A winner's pool share is `pool_absorbed[c] / winner_count`,
// integer division, derived at the mint exactly as the reallocation share is
// derived from `reallocated_count` and `winner_count`. Recording the absorbed
// amount rather than the share is forced: the residual a cycle returns to the
// pool is `absorbed - winner_count * (absorbed / winner_count)`, and a share
// alone cannot express it.
struct CycleAssignment {
  std::uint64_t share_per_winner_atomic = 0;
  std::uint32_t reallocated_count = 0;
  std::uint32_t winner_count = 0;
  std::uint32_t in_scope_count = 0;
  std::uint32_t bitmap_bits = 0;
  RecoveryPool pool_absorbed{};
  Bytes accrued_bitmap;
  Bytes winner_bitmap;
};

// The fixed part is 64 octets rather than version three's 24, and the five new
// fields sit after `bitmap_bits` so that every fixed-width field stays
// contiguous ahead of the variable-length tail.
inline constexpr std::size_t kCycleAssignmentFixedBytes = 64;

Bytes seat_value(const SeatRecord& seat);
Bytes channel_value(std::uint64_t issued_atomic, std::uint64_t outstanding_atomic);
Bytes referral_balance_value(std::uint64_t accrued_atomic,
                             std::uint64_t minted_atomic,
                             std::uint64_t collected_through_window);
// 24 octets rather than version eight's 16, in the order the units travel: a
// unit arrives and raises `accrued` and `payable` together; it is assigned to a
// winner and leaves `payable` for a claim; the winner mints it and it raises
// `minted`.
//
// **`payable` is inserted rather than appended**, for the reason the header's
// timestamp is: the width changes, so no decoder reads both layouts, and moving
// `minted` makes a version-eight decoder pointed at a version-nine value produce
// an obvious mismatch rather than a plausible pair of numbers.
//
// `nullopt` for the two identities stated over one entry: nothing can be payable
// that was never accrued, and nothing can be minted that was never assigned.
struct UnreferredPool {
  std::uint64_t accrued_atomic = 0;
  std::uint64_t payable_atomic = 0;
  std::uint64_t minted_atomic = 0;

  bool operator==(const UnreferredPool&) const = default;
};

std::optional<Bytes> unreferred_pool_value(const UnreferredPool& pool);
std::optional<UnreferredPool> decode_unreferred_pool_value(
    std::span<const std::uint8_t> raw);
Bytes typed_custody_value(std::uint64_t amount_atomic);
Bytes recovery_pool_value(const RecoveryPool& legs);
std::optional<RecoveryPool> decode_recovery_pool_value(
    std::span<const std::uint8_t> raw);
Bytes verifier_key_value(std::span<const std::uint8_t> public_key);
Bytes hub_identity_value(const HubIdentityRecord& identity);
Bytes escrow_value(const EscrowRecord& escrow);
Bytes signer_value(std::span<const std::uint8_t> escrow_id);
Bytes verified_user_value(const EnrollmentRecord& enrollment);
Bytes verified_user_counter_value(std::uint64_t enrolled_count);
std::optional<Bytes> cycle_assignment_value(const CycleAssignment& assignment);
std::optional<CycleAssignment> decode_cycle_assignment_value(
    std::span<const std::uint8_t> raw);

// --- the uptime carrier -----------------------------------------------------
//
// Version eight's whole addition to the state and its derivations. What these
// entries *mean* to a block — the issue step, the expiry step, the schedule the
// prologue derives, and the two transitions that write them — reads state and
// is the ledger's rather than the codec's.

// An open challenge is outstanding until it is answered, and an answered one is
// kept until expiry rather than deleted, so that a second response reports
// `RESPONSE_REPLAY` rather than the false `CHALLENGE_NOT_ISSUED`.
inline constexpr std::uint8_t kChallengeOutstanding = 0;
inline constexpr std::uint8_t kChallengeAnswered = 1;

std::optional<Bytes> open_challenge_value(std::uint8_t state);
// `nullopt` for a width other than one octet and for any state but `0` or `1`.
std::optional<std::uint8_t> decode_open_challenge_value(
    std::span<const std::uint8_t> raw);

// One entry per seat per window **that has lost or had a slot voided**. Both
// fields are 24-bit bitmaps in the low bits of a `u32`, bit `i` is slot `i`,
// and the upper eight bits of each are pad that a decoder refuses.
//
// A dispute sets a bit in `disputed` and never clears one in `credited`, so the
// record keeps what the seat's own evidence said and the final credit is
// `popcount(credited & ~disputed)`. That is what keeps the containment
// invariant checkable against the evidence rather than against a bitmap a
// dispute has already edited.
struct SeatWindowRecord {
  std::uint32_t credited = 0;
  std::uint32_t disputed = 0;

  bool operator==(const SeatWindowRecord&) const = default;
};

// What an absent record reads as: every slot credited, nothing disputed. A slot
// bit begins set and evidence only ever removes credit, so a machine that
// answers every challenge writes nothing at all.
SeatWindowRecord full_seat_window();
// `nullopt` when a pad bit is set or `disputed` is not a subset of `credited`,
// which is the rule version eight states outright and version seven does not
// state for its own bitmap (ADR 0056).
std::optional<Bytes> seat_window_value(const SeatWindowRecord& record);
std::optional<SeatWindowRecord> decode_seat_window_value(
    std::span<const std::uint8_t> raw);
std::uint32_t credited_slots(const SeatWindowRecord& record);
std::uint64_t uptime_seconds(const SeatWindowRecord& record);

// Challenge selection. Every in-scope seat is selected or not independently at
// every height, which is what makes a challenge unpredictable until one block
// before it must be answered, and what costs one digest per in-scope seat per
// height. The evaluation is order-independent and may be parallelised; the
// entries it writes are in ascending seat order.
std::uint64_t slot_last_height(std::uint64_t height);
bool is_challengeable_height(std::uint64_t height);
// `beacon:32 || u32_be(seat_id) || u64_be(height)`; `nullopt` for a beacon that
// is not 32 octets. The beacon is the version-eight state root at `height - 1`,
// which the ledger supplies.
std::optional<Bytes> selection_preimage(std::span<const std::uint8_t> beacon,
                                        std::uint32_t seat_id,
                                        std::uint64_t height);
std::optional<std::uint64_t> selection_value(std::span<const std::uint8_t> beacon,
                                             std::uint32_t seat_id,
                                             std::uint64_t height);
std::optional<bool> is_selected(std::span<const std::uint8_t> beacon,
                                std::uint32_t seat_id, std::uint64_t height);

std::size_t bitmap_bytes(std::uint32_t bitmap_bits);
// `nullopt` when a seat identifier lies outside the bit count, which no
// conforming assignment can produce: the count is the highest in-scope seat
// identifier plus one.
std::optional<Bytes> bitmap(std::span<const std::uint32_t> seat_ids,
                            std::uint32_t bitmap_bits);
bool bit_is_set(std::span<const std::uint8_t> packed, std::uint32_t seat_id);

// --- the calendar and the monthly settlement's state ------------------------
//
// Version nine's whole addition to the state and its derivations. What these
// entries *mean* to a block — which month closes, who competes, what each winner
// receives, and the prologue that runs it — reads state and is the ledger's.
//
// Every derivation here is a pure function of a millisecond count. **None reads
// a clock**: a timestamp is a field a block already carries by the time anything
// here is asked about it, which is `calendar-v1`'s central rule and the whole
// reason the field exists.

bool timestamp_in_range(std::uint64_t timestamp);

// `calendar-v1`'s five ordered conditions. **None of them is a transaction
// result**: a block whose height or timestamp is refused is rejected whole and
// the pre-block state is restored exactly, which is what
// `ledger-transition-v1`'s height rule already does. They are named here so each
// can be tested on its own, and they belong to the application contract's
// status space rather than to this document's result space.
enum class TimestampCondition : std::uint8_t {
  accepted = 0,
  height_not_next = 1,
  timestamp_range = 2,
  timestamp_not_monotonic = 3,
  timestamp_ahead_of_tolerance = 4,
  timestamp_behind_tolerance = 5,
};

inline constexpr std::size_t kTimestampConditionCount = 6;
std::string_view timestamp_condition_name(TimestampCondition condition);

// What a version-nine machine holds about where it is in time: two scalars, both
// committed to by the state root. At genesis the height is zero and the
// timestamp is `genesis_timestamp`, which makes C2's genesis case the same
// comparison as every other height's rather than a special rule.
struct Head {
  std::uint64_t height = 0;
  std::uint64_t timestamp = 0;

  bool operator==(const Head&) const = default;
};

// **Two entry points differing in exactly one respect, which is the structural
// half of `calendar-v1`'s separation.** `accept_timestamp` is the path a machine
// takes when it first validates a height and is the only one that reads a clock;
// `replay_timestamp` takes no clock at all, so there is no argument that could
// make a replaying, restoring, or reconstructing machine check a tolerance. A
// machine that re-applied C5 on replay would reject the chain's own past one
// tolerance-width after producing it, and the failure would be silent.
//
// Both return `accepted` or the first condition that fired, in the normative
// order: the range is refused before any derivation is attempted on the value,
// which is what keeps `month_index` total.
TimestampCondition accept_timestamp(const Head& head, std::uint64_t height,
                                    std::uint64_t timestamp,
                                    std::uint64_t observed_clock_millis);
TimestampCondition replay_timestamp(const Head& head, std::uint64_t height,
                                    std::uint64_t timestamp);

// The proleptic Gregorian derivations, exact in integers and total on the
// accepted range. `nullopt` is the out-of-range case rather than a clamp,
// because a timestamp outside the range has no month at all.
std::optional<std::uint32_t> month_index(std::uint64_t timestamp);
// `nullopt` above `kMaxMonthIndex + 1`. The one-past-the-end index is accepted
// and is the single value this derivation computes outside the accepted
// timestamp range: it is the exclusive end of December 9999, which is what
// `month_end_millis` subtracts one from.
std::optional<std::uint64_t> month_start_millis(std::uint32_t index);
std::optional<std::uint64_t> month_end_millis(std::uint32_t index);
// A window's month is the month its **first** height fell in, which is
// `unreferred-pool-payout-v1`'s attribution rule. A chain cannot evaluate it at
// the assignment — the opening height's timestamp is 57,600 blocks back and not
// in the block doing the work — so the value is written at the opening height
// and read at the assignment. This function is what genesis and that write use.
std::uint64_t window_opening_height(std::uint64_t cycle_window);

// Kind 20. One entry per window whose opening height has passed and whose
// assignment has not; it is written at the opening height, at genesis for window
// 0, and deleted when the window is assigned. A month of zero is a real month —
// January 1970 — so there is no absence rule here, unlike the figure and the
// claim.
std::optional<Bytes> window_month_value(std::uint32_t month_index);
std::optional<std::uint32_t> decode_window_month_value(
    std::span<const std::uint8_t> raw);

// Kind 21. One entry per seat per month **that accumulated uptime**, holding the
// sum of `uptime_seconds` over the windows attributed to that month.
//
// **Only nonzero figures are written**, and a decoder refuses a zero: a
// candidate with no entry has a figure of zero by absence, and a zero value
// would be a second encoding of it. That is the difference between writing as
// many entries as ran and writing 100,000 every window.
std::optional<Bytes> monthly_figure_value(std::uint64_t uptime_seconds);
std::optional<std::uint64_t> decode_monthly_figure_value(
    std::span<const std::uint8_t> raw);

// Kind 22. The referral balance's shape — an `accrued` that only rises and a
// `minted` that follows it — keyed by the seat rather than by the identity,
// because a monthly pool win is a machine's performance and two seats of one
// owner can both win in a tie.
//
// **It is a running balance and not a per-month award.** A seat that wins in two
// months before minting holds one entry whose `accrued` is the sum, and one
// transaction collects both. That is the founder-directed mint shape applied:
// a mint takes everything with no quantity choice, which kinds 4, 5, and 18 all
// implement. `accrued` is nonzero in every claim that exists, because a share
// that rounds to zero writes no entry at all.
struct MonthlyClaim {
  std::uint64_t accrued_atomic = 0;
  std::uint64_t minted_atomic = 0;

  bool operator==(const MonthlyClaim&) const = default;
};

std::optional<Bytes> monthly_claim_value(const MonthlyClaim& claim);
std::optional<MonthlyClaim> decode_monthly_claim_value(
    std::span<const std::uint8_t> raw);

// Kind 23. A singleton holding the month index whose figures are currently
// accumulating. It is a separate entry rather than a fourth field on the pool
// because it would still be needed on a chain whose pool was permanently empty:
// it describes where the window grid has reached on the calendar, not what the
// pool holds.
std::optional<Bytes> settlement_cursor_value(std::uint32_t accumulating_month);
std::optional<std::uint32_t> decode_settlement_cursor_value(
    std::span<const std::uint8_t> raw);

// The open window's month and its predecessor's. `unreferred-pool-payout-v1`
// sized this at three — the open window and the two inside the assignment lag —
// and version nine deletes the oldest of the three in the same prologue that
// assigns it, so at every point inside a block the live count is two.
inline constexpr std::size_t kLiveWindowMonths = 2;

// Version eight's fourteen genesis economy entries plus the settlement cursor
// and window zero's month.
inline constexpr std::size_t kGenesisEconomyEntries = 16;

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

// **The state carries `timestamp` beside `height` and the root commits to it,
// and that is forced rather than chosen.** C2 compares `t(h)` with `t(h - 1)`,
// so a machine that restarted, restored from a snapshot, or reconstructed state
// from the durable head must know its predecessor's stamp to validate the next
// block at all; a value held only in a header the node did not keep is not
// available to it. And a value two machines could hold differently without their
// roots differing is a fork no gate catches. It is version one's argument for
// committing to `height`, applied to the second field that orders blocks.
struct StateSummary {
  Octets32 chain_id{};
  std::uint64_t height = 0;
  std::uint64_t timestamp = 0;
  std::uint64_t supply_limit = 0;
  std::uint64_t total_supply = 0;
  std::uint64_t fee_pool_balance = 0;
};

std::optional<Hash> state_root(const StateSummary& summary,
                               std::span<const AccountEntry> accounts,
                               std::vector<EconomyEntry> economy);

// The root preimage split around its one field a quiet height changes.
//
// **Version eight is the first version whose block transition runs at every
// height** whether or not a transaction was offered, because the issue step
// needs the previous root as its beacon. A run of transaction-free heights
// therefore recomputes this preimage once per height, and every field but the
// height and the timestamp is identical across the run.
//
// Version eight split the preimage around the height alone; version nine's
// timestamp moves at every height too, so the split carries both. Splitting it
// rather than caching a root is what keeps the fast path exact: `state_root` is
// *defined* through these two functions, so there is one preimage in this kernel
// and a run of quiet heights cannot drift from it.
struct StateRootFrame {
  Bytes head;
  Bytes tail;
};

std::optional<StateRootFrame> state_root_frame(
    const StateSummary& summary, std::span<const AccountEntry> accounts,
    std::vector<EconomyEntry> economy);
// `nullopt` for a timestamp outside the accepted range, which no accepted state
// holds: a root over a stamp C1 would have refused is not a version-nine root.
std::optional<Hash> state_root_from_frame(const StateRootFrame& frame,
                                          std::uint64_t height,
                                          std::uint64_t timestamp);

// An earlier version's root over the same inputs, for versions 1 through 8.
// Distinct labels are strings rather than a chain, so refusing one collision
// implies nothing about another and version nine must prove eight separately.
// Version one's preimage has no economy half, which is why the version is a
// parameter of the construction rather than only of the label, and **no
// predecessor preimage carries a timestamp at all**.
std::optional<Hash> predecessor_state_root(std::uint16_t version,
                                           const StateSummary& summary,
                                           std::span<const AccountEntry> accounts,
                                           std::vector<EconomyEntry> economy);

// Zero genesis accounts is required rather than merely expected, as it has been
// since version six: an account with no escrow entry has no identity behind it,
// which the structural invariant forbids. The field and the 21,842 bound the
// wider prefix leaves are retained for layout compatibility and are
// unreachable.
struct Genesis {
  std::uint32_t network_id = 0;
  // The tenth field, written immediately after the network identifier because
  // it is part of what identifies this chain rather than part of what it is
  // worth. A value outside `calendar-v1`'s accepted range makes the genesis
  // malformed, and no other rule applies to it: genesis validation reads no
  // clock, which is forced, because the chain identity is a hash of these bytes
  // and a rule that read a clock would make two machines disagree about a
  // chain's own identifier.
  std::uint64_t genesis_timestamp = 0;
  std::uint64_t supply_limit = 0;
  std::uint64_t fixed_transfer_fee = 0;
  Octets32 manifest_digest{};
  Octets32 verifier_key{};
  // The ninth field, written immediately after `verifier_key` so the two keys
  // are adjacent and `account_count` stays last, which it must: the account
  // entries follow it. It is separate from `verifier_key` rather than reusing
  // it, because whoever attests HUB identities should not thereby acquire the
  // power to void a machine's uptime. ADR 0048's per-machine attestation
  // registry replaces this single key in a later transition version, which
  // changes who signs and not what a signature can do.
  Octets32 dispute_authority_key{};
  std::uint64_t total_supply = 0;
  std::uint64_t initial_fee_pool = 0;
  std::uint32_t account_count = 0;
};

// The 154-octet application block header and the identifier over it. `nullopt`
// for a timestamp outside the accepted range: a header carrying one is not a
// version-nine header, and refusing it here is what keeps every reader of the
// field total.
std::optional<Bytes> block_header(const Octets32& chain_id, std::uint64_t height,
                                  std::uint64_t timestamp,
                                  const Hash& previous_state_root,
                                  const Hash& transaction_root_value,
                                  const Hash& resulting_state_root,
                                  std::uint32_t transaction_count);
// `nullopt` for anything but a whole header: an identifier is taken over all
// 154 octets or not at all.
std::optional<Hash> block_id(std::span<const std::uint8_t> header);
// The same octets under version one's label, for the non-collision claim. A
// version-nine header is 154 octets and version one's is 146, so no earlier
// identifier can be taken over these bytes at all; the comparison is recorded
// anyway, because distinct labels are strings rather than a chain.
std::optional<Hash> predecessor_block_id(std::span<const std::uint8_t> header);

std::optional<Bytes> encode_genesis(const Genesis& genesis);
// The exact inverse of `encode_genesis`, and it checks itself against that
// claim: a decoded genesis is returned only when re-encoding it reproduces the
// input octet for octet. So there is no second statement anywhere of what a
// valid genesis is — the encoder's rule is the only one, and a file that would
// not have been produced by it is refused rather than opened.
std::optional<Genesis> decode_genesis(std::span<const std::uint8_t> raw);
std::optional<Hash> chain_id(const Genesis& genesis);
// The same fields under an earlier schema version and label, for versions 2
// through 8, so that "no predecessor genesis is the same object" is a claim
// about two derived identifiers. A predecessor's bytes omit the genesis
// timestamp, and before version eight the dispute authority key too, so the
// compared object is 110 or 142 octets and never this one.
std::optional<Hash> predecessor_chain_id(const Genesis& genesis,
                                         std::uint16_t version);

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

}  // namespace protocol::v9
