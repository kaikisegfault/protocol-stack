"""Scenario 1 checks: the complete 731-cycle staggered population run.

Every monetary total here is required to agree with a closed-form derivation
from the Founder Constitution before it is compared with the recorded file.
"""

from __future__ import annotations

from types import ModuleType
from typing import Any

from checker import Checker

BASE_EVALUATION = "evaluate_base_permission"
CARRY_BUCKET = "carry:performance"

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


def check_parameters(check: Checker, x: ModuleType) -> None:
    check.equal("economy.seats", x.POPULATION_SEATS)
    check.equal("economy.referred_seats", x.POPULATION_REFERRED_SEATS)
    check.equal("economy.cycles_per_seat", x.ISSUANCE_CYCLES_PER_SEAT)
    check.equal("economy.inactive_period", x.INACTIVE_PERIOD)
    check.equal("economy.inactive_phase", x.INACTIVE_PHASE)
    check.equal("economy.base_permission_total", x.base_permission_total())
    check.equal("economy.referral_leg", x.REFERRAL_LEG)


def check_trace(check: Checker, x: ModuleType, result: dict[str, Any]) -> None:
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


def check_totals(check: Checker, x: ModuleType, result: dict[str, Any]) -> None:
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
    # The referral channel's issuance divided by one leg counts the referrals
    # the run created. Version one created permissions conditionally; version
    # two accrues unconditionally, so the vector is named for what it counts.
    referral_count = (
        int(metrics["channels"]["founder_referral"]["issued_atomic"]) // x.REFERRAL_LEG
    )
    if x.VERSION == "v1":
        check.agree(
            "economy.referral_permissions_created",
            referral_count,
            x.referral_permissions_created(),
        )
    else:
        check.agree(
            "economy.referral_accruals_created",
            referral_count,
            x.referral_accruals_created(),
        )
    check.agree(
        "economy.activated_seats", metrics["activated_seat_count"], x.ACTIVATED_SEATS
    )
    check.equal("economy.pending_permissions", metrics["pending_permission_count"])

    remaining = int(metrics["remaining_capacity_atomic"])
    check.agree(
        "economy.supply_accounted",
        issued + int(metrics["outstanding_permissions_atomic"]) + remaining,
        x.MAXIMUM_SUPPLY_ATOMIC,
    )


def check_custody(check: Checker, x: ModuleType, result: dict[str, Any]) -> None:
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

    if x.VERSION != "v1":
        # The unreferred seats' share of the referral channel. Version one had
        # no such destination: an unreferred seat's referral was rejected, so
        # the channel's realised total depended on how seats were referred.
        check.agree(
            "economy.custody.unreferred_performance_pool",
            custody["unreferred_performance_pool:global"],
            x.unreferred_pool_custody(),
        )

    check.agree(
        "economy.custody_total",
        sum(int(value) for value in custody.values()),
        sum(channels.values()),
    )


def check_probes(check: Checker, x: ModuleType, result: dict[str, Any]) -> None:
    """Every boundary probe must still be refused after 7,303 accepted events."""
    codes = {record["event_id"]: record for record in result["records"]}
    for name, event_id in x.PROBES:
        record = codes[event_id]
        check.equal(f"economy.probe.{name}", record["result"])
        if record["accepted"] or record["journal"]:
            check.failures.append(f"economy.probe.{name}: was accepted or journalled")
        if record["state_digest_before"] != record["state_digest_after"]:
            check.failures.append(f"economy.probe.{name}: changed state")


def _carry_delta(record: dict[str, Any]) -> int:
    """The signed movement of the performance carry in one accepted event."""
    total = 0
    for item in record["journal"]:
        if item["bucket"] != CARRY_BUCKET:
            continue
        amount = int(item["amount_atomic"])
        total += amount if item["direction"] == "increase" else -amount
    return total


def check_schedule(check: Checker, x: ModuleType, result: dict[str, Any]) -> None:
    """Version three only: the enforced schedule and what it forces.

    The heights are not a free parameter. Keeping the tick a shared window is
    what scenario 1 exists to demonstrate, and the accepted grid then fixes the
    activation height of every seat, which the recorded seat table reproduces.

    The live count of unrewarded windows comes from the trace rather than from
    the generator. Every base evaluation accounts exactly one Founder portion as
    either a reserved leg or a carry movement, so a window whose whole portion
    carried is one whose carry rose by the entire leg.
    """
    state = result["final_state"]
    seats = state["seats"]
    check.equal("economy.stagger", x.STAGGER)
    check.equal("economy.cycle_blocks", x.CYCLE_BLOCKS)
    check.agree(
        "economy.last_activation_height",
        state["last_activation_height"],
        x.LAST_ACTIVATION_HEIGHT,
    )
    check.agree(
        "economy.full_scope_window",
        seats[f"{x.POPULATION_SEATS - 1:05d}"]["first_cycle_window"],
        x.full_scope_window(),
    )
    check.agree(
        "economy.probe_window",
        seats[f"{x.PROBE_SEAT:05d}"]["first_cycle_window"],
        x.PROBE_WINDOW,
    )
    check.agree(
        "economy.bound_uptime_records",
        result["metrics"]["bound_uptime_record_count"],
        x.bound_window_count(),
    )
    unrewarded = sum(
        1
        for record in result["records"]
        if record["accepted"]
        and record["kind"] == BASE_EVALUATION
        and _carry_delta(record) == x.FOUNDER_OPERATOR_LEG
    )
    check.agree("economy.unrewarded_windows", unrewarded, x.unrewarded_window_count())
    check.agree(
        "economy.performance_carry",
        state["performance_carry_atomic"],
        x.performance_carry(),
    )
    check.equal("economy.peer_evaluations", x.PEER_EVALUATIONS)


def check_peer_events(check: Checker, x: ModuleType, result: dict[str, Any]) -> None:
    """The accepted events that make the contradiction probe reachable at all.

    Version three checks a window before it checks the binding, so a record can
    only contradict one already bound inside a window the evaluating seat
    genuinely holds. These three put a record there.
    """
    records = {record["event_id"]: record for record in result["records"]}
    for name, event_id in x.PEER_EVENTS:
        record = records[event_id]
        check.equal(f"economy.peer.{name}", record["result"])
        if not record["accepted"] or not record["journal"]:
            check.failures.append(
                f"economy.peer.{name}: was refused or wrote nothing"
            )


def check_chaining(check: Checker, x: ModuleType, result: dict[str, Any]) -> None:
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


def check_economy(check: Checker, x: ModuleType, result: dict[str, Any]) -> None:
    check_parameters(check, x)
    check_trace(check, x, result)
    check_totals(check, x, result)
    check_custody(check, x, result)
    check_probes(check, x, result)
    if x.VERSION == "v3":
        check_schedule(check, x, result)
        check_peer_events(check, x, result)
    check_chaining(check, x, result)
