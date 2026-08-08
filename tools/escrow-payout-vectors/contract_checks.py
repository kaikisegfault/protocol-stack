"""Contract, constitution, and binding-provenance checks.

The escrow caps are compared against literals converted here from the Founder
Constitution's maximum-supply allocation table, so the vector file, the model's
contract module, and the constitution must all agree rather than the file simply
restating whatever the model computed.
"""

from __future__ import annotations

from pathlib import Path

import walk as w
from checker import Checker

ROOT = Path(__file__).resolve().parents[2]

# Display units from the Founder Constitution's Founder Node distribution table.
CONSTITUTION_DISPLAY_CAPS: dict[str, int] = {
    w.VENTURE: 12_500_100_000,
    w.COMMUNITY: 2_500_020_000,
    w.DEVELOPER: 1_250_010_000,
}
ATOMIC_UNITS_PER_DISPLAY_UNIT = 100_000_000
DECIMAL_PLACES = 8


def check_schema_vectors(check: Checker, spec: w.Spec) -> None:
    """The schema and digest labels as the specification writes them."""
    check.equal("schema", spec.schema)
    check.equal("events_file", spec.events_file)
    check.equal("events_domain_label", spec.events_label)
    check.equal("state_domain_label", spec.state_label)
    check.equal("trace_domain_label", spec.trace_label)
    check.equal("result_domain_label", spec.result_label)


def check_constitution_anchors(check: Checker) -> None:
    """Anchor the denomination and the three caps to constitutional literals."""
    check.equal("denomination.decimal_places", DECIMAL_PLACES)
    check.equal(
        "denomination.atomic_units_per_display_unit", ATOMIC_UNITS_PER_DISPLAY_UNIT
    )
    check.equal("escrows.count", len(w.ESCROWS))
    for index, escrow in enumerate(w.ESCROWS):
        derived = CONSTITUTION_DISPLAY_CAPS[escrow] * ATOMIC_UNITS_PER_DISPLAY_UNIT
        check.equal(f"escrow{index}.id", escrow)
        check.equal(f"escrow{index}.cap_display", CONSTITUTION_DISPLAY_CAPS[escrow])
        check.equal(f"escrow{index}.cap_atomic", derived)


def check_contract_agreement(
    binding: object, escrow_caps: dict[str, int], spec: w.Spec
) -> int:
    """The model's caps and labels must equal the specification's literals."""
    labels = (
        ("schema", spec.schema),
        ("events_label", spec.events_label),
        ("state_label", spec.state_label),
        ("trace_label", spec.trace_label),
        ("result_label", spec.result_label),
        ("economy_state_label", spec.economy_state_label),
    )
    for name, expected in labels:
        if getattr(binding, name) != expected:
            raise AssertionError(f"the model's {name} is not the specified string")

    compared = 0
    for escrow in w.ESCROWS:
        expected = CONSTITUTION_DISPLAY_CAPS[escrow] * ATOMIC_UNITS_PER_DISPLAY_UNIT
        if w.CAPS[escrow] != expected:
            raise AssertionError(f"{escrow}: the walk cap is not constitutional")
        if escrow_caps[escrow] != expected:
            raise AssertionError(f"{escrow}: the model cap is not constitutional")
        compared += 1
    if set(escrow_caps) != set(w.ESCROWS):
        raise AssertionError("the model and the walk disagree on the escrow set")
    return compared


def check_binding_vectors(
    check: Checker,
    economy_digest: str,
    opening: dict[str, int],
    events_path: Path,
    spec: w.Spec,
) -> None:
    """Prove the bound digest is a real economy run, not a fixture constant."""
    check.equal("binding.economy_state_digest", economy_digest)
    check.equal("binding.economy_state_label", spec.economy_state_label)
    for index, escrow in enumerate(w.ESCROWS):
        check.equal(f"binding.escrow{index}.opening_custody", opening[escrow])

    events = w.load_events(events_path)
    bound = [
        event
        for event in events
        if event["kind"] == "bind_opening_custody"
        and event["economy_state_result"] is not None
        and event["economy_state_result"]["state_digest"] == economy_digest
    ]
    check.equal("binding.fixture_bind_events_matching_economy_run", len(bound))

    if spec.version == "v2":
        _check_cross_version_containment(check, spec)


def _check_cross_version_containment(check: Checker, spec: w.Spec) -> None:
    """Prove a version-one economy state cannot satisfy a version-two bind.

    This is the compatibility boundary, derived rather than asserted. Every bind
    event in the retained v1 fixture is replayed through the v2 walk, which
    recomputes the supplied state's digest under the v2 economy label. None may
    be accepted, and the digest-carrying ones must fail as inconsistent rather
    than as missing input, which is what shows the label did the rejecting.
    """
    v1_events = w.load_events(ROOT / w.V1.events_file)
    binds = [event for event in v1_events if event["kind"] == "bind_opening_custody"]
    with_state = [
        event for event in binds if event["economy_state_result"] is not None
    ]

    walk = w.Walk(spec=spec)
    results = [walk.bind(event) for event in with_state]
    rejected = [result for result in results if result == "INVALID_RESEARCH_INPUT"]
    if any(result == "OK" for result in results):
        raise AssertionError("a version-one economy state satisfied a version-two bind")
    if len(rejected) != len(results):
        raise AssertionError(f"unexpected cross-version bind results: {sorted(set(results))}")

    check.equal("binding.v1_states_offered_to_v2", len(with_state))
    check.equal("binding.v1_states_rejected_by_v2", len(rejected))
    check.equal("binding.escrow_caps_agree_with_v1", 1 if _caps_agree() else 0)


def _caps_agree() -> bool:
    """Whether both accepted economy contracts give the same three escrow caps.

    The two versions share one cap table in the model, and this is the check
    that keeps that from being an assumption. ADR 0023 raised the maximum supply
    through the referral channel alone, so the three escrow caps are unchanged.
    """
    from simulation.escrow_payout import contract as c

    return c.caps_agree()
