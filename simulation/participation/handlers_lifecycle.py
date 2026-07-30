"""Height and participant lifecycle operations."""

from __future__ import annotations

from typing import Any

from .domain import (
    MAX_U64,
    Manifest,
    Participant,
    State,
    checked_add,
    current_epoch,
)
from .operations import Outcome, failure, success


def advance_height(state: State, manifest: Manifest, event: dict[str, Any]) -> Outcome:
    if event["actor"] != manifest.authorities.clock:
        return failure("UNAUTHORIZED")
    if state.height == MAX_U64:
        return failure("OVERFLOW")
    if event["to_height"] != state.height + 1:
        return failure("INVALID_TARGET")
    state.height = event["to_height"]
    return success()


def register_validator(
    state: State,
    manifest: Manifest,
    event: dict[str, Any],
) -> Outcome:
    return _register(state, manifest, event, "validator")


def register_node(
    state: State,
    manifest: Manifest,
    event: dict[str, Any],
) -> Outcome:
    return _register(state, manifest, event, "node")


def _register(
    state: State,
    manifest: Manifest,
    event: dict[str, Any],
    role: str,
) -> Outcome:
    if event["actor"] != manifest.authorities.registration:
        return failure("UNAUTHORIZED")
    if event["proof_id"] in state.accepted_proof_ids:
        return failure("PROOF_REPLAY")
    participant_id = event["participant"]
    if participant_id in state.participants:
        return failure("ALREADY_EXISTS")
    if len(state.participants) >= manifest.parameters.max_participants:
        return failure("LIMIT")
    epoch = current_epoch(state, manifest)
    activation_epoch = checked_add(epoch, manifest.parameters.activation_delay_epochs)
    if activation_epoch is None:
        return failure("OVERFLOW")
    state.participants[participant_id] = Participant(
        participant=participant_id,
        role=role,
        owner=event["owner"],
        payout_account=event["payout_account"],
        phase="pending",
        registered_epoch=epoch,
        activation_epoch=activation_epoch,
        activated_epoch=None,
        exit_epoch=None,
        unbond_ready_epoch=None,
        jailed_until_epoch=None,
        recovery_requested=False,
        bond_id=event.get("bond_id"),
        confirmed_bond=None,
        terminal_reason=None,
        removed_epoch=None,
    )
    return success()


def confirm_bond(state: State, manifest: Manifest, event: dict[str, Any]) -> Outcome:
    if event["actor"] != manifest.authorities.stake:
        return failure("UNAUTHORIZED")
    if event["proof_id"] in state.accepted_proof_ids:
        return failure("PROOF_REPLAY")
    participant = state.participants.get(event["participant"])
    if participant is None:
        return failure("NOT_FOUND")
    if participant.role != "validator":
        return failure("INVALID_ROLE")
    if participant.phase != "pending":
        return failure("INVALID_STATUS")
    if participant.confirmed_bond is not None:
        return failure("ALREADY_EXISTS")
    if event["bond_id"] != participant.bond_id:
        return failure("INVALID_TARGET")
    if event["amount"] == 0:
        return failure("ZERO_AMOUNT")
    if event["amount"] < manifest.parameters.validator_minimum_bond:
        return failure("BOND_REQUIRED")
    participant.confirmed_bond = event["amount"]
    return success()


def activate(state: State, manifest: Manifest, event: dict[str, Any]) -> Outcome:
    if event["actor"] != manifest.authorities.lifecycle:
        return failure("UNAUTHORIZED")
    participant = state.participants.get(event["participant"])
    if participant is None:
        return failure("NOT_FOUND")
    if participant.phase != "pending":
        return failure("INVALID_STATUS")
    epoch = current_epoch(state, manifest)
    if epoch < participant.activation_epoch:
        return failure("TOO_EARLY")
    if participant.role == "validator" and (
        participant.confirmed_bond is None
        or participant.confirmed_bond < manifest.parameters.validator_minimum_bond
    ):
        return failure("BOND_REQUIRED")
    participant.phase = "active"
    participant.activated_epoch = epoch
    return success()


def request_exit(state: State, manifest: Manifest, event: dict[str, Any]) -> Outcome:
    participant = state.participants.get(event["participant"])
    if participant is None:
        return failure("NOT_FOUND")
    if event["actor"] != participant.owner:
        return failure("UNAUTHORIZED")
    if participant.phase != "active":
        return failure("INVALID_STATUS")
    exit_epoch = checked_add(
        current_epoch(state, manifest),
        manifest.parameters.exit_delay_epochs,
    )
    if exit_epoch is None:
        return failure("OVERFLOW")
    participant.phase = "exit_pending"
    participant.exit_epoch = exit_epoch
    return success()


def complete_exit(state: State, manifest: Manifest, event: dict[str, Any]) -> Outcome:
    participant = state.participants.get(event["participant"])
    if participant is None:
        return failure("NOT_FOUND")
    if event["actor"] != participant.owner:
        return failure("UNAUTHORIZED")
    if participant.phase != "exit_pending":
        return failure("INVALID_STATUS")
    if participant.exit_epoch is None:
        raise AssertionError("exit-pending participant lacks exit epoch")
    if current_epoch(state, manifest) < participant.exit_epoch:
        return failure("TOO_EARLY")
    participant.phase = "exited"
    participant.jailed_until_epoch = None
    participant.recovery_requested = False
    if participant.role == "validator":
        participant.unbond_ready_epoch = participant.exit_epoch
    return success()


def jail(state: State, manifest: Manifest, event: dict[str, Any]) -> Outcome:
    if event["actor"] != manifest.authorities.enforcement:
        return failure("UNAUTHORIZED")
    if event["proof_id"] in state.accepted_proof_ids:
        return failure("PROOF_REPLAY")
    participant = state.participants.get(event["participant"])
    if participant is None:
        return failure("NOT_FOUND")
    if participant.phase not in {"active", "exit_pending"}:
        return failure("INVALID_STATUS")
    if participant.jailed_until_epoch is not None:
        return failure("INVALID_STATUS")
    epoch = current_epoch(state, manifest)
    maximum = checked_add(epoch, manifest.parameters.max_jail_epochs)
    if maximum is None:
        return failure("OVERFLOW")
    if not epoch < event["until_epoch"] <= maximum:
        return failure("INVALID_TARGET")
    participant.jailed_until_epoch = event["until_epoch"]
    participant.recovery_requested = False
    return success()


def request_recovery(
    state: State,
    manifest: Manifest,
    event: dict[str, Any],
) -> Outcome:
    participant = state.participants.get(event["participant"])
    if participant is None:
        return failure("NOT_FOUND")
    if event["actor"] != participant.owner:
        return failure("UNAUTHORIZED")
    if (
        participant.phase not in {"active", "exit_pending"}
        or participant.jailed_until_epoch is None
    ):
        return failure("INVALID_STATUS")
    epoch = current_epoch(state, manifest)
    if epoch < participant.jailed_until_epoch:
        return failure("TOO_EARLY")
    if participant.phase == "exit_pending" and epoch >= participant.exit_epoch:
        return failure("INVALID_STATUS")
    if participant.recovery_requested:
        return failure("ALREADY_EXISTS")
    participant.recovery_requested = True
    return success()


def recover(state: State, manifest: Manifest, event: dict[str, Any]) -> Outcome:
    if event["actor"] != manifest.authorities.lifecycle:
        return failure("UNAUTHORIZED")
    participant = state.participants.get(event["participant"])
    if participant is None:
        return failure("NOT_FOUND")
    if (
        participant.phase not in {"active", "exit_pending"}
        or participant.jailed_until_epoch is None
        or not participant.recovery_requested
    ):
        return failure("INVALID_STATUS")
    epoch = current_epoch(state, manifest)
    if epoch < participant.jailed_until_epoch:
        return failure("TOO_EARLY")
    if participant.phase == "exit_pending" and epoch >= participant.exit_epoch:
        return failure("INVALID_STATUS")
    participant.jailed_until_epoch = None
    participant.recovery_requested = False
    return success()


def remove(state: State, manifest: Manifest, event: dict[str, Any]) -> Outcome:
    if event["actor"] != manifest.authorities.enforcement:
        return failure("UNAUTHORIZED")
    if event["proof_id"] in state.accepted_proof_ids:
        return failure("PROOF_REPLAY")
    participant = state.participants.get(event["participant"])
    if participant is None:
        return failure("NOT_FOUND")
    if participant.phase in {"exited", "removed"}:
        return failure("INVALID_STATUS")
    epoch = current_epoch(state, manifest)
    if participant.role == "validator":
        readiness = checked_add(epoch, manifest.parameters.removal_hold_epochs)
        if readiness is None:
            return failure("OVERFLOW")
        if participant.exit_epoch is not None:
            readiness = max(readiness, participant.exit_epoch)
        participant.unbond_ready_epoch = readiness
    participant.phase = "removed"
    participant.jailed_until_epoch = None
    participant.recovery_requested = False
    participant.terminal_reason = event["reason"]
    participant.removed_epoch = epoch
    return success()


HANDLERS = {
    "advance_height": advance_height,
    "register_validator": register_validator,
    "register_node": register_node,
    "confirm_bond": confirm_bond,
    "activate": activate,
    "request_exit": request_exit,
    "complete_exit": complete_exit,
    "jail": jail,
    "request_recovery": request_recovery,
    "recover": recover,
    "remove": remove,
}
