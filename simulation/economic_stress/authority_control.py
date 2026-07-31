"""Rotation, containment, and recovery phase for one stress run."""

from __future__ import annotations

from simulation.authority.domain import domain_digest

from .authority_flow import AuthorityBuilder


def add_control_lifecycle(builder: AuthorityBuilder) -> dict[str, str]:
    delay = int(builder.config.values["authority_delay_epochs"])
    threshold = int(builder.config.values["authority_threshold"])
    schedule_id = _schedule(builder, delay, threshold)
    builder.advance(delay)
    activate_id = builder.append(
        "activate_rotation",
        actor="authority_clock",
        target_module="native_economy",
        target_capability="reward",
    )["id"]
    pause_id = _pause(builder)
    builder.advance(delay)
    recover_id = _recover(builder, threshold)
    return {
        "schedule": schedule_id,
        "activate": activate_id,
        "pause": pause_id,
        "recover": recover_id,
    }


def _schedule(builder: AuthorityBuilder, delay: int, threshold: int) -> str:
    next_members = ["next_a", "next_b", "next_c"]
    fields = {
        "target_module": "native_economy",
        "target_capability": "reward",
        "next_version": 2,
        "next_members": next_members,
        "next_threshold": threshold,
        "activation_epoch": delay,
    }
    action = {
        "kind": "schedule_rotation",
        "target_module": "native_economy",
        "target_capability": "reward",
        "set_id": "e_reward_set",
        **{key: value for key, value in fields.items() if key.startswith("next_")},
        "activation_epoch": delay,
    }
    return builder.add_control(
        "schedule_rotation",
        "rotation",
        "e_reward_set",
        1,
        builder.honest("operator") + builder.honest("next"),
        action,
        **fields,
    )


def _pause(builder: AuthorityBuilder) -> str:
    reason = domain_digest(
        "protocol-stack:economic-stress:containment-reason-v1",
        {"case_id": builder.config.case_id, "seed": builder.seed},
    )
    action = {
        "kind": "pause_capability",
        "target_module": "native_economy",
        "target_capability": "reward",
        "reason_digest": reason,
    }
    return builder.add_control(
        "pause_capability",
        "containment",
        "containment_set",
        1,
        builder.honest("contain"),
        action,
        target_module="native_economy",
        target_capability="reward",
        reason_digest=reason,
    )


def _recover(builder: AuthorityBuilder, threshold: int) -> str:
    rotation_succeeds = builder.config.honest_available >= threshold
    next_version = 3 if rotation_succeeds else 2
    replacement = ["replacement_a", "replacement_b", "replacement_c"]
    action = {
        "kind": "recover_capability",
        "target_module": "native_economy",
        "target_capability": "reward",
        "set_id": "e_reward_set",
        "next_version": next_version,
        "next_members": replacement,
        "next_threshold": threshold,
    }
    return builder.add_control(
        "recover_capability",
        "recovery",
        "recovery_set",
        1,
        builder.honest("recover") + builder.honest("replacement"),
        action,
        target_module="native_economy",
        target_capability="reward",
        next_version=next_version,
        next_members=replacement,
        next_threshold=threshold,
    )
