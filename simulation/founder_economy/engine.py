"""Ordered, failure-atomic Founder Economy simulation engine."""

from __future__ import annotations

from typing import Any, Callable

from .canonical import InvariantError, digest
from .domain import (
    STATE_LABEL,
    State,
    assert_invariants,
    initial_state,
    state_digest,
    state_value,
)
from .handlers_issuance import direct_issue, exercise_permission
from .handlers_permissions import (
    activate_seat,
    evaluate_base_permission,
    evaluate_referral_permission,
)
from .manifest import Manifest, load_manifest_file
from .metrics import build_metrics
from .operations import JournalEntry, Outcome, failure, journal_delta
from .validation import parse_events

RESULT_SCHEMA = "protocol-stack/founder-economy-simulation-result/v1"
EVENTS_LABEL = "protocol-stack:founder-economy:events-v1"
TRACE_LABEL = "protocol-stack:founder-economy:trace-v1"
RESULT_LABEL = "protocol-stack:founder-economy:result-v1"

Handler = Callable[[State, dict[str, Any]], Outcome]
HANDLERS: dict[str, Handler] = {
    "activate_seat": activate_seat,
    "evaluate_base_permission": evaluate_base_permission,
    "evaluate_referral_permission": evaluate_referral_permission,
    "exercise_permission": exercise_permission,
    "direct_issue": direct_issue,
}


def simulate(manifest: Manifest | str, events_value: Any) -> dict[str, Any]:
    """Run one deterministic simulation over an accepted manifest."""
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
            assert_balanced(outcome.journal)
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


def assert_balanced(journal: list[JournalEntry]) -> None:
    """Require both conservation dimensions of an accepted journal."""
    channel_total = 0
    custody_total = 0
    issued_total = 0
    for item in journal:
        delta = journal_delta(item)
        if delta == 0:
            raise InvariantError("journal contains a zero entry")
        bucket = item["bucket"]
        if bucket.startswith("custody:"):
            custody_total += delta
            continue
        channel_total += delta
        if bucket.startswith("issued:"):
            issued_total += delta
    if channel_total != 0:
        raise InvariantError("journal channel movements do not net to zero")
    if custody_total != issued_total:
        raise InvariantError("journal custody credits do not mirror issued supply")


__all__ = ["HANDLERS", "apply_event", "assert_balanced", "simulate"]
