"""The expiry sweep, the derived schedule, and the claim that settles nothing.

The load-bearing vector here is the last one: a schedule derived from state
reproduces a version-seven assignment record **exactly**, when the same seats
and uptimes are measured. That is what establishes that the carrier changed no
settlement, and it is checked against version seven's own accepted model rather
than against version eight's.
"""

from __future__ import annotations

import expected as x
import fixture as f
from checker import Checker

from simulation.economy_transition_v3.settlement import SeatCycle
from simulation.economy_transition_v7.settlement import (
    assignment_entry,
    derive_assignment,
    empty_pool,
)
from simulation.economy_transition_v8 import contract as c
from simulation.economy_transition_v8 import state as st
from simulation.economy_transition_v8 import uptime_transitions as t
from simulation.economy_transition_v8.schedule import derive_schedule
from simulation.economy_transition_v8.slots import slot_of_height


def check_expiry(check: Checker) -> None:
    check.section("Expiry: the model's slot-close sweep, made incremental.")
    context = t.Context(
        chain_id=bytes(32), height=0, dispute_authority_key=f.DISPUTE_AUTHORITY_KEY
    )
    # One challenge in each of three different slots, so an answered one and an
    # unanswered one cannot be confused for each other by sharing a slot.
    heights = [f.CHALLENGE_HEIGHT + slot * c.SLOT_BLOCKS for slot in range(3)]
    for height in heights:
        t.issue_challenge(context, height, f.ACTIVE_SEAT)

    # The first is answered, the second and third are not.
    context.economy[st.open_challenge_key(heights[0], f.ACTIVE_SEAT)] = (
        st.open_challenge_value(st.CHALLENGE_ANSWERED)
    )
    for height in heights:
        t.expire_challenge(context, height, f.ACTIVE_SEAT)

    check.equal(
        "expiry.deletes_every_resolved_challenge",
        not any(key[0] == c.OPEN_CHALLENGE_ENTRY for key in context.economy),
    )
    credited, disputed = st.decode_seat_window_value(
        context.economy[st.seat_window_key(f.MEASURED_WINDOW, f.ACTIVE_SEAT)]
    )
    lost = {slot_of_height(heights[1]), slot_of_height(heights[2])}
    check.agree(
        "expiry.credited_after_two_unanswered",
        x.all_slots_credited() & ~sum(1 << slot for slot in lost),
        credited,
    )
    check.agree("expiry.disputed_stays_empty", 0, disputed)
    check.agree(
        "expiry.uptime_seconds_after",
        x.uptime_seconds(x.all_slots_credited() & ~sum(1 << slot for slot in lost), 0),
        st.credited_slots(credited, disputed) * c.SLOT_SECONDS,
    )
    check.equal(
        "expiry.an_answered_challenge_costs_no_slot",
        bool(credited & (1 << slot_of_height(heights[0]))),
    )
    check.agree(
        "expiry.slots_lost", 2, x.SLOTS_PER_WINDOW - st.credited_slots(credited, disputed)
    )

    check.section("Two lost challenges in one slot cost one slot.")
    twice = t.Context(chain_id=bytes(32), height=0, dispute_authority_key=bytes(32))
    for height in (f.CHALLENGE_HEIGHT, f.CHALLENGE_HEIGHT + 5):
        t.issue_challenge(twice, height, f.ACTIVE_SEAT)
        t.expire_challenge(twice, height, f.ACTIVE_SEAT)
    credited_twice, _ = st.decode_seat_window_value(
        twice.economy[st.seat_window_key(f.MEASURED_WINDOW, f.ACTIVE_SEAT)]
    )
    check.agree(
        "expiry.two_losses_in_one_slot_cost_one_slot",
        x.SLOTS_PER_WINDOW - 1,
        st.credited_slots(credited_twice, 0),
    )


def _activations() -> dict[int, int]:
    return {
        f.ACTIVE_SEAT: f.ACTIVE_SEAT_ACTIVATION_HEIGHT,
        f.LATE_SEAT: f.LATE_SEAT_ACTIVATION_HEIGHT,
    }


def check_schedule(check: Checker) -> None:
    check.section("The schedule is derived from state, and it is complete.")
    economy: dict[bytes, bytes] = {
        st.seat_window_key(f.MEASURED_WINDOW, f.ACTIVE_SEAT): st.seat_window_value(
            x.all_slots_credited() & ~0b111, 0
        )
    }
    measured = derive_schedule(_activations(), f.MEASURED_WINDOW, economy)

    check.agree("schedule.in_scope_count", 1, len(measured))
    check.equal(
        "schedule.omits_a_seat_activated_inside_the_window",
        all(seat.seat_id != f.LATE_SEAT for seat in measured),
    )
    check.agree("schedule.seat_id", f.ACTIVE_SEAT, measured[0].seat_id)
    check.agree(
        "schedule.uptime_seconds",
        x.uptime_seconds(x.all_slots_credited() & ~0b111, 0),
        measured[0].uptime_seconds,
    )
    check.equal("schedule.in_span", measured[0].in_span)

    check.section("A seat with no record is present with a full credit.")
    without = derive_schedule(_activations(), f.MEASURED_WINDOW, {})
    check.agree("schedule.absent_record_uptime_seconds", 86_400, without[0].uptime_seconds)
    check.equal("schedule.absent_record_is_not_an_omission", len(without) == len(measured))

    check.section("A seat past its own 731 cycles is in scope and out of span.")
    past = f.ACTIVE_SEAT_ACTIVATION_HEIGHT
    late_window = x.first_cycle_window(past) + x.ISSUANCE_CYCLES_PER_SEAT
    beyond = derive_schedule({f.ACTIVE_SEAT: past}, late_window, {})
    check.agree("schedule.past_span.in_scope_count", 1, len(beyond))
    check.equal("schedule.past_span.is_out_of_span", not beyond[0].in_span)
    inside = derive_schedule({f.ACTIVE_SEAT: past}, late_window - 1, {})
    check.equal("schedule.last_window_of_the_span_is_in_span", inside[0].in_span)


def check_settlement_is_unchanged(check: Checker) -> None:
    """The claim the whole carrier rests on, checked against version seven."""
    check.section("A derived schedule settles exactly as a supplied one does.")
    economy = {
        st.seat_window_key(f.MEASURED_WINDOW, f.ACTIVE_SEAT): st.seat_window_value(
            x.all_slots_credited() & ~0b111, 0
        )
    }
    activations = dict(_activations())
    activations[4] = f.ACTIVE_SEAT_ACTIVATION_HEIGHT
    measured = derive_schedule(activations, f.MEASURED_WINDOW, economy)

    # What a version-seven caller would have supplied, computed here from the
    # specification's arithmetic rather than from the derivation under test. The
    # claim is that the chain reaches this list on its own; comparing the
    # derivation to itself would establish nothing.
    independent = [
        (f.ACTIVE_SEAT, x.uptime_seconds(x.all_slots_credited() & ~0b111, 0), True),
        (4, x.uptime_seconds(x.all_slots_credited(), 0), True),
    ]
    check.equal(
        "settlement.derived_schedule_equals_the_supplied_one",
        [(seat.seat_id, seat.uptime_seconds, seat.in_span) for seat in measured]
        == independent,
    )

    supplied = [
        SeatCycle(
            seat_id=seat_id,
            uptime_seconds=seconds,
            in_span=in_span,
            minted_through_window=0,
            referrer_account_id=None,
        )
        for seat_id, seconds, in_span in independent
    ]
    assignment = derive_assignment(f.MEASURED_WINDOW, supplied, empty_pool())
    key, value = assignment_entry(assignment)

    check.agree("settlement.measured_seats", 2, len(measured))
    check.agree("settlement.in_scope_count", 2, assignment.in_scope_count)
    check.equal("settlement.record_key", key)
    check.equal("settlement.record_value", value)
    check.agree(
        "settlement.record_fixed_bytes",
        c.CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES,
        len(value) - 2 * ((assignment.bitmap_bits + 7) // 8),
    )
    check.equal(
        "settlement.the_winner_is_the_seat_with_no_lost_slot",
        assignment.winners == (4,),
    )
    check.equal(
        "settlement.both_seats_contribute",
        assignment.assigned_permissions == 2,
    )
    check.equal(
        "settlement.the_record_is_version_seven_s_encoding",
        key == b"\x03" + f.MEASURED_WINDOW.to_bytes(8, "big"),
    )
