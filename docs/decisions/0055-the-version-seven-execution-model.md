# ADR 0055: The version-seven execution model, and two rules it had to derive

- Status: Accepted
- Date: 2026-08-20

## Context

[`economy-transition-v7`](../specifications/economy-transition-v7.md) and [ADR
0054](0054-economy-transition-v7-the-recovery-pool.md) were accepted on
2026-08-19 with a settlement, two conservation identities, 395 vectors, and a
verifier. None of it **runs** a transaction. The specification's own scope
section says so: "It does not define the version-seven transaction ledger and
its block execution, which mirror how version six separated its contract from
its execution."

This is that slice, and it is to version seven what [ADR
0045](0045-the-version-six-execution-model-and-three-derived-rules.md) and
`test-vectors/economy-transition-v6-execution.txt` were to version six.

Version seven is a narrower change than version six was. Version six replaced
the account architecture and had to implement fourteen transitions. **Version
seven changes no transaction at all**: the envelope, the two authorization
schemes, all fourteen kinds with their ordered rejection conditions, the six HUB
messages, the identity registry, both posture predicates, the receipt layout,
and the thirty-three result codes are version six's, and the specification
incorporates every one of them by reference. Exactly one transition reads a
surface that moved: a winner's collection gained the cycle's pool share.

So the question this slice had to answer was not what to implement. It was
**what may be imported, and what must be stated where a second implementer will
find it.**

## Decision

### The execution model joins version seven's package and imports version six's

`ledger.py`, `execution.py`, `transitions.py`, `value_transitions.py`,
`receipt.py`, `block.py`, and `trace.py` join
`simulation/economy_transition_v7/`, for ADR 0045's reason: there is one
version-seven contract, and a sibling package would hold a second copy of its
state keys and settlement with nothing keeping the two equal.

What is new is how much comes from version six rather than from a keyboard.

**Thirteen of the fourteen transitions are version six's own function objects.**
Not equivalent implementations — the same functions, named one at a time in a
dispatch table so the audit is a list of thirteen identities and one exception.
`mint_node` is the exception. Admission's four steps, the escrow resolution, the
five shared envelope checks in version one's order, and the receipt's
consistency rules are imported for the same reason; only the receipt's version
field differs, and it differs in one octet.

**The ledger subclasses version six's** rather than duck-typing it. Version
six's transitions annotate their parameter `Ledger`, and a sibling class
satisfying the same attributes would make every one of those annotations a false
statement that happened to work. Six methods are overridden and they are exactly what
version seven changes: genesis writes fourteen entries rather than twenty-three,
the prologue writes the extended record and the pool it leaves behind, the
projection emits kind 17 and never kind 7, the root is the version-seven root,
the channel cap predicate reads the version-three manifest, and the carry
identity becomes the channel identity and the backing identity.

**Two module-private helpers are imported across the package boundary**, and the
reason is worth stating rather than leaving to a reader's charity. `_resolve`
and `_envelope_checks` are private to version six because nothing outside its
package should *re-derive* which escrow acts or in what order the five shared
checks fire. Version seven does not re-derive them; it runs the same two
functions. The alternative is an eighty-line second copy of an accepted
rejection order. `tests/simulation/economy_transition_v7_execution_test.py`
requires object identity for every import of this kind, so a copy that appeared
later would fail a test rather than pass silently.

### 1. The assignment reads the mark and the referrer from the seat entry

A `SeatCycle` carries five fields and `uptime-measurement-v1` establishes three
of them: which seat, its uptime, and whether it is inside its own 731 issuance
cycles. `minted_through_window` and the recorded referrer are seat-entry fields
— chain state. **Version seven's block execution reads both from the seat entry
and ignores whatever the measurement supplied.** Version six's took all five
from its caller.

This is a derivation from the accepted text rather than a new rule. Step 3 of
the assignment filters on the accumulation cap, which is defined against the
seat's `minted_through_window`; step 7 accrues to "the seat's **recorded**
referrer identity". Both sentences name state, and only one place holds it.

**What forces it is ADR 0054's own open claim.** That record says `claimable(c)`
is exact rather than a bound, and that the exactness "rests on the accumulation
cap being applied at assignment against the same mark the walk uses". If a
measurement could supply a different mark, a cycle could set an accrued bit in a
window the seat's own mint can no longer reach, and the bit would be unclaimable
while `outstanding` still counted it. That is precisely the stranding the
backing identity exists to make impossible, reintroduced through the one input
the chain does not derive. `conservation.py` had already stated the rule by
leaving the mark out of `CycleSeat` altogether; this puts it where a block
executes.

A measurement naming a seat no transaction ever purchased has no seat entry to
read. It rejects the whole block rather than assigning against an invented zero.

### 2. `claimable` is the mint's own walk, run once per seat

The backing identity says `outstanding(c) = claimable(c) + recovery_pool(c)`.
`claimable` is now defined as running the settlement's `collect` — the function
a kind-4 transaction calls — once for every seat, against the same records.

A second walk written beside the first would be a second implementation of the
contract's most load-bearing derivation, and the identity would then be checking
the model against itself rather than against the mint. The refactor is behaviour
preserving: version seven's 395 accepted settlement vectors and its 82 tests
pass unchanged across it, which is the evidence that the two walks were equal
before one of them was deleted.

### The rejected assignment ordering stops being a matter of cost

This is a finding rather than a choice, and it is the most useful thing the
slice produced.

ADR 0045 had to reject the ordering that writes a cycle assignment **after** a
block's transactions by argument: the specification's sentence about the last
assigned window forces the prologue, and the cost of the other reading is that a
mint in the boundary block succeeds, collects nothing, and forfeits that cycle
permanently. Under version six that block is expensive and **valid** — a node
would accept it.

Under version seven it cannot be built. The window's permissions enter
`outstanding` while the only seat that could have claimed them is already marked
past them, so `claimable + recovery_pool` falls short of `outstanding` on every
Founder Node leg, the backing identity fails, and the block is rejected whole
with the pre-block state preserved. The recorded trace runs both readings on two
copies of one state and records exactly that.

Version six had to argue the ordering. Version seven's own invariant refuses the
alternative.

### The inherited carry map is required to stay empty

Subclassing version six's ledger inherits a `carry` field version seven has no
transition to write and no projection to read. Rather than leave it as dead
state, the conservation check requires it to be empty at every accepted state,
so an entry appearing there is reported by the invariant that runs after every
block. `require_entry_shape` refuses entry kind 7 outright, so a projection that
regressed would fail at the root as well.

## Alternatives rejected

**Copying version six's execution into version seven.** It is 1,400 lines to
change one call, and it is the failure mode ADR 0046 named when it deleted
version four's codec rather than adding beside it. Two copies of an accepted
rejection order have nothing keeping them equal.

**Re-versioning the block header and the ordered transaction tree.** Both are
`protocol-primitives-v1`'s and version seven imposes no narrower rule on either,
so both stay at version one — including the header's schema version field of
`1`. A version-seven header is already unmistakable, because the chain ID it
carries is derived under a version-seven label.

**Re-recording version six's five execution scenarios.** Registration, the
recovery path, the accepted version-one transfer, and both directions of a
posture change are fixed by 512 accepted vectors over transactions version seven
does not touch. Re-recording them would produce a second file that agrees with
the first and says nothing about the recovery pool. The three recorded scenarios
are the pool's round trip, the two block orderings, and a machine past its own
731 cycles.

**Leaving the measurement's mark alone for symmetry with version six.** It would
preserve a hole the backing identity was added to close, in the one input a
chain does not derive.

## Consequences

`test-vectors/economy-transition-v7-execution.txt` holds 412 normative vectors
over three recorded scenarios. `test-vectors/economy-transition-v7.txt` is not
edited: it is the artifact the hosted matrix verified at 395 vectors, and an
accepted vector file is not edited.

The pool scenario ends with `outstanding` at zero and the recovery pool at zero
on every Founder Node channel, with `issued` equal to `assigned_permissions *
leg(c)` exactly. **100% of what the manifest promised for those cycles reached a
beneficiary.** Under version six the same schedule leaves four base permissions
in a carry nothing ever releases. That is the first end-to-end demonstration of
what ADR 0049 directed.

Eight mutation probes were run and all eight are caught: swapping the two block
orderings; trusting the measurement's mark over the seat entry's; dropping the
pool share from the mint walk; keeping version six's receipt version; removing
the backing identity from the invariants; committing the pool the cycle found
rather than the one it left; omitting the recovery pool entry from the
projection; and filtering the winner derivation by span.

Nothing in C++ executes a version-seven transition. The kernel holds version
six's codec and its ten non-seat transitions, and the settlement and four seat
transitions against version seven are the next slice.

## Compatibility and independent review

No accepted specification, ADR, vector file, digest, root, or recorded devnet
result changes. `economy-transition-v7.md` gains an evidence pointer to the
execution model and its vectors, exactly as `economy-transition-v6.md` gained
one for version six's; **no rule in it changes.**

One claim needs review beyond this repository. **That reading the mark from the
seat entry is what a conforming implementation must do** is a derivation from
two sentences of the accepted settlement rather than an explicit rule, and it is
consensus-visible: two implementations that disagreed would write different
accrued bitmaps for the same measured cycle. It is stated here and in the
specification's evidence section so a second implementer finds it, and a later
transition version should state it in the settlement steps outright rather than
leave it derived.
