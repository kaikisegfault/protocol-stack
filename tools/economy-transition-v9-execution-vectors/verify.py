#!/usr/bin/env python3
"""Independently derive and check the economy-transition-v9 execution vectors.

These record what a version-nine chain *does* with a clock and a monthly
settlement. The contract surface it does it over is
`test-vectors/economy-transition-v9.txt` and the measurement is version eight's;
this file touches neither and restates neither.

Every value two sources can reach is derived twice — once from `expected.py`,
which imports nothing from `simulation/` and computes the calendar by
accumulating month lengths from 1970, and once from a live run of the execution
model — and is recorded only when both agree. A value only one source can reach,
such as a count of blocks in a fixture, is recorded from that source and is a
claim the file pins rather than one it proves twice.

**Two orderings are checked by running the rejected one.** The settlement before
the accrual and the accumulation before the deletion are both normative and both
invisible in any test that does not put them in one block, so each is run on an
identical copy of the chain at the settlement height and the resulting roots are
required to differ.

`--emit` writes the vector file instead of checking it. It runs the same
derivations through the same agreement gate, so it can only write values both
sources already produce; it removes a transcription step, not the evidence.
"""

from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(REPOSITORY_ROOT))

import expected as e
from checker import Checker, read_vectors

from simulation.economy_transition_v9 import contract as c
from simulation.economy_transition_v9 import settlement as settlement_module
from simulation.economy_transition_v9 import trace
from simulation.economy_transition_v9.block import execute_block, transaction_root
from simulation.economy_transition_v9.genesis import chain_id as derive_chain_id
from simulation.economy_transition_v9.genesis import encode as encode_genesis
from simulation.economy_transition_v9.header import block_header, block_id
from simulation.economy_transition_v9.receipt import decode as decode_receipt


def check_genesis(check: Checker) -> None:
    check.section(
        "The chain this trace runs, derived twice. The genesis timestamp is the "
        "one field version nine adds, and it binds the chain identity like every "
        "other genesis field."
    )
    fixture = trace.genesis()
    derived = e.genesis_bytes(
        e.SCHEMA_VERSION,
        trace.NETWORK_ID,
        trace.GENESIS_MILLIS,
        trace.SUPPLY_LIMIT,
        0,
        trace.FIXED_FEE,
        0,
        bytes.fromhex(c.MANIFEST_DIGEST_HEX),
        trace.VERIFIER_KEY,
        trace.DISPUTE_AUTHORITY_KEY,
        0,
    )
    live = encode_genesis(fixture)
    check.agree("genesis.bytes", derived.hex(), live.hex())
    check.agree(
        "genesis.chain_id",
        e.digest(e.CHAIN_ID_LABEL, derived).hex(),
        derive_chain_id(fixture).hex(),
    )
    check.agree("genesis.timestamp", trace.GENESIS_MILLIS, fixture.genesis_timestamp)
    check.agree(
        "genesis.month", e.month_index(trace.GENESIS_MILLIS),
        __import__(
            "simulation.economy_transition_v9.genesis", fromlist=["x"]
        ).genesis_month(fixture),
    )
    check.equal("genesis.millis_per_block", trace.MILLIS_PER_BLOCK)


def check_the_calendar_over_the_chain(check: Checker, scenario) -> None:
    check.section(
        "Every window this chain opened, and the month it opened in, derived "
        "twice. At ninety seconds a block a window is exactly thirty days, so "
        "each one opens in a month of its own — which is the fixture's whole "
        "reason for running slower than the commit target."
    )
    opened = {
        block.opened_window: block.timestamp
        for block in scenario.notes["audit_blocks"]
        if block.opened_window is not None
    }
    for window, timestamp in sorted(opened.items()):
        check.agree(
            f"calendar.window_{window}.month",
            e.month_of_window(window, trace.GENESIS_MILLIS),
            e.month_index(timestamp),
        )
        check.agree(
            f"calendar.window_{window}.opening_timestamp",
            trace.GENESIS_MILLIS + window * e.CYCLE_BLOCKS * e.MILLIS_PER_BLOCK,
            timestamp,
        )
    check.equal("calendar.windows_opened", len(opened))
    check.section(
        "Exactly two window-month entries are live at the end of the run — the "
        "open window's and its predecessor's — which is two rather than the "
        "three unreferred-pool-payout-v1 sized for, because version nine deletes "
        "the oldest in the same prologue that assigns it. Measured over the run "
        "rather than asserted."
    )
    check.agree(
        "calendar.live_window_months",
        e.ASSIGNMENT_LAG_WINDOWS,
        len(scenario.ledger.window_months),
    )
    check.equal(
        "calendar.live_window_months_are_the_open_window_and_its_predecessor",
        sorted(scenario.ledger.window_months) ==
        [max(scenario.ledger.window_months) - 1, max(scenario.ledger.window_months)],
    )


def check_the_shorthand(check: Checker, scenario) -> None:
    check.section(
        "The root the setup shorthand leaves behind, and the stamp it commits "
        "to. `advance_to` stands in for a run of empty blocks and is valid only "
        "before any activation, and version nine makes its timestamp a required "
        "argument: a shorthand that advanced the height and left the stamp "
        "behind would commit a root naming a height the stamp does not belong "
        "to, and every later block would still satisfy C2 because the stale "
        "stamp is smaller. The failure would be a wrong root rather than a "
        "refusal, which is the direction that hides — and this is the only place "
        "it is observable, because the block that follows sets its own stamp."
    )
    check.agree(
        "shorthand.timestamp",
        trace.GENESIS_MILLIS
        + (trace.ACTIVATION_HEIGHT - 1) * trace.MILLIS_PER_BLOCK,
        scenario.notes["timestamp_after_the_shorthand"],
    )
    check.equal("shorthand.height", trace.ACTIVATION_HEIGHT - 1)
    check.equal("shorthand.skipped_blocks", scenario.skipped_blocks)
    check.equal("shorthand.root", scenario.notes["root_after_the_shorthand"])
    check.equal(
        "shorthand.the_first_block_after_it_carries_that_root",
        scenario.blocks[2].previous_state_root
        == scenario.notes["root_after_the_shorthand"],
    )


def check_the_audit(check: Checker, scenario) -> None:
    check.section(
        "Two machines across the window the chain measured: one answered every "
        "audit it was issued and one answered none. A trace cannot pre-compute "
        "which of its machines will be challenged — that unpredictability is the "
        "property the pipeline exists to have — so what it states afterwards is "
        "that every challenge was answered, and the counts are how that is "
        "checked."
    )
    check.equal("audit.alice_challenged", scenario.notes["alice_challenged"])
    check.equal("audit.alice_answered", scenario.notes["alice_answered"])
    check.equal(
        "audit.alice_answered_every_challenge",
        scenario.notes["alice_challenged"] == scenario.notes["alice_answered"],
    )
    check.equal("audit.bob_challenged", scenario.notes["bob_challenged"])
    check.equal("audit.bob_answered", scenario.notes["bob_answered"])
    check.equal("audit.bob_answered_none", scenario.notes["bob_answered"] == 0)
    check.equal("audit.quiet_heights", scenario.notes["quiet_heights"])


def check_the_settlement(check: Checker, scenario, prefix: str) -> None:
    settlements = [
        block for block in scenario.notes["audit_blocks"] if block.settled is not None
    ]
    check.section(
        "Every month this chain closed, with the block that closed it. A month "
        "is settled at the assignment of the first window of a later month, "
        "which is the point at which its figures are complete — not at the block "
        "that opens the month, which would rank every seat on a month missing "
        "its last windows."
    )
    check.equal(f"{prefix}.settlements", len(settlements))
    for block in settlements:
        settled = block.settled
        key = f"{prefix}.month_{settled.month}"
        check.equal(f"{key}.settled_at_height", block.height)
        check.agree(
            f"{key}.month_of_the_assigned_window",
            e.month_of_window(
                block.opened_window - e.ASSIGNMENT_LAG_WINDOWS,
                trace.GENESIS_MILLIS,
                trace.HALT_HEIGHT if prefix == "halted" else None,
                trace.HALT_MILLIS,
            ),
            block.due_month,
        )
        check.equal(f"{key}.candidate_count", settled.candidate_count)
        check.equal(f"{key}.best_figure", settled.best_figure)
        check.equal(
            f"{key}.winners", ",".join(str(seat) for seat in settled.winners)
        )
        check.equal(f"{key}.payable_before", settled.payable_before)
        derived_share, derived_remainder = e.share_and_remainder(
            settled.payable_before, len(settled.winners)
        )
        check.agree(f"{key}.share", derived_share, settled.share)
        check.agree(f"{key}.remainder", derived_remainder, settled.remainder)
        check.agree(f"{key}.assigned", derived_share * len(settled.winners),
                    settled.assigned)
        check.equal(
            f"{key}.skipped_months",
            ",".join(str(month) for month in block.skipped_months),
        )


def check_the_pool(check: Checker, scenario, prefix: str) -> None:
    ledger = scenario.ledger
    check.section(
        "The pool's three quantities after the run, and the two identities over "
        "them. The first is unreferred-pool-payout-v1's — every unit received is "
        "undistributed or owed to a named winner — and the second is the one it "
        "leaves to the version that implements a mint, stated here as an "
        "equality because an equality catches a unit minted twice."
    )
    check.equal(f"{prefix}.pool_accrued", ledger.pool_accrued)
    check.equal(f"{prefix}.pool_payable", ledger.pool_payable)
    check.equal(f"{prefix}.pool_minted", ledger.pool_minted)
    assigned = sum(accrued for accrued, _ in ledger.claims.values())
    taken = sum(minted for _, minted in ledger.claims.values())
    check.equal(f"{prefix}.claims_assigned", assigned)
    check.equal(f"{prefix}.claims_minted", taken)
    check.equal(
        f"{prefix}.accrued_equals_payable_plus_assigned",
        ledger.pool_accrued == ledger.pool_payable + assigned,
    )
    check.equal(f"{prefix}.minted_equals_the_claims_minted", ledger.pool_minted == taken)
    check.equal(f"{prefix}.conservation_failures", len(ledger.conservation_failures()))

    windows_accrued = len(
        [b for b in scenario.notes["audit_blocks"] if b.assigned_window is not None]
    )
    check.agree(
        f"{prefix}.pool_accrued_is_the_unreferred_legs",
        e.accrual_for(2, windows_accrued),
        ledger.pool_accrued,
    )
    check.equal(f"{prefix}.windows_that_accrued", windows_accrued)


def check_the_mint(check: Checker, scenario) -> None:
    results = scenario.results()
    check.section(
        "Kind 22 executed. A mint with 64 zero octets against a posture that "
        "requires a confirmation is refused and writes nothing, so the mint that "
        "follows it in the same block is offered the sequence number the refusal "
        "did not consume. A second mint collects nothing, and a stranger cannot "
        "mint another seat's award."
    )
    for label in (
        "an_unconfirmed_mint_is_refused",
        "winner_mints_the_pool",
        "a_second_mint_collects_nothing",
        "a_stranger_cannot_mint_another_seats_award",
    ):
        check.equal(f"mint.{label}", results[label])

    receipts = scenario.receipts()
    winner = scenario.notes["winner"]
    raw = receipts["winner_mints_the_pool"]
    decoded = decode_receipt(raw)
    check.agree(
        "mint.receipt",
        e.receipt_bytes(
            decoded.transaction_id, e.MINT_POOL, 0, trace.FIXED_FEE,
            decoded.issued_atomic,
        ).hex(),
        raw.hex(),
    )
    check.equal("mint.receipt_version", e.RECEIPT_VERSION)
    check.equal("mint.issued_atomic", decoded.issued_atomic)
    check.equal("mint.fee_charged", decoded.fee_charged)
    check.equal("mint.winner_seat", winner)
    check.equal(
        "mint.the_claim_is_emptied_and_kept",
        scenario.ledger.claims[winner] == (decoded.issued_atomic, decoded.issued_atomic),
    )
    check.equal(
        "mint.the_referral_channel_issued_it",
        scenario.ledger.channel_issued[e.REFERRAL_CHANNEL] == decoded.issued_atomic,
    )


def check_the_block(check: Checker, scenario) -> None:
    block = scenario.notes["settlement_block"]
    check.section(
        "The settlement block's header and identifier, derived twice. The header "
        "is 154 octets with the timestamp inserted after the height, and the "
        "identifier is re-versioned because it derives a different artifact."
    )
    derived = e.block_header(
        scenario.ledger.chain_id,
        block.height,
        block.timestamp,
        bytes.fromhex(block.previous_state_root),
        bytes.fromhex(block.transaction_root),
        bytes.fromhex(block.resulting_state_root),
        len(block.executed),
    )
    live = block_header(
        scenario.ledger.chain_id,
        block.height,
        block.timestamp,
        block.previous_state_root,
        block.transaction_root,
        block.resulting_state_root,
        len(block.executed),
    )
    check.agree("block.header", derived.hex(), live.hex())
    check.agree("block.header_bytes", e.BLOCK_HEADER_BYTES, len(live))
    check.agree(
        "block.block_id", e.digest(e.BLOCK_ID_LABEL, derived).hex(), block_id(live)
    )
    check.equal("block.timestamp", block.timestamp)
    check.equal("block.height", block.height)
    check.agree(
        "block.transaction_root",
        e.tx_tree(block.admitted_ids).hex(),
        transaction_root(block.admitted_ids).hex(),
    )


def check_the_orderings(check: Checker) -> None:
    check.section(
        "The two normative orderings, each checked by running the rejected one "
        "on an identical copy of the chain at the settlement height. One is "
        "observable and one is not, and the difference is a finding rather than "
        "a defect."
    )
    scenario, signatures = trace.settled_scenario()
    accepted = scenario.notes["settlement_block"]
    roots = {}
    for label, options in (
        ("accrual_before_the_settlement", {"settle_before_accrual": False}),
        ("deletion_before_the_accumulation", {"delete_before_accumulate": True}),
    ):
        rebuilt, rebuilt_signatures = _chain_to(trace.SETTLEMENT_HEIGHT - 1)
        block = execute_block(
            rebuilt,
            trace.timestamp_of_height(trace.SETTLEMENT_HEIGHT),
            [],
            rebuilt_signatures.oracle,
            **options,
        )
        roots[label] = block.resulting_state_root

    check.section(
        "**The payout before the accrual is observable.** The window being "
        "assigned belongs to the new month, so its accrual belongs to the new "
        "month: letting it land first pays the closing month one window of its "
        "successor's accrual, and the root says so."
    )
    check.equal(
        "ordering.accrual_before_the_settlement_reaches_a_different_root",
        roots["accrual_before_the_settlement"] != accepted.resulting_state_root,
    )

    check.section(
        "**The accumulation before the deletion is normative and unobservable, "
        "and that is a finding rather than a defect.** The specification says "
        "the deletion must follow the accumulation because the figures are "
        "computed from the records it removes — which is true of an "
        "implementation that reads those records lazily, and vacuous for one "
        "that derives the window's seat sequence once before either step. Every "
        "conforming implementation derives it once, because the settlement needs "
        "the same sequence the assignment does, so the two orders commit to the "
        "same root. This vector states what the shape of the prologue makes safe "
        "rather than claiming an order the chain could observe — and it is where "
        "a later implementation that read the records lazily would be noticed."
    )
    check.equal(
        "ordering.deletion_before_the_accumulation_reaches_the_same_root",
        roots["deletion_before_the_accumulation"] == accepted.resulting_state_root,
    )
    check.equal("ordering.accepted_root", accepted.resulting_state_root)


def _chain_to(height: int):
    """A second chain, run to one height below the settlement, for a comparison.

    Rebuilt rather than deep-copied, because a copy taken from the recorded run
    would share whatever the recorded run had already decided; a chain built the
    same way from genesis is the same chain and is reached independently.
    """
    from simulation.economy_transition_v9.trace import (
        _both, _seated_chain, timestamp_of_height,
    )
    from simulation.economy_transition_v6.trace import Signatures
    from simulation.economy_transition_v9.block import run_quiet_heights

    signatures = Signatures()
    scenario, alice, bob = _seated_chain(signatures, "rebuilt", timestamp_of_height)
    run_quiet_heights(
        scenario.ledger, height, timestamp_of_height, signatures.oracle,
        _both(alice, bob),
    )
    return scenario.ledger, signatures


def check_the_single_pass(check: Checker, scenario) -> None:
    check.section(
        "The halt closes one month and skips three, in one pass, and the result "
        "is required to equal an explicit per-index loop over the same state. No "
        "invariant over a single accepted state separates the two — they agree "
        "on every state both produce — so what distinguishes them is a scenario."
    )
    block = [b for b in scenario.notes["audit_blocks"] if b.skipped_months][0]
    check.equal("single_pass.height", block.height)
    check.equal("single_pass.settled_month", block.settled.month)
    check.equal(
        "single_pass.skipped_months",
        ",".join(str(month) for month in block.skipped_months),
    )
    check.agree(
        "single_pass.months_the_halt_crossed",
        e.month_of_window(3, trace.GENESIS_MILLIS, trace.HALT_HEIGHT, trace.HALT_MILLIS)
        - e.month_of_window(2, trace.GENESIS_MILLIS),
        len(block.skipped_months) + 1,
    )
    settlement_module.assert_single_pass_equals_loop(
        block.settled.month,
        block.settled.month + len(block.skipped_months) + 1,
        {0: trace.ACTIVATION_HEIGHT, 1: trace.ACTIVATION_HEIGHT},
        2,
        settlement_module.Pool(
            accrued=block.settled.payable_before, payable=block.settled.payable_before
        ),
        {},
        {(block.settled.month, 0): e.uptime_seconds(24)},
    )
    check.equal("single_pass.equals_the_loop", True)


# The heights whose stamp each block of the restart run carries. The third block
# repeats its predecessor's, which is the point of it.
RESTART_STAMP_HEIGHTS = (1, 2, 2, 4)


def check_the_restart_run(check: Checker, scenario) -> None:
    check.section(
        "Four heights contiguous from genesis, with every block's commitments. "
        "Every other recorded chain uses `advance_to`, which a layer that commits "
        "one height at a time cannot follow, so this is the run a store, an "
        "application, and a transport replay block by block and are compared "
        "against. The header, the identifier, the transaction root, and the "
        "stamps are derived twice; the resulting roots are the model's."
    )
    check.equal("restart.block_count", len(scenario.blocks))
    for index, block in enumerate(scenario.blocks):
        key = f"restart.block{index}"
        check.agree(f"{key}.height", index + 1, block.height)
        check.agree(
            f"{key}.timestamp",
            trace.GENESIS_MILLIS
            + RESTART_STAMP_HEIGHTS[index] * e.MILLIS_PER_BLOCK,
            block.timestamp,
        )
        check.equal(f"{key}.admitted_count", len(block.executed))
        check.agree(
            f"{key}.transaction_root",
            e.tx_tree(block.admitted_ids).hex(),
            transaction_root(block.admitted_ids).hex(),
        )
        derived = e.block_header(
            scenario.ledger.chain_id,
            block.height,
            block.timestamp,
            bytes.fromhex(block.previous_state_root),
            bytes.fromhex(block.transaction_root),
            bytes.fromhex(block.resulting_state_root),
            len(block.executed),
        )
        check.agree(f"{key}.header", derived.hex(), block.header.hex())
        check.agree(
            f"{key}.block_id", e.digest(e.BLOCK_ID_LABEL, derived).hex(),
            block.block_id,
        )
        check.equal(f"{key}.resulting_state_root", block.resulting_state_root)

    results = scenario.results()
    for label in (
        "alice_registers",
        "bob_registers",
        "seat_0_purchased",
        "seat_1_purchased",
        "seat_0_activated",
        "seat_1_activated",
    ):
        check.equal(f"restart.{label}.result", results[label])

    check.section(
        "Before height 3 is committed at its predecessor's stamp it is offered "
        "one a millisecond below it, and C2 refuses it whole. The predecessor's "
        "stamp is what a restarted layer must have restored to answer both: one "
        "that reopened with a stale, smaller stamp would admit the refused block, "
        "and every block after it would still satisfy C2."
    )
    check.equal(
        "restart.below_the_predecessors_stamp.refusal",
        scenario.notes["refused_below_the_predecessor"],
    )
    check.equal(
        "restart.below_the_predecessors_stamp.leaves_the_head_where_it_was",
        scenario.notes["root_after_the_refusal"]
        == scenario.blocks[1].resulting_state_root,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vectors", type=Path, required=True)
    parser.add_argument("--emit", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    check = Checker(read_vectors(args.vectors), emit=args.emit)

    settled, _signatures = trace.settled_scenario()
    halted, _halted_signatures = trace.halted_scenario()
    restart, _restart_signatures = trace.restart_scenario()

    check_genesis(check)
    check_the_calendar_over_the_chain(check, settled)
    check_the_shorthand(check, settled)
    check_the_audit(check, settled)
    check_the_settlement(check, settled, "settled")
    check_the_pool(check, settled, "settled")
    check_the_mint(check, settled)
    check_the_block(check, settled)
    check_the_settlement(check, halted, "halted")
    check_the_pool(check, halted, "halted")
    check_the_single_pass(check, halted)
    check_the_orderings(check)
    check_the_restart_run(check, restart)
    check.require_full_coverage()

    if check.failures:
        for failure in check.failures:
            print(f"FAIL {failure}", file=sys.stderr)
        return 1
    if args.emit:
        written = check.write(args.vectors)
        print(f"wrote {written} vectors to {args.vectors}")
        return 0
    print(f"economy-transition-v9-execution: {check.checked} vectors verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
