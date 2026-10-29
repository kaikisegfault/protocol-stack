#!/usr/bin/env python3

"""Two keyed seats past the assignment lag, and a machine that registers a person.

This is the script for M4.3n, requirement 3's network evidence: **a
registration an active machine signs.** Every earlier network registration was
the launch key's, because a machine is active only once its seat meets an
assigned cycle, and the first assignment is at height 86,400. So the model runs
the history alone and the network begins at its head, as `seeded_mints_v9`
does for version nine (ADRs 0096 and 0097).

**The history, executed by the model:**

- Blocks 1 to 8: Alice and Bob register under the launch key. Each buys and
  activates a seat in window 0, Alice seat 0 and Bob seat 1, and registers its
  machine key through kind 23 under the build authority's attestation.
- The quiet heights to 86,399. Alice's machine answers every audit seat 0 is
  issued, through windows 1 and 2, except one issued at the last quiet height,
  whose answer could only land in the head. Bob's machine answers none.
- Block 86,400, the first height of window 3. It assigns window 1, and its
  registry step marks Alice's machine as having met it and leaves Bob's
  unmarked. It is the seed's head, stamped with the clock once the history is
  done. The heights below it are one millisecond apart, for `seeded_mints_v9`'s
  three reasons.

**What the network must then show**, through all four replicas:

- Carol registers under Alice's machine, which signs for seat 0. Her
  registration counts against Alice, the founder who owns the attesting seat.
- Dave's registration under Bob's machine is refused as `MACHINE_NOT_ACTIVE`.
- Erin registers under the launch key, which one active machine is far from
  retiring.
- Carol pays Alice, so the person a machine admitted is a participant.
- Alice's kind-18 and kind-4 mints collect what windows 1 and 2 earned, and a
  second kind-4 mint is refused as `NOTHING_TO_MINT`. Bob's seat failed window
  1, so its permission settles at the mint of the window's best performer
  (ADR 0049). Alice's kind-4 mint therefore issues both seats' 574.3 units.
  Each seat's 342-unit operator leg goes to her escrow, and the institutional
  legs go to their custody.

**Every transaction is built when it is submitted**, for the four-validator
run's reason: an approval is admitted for one slot from the height it is built
for. The nonces are fixed after the history, because every answered audit
moved Alice's.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from simulation.economy_transition_v8.slots import window_first_height
from simulation.economy_transition_v10 import contract as c

from version_ten_chain import ALICE_IDENTITY, BOB_IDENTITY, SEAT_ID, Session

# A seat activated in window 0 is first audited in window 1, and window 1 is
# assigned at the first height of the window two after it.
AUDITED_WINDOW = 1
SEED_HEIGHT = window_first_height(AUDITED_WINDOW + c.ASSIGNMENT_LAG_WINDOWS)
NETWORK_WINDOW = AUDITED_WINDOW + c.ASSIGNMENT_LAG_WINDOWS

BOB_SEAT = SEAT_ID + 1

# The kind-18 mint at any height of window 3 collects windows 1 and 2. Day one,
# window 0, was the registration's airdrop.
VERIFIED_USER_WINDOWS = 2

# What each mint issues, and what of it Alice's escrow receives. Kind 18 pays
# two daily 1.71-unit permissions to her whole. Kind 4 issues two seats' 574.3
# units for window 1, her own and Bob's failed one. Of each seat's share, the
# 342-unit operator leg is hers and the four institutional legs go to custody.
VERIFIED_USER_ISSUED = VERIFIED_USER_WINDOWS * 171_000_000
SEAT_ISSUED = 2 * 57_430_000_000
SEAT_OPERATOR_LEG = 2 * 34_200_000_000

CAROL_IDENTITY = bytes.fromhex("c1" * 32)
DAVE_IDENTITY = bytes.fromhex("d1" * 32)
ERIN_IDENTITY = bytes.fromhex("e1" * 32)


@dataclass(frozen=True)
class Step:
    """One transaction the network is handed, built for the height it is given.

    `refusal` names the result the contract must refuse it with, or is `None`
    for one that must succeed. `issues` is what a mint must add to the issued
    supply, and `credits` what of it must reach Alice's first escrow.
    """

    label: str
    build: Callable[[int], bytes]
    node: int
    refusal: str | None = None
    issues: int | None = None
    credits: int | None = None

    @property
    def code(self) -> int:
        if self.refusal is None:
            raise RuntimeError(f"{self.label} must succeed")
        return c.CODE_NUMBER[self.refusal]


def genesis_stamp(start: int) -> int:
    """The genesis stamp that ends the history one millisecond before `start`."""
    return start - SEED_HEIGHT


class Machine:
    """Seat 0's machine. It answers every audit it is issued, and logs them.

    Seat 1's machine is never asked, which is how it comes to meet nothing.
    """

    def __init__(self, session: Session, last_quiet_height: int) -> None:
        self._session = session
        self._last_quiet_height = last_quiet_height
        self.challenged: list[int] = []
        self.answered: list[int] = []

    def __call__(self, height: int, issued: list[int]) -> list[bytes]:
        if SEAT_ID not in issued:
            return []
        self.challenged.append(height)
        if height >= self._last_quiet_height:
            # `run_quiet_heights` refuses to end holding an input, and this
            # answer could only land in the head.
            return []
        self.answered.append(height)
        alice = self._session.alice
        nonce = self._session.nonce(alice.escrow) + 1
        return [self._session.answers(alice, SEAT_ID, height, nonce)]


def seed(chain, clock) -> Machine:
    """Run the history in `chain`'s model, and stamp its head with `clock()`.

    `chain` is a `cometbft_four_validator_v10_test.Chain` whose genesis was
    stamped by `genesis_stamp`, so that every height below the head falls
    before the history starts.
    """
    session = chain.session
    genesis = session.genesis_timestamp
    alice, bob = session.alice, session.bob

    def stamp_of(height: int) -> int:
        return genesis + height

    for build in (
        lambda h: session.register(alice, h),
        lambda h: session.register(bob, h),
        lambda h: session.buys_seat(alice, SEAT_ID, 1, h),
        lambda h: session.activates_seat(alice, SEAT_ID, 2, h),
        lambda h: session.registers_machine(
            alice, SEAT_ID, session.alice_machine_key, 3, h),
        lambda h: session.buys_seat(bob, BOB_SEAT, 1, h),
        lambda h: session.activates_seat(bob, BOB_SEAT, 2, h),
        lambda h: session.registers_machine(
            bob, BOB_SEAT, session.bob_machine_key, 3, h),
    ):
        height = session.height + 1
        chain.execute_before_launch(build(height), stamp_of(height))
    machine = Machine(session, SEED_HEIGHT - 1)
    chain.run_before_launch(SEED_HEIGHT - 1, stamp_of, machine)
    chain.execute_before_launch(None, clock())
    if session.height != SEED_HEIGHT:
        raise RuntimeError(f"the history ended at height {session.height}")
    return machine


def steps(session: Session) -> tuple[Step, ...]:
    """Seven transactions, two of them refusals, through all four replicas.

    A refused transaction consumes no nonce, so the second seat mint carries
    the nonce the next success would use.
    """
    carol = session.newcomer("carol", CAROL_IDENTITY)
    dave = session.newcomer("dave", DAVE_IDENTITY)
    erin = session.newcomer("erin", ERIN_IDENTITY)
    alice = session.alice
    nonce = session.nonce(alice.escrow) + 1
    return (
        Step("alice's machine registers carol",
             lambda h: session.register_attested(carol, SEAT_ID, h), 0),
        Step("bob's inactive machine cannot register dave",
             lambda h: session.register_attested(dave, BOB_SEAT, h), 1,
             "MACHINE_NOT_ACTIVE"),
        Step("the launch key still registers erin",
             lambda h: session.register(erin, h), 2),
        Step("carol pays alice", lambda h: session.pays(carol, alice, 1, h), 3),
        Step("alice mints her verified-user permissions",
             lambda h: session.mints_verified_user(alice, nonce, h), 0,
             issues=VERIFIED_USER_ISSUED, credits=VERIFIED_USER_ISSUED),
        Step("alice mints what seat 0 earned",
             lambda h: session.mints_seat(alice, SEAT_ID, nonce + 1, h), 1,
             issues=SEAT_ISSUED, credits=SEAT_OPERATOR_LEG),
        Step("a second seat mint collects nothing",
             lambda h: session.mints_seat(alice, SEAT_ID, nonce + 2, h), 2,
             "NOTHING_TO_MINT"),
    )


def check_the_history(session: Session, machine: Machine) -> None:
    """Seat 0's machine was audited in window 1 and answered, and the head
    holds exactly one active machine and an unretired launch key."""
    first = window_first_height(AUDITED_WINDOW)
    audited = [height for height in machine.challenged
               if first <= height < first + c.CYCLE_BLOCKS]
    if not audited:
        raise RuntimeError(f"seat {SEAT_ID} was never audited in window 1")
    unanswered = set(machine.challenged) - set(machine.answered)
    if unanswered - {SEED_HEIGHT - 1}:
        raise RuntimeError(
            f"the machine left audits unanswered: {sorted(unanswered)}")
    if not session.machine_active(SEAT_ID) or session.machine_active(BOB_SEAT):
        raise RuntimeError(
            "the head does not hold seat 0's machine active and seat 1's not")
    if session.launch_retired():
        raise RuntimeError("one active machine retired the launch key")


def check_what_the_network_did(session: Session) -> None:
    """Carol counted against Alice and nobody else, and both mints collected."""
    if session.founder_count(ALICE_IDENTITY, NETWORK_WINDOW) != 1:
        raise RuntimeError(
            "alice's machines registered "
            f"{session.founder_count(ALICE_IDENTITY, NETWORK_WINDOW)} people "
            f"in window {NETWORK_WINDOW}, not 1")
    if session.founder_count(BOB_IDENTITY, NETWORK_WINDOW) != 0:
        raise RuntimeError("bob's inactive machine was counted")
    if session.seat_minted_through(SEAT_ID) != AUDITED_WINDOW:
        raise RuntimeError(
            f"seat {SEAT_ID} has collected through window "
            f"{session.seat_minted_through(SEAT_ID)}, not {AUDITED_WINDOW}")
    if session.enrollment_minted_through(ALICE_IDENTITY) != VERIFIED_USER_WINDOWS:
        raise RuntimeError(
            "alice's enrollment has collected through window "
            f"{session.enrollment_minted_through(ALICE_IDENTITY)}, not "
            f"{VERIFIED_USER_WINDOWS}")
