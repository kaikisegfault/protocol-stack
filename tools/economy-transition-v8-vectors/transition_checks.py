"""Kind 20 and kind 21: every ordered rejection produced by a live mutation.

Each condition is produced by minimally mutating an input that is accepted
unmutated, and the positive control is recorded beside them so a suite that
stopped accepting anything would fail rather than look complete.

Every mutation is aimed: a probe that trips a *different* condition than the one
it names has proved nothing about the condition it names, so each body below
disturbs one field and compensates whatever else that disturbs.
"""

from __future__ import annotations

import expected as x
import fixture as f
from checker import Checker

from simulation.economy_transition_v6.execution import SignatureOracle
from simulation.economy_transition_v8 import contract as c
from simulation.economy_transition_v8 import envelope as e
from simulation.economy_transition_v8 import state as st
from simulation.economy_transition_v8 import uptime_transitions as t


def _context(height: int) -> t.Context:
    context = t.Context(
        chain_id=bytes([0x88]) * 32,
        height=height,
        dispute_authority_key=f.DISPUTE_AUTHORITY_KEY,
    )
    context.seats[f.ACTIVE_SEAT] = t.Seat(
        hub_identity_hash=f.HOLDER_IDENTITY,
        activation_height=f.ACTIVE_SEAT_ACTIVATION_HEIGHT,
        is_activated=True,
    )
    context.seats[f.LATE_SEAT] = t.Seat(
        hub_identity_hash=f.HOLDER_IDENTITY,
        activation_height=f.LATE_SEAT_ACTIVATION_HEIGHT,
        is_activated=True,
    )
    context.seats[f.UNACTIVATED_SEAT] = t.Seat(
        hub_identity_hash=f.HOLDER_IDENTITY,
        activation_height=0,
        is_activated=False,
    )
    context.escrow_owner[f.HOLDER_ESCROW] = f.HOLDER_IDENTITY
    context.escrow_owner[f.STRANGER_ESCROW] = f.STRANGER_IDENTITY
    return context


def _response_body(seat_id: int = f.ACTIVE_SEAT, challenge_height: int | None = None):
    return {
        "seat_id": seat_id,
        "challenge_height": (
            f.CHALLENGE_HEIGHT if challenge_height is None else challenge_height
        ),
        "answer": bytes([0x5A]) * c.ANSWER_BYTES,
    }


def check_response(check: Checker) -> None:
    check.section("Kind 20's positive control and its nine ordered refusals.")

    context = _context(f.RESPONSE_HEIGHT)
    t.issue_challenge(context, f.CHALLENGE_HEIGHT, f.ACTIVE_SEAT)
    accepted = t.submit_response(context, f.HOLDER_ESCROW, _response_body())
    check.equal("kind20.control.is_accepted", accepted.succeeded)
    check.agree(
        "kind20.control.marks_the_challenge_answered",
        st.CHALLENGE_ANSWERED,
        st.decode_open_challenge_value(
            context.economy[st.open_challenge_key(f.CHALLENGE_HEIGHT, f.ACTIVE_SEAT)]
        ),
    )
    check.equal(
        "kind20.control.writes_no_window_record",
        not any(key[0] == c.SEAT_WINDOW_ENTRY for key in context.economy),
    )

    check.equal(
        "kind20.refuses.cycle_range",
        _response_code(_response_body(seat_id=c.MAX_SEAT_ID + 1)) == "CYCLE_RANGE",
    )
    check.equal(
        "kind20.refuses.seat_not_purchased",
        _response_code(_response_body(seat_id=900)) == "SEAT_NOT_PURCHASED",
    )
    check.equal(
        "kind20.refuses.seat_not_activated",
        _response_code(_response_body(seat_id=f.UNACTIVATED_SEAT)) == "SEAT_NOT_ACTIVATED",
    )
    check.equal(
        "kind20.refuses.unauthorized",
        _response_code(_response_body(), escrow=f.STRANGER_ESCROW) == "UNAUTHORIZED",
    )
    check.equal(
        "kind20.refuses.seat_not_in_scope",
        _response_code(_response_body(seat_id=f.LATE_SEAT)) == "SEAT_NOT_IN_SCOPE",
    )
    check.equal(
        "kind20.refuses.challenge_not_open_for_the_current_height",
        _response_code(_response_body(challenge_height=f.RESPONSE_HEIGHT))
        == "CHALLENGE_NOT_OPEN",
    )
    check.equal(
        "kind20.refuses.challenge_not_open_across_a_slot",
        _response_code(
            _response_body(challenge_height=f.CHALLENGE_HEIGHT - c.SLOT_BLOCKS)
        )
        == "CHALLENGE_NOT_OPEN",
    )
    check.equal(
        "kind20.refuses.challenge_not_issued",
        _response_code(_response_body(), issue=False) == "CHALLENGE_NOT_ISSUED",
    )
    check.equal(
        "kind20.refuses.response_replay",
        _response_code(_response_body(), twice=True) == "RESPONSE_REPLAY",
    )

    check.section("The deadline boundary, and the reordering it forces.")
    check.equal(
        "kind20.accepts_at_the_deadline",
        _response_code(
            _response_body(), height=f.CHALLENGE_HEIGHT + c.RESPONSE_DEADLINE_BLOCKS
        )
        == "SUCCESS",
    )
    check.equal(
        "kind20.refuses_one_height_past_the_deadline",
        _response_code(
            _response_body(), height=f.CHALLENGE_HEIGHT + c.RESPONSE_DEADLINE_BLOCKS + 1
        )
        == "RESPONSE_TOO_LATE",
    )
    check.equal(
        "kind20.reports_late_rather_than_unissued_when_the_entry_is_gone",
        _response_code(
            _response_body(),
            height=f.CHALLENGE_HEIGHT + c.RESPONSE_DEADLINE_BLOCKS + 1,
            issue=False,
        )
        == "RESPONSE_TOO_LATE",
    )
    check.agree(
        "kind20.deadline_blocks", x.RESPONSE_DEADLINE_BLOCKS, c.RESPONSE_DEADLINE_BLOCKS
    )


def _response_code(
    body: dict,
    escrow: bytes = f.HOLDER_ESCROW,
    height: int | None = None,
    issue: bool = True,
    twice: bool = False,
) -> str:
    context = _context(f.RESPONSE_HEIGHT if height is None else height)
    if issue:
        t.issue_challenge(context, f.CHALLENGE_HEIGHT, int(body["seat_id"]))
    if twice:
        t.submit_response(context, escrow, body)
    return t.submit_response(context, escrow, body).code


def _dispute_body(
    oracle: SignatureOracle,
    chain_id: bytes,
    seat_id: int = f.ACTIVE_SEAT,
    cycle_window: int = f.MEASURED_WINDOW,
    slot_index: int = 0,
    reason_code: int = 1,
    sign: bool = True,
) -> dict:
    message = e.dispute_message(
        chain_id, seat_id, cycle_window, slot_index, reason_code, f.VALID_UNTIL_HEIGHT
    )
    signature = bytes([0x77]) * 64
    if sign:
        oracle.record(f.DISPUTE_AUTHORITY_KEY, message, signature)
    return {
        "seat_id": seat_id,
        "cycle_window": cycle_window,
        "slot_index": slot_index,
        "reason_code": reason_code,
        "authority_signature": signature,
        "valid_until_height": f.VALID_UNTIL_HEIGHT,
    }


def check_dispute(check: Checker) -> None:
    check.section("Kind 21's positive control and its ten ordered refusals.")
    disputable_height = c.CYCLE_BLOCKS * (f.MEASURED_WINDOW + 1) + 5

    oracle = SignatureOracle()
    context = _context(disputable_height)
    body = _dispute_body(oracle, context.chain_id)
    accepted = t.file_dispute(context, body, oracle.verify)
    check.equal("kind21.control.is_accepted", accepted.succeeded)
    credited, disputed = st.decode_seat_window_value(
        context.economy[st.seat_window_key(f.MEASURED_WINDOW, f.ACTIVE_SEAT)]
    )
    check.agree("kind21.control.credited_is_unchanged", x.all_slots_credited(), credited)
    check.agree("kind21.control.disputed_bit", 1, disputed)
    check.agree(
        "kind21.control.uptime_seconds_after",
        x.uptime_seconds(x.all_slots_credited(), 1),
        st.credited_slots(credited, disputed) * c.SLOT_SECONDS,
    )

    check.equal(
        "kind21.refuses.unauthorized_dispute",
        _dispute_code(sign=False) == "UNAUTHORIZED_DISPUTE",
    )
    check.equal(
        "kind21.refuses.a_signature_over_another_slot",
        _dispute_code(resign_slot=1) == "UNAUTHORIZED_DISPUTE",
    )
    check.equal(
        "kind21.refuses.cycle_range",
        _dispute_code(seat_id=c.MAX_SEAT_ID + 1) == "CYCLE_RANGE",
    )
    check.equal(
        "kind21.refuses.seat_not_purchased",
        _dispute_code(seat_id=900) == "SEAT_NOT_PURCHASED",
    )
    check.equal(
        "kind21.refuses.slot_range",
        _dispute_code(slot_index=c.MAX_SLOT_INDEX + 1) == "SLOT_RANGE",
    )
    check.equal(
        "kind21.refuses.window_not_closed",
        _dispute_code(cycle_window=f.MEASURED_WINDOW + 1) == "WINDOW_NOT_CLOSED",
    )
    check.equal(
        "kind21.refuses.dispute_window_closed",
        _dispute_code(cycle_window=f.MEASURED_WINDOW - 1) == "DISPUTE_WINDOW_CLOSED",
    )
    check.equal(
        "kind21.refuses.seat_not_in_scope",
        _dispute_code(seat_id=f.LATE_SEAT) == "SEAT_NOT_IN_SCOPE",
    )
    check.equal("kind21.refuses.dispute_replay", _dispute_code(twice=True) == "DISPUTE_REPLAY")
    check.equal(
        "kind21.refuses.dispute_slot_not_credited",
        _dispute_code(uncredit_slot=0) == "DISPUTE_SLOT_NOT_CREDITED",
    )
    check.equal(
        "kind21.refuses.dispute_cap_exceeded",
        _dispute_code(
            prefill=c.DISPUTE_CAP_SLOTS_PER_SEAT,
            slot_index=c.DISPUTE_CAP_SLOTS_PER_SEAT,
        )
        == "DISPUTE_CAP_EXCEEDED",
    )


def check_containment(check: Checker) -> None:
    """A perfect seat still meets its cycle after a maximal dispute."""
    check.section("The containment theorem, at its boundary, over encoded state.")
    disputable_height = c.CYCLE_BLOCKS * (f.MEASURED_WINDOW + 1) + 5
    oracle = SignatureOracle()
    context = _context(disputable_height)
    for slot in range(c.DISPUTE_CAP_SLOTS_PER_SEAT):
        outcome = t.file_dispute(
            context, _dispute_body(oracle, context.chain_id, slot_index=slot), oracle.verify
        )
        if not outcome.succeeded:
            check.failures.append(f"a dispute inside the cap was refused as {outcome.code}")
    credited, disputed = st.decode_seat_window_value(
        context.economy[st.seat_window_key(f.MEASURED_WINDOW, f.ACTIVE_SEAT)]
    )
    seconds = st.credited_slots(credited, disputed) * c.SLOT_SECONDS
    check.agree(
        "containment.maximal_dispute.uptime_seconds",
        x.uptime_seconds(x.all_slots_credited(), (1 << c.DISPUTE_CAP_SLOTS_PER_SEAT) - 1),
        seconds,
    )
    check.agree(
        "containment.activity_threshold_seconds", x.ACTIVITY_THRESHOLD_SECONDS, seconds
    )
    check.equal(
        "containment.a_perfect_seat_still_meets_its_cycle",
        seconds >= x.ACTIVITY_THRESHOLD_SECONDS,
    )
    check.equal(
        "containment.the_cap_is_the_grace_allowance",
        c.SLOTS_PER_WINDOW - c.DISPUTE_CAP_SLOTS_PER_SEAT == 18,
    )
    check.equal(
        "containment.the_seventh_dispute_is_refused",
        t.file_dispute(
            context,
            _dispute_body(oracle, context.chain_id, slot_index=c.DISPUTE_CAP_SLOTS_PER_SEAT),
            oracle.verify,
        ).code
        == "DISPUTE_CAP_EXCEEDED",
    )


def _dispute_code(
    seat_id: int = f.ACTIVE_SEAT,
    cycle_window: int = f.MEASURED_WINDOW,
    slot_index: int = 0,
    sign: bool = True,
    resign_slot: int | None = None,
    twice: bool = False,
    prefill: int = 0,
    uncredit_slot: int | None = None,
) -> str:
    disputable_height = c.CYCLE_BLOCKS * (f.MEASURED_WINDOW + 1) + 5
    oracle = SignatureOracle()
    context = _context(disputable_height)
    if prefill:
        context.economy[st.seat_window_key(cycle_window, seat_id)] = st.seat_window_value(
            st.all_slots_credited(), (1 << prefill) - 1
        )
    if uncredit_slot is not None:
        context.economy[st.seat_window_key(cycle_window, seat_id)] = st.seat_window_value(
            st.all_slots_credited() & ~(1 << uncredit_slot), 0
        )
    if resign_slot is not None:
        # A signature genuinely produced by the authority, over a *different*
        # slot, presented against this one. It is the authority's own signature
        # and it is still refused, which is what makes the message binding the
        # subject rather than the key.
        _dispute_body(
            oracle,
            context.chain_id,
            seat_id=seat_id,
            cycle_window=cycle_window,
            slot_index=resign_slot,
        )
        sign = False
    body = _dispute_body(
        oracle,
        context.chain_id,
        seat_id=seat_id,
        cycle_window=cycle_window,
        slot_index=slot_index,
        sign=sign,
    )
    if twice:
        t.file_dispute(context, body, oracle.verify)
    return t.file_dispute(context, body, oracle.verify).code
