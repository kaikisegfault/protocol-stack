"""Ordered, failure-atomic participation simulation engine."""

from __future__ import annotations

from typing import Any, Callable

from .domain import (
    Manifest,
    State,
    current_epoch,
    domain_digest,
    initial_state,
)
from .handlers_lifecycle import HANDLERS as LIFECYCLE_HANDLERS
from .handlers_rewards import HANDLERS as REWARD_HANDLERS
from .invariants import assert_invariants
from .metrics import build_metrics
from .operations import Outcome, failure
from .serialization import state_digest, state_value
from .validation import parse_events, parse_manifest

Handler = Callable[[State, Manifest, dict[str, Any]], Outcome]
HANDLERS: dict[str, Handler] = {**LIFECYCLE_HANDLERS, **REWARD_HANDLERS}


def simulate(manifest_value: Any, events_value: Any) -> dict[str, Any]:
    manifest = (
        manifest_value
        if isinstance(manifest_value, Manifest)
        else parse_manifest(manifest_value)
    )
    events = parse_events(events_value)
    state = initial_state(manifest)
    assert_invariants(state, manifest)
    records: list[dict[str, Any]] = []
    for index, event in enumerate(events):
        state, record = _apply_event(state, manifest, event, index)
        records.append(record)
    return {
        "schema": "protocol-stack/participation-simulation-result/v1",
        "manifest_digest": domain_digest(
            "protocol-stack:participation:manifest-v1",
            manifest.source,
        ),
        "events_digest": domain_digest(
            "protocol-stack:participation:events-v1",
            events,
        ),
        "records": records,
        "trace_digest": domain_digest(
            "protocol-stack:participation:trace-v1",
            records,
        ),
        "final_state": state_value(state),
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
    accepted_proof_id: str | None = None
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
            candidate.accepted_event_ids.add(event["id"])
            if "proof_id" in event:
                accepted_proof_id = event["proof_id"]
                candidate.accepted_proof_ids.add(accepted_proof_id)
            assert_invariants(candidate, manifest)
        else:
            candidate = state
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
        "accepted_proof_id": accepted_proof_id,
    }
    if not outcome.accepted and digest_before != digest_after:
        raise AssertionError("failed event changed participation state")
    return candidate, record
