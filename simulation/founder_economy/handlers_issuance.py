"""Permission exercise and capped direct-channel issuance."""

from __future__ import annotations

from typing import Any

from . import contract as c
from ..common.canonical import checked_add, checked_sum
from .domain import State, direct_custody_key, permission_key
from .operations import (
    Outcome,
    accepted,
    check_issuable,
    failure,
    issue,
    issue_direct,
)
from .research import bound_to_direct


def exercise_permission(state: State, event: dict[str, Any]) -> Outcome:
    seat_id = event["seat_id"]
    cycle_index = event["cycle_index"]
    if not 0 <= seat_id < c.FOUNDER_SEAT_CAPACITY:
        return failure("CYCLE_RANGE")
    if not 0 <= cycle_index < c.ISSUANCE_CYCLES_PER_SEAT:
        return failure("CYCLE_RANGE")

    key = permission_key(seat_id, cycle_index, event["permission_kind"])
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
    channel_id = event["channel"]
    if channel_id not in c.DIRECT_CHANNEL_IDS:
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
    channel = state.channels[channel_id]
    reserved = checked_add(channel.issued_atomic, channel.outstanding_atomic)
    if reserved is None or checked_add(reserved, amount) is None:
        return failure("ARITHMETIC_OVERFLOW")
    if reserved + amount > c.CHANNEL_CAPS[channel_id]:
        return failure("CHANNEL_CAP")
    if checked_add(state.typed_custody.get(custody_key, 0), amount) is None:
        return failure("ARITHMETIC_OVERFLOW")

    journal = issue_direct(state, channel_id, custody_key, amount)
    state.accepted_direct_decision_ids.add(event["decision_id"])
    return accepted(journal)


HANDLERS = {
    "exercise_permission": exercise_permission,
    "direct_issue": direct_issue,
}
