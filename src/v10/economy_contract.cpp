#include "protocol/v10/economy.hpp"

#include <array>
#include <string_view>

namespace protocol::v10 {
namespace {

// The frozen numeric result space, extended contiguously. Codes 0 through 8 are
// version one's, 9 through 25 are versions two through four's, 26 through 32 are
// version six's, 33 through 44 are version eight's, and 45 through 49 are
// version ten's own; no number is ever renumbered and no name is ever reused.
// Version nine added none, because kind 22 reuses kind 4's ladder exactly.
constexpr std::array<std::string_view, 50> kResultCodeNames{
    "SUCCESS",
    "ZERO_AMOUNT",
    "FEE_LIMIT_TOO_LOW",
    "EXPIRED",
    "SENDER_NOT_FOUND",
    "NONCE_EXHAUSTED",
    "NONCE_MISMATCH",
    "DEBIT_OVERFLOW",
    "INSUFFICIENT_BALANCE",
    "UNAUTHORIZED",
    "CYCLE_RANGE",
    "INVALID_REFERRER",
    "REPLAY",
    "SEAT_NOT_ACTIVATED",
    "SEAT_NOT_PURCHASED",
    "NOTHING_TO_MINT",
    "INVALID_CHANNEL",
    "MISSING_RESEARCH_INPUT",
    "INVALID_RESEARCH_INPUT",
    "NOT_ELIGIBLE",
    "CHANNEL_CAP",
    "NOT_HUB_VERIFIED",
    "BIOMETRIC_REQUIRED",
    "MANAGER_LIMIT",
    "SEAT_LIMIT",
    "ADDRESS_LIMIT",
    "SIGNER_NOT_FOUND",
    "RECIPIENT_NOT_REGISTERED",
    "ESCROW_NOT_FOUND",
    "ESCROW_NOT_OWNED",
    "ESCROW_NOT_EMPTY",
    "SIGNER_LIMIT",
    "NOT_ENROLLED",
    // The twelve version eight adds. Five of the measurement model's codes are
    // deliberately absent — `SCHEDULE_NOT_BOUND` and `INVALID_BOUND_SCHEDULE`
    // because the chain's schedule is its own seat table and binds nothing,
    // `HEIGHT_RANGE` and `HEIGHT_NOT_MONOTONIC` because a block rejection is
    // not a transaction result, and `RESPONSE_INVALID` because the answer
    // predicate is founder-reserved and no path produces it.
    "SEAT_NOT_IN_SCOPE",
    "CHALLENGE_NOT_ISSUED",
    "CHALLENGE_NOT_OPEN",
    "RESPONSE_TOO_LATE",
    "RESPONSE_REPLAY",
    "UNAUTHORIZED_DISPUTE",
    "SLOT_RANGE",
    "WINDOW_NOT_CLOSED",
    "DISPUTE_WINDOW_CLOSED",
    "DISPUTE_REPLAY",
    "DISPUTE_SLOT_NOT_CREDITED",
    "DISPUTE_CAP_EXCEEDED",
    // The five version ten adds, four for kind 10 and one for the lifetime rule.
    // Each names a fact a person can act on rather than folding into
    // `UNAUTHORIZED`, which would leave a wallet guessing at its next step.
    "LAUNCH_KEY_RETIRED",
    "MACHINE_KEY_NOT_FOUND",
    "MACHINE_NOT_ACTIVE",
    "REGISTRATION_LIMIT",
    "APPROVAL_LIFETIME_EXCEEDED",
};

static_assert(kResultCodeNames.size() == kResultCodeCount,
              "the result code table and its declared count must agree");


// A sentinel for a number that is not an assigned kind, which is either never
// assigned or retired. The two are distinguished by the retired table rather
// than by the width, because a retired number and an unassigned one are refused
// identically and audited differently.
constexpr std::size_t kUnassigned = static_cast<std::size_t>(-1);
constexpr std::uint8_t kNoScheme = 0;

// Every kind is fixed-length, and each width is the sum of its named fields.
// Kinds 5, 14, 15, 16, and 18 all carry 96-octet bodies and no other pair
// collides, so a decoder dispatches on the kind byte rather than on the length.
constexpr std::array<std::size_t, 24> kBodyBytes{
    kUnassigned,  // 0, never a kind
    40,           // 1  native_transfer            recipient, amount
    101,          // 2  purchase_seat              seat, flag, referrer, signature
    68,           // 3  activate_seat              seat, signature
    100,          // 4  mint_node                  seat, destination, signature
    96,           // 5  mint_referral              destination, signature
    105,          // 6  direct_issue               channel, decision, beneficiary, ...
    kUnassigned,  // 7  retired: mint_node_verified
    kUnassigned,  // 8  retired: set_mint_biometric
    kUnassigned,  // 9  retired: add_manager
    132,          // 10 hub_register               identity, signer key, seat, sig
    kUnassigned,  // 11 retired: hub_add_address
    kUnassigned,  // 12 retired: hub_remove_address
    64,           // 13 escrow_create              identity, fee escrow
    96,           // 14 escrow_delete              identity, target, fee escrow
    96,           // 15 signer_add                 identity, escrow, new key
    96,           // 16 signer_revoke              identity, escrow, signer
    77,           // 17 set_security_posture       flag, minimum, mask, signature
    96,           // 18 mint_verified_user         destination, signature
    104,          // 19 native_transfer_verified   recipient, amount, signature
    44,           // 20 challenge_response         seat, challenge height, answer
    78,           // 21 file_dispute               seat, window, slot, reason, sig
    100,          // 22 mint_monthly_pool          seat, destination, signature
    196,          // 23 register_machine_key       seat, key, digest, two sigs
};

// **Kind 22's width is kind 4's and the collision is deliberate.** Every other
// pair sharing a width shares one by arithmetic; these two share a body because
// a mint of a seat's award is authorized the way a mint of a seat's permissions
// is, field for field. The kind byte is what separates them, in the dispatcher
// and in the HUB confirmation both of them bind.
static_assert(kBodyBytes[22] == kBodyBytes[4],
              "kind 22's body is kind 4's exactly");
// Kind 10 gains the attesting seat and nothing else, so its width is version
// nine's 128 plus one `u32`.
static_assert(kBodyBytes[10] == 128 + 4,
              "kind 10's body is version nine's with the attesting seat");

// Scheme 2 is confined to the six administrative kinds, which are exactly the
// transactions a person must be able to make holding no key at all.
constexpr std::array<std::uint8_t, 24> kKindScheme{
    kNoScheme,        // 0
    kSchemeSigner,    // 1
    kSchemeSigner,    // 2
    kSchemeSigner,    // 3
    kSchemeSigner,    // 4
    kSchemeSigner,    // 5
    kSchemeSigner,    // 6
    kNoScheme,        // 7
    kNoScheme,        // 8
    kNoScheme,        // 9
    kSchemeIdentity,  // 10
    kNoScheme,        // 11
    kNoScheme,        // 12
    kSchemeIdentity,  // 13
    kSchemeIdentity,  // 14
    kSchemeIdentity,  // 15
    kSchemeIdentity,  // 16
    kSchemeSigner,    // 17
    kSchemeSigner,    // 18
    kSchemeSigner,    // 19
    // Both of version eight's kinds are scheme 1. A response is signed by a
    // signer the seat's identity owns; a dispute is relayed by any signer, and
    // the dispute authority signs the body rather than the envelope, so the
    // ecosystem AI needs no chain account, nonce, balance, or fee obligation.
    kSchemeSigner,    // 20
    kSchemeSigner,    // 21
    // Version nine's kind is kind 4's exactly, scheme included: a mint of a
    // seat's award is authorized the way a mint of a seat's permissions is.
    kSchemeSigner,    // 22
    // Version ten's kind is signed by a signer that resolves the acting escrow,
    // and the seat's owner approves it with the HUB key in the body, as kinds 3
    // and 4 are.
    kSchemeSigner,    // 23
};

constexpr std::array<std::uint8_t, 5> kRetiredKinds{7, 8, 9, 11, 12};
// Entry kind 7 held the ten per-channel carries and is version seven's
// retirement; 9 and 11 held the seat manager set and the HUB address set and
// were version six's. A retired number is never reused, which is why version
// eight's two entries take 18 and 19 rather than filling a gap, version nine's
// four take 20 through 23, and version ten's three take 24 through 26.
constexpr std::array<std::uint8_t, 3> kRetiredEntryKinds{7, 9, 11};

constexpr std::array<std::size_t, 27> kEntryKeyBytes{
    kUnassigned,  // 0, never an entry kind
    5,            // 1  seat                        u32 seat id
    2,            // 2  channel                     u8 channel id
    9,            // 3  cycle_assignment            u64 window
    33,           // 4  referral_balance            identity hash
    33,           // 5  direct_decision             decision id
    34,           // 6  typed_custody               kind, beneficiary id
    kUnassigned,  // 7  retired: carry
    1,            // 8  verifier_key
    kUnassigned,  // 9  retired: seat_manager
    33,           // 10 hub_identity                identity hash
    kUnassigned,  // 11 retired: hub_address
    1,            // 12 unreferred_pool
    33,           // 13 escrow                      escrow id
    33,           // 14 signer                      signer id
    33,           // 15 verified_user_enrollment    identity hash
    1,            // 16 verified_user_counter
    1,            // 17 recovery_pool
    13,           // 18 open_challenge              u64 height, u32 seat id
    13,           // 19 seat_window                 u64 window, u32 seat id
    9,            // 20 window_month                u64 window
    9,            // 21 monthly_uptime_figure       u32 month, u32 seat id
    5,            // 22 monthly_pool_claim          u32 seat id
    1,            // 23 settlement_cursor
    5,            // 24 machine_key                 u32 seat id
    1,            // 25 launch_retirement
    33,           // 26 machine_key_owner           machine public key
};

// A second sentinel, for the one variable-width value: the cycle assignment,
// whose width follows from a recorded bit count rather than from a table.
constexpr std::size_t kVariableValue = static_cast<std::size_t>(-2);

constexpr std::array<std::size_t, 27> kEntryValueBytes{
    kUnassigned,     // 0
    82,              // 1  seat
    16,              // 2  channel
    kVariableValue,  // 3  cycle_assignment
    24,              // 4  referral_balance
    0,               // 5  direct_decision
    8,               // 6  typed_custody
    kUnassigned,     // 7  retired: carry
    32,              // 8  verifier_key
    kUnassigned,     // 9
    52,              // 10 hub_identity
    kUnassigned,     // 11
    24,              // 12 unreferred_pool          accrued, payable, minted
    49,              // 13 escrow
    32,              // 14 signer
    24,              // 15 verified_user_enrollment
    8,               // 16 verified_user_counter
    40,              // 17 recovery_pool             five u64 legs
    1,               // 18 open_challenge            u8 state
    8,               // 19 seat_window               two u32 bitmaps
    4,               // 20 window_month              u32 month index
    8,               // 21 monthly_uptime_figure     u64 seconds, nonzero
    16,              // 22 monthly_pool_claim        accrued, minted
    4,               // 23 settlement_cursor         u32 month index
    92,              // 24 machine_key               key, digest, three u64, u32
    8,               // 25 launch_retirement         u64 height, nonzero
    4,               // 26 machine_key_owner         u32 seat id
};

template <std::size_t Size>
bool contains(const std::array<std::uint8_t, Size>& table, std::uint8_t value) {
  for (const auto entry : table) {
    if (entry == value) return true;
  }
  return false;
}

}  // namespace

bool is_transaction_kind(std::uint8_t kind) {
  return kind < kBodyBytes.size() && kBodyBytes[kind] != kUnassigned;
}

bool is_retired_kind(std::uint8_t kind) { return contains(kRetiredKinds, kind); }

bool is_approval_kind(std::uint8_t kind) { return contains(kApprovalKinds, kind); }

bool is_always_proven_kind(std::uint8_t kind) {
  return contains(kAlwaysProvenKinds, kind);
}

std::optional<std::string_view> result_code_name(std::uint8_t code) {
  if (code >= kResultCodeNames.size()) return std::nullopt;
  return kResultCodeNames[code];
}

bool is_entry_kind(std::uint8_t entry_kind) {
  return entry_kind < kEntryKeyBytes.size() &&
         kEntryKeyBytes[entry_kind] != kUnassigned;
}

bool is_retired_entry_kind(std::uint8_t entry_kind) {
  return contains(kRetiredEntryKinds, entry_kind);
}

std::optional<std::size_t> body_bytes(std::uint8_t kind) {
  if (!is_transaction_kind(kind)) return std::nullopt;
  return kBodyBytes[kind];
}

std::optional<std::size_t> unsigned_bytes(std::uint8_t kind) {
  const auto body = body_bytes(kind);
  if (!body) return std::nullopt;
  return kHeaderBytes + *body + kTrailerBytes;
}

std::optional<std::size_t> signed_bytes(std::uint8_t kind) {
  const auto unsigned_size = unsigned_bytes(kind);
  if (!unsigned_size) return std::nullopt;
  return *unsigned_size + kSignatureBytes;
}

std::optional<std::uint8_t> kind_scheme(std::uint8_t kind) {
  if (!is_transaction_kind(kind)) return std::nullopt;
  return kKindScheme[kind];
}

std::optional<std::size_t> entry_key_bytes(std::uint8_t entry_kind) {
  if (!is_entry_kind(entry_kind)) return std::nullopt;
  return kEntryKeyBytes[entry_kind];
}

std::optional<std::size_t> entry_value_bytes(std::uint8_t entry_kind) {
  if (!is_entry_kind(entry_kind)) return std::nullopt;
  const auto width = kEntryValueBytes[entry_kind];
  if (width == kVariableValue) return std::nullopt;
  return width;
}

}  // namespace protocol::v10
