"""Ordered, failure-atomic Founder Economy v2 simulation engine."""

from __future__ import annotations

from typing import Any, Callable

from . import contract as c
from ..common.canonical import InvariantError, digest
from .domain import (
    STATE_LABEL,
    State,
    assert_invariants,
    initial_state,
    state_digest,
    state_value,
)
from .handlers_issuance import accrue_referral, direct_issue, exercise_permission
from .handlers_permissions import activate_seat, evaluate_base_permission
from .manifest import Manifest, load_manifest_file
from .metrics import build_metrics
from .operations import CARRY_BUCKET, JournalEntry, Outcome, failure, journal_delta
from .validation import parse_events

RESULT_SCHEMA = "protocol-stack/founder-economy-simulation-result/v2"
EVENTS_LABEL = "protocol-stack:founder-economy:events-v2"
TRACE_LABEL = "protocol-stack:founder-economy:trace-v2"
RESULT_LABEL = "protocol-stack:founder-economy:result-v2"

BASE_EVALUATION = "evaluate_base_permission"

Handler = Callable[[State, dict[str, Any]], Outcome]
HANDLERS: dict[str, Handler] = {
    "activate_seat": activate_seat,
    BASE_EVALUATION: evaluate_base_permission,
    "accrue_referral": accrue_referral,
    "exercise_permission": exercise_permission,
    "direct_issue": direct_issue,
}


def simulate(manifest: Manifest | str, events_value: Any) -> dict[str, Any]:
    """Run one deterministic simulation over an accepted v2 manifest."""
    accepted_manifest = (
        manifest if isinstance(manifest, Manifest) else load_manifest_file(manifest)
    )
    events = parse_events(events_value)

    state = initial_state()
    records: list[dict[str, Any]] = []
    for index, event in enumerate(events):
        state, record = apply_event(state, event, index)
        records.append(record)

    final_state = state_value(state)
    result = {
        "schema": RESULT_SCHEMA,
        "manifest_digest": accepted_manifest.manifest_digest,
        "manifest_canonical_length": accepted_manifest.canonical_length,
        "events_digest": digest(EVENTS_LABEL, events),
        "records": records,
        "trace_digest": digest(TRACE_LABEL, records),
        "final_state": final_state,
        "state_digest": digest(STATE_LABEL, final_state),
        "metrics": build_metrics(state),
    }
    result["result_digest"] = digest(RESULT_LABEL, result)
    return result


def apply_event(
    state: State,
    event: dict[str, Any],
    index: int,
) -> tuple[State, dict[str, Any]]:
    """Apply one event to a clone and commit only a balanced, valid outcome."""
    digest_before = state_digest(state)
    candidate = state.clone()
    try:
        outcome = HANDLERS[event["kind"]](candidate, event)
        if outcome.accepted:
            assert_balanced(outcome.journal, event["kind"])
            assert_invariants(candidate)
    except InvariantError:
        outcome = failure("INVARIANT")

    if not outcome.accepted:
        if outcome.journal:
            raise AssertionError("a rejected event emitted a journal")
        candidate = state

    digest_after = state_digest(candidate)
    if not outcome.accepted and digest_before != digest_after:
        raise AssertionError("a rejected event changed state")

    record = {
        "index": index,
        "event_id": event["id"],
        "kind": event["kind"],
        "accepted": outcome.accepted,
        "result": outcome.code,
        "state_digest_before": digest_before,
        "state_digest_after": digest_after,
        "journal": outcome.journal,
    }
    return candidate, record


def assert_balanced(journal: list[JournalEntry], kind: str) -> None:
    """Require every conservation dimension of an accepted journal."""
    channel_total = 0
    custody_total = 0
    issued_total = 0
    carry_total = 0
    founder_outstanding = 0
    for item in journal:
        delta = journal_delta(item)
        if delta == 0:
            raise InvariantError("journal contains a zero entry")
        bucket = item["bucket"]
        if bucket == CARRY_BUCKET:
            carry_total += delta
            continue
        if bucket.startswith("custody:"):
            custody_total += delta
            continue
        channel_total += delta
        if bucket.startswith("issued:"):
            issued_total += delta
        elif bucket == f"outstanding:{c.FOUNDER_CHANNEL}":
            founder_outstanding += delta
    if channel_total != 0:
        raise InvariantError("journal channel movements do not net to zero")
    if custody_total != issued_total:
        raise InvariantError("journal custody credits do not mirror issued supply")
    _assert_founder_portion(kind, carry_total, founder_outstanding)


def _assert_founder_portion(kind: str, carry_total: int, founder_outstanding: int) -> None:
    """Require each base evaluation to account exactly one Founder portion.

    The carry is unreserved capacity rather than a separate ledger dimension,
    so it does not belong in the channel balance above. What it must satisfy is
    the per-event form of the conservation identity: an active cycle reserves
    the whole portion, a reallocation reserves the pot less its remainder and
    leaves the remainder carried, and an empty winner set carries all of it.
    """
    if kind != BASE_EVALUATION:
        if carry_total != 0:
            raise InvariantError("only a base evaluation may move the performance carry")
        return
    if founder_outstanding + carry_total != c.FOUNDER_OPERATOR_LEG:
        raise InvariantError("a base evaluation did not account one Founder portion")


__all__ = ["HANDLERS", "apply_event", "assert_balanced", "simulate"]
