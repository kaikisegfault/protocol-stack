"""The recorded cycle schedules both derivations run.

A schedule is fixture data — which seats are in scope, what each reported, and
whether it is inside its own 731 cycles — so it is stated once here and handed to
the closed-form derivation and to the model separately. Neither derives it.

**The main schedule is chosen to reach every branch of the settlement**: a cycle
nobody wins, a cycle a machine past its own distribution wins outright, a cycle
whose split leaves dust on all five legs, a cycle whose absorbed pool is smaller
than its winner count and is therefore returned whole, a cycle a single winner
drains, a cycle with no contributing seat at all, and a residual that survives to
the cycle after.

**The cap schedule** runs thirty-one windows so that one seat crosses the
accumulation cap in both directions: under it for thirty windows, over it at the
thirty-first, and under it again once its mint advances the mark.
"""

from __future__ import annotations

MET = 72_000
BEST = 79_200
FAILED = 3_600

IN_SPAN = tuple(range(7))
PAST_SPAN = (8, 9, 10)


def _seats(entries: list[tuple[int, int, bool]]) -> list[dict]:
    return [
        {"seat_id": seat_id, "uptime": uptime, "in_span": in_span}
        for seat_id, uptime, in_span in entries
    ]


# window -> (name, seats)
MAIN: dict[int, tuple[str, list[dict]]] = {
    2: (
        "nobody_met_the_cycle",
        _seats([(s, FAILED, True) for s in IN_SPAN] + [(9, FAILED, False)]),
    ),
    3: (
        "a_machine_past_its_span_wins_outright",
        _seats([(s, MET, True) for s in IN_SPAN] + [(9, BEST, False)]),
    ),
    4: (
        "a_seven_way_tie_leaves_dust_on_every_leg",
        _seats(
            [(s, MET, True) for s in IN_SPAN[:6]]
            + [(6, FAILED, True), (9, MET, False)]
        ),
    ),
    5: (
        "an_absorbed_pool_below_the_winner_count_is_returned_whole",
        _seats(
            [(s, MET, True) for s in IN_SPAN[:6]]
            + [(6, FAILED, True), (9, MET, False)]
        ),
    ),
    6: (
        "one_winner_drains_the_pool",
        _seats(
            [(0, BEST, True)]
            + [(s, MET, True) for s in IN_SPAN[1:6]]
            + [(6, FAILED, True), (9, MET, False)]
        ),
    ),
    7: (
        "nobody_met_the_cycle_again",
        _seats([(s, FAILED, True) for s in IN_SPAN] + [(9, FAILED, False)]),
    ),
    8: (
        "no_contributing_seat_and_the_pool_still_moves",
        _seats([(s, MET, False) for s in PAST_SPAN]),
    ),
    9: (
        "a_residual_survives_to_the_next_cycle",
        _seats([(s, MET, True) for s in IN_SPAN] + [(9, MET, False)]),
    ),
}

MAIN_LAST_ASSIGNED = 9

# The mints taken after the main schedule, in this order.
MAIN_MINTS: tuple[int, ...] = (9, 0, 6)

CAP_WINDOWS: tuple[int, ...] = tuple(range(1, 32))
CAP_MINT_WINDOW = 20
CAP_LAST_ASSIGNED = 31


def cap_seats() -> list[dict]:
    """Two in-span seats, both fully operational in every window."""
    return _seats([(0, MET, True), (1, MET, True)])
