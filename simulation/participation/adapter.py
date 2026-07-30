"""Deterministic adapter from entitlements to native-economy claim funding."""

from __future__ import annotations

from typing import Any

from simulation.native_economy.domain import Manifest as EconomyManifest
from simulation.native_economy.validation import parse_manifest as parse_economy

from .domain import MAX_U64, Manifest, domain_digest
from .validation import parse_manifest


class AdapterError(ValueError):
    """The participation result cannot produce claim-funding events."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def build_funding_events(
    result: dict[str, Any],
    participation_manifest: Manifest | dict[str, Any],
    economy_manifest: EconomyManifest | dict[str, Any],
    *,
    epoch: int,
    role: str,
    height: int,
) -> list[dict[str, Any]]:
    participation = (
        participation_manifest
        if isinstance(participation_manifest, Manifest)
        else parse_manifest(participation_manifest)
    )
    economy = (
        economy_manifest
        if isinstance(economy_manifest, EconomyManifest)
        else parse_economy(economy_manifest)
    )
    _validate_adapter_inputs(result, participation, economy, epoch, role, height)
    budget = _find_record(result["final_state"]["budgets"], epoch, role)
    if budget is None or not budget["finalized"]:
        raise AdapterError("BUDGET_NOT_FINAL")
    entitlements = _nonzero_entitlements(result, epoch, role)
    for item in entitlements:
        _validate_participant(result, economy, item, role)
    return [
        _funding_event(result, economy, item, role, height)
        for item in entitlements
    ]


def _validate_adapter_inputs(
    result: dict[str, Any],
    participation: Manifest,
    economy: EconomyManifest,
    epoch: int,
    role: str,
    height: int,
) -> None:
    _validate_result(result, participation)
    if (
        role not in {"validator", "node"}
        or type(epoch) is not int
        or not 0 <= epoch <= MAX_U64
        or type(height) is not int
        or not 0 <= height <= MAX_U64
    ):
        raise AdapterError("MANIFEST_MISMATCH")
    if participation.authorities.reward != economy.authorities.reward:
        raise AdapterError("MANIFEST_MISMATCH")


def _nonzero_entitlements(
    result: dict[str, Any],
    epoch: int,
    role: str,
) -> list[dict[str, Any]]:
    return sorted(
        (
            item
            for item in result["final_state"]["entitlements"]
            if item["epoch"] == epoch and item["role"] == role and item["amount"] != 0
        ),
        key=lambda value: value["participant"],
    )


def _validate_participant(
    result: dict[str, Any],
    economy: EconomyManifest,
    item: dict[str, Any],
    role: str,
) -> None:
    participants = result["final_state"]["participants"]
    economy_participants = (
        economy.participants.validators
        if role == "validator"
        else economy.participants.nodes
    )
    participant = participants.get(item["participant"])
    if (
        participant is None
        or participant["role"] != role
        or economy_participants.get(item["participant"])
        != participant["payout_account"]
    ):
        raise AdapterError("MANIFEST_MISMATCH")


def _funding_event(
    result: dict[str, Any],
    economy: EconomyManifest,
    item: dict[str, Any],
    role: str,
    height: int,
) -> dict[str, Any]:
    digest_value = {
        "trace_digest": result["trace_digest"],
        "epoch": item["epoch"],
        "role": role,
        "participant": item["participant"],
        "amount": item["amount"],
        "height": height,
    }
    suffix = domain_digest(
        "protocol-stack:participation:funding-event-v1",
        digest_value,
    )[:32]
    return {
        "id": f"fund_{suffix}",
        "height": height,
        "kind": "allocate_reward",
        "actor": economy.authorities.reward,
        "role": role,
        "participant": item["participant"],
        "amount": item["amount"],
    }


def _validate_result(result: dict[str, Any], manifest: Manifest) -> None:
    if result.get("schema") != "protocol-stack/participation-simulation-result/v1":
        raise AdapterError("MANIFEST_MISMATCH")
    expected = domain_digest(
        "protocol-stack:participation:manifest-v1",
        manifest.source,
    )
    if result.get("manifest_digest") != expected:
        raise AdapterError("MANIFEST_MISMATCH")


def _find_record(
    records: list[dict[str, Any]],
    epoch: int,
    role: str,
) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in records
            if item["epoch"] == epoch and item["role"] == role
        ),
        None,
    )
