"""Ordered, failure-atomic Founder Seat sale engine.

Handlers are pure, so the engine never copies state to obtain atomicity. That
keeps one purchase constant-time and makes the founder-directed complete sale
of 100,000 seats a scenario this model can actually run end to end.
"""

from __future__ import annotations

from typing import Any

from . import contract as c
from ..common.canonical import InvariantError, digest
from .domain import State, assert_invariants, initial_state, state_digest, state_value
from .handlers import HANDLERS, INCREASE, apply_effect, failure, journal_delta
from .metrics import build_metrics
from .validation import parse_events

# Full invariants are O(sold), so a long run checks them on a bounded schedule
# plus at both ends rather than after every purchase.
INVARIANT_STRIDE = 512


def simulate(events_value: Any, *, invariant_stride: int = INVARIANT_STRIDE) -> dict[str, Any]:
    """Run one deterministic seat sale simulation."""
    events = parse_events(events_value)
    state = initial_state()
    assert_invariants(state)

    records: list[dict[str, Any]] = []
    for index, event in enumerate(events):
        record = apply_event(state, event, index)
        records.append(record)
        if invariant_stride and record["accepted"] and index % invariant_stride == 0:
            assert_invariants(state)
    assert_invariants(state)

    final_state = state_value(state)
    result = {
        "schema": c.SCHEMA,
        "events_digest": digest(c.EVENTS_LABEL, events),
        "records": records,
        "trace_digest": digest(c.TRACE_LABEL, records),
        "final_state": final_state,
        "state_digest": digest(c.STATE_LABEL, final_state),
        "metrics": build_metrics(state),
    }
    result["result_digest"] = digest(c.RESULT_LABEL, result)
    return result


def apply_event(state: State, event: dict[str, Any], index: int) -> dict[str, Any]:
    """Evaluate one event and commit it only if it was accepted."""
    summary_before = state.summary()
    try:
        outcome = HANDLERS[event["kind"]](state, event)
        if outcome.accepted:
            assert_balanced(outcome.journal, state, outcome.effect)
            apply_effect(state, outcome.effect)
    except InvariantError:
        outcome = failure("INVARIANT")

    if not outcome.accepted:
        if outcome.journal:
            raise AssertionError("a rejected event emitted a journal")
        if state.summary() != summary_before:
            raise AssertionError("a rejected event changed state")

    return {
        "index": index,
        "event_id": event["id"],
        "kind": event["kind"],
        "accepted": outcome.accepted,
        "result": outcome.code,
        "journal": outcome.journal,
    }


def assert_balanced(journal: list[dict[str, Any]], state: State, effect: Any) -> None:
    """Require one seat to move from remaining to sold at its block price."""
    totals: dict[str, int] = {}
    for item in journal:
        delta = journal_delta(item)
        if delta == 0:
            raise InvariantError("journal contains a zero entry")
        totals[item["bucket"]] = totals.get(item["bucket"], 0) + delta

    if len(totals) != 4:
        raise InvariantError("journal contains an unexpected bucket")
    if totals.get("remaining_seats") != -1 or totals.get("seats_sold") != 1:
        raise InvariantError("journal does not move exactly one seat")

    principals = [bucket for bucket in totals if bucket.startswith("principal:")]
    if len(principals) != 1 or totals[principals[0]] != 1:
        raise InvariantError("journal does not credit exactly one principal")
    if principals[0] != f"principal:{effect.seat.principal_id}":
        raise InvariantError("journal credits a different principal than the seat")

    expected = c.seat_price_cents(effect.seat_id)
    if expected is None or totals.get("proceeds") != expected:
        raise InvariantError("journal proceeds do not equal the block price")
    if effect.seat_id != state.seats_sold:
        raise InvariantError("the effect does not allocate the next seat")


__all__ = ["INCREASE", "apply_event", "assert_balanced", "simulate", "state_digest"]
