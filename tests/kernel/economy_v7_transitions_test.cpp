// The rejection conditions the recorded trace never reaches.
//
// The six scenarios in `economy-transition-v6-execution.txt` exercise ten kinds
// but not every condition of each, and three kinds — escrow create, escrow
// delete, and direct issue — appear in no scenario at all. A mutation probe
// found this the honest way: making `signer_revoke` accept a signer assigned to
// a *different* escrow changed nothing any recorded vector observes, so that
// refusal had no evidence behind it.
//
// These checks derive their own expectations rather than comparing against a
// vector file, because there is no recorded vector to compare against. That is
// the opposite of the rule the scenario checks follow, and it is the reason this
// file is separate from them: a reader must never have to wonder which kind of
// evidence a given assertion carries.

#include "economy_v7_execution_fixture.hpp"

namespace economy_v7_execution {
namespace {

constexpr std::uint64_t kFunded = 10'000'000;

// A ledger holding two registered identities, each with one funded escrow and
// one signer, built by hand rather than by executing registrations: these checks
// are about the administrative kinds and should not fail because registration
// changed.
struct Fixture {
  v7::Ledger ledger;
  Octets32 alice_escrow{};
  Octets32 bob_escrow{};
};

void install(v7::Ledger& ledger, const Octets32& identity, const Octets32& hub_key,
             const Octets32& signer_key, const Octets32& escrow,
             std::uint64_t balance) {
  v7::HubIdentityRecord record;
  record.hub_public_key = hub_key;
  ledger.registry.identities[identity] = record;
  v7::EscrowRecord entry;
  entry.owner_hub_identity = identity;
  entry.signer_count = 1;
  ledger.registry.escrows[escrow] = entry;
  ledger.registry.signers[v7::signer_id(signer_key)] = escrow;
  ledger.registry.accounts[escrow] = v7::Account{balance, 0};
  ledger.total_supply += balance;
}

Fixture open() {
  Fixture fixture;
  fixture.ledger.supply_limit = kSupplyLimit;
  fixture.ledger.fixed_fee = kFixedFee;
  fixture.alice_escrow = v7::escrow_id(kAliceIdentity, 0);
  fixture.bob_escrow = v7::escrow_id(kBobIdentity, 0);
  install(fixture.ledger, kAliceIdentity, kAliceKey, kAliceSignerKey,
          fixture.alice_escrow, kFunded);
  install(fixture.ledger, kBobIdentity, kBobKey, kBobSignerKey, fixture.bob_escrow,
          kFunded);
  // Built by hand, so the invariants are asserted rather than assumed: a fixture
  // that is not a reachable state would make every result below meaningless.
  pv::require(v7::conservation_failures(fixture.ledger).empty(),
              "the hand-built fixture must be a conserved state");
  return fixture;
}

v7::Envelope envelope_for(std::uint8_t kind, const Octets32& authority,
                          std::uint64_t nonce, const v7::Body& body) {
  v7::Envelope envelope;
  envelope.kind = kind;
  envelope.scheme = *v7::kind_scheme(kind);
  envelope.authority_public_key = authority;
  envelope.nonce = nonce;
  envelope.body = v7::encode_body(kind, body);
  envelope.fee_limit = kFixedFee;
  envelope.valid_until_height = kValidUntil;
  return envelope;
}

// Every check here runs one transaction against a fresh state and names the
// result it expects, so a refusal that stopped happening fails loudly.
void expect(v7::Ledger& ledger, const v7::Envelope& envelope, v7::Result expected,
            const std::string& what) {
  const auto before = v7::ledger_state_root(ledger);
  const auto outcome = v7::execute(ledger, envelope, Signatures{}.verifier());
  pv::require(outcome.has_value(), what + ": expected a result, not a failure");
  const auto actual = v7::result_code_name(static_cast<std::uint8_t>(outcome->result));
  const auto wanted = v7::result_code_name(static_cast<std::uint8_t>(expected));
  pv::require(actual.has_value() && wanted.has_value(), what + ": unknown code");
  pv::require(outcome->result == expected, what + ": derived " +
                                               std::string(*actual) + ", expected " +
                                               std::string(*wanted));
  if (expected != v7::Result::success) {
    // Failed-transition atomicity for every refusal, not only the ones a block
    // happens to contain.
    const auto after = v7::ledger_state_root(ledger);
    pv::require(before && after && *before == *after,
                what + ": a refusal changed the state");
  }
}

v7::Body owned_body(const Octets32& identity, const Octets32& fee_escrow) {
  v7::Body body;
  body.hub_identity_hash = identity;
  body.fee_escrow_id = fee_escrow;
  return body;
}

// Kind 13, and with it the four resolution conditions every scheme-2 kind shares.
void check_escrow_create() {
  const auto kind = static_cast<std::uint8_t>(v7::Kind::escrow_create);
  {
    auto fixture = open();
    const auto body = owned_body(kAliceIdentity, fixture.alice_escrow);
    expect(fixture.ledger, envelope_for(kind, kAliceKey, 1, body),
           v7::Result::success, "escrow_create succeeds");
    const auto created = v7::escrow_id(kAliceIdentity, 1);
    const auto& identity = fixture.ledger.registry.identities.at(kAliceIdentity);
    pv::require(fixture.ledger.registry.escrows.contains(created),
                "escrow_create writes the escrow at the next index");
    pv::require(fixture.ledger.registry.accounts.at(created).balance == 0 &&
                    fixture.ledger.registry.accounts.at(created).nonce == 0,
                "escrow_create writes an empty account entry");
    pv::require(identity.next_escrow_index == 2 && identity.escrow_count == 2,
                "escrow_create advances the index and the live count");
    pv::require(fixture.ledger.registry.escrows.at(created).signer_count == 0,
                "a created escrow holds no signer");
    pv::require(v7::conservation_failures(fixture.ledger).empty(),
                "escrow_create leaves a conserved state");
  }
  {
    auto fixture = open();
    auto body = owned_body(kCarolIdentity, fixture.alice_escrow);
    expect(fixture.ledger, envelope_for(kind, kCarolKey, 1, body),
           v7::Result::not_hub_verified, "an unregistered identity");
  }
  {
    auto fixture = open();
    const auto body = owned_body(kAliceIdentity, fixture.alice_escrow);
    // The header key is a registered identity's, but not this one's.
    expect(fixture.ledger, envelope_for(kind, kBobKey, 1, body),
           v7::Result::unauthorized, "a header key that is not the identity's");
  }
  {
    auto fixture = open();
    const auto body = owned_body(kAliceIdentity, v7::escrow_id(kAliceIdentity, 7));
    expect(fixture.ledger, envelope_for(kind, kAliceKey, 1, body),
           v7::Result::escrow_not_found, "a fee escrow that does not exist");
  }
  {
    auto fixture = open();
    const auto body = owned_body(kAliceIdentity, fixture.bob_escrow);
    expect(fixture.ledger, envelope_for(kind, kAliceKey, 1, body),
           v7::Result::escrow_not_owned, "a fee escrow owned by another identity");
  }
}

// Kind 14, including the two conditions that share one code for different reasons.
void check_escrow_delete() {
  const auto kind = static_cast<std::uint8_t>(v7::Kind::escrow_delete);
  const auto build = [](const Octets32& identity, const Octets32& target,
                        const Octets32& fee) {
    v7::Body body;
    body.hub_identity_hash = identity;
    body.target_escrow_id = target;
    body.fee_escrow_id = fee;
    return body;
  };
  {
    auto fixture = open();
    // A second, empty escrow with a signer on it, so deletion is observed to
    // remove the signer entry as well as the escrow and the account.
    const auto target = v7::escrow_id(kAliceIdentity, 1);
    v7::EscrowRecord entry;
    entry.owner_hub_identity = kAliceIdentity;
    entry.signer_count = 1;
    fixture.ledger.registry.escrows[target] = entry;
    fixture.ledger.registry.accounts[target] = v7::Account{0, 0};
    const auto orphan = v7::signer_id(kAliceSecondSignerKey);
    fixture.ledger.registry.signers[orphan] = target;
    auto& identity = fixture.ledger.registry.identities.at(kAliceIdentity);
    identity.next_escrow_index = 2;
    identity.escrow_count = 2;
    pv::require(v7::conservation_failures(fixture.ledger).empty(),
                "the two-escrow fixture must be conserved");

    expect(fixture.ledger, envelope_for(kind, kAliceKey, 1,
                                        build(kAliceIdentity, target,
                                              fixture.alice_escrow)),
           v7::Result::success, "escrow_delete succeeds");
    pv::require(!fixture.ledger.registry.escrows.contains(target),
                "escrow_delete removes the escrow entry");
    pv::require(!fixture.ledger.registry.accounts.contains(target),
                "escrow_delete removes the account entry");
    pv::require(!fixture.ledger.registry.signers.contains(orphan),
                "escrow_delete removes every signer naming the target");
    const auto& after = fixture.ledger.registry.identities.at(kAliceIdentity);
    // The index never decreases, so a deleted escrow's identifier is never
    // reissued; only the live count falls.
    pv::require(after.escrow_count == 1 && after.next_escrow_index == 2,
                "escrow_delete lowers the count and not the index");
    pv::require(v7::conservation_failures(fixture.ledger).empty(),
                "escrow_delete leaves a conserved state");
  }
  {
    auto fixture = open();
    expect(fixture.ledger,
           envelope_for(kind, kAliceKey, 1,
                        build(kAliceIdentity, v7::escrow_id(kAliceIdentity, 9),
                              fixture.alice_escrow)),
           v7::Result::escrow_not_found, "a target that does not exist");
  }
  {
    auto fixture = open();
    expect(fixture.ledger,
           envelope_for(kind, kAliceKey, 1,
                        build(kAliceIdentity, fixture.bob_escrow,
                              fixture.alice_escrow)),
           v7::Result::escrow_not_owned, "a target owned by another identity");
  }
  {
    auto fixture = open();
    // The target is the fee escrow. Refused rather than special-cased, because
    // an escrow cannot pay for its own deletion out of a balance it is losing.
    expect(fixture.ledger,
           envelope_for(kind, kAliceKey, 1,
                        build(kAliceIdentity, fixture.alice_escrow,
                              fixture.alice_escrow)),
           v7::Result::escrow_not_empty, "a target equal to the fee escrow");
  }
  {
    auto fixture = open();
    const auto target = v7::escrow_id(kAliceIdentity, 1);
    v7::EscrowRecord entry;
    entry.owner_hub_identity = kAliceIdentity;
    fixture.ledger.registry.escrows[target] = entry;
    fixture.ledger.registry.accounts[target] = v7::Account{1, 0};
    fixture.ledger.total_supply += 1;
    auto& identity = fixture.ledger.registry.identities.at(kAliceIdentity);
    identity.next_escrow_index = 2;
    identity.escrow_count = 2;
    expect(fixture.ledger,
           envelope_for(kind, kAliceKey, 1,
                        build(kAliceIdentity, target, fixture.alice_escrow)),
           v7::Result::escrow_not_empty, "a target holding value");
  }
}

// Kinds 15 and 16. The cross-escrow refusal is the one a probe found unexercised.
void check_signers() {
  const auto add = static_cast<std::uint8_t>(v7::Kind::signer_add);
  const auto revoke = static_cast<std::uint8_t>(v7::Kind::signer_revoke);
  {
    auto fixture = open();
    v7::Body body;
    body.hub_identity_hash = kAliceIdentity;
    body.escrow_id = fixture.alice_escrow;
    body.signer_public_key = kBobSignerKey;
    // Already assigned to Bob's escrow, so a second assignment is a replay
    // rather than a shared key.
    expect(fixture.ledger, envelope_for(add, kAliceKey, 1, body),
           v7::Result::replay, "a signer key already assigned elsewhere");
  }
  {
    auto fixture = open();
    // Fill the escrow to its sixteen-signer limit, then ask for one more.
    auto& entry = fixture.ledger.registry.escrows.at(fixture.alice_escrow);
    for (std::uint32_t index = 1; index < v7::kMaxSignersPerEscrow; ++index) {
      Octets32 key{};
      key.fill(static_cast<std::uint8_t>(0x40 + index));
      fixture.ledger.registry.signers[v7::signer_id(key)] = fixture.alice_escrow;
      entry.signer_count += 1;
    }
    pv::require(entry.signer_count == v7::kMaxSignersPerEscrow,
                "the fixture fills the signer limit exactly");
    pv::require(v7::conservation_failures(fixture.ledger).empty(),
                "a full escrow is still a conserved state");
    v7::Body body;
    body.hub_identity_hash = kAliceIdentity;
    body.escrow_id = fixture.alice_escrow;
    body.signer_public_key = kMariaNewSignerKey;
    expect(fixture.ledger, envelope_for(add, kAliceKey, 1, body),
           v7::Result::signer_limit, "a seventeenth signer");
  }
  {
    auto fixture = open();
    v7::Body body;
    body.hub_identity_hash = kAliceIdentity;
    body.escrow_id = fixture.alice_escrow;
    body.signer_id = v7::signer_id(kMariaNewSignerKey);
    expect(fixture.ledger, envelope_for(revoke, kAliceKey, 1, body),
           v7::Result::signer_not_found, "revoking a signer that does not exist");
  }
  {
    auto fixture = open();
    // The condition the probe found unexercised: Alice names Bob's signer on her
    // own escrow. Both exist; the binding between them is what refuses it.
    v7::Body body;
    body.hub_identity_hash = kAliceIdentity;
    body.escrow_id = fixture.alice_escrow;
    body.signer_id = v7::signer_id(kBobSignerKey);
    expect(fixture.ledger, envelope_for(revoke, kAliceKey, 1, body),
           v7::Result::unauthorized, "revoking a signer bound to another escrow");
    pv::require(fixture.ledger.registry.signers.at(v7::signer_id(kBobSignerKey)) ==
                    fixture.bob_escrow,
                "the refused revocation left the signer where it was");
  }
}

// Kind 6, and the six conditions its first one makes unreachable.
void check_direct_issue() {
  const auto kind = static_cast<std::uint8_t>(v7::Kind::direct_issue);
  for (const std::uint8_t channel : {std::uint8_t{5}, std::uint8_t{6},
                                     std::uint8_t{9}, std::uint8_t{0}}) {
    auto fixture = open();
    v7::Body body;
    body.channel_id = channel;
    body.decision_id = kDecisionId;
    body.beneficiary_escrow_id = fixture.alice_escrow;
    body.amount_atomic = 1;
    // Every acting key is refused while the eligibility predicate is
    // founder-reserved, so the channel, amount, decision, beneficiary, and cap
    // conditions are specified and never reached.
    expect(fixture.ledger, envelope_for(kind, kAliceSignerKey, 1, body),
           v7::Result::unauthorized, "direct issue is refused for every key");
  }
}

// The two shared envelope conditions no scenario reaches.
void check_envelope_conditions() {
  const auto kind = static_cast<std::uint8_t>(v7::Kind::native_transfer);
  {
    auto fixture = open();
    v7::Body body;
    body.recipient_escrow_id = fixture.bob_escrow;
    body.amount_atomic = 1;
    auto envelope = envelope_for(kind, kAliceSignerKey, 1, body);
    envelope.fee_limit = kFixedFee - 1;
    expect(fixture.ledger, envelope, v7::Result::fee_limit_too_low,
           "a fee limit below the fixed fee");
  }
  {
    auto fixture = open();
    fixture.ledger.height = 100;
    v7::Body body;
    body.recipient_escrow_id = fixture.bob_escrow;
    body.amount_atomic = 1;
    auto envelope = envelope_for(kind, kAliceSignerKey, 1, body);
    envelope.valid_until_height = 99;
    expect(fixture.ledger, envelope, v7::Result::expired,
           "a valid-until height below the executing height");
  }
  {
    auto fixture = open();
    fixture.ledger.registry.accounts.at(fixture.alice_escrow).nonce = ~std::uint64_t{0};
    v7::Body body;
    body.recipient_escrow_id = fixture.bob_escrow;
    body.amount_atomic = 1;
    expect(fixture.ledger, envelope_for(kind, kAliceSignerKey, 0, body),
           v7::Result::nonce_exhausted, "an exhausted nonce sequence");
  }
  {
    auto fixture = open();
    v7::Body body;
    body.recipient_escrow_id = fixture.bob_escrow;
    body.amount_atomic = 1;
    expect(fixture.ledger, envelope_for(kind, kAliceSignerKey, 5, body),
           v7::Result::nonce_mismatch, "a nonce that is not stored plus one");
  }
  {
    auto fixture = open();
    v7::Body body;
    body.recipient_escrow_id = fixture.bob_escrow;
    body.amount_atomic = 1;
    // A key with no signer entry authorizes nothing. `SENDER_NOT_FOUND` is the
    // neighbouring code and is unreachable, because an escrow that resolves
    // always exists.
    expect(fixture.ledger, envelope_for(kind, kMariaNewSignerKey, 1, body),
           v7::Result::signer_not_found, "a header key with no signer entry");
  }
}

}  // namespace

void verify_transitions() {
  check_escrow_create();
  check_escrow_delete();
  check_signers();
  check_direct_issue();
  check_envelope_conditions();
}

}  // namespace economy_v7_execution
