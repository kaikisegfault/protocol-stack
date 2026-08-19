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

#include "economy_v6_execution_fixture.hpp"

namespace economy_v6_execution {

v6::Genesis trace_genesis() {
  // A Founder Economy genesis: no allocation, no accounts, a nonzero fee.
  // Version six is the first contract under which that combination is
  // reachable, because registration is fee-exempt and pays the entry airdrop.
  v6::Genesis genesis;
  genesis.network_id = kNetworkId;
  genesis.supply_limit = kSupplyLimit;
  genesis.fixed_transfer_fee = kFixedFee;
  genesis.manifest_digest =
      from_hex("84cca09865b6c62bf09d3f6bc3821a2527c7a4835652cffdc0ebefa34b314ce5");
  genesis.verifier_key = kVerifierKey;
  return genesis;
}

v6::Ledger open_trace_ledger(const Octets32* chain_id) {
  auto ledger = v6::open_ledger(trace_genesis());
  pv::require(ledger.has_value(), "the trace genesis must open a ledger");
  if (chain_id != nullptr) ledger->chain_id = *chain_id;
  return *ledger;
}

Bytes build(Signatures& signatures, const v6::Ledger& ledger, std::uint8_t kind,
            const Octets32& authority, std::uint64_t nonce, const v6::Body& body,
            std::uint64_t valid_until, std::uint64_t fee_limit) {
  v6::Envelope envelope;
  envelope.kind = kind;
  envelope.chain_id = ledger.chain_id;
  const auto scheme = v6::kind_scheme(kind);
  pv::require(scheme.has_value(), "every built kind permits a scheme");
  envelope.scheme = *scheme;
  envelope.authority_public_key = authority;
  envelope.nonce = nonce;
  envelope.body = v6::encode_body(kind, body);
  pv::require(!envelope.body.empty() || v6::body_bytes(kind) == 0,
              "a built body must encode");
  // A registration has no escrow yet, so it has no nonce sequence to advance and
  // nothing to charge; both fields are required to be zero.
  envelope.fee_limit =
      kind == static_cast<std::uint8_t>(v6::Kind::hub_register) ? 0 : fee_limit;
  envelope.valid_until_height = valid_until;

  const auto unsigned_transaction = v6::encode_unsigned(envelope);
  const auto signature =
      signatures.sign(authority, v6::signing_message(unsigned_transaction));
  return v6::encode_signed(envelope, signature);
}

Bytes register_input(Signatures& signatures, const v6::Ledger& ledger,
                     const Octets32& identity, const Octets32& hub_key,
                     const Octets32& signer_key, std::uint64_t valid_until) {
  const auto message = v6::registration_message(ledger.chain_id, identity, hub_key,
                                                signer_key, valid_until);
  v6::Body body;
  body.hub_identity_hash = identity;
  body.first_signer_public_key = signer_key;
  body.verifier_signature = signatures.sign(kVerifierKey, message);
  return build(signatures, ledger, static_cast<std::uint8_t>(v6::Kind::hub_register),
               hub_key, 0, body, valid_until);
}

Bytes transfer_input(Signatures& signatures, const v6::Ledger& ledger,
                     const Octets32& signer_key, std::uint64_t nonce,
                     const Octets32& recipient, std::uint64_t amount) {
  v6::Body body;
  body.recipient_escrow_id = recipient;
  body.amount_atomic = amount;
  return build(signatures, ledger,
               static_cast<std::uint8_t>(v6::Kind::native_transfer), signer_key,
               nonce, body);
}

Bytes confirmed_transfer_input(Signatures& signatures, const v6::Ledger& ledger,
                               std::uint64_t nonce, const Octets32& recipient,
                               std::uint64_t amount, const Octets32& identity,
                               const Octets32& hub_key,
                               const Octets32& signer_key,
                               const Octets32& escrow) {
  const auto message = v6::transfer_confirm_message(
      ledger.chain_id, identity, escrow, recipient, amount, kValidUntil);
  v6::Body body;
  body.recipient_escrow_id = recipient;
  body.amount_atomic = amount;
  body.hub_signature = signatures.sign(hub_key, message);
  return build(signatures, ledger,
               static_cast<std::uint8_t>(v6::Kind::native_transfer_verified),
               signer_key, nonce, body);
}

Bytes verified_user_mint_input(Signatures& signatures, const v6::Ledger& ledger,
                               const Octets32& identity, std::uint64_t nonce,
                               const Octets32& destination,
                               const Octets32& hub_key,
                               const Octets32& signer_key) {
  const auto kind = static_cast<std::uint8_t>(v6::Kind::mint_verified_user);
  const auto message = v6::mint_message(ledger.chain_id, identity, kind, 0,
                                        destination, kValidUntil);
  v6::Body body;
  body.destination_escrow_id = destination;
  body.hub_signature = signatures.sign(hub_key, message);
  return build(signatures, ledger, kind, signer_key, nonce, body);
}

Bytes posture_input(Signatures& signatures, const v6::Ledger& ledger,
                    std::uint64_t nonce, const v6::Posture& posture, bool signed_,
                    const Octets32& identity, const Octets32& hub_key,
                    const Octets32& signer_key, const Octets32& escrow,
                    std::uint64_t valid_until) {
  const auto message = v6::posture_relax_message(ledger.chain_id, identity, escrow,
                                                 posture, valid_until);
  v6::Body body;
  body.requires_confirmation = posture.requires_confirmation;
  body.min_amount_atomic = posture.min_amount_atomic;
  body.exempt_slot_mask = posture.exempt_slot_mask;
  // The unsigned direction carries 64 zero octets, which is the one encoding an
  // operation requiring no confirmation is permitted to use.
  body.hub_signature = signed_ ? signatures.sign(hub_key, message)
                               : Bytes(v6::kSignatureBytes, 0);
  return build(signatures, ledger,
               static_cast<std::uint8_t>(v6::Kind::set_security_posture),
               signer_key, nonce, body, valid_until);
}

const v6::BlockOutcome& run(Scenario& scenario, const Signatures& signatures,
                            const std::vector<Step>& steps) {
  std::vector<Bytes> raw_inputs;
  raw_inputs.reserve(steps.size());
  for (const auto& step : steps) raw_inputs.push_back(step.raw);

  auto outcome =
      v6::execute_block(scenario.ledger, raw_inputs, signatures.verifier());
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
  scenario.skipped_blocks = height - scenario.ledger.height;
  scenario.ledger.height = height;
}

}  // namespace economy_v6_execution
