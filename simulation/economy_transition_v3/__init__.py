"""Independent model of `economy-transition-v3`.

This is a codec, commitment, and settlement-arithmetic model, not an execution
model. The economy's transitions are executed by
`simulation/founder_economy_v3/`; what this package implements is the canonical
byte surface a consensus node must reproduce — the transaction envelope, the six
verifier messages, the state keys, the trees and roots, the receipt, the numeric
result codes — together with the two pieces of arithmetic version three adds:
the accumulation cap and the bounded mint walk it makes possible.

It is a sibling of `simulation/economy_transition/` rather than a binding into
it, on the test ADR 0029 states: version three changes transitions, inputs, and
the state shape, so a shared implementation would have to branch inside every
affected transition. The one thing it does import from the version-two package
is the RFC 9162 tree, which is an accepted construction both versions must
implement identically rather than a version-two decision.

It implements no cryptographic primitive. A signature is carried as recorded
bytes and never computed, and every digest is SHA-256 over a domain-separated
preimage using the accepted construction.
"""

from . import (
    contract,
    envelope,
    genesis,
    messages,
    receipt,
    scenario,
    settlement,
    state,
    winners,
)

__all__ = [
    "contract",
    "envelope",
    "genesis",
    "messages",
    "receipt",
    "scenario",
    "settlement",
    "state",
    "winners",
]
