"""Independent model of `economy-transition-v4`.

This is a codec, commitment, and registry model, not an execution model. The
economy's transitions are executed by `simulation/founder_economy_v3/`; what
this package implements is the canonical byte surface a consensus node must
reproduce — the transaction envelope, the eight HUB messages, the state keys,
the trees and roots, the receipt, and the numeric result codes — together with
the HUB registry version four adds and the two counts that keep it consistent.

It is a sibling of `simulation/economy_transition_v3/` rather than a binding
into it, on the test ADR 0029 states: version four changes an authorization
rule, the identity that owns a seat, and the state shape.

**What it deliberately does not duplicate is the settlement.** The accumulation
cap, the cycle-assignment record, and the bounded mint walk are unchanged, so
they are imported from the version-three package rather than copied. A second
implementation of one accepted contract would have nothing keeping the two
equal, which is the reason ADR 0026 gives for sharing and ADR 0029 for not
sharing — and here the condition ADR 0029 names is not met, because none of
that behaviour moved.

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
]
