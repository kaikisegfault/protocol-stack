"""Accepted participation, funding, and refundable-lock cross-checks."""

from __future__ import annotations

from simulation.native_economy.engine import simulate as simulate_economy
from simulation.reward_distribution.crosscheck import cross_check_proportional

from .model import identities, scores


def _event(event_id: str, height: int, kind: str, actor: str, **fields) -> dict:
    return {"id": event_id, "height": height, "kind": kind, "actor": actor, **fields}


def _lock_manifest() -> dict:
    accounts = {f"identity_{index:02d}": 1 for index in range(16)}
    return {
        "schema": "protocol-stack/native-economy-simulation-manifest/v1",
        "research_only": True,
        "parameters": {
            "supply_limit": 16,
            "epoch_length": 1,
            "unbonding_epochs": 1,
            "fee_split_denominator": 1,
            "fee_reward_parts": 0,
        },
        "authorities": {
            "clock": "clock",
            "issuance": "issuer",
            "fee_allocation": "fee_allocator",
            "treasury": "treasury",
            "escrow": "escrow",
            "reward": "reward",
            "penalty": "penalty",
        },
        "participants": {"validators": {}, "nodes": {}},
        "genesis": {
            "height": 0,
            "issued_supply": 16,
            "accounts": accounts,
            "fee_pool": 0,
            "treasury": 0,
            "reward_pool": 0,
            "penalty_pool": 0,
        },
    }


def _open(event_id: str, height: int, index: int, unlock: int) -> dict:
    account = f"identity_{index:02d}"
    return _event(
        event_id,
        height,
        "open_escrow",
        account,
        escrow_id=f"bond_{index:02d}",
        escrow_kind="general",
        source_kind="account",
        source=account,
        beneficiary=account,
        unlock_epoch=unlock,
        amount=1,
    )


def _release(event_id: str, height: int, index: int) -> dict:
    return _event(
        event_id, height, "release_escrow", "escrow", escrow_id=f"bond_{index:02d}"
    )


def _advance(events: list[dict], height: int) -> int:
    events.append(
        _event(f"advance_{height + 1}", height, "advance_height", "clock", to_height=height + 1)
    )
    return height + 1


def _persistent_events(lock_epochs: int) -> list[dict]:
    unlock = 8 + lock_epochs
    events = [_open(f"open_{index:02d}", 0, index, unlock) for index in range(16)]
    height = 0
    while height < unlock - 1:
        height = _advance(events, height)
    events.append(_release("early_release", height, 0))
    height = _advance(events, height)
    events.extend(_release(f"release_{index:02d}", height, index) for index in range(16))
    return events


def _churn_events(lock_epochs: int) -> list[dict]:
    events: list[dict] = []
    final_epoch = 16 + lock_epochs
    for epoch in range(final_epoch + 1):
        if epoch == lock_epochs:
            events.append(_release("early_release", epoch, 0))
        due = epoch - 1 - lock_epochs
        if 0 <= due < 16:
            events.append(_release(f"release_{due:02d}", epoch, due))
        if epoch < 16:
            events.append(_open(f"open_{epoch:02d}", epoch, epoch, epoch + 1 + lock_epochs))
        if epoch < final_epoch:
            _advance(events, epoch)
    return events


def _lock_result(pattern: str, lock_epochs: int, events: list[dict]) -> dict:
    result = simulate_economy(_lock_manifest(), events)
    early = next(record for record in result["records"] if record["event_id"] == "early_release")
    locked = 0
    peak = 0
    for record in result["records"]:
        if not record["accepted"]:
            continue
        for entry in record["journal"]:
            if str(entry["bucket"]).startswith("escrow:"):
                locked += int(entry["delta"])
                peak = max(peak, locked)
    state = result["final_state"]
    expected_peak = 16 if pattern == "persistent" else min(16, lock_epochs + 1)
    refunded = sum(state["accounts"].values())
    valid = (
        early["result"] == "TOO_EARLY"
        and early["state_digest_before"] == early["state_digest_after"]
        and not state["escrows"]
        and state["issued_supply"] == 16
        and refunded == 16
        and peak == expected_peak
        and locked == 0
    )
    if not valid:
        raise AssertionError("native admission-bond lock replay mismatch")
    return {
        "pattern": pattern,
        "post_exit_lock_epochs": lock_epochs,
        "event_count": len(events),
        "early_release_result": early["result"],
        "peak_locked_unit_bonds": peak,
        "expected_peak_locked_unit_bonds": expected_peak,
        "refunded_principal": refunded,
        "ending_locked_principal": locked,
        "issued_supply": state["issued_supply"],
        "trace_digest": result["trace_digest"],
        "lock_enforced": valid,
    }


def lock_replays(lock_epochs: int) -> list[dict]:
    if not 1 <= lock_epochs <= 16:
        raise ValueError("lock duration must be in 1..16")
    return [
        _lock_result("persistent", lock_epochs, _persistent_events(lock_epochs)),
        _lock_result("churn", lock_epochs, _churn_events(lock_epochs)),
    ]


def participation_cross_checks(total_units: int) -> list[dict]:
    results = []
    for identity_count in (1, 2, 16):
        results.append(
            cross_check_proportional(
                f"distinct_principals_{identity_count}",
                identities(identity_count),
                scores(total_units, identity_count, 1, 1),
            )
        )
    return results
