"""Ordered, failure-atomic threshold-authority simulation engine."""

from __future__ import annotations

from typing import Any, Callable

from .domain import Manifest, State, current_epoch, domain_digest, initial_state
from .handlers_control import HANDLERS as CONTROL_HANDLERS
from .handlers_operational import HANDLERS as OPERATIONAL_HANDLERS
from .invariants import assert_invariants
from .metrics import build_metrics
from .operations import Outcome, failure
from .serialization import state_digest, state_value
from .validation import parse_events, parse_manifest

Handler = Callable[[State, Manifest, dict[str, Any]], Outcome]
HANDLERS: dict[str, Handler] = {**OPERATIONAL_HANDLERS, **CONTROL_HANDLERS}
THRESHOLD_KINDS = {
    "authorize_action",
    "schedule_rotation",
    "pause_capability",
    "revoke_member",
    "recover_capability",
}


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
        "schema": "protocol-stack/authority-simulation-result/v1",
        "manifest_digest": domain_digest(
            "protocol-stack:authority:manifest-v1",
            manifest.source,
        ),
        "events_digest": domain_digest(
            "protocol-stack:authority:events-v1",
            events,
        ),
        "records": records,
        "trace_digest": domain_digest(
            "protocol-stack:authority:trace-v1",
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
    accepted_result_id: str | None = None
    accepted_action_id: str | None = None
    accepted_proof_ids: list[str] = []
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
            if event["kind"] in THRESHOLD_KINDS:
                accepted_result_id = event["result_id"]
                accepted_action_id = event["action_id"]
                accepted_proof_ids = sorted(
                    item["proof_id"] for item in event["approvals"]
                )
                candidate.accepted_result_ids.add(accepted_result_id)
                candidate.accepted_action_ids.add(accepted_action_id)
                candidate.accepted_proof_ids.update(accepted_proof_ids)
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
        "accepted_result_id": accepted_result_id,
        "accepted_action_id": accepted_action_id,
        "accepted_proof_ids": accepted_proof_ids,
    }
    if not outcome.accepted and digest_before != digest_after:
        raise AssertionError("failed authority event changed state")
    return candidate, record
