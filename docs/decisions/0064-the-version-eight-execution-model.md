# ADR 0064: The version-eight execution model, one derived rule, and three findings

- Status: Accepted
- Date: 2026-09-03

## Context

[`economy-transition-v8`](../specifications/economy-transition-v8.md) and [ADR
0063](0063-the-version-eight-uptime-carrier.md) were accepted on 2026-09-02 with
two transaction kinds, two state entries, twelve result codes, a genesis field,
183 vectors, and a verifier. None of it **runs** a block. The specification's own
required-evidence section says so: "A second file must record what a chain
conforming to this document does."

This is that slice, and it is to version eight what [ADR
0055](0055-the-version-seven-execution-model.md) and
`test-vectors/economy-transition-v7-execution.txt` were to version seven.

Version eight is a narrower change to *transactions* than version seven was —
it adds two and edits none — and a much wider change to **the block**. Version
seven's block does something at a height only if a transaction was offered or a
window boundary was crossed. Version eight's audits every in-scope seat at every
height, resolves the audits twenty heights later, and derives the schedule the
prologue settles instead of accepting one.

So the question this slice had to answer was not what to implement. It was
**what an empty block now means**, and what may still be imported once the kind
space and the code space have both moved.

## Decision

### The execution model joins version eight's package and extends version seven's

`ledger.py`, `execution.py`, `transitions.py`, `receipt.py`, `block.py`, and
`trace.py` join `simulation/economy_transition_v8/`, for ADR 0045's reason: there
is one package per accepted contract and a reader opening it finds the whole
contract.

`Ledger` subclasses version seven's, which subclasses version six's. Four things
are overridden and they are exactly what version eight changes: genesis binds a
dispute authority key, the projection emits the two new entry kinds, the root is
the version-eight root, and the invariants gain the six the specification adds.

`dispatch` delegates every carried kind to version seven's own `dispatch`
function object and adds two rows. `tests/simulation/economy_transition_v8_execution_test.py`
requires that delegation to be version seven's object rather than an equal one.

### Three things are restated, and each because a table moved

Version seven imported version six's `Outcome`, `admit`, and `require_consistent`
unchanged, because it changed neither the transaction kind space nor the result
code space. Version eight changes both, so each of the three would be wrong:

* `Outcome.code` reads `CODE_NUMBER`, and version six's raises on all twelve
  added names. Version eight's `Outcome` is a **subclass** over its own table, so
  a carried transition's version-six outcome and a new transition's version-eight
  one are the same shape. A test requires the two tables to agree on every name
  version six defines, which is what makes the mixed types safe by evidence.
* `admit` decodes through version six's kind table and would refuse a kind-20
  transaction as unknown. The four steps, their order, and their meanings are
  unchanged; only the decoder differs.
* `require_consistent` would refuse a conforming kind-20 receipt as an unknown
  kind and accept a result code no version produces. The restatement adds two
  rows: kinds 20 and 21 issue nothing, and kind 20 charges nothing.

### The uptime evidence is one raw key-to-value map, not a typed shadow

`Ledger.uptime` holds every kind-18 and kind-19 entry and nothing else, and
`Ledger.uptime_context()` hands that very dictionary to the accepted contract
model's `Context`. So `submit_response` and `file_dispute` — the functions the
183 accepted vectors were recorded against — are *the* implementation rather
than siblings of one, and their writes are state writes rather than a model-side
copy that something else has to reconcile.

Every other surface on this ledger is typed. This one is deliberately not, for
the reason ADR 0026, ADR 0029, and ADR 0046 each record: a typed shadow would be
a second encoding of the same entries with nothing keeping the two equal.

## The one rule the execution model had to derive

### A challenge response's debit is zero, so three codes are unreachable for it

The owner answered on 2026-09-02 that **answering a mandatory audit costs an
operator nothing**. The specification draws two encoding consequences: the fee
limit must be zero and is refused at admission, and the nonce is kept. It leaves
a third to the execution model, because it belongs to version seven's shared
envelope checks rather than to kind 20's own conditions: **what the acting escrow
must cover.**

Version six defines that as "the fee, plus a transfer's amount". A kind-20
response is charged no fee and moves no amount, so its debit is zero and both
checks stated over the debit become vacuous. `FEE_LIMIT_TOO_LOW`,
`DEBIT_OVERFLOW`, and `INSUFFICIENT_BALANCE` are therefore all unreachable for
kind 20; the expiry and the two nonce conditions are not.

**The alternative is not neutral.** Leaving the debit at the fixed fee would
refuse a response from an escrow holding less than one fee — so an operator
would have to keep a balance in order to prove the uptime they are paid for,
which is a cost the founder answer removes and a thing an end user must own in
order to be paid. Deducing that from a decided principle is delegated work; the
specification now states the consequence in place, and
`measured.responses_charged_no_fee` records it over a chain where one machine
answered fifty-four audits and paid nothing.

## Three findings

### 1. The prologue precedes the issue step, and at the accepted lag that is unobservable

The specification makes the order normative and argues it: "a window's evidence
is consumed before the block that consumes it issues new challenges."

It is normative and, at `ASSIGNMENT_LAG_WINDOWS` of 2, **the two steps provably
cannot touch the same entry.** A challenge issued at height `h` belongs to
`window_of_height(h)`; its expiry clears a bit in that window or the one before;
the prologue deletes records for `window_of_height(h) - 2`. Those windows are
always disjoint, so both orderings commit to the same state root.

`issue_before_prologue` runs the alternative on a copy of the boundary block, and
`measured.issuing_before_the_prologue_commits_the_same_root` records the
equality. That states what the encoding makes safe rather than claiming an order
a chain could observe — and a later version shortening the lag to one window
would make the vector false here first, which is exactly where it should be
noticed.

### 2. The expiry step following the transactions *is* observable, and it costs a slot

The other ordering is not a formality. `deadline` waits for a real challenge —
selection is unpredictable, which is the point of it — copies the chain, and runs
the same response three ways:

| when | order | result | slots kept |
| --- | --- | --- | ---: |
| `c + 20` | accepted | `SUCCESS` | 24 |
| `c + 21` | accepted | `RESPONSE_TOO_LATE` | 23 |
| `c + 20` | expiry first | `CHALLENGE_NOT_ISSUED` | 23 |

The third row is what "expiring first would shorten the deadline to nineteen
blocks without saying so" costs, stated as a result code and a cleared bit: the
seat answered inside the deadline and lost the slot anyway.

The middle row also demonstrates why condition 7 precedes condition 8. At
`c + 21` the entry has already been deleted, so checking issuance first would
report that a challenge which *was* issued never was.

### 3. An unactivated seat's default activation height is zero, so the activation check is load-bearing

A purchased, unactivated seat has no recorded activation height, and the seat
record carries zero. `first_cycle_window(0)` is 1, so **an unactivated seat reads
as in scope for every window from the first** unless the issue step checks
activation separately. `derive_schedule` cannot make this mistake — it iterates
activated seats only — but the issue step reads the seat table directly.

A mutation removing that check went **uncaught** by the first version of these
vectors, because every seat in every scenario was activated. `measured` now sells
Bob a second seat he never runs, and the mutation is caught by twenty-three
vectors. The general lesson is the one the session record already carries: a
probe that passes is a question about the fixture, not only about the probe.

## `advance_to` is refused once a seat is activated

Version six's shorthand stands in for a run of empty blocks on the argument that
such a block "changes height and nothing else". **Under version eight that
argument is false**: the issue step and the expiry step run at every height, so a
run of transaction-free blocks issues challenges, expires them, and clears slot
bits.

It is still exactly true while no seat is in scope, and no seat is in scope until
one is activated. So `Ledger.advance_to` keeps working for the setup segment of a
trace and **raises** everywhere else, and `block.run_quiet_heights` replaces it:
it executes every height, runs the whole block transition at a height that opens
a window or that a responder has inputs for, and offers a responder the seats a
challenge was just issued to.

The cost is real and it is paid. A window is 28,800 heights, and `measured`
runs 57,609 of them — the tail of window zero, then windows one and two, because
window one's assignment is not due until the first height of window three. What makes that affordable is
`state.state_root_frame`, which splits the root preimage around its height field:
`state_root` is *defined* through it, so the quiet path cannot drift from the
root it is standing in for, and the economy tree is rebuilt only when the issue
step or the expiry step writes — which no transaction can do here, because there
are none.

## Alternatives rejected

**A typed pair of dictionaries for the uptime evidence.** It would match every
other surface on the ledger and would require the two accepted transitions to be
re-implemented against it. Rejected for ADR 0046's reason.

**A retained ring of past state roots, so selection could be re-derived.** The
specification already declines it: the beacon is read once, at the height it
belongs to, and materialising the selection makes every downstream check a state
lookup instead of a digest.

**Deriving `in_span` or the collection mark inside the schedule.** ADR 0055's
rule survives version eight unchanged, and version eight enforces it by shape
rather than by discipline: `derive_schedule` returns three fields, so `_in_scope`
must read the other two from the seat entry and a measurement cannot supply them
even by accident.

**Recording the whole audited run block by block.** 57,609 heights per scenario
would be a vector file nobody reads. What is recorded instead is every block that
carried a transaction, plus aggregates over the run — how many challenges each
machine was issued, how many it answered, how many the chain accepted, and what
the responses cost in total — and the two are cross-checked: the window record
the chain wrote must name exactly the slots the responder's own log says it was
audited in and did not answer.

**Skipping the second window.** Window `w`'s assignment is due at the first
height of `w + 2`, so a chain that measures window 1 must also run window 2, in
which its seats are still in scope and still audited. Skipping it would record a
window the chain never lived through.

## Consequences

`test-vectors/economy-transition-v8-execution.txt` records 434 vectors over four
scenarios. Every kind version eight admits is executed; the coverage claim is
itself a vector, so a later scenario change that stopped reaching one fails.

**The first node reward in this repository derived from evidence the chain
recorded.** In `measured`, Alice answers every one of fifty-four challenges and
writes no window record at all; Bob answers none, loses fifteen slots, and fails
his cycle at nine credited slots against the eighteen the founder-directed
threshold requires. Window 1's assignment then makes Alice the sole winner, she
collects her own permission and the one Bob failed to earn, and the recovery pool
ends empty. Nothing anywhere had to be told that Bob was offline.

**The settlement claim is checked against version seven.** The derived schedule
is compared to an independently stated seat list, and that list is settled by
`economy-transition-v7-vectors/expected.py` — so "the carrier changed no
settlement" is evidence rather than an assertion version eight makes about
itself.

**Eight of nine mutation probes are caught and the ninth is a theorem.** Changing
which slot an expiry clears — the challenge's or the expiry's — is a no-op,
because selection excludes the final twenty heights of every slot and the two are
therefore always the same slot. Two probes are caught by the model's own
invariants rather than by a vector mismatch, and both report the rule they broke
by name: removing the prologue's deletion gives "a seat window record outlived its
retention", and widening the dispute cap by one slot gives "a maximal dispute
failed a fully credited seat", because seventeen slots is 61,200 seconds against
a threshold of 64,800.

**The containment theorem has a margin of zero and the vectors say so.**
Twenty-four slots less the six-slot cap is eighteen slots, which at one hour per
slot is exactly the activity threshold. `disputed` files six disputes against a
perfect machine: it keeps its cycle and loses the winner set to the machine that
was not disputed, and a seventh dispute is refused by the cap.

## Compatibility and independent review

No accepted M1 or version-two through version-seven vector, digest, receipt,
root, or recorded devnet result changes, and none is recomputed here.
`economy-transition-v8.txt`'s 183 contract vectors are unchanged and passing.

The C++20 kernel does not yet compile version eight. Following ADR 0046, it will
*replace* version seven rather than sit beside it, and the storage, application,
transport, node process, and adapter layers each carry a version number and each
still name version seven.

The dispute authority remains one key during the interim ADR 0048 names, and the
sampling security margin still needs the independent review of requirement 15.
Neither is affected by anything decided here.
