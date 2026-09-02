"""Deriving a window's measured seats from chain state.

This is the whole point of version eight. Version seven's `execute_block` takes
an `UptimeSchedule` a caller supplies; version eight derives one, so a node
cannot be handed a different answer than its peers computed.

Three things are read and nothing is supplied: whether a seat is in scope and in
span follow from its recorded `activation_height` through `cycle-boundary-v1`,
and its credited slots follow from its window record — of which **an absent
record means a fully credited seat**, because a slot bit begins set and evidence
only ever removes credit.

**Record completeness is structural.** The seat set is derived from the seat
table rather than supplied, so a seat cannot be omitted and a seat with no
window record is present with a full credit rather than absent. That closes the
gap `founder-economy-simulator-v2` and `cycle-boundary-v1` both record, by
construction rather than by validation.

**The collection mark and the recorded referrer are not here**, and their
absence is the contract. ADR 0055 derives it from two sentences of the accepted
settlement, and version seven's kernel performs it: a measurement able to supply
a different mark could set an accrued bit in a window the seat's own mint can no
longer reach.
"""

from __future__ import annotations

from dataclasses import dataclass

from .state import all_slots_credited, credited_slots, decode_seat_window_value
from .state import seat_window_key
from . import contract as c
from .slots import in_scope, in_span

__all__ = ["MeasuredSeat", "derive_schedule", "seat_uptime_seconds"]


@dataclass(frozen=True)
class MeasuredSeat:
    """One measured seat for one window, in version seven's three fields.

    Three fields and not five, for the reason ADR 0055 gives. `uptime_seconds`
    is the denomination `founder-economy-simulator-v2` already accepts, so
    binding the carrier renamed nothing.
    """

    seat_id: int
    uptime_seconds: int
    in_span: bool


def seat_uptime_seconds(credited: int, disputed: int) -> int:
    """Whole hours, by construction: a slot is credited or it is not."""
    return credited_slots(credited, disputed) * c.SLOT_SECONDS


def derive_schedule(
    activations: dict[int, int],
    window: int,
    economy: dict[bytes, bytes],
) -> list[MeasuredSeat]:
    """Every in-scope seat of `window`, in ascending seat order.

    `activations` maps a seat identifier to its recorded activation height and
    holds only activated seats; a purchased, unactivated seat has no activation
    height and is in no window's scope.
    """
    measured: list[MeasuredSeat] = []
    for seat_id in sorted(activations):
        activation_height = activations[seat_id]
        if not in_scope(activation_height, window):
            continue
        record = economy.get(seat_window_key(window, seat_id))
        if record is None:
            credited, disputed = all_slots_credited(), 0
        else:
            credited, disputed = decode_seat_window_value(record)
        measured.append(
            MeasuredSeat(
                seat_id=seat_id,
                uptime_seconds=seat_uptime_seconds(credited, disputed),
                in_span=in_span(activation_height, window),
            )
        )
    return measured
