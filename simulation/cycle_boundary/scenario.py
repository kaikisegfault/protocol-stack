"""The recorded cycle-boundary scenario.

Deterministic and closed over the module: no seed, no clock, no file input. The
activation heights are chosen at grid boundaries rather than at round numbers,
so the recorded schedule exercises the cases where an off-by-one in the grid
would be invisible at a height in the middle of a window.
"""

from __future__ import annotations

from simulation.common.canonical import CodedError

from . import contract as c
from .model import CycleBoundary

# Heights chosen so the boundary carries the evidence:
#   genesis, the last height of window 0, the first height of window 1, and a
#   height inside window 3. The first two must produce the same span, which is
#   what makes the grid shared rather than per-seat.
GENESIS_SEAT = 0
WINDOW_END_SEAT = 1
WINDOW_START_SEAT = 2
INTERIOR_SEAT = 3
SAME_BLOCK_SEAT = 7
UNACTIVATED_SEAT = 4

INTERIOR_HEIGHT = 100_000

ACTIVATIONS: tuple[tuple[int, int], ...] = (
    (GENESIS_SEAT, c.GENESIS_HEIGHT),
    (WINDOW_END_SEAT, c.CYCLE_BLOCKS - 1),
    (WINDOW_START_SEAT, c.CYCLE_BLOCKS),
    (INTERIOR_SEAT, INTERIOR_HEIGHT),
    (SAME_BLOCK_SEAT, INTERIOR_HEIGHT),
)

# (label, seat_id, height) rejections, including two pairs carrying two defects
# at once so the recorded order is proved rather than asserted.
ACTIVATION_REJECTIONS: tuple[tuple[str, int, int], ...] = (
    ("seat_above_capacity", c.FOUNDER_SEAT_CAPACITY, INTERIOR_HEIGHT),
    ("height_span_unrepresentable", 10, c.MAX_HEIGHT),
    ("replayed_seat", INTERIOR_SEAT, INTERIOR_HEIGHT),
    ("height_below_recorded", 11, INTERIOR_HEIGHT - 1),
    # Both defects at once: the seat bound is reported before the height bound.
    ("seat_and_height_both_out_of_range", c.FOUNDER_SEAT_CAPACITY, c.MAX_HEIGHT),
    # Both defects at once: a replayed seat is reported before a stale height.
    ("replayed_seat_with_stale_height", INTERIOR_SEAT, 0),
)

# (label, seat_id, cycle_index, cycle_window) checks covering every code.
CHECKS: tuple[tuple[str, int, int, int], ...] = (
    ("first_cycle", GENESIS_SEAT, 0, 1),
    ("last_cycle", GENESIS_SEAT, c.MAX_CYCLE_INDEX, c.ISSUANCE_CYCLES_PER_SEAT),
    ("interior_cycle", INTERIOR_SEAT, 365, 369),
    ("window_before_span", GENESIS_SEAT, 0, 0),
    ("window_after_span", GENESIS_SEAT, c.MAX_CYCLE_INDEX, c.ISSUANCE_CYCLES_PER_SEAT + 1),
    ("window_in_span_wrong_cycle", GENESIS_SEAT, 5, 1),
    ("unactivated_seat", UNACTIVATED_SEAT, 0, 1),
    ("cycle_above_span", GENESIS_SEAT, c.ISSUANCE_CYCLES_PER_SEAT, 1),
    ("seat_above_capacity", c.FOUNDER_SEAT_CAPACITY, 0, 1),
    # Both defects at once: the seat bound is reported before the cycle bound.
    ("seat_and_cycle_both_out_of_range", c.FOUNDER_SEAT_CAPACITY, c.ISSUANCE_CYCLES_PER_SEAT, 1),
    # Both defects at once: the cycle bound is reported before activation.
    ("unactivated_seat_and_cycle_out_of_range", UNACTIVATED_SEAT, c.ISSUANCE_CYCLES_PER_SEAT, 1),
)


def build() -> CycleBoundary:
    """Apply the accepted activations in order."""
    boundary = CycleBoundary()
    for seat_id, height in ACTIVATIONS:
        boundary.record_activation(seat_id, height)
    return boundary


def activation_rejection_codes() -> dict[str, str]:
    """Run each rejection against a rebuilt scenario and record what it produced.

    Each attempt starts from a fresh accepted state, so one rejection cannot
    change what the next one reports, and none of them can alter the recorded
    state digest.
    """
    codes: dict[str, str] = {}
    for label, seat_id, height in ACTIVATION_REJECTIONS:
        boundary = build()
        try:
            boundary.record_activation(seat_id, height)
        except CodedError as error:
            codes[label] = error.code
        else:
            codes[label] = "ACCEPTED"
    return codes


def check_codes() -> dict[str, str]:
    boundary = build()
    return {
        label: boundary.check_window(seat_id, cycle_index, cycle_window).code
        for label, seat_id, cycle_index, cycle_window in CHECKS
    }
