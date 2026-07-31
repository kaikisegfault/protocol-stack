#!/usr/bin/env python3
"""Run the deterministic cross-simulator economic stress study."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.authority.domain import MAX_U64, domain_digest
from simulation.economic_stress.compose import run_configuration
from simulation.economic_stress.design import (
    DESIGN_NAME,
    FACTORS,
    FACTOR_LEVELS,
    assert_design,
    configurations,
    design_value,
)


def run_study(seed_start: int = 0, seed_count: int = 8) -> dict:
    _validate_bounds(seed_start, seed_count)
    assert_design()
    design = design_value()
    runs = [
        run_configuration(config, seed)
        for config in configurations()
        for seed in range(seed_start, seed_start + seed_count)
    ]
    objective_names = tuple(runs[0]["objectives"])
    classifications = {name: 0 for name in ("robust", "fragile", "infeasible")}
    reverse_counts: dict[str, int] = {}
    for run in runs:
        classifications[run["classification"]] += 1
        for code in run["reverse_stress"]:
            reverse_counts[code] = reverse_counts.get(code, 0) + 1
    report = {
        "schema": "protocol-stack/economic-stress-study/v1",
        "design": DESIGN_NAME,
        "generator": "SplitMix64-v1",
        "seed_start": seed_start,
        "seed_count": seed_count,
        "case_count": len(configurations()),
        "run_count": len(runs),
        "factor_levels": {
            factor: list(FACTOR_LEVELS[factor]) for factor in FACTORS
        },
        "design_digest": domain_digest(
            "protocol-stack:economic-stress:design-v1",
            design,
        ),
        "objective_pass_counts": {
            name: sum(run["objectives"][name] for run in runs)
            for name in objective_names
        },
        "classification_counts": classifications,
        "reverse_stress_counts": dict(sorted(reverse_counts.items())),
        "runs": runs,
    }
    report["study_digest"] = domain_digest(
        "protocol-stack:economic-stress:study-v1",
        report,
    )
    return report


def _validate_bounds(seed_start: int, seed_count: int) -> None:
    if type(seed_start) is not int or not 0 <= seed_start <= MAX_U64:
        raise ValueError("seed_start must be a u64")
    if type(seed_count) is not int or not 1 <= seed_count <= 16:
        raise ValueError("seed_count must be in 1..16")
    if seed_start > MAX_U64 - (seed_count - 1):
        raise ValueError("seed range exceeds u64")


def _u64(text: str) -> int:
    value = int(text, 0)
    if not 0 <= value <= MAX_U64:
        raise argparse.ArgumentTypeError("value must be a u64")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-start", type=_u64, default=0)
    parser.add_argument("--seed-count", type=int, default=8)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    try:
        report = run_study(arguments.seed_start, arguments.seed_count)
    except ValueError as error:
        parser.error(str(error))
    text = json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n"
    if arguments.output is None:
        sys.stdout.write(text)
    else:
        arguments.output.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
