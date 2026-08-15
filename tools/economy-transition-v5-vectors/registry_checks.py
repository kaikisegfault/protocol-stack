"""The HUB registry, the per-human seat bound, and the settlement's continuity.

The registry is version four's, imported rather than copied, so these checks
run version four's operations under version five's package and require the same
outcomes. That is the point: version four's defect was never in the registry.

The settlement section reaches two versions back. Version four imported version
three's cap, assignment record, and mint walk, and version five imports version
four's, so the record it writes for the same population must still be
byte-identical to the value `test-vectors/economy-transition-v3.txt` records.
Checking against that accepted file is a third source rather than any of the
three implementations.
"""

from __future__ import annotations

from pathlib import Path

import expected as e
from checker import Checker, read_vectors

from simulation.economy_transition_v3 import settlement
from simulation.economy_transition_v5 import contract as c
from simulation.economy_transition_v5 import identity, scenario, state


def _build(registry_class) -> object:
    """The fixture's registry, built the same way by either implementation."""
    built = registry_class()
    built.register(
        scenario.ALICE_IDENTITY,
        scenario.ALICE_KEY,
        scenario.ALICE_FIRST_ADDRESS,
        scenario.REGISTRATION_HEIGHT,
    )
    built.add_address(scenario.ALICE_IDENTITY, scenario.ALICE_SECOND_ADDRESS)
    built.register(
        scenario.BOB_IDENTITY,
        scenario.BOB_KEY,
        scenario.BOB_ADDRESS,
        scenario.REGISTRATION_HEIGHT + 1,
    )
    built.register(
        scenario.CAROL_IDENTITY,
        scenario.CAROL_KEY,
        scenario.CAROL_ADDRESS,
        scenario.REGISTRATION_HEIGHT + 2,
    )
    built.remove_address(scenario.CAROL_ADDRESS)
    built.claim_seat(scenario.ALICE_IDENTITY)
    return built


def check_registry(check: Checker) -> None:
    model = _build(identity.Registry)
    independent = _build(e.Registry)

    check.agree(
        "registry.identity_count", len(independent.identities), len(model.identities)
    )
    check.agree(
        "registry.address_count", len(independent.addresses), len(model.addresses)
    )
    for name, who in (
        ("alice", scenario.ALICE_IDENTITY),
        ("bob", scenario.BOB_IDENTITY),
        ("carol", scenario.CAROL_IDENTITY),
    ):
        check.agree(
            f"registry.addresses.{name}",
            independent.identities[who]["addresses"],
            model.identities[who].address_count,
        )
        check.agree(
            f"registry.seats.{name}",
            independent.identities[who]["seats"],
            model.identities[who].seat_count,
        )

    check.equal(
        "registry.two_addresses_resolve_to_one_identity",
        model.identity_of(scenario.ALICE_FIRST_ADDRESS)
        == model.identity_of(scenario.ALICE_SECOND_ADDRESS)
        == scenario.ALICE_IDENTITY,
    )
    check.equal(
        "registry.removal_unlinks_the_account",
        not model.is_verified(scenario.CAROL_ADDRESS),
    )
    check.equal(
        "registry.removal_keeps_the_identity",
        scenario.CAROL_IDENTITY in model.identities,
    )
    check.equal(
        "registry.an_identity_may_hold_zero_addresses",
        model.identities[scenario.CAROL_IDENTITY].address_count == 0,
    )
    recovered = _build(identity.Registry)
    check.equal(
        "registry.zero_address_identity_can_recover",
        recovered.add_address(scenario.CAROL_IDENTITY, bytes.fromhex("c9" * 32))
        == "SUCCESS",
    )

    check.equal(
        "registry.counts_agree", model.counts_agree({scenario.ALICE_IDENTITY: 1})
    )
    check.equal(
        "registry.counts_disagree_when_a_seat_is_unaccounted",
        not model.counts_agree({}),
    )

    for name, outcome in sorted(_registry_rejections().items()):
        check.equal(f"registry.reject.{name}", outcome)

    check.agree(
        "registry.max_identity_addresses",
        e.MAX_IDENTITY_ADDRESSES,
        c.MAX_IDENTITY_ADDRESSES,
    )
    check.agree(
        "registry.max_seats_per_identity",
        e.MAX_SEATS_PER_IDENTITY,
        c.MAX_SEATS_PER_IDENTITY,
    )


def _registry_rejections() -> dict[str, str]:
    base = _build(identity.Registry)
    outcomes = {
        "reregistering_an_identity": base.register(
            scenario.ALICE_IDENTITY, scenario.ALICE_KEY, bytes.fromhex("f1" * 32), 1
        ),
        "reregistering_an_account": base.register(
            bytes.fromhex("f2" * 32),
            scenario.ALICE_KEY,
            scenario.ALICE_FIRST_ADDRESS,
            1,
        ),
        "adding_a_linked_account": base.add_address(
            scenario.BOB_IDENTITY, scenario.ALICE_FIRST_ADDRESS
        ),
        "adding_to_an_unregistered_identity": base.add_address(
            bytes.fromhex("f3" * 32), bytes.fromhex("f4" * 32)
        ),
        "removing_an_unlinked_account": base.remove_address(bytes.fromhex("f5" * 32)),
        "claiming_a_seat_for_an_unregistered_identity": base.claim_seat(
            bytes.fromhex("f6" * 32)
        ),
    }

    full = identity.Registry()
    full.register(scenario.BOB_IDENTITY, scenario.BOB_KEY, scenario.BOB_ADDRESS, 1)
    for index in range(c.MAX_IDENTITY_ADDRESSES - 1):
        full.add_address(scenario.BOB_IDENTITY, index.to_bytes(32, "big"))
    outcomes["address_beyond_the_bound"] = full.add_address(
        scenario.BOB_IDENTITY, bytes.fromhex("fe" * 32)
    )
    return outcomes


def check_seat_bound(check: Checker) -> None:
    """The constitution's per-human bound, at 999, 1,000, and 1,001 seats."""
    model = identity.Registry()
    model.register(
        scenario.ALICE_IDENTITY, scenario.ALICE_KEY, scenario.ALICE_FIRST_ADDRESS, 1
    )
    independent = e.Registry()
    independent.register(
        scenario.ALICE_IDENTITY, scenario.ALICE_KEY, scenario.ALICE_FIRST_ADDRESS, 1
    )

    outcomes: dict[int, str] = {}
    for index in range(c.MAX_SEATS_PER_IDENTITY + 1):
        outcome = model.claim_seat(scenario.ALICE_IDENTITY)
        mirror = independent.claim_seat(scenario.ALICE_IDENTITY)
        if outcome != mirror:
            check.failures.append(
                f"seat bound: model {outcome} but derivation {mirror} at {index}"
            )
        outcomes[index + 1] = outcome

    check.equal("seats.claim_999", outcomes[999])
    check.equal("seats.claim_1000", outcomes[c.MAX_SEATS_PER_IDENTITY])
    check.equal("seats.claim_1001", outcomes[c.MAX_SEATS_PER_IDENTITY + 1])
    check.equal(
        "seats.count_stops_at_the_bound",
        model.identities[scenario.ALICE_IDENTITY].seat_count
        == c.MAX_SEATS_PER_IDENTITY,
    )
    check.equal("seats.limit_code", c.CODE_NUMBER["SEAT_LIMIT"])
    check.equal(
        "seats.version_three_could_not_enforce_it",
        "SEAT_LIMIT" not in _version_three_codes(),
    )


def _version_three_codes() -> set[str]:
    from simulation.economy_transition_v3 import contract as v3

    return set(v3.RESULT_CODES.values())


def check_self_referral(check: Checker) -> None:
    """Version three compares accounts; versions four and five compare people."""
    check.equal(
        "referral.self_referral_across_two_addresses_is_refused",
        identity.self_referral(scenario.ALICE_IDENTITY, scenario.ALICE_IDENTITY),
    )
    check.equal(
        "referral.a_different_person_is_accepted",
        not identity.self_referral(scenario.ALICE_IDENTITY, scenario.BOB_IDENTITY),
    )
    check.equal(
        "referral.no_referrer_is_accepted",
        not identity.self_referral(scenario.ALICE_IDENTITY, None),
    )
    registry = _build(identity.Registry)
    check.equal(
        "referral.version_three_would_have_accepted_it",
        scenario.ALICE_FIRST_ADDRESS != scenario.ALICE_SECOND_ADDRESS
        and registry.identity_of(scenario.ALICE_FIRST_ADDRESS)
        == registry.identity_of(scenario.ALICE_SECOND_ADDRESS),
    )


def check_settlement_is_version_three(check: Checker, vector_root: Path) -> None:
    """The twice-imported settlement must still reproduce version three's values."""
    accepted = read_vectors(vector_root / "economy-transition-v3.txt")

    check.agree("cap.windows", e.MINT_ACCUMULATION_CAP, c.MINT_ACCUMULATION_CAP)
    check.equal(
        "cap.matches_version_three",
        str(c.MINT_ACCUMULATION_CAP) == accepted["cap.windows"],
    )
    check.agree(
        "cap.assignment_lag_windows",
        e.ASSIGNMENT_LAG_WINDOWS,
        c.ASSIGNMENT_LAG_WINDOWS,
    )

    for name, window, seats in (
        ("cycle", scenario.CYCLE_WINDOW, scenario.cycle_seats()),
        ("outage", scenario.OUTAGE_WINDOW, scenario.outage_seats()),
    ):
        assignment = settlement.derive_assignment(window, seats)
        key, value = settlement.assignment_entry(assignment)
        check.equal(f"{name}.assignment_key", key.hex())
        check.equal(f"{name}.assignment_value_hex", value.hex())
        check.equal(
            f"{name}.matches_version_three",
            value.hex() == accepted[f"{name}.assignment_value_hex"],
        )
        check.agree(
            f"{name}.assignment_entry_bytes",
            e.entry_bytes(c.CYCLE_ASSIGNMENT_ENTRY, assignment.bitmap_bits),
            len(key) + len(value),
        )

    last = settlement.last_assigned_window(scenario.ASSIGNMENT_HEIGHT)
    records = scenario.assignment_records()
    marks = {
        seat.seat_id: seat.minted_through_window for seat in scenario.cycle_seats()
    }
    for seat_id in sorted(marks):
        collection = settlement.collect(seat_id, marks[seat_id], last, records)
        check.equal(f"mint.total_atomic.{seat_id}", collection.total_atomic)
        check.equal(
            f"mint.matches_version_three.{seat_id}",
            str(collection.total_atomic) == accepted[f"mint.total_atomic.{seat_id}"],
        )
        check.equal(f"mint.windows_walked.{seat_id}", collection.windows_walked)

    accruals, pool = settlement.referral_accrual(
        scenario.CYCLE_WINDOW, scenario.cycle_seats(), scenario.REFERRER_MARKS
    )
    check.equal("referral.referrer_count", len(accruals))
    check.equal("referral.unreferred_pool_atomic", pool)
    check.equal(
        "referral.pool_matches_version_three",
        str(pool) == accepted["referral.unreferred_pool_atomic"],
    )
    check.equal(
        "referral.accrued_to_an_identity",
        accruals.get(scenario.REFERRER_IDENTITY, 0) > 0,
    )
    check.equal(
        "referral.the_key_is_an_identity_not_an_account",
        set(accruals)
        <= {scenario.REFERRER_IDENTITY, scenario.CAPPED_REFERRER_IDENTITY},
    )


def check_state_entries(check: Checker) -> None:
    """The registry as canonical entries, and the two structural invariants."""
    registry = scenario.registry()
    entries = registry.entries()
    check.equal("registry.entry_count", len(entries))
    check.equal(
        "registry.entry_kinds",
        ",".join(c.ENTRY_KINDS[kind] for kind in sorted({key[0] for key in entries})),
    )
    alice = entries[state.hub_identity_key(scenario.ALICE_IDENTITY)]
    check.equal("registry.alice_identity_value_hex", alice.hex())
    check.equal("registry.identity_value_bytes", len(alice))
    check.agree(
        "registry.identity_value_bytes_agrees",
        e.ENTRY_WIDTHS[c.HUB_IDENTITY_ENTRY][1],
        len(alice),
    )
    check.equal(
        "registry.alice_address_value_hex",
        entries[state.hub_address_key(scenario.ALICE_SECOND_ADDRESS)].hex(),
    )
    check.equal(
        "registry.reject.address_count_above_the_bound",
        _identity_refusal(
            lambda: state.hub_identity_value(
                scenario.ALICE_KEY, 1, c.MAX_IDENTITY_ADDRESSES + 1, 0
            )
        ),
    )
    check.equal(
        "registry.reject.seat_count_above_the_bound",
        _identity_refusal(
            lambda: state.hub_identity_value(
                scenario.ALICE_KEY, 1, 1, c.MAX_SEATS_PER_IDENTITY + 1
            )
        ),
    )


def _identity_refusal(build) -> str:
    try:
        build()
    except state.InvalidStateEntry:
        return "INVALID_STATE_ENTRY"
    except Exception as error:  # noqa: BLE001 - shape errors are a distinct class
        return type(error).__name__
    return "accepted"
