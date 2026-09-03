#!/usr/bin/env python3
"""Independently derive and check the economy-transition-v8 execution vectors.

These vectors record what a version-eight chain *does* with the uptime carrier.
The contract surface it does it over is `test-vectors/economy-transition-v8.txt`
and the settlement is version seven's; this file touches neither and restates
neither.

Every value two sources can reach is derived twice — once from `expected.py`,
which imports nothing from `simulation/`, and once from a live run of the
execution model — and is recorded only when both agree. Three constructions go
further and are checked against a third source: the ordered transaction tree
against `test-vectors/protocol-primitives-v1.txt`, and the application block
header and block ID against `test-vectors/ledger-transition-v1.txt`. Each is
inherited from version one, so a restatement that had drifted would otherwise
agree only with itself.

**The settlement claim is checked against version seven's accepted derivation.**
The measured schedule is compared to an independently stated seat list, and that
list is settled by `economy-transition-v7-vectors/expected.py` — so "the carrier
changed no settlement" is evidence rather than an assertion version eight makes
about itself.

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
from measurement_checks import (
    check_deadline,
    check_determinism,
    check_dispute_moves_the_winner_set,
    check_kind_coverage,
    check_measured_window,
)
from trace_checks import check_constructions, check_genesis, check_receipt, check_scenario

from simulation.economy_transition_v8 import trace

# Each chain carries two identities, two escrows, two signers, two enrollments,
# and whatever the scenario itself writes.
SHAPES = {
    # One window record survives the prologue: Bob lost slots in window two as
    # well, and the prologue deleted window one's alone.
    "measured": dict(identities=2, escrows=2, signers=2, enrollments=2, seats=3,
                     assignments=1, referral_balances=1, custody=4,
                     window_records=1),
    # Both machines answered every challenge on this chain, so no window record
    # exists at all and the dispute's own record was deleted with its window.
    "disputed": dict(identities=2, escrows=2, signers=2, enrollments=2, seats=2,
                     assignments=1),
    # The chain stops one height after a challenge was issued and one slot has
    # been lost, so both new entry kinds are live at once.
    "deadline": dict(identities=2, escrows=2, signers=2, enrollments=2, seats=2,
                     open_challenges=1, window_records=1),
    # A created escrow was deleted and an assigned signer was revoked, so both
    # counts are back where they started — which is the point of recording them.
    "carried": dict(identities=2, escrows=2, signers=2, enrollments=2),
}

# Registration and the challenge response charge nothing, so the fee-charging
# successes are the purchases, the activations, the accepted disputes, the
# escrow and signer transactions, the accepted posture changes, and each mint
# that was not refused.
FEE_CHARGING_SUCCESSES = {
    "measured": 8, "disputed": 10, "deadline": 4, "carried": 8,
}


def _totals(scenario) -> dict[str, object]:
    """The closed-form supply and fee pool of each chain, before any is run."""
    name = scenario.name
    airdrops = 2 * e.VERIFIED_USER_DAILY_ATOMIC
    minted = 0
    if name == "measured":
        totals = e.measured_totals(scenario.notes["bob_credited_slots"])
        minted = totals["alice_minted_atomic"] + totals["alice_referral_atomic"]
    if name == "carried":
        minted = e.MINT_ACCUMULATION_CAP * e.VERIFIED_USER_DAILY_ATOMIC
    return {
        "total_supply": airdrops + minted,
        "fee_pool": e.fee_pool_atomic(FEE_CHARGING_SUCCESSES[name]),
    }


def run(check: Checker, accepted: Path) -> None:
    check_constructions(check, accepted)
    check_genesis(check)
    check_receipt(check)

    built = {maker.__name__.removesuffix("_scenario"): maker()[0]
             for maker in trace.SCENARIOS}

    for name in ("measured", "disputed", "deadline", "carried"):
        scenario = built[name]
        check.section(f"Scenario {name}: every recorded block's commitments.")
        check_scenario(
            check,
            scenario,
            _totals(scenario),
            shape=e.economy_entry_count(**SHAPES[name]),
            issued=e.issued_by_label(
                name, scenario.notes.get("bob_credited_slots", 0)
            ),
        )

    check_measured_window(check, built["measured"])
    check_dispute_moves_the_winner_set(check, built["disputed"])
    check_deadline(check, built["deadline"])
    check_kind_coverage(check, list(built.values()))
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
        print(f"economy-transition-v8-execution: {written} vectors written")
        return 0
    print(f"economy-transition-v8-execution: {check.checked} vectors verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
