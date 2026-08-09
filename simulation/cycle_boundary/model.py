"""The cycle-boundary model: a seat activation table and a window check.

Recording an activation issues nothing, reserves nothing, and credits nothing.
Checking a window writes nothing. This model holds a schedule; it does not
measure uptime and cannot tell whether a seat was operational for any block.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from simulation.common.canonical import MAX_U64, CodedError, InvariantError, digest

from . import contract as c
from .grid import (
    cycle_for_window,
    first_cycle_window,
    last_cycle_window,
    span_is_representable,
    window_for_cycle,
)


@dataclass(frozen=True)
class CheckResult:
    """The outcome of a window check, carrying the derived cycle when accepted."""

    code: str
    cycle_index: int | None = None


@dataclass
class CycleBoundary:
    activation_heights: dict[int, int] = field(default_factory=dict)
    last_activation_height: int | None = None

    # --- transitions ----------------------------------------------------

    def record_activation(self, seat_id: int, height: int) -> None:
        """Record a seat's activation height.

        Conditions are ordered so a request carrying two defects has one defined
        result: an out-of-range seat before an out-of-range height, and a
        replayed seat before a non-monotonic height.
        """
        _require_count(seat_id, "seat_id")
        _require_count(height, "height")

        if seat_id > c.MAX_SEAT_ID:
            raise CodedError("SEAT_RANGE", f"seat {seat_id} above {c.MAX_SEAT_ID}")
        if height > c.MAX_HEIGHT or not span_is_representable(height):
            raise CodedError("HEIGHT_RANGE", f"height {height} has no representable span")
        if seat_id in self.activation_heights:
            raise CodedError("REPLAY", f"seat {seat_id} is already activated")
        if self.last_activation_height is not None and height < self.last_activation_height:
            raise CodedError(
                "HEIGHT_NOT_MONOTONIC",
                f"height {height} is below the recorded {self.last_activation_height}",
            )

        self.activation_heights[seat_id] = height
        self.last_activation_height = height

    def check_window(self, seat_id: int, cycle_index: int, cycle_window: int) -> CheckResult:
        """Decide whether `cycle_window` is the window for `(seat, cycle_index)`.

        A pure query. The three window codes stay distinct because a window
        before a seat's span, one after it, and one inside it attached to the
        wrong cycle are different failures, and only the last indicates a defect
        in the caller rather than an out-of-bounds request.
        """
        _require_count(seat_id, "seat_id")
        _require_count(cycle_index, "cycle_index")
        _require_count(cycle_window, "cycle_window")

        if seat_id > c.MAX_SEAT_ID:
            return CheckResult("SEAT_RANGE")
        if cycle_index > c.MAX_CYCLE_INDEX:
            return CheckResult("CYCLE_RANGE")

        activation_height = self.activation_heights.get(seat_id)
        if activation_height is None:
            return CheckResult("SEAT_NOT_ACTIVATED")

        if cycle_window < first_cycle_window(activation_height):
            return CheckResult("WINDOW_BEFORE_ISSUANCE")
        if cycle_window > last_cycle_window(activation_height):
            return CheckResult("WINDOW_AFTER_ISSUANCE")
        if cycle_window != window_for_cycle(activation_height, cycle_index):
            return CheckResult("WINDOW_NOT_FOR_CYCLE")

        derived = cycle_for_window(activation_height, cycle_window)
        if derived != cycle_index:
            raise InvariantError(
                f"window {cycle_window} accepted for cycle {cycle_index} but inverts to {derived}"
            )
        return CheckResult("ACCEPTED", derived)

    # --- queries --------------------------------------------------------

    def schedule(self, seat_id: int) -> tuple[int, int, int]:
        """A seat's activation height and its inclusive span endpoints."""
        activation_height = self.activation_heights.get(seat_id)
        if activation_height is None:
            raise CodedError("SEAT_NOT_ACTIVATED", f"seat {seat_id} is not activated")
        return (
            activation_height,
            first_cycle_window(activation_height),
            last_cycle_window(activation_height),
        )

    # --- canonical state ------------------------------------------------

    def canonical_state(self) -> dict[str, object]:
        """Seats in ascending identifier order, heights as decimal strings.

        A height is a u64 and can exceed the largest integer a conforming JSON
        stack represents exactly, so heights and windows are canonical decimal
        strings for the same reason monetary values are. Ordering by seat makes
        the digest cover the recorded schedule rather than the order activations
        happened to arrive in.
        """
        return {
            "schema": c.STATE_SCHEMA,
            "cycle_blocks": c.CYCLE_BLOCKS,
            "seats": [
                {
                    "seat_id": seat_id,
                    "activation_height": _height_string(self.activation_heights[seat_id]),
                    "first_cycle_window": _height_string(
                        first_cycle_window(self.activation_heights[seat_id])
                    ),
                    "last_cycle_window": _height_string(
                        last_cycle_window(self.activation_heights[seat_id])
                    ),
                }
                for seat_id in sorted(self.activation_heights)
            ],
            "last_activation_height": (
                None
                if self.last_activation_height is None
                else _height_string(self.last_activation_height)
            ),
        }

    def state_digest(self) -> str:
        return digest(c.STATE_LABEL, self.canonical_state())


def _height_string(value: int) -> str:
    """Render a u64 height or window as a canonical decimal string."""
    if type(value) is not int or not 0 <= value <= MAX_U64:
        raise InvariantError(f"cannot format non-u64 height: {value!r}")
    return str(value)


def _require_count(value: object, name: str) -> None:
    """Reject a non-count before it can reach an ordered rejection condition.

    A negative or non-integer input is an input-shape error rather than a
    modelled rejection, in the same way the economy model treats a value it
    could not canonicalize.
    """
    if not isinstance(value, int) or isinstance(value, bool):
        raise InvariantError(f"{name} {value!r} is not an integer")
    if value < 0:
        raise InvariantError(f"{name} {value} is negative")
