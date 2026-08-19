// The five recorded scenarios this kernel can execute, rebuilt transaction for
// transaction.
//
// Each is chosen for what would go undetected otherwise:
//
// 1. **registration** — a whole participant created in one atomic execution, the
//    entry airdrop that makes the new escrow able to transact, and a forfeiting
//    verified-user collection thirty windows later.
// 2. **millionth** — the identity past the enrollment population, which
//    registers successfully, receives no airdrop, and can then sign nothing that
//    reaches its own kind's conditions until somebody funds it.
// 3. **recovery** — a person with an identity, no signer, and an escrow that
//    holds value assigns a new signer under scheme 2 and pays from that escrow.
// 4. **compatibility** — the accepted version-one signed transfer, byte for
//    byte, admitted and then refused for its recipient; and the same transaction
//    with only the recipient replaced, accepted.
// 5. **posture** — both directions of a change, including a mixed one that
//    tightens the slot mask and raises the minimum and therefore needs the HUB
//    signature.
//
// The sixth, the boundary block, writes a cycle assignment and mints against it,
// and belongs to the settlement slice.

#include "economy_v6_execution_fixture.hpp"

namespace economy_v6_execution {
namespace {

Octets32 first_escrow(const Octets32& identity) {
  return v6::escrow_id(identity, 0);
}

// A well-formed transfer whose kind byte is 7, the lowest number version six
// retired. Admission refuses it on the width no retired kind has.
Bytes retired_kind_input(Signatures& signatures, const v6::Ledger& ledger) {
  auto raw = transfer_input(signatures, ledger, kAliceSignerKey, 1,
                            first_escrow(kBobIdentity), 1);
  raw[6] = 7;
  return raw;
}

// A well-formed, correctly signed transfer carrying another chain's identifier.
Bytes foreign_chain_input(Signatures& signatures, const v6::Ledger& ledger) {
  v6::Ledger foreign = ledger;
  foreign.chain_id = Octets32{};
  return transfer_input(signatures, foreign, kAliceSignerKey, 1,
                        first_escrow(kBobIdentity), 1);
}

}  // namespace

Scenario registration_scenario(Signatures& signatures) {
  Scenario scenario{"registration", open_trace_ledger(), {}, {}, {}, {}, 0};
  auto& ledger = scenario.ledger;
  const auto alice = first_escrow(kAliceIdentity);
  const auto bob = first_escrow(kBobIdentity);

  run(scenario, signatures,
      {{"alice_registers",
        register_input(signatures, ledger, kAliceIdentity, kAliceKey,
                       kAliceSignerKey)},
       // The identical bytes a second time: one registration has exactly one
       // encoding, so the replay carries the same transaction identifier.
       {"alice_registers_again",
        register_input(signatures, ledger, kAliceIdentity, kAliceKey,
                       kAliceSignerKey)}});
  run(scenario, signatures,
      {{"bob_registers",
        register_input(signatures, ledger, kBobIdentity, kBobKey, kBobSignerKey)},
       {"carol_reuses_alices_signer_key",
        register_input(signatures, ledger, kCarolIdentity, kCarolKey,
                       kAliceSignerKey)},
       // An admission failure reads no state, produces no receipt, and never
       // enters the transaction root, so these leave the block two wide.
       {"a_retired_kind_byte", retired_kind_input(signatures, ledger), false},
       {"a_foreign_chain_id", foreign_chain_input(signatures, ledger), false}});
  run(scenario, signatures,
      {{"alice_transfers_unconfirmed",
        transfer_input(signatures, ledger, kAliceSignerKey, 1, bob,
                       kTransferAmount)},
       {"alice_transfers_confirmed",
        confirmed_transfer_input(signatures, ledger, 1, bob, kTransferAmount,
                                 kAliceIdentity, kAliceKey, kAliceSignerKey,
                                 alice)},
       {"alice_transfers_to_an_unregistered_recipient",
        transfer_input(signatures, ledger, kAliceSignerKey, 2, kAcceptedRecipient,
                       kTransferAmount)},
       {"alice_collects_before_any_window_completes",
        verified_user_mint_input(signatures, ledger, kAliceIdentity, 2, alice,
                                 kAliceKey, kAliceSignerKey)}});

  advance_to(scenario, kCollectionHeight - 1);
  run(scenario, signatures,
      {{"alice_collects_thirty_windows",
        verified_user_mint_input(signatures, ledger, kAliceIdentity, 2, alice,
                                 kAliceKey, kAliceSignerKey)},
       {"alice_collects_again_immediately",
        verified_user_mint_input(signatures, ledger, kAliceIdentity, 3, alice,
                                 kAliceKey, kAliceSignerKey)}});
  return scenario;
}

// The counter is stamped one short of the population before any block runs,
// because reaching 999,999 needs 999,999 registrations. Everything after the
// stamp is executed: Alice's registration is the millionth and takes the last
// airdrop, and Dave's is the millionth and first and takes none.
Scenario millionth_scenario(Signatures& signatures) {
  Scenario scenario{"millionth", open_trace_ledger(), {}, {}, {}, {}, 0};
  auto& ledger = scenario.ledger;
  ledger.registry.enrolled_count = v6::kVerifiedUserPopulation - 1;
  const auto alice = first_escrow(kAliceIdentity);
  const auto dave = first_escrow(kDaveIdentity);

  run(scenario, signatures,
      {{"alice_registers_inside_the_population",
        register_input(signatures, ledger, kAliceIdentity, kAliceKey,
                       kAliceSignerKey)}});
  run(scenario, signatures,
      {{"dave_registers_past_the_population",
        register_input(signatures, ledger, kDaveIdentity, kDaveKey,
                       kDaveSignerKey)}});
  run(scenario, signatures,
      {{"dave_collects_holding_nothing",
        verified_user_mint_input(signatures, ledger, kDaveIdentity, 1, dave,
                                 kDaveKey, kDaveSignerKey)},
       {"dave_transfers_holding_nothing",
        transfer_input(signatures, ledger, kDaveSignerKey, 1, alice, 1)},
       // Version one answers this one `ZERO_AMOUNT`, because its order puts that
       // condition first. Version six puts the shared envelope checks ahead of
       // every kind's own conditions, so the same bytes against the same balance
       // answer `INSUFFICIENT_BALANCE`.
       {"dave_sends_a_zero_amount_holding_nothing",
        transfer_input(signatures, ledger, kDaveSignerKey, 1, alice, 0)}});
  // Nothing Dave can sign reaches its own kind's conditions while his escrow
  // cannot cover the fee, so the enrollment refusal is only observable after
  // somebody already inside the ecosystem sends him value.
  run(scenario, signatures,
      {{"alice_funds_dave",
        confirmed_transfer_input(signatures, ledger, 1, dave, kTransferAmount,
                                 kAliceIdentity, kAliceKey, kAliceSignerKey,
                                 alice)}});
  run(scenario, signatures,
      {{"dave_collects_with_no_enrollment",
        verified_user_mint_input(signatures, ledger, kDaveIdentity, 1, dave,
                                 kDaveKey, kDaveSignerKey)}});
  return scenario;
}

// Maria holds her face and nothing else, and the chain is enough.
Scenario recovery_scenario(Signatures& signatures) {
  Scenario scenario{"recovery", open_trace_ledger(), {}, {}, {}, {}, 0};
  auto& ledger = scenario.ledger;
  const auto maria = first_escrow(kMariaIdentity);
  const auto bob = first_escrow(kBobIdentity);

  run(scenario, signatures,
      {{"maria_registers",
        register_input(signatures, ledger, kMariaIdentity, kMariaKey,
                       kMariaLostSignerKey)},
       {"bob_registers",
        register_input(signatures, ledger, kBobIdentity, kBobKey, kBobSignerKey)}});

  v6::Body revoke;
  revoke.hub_identity_hash = kMariaIdentity;
  revoke.escrow_id = maria;
  revoke.signer_id = v6::signer_id(kMariaLostSignerKey);
  run(scenario, signatures,
      {{"maria_revokes_her_only_signer",
        build(signatures, ledger,
              static_cast<std::uint8_t>(v6::Kind::signer_revoke), kMariaKey, 1,
              revoke)}});

  v6::Body add;
  add.hub_identity_hash = kMariaIdentity;
  add.escrow_id = maria;
  add.signer_public_key = kMariaNewSignerKey;
  run(scenario, signatures,
      {{"the_revoked_key_still_tries_to_spend",
        transfer_input(signatures, ledger, kMariaLostSignerKey, 2, bob,
                       kTransferAmount)},
       {"maria_assigns_a_new_signer",
        build(signatures, ledger, static_cast<std::uint8_t>(v6::Kind::signer_add),
              kMariaKey, 2, add)}});
  run(scenario, signatures,
      {{"maria_spends_with_the_new_key",
        confirmed_transfer_input(signatures, ledger, 3, bob, kTransferAmount,
                                 kMariaIdentity, kMariaKey, kMariaNewSignerKey,
                                 maria)}});
  return scenario;
}

// The chain identifier is stamped to the accepted vectors' value so the accepted
// bytes are admitted rather than refused with `WRONG_CHAIN`; every other field is
// a version-six genesis's. That is the only way the exact 200 octets can reach
// execution at all, and reaching execution is the whole point.
Scenario compatibility_scenario(Signatures& signatures,
                                const pv::Values& primitives) {
  const auto chain_id = from_hex(expect_text(primitives, "chain_id"));
  pv::require(chain_id == kAcceptedChainId,
              "the accepted chain identifier is the ascending fixture value");
  const auto sender_key = from_hex(expect_text(primitives, "rfc8032.public_key"));
  const auto recipient = from_hex(expect_text(primitives, "tx.recipient"));
  pv::require(recipient == kAcceptedRecipient,
              "the accepted recipient is the ascending fixture value");
  const auto signature = pv::hex_decode(expect_text(primitives, "signature"));

  Scenario scenario{"compatibility", open_trace_ledger(&chain_id), {}, {}, {}, {}, 0};
  auto& ledger = scenario.ledger;
  const auto sender = first_escrow(kAcceptedIdentity);
  const auto bob = first_escrow(kBobIdentity);

  run(scenario, signatures,
      {{"the_sender_registers",
        register_input(signatures, ledger, kAcceptedIdentity, kAcceptedHubKey,
                       sender_key, kAcceptedValidUntil)},
       {"bob_registers",
        register_input(signatures, ledger, kBobIdentity, kBobKey, kBobSignerKey,
                       kAcceptedValidUntil)}});

  // The accepted 200 octets, with the accepted signature adopted as-is: this
  // fixture chose none of these bytes.
  v6::Envelope accepted;
  accepted.kind = static_cast<std::uint8_t>(v6::Kind::native_transfer);
  accepted.chain_id = chain_id;
  accepted.scheme = v6::kSchemeSigner;
  accepted.authority_public_key = sender_key;
  accepted.nonce = kAcceptedNonce;
  v6::Body accepted_body;
  accepted_body.recipient_escrow_id = recipient;
  accepted_body.amount_atomic = kAcceptedAmount;
  accepted.body = v6::encode_body(accepted.kind, accepted_body);
  accepted.fee_limit = kAcceptedFeeLimit;
  accepted.valid_until_height = kAcceptedValidUntil;
  const auto unsigned_transaction = v6::encode_unsigned(accepted);
  signatures.adopt(sender_key, v6::signing_message(unsigned_transaction), signature);
  run(scenario, signatures,
      {{"the_accepted_transfer", v6::encode_signed(accepted, signature)}});

  v6::Posture relaxed;
  relaxed.requires_confirmation = false;
  run(scenario, signatures,
      {{"the_sender_relaxes_its_posture",
        posture_input(signatures, ledger, 1, relaxed, true, kAcceptedIdentity,
                      kAcceptedHubKey, sender_key, sender, kAcceptedValidUntil)}});

  v6::Body rerouted;
  rerouted.recipient_escrow_id = bob;
  rerouted.amount_atomic = kAcceptedAmount;
  run(scenario, signatures,
      {{"the_same_transfer_to_a_registered_recipient",
        build(signatures, ledger,
              static_cast<std::uint8_t>(v6::Kind::native_transfer), sender_key, 2,
              rerouted, kAcceptedValidUntil, kAcceptedFeeLimit)}});
  return scenario;
}

// Both directions, including a change that tightens and relaxes at once.
Scenario posture_scenario(Signatures& signatures) {
  Scenario scenario{"posture", open_trace_ledger(), {}, {}, {}, {}, 0};
  auto& ledger = scenario.ledger;
  const auto alice = first_escrow(kAliceIdentity);
  const auto bob = first_escrow(kBobIdentity);

  run(scenario, signatures,
      {{"alice_registers",
        register_input(signatures, ledger, kAliceIdentity, kAliceKey,
                       kAliceSignerKey)},
       {"bob_registers",
        register_input(signatures, ledger, kBobIdentity, kBobKey, kBobSignerKey)}});

  v6::Posture exempt;
  exempt.exempt_slot_mask = 0b1;
  v6::Posture mixed;
  mixed.min_amount_atomic = kPostureMinimum;
  const v6::Posture strict;

  const auto change = [&](std::uint64_t nonce, const v6::Posture& posture,
                          bool signed_) {
    return posture_input(signatures, ledger, nonce, posture, signed_,
                         kAliceIdentity, kAliceKey, kAliceSignerKey, alice);
  };
  run(scenario, signatures,
      {{"relax_the_slot_mask_unsigned", change(1, exempt, false)},
       {"relax_the_slot_mask_signed", change(1, exempt, true)}});
  run(scenario, signatures,
      {{"mixed_change_unsigned", change(2, mixed, false)},
       {"mixed_change_signed", change(2, mixed, true)}});
  run(scenario, signatures,
      {{"transfer_below_the_minimum",
        transfer_input(signatures, ledger, kAliceSignerKey, 3, bob,
                       kPostureMinimum - 1)},
       {"transfer_at_the_minimum",
        transfer_input(signatures, ledger, kAliceSignerKey, 4, bob,
                       kPostureMinimum)}});
  run(scenario, signatures,
      {{"tighten_signed", change(4, strict, true)},
       {"tighten_unsigned", change(4, strict, false)},
       {"tighten_to_the_same_posture", change(5, strict, false)}});
  return scenario;
}

}  // namespace economy_v6_execution
