// The trace scaffolding: the genesis every scenario opens on, the builders that
// reproduce the model's exact transaction bytes, and the block runner.
//
// Reproducing a recorded outcome means rebuilding the exact transactions that
// produced it, down to the signature bytes: a transaction ID is a digest over
// the signed bytes, so a signature issued in a different order would produce a
// different receipt and a different transaction root. The builders therefore
// issue a body's own signature before the envelope's, which is the order the
// model issues them in for the structural reason that a body must be complete
// before the envelope containing it can be encoded.

#include "economy_v7_execution_fixture.hpp"

namespace economy_v7_execution {

v7::Genesis trace_genesis() {
  // A Founder Economy genesis: no allocation, no accounts, a nonzero fee.
  // Version six is the first contract under which that combination is
  // reachable, because registration is fee-exempt and pays the entry airdrop,
  // and version seven inherits it without restating it.
  v7::Genesis genesis;
  genesis.network_id = kNetworkId;
  genesis.supply_limit = kSupplyLimit;
  genesis.fixed_transfer_fee = kFixedFee;
  genesis.manifest_digest = from_hex(std::string(kManifestDigestHex));
  genesis.verifier_key = kVerifierKey;
  return genesis;
}

v7::Ledger open_trace_ledger(const Octets32* chain_id) {
  auto ledger = v7::open_ledger(trace_genesis());
  pv::require(ledger.has_value(), "the trace genesis must open a ledger");
  if (chain_id != nullptr) ledger->chain_id = *chain_id;
  return *ledger;
}

Bytes build(Signatures& signatures, const v7::Ledger& ledger, std::uint8_t kind,
            const Octets32& authority, std::uint64_t nonce, const v7::Body& body,
            std::uint64_t valid_until, std::uint64_t fee_limit) {
  v7::Envelope envelope;
  envelope.kind = kind;
  envelope.chain_id = ledger.chain_id;
  const auto scheme = v7::kind_scheme(kind);
  pv::require(scheme.has_value(), "every built kind permits a scheme");
  envelope.scheme = *scheme;
  envelope.authority_public_key = authority;
  envelope.nonce = nonce;
  envelope.body = v7::encode_body(kind, body);
  pv::require(!envelope.body.empty() || v7::body_bytes(kind) == 0,
              "a built body must encode");
  // A registration has no escrow yet, so it has no nonce sequence to advance and
  // nothing to charge; both fields are required to be zero.
  envelope.fee_limit =
      kind == static_cast<std::uint8_t>(v7::Kind::hub_register) ? 0 : fee_limit;
  envelope.valid_until_height = valid_until;

  const auto unsigned_transaction = v7::encode_unsigned(envelope);
  const auto signature =
      signatures.sign(authority, v7::signing_message(unsigned_transaction));
  return v7::encode_signed(envelope, signature);
}

Bytes register_input(Signatures& signatures, const v7::Ledger& ledger,
                     const Octets32& identity, const Octets32& hub_key,
                     const Octets32& signer_key, std::uint64_t valid_until) {
  const auto message = v7::registration_message(ledger.chain_id, identity, hub_key,
                                                signer_key, valid_until);
  v7::Body body;
  body.hub_identity_hash = identity;
  body.first_signer_public_key = signer_key;
  body.verifier_signature = signatures.sign(kVerifierKey, message);
  return build(signatures, ledger, static_cast<std::uint8_t>(v7::Kind::hub_register),
               hub_key, 0, body, valid_until);
}

Bytes transfer_input(Signatures& signatures, const v7::Ledger& ledger,
                     const Octets32& signer_key, std::uint64_t nonce,
                     const Octets32& recipient, std::uint64_t amount) {
  v7::Body body;
  body.recipient_escrow_id = recipient;
  body.amount_atomic = amount;
  return build(signatures, ledger,
               static_cast<std::uint8_t>(v7::Kind::native_transfer), signer_key,
               nonce, body);
}

Bytes confirmed_transfer_input(Signatures& signatures, const v7::Ledger& ledger,
                               std::uint64_t nonce, const Octets32& recipient,
                               std::uint64_t amount, const Octets32& identity,
                               const Octets32& hub_key,
                               const Octets32& signer_key,
                               const Octets32& escrow,
                               std::uint64_t valid_until) {
  const auto message = v7::transfer_confirm_message(
      ledger.chain_id, identity, escrow, recipient, amount, valid_until);
  v7::Body body;
  body.recipient_escrow_id = recipient;
  body.amount_atomic = amount;
  body.hub_signature = signatures.sign(hub_key, message);
  return build(signatures, ledger,
               static_cast<std::uint8_t>(v7::Kind::native_transfer_verified),
               signer_key, nonce, body, valid_until);
}

Bytes verified_user_mint_input(Signatures& signatures, const v7::Ledger& ledger,
                               const Octets32& identity, std::uint64_t nonce,
                               const Octets32& destination,
                               const Octets32& hub_key,
                               const Octets32& signer_key,
                               std::uint64_t valid_until) {
  const auto kind = static_cast<std::uint8_t>(v7::Kind::mint_verified_user);
  const auto message = v7::mint_message(ledger.chain_id, identity, kind, 0,
                                        destination, valid_until);
  v7::Body body;
  body.destination_escrow_id = destination;
  body.hub_signature = signatures.sign(hub_key, message);
  return build(signatures, ledger, kind, signer_key, nonce, body, valid_until);
}

// Kind 2. The referrer is named by escrow — the shareable thing — and recorded
// as an identity, so referral earnings follow the person rather than the address.
Bytes purchase_input(Signatures& signatures, const v7::Ledger& ledger,
                     const Octets32& identity, const Octets32& hub_key,
                     const Octets32& signer_key, std::uint32_t seat_id,
                     std::uint64_t nonce, const Octets32* referrer) {
  const auto message =
      v7::purchase_message(ledger.chain_id, identity, seat_id, kValidUntil);
  v7::Body body;
  body.seat_id = seat_id;
  body.has_referrer = referrer != nullptr;
  if (referrer != nullptr) body.referrer_escrow_id = *referrer;
  body.hub_signature = signatures.sign(hub_key, message);
  return build(signatures, ledger,
               static_cast<std::uint8_t>(v7::Kind::purchase_seat), signer_key,
               nonce, body);
}

// Kind 3.
Bytes activate_input(Signatures& signatures, const v7::Ledger& ledger,
                     const Octets32& identity, const Octets32& hub_key,
                     const Octets32& signer_key, std::uint32_t seat_id,
                     std::uint64_t nonce) {
  const auto message =
      v7::activation_message(ledger.chain_id, identity, seat_id, kValidUntil);
  v7::Body body;
  body.seat_id = seat_id;
  body.hub_signature = signatures.sign(hub_key, message);
  return build(signatures, ledger,
               static_cast<std::uint8_t>(v7::Kind::activate_seat), signer_key,
               nonce, body);
}

// Kind 4. The default posture requires a confirmation at every amount, so every
// node mint in this trace carries a real HUB signature over the mint message.
Bytes node_mint_input(Signatures& signatures, const v7::Ledger& ledger,
                      const Octets32& identity, const Octets32& hub_key,
                      const Octets32& signer_key, std::uint32_t seat_id,
                      const Octets32& destination, std::uint64_t nonce) {
  const auto kind = static_cast<std::uint8_t>(v7::Kind::mint_node);
  const auto message = v7::mint_message(ledger.chain_id, identity, kind, seat_id,
                                        destination, kValidUntil);
  v7::Body body;
  body.seat_id = seat_id;
  body.destination_escrow_id = destination;
  body.hub_signature = signatures.sign(hub_key, message);
  return build(signatures, ledger, kind, signer_key, nonce, body);
}

// Kind 5. Any escrow of the person may receive it, because the balance is the
// identity's rather than an address's.
Bytes referral_mint_input(Signatures& signatures, const v7::Ledger& ledger,
                          const Octets32& identity, const Octets32& hub_key,
                          const Octets32& signer_key,
                          const Octets32& destination, std::uint64_t nonce) {
  const auto kind = static_cast<std::uint8_t>(v7::Kind::mint_referral);
  const auto message = v7::mint_message(ledger.chain_id, identity, kind, 0,
                                        destination, kValidUntil);
  v7::Body body;
  body.destination_escrow_id = destination;
  body.hub_signature = signatures.sign(hub_key, message);
  return build(signatures, ledger, kind, signer_key, nonce, body);
}

Bytes posture_input(Signatures& signatures, const v7::Ledger& ledger,
                    std::uint64_t nonce, const v7::Posture& posture, bool signed_,
                    const Octets32& identity, const Octets32& hub_key,
                    const Octets32& signer_key, const Octets32& escrow,
                    std::uint64_t valid_until) {
  const auto message = v7::posture_relax_message(ledger.chain_id, identity, escrow,
                                                 posture, valid_until);
  v7::Body body;
  body.requires_confirmation = posture.requires_confirmation;
  body.min_amount_atomic = posture.min_amount_atomic;
  body.exempt_slot_mask = posture.exempt_slot_mask;
  // The unsigned direction carries 64 zero octets, which is the one encoding an
  // operation requiring no confirmation is permitted to use.
  body.hub_signature = signed_ ? signatures.sign(hub_key, message)
                               : Bytes(v7::kSignatureBytes, 0);
  return build(signatures, ledger,
               static_cast<std::uint8_t>(v7::Kind::set_security_posture),
               signer_key, nonce, body, valid_until);
}

const v7::BlockOutcome& run(Scenario& scenario, const Signatures& signatures,
                            const std::vector<Step>& steps,
                            const v7::UptimeSchedule* uptime,
                            bool assignment_is_prologue) {
  std::vector<Bytes> raw_inputs;
  raw_inputs.reserve(steps.size());
  for (const auto& step : steps) raw_inputs.push_back(step.raw);

  auto outcome = v7::execute_block(scenario.ledger, raw_inputs,
                                   signatures.verifier(), uptime,
                                   assignment_is_prologue);
  pv::require(outcome.has_value(),
              scenario.name + ": the whole block was rejected");
  scenario.blocks.push_back(std::move(*outcome));
  scenario.raw_inputs.push_back(steps.size());

  std::vector<std::string> labels;
  for (const auto& step : steps) {
    if (step.admits) labels.push_back(step.label);
  }
  scenario.labels.push_back(std::move(labels));

  const auto& block = scenario.blocks.back();
  pv::require(block.admissions.size() == steps.size(),
              scenario.name + ": every raw input has an admission outcome");
  for (std::size_t index = 0; index < steps.size(); ++index) {
    const auto& admission = block.admissions[index];
    pv::require(admission.admitted() == steps[index].admits,
                scenario.name + ": " + steps[index].label +
                    " was admitted against expectation");
    if (!steps[index].admits) {
      scenario.rejected[steps[index].label] =
          static_cast<std::uint8_t>(*admission.error);
    }
  }
  return block;
}

void advance_to(Scenario& scenario, std::uint64_t height) {
  pv::require(height >= scenario.ledger.height, "height never decreases");
  // Accumulated rather than assigned: a scenario that skips twice has skipped
  // the sum, and the vectors record one figure per scenario.
  scenario.skipped_blocks += height - scenario.ledger.height;
  scenario.ledger.height = height;
}

void advance_to_boundary(Scenario& scenario, std::uint64_t window) {
  advance_to(scenario, boundary_height(window) - 1);
}

}  // namespace economy_v7_execution
