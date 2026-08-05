"""Scenario 1 checks: the complete 731-cycle staggered population run.

Every monetary total here is required to agree with a closed-form derivation
from the Founder Constitution before it is compared with the recorded file.
"""

from __future__ import annotations

from typing import Any

import expected as x
from checker import Checker

PROBES = (
    ("cycle_beyond_window", "probe-cycle-beyond-window"),
    ("base_replay", "probe-base-replay"),
    ("exercise_replay", "probe-exercise-replay"),
    ("activation_replay", "probe-activation-replay"),
    ("unreferred_referral", "probe-unreferred-referral"),
)

# (vector name, custody key, the channel whose whole issuance it holds)
CUSTODY_SINGLETONS = (
    ("venture_escrow", "venture_escrow:global", "venture_escrow"),
    (
        "community_grants_escrow",
        "community_grants_escrow:global",
        "community_grants_escrow",
    ),
    (
        "developer_incentives_escrow",
        "developer_incentives_escrow:global",
        "developer_incentives_escrow",
    ),
    (
        "system_creator_company",
        "system_creator_company:global",
        "system_creator_issuance_royalty",
    ),
)


def check_parameters(check: Checker) -> None:
    check.equal("economy.seats", x.POPULATION_SEATS)
    check.equal("economy.referred_seats", x.POPULATION_REFERRED_SEATS)
    check.equal("economy.cycles_per_seat", x.ISSUANCE_CYCLES_PER_SEAT)
    check.equal("economy.inactive_period", x.INACTIVE_PERIOD)
    check.equal("economy.inactive_phase", x.INACTIVE_PHASE)
    check.equal("economy.base_permission_total", x.base_permission_total())
    check.equal("economy.referral_leg", x.REFERRAL_LEG)


def check_trace(check: Checker, result: dict[str, Any]) -> None:
    records = result["records"]
    check.equal("economy.schema", result["schema"])
    check.equal("economy.event_count", len(records))
    check.equal(
        "economy.accepted_count",
        sum(1 for record in records if record["accepted"]),
    )
    check.equal(
        "economy.rejected_count",
        sum(1 for record in records if not record["accepted"]),
    )
    for name in ("events_digest", "trace_digest", "state_digest", "result_digest"):
        check.equal(f"economy.{name}", result[name])


def check_totals(check: Checker, result: dict[str, Any]) -> None:
    metrics = result["metrics"]
    channels = x.economy_channel_totals()
    issued = 0
    for channel_id, closed_form in channels.items():
        live = int(metrics["channels"][channel_id]["issued_atomic"])
        check.agree(f"economy.channel.{channel_id}", live, closed_form)
        issued += closed_form

    check.agree("economy.issued_supply", metrics["issued_supply_atomic"], issued)
    check.equal(
        "economy.outstanding_permissions",
        metrics["outstanding_permissions_atomic"],
    )
    check.agree(
        "economy.evaluated_permission_keys",
        metrics["evaluated_permission_key_count"],
        x.evaluated_permission_keys(),
    )
    check.agree(
        "economy.referral_permissions_created",
        int(metrics["channels"]["founder_referral"]["issued_atomic"])
        // x.REFERRAL_LEG,
        x.referral_permissions_created(),
    )
    check.equal("economy.activated_seats", metrics["activated_seat_count"])
    check.equal("economy.pending_permissions", metrics["pending_permission_count"])

    remaining = int(metrics["remaining_capacity_atomic"])
    check.agree(
        "economy.supply_accounted",
        issued + int(metrics["outstanding_permissions_atomic"]) + remaining,
        x.MAXIMUM_SUPPLY_ATOMIC,
    )


def check_custody(check: Checker, result: dict[str, Any]) -> None:
    """Custody must equal issued supply and match the per-seat closed form."""
    custody = result["final_state"]["typed_custody"]
    for seat_id, closed_form in x.economy_seat_custody().items():
        check.agree(
            f"economy.custody.founder_seat_{seat_id:05d}",
            custody[f"founder_seat:{seat_id:05d}"],
            closed_form,
        )

    channels = x.economy_channel_totals()
    for name, key, channel_id in CUSTODY_SINGLETONS:
        check.agree(
            f"economy.custody.{name}", custody[key], channels[channel_id]
        )

    check.agree(
        "economy.custody_total",
        sum(int(value) for value in custody.values()),
        sum(channels.values()),
    )


def check_probes(check: Checker, result: dict[str, Any]) -> None:
    """Every boundary probe must still be refused after 7,303 accepted events."""
    codes = {record["event_id"]: record for record in result["records"]}
    for name, event_id in PROBES:
        record = codes[event_id]
        check.equal(f"economy.probe.{name}", record["result"])
        if record["accepted"] or record["journal"]:
            check.failures.append(f"economy.probe.{name}: was accepted or journalled")
        if record["state_digest_before"] != record["state_digest_after"]:
            check.failures.append(f"economy.probe.{name}: changed state")


def check_chaining(check: Checker, result: dict[str, Any]) -> None:
    """Each record's digest must chain to the next and to the final state."""
    records = result["records"]
    breaks = sum(
        1
        for previous, current in zip(records, records[1:])
        if previous["state_digest_after"] != current["state_digest_before"]
    )
    check.equal("economy.trace_digest_breaks", breaks)
    if records[-1]["state_digest_after"] != result["state_digest"]:
        check.failures.append("economy.trace_digest_breaks: final digest differs")


def check_economy(check: Checker, result: dict[str, Any]) -> None:
    check_parameters(check)
    check_trace(check, result)
    check_totals(check, result)
    check_custody(check, result)
    check_probes(check, result)
    check_chaining(check, result)
