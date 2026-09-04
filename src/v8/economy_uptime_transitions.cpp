// Kind 20 and kind 21, and the two block steps that write the same entries
// without any transaction asking for them.
//
// Each transition is stated as its ordered rejection conditions and its writes,
// over exactly the state it reads. **Version seven's shared envelope checks are
// not restated here** — the nonce, the fee limit, the expiry, and the
// resolution of the acting escrow are version seven's and run before any
// condition below.
//
// One condition order departs from the accepted measurement model and the
// reason is recorded where it happens: kind 20 checks `RESPONSE_TOO_LATE`
// *before* `CHALLENGE_NOT_ISSUED`.

#include "economy_ledger_internal.hpp"

#include <bit>

namespace protocol::v8::internal {
namespace {

Outcome refused(Result result) { return Outcome{result, 0, 0}; }

bool same_slot(std::uint64_t left, std::uint64_t right) {
  return window_of_height(left) == window_of_height(right) &&
         slot_of(left) == slot_of(right);
}

// The identity that owns an escrow, or nothing when the escrow is not one.
const Octets32* escrow_owner(const Ledger& ledger, const Octets32& escrow) {
  const auto entry = ledger.registry.escrows.find(escrow);
  if (entry == ledger.registry.escrows.end()) return nullptr;
  return &entry->second.owner_hub_identity;
}

void store_window(Ledger& ledger, std::uint64_t cycle_window,
                  std::uint32_t seat_id, const SeatWindowRecord& record) {
  // The encoder refuses a pad bit and a dispute of an uncredited slot, and no
  // caller here can produce either: expiry only clears a credited bit and a
  // dispute only sets one it has just checked. A refusal would therefore be an
  // implementation disagreement, so the value is written and the invariants
  // re-read it after the block.
  const auto value = seat_window_value(record);
  if (!value) return;
  ledger.uptime[seat_window_key(cycle_window, seat_id)] = *value;
}

}  // namespace

std::optional<SeatWindowRecord> window_record(const Ledger& ledger,
                                              std::uint64_t cycle_window,
                                              std::uint32_t seat_id) {
  const auto entry = ledger.uptime.find(seat_window_key(cycle_window, seat_id));
  // An absent record reads as a fully credited seat, because a slot bit begins
  // set and evidence only ever removes credit. So a machine that answers every
  // challenge writes nothing at all and the storage the pipeline adds is
  // proportional to failure rather than to population.
  if (entry == ledger.uptime.end()) return full_seat_window();
  return decode_seat_window_value(entry->second);
}

// Kind 20. Nine ordered conditions, then one state write.
//
// On acceptance the open challenge entry's state becomes `1` and **no fee is
// charged**. No credited slot is added, because a slot bit is already set and
// only expiry or a dispute ever clears one.
std::optional<Outcome> submit_response(Ledger& ledger, const Body& body,
                                       const Octets32& escrow) {
  const auto window = window_of_height(ledger.height);

  if (body.seat_id > kMaxSeatId) return refused(Result::cycle_range);
  const auto seat = ledger.seats.find(body.seat_id);
  if (seat == ledger.seats.end()) return refused(Result::seat_not_purchased);
  if (!seat->second.is_activated) return refused(Result::seat_not_activated);
  const auto* owner = escrow_owner(ledger, escrow);
  if (owner == nullptr || *owner != seat->second.hub_identity_hash) {
    return refused(Result::unauthorized);
  }
  if (!seat_in_scope(seat->second.activation_height, window)) {
    return refused(Result::seat_not_in_scope);
  }
  if (body.challenge_height >= ledger.height ||
      !same_slot(body.challenge_height, ledger.height)) {
    return refused(Result::challenge_not_open);
  }
  // **Ahead of the issuance check, and the accepted model orders them the other
  // way.** The model recomputes selection from retained beacons and can say
  // "issued, and you are late"; version eight deletes the entry at expiry, so
  // checking issuance first would report that a challenge which *was* issued
  // never was. Both are refusals that write nothing, so the reordering changes
  // no accepted outcome and makes the report true.
  if (ledger.height > body.challenge_height + kResponseDeadlineBlocks) {
    return refused(Result::response_too_late);
  }

  const auto key = open_challenge_key(body.challenge_height, body.seat_id);
  const auto recorded = ledger.uptime.find(key);
  if (recorded == ledger.uptime.end()) {
    return refused(Result::challenge_not_issued);
  }
  const auto state = decode_open_challenge_value(recorded->second);
  if (!state) return std::nullopt;
  if (*state == kChallengeAnswered) return refused(Result::response_replay);

  const auto value = open_challenge_value(kChallengeAnswered);
  if (!value) return std::nullopt;
  recorded->second = *value;

  // **The nonce advances and no fee is taken**, which is the asymmetry with the
  // other fee-exempt kind: a registration has no escrow and therefore no nonce
  // sequence, while a response has both, so replay protection is doubled rather
  // than replaced. Answering a mandatory audit costs an operator nothing, which
  // the owner decided on 2026-09-02 and ADR 0064 derives the debit from.
  set_nonce(ledger, escrow, nonce_of(ledger, escrow) + 1);
  return Outcome{Result::success, 0, 0};
}

// Kind 21. Ten ordered conditions, then one bit set.
//
// On acceptance the slot's bit is set in `disputed`, the record is created if
// absent, and the fixed fee is charged to the relaying escrow. **`credited` is
// not changed**, so the record keeps what the seat's own evidence said and the
// containment invariant stays checkable against that evidence rather than
// against a bitmap a dispute has already edited.
std::optional<Outcome> file_dispute(Ledger& ledger, const Envelope& envelope,
                                    const Body& body, const Octets32& escrow,
                                    const SignatureVerifier& verify) {
  const auto window = window_of_height(ledger.height);

  // The dispute authority signs the body while an ordinary signer carries the
  // transaction and pays its fee. It is kind 10's pattern and it is the right
  // shape rather than a familiar one: under ADR 0047 the deciding machine
  // issues one signed, bounded decision and someone submits it, and a scheme in
  // which the authority were the envelope's own signer would give the ecosystem
  // AI a chain account, a nonce sequence, a balance, and a fee obligation.
  const auto message =
      dispute_message(ledger.chain_id, body.seat_id, body.cycle_window,
                      body.slot_index, body.reason_code,
                      envelope.valid_until_height);
  if (!verify(ledger.dispute_authority_key, message, body.authority_signature)) {
    return refused(Result::unauthorized_dispute);
  }
  if (body.seat_id > kMaxSeatId) return refused(Result::cycle_range);
  const auto seat = ledger.seats.find(body.seat_id);
  if (seat == ledger.seats.end()) return refused(Result::seat_not_purchased);
  if (body.slot_index > kMaxSlotIndex) return refused(Result::slot_range);
  // Conditions 5 and 6 are finalisation by expiry stated as a pair of bounds:
  // window `w` is disputable exactly while the executing height is inside
  // window `w + 1`, which is `kAssignmentLagWindows` restated from the dispute
  // side. No signature, liveness, quorum, or acknowledgement is required at any
  // point, so an outage of the dispute authority of any length delays nothing.
  if (body.cycle_window >= window) return refused(Result::window_not_closed);
  if (body.cycle_window + kAssignmentLagWindows <= window) {
    return refused(Result::dispute_window_closed);
  }
  if (!seat_in_scope(seat->second.activation_height, body.cycle_window)) {
    return refused(Result::seat_not_in_scope);
  }

  auto record = window_record(ledger, body.cycle_window, body.seat_id);
  if (!record) return std::nullopt;
  const std::uint32_t bit = 1U << body.slot_index;
  if ((record->disputed & bit) != 0U) return refused(Result::dispute_replay);
  if ((record->credited & bit) == 0U) {
    return refused(Result::dispute_slot_not_credited);
  }
  // The cap is the founder-directed grace allowance, which is what makes the
  // containment theorem hold: a seat credited for every slot still meets its
  // cycle after a maximal dispute, so a compromised authority key can reduce a
  // result and never manufacture one.
  if (static_cast<std::uint32_t>(std::popcount(record->disputed)) >=
      kDisputeCapSlotsPerSeat) {
    return refused(Result::dispute_cap_exceeded);
  }

  record->disputed |= bit;
  store_window(ledger, body.cycle_window, body.seat_id, *record);
  return charged(ledger, escrow);
}

bool issue_challenge(Ledger& ledger, std::uint64_t challenge_height,
                     std::uint32_t seat_id) {
  const auto key = open_challenge_key(challenge_height, seat_id);
  if (ledger.uptime.contains(key)) return false;
  const auto value = open_challenge_value(kChallengeOutstanding);
  if (!value) return false;
  ledger.uptime[key] = *value;
  return true;
}

bool expire_challenge(Ledger& ledger, std::uint64_t challenge_height,
                      std::uint32_t seat_id, bool& lost) {
  lost = false;
  const auto key = open_challenge_key(challenge_height, seat_id);
  const auto entry = ledger.uptime.find(key);
  if (entry == ledger.uptime.end()) return true;
  const auto state = decode_open_challenge_value(entry->second);
  if (!state) return false;
  ledger.uptime.erase(entry);
  if (*state == kChallengeAnswered) return true;

  // An unanswered challenge clears the seat's bit for the slot of its *own*
  // height, which is the model's slot-close sweep made incremental and exact.
  // Selection excludes the final `kResponseDeadlineBlocks` heights of every
  // slot, so that slot and this height's slot are always the same one and the
  // window this writes to is never one the prologue has already deleted.
  const auto window = window_of_height(challenge_height);
  auto record = window_record(ledger, window, seat_id);
  if (!record) return false;
  const std::uint32_t bit = 1U << slot_of(challenge_height);
  if ((record->credited & bit) == 0U) return true;
  record->credited &= ~bit;
  store_window(ledger, window, seat_id, *record);
  lost = true;
  return true;
}

}  // namespace protocol::v8::internal
