"""Clock and operational authority-result transitions."""

from __future__ import annotations

from typing import Any, Callable

from .domain import (
    MAX_U64,
    AuthorizationResult,
    Manifest,
    State,
    active_version,
    current_epoch,
)
from .operations import (
    Outcome,
    check_approvals,
    check_window,
    failure,
    success,
    threshold_prefix,
)


def advance_height(state: State, manifest: Manifest, event: dict[str, Any]) -> Outcome:
    if event["actor"] != manifest.clock:
        return failure("UNAUTHORIZED")
    if state.height == MAX_U64:
        return failure("OVERFLOW")
    if event["to_height"] != state.height + 1:
        return failure("INVALID_TARGET")
    state.height = event["to_height"]
    return success()


def authorize_action(
    state: State,
    manifest: Manifest,
    event: dict[str, Any],
) -> Outcome:
    prefix = threshold_prefix(state, manifest, event)
    if prefix is not None:
        return prefix
    binding = state.capabilities.get((event["module"], event["capability"]))
    if binding is None:
        return failure("NOT_FOUND")
    if binding.paused:
        return failure("PAUSED")
    version = active_version(binding)
    if (
        event["set_id"] != binding.set_id
        or event["set_version"] != version.version
    ):
        return failure("WRONG_SET")
    window = check_window(state, manifest, event)
    if window is not None:
        return window
    approvals = check_approvals(state, manifest, event, [version])
    if approvals is not None:
        return approvals
    state.authorization_results[event["result_id"]] = AuthorizationResult(
        result_id=event["result_id"],
        action_id=event["action_id"],
        chain_id=event["chain_id"],
        module=event["module"],
        capability=event["capability"],
        set_id=event["set_id"],
        set_version=event["set_version"],
        valid_from_epoch=event["valid_from_epoch"],
        deadline_epoch=event["deadline_epoch"],
        action_digest=event["action_digest"],
        authorized_height=state.height,
        authorized_epoch=current_epoch(state, manifest),
        approvals=sorted(
            (dict(item) for item in event["approvals"]),
            key=lambda item: (item["member"], item["proof_id"]),
        ),
    )
    return success()


Handler = Callable[[State, Manifest, dict[str, Any]], Outcome]
HANDLERS: dict[str, Handler] = {
    "advance_height": advance_height,
    "authorize_action": authorize_action,
}
