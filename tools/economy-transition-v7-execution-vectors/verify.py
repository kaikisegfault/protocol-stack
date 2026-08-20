#!/usr/bin/env python3
"""Independently derive and check the economy-transition-v7 execution vectors.

These vectors record what a version-seven chain *does* with the recovery pool.
The settlement it does it over is `test-vectors/economy-transition-v7.txt` and
the transaction surface is version six's, unchanged; this file touches neither
and restates neither.

Every value two sources can reach is derived twice — once from `expected.py`,
which imports nothing from `simulation/`, and once from a live run of the
execution model — and is recorded only when both agree. Two constructions go
further and are checked against a third source: the ordered transaction tree
against `test-vectors/protocol-primitives-v1.txt`, and the application block
header and block ID against `test-vectors/ledger-transition-v1.txt`. Each is
inherited from version one, so a restatement that had drifted would otherwise
agree only with itself.

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
from settlement_checks import (
    check_boundary_scenario,
    check_permanence_scenario,
    check_pool_scenario,
)
from trace_checks import check_constructions, check_genesis, check_receipt, check_scenario

from simulation.economy_transition_v7 import trace

# Each chain carries two identities, two escrows, two signers, two enrollments,
# two seats, the cycle assignment records it wrote, one unreferred pool entry
# already counted in genesis, and one typed-custody entry per institutional leg.
SHAPES = {
    "pool": dict(identities=2, escrows=2, signers=2, enrollments=2, seats=2,
                 assignments=2, custody=4),
    "boundary": dict(identities=2, escrows=2, signers=2, enrollments=2, seats=2,
                     assignments=2, custody=4),
    "permanence": dict(identities=2, escrows=2, signers=2, enrollments=2, seats=2,
                       assignments=2, custody=4),
}

# Registration is fee-exempt, so the fee-charging successes are the purchases,
# the activations, and each mint that was not refused.
FEE_CHARGING_SUCCESSES = {"pool": 6, "boundary": 5, "permanence": 5}


def _totals(name: str) -> dict[str, object]:
    airdrops = 2 * e.VERIFIED_USER_DAILY_ATOMIC
    minted = (
        e.pool_scenario_totals()["minted_total_atomic"]
        if name in ("pool", "boundary")
        else e.permanence_scenario_totals()["minted_total_atomic"]
    )
    return {
        "total_supply": airdrops + minted,
        "fee_pool": e.fee_pool_atomic(FEE_CHARGING_SUCCESSES[name]),
    }


def run(check: Checker, accepted: Path) -> None:
    check_constructions(check, accepted)
    check_genesis(check)
    check_receipt(check)

    built = {maker.__name__: maker()[0] for maker in trace.SCENARIOS}
    pool = built["pool_scenario"]
    boundary = built["boundary_scenario"]
    permanence = built["permanence_scenario"]

    for scenario in (pool, boundary, permanence):
        check.section(f"Scenario {scenario.name}: every block's commitments.")
        check_scenario(
            check,
            scenario,
            _totals(scenario.name),
            shape=e.economy_entry_count(**SHAPES[scenario.name]),
        )

    check_pool_scenario(check, pool)
    check_boundary_scenario(check, boundary)
    check_permanence_scenario(check, permanence)
    check_determinism(check, list(built.values()))


def check_determinism(check: Checker, scenarios: list) -> None:
    """The same fixture, executed twice, commits to the same roots.

    A model that read a clock, a hash seed, or an unordered iteration would
    disagree with itself here, which is the one defect no amount of independent
    derivation would ever notice.
    """
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
        print(f"economy-transition-v7-execution: {written} vectors written")
        return 0
    print(f"economy-transition-v7-execution: {check.checked} vectors verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
