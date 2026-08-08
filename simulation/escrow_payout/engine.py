"""Ordered, failure-atomic escrow payout engine.

Handlers are pure, so the engine never copies state to obtain atomicity. It
re-derives every journalled amount from the event and the pre-state, which is
what makes the journal an independent check rather than a restatement of the
handler's own arithmetic.
"""

from __future__ import annotations

from typing import Any, Callable

from . import contract as c
from ..common.canonical import InvariantError, digest, required_sum
from .domain import State, assert_invariants, initial_state, state_digest, state_value
from .handlers_binding import bind_opening_custody
from .handlers_capability import advance_cycle, grant_capability, revoke_capability
from .handlers_payout import execute_payout
from .metrics import build_metrics
from .operations import (
    DECREASE,
    INCREASE,
    BindEffect,
    Outcome,
    PayoutEffect,
    apply_effect,
    failure,
    journal_delta,
)
from .validation import parse_events

Handler = Callable[[State, dict[str, Any]], Outcome]

HANDLERS: dict[str, Handler] = {
    "bind_opening_custody": bind_opening_custody,
    "grant_capability": grant_capability,
    "execute_payout": execute_payout,
    "revoke_capability": revoke_capability,
    "advance_cycle": advance_cycle,
}

# Empty by contract: these transitions move no value.
SILENT_KINDS = frozenset({"grant_capability", "revoke_capability", "advance_cycle"})

# Full invariants are O(capabilities + credited recipients), so a long run
# checks them on a bounded schedule plus at both ends rather than every event.
INVARIANT_STRIDE = 64


def handlers_for(binding: c.Binding) -> dict[str, Handler]:
    """Bind the one version-specific handler and leave the rest untouched.

    Only `bind_opening_custody` reads the economy contract, so the other four
    transitions are shared rather than re-declared per version. A version that
    needed a second version-specific handler would replace it here and would be
    visible in this one table.
    """

    def bind(state: State, event: dict[str, Any]) -> Outcome:
        return bind_opening_custody(state, event, binding)

    return {**HANDLERS, "bind_opening_custody": bind}


def simulate(
    events_value: Any,
    *,
    binding: c.Binding = c.V1,
    invariant_stride: int = INVARIANT_STRIDE,
) -> dict[str, Any]:
    """Run one deterministic escrow payout simulation under one binding."""
    events = parse_events(events_value)
    state = initial_state()
    assert_invariants(state)

    records: list[dict[str, Any]] = []
    for index, event in enumerate(events):
        record = apply_event(state, event, index, binding=binding)
        records.append(record)
        if invariant_stride and record["accepted"] and index % invariant_stride == 0:
            assert_invariants(state)
    assert_invariants(state)

    final_state = state_value(state)
    result = {
        "schema": binding.schema,
        "events_digest": digest(binding.events_label, events),
        "records": records,
        "trace_digest": digest(binding.trace_label, records),
        "final_state": final_state,
        "state_digest": digest(binding.state_label, final_state),
        "metrics": build_metrics(state),
    }
    result["result_digest"] = digest(binding.result_label, result)
    return result


def apply_event(
    state: State,
    event: dict[str, Any],
    index: int,
    *,
    binding: c.Binding = c.V1,
) -> dict[str, Any]:
    """Evaluate one event and commit it only if it was accepted."""
    summary_before = state.summary()
    try:
        outcome = handlers_for(binding)[event["kind"]](state, event)
        if outcome.accepted:
            assert_balanced(outcome, state, event)
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


def assert_balanced(outcome: Outcome, state: State, event: dict[str, Any]) -> None:
    """Re-derive every journalled amount from the event and the pre-state."""
    increases, decreases = _totals(outcome.journal)
    if sum(increases.values()) != sum(decreases.values()):
        raise InvariantError("journal increases do not equal journal decreases")

    kind = event["kind"]
    if kind in SILENT_KINDS:
        if outcome.journal:
            raise InvariantError(f"{kind} emitted a journal")
    elif kind == "bind_opening_custody":
        _assert_bind(increases, decreases, outcome.effect)
    else:
        _assert_payout(increases, decreases, state, event, outcome.effect)


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


def _assert_bind(
    increases: dict[str, int],
    decreases: dict[str, int],
    effect: object,
) -> None:
    if type(effect) is not BindEffect:
        raise InvariantError("an accepted bind produced no binding effect")

    opening = dict(effect.opening)
    if set(opening) != set(c.ESCROW_IDS):
        raise InvariantError("a bind did not derive every escrow")
    total = required_sum(list(opening.values()), "bound opening custody")

    expected_out = {"economy_custody": total} if total else {}
    expected_in = {
        f"custody:{escrow_id}": amount
        for escrow_id, amount in opening.items()
        if amount != 0
    }
    if decreases != expected_out or increases != expected_in:
        raise InvariantError("the journal does not credit the bound opening custody")


def _assert_payout(
    increases: dict[str, int],
    decreases: dict[str, int],
    state: State,
    event: dict[str, Any],
    effect: object,
) -> None:
    if type(effect) is not PayoutEffect:
        raise InvariantError("an accepted payout produced no payout effect")

    amount = int(event["amount_atomic"])
    escrow_id = state.capabilities[event["capability_id"]].escrow_id
    if escrow_id != effect.escrow_id:
        raise InvariantError("a payout charged an escrow the capability does not hold")
    if decreases != {f"custody:{escrow_id}": amount}:
        raise InvariantError("the journal does not consume exactly the payout")
    if increases != {f"recipient:{escrow_id}:{effect.recipient_id}": amount}:
        raise InvariantError("the journal does not credit exactly the recipient")

    if effect.available_custody != state.available_custody[escrow_id] - amount:
        raise InvariantError("a payout did not reduce the escrow by its amount")


__all__ = [
    "DECREASE",
    "HANDLERS",
    "INCREASE",
    "apply_event",
    "assert_balanced",
    "handlers_for",
    "simulate",
    "state_digest",
]
