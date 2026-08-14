"""The accumulation cap, the cycle assignment, the mint walk, and conservation.

Every value here is derived twice: once by `expected.py`, which reimplements the
cap predicate, the winner rule, the split, and the walk from the specification's
prose, and once by the model. A settlement defect that produced a
self-consistent record would still have to produce the same record twice from
two independently written implementations.

The winner rule is derived a third time where it can be: the accepted economy
model `founder-economy-simulator-v3` already decides who wins a cycle from a
supplied uptime record, and this encoding must not hold a second opinion about
it.
"""

from __future__ import annotations

import expected as e
from checker import Checker

from simulation.economy_transition_v3 import contract as c
from simulation.economy_transition_v3 import scenario, settlement, state, winners


def _as_expected_seats(seats: list[settlement.SeatCycle]) -> list[dict]:
    return [
        {
            "seat_id": seat.seat_id,
            "uptime_seconds": seat.uptime_seconds,
            "in_span": seat.in_span,
            "mark": seat.minted_through_window,
        }
        for seat in seats
    ]


def check_cap(check: Checker) -> None:
    """The accrual predicate at its boundary, and the walk range it bounds."""
    check.agree(
        "cap.windows", e.MINT_ACCUMULATION_CAP, c.MINT_ACCUMULATION_CAP
    )
    check.equal("cap.days", c.MINT_ACCUMULATION_CAP)
    check.equal("cap.blocks", c.MINT_ACCUMULATION_CAP * c.CYCLE_BLOCKS)
    check.agree(
        "cap.assignment_lag_windows", e.ASSIGNMENT_LAG_WINDOWS, c.ASSIGNMENT_LAG_WINDOWS
    )

    mark = 1_000
    for offset in (1, c.MINT_ACCUMULATION_CAP, c.MINT_ACCUMULATION_CAP + 1):
        window = mark + offset
        check.agree(
            f"cap.accrues_at_offset.{offset}",
            e.accrues(window, mark),
            settlement.accrues_in_window(window, mark),
        )
    # The boundary is inclusive: a seat accrues for exactly thirty windows after
    # its mark and nothing after that.
    check.equal(
        "cap.accruing_windows_after_a_mark",
        sum(
            1
            for offset in range(1, 2 * c.MINT_ACCUMULATION_CAP + 1)
            if settlement.accrues_in_window(mark + offset, mark)
        ),
    )

    # `window_of_height(h) - 2`, and nothing while the chain is younger.
    for height in (0, c.CYCLE_BLOCKS, 2 * c.CYCLE_BLOCKS, scenario.ASSIGNMENT_HEIGHT):
        derived = settlement.last_assigned_window(height)
        check.agree(
            f"cap.last_assigned_window.{height}",
            "none" if e.last_assigned_window(height) is None else e.last_assigned_window(height),
            "none" if derived is None else derived,
        )

    # The walk range at the fixture's own mark, and on a chain old enough for a
    # mark to be a decade behind. A seat that never mints is the case the cap
    # exists to bound, so it is exercised against a real span rather than a
    # synthetic one.
    last = settlement.last_assigned_window(scenario.ASSIGNMENT_HEIGHT)
    decade = 3_650
    cases = {
        "current": (scenario.CURRENT_MARK, last),
        "at_last_assigned": (last, last),
        "one_window_behind": (decade - 1, decade),
        "a_month_behind": (decade - 30, decade),
        "a_month_and_a_day_behind": (decade - 31, decade),
        "a_decade_behind": (0, decade),
    }
    for name, (mark_value, horizon) in sorted(cases.items()):
        derived = settlement.walk_range(mark_value, horizon)
        expected = e.walk_range(mark_value, horizon)
        check.agree(
            f"cap.walk_range.{name}",
            "none" if expected is None else f"{expected[0]}..{expected[1]}",
            "none" if derived is None else f"{derived[0]}..{derived[1]}",
        )
        check.equal(
            f"cap.walk_length.{name}", settlement.walk_length(mark_value, horizon)
        )
    # The bound is the point of the window form: however long a founder waits,
    # the walk is at most the cap.
    check.equal(
        "cap.walk_never_exceeds_the_cap",
        all(
            settlement.walk_length(decade - behind, decade) <= c.MINT_ACCUMULATION_CAP
            for behind in (0, 1, 30, 31, 365, 3_650)
        ),
    )
    check.equal(
        "cap.walk_is_empty_at_the_last_assigned_window",
        settlement.walk_length(last, last) == 0,
    )
    check.equal(
        "cap.no_window_before_the_chain_has_assigned_anything",
        settlement.walk_range(0, settlement.last_assigned_window(0)) is None,
    )
    check.equal("cap.reject.negative_mark", _walk_refusal(-1, last))


def _walk_refusal(mark: int, last_assigned: int | None) -> str:
    try:
        settlement.walk_range(mark, last_assigned)
    except settlement.InvalidSettlement:
        return "INVALID_SETTLEMENT"
    return "accepted"


def check_assignment(check: Checker) -> None:
    """Both cycles, derived twice and cross-checked against the economy model."""
    from simulation.founder_economy_v3 import uptime as economy_uptime

    for name, window, seats in (
        ("cycle", scenario.CYCLE_WINDOW, scenario.cycle_seats()),
        ("outage", scenario.OUTAGE_WINDOW, scenario.outage_seats()),
    ):
        derived = settlement.derive_assignment(window, seats)
        independent = e.derive_cycle(window, _as_expected_seats(seats))

        check.agree(
            f"{name}.winners",
            ",".join(str(seat) for seat in independent["winners"]),
            ",".join(str(seat) for seat in derived.winners),
        )
        check.agree(
            f"{name}.accrued",
            ",".join(str(seat) for seat in independent["accrued"]),
            ",".join(str(seat) for seat in derived.accrued),
        )
        check.agree(
            f"{name}.winner_count", len(independent["winners"]), derived.winner_count
        )
        check.agree(
            f"{name}.reallocated_count",
            independent["reallocated_count"],
            derived.reallocated_count,
        )
        check.agree(
            f"{name}.in_scope_count", independent["in_scope_count"], derived.in_scope_count
        )
        check.agree(
            f"{name}.assigned_permissions",
            independent["assigned"],
            derived.assigned_permissions,
        )
        check.agree(
            f"{name}.bitmap_bits", independent["bitmap_bits"], derived.bitmap_bits
        )
        for channel in sorted(derived.share_per_channel):
            check.agree(
                f"{name}.share_atomic.{channel}",
                independent["shares"][channel],
                derived.share_per_channel[channel],
            )
            check.agree(
                f"{name}.carry_atomic.{channel}",
                independent["carries"][channel],
                derived.carry_per_channel[channel],
            )

        key, value = settlement.assignment_entry(derived)
        check.equal(f"{name}.assignment_key", key.hex())
        check.equal(f"{name}.assignment_value_hex", value.hex())
        check.agree(
            f"{name}.assignment_entry_bytes",
            e.entry_bytes(c.CYCLE_ASSIGNMENT_ENTRY, derived.bitmap_bits),
            len(key) + len(value),
        )
        decoded = state.decode_cycle_assignment_value(value)
        check.equal(f"{name}.assignment_roundtrip", decoded["bitmap_bits"] == derived.bitmap_bits)
        check.agree(
            f"{name}.accrued_bitmap",
            e.bitmap(independent["accrued"], independent["bitmap_bits"]).hex(),
            decoded["accrued_bitmap"].hex(),
        )
        check.agree(
            f"{name}.winner_bitmap",
            e.bitmap(independent["winners"], independent["bitmap_bits"]).hex(),
            decoded["winner_bitmap"].hex(),
        )

        # The encoding must not hold a second opinion about who met a cycle.
        check.equal(
            f"{name}.met_flags_are_the_accepted_threshold",
            all(
                winners.met_cycle(seat.uptime_seconds)
                == economy_uptime.met_cycle(seat.uptime_seconds)
                for seat in seats
            ),
        )

    _check_cap_excludes_the_best_performer(check)
    _check_bitmap_indexing(check)


def _check_cap_excludes_the_best_performer(check: Checker) -> None:
    """The one case version two could not have, isolated as a discriminator.

    Seat 11 holds the cycle's maximum uptime and is over the cap. If a capped
    seat were eligible to win, the winner set would be that seat alone. Because
    it is not, the winners are the three seats at the next-highest figure, and
    seat 11's own permission is reallocated to them.
    """
    from simulation.founder_economy_v3 import uptime as economy_uptime

    seats = scenario.cycle_seats()
    derived = settlement.derive_assignment(scenario.CYCLE_WINDOW, seats)
    capped = [
        seat.seat_id
        for seat in seats
        if not settlement.accrues_in_window(
            scenario.CYCLE_WINDOW, seat.minted_through_window
        )
    ]
    check.equal("cap.capped_seats", ",".join(str(seat) for seat in sorted(capped)))
    check.equal(
        "cap.capped_seat_holds_the_maximum_uptime",
        max(seat.uptime_seconds for seat in seats)
        == max(seat.uptime_seconds for seat in seats if seat.seat_id in capped),
    )
    check.equal(
        "cap.capped_seat_is_not_a_winner",
        all(seat not in derived.winners for seat in capped),
    )
    check.equal(
        "cap.capped_seat_does_not_accrue",
        all(seat not in derived.accrued for seat in capped),
    )
    # Without the cap the same measurements give a different winner set, which
    # is what makes this a discriminator rather than a restatement. The accepted
    # economy model applies no cap, so it is the uncapped answer.
    record = {
        "entries": [
            {"seat_id": seat.seat_id, "uptime_seconds": seat.uptime_seconds}
            for seat in seats
        ]
    }
    uncapped = economy_uptime.winner_seats(record)
    check.equal("cap.uncapped_winner_set", ",".join(str(seat) for seat in uncapped))
    check.equal("cap.the_cap_changes_the_winner_set", uncapped != derived.winners)
    # Every reallocated unit reaches a seat that can collect it, which is the
    # property excluding capped seats exists to preserve.
    check.equal(
        "cap.every_winner_can_collect",
        all(
            settlement.accrues_in_window(
                scenario.CYCLE_WINDOW,
                next(s.minted_through_window for s in seats if s.seat_id == seat),
            )
            for seat in derived.winners
        ),
    )


def _check_bitmap_indexing(check: Checker) -> None:
    """Bits are addressed by seat ID, so a lookup is a shift and a mask."""
    derived = settlement.derive_assignment(scenario.CYCLE_WINDOW, scenario.cycle_seats())
    _, value = settlement.assignment_entry(derived)
    decoded = state.decode_cycle_assignment_value(value)
    for seat in (0, 4, 7, 11, 23):
        check.equal(
            f"cycle.accrued_bit.{seat}",
            state.bit_is_set(decoded["accrued_bitmap"], seat),
        )
        check.equal(
            f"cycle.winner_bit.{seat}",
            state.bit_is_set(decoded["winner_bitmap"], seat),
        )
    check.equal(
        "cycle.bitmaps_differ",
        decoded["accrued_bitmap"] != decoded["winner_bitmap"],
    )
    # Accruing and winning are independent facts, and the fixture shows both
    # directions. A seat past its own 731 cycles wins without accruing; a seat
    # exactly on the activity threshold accrues without winning.
    check.equal(
        "cycle.a_seat_may_win_without_accruing",
        any(
            state.bit_is_set(decoded["winner_bitmap"], seat)
            and not state.bit_is_set(decoded["accrued_bitmap"], seat)
            for seat in range(derived.bitmap_bits)
        ),
    )
    check.equal(
        "cycle.a_seat_may_accrue_without_winning",
        any(
            state.bit_is_set(decoded["accrued_bitmap"], seat)
            and not state.bit_is_set(decoded["winner_bitmap"], seat)
            for seat in range(derived.bitmap_bits)
        ),
    )
    # A seat beyond the record reads as clear rather than as an error, so an
    # absent record and a record with both bits clear are the same fact.
    check.equal(
        "cycle.a_seat_beyond_the_bitmap_reads_clear",
        not state.bit_is_set(decoded["accrued_bitmap"], derived.bitmap_bits + 1),
    )
    check.equal("cycle.bitmap_bytes", e.bitmap_bytes(derived.bitmap_bits))


def check_mint_walk(check: Checker) -> None:
    """What each seat collects, derived twice."""
    last = settlement.last_assigned_window(scenario.ASSIGNMENT_HEIGHT)
    records = scenario.assignment_records()
    cycles = {
        window: e.derive_cycle(
            window,
            _as_expected_seats(
                scenario.cycle_seats() if window == scenario.CYCLE_WINDOW
                else scenario.outage_seats()
            ),
        )
        for window in records
    }

    marks = {seat.seat_id: seat.minted_through_window for seat in scenario.cycle_seats()}
    for seat_id in sorted(marks):
        mark = marks[seat_id]
        collection = settlement.collect(seat_id, mark, last, records)
        independent = e.collect(seat_id, mark, last, cycles)
        for channel in sorted(collection.per_channel):
            check.agree(
                f"mint.per_channel_atomic.{seat_id}.{channel}",
                independent[channel],
                collection.per_channel[channel],
            )
        check.agree(
            f"mint.total_atomic.{seat_id}", sum(independent.values()), collection.total_atomic
        )
        check.equal(f"mint.windows_walked.{seat_id}", collection.windows_walked)
        check.equal(
            f"mint.accrued_windows.{seat_id}",
            ",".join(str(window) for window in collection.accrued_windows),
        )
        check.equal(
            f"mint.won_windows.{seat_id}",
            ",".join(str(window) for window in collection.won_windows),
        )

    # The operator leg credits the signing manager's account; the other four
    # reach typed custody. Version two sent all five to typed custody.
    collection = settlement.collect(0, marks[0], last, records)
    check.equal("mint.operator_atomic_to_account", collection.operator_atomic)
    for kind, amount in sorted(collection.custody_atomic.items()):
        check.equal(
            f"mint.custody_atomic.{c.BENEFICIARY_KINDS[kind]}", amount
        )
    check.equal(
        "mint.operator_leg_has_no_custody_kind",
        c.LEG_BENEFICIARY_KIND[c.FOUNDER_OPERATOR_CHANNEL] is None,
    )
    # An immediate second mint finds nothing, because the mark now sits at the
    # last assigned window.
    check.equal(
        "mint.second_mint_finds_nothing",
        settlement.collect(0, last, last, records).total_atomic == 0
        and settlement.walk_range(last, last) is None,
    )
    # A capped seat's whole walk lies inside the thirty windows after its own
    # mark, which hold no record at all here, so it collects nothing and still
    # needs its mark advanced. That is why such a mint succeeds rather than
    # returning NOTHING_TO_MINT: refusing it would leave the seat permanently
    # past the cap with nothing it could ever collect.
    capped = settlement.collect(11, marks[11], last, records)
    check.equal(
        "mint.a_capped_seat_collects_nothing_and_still_has_a_walk",
        capped.total_atomic == 0 and capped.windows_walked == c.MINT_ACCUMULATION_CAP,
    )
    check.equal(
        "mint.a_capped_seat_cannot_reach_the_cycle_it_lost",
        scenario.CYCLE_WINDOW not in range(
            *_inclusive(settlement.walk_range(marks[11], last))
        ),
    )
    # A seat that failed every cycle in its walk also collects nothing, and its
    # mark is not stale — the two cases are distinct and both succeed.
    failed = settlement.collect(7, marks[7], last, records)
    check.equal(
        "mint.a_failing_seat_collects_nothing_from_a_current_mark",
        failed.total_atomic == 0 and failed.windows_walked == 2,
    )


def _inclusive(span: tuple[int, int]) -> tuple[int, int]:
    return span[0], span[1] + 1


def check_referral(check: Checker) -> None:
    """The three destinations one referral leg can reach."""
    accruals, pool = settlement.referral_accrual(
        scenario.CYCLE_WINDOW, scenario.cycle_seats(), scenario.REFERRER_MARKS
    )
    check.equal("referral.leg_atomic", c.REFERRAL_LEG_ATOMIC)
    check.agree("referral.leg_atomic_agrees", e.REFERRAL_LEG_ATOMIC, c.REFERRAL_LEG_ATOMIC)
    check.equal("referral.referrer_count", len(accruals))
    for account, amount in sorted(accruals.items()):
        check.equal(f"referral.accrued_atomic.{account.hex()[:8]}", amount)
    check.equal("referral.unreferred_pool_atomic", pool)

    seats = scenario.cycle_seats()
    in_span = [seat for seat in seats if seat.in_span]
    unreferred = [seat for seat in in_span if seat.referrer_account_id is None]
    capped = [
        seat
        for seat in in_span
        if seat.referrer_account_id is not None
        and not settlement.accrues_in_window(
            scenario.CYCLE_WINDOW,
            scenario.REFERRER_MARKS[seat.referrer_account_id],
        )
    ]
    check.equal("referral.in_span_seats", len(in_span))
    check.equal("referral.unreferred_seats", len(unreferred))
    check.equal("referral.seats_whose_referrer_is_capped", len(capped))
    check.equal(
        "referral.channel_is_consumed_exactly",
        sum(accruals.values()) + pool == len(in_span) * c.REFERRAL_LEG_ATOMIC,
    )
    # An unreferred seat and a capped referrer reach the same destination, which
    # the constitution already defines as the channel's second one, so the pool
    # takes exactly one leg for each.
    check.equal(
        "referral.unreferred_and_capped_share_a_destination",
        pool == (len(unreferred) + len(capped)) * c.REFERRAL_LEG_ATOMIC,
    )
    # A referrer with no recorded mark has never accrued, so its first accrual
    # always succeeds and it can never be capped before it has been paid. With
    # no marks at all, every referred seat accrues to its referrer.
    fresh, fresh_pool = settlement.referral_accrual(scenario.CYCLE_WINDOW, seats, {})
    check.equal(
        "referral.a_first_accrual_is_never_capped",
        sum(fresh.values())
        == (len(in_span) - len(unreferred)) * c.REFERRAL_LEG_ATOMIC,
    )
    check.equal(
        "referral.with_no_marks_only_unreferred_seats_reach_the_pool",
        fresh_pool == len(unreferred) * c.REFERRAL_LEG_ATOMIC,
    )


def check_conservation(check: Checker) -> None:
    """The carry identity, per channel, across both cycles and both mints.

    A settlement defect that moved value between beneficiaries would satisfy a
    per-transaction check and fail this one.
    """
    last = settlement.last_assigned_window(scenario.ASSIGNMENT_HEIGHT)
    records = scenario.assignment_records()
    all_assignments = scenario.assignments()

    assigned = sum(a.assigned_permissions for a in all_assignments.values())
    check.equal("conservation.assigned_permissions", assigned)

    # The assignment writes outstanding and moves the carried remainder out of
    # it. Both are tracked as a chain would: outstanding is a running balance,
    # not a derived quantity.
    carry = {channel: 0 for channel, _ in c.BASE_PERMISSION_LEGS}
    outstanding = {channel: 0 for channel, _ in c.BASE_PERMISSION_LEGS}
    for assignment in all_assignments.values():
        for channel, amount in settlement.outstanding_delta(assignment).items():
            outstanding[channel] += amount
        for channel, amount in assignment.carry_per_channel.items():
            carry[channel] += amount

    # Every seat then mints, which moves value from outstanding to issued.
    seat_ids = sorted({seat.seat_id for seat in scenario.cycle_seats()})
    marks = {seat.seat_id: seat.minted_through_window for seat in scenario.cycle_seats()}
    issued = {channel: 0 for channel, _ in c.BASE_PERMISSION_LEGS}
    for seat_id in seat_ids:
        collection = settlement.collect(seat_id, marks[seat_id], last, records)
        for channel, amount in collection.per_channel.items():
            issued[channel] += amount
            outstanding[channel] -= amount

    legs = dict(c.BASE_PERMISSION_LEGS)
    for channel in sorted(legs):
        check.equal(f"conservation.issued_atomic.{channel}", issued[channel])
        check.equal(f"conservation.outstanding_atomic.{channel}", outstanding[channel])
        check.equal(f"conservation.carry_atomic.{channel}", carry[channel])
        check.agree(
            f"conservation.assigned_atomic.{channel}",
            assigned * e.base_permission_legs()[channel],
            assigned * legs[channel],
        )
        check.equal(
            f"conservation.identity_holds.{channel}",
            issued[channel] + outstanding[channel] + carry[channel]
            == assigned * legs[channel],
        )
        # With every seat minting there is nothing left unminted, so outstanding
        # falls to zero and the carry is the only residue. A settlement defect
        # that paid a winner too much or too little would break this before it
        # broke the identity.
        check.equal(
            f"conservation.outstanding_falls_to_zero.{channel}",
            outstanding[channel] == 0,
        )
        check.equal(
            f"conservation.carry_is_the_only_residue.{channel}",
            issued[channel] + carry[channel] == assigned * legs[channel],
        )
    check.agree(
        "conservation.base_permission_total_atomic",
        sum(e.base_permission_legs().values()),
        c.BASE_PERMISSION_TOTAL,
    )
    check.equal(
        "conservation.total_assigned_atomic", assigned * c.BASE_PERMISSION_TOTAL
    )
    # The outage cycle carries a whole permission per in-span seat, which is the
    # founder-directed rule for a cycle no seat met.
    outage = all_assignments[scenario.OUTAGE_WINDOW]
    check.equal(
        "conservation.empty_winner_set_carries_everything",
        sum(outage.carry_per_channel.values())
        == outage.reallocated_count * c.BASE_PERMISSION_TOTAL,
    )


def check_split(check: Checker) -> None:
    """The split conserves every leg at every winner count, not only the fixture's."""
    for count in (0, 1, 2, 3, 7, 13, 100, 99_999):
        shares, carries = winners.split_permission(count)
        expected_shares, expected_carries = e.split_permission(count)
        check.agree(
            f"split.share_atomic.{count}.0", expected_shares[0], shares[0]
        )
        check.agree(
            f"split.remainder_atomic.{count}.0", expected_carries[0], carries[0]
        )
        check.equal(
            f"split.conserves_every_leg.{count}",
            all(
                shares[channel] * count + carries[channel] == amount
                for channel, amount in c.BASE_PERMISSION_LEGS
            ),
        )
    check.equal(
        "split.empty_set_carries_the_whole_permission",
        sum(winners.split_permission(0)[1].values()) == c.BASE_PERMISSION_TOTAL,
    )
    check.equal(
        "split.uncanonical_winner_lists_are_refused",
        all(
            _winner_refusal(candidate) == "INVALID_WINNER_SET"
            for candidate in ((4, 0), (0, 0), (c.FOUNDER_SEAT_CAPACITY,))
        ),
    )


def _winner_refusal(candidate: tuple[int, ...]) -> str:
    try:
        winners.require_canonical(candidate)
    except winners.InvalidWinnerSet:
        return "INVALID_WINNER_SET"
    return "accepted"
