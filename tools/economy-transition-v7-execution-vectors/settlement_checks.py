"""What the recovery pool did, block by block, and what it means at the end.

`trace_checks.py` records the commitments — roots, headers, receipts, results.
This module records the thing those commitments are about: where an unclaimable
remainder went, who was able to collect it, and whether anything was left over.

Every figure has an independent side in `expected.py`, which reaches the
settlement through `economy-transition-v7-vectors/expected.py` — the derivation
the hosted matrix already verified over 395 vectors — and never through the
execution model it is checking.
"""

from __future__ import annotations

import expected as e
from checker import Checker

from simulation.economy_transition_v7 import trace
from simulation.economy_transition_v7.state import decode_cycle_assignment_value


def check_pool_scenario(check: Checker, scenario) -> None:
    check.section(
        "Scenario pool: an unwon cycle fills the recovery pool, the next cycle "
        "absorbs it whole, and a mint collects both."
    )
    totals = e.pool_scenario_totals()
    ledger = scenario.ledger
    notes = scenario.notes

    check.agree("pool.dead_window", trace.DEAD_WINDOW, notes["dead_window"])
    check.agree("pool.won_window", trace.WON_WINDOW, notes["won_window"])
    _legs(check, "pool.pool_after_dead_cycle",
          totals["pool_after_dead_cycle"], notes["pool_after_dead_cycle"])
    _legs(check, "pool.outstanding_after_dead_cycle",
          totals["outstanding_after_dead_cycle"],
          {channel: notes["outstanding_after_dead_cycle"][channel]
           for channel in e.RECOVERY_POOL_LEGS})
    _legs(check, "pool.claimable_after_dead_cycle",
          totals["claimable_after_dead_cycle"], notes["claimable_after_dead_cycle"])
    check.equal(
        "pool.a_cycle_nobody_won_left_its_whole_contribution_in_the_pool",
        notes["pool_after_dead_cycle"] == totals["pool_after_dead_cycle"],
    )
    check.equal(
        "pool.a_cycle_nobody_won_owed_nobody_anything",
        all(amount == 0 for amount in notes["claimable_after_dead_cycle"].values()),
    )

    _legs(check, "pool.pool_after_mint", totals["pool_after_won_cycle"],
          notes["pool_after_mint"])
    _legs(check, "pool.outstanding_after_mint", totals["outstanding_after_mint"],
          {channel: notes["outstanding_after_mint"][channel]
           for channel in e.RECOVERY_POOL_LEGS})
    _legs(check, "pool.issued_after_mint", totals["minted"],
          {channel: notes["issued_after_mint"][channel]
           for channel in e.RECOVERY_POOL_LEGS})
    check.agree(
        "pool.minted_total_atomic",
        totals["minted_total_atomic"],
        sum(notes["issued_after_mint"][channel] for channel in e.RECOVERY_POOL_LEGS),
    )
    check.agree(
        "pool.assigned_permissions",
        totals["assigned_permissions"],
        ledger.assigned_permissions,
    )
    check.agree("pool.alice_mark", trace.WON_WINDOW, notes["alice_mark"])
    check.agree("pool.bob_mark", trace.WON_WINDOW, notes["bob_mark"])
    check.agree(
        "pool.unreferred_pool_atomic",
        totals["unreferred_pool_atomic"],
        ledger.pool_accrued,
    )
    check.agree(
        "pool.verified_user_issued_atomic",
        totals["verified_user_issued_atomic"],
        ledger.channel_issued[e.VERIFIED_USER_CHANNEL],
    )

    # The claim version seven exists to make, stated as one boolean over an
    # exact figure rather than as a comparison against version six.
    check.equal(
        "pool.every_unit_the_manifest_promised_for_these_cycles_reached_a_beneficiary",
        all(
            notes["issued_after_mint"][channel]
            == ledger.assigned_permissions * e.base_permission_legs()[channel]
            and notes["outstanding_after_mint"][channel] == 0
            and notes["pool_after_mint"][channel] == 0
            for channel in e.RECOVERY_POOL_LEGS
        ),
    )
    _check_records(check, "pool", ledger, trace.POOL_UPTIME,
                   [trace.DEAD_WINDOW, trace.WON_WINDOW], trace.DEAD_WINDOW)


def check_boundary_scenario(check: Checker, scenario) -> None:
    check.section(
        "Scenario boundary: the ordering version six rejected by argument, "
        "which version seven's own invariant refuses."
    )
    notes = scenario.notes
    refusal = notes["rejected_ordering_refusal"]
    check.equal(
        "boundary.the_rejected_ordering_produces_no_block", refusal is not None
    )
    for channel in e.RECOVERY_POOL_LEGS:
        check.equal(
            f"boundary.the_rejected_ordering_breaks_channel{channel}_backing_identity",
            refusal is not None
            and f"channel {channel} breaks the backing identity" in refusal,
        )
    check.equal(
        "boundary.the_rejected_block_preserved_the_pre_block_state",
        bool(notes["rejected_ordering_preserved_state"]),
    )
    check.agree(
        "boundary.the_accepted_ordering_issued",
        e.pool_scenario_totals()["minted_total_atomic"],
        notes["accepted_ordering_issued"],
    )
    check.equal(
        "boundary.state_root_before_the_boundary_block",
        notes["state_root_before_the_boundary_block"],
    )
    check.equal(
        "boundary.the_two_orderings_differ_by_a_whole_mint",
        notes["accepted_ordering_issued"] > 0 and refusal is not None,
    )


def check_permanence_scenario(check: Checker, scenario) -> None:
    check.section(
        "Scenario permanence: a machine past its own 731 cycles drains a pool "
        "that no cycle in the block was contributing to."
    )
    totals = e.permanence_scenario_totals()
    ledger = scenario.ledger
    notes = scenario.notes

    check.agree("permanence.stranded_window", trace.STRANDED_WINDOW,
                notes["stranded_window"])
    check.agree("permanence.drained_window", trace.DRAINED_WINDOW,
                notes["drained_window"])
    _legs(check, "permanence.pool_after_stranded_cycle",
          totals["pool_after_stranded_cycle"], notes["pool_after_stranded_cycle"])
    _legs(check, "permanence.pool_after_mint", totals["pool_after_drained_cycle"],
          notes["pool_after_mint"])
    _legs(check, "permanence.issued_after_mint", totals["minted"],
          {channel: notes["issued_after_mint"][channel]
           for channel in e.RECOVERY_POOL_LEGS})
    check.agree("permanence.carol_issued_atomic", totals["minted_total_atomic"],
                notes["carol_issued"])
    check.agree("permanence.assigned_permissions", totals["assigned_permissions"],
                ledger.assigned_permissions)
    check.equal(
        "permanence.the_drained_cycle_assigned_no_permission_at_all",
        notes["assigned_after_drained_cycle"] == notes["assigned_after_stranded_cycle"],
    )
    check.equal(
        "permanence.a_cycle_with_no_contributing_seat_still_drained_the_pool",
        all(amount == 0 for amount in notes["pool_after_mint"].values()),
    )
    check.equal(
        "permanence.the_seat_that_generated_the_permission_never_accrued_a_bit",
        notes["alice_never_accrued"] == trace.STRANDED_WINDOW - 1,
    )
    check.equal(
        "permanence.an_out_of_span_machine_collected_a_whole_base_permission",
        notes["carol_issued"] == e.base_permission_total(),
    )
    check.equal(
        "permanence.a_winner_was_outside_the_contributing_set",
        _won_outside_the_contributing_set(ledger, trace.PERMANENCE_UPTIME,
                                          trace.DRAINED_WINDOW),
    )
    _check_records(check, "permanence", ledger, trace.PERMANENCE_UPTIME,
                   [trace.STRANDED_WINDOW, trace.DRAINED_WINDOW],
                   trace.STRANDED_WINDOW)


def _check_records(check, name, ledger, uptime, windows, first_window) -> None:
    """Each written cycle assignment record, against the independent settlement.

    The pool the independent side absorbs is the one it derived for the previous
    cycle, so the chain of records is reproduced from the first window forward
    rather than read back out of the ledger one at a time.

    **The marks come from the fixture, not from the ledger.** Every seat is
    activated at a height inside the window before the first assignable one, so
    its mark is that window; both mints in each scenario execute in the block
    that writes the second record, and the prologue runs before a block's
    transactions, so no mark has moved at either assignment. Reading the marks
    back out of the model would make the record agree with itself.
    """
    mark = first_window - 1
    pool = {channel: 0 for channel in e.RECOVERY_POOL_LEGS}
    for window in windows:
        seats = [
            {
                "seat_id": seat.seat_id,
                "uptime": seat.uptime_seconds,
                "in_span": seat.in_span,
                "mark": mark,
                "window": window,
            }
            for seat in uptime[window]
        ]
        derived = e.assign(seats, pool)
        pool = derived["pool_after"]
        bits = max(seat["seat_id"] for seat in seats) + 1
        raw = ledger.assignments[window]
        decoded = decode_cycle_assignment_value(raw)
        prefix = f"{name}.window{window}"
        check.agree(f"{prefix}.winner_count", derived["winner_count"],
                    decoded["winner_count"])
        check.agree(f"{prefix}.reallocated_count", derived["reallocated"],
                    decoded["reallocated_count"])
        check.agree(f"{prefix}.in_scope_count", len(seats), decoded["in_scope_count"])
        check.agree(f"{prefix}.bitmap_bits", bits, decoded["bitmap_bits"])
        # The two seat sets and the pool the cycle leaves behind are reachable
        # only from the independent derivation — the record commits to what was
        # absorbed, not to what remains — so they are recorded from one source
        # and pinned rather than agreed. What binds them to the model is the
        # encoded record below, whose next window absorbs exactly this pool.
        check.equal(f"{prefix}.contributing_count", derived["assigned"])
        check.equal(f"{prefix}.eligible_count", len(derived["eligible"]))
        for channel in e.RECOVERY_POOL_LEGS:
            check.equal(f"{prefix}.pool_after.channel{channel}",
                        derived["pool_after"][channel])
        _legs(check, f"{prefix}.pool_absorbed", derived["pool_absorbed"],
              decoded["pool_absorbed"])
        check.agree(
            f"{prefix}.record",
            e.cycle_assignment_value_hex(
                derived["share"][e.FOUNDER_OPERATOR_CHANNEL],
                derived["reallocated"],
                derived["winner_count"],
                len(seats),
                bits,
                derived["pool_absorbed"],
                derived["accrued"],
                derived["winners"],
            ),
            raw.hex(),
        )
        check.equal(
            f"{prefix}.absorbed_before_the_cycle_contributed_its_own_dust",
            all(
                decoded["pool_absorbed"][channel] == derived["pool_before"][channel]
                if derived["winner_count"]
                else decoded["pool_absorbed"][channel] == 0
                for channel in e.RECOVERY_POOL_LEGS
            ),
        )


def _won_outside_the_contributing_set(ledger, uptime, window: int) -> bool:
    """The rule ADR 0049 states and version seven guards: rule 3, in one line.

    A winner bit is set for a seat that is not in the cycle's contributing set,
    so the cycle paid a machine past its own 731 issuance cycles out of a pool
    no seat in that cycle contributed to.
    """
    from simulation.economy_transition_v7.state import bit_is_set

    decoded = decode_cycle_assignment_value(ledger.assignments[window])
    contributing = {seat.seat_id for seat in uptime[window] if seat.in_span}
    winners = {
        seat.seat_id
        for seat in uptime[window]
        if bit_is_set(decoded["winner_bitmap"], seat.seat_id)
    }
    return bool(winners) and not (winners & contributing)


def _legs(check: Checker, key: str, closed_form: dict, live: dict) -> None:
    for channel in e.RECOVERY_POOL_LEGS:
        check.agree(f"{key}.channel{channel}", closed_form[channel], live[channel])
