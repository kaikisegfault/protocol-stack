"""The cycle uptime record and the rules derived from it.

The record carries measurements only. It cannot express a verdict, an
eligibility flag, a winner, a ranking, or an amount, so the activity predicate
and the winner set are computed here rather than supplied. That is the whole
difference between this input and the research placeholder it replaces: a
placeholder stands in for an undecided founder policy, while these rules are
decided in the Founder Constitution and ADR 0023 and are implemented as stated.

Nothing here proves that a supplied measurement reflects a real machine. The
challenge construction, sampling rate, and dispute window remain unspecified.
"""

from __future__ import annotations

from typing import Any

from . import contract as c
from ..common.canonical import InvariantError, checked_add, digest
from .domain import Leg, State, founder_custody_key

RECORD_LABEL = "protocol-stack:founder-economy:uptime-record-v2"


def record_value(record: dict[str, Any]) -> dict[str, Any]:
    """Return the canonical record value, ordered by seat.

    Sorting means the binding is over a window's measurements rather than over
    the order one event happened to present them in. Duplicate seats are
    rejected before this runs, so the order is total.
    """
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

    The seat bound and the activation requirement apply to every listed seat,
    because any of them may become a reallocation recipient.
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


def uptime_of(record: dict[str, Any], seat_id: int) -> int:
    for entry in record["entries"]:
        if entry["seat_id"] == seat_id:
            return entry["uptime_seconds"]
    raise InvariantError("a validated record is missing the evaluated seat")


def met_cycle(uptime_seconds: int) -> bool:
    """Derive whether a cycle was met, checking both stated forms agree.

    The Founder Constitution states the rule as a floor on uptime and as a
    ceiling on downtime without deriving either from the other. They agree
    exactly because the threshold and the allowance sum to the cycle target, so
    computing both and requiring agreement checks that claim on every call.
    """
    by_uptime = uptime_seconds >= c.ACTIVITY_THRESHOLD_SECONDS
    by_downtime = (c.CYCLE_TARGET_SECONDS - uptime_seconds) <= c.GRACE_ALLOWANCE_SECONDS
    if by_uptime is not by_downtime:
        raise InvariantError("the uptime and downtime forms of the cycle rule disagree")
    return by_uptime


def winner_seats(record: dict[str, Any]) -> tuple[int, ...]:
    """Return the seats at the highest uptime among those that met the cycle.

    Restricting to seats that met the cycle implements the founder-directed
    rule that a failed seat never rewards another failed seat, and it excludes
    the evaluated seat without a separate test.
    """
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
    """Split the Founder portion plus the carry equally among the winners.

    Returns a failure code, the resulting legs, and the new carry. An empty
    winner set reallocates nothing and carries the whole pot forward, and the
    integer remainder of an equal split carries forward rather than being
    burned. Both rules are founder-directed.
    """
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
