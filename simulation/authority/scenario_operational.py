"""Operational threshold, domain, and replay attack scenario phase."""

from __future__ import annotations

from typing import Any

from .scenario_support import Builder


def add_operational_attacks(
    builder: Builder,
) -> tuple[dict[str, Any], dict[str, Any]]:
    issue_target, register_target = _targets(builder)
    builder.authorize(
        issue_target,
        "native_economy",
        "issuance",
        "issuance_set",
        1,
        [builder.approval("issuer_a")],
    )
    duplicate = builder.approval("issuer_a")
    builder.authorize(
        issue_target,
        "native_economy",
        "issuance",
        "issuance_set",
        1,
        [duplicate, builder.approval("issuer_a")],
    )
    builder.authorize(
        issue_target,
        "native_economy",
        "issuance",
        "issuance_set",
        1,
        [builder.approval("issuer_a"), builder.approval("outsider")],
    )
    builder.authorize(
        issue_target,
        "native_economy",
        "issuance",
        "issuance_set",
        1,
        [builder.approval("issuer_a"), builder.approval("issuer_b")],
        chain_id="other_chain",
    )
    builder.authorize(
        issue_target,
        "native_economy",
        "issuance",
        "issuance_set",
        1,
        [builder.approval("issuer_a"), builder.approval("issuer_b")],
        valid_from=1,
        deadline=2,
    )
    accepted = builder.authorize(
        issue_target,
        "native_economy",
        "issuance",
        "issuance_set",
        1,
        [builder.approval("issuer_a"), builder.approval("issuer_b")],
        result_id="result_issue",
        action_id="action_issue",
    )
    builder.events.append(dict(accepted))
    builder.authorize(
        issue_target,
        "native_economy",
        "issuance",
        "issuance_set",
        1,
        [builder.approval("issuer_a"), builder.approval("issuer_b")],
        result_id="result_issue",
    )
    builder.authorize(
        issue_target,
        "native_economy",
        "issuance",
        "issuance_set",
        1,
        [builder.approval("issuer_a"), builder.approval("issuer_b")],
        action_id="action_issue",
    )
    builder.authorize(
        issue_target,
        "native_economy",
        "issuance",
        "issuance_set",
        1,
        [accepted["approvals"][0], builder.approval("issuer_c")],
    )
    builder.authorize(
        register_target,
        "participation",
        "registration",
        "registration_set",
        1,
        [builder.approval("registrar_a"), builder.approval("registrar_b")],
        result_id="result_register",
        action_id="action_register",
    )
    builder.authorize(
        register_target,
        "participation",
        "registration",
        "issuance_set",
        1,
        [builder.approval("issuer_a"), builder.approval("issuer_b")],
    )
    return issue_target, register_target


def _targets(builder: Builder) -> tuple[dict[str, Any], dict[str, Any]]:
    issue_target = {
        "id": "target_issue",
        "height": 0,
        "kind": "issue",
        "actor": "issuer",
        "amount": 1 + builder.stream.bounded(100),
    }
    register_target = {
        "id": "target_register",
        "height": 0,
        "kind": "register_node",
        "actor": "registrar",
        "participant": "node_a",
        "owner": "alice",
        "payout_account": "alice",
        "proof_id": "registration_proof",
        "evidence_digest": "a" * 64,
    }
    return issue_target, register_target
