#!/usr/bin/env python3
"""Independently derive and check the Founder Economy normative vectors.

Every recorded value is rederived from the loaded manifest and a live
simulation run, then compared. Restating a recorded value instead of deriving
it would make the vector file unfalsifiable.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.founder_economy import contract as c
from simulation.common.canonical import MAX_U64, label_prefix
from simulation.founder_economy.engine import (
    EVENTS_LABEL,
    RESULT_LABEL,
    RESULT_SCHEMA,
    TRACE_LABEL,
    simulate,
)
from simulation.founder_economy.domain import STATE_LABEL
from simulation.founder_economy.manifest import load_manifest_file
from simulation.founder_economy.validation import load_events_file

ROOT = Path(__file__).resolve().parents[2]
MODELLED_CODES = frozenset(
    {
        "INVALID_JSON",
        "UNKNOWN_FIELD",
        "SCHEMA",
        "TYPE",
        "RANGE",
        "MANIFEST_MISMATCH",
        "ARITHMETIC_OVERFLOW",
        "SUPPLY_MISMATCH",
        "CYCLE_RANGE",
        "REPLAY",
        "MISSING_RESEARCH_INPUT",
        "INVALID_RESEARCH_INPUT",
        "INVALID_PERFORMANCE_ALLOCATION",
        "CHANNEL_CAP",
        "PERMISSION_NOT_FOUND",
        "INVARIANT",
        "INVALID_REFERRER",
        "SEAT_NOT_ACTIVATED",
        "SEAT_NOT_REFERRED",
        "INVALID_CHANNEL",
        "ZERO_AMOUNT",
        "NOT_ELIGIBLE",
    }
)
CUSTODY_KEYS = {
    "venture_escrow": "venture_escrow:global",
    "community_grants_escrow": "community_grants_escrow:global",
    "developer_incentives_escrow": "developer_incentives_escrow:global",
    "system_creator_company": "system_creator_company:global",
    "founder_seat_00000": "founder_seat:00000",
    "founder_seat_00001": "founder_seat:00001",
    "founder_seat_00002": "founder_seat:00002",
    "founder_seat_00003": "founder_seat:00003",
    "direct_beneficiary": "direct_beneficiary:research-user-0001",
}


class Checker:
    def __init__(self, recorded: dict[str, str]) -> None:
        self.recorded = recorded
        self.failures: list[str] = []
        self.seen: set[str] = set()

    @property
    def checked(self) -> int:
        return len(self.seen)

    def equal(self, key: str, derived: object) -> None:
        if key not in self.recorded:
            self.failures.append(f"{key}: not recorded in the vector file")
            return
        self.seen.add(key)
        expected = self.recorded[key]
        if str(derived) != expected:
            self.failures.append(f"{key}: derived {derived!r}, recorded {expected!r}")

    def require_full_coverage(self) -> None:
        """Fail closed when a recorded vector was never derived."""
        for key in sorted(set(self.recorded) - self.seen):
            self.failures.append(f"{key}: recorded but never derived")


def read_vectors(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, separator, value = stripped.partition("=")
        if not separator or key in values:
            raise ValueError(f"{path}:{number}: malformed or duplicate vector line")
        values[key] = value
    return values


def check_manifest_vectors(check: Checker, manifest) -> None:
    check.equal("schema", c.MANIFEST_SCHEMA)
    check.equal("manifest_file", "test-vectors/founder-economy-manifest-v1.json")
    check.equal("manifest_domain_label", c.MANIFEST_LABEL)
    check.equal("manifest_domain_label_length", len(label_prefix(c.MANIFEST_LABEL)) - 1)
    check.equal("manifest_canonical_json_length", manifest.canonical_length)
    check.equal("manifest_digest", manifest.manifest_digest)
    check.equal("u64_max", MAX_U64)

    display = c.MAXIMUM_SUPPLY_DISPLAY
    atomic = display * c.ATOMIC_UNITS_PER_DISPLAY_UNIT
    check.equal("denomination.decimal_places", c.DECIMAL_PLACES)
    check.equal("denomination.atomic_units_per_display_unit", c.ATOMIC_UNITS_PER_DISPLAY_UNIT)
    check.equal("denomination.maximum_supply_display", display)
    check.equal("denomination.maximum_supply_atomic", atomic)
    check.equal("denomination.u64_headroom", MAX_U64 - atomic)
    check.equal("denomination.maximum_decimal_multiplier", MAX_U64 // display)
    check.equal("denomination.nine_decimal_atomic", display * 1_000_000_000)
    check.equal(
        "denomination.nine_decimal.result",
        "ARITHMETIC_OVERFLOW" if display * 1_000_000_000 > MAX_U64 else "OK",
    )

    seats = c.FOUNDER_SEAT_CAPACITY
    cycles = c.ISSUANCE_CYCLES_PER_SEAT
    check.equal("seat_schedule.founder_seat_capacity", seats)
    check.equal("seat_schedule.maximum_seats_per_person", c.MAXIMUM_SEATS_PER_PERSON)
    check.equal("seat_schedule.issuance_cycles_per_seat", cycles)
    check.equal("seat_schedule.maximum_base_permission_count", seats * cycles)
    check.equal("seat_schedule.maximum_referral_permission_count", seats * cycles)


def check_channel_vectors(check: Checker) -> None:
    check.equal("channels.count", len(c.CHANNELS))
    founder = 0
    direct = 0
    for index, (channel_id, kind, cap) in enumerate(c.CHANNELS):
        check.equal(f"channel{index}.id", channel_id)
        check.equal(f"channel{index}.kind", kind)
        check.equal(f"channel{index}.cap", cap)
        if kind == c.DIRECT_MINT:
            direct += cap
        else:
            founder += cap
    check.equal("channels.founder_subtotal", founder)
    check.equal("channels.direct_subtotal", direct)
    check.equal("channels.total", founder + direct)


def check_schedule_vectors(check: Checker) -> None:
    seats = c.FOUNDER_SEAT_CAPACITY
    cycles = c.ISSUANCE_CYCLES_PER_SEAT
    base_total = 0
    per_seat_total = 0
    full_total = 0
    for channel_id, _, amount in c.BASE_LEGS:
        check.equal(f"base_permission.{channel_id}", amount)
        check.equal(f"per_seat_731.{channel_id}", amount * cycles)
        check.equal(f"full_schedule.{channel_id}", amount * cycles * seats)
        base_total += amount
        per_seat_total += amount * cycles
        full_total += amount * cycles * seats
    check.equal("base_permission.total", base_total)
    check.equal("per_seat_731.base_total", per_seat_total)
    check.equal("full_schedule.base_total", full_total)

    referral = c.REFERRAL_AMOUNT
    check.equal("referral_permission.amount", referral)
    check.equal("per_seat_731.referral", referral * cycles)
    check.equal("full_schedule.referral", referral * cycles * seats)
    check.equal("per_seat_731.founder_total", per_seat_total + referral * cycles)
    check.equal("full_schedule.founder_subtotal", full_total + referral * cycles * seats)


def check_fixture_vectors(check: Checker, result: dict) -> None:
    custody = result["final_state"]["typed_custody"]
    base = {channel: amount for channel, _, amount in c.BASE_LEGS}

    check.equal("active_fixture.seat_id", 0)
    check.equal("active_fixture.cycle_index", 0)
    check.equal("active_fixture.founder_beneficiary", 0)
    check.equal("active_fixture.base_outstanding_delta", c.BASE_PERMISSION_TOTAL)
    check.equal("active_fixture.issued_delta_before_exercise", 0)
    check.equal("active_fixture.issued_delta_after_exercise", c.BASE_PERMISSION_TOTAL)
    check.equal("active_fixture.outstanding_delta_after_exercise", 0)

    non_founder = sum(
        amount for channel, amount in base.items() if channel != "founder_operator"
    )
    check.equal("inactive_fixture.source_seat_id", 0)
    check.equal("inactive_fixture.cycle_index", 1)
    check.equal("inactive_fixture.performance_recipient0", 1)
    check.equal("inactive_fixture.performance_amount0", custody["founder_seat:00001"])
    check.equal("inactive_fixture.performance_recipient1", 2)
    check.equal("inactive_fixture.performance_amount1", custody["founder_seat:00002"])
    check.equal(
        "inactive_fixture.performance_total",
        int(custody["founder_seat:00001"]) + int(custody["founder_seat:00002"]),
    )
    check.equal("inactive_fixture.source_founder_credit", 0)
    check.equal("inactive_fixture.non_founder_legs_total", non_founder)
    check.equal("inactive_fixture.base_total", c.BASE_PERMISSION_TOTAL)

    check.equal("referral_fixture.seat_id", 0)
    check.equal("referral_fixture.cycle_index", 0)
    check.equal("referral_fixture.referrer_seat_id", 3)
    check.equal("referral_fixture.outstanding_delta", c.REFERRAL_AMOUNT)
    check.equal(
        "referral_fixture.issued_delta_after_exercise",
        custody["founder_seat:00003"],
    )

    check.equal("direct_fixture.channel", "liquidity_mining")
    check.equal("direct_fixture.decision_id", "research-direct-0001")
    check.equal("direct_fixture.beneficiary_id", "research-user-0001")
    check.equal("direct_fixture.amount", custody["direct_beneficiary:research-user-0001"])
    check.equal("direct_fixture.issued_delta", custody["direct_beneficiary:research-user-0001"])
    check.equal("direct_fixture.outstanding_delta", 0)


def check_scenario_vectors(check: Checker, result: dict) -> None:
    records = result["records"]
    rejected = [record for record in records if not record["accepted"]]
    metrics = result["metrics"]

    check.equal("schema", RESULT_SCHEMA)
    check.equal("manifest_file", "test-vectors/founder-economy-manifest-v1.json")
    check.equal("events_file", "simulation/founder_economy/fixtures/research-events-v1.json")
    check.equal("events_domain_label", EVENTS_LABEL)
    check.equal("state_domain_label", STATE_LABEL)
    check.equal("trace_domain_label", TRACE_LABEL)
    check.equal("result_domain_label", RESULT_LABEL)

    check.equal("scenario.manifest_canonical_length", result["manifest_canonical_length"])
    check.equal("scenario.event_count", len(records))
    check.equal("scenario.accepted_count", len(records) - len(rejected))
    check.equal("scenario.rejected_count", len(rejected))
    check.equal("scenario.events_digest", result["events_digest"])
    check.equal("scenario.trace_digest", result["trace_digest"])
    check.equal("scenario.state_digest", result["state_digest"])
    check.equal("scenario.result_digest", result["result_digest"])

    check.equal("scenario.issued_supply", metrics["issued_supply_atomic"])
    check.equal("scenario.outstanding_permissions", metrics["outstanding_permissions_atomic"])
    check.equal("scenario.pending_permission_count", metrics["pending_permission_count"])
    check.equal(
        "scenario.evaluated_permission_key_count",
        metrics["evaluated_permission_key_count"],
    )
    check.equal(
        "scenario.accepted_direct_decision_count",
        metrics["accepted_direct_decision_count"],
    )
    check.equal("scenario.activated_seat_count", metrics["activated_seat_count"])

    custody = result["final_state"]["typed_custody"]
    for name, key in CUSTODY_KEYS.items():
        check.equal(f"scenario.custody.{name}", custody[key])

    for index, record in enumerate(records):
        check.equal(f"record{index}.kind", record["kind"])
        check.equal(f"record{index}.result", record["result"])

    writes = sum(
        1
        for record in rejected
        if record["state_digest_before"] != record["state_digest_after"]
    )
    check.equal("atomic_failure.rejected_state_writes", writes)
    check.equal(
        "atomic_failure.rejected_journal_entries",
        sum(len(record["journal"]) for record in rejected),
    )
    check.equal("atomic_failure.replay_identifiers_consumed", replayed_identifiers(records))


ATOMICITY_EVENTS: list[dict] = [
    {"id": "seed-3", "kind": "activate_seat", "seat_id": 3, "referrer_seat_id": None},
    {"id": "seed-0", "kind": "activate_seat", "seat_id": 0, "referrer_seat_id": 3},
    {
        "id": "creation-missing-input",
        "kind": "evaluate_base_permission",
        "seat_id": 0,
        "cycle_index": 0,
        "activity_result": None,
        "performance_allocation": None,
    },
    {
        "id": "creation-accepted",
        "kind": "evaluate_base_permission",
        "seat_id": 0,
        "cycle_index": 0,
        "activity_result": {"seat_id": 0, "cycle_index": 0, "active": True},
        "performance_allocation": None,
    },
    {
        "id": "creation-replay",
        "kind": "evaluate_base_permission",
        "seat_id": 0,
        "cycle_index": 0,
        "activity_result": {"seat_id": 0, "cycle_index": 0, "active": True},
        "performance_allocation": None,
    },
    {
        "id": "exercise-missing",
        "kind": "exercise_permission",
        "seat_id": 0,
        "cycle_index": 5,
        "permission_kind": "base",
    },
    {
        "id": "exercise-accepted",
        "kind": "exercise_permission",
        "seat_id": 0,
        "cycle_index": 0,
        "permission_kind": "base",
    },
    {
        "id": "exercise-second",
        "kind": "exercise_permission",
        "seat_id": 0,
        "cycle_index": 0,
        "permission_kind": "base",
    },
    {
        "id": "direct-ineligible",
        "kind": "direct_issue",
        "channel": "liquidity_mining",
        "decision_id": "atomicity-decision",
        "beneficiary_id": "atomicity-user",
        "amount_atomic": "100",
        "eligibility_result": {
            "channel": "liquidity_mining",
            "decision_id": "atomicity-decision",
            "beneficiary_id": "atomicity-user",
            "amount_atomic": "100",
            "eligible": False,
        },
    },
    {
        "id": "direct-over-cap",
        "kind": "direct_issue",
        "channel": "initial_mystery_box_incentives",
        "decision_id": "atomicity-over-cap",
        "beneficiary_id": "atomicity-user",
        "amount_atomic": "1250010000000001",
        "eligibility_result": {
            "channel": "initial_mystery_box_incentives",
            "decision_id": "atomicity-over-cap",
            "beneficiary_id": "atomicity-user",
            "amount_atomic": "1250010000000001",
            "eligible": True,
        },
    },
]
CREATION_KINDS = {"evaluate_base_permission", "evaluate_referral_permission"}


def check_atomicity_vectors(check: Checker, manifest) -> None:
    """Derive the zero-write claims from a run that rejects each transition."""
    records = simulate(manifest, ATOMICITY_EVENTS)["records"]
    rejected = [record for record in records if not record["accepted"]]
    if len(rejected) != 6:
        check.failures.append(
            f"atomicity scenario rejected {len(rejected)} events, expected 6"
        )

    def writes(kinds: set[str]) -> int:
        return sum(
            1
            for record in rejected
            if record["kind"] in kinds
            and (
                record["state_digest_before"] != record["state_digest_after"]
                or record["journal"]
            )
        )

    check.equal("atomic_failure.creation_state_writes", writes(CREATION_KINDS))
    check.equal("atomic_failure.exercise_state_writes", writes({"exercise_permission"}))
    check.equal("atomic_failure.direct_state_writes", writes({"direct_issue"}))

    final = simulate(manifest, ATOMICITY_EVENTS)["final_state"]
    accepted_creations = sum(
        1 for record in records if record["accepted"] and record["kind"] in CREATION_KINDS
    )
    accepted_direct = sum(
        1 for record in records if record["accepted"] and record["kind"] == "direct_issue"
    )
    consumed = (
        len(final["evaluated_permission_keys"]) - accepted_creations
        + len(final["accepted_direct_decision_ids"]) - accepted_direct
    )
    check.equal("atomic_failure.replay_identifiers_consumed", consumed)


def check_negative_vectors(check: Checker) -> None:
    """Confirm every recorded rejection names a code this simulator models.

    The rejections themselves are executed by the simulator error tests; this
    stage exists so an unmodelled code cannot sit unnoticed in the vector file.
    """
    for key in sorted(check.recorded):
        if key.startswith("negative.") and key.endswith(".result"):
            recorded = check.recorded[key]
            check.equal(key, recorded if recorded in MODELLED_CODES else "UNMODELLED")


def replayed_identifiers(records: list[dict]) -> int:
    """Count rejected events that nevertheless consumed a replay identifier.

    A consumed identifier would make the state digest change, so a rejection
    that preserves the digest cannot have recorded one.
    """
    return sum(
        1
        for record in records
        if not record["accepted"]
        and record["state_digest_before"] != record["state_digest_after"]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest-vectors",
        type=Path,
        default=ROOT / "test-vectors" / "founder-economy-manifest-v1.txt",
    )
    parser.add_argument(
        "--simulator-vectors",
        type=Path,
        default=ROOT / "test-vectors" / "founder-economy-simulator-v1.txt",
    )
    arguments = parser.parse_args()

    manifest = load_manifest_file(ROOT / "test-vectors" / "founder-economy-manifest-v1.json")
    events = load_events_file(
        ROOT / "simulation" / "founder_economy" / "fixtures" / "research-events-v1.json"
    )
    result = simulate(manifest, events)

    manifest_check = Checker(read_vectors(arguments.manifest_vectors))
    check_manifest_vectors(manifest_check, manifest)
    check_channel_vectors(manifest_check)
    check_schedule_vectors(manifest_check)
    check_fixture_vectors(manifest_check, result)
    check_atomicity_vectors(manifest_check, manifest)
    check_negative_vectors(manifest_check)
    manifest_check.require_full_coverage()

    simulator_check = Checker(read_vectors(arguments.simulator_vectors))
    check_scenario_vectors(simulator_check, result)
    simulator_check.require_full_coverage()

    failures = manifest_check.failures + simulator_check.failures
    for failure in failures:
        sys.stderr.write(f"vector mismatch: {failure}\n")
    if failures:
        return 1

    sys.stdout.write(
        f"derived and matched {manifest_check.checked} manifest and "
        f"{simulator_check.checked} simulator vectors\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
