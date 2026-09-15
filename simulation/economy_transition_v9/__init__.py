"""The `economy-transition-v9` model.

Version nine is version eight with a clock and a monthly settlement, so the two
accepted specifications that describe rules no chain applies —
[`calendar-v1`](../../docs/specifications/calendar-v1.md) and
[`unreferred-pool-payout-v1`](../../docs/specifications/unreferred-pool-payout-v1.md)
— become behaviour independent nodes reproduce.

**The contract half, which is this package as it stands.** `contract.py`
declares which of version eight's constants are carried, revised, and added, and
imports the carried ones rather than copying them. `state.py` re-exports every
unchanged key builder and value encoder and defines the four new entries and the
widened pool value. `genesis.py` binds the genesis timestamp into the chain
identity and writes sixteen economy entries. `envelope.py` adds kind 22's body.
`timeline.py` holds `calendar-v1`'s five rules split into the path that reads a
clock and the path that cannot. `settlement.py` holds the monthly ranking, the
single-pass closing rule, and the two pool identities. `scenario.py` is the
recorded fixture, bound from `simulation.unreferred_pool`'s rather than invented
beside it.

**The execution half.** `ledger.py` holds the state a transition runs against,
`execution.py` and `transitions.py` admit and dispatch the seventeen kinds —
sixteen of them delegated to version eight's own table — `receipt.py` restates
the one consistency rule the added kind moves, `block.py` runs the timestamp
rule, the six-step prologue and the three steps around the transactions, and
`trace.py` records the first chain in this repository that takes value **out** of
the unreferred pool.

**Three modules bind an accepted model rather than restating its judgement**,
and each carries the guard that keeps the binding honest: `timeline` against
`simulation.calendar`, `settlement` against `simulation.unreferred_pool`, and
`envelope`'s mint message against version six's own construction. Where a
restatement was unavoidable — version six's guard is a statement about version
six's kind space, and a ledger holds a head rather than every block it has seen —
the restatement is checked against the accepted artifact instead of trusted.

It implements no cryptographic primitive. Every digest is SHA-256 over a
domain-separated preimage using the accepted construction.
"""

from . import (
    block,
    contract,
    envelope,
    execution,
    genesis,
    header,
    ledger,
    receipt,
    scenario,
    settlement,
    state,
    timeline,
    trace,
    transitions,
)

__all__ = [
    "block",
    "contract",
    "envelope",
    "execution",
    "genesis",
    "header",
    "ledger",
    "receipt",
    "scenario",
    "settlement",
    "state",
    "timeline",
    "trace",
    "transitions",
]
