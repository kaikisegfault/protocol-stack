"""Seat activation and base and referral permission evaluation."""

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
from .operations import Outcome, accepted, check_reservable, failure, reserve
from .research import (
    FOUNDER_CHANNEL,
    bound_to_cycle,
    fixed_base_legs,
    resolve_performance_allocation,
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
    if referrer is not None and referrer not in state.seats:
        return failure("SEAT_NOT_ACTIVATED")
    state.seats[seat_id] = referrer
    return accepted()


def evaluate_base_permission(state: State, event: dict[str, Any]) -> Outcome:
    seat_id = event["seat_id"]
    cycle_index = event["cycle_index"]
    guard = _guard_evaluation(state, seat_id, cycle_index, "base")
    if guard is not None:
        return guard

    activity = event["activity_result"]
    if activity is None:
        return failure("MISSING_RESEARCH_INPUT")
    if not bound_to_cycle(activity, seat_id, cycle_index):
        return failure("INVALID_RESEARCH_INPUT")

    allocation = event["performance_allocation"]
    if activity["active"]:
        if allocation is not None:
            return failure("INVALID_RESEARCH_INPUT")
        founder_legs: tuple[Leg, ...] = (
            Leg(
                channel=FOUNDER_CHANNEL,
                custody_key=founder_custody_key(seat_id),
                amount_atomic=c.FOUNDER_OPERATOR_LEG,
            ),
        )
    else:
        if allocation is None:
            return failure("MISSING_RESEARCH_INPUT")
        if not bound_to_cycle(allocation, seat_id, cycle_index):
            return failure("INVALID_RESEARCH_INPUT")
        code, founder_legs = resolve_performance_allocation(state, seat_id, allocation)
        if code is not None:
            return failure(code)

    legs = fixed_base_legs() + founder_legs
    return _create(state, seat_id, cycle_index, "base", c.BASE_PERMISSION_TOTAL, legs)


def evaluate_referral_permission(state: State, event: dict[str, Any]) -> Outcome:
    seat_id = event["seat_id"]
    cycle_index = event["cycle_index"]
    guard = _guard_evaluation(state, seat_id, cycle_index, "referral")
    if guard is not None:
        return guard

    referrer = state.seats[seat_id]
    if referrer is None:
        return failure("SEAT_NOT_REFERRED")

    activity = event["activity_result"]
    if activity is None:
        return failure("MISSING_RESEARCH_INPUT")
    if not bound_to_cycle(activity, seat_id, cycle_index):
        return failure("INVALID_RESEARCH_INPUT")

    referral_result = event["inactive_referral_result"]
    if activity["active"]:
        if referral_result is not None:
            return failure("INVALID_RESEARCH_INPUT")
    else:
        if referral_result is None:
            return failure("MISSING_RESEARCH_INPUT")
        if not bound_to_cycle(referral_result, seat_id, cycle_index):
            return failure("INVALID_RESEARCH_INPUT")
        if not referral_result["create"]:
            return _record_without_reserving(state, seat_id, cycle_index)

    legs = (
        Leg(
            channel=c.REFERRAL_CHANNEL,
            custody_key=founder_custody_key(referrer),
            amount_atomic=c.REFERRAL_AMOUNT,
        ),
    )
    return _create(state, seat_id, cycle_index, "referral", c.REFERRAL_AMOUNT, legs)


def _seat_in_range(seat_id: int) -> bool:
    return 0 <= seat_id < c.FOUNDER_SEAT_CAPACITY


def _guard_evaluation(
    state: State,
    seat_id: int,
    cycle_index: int,
    kind: str,
) -> Outcome | None:
    if not _seat_in_range(seat_id) or not 0 <= cycle_index < c.ISSUANCE_CYCLES_PER_SEAT:
        return failure("CYCLE_RANGE")
    if seat_id not in state.seats:
        return failure("SEAT_NOT_ACTIVATED")
    if permission_key(seat_id, cycle_index, kind) in state.evaluated_permission_keys:
        return failure("REPLAY")
    return None


def _create(
    state: State,
    seat_id: int,
    cycle_index: int,
    kind: str,
    total_atomic: int,
    legs: tuple[Leg, ...],
) -> Outcome:
    code = check_reservable(state, legs)
    if code is not None:
        return failure(code)
    journal = reserve(state, legs)
    key = permission_key(seat_id, cycle_index, kind)
    state.pending_permissions[key] = PendingPermission(
        seat_id=seat_id,
        cycle_index=cycle_index,
        kind=kind,
        total_atomic=total_atomic,
        legs=legs,
    )
    state.evaluated_permission_keys.add(key)
    return accepted(journal)


def _record_without_reserving(state: State, seat_id: int, cycle_index: int) -> Outcome:
    """A false inactive-referral result consumes the key but reserves no value."""
    state.evaluated_permission_keys.add(permission_key(seat_id, cycle_index, "referral"))
    return accepted()
