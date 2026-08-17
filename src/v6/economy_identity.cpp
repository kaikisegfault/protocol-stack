#include "economy_internal.hpp"

#include "../v1/account.hpp"

#include "protocol/v1/crypto.hpp"

namespace protocol::v6 {
namespace {

namespace i = protocol::v6::internal;

}  // namespace

Hash escrow_id(std::span<const std::uint8_t> hub_identity_hash,
               std::uint32_t escrow_index) {
  Bytes payload;
  payload.reserve(hub_identity_hash.size() + 4);
  i::append(payload, hub_identity_hash);
  i::append_u32(payload, escrow_index);
  return protocol::v1::hash(kEscrowLabel, payload);
}

Hash signer_id(std::span<const std::uint8_t> ed25519_public_key) {
  // The version-one kernel's own derivation rather than a second copy of it.
  // A restatement here would agree with itself while both drifted, which is
  // exactly what the accepted vectors check this against.
  const auto identifier =
      protocol::v1::internal::account_id_from_public_key(ed25519_public_key);
  Hash value{};
  std::copy(identifier.begin(), identifier.end(), value.begin());
  return value;
}

std::uint32_t slot_of(std::uint64_t height) {
  return static_cast<std::uint32_t>((height % kCycleBlocks) / kSlotBlocks);
}

bool requires_confirmation(const Posture& posture, std::uint64_t amount,
                           std::uint64_t height) {
  if (!posture.requires_confirmation) return false;
  // A minimum of zero means every amount requires a confirmation, because every
  // amount is at least zero. A person who wants none below one unit sets the
  // minimum to 100,000,000.
  if (amount < posture.min_amount_atomic) return false;
  const auto slot = slot_of(height);
  return ((posture.exempt_slot_mask >> slot) & 1U) == 0U;
}

bool relaxes(const Posture& current, const Posture& proposed) {
  // The three ways to shrink the set of operations that require a confirmation,
  // each checked independently. A change that tightens one field and relaxes
  // another therefore counts as a relaxation and needs the HUB signature: the
  // failure that matters is a stolen key weakening a protection, so a mixed
  // change that weakens anything is a weakening.
  if (current.requires_confirmation && !proposed.requires_confirmation) return true;
  if (proposed.min_amount_atomic > current.min_amount_atomic) return true;
  return (proposed.exempt_slot_mask & ~current.exempt_slot_mask) != 0U;
}

}  // namespace protocol::v6
