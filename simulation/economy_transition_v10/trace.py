"""The recorded version-ten chain: registrations, machine keys, and approvals.

Version ten changes who may sign a registration and what an approval signs, and
this chain records both through blocks, the way a node runs them:

1. **the launch key** registers Alice and Bob, and refuses a forgery, a
   withheld approval, a replayed identity, and a reused signer key;
2. **the seats** are bought and activated under whole-transaction approvals, and
   a version-nine approval is refused;
3. **kind 23** is refused at each of its seven conditions in order, then
   registers Alice's machine and Bob's;
4. **the two replays version nine executed** — a republished posture relax and
   a reused transfer confirmation — are each refused in both forms;
5. **the lifetime** admits a scheme-2 kind at exactly one slot and refuses it one
   height later, and does not govern a transaction with no HUB proof;
6. **the registry step** marks Alice's machine at the assignment of window 1, and
   not Bob's, whose machine answered no audit;
7. **machines register people**: Alice's active machine succeeds, Bob's inactive
   one is refused, a seat with no key is refused, and another machine's
   signature presented under Alice's seat is refused;
8. **the next window**: the count restarts, Alice replaces her key and keeps her
   count and her mark, the old key signs nothing, and every mint is approved
   over the whole transaction.

The population the launch key's retirement and the per-window limit need is in
`population.py`, because no chain of blocks reaches it in a recorded run.

**The chain runs at version nine's ninety seconds a block**, so each window is a
month and the monthly pool pays inside four windows, which is what lets kind 22
be approved here at all.
"""

from __future__ import annotations

from dataclasses import replace

from simulation.economy_transition_v6.trace import Scenario, Step

from . import contract as c
from .block import BlockOutcome, execute_block, run_quiet_heights
from .envelope import decode_signed
from .fixture import (
    ALICE,
    BOB,
    BUILD_AUTHORITY_KEY,
    Builder,
    FAR,
    LAUNCH_KEY,
    Person,
    Signatures,
    genesis,
    machine_key,
    person,
    timestamp_of_height,
)
from .ledger import Ledger

__all__ = [
    "ACTIVATION_HEIGHT",
    "FIRST_ASSIGNMENT_HEIGHT",
    "LIFETIME",
    "Responder",
    "SECOND_ASSIGNMENT_HEIGHT",
    "chain_scenario",
]

LIFETIME = c.APPROVAL_LIFETIME_BLOCKS

ALICE_SEAT = 0
BOB_SEAT = 1
BOB_IDLE_SEAT = 2

# Both seats activate near the end of window 0, so window 1 is the first window
# either is in scope for. Window 1 is assigned at the first height of window 3,
# and window 2 at the first height of window 4.
ACTIVATION_HEIGHT = c.CYCLE_BLOCKS - 10
FIRST_ASSIGNMENT_HEIGHT = 3 * c.CYCLE_BLOCKS
SECOND_ASSIGNMENT_HEIGHT = 4 * c.CYCLE_BLOCKS

CAROL, DAVE, ERIN, FRANK, GRACE, HEIDI, IVAN = (person(i) for i in range(1, 8))
# Someone who presents Alice's signer key as their own first signer.
MALLORY = Person(person(8).identity, person(8).hub_key, ALICE.signer_key)


class Responder:
    """Answers the challenges a quiet run issues to one machine, or none.

    It answers nothing at a height where the run will stop, because the answer
    would belong to a block the run does not execute. A challenge left that way
    costs at most one slot, which the threshold of 18 of 24 absorbs, and the
    count of them is recorded rather than hidden.
    """

    def __init__(
        self, builder: Builder, who: Person, seat_id: int, silent: bool = False
    ) -> None:
        self._builder = builder
        self._who = who
        self._seat_id = seat_id
        self._silent = silent
        self.stop = 0
        self.challenged: list[int] = []
        self.answered: list[int] = []
        self.left_at_a_stop: list[int] = []

    def __call__(self, height: int, issued: list[int]) -> list[bytes]:
        if self._seat_id not in issued:
            return []
        self.challenged.append(height)
        if self._silent:
            return []
        if height == self.stop:
            self.left_at_a_stop.append(height)
            return []
        self.answered.append(height)
        nonce = self._builder.ledger.nonce(self._who.escrow) + 1
        return [self._builder.response(self._who, self._seat_id, height, nonce)]


def _run(scenario: Scenario, signatures: Signatures, steps: list[Step]) -> BlockOutcome:
    ledger = scenario.ledger
    block = execute_block(
        ledger, timestamp_of_height(ledger.height + 1), [s.raw for s in steps],
        signatures.oracle,
    )
    scenario.blocks.append(block)
    scenario.labels.append([step.label for step in steps])
    raw = scenario.notes.setdefault("raw", {})
    raw.update({step.label: step.raw for step in steps})
    scenario.raw_inputs.append(len(steps))
    return block


def _quiet(scenario: Scenario, signatures: Signatures, target: int, *machines) -> None:
    for machine in machines:
        machine.stop = target

    def respond(height: int, issued: list[int]) -> list[bytes]:
        return [raw for machine in machines for raw in machine(height, issued)]

    quiet, recorded = run_quiet_heights(
        scenario.ledger, target, timestamp_of_height, signatures.oracle, respond
    )
    scenario.notes.setdefault("quiet_heights", 0)
    scenario.notes["quiet_heights"] += quiet
    scenario.notes.setdefault("audit_blocks", []).extend(recorded)


def reused(builder: Builder, raw: bytes, nonce: int) -> bytes:
    """The same transaction under another nonce, its HUB field carried over.

    This is how a published approval is re-presented: the signer signs a new
    envelope and the HUB signature is copied from the old one.
    """
    transaction, _signature = decode_signed(raw)
    return builder.sign(replace(transaction, nonce=nonce))


# --- the segments ------------------------------------------------------------


def _launch(scenario: Scenario, build: Builder, signatures: Signatures) -> None:
    h = scenario.ledger.height + 1
    _run(scenario, signatures, [
        Step("launch.alice_registers",
             build.registration(ALICE, c.LAUNCH_ATTESTER, LAUNCH_KEY, h + LIFETIME)),
        Step("lifetime.kind_10_past_the_bound",
             build.registration(ALICE, c.LAUNCH_ATTESTER, BUILD_AUTHORITY_KEY,
                                h + LIFETIME + 1)),
        Step("launch.a_registration_the_launch_key_did_not_sign",
             build.registration(CAROL, c.LAUNCH_ATTESTER, BUILD_AUTHORITY_KEY,
                                h + LIFETIME)),
        Step("kind_10.a_seat_with_no_machine_key",
             build.registration(CAROL, ALICE_SEAT, machine_key(ALICE_SEAT),
                                h + LIFETIME)),
        Step("kind_10.a_seat_above_the_range",
             build.registration(CAROL, c.MAX_SEAT_ID + 1, machine_key(0), h + LIFETIME)),
        Step("launch.bob_registers",
             build.registration(BOB, c.LAUNCH_ATTESTER, LAUNCH_KEY, h + LIFETIME)),
        Step("kind_10.an_identity_registered_twice",
             build.registration(ALICE, c.LAUNCH_ATTESTER, BUILD_AUTHORITY_KEY,
                                h + LIFETIME)),
        Step("kind_10.a_first_signer_already_assigned",
             build.registration(MALLORY, c.LAUNCH_ATTESTER, BUILD_AUTHORITY_KEY,
                                h + LIFETIME)),
    ])


def _seats(scenario: Scenario, build: Builder, signatures: Signatures) -> None:
    ledger = scenario.ledger
    h = ledger.height + 1
    _run(scenario, signatures, [
        Step("approval.kind_2", build.purchase(ALICE, ALICE_SEAT, 1, h + LIFETIME)),
        Step("approval.a_version_nine_approval_is_refused",
             build.version_nine_purchase(BOB, BOB_SEAT, 1, h + LIFETIME)),
        Step("lifetime.kind_2_past_the_bound",
             build.purchase(BOB, BOB_SEAT, 1, h + LIFETIME + 1, referrer=ALICE)),
        Step("seats.bob_buys_a_seat_alice_referred",
             build.purchase(BOB, BOB_SEAT, 1, h + LIFETIME, referrer=ALICE)),
        Step("seats.bob_buys_a_seat_he_never_activates",
             build.purchase(BOB, BOB_IDLE_SEAT, 2, h + LIFETIME)),
    ])
    scenario.skipped_blocks = ledger.advance_to(
        ACTIVATION_HEIGHT - 1, timestamp_of_height(ACTIVATION_HEIGHT - 1)
    )
    h = ledger.height + 1
    _run(scenario, signatures, [
        Step("approval.kind_3", build.activation(ALICE, ALICE_SEAT, 2, h + LIFETIME)),
        Step("seats.bob_activates", build.activation(BOB, BOB_SEAT, 3, h + LIFETIME)),
    ])


def _machine_keys(scenario: Scenario, build: Builder, signatures: Signatures) -> None:
    """Kind 23's seven conditions, each case failing every later one as well.

    Alice's key is registered first, so a refusal can present a key a seat
    already holds. Every refusal before the attestation condition then also
    carries a held key, an attestation the build authority did not sign, and no
    approval, so a kernel that checked any later condition earlier would give a
    different answer, and the vectors would say so.
    """
    h = scenario.ledger.height + 1
    v = h + LIFETIME
    alice_key, bob_key = machine_key(ALICE_SEAT), machine_key(BOB_SEAT)

    def failing(who: Person, seat_id: int, key: bytes, nonce: int) -> bytes:
        return build.machine_registration(
            who, seat_id, key, nonce, v, attester=LAUNCH_KEY, approve=False
        )

    _run(scenario, signatures, [
        Step("approval.kind_23",
             build.machine_registration(ALICE, ALICE_SEAT, alice_key, 3, v)),
        Step("kind_23.a_seat_above_the_range",
             failing(ALICE, c.MAX_SEAT_ID + 1, alice_key, 4)),
        Step("kind_23.an_unpurchased_seat", failing(ALICE, 5, alice_key, 4)),
        Step("kind_23.an_unactivated_seat", failing(ALICE, BOB_IDLE_SEAT, alice_key, 4)),
        Step("kind_23.another_identitys_seat", failing(ALICE, BOB_SEAT, alice_key, 4)),
        Step("kind_23.a_key_another_seat_holds", failing(BOB, BOB_SEAT, alice_key, 4)),
        Step("kind_23.a_key_this_seat_holds", failing(ALICE, ALICE_SEAT, alice_key, 4)),
        Step("kind_23.an_attestation_the_build_authority_did_not_sign",
             failing(BOB, BOB_SEAT, bob_key, 4)),
        Step("kind_23.no_approval",
             build.machine_registration(BOB, BOB_SEAT, bob_key, 4, v, approve=False)),
        Step("kind_23.another_persons_approval",
             build.machine_registration(BOB, BOB_SEAT, bob_key, 4, v,
                                        hub_key=ALICE.hub_key)),
        Step("kind_23.bob_registers_his_machine",
             build.machine_registration(BOB, BOB_SEAT, bob_key, 4, v)),
    ])


def _replays(scenario: Scenario, build: Builder, signatures: Signatures) -> None:
    """Version nine's two executed replays, each refused in both forms."""
    h = scenario.ledger.height + 1
    relax = build.posture(ALICE, 4, False, h + LIFETIME, approve=True)
    confirm = build.confirmed_transfer(ALICE, BOB, 2_000, 6, h + LIFETIME)
    _run(scenario, signatures, [
        Step("approval.kind_17", relax),
        Step("lifetime.a_transfer_with_no_proof_is_not_governed",
             build.transfer(ALICE, BOB, 1_000, 5)),
        Step("approval.kind_19", confirm),
        Step("lifetime.a_tightening_with_no_proof_is_not_governed",
             build.posture(ALICE, 7, True, FAR, approve=False)),
    ])
    _run(scenario, signatures, [
        Step("replay.the_republished_relax", relax),
        Step("replay.the_relax_resigned_under_a_new_nonce", reused(build, relax, 8)),
        Step("replay.the_reused_confirmation", confirm),
        Step("replay.the_confirmation_resigned_under_a_new_nonce",
             reused(build, confirm, 8)),
    ])
    h = scenario.ledger.height + 1
    added = person(99).signer_key
    _run(scenario, signatures, [
        Step("lifetime.kind_15_past_the_bound",
             build.signer_add(ALICE, added, 8, h + LIFETIME + 1)),
        Step("lifetime.kind_15_at_the_bound",
             build.signer_add(ALICE, added, 8, h + LIFETIME)),
    ])


def _machines_register(scenario: Scenario, build: Builder, signatures: Signatures) -> None:
    h = scenario.ledger.height + 1
    v = h + LIFETIME
    _run(scenario, signatures, [
        Step("kind_10.an_active_machine_registers",
             build.registration(CAROL, ALICE_SEAT, machine_key(ALICE_SEAT), v)),
        Step("kind_10.an_inactive_machine",
             build.registration(DAVE, BOB_SEAT, machine_key(ALICE_SEAT), v)),
        Step("kind_10.a_seat_with_no_machine_key_later",
             build.registration(DAVE, BOB_IDLE_SEAT, machine_key(BOB_IDLE_SEAT), v)),
        Step("kind_10.another_machines_signature_under_this_seat",
             build.registration(DAVE, ALICE_SEAT, machine_key(BOB_SEAT), v)),
        Step("launch.still_signs_below_the_cutoff",
             build.registration(ERIN, c.LAUNCH_ATTESTER, LAUNCH_KEY, v)),
    ])


def _next_window(scenario: Scenario, build: Builder, signatures: Signatures) -> None:
    ledger = scenario.ledger
    h = ledger.height + 1
    v = h + LIFETIME
    n = ledger.nonce(ALICE.escrow)
    old_key, new_key = machine_key(ALICE_SEAT), machine_key(ALICE_SEAT, 1)
    winner = scenario.notes["audit_blocks"][-1].settled.winners[0]
    _run(scenario, signatures, [
        Step("kind_10.the_count_restarts_in_the_next_window",
             build.registration(FRANK, ALICE_SEAT, old_key, v)),
        Step("kind_23.the_replacement",
             build.machine_registration(ALICE, ALICE_SEAT, new_key, n + 1, v)),
        Step("kind_10.the_replaced_key_signs_nothing",
             build.registration(GRACE, ALICE_SEAT, old_key, v)),
        Step("kind_10.the_new_key_signs",
             build.registration(GRACE, ALICE_SEAT, new_key, v)),
        Step("approval.kind_4",
             build.mint(ALICE, c.MINT_NODE, n + 2, v, seat_id=ALICE_SEAT)),
        Step("approval.kind_5", build.mint(ALICE, c.MINT_REFERRAL, n + 3, v)),
        Step("approval.kind_18", build.mint(ALICE, c.MINT_VERIFIED_USER, n + 4, v)),
        Step("approval.kind_22",
             build.mint(ALICE, c.MINT_POOL, n + 5, v, seat_id=winner)),
    ])
    scenario.notes["pool_winner"] = winner


def chain_scenario() -> tuple[Scenario, Signatures]:
    signatures = Signatures()
    scenario = Scenario(name="chain", ledger=Ledger.from_genesis(genesis()))
    build = Builder(signatures, scenario.ledger)
    _launch(scenario, build, signatures)
    _seats(scenario, build, signatures)
    _machine_keys(scenario, build, signatures)
    _replays(scenario, build, signatures)

    alice = Responder(build, ALICE, ALICE_SEAT)
    bob = Responder(build, BOB, BOB_SEAT, silent=True)
    _quiet(scenario, signatures, FIRST_ASSIGNMENT_HEIGHT, alice, bob)
    scenario.notes["first_assignment"] = scenario.notes["audit_blocks"][-1]
    scenario.notes["marks_after_the_first_assignment"] = {
        seat: entry.last_met_window
        for seat, entry in scenario.ledger.machine_keys.items()
    }
    _machines_register(scenario, build, signatures)
    _quiet(scenario, signatures, SECOND_ASSIGNMENT_HEIGHT, alice, bob)
    scenario.notes["second_assignment"] = scenario.notes["audit_blocks"][-1]
    _next_window(scenario, build, signatures)
    scenario.notes["responders"] = (alice, bob)
    return scenario, signatures
