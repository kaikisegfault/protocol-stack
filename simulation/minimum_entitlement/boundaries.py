"""Exact reserve-funding and identity-count boundaries."""

from __future__ import annotations

from .model import (
    evaluate_floor,
    identities,
    maximum_floor,
    maximum_identities,
    work_maps,
)


def funding_boundaries(design: dict) -> dict:
    budgets = sorted({item["budget"] for item in design["retained_coordinates"]})
    floor_rows = []
    identity_rows = []
    for budget in budgets:
        for family in ("per_participant", "work_proportional"):
            for identity_count in range(1, 17):
                maximum = maximum_floor(budget, family, identity_count)
                divisor = identity_count + 1 if family == "per_participant" else 17
                raw_units, scores = work_maps(identity_count, 7)
                participants = identities(identity_count)
                boundary = evaluate_floor(
                    budget,
                    raw_units,
                    scores,
                    participants,
                    family,
                    maximum,
                    "proportional",
                )
                beyond = evaluate_floor(
                    budget,
                    raw_units,
                    scores,
                    participants,
                    family,
                    maximum + 1,
                    "proportional",
                )
                floor_rows.append(
                    {
                        "budget": budget,
                        "floor_family": family,
                        "identity_count": identity_count,
                        "maximum_floor": maximum,
                        "reserve_at_maximum": maximum * divisor,
                        "exhausts_budget": maximum * divisor == budget,
                        "next_floor_reserve": (maximum + 1) * divisor,
                        "boundary_projection_feasible": boundary["feasible"],
                        "next_projection_infeasible": not beyond["feasible"],
                    }
                )
            for floor in range(1, 6):
                identity_rows.append(
                    {
                        "budget": budget,
                        "floor_family": family,
                        "floor": floor,
                        "maximum_identities": maximum_identities(budget, family, floor),
                    }
                )
    safe = all(
        item["reserve_at_maximum"] <= item["budget"]
        and item["next_floor_reserve"] > item["budget"]
        and item["boundary_projection_feasible"]
        and item["next_projection_infeasible"]
        for item in floor_rows
    )
    return {
        "maximum_floor_boundaries": floor_rows,
        "common_floor_identity_boundaries": identity_rows,
        "common_floor_ceiling": min(
            item["maximum_floor"] for item in floor_rows
        ),
        "budget_exhaustion_instances": sum(
            int(item["exhausts_budget"]) for item in floor_rows
        ),
        "boundary_safe": safe,
    }
