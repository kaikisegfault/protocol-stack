// `TestVerifierV9`, the deterministic stand-in for the HUB verifier (ADR 0099).
//
// Every message it signs is built here from the transaction's own fields with
// the kernel's builders, so a message this file signs and one the chain checks
// cannot differ by construction. The model's builders are the independent
// check, in `hub-test-verifier-v9-cross`. What this file adds is a derivation
// the production verifier will replace: a secret stands in for a face.

#include "protocol/hub/verifier_v9.hpp"

#include "protocol/v1/crypto.hpp"

#include <sodium.h>

#include <span>
#include <stdexcept>

namespace protocol::hub {
namespace {

namespace v1 = protocol::v1;

constexpr std::string_view kIdentityLabel =
    "protocol-stack:hub-test-verifier:identity";
constexpr std::string_view kHubKeyLabel =
    "protocol-stack:hub-test-verifier:hub-key";

using SecretKey = std::array<std::uint8_t, crypto_sign_SECRETKEYBYTES>;

Octets32 seed_keypair(const Octets32& seed, SecretKey& secret) {
  if (sodium_init() < 0) {
    throw std::runtime_error("libsodium initialization failure");
  }
  Octets32 public_key{};
  if (crypto_sign_seed_keypair(public_key.data(), secret.data(), seed.data()) !=
      0) {
    throw std::runtime_error("Ed25519 key derivation failure");
  }
  return public_key;
}

Bytes sign_with(const SecretKey& secret, std::span<const std::uint8_t> message) {
  Bytes signature(crypto_sign_BYTES);
  unsigned long long size = 0;
  if (crypto_sign_detached(signature.data(), &size, message.data(),
                           message.size(), secret.data()) != 0 ||
      size != crypto_sign_BYTES) {
    throw std::runtime_error("Ed25519 signing failure");
  }
  return signature;
}

// The person a capture derives. Their HUB key exists for one decision and is
// wiped when it ends.
class Person {
 public:
  explicit Person(const Capture& capture) {
    identity_.hub_identity_hash = v1::hash(kIdentityLabel, capture.secret);
    auto seed = v1::hash(kHubKeyLabel, capture.secret);
    identity_.hub_public_key = seed_keypair(seed, secret_);
    sodium_memzero(seed.data(), seed.size());
  }
  ~Person() { sodium_memzero(secret_.data(), secret_.size()); }
  Person(const Person&) = delete;
  Person& operator=(const Person&) = delete;

  const Identity& identity() const { return identity_; }
  Bytes sign(std::span<const std::uint8_t> message) const {
    return sign_with(secret_, message);
  }
  Bytes sign_transaction(const v9::Envelope& envelope) const {
    const auto unsigned_transaction = v9::encode_unsigned(envelope);
    return v9::encode_signed(
        envelope, sign(v9::signing_message(unsigned_transaction)));
  }

 private:
  Identity identity_;
  SecretKey secret_{};
};

Decision refused(const Identity& identity, Refusal refusal) {
  Decision decision;
  decision.refusal = refusal;
  decision.identity = identity;
  return decision;
}

// The twelve kinds that take a HUB proof once a person is registered.
bool takes_hub_proof(std::uint8_t kind) {
  switch (static_cast<v9::Kind>(kind)) {
    case v9::Kind::purchase_seat:
    case v9::Kind::activate_seat:
    case v9::Kind::mint_node:
    case v9::Kind::mint_referral:
    case v9::Kind::escrow_create:
    case v9::Kind::escrow_delete:
    case v9::Kind::signer_add:
    case v9::Kind::signer_revoke:
    case v9::Kind::set_security_posture:
    case v9::Kind::mint_verified_user:
    case v9::Kind::native_transfer_verified:
    case v9::Kind::mint_monthly_pool:
      return true;
    default:
      return false;
  }
}

// The action message a body-carried HUB signature covers, built from the
// transaction exactly as the chain builds it to check one.
Bytes action_message(const Identity& identity, const v9::Envelope& transaction,
                     const v9::Body& body, const Octets32& acting_escrow_id) {
  const auto& chain = transaction.chain_id;
  const auto& person = identity.hub_identity_hash;
  const auto until = transaction.valid_until_height;
  switch (static_cast<v9::Kind>(transaction.kind)) {
    case v9::Kind::purchase_seat:
      return v9::purchase_message(chain, person, body.seat_id, until);
    case v9::Kind::activate_seat:
      return v9::activation_message(chain, person, body.seat_id, until);
    case v9::Kind::set_security_posture: {
      v9::Posture proposed;
      proposed.requires_confirmation = body.requires_confirmation;
      proposed.min_amount_atomic = body.min_amount_atomic;
      proposed.exempt_slot_mask = body.exempt_slot_mask;
      return v9::posture_relax_message(chain, person, acting_escrow_id, proposed,
                                       until);
    }
    case v9::Kind::native_transfer_verified:
      return v9::transfer_confirm_message(chain, person, acting_escrow_id,
                                          body.recipient_escrow_id,
                                          body.amount_atomic, until);
    default:
      // Kinds 4, 5, 18, and 22. The bodies of 5 and 18 carry no seat, so the
      // decoded `seat_id` is zero, which is the term their message binds.
      return v9::mint_message(chain, person, transaction.kind, body.seat_id,
                              body.destination_escrow_id, until);
  }
}

}  // namespace

std::string_view refusal_name(Refusal refusal) {
  switch (refusal) {
    case Refusal::not_the_person:
      return "not_the_person";
    case Refusal::not_a_hub_decision:
      return "not_a_hub_decision";
    case Refusal::wrong_scheme:
      return "wrong_scheme";
    case Refusal::malformed:
      return "malformed";
  }
  return "unknown";
}

// The keypair is derived in the body, not the initializer list: `secret_key_`
// is declared after `public_key_`, so its own initializer would run after the
// derivation and zero the key it had just written.
TestVerifierV9::TestVerifierV9(const Octets32& verifier_seed) {
  public_key_ = seed_keypair(verifier_seed, secret_key_);
}

TestVerifierV9::~TestVerifierV9() {
  sodium_memzero(secret_key_.data(), secret_key_.size());
}

Identity TestVerifierV9::identify(const Capture& capture) {
  return Person(capture).identity();
}

Octets32 TestVerifierV9::registration_key() const { return public_key_; }

Decision TestVerifierV9::register_person(
    const RegistrationRequest& request) const {
  const Person person(request.capture);
  const auto& identity = person.identity();
  v9::Body body;
  body.hub_identity_hash = identity.hub_identity_hash;
  body.first_signer_public_key = request.first_signer_public_key;
  body.verifier_signature = sign_with(
      secret_key_,
      v9::registration_message(request.chain_id, identity.hub_identity_hash,
                               identity.hub_public_key,
                               request.first_signer_public_key,
                               request.valid_until_height));

  // A registration is fee-exempt and has no escrow yet, so its nonce and fee
  // limit are zero, which admission requires.
  v9::Envelope envelope;
  envelope.kind = static_cast<std::uint8_t>(v9::Kind::hub_register);
  envelope.chain_id = request.chain_id;
  envelope.scheme = v9::kSchemeIdentity;
  envelope.authority_public_key = identity.hub_public_key;
  envelope.body = v9::encode_body(envelope.kind, body);
  envelope.valid_until_height = request.valid_until_height;

  Decision decision;
  decision.identity = identity;
  decision.signed_transaction = person.sign_transaction(envelope);
  return decision;
}

Decision TestVerifierV9::approve(const ApprovalRequest& request) const {
  const Person person(request.capture);
  const auto& identity = person.identity();
  const auto& transaction = request.transaction;
  if (!takes_hub_proof(transaction.kind)) {
    return refused(identity, Refusal::not_a_hub_decision);
  }
  const auto scheme = v9::kind_scheme(transaction.kind);
  if (!scheme || transaction.scheme != *scheme) {
    return refused(identity, Refusal::wrong_scheme);
  }
  const auto body = v9::decode_body(transaction.kind, transaction.body);
  if (!body) return refused(identity, Refusal::malformed);

  Decision decision;
  decision.identity = identity;
  if (*scheme == v9::kSchemeIdentity) {
    // Identity administration: the HUB key is the envelope's authority, so the
    // transaction must name this person both ways before it signs.
    if (body->hub_identity_hash != identity.hub_identity_hash ||
        transaction.authority_public_key != identity.hub_public_key) {
      return refused(identity, Refusal::not_the_person);
    }
    decision.signed_transaction = person.sign_transaction(transaction);
    return decision;
  }
  decision.hub_signature = person.sign(
      action_message(identity, transaction, *body, request.acting_escrow_id));
  return decision;
}

}  // namespace protocol::hub
