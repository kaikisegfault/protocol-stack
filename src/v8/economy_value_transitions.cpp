// The eight value transitions version eight carries unchanged: the two
// transfers, the four seat transitions, the referral mint, the verified-user
// mint, and the refused direct issue.
//
// **Kind 4 is the only transition in the whole contract that reads a surface
// version seven moved.** A winner's collection gained one term — the cycle's
// pool share — and that term lives inside `collect_node`. Everything else kind 4
// does is version six's, and so is every other transition here: version seven
// changes no transaction, and the four seat transitions arrive in this kernel
// unchanged from the contract version six accepted rather than revised.

#include "economy_ledger_internal.hpp"

namespace protocol::v8::internal {
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

// The seat a kind-3 or kind-4 transaction names, in the specification's
// rejection order: range, existence, activation, then ownership. A refusal
// carries its code and nothing else, because none of the four writes anything.
struct SeatCheck {
  std::optional<Result> refusal;
};

SeatCheck require_seat(const Ledger& ledger, std::uint32_t seat_id,
                       const Octets32& escrow, bool require_activated) {
  if (seat_id > kMaxSeatId) return SeatCheck{Result::cycle_range};
  const auto seat = ledger.seats.find(seat_id);
  if (seat == ledger.seats.end()) return SeatCheck{Result::seat_not_purchased};
  if (require_activated && !seat->second.is_activated) {
    return SeatCheck{Result::seat_not_activated};
  }
  if (seat->second.hub_identity_hash != owner_of(ledger, escrow)) {
    return SeatCheck{Result::unauthorized};
  }
  return SeatCheck{};
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

// Kind 2. The purchaser is the identity that signed, and no account is named.
//
// Self-referral is refused across every escrow a person holds, because the
// comparison is between two identities and one person has exactly one. The
// referrer is named by escrow — which is the shareable thing — and recorded as
// an identity, so referral earnings follow the person rather than the address.
std::optional<Outcome> purchase_seat(Ledger& ledger, const Envelope& envelope,
                                     const Body& body, const Octets32& escrow,
                                     const SignatureVerifier& verify) {
  const auto seat_id = body.seat_id;
  if (seat_id > kMaxSeatId) return refused(Result::cycle_range);
  if (ledger.seats.contains(seat_id)) return refused(Result::replay);
  const auto identity = owner_of(ledger, escrow);

  bool has_referrer = false;
  Octets32 referrer_identity{};
  if (body.has_referrer) {
    const auto referrer = ledger.registry.escrows.find(body.referrer_escrow_id);
    if (referrer == ledger.registry.escrows.end()) {
      return refused(Result::recipient_not_registered);
    }
    referrer_identity = referrer->second.owner_hub_identity;
    if (referrer_identity == identity) return refused(Result::invalid_referrer);
    has_referrer = true;
  }

  const auto entry = ledger.registry.identities.find(identity);
  if (entry == ledger.registry.identities.end()) return std::nullopt;
  if (entry->second.seat_count >= kMaxSeatsPerIdentity) {
    return refused(Result::seat_limit);
  }

  const auto message = purchase_message(ledger.chain_id, identity, seat_id,
                                        envelope.valid_until_height);
  if (!verify_hub_signature(ledger, identity, message, body.hub_signature,
                            verify)) {
    return refused(Result::unauthorized);
  }

  SeatRecord seat;
  seat.hub_identity_hash = identity;
  seat.has_referrer = has_referrer;
  seat.referrer_hub_identity = referrer_identity;
  ledger.seats[seat_id] = seat;
  entry->second.seat_count += 1;
  return charged(ledger, escrow);
}

// Kind 3. One-time and permanent, and it issues nothing.
//
// The mark it writes is the window the activation happens in, which is what
// makes the accumulation cap well-defined from the moment a seat activates: the
// seat's first collectable window is the one after it.
std::optional<Outcome> activate_seat(Ledger& ledger, const Envelope& envelope,
                                     const Body& body, const Octets32& escrow,
                                     const SignatureVerifier& verify) {
  const auto check = require_seat(ledger, body.seat_id, escrow, false);
  if (check.refusal) return refused(*check.refusal);
  auto& record = ledger.seats[body.seat_id];
  if (record.is_activated) return refused(Result::replay);

  const auto message = activation_message(ledger.chain_id, record.hub_identity_hash,
                                          body.seat_id,
                                          envelope.valid_until_height);
  if (!verify_hub_signature(ledger, record.hub_identity_hash, message,
                            body.hub_signature, verify)) {
    return refused(Result::unauthorized);
  }
  record.is_activated = true;
  record.activation_height = ledger.height;
  record.minted_through_window = window_of_height(ledger.height);
  return charged(ledger, escrow);
}

// Kind 4. One button, everything, no quantity — now including the pool.
//
// The walk is version three's range and version seven's per-window read: an
// accrued bit still pays one base permission, and a winner bit now pays the
// reallocation share **and** the cycle's pool share. The Founder operator leg
// credits the named destination escrow, the four institutional legs credit typed
// custody, and the mark advances to the last assigned window whatever the walk
// found, which is what makes the accumulation cap forfeit rather than defer.
//
// **Nothing here reads the recovery pool entry.** A mint takes what the records
// it walks say each cycle absorbed, which is why the record commits to the
// absorbed amount at all: the pool's balance at a window is a function of every
// earlier cycle, and deriving it would replay the whole assignment history
// inside a transition that must stay `O(cap)`.
//
// **It is not gated on span**, in this version or any earlier one. A seat past
// its own 731 issuance cycles collecting only reallocation and pool shares is a
// conforming transaction, and version seven states that as a requirement so a
// later reader does not add the gate as an optimisation.
std::optional<Outcome> mint_node(Ledger& ledger, const Envelope& envelope,
                                 const Body& body, const Octets32& escrow,
                                 const SignatureVerifier& verify) {
  const auto check = require_seat(ledger, body.seat_id, escrow, true);
  if (check.refusal) return refused(*check.refusal);
  auto& seat = ledger.seats[body.seat_id];
  const auto identity = seat.hub_identity_hash;
  const auto& destination = body.destination_escrow_id;
  if (const auto refusal = require_destination(ledger, destination, identity)) {
    return refused(*refusal);
  }

  const auto mark = seat.minted_through_window;
  const auto last_assigned = last_assigned_window(ledger.height);
  if (!walk_range(mark, last_assigned)) return refused(Result::nothing_to_mint);
  const auto collection = collect_node(ledger, body.seat_id, mark, last_assigned);
  if (!collection) return std::nullopt;
  const auto total = collection->total_atomic();

  const auto message =
      mint_message(ledger.chain_id, identity, static_cast<std::uint8_t>(Kind::mint_node),
                   body.seat_id, destination, envelope.valid_until_height);
  if (const auto refusal = require_confirmation(ledger, destination, total, identity,
                                                message, body.hub_signature, verify)) {
    return refused(*refusal);
  }
  for (std::uint8_t channel = 0; channel < kRecoveryPoolLegs; ++channel) {
    if (!fits_channel(ledger, channel, collection->per_channel[channel])) {
      return refused(Result::channel_cap);
    }
  }

  if (!credit(ledger, destination, collection->operator_atomic())) {
    return std::nullopt;
  }
  for (std::uint8_t channel = 0; channel < kRecoveryPoolLegs; ++channel) {
    const auto beneficiary = leg_beneficiary_kind(channel);
    if (!beneficiary) continue;
    auto& held = ledger.custody[*beneficiary];
    if (collection->per_channel[channel] > kMaxU64 - held) return std::nullopt;
    held += collection->per_channel[channel];
  }
  for (std::uint8_t channel = 0; channel < kRecoveryPoolLegs; ++channel) {
    if (!issue(ledger, channel, collection->per_channel[channel])) {
      return std::nullopt;
    }
  }
  // The advance is to the last assigned window rather than to what the walk
  // reached, which is the line that makes the thirty-window cap permanent.
  seat.minted_through_window = *last_assigned;
  const auto outcome = charged(ledger, escrow);
  if (!outcome) return std::nullopt;
  return issued(*outcome, total);
}

// Kind 5. Any escrow of the person may receive it: the balance is the identity's,
// so a referrer who changes escrows keeps everything already accrued.
//
// The referral leg has no winner split and therefore no remainder, which is why
// the recovery pool never touches this channel and version seven leaves its
// identity exactly as version six stated it.
std::optional<Outcome> mint_referral(Ledger& ledger, const Envelope& envelope,
                                     const Body& body, const Octets32& escrow,
                                     const SignatureVerifier& verify) {
  const auto identity = owner_of(ledger, escrow);
  const auto& destination = body.destination_escrow_id;
  if (const auto refusal = require_destination(ledger, destination, identity)) {
    return refused(*refusal);
  }
  const auto entry = ledger.referral.find(identity);
  if (entry == ledger.referral.end()) return refused(Result::nothing_to_mint);

  const auto last_assigned = last_assigned_window(ledger.height);
  const bool settled = entry->second.accrued_atomic == entry->second.minted_atomic;
  if (settled && (!last_assigned ||
                  entry->second.collected_through_window >= *last_assigned)) {
    return refused(Result::nothing_to_mint);
  }
  // A referral balance is written by the assignment prologue, so one can only
  // exist on a chain that has assigned a window. Reaching this is a state no
  // sequence of conforming transitions produces.
  if (!last_assigned) return std::nullopt;
  if (entry->second.minted_atomic > entry->second.accrued_atomic) return std::nullopt;
  const auto amount = entry->second.accrued_atomic - entry->second.minted_atomic;

  const auto message = mint_message(
      ledger.chain_id, identity, static_cast<std::uint8_t>(Kind::mint_referral), 0,
      destination, envelope.valid_until_height);
  if (const auto refusal = require_confirmation(ledger, destination, amount, identity,
                                                message, body.hub_signature, verify)) {
    return refused(*refusal);
  }
  if (!fits_channel(ledger, kReferralChannel, amount)) {
    return refused(Result::channel_cap);
  }

  if (!credit(ledger, destination, amount)) return std::nullopt;
  entry->second.minted_atomic = entry->second.accrued_atomic;
  entry->second.collected_through_window = *last_assigned;
  if (!issue(ledger, kReferralChannel, amount)) return std::nullopt;
  const auto outcome = charged(ledger, escrow);
  if (!outcome) return std::nullopt;
  return issued(*outcome, amount);
}

}  // namespace

std::optional<Outcome> dispatch_value(Ledger& ledger, const Envelope& envelope,
                                      const Body& body, const Octets32& escrow,
                                      const SignatureVerifier& verify) {
  switch (static_cast<Kind>(envelope.kind)) {
    case Kind::native_transfer:
    case Kind::native_transfer_verified:
      return native_transfer(ledger, envelope, body, escrow, verify);
    case Kind::purchase_seat:
      return purchase_seat(ledger, envelope, body, escrow, verify);
    case Kind::activate_seat:
      return activate_seat(ledger, envelope, body, escrow, verify);
    case Kind::mint_node:
      return mint_node(ledger, envelope, body, escrow, verify);
    case Kind::mint_referral:
      return mint_referral(ledger, envelope, body, escrow, verify);
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

}  // namespace protocol::v8::internal
