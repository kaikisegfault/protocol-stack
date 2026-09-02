"""Challenge selection: its preimage, its exclusion, and its rate.

The recorded run is over a fixed beacon and a fixed seat range, so the rate is a
property of a stated sample rather than a claim about every beacon. What is
claimed absolutely is the rule: the preimage's shape, the excluded tail of every
slot, and that the height is bound.
"""

from __future__ import annotations

import expected as x
import fixture as f
from checker import Checker

from simulation.economy_transition_v8 import contract as c
from simulation.economy_transition_v8 import slots as s

SAMPLE_SEATS = 400


def check_preimage(check: Checker) -> None:
    check.section("The selection preimage is 44 octets of fixed-width fields.")
    preimage = s.challenge_preimage(f.BEACON, 7, f.CHALLENGE_HEIGHT)
    check.agree(
        "selection.preimage",
        x.challenge_preimage(f.BEACON, 7, f.CHALLENGE_HEIGHT),
        preimage,
    )
    check.agree("selection.preimage_bytes", 32 + 4 + 8, len(preimage))
    check.agree(
        "selection.value",
        x.selection_value(f.BEACON, 7, f.CHALLENGE_HEIGHT),
        s.selection_value(f.BEACON, 7, f.CHALLENGE_HEIGHT),
    )
    check.equal(
        "selection.binds_the_height",
        s.selection_value(f.BEACON, 7, f.CHALLENGE_HEIGHT)
        != s.selection_value(f.BEACON, 7, f.CHALLENGE_HEIGHT + 1),
    )
    check.equal(
        "selection.binds_the_seat",
        s.selection_value(f.BEACON, 7, f.CHALLENGE_HEIGHT)
        != s.selection_value(f.BEACON, 8, f.CHALLENGE_HEIGHT),
    )
    check.equal(
        "selection.binds_the_beacon",
        s.selection_value(f.BEACON, 7, f.CHALLENGE_HEIGHT)
        != s.selection_value(bytes(32), 7, f.CHALLENGE_HEIGHT),
    )


def check_exclusion(check: Checker) -> None:
    check.section("The final twenty heights of every slot issue nothing.")
    window_start = c.CYCLE_BLOCKS * f.MEASURED_WINDOW
    last = window_start + c.SLOT_BLOCKS - 1
    boundary = last - c.RESPONSE_DEADLINE_BLOCKS
    check.agree(
        "selection.challengeable_heights_per_slot",
        x.CHALLENGEABLE_HEIGHTS_PER_SLOT,
        sum(
            1
            for height in range(window_start, last + 1)
            if s.is_challengeable_height(height)
        ),
    )
    check.equal(
        "selection.last_challengeable_height_of_a_slot_is_challengeable",
        s.is_challengeable_height(boundary),
    )
    check.equal(
        "selection.the_next_height_is_excluded",
        not s.is_challengeable_height(boundary + 1),
    )
    check.equal(
        "selection.the_slot_s_last_height_is_excluded",
        not s.is_challengeable_height(last),
    )
    check.equal(
        "selection.an_excluded_height_selects_nobody",
        not any(s.is_selected(f.BEACON, seat, last) for seat in range(SAMPLE_SEATS)),
    )
    check.equal(
        "selection.a_challenge_and_its_deadline_share_a_slot",
        all(
            s.slot_of_height(height) == s.slot_of_height(height + c.RESPONSE_DEADLINE_BLOCKS)
            for height in range(window_start, boundary + 1)
        ),
    )


def check_rate(check: Checker) -> None:
    """One challenge per slot in expectation, over a recorded sample."""
    check.section("The sampling rate, over a stated sample rather than in general.")
    window_start = c.CYCLE_BLOCKS * f.MEASURED_WINDOW
    heights = range(window_start, window_start + c.SLOT_BLOCKS)
    selected = sum(
        1
        for height in heights
        for seat in range(SAMPLE_SEATS)
        if s.is_selected(f.BEACON, seat, height)
    )
    check.agree(
        "selection.sample.seats", SAMPLE_SEATS, SAMPLE_SEATS
    )
    check.equal("selection.sample.selected_in_one_slot", selected)
    check.equal(
        "selection.sample.is_within_half_of_one_per_seat",
        abs(selected - SAMPLE_SEATS) * 2 <= SAMPLE_SEATS,
    )
    check.agree(
        "selection.period_equals_the_slot",
        x.CHALLENGE_PERIOD_BLOCKS,
        c.CHALLENGE_PERIOD_BLOCKS,
    )
    check.equal(
        "selection.period_is_the_slot_length",
        c.CHALLENGE_PERIOD_BLOCKS == c.SLOT_BLOCKS,
    )
