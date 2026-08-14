#include "economy_internal.hpp"

namespace protocol::v4 {
namespace {

namespace i = protocol::v4::internal;

constexpr std::string_view kRegistrationLabel = "protocol-stack:v4:hub-registration";
constexpr std::string_view kAddressAddLabel = "protocol-stack:v4:hub-address-add";
constexpr std::string_view kAddressRemoveLabel = "protocol-stack:v4:hub-address-remove";
constexpr std::string_view kPurchaseLabel = "protocol-stack:v4:seat-purchase";
constexpr std::string_view kActivationLabel = "protocol-stack:v4:seat-activation";
constexpr std::string_view kMintLabel = "protocol-stack:v4:seat-mint";
constexpr std::string_view kDisableLabel = "protocol-stack:v4:mint-biometric-disable";
constexpr std::string_view kManagerLabel = "protocol-stack:v4:seat-manager";

// Every message opens with its domain label, length-prefixed, and then names the
// identity. Naming the identity is what stops one person's signature being
// presented as another's where the remaining fields coincide.
Bytes opened(std::string_view label, std::span<const std::uint8_t> chain_id,
             std::span<const std::uint8_t> hub_identity_hash) {
  Bytes message;
  message.push_back(static_cast<std::uint8_t>(label.size()));
  message.insert(message.end(), label.begin(), label.end());
  i::append(message, chain_id);
  i::append(message, hub_identity_hash);
  return message;
}

// Three messages share this shape and are separated only by their labels, which
// is what domain separation is for: an approval to activate a seat must not be
// presentable as an approval to mint from it or to remove its protection.
Bytes seat_action(std::string_view label, std::span<const std::uint8_t> chain_id,
                  std::span<const std::uint8_t> hub_identity_hash,
                  std::uint32_t seat_id, std::uint64_t valid_until_height) {
  auto message = opened(label, chain_id, hub_identity_hash);
  i::append_u32(message, seat_id);
  i::append_u64(message, valid_until_height);
  return message;
}

Bytes account_action(std::string_view label, std::span<const std::uint8_t> chain_id,
                     std::span<const std::uint8_t> hub_identity_hash,
                     std::span<const std::uint8_t> account_id,
                     std::uint64_t valid_until_height) {
  auto message = opened(label, chain_id, hub_identity_hash);
  i::append(message, account_id);
  i::append_u64(message, valid_until_height);
  return message;
}

}  // namespace

Bytes registration_message(std::span<const std::uint8_t> chain_id,
                           std::span<const std::uint8_t> hub_identity_hash,
                           std::span<const std::uint8_t> hub_public_key,
                           std::span<const std::uint8_t> sender_account_id,
                           std::uint64_t valid_until_height) {
  auto message = opened(kRegistrationLabel, chain_id, hub_identity_hash);
  i::append(message, hub_public_key);
  i::append(message, sender_account_id);
  i::append_u64(message, valid_until_height);
  return message;
}

Bytes address_add_message(std::span<const std::uint8_t> chain_id,
                          std::span<const std::uint8_t> hub_identity_hash,
                          std::span<const std::uint8_t> account_id,
                          std::uint64_t valid_until_height) {
  return account_action(kAddressAddLabel, chain_id, hub_identity_hash, account_id,
                        valid_until_height);
}

Bytes address_remove_message(std::span<const std::uint8_t> chain_id,
                             std::span<const std::uint8_t> hub_identity_hash,
                             std::span<const std::uint8_t> account_id,
                             std::uint64_t valid_until_height) {
  return account_action(kAddressRemoveLabel, chain_id, hub_identity_hash, account_id,
                        valid_until_height);
}

Bytes purchase_message(std::span<const std::uint8_t> chain_id,
                       std::span<const std::uint8_t> hub_identity_hash,
                       std::uint32_t seat_id,
                       std::span<const std::uint8_t> purchaser_account_id,
                       std::uint64_t valid_until_height) {
  auto message = opened(kPurchaseLabel, chain_id, hub_identity_hash);
  i::append_u32(message, seat_id);
  i::append(message, purchaser_account_id);
  i::append_u64(message, valid_until_height);
  return message;
}

Bytes activation_message(std::span<const std::uint8_t> chain_id,
                         std::span<const std::uint8_t> hub_identity_hash,
                         std::uint32_t seat_id, std::uint64_t valid_until_height) {
  return seat_action(kActivationLabel, chain_id, hub_identity_hash, seat_id,
                     valid_until_height);
}

Bytes mint_message(std::span<const std::uint8_t> chain_id,
                   std::span<const std::uint8_t> hub_identity_hash,
                   std::uint32_t seat_id, std::uint64_t valid_until_height) {
  return seat_action(kMintLabel, chain_id, hub_identity_hash, seat_id,
                     valid_until_height);
}

Bytes mint_biometric_disable_message(std::span<const std::uint8_t> chain_id,
                                     std::span<const std::uint8_t> hub_identity_hash,
                                     std::uint32_t seat_id,
                                     std::uint64_t valid_until_height) {
  return seat_action(kDisableLabel, chain_id, hub_identity_hash, seat_id,
                     valid_until_height);
}

Bytes manager_message(std::span<const std::uint8_t> chain_id,
                      std::span<const std::uint8_t> hub_identity_hash,
                      std::uint32_t seat_id,
                      std::span<const std::uint8_t> manager_account_id,
                      std::uint64_t valid_until_height) {
  auto message = opened(kManagerLabel, chain_id, hub_identity_hash);
  i::append_u32(message, seat_id);
  i::append(message, manager_account_id);
  i::append_u64(message, valid_until_height);
  return message;
}

}  // namespace protocol::v4
