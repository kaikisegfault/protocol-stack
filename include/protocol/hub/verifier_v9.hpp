#pragma once

// The HUB verifier interface, and its deterministic test implementation
// (ADR 0099).
//
// A HUB verifier is what stands between a person and every HUB proof version
// nine checks. **It holds the person's HUB key and nobody else does**: a
// registration comes back as a whole signed transaction, and so does identity
// administration, because the HUB key signs those envelopes. For a kind whose
// body carries a HUB signature, the verifier returns those 64 octets, and the
// signer's envelope then covers them.
//
// **It builds every message it signs.** It is handed a transaction, decodes it,
// and derives the action message from its fields with the kernel's own
// builders. It never signs bytes a caller chose, because a verifier that did
// would give a compromised wallet a HUB signature for any action at all.
//
// The production verifier runs sandboxed on the person's Founder Machine and
// derives the HUB key from a capture (ADR 0048). It cannot be built until the
// stabilization scheme passes review. `TestVerifierV9` stands in for it, and is
// linked into no node.

#include "protocol/v9/economy.hpp"

#include <array>
#include <cstdint>
#include <optional>
#include <string_view>

namespace protocol::hub {

using Bytes = v9::Bytes;
using Octets32 = v9::Octets32;

// What a person presents. A production verifier derives a stable secret from a
// face; the test verifier is handed that secret directly.
struct Capture {
  Octets32 secret{};
};

struct Identity {
  Octets32 hub_identity_hash{};
  Octets32 hub_public_key{};
};

enum class Refusal : std::uint8_t {
  // A transaction names an identity, or an authority key, that the capture
  // does not derive: the stand-in for "this is not the enrolled person".
  not_the_person = 1,
  // The kind takes no HUB proof: 1, 6, 20, and 21, and 10 through `approve`.
  not_a_hub_decision = 2,
  // The transaction names a scheme its kind does not permit.
  wrong_scheme = 3,
  // The body does not decode for its kind.
  malformed = 4,
};

std::string_view refusal_name(Refusal refusal);

struct Decision {
  std::optional<Refusal> refusal;
  // The identity the capture belongs to, reported even on a refusal.
  Identity identity;
  // Kinds 2, 3, 4, 5, 17, 18, 19, and 22: the body's HUB signature.
  Bytes hub_signature;
  // Kinds 10 and 13 to 16: the whole transaction, signed by the HUB key.
  Bytes signed_transaction;

  bool approved() const { return !refusal.has_value(); }
};

struct RegistrationRequest {
  Octets32 chain_id{};
  Capture capture;
  Octets32 first_signer_public_key{};
  std::uint64_t valid_until_height = 0;
};

struct ApprovalRequest {
  Capture capture;
  // The transaction the person approves, with every signature octet zero.
  v9::Envelope transaction;
  // The escrow the signer acts for. Kinds 17 and 19 bind it and their bodies do
  // not carry it, so it is read for those two and ignored otherwise. If it is
  // not the person's, the chain refuses the proof as `UNAUTHORIZED`.
  Octets32 acting_escrow_id{};
};

class VerifierV9 {
 public:
  virtual ~VerifierV9() = default;

  // The key a version-nine genesis carries as `verifier_key`. Requirement 3's
  // registry replaces it with a machine's attestation key.
  virtual Octets32 registration_key() const = 0;
  virtual Decision register_person(const RegistrationRequest& request) const = 0;
  virtual Decision approve(const ApprovalRequest& request) const = 0;
};

// Deterministic: no clock, no randomness, no state. One secret derives both the
// identity and the HUB key, as one face will:
//
//   hub_identity_hash = H(D("protocol-stack:hub-test-verifier:identity") || secret)
//   hub_key_seed      = H(D("protocol-stack:hub-test-verifier:hub-key")  || secret)
class TestVerifierV9 final : public VerifierV9 {
 public:
  explicit TestVerifierV9(const Octets32& verifier_seed);
  ~TestVerifierV9() override;
  TestVerifierV9(const TestVerifierV9&) = delete;
  TestVerifierV9& operator=(const TestVerifierV9&) = delete;

  // The identity a capture derives, with no signature made.
  static Identity identify(const Capture& capture);

  Octets32 registration_key() const override;
  Decision register_person(const RegistrationRequest& request) const override;
  Decision approve(const ApprovalRequest& request) const override;

 private:
  Octets32 public_key_{};
  std::array<std::uint8_t, 64> secret_key_{};
};

}  // namespace protocol::hub
