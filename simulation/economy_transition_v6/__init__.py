"""Independent model of `economy-transition-v6`.

This is a codec, commitment, and registry model, not an execution model. The
economy's transitions are executed by `simulation/founder_economy_v3/`; what this
package implements is the canonical byte surface a consensus node must
reproduce — the transaction envelope and its two authorization schemes, the six
HUB messages, the state keys, the trees and roots, the receipt, and the numeric
result codes — together with the account architecture version six introduces:
identities, keyless escrows, revocable signers, the per-escrow security posture,
and the verified-user channel's arithmetic.

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
    contract,
    envelope,
    genesis,
    identity,
    messages,
    receipt,
    scenario,
    state,
    verified_user,
)

__all__ = [
    "contract",
    "envelope",
    "genesis",
    "identity",
    "messages",
    "receipt",
    "scenario",
    "state",
    "verified_user",
]
