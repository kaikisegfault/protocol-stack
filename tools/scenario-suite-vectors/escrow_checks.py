"""Scenario 4 checks: the escrow drain and its join to the population run.

The opening custody is not a free parameter here. It must equal what the
population run issued into each escrow, derived in closed form, and the digest
the escrow model bound must be the digest that run produced.
"""

from __future__ import annotations

from typing import Any

import expected as x
from checker import Checker

ESCROWS = (
    ("venture_escrow", "venture_escrow"),
    ("community_grants_escrow", "community_grants_escrow"),
    ("developer_incentives_escrow", "developer_incentives_escrow"),
)

PROBE_SUFFIXES = (
    ("envelope", "ENVELOPE_EXCEEDED"),
    ("custody", "INSUFFICIENT_CUSTODY"),
)


def check_join(
    check: Checker,
    escrow_result: dict[str, Any],
    economy_result: dict[str, Any],
) -> None:
    """The bound digest must be the population run's own state digest."""
    bound = escrow_result["final_state"]["bound_state_digest"]
    if bound != economy_result["state_digest"]:
        check.failures.append(
            "escrow.bound_state_digest: does not equal the population run digest"
        )
    check.equal("escrow.bound_state_digest", bound)


def check_trace(check: Checker, result: dict[str, Any]) -> None:
    records = result["records"]
    check.equal("escrow.schema", result["schema"])
    check.equal("escrow.event_count", len(records))
    check.equal(
        "escrow.accepted_count",
        sum(1 for record in records if record["accepted"]),
    )
    check.equal(
        "escrow.rejected_count",
        sum(1 for record in records if not record["accepted"]),
    )
    for name in ("events_digest", "trace_digest", "state_digest", "result_digest"):
        check.equal(f"escrow.{name}", result[name])

    metrics = result["metrics"]
    check.equal("escrow.payouts_per_escrow", x.PAYOUTS_PER_ESCROW)
    check.equal("escrow.capability_count", metrics["capability_count"])
    check.equal("escrow.accepted_payouts", metrics["accepted_payout_count"])
    check.equal(
        "escrow.exhausted_envelopes", metrics["exhausted_envelope_count"]
    )


def _accepted_payouts(result: dict[str, Any], escrow_id: str) -> int:
    """Count the payouts the run actually charged to one escrow."""
    return sum(
        1
        for record in result["records"]
        if record["kind"] == "execute_payout"
        and record["accepted"]
        and any(
            item["bucket"] == f"custody:{escrow_id}"
            for item in record["journal"]
        )
    )


def check_drain(check: Checker, result: dict[str, Any]) -> None:
    """Each escrow opened at its closed-form total and ended empty."""
    state = result["final_state"]
    channels = x.economy_channel_totals()
    for index, (escrow_id, channel_id) in enumerate(ESCROWS):
        opening = channels[channel_id]
        check.agree(
            f"escrow{index}.opening_custody",
            state["opening_custody"][escrow_id],
            opening,
        )
        check.agree(
            f"escrow{index}.available_custody",
            state["available_custody"][escrow_id],
            0,
        )
        check.agree(
            f"escrow{index}.paid_out_total",
            state["paid_out_total"][escrow_id],
            opening,
        )
        # The live count comes from the trace; the closed form is the split
        # this module derives from the opening custody it already checked.
        check.agree(
            f"escrow{index}.payout_count",
            _accepted_payouts(result, escrow_id),
            len(x.payout_amounts(opening)),
        )
        check.equal(
            f"escrow{index}.recipient_count",
            len(state["recipient_balances"][escrow_id]),
        )


def check_conservation(check: Checker, result: dict[str, Any]) -> None:
    """Three equations per escrow, summed here rather than read from a metric."""
    state = result["final_state"]
    for index, (escrow_id, _) in enumerate(ESCROWS):
        opening = int(state["opening_custody"][escrow_id])
        held = int(state["available_custody"][escrow_id]) + int(
            state["paid_out_total"][escrow_id]
        )
        credited = sum(
            int(value)
            for value in state["recipient_balances"][escrow_id].values()
        )
        charged = sum(
            int(capability["spent"])
            for capability in state["capabilities"].values()
            if capability["escrow_id"] == escrow_id
        )
        check.agree(f"escrow{index}.conservation.held", held, opening)
        check.agree(f"escrow{index}.conservation.credited", credited, opening)
        check.agree(f"escrow{index}.conservation.charged", charged, opening)


def check_probes(check: Checker, result: dict[str, Any]) -> None:
    """Exhausted authority and an emptied escrow must report differently."""
    records = {record["event_id"]: record for record in result["records"]}
    for index in range(len(ESCROWS)):
        for suffix, expected_code in PROBE_SUFFIXES:
            record = records[f"probe-{index}-{suffix}"]
            check.equal(f"escrow{index}.probe.{suffix}", record["result"])
            if record["result"] != expected_code:
                check.failures.append(
                    f"escrow{index}.probe.{suffix}: expected {expected_code}"
                )
            if record["accepted"] or record["journal"]:
                check.failures.append(
                    f"escrow{index}.probe.{suffix}: was accepted or journalled"
                )


def check_escrow(
    check: Checker,
    result: dict[str, Any],
    economy_result: dict[str, Any],
) -> None:
    check_join(check, result, economy_result)
    check_trace(check, result)
    check_drain(check, result)
    check_conservation(check, result)
    check_probes(check, result)
