"""Scenario, coverage, and determinism vectors for founder-economy-simulator-v3.

Split from `verify.py` so each module stays readable: that one derives the
contract, the rendering rule, the schedule, the in-scope set, and the agreement
with `cycle-boundary-v1`, and this one derives what a run of the research
scenario produces.

Both halves compare a founder-side derivation against a live model run. Nothing
here restates a recorded value.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import expected as e
import walk as w
from checker import Checker

from simulation.common.canonical import MAX_U64
from simulation.founder_economy_v3 import contract as c
from simulation.founder_economy_v3.domain import (
    Channel,
    Leg,
    PendingPermission,
    Seat,
    initial_state,
)
from simulation.founder_economy_v3.engine import simulate
from simulation.founder_economy_v3.handlers_issuance import exercise_permission
from simulation.founder_economy_v3.uptime import reallocate

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "test-vectors" / "founder-economy-manifest-v2.json"

CUSTODY_KEYS: dict[str, str] = {
    "venture_escrow": "venture_escrow:global",
    "community_grants_escrow": "community_grants_escrow:global",
    "developer_incentives_escrow": "developer_incentives_escrow:global",
    "system_creator_company": "system_creator_company:global",
    "unreferred_performance_pool": "unreferred_performance_pool:global",
}


def check_trace_vectors(
    check: Checker, records: list[dict[str, Any]], walk_codes: list[str]
) -> None:
    """Every event's result, derived by the independent walk and by the model."""
    for record, derived in zip(records, walk_codes):
        index = record["index"]
        check.equal(f"record{index}.event_id", record["event_id"])
        check.equal(f"record{index}.kind", record["kind"])
        check.agree(f"record{index}.result", derived, record["result"])


def check_ordering_vectors(check: Checker, records: list[dict[str, Any]]) -> None:
    """Events carrying two defects at once, proving which condition reports first."""
    by_id = {record["event_id"]: record["result"] for record in records}
    pairs = (
        ("seat_range_before_height_range", "act-range-before-height", "CYCLE_RANGE"),
        ("height_range_before_invalid_referrer", "act-height-before-referrer", "HEIGHT_RANGE"),
        ("replay_before_monotonic", "act-replay-before-monotonic", "REPLAY"),
        ("referrer_before_monotonic", "act-referrer-before-monotonic", "SEAT_NOT_ACTIVATED"),
        ("scope_before_completeness", "eval-scope-before-completeness", "SEAT_NOT_IN_SCOPE"),
        ("window_before_inconsistency", "eval-window-not-for-cycle", "WINDOW_NOT_FOR_CYCLE"),
        ("completeness_before_inconsistency", "eval-record-incomplete", "INCOMPLETE_UPTIME_RECORD"),
    )
    for name, event_id, expected_code in pairs:
        check.agree(f"ordering.{name}", expected_code, by_id[event_id])
    check.equal("ordering.pairs", len(pairs))


def check_scenario_vectors(
    check: Checker, result: dict[str, Any], walk: w.Walk
) -> None:
    """The run's economic totals, derived by the walk and produced by the model."""
    final_state = result["final_state"]
    metrics = result["metrics"]
    records = result["records"]

    check.equal("scenario.events", len(records))
    check.equal("scenario.accepted", sum(1 for record in records if record["accepted"]))
    check.equal("scenario.rejected", sum(1 for record in records if not record["accepted"]))

    check.agree("scenario.issued_supply_atomic", sum(walk.issued.values()),
                int(metrics["issued_supply_atomic"]))
    check.agree("scenario.outstanding_atomic", sum(walk.outstanding.values()),
                int(metrics["outstanding_permissions_atomic"]))
    check.agree("scenario.performance_carry_atomic", walk.carry,
                int(metrics["performance_carry_atomic"]))
    check.agree("scenario.pending_permissions", len(walk.pending),
                metrics["pending_permission_count"])
    check.agree("scenario.evaluated_keys", len(walk.evaluated),
                metrics["evaluated_permission_key_count"])
    check.agree("scenario.referral_accruals", len(walk.accruals),
                metrics["referral_accrual_key_count"])
    check.agree("scenario.bound_windows", len(walk.bound), metrics["bound_uptime_record_count"])

    for name, custody_key in sorted(CUSTODY_KEYS.items()):
        check.agree(
            f"scenario.custody.{name}",
            walk.custody.get(custody_key, 0),
            int(final_state["typed_custody"].get(custody_key, "0")),
        )
    for seat in sorted(walk.heights):
        key = f"founder_seat:{seat:05d}"
        check.agree(
            f"scenario.custody.founder_seat_{seat:05d}",
            walk.custody.get(key, 0),
            int(final_state["typed_custody"].get(key, "0")),
        )
    check.agree(
        "scenario.custody_total",
        sum(walk.custody.values()),
        sum(int(value) for value in final_state["typed_custody"].values()),
    )

    # The carry conservation identity, stated as an equality rather than a bound
    # so a defect that lost carried value fails instead of being reported.
    check.agree(
        "scenario.founder_accounted_atomic",
        len(walk.evaluated) * e.FOUNDER_OPERATOR_LEG,
        int(metrics["founder_accounted_atomic"]),
    )
    check.equal("scenario.state_digest", result["state_digest"])
    check.equal("scenario.trace_digest", result["trace_digest"])
    check.equal("scenario.events_digest", result["events_digest"])
    check.equal("scenario.result_digest", result["result_digest"])
    check.equal("scenario.manifest_digest", result["manifest_digest"])
    check.equal("scenario.manifest_canonical_length", result["manifest_canonical_length"])


def check_reallocation_vectors(check: Checker, events: list[dict[str, Any]]) -> None:
    """The two reallocating windows and the empty winner set, derived by hand."""
    by_id = {event["id"]: event for event in events}
    for name, event_id in (
        ("window_1", "eval-000-c0"),
        ("window_2", "eval-001-c1"),
        ("window_3", "eval-002-c2"),
    ):
        record = by_id[event_id]["cycle_uptime_record"]
        winners = e.winner_seats(record)
        check.equal(f"reallocation.{name}.winners", ",".join(str(x) for x in winners) or "none")
        check.equal(f"reallocation.{name}.winner_count", len(winners))
    # Window 1 splits the portion seven ways with a remainder, window 2 gives it
    # to a single seat and consumes the carry exactly, and window 3 has no
    # qualified seat so the whole pot carries forward.
    share, remainder = e.equal_split(e.FOUNDER_OPERATOR_LEG, 7)
    check.equal("reallocation.window_1.share_atomic", share)
    check.equal("reallocation.window_1.remainder_atomic", remainder)
    check.equal("reallocation.window_2.share_atomic", e.FOUNDER_OPERATOR_LEG + remainder)
    check.equal("reallocation.window_3.carried_atomic", e.FOUNDER_OPERATOR_LEG)


def check_atomicity_vectors(check: Checker, records: list[dict[str, Any]]) -> None:
    """Derive the zero-write claims from the trace rather than asserting them."""
    rejected = [record for record in records if not record["accepted"]]
    check.equal("atomicity.rejected_events", len(rejected))
    check.equal(
        "atomicity.rejected_journal_entries",
        sum(len(record["journal"]) for record in rejected),
    )
    check.equal(
        "atomicity.rejected_state_unchanged",
        all(
            record["state_digest_before"] == record["state_digest_after"]
            for record in rejected
        ),
    )
    # A rejected event binds nothing, so a defective record cannot occupy a
    # window and make a later correct record inconsistent with it.
    check.equal(
        "atomicity.rejected_bound_no_window",
        all(record["journal"] == [] for record in rejected),
    )


def check_coverage_vectors(check: Checker, records: list[dict[str, Any]]) -> None:
    """Result-code coverage as a derived claim, partitioned honestly."""
    produced = {record["result"] for record in records}
    produced.add(_cap_exhaustion_code())

    reachable = set(c.EVENT_REACHABLE_RESULT_CODES)
    check.equal("coverage.declared_result_codes", len(c.RESULT_CODES))
    check.equal("coverage.event_reachable_codes", len(reachable))
    check.equal("coverage.codes_produced_by_execution", len(produced))
    check.equal("coverage.every_reachable_code_is_produced", produced == reachable)
    check.equal("coverage.added_by_version_three", len(c.ADDED_RESULT_CODES))
    check.equal(
        "coverage.added_codes_produced",
        set(c.ADDED_RESULT_CODES) <= produced,
    )
    # The two guards are proved present by direct exercise rather than deleted or
    # claimed reachable. Both are produced here by executing the guarded path.
    check.equal("coverage.guard_codes", len(c.GUARD_RESULT_CODES))
    check.equal("coverage.guard_arithmetic_overflow", _overflow_code())
    check.equal("coverage.guard_invariant", _invariant_code())
    check.equal(
        "coverage.declared_is_reachable_plus_guards",
        reachable | set(c.GUARD_RESULT_CODES) == set(c.RESULT_CODES),
    )


def _cap_exhaustion_code() -> str:
    """Produce CHANNEL_CAP by execution: one direct mint above a channel cap."""
    channel = "liquidity_mining"
    amount = str(c.CHANNEL_CAPS[channel] + 1)
    eligibility = {
        "channel": channel,
        "decision_id": "cap-probe",
        "beneficiary_id": "cap-beneficiary",
        "amount_atomic": amount,
        "eligible": True,
    }
    events = [
        {
            "id": "cap-probe",
            "kind": "direct_issue",
            "channel": channel,
            "decision_id": "cap-probe",
            "beneficiary_id": "cap-beneficiary",
            "amount_atomic": amount,
            "eligibility_result": eligibility,
        }
    ]
    return simulate(str(MANIFEST), events)["records"][0]["result"]


def _overflow_code() -> str:
    """Produce ARITHMETIC_OVERFLOW by exercising the guarded arithmetic directly.

    No event array reaches it: every accumulated quantity is bounded far below
    u64 by a channel cap. The check is still real, so it is exercised rather
    than deleted.
    """
    code, legs, carry = reallocate(MAX_U64, (0,))
    if legs or carry != MAX_U64:
        raise AssertionError("an overflowing reallocation produced legs or moved the carry")
    return code or "OK"


def _invariant_code() -> str:
    """Produce INVARIANT by exercising a permission whose legs do not sum."""
    state = initial_state()
    state.seats[0] = Seat(referrer_seat_id=None, activation_height=0)
    state.channels["founder_operator"] = Channel(issued_atomic=0, outstanding_atomic=0)
    state.pending_permissions["00000:000"] = PendingPermission(
        seat_id=0,
        cycle_index=0,
        cycle_window=1,
        met_cycle=True,
        total_atomic=c.FOUNDER_OPERATOR_LEG + 1,
        legs=(
            Leg(
                channel="founder_operator",
                custody_key="founder_seat:00000",
                amount_atomic=c.FOUNDER_OPERATOR_LEG,
            ),
        ),
    )
    outcome = exercise_permission(state, {"seat_id": 0, "cycle_index": 0})
    return outcome.code


def check_determinism_vectors(check: Checker, result: dict[str, Any], events: Any) -> None:
    repeat = simulate(str(MANIFEST), events)
    check.equal("determinism.result_digest_is_stable", repeat["result_digest"] == result["result_digest"])
    check.equal("determinism.state_digest_is_stable", repeat["state_digest"] == result["state_digest"])
    # A prefix must reproduce the state the full run held at that point, which is
    # restart equivalence as state equivalence under replay.
    cut = len(events) // 2
    prefix = simulate(str(MANIFEST), events[:cut])
    check.equal(
        "determinism.prefix_reproduces_state",
        prefix["state_digest"] == result["records"][cut - 1]["state_digest_after"],
    )
