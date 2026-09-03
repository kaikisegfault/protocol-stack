"""The claims that are version eight's own: the carrier, in motion.

Everything here is a fact about a chain that audited its own machines. The
settlement each fact ends in is checked against the accepted **version-seven**
derivation rather than against version eight's model, which is the only way "the
carrier changed no settlement" can be evidence rather than an assertion version
eight makes about itself.

Three claims are cross-checked from two directions rather than one:

* a seat's lost slots, from the window record the chain wrote and from the log of
  the challenges it was actually issued;
* the winner set, from the assignment record read back out of state and from
  version seven's settlement over an independently stated seat list;
* the deadline, from an accepted response at `c + 20` and a refused one at
  `c + 21` on copies of one chain.
"""

from __future__ import annotations

import expected as e
from checker import Checker

from simulation.economy_transition_v8 import contract as c
from simulation.economy_transition_v8.state import decode_cycle_assignment_value


def check_measured_window(check: Checker, scenario) -> None:
    """A window the chain measured itself, and the reward it paid from it."""
    notes = scenario.notes
    ledger = scenario.ledger
    bob_slots = notes["bob_credited_slots"]

    check.section(
        "The measured window: two machines audited block by block, and the "
        "first node reward in this repository derived from evidence the chain "
        "recorded rather than from a schedule it was handed."
    )
    check.equal("measured.heights_executed", notes["quiet_heights"])
    check.equal("measured.blocks_carrying_a_response", notes["audit_blocks"])
    check.equal("measured.alice_challenges_issued", notes["alice_challenges"])
    check.equal("measured.alice_challenges_answered", notes["alice_answered"])
    check.equal("measured.alice_answered_every_challenge", notes["alice_unanswered"] == 0)
    check.agree(
        "measured.every_offered_response_was_accepted",
        notes["alice_answered"],
        notes["responses_accepted"],
    )
    # The founder answer of 2026-09-02, at the scale it was answered for: a
    # machine proving a whole window's uptime paid nothing at all.
    check.equal("measured.responses_charged_no_fee", notes["response_fees_charged"] == 0)

    check.equal(
        "measured.a_machine_that_answers_everything_writes_no_record",
        notes["alice_has_no_window_record"],
    )
    check.equal("measured.bob_challenges_issued", notes["bob_challenges"])
    # A seat the chain sold that never ran. It is in no window's scope, so the
    # issue step must not audit it and the derived schedule must not name it —
    # and its default activation height of zero would put it inside every window
    # if activation were not checked.
    check.equal(
        "measured.an_unactivated_seat_is_never_audited",
        notes["the_unactivated_seat_was_never_audited"],
    )
    check.equal(
        "measured.an_unactivated_seat_is_not_in_the_derived_schedule",
        notes["the_unactivated_seat_is_not_in_the_schedule"],
    )
    check.equal("measured.bob_credited_slots", bob_slots)
    check.equal("measured.bob_lost_slots", notes["bob_lost_slots"])
    check.equal(
        "measured.bob_lost_exactly_the_slots_he_was_audited_in",
        notes["bob_lost_exactly_the_slots_he_was_audited_in"],
    )
    check.equal(
        "measured.every_challenge_expired_inside_its_own_slot",
        notes["every_challenge_expired_in_its_own_slot"],
    )
    check.agree(
        "measured.bob_failed_the_cycle",
        bob_slots * e.SLOT_SECONDS < e.ACTIVITY_THRESHOLD_SECONDS,
        e.uptime_seconds(_credited_bitmap(bob_slots), 0)
        < e.ACTIVITY_THRESHOLD_SECONDS,
    )

    totals = e.measured_totals(bob_slots)
    check.equal("measured.assigned_window", notes["assigned_window"])
    check.agree(
        "measured.winner_set", list(totals["winners"]), list(ledger.winners_of(1))
    )
    check.agree(
        "measured.accrued_set",
        list(totals["accrued"]),
        _accrued_of(ledger, e.MEASURED_WINDOW),
    )
    check.agree(
        "measured.reallocated_count",
        totals["reallocated"],
        decode_cycle_assignment_value(ledger.assignments[1])["reallocated_count"],
    )
    check.agree(
        "measured.assigned_permissions",
        totals["assigned_permissions"],
        ledger.assigned_permissions,
    )
    check.agree(
        "measured.alice_minted_atomic",
        totals["alice_minted_atomic"],
        _issued_by(scenario, "alice_mints_her_measured_cycle"),
    )
    check.agree(
        "measured.alice_referral_atomic",
        totals["alice_referral_atomic"],
        _issued_by(scenario, "alice_mints_her_referral_leg"),
    )
    check.agree(
        "measured.unreferred_pool_atomic",
        totals["unreferred_pool_atomic"],
        ledger.pool_accrued,
    )
    check.equal(
        "measured.the_recovery_pool_is_empty_after_the_mint",
        all(amount == 0 for amount in notes["pool_after_mint"].values()),
    )

    check.equal(
        "measured.the_due_window_records_were_deleted_by_the_prologue",
        notes["window_one_records_were_deleted"],
    )
    check.equal(
        "measured.retained_windows_are_inside_the_executing_window_and_the_one_before",
        all(
            window in (ledger.height // e.CYCLE_BLOCKS, ledger.height // e.CYCLE_BLOCKS - 1)
            for window in notes["retained_window_span"]
        ),
    )
    check.equal(
        "measured.issuing_before_the_prologue_commits_the_same_root",
        notes["issue_before_prologue_commits_the_same_root"],
    )
    check.equal(
        "measured.issuing_before_the_prologue_assigns_the_same_window",
        notes["issue_before_prologue_assigns_the_same_window"],
    )
    check.equal(
        "measured.the_two_steps_touch_windows_two_apart",
        e.ASSIGNMENT_LAG_WINDOWS == 2,
    )


def check_dispute_moves_the_winner_set(check: Checker, scenario) -> None:
    """Six voided slots, a seat that still meets its cycle, and a moved winner set."""
    notes = scenario.notes
    check.section(
        "The dispute: what an ecosystem AI's judgment can and cannot do to a "
        "machine, run against the counterfactual chain that had none filed."
    )
    check.equal("disputed.alice_challenges_issued", notes["alice_challenges"])
    check.equal("disputed.bob_challenges_issued", notes["bob_challenges"])
    check.equal(
        "disputed.both_machines_were_perfect_before_the_dispute",
        notes["no_window_records_before_the_dispute"],
    )
    check.equal("disputed.responses_charged_no_fee", notes["response_fees_charged"] == 0)

    check.equal("disputed.accepted_disputes", notes["alice_disputed_bits"])
    check.agree(
        "disputed.the_cap_is_the_founder_directed_grace_allowance",
        e.DISPUTE_CAP_SLOTS_PER_SEAT,
        notes["alice_disputed_bits"],
    )
    check.equal(
        "disputed.a_dispute_does_not_clear_a_credited_bit",
        notes["alice_credited_bits"] == e.SLOTS_PER_WINDOW,
    )
    check.agree(
        "disputed.alice_final_slots",
        e.credited_slots(e.all_slots_credited(), (1 << e.DISPUTE_CAP_SLOTS_PER_SEAT) - 1),
        notes["alice_final_slots"],
    )
    check.agree(
        "disputed.alice_uptime_seconds",
        e.containment_uptime_seconds(),
        notes["alice_uptime_seconds"],
    )
    # The containment theorem with its margin stated: a maximal dispute leaves a
    # fully credited seat exactly at the threshold and never below it.
    check.equal(
        "disputed.a_maximal_dispute_leaves_a_perfect_seat_at_the_threshold",
        e.containment_uptime_seconds() == e.ACTIVITY_THRESHOLD_SECONDS,
    )
    check.equal(
        "disputed.alice_still_meets_her_cycle",
        notes["alice_meets_her_cycle_after_a_maximal_dispute"],
    )

    check.agree(
        "disputed.winners_with_the_dispute",
        list(e.disputed_winners(e.DISPUTE_CAP_SLOTS_PER_SEAT)),
        notes["winners_with_the_dispute"],
    )
    check.agree(
        "disputed.winners_without_the_dispute",
        list(e.disputed_winners(0)),
        notes["winners_without_the_dispute"],
    )
    check.equal(
        "disputed.the_dispute_moved_the_winner_set",
        notes["winners_with_the_dispute"] != notes["winners_without_the_dispute"],
    )
    check.equal(
        "disputed.the_disputed_seat_lost_only_its_place_in_the_winner_set",
        e.ALICE_SEAT in notes["winners_without_the_dispute"]
        and e.ALICE_SEAT not in notes["winners_with_the_dispute"]
        and notes["alice_meets_her_cycle_after_a_maximal_dispute"],
    )


def check_deadline(check: Checker, scenario) -> None:
    """The one execution ordering a chain can observe, from both sides of it."""
    notes = scenario.notes
    on_time = notes["response_at_the_deadline"]
    late = notes["response_one_height_late"]
    rejected = notes["response_under_the_rejected_order"]
    challenge = notes["challenge_height"]

    check.section(
        "The deadline: the expiry step follows the transactions, so the last "
        "admissible response arrives in block c + 20 and the rejected order "
        "costs the seat the slot it had just proved."
    )
    check.equal("deadline.challenge_height", challenge)
    check.equal("deadline.challenge_slot", notes["challenge_slot"])
    check.equal(
        "deadline.the_challenge_was_issued_at_a_challengeable_height",
        e.is_challengeable_height(challenge),
    )
    check.equal(
        "deadline.a_response_in_the_issuing_block_is_not_open",
        notes["same_block_result"] == "CHALLENGE_NOT_OPEN",
    )
    check.agree(
        "deadline.response_height_at_the_deadline",
        challenge + e.RESPONSE_DEADLINE_BLOCKS,
        on_time["height"],
    )
    check.equal("deadline.response_at_the_deadline_is_accepted", on_time["result"])
    check.equal(
        "deadline.the_seat_keeps_every_slot_when_it_answers_in_time",
        on_time["credited_slots_after"] == e.SLOTS_PER_WINDOW,
    )
    check.agree(
        "deadline.response_height_one_past_the_deadline",
        challenge + e.RESPONSE_DEADLINE_BLOCKS + 1,
        late["height"],
    )
    check.equal("deadline.response_one_height_late_is_refused", late["result"])
    check.equal(
        "deadline.the_slot_was_already_lost_one_height_past_the_deadline",
        late["credited_slots_before"] == e.SLOTS_PER_WINDOW - 1,
    )
    check.equal(
        "deadline.the_late_response_finds_no_open_challenge",
        not late["challenge_survives"],
    )
    # The rejected reading, run on an identical copy of the same chain.
    check.equal(
        "deadline.expiring_before_the_transactions_refuses_the_same_response",
        rejected["result"] == "CHALLENGE_NOT_ISSUED",
    )
    check.equal(
        "deadline.expiring_before_the_transactions_costs_the_seat_a_slot",
        rejected["credited_slots_before"] - rejected["credited_slots_after"] == 1,
    )
    check.equal(
        "deadline.the_accepted_order_costs_the_same_seat_nothing",
        on_time["credited_slots_before"] == on_time["credited_slots_after"],
    )


def check_kind_coverage(check: Checker, scenarios: list) -> None:
    """Every kind version eight admits is executed somewhere in this file."""
    check.section("Coverage: every transaction kind version eight admits.")
    reached = set()
    for scenario in scenarios:
        for block in list(scenario.blocks) + list(scenario.audit_blocks):
            for entry in block.executed:
                reached.add(entry.kind)
    check.equal("coverage.kinds_executed", len(reached))
    check.equal(
        "coverage.every_kind_version_eight_admits_is_executed",
        reached == set(e.KIND_NUMBERS),
    )
    check.equal(
        "coverage.the_two_kinds_version_eight_adds_are_among_them",
        {c.CHALLENGE_RESPONSE, c.FILE_DISPUTE} <= reached,
    )


def check_determinism(check: Checker, scenarios: list) -> None:
    """The same fixture, executed twice, commits to the same roots.

    A model that read a clock, a hash seed, or an unordered iteration would
    disagree with itself here, which is the one defect no amount of independent
    derivation would ever notice. It matters more under version eight than under
    any predecessor: selection is a digest over a state root, so a projection
    whose iteration order wandered would change *who gets audited* and not merely
    what a commitment reads.
    """
    from simulation.economy_transition_v8 import trace

    check.section("Determinism: the same inputs commit to the same roots twice.")
    rebuilt = {maker.__name__.removesuffix("_scenario"): maker()[0]
               for maker in trace.SCENARIOS}
    for scenario in scenarios:
        again = rebuilt[scenario.name]
        check.equal(
            f"determinism.{scenario.name}_reproduces_every_block_id",
            [block.block_id for block in scenario.blocks]
            == [block.block_id for block in again.blocks],
        )
        check.equal(
            f"determinism.{scenario.name}_reproduces_the_final_state_root",
            scenario.ledger.state_root() == again.ledger.state_root(),
        )
        check.equal(
            f"determinism.{scenario.name}_audits_the_same_heights_twice",
            [block.height for block in scenario.audit_blocks]
            == [block.height for block in again.audit_blocks],
        )


def _credited_bitmap(slots: int) -> int:
    return (1 << slots) - 1


def _accrued_of(ledger, window: int) -> list[int]:
    from simulation.economy_transition_v3.state import bit_is_set

    decoded = decode_cycle_assignment_value(ledger.assignments[window])
    packed = decoded["accrued_bitmap"]
    return [
        seat for seat in range(decoded["bitmap_bits"]) if bit_is_set(packed, seat)
    ]


def _issued_by(scenario, label: str) -> int:
    for block, labels in zip(scenario.blocks, scenario.labels):
        for name, entry in zip(labels, block.executed):
            if name == label:
                return entry.outcome.issued_atomic
    raise KeyError(label)
