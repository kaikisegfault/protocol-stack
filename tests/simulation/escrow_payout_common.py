"""Shared escrow payout test inputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "simulation" / "escrow_payout" / "fixtures"
VECTORS_PATH = ROOT / "test-vectors" / "escrow-payout-v1.txt"
VECTORS_V2_PATH = ROOT / "test-vectors" / "escrow-payout-v2.txt"
VECTORS_V3_PATH = ROOT / "test-vectors" / "escrow-payout-v3.txt"
ECONOMY_FIXTURES = ROOT / "simulation" / "founder_economy" / "fixtures"
ECONOMY_MANIFEST = ROOT / "test-vectors" / "founder-economy-manifest-v1.json"
ECONOMY_V2_FIXTURES = ROOT / "simulation" / "founder_economy_v2" / "fixtures"
ECONOMY_V2_MANIFEST = ROOT / "test-vectors" / "founder-economy-manifest-v2.json"
ECONOMY_V3_FIXTURES = ROOT / "simulation" / "founder_economy_v3" / "fixtures"

VENTURE = "venture_escrow"
COMMUNITY = "community_grants_escrow"
DEVELOPER = "developer_incentives_escrow"


def research_events(version: str = "v1") -> list[dict[str, Any]]:
    return json.loads(
        (FIXTURES / f"research-events-{version}.json").read_text(encoding="utf-8")
    )


def vectors(path: Path | None = None) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in (path or VECTORS_PATH).read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            key, _, value = stripped.partition("=")
            values[key] = value
    return values


def economy_state() -> tuple[str, dict[str, Any]]:
    """Run the accepted economy fixture and return its digest and state value."""
    from simulation.founder_economy.engine import simulate as economy_simulate
    from simulation.founder_economy.manifest import load_manifest_file
    from simulation.founder_economy.validation import load_events_file

    result = economy_simulate(
        load_manifest_file(ECONOMY_MANIFEST),
        load_events_file(ECONOMY_FIXTURES / "research-events-v1.json"),
    )
    return result["state_digest"], result["final_state"]


def economy_state_v2() -> tuple[str, dict[str, Any]]:
    """The same for version two, which the v2 escrow binding must accept."""
    from simulation.founder_economy_v2.engine import simulate as economy_simulate
    from simulation.founder_economy_v2.manifest import load_manifest_file
    from simulation.founder_economy_v2.validation import load_events_file

    result = economy_simulate(
        load_manifest_file(ECONOMY_V2_MANIFEST),
        load_events_file(ECONOMY_V2_FIXTURES / "research-events-v2.json"),
    )
    return result["state_digest"], result["final_state"]


def economy_state_v3() -> tuple[str, dict[str, Any]]:
    """The same for version three, which loads the accepted v2 manifest.

    Version three re-versions the simulator and not the economic contract, so
    the manifest path is deliberately the same one version two uses.
    """
    from simulation.founder_economy_v2.manifest import load_manifest_file
    from simulation.founder_economy_v3.engine import simulate as economy_simulate
    from simulation.founder_economy_v3.validation import load_events_file

    result = economy_simulate(
        load_manifest_file(ECONOMY_V2_MANIFEST),
        load_events_file(ECONOMY_V3_FIXTURES / "research-events-v3.json"),
    )
    return result["state_digest"], result["final_state"]


def synthetic_state(custody: dict[str, str]) -> dict[str, Any]:
    """A minimal economy-shaped state value carrying only the custody keys."""
    return {
        "seats": {},
        "channels": {},
        "pending_permissions": {},
        "evaluated_permission_keys": [],
        "accepted_direct_decision_ids": [],
        "typed_custody": dict(custody),
    }


def bind(
    state_value: dict[str, Any] | None,
    digest: str | None = None,
    *,
    event_id: str = "bind-0001",
    version: str = "v1",
) -> dict[str, Any]:
    """Build a bind whose supplied digest defaults to the honest one.

    The honest digest is version specific, so a bind built for one version is
    rejected by the other. That is the property, not an inconvenience.
    """
    from simulation.common.canonical import digest as compute
    from simulation.escrow_payout import contract as c

    if state_value is None:
        supplied = None
    else:
        label = c.BINDINGS[version].economy_state_label
        supplied = {
            "state_digest": digest or compute(label, state_value),
            "state_value": state_value,
        }
    return {
        "id": event_id,
        "kind": "bind_opening_custody",
        "economy_state_result": supplied,
    }


def opening(**amounts: int) -> dict[str, Any]:
    """A bind of a synthetic state opening the named escrows."""
    custody = {f"{escrow}:global": str(amount) for escrow, amount in amounts.items()}
    return bind(synthetic_state(custody))


def grant(
    capability_id: str = "cap-0001",
    *,
    escrow: str = VENTURE,
    per_payout: int = 1_000,
    envelope: int = 10_000,
    expiry: int = 10,
    event_id: str | None = None,
) -> dict[str, Any]:
    return {
        "id": event_id or f"grant-{capability_id}",
        "kind": "grant_capability",
        "capability_id": capability_id,
        "escrow_id": escrow,
        "per_payout_maximum": str(per_payout),
        "envelope_total": str(envelope),
        "expiry_cycle": expiry,
    }


def approval(
    payout_id: str,
    *,
    decision: str = "approved",
    reference: str = "ai-evaluation-0001",
) -> dict[str, Any]:
    return {
        "payout_id": payout_id,
        "decision": decision,
        "evaluation_reference": reference,
    }


def payout(
    amount: int,
    *,
    payout_id: str = "payout-0001",
    capability_id: str = "cap-0001",
    escrow: str = VENTURE,
    recipient: str = "recipient-alpha",
    event_id: str | None = None,
    approve: dict[str, Any] | None = ...,  # type: ignore[assignment]
) -> dict[str, Any]:
    if approve is ...:
        approve = approval(payout_id)
    return {
        "id": event_id or payout_id,
        "kind": "execute_payout",
        "payout_id": payout_id,
        "capability_id": capability_id,
        "escrow_id": escrow,
        "recipient_id": recipient,
        "amount_atomic": str(amount),
        "approval_result": approve,
    }


def revoke(capability_id: str = "cap-0001", *, event_id: str | None = None):
    return {
        "id": event_id or f"revoke-{capability_id}",
        "kind": "revoke_capability",
        "capability_id": capability_id,
    }


def advance(cycle: int, *, event_id: str | None = None) -> dict[str, Any]:
    return {
        "id": event_id or f"advance-{cycle:04d}",
        "kind": "advance_cycle",
        "cycle_index": cycle,
    }


def codes(result: dict[str, Any]) -> list[str]:
    return [record["result"] for record in result["records"]]
