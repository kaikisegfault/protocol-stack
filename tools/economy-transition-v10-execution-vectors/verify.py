#!/usr/bin/env python3
"""Independently derive and check the economy-transition-v10 execution vectors.

Every outcome the specification's ordered conditions decide is derived twice:
once by `expected.py`, which imports nothing from `simulation/` and is handed
the facts each case was built to have, and once by executing the case with the
version-ten model. Encodings are built field by field and compared with the
model's bytes. State roots are the model's alone and are pinned, not proved,
for the kernel that follows.

`--emit` rewrites the file through the same agreement gate.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import sys
from dataclasses import replace
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import expected as e
from checker import Checker, read_vectors

from simulation.economy_transition_v3.state import bit_is_set
from simulation.economy_transition_v7.state import decode_cycle_assignment_value
from simulation.economy_transition_v9 import receipt as v9receipt
from simulation.economy_transition_v10 import fixture, population, trace
from simulation.economy_transition_v10.block import require_retirement_kept
from simulation.economy_transition_v10.envelope import decode_signed
from simulation.economy_transition_v10.genesis import chain_id, encode
from simulation.economy_transition_v10.ledger import ConservationFailure
from simulation.economy_transition_v10.messages import approval_message
from simulation.economy_transition_v10.state import MachineKey, machine_key_value

LAUNCH = "launch"

# The facts each kind-10 case in the chain was built to have.
CHAIN_REGISTRATIONS = {
    "launch.alice_registers": dict(attester=LAUNCH),
    "lifetime.kind_10_past_the_bound": dict(
        attester=LAUNCH, beyond_lifetime=True, identity_known=True, signed=False),
    "launch.a_registration_the_launch_key_did_not_sign": dict(
        attester=LAUNCH, signed=False),
    "kind_10.a_seat_with_no_machine_key": dict(attester=0, has_key=False),
    "kind_10.a_seat_above_the_range": dict(attester=e.MAX_SEAT_ID + 1),
    "launch.bob_registers": dict(attester=LAUNCH),
    "kind_10.an_identity_registered_twice": dict(
        attester=LAUNCH, identity_known=True, signer_known=True, signed=False),
    "kind_10.a_first_signer_already_assigned": dict(
        attester=LAUNCH, signer_known=True, signed=False),
    "kind_10.an_active_machine_registers": dict(attester=0),
    "kind_10.an_inactive_machine": dict(attester=1, active=False, signed=False),
    "kind_10.a_seat_with_no_machine_key_later": dict(attester=2, has_key=False),
    "kind_10.another_machines_signature_under_this_seat": dict(attester=0, signed=False),
    "launch.still_signs_below_the_cutoff": dict(attester=LAUNCH),
    "kind_10.the_count_restarts_in_the_next_window": dict(attester=0, count=0),
    "kind_10.the_replaced_key_signs_nothing": dict(attester=0, signed=False),
    "kind_10.the_new_key_signs": dict(attester=0, count=1),
}

# The facts each kind-23 case was built to have.
_LATER = dict(key_held=True, attested=False, approval=None)
CHAIN_MACHINE_KEYS = {
    "approval.kind_23": dict(seat_id=0),
    "kind_23.a_seat_above_the_range": dict(
        seat_id=e.MAX_SEAT_ID + 1, purchased=False, activated=False, owned=False,
        **_LATER),
    "kind_23.an_unpurchased_seat": dict(
        seat_id=5, purchased=False, activated=False, owned=False, **_LATER),
    "kind_23.an_unactivated_seat": dict(seat_id=2, activated=False, owned=False, **_LATER),
    "kind_23.another_identitys_seat": dict(seat_id=1, owned=False, **_LATER),
    "kind_23.a_key_another_seat_holds": dict(seat_id=1, **_LATER),
    "kind_23.a_key_this_seat_holds": dict(seat_id=0, **_LATER),
    "kind_23.an_attestation_the_build_authority_did_not_sign": dict(
        seat_id=1, attested=False, approval=None),
    "kind_23.no_approval": dict(seat_id=1, approval=None),
    "kind_23.another_persons_approval": dict(seat_id=1, approval=False),
    "kind_23.bob_registers_his_machine": dict(seat_id=1),
    "kind_23.the_replacement": dict(seat_id=0),
}

# Lifetime cases: whether the transaction carries a HUB proof.
CHAIN_LIFETIMES = {
    "lifetime.kind_2_past_the_bound": True,
    "lifetime.kind_15_past_the_bound": True,
    "lifetime.kind_15_at_the_bound": True,
    "lifetime.a_transfer_with_no_proof_is_not_governed": False,
    "lifetime.a_tightening_with_no_proof_is_not_governed": False,
}

# The two executed replays of version nine, each in both forms, with the
# acting escrow's stored nonce when they were offered: Alice's seven successes.
CHAIN_REPLAYS = (
    "replay.the_republished_relax",
    "replay.the_relax_resigned_under_a_new_nonce",
    "replay.the_reused_confirmation",
    "replay.the_confirmation_resigned_under_a_new_nonce",
)
ALICE_STORED_NONCE_AT_THE_REPLAYS = 7

APPROVED_KINDS = (2, 3, 4, 5, 17, 18, 19, 22, 23)


def _nonce(raw: bytes) -> int:
    return int.from_bytes(raw[72:80], "big")


def _valid_until(raw: bytes) -> int:
    return int.from_bytes(raw[-72:-64], "big")


def _heights(scenario) -> dict[str, int]:
    return {
        label: block.height
        for block, labels in zip(scenario.blocks, scenario.labels)
        for label in labels
    }


def _signed_over(signatures, hub_key: bytes, raw: bytes) -> bool:
    """Whether the HUB field holds a signature this key made over the approval
    message built independently from the bytes."""
    return signatures.oracle.verify(hub_key, e.approval_message(raw), e.hub_field(raw))


# --- genesis --------------------------------------------------------------------


def check_genesis(check: Checker) -> None:
    check.section(
        "The genesis both fixtures run, derived twice. It is the contract "
        "vectors' fixture, so the chain identity is the one they record."
    )
    derived = e.genesis_bytes(
        fixture.NETWORK_ID, fixture.GENESIS_MILLIS, fixture.SUPPLY_LIMIT,
        fixture.FIXED_FEE, fixture.LAUNCH_KEY, fixture.DISPUTE_AUTHORITY_KEY,
        fixture.BUILD_AUTHORITY_KEY,
    )
    check.agree("genesis.bytes", derived, encode(fixture.genesis()))
    check.agree(
        "genesis.chain_id", e.digest(e.CHAIN_ID_LABEL, derived),
        chain_id(fixture.genesis()),
    )


# --- the chain ------------------------------------------------------------------


def check_registrations(check: Checker, results: dict[str, str]) -> None:
    check.section(
        "Kind 10 through blocks: the launch key while it is unretired, active "
        "and inactive machines, a seat with no key, a seat above the range, and "
        "another machine's signature under a seat. Each outcome is read off the "
        "specification's order and agreed with the executed one."
    )
    for label, facts in CHAIN_REGISTRATIONS.items():
        check.agree(f"chain.{label}", e.kind_10_outcome(**facts), results[label])


def check_machine_keys(check: Checker, results: dict[str, str]) -> None:
    check.section(
        "Kind 23 refused at each of its seven conditions in order, including a "
        "key another seat holds and a key this seat holds, then two keys "
        "registered and one replaced."
    )
    for label, facts in CHAIN_MACHINE_KEYS.items():
        if label.startswith("approval."):
            continue  # recorded with the approvals, below
        check.agree(f"chain.{label}", e.kind_23_outcome(**facts), results[label])


def check_lifetimes(check: Checker, scenario, results: dict[str, str]) -> None:
    check.section(
        "The lifetime: a body-carried kind and a scheme-2 kind one height past "
        "the bound are refused, the scheme-2 kind at exactly the bound is "
        "admitted, and a transaction with no HUB proof is not governed however "
        "far its validity reaches."
    )
    heights = _heights(scenario)
    raw = scenario.notes["raw"]
    for label, governed in CHAIN_LIFETIMES.items():
        past = e.lifetime_exceeded(_valid_until(raw[label]), heights[label])
        expected = "APPROVAL_LIFETIME_EXCEEDED" if governed and past else "SUCCESS"
        check.agree(f"chain.{label}", expected, results[label])
        if not governed:
            check.equal(f"chain.{label}.validity_reaches_past_the_bound", past)


def check_replays(check: Checker, scenario, signatures, results) -> None:
    check.section(
        "Version nine's two executed replays, refused in both forms. The "
        "republished bytes carry a spent nonce. Re-signed under the next nonce, "
        "they carry an approval that signed a different transaction."
    )
    raw = scenario.notes["raw"]
    for label in CHAIN_REPLAYS:
        matches = _signed_over(signatures, fixture.ALICE.hub_key, raw[label])
        derived = e.resubmission_outcome(
            nonce=_nonce(raw[label]),
            stored=ALICE_STORED_NONCE_AT_THE_REPLAYS,
            approval_matches=matches,
        )
        check.agree(f"chain.{label}", derived, results[label])


def check_approvals(check: Checker, scenario, signatures, results) -> None:
    check.section(
        "Every body-carried kind approved over the whole transaction. The "
        "approval message is built from the bytes with the HUB field zeroed and "
        "agreed with the model's, and the HUB field holds the person's signature "
        "over exactly that message."
    )
    raw = scenario.notes["raw"]
    for kind in APPROVED_KINDS:
        label = f"approval.kind_{kind}"
        transaction, _signature = decode_signed(raw[label])
        check.agree(
            f"chain.{label}.message_sha256",
            hashlib.sha256(e.approval_message(raw[label])).hexdigest(),
            hashlib.sha256(approval_message(transaction)).hexdigest(),
        )
        signed = _signed_over(signatures, fixture.ALICE.hub_key, raw[label])
        check.equal(f"chain.{label}.signed_over_the_whole_transaction", signed)
        check.agree(
            f"chain.{label}", "SUCCESS" if signed else "UNAUTHORIZED", results[label]
        )
    label = "approval.a_version_nine_approval_is_refused"
    signed = _signed_over(signatures, fixture.BOB.hub_key, scenario.notes["raw"][label])
    check.equal(f"chain.{label}.signs_another_message", not signed)
    check.agree(f"chain.{label}", "UNAUTHORIZED", results[label])


def check_registry_in_the_chain(check: Checker, scenario) -> None:
    check.section(
        "The registry step at the assignment of window 1. Alice's machine "
        "answered every audit and is marked; Bob's answered none, lost a slot "
        "for every slot it was challenged in, and is not."
    )
    alice, bob = scenario.notes["responders"]
    check.equal("chain.audit.alice_challenged", len(alice.challenged))
    check.equal(
        "chain.audit.alice_answered_every_challenge",
        alice.answered == alice.challenged and not alice.left_at_a_stop,
    )
    lost = {
        (height % e.CYCLE_BLOCKS) // 1_200
        for height in bob.challenged
        if e.window_of_height(height) == 1
    }
    credited = e.SLOTS_PER_WINDOW - len(lost)
    check.equal("chain.audit.bob_window_1_credited_slots", credited)
    marks = scenario.notes["marks_after_the_first_assignment"]
    check.agree("chain.registry.alice_mark_after_window_1", 1, marks[0])
    check.agree(
        "chain.registry.bob_mark_after_window_1", 1 if e.met(credited) else 0, marks[1]
    )
    for name in ("first_assignment", "second_assignment"):
        block = scenario.notes[name]
        check.equal(f"chain.registry.{name}.height", block.height)
        check.agree(f"chain.registry.{name}.active_machines", 1, block.active_machines)
        check.equal(f"chain.registry.{name}.root", block.resulting_state_root)
    check.equal(
        "chain.registry.launch_key_unretired",
        scenario.ledger.launch_retired_at is None,
    )


def check_entries(check: Checker, scenario) -> None:
    check.section(
        "The machine-key entries the chain ends with, built from the table. "
        "Alice's replacement kept her mark from window 2 and her count of two "
        "in window 4, and moved the key and the height."
    )
    heights = _heights(scenario)
    ledger = scenario.ledger
    expected_alice = e.machine_key_value(
        fixture.machine_key(0, 1), fixture.BUILD_DIGEST,
        heights["kind_23.the_replacement"], 2, 4, 2,
    )
    expected_bob = e.machine_key_value(
        fixture.machine_key(1), fixture.BUILD_DIGEST,
        heights["kind_23.bob_registers_his_machine"], 0, 0, 0,
    )
    check.agree("chain.entry.seat_0", expected_alice, machine_key_value(ledger.machine_keys[0]))
    check.agree("chain.entry.seat_1", expected_bob, machine_key_value(ledger.machine_keys[1]))
    check.equal(
        "chain.entry.the_replaced_key_has_no_owner",
        fixture.machine_key(0) not in ledger.machine_key_owners,
    )
    check.equal(
        "chain.entry.the_new_key_names_its_seat",
        ledger.machine_key_owners.get(fixture.machine_key(0, 1)) == 0,
    )


def check_receipts(check: Checker, scenario, receipts: dict[str, bytes]) -> None:
    check.section(
        "Receipts at version 10, built field by field. A machine registration "
        "issues the entry airdrop and charges nothing; kind 23 charges the fee "
        "and issues nothing; a refusal does neither."
    )
    raw = scenario.notes["raw"]
    cases = (
        ("approval.kind_23", 23, "SUCCESS", fixture.FIXED_FEE, 0),
        ("kind_10.an_active_machine_registers", 10, "SUCCESS", 0,
         e.VERIFIED_USER_DAILY_ATOMIC),
        ("kind_10.an_inactive_machine", 10, "MACHINE_NOT_ACTIVE", 0, 0),
        ("kind_10.a_seat_with_no_machine_key", 10, "MACHINE_KEY_NOT_FOUND", 0, 0),
        ("lifetime.kind_15_past_the_bound", 15, "APPROVAL_LIFETIME_EXCEEDED", 0, 0),
    )
    for label, kind, result, fee, issued in cases:
        check.agree(
            f"chain.receipt.{label}",
            e.receipt_bytes(raw[label], kind, result, fee, issued),
            receipts[label],
        )
    check.equal(
        "chain.receipt.version_nine_refuses_a_version_ten_receipt",
        _refused(v9receipt.decode, receipts["approval.kind_23"]),
    )


def _refused(function, raw: bytes) -> bool:
    try:
        function(raw)
    except Exception:  # InvalidReceipt, by construction
        return True
    return False


def check_blocks(check: Checker, scenario) -> None:
    check.section(
        "Two blocks' headers and identifiers, built field by field: the first "
        "assignment and the last block. The header keeps version nine's schema "
        "version and bytes. The roots are the model's, pinned for the kernel."
    )
    ledger = scenario.ledger
    for name, block in (
        ("first_assignment", scenario.notes["first_assignment"]),
        ("last", scenario.blocks[-1]),
    ):
        derived = e.block_header(
            ledger.chain_id, block.height, block.timestamp,
            bytes.fromhex(block.previous_state_root),
            e.tx_tree(block.admitted_ids),
            bytes.fromhex(block.resulting_state_root),
            len(block.executed),
        )
        check.agree(f"chain.block.{name}.header", derived, block.header)
        check.agree(
            f"chain.block.{name}.block_id",
            e.digest(e.BLOCK_ID_LABEL, derived).hex(), block.block_id,
        )
    results = scenario.results()
    refused = sum(
        1 for facts in CHAIN_REGISTRATIONS.values()
        if e.kind_10_outcome(**facts) != "SUCCESS"
    ) + sum(
        1 for facts in CHAIN_MACHINE_KEYS.values()
        if e.kind_23_outcome(**facts) != "SUCCESS"
    )
    executed = sum(
        1 for label in (*CHAIN_REGISTRATIONS, *CHAIN_MACHINE_KEYS)
        if results[label] != "SUCCESS"
    )
    check.agree("chain.refusals_among_kinds_10_and_23", refused, executed)
    check.equal(
        "chain.every_refusal_left_the_root_unchanged",
        sum(block.atomic_failures for block in scenario.blocks)
        == sum(1 for r in scenario.results().values() if r != "SUCCESS"),
    )
    check.equal("chain.final_root", ledger.state_root())
    check.equal("chain.final_height", ledger.height)


# --- the population ---------------------------------------------------------------


def _cutoff_facts() -> dict[str, dict]:
    plan = population.CUTOFF_PLAN
    first = e.first_cycle_window(population.ACTIVATION_HEIGHT)
    retired_at = e.retirement_height(population.MACHINES, first, plan, 31)
    heights = {
        "launch.still_signs_at_ninety_nine": 3,
        "launch.refused_once_retired": 4,
        "launch.not_revived_when_the_count_falls": 5,
    }

    def retired(window: int) -> bool:
        return retired_at is not None and window * e.CYCLE_BLOCKS + 1 >= retired_at

    def active(seat: int, window: int) -> bool:
        due = window - e.ASSIGNMENT_LAG_WINDOWS
        return due >= first and e.met(plan.get(due, {}).get(seat, e.SLOTS_PER_WINDOW))

    facts = {
        "founder_registers": dict(attester=LAUNCH),
        "crossed.a_key_signing_for_another_seat": dict(
            attester=2, active=active(2, 3), signed=False),
        "crossed.a_genuine_signature_under_another_seat": dict(
            attester=2, active=active(2, 3), signed=False),
        "limit.the_first": dict(attester=0, active=active(0, 3), count=0),
        "limit.the_thousandth": dict(
            attester=0, active=active(0, 3),
            count=e.MACHINE_REGISTRATIONS_PER_WINDOW - 1),
        "limit.a_forgery_naming_a_full_machine": dict(
            attester=0, active=active(0, 3), signed=False,
            count=e.MACHINE_REGISTRATIONS_PER_WINDOW),
        "limit.the_thousand_and_first": dict(
            attester=0, active=active(0, 3), count=e.MACHINE_REGISTRATIONS_PER_WINDOW),
        "limit.another_machine_still_signs": dict(attester=1, active=active(1, 3)),
        "limit.the_count_restarts_in_the_next_window": dict(
            attester=0, active=active(0, 4), count=0),
    }
    for label, window in heights.items():
        facts[label] = dict(attester=LAUNCH, retired=retired(window))
    return facts


def check_cutoff(check: Checker, harness) -> None:
    plan = population.CUTOFF_PLAN
    first = e.first_cycle_window(population.ACTIVATION_HEIGHT)
    check.section(
        "101 machines through the registry step. The count is derived from the "
        "uptime plan alone: a machine counts when its seat is in scope and "
        "credited with at least 18 of 24 slots. At the window-0 assignment no "
        "seat is in scope and every one of the 101 keys is unmarked, so the "
        "count is zero (ADR 0103). It is 99 at window 1's, 100 at window 2's, "
        "which retires the launch key, and 50 at window 3's, which does not "
        "revive it."
    )
    for window in (2, 3, 4, 5, 6, population.CAP_RUN_WINDOW):
        due = window - e.ASSIGNMENT_LAG_WINDOWS
        check.agree(
            f"cutoff.registry.window_{due}_count",
            e.active_count(due, population.MACHINES, first, plan),
            harness.windows[window].active_machines,
        )
    check.equal(
        "cutoff.registry.unmarked_keys_at_the_window_0_assignment",
        population.MACHINES,
    )
    check.equal(
        "cutoff.registry.unmarked_keys_alone_would_reach_the_cutoff",
        population.MACHINES >= e.LAUNCH_RETIREMENT_ACTIVE_MACHINES,
    )
    check.agree(
        "cutoff.registry.retired_at_height",
        e.retirement_height(population.MACHINES, first, plan, 31),
        harness.ledger.launch_retired_at,
    )
    check.equal(
        "cutoff.registry.retired_exactly_once",
        sum(1 for outcome in harness.windows.values() if outcome.retired) == 1,
    )
    check.section(
        "Kind 10 across the population: the launch key at 99 and after the "
        "cutoff, two machines' signatures crossed, the 1,000th and 1,001st "
        "registration of one machine in one window, a forgery naming the full "
        "machine, and the count restarting in the next window."
    )
    for label, facts in _cutoff_facts().items():
        check.agree(f"cutoff.{label}", e.kind_10_outcome(**facts), harness.results[label])
    check.agree(
        "cutoff.limit.count_after_the_thousandth",
        e.MACHINE_REGISTRATIONS_PER_WINDOW,
        harness.notes["count_after_the_thousandth"],
    )
    for label, kind, result in (
        ("limit.the_thousand_and_first", 10, "REGISTRATION_LIMIT"),
        ("launch.refused_once_retired", 10, "LAUNCH_KEY_RETIRED"),
    ):
        check.agree(
            f"cutoff.receipt.{label}",
            e.receipt_bytes(harness.raw[label], kind, result, 0, 0),
            harness.receipts[label],
        )


def check_cap(check: Checker, harness) -> None:
    check.section(
        "A seat that never collects is capped from window 31, so its cycle there "
        "accrues nothing, and its machine is marked all the same: met is the "
        "uptime test, whatever the cap says."
    )
    mark = 0  # the window before a seat's first cycle window
    capped = mark + e.MINT_ACCUMULATION_CAP + 1
    record = decode_cycle_assignment_value(harness.ledger.assignments[capped])
    model_capped = min(
        window for window, raw in harness.ledger.assignments.items()
        if not bit_is_set(decode_cycle_assignment_value(raw)["accrued_bitmap"], 0)
        and window >= 1
    )
    check.agree("cap.first_capped_window", capped, model_capped)
    check.equal(
        "cap.the_capped_cycle_accrued_nothing",
        not bit_is_set(record["accrued_bitmap"], 0),
    )
    check.agree("cap.the_capped_machine_is_marked", capped,
                harness.ledger.machine_keys[0].last_met_window)
    check.equal("cap.final_root", harness.ledger.state_root())


def check_span(check: Checker, harness) -> None:
    check.section(
        "One machine past its seat's 731 cycles. The cycle after the span "
        "accrues nothing, and the machine is still marked, because a seat past "
        "its span stays in scope and measured."
    )
    first = e.first_cycle_window(population.ACTIVATION_HEIGHT)
    last_span = first + e.ISSUANCE_CYCLES_PER_SEAT - 1
    accrued = [
        window for window, raw in harness.ledger.assignments.items()
        if bit_is_set(decode_cycle_assignment_value(raw)["accrued_bitmap"], 0)
    ]
    check.agree("span.last_span_window", last_span, max(accrued))
    past = decode_cycle_assignment_value(harness.ledger.assignments[last_span + 1])
    check.equal(
        "span.the_cycle_past_the_span_accrued_nothing",
        not bit_is_set(past["accrued_bitmap"], 0),
    )
    check.agree("span.the_machine_is_marked_past_its_span", last_span + 1,
                harness.ledger.machine_keys[0].last_met_window)
    check.equal("span.final_root", harness.ledger.state_root())


# --- the invariants ------------------------------------------------------------------


def check_invariants(check: Checker, harness) -> None:
    check.section(
        "Each of the seven invariants, broken by a probe on a copy of the "
        "population's ledger. The first six are the ledger's own checks and "
        "the seventh is the block's, because it is about two heights."
    )
    check.equal("invariants.the_population_satisfies_all", not harness.ledger.conservation_failures())
    probes = {
        "1_a_key_on_an_unactivated_seat": (
            lambda l: (l.machine_keys.__setitem__(200, MachineKey(b"\x99" * 32, fixture.BUILD_DIGEST, 1)),
                       l.machine_key_owners.__setitem__(b"\x99" * 32, 200)),
            "a machine key names a seat that is not activated",
        ),
        "2_an_owner_entry_missing": (
            lambda l: l.machine_key_owners.pop(fixture.machine_key(0)),
            "a machine key has no owner entry naming its seat",
        ),
        "3_two_seats_holding_one_key": (
            lambda l: l.machine_keys.__setitem__(1, MachineKey(fixture.machine_key(0), fixture.BUILD_DIGEST, 1)),
            "two machine-key entries hold the same key",
        ),
        "4_a_mark_for_an_unassigned_window": (
            lambda l: _rewrite(l, 0, last_met_window=l.height // e.CYCLE_BLOCKS - 1),
            "a machine was marked for a window not yet assigned",
        ),
        "5_a_count_for_a_future_window": (
            lambda l: _rewrite(l, 0, registration_window=l.height // e.CYCLE_BLOCKS + 1),
            "a machine counted registrations for a future window",
        ),
        "6_a_count_above_the_limit": (
            lambda l: _rewrite(l, 0, registrations_in_window=e.MACHINE_REGISTRATIONS_PER_WINDOW + 1),
            "a machine signed more registrations than its limit",
        ),
    }
    for name, (probe, failure) in probes.items():
        ledger = copy.deepcopy(harness.ledger)
        probe(ledger)
        check.equal(f"invariants.{name}", failure in ledger.registry_failures())
    retired = harness.ledger.launch_retired_at
    for name, after in (("7_a_retirement_removed", None), ("7_a_retirement_moved", retired + 1)):
        ledger = copy.deepcopy(harness.ledger)
        ledger.launch_retired_at = after
        try:
            require_retirement_kept(retired, ledger)
            caught = False
        except ConservationFailure:
            caught = True
        check.equal(f"invariants.{name}", caught)


def _rewrite(ledger, seat: int, **fields) -> None:
    ledger.machine_keys[seat] = replace(ledger.machine_keys[seat], **fields)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vectors", type=Path, required=True)
    parser.add_argument("--emit", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    check = Checker(read_vectors(args.vectors), emit=args.emit)

    scenario, signatures = trace.chain_scenario()
    results = scenario.results()
    receipts = scenario.receipts()
    cutoff = population.cutoff_run()
    span = population.span_run()

    check_genesis(check)
    check_registrations(check, results)
    check_machine_keys(check, results)
    check_lifetimes(check, scenario, results)
    check_replays(check, scenario, signatures, results)
    check_approvals(check, scenario, signatures, results)
    check_registry_in_the_chain(check, scenario)
    check_entries(check, scenario)
    check_receipts(check, scenario, receipts)
    check_blocks(check, scenario)
    check_cutoff(check, cutoff)
    check_cap(check, cutoff)
    check_span(check, span)
    check_invariants(check, cutoff)
    check.require_full_coverage()

    if check.failures:
        for failure in check.failures:
            print(f"FAIL {failure}", file=sys.stderr)
        return 1
    if args.emit:
        written = check.write(args.vectors)
        print(f"wrote {written} vectors to {args.vectors}")
        return 0
    print(f"economy-transition-v10-execution: {check.checked} vectors verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
