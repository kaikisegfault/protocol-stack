"""Independent model of `economy-transition-v6`.

Two halves, delivered one slice apart. The first is a codec, commitment, and
registry model: the canonical byte surface a consensus node must reproduce — the
transaction envelope and its two authorization schemes, the six HUB messages,
the state keys, the trees and roots, the receipt, and the numeric result codes —
together with the account architecture version six introduces: identities,
keyless escrows, revocable signers, the per-escrow security posture, and the
verified-user channel's arithmetic.

The second half **executes**. `ledger.py` holds a version-six state,
`execution.py` resolves the acting escrow and applies the shared envelope
checks, `transitions.py` and `value_transitions.py` implement the fourteen
kinds in their specified rejection orders, `block.py` runs ordered blocks with
the cycle-assignment prologue and commits a root, and `trace.py` is the recorded
fixture the execution vectors are taken over. That half exists because a codec
never asks where a transaction gets its arguments — the defect version five was
written to correct — and because three execution rules had to be derived from an
accepted contract that admits two readings of each. ADR 0045 records them.

It is a sibling of `simulation/economy_transition_v4/` rather than a binding into
it, on the test ADR 0029 states: version six changes what an account is, who may
hold one, what authorizes a transaction, and the state shape. That is the
condition ADR 0029 names, met more completely than any version before it.

**What it deliberately does not duplicate is the settlement.** The accumulation
cap, the cycle-assignment record, and the bounded mint walk are unchanged, so
they are imported from the version-three package rather than copied, and the
constants that did not move are imported from version four's. A second
implementation of one accepted contract would have nothing keeping the two equal,
which is the reason ADR 0026 gives for sharing and ADR 0029 for not sharing.

It implements no cryptographic primitive. A signature is carried as recorded
bytes and never computed, and every digest is SHA-256 over a domain-separated
preimage using the accepted construction.
"""

from . import (
    block,
    contract,
    envelope,
    execution,
    genesis,
    identity,
    ledger,
    messages,
    receipt,
    scenario,
    state,
    trace,
    transitions,
    value_transitions,
    verified_user,
)

__all__ = [
    "block",
    "contract",
    "envelope",
    "execution",
    "genesis",
    "identity",
    "ledger",
    "messages",
    "receipt",
    "scenario",
    "state",
    "trace",
    "transitions",
    "value_transitions",
    "verified_user",
]
