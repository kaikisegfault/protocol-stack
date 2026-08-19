// The version-six transitions that move or issue value without reading a cycle
// assignment: the two transfers, the verified-user mint, and the refused direct
// issue.
//
// The four seat transitions — purchase, activate, and the two mints whose walk
// reads assignment records — belong to the settlement this kernel does not yet
// derive, and `dispatch` refuses to execute them rather than answering wrongly.

#include "economy_ledger_internal.hpp"

namespace protocol::v6::internal {
namespace {

Outcome refused(Result result) { return Outcome{result, 0, 0}; }

Outcome issued(Outcome outcome, std::uint64_t amount) {
  outcome.issued_atomic = amount;
  return outcome;
}

// A mint names its destination and the chain checks it belongs to the minting
// identity, because a person holds many escrows and none is privileged.
std::optional<Result> require_destination(const Ledger& ledger,
                                          const Octets32& destination,
                                          const Octets32& identity) {
  const auto entry = ledger.registry.escrows.find(destination);
  if (entry == ledger.registry.escrows.end()) return Result::escrow_not_found;
  if (entry->second.owner_hub_identity != identity) return Result::escrow_not_owned;
  return std::nullopt;
}

// The destination's posture applied to the total the mint would credit. The
// total is computed before any write, so a mint that needs a confirmation and
// carries 64 zero octets is refused with nothing written.
std::optional<Result> require_confirmation(const Ledger& ledger,
                                           const Octets32& destination,
                                           std::uint64_t amount,
                                           const Octets32& identity,
                                           const Bytes& message,
                                           const Bytes& field,
                                           const SignatureVerifier& verify) {
  if (confirmation_required(ledger, destination, amount)) {
    if (confirmation_field_is_absent(field)) return Result::biometric_required;
    if (!verify_hub_signature(ledger, identity, message, field, verify)) {
      return Result::unauthorized;
    }
    return std::nullopt;
  }
  // The confirmation field of an operation that requires none must be 64 zero
  // octets, or the same effect has two encodings and two transaction IDs.
  if (!confirmation_field_is_absent(field)) return Result::unauthorized;
  return std::nullopt;
}

const Octets32& owner_of(const Ledger& ledger, const Octets32& escrow) {
  return ledger.registry.escrows.at(escrow).owner_hub_identity;
}

// Kinds 1 and 19. **It never creates an account.**
//
// That is the one execution change to the accepted version-one bytes in five
// contract revisions: a recipient with no escrow entry is refused rather than
// created, which withdraws the last way an account could come into existence
// with no identity behind it.
//
// A self-transfer needs no special case. Version one gives it one because it
// must not credit an account it is about to debit; here the amount cancels when
// the same key is debited and credited, and the envelope check already required
// the balance to cover `amount + fee`.
std::optional<Outcome> native_transfer(Ledger& ledger, const Envelope& envelope,
                                       const Body& body, const Octets32& escrow,
                                       const SignatureVerifier& verify) {
  const auto amount = body.amount_atomic;
  if (amount == 0) return refused(Result::zero_amount);
  if (!ledger.registry.escrows.contains(body.recipient_escrow_id)) {
    return refused(Result::recipient_not_registered);
  }
  const auto identity = owner_of(ledger, escrow);
  if (envelope.kind == static_cast<std::uint8_t>(Kind::native_transfer)) {
    if (confirmation_required(ledger, escrow, amount)) {
      return refused(Result::biometric_required);
    }
  } else {
    const auto message = transfer_confirm_message(
        ledger.chain_id, identity, escrow, body.recipient_escrow_id, amount,
        envelope.valid_until_height);
    if (!verify_hub_signature(ledger, identity, message, body.hub_signature,
                              verify)) {
      return refused(Result::unauthorized);
    }
  }
  if (!debit(ledger, escrow, amount)) return std::nullopt;
  if (!credit(ledger, body.recipient_escrow_id, amount)) return std::nullopt;
  return charged(ledger, escrow);
}

// Kind 18. The walk is arithmetic rather than iteration, so it is `O(1)`.
//
// Every window in the period pays the same amount unconditionally, which is why
// no per-window record exists for a million identities and why the cap is
// applied here rather than at assignment.
std::optional<Outcome> mint_verified_user(Ledger& ledger,
                                          const Envelope& envelope,
                                          const Body& body,
                                          const Octets32& escrow,
                                          const SignatureVerifier& verify) {
  const auto identity = owner_of(ledger, escrow);
  const auto& destination = body.destination_escrow_id;
  if (const auto refusal = require_destination(ledger, destination, identity)) {
    return refused(*refusal);
  }
  const auto enrolled = ledger.registry.enrollments.find(identity);
  if (enrolled == ledger.registry.enrollments.end()) {
    return refused(Result::not_enrolled);
  }
  const auto collection = verified_user_collection(
      enrolled->second.minted_through_window,
      window_of_height(enrolled->second.enrolled_at_height), ledger.height);
  if (collection.count == 0) return refused(Result::nothing_to_mint);

  const auto message = mint_message(
      ledger.chain_id, identity, static_cast<std::uint8_t>(Kind::mint_verified_user),
      0, destination, envelope.valid_until_height);
  if (const auto refusal =
          require_confirmation(ledger, destination, collection.amount_atomic,
                               identity, message, body.hub_signature, verify)) {
    return refused(*refusal);
  }
  if (!fits_channel(ledger, kVerifiedUserChannel, collection.amount_atomic)) {
    return refused(Result::channel_cap);
  }

  if (!credit(ledger, destination, collection.amount_atomic)) return std::nullopt;
  // The mark advances to `collectable_end` rather than to the walk's end, which
  // is what makes the thirty-window cap forfeit rather than defer.
  enrolled->second.minted_through_window = collection.collectable_end;
  if (collection.amount_atomic > kMaxU64 - enrolled->second.issued_atomic) {
    return std::nullopt;
  }
  enrolled->second.issued_atomic += collection.amount_atomic;
  if (!issue(ledger, kVerifiedUserChannel, collection.amount_atomic)) {
    return std::nullopt;
  }
  const auto outcome = charged(ledger, escrow);
  if (!outcome) return std::nullopt;
  return issued(*outcome, collection.amount_atomic);
}

}  // namespace

std::optional<Outcome> dispatch_value(Ledger& ledger, const Envelope& envelope,
                                      const Body& body, const Octets32& escrow,
                                      const SignatureVerifier& verify) {
  switch (static_cast<Kind>(envelope.kind)) {
    case Kind::native_transfer:
    case Kind::native_transfer_verified:
      return native_transfer(ledger, envelope, body, escrow, verify);
    case Kind::mint_verified_user:
      return mint_verified_user(ledger, envelope, body, escrow, verify);
    case Kind::direct_issue:
      // Kind 6. Refused for every acting key while the eligibility predicate is
      // founder-reserved, which is why the channel, amount, decision,
      // beneficiary, and cap conditions are specified and never exercised.
      return refused(Result::unauthorized);
    default:
      return std::nullopt;
  }
}

}  // namespace protocol::v6::internal
