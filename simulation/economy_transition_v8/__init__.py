"""The `economy-transition-v8` model.

Version eight is version seven with an on-chain carrier for
`uptime-measurement-v1`, so a cycle assignment is derived from evidence the
chain recorded rather than from a schedule a caller supplies.

**The contract half.** `contract.py` declares which of version seven's constants
are carried, revised, and added, and imports the carried ones rather than
copying them. `state.py` re-exports every unchanged key builder and value encoder
and defines the open challenge and the seat window record. `envelope.py` adds the
two bodies and the one admission rule the fee exemption brings. `slots.py` holds
the window and slot grid and the canonical selection preimage.
`uptime_transitions.py` holds the two new transitions as their ordered rejection
conditions, and `schedule.py` derives a window's measured seats from state.
`genesis.py` binds the dispute authority key into the chain identity.

**The execution half.** `ledger.py` holds the state a transition runs against,
`execution.py` and `transitions.py` admit and dispatch the sixteen kinds —
fourteen of them delegated to version seven's own table — `receipt.py` restates
the one consistency rule the two new kinds and twelve new codes move, `block.py`
runs the four ordered steps and the audited heights between them, and `trace.py`
records four scenarios including the first node reward in this repository paid
from uptime the chain itself measured.

It implements no cryptographic primitive. Every digest is SHA-256 over a
domain-separated preimage using the accepted construction.
"""

from . import (
    block,
    contract,
    envelope,
    execution,
    genesis,
    ledger,
    receipt,
    schedule,
    slots,
    state,
    trace,
    transitions,
    uptime_transitions,
)

__all__ = [
    "block",
    "contract",
    "envelope",
    "execution",
    "genesis",
    "ledger",
    "receipt",
    "schedule",
    "slots",
    "state",
    "trace",
    "transitions",
    "uptime_transitions",
]
