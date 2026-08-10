"""Independently derive and check the founder-economy-simulator-v3 vectors.

Every recorded value is derived twice: once from the founder documents through
`expected.py` and `walk.py`, neither of which imports anything from
`simulation/`, and once from a live model run. A value both sources agree on has
been reached from the Founder Constitution and from the implementation
independently. Restating a recorded value instead of deriving it would make the
vector file unfalsifiable.

The verifier fails closed in both directions: a derived key the file does not
carry is a failure, and a recorded key no derivation reaches is a failure too.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import expected as e
import verify_scenario as s
import walk as w
from checker import Checker, read_vectors

from simulation.common.canonical import MAX_U64, InvariantError
from simulation.cycle_boundary.model import CycleBoundary
from simulation.founder_economy_v3 import contract as c
from simulation.founder_economy_v3.domain import STATE_LABEL, Seat, State
from simulation.founder_economy_v3.engine import (
    EVENTS_LABEL,
    RESULT_LABEL,
    RESULT_SCHEMA,
    TRACE_LABEL,
    simulate,
)
from simulation.founder_economy_v3.schedule import check_window, in_scope_seats
from simulation.founder_economy_v3.uptime import RECORD_LABEL
from simulation.founder_economy_v3.validation import load_events_file

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "test-vectors" / "founder-economy-manifest-v2.json"
FIXTURE = ROOT / "simulation" / "founder_economy_v3" / "fixtures" / "research-events-v3.json"
VECTORS = ROOT / "test-vectors" / "founder-economy-simulator-v3.txt"

# Windows the scenario's schedule makes interesting: before any seat opens, the
# window seats 0..7 open in, the window seat 8 joins them in, and one beyond.
SCOPE_PROBE_WINDOWS: tuple[int, ...] = (0, 1, 2, 3)


def load_fixture() -> list[dict[str, Any]]:
    """Read the scenario as plain JSON, so the walk shares no parser with the model."""
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def check_contract_vectors(check: Checker) -> None:
    check.equal("schema", RESULT_SCHEMA)
    check.equal("state_domain_label", STATE_LABEL)
    check.equal("events_domain_label", EVENTS_LABEL)
    check.equal("trace_domain_label", TRACE_LABEL)
    check.equal("result_domain_label", RESULT_LABEL)
    check.equal("uptime_record_domain_label", RECORD_LABEL)
    # Every version-three label carries its version, so no digest computed under
    # version one or two can be replayed as version three.
    labels = (EVENTS_LABEL, STATE_LABEL, TRACE_LABEL, RESULT_LABEL, RECORD_LABEL)
    check.equal("labels_are_version_three", all(label.endswith("-v3") for label in labels))
    check.equal("labels_are_distinct", len(set(labels)) == len(labels))
    # The manifest is not re-versioned, because no founder-directed figure moves.
    check.equal("manifest_domain_label", c.MANIFEST_LABEL)
    check.equal("manifest_label_is_version_two", c.MANIFEST_LABEL.endswith("-v2"))

    check.agree("maximum_supply_atomic", e.MAXIMUM_SUPPLY_ATOMIC, c.MAXIMUM_SUPPLY_ATOMIC)
    check.agree("founder_operator_leg_atomic", e.FOUNDER_OPERATOR_LEG, c.FOUNDER_OPERATOR_LEG)
    check.agree("base_permission_total_atomic", e.BASE_PERMISSION_TOTAL, c.BASE_PERMISSION_TOTAL)
    check.agree("referral_amount_atomic", e.REFERRAL_AMOUNT, c.REFERRAL_AMOUNT)
    check.agree(
        "activity_threshold_seconds",
        e.ACTIVITY_THRESHOLD_SECONDS,
        c.ACTIVITY_THRESHOLD_SECONDS,
    )
    check.agree("cycle_target_seconds", e.CYCLE_TARGET_SECONDS, c.CYCLE_TARGET_SECONDS)
    check.agree("cycle_blocks", e.CYCLE_BLOCKS, c.CYCLE_BLOCKS)
    check.agree("issuance_cycles_per_seat", e.ISSUANCE_CYCLES_PER_SEAT, c.ISSUANCE_CYCLES_PER_SEAT)
    check.agree("founder_seat_capacity", e.FOUNDER_SEAT_CAPACITY, c.FOUNDER_SEAT_CAPACITY)
    check.agree("schedule_storage_bytes", e.SCHEDULE_STORAGE_BYTES, c.SCHEDULE_STORAGE_BYTES)
    # Executed rather than asserted: the bound manifest and grid contracts must
    # still agree on every shared founder figure, and a run refuses to start
    # otherwise.
    check.equal("bindings.agree", _bindings_agree())


def _bindings_agree() -> bool:
    try:
        c.assert_agrees_with_bindings()
    except InvariantError:
        return False
    return True


def check_rendering_vectors(check: Checker) -> None:
    """A height is a decimal string and a window is a number, derived not assumed."""
    check.equal("rendering.max_json_integer", e.MAX_JSON_INTEGER)
    check.agree("rendering.max_window", e.MAX_WINDOW, MAX_U64 // c.CYCLE_BLOCKS)
    check.equal(
        "rendering.window_is_an_exact_json_integer", e.window_is_exact_json_integer()
    )
    check.equal("rendering.height_exceeds_exact_json_integer", MAX_U64 > e.MAX_JSON_INTEGER)
    # The headroom is recorded so a later grid change that narrowed it is visible
    # rather than merely still passing.
    check.equal("rendering.window_headroom_factor", e.MAX_JSON_INTEGER // e.MAX_WINDOW)


def check_schedule_vectors(check: Checker, final_state: dict[str, Any]) -> None:
    """Each seat's recorded schedule, derived from the founder grid."""
    for key, seat in sorted(final_state["seats"].items()):
        seat_id = int(key)
        height = int(seat["activation_height"])
        check.equal(f"schedule.seat_{key}.activation_height", height)
        check.agree(
            f"schedule.seat_{key}.first_cycle_window",
            e.first_cycle_window(height),
            seat["first_cycle_window"],
        )
        check.agree(
            f"schedule.seat_{key}.last_cycle_window",
            e.last_cycle_window(height),
            seat["last_cycle_window"],
        )
        check.equal(
            f"schedule.seat_{key}.span_windows",
            seat["last_cycle_window"] - seat["first_cycle_window"] + 1,
        )
    check.equal("schedule.last_activation_height", int(final_state["last_activation_height"]))
    check.equal("schedule.activated_seats", len(final_state["seats"]))


def check_scope_vectors(check: Checker, heights: dict[int, int]) -> None:
    """The in-scope set a record must cover, derived and then produced live."""
    state = State(
        seats={
            seat_id: Seat(referrer_seat_id=None, activation_height=height)
            for seat_id, height in heights.items()
        }
    )
    for window in SCOPE_PROBE_WINDOWS:
        derived = e.in_scope_seats(heights, window)
        check.agree(
            f"scope.window_{window}.seats",
            ",".join(str(seat) for seat in derived) or "none",
            ",".join(str(seat) for seat in in_scope_seats(state, window)) or "none",
        )
        check.equal(f"scope.window_{window}.seat_count", len(derived))
    # A seat past its 731 windows stays in scope, because the founder rule ranks
    # the highest uptime in the window rather than among seats still issuing.
    beyond = e.last_cycle_window(min(heights.values())) + 1
    check.agree(
        "scope.beyond_issuance_span.seat_count",
        len(e.in_scope_seats(heights, beyond)),
        len(in_scope_seats(state, beyond)),
    )
    check.equal(
        "scope.monotonicity_refuses_a_late_in_scope_activation",
        _late_in_scope_activation_code(),
    )


def _late_in_scope_activation_code() -> str:
    """Show by execution how monotonicity bounds the completeness residue.

    Completeness is measured against the seat table as it stands, and the model
    has no current height for an evaluation. Once an activation lands at or above
    a window's first height, though, no later activation can be in scope for that
    window, because a lower height is refused outright.
    """
    first_height = c.CYCLE_BLOCKS  # the first height of window 1
    events = [
        {
            "id": "at-or-above",
            "kind": "activate_seat",
            "seat_id": 0,
            "referrer_seat_id": None,
            "activation_height": str(first_height),
        },
        {
            "id": "would-be-in-scope",
            "kind": "activate_seat",
            "seat_id": 1,
            "referrer_seat_id": None,
            "activation_height": str(first_height - 1),
        },
    ]
    records = simulate(str(MANIFEST), events)["records"]
    if records[0]["result"] != "OK":
        raise AssertionError("the control activation was rejected")
    return records[1]["result"]


def check_cross_model_vectors(check: Checker, heights: dict[int, int]) -> None:
    """Require the accepted cycle-boundary model and this one to agree.

    The economy model is the writer of activation heights and binds no foreign
    schedule, so agreement is a property to be proved rather than one enforced by
    a digest. Three sources must give the same answer: the founder restatement in
    `expected.py`, the accepted `cycle-boundary-v1` model, and this version.
    """
    boundary = CycleBoundary()
    for seat_id, height in sorted(heights.items()):
        boundary.record_activation(seat_id, height)

    probes: list[tuple[str, int, int, int]] = []
    for seat_id, height in sorted(heights.items()):
        first = e.first_cycle_window(height)
        last = e.last_cycle_window(height)
        probes += [
            (f"seat_{seat_id:05d}_cycle_0_correct", seat_id, 0, first),
            (f"seat_{seat_id:05d}_cycle_0_before", seat_id, 0, first - 1),
            (f"seat_{seat_id:05d}_cycle_0_next_window", seat_id, 0, first + 1),
            (f"seat_{seat_id:05d}_cycle_730_correct", seat_id, 730, last),
            (f"seat_{seat_id:05d}_cycle_730_after", seat_id, 730, last + 1),
        ]

    for name, seat_id, cycle_index, window in probes:
        seat = Seat(referrer_seat_id=None, activation_height=heights[seat_id])
        live = check_window(seat, cycle_index, window) or "ACCEPTED"
        accepted_model = boundary.check_window(seat_id, cycle_index, window).code
        if live != accepted_model:
            check.failures.append(
                f"cross_model.{name}: cycle-boundary-v1 gives {accepted_model!r} "
                f"and founder-economy-simulator-v3 gives {live!r}"
            )
            continue
        check.agree(f"cross_model.{name}", _expected_window_code(heights, seat_id, cycle_index, window), live)
    check.equal("cross_model.probes", len(probes))


def _expected_window_code(
    heights: dict[int, int], seat_id: int, cycle_index: int, window: int
) -> str:
    """The window verdict restated from the founder grid alone."""
    height = heights[seat_id]
    if window < e.first_cycle_window(height):
        return "WINDOW_BEFORE_ISSUANCE"
    if window > e.last_cycle_window(height):
        return "WINDOW_AFTER_ISSUANCE"
    if window != e.window_for_cycle(height, cycle_index):
        return "WINDOW_NOT_FOR_CYCLE"
    return "ACCEPTED"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vectors", type=Path, default=VECTORS)
    arguments = parser.parse_args()

    for failure in e.check_constitution_is_self_consistent() + e.check_two_constitutions_agree():
        print(f"closed-form derivation failed: {failure}")
        return 1

    events = load_events_file(FIXTURE)
    try:
        result = simulate(str(MANIFEST), events)
    except InvariantError as error:
        # A run refuses to start when the bound manifest and grid contracts have
        # drifted, so there is no result to check. That is the containment
        # working; reporting it as a verifier failure is the correct outcome.
        print(f"the model refused to run: {error}")
        return 1
    walk, walk_codes = w.replay(load_fixture())

    check = Checker(read_vectors(arguments.vectors))
    check_contract_vectors(check)
    check_rendering_vectors(check)
    check_schedule_vectors(check, result["final_state"])
    check_scope_vectors(check, walk.heights)
    check_cross_model_vectors(check, walk.heights)
    s.check_trace_vectors(check, result["records"], walk_codes)
    s.check_ordering_vectors(check, result["records"])
    s.check_scenario_vectors(check, result, walk)
    s.check_reallocation_vectors(check, load_fixture())
    s.check_atomicity_vectors(check, result["records"])
    s.check_coverage_vectors(check, result["records"])
    s.check_determinism_vectors(check, result, events)
    check.require_full_coverage()

    if check.failures:
        for failure in check.failures:
            print(failure)
        return 1
    print(f"derived and matched {check.checked} founder-economy-simulator-v3 vectors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
