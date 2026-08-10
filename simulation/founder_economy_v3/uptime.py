"""The cycle uptime record and the rules derived from it.

The record's shape is version two's, unchanged: `cycle_window` is a count and
`uptime_seconds` is whole seconds bounded by the cycle target, which is what
lets `uptime-measurement-v1` feed this version without a version of its own.
The activity predicate, the winner set, the tie rule, and the remainder rule are
also version two's and are unchanged.

What version three adds is completeness. A record must cover exactly the
in-scope seat set of its window, so a reallocation ranks the population the
schedule says was running rather than whichever subset the record listed.

Nothing here proves that a supplied measurement reflects a real machine.
"""

from __future__ import annotations

from typing import Any

from . import contract as c
from ..common.canonical import InvariantError, checked_add, digest
from .domain import Leg, State, founder_custody_key
from .schedule import in_scope_seats, is_in_scope

RECORD_LABEL = "protocol-stack:founder-economy:uptime-record-v3"


def record_value(record: dict[str, Any]) -> dict[str, Any]:
    """Return the canonical record value, ordered by seat."""
    return {
        "cycle_window": record["cycle_window"],
        "entries": [
            {"seat_id": entry["seat_id"], "uptime_seconds": entry["uptime_seconds"]}
            for entry in sorted(record["entries"], key=lambda item: item["seat_id"])
        ],
    }


def record_digest(record: dict[str, Any]) -> str:
    return digest(RECORD_LABEL, record_value(record))


def validate_record(state: State, record: dict[str, Any], seat_id: int) -> bool:
    """Return whether the record is well formed for evaluating this seat.

    Unchanged from version two. The seat bound and the activation requirement
    apply to every listed seat, because any of them may become a reallocation
    recipient.
    """
    entries = record["entries"]
    if not entries:
        return False

    seen: set[int] = set()
    for entry in entries:
        listed = entry["seat_id"]
        if not 0 <= listed < c.FOUNDER_SEAT_CAPACITY:
            return False
        if listed in seen or listed not in state.seats:
            return False
        if entry["uptime_seconds"] > c.CYCLE_TARGET_SECONDS:
            return False
        seen.add(listed)
    return seat_id in seen


def check_completeness(state: State, record: dict[str, Any]) -> str | None:
    """Require the record's seat set to be exactly its window's in-scope set.

    Two codes rather than one, because the two defects have opposite effects. An
    omission shrinks the population a reallocation ranks over and can send a
    failed cycle's Founder portion to a seat that was not the best; an addition
    admits a seat with no evidence for the window and could make it the winner.

    Runs after `validate_record`, so every listed seat is activated and distinct
    and every lookup below is total.
    """
    window = record["cycle_window"]
    listed = {entry["seat_id"] for entry in record["entries"]}
    for seat_id in sorted(listed):
        if not is_in_scope(state.seats[seat_id], window):
            return "SEAT_NOT_IN_SCOPE"

    expected = in_scope_seats(state, window)
    if listed != set(expected):
        if not listed <= set(expected):
            raise InvariantError("an out-of-scope seat survived the scope check")
        return "INCOMPLETE_UPTIME_RECORD"
    return None


def uptime_of(record: dict[str, Any], seat_id: int) -> int:
    for entry in record["entries"]:
        if entry["seat_id"] == seat_id:
            return entry["uptime_seconds"]
    raise InvariantError("a validated record is missing the evaluated seat")


def met_cycle(uptime_seconds: int) -> bool:
    """Derive whether a cycle was met, checking both stated forms agree."""
    by_uptime = uptime_seconds >= c.ACTIVITY_THRESHOLD_SECONDS
    by_downtime = (c.CYCLE_TARGET_SECONDS - uptime_seconds) <= c.GRACE_ALLOWANCE_SECONDS
    if by_uptime is not by_downtime:
        raise InvariantError("the uptime and downtime forms of the cycle rule disagree")
    return by_uptime


def winner_seats(record: dict[str, Any]) -> tuple[int, ...]:
    """Return the seats at the highest uptime among those that met the cycle."""
    qualified = [
        entry for entry in record["entries"] if met_cycle(entry["uptime_seconds"])
    ]
    if not qualified:
        return ()
    maximum = max(entry["uptime_seconds"] for entry in qualified)
    return tuple(
        sorted(
            entry["seat_id"] for entry in qualified if entry["uptime_seconds"] == maximum
        )
    )


def reallocate(
    carry_atomic: int,
    winners: tuple[int, ...],
) -> tuple[str | None, tuple[Leg, ...], int]:
    """Split the Founder portion plus the carry equally among the winners."""
    pot = checked_add(c.FOUNDER_OPERATOR_LEG, carry_atomic)
    if pot is None:
        return "ARITHMETIC_OVERFLOW", (), carry_atomic
    if not winners:
        return None, (), pot

    share, remainder = divmod(pot, len(winners))
    if share == 0:
        raise InvariantError("an equal split produced a zero share")
    legs = tuple(
        Leg(
            channel=c.FOUNDER_CHANNEL,
            custody_key=founder_custody_key(seat_id),
            amount_atomic=share,
        )
        for seat_id in winners
    )
    return None, legs, remainder


def fixed_base_legs() -> tuple[Leg, ...]:
    """Return the four base legs whose beneficiaries never change."""
    return tuple(
        Leg(
            channel=channel,
            custody_key=f"{beneficiary_kind}:{c.SINGLETON_BENEFICIARY_ID}",
            amount_atomic=amount,
        )
        for channel, beneficiary_kind, amount in c.BASE_LEGS
        if beneficiary_kind in c.SINGLETON_BENEFICIARY_KINDS
    )
