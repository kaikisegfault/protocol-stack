"""The recorded calendar-v1 scenario.

The chain is short and every one of its timestamps sits where an error is
visible rather than where a value is round: the last millisecond of a month,
the first millisecond of the next, a repeated timestamp, and a halt long enough
to leave two whole months without a single height.

The clock readings are part of the fixture. Two of the accepted blocks are
observed at exactly the tolerance, one on each side, so the accepted chain
itself proves the boundary is inclusive; the refusals one millisecond further
out are in `rejections`.
"""

from __future__ import annotations

from simulation.calendar import contract as c
from simulation.calendar.chain import Calendar
from simulation.calendar.civil import days_from_civil
from simulation.common.canonical import CodedError

# (year, month, day, hour, minute, second, millisecond)
CivilInstant = tuple[int, int, int, int, int, int, int]


def millis_of(instant: CivilInstant) -> int:
    """The timestamp of a civil instant, by the model's own derivation."""
    year, month, day, hour, minute, second, milli = instant
    days = days_from_civil(year, month, day)
    seconds = (hour * 60 + minute) * 60 + second
    return (days * c.SECONDS_PER_DAY + seconds) * c.MILLIS_PER_SECOND + milli


# Genesis falls one minute before a month boundary, so the chain's first block
# lands in the same month as genesis and closes nothing.
GENESIS_INSTANT: CivilInstant = (2026, 1, 31, 23, 59, 0, 0)

# label, instant, clock offset observed by the validating machine
CHAIN: tuple[tuple[str, CivilInstant, int], ...] = (
    ("first_block", (2026, 1, 31, 23, 59, 30, 0), 0),
    # Observed a full tolerance *after* the stamp: the behind edge, inclusive.
    ("repeated_timestamp", (2026, 1, 31, 23, 59, 30, 0), c.TIMESTAMP_TOLERANCE_MILLIS),
    # Observed a full tolerance *before* the stamp: the ahead edge, inclusive.
    ("january_last_milli", (2026, 1, 31, 23, 59, 59, 999), -c.TIMESTAMP_TOLERANCE_MILLIS),
    ("february_first_milli", (2026, 2, 1, 0, 0, 0, 0), 0),
    ("february_last_milli", (2026, 2, 28, 23, 59, 59, 999), 0),
    # A halt across March and April: this block opens May and closes three
    # months at once, two of which hold no height at all.
    ("after_a_two_month_halt", (2026, 5, 1, 0, 0, 0, 0), 0),
    ("one_milli_later", (2026, 5, 1, 0, 0, 0, 1), 0),
)

# Dates whose month index an off-by-one anywhere in the derivation would change.
DERIVATION_PROBES: tuple[tuple[str, CivilInstant], ...] = (
    ("epoch", (1970, 1, 1, 0, 0, 0, 0)),
    ("epoch_month_last_milli", (1970, 1, 31, 23, 59, 59, 999)),
    ("second_month_first_milli", (1970, 2, 1, 0, 0, 0, 0)),
    ("common_year_february_last", (2026, 2, 28, 23, 59, 59, 999)),
    ("common_year_march_first", (2026, 3, 1, 0, 0, 0, 0)),
    # Divisible by four: a leap year, and the abbreviated rule agrees.
    ("leap_year_february_29", (2024, 2, 29, 12, 0, 0, 0)),
    # Divisible by 400: a leap year, and the abbreviated rule disagrees.
    ("century_leap_february_29", (2000, 2, 29, 0, 0, 0, 0)),
    # Divisible by 100 but not 400: not a leap year, and the abbreviated rule
    # disagrees the other way.
    ("century_common_february_28", (2100, 2, 28, 23, 59, 59, 999)),
    ("century_common_march_first", (2100, 3, 1, 0, 0, 0, 0)),
    ("year_end", (2026, 12, 31, 23, 59, 59, 999)),
    ("year_start", (2027, 1, 1, 0, 0, 0, 0)),
    ("range_end", (9999, 12, 31, 23, 59, 59, 999)),
)

# Every rejection reachable from the built chain, one per condition plus the
# three probes that make the stated order normative rather than decorative.
# label, height offset from the chain's next height, timestamp, clock
Rejection = tuple[str, int, int, int]


def rejections(chain: Calendar) -> tuple[Rejection, ...]:
    head = chain.head_timestamp
    tolerance = c.TIMESTAMP_TOLERANCE_MILLIS
    return (
        ("height_far_ahead", 92, head, head),
        ("height_already_accepted", -1, head, head),
        ("timestamp_above_range", 0, c.MAX_TIMESTAMP_MILLIS + 1, head),
        # Unreachable on a u64 field and refused anyway, so the guard is a rule
        # rather than a comment about the encoding.
        ("timestamp_below_range", 0, c.MIN_TIMESTAMP_MILLIS - 1, head),
        ("timestamp_not_monotonic", 0, head - 1, head - 1),
        ("timestamp_one_milli_too_far_ahead", 0, head + tolerance + 1, head),
        ("timestamp_one_milli_too_far_behind", 0, head, head + tolerance + 1),
        # Order: a wrong height is refused before the timestamp is looked at.
        ("order_height_before_range", 92, c.MAX_TIMESTAMP_MILLIS + 1, head),
        # Order: an unrepresentable timestamp is refused before monotonicity,
        # which this value also violates.
        ("order_range_before_monotonic", 0, c.MIN_TIMESTAMP_MILLIS - 1, head),
        # Order: monotonicity is refused before the tolerance, which this pair
        # also violates on the behind side.
        ("order_monotonic_before_tolerance", 0, head - 1, head + tolerance),
    )


def build() -> Calendar:
    """The recorded chain, accepted block by block through the admission path."""
    chain = Calendar(millis_of(GENESIS_INSTANT))
    for _label, instant, clock_offset in CHAIN:
        timestamp = millis_of(instant)
        chain.accept(chain.next_height, timestamp, timestamp + clock_offset)
    return chain


def replay(chain: Calendar) -> Calendar:
    """The same chain re-applied with no clock available at all."""
    replayed = Calendar(chain.genesis_timestamp)
    for block in chain.blocks:
        replayed.replay(block.height, block.timestamp)
    return replayed


def rejection_codes(chain: Calendar) -> dict[str, str]:
    """The code each refusal produces, run against the chain itself.

    Deliberately not against a copy. The verifier measures that a run of
    refusals leaves the chain's digest unchanged, and that claim is only
    meaningful on the instance the refusals were offered to: comparing two
    separately built chains would show that the model is deterministic, which
    is a different thing.
    """
    codes: dict[str, str] = {}
    for label, height_offset, timestamp, clock in rejections(chain):
        try:
            chain.accept(chain.next_height + height_offset, timestamp, clock)
        except CodedError as error:
            codes[label] = error.code
        else:  # pragma: no cover - a refusal that is accepted is a defect
            codes[label] = "ACCEPTED"
    return codes


def genesis_boundary_codes() -> dict[str, str]:
    """The two cases only a chain with no blocks yet can reach."""
    genesis = millis_of(GENESIS_INSTANT)
    codes: dict[str, str] = {}

    equal = Calendar(genesis)
    try:
        equal.accept(c.FIRST_BLOCK_HEIGHT, genesis, genesis)
    except CodedError as error:
        codes["first_block_equal_to_genesis"] = error.code
    else:
        codes["first_block_equal_to_genesis"] = "ACCEPTED"

    below = Calendar(genesis)
    try:
        below.accept(c.FIRST_BLOCK_HEIGHT, genesis - 1, genesis - 1)
    except CodedError as error:
        codes["first_block_below_genesis"] = error.code
    else:  # pragma: no cover - a refusal that is accepted is a defect
        codes["first_block_below_genesis"] = "ACCEPTED"

    return codes


# Ten days, which is four orders of magnitude outside any plausible tolerance.
REPLAY_PROBE_OFFSET_MILLIS = 10 * c.SECONDS_PER_DAY * c.MILLIS_PER_SECOND


def replay_ignores_the_tolerance(chain: Calendar) -> tuple[str, str]:
    """Offer one stamp far outside any tolerance to both paths.

    Returns the replay path's answer and the admission path's, in that order.
    This is the difference between C1-C3 and C5 made falsifiable: a replaying
    machine has no clock to judge the stamp against and must accept what the
    tolerance once admitted, while a machine admitting the same stamp live
    refuses it.
    """
    far_ahead = chain.head_timestamp + REPLAY_PROBE_OFFSET_MILLIS

    replayed = replay(chain)
    try:
        replayed.replay(replayed.next_height, far_ahead)
    except CodedError as error:  # pragma: no cover - a replay reads no clock
        replay_code = error.code
    else:
        replay_code = "ACCEPTED"

    live = replay(chain)
    try:
        live.accept(live.next_height, far_ahead, chain.head_timestamp)
    except CodedError as error:
        admission_code = error.code
    else:  # pragma: no cover - a stamp ten days out is not within tolerance
        admission_code = "ACCEPTED"

    return (replay_code, admission_code)
