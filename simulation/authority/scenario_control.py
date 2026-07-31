"""Rotation, containment, revocation, and recovery scenario phase."""

from __future__ import annotations

from typing import Any

from .domain import domain_digest
from .scenario_support import Builder


def add_control_lifecycle(
    builder: Builder,
    issue_target: dict[str, Any],
    register_target: dict[str, Any],
) -> None:
    _issuance_rotation(builder)
    reason = _registration_containment(builder, register_target)
    builder.advance_to(20)
    _recovery(
        builder,
        "participation",
        "registration",
        ["registrar_d", "registrar_e", "registrar_f"],
        2,
    )
    _activate_and_revoke_issuance(builder, issue_target, reason)
    builder.advance_to(40)
    _recovery(
        builder,
        "native_economy",
        "issuance",
        ["issuer_g", "issuer_h", "issuer_i"],
        3,
    )


def _issuance_rotation(builder: Builder) -> None:
    next_members = ["issuer_d", "issuer_e", "issuer_f"]
    fields = _rotation_fields(
        "native_economy",
        "issuance",
        next_members,
    )
    action = _rotation_action("issuance_set", fields)
    builder.control(
        "schedule_rotation",
        "rotation",
        action,
        "issuance_set",
        1,
        [builder.approval("issuer_a"), builder.approval("issuer_b")],
        **fields,
    )
    builder.control(
        "schedule_rotation",
        "rotation",
        action,
        "issuance_set",
        1,
        [
            builder.approval("issuer_a"),
            builder.approval("issuer_b"),
            builder.approval("issuer_d"),
            builder.approval("issuer_e"),
        ],
        **fields,
    )
    builder.append(
        "activate_rotation",
        actor="clock",
        target_module="native_economy",
        target_capability="issuance",
    )


def _registration_containment(
    builder: Builder,
    register_target: dict[str, Any],
) -> str:
    next_members = ["registrar_d", "registrar_e", "registrar_f"]
    fields = _rotation_fields(
        "participation",
        "registration",
        next_members,
    )
    action = _rotation_action("registration_set", fields)
    builder.control(
        "schedule_rotation",
        "rotation",
        action,
        "registration_set",
        1,
        [
            builder.approval("registrar_a"),
            builder.approval("registrar_b"),
            builder.approval("registrar_d"),
            builder.approval("registrar_e"),
        ],
        **fields,
    )
    reason = domain_digest(
        "protocol-stack:authority:scenario-reason-v1",
        {"seed": builder.seed},
    )
    pause_action = {
        "kind": "pause_capability",
        "target_module": "participation",
        "target_capability": "registration",
        "reason_digest": reason,
    }
    mutated = _pause(builder, pause_action, reason)
    mutated["action_digest"] = "f" * 64
    _pause(builder, pause_action, reason)
    builder.authorize(
        register_target,
        "participation",
        "registration",
        "registration_set",
        1,
        [builder.approval("registrar_a"), builder.approval("registrar_b")],
    )
    builder.append(
        "activate_rotation",
        actor="clock",
        target_module="participation",
        target_capability="registration",
    )
    _recovery(builder, "participation", "registration", next_members, 2)
    return reason


def _activate_and_revoke_issuance(
    builder: Builder,
    issue_target: dict[str, Any],
    reason: str,
) -> None:
    builder.append(
        "activate_rotation",
        actor="clock",
        target_module="native_economy",
        target_capability="issuance",
    )
    builder.authorize(
        issue_target,
        "native_economy",
        "issuance",
        "issuance_set",
        1,
        [builder.approval("issuer_a"), builder.approval("issuer_b")],
        valid_from=0,
        deadline=0,
    )
    builder.authorize(
        issue_target,
        "native_economy",
        "issuance",
        "issuance_set",
        2,
        [builder.approval("issuer_d"), builder.approval("issuer_e")],
        valid_from=0,
        deadline=0,
    )
    builder.authorize(
        issue_target,
        "native_economy",
        "issuance",
        "issuance_set",
        2,
        [builder.approval("issuer_d"), builder.approval("issuer_e")],
        result_id="result_rotated_issue",
        action_id="action_rotated_issue",
        valid_from=2,
        deadline=3,
    )
    action = {
        "kind": "revoke_member",
        "target_module": "native_economy",
        "target_capability": "issuance",
        "member": "issuer_d",
        "reason_digest": reason,
    }
    builder.control(
        "revoke_member",
        "containment",
        action,
        "containment_set",
        1,
        [builder.approval("contain_a"), builder.approval("contain_c")],
        target_module="native_economy",
        target_capability="issuance",
        member="issuer_d",
        reason_digest=reason,
    )
    builder.authorize(
        issue_target,
        "native_economy",
        "issuance",
        "issuance_set",
        2,
        [builder.approval("issuer_e"), builder.approval("issuer_f")],
        valid_from=2,
        deadline=3,
    )


def _pause(
    builder: Builder,
    action: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    return builder.control(
        "pause_capability",
        "containment",
        action,
        "containment_set",
        1,
        [builder.approval("contain_a"), builder.approval("contain_b")],
        target_module="participation",
        target_capability="registration",
        reason_digest=reason,
    )


def _recovery(
    builder: Builder,
    module: str,
    capability: str,
    members: list[str],
    version: int,
) -> None:
    epoch = builder.height // builder.manifest.parameters.epoch_length
    set_id = "registration_set" if capability == "registration" else "issuance_set"
    action = {
        "kind": "recover_capability",
        "target_module": module,
        "target_capability": capability,
        "set_id": set_id,
        "next_version": version,
        "next_members": members,
        "next_threshold": 2,
    }
    builder.control(
        "recover_capability",
        "recovery",
        action,
        "recovery_set",
        1,
        [
            builder.approval("recover_a"),
            builder.approval("recover_b"),
            builder.approval(members[0]),
            builder.approval(members[1]),
        ],
        valid_from=epoch,
        deadline=epoch + 2,
        target_module=module,
        target_capability=capability,
        next_version=version,
        next_members=members,
        next_threshold=2,
    )


def _rotation_fields(
    module: str,
    capability: str,
    members: list[str],
) -> dict[str, Any]:
    return {
        "target_module": module,
        "target_capability": capability,
        "next_version": 2,
        "next_members": members,
        "next_threshold": 2,
        "activation_epoch": 1,
    }


def _rotation_action(
    set_id: str,
    fields: dict[str, Any],
) -> dict[str, Any]:
    return {
        "kind": "schedule_rotation",
        "target_module": fields["target_module"],
        "target_capability": fields["target_capability"],
        "set_id": set_id,
        "next_version": fields["next_version"],
        "next_members": fields["next_members"],
        "next_threshold": fields["next_threshold"],
        "activation_epoch": fields["activation_epoch"],
    }
