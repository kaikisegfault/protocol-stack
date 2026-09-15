"""The recorded version-nine contract scenario.

**It binds `simulation.unreferred_pool`'s fixture rather than inventing a
second one.** The settlement arithmetic version nine encodes is that
specification's, so driving it from a different window sequence would produce two
fixtures that could disagree about what the rule does. The genesis timestamp, the
block rate, the window sequence, the seat activations and the accruals all come
from there; what this module adds is everything version nine has that the payout
model does not — a genesis object, a head that advances in time, and the
proposals that exercise `calendar-v1`'s five rules.

**The genesis sits six hours off a day boundary**, which is the pool fixture's
choice and the reason the straddling case is reachable at all: at the commit
target a window is exactly one day, so a genesis at midnight would make every
window exactly one calendar day and no window would ever cross a month boundary.
"""

from __future__ import annotations

from simulation.unreferred_pool import scenario as pool_scenario

from . import contract as c
from .genesis import Genesis
from .timeline import Head

__all__ = [
    "ACTIVATIONS",
    "DISPUTE_AUTHORITY_KEY",
    "FIXED_TRANSFER_FEE",
    "GENESIS_MILLIS",
    "MANIFEST_DIGEST",
    "NETWORK_ID",
    "SUPPLY_LIMIT",
    "VERIFIER_KEY",
    "genesis",
    "genesis_head",
    "proposals",
    "timestamp_of_height",
    "window_months",
]

NETWORK_ID = 9
SUPPLY_LIMIT = 5_699_395_010_000_000_000
FIXED_TRANSFER_FEE = 1_000

VERIFIER_KEY = bytes([0xA1]) * 32
DISPUTE_AUTHORITY_KEY = bytes([0xD8]) * 32
MANIFEST_DIGEST = bytes.fromhex(c.MANIFEST_DIGEST_HEX)

# Bound, not restated. A second genesis timestamp here would be a second opinion
# about which month a window belongs to.
GENESIS_MILLIS = pool_scenario.GENESIS_MILLIS
ACTIVATIONS = dict(pool_scenario.ACTIVATIONS)
timestamp_of_height = pool_scenario.timestamp_of_height


def genesis() -> Genesis:
    return Genesis(
        network_id=NETWORK_ID,
        genesis_timestamp=GENESIS_MILLIS,
        supply_limit=SUPPLY_LIMIT,
        fixed_transfer_fee=FIXED_TRANSFER_FEE,
        manifest_digest=MANIFEST_DIGEST,
        verifier_key=VERIFIER_KEY,
        dispute_authority_key=DISPUTE_AUTHORITY_KEY,
    )


def genesis_head() -> Head:
    """Height zero and the genesis timestamp.

    A chain starts at height one, so height zero is never a block. Holding it as
    the head is what makes C2's genesis case the same comparison as every other
    height's rather than a rule of its own.
    """
    return Head(height=0, timestamp=GENESIS_MILLIS)


def window_months() -> dict[int, int]:
    """Each recorded window's month, derived through `calendar-v1`."""
    return {window.index: window.month for window in pool_scenario.windows()}


# `(height, timestamp, observed_clock, label)`. The labels are what the vectors
# record, so a condition that stopped firing would lose its vector rather than
# quietly pass. A machine's own clock is written as the proposed timestamp plus
# an offset, because C5 is about the distance between the two and not about
# either value.
_MS = 1_000
_TOLERANCE = c.TIMESTAMP_TOLERANCE_MILLIS


def proposals() -> tuple[tuple[int, int, int, str], ...]:
    g = GENESIS_MILLIS
    at = timestamp_of_height
    return (
        (1, at(1), at(1), "accepts_the_first_block"),
        # Two consecutive blocks may carry the same millisecond: C2 is
        # non-decreasing, not strictly increasing, because a chain catching up
        # after a halt produces blocks faster than one a second.
        (2, at(1), at(1), "accepts_an_equal_timestamp"),
        (3, at(3), at(3), "accepts_a_later_timestamp"),
        (5, at(4), at(4), "refuses_a_height_that_is_not_next"),
        (4, c.MAX_TIMESTAMP_MILLIS + 1, at(4), "refuses_a_timestamp_above_the_range"),
        (4, at(3) - _MS, at(3), "refuses_a_timestamp_below_its_predecessor"),
        (4, g - _MS, g, "refuses_a_timestamp_below_genesis_after_a_reset"),
        (
            4,
            at(4) + _TOLERANCE + 1,
            at(4),
            "refuses_a_timestamp_ahead_of_the_tolerance",
        ),
        (
            4,
            at(4),
            at(4) + _TOLERANCE + 1,
            "refuses_a_timestamp_behind_the_tolerance",
        ),
        (4, at(4) + _TOLERANCE, at(4), "accepts_at_the_ahead_boundary"),
        # Exactly one tolerance behind the observing machine's clock, and equal
        # to its predecessor rather than below it: the two rules are separate,
        # and a case that failed C2 would test nothing about C5.
        (
            5,
            at(4) + _TOLERANCE,
            at(4) + 2 * _TOLERANCE,
            "accepts_at_the_behind_boundary",
        ),
    )
