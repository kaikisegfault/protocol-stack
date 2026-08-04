"""Scenario, conservation, containment, and rejection-code checks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import walk as w
from checker import Checker

ROOT = Path(__file__).resolve().parents[2]
EVENTS_FILE = "simulation/escrow_payout/fixtures/research-events-v1.json"

RESULT_CODES: tuple[str, ...] = (
    "already_bound",
    "already_revoked",
    "approval_withheld",
    "arithmetic_overflow",
    "capability_expired",
    "capability_revoked",
    "custody_above_cap",
    "cycle_mismatch",
    "envelope_exceeded",
    "escrow_mismatch",
    "insufficient_custody",
    "invalid_capability",
    "invalid_research_input",
    "invariant",
    "missing_research_input",
    "not_bound",
    "payout_limit_exceeded",
    "replay",
    "unknown_capability",
    "unknown_escrow",
    "zero_amount",
)


def check_scenario_vectors(
    check: Checker, result: dict[str, Any], walk: w.Walk
) -> None:
    records = result["records"]
    _check_trace(check, records, walk)
    _check_totals(check, result, walk)
    _check_conservation(check, walk)
    _check_containment(check, records, walk)


def _check_trace(check: Checker, records: list[dict[str, Any]], walk: w.Walk) -> None:
    check.equal("scenario.event_count", len(records))
    check.equal("scenario.accepted_count", sum(1 for r in records if r["accepted"]))
    check.equal("scenario.rejected_count", sum(1 for r in records if not r["accepted"]))

    if len(walk.results) != len(records):
        raise AssertionError("the independent walk saw a different event count")
    for index, record in enumerate(records):
        if walk.results[index] != record["result"]:
            raise AssertionError(
                f"event {index} ({record['event_id']}): the walk derived "
                f"{walk.results[index]}, the model derived {record['result']}"
            )
        check.equal(f"record{index}.event_id", record["event_id"])
        check.equal(f"record{index}.result", record["result"])


def _check_totals(check: Checker, result: dict[str, Any], walk: w.Walk) -> None:
    metrics = result["metrics"]
    check.equal("scenario.events_digest", result["events_digest"])
    check.equal("scenario.trace_digest", result["trace_digest"])
    check.equal("scenario.state_digest", result["state_digest"])
    check.equal("scenario.result_digest", result["result_digest"])
    check.equal("scenario.bound_state_digest", metrics["bound_state_digest"])
    check.equal("scenario.current_cycle", walk.current_cycle)
    check.equal("scenario.capability_count", len(walk.capabilities))
    check.equal(
        "scenario.revoked_capability_count",
        sum(1 for item in walk.capabilities.values() if item.revoked),
    )
    check.equal(
        "scenario.exhausted_envelope_count",
        sum(
            1
            for item in walk.capabilities.values()
            if item.spent == item.envelope_total
        ),
    )
    check.equal("scenario.accepted_payout_count", len(walk.accepted_payouts))
    check.equal(
        "scenario.paid_out_total", sum(walk.paid_out[e] for e in w.ESCROWS)
    )

    if metrics["current_cycle"] != walk.current_cycle:
        raise AssertionError("the walk and the model disagree on the cycle")
    if metrics["accepted_payout_count"] != len(walk.accepted_payouts):
        raise AssertionError("the walk and the model disagree on accepted payouts")


def _check_conservation(check: Checker, walk: w.Walk) -> None:
    """Each escrow conserves independently: opening = available + paid out."""
    for index, escrow in enumerate(w.ESCROWS):
        opening = walk.opening[escrow]
        available = walk.available[escrow]
        paid_out = walk.paid_out[escrow]
        check.equal(f"escrow{index}.opening_custody", opening)
        check.equal(f"escrow{index}.available_custody", available)
        check.equal(f"escrow{index}.paid_out_total", paid_out)
        check.equal(f"escrow{index}.recipient_count", len(walk.recipients[escrow]))
        check.equal(
            f"escrow{index}.largest_recipient_balance",
            max(walk.recipients[escrow].values(), default=0),
        )
        prefix = f"conservation.escrow{index}"
        check.equal(f"{prefix}.available_plus_paid", available + paid_out)
        check.equal(f"{prefix}.credited_recipients", walk.credited(escrow))
        check.equal(f"{prefix}.charged_envelopes", walk.charged(escrow))

        if available + paid_out != opening:
            raise AssertionError(f"{escrow}: custody is neither available nor paid out")
        if walk.credited(escrow) != paid_out:
            raise AssertionError(f"{escrow}: payouts do not reach its recipients")
        if walk.charged(escrow) != paid_out:
            raise AssertionError(f"{escrow}: payouts do not match its envelopes")


def _check_containment(
    check: Checker, records: list[dict[str, Any]], walk: w.Walk
) -> None:
    """Custody never rises after the bind and no payout touches two escrows."""
    check.equal(
        "containment.custody_increases_after_bind",
        walk.custody_increases_after_bind,
    )
    check.equal("containment.multi_escrow_payouts", walk.multi_escrow_payouts)

    touched = 0
    for record in records:
        if not record["accepted"] or record["kind"] != "execute_payout":
            continue
        escrows = {
            entry["bucket"].split(":")[1]
            for entry in record["journal"]
        }
        if len(escrows) != 1:
            raise AssertionError("a payout journal named more than one escrow")
        touched += 1
    check.equal("containment.single_escrow_payouts", touched)

    silent = sum(
        1
        for record in records
        if record["accepted"]
        and record["kind"] in {"grant_capability", "revoke_capability", "advance_cycle"}
    )
    check.equal("containment.value_free_transitions", silent)
    for record in records:
        if record["kind"] in {"grant_capability", "revoke_capability", "advance_cycle"}:
            if record["journal"]:
                raise AssertionError(f"{record['event_id']} moved value")


def check_negative_vectors(check: Checker, records: list[dict[str, Any]]) -> None:
    """Every specified result code is recorded, and the reachable ones occur."""
    observed = {record["result"] for record in records if not record["accepted"]}
    for code in RESULT_CODES:
        check.equal(f"negative.{code}.result", code.upper())

    unreachable = {"ARITHMETIC_OVERFLOW", "INVARIANT"}
    expected = {code.upper() for code in RESULT_CODES} - unreachable
    if observed != expected:
        missing = sorted(expected - observed)
        extra = sorted(observed - expected)
        raise AssertionError(
            f"scenario rejection coverage: missing={missing}, unexpected={extra}"
        )
    check.equal("negative.codes_reached_by_scenario", len(observed))
    check.equal("negative.codes_covered_by_tests_only", len(unreachable))


def check_atomicity_vectors(check: Checker, records: list[dict[str, Any]]) -> None:
    """A rejection writes nothing, journals nothing, and consumes no identifier."""
    rejected = [record for record in records if not record["accepted"]]
    check.equal("atomic_failure.rejected_count", len(rejected))
    check.equal(
        "atomic_failure.rejected_journal_entries",
        sum(len(record["journal"]) for record in rejected),
    )
    for record in rejected:
        if record["journal"]:
            raise AssertionError(f"{record['event_id']} journalled while rejected")
