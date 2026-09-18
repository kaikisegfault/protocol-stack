// The trace scaffolding: the genesis every scenario opens on, the builders that
// reproduce the model's exact transaction bytes, and the three recorded chains.
//
// Reproducing a recorded outcome means rebuilding the exact transactions that
// produced it, down to the signature bytes: a transaction ID is a digest over
// the signed bytes, so a signature issued in a different order would produce a
// different receipt and a different transaction root. The builders therefore
// issue a body's own signature before the envelope's, which is the order the
// model issues them in for the structural reason that a body must be complete
// before the envelope containing it can be encoded.

#include "economy_v9_execution_fixture.hpp"

#include <algorithm>

namespace economy_v9_execution {
namespace {

// One machine answering every challenge the chain issues it, and its log.
//
// **The log is the evidence.** A trace cannot pre-compute which of its own
// machines will be audited — that unpredictability is the property the pipeline
// exists to have — so what a scenario can state afterwards is that every
// challenge it was issued was answered, and the counts are how that is checked.
class Responder {
 public:
  Responder(Signatures& signatures, v9::Ledger& ledger, std::uint32_t seat_id,
            const Octets32& escrow, const Octets32& signer_key, bool silent)
      : signatures_(&signatures),
        ledger_(&ledger),
        seat_id_(seat_id),
        escrow_(escrow),
        signer_key_(signer_key),
        silent_(silent) {}

  std::vector<Bytes> operator()(std::uint64_t height,
                                std::span<const std::uint32_t> issued) {
    if (std::find(issued.begin(), issued.end(), seat_id_) == issued.end()) {
      return {};
    }
    challenged_ += 1;
    if (silent_) return {};
    answered_ += 1;
    const auto account = ledger_->registry.accounts.find(escrow_);
    const auto nonce =
        (account == ledger_->registry.accounts.end() ? 0 : account->second.nonce) + 1;
    return {response_input(*signatures_, *ledger_, signer_key_, seat_id_, height,
                           nonce)};
  }

  std::uint64_t challenged() const { return challenged_; }
  std::uint64_t answered() const { return answered_; }

 private:
  Signatures* signatures_;
  v9::Ledger* ledger_;
  std::uint32_t seat_id_;
  Octets32 escrow_;
  Octets32 signer_key_;
  bool silent_;
  std::uint64_t challenged_ = 0;
  std::uint64_t answered_ = 0;
};

std::uint64_t nonce_of(const v9::Ledger& ledger, const Octets32& escrow) {
  const auto account = ledger.registry.accounts.find(escrow);
  return account == ledger.registry.accounts.end() ? 0 : account->second.nonce;
}

// Register both people, sell each an unreferred seat, and activate both.
//
// The shorthand that jumps to the activation height is used exactly once and
// only before any activation, which is the only stretch of a version-nine chain
// where a block with no transactions really does change height and nothing else:
// once a seat is in scope the issue step and the expiry step run at every
// height.
Scenario seated_chain(Signatures& signatures, const std::string& name,
                      std::uint64_t (*stamp)(std::uint64_t)) {
  Scenario scenario;
  scenario.name = name;
  scenario.ledger = open_trace_ledger();
  auto& ledger = scenario.ledger;

  run(scenario, signatures, stamp(ledger.height + 1),
      {{"alice_registers",
        register_input(signatures, ledger, kAliceIdentity, kAliceKey,
                       kAliceSignerKey)},
       {"bob_registers",
        register_input(signatures, ledger, kBobIdentity, kBobKey, kBobSignerKey)}});
  run(scenario, signatures, stamp(ledger.height + 1),
      {{"seat_0_purchased",
        purchase_input(signatures, ledger, kAliceIdentity, kAliceKey,
                       kAliceSignerKey, kAliceSeat, 1)},
       {"seat_1_purchased",
        purchase_input(signatures, ledger, kBobIdentity, kBobKey, kBobSignerKey,
                       kBobSeat, 1)}});

  // The shorthand: every height up to the one before activation, with the stamp
  // carried through it. **The stamp is not optional here**, which is the one
  // place version nine could have inherited a latent defect — a shorthand that
  // advanced the height and left it behind would commit a root naming a height
  // the stamp does not belong to.
  scenario.skipped_blocks = kActivationHeight - 1 - ledger.height;
  ledger.height = kActivationHeight - 1;
  ledger.timestamp = stamp(kActivationHeight - 1);
  const auto root = v9::ledger_state_root(ledger);
  pv::require(root.has_value(), "the shorthand leaves a committable state");
  scenario.root_after_the_shorthand = *root;
  scenario.timestamp_after_the_shorthand = ledger.timestamp;

  run(scenario, signatures, stamp(ledger.height + 1),
      {{"seat_0_activated",
        activate_input(signatures, ledger, kAliceIdentity, kAliceKey,
                       kAliceSignerKey, kAliceSeat, 2)},
       {"seat_1_activated",
        activate_input(signatures, ledger, kBobIdentity, kBobKey, kBobSignerKey,
                       kBobSeat, 2)}});
  return scenario;
}

// Run the measured stretch with both machines answering through one responder,
// because `run_quiet_heights` takes one.
void measure(Scenario& scenario, Signatures& signatures, std::uint64_t target,
             std::uint64_t (*stamp)(std::uint64_t)) {
  Responder alice(signatures, scenario.ledger, kAliceSeat, kAliceEscrow,
                  kAliceSignerKey, false);
  Responder bob(signatures, scenario.ledger, kBobSeat, kBobEscrow, kBobSignerKey,
                true);
  const auto respond = [&alice, &bob](std::uint64_t height,
                                      std::span<const std::uint32_t> issued) {
    auto inputs = alice(height, issued);
    auto from_bob = bob(height, issued);
    inputs.insert(inputs.end(), from_bob.begin(), from_bob.end());
    return inputs;
  };
  auto run_result = v9::run_quiet_heights(
      scenario.ledger, target, [stamp](std::uint64_t height) { return stamp(height); },
      signatures.verifier(), respond);
  pv::require(run_result.has_value(), "the measured run must complete");
  scenario.quiet_heights = run_result->heights;
  scenario.audit_blocks = std::move(run_result->recorded);
  scenario.alice_challenged = alice.challenged();
  scenario.alice_answered = alice.answered();
  scenario.bob_challenged = bob.challenged();
  scenario.bob_answered = bob.answered();
}

}  // namespace

v9::Genesis trace_genesis() {
  // A Founder Economy genesis: no allocation, no accounts, a nonzero fee, and
  // the one field version nine adds.
  v9::Genesis genesis;
  genesis.network_id = kNetworkId;
  genesis.genesis_timestamp = kGenesisMillis;
  genesis.supply_limit = kSupplyLimit;
  genesis.fixed_transfer_fee = kFixedFee;
  genesis.manifest_digest = from_hex(std::string(kManifestDigestHex));
  genesis.verifier_key = kVerifierKey;
  genesis.dispute_authority_key = kDisputeAuthorityKey;
  return genesis;
}

v9::Ledger open_trace_ledger() {
  auto ledger = v9::open_ledger(trace_genesis());
  pv::require(ledger.has_value(), "the trace genesis must open a ledger");
  return *ledger;
}

Bytes build(Signatures& signatures, const v9::Ledger& ledger, std::uint8_t kind,
            const Octets32& authority, std::uint64_t nonce, const v9::Body& body,
            std::uint64_t valid_until, std::uint64_t fee_limit) {
  v9::Envelope envelope;
  envelope.kind = kind;
  envelope.chain_id = ledger.chain_id;
  const auto scheme = v9::kind_scheme(kind);
  pv::require(scheme.has_value(), "every built kind permits a scheme");
  envelope.scheme = *scheme;
  envelope.authority_public_key = authority;
  envelope.nonce = nonce;
  envelope.body = v9::encode_body(kind, body);
  pv::require(!envelope.body.empty(), "a built body must encode");
  // The two fee-exempt kinds carry a zero fee limit rather than one. A
  // registration always did, because it has no escrow yet and therefore no nonce
  // sequence and nothing to charge; a challenge response does on the founder
  // answer of 2026-09-02, and offering one with a nonzero limit is refused at
  // admission.
  const bool exempt = kind == static_cast<std::uint8_t>(v9::Kind::hub_register) ||
                      kind == static_cast<std::uint8_t>(v9::Kind::challenge_response);
  envelope.fee_limit = exempt ? 0 : fee_limit;
  envelope.valid_until_height = valid_until;

  const auto unsigned_transaction = v9::encode_unsigned(envelope);
  const auto signature =
      signatures.sign(authority, v9::signing_message(unsigned_transaction));
  return v9::encode_signed(envelope, signature);
}

Bytes register_input(Signatures& signatures, const v9::Ledger& ledger,
                     const Octets32& identity, const Octets32& hub_key,
                     const Octets32& signer_key) {
  const auto message = v9::registration_message(
      ledger.chain_id, identity, hub_key, signer_key, kInheritedValidUntil);
  v9::Body body;
  body.hub_identity_hash = identity;
  body.first_signer_public_key = signer_key;
  body.verifier_signature = signatures.sign(kVerifierKey, message);
  return build(signatures, ledger, static_cast<std::uint8_t>(v9::Kind::hub_register),
               hub_key, 0, body, kInheritedValidUntil);
}

Bytes purchase_input(Signatures& signatures, const v9::Ledger& ledger,
                     const Octets32& identity, const Octets32& hub_key,
                     const Octets32& signer_key, std::uint32_t seat_id,
                     std::uint64_t nonce) {
  const auto message =
      v9::purchase_message(ledger.chain_id, identity, seat_id, kValidUntil);
  v9::Body body;
  body.seat_id = seat_id;
  body.has_referrer = false;
  body.hub_signature = signatures.sign(hub_key, message);
  return build(signatures, ledger, static_cast<std::uint8_t>(v9::Kind::purchase_seat),
               signer_key, nonce, body);
}

Bytes activate_input(Signatures& signatures, const v9::Ledger& ledger,
                     const Octets32& identity, const Octets32& hub_key,
                     const Octets32& signer_key, std::uint32_t seat_id,
                     std::uint64_t nonce) {
  const auto message =
      v9::activation_message(ledger.chain_id, identity, seat_id, kValidUntil);
  v9::Body body;
  body.seat_id = seat_id;
  body.hub_signature = signatures.sign(hub_key, message);
  return build(signatures, ledger, static_cast<std::uint8_t>(v9::Kind::activate_seat),
               signer_key, nonce, body);
}

Bytes response_input(Signatures& signatures, const v9::Ledger& ledger,
                     const Octets32& signer_key, std::uint32_t seat_id,
                     std::uint64_t challenge_height, std::uint64_t nonce) {
  v9::Body body;
  body.seat_id = seat_id;
  body.challenge_height = challenge_height;
  body.answer = Bytes(v9::kAnswerBytes, 0);
  return build(signatures, ledger,
               static_cast<std::uint8_t>(v9::Kind::challenge_response), signer_key,
               nonce, body);
}

Bytes pool_mint_input(Signatures& signatures, const v9::Ledger& ledger,
                      const Octets32& identity, const Octets32& hub_key,
                      const Octets32& signer_key, std::uint32_t seat_id,
                      const Octets32& destination, std::uint64_t nonce,
                      bool confirm) {
  const auto kind = static_cast<std::uint8_t>(v9::Kind::mint_monthly_pool);
  v9::Body body;
  body.seat_id = seat_id;
  body.destination_escrow_id = destination;
  body.hub_signature = Bytes(v9::kSignatureBytes, 0);
  if (confirm) {
    const auto message = v9::mint_message(ledger.chain_id, identity, kind, seat_id,
                                          destination, kValidUntil);
    body.hub_signature = signatures.sign(hub_key, message);
  }
  return build(signatures, ledger, kind, signer_key, nonce, body);
}

const v9::BlockOutcome& run(Scenario& scenario, const Signatures& signatures,
                            std::uint64_t timestamp,
                            const std::vector<Step>& steps,
                            const v9::BlockOrder& order) {
  std::vector<Bytes> raw;
  std::vector<std::string> labels;
  raw.reserve(steps.size());
  for (const auto& step : steps) {
    raw.push_back(step.raw);
    labels.push_back(step.label);
  }
  auto block = v9::execute_block(scenario.ledger, timestamp, raw,
                                 signatures.verifier(), order);
  pv::require(block.has_value(), "every recorded block must execute: " +
                                     scenario.name + " at height " +
                                     std::to_string(scenario.ledger.height + 1));
  scenario.blocks.push_back(std::move(*block));
  scenario.labels.push_back(std::move(labels));
  return scenario.blocks.back();
}

Scenario settled_scenario(Signatures& signatures) {
  auto scenario = seated_chain(signatures, "settled", timestamp_of_height);
  auto& ledger = scenario.ledger;
  measure(scenario, signatures, kSettlementHeight, timestamp_of_height);

  pv::require(!scenario.audit_blocks.empty(), "the run recorded a settlement");
  const auto& settlement = scenario.audit_blocks.back();
  pv::require(settlement.settled.has_value() && !settlement.settled->winners.empty(),
              "February closes with a winner");
  const auto winner = settlement.settled->winners.front();

  // Both mints on the same nonce and in the same block: the refusal writes
  // nothing, so the mint that follows it is offered the sequence number the
  // refusal did not consume.
  const auto nonce = nonce_of(ledger, kAliceEscrow) + 1;
  run(scenario, signatures, timestamp_of_height(ledger.height + 1),
      {{"an_unconfirmed_mint_is_refused",
        pool_mint_input(signatures, ledger, kAliceIdentity, kAliceKey,
                        kAliceSignerKey, winner, kAliceEscrow, nonce, false)},
       {"winner_mints_the_pool",
        pool_mint_input(signatures, ledger, kAliceIdentity, kAliceKey,
                        kAliceSignerKey, winner, kAliceEscrow, nonce)}});
  run(scenario, signatures, timestamp_of_height(ledger.height + 1),
      {{"a_second_mint_collects_nothing",
        pool_mint_input(signatures, ledger, kAliceIdentity, kAliceKey,
                        kAliceSignerKey, winner, kAliceEscrow,
                        nonce_of(ledger, kAliceEscrow) + 1)},
       {"a_stranger_cannot_mint_another_seats_award",
        pool_mint_input(signatures, ledger, kBobIdentity, kBobKey, kBobSignerKey,
                        kAliceSeat, kBobEscrow,
                        nonce_of(ledger, kBobEscrow) + 1)}});
  return scenario;
}

Scenario rebuilt_chain_to(Signatures& signatures, std::uint64_t height) {
  auto scenario = seated_chain(signatures, "rebuilt", timestamp_of_height);
  measure(scenario, signatures, height, timestamp_of_height);
  return scenario;
}

Scenario halted_scenario(Signatures& signatures) {
  auto scenario = seated_chain(signatures, "halted", halted_timestamp_of_height);
  measure(scenario, signatures, kHaltedTargetHeight, halted_timestamp_of_height);
  return scenario;
}

Scenario restart_scenario(Signatures& signatures) {
  Scenario scenario;
  scenario.name = "restart";
  scenario.ledger = open_trace_ledger();
  auto& ledger = scenario.ledger;
  const auto stamp = [](std::size_t index) {
    return timestamp_of_height(kRestartStampHeights[index]);
  };

  run(scenario, signatures, stamp(0),
      {{"alice_registers",
        register_input(signatures, ledger, kAliceIdentity, kAliceKey,
                       kAliceSignerKey)},
       {"bob_registers",
        register_input(signatures, ledger, kBobIdentity, kBobKey, kBobSignerKey)}});
  run(scenario, signatures, stamp(1),
      {{"seat_0_purchased",
        purchase_input(signatures, ledger, kAliceIdentity, kAliceKey,
                       kAliceSignerKey, kAliceSeat, 1)},
       {"seat_1_purchased",
        purchase_input(signatures, ledger, kBobIdentity, kBobKey, kBobSignerKey,
                       kBobSeat, 1)}});

  // Height 3 is offered a stamp one millisecond below its predecessor's first.
  // The kernel's rejection carries no reason, so the condition is read from the
  // replay rule the block runs as its step 0, and the rejection itself from the
  // block.
  const auto below = stamp(1) - 1;
  scenario.refused_below_the_predecessor = v9::replay_timestamp(
      v9::Head{ledger.height, ledger.timestamp}, ledger.height + 1, below);
  scenario.refusal_rejected_the_block =
      !v9::execute_block(ledger, below, {}, signatures.verifier()).has_value();
  const auto root = v9::ledger_state_root(ledger);
  pv::require(root.has_value(), "the refused block leaves a committable state");
  scenario.root_after_the_refusal = *root;

  run(scenario, signatures, stamp(2), {});
  run(scenario, signatures, stamp(3),
      {{"seat_0_activated",
        activate_input(signatures, ledger, kAliceIdentity, kAliceKey,
                       kAliceSignerKey, kAliceSeat, 2)},
       {"seat_1_activated",
        activate_input(signatures, ledger, kBobIdentity, kBobKey, kBobSignerKey,
                       kBobSeat, 2)}});
  return scenario;
}

}  // namespace economy_v9_execution
