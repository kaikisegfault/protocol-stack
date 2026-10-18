// Everything version ten adds to the codec: the machine-key registry's three
// entries, the build authority's attestation, the one approval message, and the
// approval lifetime rule.
//
// **This is the one translation unit version nine does not have**, so the
// difference between the two codecs is this file plus the edits the contract
// forces in six others: the kind and entry tables, kind 10's body and kind
// 23's, the registration message, the genesis field, the receipt's kind set,
// and the tree's content checks and ninth predecessor root. That is the shape
// every port since version eight has kept, and it is why a reader can audit
// this one while both kernels compile.

#include "economy_internal.hpp"

namespace protocol::v10 {
namespace {

namespace i = protocol::v10::internal;

constexpr std::size_t kMachineKeyValueBytes = 92;
constexpr std::size_t kLaunchRetirementValueBytes = 8;
constexpr std::size_t kMachineKeyOwnerValueBytes = 4;

const Bytes kNoSignature(kSignatureBytes, 0);

}  // namespace

// --- the three entries ------------------------------------------------------

Bytes machine_key_key(std::uint32_t seat_id) {
  auto key = i::key_prefix(Entry::machine_key);
  i::append_u32(key, seat_id);
  return key;
}

Bytes launch_retirement_key() { return i::key_prefix(Entry::launch_retirement); }

Bytes machine_key_owner_key(std::span<const std::uint8_t> machine_public_key) {
  auto key = i::key_prefix(Entry::machine_key_owner);
  i::append(key, machine_public_key);
  return key;
}

std::optional<Bytes> machine_key_value(const MachineKey& entry) {
  if (entry.registered_at_height == 0) return std::nullopt;
  if (entry.registrations_in_window > kMachineRegistrationsPerWindow) {
    return std::nullopt;
  }
  Bytes value;
  value.reserve(kMachineKeyValueBytes);
  i::append(value, entry.machine_public_key);
  i::append(value, entry.build_digest);
  i::append_u64(value, entry.registered_at_height);
  i::append_u64(value, entry.last_met_window);
  i::append_u64(value, entry.registration_window);
  i::append_u32(value, entry.registrations_in_window);
  return value;
}

std::optional<MachineKey> decode_machine_key_value(std::span<const std::uint8_t> raw) {
  if (raw.size() != kMachineKeyValueBytes) return std::nullopt;
  MachineKey entry;
  if (!i::copy32(raw.subspan(0, 32), entry.machine_public_key)) return std::nullopt;
  if (!i::copy32(raw.subspan(32, 32), entry.build_digest)) return std::nullopt;
  const auto registered = i::read_u64(raw, 64);
  const auto met = i::read_u64(raw, 72);
  const auto window = i::read_u64(raw, 80);
  const auto count = i::read_u32(raw, 88);
  if (!registered || !met || !window || !count) return std::nullopt;
  entry.registered_at_height = *registered;
  entry.last_met_window = *met;
  entry.registration_window = *window;
  entry.registrations_in_window = *count;
  // Checked against the encoder's own rule rather than a second copy of it: a
  // value the encoder would refuse to write is not one a decoder may open.
  if (!machine_key_value(entry)) return std::nullopt;
  return entry;
}

std::optional<Bytes> launch_retirement_value(std::uint64_t retired_at_height) {
  if (retired_at_height == 0) return std::nullopt;
  Bytes value;
  i::append_u64(value, retired_at_height);
  return value;
}

std::optional<std::uint64_t> decode_launch_retirement_value(
    std::span<const std::uint8_t> raw) {
  if (raw.size() != kLaunchRetirementValueBytes) return std::nullopt;
  const auto height = i::read_u64(raw, 0);
  if (!height || *height == 0) return std::nullopt;
  return height;
}

Bytes machine_key_owner_value(std::uint32_t seat_id) {
  Bytes value;
  i::append_u32(value, seat_id);
  return value;
}

std::optional<std::uint32_t> decode_machine_key_owner_value(
    std::span<const std::uint8_t> raw) {
  if (raw.size() != kMachineKeyOwnerValueBytes) return std::nullopt;
  return i::read_u32(raw, 0);
}

// --- the attestation --------------------------------------------------------

// It names no identity, because the build authority is attesting a machine
// rather than acting for a person. It binds the seat, so an attestation for one
// seat cannot install a key on another, and the digest, so it says which build
// the key belongs to.
Bytes attestation_message(std::span<const std::uint8_t> chain_id,
                          std::uint32_t seat_id,
                          std::span<const std::uint8_t> machine_public_key,
                          std::span<const std::uint8_t> build_digest,
                          std::uint64_t valid_until_height) {
  Bytes message;
  i::append_domain(message, kAttestationLabel);
  i::append(message, chain_id);
  i::append_u32(message, seat_id);
  i::append(message, machine_public_key);
  i::append(message, build_digest);
  i::append_u64(message, valid_until_height);
  return message;
}

// --- the approval -----------------------------------------------------------

// **The body is decoded, its HUB field set to zero octets, and re-encoded**,
// which is the specification's definition stated as code: "the transaction's
// unsigned encoding, with its 64-octet `hub_signature` field set to zero
// octets". Zeroing a fixed offset would be shorter and would hold today, since
// every approval kind's field is its body's last 64 octets, but it would be a
// second statement of nine layouts with nothing keeping it equal to the first.
std::optional<Bytes> approved_bytes(const Envelope& envelope) {
  if (!is_approval_kind(envelope.kind)) return std::nullopt;
  auto body = decode_body(envelope.kind, envelope.body);
  if (!body) return std::nullopt;
  body->hub_signature = kNoSignature;
  auto blank = envelope;
  blank.body = encode_body(envelope.kind, *body);
  if (blank.body.size() != envelope.body.size()) return std::nullopt;
  return encode_unsigned(blank);
}

std::optional<Bytes> approval_message(const Envelope& envelope) {
  const auto approved = approved_bytes(envelope);
  if (!approved) return std::nullopt;
  Bytes message;
  i::append_domain(message, kApprovalLabel);
  i::append(message, *approved);
  return message;
}

// --- the lifetime rule ------------------------------------------------------

bool carries_hub_proof(const Envelope& envelope) {
  if (is_always_proven_kind(envelope.kind)) return true;
  if (!is_approval_kind(envelope.kind)) return false;
  const auto body = decode_body(envelope.kind, envelope.body);
  if (!body) return true;
  return !i::all_zero(body->hub_signature);
}

// `valid_until_height > height + kApprovalLifetimeBlocks`, written so the sum
// is never formed: a height within one slot of `u64` maximum would otherwise
// wrap and admit every validity.
bool approval_lifetime_exceeded(const Envelope& envelope, std::uint64_t height) {
  if (!carries_hub_proof(envelope)) return false;
  return envelope.valid_until_height > height &&
         envelope.valid_until_height - height > kApprovalLifetimeBlocks;
}

}  // namespace protocol::v10
