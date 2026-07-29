"""Ordered, failure-atomic simulation engine."""

from __future__ import annotations

from typing import Any, Callable

from .handlers_positions import HANDLERS as POSITION_HANDLERS
from .handlers_value import HANDLERS as VALUE_HANDLERS
from .metrics import build_metrics
from .operations import Outcome, failure
from .types import (
    Manifest,
    State,
    assert_invariants,
    current_epoch,
    domain_digest,
    initial_state,
    state_digest,
    state_value,
)
from .validation import parse_events, parse_manifest

Handler = Callable[[State, Manifest, dict[str, Any]], Outcome]
HANDLERS: dict[str, Handler] = {**VALUE_HANDLERS, **POSITION_HANDLERS}


def simulate(manifest_value: Any, events_value: Any) -> dict[str, Any]:
    manifest = (
        manifest_value
        if isinstance(manifest_value, Manifest)
        else parse_manifest(manifest_value)
    )
    events = parse_events(events_value)
    state = initial_state(manifest)
    records: list[dict[str, Any]] = []

    for index, event in enumerate(events):
        state, record = _apply_event(state, manifest, event, index)
        records.append(record)

    final_state = state_value(state)
    return {
        "schema": "protocol-stack/native-economy-simulation-result/v1",
        "manifest_digest": domain_digest(
            "protocol-stack:native-economy:manifest-v1",
            manifest.source,
        ),
        "events_digest": domain_digest(
            "protocol-stack:native-economy:events-v1",
            events,
        ),
        "records": records,
        "trace_digest": domain_digest(
            "protocol-stack:native-economy:trace-v1",
            records,
        ),
        "final_state": final_state,
        "metrics": build_metrics(state, manifest, records),
    }


def _apply_event(
    state: State,
    manifest: Manifest,
    event: dict[str, Any],
    index: int,
) -> tuple[State, dict[str, Any]]:
    height_before = state.height
    epoch_before = current_epoch(state, manifest)
    digest_before = state_digest(state)

    if event["height"] != state.height:
        outcome = failure("WRONG_HEIGHT")
        candidate = state
    elif event["id"] in state.accepted_event_ids:
        outcome = failure("REPLAY")
        candidate = state
    else:
        candidate = state.clone()
        outcome = HANDLERS[event["kind"]](candidate, manifest, event)
        if outcome.accepted:
            _assert_balanced(outcome.journal)
            candidate.accepted_event_ids.add(event["id"])
            assert_invariants(candidate, manifest)
        else:
            candidate = state
            if outcome.journal:
                raise AssertionError("failed event emitted a journal")

    digest_after = state_digest(candidate)
    record = {
        "index": index,
        "event_id": event["id"],
        "kind": event["kind"],
        "accepted": outcome.accepted,
        "result": outcome.code,
        "height_before": height_before,
        "height_after": candidate.height,
        "epoch_before": epoch_before,
        "epoch_after": current_epoch(candidate, manifest),
        "state_digest_before": digest_before,
        "state_digest_after": digest_after,
        "journal": outcome.journal,
    }
    if not outcome.accepted and digest_before != digest_after:
        raise AssertionError("failed event changed state")
    return candidate, record


def _assert_balanced(journal: list[dict[str, int | str]]) -> None:
    if sum(int(entry["delta"]) for entry in journal) != 0:
        raise AssertionError("accepted event journal is not balanced")
    if any(entry["delta"] == 0 for entry in journal):
        raise AssertionError("journal contains a zero entry")
