#!/usr/bin/env python3
"""Independently derive and check the founder-economy-simulator-v2 vectors.

Every recorded value is rederived from the Founder Constitution literals in
`expected.py` and from a live simulation run over the checked-in fixture, then
compared. `expected.py` imports nothing from `simulation/`, so a value that both
sources agree on has been reached from the founder document and from the model
independently. Restating a recorded value instead of deriving it would make the
vector file unfalsifiable.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import expected as e
from checker import Checker, read_vectors

from simulation.founder_economy_v2 import contract as c
from simulation.founder_economy_v2.domain import STATE_LABEL
from simulation.founder_economy_v2.engine import (
    EVENTS_LABEL,
    RESULT_LABEL,
    RESULT_SCHEMA,
    TRACE_LABEL,
    simulate,
)
from simulation.founder_economy_v2.manifest import ManifestError, load_manifest_file
from simulation.founder_economy_v2.uptime import RECORD_LABEL
from simulation.founder_economy_v2.validation import load_events_file

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = "test-vectors/founder-economy-manifest-v2.json"
EVENTS_PATH = "simulation/founder_economy_v2/fixtures/research-events-v2.json"

CUSTODY_KEYS = {
    "venture_escrow": "venture_escrow:global",
    "community_grants_escrow": "community_grants_escrow:global",
    "developer_incentives_escrow": "developer_incentives_escrow:global",
    "system_creator_company": "system_creator_company:global",
    "unreferred_performance_pool": "unreferred_performance_pool:global",
    "direct_beneficiary": "direct_beneficiary:b1",
}

# The result codes this contract can produce. A code the fixture never reaches
# is a coverage gap, so the verifier records which ones the scenario exercised
# and requires the set to be exactly this one.
MODELLED_CODES = frozenset(
    {
        "OK",
        "CYCLE_RANGE",
        "REPLAY",
        "INVALID_REFERRER",
        "SEAT_NOT_ACTIVATED",
        "MISSING_UPTIME_RECORD",
        "INVALID_UPTIME_RECORD",
        "INCONSISTENT_UPTIME_RECORD",
        "MISSING_RESEARCH_INPUT",
        "INVALID_RESEARCH_INPUT",
        "NOT_ELIGIBLE",
        "INVALID_CHANNEL",
        "ZERO_AMOUNT",
        "PERMISSION_NOT_FOUND",
    }
)


def check_identity_vectors(check: Checker, result: dict[str, Any]) -> None:
    check.equal("schema", RESULT_SCHEMA)
    check.equal("manifest_file", MANIFEST_PATH)
    check.equal("events_file", EVENTS_PATH)
    check.equal("events_domain_label", EVENTS_LABEL)
    check.equal("state_domain_label", STATE_LABEL)
    check.equal("trace_domain_label", TRACE_LABEL)
    check.equal("result_domain_label", RESULT_LABEL)
    check.equal("uptime_record_domain_label", RECORD_LABEL)
    check.equal("scenario.manifest_canonical_length", result["manifest_canonical_length"])
    check.equal("scenario.manifest_digest", result["manifest_digest"])

    # Every label must end in the version suffix, so no digest computed under
    # version one can be replayed as version two.
    labels = (EVENTS_LABEL, STATE_LABEL, TRACE_LABEL, RESULT_LABEL, RECORD_LABEL)
    check.equal(
        "labels.all_version_two", str(all(label.endswith("-v2") for label in labels)).lower()
    )


def check_cycle_vectors(check: Checker) -> None:
    """Derive the cycle rule from the constitution and from the model."""
    source = "the model"
    check.agree("cycle.target_seconds", e.CYCLE_TARGET_SECONDS,
                c.CYCLE_TARGET_SECONDS, source)
    check.agree("cycle.activity_threshold_seconds", e.ACTIVITY_THRESHOLD_SECONDS,
                c.ACTIVITY_THRESHOLD_SECONDS, source)
    check.agree("cycle.grace_allowance_seconds", e.GRACE_ALLOWANCE_SECONDS,
                c.GRACE_ALLOWANCE_SECONDS, source)
    check.equal(
        "cycle.threshold_plus_grace",
        e.ACTIVITY_THRESHOLD_SECONDS + e.GRACE_ALLOWANCE_SECONDS,
    )

    # The boundary is resolved in the operator's favour: exactly 18 hours of
    # uptime, equivalently exactly 6 hours of downtime, meets the cycle.
    check.equal("cycle.boundary_met_seconds", e.ACTIVITY_THRESHOLD_SECONDS)
    check.equal("cycle.boundary_failed_seconds", e.ACTIVITY_THRESHOLD_SECONDS - 1)
    check.equal(
        "cycle.boundary_met_downtime_seconds",
        e.CYCLE_TARGET_SECONDS - e.ACTIVITY_THRESHOLD_SECONDS,
    )
    check.equal(
        "cycle.boundary_failed_downtime_seconds",
        e.CYCLE_TARGET_SECONDS - e.ACTIVITY_THRESHOLD_SECONDS + 1,
    )
    check.equal("cycle.boundary_met", str(e.met_cycle(e.ACTIVITY_THRESHOLD_SECONDS)).lower())
    check.equal(
        "cycle.boundary_failed",
        str(e.met_cycle(e.ACTIVITY_THRESHOLD_SECONDS - 1)).lower(),
    )
    check.equal("cycle.full_window_met", str(e.met_cycle(e.CYCLE_TARGET_SECONDS)).lower())
    check.equal("cycle.zero_uptime_met", str(e.met_cycle(0)).lower())


def check_base_permission_vectors(check: Checker) -> None:
    founder_leg = e.BASE_LEGS["founder_operator"]
    fixed_total = e.BASE_PERMISSION_TOTAL - founder_leg
    check.agree("base.founder_operator_leg", founder_leg, c.FOUNDER_OPERATOR_LEG, "the model")
    check.agree("base.permission_total", e.BASE_PERMISSION_TOTAL,
                c.BASE_PERMISSION_TOTAL, "the model")
    check.agree("base.fixed_leg_total", fixed_total, c.FIXED_LEG_TOTAL, "the model")
    # The four retained legs are exactly the base permission less the Founder
    # portion, so a failed cycle changes one beneficiary and nothing else.
    check.equal(
        "base.fixed_legs_sum",
        sum(leg for channel, leg in e.BASE_LEGS.items() if channel != "founder_operator"),
    )


def check_referral_vectors(check: Checker, manifest_caps: dict[str, int]) -> None:
    consumed = e.full_schedule(e.REFERRAL_AMOUNT)
    cap = e.CHANNEL_CAPS[e.REFERRAL_CHANNEL]
    check.agree("referral.amount", e.REFERRAL_AMOUNT, c.REFERRAL_AMOUNT, "the model")
    check.agree("referral.channel", e.REFERRAL_CHANNEL, c.REFERRAL_CHANNEL, "the model")
    check.agree("referral.channel_cap", cap, manifest_caps[e.REFERRAL_CHANNEL])
    check.equal("referral.full_consumption", consumed)
    check.equal("referral.consumption_remainder", cap - consumed)
    check.agree("referral.referred_beneficiary_kind", e.REFERRED_BENEFICIARY_KIND,
                c.REFERRED_BENEFICIARY_KIND, "the model")
    check.agree("referral.unreferred_beneficiary_kind", e.UNREFERRED_BENEFICIARY_KIND,
                c.UNREFERRED_BENEFICIARY_KIND, "the model")
    check.equal("referral.unconditional", str(c.REFERRAL_UNCONDITIONAL).lower())

    # The referral channel is consumed by the per-seat-cycle accrual alone, so
    # it must not be reachable through the placeholder direct-issue path.
    check.agree(
        "referral.placeholder_direct_channels",
        len(e.PLACEHOLDER_DIRECT_CHANNELS),
        len(c.PLACEHOLDER_DIRECT_CHANNELS),
        "the model",
    )
    check.equal(
        "referral.direct_issue_admits_referral",
        str(e.REFERRAL_CHANNEL in c.PLACEHOLDER_DIRECT_CHANNELS).lower(),
    )


def check_reallocation_vectors(check: Checker, custody: dict[str, str]) -> None:
    """Derive the split arithmetic and require the run to have produced it."""
    leg = e.BASE_LEGS["founder_operator"]

    # Window 100: seven seats tie at a full window, leaving a remainder of 5.
    share, remainder = e.equal_split(leg, 7)
    check.agree(
        "reallocation.seven_winner_share", share, custody["founder_seat:00001"],
        "the run's custody",
    )
    check.equal("reallocation.seven_winner_remainder", remainder)
    check.equal("reallocation.seven_winner_reserved", share * 7)
    check.equal("reallocation.seven_winner_pot", leg)

    # Window 101: one winner absorbs the pot including the carried remainder.
    carried_pot = leg + remainder
    carried_share, carried_remainder = e.equal_split(carried_pot, 1)
    check.equal("reallocation.carried_pot", carried_pot)
    check.equal("reallocation.single_winner_share", carried_share)
    check.equal("reallocation.single_winner_remainder", carried_remainder)

    # Window 102: nobody met the cycle, so the whole portion carries forward,
    # and window 103 then delivers two portions at once.
    check.equal("reallocation.empty_winner_carry", leg)
    check.equal("reallocation.empty_winner_founder_legs", 0)
    check.equal("reallocation.carried_forward_pot", leg * 2)
    check.equal("reallocation.carried_forward_share", e.equal_split(leg * 2, 1)[0])


def check_scenario_vectors(check: Checker, result: dict[str, Any]) -> None:
    records = result["records"]
    metrics = result["metrics"]
    accepted = [record for record in records if record["accepted"]]

    check.equal("scenario.event_count", len(records))
    check.equal("scenario.accepted_count", len(accepted))
    check.equal("scenario.rejected_count", len(records) - len(accepted))
    check.equal("scenario.events_digest", result["events_digest"])
    check.equal("scenario.trace_digest", result["trace_digest"])
    check.equal("scenario.state_digest", result["state_digest"])
    check.equal("scenario.result_digest", result["result_digest"])

    for key in (
        "issued_supply_atomic",
        "outstanding_permissions_atomic",
        "performance_carry_atomic",
        "founder_accounted_atomic",
        "unreferred_pool_atomic",
        "activated_seat_count",
        "pending_permission_count",
        "evaluated_permission_key_count",
        "referral_accrual_key_count",
        "bound_uptime_record_count",
        "accepted_direct_decision_count",
    ):
        check.equal(f"scenario.{key}", metrics[key])

    # The carry conservation identity, derived from the constitution's Founder
    # leg and the run's own evaluated key count rather than read from a metric.
    evaluations = metrics["evaluated_permission_key_count"]
    check.agree(
        "scenario.founder_accounted_identity",
        evaluations * e.BASE_LEGS["founder_operator"],
        metrics["founder_accounted_atomic"],
        "the run",
    )

    for name, custody_key in CUSTODY_KEYS.items():
        check.equal(
            f"scenario.custody.{name}", result["final_state"]["typed_custody"].get(custody_key, "0")
        )
    for seat in range(0, 8):
        check.equal(
            f"scenario.custody.founder_seat_{seat:05d}",
            result["final_state"]["typed_custody"].get(f"founder_seat:{seat:05d}", "0"),
        )

    check.equal(
        "scenario.custody_total",
        sum(int(value) for value in result["final_state"]["typed_custody"].values()),
    )
    check.equal("scenario.result_codes", ",".join(sorted({r["result"] for r in records})))
    check.equal(
        "scenario.result_codes_are_modelled",
        str({r["result"] for r in records} == MODELLED_CODES).lower(),
    )


def check_trace_vectors(check: Checker, records: list[dict[str, Any]]) -> None:
    for record in records:
        index = record["index"]
        check.equal(f"record{index}.kind", record["kind"])
        check.equal(f"record{index}.result", record["result"])


def check_atomicity_vectors(check: Checker, records: list[dict[str, Any]]) -> None:
    """Derive the zero-write claims from the trace rather than asserting them."""
    rejected = [record for record in records if not record["accepted"]]
    check.equal("atomicity.rejected_events", len(rejected))
    check.equal(
        "atomicity.rejected_journal_entries",
        sum(len(record["journal"]) for record in rejected),
    )
    check.equal(
        "atomicity.rejected_state_changes",
        sum(
            1
            for record in rejected
            if record["state_digest_before"] != record["state_digest_after"]
        ),
    )
    check.equal(
        "atomicity.accepted_zero_amounts",
        sum(
            1
            for record in records
            for item in record["journal"]
            if int(item["amount_atomic"]) == 0
        ),
    )
    # Only a base evaluation may move the performance carry.
    carry_kinds = {
        record["kind"]
        for record in records
        for item in record["journal"]
        if item["bucket"] == "carry:performance"
    }
    check.equal("atomicity.carry_moving_kinds", ",".join(sorted(carry_kinds)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--vectors",
        type=Path,
        default=ROOT / "test-vectors" / "founder-economy-simulator-v2.txt",
    )
    arguments = parser.parse_args()

    inconsistencies = e.check_constitution_is_self_consistent()
    for detail in inconsistencies:
        sys.stderr.write(f"constitution inconsistency: {detail}\n")
    if inconsistencies:
        return 1

    try:
        manifest = load_manifest_file(ROOT / MANIFEST_PATH)
    except ManifestError as error:
        sys.stderr.write(f"manifest rejected: {error.code}: {error.detail}\n")
        return 1

    events = load_events_file(ROOT / EVENTS_PATH)
    result = simulate(manifest, events)
    if simulate(manifest, events)["result_digest"] != result["result_digest"]:
        sys.stderr.write("the simulator is not deterministic across repeated runs\n")
        return 1

    manifest_caps = {
        entry["id"]: int(entry["cap_atomic"]) for entry in manifest.source["channels"]
    }
    custody = result["final_state"]["typed_custody"]

    check = Checker(read_vectors(arguments.vectors))
    check_identity_vectors(check, result)
    check_cycle_vectors(check)
    check_base_permission_vectors(check)
    check_referral_vectors(check, manifest_caps)
    check_reallocation_vectors(check, custody)
    check_scenario_vectors(check, result)
    check_trace_vectors(check, result["records"])
    check_atomicity_vectors(check, result["records"])
    check.require_full_coverage()

    for failure in check.failures:
        sys.stderr.write(f"vector mismatch: {failure}\n")
    if check.failures:
        return 1

    sys.stdout.write(
        f"derived and matched {check.checked} founder-economy-simulator-v2 vectors\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
