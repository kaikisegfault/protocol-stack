#pragma once

// The canonical byte surface of `economy-transition-v4`.
//
// This header declares the codec alone: the transaction envelope and its twelve
// bodies, the eight HUB messages, the economy state key space, the economy tree
// and the version-four state root, genesis and chain identity, and the receipt.
// It performs no state transition and reads no ledger, which is why every entry
// point here is a pure function of its arguments.
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
#include <string>
#include <string_view>
#include <vector>

namespace protocol::v4 {

using Bytes = protocol::v1::Bytes;
using Hash = protocol::v1::Hash;
using Octets32 = std::array<std::uint8_t, 32>;

// The envelope is version one's, unchanged: the header is the accepted transfer's
// first 80 bytes and the trailer its last 16, so kind 1's body is what remains.
inline constexpr std::size_t kHeaderBytes = 80;
inline constexpr std::size_t kTrailerBytes = 16;
inline constexpr std::size_t kSignatureBytes = 64;
inline constexpr std::uint16_t kEnvelopeSchemaVersion = 1;
inline constexpr std::uint8_t kSignatureScheme = 1;
inline constexpr std::uint16_t kReceiptVersion = 4;
inline constexpr std::uint16_t kGenesisSchemaVersion = 4;
inline constexpr std::uint16_t kStateRootSchemaVersion = 4;
inline constexpr std::size_t kReceiptBytes = 56;
inline constexpr std::size_t kGenesisPrefixBytes = 110;
inline constexpr std::size_t kAccountEntryBytes = 48;
inline constexpr std::size_t kMaxObjectBytes = 1'048'576;
inline constexpr std::size_t kMaxGenesisAccounts =
    (kMaxObjectBytes - kGenesisPrefixBytes) / kAccountEntryBytes;

inline constexpr std::uint32_t kFounderSeatCapacity = 100'000;
inline constexpr std::uint32_t kMaxSeatId = kFounderSeatCapacity - 1;
inline constexpr std::uint32_t kMaxSeatsPerIdentity = 1'000;
inline constexpr std::uint32_t kMaxSeatManagers = 16;
inline constexpr std::uint32_t kMaxIdentityAddresses = 16;

// One flat space, extending version three's contiguously: codes 0 through 23
// keep their exact version-three meanings and 0 through 8 their version-one
// meanings. `SEAT_LIMIT` and `ADDRESS_LIMIT` are the two version four adds.
inline constexpr std::uint8_t kResultCodeCount = 26;
inline constexpr std::uint8_t kSuccessResultCode = 0;

// The version-one labels, deliberately not re-versioned: re-versioning would
// destroy the kind-1 byte identity for separation the preimage already carries.
inline constexpr std::string_view kSignLabel = "protocol-stack:v1:tx-sign";
inline constexpr std::string_view kTransactionIdLabel = "protocol-stack:v1:tx-id";
inline constexpr std::string_view kChainIdLabel = "protocol-stack:v4:chain-id";
inline constexpr std::string_view kStateRootLabel = "protocol-stack:v4:state-root";
inline constexpr std::string_view kEconomyTreePrefix = "protocol-stack:v4:economy";
inline constexpr std::string_view kAccountsTreePrefix = "protocol-stack:v1:state";

enum class Kind : std::uint8_t {
  native_transfer = 1,
  purchase_seat = 2,
  activate_seat = 3,
  mint_node = 4,
  mint_referral = 5,
  direct_issue = 6,
  mint_node_verified = 7,
  set_mint_biometric = 8,
  add_manager = 9,
  hub_register = 10,
  hub_add_address = 11,
  hub_remove_address = 12,
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
  seat_manager = 9,
  hub_identity = 10,
  hub_address = 11,
  unreferred_pool = 12,
};

// Every kind is fixed-length. Two pairs coincide — kinds 3 and 7, kinds 11 and
// 12 — so a decoder dispatches on the kind byte rather than on the length.
bool is_transaction_kind(std::uint8_t kind);
bool is_entry_kind(std::uint8_t entry_kind);

std::optional<std::size_t> body_bytes(std::uint8_t kind);
std::optional<std::size_t> signed_bytes(std::uint8_t kind);
std::optional<std::size_t> entry_key_bytes(std::uint8_t entry_kind);
// `nullopt` for an unknown kind, and for the one variable-width value — the
// cycle assignment, whose width follows from its recorded bit count.
// `is_entry_kind` distinguishes the two.
std::optional<std::size_t> entry_value_bytes(std::uint8_t entry_kind);

struct Envelope {
  std::uint8_t kind = 0;
  Octets32 chain_id{};
  Octets32 sender_public_key{};
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
// execution.
std::optional<DecodedTransaction> decode_signed(std::span<const std::uint8_t> raw);

// The eight HUB messages. Seven verify against the acting identity's recorded
// public key; only the registration verifies against the ecosystem verifier key.
Bytes registration_message(std::span<const std::uint8_t> chain_id,
                           std::span<const std::uint8_t> hub_identity_hash,
                           std::span<const std::uint8_t> hub_public_key,
                           std::span<const std::uint8_t> sender_account_id,
                           std::uint64_t valid_until_height);
Bytes address_add_message(std::span<const std::uint8_t> chain_id,
                          std::span<const std::uint8_t> hub_identity_hash,
                          std::span<const std::uint8_t> account_id,
                          std::uint64_t valid_until_height);
Bytes address_remove_message(std::span<const std::uint8_t> chain_id,
                             std::span<const std::uint8_t> hub_identity_hash,
                             std::span<const std::uint8_t> account_id,
                             std::uint64_t valid_until_height);
Bytes purchase_message(std::span<const std::uint8_t> chain_id,
                       std::span<const std::uint8_t> hub_identity_hash,
                       std::uint32_t seat_id,
                       std::span<const std::uint8_t> purchaser_account_id,
                       std::uint64_t valid_until_height);
Bytes activation_message(std::span<const std::uint8_t> chain_id,
                         std::span<const std::uint8_t> hub_identity_hash,
                         std::uint32_t seat_id, std::uint64_t valid_until_height);
Bytes mint_message(std::span<const std::uint8_t> chain_id,
                   std::span<const std::uint8_t> hub_identity_hash,
                   std::uint32_t seat_id, std::uint64_t valid_until_height);
Bytes mint_biometric_disable_message(std::span<const std::uint8_t> chain_id,
                                     std::span<const std::uint8_t> hub_identity_hash,
                                     std::uint32_t seat_id,
                                     std::uint64_t valid_until_height);
Bytes manager_message(std::span<const std::uint8_t> chain_id,
                      std::span<const std::uint8_t> hub_identity_hash,
                      std::uint32_t seat_id,
                      std::span<const std::uint8_t> manager_account_id,
                      std::uint64_t valid_until_height);

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
Bytes seat_manager_key(std::uint32_t seat_id,
                       std::span<const std::uint8_t> manager_account_id);
Bytes hub_identity_key(std::span<const std::uint8_t> hub_identity_hash);
Bytes hub_address_key(std::span<const std::uint8_t> account_id);
Bytes unreferred_pool_key();

struct SeatRecord {
  Octets32 hub_identity_hash{};
  Octets32 purchaser_account_id{};
  bool has_referrer = false;
  Octets32 referrer_hub_identity{};
  bool is_activated = false;
  std::uint64_t activation_height = 0;
  std::uint64_t minted_through_window = 0;
  bool mint_requires_biometric = false;
  std::uint32_t manager_count = 1;
};

struct HubIdentityRecord {
  Octets32 hub_public_key{};
  std::uint64_t registered_at_height = 0;
  std::uint32_t address_count = 1;
  std::uint32_t seat_count = 0;
};

// The record the chain writes when a cycle is finalised. The two bitmaps are
// indexed by seat identifier, most significant bit first, and carry no length
// prefixes: both widths follow from `bitmap_bits`.
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
Bytes hub_address_value(std::span<const std::uint8_t> hub_identity_hash);
Bytes cycle_assignment_value(const CycleAssignment& assignment);
std::optional<CycleAssignment> decode_cycle_assignment_value(
    std::span<const std::uint8_t> raw);

std::size_t bitmap_bytes(std::uint32_t bitmap_bits);
Bytes bitmap(std::span<const std::uint32_t> seat_ids, std::uint32_t bitmap_bits);
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
// length-prefixed `bytes` primitive for both halves.
Hash economy_root(std::vector<EconomyEntry> entries);
Hash accounts_root(std::span<const AccountEntry> accounts);

struct StateSummary {
  Octets32 chain_id{};
  std::uint64_t height = 0;
  std::uint64_t supply_limit = 0;
  std::uint64_t total_supply = 0;
  std::uint64_t fee_pool_balance = 0;
};

Hash state_root(const StateSummary& summary, std::span<const AccountEntry> accounts,
                std::vector<EconomyEntry> economy);

struct Genesis {
  std::uint32_t network_id = 0;
  std::uint64_t supply_limit = 0;
  std::uint64_t total_supply = 0;
  std::uint64_t fixed_transfer_fee = 0;
  std::uint64_t initial_fee_pool = 0;
  Octets32 manifest_digest{};
  Octets32 verifier_key{};
  std::vector<AccountEntry> accounts;
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

}  // namespace protocol::v4
