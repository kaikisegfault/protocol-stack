"""Seat activation and base permission evaluation."""

from __future__ import annotations

from typing import Any

from . import contract as c
from .domain import (
    Leg,
    PendingPermission,
    State,
    founder_custody_key,
    permission_key,
)
from ..common.canonical import required_sum
from .operations import Outcome, accepted, carry_entries, check_reservable, failure, reserve
from .uptime import (
    fixed_base_legs,
    met_cycle,
    record_digest,
    reallocate,
    uptime_of,
    validate_record,
    winner_seats,
)


def activate_seat(state: State, event: dict[str, Any]) -> Outcome:
    seat_id = event["seat_id"]
    referrer = event["referrer_seat_id"]
    if not _seat_in_range(seat_id):
        return failure("CYCLE_RANGE")
    if referrer is not None and (not _seat_in_range(referrer) or referrer == seat_id):
        return failure("INVALID_REFERRER")
    if seat_id in state.seats:
        return failure("REPLAY")
    # A referrer must itself be an activated seat, because the referral credits
    # `founder_seat:{referrer}` custody and a non-seat referrer has no bucket.
    # Whether a referrer must hold a seat is open specification work; this is a
    # modelling choice recorded in ADR 0025, not a settled rule.
    if referrer is not None and referrer not in state.seats:
        return failure("SEAT_NOT_ACTIVATED")
    state.seats[seat_id] = referrer
    return accepted()


def evaluate_base_permission(state: State, event: dict[str, Any]) -> Outcome:
    seat_id = event["seat_id"]
    cycle_index = event["cycle_index"]
    if not _seat_in_range(seat_id) or not 0 <= cycle_index < c.ISSUANCE_CYCLES_PER_SEAT:
        return failure("CYCLE_RANGE")
    if seat_id not in state.seats:
        return failure("SEAT_NOT_ACTIVATED")
    if permission_key(seat_id, cycle_index) in state.evaluated_permission_keys:
        return failure("REPLAY")

    record = event["cycle_uptime_record"]
    if record is None:
        return failure("MISSING_UPTIME_RECORD")
    if not validate_record(state, record, seat_id):
        return failure("INVALID_UPTIME_RECORD")

    window = record["cycle_window"]
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
