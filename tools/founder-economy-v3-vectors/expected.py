"""Closed-form expectations for founder-economy-simulator-v3.

This module is the independence in the version-three verifier. It imports
nothing from `simulation/`.

It restates nothing that is already hand-restated. The economy tables come from
`tools/founder-economy-v2-vectors/expected.py` and the window grid from
`tools/cycle-boundary-vectors/expected.py`, both of which convert the Founder
Constitution and the pinned M1 commit interval by hand and neither of which
reads a model. A third hand-restatement of one constitutional rule would be a
third thing to keep equal, which is the failure the closed-form method exists to
avoid, and ADR 0026 already records that reasoning for the suite verifier.

What this module adds is version three's own rules, restated from the
specification rather than read from the implementation: the two ordered
rejection sequences, the in-scope set, and the bound that keeps a window an
exact JSON number.
"""

from __future__ import annotations

import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parents[1]
for _sibling in ("founder-economy-v2-vectors", "cycle-boundary-vectors"):
    _path = str(_TOOLS / _sibling)
    if _path not in sys.path:
        sys.path.append(_path)

import importlib.util as _importlib_util


def _load(name: str, relative: str):
    """Load a sibling verifier's closed-form module under its own name.

    Both siblings define a module called `expected`, so they are loaded by path
    rather than by name; importing them normally would make the second import
    return the first.
    """
    spec = _importlib_util.spec_from_file_location(name, _TOOLS / relative)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {relative}")
    module = _importlib_util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


economy = _load("expected_economy_v2", "founder-economy-v2-vectors/expected.py")
grid = _load("expected_cycle_boundary", "cycle-boundary-vectors/expected.py")

# --- re-exported so the verifier reads one constitution ----------------------

D = economy.D
MAXIMUM_SUPPLY_ATOMIC = economy.MAXIMUM_SUPPLY_ATOMIC
FOUNDER_SEAT_CAPACITY = economy.FOUNDER_SEAT_CAPACITY
ISSUANCE_CYCLES_PER_SEAT = economy.ISSUANCE_CYCLES_PER_SEAT
SEAT_CYCLE_POPULATION = economy.SEAT_CYCLE_POPULATION
CHANNEL_CAPS = economy.CHANNEL_CAPS
CHANNEL_ORDER = economy.CHANNEL_ORDER
BASE_LEGS = economy.BASE_LEGS
BASE_PERMISSION_TOTAL = economy.BASE_PERMISSION_TOTAL
FOUNDER_OPERATOR_LEG = economy.BASE_LEGS["founder_operator"]
REFERRAL_AMOUNT = economy.REFERRAL_AMOUNT
REFERRAL_CHANNEL = economy.REFERRAL_CHANNEL
PLACEHOLDER_DIRECT_CHANNELS = economy.PLACEHOLDER_DIRECT_CHANNELS
CYCLE_TARGET_SECONDS = economy.CYCLE_TARGET_SECONDS
ACTIVITY_THRESHOLD_SECONDS = economy.ACTIVITY_THRESHOLD_SECONDS
GRACE_ALLOWANCE_SECONDS = economy.GRACE_ALLOWANCE_SECONDS
met_cycle = economy.met_cycle
equal_split = economy.equal_split
full_schedule = economy.full_schedule
check_constitution_is_self_consistent = economy.check_constitution_is_self_consistent

CYCLE_BLOCKS = grid.CYCLE_BLOCKS
MAX_WINDOW = grid.MAX_WINDOW
MAX_U64 = grid.MAX_U64
MAX_SEAT_ID = grid.MAX_SEAT_ID
MAX_CYCLE_INDEX = grid.MAX_CYCLE_INDEX
SCHEDULE_STORAGE_BYTES = grid.SCHEDULE_STORAGE_BYTES
first_cycle_window = grid.first_cycle_window
last_cycle_window = grid.last_cycle_window
window_for_cycle = grid.window_for_cycle
window_of_height = grid.window_of_height
span_is_representable = grid.span_is_representable

# The largest integer a conforming JSON stack represents exactly. A height can
# exceed it and is therefore a decimal string; a window is a height divided by
# 28,800 and cannot, which is what keeps the uptime record's shape unchanged.
MAX_JSON_INTEGER = (1 << 53) - 1


def check_two_constitutions_agree() -> list[str]:
    """Require the two hand-restatements to agree on every shared figure.

    The economy module and the grid module were written independently and each
    restates the constitution's 24, 18, and 6 hours and its 731 cycles and
    100,000 seats. Version three depends on both, so a divergence between them
    is a defect in the evidence rather than in the model, and it is caught here
    instead of surfacing as a confusing model mismatch.
    """
    failures: list[str] = []
    for name, left, right in (
        ("CYCLE_TARGET_SECONDS", CYCLE_TARGET_SECONDS, grid.CYCLE_TARGET_SECONDS),
        (
            "ACTIVITY_THRESHOLD_SECONDS",
            ACTIVITY_THRESHOLD_SECONDS,
            grid.ACTIVITY_THRESHOLD_SECONDS,
        ),
        (
            "GRACE_ALLOWANCE_SECONDS",
            GRACE_ALLOWANCE_SECONDS,
            grid.GRACE_ALLOWANCE_SECONDS,
        ),
        (
            "ISSUANCE_CYCLES_PER_SEAT",
            ISSUANCE_CYCLES_PER_SEAT,
            grid.ISSUANCE_CYCLES_PER_SEAT,
        ),
        ("FOUNDER_SEAT_CAPACITY", FOUNDER_SEAT_CAPACITY, grid.FOUNDER_SEAT_CAPACITY),
    ):
        if left != right:
            failures.append(
                f"{name}: the economy restatement gives {left} and the grid "
                f"restatement gives {right}"
            )
    return failures


def window_is_exact_json_integer() -> bool:
    """Whether every window reachable from a representable height is exact."""
    return MAX_WINDOW <= MAX_JSON_INTEGER


def is_in_scope(activation_height: int, cycle_window: int) -> bool:
    """Whether a seat was activated strictly before this window's first height.

    `uptime-measurement-v1`'s definition, with no upper bound: a seat past its
    731 windows still runs a node and may still win a reallocation.
    """
    return first_cycle_window(activation_height) <= cycle_window


def in_scope_seats(activation_heights: dict[int, int], cycle_window: int) -> tuple[int, ...]:
    return tuple(
        sorted(
            seat_id
            for seat_id, height in activation_heights.items()
            if is_in_scope(height, cycle_window)
        )
    )


def activate_seat(
    activation_heights: dict[int, int],
    last_activation_height: int | None,
    seat_id: int,
    referrer_seat_id: int | None,
    activation_height: int,
) -> str:
    """Version three's activation rejection order, restated independently.

    Conditions 1, 3, 4, and 5 are version two's in version two's order, and
    conditions 2 and 6 are `cycle-boundary-v1`'s in its order.
    """
    if not 0 <= seat_id <= MAX_SEAT_ID:
        return "CYCLE_RANGE"
    if activation_height > MAX_U64 or not span_is_representable(activation_height):
        return "HEIGHT_RANGE"
    if referrer_seat_id is not None and (
        not 0 <= referrer_seat_id <= MAX_SEAT_ID or referrer_seat_id == seat_id
    ):
        return "INVALID_REFERRER"
    if seat_id in activation_heights:
        return "REPLAY"
    if referrer_seat_id is not None and referrer_seat_id not in activation_heights:
        return "SEAT_NOT_ACTIVATED"
    if last_activation_height is not None and activation_height < last_activation_height:
        return "HEIGHT_NOT_MONOTONIC"
    return "OK"


def record_is_valid(
    activation_heights: dict[int, int],
    record: dict | None,
    seat_id: int,
) -> bool:
    """Version two's record validity conditions, restated independently."""
    entries = record["entries"]
    if not entries:
        return False
    seen: set[int] = set()
    for entry in entries:
        listed = entry["seat_id"]
        if not 0 <= listed <= MAX_SEAT_ID:
            return False
        if listed in seen or listed not in activation_heights:
            return False
        if entry["uptime_seconds"] > CYCLE_TARGET_SECONDS:
            return False
        seen.add(listed)
    return seat_id in seen


def evaluate_base_permission(
    activation_heights: dict[int, int],
    evaluated_keys: set[tuple[int, int]],
    bound_windows: dict[int, object],
    record_identity,
    seat_id: int,
    cycle_index: int,
    record: dict | None,
) -> str:
    """Version three's evaluation rejection order, restated independently.

    `record_identity` stands in for the record digest: any injective function of
    the canonical record value works here, because the verifier only needs to
    know whether two records for one window are the same record, not what their
    digest is. Recomputing the digest would import the model's labelling.
    """
    if not 0 <= seat_id <= MAX_SEAT_ID or not 0 <= cycle_index <= MAX_CYCLE_INDEX:
        return "CYCLE_RANGE"
    if seat_id not in activation_heights:
        return "SEAT_NOT_ACTIVATED"
    if (seat_id, cycle_index) in evaluated_keys:
        return "REPLAY"
    if record is None:
        return "MISSING_UPTIME_RECORD"
    if not record_is_valid(activation_heights, record, seat_id):
        return "INVALID_UPTIME_RECORD"

    height = activation_heights[seat_id]
    window = record["cycle_window"]
    if window < first_cycle_window(height):
        return "WINDOW_BEFORE_ISSUANCE"
    if window > last_cycle_window(height):
        return "WINDOW_AFTER_ISSUANCE"
    if window != window_for_cycle(height, cycle_index):
        return "WINDOW_NOT_FOR_CYCLE"

    listed = {entry["seat_id"] for entry in record["entries"]}
    if any(not is_in_scope(activation_heights[seat], window) for seat in sorted(listed)):
        return "SEAT_NOT_IN_SCOPE"
    if listed != set(in_scope_seats(activation_heights, window)):
        return "INCOMPLETE_UPTIME_RECORD"

    bound = bound_windows.get(window)
    if bound is not None and bound != record_identity(record):
        return "INCONSISTENT_UPTIME_RECORD"
    return "OK"


def winner_seats(record: dict) -> tuple[int, ...]:
    """The highest uptime among the seats that met the cycle, restated."""
    qualified = [
        entry for entry in record["entries"] if met_cycle(entry["uptime_seconds"])
    ]
    if not qualified:
        return ()
    maximum = max(entry["uptime_seconds"] for entry in qualified)
    return tuple(
        sorted(entry["seat_id"] for entry in qualified if entry["uptime_seconds"] == maximum)
    )
