#!/usr/bin/env python3
"""Run the deterministic minimum-entitlement boundary study."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.participation.domain import domain_digest

from simulation.minimum_entitlement.boundaries import funding_boundaries
from simulation.minimum_entitlement.crosscheck import boundary_cross_checks
from simulation.minimum_entitlement.design import build_design
from simulation.minimum_entitlement.model import evaluate_floor, identities, work_maps
from simulation.minimum_entitlement.support import exact_support


def _zero_work_probes(design: dict) -> list[dict]:
    results = []
    participants = identities(2)
    raw_units, scores = work_maps(2, 7)
    for family in design["floor_families"]:
        floor = 0 if family == "zero" else 1
        for mechanism in design["mechanisms"]:
            baseline = evaluate_floor(
                100, raw_units, scores, participants, family, floor, mechanism
            )
            extended_participants = {
                **participants,
                "zero_probe": {
                    "principal": "zero_probe_owner",
                    "payout_account": "zero_probe_payout",
                },
            }
            extended = evaluate_floor(
                100,
                {**raw_units, "zero_probe": 0},
                {**scores, "zero_probe": 0},
                extended_participants,
                family,
                floor,
                mechanism,
            )
            unchanged = baseline == extended and "zero_probe" not in extended["credits"]
            if not unchanged:
                raise AssertionError("zero-work identifier changed floor projection")
            results.append(
                {
                    "floor_family": family,
                    "floor": floor,
                    "mechanism": mechanism,
                    "zero_work_rejected": unchanged,
                }
            )
    return results


def run_study() -> dict:
    design = build_design()
    design_digest = domain_digest(
        "protocol-stack:minimum-entitlement:design-v1", design
    )
    support, break_evens, zero_checks, cap_equivalence = exact_support(design)
    boundaries = funding_boundaries(design)
    probes = _zero_work_probes(design)
    participation, native = boundary_cross_checks(design)
    reserve_summaries = [item for item in support if item["floor_family"] != "zero"]
    report = {
        "schema": "protocol-stack/minimum-entitlement-study/v1",
        "design": design["design"],
        "design_digest": design_digest,
        "funding_boundaries": boundaries,
        "exact_support": support,
        "coordinate_break_evens": break_evens,
        "zero_floor_cross_check_count": zero_checks,
        "registered_scope_equivalence": cap_equivalence,
        "zero_work_probes": probes,
        "participation_cross_checks": participation,
        "native_funding_replays": native,
        "objectives": {
            "work_invariant": all(
                item["objectives"]["work_invariant"] for item in support
            ),
            "strictly_funded": boundaries["boundary_safe"]
            and all(item["objectives"]["strictly_funded"] for item in support),
            "zero_work_rejected": all(item["zero_work_rejected"] for item in probes),
            "honest_entry_family_exists": any(
                item["objectives"]["honest_entry"] for item in reserve_summaries
            ),
            "nonprofitable_same_floor_family_exists": any(
                item["objectives"]["nonprofitable_same_floor_split"]
                for item in reserve_summaries
            ),
            "no_baseline_amplification_family_exists": any(
                item["objectives"]["no_baseline_amplification"]
                for item in reserve_summaries
            ),
            "hidden_concentration": all(
                item["objectives"]["hidden_concentration"] for item in support
            ),
            "liveness_family_exists": any(
                item["objectives"]["liveness"] for item in reserve_summaries
            ),
            "budget_exhaustion_safe": boundaries["boundary_safe"],
            "native_funding": all(
                item["funding_failures"] == 0
                and item["native_funding_conserved"]
                for item in native
            ),
            "registered_scope_equivalence": cap_equivalence,
            "global_joint_floor_exists": any(
                item["global_joint_break_even"] is not None
                for item in reserve_summaries
            ),
        },
    }
    report["study_digest"] = domain_digest(
        "protocol-stack:minimum-entitlement:study-v1", report
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    text = json.dumps(
        run_study(), sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False
    ) + "\n"
    if arguments.output is None:
        sys.stdout.write(text)
    else:
        arguments.output.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
