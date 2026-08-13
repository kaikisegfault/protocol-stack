"""The per-cycle winner set and the equal split of a failed seat's permission.

A failed cycle's whole base permission moves to that cycle's best performers,
so the winner set is a property of the cycle and every seat failing in it
reallocates to the same set. The set is recorded once, as a bitmap inside the
cycle's assignment record, rather than committed and carried by a transaction:
under a mint that takes everything, a founder with many saved failed cycles
would otherwise carry one winner list per cycle in a single transaction.
"""

from __future__ import annotations

from . import contract as c


class InvalidWinnerSet(ValueError):
    """A winner set that no assignment could have produced."""


def derive_winner_set(
    uptime_by_seat: dict[int, int], met_by_seat: dict[int, bool]
) -> tuple[int, ...]:
    """The seats at the highest uptime among those that met the cycle.

    The candidate set is restricted before the maximum is taken. Taking the
    maximum first and filtering afterwards would return an empty set whenever
    the best uptime in a cycle belonged to a seat that failed it, and a failed
    seat never rewards another failed seat.
    """
    candidates = {
        seat: uptime
        for seat, uptime in uptime_by_seat.items()
        if met_by_seat.get(seat, False)
    }
    if not candidates:
        return ()
    best = max(candidates.values())
    return tuple(sorted(seat for seat, uptime in candidates.items() if uptime == best))


def split_permission(winner_count: int) -> tuple[dict[int, int], dict[int, int]]:
    """Divide every leg of one base permission among the winners.

    Returns the per-winner share and the carried remainder, both keyed by
    channel. Every leg is divided rather than only the operator leg, because the
    whole permission moves to the winners and the escrows and System Creator are
    paid at the winner's mint.
    """
    shares: dict[int, int] = {}
    carries: dict[int, int] = {}
    for channel, amount in c.BASE_PERMISSION_LEGS:
        if winner_count == 0:
            shares[channel] = 0
            carries[channel] = amount
            continue
        share = amount // winner_count
        shares[channel] = share
        carries[channel] = amount - share * winner_count
    return shares, carries


def require_canonical(winners: tuple[int, ...]) -> None:
    if len(winners) > c.FOUNDER_SEAT_CAPACITY:
        raise InvalidWinnerSet("winner count above the seat capacity")
    for index, seat in enumerate(winners):
        if not 0 <= seat <= c.MAX_SEAT_ID:
            raise InvalidWinnerSet(f"winner seat {seat} outside the seat range")
        if index and seat <= winners[index - 1]:
            raise InvalidWinnerSet("winner list is not strictly increasing")
