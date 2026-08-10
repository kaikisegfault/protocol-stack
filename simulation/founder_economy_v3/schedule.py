"""The seat schedule: the window check and the in-scope set.

Both rules are read from accepted artifacts rather than restated here. The
window functions come from `cycle-boundary-v1`, and the in-scope definition is
`uptime-measurement-v1`'s. What this module adds is applying them to the seat
table the economy model itself writes.
"""

from __future__ import annotations

from ..cycle_boundary.grid import (
    cycle_for_window,
    first_cycle_window,
    last_cycle_window,
    window_for_cycle,
)
from ..common.canonical import InvariantError
from .domain import Seat, State


def check_window(seat: Seat, cycle_index: int, cycle_window: int) -> str | None:
    """Return a rejection code, or None when this is the window for the cycle.

    The three codes stay distinct for the reason `cycle-boundary-v1` gives: a
    window before the span is a claim on issuance the seat had not begun, one
    after it is a claim on issuance that has ended, and one inside the span
    attached to the wrong cycle is an accounting error inside a live schedule.
    Only the last indicates a defect in the caller.
    """
    activation_height = seat.activation_height
    if cycle_window < first_cycle_window(activation_height):
        return "WINDOW_BEFORE_ISSUANCE"
    if cycle_window > last_cycle_window(activation_height):
        return "WINDOW_AFTER_ISSUANCE"
    if cycle_window != window_for_cycle(activation_height, cycle_index):
        return "WINDOW_NOT_FOR_CYCLE"

    derived = cycle_for_window(activation_height, cycle_window)
    if derived != cycle_index:
        raise InvariantError(
            f"window {cycle_window} accepted for cycle {cycle_index} but inverts to {derived}"
        )
    return None


def is_in_scope(seat: Seat, cycle_window: int) -> bool:
    """Whether a seat was activated strictly before this window's first height.

    There is deliberately no upper bound. A seat whose own 731 windows have
    ended still runs a node, is still measured, and may still be a reallocation
    winner, because the founder-directed rule asks for the highest uptime in the
    window rather than the highest among seats still issuing.
    """
    return first_cycle_window(seat.activation_height) <= cycle_window


def in_scope_seats(state: State, cycle_window: int) -> tuple[int, ...]:
    """The seats a window's record must cover, in ascending order.

    One of the model's two population-scale reads. It is bounded by the
    100,000-seat capacity rather than by the seat-cycle population, and it
    writes nothing.
    """
    return tuple(
        sorted(
            seat_id
            for seat_id, seat in state.seats.items()
            if is_in_scope(seat, cycle_window)
        )
    )
