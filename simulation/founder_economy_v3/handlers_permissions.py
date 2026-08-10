"""Seat activation and base permission evaluation.

Version three records a seat's activation height and enforces the schedule that
follows from it. The window a cycle is evaluated against is no longer whatever
the record supplied.
"""

from __future__ import annotations

from typing import Any

from . import contract as c
from .domain import (
    Leg,
    PendingPermission,
    Seat,
    State,
    founder_custody_key,
    permission_key,
)
from ..common.canonical import required_sum
from ..cycle_boundary.grid import span_is_representable
from .operations import Outcome, accepted, carry_entries, check_reservable, failure, reserve
from .schedule import check_window, is_in_scope
from .uptime import (
    check_completeness,
    fixed_base_legs,
    met_cycle,
    record_digest,
    reallocate,
    uptime_of,
    validate_record,
    winner_seats,
)


def activate_seat(state: State, event: dict[str, Any]) -> Outcome:
    """Record a seat, its referrer, and the height its schedule starts from.

    Conditions 1, 3, 4, and 5 keep version two's relative order, and conditions
    2 and 6 keep `cycle-boundary-v1`'s, so the two models agree on which of two
    simultaneous defects is reported first.
    """
    seat_id = event["seat_id"]
    referrer = event["referrer_seat_id"]
    height = int(event["activation_height"])

    if not _seat_in_range(seat_id):
        return failure("CYCLE_RANGE")
    # A height whose complete 731-window span is not representable is refused
    # rather than wrapped, because a wrapped window would silently alias another
    # seat's schedule.
    if height > c.MAX_HEIGHT or not span_is_representable(height):
        return failure("HEIGHT_RANGE")
    if referrer is not None and (not _seat_in_range(referrer) or referrer == seat_id):
        return failure("INVALID_REFERRER")
    if seat_id in state.seats:
        return failure("REPLAY")
    # A referrer must itself be an activated seat, because the referral credits
    # `founder_seat:{referrer}` custody and a non-seat referrer has no bucket.
    if referrer is not None and referrer not in state.seats:
        return failure("SEAT_NOT_ACTIVATED")
    # A real activation executes inside the block that includes it, so a height
    # cannot decrease across the sequence a chain records. Enforcing it at the
    # writer is what stops a replayed or reordered activation installing a
    # schedule in the past and collecting windows the seat did not hold. Equal
    # heights are accepted, because one block may activate several seats.
    if state.last_activation_height is not None and height < state.last_activation_height:
        return failure("HEIGHT_NOT_MONOTONIC")

    state.seats[seat_id] = Seat(referrer_seat_id=referrer, activation_height=height)
    state.last_activation_height = height
    return accepted()


def evaluate_base_permission(state: State, event: dict[str, Any]) -> Outcome:
    seat_id = event["seat_id"]
    cycle_index = event["cycle_index"]
    if not _seat_in_range(seat_id) or not 0 <= cycle_index < c.ISSUANCE_CYCLES_PER_SEAT:
        return failure("CYCLE_RANGE")
    seat = state.seats.get(seat_id)
    if seat is None:
        return failure("SEAT_NOT_ACTIVATED")
    if permission_key(seat_id, cycle_index) in state.evaluated_permission_keys:
        return failure("REPLAY")

    record = event["cycle_uptime_record"]
    if record is None:
        return failure("MISSING_UPTIME_RECORD")
    if not validate_record(state, record, seat_id):
        return failure("INVALID_UPTIME_RECORD")

    window = record["cycle_window"]
    # The boundary and completeness checks come first because they are
    # properties of the record, the seat, and the schedule alone, while the
    # binding check below is a property of the run's history. Ordering them the
    # other way would make one defect produce two different codes depending on
    # whether the window happened to have been bound already.
    code = check_window(seat, cycle_index, window)
    if code is not None:
        return failure(code)
    code = check_completeness(state, record)
    if code is not None:
        return failure(code)
    if not is_in_scope(seat, window):
        raise AssertionError("an accepted window left the evaluated seat out of scope")

    supplied = record_digest(record)
    bound = state.bound_uptime_records.get(window)
    if bound is not None and bound != supplied:
        return failure("INCONSISTENT_UPTIME_RECORD")

    met = met_cycle(uptime_of(record, seat_id))
    carry_before = state.performance_carry_atomic
    if met:
        founder_legs: tuple[Leg, ...] = (
            Leg(
                channel=c.FOUNDER_CHANNEL,
                custody_key=founder_custody_key(seat_id),
                amount_atomic=c.FOUNDER_OPERATOR_LEG,
            ),
        )
        carry_after = carry_before
    else:
        code, founder_legs, carry_after = reallocate(carry_before, winner_seats(record))
        if code is not None:
            return failure(code)

    legs = fixed_base_legs() + founder_legs
    reservation = check_reservable(state, legs)
    if reservation is not None:
        return failure(reservation)

    journal = reserve(state, legs)
    state.performance_carry_atomic = carry_after
    journal.extend(carry_entries(carry_before, carry_after))

    key = permission_key(seat_id, cycle_index)
    state.pending_permissions[key] = PendingPermission(
        seat_id=seat_id,
        cycle_index=cycle_index,
        cycle_window=window,
        met_cycle=met,
        total_atomic=required_sum([leg.amount_atomic for leg in legs], key),
        legs=legs,
    )
    state.evaluated_permission_keys.add(key)
    state.bound_uptime_records[window] = supplied
    return accepted(journal)


def _seat_in_range(seat_id: int) -> bool:
    return 0 <= seat_id < c.FOUNDER_SEAT_CAPACITY
