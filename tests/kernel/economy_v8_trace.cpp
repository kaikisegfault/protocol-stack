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

#include "economy_v8_execution_fixture.hpp"

#include <algorithm>

namespace economy_v8_execution {

v8::Genesis trace_genesis() {
  // A Founder Economy genesis: no allocation, no accounts, a nonzero fee.
  // Version six is the first contract under which that combination is
  // reachable, because registration is fee-exempt and pays the entry airdrop,
  // and version seven inherits it without restating it.
  v8::Genesis genesis;
  genesis.network_id = kNetworkId;
  genesis.supply_limit = kSupplyLimit;
  genesis.fixed_transfer_fee = kFixedFee;
  genesis.manifest_digest = from_hex(std::string(kManifestDigestHex));
  genesis.verifier_key = kVerifierKey;
  genesis.dispute_authority_key = kDisputeAuthorityKey;
  return genesis;
}

v8::Ledger open_trace_ledger(const Octets32* chain_id) {
  auto ledger = v8::open_ledger(trace_genesis());
  pv::require(ledger.has_value(), "the trace genesis must open a ledger");
  if (chain_id != nullptr) ledger->chain_id = *chain_id;
  return *ledger;
}

Bytes build(Signatures& signatures, const v8::Ledger& ledger, std::uint8_t kind,
            const Octets32& authority, std::uint64_t nonce, const v8::Body& body,
            std::uint64_t valid_until, std::uint64_t fee_limit) {
  v8::Envelope envelope;
  envelope.kind = kind;
  envelope.chain_id = ledger.chain_id;
  const auto scheme = v8::kind_scheme(kind);
  pv::require(scheme.has_value(), "every built kind permits a scheme");
  envelope.scheme = *scheme;
  envelope.authority_public_key = authority;
  envelope.nonce = nonce;
  envelope.body = v8::encode_body(kind, body);
  pv::require(!envelope.body.empty() || v8::body_bytes(kind) == 0,
              "a built body must encode");
  // The two fee-exempt kinds carry a zero fee limit rather than one. A
  // registration always did, because it has no escrow yet and therefore no
  // nonce sequence and nothing to charge; a challenge response does on the
  // founder answer of 2026-09-02, and offering one with a nonzero limit is
  // refused at admission.
  const bool exempt = kind == static_cast<std::uint8_t>(v8::Kind::hub_register) ||
                      kind == static_cast<std::uint8_t>(v8::Kind::challenge_response);
  envelope.fee_limit = exempt ? 0 : fee_limit;
  envelope.valid_until_height = valid_until;

  const auto unsigned_transaction = v8::encode_unsigned(envelope);
  const auto signature =
      signatures.sign(authority, v8::signing_message(unsigned_transaction));
  return v8::encode_signed(envelope, signature);
}

Bytes register_input(Signatures& signatures, const v8::Ledger& ledger,
                     const Octets32& identity, const Octets32& hub_key,
                     const Octets32& signer_key, std::uint64_t valid_until) {
  const auto message = v8::registration_message(ledger.chain_id, identity, hub_key,
                                                signer_key, valid_until);
  v8::Body body;
  body.hub_identity_hash = identity;
  body.first_signer_public_key = signer_key;
  body.verifier_signature = signatures.sign(kVerifierKey, message);
  return build(signatures, ledger, static_cast<std::uint8_t>(v8::Kind::hub_register),
               hub_key, 0, body, valid_until);
}

Bytes transfer_input(Signatures& signatures, const v8::Ledger& ledger,
                     const Octets32& signer_key, std::uint64_t nonce,
                     const Octets32& recipient, std::uint64_t amount) {
  v8::Body body;
  body.recipient_escrow_id = recipient;
  body.amount_atomic = amount;
  return build(signatures, ledger,
               static_cast<std::uint8_t>(v8::Kind::native_transfer), signer_key,
               nonce, body, kInheritedValidUntil);
}

Bytes confirmed_transfer_input(Signatures& signatures, const v8::Ledger& ledger,
                               std::uint64_t nonce, const Octets32& recipient,
                               std::uint64_t amount, const Octets32& identity,
                               const Octets32& hub_key,
                               const Octets32& signer_key,
                               const Octets32& escrow,
                               std::uint64_t valid_until) {
  const auto message = v8::transfer_confirm_message(
      ledger.chain_id, identity, escrow, recipient, amount, valid_until);
  v8::Body body;
  body.recipient_escrow_id = recipient;
  body.amount_atomic = amount;
  body.hub_signature = signatures.sign(hub_key, message);
  return build(signatures, ledger,
               static_cast<std::uint8_t>(v8::Kind::native_transfer_verified),
               signer_key, nonce, body, valid_until);
}

Bytes verified_user_mint_input(Signatures& signatures, const v8::Ledger& ledger,
                               const Octets32& identity, std::uint64_t nonce,
                               const Octets32& destination,
                               const Octets32& hub_key,
                               const Octets32& signer_key,
                               std::uint64_t valid_until) {
  const auto kind = static_cast<std::uint8_t>(v8::Kind::mint_verified_user);
  const auto message = v8::mint_message(ledger.chain_id, identity, kind, 0,
                                        destination, valid_until);
  v8::Body body;
  body.destination_escrow_id = destination;
  body.hub_signature = signatures.sign(hub_key, message);
  return build(signatures, ledger, kind, signer_key, nonce, body, valid_until);
}

// Kind 2. The referrer is named by escrow — the shareable thing — and recorded
// as an identity, so referral earnings follow the person rather than the address.
Bytes purchase_input(Signatures& signatures, const v8::Ledger& ledger,
                     const Octets32& identity, const Octets32& hub_key,
                     const Octets32& signer_key, std::uint32_t seat_id,
                     std::uint64_t nonce, const Octets32* referrer) {
  const auto message =
      v8::purchase_message(ledger.chain_id, identity, seat_id, kValidUntil);
  v8::Body body;
  body.seat_id = seat_id;
  body.has_referrer = referrer != nullptr;
  if (referrer != nullptr) body.referrer_escrow_id = *referrer;
  body.hub_signature = signatures.sign(hub_key, message);
  return build(signatures, ledger,
               static_cast<std::uint8_t>(v8::Kind::purchase_seat), signer_key,
               nonce, body);
}

// Kind 3.
Bytes activate_input(Signatures& signatures, const v8::Ledger& ledger,
                     const Octets32& identity, const Octets32& hub_key,
                     const Octets32& signer_key, std::uint32_t seat_id,
                     std::uint64_t nonce) {
  const auto message =
      v8::activation_message(ledger.chain_id, identity, seat_id, kValidUntil);
  v8::Body body;
  body.seat_id = seat_id;
  body.hub_signature = signatures.sign(hub_key, message);
  return build(signatures, ledger,
               static_cast<std::uint8_t>(v8::Kind::activate_seat), signer_key,
               nonce, body);
}

// Kind 4. The default posture requires a confirmation at every amount, so every
// node mint in this trace carries a real HUB signature over the mint message.
Bytes node_mint_input(Signatures& signatures, const v8::Ledger& ledger,
                      const Octets32& identity, const Octets32& hub_key,
                      const Octets32& signer_key, std::uint32_t seat_id,
                      const Octets32& destination, std::uint64_t nonce) {
  const auto kind = static_cast<std::uint8_t>(v8::Kind::mint_node);
  const auto message = v8::mint_message(ledger.chain_id, identity, kind, seat_id,
                                        destination, kValidUntil);
  v8::Body body;
  body.seat_id = seat_id;
  body.destination_escrow_id = destination;
  body.hub_signature = signatures.sign(hub_key, message);
  return build(signatures, ledger, kind, signer_key, nonce, body);
}

// Kind 5. Any escrow of the person may receive it, because the balance is the
// identity's rather than an address's.
Bytes referral_mint_input(Signatures& signatures, const v8::Ledger& ledger,
                          const Octets32& identity, const Octets32& hub_key,
                          const Octets32& signer_key,
                          const Octets32& destination, std::uint64_t nonce) {
  const auto kind = static_cast<std::uint8_t>(v8::Kind::mint_referral);
  const auto message = v8::mint_message(ledger.chain_id, identity, kind, 0,
                                        destination, kValidUntil);
  v8::Body body;
  body.destination_escrow_id = destination;
  body.hub_signature = signatures.sign(hub_key, message);
  return build(signatures, ledger, kind, signer_key, nonce, body);
}

Bytes posture_input(Signatures& signatures, const v8::Ledger& ledger,
                    std::uint64_t nonce, const v8::Posture& posture, bool signed_,
                    const Octets32& identity, const Octets32& hub_key,
                    const Octets32& signer_key, const Octets32& escrow,
                    std::uint64_t valid_until) {
  const auto message = v8::posture_relax_message(ledger.chain_id, identity, escrow,
                                                 posture, valid_until);
  v8::Body body;
  body.requires_confirmation = posture.requires_confirmation;
  body.min_amount_atomic = posture.min_amount_atomic;
  body.exempt_slot_mask = posture.exempt_slot_mask;
  // The unsigned direction carries 64 zero octets, which is the one encoding an
  // operation requiring no confirmation is permitted to use.
  body.hub_signature = signed_ ? signatures.sign(hub_key, message)
                               : Bytes(v8::kSignatureBytes, 0);
  return build(signatures, ledger,
               static_cast<std::uint8_t>(v8::Kind::set_security_posture),
               signer_key, nonce, body, valid_until);
}

const v8::BlockOutcome& run(Scenario& scenario, const Signatures& signatures,
                            const std::vector<Step>& steps,
                            const v8::BlockOrder& order) {
  std::vector<Bytes> raw_inputs;
  raw_inputs.reserve(steps.size());
  for (const auto& step : steps) raw_inputs.push_back(step.raw);

  auto outcome = v8::execute_block(scenario.ledger, raw_inputs,
                                   signatures.verifier(), order);
  pv::require(outcome.has_value(),
              scenario.name + ": the whole block was rejected");
  scenario.blocks.push_back(std::move(*outcome));
  scenario.raw_inputs.push_back(steps.size());
  scenario.block_inputs.push_back(raw_inputs);

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

// --- the two builders version eight adds -------------------------------

Bytes response_input(Signatures& signatures, const v8::Ledger& ledger,
                     const Octets32& signer_key, std::uint32_t seat_id,
                     std::uint64_t challenge_height, std::uint64_t nonce,
                     const Bytes* answer) {
  v8::Body body;
  body.seat_id = seat_id;
  body.challenge_height = challenge_height;
  // Opaque under this version: an answer of the defined width is accepted,
  // because the predicate that would judge it is the challenge's content and
  // that is founder-reserved.
  body.answer = answer != nullptr ? *answer : Bytes(v8::kAnswerBytes, 0);
  return build(signatures, ledger,
               static_cast<std::uint8_t>(v8::Kind::challenge_response),
               signer_key, nonce, body);
}

Bytes dispute_input(Signatures& signatures, const v8::Ledger& ledger,
                    const Octets32& signer_key, std::uint32_t seat_id,
                    std::uint64_t cycle_window, std::uint8_t slot_index,
                    std::uint64_t nonce, const Octets32& authority_key,
                    std::uint8_t reason_code, const std::uint8_t* signed_slot) {
  // The signed message binds the slot, so signing one and submitting another is
  // how a transition test reaches `UNAUTHORIZED_DISPUTE` without touching the
  // key: the table holds no entry for the message that arrives.
  const auto message =
      v8::dispute_message(ledger.chain_id, seat_id, cycle_window,
                          signed_slot != nullptr ? *signed_slot : slot_index,
                          reason_code, kValidUntil);
  v8::Body body;
  body.seat_id = seat_id;
  body.cycle_window = cycle_window;
  body.slot_index = slot_index;
  body.reason_code = reason_code;
  body.authority_signature = signatures.sign(authority_key, message);
  return build(signatures, ledger,
               static_cast<std::uint8_t>(v8::Kind::file_dispute), signer_key,
               nonce, body);
}

// --- the responder and the quiet run -----------------------------------

std::vector<Bytes> Responder::operator()(std::uint64_t height,
                                         std::span<const std::uint32_t> issued) {
  if (std::find(issued.begin(), issued.end(), seat_id_) == issued.end()) {
    return {};
  }
  challenged.push_back(height);
  // A machine that logs its audits and answers none. Its log is what lets a
  // scenario check the window record against the challenges that produced it,
  // from the other side.
  if (silent_) return {};
  answered.push_back(height);
  const auto nonce = ledger_->registry.accounts.count(escrow_) == 1
                         ? ledger_->registry.accounts.at(escrow_).nonce + 1
                         : 1;
  return {response_input(*signatures_, *ledger_, signer_key_, seat_id_, height,
                         nonce)};
}

std::set<std::uint32_t> Responder::slots() const {
  std::set<std::uint32_t> seen;
  for (const auto height : challenged) seen.insert(v8::slot_of(height));
  return seen;
}

std::uint64_t run_to(Scenario& scenario, const Signatures& signatures,
                     std::uint64_t target_height, Responder* responder) {
  v8::Responder respond;
  if (responder != nullptr) {
    respond = [responder](std::uint64_t height,
                          std::span<const std::uint32_t> issued) {
      return (*responder)(height, issued);
    };
  }
  auto run = v8::run_quiet_heights(scenario.ledger, target_height,
                                   signatures.verifier(), respond);
  pv::require(run.has_value(), scenario.name + ": a quiet run was rejected");
  scenario.quiet_heights += run->heights;
  for (auto& block : run->recorded) {
    scenario.audit_blocks.push_back(std::move(block));
  }
  return run->heights;
}

}  // namespace economy_v8_execution
