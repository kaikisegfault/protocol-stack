#!/usr/bin/env python3
"""Independently derive and check the economy-transition-v6 execution vectors.

These vectors record what a version-six chain *does*. The byte surface it does
it over is `test-vectors/economy-transition-v6.txt`, which this file does not
touch and does not restate.

Every value two sources can reach is derived twice — once from `expected.py`,
which imports nothing from `simulation/`, and once from a live run of the
execution model — and is recorded only when both agree. Three constructions go
further and are checked against a third source: the ordered transaction tree and
the accepted signed transfer against `test-vectors/protocol-primitives-v1.txt`,
and the application block header and block ID against
`test-vectors/ledger-transition-v1.txt`. Each is an inherited construction, so a
restatement that had drifted would otherwise agree only with itself.

`--emit` writes the vector file instead of checking it. It runs the same
derivations through the same agreement gate, so it can only write values both
sources already produce; it removes a transcription step, not the evidence.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(REPOSITORY_ROOT))

import expected as e
from checker import Checker, read_vectors
from derivation_checks import (
    check_compatibility,
    check_derived_rules,
    check_determinism,
    check_ordering,
)
from trace_checks import (
    TRANSFER_AMOUNT,
    check_balances,
    check_constructions,
    check_genesis,
    check_scenario,
)

from simulation.economy_transition_v6 import trace


def run(check: Checker, accepted: Path) -> None:
    check_constructions(check, accepted)
    check_genesis(check)

    built = {maker.__name__: maker()[0] for maker in trace.SCENARIOS}
    registration = built["registration_scenario"]
    millionth = built["millionth_scenario"]
    recovery = built["recovery_scenario"]
    compatibility = built["compatibility_scenario"]
    posture = built["posture_scenario"]
    boundary = built["block_scenario"]

    # Two identities, two escrows, two signers, two enrollments, and no seat.
    check_scenario(
        check,
        registration,
        e.registration_totals(TRANSFER_AMOUNT, collected_windows=30),
        shape=e.economy_entry_count(
            identities=2, escrows=2, signers=2, enrollments=2
        ),
    )
    check_balances(
        check,
        "registration",
        registration.ledger,
        {
            "alice_balance": (
                trace.ALICE_ESCROW,
                e.registration_totals(TRANSFER_AMOUNT, 30)["alice_balance"],
            ),
            "bob_balance": (
                trace.BOB_ESCROW,
                e.registration_totals(TRANSFER_AMOUNT, 30)["bob_balance"],
            ),
        },
    )

    # Dave registers past the population, so he has an escrow and no enrollment.
    check_scenario(
        check,
        millionth,
        e.millionth_totals(TRANSFER_AMOUNT),
        shape=e.economy_entry_count(
            identities=2, escrows=2, signers=2, enrollments=1
        ),
    )
    check_balances(
        check,
        "millionth",
        millionth.ledger,
        {
            "alice_balance": (
                trace.ALICE_ESCROW,
                e.millionth_totals(TRANSFER_AMOUNT)["alice_balance"],
            ),
            "dave_balance": (
                trace.DAVE_ESCROW,
                e.millionth_totals(TRANSFER_AMOUNT)["dave_balance"],
            ),
        },
    )

    # Maria ends with one signer again: the lost one is gone and the new one is
    # assigned, which is what makes the count a property rather than a total.
    check_scenario(
        check,
        recovery,
        e.recovery_totals(TRANSFER_AMOUNT),
        shape=e.economy_entry_count(
            identities=2, escrows=2, signers=2, enrollments=2
        ),
    )
    check_balances(
        check,
        "recovery",
        recovery.ledger,
        {
            "maria_balance": (
                trace.MARIA_ESCROW,
                e.recovery_totals(TRANSFER_AMOUNT)["maria_balance"],
            ),
            "bob_balance": (
                trace.BOB_ESCROW,
                e.recovery_totals(TRANSFER_AMOUNT)["bob_balance"],
            ),
        },
    )

    check_scenario(
        check,
        compatibility,
        e.compatibility_totals(TRANSFER_AMOUNT),
        shape=e.economy_entry_count(
            identities=2, escrows=2, signers=2, enrollments=2
        ),
    )
    check_balances(
        check,
        "compatibility",
        compatibility.ledger,
        {
            "sender_balance": (
                trace.ACCEPTED_ESCROW,
                e.compatibility_totals(TRANSFER_AMOUNT)["sender_balance"],
            ),
            "bob_balance": (
                trace.BOB_ESCROW,
                e.compatibility_totals(TRANSFER_AMOUNT)["bob_balance"],
            ),
        },
    )

    posture_transfer = trace.POSTURE_MINIMUM - 1
    check_scenario(
        check,
        posture,
        e.posture_totals(posture_transfer),
        shape=e.economy_entry_count(
            identities=2, escrows=2, signers=2, enrollments=2
        ),
    )
    check_balances(
        check,
        "posture",
        posture.ledger,
        {
            "alice_balance": (
                trace.ALICE_ESCROW,
                e.posture_totals(posture_transfer)["alice_balance"],
            ),
            "bob_balance": (
                trace.BOB_ESCROW,
                e.posture_totals(posture_transfer)["bob_balance"],
            ),
        },
    )

    # Three identities, two seats, one assignment, one referral balance, and the
    # four institutional custody entries the mint wrote.
    block_totals = e.block_totals(in_span=2, referred=1)
    check_scenario(
        check,
        boundary,
        block_totals,
        shape=e.economy_entry_count(
            identities=3,
            escrows=3,
            signers=3,
            enrollments=3,
            seats=2,
            assignments=1,
            referral_balances=1,
            custody=4,
        ),
    )
    check_balances(
        check,
        "block",
        boundary.ledger,
        {
            "alice_balance": (trace.ALICE_ESCROW, block_totals["alice_balance"]),
            "bob_balance": (trace.BOB_ESCROW, block_totals["bob_balance"]),
            "carol_balance": (trace.CAROL_ESCROW, block_totals["carol_balance"]),
        },
    )
    check.section("What one cycle assigns, derived from the winner rule.")
    cycle = e.one_cycle_shares(in_span=2, met=1)
    for field, value in cycle.items():
        check.equal(f"cycle.{field}", value)
    for channel, amount in e.custody_after_one_cycle(2).items():
        check.agree(
            f"cycle.custody{channel}", amount, boundary.ledger.custody[channel]
        )
    check.agree(
        "cycle.unreferred_pool_atomic",
        block_totals["unreferred_pool_atomic"],
        boundary.ledger.pool_accrued,
    )

    check_compatibility(check, accepted, compatibility)
    check_ordering(check, boundary)
    check_derived_rules(check)
    check_determinism(check, list(built.values()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vectors", required=True, type=Path)
    parser.add_argument(
        "--emit",
        action="store_true",
        help="write the vector file from the derivations instead of checking it",
    )
    arguments = parser.parse_args()

    recorded = {} if arguments.emit else read_vectors(arguments.vectors)
    check = Checker(recorded, emit=arguments.emit)
    run(check, REPOSITORY_ROOT / "test-vectors")
    check.require_full_coverage()

    if check.failures:
        for failure in check.failures:
            print(f"FAIL {failure}", file=sys.stderr)
        print(f"{len(check.failures)} vector failures", file=sys.stderr)
        return 1
    if arguments.emit:
        written = check.write(arguments.vectors)
        print(f"economy-transition-v6-execution: {written} vectors written")
        return 0
    print(f"economy-transition-v6-execution: {check.checked} vectors verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
