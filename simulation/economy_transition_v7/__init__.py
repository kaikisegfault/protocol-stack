"""Independent model of `economy-transition-v7`.

Version seven is version six with the per-channel carry deleted from state and
replaced by a recovery pool, so that the node distribution assigns 100% of the
permissions the manifest promises. Four things move — the state key space, the
cycle assignment record's fixed part, the settlement's steps 5 through 7, and
the per-channel conservation identity — and the manifest binding moves from
version two to version three.

`contract.py` declares which of version six's constants are carried, rebound,
revised, and added, and imports the carried ones rather than copying them.
`state.py` re-exports every unchanged key builder and value encoder and defines
the recovery pool entry and the extended cycle assignment record. `settlement.py`
holds the respecified steps 5 through 7 and the mint walk's added term.
`genesis.py` writes fourteen entries where version six wrote twenty-three. And
`conservation.py` holds the two identities over a schedule of cycles and mints,
which is the evidence this version exists to produce.

**It executes transactions.** `ledger.py` holds the state a transition runs
against, `execution.py` and `transitions.py` dispatch the fourteen kinds —
thirteen of them version six's own function objects — `value_transitions.py`
rebinds the one transition that reads a moved surface, `block.py` runs ordered
blocks with the assignment prologue, and `trace.py` records three scenarios that
carry the recovery pool from an unwon cycle to a mint.

It implements no cryptographic primitive. Every digest is SHA-256 over a
domain-separated preimage using the accepted construction.
"""

from . import (
    block,
    conservation,
    contract,
    execution,
    genesis,
    ledger,
    receipt,
    settlement,
    state,
    trace,
    transitions,
    value_transitions,
)

__all__ = [
    "block",
    "conservation",
    "contract",
    "execution",
    "genesis",
    "ledger",
    "receipt",
    "settlement",
    "state",
    "trace",
    "transitions",
    "value_transitions",
]
