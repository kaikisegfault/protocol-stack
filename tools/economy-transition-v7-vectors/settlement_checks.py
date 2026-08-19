"""The settlement: the recovery pool's arithmetic, the two sets, and both
conservation identities.

Every recorded figure is produced twice — once by `expected.py`, which restates
steps 5 through 7 from the specification and imports nothing from `simulation/`,
and once by a live run of the model — and the two must agree before a value is
recorded at all.
"""

from __future__ import annotations

from pathlib import Path

import expected as e
import schedule as fixture
from simulation.economy_transition_v7 import contract as c
from simulation.economy_transition_v7 import settlement as t
from simulation.economy_transition_v7.conservation import CycleSeat, SettlementLedger


def _cycle_seats(seats: list[dict]) -> list[CycleSeat]:
    return [
        CycleSeat(
            seat_id=seat["seat_id"],
            uptime_seconds=seat["uptime"],
            in_span=seat["in_span"],
        )
        for seat in seats
    ]


def _with_marks(seats: list[dict], window: int, marks: dict[int, int]) -> list[dict]:
    return [
        dict(seat, window=window, mark=marks.get(seat["seat_id"], 0)) for seat in seats
    ]


def _legs_string(values: dict[int, int]) -> str:
    return ",".join(str(values[channel]) for channel in e.RECOVERY_POOL_LEGS)


def run_main() -> tuple[SettlementLedger, dict[int, dict]]:
    """One live run of the model over the recorded schedule."""
    ledger = SettlementLedger()
    derived: dict[int, dict] = {}
    for window in sorted(fixture.MAIN):
        _name, seats = fixture.MAIN[window]
        derived[window] = ledger.assign(window, _cycle_seats(seats))
    return ledger, derived


def run_main_closed_form() -> tuple[list[dict], dict[int, dict]]:
    """The same schedule under the specification's own restatement."""
    pool = {channel: 0 for channel in e.RECOVERY_POOL_LEGS}
    ordered: list[dict] = []
    records: dict[int, dict] = {}
    for window in sorted(fixture.MAIN):
        _name, seats = fixture.MAIN[window]
        outcome = e.assign(_with_marks(seats, window, {}), pool)
        outcome["window"] = window
        pool = outcome["pool_after"]
        ordered.append(outcome)
        records[window] = outcome
    return ordered, records


def check_cycles(check) -> None:
    live, live_records = run_main()
    closed, closed_records = run_main_closed_form()
    check.equal("settlement.schedule.cycle_count", len(closed))

    for outcome in closed:
        window = outcome["window"]
        name, _seats = fixture.MAIN[window]
        assignment = live_records[window]
        prefix = f"settlement.w{window}"
        check.equal(f"{prefix}.name", name)
        check.agree(f"{prefix}.in_scope_count", len(fixture.MAIN[window][1]), assignment.in_scope_count)
        # The two sets are the specification's reading of the fixture, so they
        # are recorded from the closed form alone. What the model is required to
        # agree about is what it *did* with them: its winner set is exactly the
        # top of the eligible set, and its contributing count is the number of
        # permissions it assigned.
        check.equal(
            f"{prefix}.eligible",
            ",".join(str(seat) for seat in outcome["eligible"]) or "none",
        )
        check.equal(
            f"{prefix}.contributing",
            ",".join(str(seat) for seat in outcome["contributing"]) or "none",
        )
        check.equal(
            f"{prefix}.winners_are_the_top_of_the_eligible_set",
            _tops_the_eligible_set(assignment.winners, outcome, window),
        )
        check.equal(
            f"{prefix}.assigned_permissions_is_the_contributing_count",
            assignment.assigned_permissions == len(outcome["contributing"]),
        )
        check.agree(
            f"{prefix}.winners",
            ",".join(str(seat) for seat in outcome["winners"]) or "none",
            ",".join(str(seat) for seat in assignment.winners) or "none",
        )
        check.agree(
            f"{prefix}.accrued",
            ",".join(str(seat) for seat in outcome["accrued"]) or "none",
            ",".join(str(seat) for seat in assignment.accrued) or "none",
        )
        check.agree(
            f"{prefix}.assigned_permissions",
            outcome["assigned"],
            assignment.assigned_permissions,
        )
        check.agree(
            f"{prefix}.reallocated_count",
            outcome["reallocated"],
            assignment.reallocated_count,
        )
        check.agree(
            f"{prefix}.pool_before",
            _legs_string(outcome["pool_before"]),
            _legs_string(assignment.pool_before),
        )
        check.agree(
            f"{prefix}.pool_absorbed",
            _legs_string(outcome["pool_absorbed"]),
            _legs_string(assignment.pool_absorbed),
        )
        check.agree(
            f"{prefix}.pool_share_per_winner",
            _legs_string(outcome["pool_share"]),
            _legs_string(assignment.pool_share_per_channel),
        )
        check.agree(
            f"{prefix}.pool_residual",
            _legs_string(outcome["pool_residual"]),
            _legs_string(assignment.pool_residual_per_channel),
        )
        check.agree(
            f"{prefix}.reallocation_dust",
            _legs_string(outcome["dust"]),
            _legs_string(assignment.dust_per_channel),
        )
        check.agree(
            f"{prefix}.pool_after",
            _legs_string(outcome["pool_after"]),
            _legs_string(assignment.pool_after),
        )
        check.agree(
            f"{prefix}.outstanding_delta",
            _legs_string(outcome["outstanding_delta"]),
            _legs_string(t.outstanding_delta(assignment)),
        )


def _tops_the_eligible_set(winners, outcome, window: int) -> bool:
    """The model's winner set is exactly the highest uptime in the eligible set.

    An empty eligible set must produce an empty winner set; a non-empty one must
    produce every seat at its maximum uptime and no other. This is what makes the
    recorded eligible set a claim about the model rather than a restatement of
    the fixture.
    """
    eligible = set(outcome["eligible"])
    if not eligible:
        return tuple(winners) == ()
    _name, seats = fixture.MAIN[window]
    uptime = {
        seat["seat_id"]: seat["uptime"]
        for seat in seats
        if seat["seat_id"] in eligible
    }
    best = max(uptime.values())
    return tuple(winners) == tuple(
        sorted(seat for seat, value in uptime.items() if value == best)
    )


def check_two_sets(check) -> None:
    """Rule 2 and rule 3, guarded rather than described."""
    _live, closed_records = run_main_closed_form()
    outsider_window = 3
    outcome = closed_records[outsider_window]
    check.equal(
        "settlement.sets.eligible_holds_a_seat_the_contributing_set_does_not",
        set(outcome["eligible"]) - set(outcome["contributing"]) != set(),
    )
    check.equal(
        "settlement.sets.a_seat_past_its_span_won_the_cycle",
        set(outcome["winners"]) - set(outcome["contributing"]) != set(),
    )
    check.equal(
        "settlement.sets.that_winner_took_the_whole_pool",
        outcome["pool_share"] == outcome["pool_before"]
        and outcome["pool_before"] != {ch: 0 for ch in e.RECOVERY_POOL_LEGS},
    )

    # The regression guard: a winner derivation narrowed to the contributing set
    # would return a different winner set here, and none at all at window 8.
    narrowed = _span_filtered_winners(outsider_window)
    check.equal(
        "settlement.sets.a_span_filtered_winner_set_would_differ",
        narrowed != outcome["winners"],
    )
    check.equal(
        "settlement.sets.a_span_filtered_winner_set_would_be_empty_at_window8",
        _span_filtered_winners(8) == (),
    )
    check.equal(
        "settlement.sets.window8_has_no_contributing_seat",
        closed_records[8]["contributing"] == (),
    )
    check.equal(
        "settlement.sets.window8_still_drained_the_pool",
        sum(closed_records[8]["pool_absorbed"].values()) > 0,
    )


def _span_filtered_winners(window: int) -> tuple[int, ...]:
    _name, seats = fixture.MAIN[window]
    in_span = [seat for seat in seats if seat["in_span"]]
    return e.winner_set(_with_marks(in_span, window, {}))


def check_collection(check) -> None:
    """What each mint takes, under both derivations."""
    ledger, _records = run_main()
    _closed, closed_records = run_main_closed_form()
    last = fixture.MAIN_LAST_ASSIGNED
    for seat_id in fixture.MAIN_MINTS:
        live = ledger.mint(seat_id, last)
        closed = e.collect(seat_id, 0, last, closed_records)
        prefix = f"collection.seat{seat_id}"
        check.agree(f"{prefix}.per_channel", _legs_string(closed), _legs_string(live.per_channel))
        check.agree(f"{prefix}.total_atomic", sum(closed.values()), live.total_atomic)
        check.equal(f"{prefix}.windows_walked", live.windows_walked)
        check.equal(
            f"{prefix}.accrued_windows",
            ",".join(str(window) for window in live.accrued_windows) or "none",
        )
        check.equal(
            f"{prefix}.won_windows",
            ",".join(str(window) for window in live.won_windows) or "none",
        )
    check.equal(
        "collection.a_seat_past_its_span_collected_without_ever_accruing",
        ledger.marks[9] == last,
    )
    check.equal("collection.identities_hold_after_every_mint", ledger.identity_failures() == [])


def check_conservation(check) -> None:
    """Both identities, at every step and at the end."""
    ledger = SettlementLedger()
    for window in sorted(fixture.MAIN):
        _name, seats = fixture.MAIN[window]
        ledger.assign(window, _cycle_seats(seats))
        prefix = f"conservation.w{window}"
        check.equal(f"{prefix}.assigned_permissions", ledger.assigned_permissions)
        check.equal(f"{prefix}.pool_total", ledger.pool_total())
        check.equal(
            f"{prefix}.outstanding_total", sum(ledger.channel_outstanding.values())
        )
        check.equal(f"{prefix}.claimable_total", sum(ledger.claimable().values()))
        check.equal(f"{prefix}.both_identities_hold", ledger.identity_failures() == [])

    for seat_id in fixture.MAIN_MINTS:
        ledger.mint(seat_id, fixture.MAIN_LAST_ASSIGNED)

    owed = ledger.claimable()
    for channel in c.RECOVERY_POOL_LEGS:
        prefix = f"conservation.final.channel{channel}"
        check.equal(f"{prefix}.issued", ledger.channel_issued[channel])
        check.equal(f"{prefix}.outstanding", ledger.channel_outstanding[channel])
        check.equal(f"{prefix}.claimable", owed[channel])
        check.equal(f"{prefix}.recovery_pool", ledger.pool[channel])
        check.equal(f"{prefix}.assigned_total", ledger.assigned_total(channel))
        check.equal(
            f"{prefix}.channel_identity_holds",
            ledger.channel_issued[channel] + ledger.channel_outstanding[channel]
            == ledger.assigned_total(channel),
        )
        check.equal(
            f"{prefix}.backing_identity_holds",
            owed[channel] + ledger.pool[channel]
            == ledger.channel_outstanding[channel],
        )
    check.equal(
        "conservation.final.every_assigned_unit_is_issued_claimable_or_pooled",
        all(
            ledger.channel_issued[channel] + owed[channel] + ledger.pool[channel]
            == ledger.assigned_total(channel)
            for channel in c.RECOVERY_POOL_LEGS
        ),
    )
    check.equal(
        "conservation.final.assigned_total_atomic",
        sum(ledger.assigned_total(channel) for channel in c.RECOVERY_POOL_LEGS),
    )


def check_accumulation_cap(check) -> None:
    """A seat crossing the cap in both directions loses nothing."""
    ledger = SettlementLedger()
    seats = fixture.cap_seats()
    for window in fixture.CAP_WINDOWS:
        ledger.assign(window, _cycle_seats(seats))
        if window == fixture.CAP_MINT_WINDOW:
            ledger.mint(1, window)
    over = fixture.CAP_LAST_ASSIGNED
    record = ledger.assignments[over]
    from simulation.economy_transition_v7.state import (
        bit_is_set,
        decode_cycle_assignment_value,
    )

    decoded = decode_cycle_assignment_value(record)
    check.equal("settlement.cap.window", over)
    check.agree(
        "settlement.cap.seat0_is_over_the_cap_at_this_window",
        not e.accrues(over, 0),
        not t.accrues_in_window(over, 0),
    )
    check.agree(
        "settlement.cap.seat1_is_under_the_cap_at_this_window",
        e.accrues(over, fixture.CAP_MINT_WINDOW),
        t.accrues_in_window(over, fixture.CAP_MINT_WINDOW),
    )
    check.equal(
        "settlement.cap.an_over_cap_seat_does_not_accrue",
        not bit_is_set(decoded["accrued_bitmap"], 0),
    )
    check.equal(
        "settlement.cap.an_over_cap_seat_is_not_a_winner",
        not bit_is_set(decoded["winner_bitmap"], 0),
    )
    check.equal(
        "settlement.cap.its_permission_was_reallocated",
        decoded["reallocated_count"] == 1,
    )
    check.equal("settlement.cap.identities_hold_over_the_cap", ledger.identity_failures() == [])

    walk = t.walk_range(0, over)
    check.agree("settlement.cap.walk_first_window", e.walk_range(0, over)[0], walk[0])
    check.agree("settlement.cap.walk_last_window", e.walk_range(0, over)[1], walk[1])
    check.equal(
        "settlement.cap.the_walk_stops_before_the_over_cap_window", walk[1] < over
    )

    collection = ledger.mint(0, over)
    check.equal("settlement.cap.seat0_collected_atomic", collection.total_atomic)
    check.equal(
        "settlement.cap.seat0_collected_every_window_it_accrued",
        len(collection.accrued_windows) == c.MINT_ACCUMULATION_CAP,
    )
    check.equal("settlement.cap.seat0_mark_after_the_mint", ledger.marks[0])
    check.equal(
        "settlement.cap.seat0_is_under_the_cap_again",
        t.accrues_in_window(over + 1, ledger.marks[0]),
    )
    check.equal(
        "settlement.cap.identities_hold_after_the_mint", ledger.identity_failures() == []
    )
    check.equal("settlement.cap.pool_total_after_the_mint", ledger.pool_total())
