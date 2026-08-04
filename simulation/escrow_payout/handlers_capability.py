"""Capability delegation, revocation, and the deterministic cycle counter.

None of these transitions moves value, so each emits an empty journal. A grant
is bounded authority rather than a reservation: an envelope above the escrow's
current custody is valid here and fails only when a payout is attempted.
"""

from __future__ import annotations

from typing import Any

from . import contract as c
from ..common.canonical import checked_add
from .domain import Capability, State
from .operations import CycleEffect, GrantEffect, Outcome, RevokeEffect, failure


def grant_capability(state: State, event: dict[str, Any]) -> Outcome:
    if not state.bound:
        return failure("NOT_BOUND")
    if event["capability_id"] in state.capabilities:
        return failure("REPLAY")
    if event["escrow_id"] not in c.ESCROW_CAPS:
        return failure("UNKNOWN_ESCROW")

    per_payout = int(event["per_payout_maximum"])
    envelope = int(event["envelope_total"])
    if per_payout == 0 or envelope == 0:
        return failure("ZERO_AMOUNT")
    if per_payout > envelope:
        return failure("INVALID_CAPABILITY")
    if event["expiry_cycle"] < state.current_cycle:
        return failure("CAPABILITY_EXPIRED")

    return Outcome(
        code="OK",
        effect=GrantEffect(
            capability_id=event["capability_id"],
            capability=Capability(
                escrow_id=event["escrow_id"],
                per_payout_maximum=per_payout,
                envelope_total=envelope,
                expiry_cycle=event["expiry_cycle"],
            ),
        ),
    )


def revoke_capability(state: State, event: dict[str, Any]) -> Outcome:
    capability = state.capabilities.get(event["capability_id"])
    if capability is None:
        return failure("UNKNOWN_CAPABILITY")
    if capability.revoked:
        return failure("ALREADY_REVOKED")

    return Outcome(
        code="OK",
        effect=RevokeEffect(capability_id=event["capability_id"]),
    )


def advance_cycle(state: State, event: dict[str, Any]) -> Outcome:
    """Advance the counter that makes capability expiry deterministic.

    This is not an accounting period. It distributes nothing and touches no
    custody; it exists so expiry never depends on a wall clock.
    """
    if event["cycle_index"] != state.current_cycle:
        return failure("CYCLE_MISMATCH")

    advanced = checked_add(state.current_cycle, 1)
    if advanced is None:
        return failure("ARITHMETIC_OVERFLOW")

    return Outcome(code="OK", effect=CycleEffect(current_cycle=advanced))
