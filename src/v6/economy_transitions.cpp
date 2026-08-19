// The six administrative transitions and the dispatch that reaches them.
//
// Every one of the six requires no signer at all, and each is a recovery path:
// register, create an escrow, delete one, assign a signer, revoke a signer, and
// set a posture are exactly the transactions a person must be able to make
// holding no key. The HUB signature is the authority and a named escrow pays, so
// nothing here needs a helper, a third party, or an external funding step.
//
// Each transition validates completely before it writes, so a refusal leaves the
// state untouched without a rollback — and `execute_block` requires that, by
// re-deriving the state root across every failure.

#include "economy_ledger_internal.hpp"

namespace protocol::v6::internal {
namespace {

Outcome refused(Result result) { return Outcome{result, 0, 0}; }

Posture proposed_posture(const Body& body) {
  Posture posture;
  posture.requires_confirmation = body.requires_confirmation;
  posture.min_amount_atomic = body.min_amount_atomic;
  posture.exempt_slot_mask = body.exempt_slot_mask;
  return posture;
}

// Kind 10. One transaction that creates a whole participant, atomically.
//
// It is fee-exempt, and the exemption is deliberate rather than the smaller of
// two equal options: the entry airdrop is bounded at 1,000,000 identities, so a
// credit-then-charge rule would refuse user 1,000,001 with
// `INSUFFICIENT_BALANCE` and close the ecosystem at exactly the point the
// bootstrap problem was supposed to stop recurring. Exemption works forever, and
// its anti-abuse bound is non-monetary and already present, because only the
// ecosystem verifier can sign a registration.
std::optional<Outcome> hub_register(Ledger& ledger, const Envelope& envelope,
                                    const Body& body,
                                    const SignatureVerifier& verify) {
  if (envelope.valid_until_height < ledger.height) return refused(Result::expired);
  if (ledger.registry.identities.contains(body.hub_identity_hash)) {
    return refused(Result::replay);
  }
  const auto first_signer = signer_id(body.first_signer_public_key);
  if (ledger.registry.signers.contains(first_signer)) return refused(Result::replay);

  const auto message = registration_message(
      ledger.chain_id, body.hub_identity_hash, envelope.authority_public_key,
      body.first_signer_public_key, envelope.valid_until_height);
  if (!verify(ledger.verifier_key, message, body.verifier_signature)) {
    return refused(Result::unauthorized);
  }

  const bool enrolling = ledger.registry.enrolled_count < kVerifiedUserPopulation;
  const std::uint64_t airdrop = enrolling ? kVerifiedUserDailyAtomic : 0;
  if (airdrop != 0 && !fits_channel(ledger, kVerifiedUserChannel, airdrop)) {
    return refused(Result::channel_cap);
  }

  const auto first_escrow = escrow_id(body.hub_identity_hash, 0);
  HubIdentityRecord identity;
  identity.hub_public_key = envelope.authority_public_key;
  identity.registered_at_height = ledger.height;
  ledger.registry.identities[body.hub_identity_hash] = identity;
  EscrowRecord escrow;
  escrow.owner_hub_identity = body.hub_identity_hash;
  escrow.signer_count = 1;
  ledger.registry.escrows[first_escrow] = escrow;
  ledger.registry.signers[first_signer] = first_escrow;
  ledger.registry.accounts[first_escrow] = Account{0, 0};
  if (enrolling) {
    EnrollmentRecord enrollment;
    enrollment.enrolled_at_height = ledger.height;
    enrollment.minted_through_window = window_of_height(ledger.height);
    enrollment.issued_atomic = airdrop;
    ledger.registry.enrollments[body.hub_identity_hash] = enrollment;
    ledger.registry.enrolled_count += 1;
    if (!issue(ledger, kVerifiedUserChannel, airdrop)) return std::nullopt;
    if (!credit(ledger, first_escrow, airdrop)) return std::nullopt;
  }
  return Outcome{Result::success, airdrop, 0};
}

// Kind 13. The identity is the admin, so no signer is involved.
std::optional<Outcome> escrow_create(Ledger& ledger, const Body& body,
                                     const Octets32& escrow) {
  auto& identity = ledger.registry.identities[body.hub_identity_hash];
  const auto created = escrow_id(body.hub_identity_hash, identity.next_escrow_index);
  EscrowRecord record;
  record.owner_hub_identity = body.hub_identity_hash;
  ledger.registry.escrows[created] = record;
  ledger.registry.accounts[created] = Account{0, 0};
  identity.next_escrow_index += 1;
  identity.escrow_count += 1;
  return charged(ledger, escrow);
}

// Kind 14. A deleted escrow must be empty, and its index is never reused.
//
// The fee escrow is named separately because an escrow with a zero balance
// cannot pay for its own deletion, so a target equal to the fee escrow is
// refused rather than special-cased.
std::optional<Outcome> escrow_delete(Ledger& ledger, const Body& body,
                                     const Octets32& escrow) {
  const auto target = ledger.registry.escrows.find(body.target_escrow_id);
  if (target == ledger.registry.escrows.end()) {
    return refused(Result::escrow_not_found);
  }
  if (target->second.owner_hub_identity != body.hub_identity_hash) {
    return refused(Result::escrow_not_owned);
  }
  if (body.target_escrow_id == escrow) return refused(Result::escrow_not_empty);
  if (balance_of(ledger, body.target_escrow_id) != 0) {
    return refused(Result::escrow_not_empty);
  }

  std::erase_if(ledger.registry.signers, [&body](const auto& entry) {
    return entry.second == body.target_escrow_id;
  });
  ledger.registry.escrows.erase(target);
  ledger.registry.accounts.erase(body.target_escrow_id);
  ledger.registry.identities[body.hub_identity_hash].escrow_count -= 1;
  return charged(ledger, escrow);
}

// Kind 15, and the recovery path — the ordinary transaction, not a special one.
// A person who has lost every signer proves their identity with their HUB key,
// names an escrow that already holds value, and assigns a fresh signer to it.
std::optional<Outcome> signer_add(Ledger& ledger, const Body& body,
                                  const Octets32& escrow) {
  const auto identifier = signer_id(body.signer_public_key);
  if (ledger.registry.signers.contains(identifier)) return refused(Result::replay);
  auto& record = ledger.registry.escrows[escrow];
  if (record.signer_count >= kMaxSignersPerEscrow) {
    return refused(Result::signer_limit);
  }
  ledger.registry.signers[identifier] = escrow;
  record.signer_count += 1;
  return charged(ledger, escrow);
}

// Kind 16. Immediate and total: a revoked key authorizes nothing from here.
std::optional<Outcome> signer_revoke(Ledger& ledger, const Body& body,
                                     const Octets32& escrow) {
  const auto assigned = ledger.registry.signers.find(body.signer_id);
  if (assigned == ledger.registry.signers.end()) {
    return refused(Result::signer_not_found);
  }
  if (assigned->second != escrow) return refused(Result::unauthorized);
  ledger.registry.signers.erase(assigned);
  ledger.registry.escrows[escrow].signer_count -= 1;
  return charged(ledger, escrow);
}

// Kind 17. The direction of the change decides what must have authorized it.
// A change that tightens one field and relaxes another counts as a relaxation,
// because each disjunct is one way to shrink the set of operations needing a
// proof and the failure that matters is a stolen key weakening a protection.
std::optional<Outcome> set_security_posture(Ledger& ledger,
                                            const Envelope& envelope,
                                            const Body& body,
                                            const Octets32& escrow,
                                            const SignatureVerifier& verify) {
  const auto proposed = proposed_posture(body);
  auto& record = ledger.registry.escrows[escrow];
  if (record.posture == proposed) return refused(Result::replay);
  if (relaxes(record.posture, proposed)) {
    const auto message = posture_relax_message(
        ledger.chain_id, record.owner_hub_identity, escrow, proposed,
        envelope.valid_until_height);
    if (!verify_hub_signature(ledger, record.owner_hub_identity, message,
                              body.hub_signature, verify)) {
      return refused(Result::unauthorized);
    }
  } else if (!confirmation_field_is_absent(body.hub_signature)) {
    return refused(Result::unauthorized);
  }
  record.posture = proposed;
  return charged(ledger, escrow);
}

}  // namespace

std::optional<Outcome> dispatch(Ledger& ledger, const Envelope& envelope,
                                const Body& body, const Octets32* escrow,
                                const SignatureVerifier& verify) {
  switch (static_cast<Kind>(envelope.kind)) {
    case Kind::hub_register:
      return hub_register(ledger, envelope, body, verify);
    case Kind::escrow_create:
      return escrow_create(ledger, body, *escrow);
    case Kind::escrow_delete:
      return escrow_delete(ledger, body, *escrow);
    case Kind::signer_add:
      return signer_add(ledger, body, *escrow);
    case Kind::signer_revoke:
      return signer_revoke(ledger, body, *escrow);
    case Kind::set_security_posture:
      return set_security_posture(ledger, envelope, body, *escrow, verify);
    case Kind::native_transfer:
    case Kind::native_transfer_verified:
    case Kind::mint_verified_user:
    case Kind::direct_issue:
      return dispatch_value(ledger, envelope, body, *escrow, verify);
    case Kind::purchase_seat:
    case Kind::activate_seat:
    case Kind::mint_node:
    case Kind::mint_referral:
      // The four seat transitions read or write a cycle assignment, which this
      // kernel does not yet derive. An implementation that cannot execute a
      // transaction has no result to report, so it fails the whole block rather
      // than inventing one — the loud failure rather than the silent refusal.
      return std::nullopt;
  }
  return std::nullopt;
}

}  // namespace protocol::v6::internal
