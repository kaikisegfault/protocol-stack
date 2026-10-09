// `hub-test-verifier-v9`: the test HUB verifier's decisions, judged by the
// version-nine kernel (ADR 0099).
//
// Every decision except the four mints is executed. A mint checks
// `NOTHING_TO_MINT` before its confirmation, which a fresh chain cannot get
// past, so each mint's proof is checked against the kernel's own message builder
// with the strict verification the chain applies.
//
// **One check records what version nine accepts rather than what it should.** A
// HUB approval replayed under a new nonce is accepted, because no HUB message
// binds a nonce and nothing bounds `valid_until_height` from above. Requirement
// 5's contract must refuse it, and that check is the one that will flip.

#include "test_verifier_v9_fixture.hpp"

#include <exception>
#include <iostream>

namespace {

using namespace hub_test_verifier_v9;

void check_decisions_are_deterministic() {
  const hub::TestVerifierV9 verifier(filled(0x77));
  const auto alice = hub::TestVerifierV9::identify(face(0xA1));
  pv::require(alice.hub_identity_hash ==
                  hub::TestVerifierV9::identify(face(0xA1)).hub_identity_hash,
              "one capture derives one identity");
  pv::require(alice.hub_identity_hash !=
                      hub::TestVerifierV9::identify(face(0xB1)).hub_identity_hash &&
                  alice.hub_public_key != alice.hub_identity_hash,
              "two captures derive two identities, and a key is not its hash");
  const hub::RegistrationRequest request{filled(0x0C), face(0xA1), filled(0x11),
                                         kValidUntil};
  pv::require(verifier.register_person(request).signed_transaction ==
                  verifier.register_person(request).signed_transaction,
              "a registration is the same bytes every time");
  pv::require(hub::TestVerifierV9(filled(0x77)).registration_key() ==
                      verifier.registration_key() &&
                  hub::TestVerifierV9(filled(0x78)).registration_key() !=
                      verifier.registration_key(),
              "the verifier key is its seed's");
}

// Every kind that takes a HUB proof, accepted by the chain in one lifecycle.
void check_the_chain_accepts_every_decision() {
  People people;
  auto& chain = people.chain;
  const auto& verifier = people.verifier;
  const auto& alice = people.alice;
  const auto& escrow = people.alice_escrow;
  const auto signer = people.alice_signer.public_key();
  const auto hub_key = people.alice_identity.hub_public_key;
  const auto identity = people.alice_identity.hub_identity_hash;

  v9::Body seat;
  seat.seat_id = 0;
  for (const auto kind : {v9::Kind::purchase_seat, v9::Kind::activate_seat}) {
    const auto transaction =
        envelope(chain.chain_id(), kind, signer, chain.next_nonce(escrow));
    const auto body = approved_body(verifier, alice, transaction, seat, escrow);
    pv::require(chain.run(with_body(people.alice_signer, transaction, body)) ==
                    v9::Result::success,
                "the chain accepts a seat purchase and activation");
  }

  v9::Body transfer;
  transfer.recipient_escrow_id = people.bob_escrow;
  transfer.amount_atomic = kAmount;
  const auto bob_before = chain.balance(people.bob_escrow);
  pv::require(
      chain.run(people.transfer(approved_body(
          verifier, alice,
          envelope(chain.chain_id(), v9::Kind::native_transfer_verified, signer,
                   chain.next_nonce(escrow)),
          transfer, escrow))) == v9::Result::success &&
          chain.balance(people.bob_escrow) == bob_before + kAmount,
      "the chain accepts a confirmed transfer");

  v9::Body relax;
  relax.requires_confirmation = false;
  pv::require(
      chain.run(people.posture(approved_body(
          verifier, alice,
          envelope(chain.chain_id(), v9::Kind::set_security_posture, signer,
                   chain.next_nonce(escrow)),
          relax, escrow))) == v9::Result::success &&
          !chain.confirms(escrow),
      "the chain accepts a posture relax");

  // Identity administration, which a recovering person does with no signer.
  const Wallet second(0x13);
  const auto holding = v9::escrow_id(identity, 1);
  v9::Body create;
  create.hub_identity_hash = identity;
  create.fee_escrow_id = escrow;
  v9::Body add;
  add.hub_identity_hash = identity;
  add.escrow_id = escrow;
  add.signer_public_key = second.public_key();
  v9::Body revoke = add;
  revoke.signer_id = v9::signer_id(second.public_key());
  v9::Body remove;
  remove.hub_identity_hash = identity;
  remove.target_escrow_id = holding;
  remove.fee_escrow_id = escrow;
  const std::pair<v9::Kind, v9::Body> steps[] = {
      {v9::Kind::escrow_create, create},
      {v9::Kind::signer_add, add},
      {v9::Kind::signer_revoke, revoke},
      {v9::Kind::escrow_delete, remove}};
  for (const auto& [kind, body] : steps) {
    pv::require(
        chain.run(administered(verifier, alice,
                               envelope(chain.chain_id(), kind, hub_key,
                                        chain.next_nonce(escrow)),
                               body)) == v9::Result::success,
        "the chain accepts identity administration");
    if (kind == v9::Kind::escrow_create) {
      pv::require(chain.has_escrow(holding), "the holding escrow exists");
    }
    if (kind == v9::Kind::signer_add) {
      pv::require(chain.has_signer(second.public_key()), "the signer was added");
    }
  }
  pv::require(!chain.has_signer(second.public_key()) && !chain.has_escrow(holding),
              "the signer was revoked and the escrow deleted");

  // The four mints: the proof the chain's confirmation step would check.
  const std::pair<v9::Kind, std::uint32_t> mints[] = {
      {v9::Kind::mint_node, 0},
      {v9::Kind::mint_referral, 0},
      {v9::Kind::mint_verified_user, 0},
      {v9::Kind::mint_monthly_pool, 0}};
  for (const auto& [kind, seat_id] : mints) {
    v9::Body mint;
    mint.seat_id = seat_id;
    mint.destination_escrow_id = escrow;
    const auto transaction =
        envelope(chain.chain_id(), kind, signer, chain.next_nonce(escrow));
    const auto body = approved_body(verifier, alice, transaction, mint, escrow);
    for (const auto& [other, ignored] : mints) {
      static_cast<void>(ignored);
      const auto message =
          v9::mint_message(chain.chain_id(), identity, static_cast<std::uint8_t>(other),
                           seat_id, escrow, kValidUntil);
      pv::require(v9::ed25519_verifier()(hub_key, message, body.hub_signature) ==
                      (other == kind),
                  "a mint's proof verifies for its own kind and no other");
    }
  }
}

void check_refusals() {
  const hub::TestVerifierV9 verifier(filled(0x77));
  const auto chain_id = filled(0x0C);
  const auto alice = hub::TestVerifierV9::identify(face(0xA1));
  const auto bob = hub::TestVerifierV9::identify(face(0xB1));
  v9::Body add;
  add.hub_identity_hash = alice.hub_identity_hash;
  add.escrow_id = v9::escrow_id(alice.hub_identity_hash, 0);
  add.signer_public_key = filled(0x13);
  const auto alices = envelope(chain_id, v9::Kind::signer_add, alice.hub_public_key, 1);

  const auto refusal = [&](const hub::Capture& capture, const v9::Envelope& transaction,
                           const v9::Body& body) {
    const auto decision = ask(verifier, capture, transaction, body);
    pv::require(decision.identity.hub_identity_hash ==
                    hub::TestVerifierV9::identify(capture).hub_identity_hash,
                "a decision names the capture's identity, refused or not");
    pv::require(decision.approved() || (decision.hub_signature.empty() &&
                                         decision.signed_transaction.empty()),
                "a refusal carries no proof");
    return decision.refusal;
  };
  pv::require(refusal(face(0xA1), alices, add) == std::nullopt,
              "the control: Alice's own administration is approved");
  pv::require(refusal(face(0xB1), alices, add) == hub::Refusal::not_the_person,
              "Bob's capture cannot approve Alice's administration");
  pv::require(refusal(face(0xA1),
                      envelope(chain_id, v9::Kind::signer_add, bob.hub_public_key, 1),
                      add) == hub::Refusal::not_the_person,
              "nor can Alice's capture approve one authorized by another key");

  for (const auto kind : {v9::Kind::native_transfer, v9::Kind::direct_issue,
                          v9::Kind::hub_register, v9::Kind::challenge_response,
                          v9::Kind::file_dispute}) {
    pv::require(refusal(face(0xA1), envelope(chain_id, kind, alice.hub_public_key, 1),
                        v9::Body{}) == hub::Refusal::not_a_hub_decision,
                "a kind that takes no HUB proof is refused");
  }
  auto wrong = alices;
  wrong.scheme = v9::kSchemeSigner;
  pv::require(refusal(face(0xA1), wrong, add) == hub::Refusal::wrong_scheme,
              "a scheme its kind does not permit is refused");
  auto short_body = envelope(chain_id, v9::Kind::purchase_seat, filled(0x11), 1);
  pv::require(verifier.approve({face(0xA1), short_body, {}}).refusal ==
                  hub::Refusal::malformed,
              "a body that does not decode is refused");
}

// The verifier cannot know whose escrow a signer acts for. The chain does.
void check_the_chain_judges_what_the_verifier_cannot() {
  People people;
  auto& chain = people.chain;
  const auto transaction =
      envelope(chain.chain_id(), v9::Kind::native_transfer_verified,
               people.alice_signer.public_key(), chain.next_nonce(people.alice_escrow));
  v9::Body transfer;
  transfer.recipient_escrow_id = people.bob_escrow;
  transfer.amount_atomic = kAmount;
  const auto bobs = approved_body(people.verifier, people.bob, transaction, transfer,
                                  people.alice_escrow);
  pv::require(chain.run(people.transfer(bobs)) == v9::Result::unauthorized,
              "Bob's approval of a transfer from Alice's escrow is refused");
  auto larger = approved_body(people.verifier, people.alice, transaction, transfer,
                              people.alice_escrow);
  larger.amount_atomic = kAmount + 1;
  pv::require(chain.run(people.transfer(larger)) == v9::Result::unauthorized,
              "an approval for one amount does not move another");
}

// What requirement 5 must close: one approval, used twice.
void check_version_nine_accepts_a_replayed_approval() {
  People people;
  auto& chain = people.chain;
  const auto& escrow = people.alice_escrow;
  const auto signer = people.alice_signer.public_key();

  v9::Body relax;
  relax.requires_confirmation = false;
  const auto relaxed = approved_body(
      people.verifier, people.alice,
      envelope(chain.chain_id(), v9::Kind::set_security_posture, signer,
               chain.next_nonce(escrow)),
      relax, escrow);
  v9::Body tighten;
  tighten.requires_confirmation = true;
  tighten.hub_signature.assign(v9::kSignatureBytes, 0);
  pv::require(chain.run(people.posture(relaxed)) == v9::Result::success &&
                  chain.run(people.posture(tighten)) == v9::Result::success &&
                  chain.confirms(escrow),
              "Alice relaxes with an approval, then tightens with her signer");
  pv::require(chain.run(people.posture(relaxed)) == v9::Result::success &&
                  !chain.confirms(escrow),
              "version nine accepts the published relax again, with no new "
              "approval: a signer key alone undoes the tightening");

  v9::Body transfer;
  transfer.recipient_escrow_id = people.bob_escrow;
  transfer.amount_atomic = kAmount;
  const auto confirmed = approved_body(
      people.verifier, people.alice,
      envelope(chain.chain_id(), v9::Kind::native_transfer_verified, signer,
               chain.next_nonce(escrow)),
      transfer, escrow);
  const auto bob_before = chain.balance(people.bob_escrow);
  pv::require(chain.run(people.transfer(confirmed)) == v9::Result::success &&
                  chain.run(people.transfer(confirmed)) == v9::Result::success &&
                  chain.balance(people.bob_escrow) == bob_before + 2 * kAmount,
              "version nine accepts one transfer confirmation twice");
}

}  // namespace

int main() {
  try {
    pv::require(sodium_init() >= 0, "libsodium initialization");
    check_decisions_are_deterministic();
    check_the_chain_accepts_every_decision();
    check_refusals();
    check_the_chain_judges_what_the_verifier_cannot();
    check_version_nine_accepts_a_replayed_approval();
    std::cout << "hub-test-verifier-v9: five checks passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "hub-test-verifier-v9: " << error.what() << '\n';
    return 1;
  }
}
