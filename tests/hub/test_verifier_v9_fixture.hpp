#pragma once

// The fixture behind `hub-test-verifier-v9` (ADR 0099): one chain, a wallet's
// signer keys, and the two ways a decision reaches a transaction.
//
// **The chain is the judge, not the checks.** `Chain::run` puts every
// transaction through admission and execution under the production Ed25519
// verifier, so a check that passes means a node would accept the decision.

#include "protocol/hub/verifier_v9.hpp"
#include "protocol/v9/ledger.hpp"

#include "../../tools/protocol-vectors/vector_common.hpp"

#include <sodium.h>

#include <algorithm>
#include <array>

namespace hub = protocol::hub;
namespace pv = protocol_vectors;
namespace v9 = protocol::v9;

namespace hub_test_verifier_v9 {

using Bytes = v9::Bytes;
using Octets32 = v9::Octets32;

inline constexpr std::uint64_t kValidUntil = 1'000;
inline constexpr std::uint64_t kFee = 1'000;
inline constexpr std::uint64_t kAmount = 1'000'000;
inline constexpr std::string_view kManifestDigestHex =
    "af153c99adf7c49e5a92563946cf0e60dfd7a58785462530988f661aa68faaa7";

inline Octets32 filled(std::uint8_t octet) {
  Octets32 value{};
  value.fill(octet);
  return value;
}

inline hub::Capture face(std::uint8_t octet) {
  hub::Capture capture;
  capture.secret = filled(octet);
  return capture;
}

// A signer key, which a wallet holds and the verifier never sees.
class Wallet {
 public:
  explicit Wallet(std::uint8_t octet) {
    const auto seed = filled(octet);
    pv::require(crypto_sign_seed_keypair(public_key_.data(), secret_.data(),
                                         seed.data()) == 0,
                "a signer key derives");
  }
  const Octets32& public_key() const { return public_key_; }
  Bytes sign(const v9::Envelope& envelope) const {
    const auto message = v9::signing_message(v9::encode_unsigned(envelope));
    Bytes signature(crypto_sign_BYTES);
    pv::require(crypto_sign_detached(signature.data(), nullptr, message.data(),
                                     message.size(), secret_.data()) == 0,
                "a signer signs");
    return v9::encode_signed(envelope, signature);
  }

 private:
  Octets32 public_key_{};
  std::array<std::uint8_t, crypto_sign_SECRETKEYBYTES> secret_{};
};

// One chain, driven a transaction at a time through admission and execution.
class Chain {
 public:
  explicit Chain(const Octets32& verifier_key) {
    v9::Genesis genesis;
    genesis.network_id = 9;
    genesis.genesis_timestamp = 1'768'435'200'000;
    genesis.supply_limit = 5'699'395'010'000'000'000;
    genesis.fixed_transfer_fee = kFee;
    const auto digest = pv::hex_decode(kManifestDigestHex);
    std::copy(digest.begin(), digest.end(), genesis.manifest_digest.begin());
    genesis.verifier_key = verifier_key;
    genesis.dispute_authority_key = filled(0xD8);
    auto ledger = v9::open_ledger(genesis);
    pv::require(ledger.has_value(), "the genesis opens a ledger");
    ledger_ = std::move(*ledger);
    ledger_.height = 1;
  }

  const Octets32& chain_id() const { return ledger_.chain_id; }

  v9::Result run(const Bytes& raw) {
    const auto admitted = v9::admit(raw, ledger_.chain_id, v9::ed25519_verifier());
    pv::require(admitted.admitted(), "admission accepts the envelope signature");
    const auto outcome =
        v9::execute(ledger_, admitted.transaction.envelope, v9::ed25519_verifier());
    pv::require(outcome.has_value(), "no invariant fails");
    return outcome->result;
  }

  std::uint64_t next_nonce(const Octets32& escrow) const {
    const auto account = ledger_.registry.accounts.find(escrow);
    return (account == ledger_.registry.accounts.end() ? 0 : account->second.nonce) +
           1;
  }
  std::uint64_t balance(const Octets32& escrow) const {
    return ledger_.registry.accounts.at(escrow).balance;
  }
  bool confirms(const Octets32& escrow) const {
    return ledger_.registry.escrows.at(escrow).posture.requires_confirmation;
  }
  bool has_escrow(const Octets32& escrow) const {
    return ledger_.registry.escrows.contains(escrow);
  }
  bool has_signer(const Octets32& key) const {
    return ledger_.registry.signers.contains(v9::signer_id(key));
  }

 private:
  v9::Ledger ledger_;
};

inline v9::Envelope envelope(const Octets32& chain_id, v9::Kind kind,
                      const Octets32& authority, std::uint64_t nonce) {
  v9::Envelope result;
  result.kind = static_cast<std::uint8_t>(kind);
  result.chain_id = chain_id;
  result.scheme = *v9::kind_scheme(result.kind);
  result.authority_public_key = authority;
  result.nonce = nonce;
  result.fee_limit = kFee;
  result.valid_until_height = kValidUntil;
  return result;
}

inline hub::Decision ask(const hub::VerifierV9& verifier, const hub::Capture& capture,
                  v9::Envelope transaction, const v9::Body& body,
                  const Octets32& acting_escrow = {}) {
  transaction.body = v9::encode_body(transaction.kind, body);
  return verifier.approve({capture, transaction, acting_escrow});
}

// A body-carried kind: the verifier signs the action, then the signer signs the
// envelope over the completed body.
inline v9::Body approved_body(const hub::VerifierV9& verifier, const hub::Capture& capture,
                       const v9::Envelope& transaction, v9::Body body,
                       const Octets32& acting_escrow) {
  body.hub_signature.assign(v9::kSignatureBytes, 0);
  const auto decision = ask(verifier, capture, transaction, body, acting_escrow);
  pv::require(decision.approved() && decision.hub_signature.size() == 64 &&
                  decision.signed_transaction.empty(),
              "a body-carried kind is approved with a HUB signature alone");
  body.hub_signature = decision.hub_signature;
  return body;
}

inline Bytes with_body(const Wallet& signer, v9::Envelope transaction, const v9::Body& body) {
  transaction.body = v9::encode_body(transaction.kind, body);
  return signer.sign(transaction);
}

// Identity administration: the verifier returns the whole signed transaction.
inline Bytes administered(const hub::VerifierV9& verifier, const hub::Capture& capture,
                   const v9::Envelope& transaction, const v9::Body& body) {
  const auto decision = ask(verifier, capture, transaction, body);
  pv::require(decision.approved() && decision.hub_signature.empty() &&
                  !decision.signed_transaction.empty(),
              "identity administration is approved as a signed transaction");
  return decision.signed_transaction;
}

// Two people registered on one chain, the verifier their only HUB key holder.
struct People {
  hub::TestVerifierV9 verifier{filled(0x77)};
  Chain chain{verifier.registration_key()};
  hub::Capture alice = face(0xA1);
  hub::Capture bob = face(0xB1);
  Wallet alice_signer{0x11};
  Wallet bob_signer{0x22};
  hub::Identity alice_identity = hub::TestVerifierV9::identify(alice);
  hub::Identity bob_identity = hub::TestVerifierV9::identify(bob);
  Octets32 alice_escrow = v9::escrow_id(alice_identity.hub_identity_hash, 0);
  Octets32 bob_escrow = v9::escrow_id(bob_identity.hub_identity_hash, 0);

  People() {
    for (const auto& [capture, signer] :
         {std::pair{alice, &alice_signer}, std::pair{bob, &bob_signer}}) {
      const auto decision = verifier.register_person(
          {chain.chain_id(), capture, signer->public_key(), kValidUntil});
      pv::require(decision.approved(), "a registration is never refused here");
      pv::require(decision.identity.hub_identity_hash ==
                      hub::TestVerifierV9::identify(capture).hub_identity_hash,
                  "a registration names the identity its capture derives");
      pv::require(chain.run(decision.signed_transaction) == v9::Result::success,
                  "the chain accepts the verifier's registration");
    }
  }

  Bytes transfer(const v9::Body& body) {
    return with_body(alice_signer,
                     envelope(chain.chain_id(), v9::Kind::native_transfer_verified,
                              alice_signer.public_key(),
                              chain.next_nonce(alice_escrow)),
                     body);
  }
  Bytes posture(const v9::Body& body) {
    return with_body(alice_signer,
                     envelope(chain.chain_id(), v9::Kind::set_security_posture,
                              alice_signer.public_key(),
                              chain.next_nonce(alice_escrow)),
                     body);
  }
};

}  // namespace hub_test_verifier_v9
