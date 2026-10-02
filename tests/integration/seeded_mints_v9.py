#!/usr/bin/env python3

"""A seat past the assignment lag, and the mints it has earned.

This is the script for M4.2c, the last of ADR 0096's three slices, and for
requirement 2 of the M4 goal: a kind-4 mint and a kind-18 mint on a network. A
network begun at genesis has nothing to mint for days. So the model runs the
history alone, and the network begins at its head (ADR 0096, ADR 0097).

**The history, executed by the model:**

- Blocks 1 to 4: Alice and Bob register, and Alice buys seat 0 and activates
  it, all in window 0. So window 1 is the first window the seat is audited in.
- The quiet heights to 86,399. Seat 0's machine answers every audit it is
  issued, through all of window 1 and window 2, except one issued at the last
  quiet height. That one's answer would land in the head, which the fast path
  cannot hold for it.
- Block 86,400, the first height of window 3. It assigns window 1 and is the
  seed's head.

**How the history is stamped.** Heights 1 to 86,399 are one millisecond apart
and end one millisecond before the history starts. The head is stamped with the
clock once the history is done. Three rules force this:

- The network's first block carries the head's stamp, and C5 refuses it once
  civil time is a minute past it (ADR 0097). So the head must be stamped at the
  launch.
- A restore never applies C5. So the stamps below the head are free, as long as
  C2 holds.
- At one millisecond a block, the whole history falls inside two minutes of the
  launch. So every window opens in the launch's month, and no settlement depends
  on the date the run happens on.

Both mints count heights, not stamps, so neither amount depends on a stamp.

**What the head holds that a network begun at genesis could not:**

- From height 86,401, Alice's enrollment has completed windows 1 and 2, so a
  kind-18 mint collects two daily permissions.
- Window 1's assignment is written, so a kind-4 mint collects what seat 0
  earned in it.

**The mints are built after the history**, because every answered audit moves
the nonce Alice's next transaction must carry. Each is signed in milliseconds,
so building them costs the launch window nothing.
"""

from __future__ import annotations

from simulation.economy_transition_v8.slots import window_first_height
from simulation.economy_transition_v9 import contract as c

from founder_lifecycle_v9 import Step
from version_nine_chain import (
    ALICE_ESCROW,
    ALICE_IDENTITY,
    BOB_ESCROW,
    SEAT_ID,
    Session,
)

# A seat activated in window 0 is first audited in window 1, and window 1 is
# assigned at the first height of the window two after it.
AUDITED_WINDOW = 1
SEED_HEIGHT = window_first_height(AUDITED_WINDOW + c.ASSIGNMENT_LAG_WINDOWS)

# The kind-18 mint at any height of window 3 collects windows 1 and 2. Day one,
# window 0, was the registration's airdrop.
VERIFIED_USER_WINDOWS = 2


def genesis_stamp(start: int) -> int:
    """The genesis stamp that ends the history one millisecond before `start`."""
    return start - SEED_HEIGHT


class Machine:
    """Seat 0's machine. It answers every audit it is issued, and logs them."""

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
        nonce = self._session.nonce(ALICE_ESCROW) + 1
        return [self._session.alice_answers(height, nonce)]


def seed(chain, clock) -> Machine:
    """Run the history in `chain`'s model, and stamp its head with `clock()`.

    `chain` is a `cometbft_four_validator_v9_test.Chain` whose genesis was
    stamped by `genesis_stamp`, so that every height below the head falls
    before the history starts.
    """
    session = chain.session
    genesis = session.genesis_timestamp

    def stamp_of(height: int) -> int:
        return genesis + height

    for raw in (
        session.register_alice(),
        session.register_bob(),
        session.alice_buys_seat(1),
        session.alice_activates_seat(2),
    ):
        chain.execute_before_launch(raw, stamp_of(session.height + 1))
    machine = Machine(session, SEED_HEIGHT - 1)
    chain.run_before_launch(SEED_HEIGHT - 1, stamp_of, machine)
    chain.execute_before_launch(None, clock())
    if session.height != SEED_HEIGHT:
        raise RuntimeError(f"the history ended at height {session.height}")
    return machine


def mints(session: Session) -> tuple[Step, ...]:
    """Five blocks: both mints, both repeated, and a stranger's.

    A refused transaction consumes no nonce, so each refusal carries the nonce
    the next success would use, and the two repeats differ by kind.
    """
    alice = session.nonce(ALICE_ESCROW) + 1
    bob = session.nonce(BOB_ESCROW) + 1
    return (
        Step("alice mints her verified-user permissions",
             session.alice_mints_verified_user(alice), 0),
        Step("alice mints what seat 0 earned", session.alice_mints_seat(alice + 1), 1),
        Step("a second seat mint collects nothing",
             session.alice_mints_seat(alice + 2), 2, "NOTHING_TO_MINT"),
        Step("bob cannot mint alice's seat",
             session.bob_mints_alices_seat(bob), 3, "UNAUTHORIZED"),
        Step("a second verified-user mint collects nothing",
             session.alice_mints_verified_user(alice + 2), 0, "NOTHING_TO_MINT"),
    )


def check_the_history(machine: Machine) -> None:
    """The machine was audited in the window it is paid for, and answered."""
    first = window_first_height(AUDITED_WINDOW)
    audited = [height for height in machine.challenged
               if first <= height < first + c.CYCLE_BLOCKS]
    if not audited:
        raise RuntimeError(f"seat {SEAT_ID} was never audited in window 1")
    unanswered = set(machine.challenged) - set(machine.answered)
    if unanswered - {SEED_HEIGHT - 1}:
        raise RuntimeError(f"the machine left audits unanswered: {sorted(unanswered)}")


def check_what_was_minted(session: Session) -> None:
    """Both marks advanced to the last window each mint could collect."""
    if session.seat_minted_through() != AUDITED_WINDOW:
        raise RuntimeError(
            f"seat {SEAT_ID} has collected through window "
            f"{session.seat_minted_through()}, not window {AUDITED_WINDOW}")
    if session.enrollment_minted_through(ALICE_IDENTITY) != VERIFIED_USER_WINDOWS:
        raise RuntimeError(
            "alice's enrollment has collected through window "
            f"{session.enrollment_minted_through(ALICE_IDENTITY)}, not "
            f"window {VERIFIED_USER_WINDOWS}")
