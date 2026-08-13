"""The performance reallocation commitment.

A failed cycle's Founder portion goes to the highest uptime in the same window,
so the winner set is a property of the window and every seat failing in that
window reallocates to the same set. The set is committed once, at the window's
finalisation, and carried by each exercise that spends against it.

The commitment is an ordered Merkle root rather than a flat hash so that a later
version can add a per-winner claim path with a logarithmic membership proof
without changing the committed value.
"""

from __future__ import annotations

from . import contract as c
from .envelope import u32
from .merkle import root


class InvalidWinnerSet(ValueError):
    """A winner list that does not reproduce the recorded commitment."""


def derive_winner_set(uptime_by_seat: dict[int, int], met_by_seat: dict[int, bool]) -> tuple[int, ...]:
    """The seats that met the cycle and hold the maximum uptime among them.

    This is `founder-economy-simulator-v3`'s winner rule, applied to a window's
    finalised record. A failed seat never rewards another failed seat, so the
    candidate set is restricted before the maximum is taken; taking the maximum
    first and filtering afterwards would return an empty set whenever the best
    uptime in a window belonged to a seat that failed it.
    """
    candidates = {seat: uptime for seat, uptime in uptime_by_seat.items() if met_by_seat.get(seat, False)}
    if not candidates:
        return ()
    best = max(candidates.values())
    return tuple(sorted(seat for seat, uptime in candidates.items() if uptime == best))


def winner_root(winners: tuple[int, ...]) -> bytes:
    require_canonical(winners)
    return root([u32(seat) for seat in winners], c.WINNER_TREE_PREFIX)


def require_canonical(winners: tuple[int, ...]) -> None:
    if len(winners) > c.FOUNDER_SEAT_CAPACITY:
        raise InvalidWinnerSet("winner count above the seat capacity")
    for index, seat in enumerate(winners):
        if not 0 <= seat <= c.MAX_SEAT_ID:
            raise InvalidWinnerSet(f"winner seat {seat} outside the seat range")
        if index and seat <= winners[index - 1]:
            raise InvalidWinnerSet("winner list is not strictly increasing")


def matches_commitment(
    supplied: tuple[int, ...], recorded_root: bytes, recorded_count: int
) -> bool:
    """Both the count and the root must reproduce.

    Checking the root alone would be sufficient in a collision-free model and is
    deliberately not relied on: the count is recorded state, comparing it is one
    integer comparison, and a mismatch is then reported before any tree is built
    over an attacker-chosen list.
    """
    if len(supplied) != recorded_count:
        return False
    try:
        return winner_root(supplied) == recorded_root
    except InvalidWinnerSet:
        return False


def equal_split(portion_atomic: int, winner_count: int) -> tuple[int, int]:
    """The per-winner share and the integer remainder carried forward.

    An empty winner set carries the whole portion, which is the founder-directed
    rule for a window in which no node met the cycle.
    """
    if winner_count == 0:
        return 0, portion_atomic
    share = portion_atomic // winner_count
    return share, portion_atomic - share * winner_count
