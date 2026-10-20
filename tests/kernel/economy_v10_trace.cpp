// The builders and the recorded chain: `simulation/economy_transition_v10/
// fixture.py` and `trace.py`, rebuilt down to the signature bytes.
//
// The chain records, through blocks, the way a node runs them:
//
// 1. the launch key registers Alice and Bob, and refuses a forgery, a withheld
//    approval, a replayed identity, and a reused signer key;
// 2. the seats are bought and activated under whole-transaction approvals, and
//    a version-nine approval is refused;
// 3. kind 23 is refused at each of its seven conditions in order, then
//    registers Alice's machine and Bob's;
// 4. the two replays version nine executed are each refused in both forms;
// 5. the lifetime admits a scheme-2 kind at exactly one slot and refuses it one
//    height later, and does not govern a transaction with no HUB proof;
// 6. the registry step marks Alice's machine at the assignment of window 1, and
//    not Bob's, whose machine answered no audit;
// 7. machines register people;
// 8. the next window: the count restarts, Alice replaces her key and keeps her
//    count and her mark, the old key signs nothing, and every mint is approved
//    over the whole transaction.
//
// **Every step list is a braced initializer**, whose elements C++ evaluates in
// the order they appear, so each builder issues its signatures in the order the
// model's list literal does. Two transactions the model builds before its list
// are built before it here too.

#include "economy_v10_execution_fixture.hpp"

#include <algorithm>

namespace economy_v10_execution {
namespace {

using Kind = v10::Kind;

constexpr std::uint32_t kAliceSeat = 0;
constexpr std::uint32_t kBobSeat = 1;
constexpr std::uint32_t kBobIdleSeat = 2;

// Both seats activate near the end of window 0, so window 1 is the first window
// either is in scope for. Window 1 is assigned at the first height of window 3,
// and window 2 at the first height of window 4.
constexpr std::uint64_t kActivationHeight = v10::kCycleBlocks - 10;
constexpr std::uint64_t kFirstAssignmentHeight = 3 * v10::kCycleBlocks;
constexpr std::uint64_t kSecondAssignmentHeight = 4 * v10::kCycleBlocks;

const Bytes kNoSignature(v10::kSignatureBytes, 0);

std::uint8_t kind_byte(Kind kind) { return static_cast<std::uint8_t>(kind); }

// Execute one block of steps at the next height and record what the vectors
// read: the block, its labels, and each step's raw bytes and height.
void run(Chain& chain, const Signatures& signatures, std::vector<Step> steps) {
  std::vector<Bytes> raw;
  std::vector<std::string> labels;
  const auto height = chain.ledger.height + 1;
  for (auto& step : steps) {
    raw.push_back(step.raw);
    labels.push_back(step.label);
    chain.raw[step.label] = std::move(step.raw);
    chain.heights[step.label] = height;
  }
  auto block = v10::execute_block(chain.ledger, timestamp_of_height(height), raw,
                                  signatures.verifier());
  pv::require(block.has_value(),
              "every recorded block must execute, at height " +
                  std::to_string(height));
  // Every step is offered to be executed, so a label pairs with an executed
  // transaction only if every one was admitted.
  pv::require(block->executed.size() == labels.size(),
              "every recorded step is admitted, at height " +
                  std::to_string(height));
  chain.blocks.push_back(std::move(*block));
  chain.labels.push_back(std::move(labels));
}

// Run the quiet stretch to `target`, with both machines answering through one
// responder because `run_quiet_heights` takes one: Alice's first, then Bob's.
void quiet(Chain& chain, Signatures& signatures, std::uint64_t target) {
  const Builder build(signatures, chain.ledger);
  const auto answer = [&](ResponderLog& log, const Person& who,
                          std::uint32_t seat_id, bool silent, std::uint64_t height,
                          std::span<const std::uint32_t> issued) {
    std::vector<Bytes> inputs;
    if (std::find(issued.begin(), issued.end(), seat_id) == issued.end()) {
      return inputs;
    }
    log.challenged.push_back(height);
    if (silent) return inputs;
    if (height == target) {
      log.left_at_a_stop.push_back(height);
      return inputs;
    }
    log.answered.push_back(height);
    inputs.push_back(build.response(who, seat_id, height,
                                    nonce_of(chain.ledger, who.escrow()) + 1));
    return inputs;
  };
  const auto respond = [&](std::uint64_t height,
                           std::span<const std::uint32_t> issued) {
    auto inputs = answer(chain.alice, kAlice, kAliceSeat, false, height, issued);
    auto from_bob = answer(chain.bob, kBob, kBobSeat, true, height, issued);
    inputs.insert(inputs.end(), from_bob.begin(), from_bob.end());
    return inputs;
  };
  auto quiet_run = v10::run_quiet_heights(
      chain.ledger, target, [](std::uint64_t height) { return timestamp_of_height(height); },
      signatures.verifier(), respond);
  pv::require(quiet_run.has_value(), "the quiet run must complete");
  for (auto& block : quiet_run->recorded) chain.audit_blocks.push_back(std::move(block));
}

void launch(Chain& chain, Signatures& signatures) {
  const Builder build(signatures, chain.ledger);
  const auto h = chain.ledger.height + 1;
  const auto carol = person(1);
  // Someone who presents Alice's signer key as their own first signer.
  const Person mallory{person(8).identity, person(8).hub_key, kAlice.signer_key};
  run(chain, signatures, {
      {"launch.alice_registers",
       build.registration(kAlice, v10::kLaunchAttester, kLaunchKey, h + kLifetime)},
      {"lifetime.kind_10_past_the_bound",
       build.registration(kAlice, v10::kLaunchAttester, kBuildAuthorityKey,
                          h + kLifetime + 1)},
      {"launch.a_registration_the_launch_key_did_not_sign",
       build.registration(carol, v10::kLaunchAttester, kBuildAuthorityKey,
                          h + kLifetime)},
      {"kind_10.a_seat_with_no_machine_key",
       build.registration(carol, kAliceSeat, machine_key(kAliceSeat), h + kLifetime)},
      {"kind_10.a_seat_above_the_range",
       build.registration(carol, v10::kMaxSeatId + 1, machine_key(0), h + kLifetime)},
      {"launch.bob_registers",
       build.registration(kBob, v10::kLaunchAttester, kLaunchKey, h + kLifetime)},
      {"kind_10.an_identity_registered_twice",
       build.registration(kAlice, v10::kLaunchAttester, kBuildAuthorityKey,
                          h + kLifetime)},
      {"kind_10.a_first_signer_already_assigned",
       build.registration(mallory, v10::kLaunchAttester, kBuildAuthorityKey,
                          h + kLifetime)},
  });
}

void seats(Chain& chain, Signatures& signatures, std::string_view purchase_label) {
  const Builder build(signatures, chain.ledger);
  auto h = chain.ledger.height + 1;
  run(chain, signatures, {
      {"approval.kind_2", build.purchase(kAlice, kAliceSeat, 1, h + kLifetime)},
      {"approval.a_version_nine_approval_is_refused",
       build.version_nine_purchase(kBob, kBobSeat, 1, h + kLifetime, purchase_label)},
      {"lifetime.kind_2_past_the_bound",
       build.purchase(kBob, kBobSeat, 1, h + kLifetime + 1, &kAlice)},
      {"seats.bob_buys_a_seat_alice_referred",
       build.purchase(kBob, kBobSeat, 1, h + kLifetime, &kAlice)},
      {"seats.bob_buys_a_seat_he_never_activates",
       build.purchase(kBob, kBobIdleSeat, 2, h + kLifetime)},
  });
  // The shorthand, used once and only before any activation, which is the only
  // stretch of a chain where a block with no transactions changes height and
  // nothing else. No window boundary lies inside it.
  chain.skipped_blocks = kActivationHeight - 1 - chain.ledger.height;
  chain.ledger.height = kActivationHeight - 1;
  chain.ledger.timestamp = timestamp_of_height(kActivationHeight - 1);
  h = chain.ledger.height + 1;
  run(chain, signatures, {
      {"approval.kind_3", build.activation(kAlice, kAliceSeat, 2, h + kLifetime)},
      {"seats.bob_activates", build.activation(kBob, kBobSeat, 3, h + kLifetime)},
  });
}

// Kind 23's seven conditions, each case failing every later one as well.
// Alice's key is registered first, so a refusal can present a key a seat
// already holds. Every refusal before the attestation condition also carries a
// held key, an attestation the build authority did not sign, and no approval,
// so a kernel that checked a later condition earlier would answer differently.
void machine_keys(Chain& chain, Signatures& signatures) {
  const Builder build(signatures, chain.ledger);
  const auto v = chain.ledger.height + 1 + kLifetime;
  const auto alice_key = machine_key(kAliceSeat);
  const auto bob_key = machine_key(kBobSeat);
  const auto failing = [&](const Person& who, std::uint32_t seat_id,
                           const Octets32& key, std::uint64_t nonce) {
    return build.machine_registration(who, seat_id, key, nonce, v, kLaunchKey,
                                      std::nullopt, false);
  };
  run(chain, signatures, {
      {"approval.kind_23",
       build.machine_registration(kAlice, kAliceSeat, alice_key, 3, v)},
      {"kind_23.a_seat_above_the_range",
       failing(kAlice, v10::kMaxSeatId + 1, alice_key, 4)},
      {"kind_23.an_unpurchased_seat", failing(kAlice, 5, alice_key, 4)},
      {"kind_23.an_unactivated_seat", failing(kAlice, kBobIdleSeat, alice_key, 4)},
      {"kind_23.another_identitys_seat", failing(kAlice, kBobSeat, alice_key, 4)},
      {"kind_23.a_key_another_seat_holds", failing(kBob, kBobSeat, alice_key, 4)},
      {"kind_23.a_key_this_seat_holds", failing(kAlice, kAliceSeat, alice_key, 4)},
      {"kind_23.an_attestation_the_build_authority_did_not_sign",
       failing(kBob, kBobSeat, bob_key, 4)},
      {"kind_23.no_approval",
       build.machine_registration(kBob, kBobSeat, bob_key, 4, v, kBuildAuthorityKey,
                                  std::nullopt, false)},
      {"kind_23.another_persons_approval",
       build.machine_registration(kBob, kBobSeat, bob_key, 4, v, kBuildAuthorityKey,
                                  kAlice.hub_key)},
      {"kind_23.bob_registers_his_machine",
       build.machine_registration(kBob, kBobSeat, bob_key, 4, v)},
  });
}

// Version nine's two executed replays, each refused in both forms.
void replays(Chain& chain, Signatures& signatures) {
  const Builder build(signatures, chain.ledger);
  auto h = chain.ledger.height + 1;
  // Built before the block's list, as the model builds them.
  const auto relax = build.posture(kAlice, 4, false, h + kLifetime, true);
  const auto confirm = build.confirmed_transfer(kAlice, kBob, 2'000, 6, h + kLifetime);
  run(chain, signatures, {
      {"approval.kind_17", relax},
      {"lifetime.a_transfer_with_no_proof_is_not_governed",
       build.transfer(kAlice, kBob, 1'000, 5)},
      {"approval.kind_19", confirm},
      {"lifetime.a_tightening_with_no_proof_is_not_governed",
       build.posture(kAlice, 7, true, kFar, false)},
  });
  run(chain, signatures, {
      {"replay.the_republished_relax", relax},
      {"replay.the_relax_resigned_under_a_new_nonce", build.reused(relax, 8)},
      {"replay.the_reused_confirmation", confirm},
      {"replay.the_confirmation_resigned_under_a_new_nonce",
       build.reused(confirm, 8)},
  });
  h = chain.ledger.height + 1;
  const auto added = person(99).signer_key;
  run(chain, signatures, {
      {"lifetime.kind_15_past_the_bound",
       build.signer_add(kAlice, added, 8, h + kLifetime + 1)},
      {"lifetime.kind_15_at_the_bound", build.signer_add(kAlice, added, 8, h + kLifetime)},
  });
}

void machines_register(Chain& chain, Signatures& signatures) {
  const Builder build(signatures, chain.ledger);
  const auto v = chain.ledger.height + 1 + kLifetime;
  const auto carol = person(1);
  const auto dave = person(2);
  const auto erin = person(3);
  run(chain, signatures, {
      {"kind_10.an_active_machine_registers",
       build.registration(carol, kAliceSeat, machine_key(kAliceSeat), v)},
      {"kind_10.an_inactive_machine",
       build.registration(dave, kBobSeat, machine_key(kAliceSeat), v)},
      {"kind_10.a_seat_with_no_machine_key_later",
       build.registration(dave, kBobIdleSeat, machine_key(kBobIdleSeat), v)},
      {"kind_10.another_machines_signature_under_this_seat",
       build.registration(dave, kAliceSeat, machine_key(kBobSeat), v)},
      {"launch.still_signs_below_the_cutoff",
       build.registration(erin, v10::kLaunchAttester, kLaunchKey, v)},
  });
}

void next_window(Chain& chain, Signatures& signatures) {
  const Builder build(signatures, chain.ledger);
  const auto v = chain.ledger.height + 1 + kLifetime;
  const auto n = nonce_of(chain.ledger, kAlice.escrow());
  const auto old_key = machine_key(kAliceSeat);
  const auto new_key = machine_key(kAliceSeat, 1);
  const auto& settled = chain.audit_blocks.back().settled;
  pv::require(settled.has_value() && !settled->winners.empty(),
              "the second assignment closes a month with a winner");
  const auto winner = settled->winners.front();
  const auto frank = person(4);
  const auto grace = person(5);
  run(chain, signatures, {
      {"kind_10.the_count_restarts_in_the_next_window",
       build.registration(frank, kAliceSeat, old_key, v)},
      {"kind_23.the_replacement",
       build.machine_registration(kAlice, kAliceSeat, new_key, n + 1, v)},
      {"kind_10.the_replaced_key_signs_nothing",
       build.registration(grace, kAliceSeat, old_key, v)},
      {"kind_10.the_new_key_signs", build.registration(grace, kAliceSeat, new_key, v)},
      {"approval.kind_4", build.mint(kAlice, Kind::mint_node, n + 2, v, kAliceSeat)},
      {"approval.kind_5", build.mint(kAlice, Kind::mint_referral, n + 3, v)},
      {"approval.kind_18", build.mint(kAlice, Kind::mint_verified_user, n + 4, v)},
      {"approval.kind_22", build.mint(kAlice, Kind::mint_monthly_pool, n + 5, v, winner)},
  });
}

}  // namespace

v10::Genesis trace_genesis() {
  // No allocation, no accounts, a nonzero fee, and three distinct keys.
  v10::Genesis genesis;
  genesis.network_id = kNetworkId;
  genesis.genesis_timestamp = kGenesisMillis;
  genesis.supply_limit = kSupplyLimit;
  genesis.fixed_transfer_fee = kFixedFee;
  genesis.manifest_digest = from_hex(std::string(kManifestDigestHex));
  genesis.launch_key = kLaunchKey;
  genesis.dispute_authority_key = kDisputeAuthorityKey;
  genesis.build_authority_key = kBuildAuthorityKey;
  return genesis;
}

v10::Ledger open_trace_ledger() {
  auto ledger = v10::open_ledger(trace_genesis());
  pv::require(ledger.has_value(), "the trace genesis must open a ledger");
  return *ledger;
}

std::string result_name(v10::Result result) {
  const auto name = v10::result_code_name(static_cast<std::uint8_t>(result));
  pv::require(name.has_value(), "every result code has a name");
  return std::string(*name);
}

// --- the builders -----------------------------------------------------------

v10::Envelope Builder::transaction(Kind kind, const Octets32& authority,
                                   std::uint64_t nonce, const v10::Body& body,
                                   std::uint64_t valid_until) const {
  v10::Envelope envelope;
  envelope.kind = kind_byte(kind);
  envelope.chain_id = ledger_->chain_id;
  const auto scheme = v10::kind_scheme(envelope.kind);
  pv::require(scheme.has_value(), "every built kind permits a scheme");
  envelope.scheme = *scheme;
  envelope.authority_public_key = authority;
  envelope.nonce = nonce;
  envelope.body = v10::encode_body(envelope.kind, body);
  pv::require(!envelope.body.empty(), "a built body must encode");
  // The two fee-exempt kinds carry a zero fee limit: a registration has no
  // escrow to charge, and a challenge response is free on the founder answer of
  // 2026-09-02.
  const bool exempt = kind == Kind::hub_register || kind == Kind::challenge_response;
  envelope.fee_limit = exempt ? 0 : kFixedFee;
  envelope.valid_until_height = valid_until;
  return envelope;
}

Bytes Builder::sign(const v10::Envelope& envelope) const {
  const auto signature = signatures_->sign(
      envelope.authority_public_key,
      v10::signing_message(v10::encode_unsigned(envelope)));
  return v10::encode_signed(envelope, signature);
}

v10::Envelope Builder::approve(v10::Envelope draft, const Octets32& hub_key) const {
  auto body = v10::decode_body(draft.kind, draft.body);
  pv::require(body.has_value(), "a drafted body decodes");
  body->hub_signature = kNoSignature;
  draft.body = v10::encode_body(draft.kind, *body);
  const auto message = v10::approval_message(draft);
  pv::require(message.has_value(), "an approval kind has an approval message");
  body->hub_signature = signatures_->sign(hub_key, *message);
  draft.body = v10::encode_body(draft.kind, *body);
  return draft;
}

Bytes Builder::approved(const Person& who, Kind kind, std::uint64_t nonce,
                        v10::Body body, std::uint64_t valid_until,
                        const std::optional<Octets32>& hub_key) const {
  body.hub_signature = kNoSignature;
  const auto draft = transaction(kind, who.signer_key, nonce, body, valid_until);
  return sign(approve(draft, hub_key.value_or(who.hub_key)));
}

Bytes Builder::registration(const Person& who, std::uint32_t attester_seat,
                            const Octets32& attester_key, std::uint64_t valid_until,
                            std::optional<std::uint32_t> signed_seat) const {
  const auto message = v10::registration_message(
      ledger_->chain_id, signed_seat.value_or(attester_seat), who.identity,
      who.hub_key, who.signer_key, valid_until);
  v10::Body body;
  body.hub_identity_hash = who.identity;
  body.first_signer_public_key = who.signer_key;
  body.attesting_seat_id = attester_seat;
  body.attestation_signature = signatures_->sign(attester_key, message);
  return sign(transaction(Kind::hub_register, who.hub_key, 0, body, valid_until));
}

Bytes Builder::purchase(const Person& who, std::uint32_t seat_id,
                        std::uint64_t nonce, std::uint64_t valid_until,
                        const Person* referrer) const {
  v10::Body body;
  body.seat_id = seat_id;
  body.has_referrer = referrer != nullptr;
  if (referrer != nullptr) body.referrer_escrow_id = referrer->escrow();
  return approved(who, Kind::purchase_seat, nonce, body, valid_until);
}

Bytes Builder::version_nine_purchase(const Person& who, std::uint32_t seat_id,
                                     std::uint64_t nonce, std::uint64_t valid_until,
                                     std::string_view purchase_label) const {
  // `D(label) || chain_id || identity || u32(seat_id) || u64(valid_until)`,
  // version six's purchase message, which version nine carried unchanged.
  auto message = pv::domain(purchase_label);
  message.insert(message.end(), ledger_->chain_id.begin(), ledger_->chain_id.end());
  message.insert(message.end(), who.identity.begin(), who.identity.end());
  for (int shift = 24; shift >= 0; shift -= 8) {
    message.push_back(static_cast<std::uint8_t>(seat_id >> shift));
  }
  pv::append_u64(message, valid_until);
  v10::Body body;
  body.seat_id = seat_id;
  body.has_referrer = false;
  body.hub_signature = signatures_->sign(who.hub_key, message);
  return sign(transaction(Kind::purchase_seat, who.signer_key, nonce, body,
                          valid_until));
}

Bytes Builder::activation(const Person& who, std::uint32_t seat_id,
                          std::uint64_t nonce, std::uint64_t valid_until) const {
  v10::Body body;
  body.seat_id = seat_id;
  return approved(who, Kind::activate_seat, nonce, body, valid_until);
}

Bytes Builder::machine_registration(const Person& who, std::uint32_t seat_id,
                                    const Octets32& key, std::uint64_t nonce,
                                    std::uint64_t valid_until,
                                    const Octets32& attester,
                                    const std::optional<Octets32>& hub_key,
                                    bool approve_it) const {
  const auto attestation = v10::attestation_message(ledger_->chain_id, seat_id, key,
                                                    kBuildDigest, valid_until);
  v10::Body body;
  body.seat_id = seat_id;
  body.machine_public_key = key;
  body.build_digest = kBuildDigest;
  body.attestation_signature = signatures_->sign(attester, attestation);
  body.hub_signature = kNoSignature;
  auto draft = transaction(Kind::register_machine_key, who.signer_key, nonce, body,
                           valid_until);
  if (approve_it) draft = approve(draft, hub_key.value_or(who.hub_key));
  return sign(draft);
}

Bytes Builder::posture(const Person& who, std::uint64_t nonce,
                       bool requires_confirmation, std::uint64_t valid_until,
                       bool approve_it) const {
  // The default minimum and exempt mask are both zero, so only the switch moves.
  v10::Body body;
  body.requires_confirmation = requires_confirmation;
  body.min_amount_atomic = 0;
  body.exempt_slot_mask = 0;
  body.hub_signature = kNoSignature;
  const auto draft = transaction(Kind::set_security_posture, who.signer_key, nonce,
                                 body, valid_until);
  return sign(approve_it ? approve(draft, who.hub_key) : draft);
}

Bytes Builder::transfer(const Person& who, const Person& recipient,
                        std::uint64_t amount, std::uint64_t nonce) const {
  v10::Body body;
  body.recipient_escrow_id = recipient.escrow();
  body.amount_atomic = amount;
  return sign(transaction(Kind::native_transfer, who.signer_key, nonce, body, kFar));
}

Bytes Builder::confirmed_transfer(const Person& who, const Person& recipient,
                                  std::uint64_t amount, std::uint64_t nonce,
                                  std::uint64_t valid_until) const {
  v10::Body body;
  body.recipient_escrow_id = recipient.escrow();
  body.amount_atomic = amount;
  return approved(who, Kind::native_transfer_verified, nonce, body, valid_until);
}

Bytes Builder::signer_add(const Person& who, const Octets32& signer_key,
                          std::uint64_t nonce, std::uint64_t valid_until) const {
  // Signed whole by the HUB key, so always governed by the lifetime.
  v10::Body body;
  body.hub_identity_hash = who.identity;
  body.escrow_id = who.escrow();
  body.signer_public_key = signer_key;
  return sign(transaction(Kind::signer_add, who.hub_key, nonce, body, valid_until));
}

Bytes Builder::mint(const Person& who, Kind kind, std::uint64_t nonce,
                    std::uint64_t valid_until,
                    std::optional<std::uint32_t> seat_id) const {
  v10::Body body;
  body.destination_escrow_id = who.escrow();
  if (seat_id) body.seat_id = *seat_id;
  return approved(who, kind, nonce, body, valid_until);
}

Bytes Builder::response(const Person& who, std::uint32_t seat_id,
                        std::uint64_t challenge_height, std::uint64_t nonce) const {
  v10::Body body;
  body.seat_id = seat_id;
  body.challenge_height = challenge_height;
  body.answer = Bytes(v10::kAnswerBytes, 0);
  return sign(transaction(Kind::challenge_response, who.signer_key, nonce, body, kFar));
}

Bytes Builder::reused(const Bytes& raw, std::uint64_t nonce) const {
  auto decoded = v10::decode_signed(raw);
  pv::require(decoded.has_value(), "a recorded transaction decodes");
  decoded->envelope.nonce = nonce;
  return sign(decoded->envelope);
}

// --- the chain --------------------------------------------------------------

std::map<std::string, v10::ExecutedTransaction> Chain::executed() const {
  std::map<std::string, v10::ExecutedTransaction> recorded;
  for (std::size_t block = 0; block < blocks.size(); ++block) {
    for (std::size_t index = 0; index < labels[block].size(); ++index) {
      recorded[labels[block][index]] = blocks[block].executed[index];
    }
  }
  return recorded;
}

Chain chain_scenario(Signatures& signatures, std::string_view purchase_label) {
  Chain chain;
  chain.ledger = open_trace_ledger();
  launch(chain, signatures);
  seats(chain, signatures, purchase_label);
  machine_keys(chain, signatures);
  replays(chain, signatures);

  quiet(chain, signatures, kFirstAssignmentHeight);
  chain.first_assignment = chain.audit_blocks.back();
  for (const auto& [seat_id, entry] : chain.ledger.machine_keys) {
    chain.marks_after_the_first_assignment[seat_id] = entry.last_met_window;
  }
  machines_register(chain, signatures);
  quiet(chain, signatures, kSecondAssignmentHeight);
  chain.second_assignment = chain.audit_blocks.back();
  next_window(chain, signatures);
  return chain;
}

}  // namespace economy_v10_execution
