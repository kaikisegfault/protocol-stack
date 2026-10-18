#include "economy_internal.hpp"

namespace protocol::v10 {
namespace {

namespace i = protocol::v10::internal;

}  // namespace

// **Version ten's registration, under a version-ten label.** Version nine's
// opened with the identity straight after the chain; this one names the
// attesting seat first, so the machine that signed is bound before anything
// about the person, and a signature under one seat's key cannot be presented
// under another seat. The other four fields and their order are version nine's.
//
// **The five per-action HUB messages version nine defined are gone**, and their
// labels with them. One approval over the whole transaction replaces them, in
// `economy_registry.cpp`, because their field lists are where version nine's
// replay got in.
Bytes registration_message(std::span<const std::uint8_t> chain_id,
                           std::uint32_t attesting_seat_id,
                           std::span<const std::uint8_t> hub_identity_hash,
                           std::span<const std::uint8_t> hub_public_key,
                           std::span<const std::uint8_t> first_signer_public_key,
                           std::uint64_t valid_until_height) {
  Bytes message;
  i::append_domain(message, kRegistrationLabel);
  i::append(message, chain_id);
  i::append_u32(message, attesting_seat_id);
  i::append(message, hub_identity_hash);
  i::append(message, hub_public_key);
  i::append(message, first_signer_public_key);
  i::append_u64(message, valid_until_height);
  return message;
}

// The dispute message, carried unchanged from version eight, and the only
// signed construction that is not a HUB or registry message.
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

}  // namespace protocol::v10
