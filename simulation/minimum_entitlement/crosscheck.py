"""Accepted participation and native-funding boundary replays."""

from __future__ import annotations

from simulation.native_economy.engine import simulate as simulate_economy
from simulation.participation.adapter import build_funding_events
from simulation.participation.domain import domain_digest
from simulation.participation.engine import simulate as simulate_participation
from simulation.reward_distribution.crosscheck import economy_manifest

from .model import evaluate_floor, identities, sum_u64, work_maps


def _digest(label: str) -> str:
    return domain_digest("protocol-stack:minimum-entitlement:evidence-v1", label)


def _event(event_id: str, height: int, kind: str, actor: str, **fields) -> dict:
    return {"id": event_id, "height": height, "kind": kind, "actor": actor, **fields}


def _participation_manifest(participant_count: int, selected_weight: int) -> dict:
    policies = {
        "honest": {"verifier": "honest_verifier", "weight": 1},
        "selected": {"verifier": "selected_verifier", "weight": selected_weight},
    }
    return {
        "schema": "protocol-stack/participation-simulation-manifest/v1",
        "research_only": True,
        "parameters": {
            "epoch_length": 1,
            "activation_delay_epochs": 1,
            "exit_delay_epochs": 1,
            "removal_hold_epochs": 1,
            "max_jail_epochs": 2,
            "max_participants": participant_count,
            "validator_minimum_bond": 1,
            "max_units_per_proof": 100,
            "max_units_per_participant_epoch": 100,
        },
        "authorities": {
            "clock": "clock",
            "registration": "registrar",
            "stake": "stake_verifier",
            "lifecycle": "lifecycle",
            "enforcement": "enforcement",
            "reward": "reward",
        },
        "contributions": {"validators": policies, "nodes": policies},
        "genesis": {"height": 0},
    }


def _participation_events(participants: dict, raw_units: dict, budget: int) -> list[dict]:
    events = []
    for index, (participant, identity) in enumerate(sorted(participants.items())):
        events.append(
            _event(
                f"register_{index}",
                0,
                "register_node",
                "registrar",
                participant=participant,
                owner=identity["principal"],
                payout_account=identity["payout_account"],
                proof_id=f"registration_proof_{index}",
                evidence_digest=_digest(f"register:{participant}"),
            )
        )
    events.append(_event("advance_1", 0, "advance_height", "clock", to_height=1))
    for index, participant in enumerate(sorted(participants)):
        events.append(
            _event(f"activate_{index}", 1, "activate", "lifecycle", participant=participant)
        )
    for index, (participant, units) in enumerate(sorted(raw_units.items())):
        kind = "honest" if participant == "honest" else "selected"
        events.append(
            _event(
                f"contribute_{index}",
                1,
                "attest_contribution",
                f"{kind}_verifier",
                participant=participant,
                role="node",
                contribution_kind=kind,
                epoch=1,
                units=units,
                proof_id=f"contribution_proof_{index}",
                evidence_digest=_digest(f"contribute:{participant}"),
            )
        )
    events.append(_event("advance_2", 1, "advance_height", "clock", to_height=2))
    events.append(
        _event(
            "set_budget", 2, "set_reward_budget", "reward", epoch=1, role="node", amount=budget
        )
    )
    for index, participant in enumerate(sorted(participants)):
        events.append(
            _event(
                f"settle_{index}",
                2,
                "settle_entitlement",
                "reward",
                epoch=1,
                role="node",
                participant=participant,
            )
        )
    events.append(
        _event("finalize_budget", 2, "finalize_budget", "reward", epoch=1, role="node")
    )
    return events


def _participation_evidence(coordinate: dict, identity_count: int) -> tuple[dict, dict, dict]:
    participants = identities(identity_count)
    raw_units, scores = work_maps(identity_count, coordinate["selected_weight"])
    manifest = _participation_manifest(len(participants), coordinate["selected_weight"])
    result = simulate_participation(
        manifest,
        _participation_events(participants, raw_units, coordinate["budget"]),
    )
    if not all(record["accepted"] for record in result["records"]):
        raise AssertionError("participation boundary replay failed")
    economy = economy_manifest(participants, coordinate["budget"])
    funding = build_funding_events(
        result, manifest, economy, epoch=1, role="node", height=0
    )
    actual = {item["participant"]: item["amount"] for item in funding}
    expected = evaluate_floor(
        coordinate["budget"],
        raw_units,
        scores,
        participants,
        "zero",
        0,
        "proportional",
    )["payouts"]
    if actual != expected:
        raise AssertionError("participation weighted-score replay changed zero floor")
    evidence = {
        **coordinate,
        "adapter_role": "node",
        "identity_count": identity_count,
        "participant_count": len(participants),
        "accepted_event_count": len(result["records"]),
        "adapter_funding_event_count": len(funding),
        "adapter_funded_amount": sum_u64(actual.values()),
        "participation_trace_digest": result["trace_digest"],
    }
    return evidence, raw_units, scores


def _fund_projection(
    coordinate: dict,
    participants: dict,
    observation: dict,
    case_suffix: str,
) -> dict:
    manifest = economy_manifest(participants, coordinate["budget"])
    events = [
        _event(
            f"pay_{index:02d}_{case_suffix}",
            0,
            "allocate_reward",
            "reward",
            role="node",
            participant=participant,
            amount=amount,
        )
        for index, (participant, amount) in enumerate(observation["payouts"].items())
        if amount != 0
    ]
    result = simulate_economy(manifest, events)
    failures = sum(int(not record["accepted"]) for record in result["records"])
    state = result["final_state"]
    claims = dict(sorted(state["node_claims"].items()))
    claim_total = sum_u64(claims.values())
    conserved = state["reward_pool"] + claim_total == coordinate["budget"]
    if failures or claims != observation["payouts"] or not conserved:
        raise AssertionError("native minimum-entitlement funding replay mismatch")
    return {
        "funding_event_count": len(events),
        "funding_failures": failures,
        "native_claim_amount": claim_total,
        "native_reward_pool": state["reward_pool"],
        "native_funding_conserved": conserved,
        "economy_trace_digest": result["trace_digest"],
    }


def boundary_cross_checks(design: dict) -> tuple[list[dict], list[dict]]:
    node_coordinates = [
        item for item in design["retained_coordinates"] if item["role"] == "node"
    ]
    selected = [node_coordinates[0], node_coordinates[-1]]
    participation = []
    funding = []
    for coordinate_index, coordinate in enumerate(selected):
        for identity_count in design["cross_check_identity_counts"]:
            evidence, raw_units, scores = _participation_evidence(
                coordinate, identity_count
            )
            participation.append(evidence)
            participants = identities(identity_count)
            for family in design["floor_families"]:
                floors = [0] if family == "zero" else design["cross_check_floors"]
                for floor in floors:
                    for mechanism in design["mechanisms"]:
                        observation = evaluate_floor(
                            coordinate["budget"],
                            raw_units,
                            scores,
                            participants,
                            family,
                            floor,
                            mechanism,
                        )
                        if not observation["feasible"]:
                            continue
                        suffix = f"{coordinate_index}_{identity_count}_{family[:2]}_{floor}_{mechanism[:2]}"
                        funded = _fund_projection(
                            coordinate, participants, observation, suffix
                        )
                        funding.append(
                            {
                                **coordinate,
                                "identity_count": identity_count,
                                "floor_family": family,
                                "floor": floor,
                                "mechanism": mechanism,
                                "calculated_payout": observation["paid_credit"],
                                **funded,
                            }
                        )
    return participation, funding
