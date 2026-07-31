"""Nominal participation targets for one stress run."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from simulation.authority.domain import domain_digest
from simulation.native_economy.scenario import SplitMix64

from .design import Configuration


@dataclass(frozen=True)
class Flow:
    events: list[dict[str, Any]]
    privileged: dict[str, str]
    contribution_epoch: int


def build_participation_flow(
    config: Configuration,
    seed: int,
) -> Flow:
    stream = SplitMix64(seed ^ (config.case_index << 32))
    events: list[dict[str, Any]] = []
    privileged: dict[str, str] = {}
    height = 0
    sequence = 0
    proof_sequence = 0

    def proof() -> dict[str, str]:
        nonlocal proof_sequence
        proof_sequence += 1
        proof_id = f"p_proof_{proof_sequence:04d}"
        return {
            "proof_id": proof_id,
            "evidence_digest": domain_digest(
                "protocol-stack:economic-stress:evidence-v1",
                {
                    "case_id": config.case_id,
                    "seed": seed,
                    "proof_id": proof_id,
                    "kind": "participation",
                },
            ),
        }

    def append(kind: str, actor: str, capability: str | None, **fields: Any) -> None:
        nonlocal sequence
        sequence += 1
        event = {
            "id": f"p_event_{sequence:04d}",
            "height": height,
            "kind": kind,
            "actor": actor,
            **fields,
        }
        events.append(event)
        if capability is not None:
            privileged[event["id"]] = capability

    participants = (
        ("validator_a", "validator", "alice"),
        ("validator_b", "validator", "bob"),
        ("node_a", "node", "carol"),
        ("node_b", "node", "dave"),
    )
    for participant, role, owner in participants:
        fields = {
            "participant": participant,
            "owner": owner,
            "payout_account": owner,
            **proof(),
        }
        if role == "validator":
            fields["bond_id"] = f"stake_{participant[-1]}"
        append(f"register_{role}", "registrar", "registration", **fields)

    for participant, _, _ in participants[:2]:
        append(
            "confirm_bond",
            "stake_verifier",
            "stake",
            participant=participant,
            bond_id=f"stake_{participant[-1]}",
            amount=config.values["validator_minimum_bond"],
            **proof(),
        )

    activation_delay = int(config.values["activation_delay_epochs"])
    while height < activation_delay:
        append("advance_height", "clock", "clock", to_height=height + 1)
        height += 1
    for participant, _, _ in participants:
        append("activate", "lifecycle", "lifecycle", participant=participant)

    contribution_epoch = height
    for participant, role, _ in participants:
        if role == "validator":
            kind = "proposal" if participant == "validator_a" else "vote"
        else:
            kind = "compute" if participant == "node_a" else "storage"
        actor = "vote_verifier" if role == "validator" else "storage_verifier"
        capability = f"contribution/{role}/{kind}"
        append(
            "attest_contribution",
            actor,
            capability,
            participant=participant,
            role=role,
            contribution_kind=kind,
            epoch=contribution_epoch,
            units=1 + stream.bounded(20),
            **proof(),
        )

    append("advance_height", "clock", "clock", to_height=height + 1)
    height += 1
    budget = config.values["reward_budget_per_role"]
    for role, role_participants in (
        ("validator", ("validator_a", "validator_b")),
        ("node", ("node_a", "node_b")),
    ):
        append(
            "set_reward_budget",
            "reward",
            "reward",
            epoch=contribution_epoch,
            role=role,
            amount=budget,
        )
        for participant in role_participants:
            append(
                "settle_entitlement",
                "reward",
                "reward",
                epoch=contribution_epoch,
                role=role,
                participant=participant,
            )
        append(
            "finalize_budget",
            "reward",
            "reward",
            epoch=contribution_epoch,
            role=role,
        )

    append("request_exit", "bob", None, participant="validator_b")
    exit_delay = int(config.values["exit_unbond_delay_epochs"])
    target = height + exit_delay
    while height < target:
        append("advance_height", "clock", "clock", to_height=height + 1)
        height += 1
    append("complete_exit", "bob", None, participant="validator_b")
    return Flow(events, privileged, contribution_epoch)
