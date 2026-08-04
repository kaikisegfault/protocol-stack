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

# Display units from the Founder Constitution's Founder Node distribution table.
CONSTITUTION_DISPLAY_CAPS: dict[str, int] = {
    w.VENTURE: 12_500_100_000,
    w.COMMUNITY: 2_500_020_000,
    w.DEVELOPER: 1_250_010_000,
}
ATOMIC_UNITS_PER_DISPLAY_UNIT = 100_000_000
DECIMAL_PLACES = 8


def check_schema_vectors(check: Checker) -> None:
    """The schema and digest labels as the specification writes them."""
    check.equal("schema", w.SCHEMA)
    check.equal("events_file", w.EVENTS_FILE)
    check.equal("events_domain_label", w.EVENTS_LABEL)
    check.equal("state_domain_label", w.STATE_LABEL)
    check.equal("trace_domain_label", w.TRACE_LABEL)
    check.equal("result_domain_label", w.RESULT_LABEL)


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


def check_contract_agreement(model: object, escrow_caps: dict[str, int]) -> int:
    """The model's caps and labels must equal the specification's literals."""
    labels = (
        ("SCHEMA", w.SCHEMA),
        ("EVENTS_LABEL", w.EVENTS_LABEL),
        ("STATE_LABEL", w.STATE_LABEL),
        ("TRACE_LABEL", w.TRACE_LABEL),
        ("RESULT_LABEL", w.RESULT_LABEL),
        ("ECONOMY_STATE_LABEL", w.ECONOMY_STATE_LABEL),
    )
    for name, expected in labels:
        if getattr(model, name) != expected:
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
) -> None:
    """Prove the bound digest is a real economy run, not a fixture constant."""
    check.equal("binding.economy_state_digest", economy_digest)
    check.equal("binding.economy_state_label", w.ECONOMY_STATE_LABEL)
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
