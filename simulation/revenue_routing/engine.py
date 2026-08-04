"""Ordered, failure-atomic revenue routing engine.

Handlers are pure, so the engine never copies state to obtain atomicity. It
re-derives every journalled amount from the event and the pre-state, which is
what makes the journal an independent check rather than a restatement of the
handler's own arithmetic.
"""

from __future__ import annotations

from typing import Any, Callable

from . import contract as c
from ..common.canonical import InvariantError, digest
from .domain import State, assert_invariants, initial_state, state_digest, state_value
from .handlers_cycle import close_cycle
from .handlers_revenue import route_commercial_payment, route_transaction_fee
from .metrics import build_metrics
from .operations import (
    DECREASE,
    INCREASE,
    Outcome,
    apply_effect,
    failure,
    journal_delta,
)
from .validation import parse_events

Handler = Callable[[State, dict[str, Any]], Outcome]

HANDLERS: dict[str, Handler] = {
    "route_commercial_payment": route_commercial_payment,
    "route_transaction_fee": route_transaction_fee,
    "close_cycle": close_cycle,
}

# Full invariants are O(creators + credited seats), so a long run checks them
# on a bounded schedule plus at both ends rather than after every event.
INVARIANT_STRIDE = 64


def simulate(
    events_value: Any,
    *,
    invariant_stride: int = INVARIANT_STRIDE,
) -> dict[str, Any]:
    """Run one deterministic revenue routing simulation."""
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
            assert_balanced(outcome.journal, state, event)
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


def assert_balanced(
    journal: list[dict[str, Any]],
    state: State,
    event: dict[str, Any],
) -> None:
    """Re-derive every journalled amount from the event and the pre-state."""
    increases, decreases = _totals(journal)
    if sum(increases.values()) != sum(decreases.values()):
        raise InvariantError("journal increases do not equal journal decreases")

    kind = event["kind"]
    if kind == "route_commercial_payment":
        _assert_payment(increases, decreases, event)
    elif kind == "route_transaction_fee":
        _assert_fee(increases, decreases, event)
    else:
        _assert_close(increases, decreases, state, event)


def _totals(
    journal: list[dict[str, Any]],
) -> tuple[dict[str, int], dict[str, int]]:
    increases: dict[str, int] = {}
    decreases: dict[str, int] = {}
    for item in journal:
        delta = journal_delta(item)
        if delta == 0:
            raise InvariantError("journal contains a zero entry")
        target = increases if item["direction"] == INCREASE else decreases
        bucket = item["bucket"]
        if bucket in target:
            raise InvariantError(f"journal repeats the bucket {bucket}")
        target[bucket] = abs(delta)
    return increases, decreases


def _assert_payment(
    increases: dict[str, int],
    decreases: dict[str, int],
    event: dict[str, Any],
) -> None:
    amount = int(event["amount_atomic"])
    if decreases != {"payment": amount}:
        raise InvariantError("the journal does not consume exactly the payment")

    product_id = event["product_creator_id"]
    parts = c.split(amount, product_creator=product_id is not None)
    if parts is None:
        raise InvariantError("an accepted payment does not split")
    founder_credit, project_amount, product_amount, system_share = parts

    expected = {"commercial_pool": founder_credit}
    if system_share != 0:
        expected["system_creator"] = system_share
    for creator_id, leg in (
        (event["project_creator_id"], project_amount),
        (product_id, product_amount),
    ):
        if creator_id is not None and leg != 0:
            expected[f"creator:{creator_id}"] = leg
    if increases != expected:
        raise InvariantError("the journal does not credit the specified shares")


def _assert_fee(
    increases: dict[str, int],
    decreases: dict[str, int],
    event: dict[str, Any],
) -> None:
    amount = int(event["amount_atomic"])
    if decreases != {"fee": amount} or increases != {"fee_pool": amount}:
        raise InvariantError("a fee does not route wholly to the fee pool")


def _assert_close(
    increases: dict[str, int],
    decreases: dict[str, int],
    state: State,
    event: dict[str, Any],
) -> None:
    seats = event["active_seats_result"]["seat_ids"]
    sides = (
        ("commercial", state.commercial_pool + state.commercial_carry),
        ("fee", state.fee_pool + state.fee_carry),
    )
    for side, pool_in in sides:
        _assert_side(increases, decreases, side, pool_in, seats)

    unexpected = set(decreases) - {f"{side}_distribution" for side, _ in sides}
    if unexpected:
        raise InvariantError("a cycle close consumes an unexpected bucket")


def _assert_side(
    increases: dict[str, int],
    decreases: dict[str, int],
    side: str,
    pool_in: int,
    seats: list[int],
) -> None:
    if pool_in == 0:
        if f"{side}_distribution" in decreases:
            raise InvariantError(f"an empty {side} pool was distributed")
        return
    if decreases.get(f"{side}_distribution") != pool_in:
        raise InvariantError(f"the {side} journal does not consume the whole pool")

    per_seat = pool_in // len(seats) if seats else 0
    credited = {
        bucket: amount
        for bucket, amount in increases.items()
        if bucket.endswith(f":{side}")
    }
    if any(amount != per_seat for amount in credited.values()):
        raise InvariantError(f"a {side} seat credit is not the per-seat amount")
    if len(credited) != (len(seats) if per_seat else 0):
        raise InvariantError(f"the {side} credits do not cover the active seats")

    carry = increases.get(f"{side}_carry", 0)
    if seats and carry >= len(seats):
        raise InvariantError(f"the {side} carry is not below the active seat count")
    if carry != pool_in - per_seat * len(credited):
        raise InvariantError(f"the {side} carry is not the undistributed residue")


__all__ = [
    "DECREASE",
    "HANDLERS",
    "INCREASE",
    "apply_event",
    "assert_balanced",
    "simulate",
    "state_digest",
]
