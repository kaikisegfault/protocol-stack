"""Scenario 2 and 3 checks: the concentrated sale and the routing population.

The sale proceeds are re-derived by walking the constitutional block schedule,
and the routed totals by summing the scenario's stated payment and fee series.
Neither derivation touches the models.
"""

from __future__ import annotations

from typing import Any

import expected as x
from checker import Checker

SEAT_PROBES = (
    ("beyond_capacity", "beyond-capacity"),
    ("purchase_replay", "probe-purchase-replay"),
)

ROUTING_PROBES = (
    ("payment_replay", "probe-payment-replay"),
    ("close_wrong_cycle", "probe-close-wrong-cycle"),
    ("close_stale_snapshot", "probe-close-stale-snapshot"),
)


def _trace(check: Checker, prefix: str, result: dict[str, Any]) -> None:
    records = result["records"]
    check.equal(f"{prefix}.schema", result["schema"])
    check.equal(f"{prefix}.event_count", len(records))
    check.equal(
        f"{prefix}.accepted_count",
        sum(1 for record in records if record["accepted"]),
    )
    check.equal(
        f"{prefix}.rejected_count",
        sum(1 for record in records if not record["accepted"]),
    )
    for name in ("events_digest", "trace_digest", "state_digest", "result_digest"):
        check.equal(f"{prefix}.{name}", result[name])


def _probes(
    check: Checker,
    prefix: str,
    result: dict[str, Any],
    probes: tuple[tuple[str, str], ...],
) -> None:
    records = {record["event_id"]: record for record in result["records"]}
    for name, event_id in probes:
        record = records[event_id]
        check.equal(f"{prefix}.probe.{name}", record["result"])
        if record["accepted"] or record["journal"]:
            check.failures.append(f"{prefix}.probe.{name}: was accepted or journalled")


def check_seats(check: Checker, result: dict[str, Any]) -> None:
    _trace(check, "seats", result)
    metrics = result["metrics"]

    check.equal("seats.capacity", x.FOUNDER_SEAT_CAPACITY)
    check.equal("seats.maximum_per_principal", x.MAXIMUM_SEATS_PER_PERSON)
    check.agree(
        "seats.minimum_principals",
        metrics["distinct_principal_count"],
        x.minimum_principals(),
    )
    check.equal("seats.sold", metrics["seats_sold"])
    check.equal("seats.remaining", metrics["seats_remaining"])
    check.agree(
        "seats.largest_principal_holding",
        metrics["largest_principal_holding"],
        x.MAXIMUM_SEATS_PER_PERSON,
    )
    check.agree(
        "seats.proceeds_usd_cents",
        metrics["proceeds_usd_cents"],
        x.full_sale_proceeds_cents(),
    )
    check.agree(
        "seats.final_block_price_usd_cents",
        metrics["current_block_price_usd_cents"],
        x.block_price_cents(x.BLOCK_COUNT - 1),
    )

    over_limit = sum(
        1
        for record in result["records"]
        if record["result"] == "PRINCIPAL_SEAT_LIMIT"
    )
    check.agree(
        "seats.over_limit_rejections", over_limit, x.minimum_principals() - 1
    )
    _probes(check, "seats", result, SEAT_PROBES)


def check_routing(check: Checker, result: dict[str, Any]) -> None:
    _trace(check, "routing", result)
    state = result["final_state"]
    totals = x.routing_totals()

    check.equal("routing.cycles", x.ROUTING_CYCLES)
    check.agree("routing.cycles_closed", state["current_cycle"], x.ROUTING_CYCLES)
    check.agree(
        "routing.empty_cycles",
        sum(
            1
            for cycle in range(x.ROUTING_CYCLES)
            if x.active_seat_count(cycle) == 0
        ),
        x.empty_cycle_count(),
    )
    check.agree(
        "routing.commercial_routed_total",
        state["commercial_routed_total"],
        totals["commercial"],
    )
    check.agree(
        "routing.fee_routed_total", state["fee_routed_total"], totals["fee"]
    )
    check.agree(
        "routing.system_creator_balance",
        state["system_creator_balance"],
        x.system_creator_total(),
    )

    for name in ("commercial_pool", "fee_pool", "commercial_carry", "fee_carry"):
        check.equal(f"routing.{name}", state[name])
    check.equal("routing.creator_count", len(state["creator_balances"]))
    check.equal(
        "routing.credited_seats", len(state["founder_commercial_balances"])
    )
    _check_conservation(check, state, totals)
    _probes(check, "routing", result, ROUTING_PROBES)


def _check_conservation(
    check: Checker,
    state: dict[str, Any],
    totals: dict[str, int],
) -> None:
    """Both conservation equations, summed here rather than read from a metric."""
    commercial = (
        int(state["system_creator_balance"])
        + sum(int(value) for value in state["creator_balances"].values())
        + sum(
            int(value) for value in state["founder_commercial_balances"].values()
        )
        + int(state["commercial_pool"])
        + int(state["commercial_carry"])
    )
    fees = (
        sum(int(value) for value in state["founder_fee_balances"].values())
        + int(state["fee_pool"])
        + int(state["fee_carry"])
    )
    check.agree(
        "routing.conservation.commercial", commercial, totals["commercial"]
    )
    check.agree("routing.conservation.fee", fees, totals["fee"])
