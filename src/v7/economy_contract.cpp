#include "protocol/v7/economy.hpp"

#include <array>
#include <string_view>

namespace protocol::v7 {
namespace {

// The frozen numeric result space, extended contiguously. Codes 0 through 8 are
// version one's, 9 through 25 are versions two through four's, and 26 through 32
// are version six's own; no number is ever renumbered or reused.
constexpr std::array<std::string_view, 33> kResultCodeNames{
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
constexpr std::array<std::size_t, 20> kBodyBytes{
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
    128,          // 10 hub_register               identity, signer key, signature
    kUnassigned,  // 11 retired: hub_add_address
    kUnassigned,  // 12 retired: hub_remove_address
    64,           // 13 escrow_create              identity, fee escrow
    96,           // 14 escrow_delete              identity, target, fee escrow
    96,           // 15 signer_add                 identity, escrow, new key
    96,           // 16 signer_revoke              identity, escrow, signer
    77,           // 17 set_security_posture       flag, minimum, mask, signature
    96,           // 18 mint_verified_user         destination, signature
    104,          // 19 native_transfer_verified   recipient, amount, signature
};

// Scheme 2 is confined to the six administrative kinds, which are exactly the
// transactions a person must be able to make holding no key at all.
constexpr std::array<std::uint8_t, 20> kKindScheme{
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
};

constexpr std::array<std::uint8_t, 5> kRetiredKinds{7, 8, 9, 11, 12};
// Entry kind 7 held the ten per-channel carries and is version seven's own
// retirement; 9 and 11 held the seat manager set and the HUB address set and
// were version six's. A retired number is never reused.
constexpr std::array<std::uint8_t, 3> kRetiredEntryKinds{7, 9, 11};

constexpr std::array<std::size_t, 18> kEntryKeyBytes{
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
};

// A second sentinel, for the one variable-width value: the cycle assignment,
// whose width follows from a recorded bit count rather than from a table.
constexpr std::size_t kVariableValue = static_cast<std::size_t>(-2);

constexpr std::array<std::size_t, 18> kEntryValueBytes{
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
    16,              // 12 unreferred_pool
    49,              // 13 escrow
    32,              // 14 signer
    24,              // 15 verified_user_enrollment
    8,               // 16 verified_user_counter
    40,              // 17 recovery_pool             five u64 legs
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

}  // namespace protocol::v7
