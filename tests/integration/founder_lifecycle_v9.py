#!/usr/bin/env python3

"""A test Founder's lifecycle, as the blocks a network is asked to commit.

This is requirement 1 of the M4 goal. The version-nine kernel executes every
step below, and before M4.1 no network had been asked for one past a transfer.
Each step says which replica receives it and what the contract must answer, so
the network run and the offline check read one script and cannot drift apart.

**The order is the lifecycle a person lives:**

- Alice enrolls, buys a seat, and activates it.
- Her HUB key admits a second signer, creates a holding escrow, and funds it.
- She gives the holding escrow a signer of its own, and pays from it.
- Then she loses her keys: the HUB key revokes the first signer and then the
  last, and a revoked key is refused wherever it is presented.
- Her HUB key recovers her by admitting a new signer, which pays at once.

**Two claims are refused by name, because they are what M4's exit criterion
means by "no wallet key alone rewriting identity":**

- another person's HUB key cannot admit a signer to Alice's escrow;
- Alice's own signer, presented as the authority, cannot admit one either.

A holding escrow that still holds value cannot be deleted, which is the last
refusal. Every refusal must land on the root an empty block at that height and
stamp would produce: it writes nothing and charges nothing.

**Nonces are per escrow.** Alice's first escrow pays for everything her HUB key
does except the holding escrow's own signer, which that escrow pays for, so the
two sequences run independently. A refused transaction consumes no nonce, so
each refusal carries the nonce the next success will use, as distinct bytes.
"""

from __future__ import annotations

from dataclasses import dataclass

from simulation.economy_transition_v9 import contract as c
from version_nine_chain import (
    ALICE_ESCROW,
    ALICE_HOLDING_ESCROW,
    BOB_ESCROW,
    Session,
)

# The amount Alice moves into her holding escrow. It covers the holding
# escrow's own fees and a payment, and leaves it holding value to the end.
HOLDING_FUNDS = 5_000_000


@dataclass(frozen=True)
class Step:
    """One block: its label, its transaction, where it enters, what it answers.

    `refusal` is the result name the contract must return, or `None` for a
    success. `restart_before` stops and restarts the whole network first.
    """

    label: str
    raw: bytes
    node: int
    refusal: str | None = None
    restart_before: bool = False

    @property
    def code(self) -> int:
        return c.CODE_NUMBER[self.refusal] if self.refusal else 0


def lifecycle(session: Session) -> tuple[Step, ...]:
    """Every block of the lifecycle, built before the network starts.

    They are built up front because a version-nine network must propose within
    a minute of its genesis stamp (ADR 0088), and signing costs time the launch
    window cannot spare. Nothing here reads the ledger.
    """
    s = session
    second, holding, recovered = (
        s.alice_second_signer, s.alice_holding_signer, s.alice_recovered_signer
    )
    stranger = s.bob_hub
    return (
        Step("alice enrolls", s.register_alice(), 0),
        Step("bob enrolls", s.register_bob(), 1),
        Step("alice buys a seat", s.alice_buys_seat(1), 2),
        Step("alice activates the seat", s.alice_activates_seat(2), 3),
        Step("her HUB key admits a second signer",
             s.alice_adds_signer(ALICE_ESCROW, second, 3), 0),
        Step("her HUB key creates a holding escrow", s.alice_creates_escrow(4), 1),
        Step("the second signer funds the holding escrow",
             s.alice_pays(second, ALICE_ESCROW, ALICE_HOLDING_ESCROW, 5,
                          HOLDING_FUNDS), 2),
        Step("the holding escrow gets a signer, and pays for it",
             s.alice_adds_signer(ALICE_HOLDING_ESCROW, holding, 1), 3,
             restart_before=True),
        Step("the holding escrow pays bob",
             s.alice_pays(holding, ALICE_HOLDING_ESCROW, BOB_ESCROW, 2), 0),
        Step("her HUB key revokes the first signer",
             s.alice_revokes_signer(ALICE_ESCROW, s.alice_signer, 6), 1),
        Step("the revoked first signer is refused",
             s.alice_pays(s.alice_signer, ALICE_ESCROW, BOB_ESCROW, 7), 2,
             "SIGNER_NOT_FOUND"),
        Step("bob's HUB key cannot admit a signer to alice's escrow",
             s.alice_adds_signer(ALICE_ESCROW, s.bob_signer, 7,
                                 authority=stranger), 3, "UNAUTHORIZED"),
        Step("alice's own signer cannot admit a signer",
             s.alice_adds_signer(ALICE_ESCROW, recovered, 7, authority=second),
             0, "UNAUTHORIZED"),
        Step("her HUB key revokes the last signer",
             s.alice_revokes_signer(ALICE_ESCROW, second, 7), 1),
        Step("the last revoked signer is refused",
             s.alice_pays(second, ALICE_ESCROW, BOB_ESCROW, 8), 2,
             "SIGNER_NOT_FOUND"),
        Step("her HUB key recovers her with a new signer",
             s.alice_adds_signer(ALICE_ESCROW, recovered, 8), 3,
             restart_before=True),
        Step("the recovered signer pays bob",
             s.alice_pays(recovered, ALICE_ESCROW, BOB_ESCROW, 9), 0),
        Step("a holding escrow with value cannot be deleted",
             s.alice_deletes_escrow(ALICE_HOLDING_ESCROW, 10), 1,
             "ESCROW_NOT_EMPTY"),
    )
