#!/usr/bin/env python3

"""Generate seeded ledger sequences and compare the Python and C++ kernels."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from cases import (
    DEFAULT_RANDOM_SCENARIOS,
    DEFAULT_SEED,
    DIRECTED_SCENARIOS,
    directed_blocks,
    make_fixture,
    verify_prng,
)
from coverage import Coverage
from model import ReferenceLedger
from pinned_sodium import Sodium
from protocol_bytes import require
from random_cases import random_blocks, scenario_rng
from transcript import compare, format_block


def run(
    runner: Path,
    random_count: int,
    seed: int,
    library_name: str | None,
) -> Coverage:
    require(random_count >= 0, "random scenario count cannot be negative")
    require(0 <= seed < (1 << 256), "seed must fit 256 bits")
    require(runner.is_file(), f"runner not found: {runner}")
    verify_prng()
    sodium = Sodium(library_name)
    fixture = make_fixture(sodium)
    coverage = Coverage()
    randomized_coverage = Coverage()
    total_count = DIRECTED_SCENARIOS + random_count
    require(total_count <= 100_000, "scenario count exceeds runner bound")
    request = [f"PSDIFF1 {total_count}"]
    expected: list[str] = []

    for scenario in range(total_count):
        reference = ReferenceLedger(fixture.genesis, sodium)
        if scenario < DIRECTED_SCENARIOS:
            blocks = directed_blocks(scenario, sodium, fixture)
        else:
            rng = scenario_rng(seed, scenario)
            block_count = 1 + rng.below(3)
            generation = ReferenceLedger(fixture.genesis, sodium)
            blocks = random_blocks(
                rng, scenario, block_count, generation, sodium, fixture
            )
        request.append(
            f"S {scenario} {fixture.genesis.hex()} {len(blocks)}"
        )
        seen: dict[bytes, int] = {}
        randomized_seen: dict[bytes, int] = {}
        for block_index, raws in enumerate(blocks):
            height = reference.state.height + 1
            encoded_raws = [
                raw.hex() if raw else "-" for raw in raws
            ]
            request.append(
                " ".join(
                    ["B", str(height), str(len(raws)), *encoded_raws]
                )
            )
            commit = reference.apply_block(height, raws)
            coverage.observe(raws, commit, seen)
            if scenario >= DIRECTED_SCENARIOS:
                randomized_coverage.observe(
                    raws, commit, randomized_seen
                )
            expected.append(
                format_block(
                    scenario, block_index, commit, reference.state
                )
            )

    coverage.verify()
    require(
        randomized_coverage.blocks >= random_count,
        "randomized block coverage below sequence count",
    )
    require(
        randomized_coverage.raw_inputs >= random_count,
        "randomized transaction coverage below sequence count",
    )
    if random_count >= 1_000:
        randomized_coverage.verify()
    completed = subprocess.run(
        [str(runner)],
        input="\n".join(request) + "\n",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(
        completed.returncode == 0,
        "C++ differential runner failed:\n" + completed.stderr,
    )
    require(
        not completed.stderr,
        "C++ differential runner wrote stderr:\n" + completed.stderr,
    )
    compare(expected, completed.stdout)
    return coverage


def parse_integer(value: str) -> int:
    return int(value, 0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runner", type=Path, help="kernel runner executable")
    parser.add_argument(
        "--count",
        type=int,
        default=DEFAULT_RANDOM_SCENARIOS,
        help=(
            "seeded randomized sequences, in addition to directed coverage "
            f"(default: {DEFAULT_RANDOM_SCENARIOS})"
        ),
    )
    parser.add_argument(
        "--seed",
        type=parse_integer,
        default=DEFAULT_SEED,
        help=f"root seed (default: {DEFAULT_SEED:#x})",
    )
    parser.add_argument(
        "--libsodium",
        help="path to the pinned libsodium 1.0.22 shared library",
    )
    arguments = parser.parse_args()
    coverage = run(
        arguments.runner.resolve(),
        arguments.count,
        arguments.seed,
        arguments.libsodium,
    )
    print(
        "kernel differential: passed "
        f"{arguments.count} seeded randomized sequences plus "
        f"{DIRECTED_SCENARIOS} directed sequences, {coverage.blocks} blocks, "
        f"{coverage.raw_inputs} raw inputs, {coverage.admitted} admitted; "
        "admission=1,2,3 execution=0,1,2,3,4,6,7,8 "
        "(nonce-exhausted remains unit-boundary-only); "
        f"prng=splitmix64-v1 seed={arguments.seed:#x}"
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError) as error:
        print(f"kernel differential: failed: {error}", file=sys.stderr)
        sys.exit(1)
