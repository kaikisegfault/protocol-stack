#!/usr/bin/env python3

"""A test Founder's lifecycle under version ten, as a network is asked for it.

This is requirement 1 of the M4 goal, moved onto version ten. It is
`founder_lifecycle_v9`'s script, so that ADR 0104's step 7 can delete that one
without taking the requirement's evidence with it. Each step says which replica
receives it and what the contract must answer.

**The order is the lifecycle a person lives:**

- Alice enrolls under the launch key, buys a seat, activates it, and keys its
  machine through kind 23, which version nine did not have.
- Her HUB key admits a second signer, creates a holding escrow, and funds it.
- She gives the holding escrow a signer of its own, and pays from it.
- Then she loses her keys: the HUB key revokes the first signer and then the
  last, and a revoked key is refused wherever it is presented.
- Her HUB key recovers her by admitting a new signer, which pays at once.

**Three claims are refused by name.** Two are what M4's exit criterion means by
"no wallet key alone rewriting identity":

- another person's HUB key cannot admit a signer to Alice's escrow;
- Alice's own signer, presented as the authority, cannot admit one either.

The third is version ten's: a recovery whose approval would outlive its slot is
refused as `APPROVAL_LIFETIME_EXCEEDED`, so a captured recovery cannot be
withheld for later. It comes while Alice holds no signer, when a recovery is
the only thing she can do.

A holding escrow that still holds value cannot be deleted, which is the last
refusal. Every refusal must land on the root an empty block at that height and
stamp would produce: it writes nothing and charges nothing. Then her HUB key
creates an empty escrow and deletes it, so kind 14 runs to both of its answers.

**Every transaction is built when it is submitted.** Version nine's script was
built before the launch. Kinds 13 to 16 are signed whole by the HUB key, so each
always carries a HUB proof, and an approval is admitted for one slot from the
height it is built for.

**Nonces are per escrow.** Alice's first escrow pays for everything her HUB key
does except the holding escrow's own signer, which that escrow pays for, so the
two sequences run independently. A refused transaction consumes no nonce, so
each refusal carries the nonce the next success will use, as distinct bytes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from simulation.economy_transition_v6.identity import escrow_id, signer_id
from simulation.economy_transition_v10 import contract as c

from version_ten_chain import ALICE_IDENTITY, LIFETIME, SEAT_ID, Session

# The amount Alice moves into her holding escrow. It covers the holding
# escrow's own fees and a payment, and leaves it holding value to the end.
HOLDING_FUNDS = 5_000_000

# The holding escrow her HUB key creates second. An escrow is derived from its
# owner and an index, so it is known before the chain exists.
ALICE_HOLDING_ESCROW = escrow_id(ALICE_IDENTITY, 1)

# The escrow she creates third, and deletes while it is empty.
ALICE_EMPTY_ESCROW = escrow_id(ALICE_IDENTITY, 2)

# The keys a Founder's lifecycle adds and loses, derived from these labels.
SECOND_SIGNER = "alice-second-signer"
HOLDING_SIGNER = "alice-holding-signer"
RECOVERED_SIGNER = "alice-recovered-signer"


@dataclass(frozen=True)
class Step:
    """One transaction the network is handed, built for the height it is given.

    `refusal` is the result name the contract must return, or `None` for a
    success. `restart_before` stops and restarts the whole network first.
    """

    label: str
    build: Callable[[int], bytes]
    node: int
    refusal: str | None = None
    restart_before: bool = False

    @property
    def code(self) -> int:
        if self.refusal is None:
            raise RuntimeError(f"{self.label} must succeed")
        return c.CODE_NUMBER[self.refusal]


def lifecycle(session: Session) -> tuple[Step, ...]:
    """Every step of the lifecycle. Nothing here reads the ledger."""
    s = session
    alice, bob = s.alice, s.bob
    first = alice.signer_key
    second, holding, recovered = (
        s.key(SECOND_SIGNER), s.key(HOLDING_SIGNER), s.key(RECOVERED_SIGNER)
    )
    escrow = alice.escrow
    return (
        Step("alice enrolls", lambda h: s.register(alice, h), 0),
        Step("bob enrolls", lambda h: s.register(bob, h), 1),
        Step("alice buys a seat", lambda h: s.alice_buys_seat(1, h), 2),
        Step("alice activates the seat",
             lambda h: s.alice_activates_seat(2, h), 3),
        Step("alice keys the seat's machine",
             lambda h: s.alice_registers_machine(3, h), 0),
        Step("her HUB key admits a second signer",
             lambda h: s.adds_signer(alice, escrow, second, 4, h), 1),
        Step("her HUB key creates a holding escrow",
             lambda h: s.creates_escrow(alice, 5, h), 2),
        Step("the second signer funds the holding escrow",
             lambda h: s.pays_from(alice, second, ALICE_HOLDING_ESCROW, 6, h,
                                   HOLDING_FUNDS), 3),
        Step("the holding escrow gets a signer, and pays for it",
             lambda h: s.adds_signer(alice, ALICE_HOLDING_ESCROW, holding, 1, h),
             0, restart_before=True),
        Step("the holding escrow pays bob",
             lambda h: s.pays_from(alice, holding, bob.escrow, 2, h), 1),
        Step("her HUB key revokes the first signer",
             lambda h: s.revokes_signer(alice, escrow, first, 7, h), 2),
        Step("the revoked first signer is refused",
             lambda h: s.pays_from(alice, first, bob.escrow, 8, h), 3,
             "SIGNER_NOT_FOUND"),
        Step("bob's HUB key cannot admit a signer to alice's escrow",
             lambda h: s.adds_signer(alice, escrow, bob.signer_key, 8, h,
                                     authority=bob.hub_key), 0, "UNAUTHORIZED"),
        Step("alice's own signer cannot admit a signer",
             lambda h: s.adds_signer(alice, escrow, recovered, 8, h,
                                     authority=second), 1, "UNAUTHORIZED"),
        Step("her HUB key revokes the last signer",
             lambda h: s.revokes_signer(alice, escrow, second, 8, h), 2),
        Step("the last revoked signer is refused",
             lambda h: s.pays_from(alice, second, bob.escrow, 9, h), 3,
             "SIGNER_NOT_FOUND"),
        Step("a recovery that would outlive its slot is refused",
             lambda h: s.adds_signer(alice, escrow, recovered, 9, h,
                                     lifetime=2 * LIFETIME), 0,
             "APPROVAL_LIFETIME_EXCEEDED", restart_before=True),
        Step("her HUB key recovers her with a new signer",
             lambda h: s.adds_signer(alice, escrow, recovered, 9, h), 1),
        Step("the recovered signer pays bob",
             lambda h: s.pays_from(alice, recovered, bob.escrow, 10, h), 2),
        Step("a holding escrow with value cannot be deleted",
             lambda h: s.deletes_escrow(alice, ALICE_HOLDING_ESCROW, 11, h), 3,
             "ESCROW_NOT_EMPTY"),
        Step("her HUB key creates an empty escrow",
             lambda h: s.creates_escrow(alice, 11, h), 0),
        Step("her HUB key deletes the empty escrow",
             lambda h: s.deletes_escrow(alice, ALICE_EMPTY_ESCROW, 12, h), 1),
    )


def check_the_identity(session: Session) -> None:
    """What every replica now holds, read from the model they all agreed with.

    The machine key is the seat's and no signer's, so losing every signer must
    leave it where it was.
    """
    if session.signers_of(session.alice.escrow) != {
        signer_id(session.key(RECOVERED_SIGNER))
    }:
        raise RuntimeError("alice's first escrow does not hold the recovered signer")
    if session.signers_of(ALICE_HOLDING_ESCROW) != {
        signer_id(session.key(HOLDING_SIGNER))
    }:
        raise RuntimeError("the holding escrow does not hold its own signer")
    if session.balance(ALICE_HOLDING_ESCROW) == 0:
        raise RuntimeError("the holding escrow was emptied")
    if session.has_escrow(ALICE_EMPTY_ESCROW):
        raise RuntimeError("the deleted escrow is still there")
    if session.machine_key(SEAT_ID) != session.alice_machine_key:
        raise RuntimeError("losing every signer moved the seat's machine key")
