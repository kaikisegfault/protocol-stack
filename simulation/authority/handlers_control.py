"""Versioned rotation, containment, revocation, and recovery transitions."""

from __future__ import annotations

from typing import Any, Callable

from .domain import (
    Capability,
    Manifest,
    PendingRotation,
    State,
    Version,
    active_version,
    checked_add,
    control_digest,
    current_epoch,
)
from .operations import (
    Outcome,
    check_approvals,
    check_window,
    failure,
    proposed_set,
    success,
    threshold_prefix,
)


def schedule_rotation(
    state: State,
    manifest: Manifest,
    event: dict[str, Any],
) -> Outcome:
    prefix = threshold_prefix(state, manifest, event)
    if prefix is not None:
        return prefix
    binding = _binding(state, event)
    if binding is None:
        return failure("NOT_FOUND")
    current = active_version(binding)
    if event["set_id"] != binding.set_id or event["set_version"] != current.version:
        return failure("WRONG_SET")
    if binding.paused:
        return failure("PAUSED")
    if binding.pending_rotation is not None:
        return failure("ALREADY_EXISTS")
    if len(binding.versions) >= manifest.parameters.max_versions_per_capability:
        return failure("LIMIT")
    next_version = checked_add(current.version, 1)
    if next_version is None:
        return failure("OVERFLOW")
    if event["next_version"] != next_version:
        return failure("INVALID_TARGET")
    proposed = proposed_set(manifest, event, binding.set_id)
    if isinstance(proposed, Outcome):
        return proposed
    epoch = current_epoch(state, manifest)
    minimum = checked_add(epoch, manifest.parameters.min_rotation_delay_epochs)
    maximum = checked_add(epoch, manifest.parameters.max_rotation_delay_epochs)
    if minimum is None or maximum is None:
        return failure("OVERFLOW")
    if not minimum <= event["activation_epoch"] <= maximum:
        return failure("INVALID_TARGET")
    window = check_window(state, manifest, event)
    if window is not None:
        return window
    action = _schedule_action(event, binding)
    if event["action_digest"] != control_digest(manifest, event, "rotation", action):
        return failure("DIGEST_MISMATCH")
    approvals = check_approvals(state, manifest, event, [current, proposed])
    if approvals is not None:
        return approvals
    binding.pending_rotation = PendingRotation(
        version=event["next_version"],
        members=list(event["next_members"]),
        threshold=event["next_threshold"],
        activation_epoch=event["activation_epoch"],
        result_id=event["result_id"],
        action_id=event["action_id"],
        action_digest=event["action_digest"],
    )
    return success()


def activate_rotation(
    state: State,
    manifest: Manifest,
    event: dict[str, Any],
) -> Outcome:
    if event["actor"] != manifest.clock:
        return failure("UNAUTHORIZED")
    binding = _binding(state, event)
    if binding is None:
        return failure("NOT_FOUND")
    if binding.pending_rotation is None:
        return failure("NOT_FOUND")
    if binding.paused:
        return failure("PAUSED")
    pending = binding.pending_rotation
    if current_epoch(state, manifest) < pending.activation_epoch:
        return failure("TOO_EARLY")
    _replace_version(binding, pending, current_epoch(state, manifest), "rotation")
    binding.pending_rotation = None
    return success()


def pause_capability(
    state: State,
    manifest: Manifest,
    event: dict[str, Any],
) -> Outcome:
    prefix = threshold_prefix(state, manifest, event)
    if prefix is not None:
        return prefix
    if not _matches_set(event, manifest.containment):
        return failure("WRONG_SET")
    binding = _binding(state, event)
    if binding is None:
        return failure("NOT_FOUND")
    if binding.paused:
        return failure("ALREADY_EXISTS")
    window = check_window(state, manifest, event)
    if window is not None:
        return window
    action = {
        "kind": "pause_capability",
        "target_module": event["target_module"],
        "target_capability": event["target_capability"],
        "reason_digest": event["reason_digest"],
    }
    if event["action_digest"] != control_digest(
        manifest, event, "containment", action
    ):
        return failure("DIGEST_MISMATCH")
    approvals = check_approvals(state, manifest, event, [manifest.containment])
    if approvals is not None:
        return approvals
    _pause(binding, state, manifest, event["reason_digest"])
    return success()


def revoke_member(
    state: State,
    manifest: Manifest,
    event: dict[str, Any],
) -> Outcome:
    prefix = threshold_prefix(state, manifest, event)
    if prefix is not None:
        return prefix
    if not _matches_set(event, manifest.containment):
        return failure("WRONG_SET")
    binding = _binding(state, event)
    if binding is None:
        return failure("NOT_FOUND")
    if binding.paused:
        return failure("ALREADY_EXISTS")
    version = active_version(binding)
    if event["member"] not in version.members:
        return failure("INVALID_TARGET")
    if event["member"] in version.revoked_members:
        return failure("ALREADY_EXISTS")
    window = check_window(state, manifest, event)
    if window is not None:
        return window
    action = {
        "kind": "revoke_member",
        "target_module": event["target_module"],
        "target_capability": event["target_capability"],
        "member": event["member"],
        "reason_digest": event["reason_digest"],
    }
    if event["action_digest"] != control_digest(
        manifest, event, "containment", action
    ):
        return failure("DIGEST_MISMATCH")
    approvals = check_approvals(state, manifest, event, [manifest.containment])
    if approvals is not None:
        return approvals
    version.revoked_members.append(event["member"])
    version.revoked_members.sort()
    _pause(binding, state, manifest, event["reason_digest"])
    return success()


def recover_capability(
    state: State,
    manifest: Manifest,
    event: dict[str, Any],
) -> Outcome:
    prefix = threshold_prefix(state, manifest, event)
    if prefix is not None:
        return prefix
    if not _matches_set(event, manifest.recovery):
        return failure("WRONG_SET")
    binding = _binding(state, event)
    if binding is None:
        return failure("NOT_FOUND")
    if not binding.paused:
        return failure("INVALID_STATUS")
    if len(binding.versions) >= manifest.parameters.max_versions_per_capability:
        return failure("LIMIT")
    current = active_version(binding)
    next_version = checked_add(current.version, 1)
    if next_version is None:
        return failure("OVERFLOW")
    if event["next_version"] != next_version:
        return failure("INVALID_TARGET")
    proposed = proposed_set(manifest, event, binding.set_id)
    if isinstance(proposed, Outcome):
        return proposed
    ready = checked_add(
        binding.paused_epoch,
        manifest.parameters.recovery_delay_epochs,
    )
    if ready is None:
        return failure("OVERFLOW")
    if current_epoch(state, manifest) < ready:
        return failure("TOO_EARLY")
    window = check_window(state, manifest, event)
    if window is not None:
        return window
    action = {
        "kind": "recover_capability",
        "target_module": event["target_module"],
        "target_capability": event["target_capability"],
        "set_id": binding.set_id,
        "next_version": event["next_version"],
        "next_members": list(event["next_members"]),
        "next_threshold": event["next_threshold"],
    }
    if event["action_digest"] != control_digest(manifest, event, "recovery", action):
        return failure("DIGEST_MISMATCH")
    approvals = check_approvals(
        state, manifest, event, [manifest.recovery, proposed]
    )
    if approvals is not None:
        return approvals
    pending = PendingRotation(
        version=event["next_version"],
        members=list(event["next_members"]),
        threshold=event["next_threshold"],
        activation_epoch=current_epoch(state, manifest),
        result_id=event["result_id"],
        action_id=event["action_id"],
        action_digest=event["action_digest"],
    )
    _replace_version(binding, pending, current_epoch(state, manifest), "recovery")
    binding.paused = False
    binding.paused_epoch = None
    binding.pause_reason_digest = None
    binding.pending_rotation = None
    return success()


def _binding(state: State, event: dict[str, Any]) -> Capability | None:
    return state.capabilities.get(
        (event["target_module"], event["target_capability"])
    )


def _matches_set(event: dict[str, Any], authority_set: Any) -> bool:
    return (
        event["set_id"] == authority_set.set_id
        and event["set_version"] == authority_set.version
    )


def _schedule_action(event: dict[str, Any], binding: Capability) -> dict[str, Any]:
    return {
        "kind": "schedule_rotation",
        "target_module": event["target_module"],
        "target_capability": event["target_capability"],
        "set_id": binding.set_id,
        "next_version": event["next_version"],
        "next_members": list(event["next_members"]),
        "next_threshold": event["next_threshold"],
        "activation_epoch": event["activation_epoch"],
    }


def _pause(
    binding: Capability,
    state: State,
    manifest: Manifest,
    reason_digest: str,
) -> None:
    binding.paused = True
    binding.paused_epoch = current_epoch(state, manifest)
    binding.pause_reason_digest = reason_digest
    binding.pending_rotation = None


def _replace_version(
    binding: Capability,
    pending: PendingRotation,
    epoch: int,
    source: str,
) -> None:
    active_version(binding).retired_epoch = epoch
    binding.versions.append(
        Version(
            version=pending.version,
            members=list(pending.members),
            threshold=pending.threshold,
            activated_epoch=epoch,
            retired_epoch=None,
            source=source,
        )
    )
    binding.active_version = pending.version


Handler = Callable[[State, Manifest, dict[str, Any]], Outcome]
HANDLERS: dict[str, Handler] = {
    "schedule_rotation": schedule_rotation,
    "activate_rotation": activate_rotation,
    "pause_capability": pause_capability,
    "revoke_member": revoke_member,
    "recover_capability": recover_capability,
}
