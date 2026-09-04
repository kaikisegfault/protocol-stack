// Admission, escrow resolution, the shared envelope checks, and dispatch.
//
// This is the first translation unit in the kernel that **runs** a version-six
// transition rather than encoding one. Two execution orders had to be derived,
// because the accepted contract admits two readings of each and only one reading
// leaves the contract self-consistent; ADR 0045 records both, and they are
// repeated where a reader will look for them.
//
// 1. **`DEBIT_OVERFLOW` is returned inside envelope check 8**, not at kind 1's
//    own step 5. Check 8 is "escrow balance is below what it must debit", and
//    for a transfer what it must debit is `amount + fixed_fee` — exactly the sum
//    kind 1's step 5 tests. Testing it afterwards would leave check 8 undefined
//    on a sum that does not fit `u64` and would make code 7 unreachable in a
//    version whose specification lists exactly three unreachable frozen codes and
//    does not list it.
// 2. **The zero-confirmation-field rule is an execution condition returning
//    `UNAUTHORIZED`.** The specification places it at admission and names
//    `MALFORMED_TRANSACTION`; neither survives contact with the rest of the
//    contract, because the predicate reads a stored posture and admission reads
//    no state, and because the result-code space has no such name.

#include "economy_internal.hpp"
#include "economy_ledger_internal.hpp"

#include "protocol/v1/crypto.hpp"

namespace protocol::v8 {
namespace {

namespace i = protocol::v8::internal;

// Which body field names the escrow a scheme-2 kind acts on and charges.
const Octets32* scheme_two_fee_escrow(std::uint8_t kind, const Body& body) {
  switch (static_cast<Kind>(kind)) {
    case Kind::escrow_create:
    case Kind::escrow_delete:
      return &body.fee_escrow_id;
    case Kind::signer_add:
    case Kind::signer_revoke:
      return &body.escrow_id;
    default:
      return nullptr;
  }
}

// A refusal carries its code; a resolution carries the escrow that acts and
// pays. A registration has neither, which is why the escrow is optional.
struct Resolution {
  std::optional<Result> refusal;
  std::optional<Octets32> escrow;
};

// `SENDER_NOT_FOUND` is frozen and unreachable from here: a signer entry names
// an escrow, an escrow entry implies a version-one account entry, and the two
// are written and deleted together, so an escrow that resolves always exists.
// The check is kept because "unreachable" is a property of the state invariants
// rather than of this function.
Resolution resolve(const Ledger& ledger, const Envelope& envelope,
                   const Body& body) {
  if (envelope.kind == static_cast<std::uint8_t>(Kind::hub_register)) {
    return Resolution{};
  }
  if (envelope.scheme == kSchemeSigner) {
    const auto identifier = signer_id(envelope.authority_public_key);
    const auto assigned = ledger.registry.signers.find(identifier);
    if (assigned == ledger.registry.signers.end()) {
      return Resolution{Result::signer_not_found, std::nullopt};
    }
    if (!ledger.registry.accounts.contains(assigned->second)) {
      return Resolution{Result::sender_not_found, std::nullopt};
    }
    return Resolution{std::nullopt, assigned->second};
  }

  const auto identity = ledger.registry.identities.find(body.hub_identity_hash);
  if (identity == ledger.registry.identities.end()) {
    return Resolution{Result::not_hub_verified, std::nullopt};
  }
  if (identity->second.hub_public_key != envelope.authority_public_key) {
    return Resolution{Result::unauthorized, std::nullopt};
  }
  const auto* named = scheme_two_fee_escrow(envelope.kind, body);
  if (named == nullptr) return Resolution{Result::unauthorized, std::nullopt};
  const auto escrow = ledger.registry.escrows.find(*named);
  if (escrow == ledger.registry.escrows.end()) {
    return Resolution{Result::escrow_not_found, std::nullopt};
  }
  if (escrow->second.owner_hub_identity != body.hub_identity_hash) {
    return Resolution{Result::escrow_not_owned, std::nullopt};
  }
  return Resolution{std::nullopt, *named};
}

// What the acting escrow must cover: the fee, plus a transfer's amount. The sum
// is tested against `u64` before it is compared to a balance, which is derived
// rule 1 above.
//
// **A challenge response covers nothing**, which is version eight's one change
// to this function and is derived rather than chosen. The owner decided on
// 2026-09-02 that answering a mandatory audit costs an operator nothing; kind
// 20 is charged no fee and moves no amount, so its debit is zero and both
// checks stated over the debit become vacuous. Leaving it at the fixed fee
// would refuse a response from an escrow holding less than one fee, so an
// operator would have to keep a balance in order to prove the uptime they are
// paid for — a thing an end user must own in order to be paid, which the
// founder answer removes. ADR 0064 records the derivation.
std::optional<std::uint64_t> debit_of(const Ledger& ledger,
                                      const Envelope& envelope,
                                      const Body& body) {
  const auto kind = static_cast<Kind>(envelope.kind);
  if (kind == Kind::challenge_response) return 0;
  if (kind != Kind::native_transfer && kind != Kind::native_transfer_verified) {
    return ledger.fixed_fee;
  }
  if (body.amount_atomic > kMaxU64 - ledger.fixed_fee) return std::nullopt;
  return ledger.fixed_fee + body.amount_atomic;
}

// Checks 2, 3, 5, 6, and 8, in version one's order and with its meanings. A
// registration is exempt from all of them but expiry, and the exemption is
// forced rather than chosen: its fee limit is required to be zero, so on any
// chain with a nonzero fixed fee a fee-limit check would refuse every
// registration and close the ecosystem to new members.
// **`FEE_LIMIT_TOO_LOW` does not run for a challenge response.** Its fee limit
// is required to be zero at admission, so on any chain with a nonzero fixed fee
// this check would refuse every response and make the exemption unreachable —
// the same shape, and the same reason, as the registration's exemption below.
// The code is therefore unreachable for kind 20 and reachable for every other
// kind, which is why it is not a frozen code.
std::optional<Result> envelope_checks(const Ledger& ledger,
                                      const Envelope& envelope, const Body& body,
                                      const Octets32& escrow) {
  const bool fee_exempt =
      static_cast<Kind>(envelope.kind) == Kind::challenge_response;
  if (!fee_exempt && envelope.fee_limit < ledger.fixed_fee) {
    return Result::fee_limit_too_low;
  }
  if (envelope.valid_until_height < ledger.height) return Result::expired;
  const auto stored = i::nonce_of(ledger, escrow);
  if (stored == kMaxU64) return Result::nonce_exhausted;
  if (envelope.nonce != stored + 1) return Result::nonce_mismatch;
  const auto debit = debit_of(ledger, envelope, body);
  if (!debit) return Result::debit_overflow;
  if (i::balance_of(ledger, escrow) < *debit) return Result::insufficient_balance;
  return std::nullopt;
}

Outcome refused(Result result) { return Outcome{result, 0, 0}; }

}  // namespace

SignatureVerifier ed25519_verifier() {
  return [](std::span<const std::uint8_t> public_key,
            std::span<const std::uint8_t> message,
            std::span<const std::uint8_t> signature) {
    return protocol::v1::strict_ed25519_verify(public_key, message, signature);
  };
}

Admitted admit(std::span<const std::uint8_t> raw, const Octets32& chain_id,
               const SignatureVerifier& verify) {
  // Version one's four steps, unchanged in order and in meaning. Step 4 is
  // unchanged by the second scheme, which is why the scheme byte selects a key
  // rather than a verification rule: under both schemes the envelope signature
  // verifies against the 32-byte header field, so admission reads no state.
  Admitted result;
  auto decoded = decode_signed(raw);
  if (!decoded) {
    result.error = AdmissionError::malformed_transaction;
    return result;
  }
  if (decoded->envelope.chain_id != chain_id) {
    result.error = AdmissionError::wrong_chain;
    return result;
  }
  const auto message = signing_message(encode_unsigned(decoded->envelope));
  if (!verify(decoded->envelope.authority_public_key, message,
              decoded->signature)) {
    result.error = AdmissionError::invalid_signature;
    return result;
  }
  result.transaction = std::move(*decoded);
  result.transaction_id = transaction_id(raw);
  return result;
}

std::optional<Outcome> execute(Ledger& ledger, const Envelope& envelope,
                               const SignatureVerifier& verify) {
  const auto body = decode_body(envelope.kind, envelope.body);
  // Admission accepted these bytes, so a body that will not project is an
  // implementation disagreement between the two halves of one codec rather than
  // a transaction result.
  if (!body) return std::nullopt;

  const auto resolution = resolve(ledger, envelope, *body);
  if (resolution.refusal) return refused(*resolution.refusal);
  if (envelope.kind != static_cast<std::uint8_t>(Kind::hub_register)) {
    const auto refusal = envelope_checks(ledger, envelope, *body,
                                         *resolution.escrow);
    if (refusal) return refused(*refusal);
  }
  return i::dispatch(ledger, envelope, *body,
                     resolution.escrow ? &*resolution.escrow : nullptr, verify);
}

Receipt receipt_for(const Hash& transaction_id, const Envelope& envelope,
                    const Outcome& outcome) {
  Receipt receipt;
  receipt.transaction_id = transaction_id;
  receipt.kind = envelope.kind;
  receipt.result_code = static_cast<std::uint8_t>(outcome.result);
  receipt.fee_charged = outcome.fee_charged;
  receipt.issued_atomic = outcome.issued_atomic;
  return receipt;
}

namespace internal {

bool verify_hub_signature(const Ledger& ledger, const Octets32& identity,
                          std::span<const std::uint8_t> message,
                          const Bytes& signature,
                          const SignatureVerifier& verify) {
  // Every HUB message binds the identity, so a signature made by one person's
  // key cannot be presented as another's even where the other fields coincide.
  const auto entry = ledger.registry.identities.find(identity);
  if (entry == ledger.registry.identities.end()) return false;
  return verify(entry->second.hub_public_key, message, signature);
}

bool confirmation_field_is_absent(const Bytes& field) {
  return field.size() == kSignatureBytes && internal::all_zero(field);
}

bool confirmation_required(const Ledger& ledger, const Octets32& escrow,
                           std::uint64_t amount) {
  // The posture predicate at the executing height, in block heights only, so
  // two nodes agree on whether a confirmation was required without agreeing on
  // what time it is.
  const auto entry = ledger.registry.escrows.find(escrow);
  if (entry == ledger.registry.escrows.end()) return false;
  return requires_confirmation(entry->second.posture, amount, ledger.height);
}

}  // namespace internal
}  // namespace protocol::v8
