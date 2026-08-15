"""Independent model of `economy-transition-v5`.

This is a codec, commitment, and registry model, not an execution model. What
it implements is the canonical byte surface a consensus node must reproduce —
the transaction envelope, the eight HUB messages, the state keys, the trees and
roots, the receipt, and the numeric result codes — together with the HUB
registry and kind 11's corrected reading of who is being linked.

**It deliberately duplicates almost nothing.** Version five is version four
with one field's meaning corrected, so the envelope, the key space, the entry
encodings, the registry, the settlement, the genesis field table, and the
receipt layout are imported from `simulation/economy_transition_v4/` rather
than copied. A second implementation of an accepted contract has nothing
keeping the two equal, which is the reason ADR 0026 gives for sharing and
ADR 0029 for not sharing — and the condition ADR 0029 names, a revised
transition, is not met by a relabelling.

What is written here is what version five defines for itself: the labels and
schema versions that separate one chain from another, kind 11's reading of its
32-byte field, the sender derivation that reading requires, and the transition
entry point that has no parameter through which an account other than the
sender's could be named.

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
