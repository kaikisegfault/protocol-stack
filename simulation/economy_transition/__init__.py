"""Independent model of `economy-transition-v2`.

This is a codec and commitment model, not an execution model. The economy's
transitions are already executed by `simulation/founder_economy_v3/`; what had
no implementation was the canonical byte surface a consensus node must reproduce
— the transaction envelope, the state keys, the trees and roots, the receipt,
the numeric result codes, and the performance reallocation commitment.

It implements no cryptographic primitive. A signature is carried as recorded
bytes and never computed, and every digest is SHA-256 over a domain-separated
preimage using the accepted construction.
"""

from . import contract, envelope, genesis, merkle, receipt, scenario, state, winners

__all__ = [
    "contract",
    "envelope",
    "genesis",
    "merkle",
    "receipt",
    "scenario",
    "state",
    "winners",
]
