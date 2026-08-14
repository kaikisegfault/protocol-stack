#include "protocol/v4/economy.hpp"

#include <array>

namespace protocol::v4 {
namespace {

// Every kind is fixed-length. Kinds 3 and 7 coincide because both name a seat
// and carry one signature; kinds 11 and 12 coincide because both name an
// account and carry one. Version two recorded that a decoder must dispatch on
// the kind byte rather than on the length for exactly this case, so the
// coincidence is the anticipated one rather than a defect.
constexpr std::array<std::size_t, 13> kBodyBytes{
    0,    // no kind 0
    40,   // native_transfer
    133,  // purchase_seat
    68,   // activate_seat
    4,    // mint_node
    0,    // mint_referral
    105,  // direct_issue
    68,   // mint_node_verified
    69,   // set_mint_biometric
    100,  // add_manager
    128,  // hub_register
    96,   // hub_add_address
    96,   // hub_remove_address
};

constexpr std::array<std::size_t, 13> kEntryKeyBytes{
    0,   // no entry kind 0
    5,   // seat
    2,   // channel
    9,   // cycle_assignment
    33,  // referral_balance
    33,  // direct_decision
    34,  // typed_custody
    2,   // carry
    1,   // verifier_key
    37,  // seat_manager
    33,  // hub_identity
    33,  // hub_address
    1,   // unreferred_pool
};

// A sentinel rather than an optional in the table: the cycle assignment is the
// only variable-width value, and its width follows from a recorded bit count.
constexpr std::size_t kVariableValue = static_cast<std::size_t>(-1);

constexpr std::array<std::size_t, 13> kEntryValueBytes{
    0,               // no entry kind 0
    119,             // seat
    16,              // channel
    kVariableValue,  // cycle_assignment
    24,              // referral_balance
    0,               // direct_decision
    8,               // typed_custody
    8,               // carry
    32,              // verifier_key
    0,               // seat_manager
    48,              // hub_identity
    32,              // hub_address
    16,              // unreferred_pool
};

constexpr bool is_kind(std::uint8_t kind) { return kind >= 1 && kind <= 12; }

}  // namespace

bool is_transaction_kind(std::uint8_t kind) { return is_kind(kind); }

bool is_entry_kind(std::uint8_t entry_kind) { return is_kind(entry_kind); }

std::optional<std::size_t> body_bytes(std::uint8_t kind) {
  if (!is_kind(kind)) return std::nullopt;
  return kBodyBytes[kind];
}

std::optional<std::size_t> signed_bytes(std::uint8_t kind) {
  const auto body = body_bytes(kind);
  if (!body) return std::nullopt;
  return kHeaderBytes + *body + kTrailerBytes + kSignatureBytes;
}

std::optional<std::size_t> entry_key_bytes(std::uint8_t entry_kind) {
  if (!is_kind(entry_kind)) return std::nullopt;
  return kEntryKeyBytes[entry_kind];
}

std::optional<std::size_t> entry_value_bytes(std::uint8_t entry_kind) {
  if (!is_kind(entry_kind)) return std::nullopt;
  const auto width = kEntryValueBytes[entry_kind];
  if (width == kVariableValue) return std::nullopt;
  return width;
}

}  // namespace protocol::v4
