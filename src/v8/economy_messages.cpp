#include "economy_internal.hpp"

namespace protocol::v8 {
namespace {

namespace i = protocol::v8::internal;

constexpr std::string_view kRegistrationLabel = "protocol-stack:v6:hub-registration";
constexpr std::string_view kPurchaseLabel = "protocol-stack:v6:seat-purchase";
constexpr std::string_view kActivationLabel = "protocol-stack:v6:seat-activation";
constexpr std::string_view kMintLabel = "protocol-stack:v6:mint-confirm";
constexpr std::string_view kPostureRelaxLabel = "protocol-stack:v6:posture-relax";
constexpr std::string_view kTransferConfirmLabel = "protocol-stack:v6:transfer-confirm";

// Every message opens with its domain label and then names the chain and the
// identity. Naming the identity is what stops one person's signature being
// presented as another's where the remaining fields coincide.
Bytes opened(std::string_view label, std::span<const std::uint8_t> chain_id,
             std::span<const std::uint8_t> hub_identity_hash) {
  Bytes message;
  i::append_domain(message, label);
  i::append(message, chain_id);
  i::append(message, hub_identity_hash);
  return message;
}

// Purchase and activation carry identical field shapes and are separated only
// by their labels, which is what domain separation is for: an approval to buy a
// seat must not be presentable as an approval to activate it.
Bytes seat_action(std::string_view label, std::span<const std::uint8_t> chain_id,
                  std::span<const std::uint8_t> hub_identity_hash,
                  std::uint32_t seat_id, std::uint64_t valid_until_height) {
  auto message = opened(label, chain_id, hub_identity_hash);
  i::append_u32(message, seat_id);
  i::append_u64(message, valid_until_height);
  return message;
}

}  // namespace

Bytes registration_message(std::span<const std::uint8_t> chain_id,
                           std::span<const std::uint8_t> hub_identity_hash,
                           std::span<const std::uint8_t> hub_public_key,
                           std::span<const std::uint8_t> first_signer_public_key,
                           std::uint64_t valid_until_height) {
  auto message = opened(kRegistrationLabel, chain_id, hub_identity_hash);
  i::append(message, hub_public_key);
  i::append(message, first_signer_public_key);
  i::append_u64(message, valid_until_height);
  return message;
}

Bytes purchase_message(std::span<const std::uint8_t> chain_id,
                       std::span<const std::uint8_t> hub_identity_hash,
                       std::uint32_t seat_id, std::uint64_t valid_until_height) {
  return seat_action(kPurchaseLabel, chain_id, hub_identity_hash, seat_id,
                     valid_until_height);
}

Bytes activation_message(std::span<const std::uint8_t> chain_id,
                         std::span<const std::uint8_t> hub_identity_hash,
                         std::uint32_t seat_id, std::uint64_t valid_until_height) {
  return seat_action(kActivationLabel, chain_id, hub_identity_hash, seat_id,
                     valid_until_height);
}

Bytes mint_message(std::span<const std::uint8_t> chain_id,
                   std::span<const std::uint8_t> hub_identity_hash,
                   std::uint8_t transaction_kind, std::uint32_t seat_id,
                   std::span<const std::uint8_t> destination_escrow_id,
                   std::uint64_t valid_until_height) {
  auto message = opened(kMintLabel, chain_id, hub_identity_hash);
  i::append_u8(message, transaction_kind);
  i::append_u32(message, seat_id);
  i::append(message, destination_escrow_id);
  i::append_u64(message, valid_until_height);
  return message;
}

Bytes posture_relax_message(std::span<const std::uint8_t> chain_id,
                            std::span<const std::uint8_t> hub_identity_hash,
                            std::span<const std::uint8_t> escrow_id,
                            const Posture& proposed,
                            std::uint64_t valid_until_height) {
  auto message = opened(kPostureRelaxLabel, chain_id, hub_identity_hash);
  i::append(message, escrow_id);
  i::append_u8(message, proposed.requires_confirmation ? 1 : 0);
  i::append_u64(message, proposed.min_amount_atomic);
  i::append_u32(message, proposed.exempt_slot_mask);
  i::append_u64(message, valid_until_height);
  return message;
}

Bytes transfer_confirm_message(std::span<const std::uint8_t> chain_id,
                               std::span<const std::uint8_t> hub_identity_hash,
                               std::span<const std::uint8_t> escrow_id,
                               std::span<const std::uint8_t> recipient_escrow_id,
                               std::uint64_t amount,
                               std::uint64_t valid_until_height) {
  auto message = opened(kTransferConfirmLabel, chain_id, hub_identity_hash);
  i::append(message, escrow_id);
  i::append(message, recipient_escrow_id);
  i::append_u64(message, amount);
  i::append_u64(message, valid_until_height);
  return message;
}

// The seventh signed construction, and the only one that is not a HUB message.
//
// It names no identity, because the signer is not the subject: the dispute
// authority is judging a seat rather than acting for a person. What it binds
// instead is the chain, so a decision cannot be moved between chains, and
// `valid_until_height`, so a signature cannot be held indefinitely before it is
// relayed. The reason code carries no protocol effect and is bound anyway, so a
// relayer cannot alter the stated reason of a decision it did not make.
Bytes dispute_message(std::span<const std::uint8_t> chain_id, std::uint32_t seat_id,
                      std::uint64_t cycle_window, std::uint8_t slot_index,
                      std::uint8_t reason_code, std::uint64_t valid_until_height) {
  Bytes message;
  i::append_domain(message, kDisputeLabel);
  i::append(message, chain_id);
  i::append_u32(message, seat_id);
  i::append_u64(message, cycle_window);
  i::append_u8(message, slot_index);
  i::append_u8(message, reason_code);
  i::append_u64(message, valid_until_height);
  return message;
}

}  // namespace protocol::v8
