"""Derive the research scenario from an independent replay of the events.

`walk.replay` applies the specification's transitions to plain dictionaries. It
must reproduce the model's whole final state, conserve every routed unit on both
paths, and keep the two paths from touching each other's value.
"""

from __future__ import annotations

from pathlib import Path

import walk as w
from checker import Checker

from simulation.revenue_routing import contract as c
from simulation.revenue_routing.domain import initial_state, state_digest
from simulation.revenue_routing.engine import apply_event
from simulation.revenue_routing.validation import load_events_file

ROOT = Path(__file__).resolve().parents[2]
EVENTS_FILE = "simulation/revenue_routing/fixtures/research-events-v1.json"

MODELLED_CODES = frozenset(
    {
        "REPLAY",
        "ZERO_AMOUNT",
        "DUPLICATE_CREATOR",
        "CYCLE_MISMATCH",
        "MISSING_RESEARCH_INPUT",
        "INVALID_RESEARCH_INPUT",
        "ARITHMETIC_OVERFLOW",
        "INVARIANT",
    }
)


def check_scenario_vectors(check: Checker, result: dict, events: list[dict]) -> None:
    walk = w.replay(events)
    records = result["records"]

    check.equal("schema", result["schema"])
    check.equal("events_file", EVENTS_FILE)
    check.equal("events_domain_label", c.EVENTS_LABEL)
    check.equal("state_domain_label", c.STATE_LABEL)
    check.equal("trace_domain_label", c.TRACE_LABEL)
    check.equal("result_domain_label", c.RESULT_LABEL)

    check.equal("scenario.event_count", len(records))
    check.equal("scenario.accepted_count", walk.accepted)
    check.equal("scenario.rejected_count", walk.rejected)
    check.equal("scenario.events_digest", result["events_digest"])
    check.equal("scenario.trace_digest", result["trace_digest"])
    check.equal("scenario.state_digest", result["state_digest"])
    check.equal("scenario.result_digest", result["result_digest"])

    _check_totals(check, result, walk)
    check_walk_agreement(check, result, walk)
    check_conservation(check, walk)
    check_independence(check, events, walk)
    _check_closes(check, walk)
    _check_trace(check, result, walk)


def _check_totals(check: Checker, result: dict, walk: w.Walk) -> None:
    check.equal("scenario.cycles_closed", walk.current_cycle)
    check.equal("scenario.commercial_routed_total", walk.commercial_routed_total)
    check.equal("scenario.fee_routed_total", walk.fee_routed_total)
    check.equal("scenario.commercial_pool", walk.commercial_pool)
    check.equal("scenario.fee_pool", walk.fee_pool)
    check.equal("scenario.commercial_carry", walk.commercial_carry)
    check.equal("scenario.fee_carry", walk.fee_carry)
    check.equal("scenario.system_creator_balance", walk.system_creator_balance)
    check.equal("scenario.creator_total", sum(walk.creator_balances.values()))
    check.equal(
        "scenario.founder_commercial_total", sum(walk.commercial_seats.values())
    )
    check.equal("scenario.founder_fee_total", sum(walk.fee_seats.values()))
    check.equal("scenario.creator_count", len(walk.creator_balances))
    check.equal(
        "scenario.credited_seat_count", result["metrics"]["credited_seat_count"]
    )
    check.equal(
        "scenario.largest_seat_commercial_balance",
        max(walk.commercial_seats.values(), default=0),
    )
    check.equal(
        "scenario.largest_seat_fee_balance", max(walk.fee_seats.values(), default=0)
    )


def check_walk_agreement(check: Checker, result: dict, walk: w.Walk) -> None:
    """The independent replay must reproduce the model's whole final state."""
    final = result["final_state"]
    scalars = {
        "current_cycle": walk.current_cycle,
        "commercial_pool": walk.commercial_pool,
        "fee_pool": walk.fee_pool,
        "commercial_carry": walk.commercial_carry,
        "fee_carry": walk.fee_carry,
        "commercial_routed_total": walk.commercial_routed_total,
        "fee_routed_total": walk.fee_routed_total,
        "system_creator_balance": walk.system_creator_balance,
    }
    for key, derived in scalars.items():
        if str(final[key]) != str(derived):
            check.failures.append(f"walk: {key} disagrees with the model")
    maps = (
        ("creator_balances", {k: str(v) for k, v in walk.creator_balances.items()}),
        ("founder_commercial_balances", _seat_map(walk.commercial_seats)),
        ("founder_fee_balances", _seat_map(walk.fee_seats)),
    )
    for key, derived in maps:
        if final[key] != derived:
            check.failures.append(f"walk: {key} disagrees with the model")


def _seat_map(balances: dict[int, int]) -> dict[str, str]:
    return {f"{seat:05d}": str(amount) for seat, amount in sorted(balances.items())}


def check_conservation(check: Checker, walk: w.Walk) -> None:
    """Every routed unit is either credited to a beneficiary or still pooled."""
    commercial = (
        walk.system_creator_balance
        + sum(walk.creator_balances.values())
        + sum(walk.commercial_seats.values())
        + walk.commercial_pool
        + walk.commercial_carry
    )
    fees = sum(walk.fee_seats.values()) + walk.fee_pool + walk.fee_carry
    check.equal("conservation.commercial_credited_and_pooled", commercial)
    check.equal("conservation.fee_credited_and_pooled", fees)
    if commercial != walk.commercial_routed_total:
        check.failures.append("conservation: commercial value was created or lost")
    if fees != walk.fee_routed_total:
        check.failures.append("conservation: fee value was created or lost")


def check_independence(check: Checker, events: list[dict], walk: w.Walk) -> None:
    """Neither path may move value belonging to the other."""
    without_fees = w.replay([e for e in events if e["kind"] != "route_transaction_fee"])
    without_payments = w.replay(
        [e for e in events if e["kind"] != "route_commercial_payment"]
    )
    check.equal(
        "independence.fee_total_without_fee_events", without_fees.fee_routed_total
    )
    check.equal(
        "independence.commercial_total_without_payment_events",
        without_payments.commercial_routed_total,
    )
    check.equal(
        "independence.commercial_total_without_fee_events",
        without_fees.commercial_routed_total,
    )
    if without_fees.commercial_routed_total != walk.commercial_routed_total:
        check.failures.append("independence: removing fees changed commercial revenue")


def _check_closes(check: Checker, walk: w.Walk) -> None:
    for index, close in enumerate(walk.closes):
        prefix = f"close{index}"
        check.equal(f"{prefix}.active_seat_count", close.active_seat_count)
        check.equal(f"{prefix}.commercial_pool_in", close.commercial_pool_in)
        check.equal(f"{prefix}.commercial_per_seat", close.commercial_per_seat)
        check.equal(f"{prefix}.commercial_carry", close.commercial_carry)
        check.equal(f"{prefix}.fee_pool_in", close.fee_pool_in)
        check.equal(f"{prefix}.fee_per_seat", close.fee_per_seat)
        check.equal(f"{prefix}.fee_carry", close.fee_carry)


def _check_trace(check: Checker, result: dict, walk: w.Walk) -> None:
    records = result["records"]
    for index, record in enumerate(records):
        check.equal(f"record{index}.event_id", record["event_id"])
        check.equal(f"record{index}.result", record["result"])

    check.equal("atomic_failure.rejected_state_writes", count_rejected_writes())
    check.equal(
        "atomic_failure.rejected_journal_entries",
        sum(len(r["journal"]) for r in records if not r["accepted"]),
    )
    final = result["final_state"]
    check.equal(
        "atomic_failure.payment_identifiers_consumed",
        len(final["accepted_payment_ids"]) - len(walk.payments),
    )
    check.equal(
        "atomic_failure.fee_identifiers_consumed",
        len(final["accepted_fee_ids"]) - len(walk.fees),
    )


def count_rejected_writes() -> int:
    """Step the scenario and digest the whole state around every event."""
    events = load_events_file(ROOT / EVENTS_FILE)
    state = initial_state()
    writes = 0
    for index, event in enumerate(events):
        before = state_digest(state)
        record = apply_event(state, event, index)
        after = state_digest(state)
        if not record["accepted"] and before != after:
            writes += 1
    return writes


def check_negative_vectors(check: Checker) -> None:
    for key in sorted(check.recorded):
        if key.startswith("negative.") and key.endswith(".result"):
            recorded = check.recorded[key]
            check.equal(key, recorded if recorded in MODELLED_CODES else "UNMODELLED")
