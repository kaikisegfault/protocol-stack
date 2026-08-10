"""Referral accrual, permission exercise, and capped direct-channel issuance."""

from __future__ import annotations

from typing import Any

from . import contract as c
from ..common.canonical import checked_sum
from .domain import (
    State,
    direct_custody_key,
    founder_custody_key,
    permission_key,
    singleton_custody_key,
)
from .operations import (
    Outcome,
    accepted,
    check_direct_issuable,
    check_issuable,
    failure,
    issue,
    issue_direct,
)
from .research import bound_to_direct


def accrue_referral(state: State, event: dict[str, Any]) -> Outcome:
    """Credit one unconditional direct-mint referral accrual.

    The accrual takes no activity and no eligibility input. It is unconditional
    by founder direction, because a referrer cannot operate, repair, or
    influence someone else's machine. Its eligibility is the recorded referrer
    relationship the state already holds.
    """
    seat_id = event["seat_id"]
    cycle_index = event["cycle_index"]
    if not 0 <= seat_id < c.FOUNDER_SEAT_CAPACITY:
        return failure("CYCLE_RANGE")
    if not 0 <= cycle_index < c.ISSUANCE_CYCLES_PER_SEAT:
        return failure("CYCLE_RANGE")
    if seat_id not in state.seats:
        return failure("SEAT_NOT_ACTIVATED")

    key = permission_key(seat_id, cycle_index)
    if key in state.referral_accrual_keys:
        return failure("REPLAY")

    referrer = state.seats[seat_id].referrer_seat_id
    custody_key = (
        singleton_custody_key(c.UNREFERRED_POOL_KIND)
        if referrer is None
        else founder_custody_key(referrer)
    )

    code = check_direct_issuable(
        state, c.REFERRAL_CHANNEL, custody_key, c.REFERRAL_AMOUNT
    )
    if code is not None:
        return failure(code)

    journal = issue_direct(state, c.REFERRAL_CHANNEL, custody_key, c.REFERRAL_AMOUNT)
    state.referral_accrual_keys.add(key)
    return accepted(journal)


def exercise_permission(state: State, event: dict[str, Any]) -> Outcome:
    seat_id = event["seat_id"]
    cycle_index = event["cycle_index"]
    if not 0 <= seat_id < c.FOUNDER_SEAT_CAPACITY:
        return failure("CYCLE_RANGE")
    if not 0 <= cycle_index < c.ISSUANCE_CYCLES_PER_SEAT:
        return failure("CYCLE_RANGE")

    key = permission_key(seat_id, cycle_index)
    permission = state.pending_permissions.get(key)
    if permission is None:
        return failure("PERMISSION_NOT_FOUND")

    total = checked_sum([leg.amount_atomic for leg in permission.legs])
    if total is None or total != permission.total_atomic:
        return failure("INVARIANT")

    code = check_issuable(state, permission.legs)
    if code is not None:
        return failure(code)

    journal = issue(state, permission.legs)
    del state.pending_permissions[key]
    return accepted(journal)


def direct_issue(state: State, event: dict[str, Any]) -> Outcome:
    """Issue against one placeholder direct-mint channel.

    `founder_referral` is a direct-mint channel but is not reachable here. It
    is consumed exactly by the per-seat-cycle accrual above, and admitting it
    would let a supplied eligibility fixture mint referral units outside that
    accounting.
    """
    channel_id = event["channel"]
    if channel_id not in c.PLACEHOLDER_DIRECT_CHANNELS:
        return failure("INVALID_CHANNEL")

    amount = int(event["amount_atomic"])
    if amount == 0:
        return failure("ZERO_AMOUNT")
    if event["decision_id"] in state.accepted_direct_decision_ids:
        return failure("REPLAY")

    eligibility = event["eligibility_result"]
    if eligibility is None:
        return failure("MISSING_RESEARCH_INPUT")
    if not bound_to_direct(eligibility, event):
        return failure("INVALID_RESEARCH_INPUT")
    if not eligibility["eligible"]:
        return failure("NOT_ELIGIBLE")

    custody_key = direct_custody_key(event["beneficiary_id"])
    code = check_direct_issuable(state, channel_id, custody_key, amount)
    if code is not None:
        return failure(code)

    journal = issue_direct(state, channel_id, custody_key, amount)
    state.accepted_direct_decision_ids.add(event["decision_id"])
    return accepted(journal)
