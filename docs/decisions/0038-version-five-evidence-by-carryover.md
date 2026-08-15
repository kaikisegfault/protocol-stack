# ADR 0038: Version five's evidence, and proving a negative by carryover

- Status: Accepted
- Date: 2026-08-15

## Context

[`economy-transition-v5`](../specifications/economy-transition-v5.md) and
[ADR 0037](0037-economy-transition-v5-the-kind-eleven-identity.md) were accepted
on 2026-08-15 with no model, no vectors, and no verifier. That was recorded as a
departure at the time: every earlier transition contract arrived with its
evidence in one slice. This slice supplies it.

Version five is unusual among the transition contracts, and the unusual part
drives every decision here. Versions two, three, and four each revised
behaviour: new kinds, new state, new authorization rules, new result codes.
Version five changes **one field's meaning, eight labels, and four version
fields**, and its central claim is negative — "everything else in version four
carries over unchanged and is incorporated by reference".

A negative claim is the hard kind to evidence. No derivation demonstrates the
absence of a change: a body width that quietly moved would simply be derived at
its new value, recorded at its new value, and pass.

## Decision

### The model imports version four rather than restating it

`simulation/economy_transition_v5/` imports the envelope, the key space, the
registry, the settlement, the genesis field table, and the receipt layout from
`simulation/economy_transition_v4/`, and defines only the labels, the schema
versions, kind 11's reading of its 32-byte field, the sender derivation that
reading requires, and the transition entry point.

This is the test ADR 0029 states, applied in the direction it points. ADR 0026
chose one shared implementation for `escrow-payout-v2` because the two versions
differed only in strings, and named the condition under which that inverts: a
version that revises a transition. Version four met it — a new authorization
rule, a new identity root, a changed state shape — and earned a sibling
package. **A relabelling does not meet it.** Copying twelve kind identifiers,
twelve entry kinds, and twenty-six result codes to change eight strings would
produce a second implementation of an accepted contract with nothing keeping
the two equal, which is exactly the defect both ADRs exist to avoid.

### The independent derivation loads version four's rather than transcribing it

`tools/economy-transition-v5-vectors/expected.py` loads version four's accepted
`expected.py` by path — it is a separate file with the same name, so the load is
explicit — re-exports it by name, and overrides the eight message labels, the
four version fields, kind 11's body table, and the identity-source table.

The property that makes an `expected.py` worth having is that it imports
nothing from `simulation/`. Loading version four's preserves that exactly, and
version four's is not a draft: the hosted matrix verified it over 441 vectors on
2026-08-15. Re-transcribing the version-one transfer field table, the
constitution's capacity figures, the entry widths, and the RFC 9162
construction by hand a second time would put a transcription risk into the one
artifact whose whole job is to be a second opinion, and would leave two hand
restatements of one accepted document with nothing keeping them equal.

**The alternative was considered and rejected on that ground rather than on
size.** A fresh transcription would be genuinely independent of version four's,
and that independence buys nothing here: the documents behind it did not
change, so a disagreement between the two transcriptions could only be a
transcription error, and the version four one is the one already checked.

### The vector file is complete, and is read a second time against version four's

`test-vectors/economy-transition-v5.txt` records all 550 values under version
five's labels, because the specification requires it to fix everything version
four's file fixes. Every value is still derived twice: once from the derivation
and once from a live run of the model.

**And then the whole file is compared against
`test-vectors/economy-transition-v4.txt`.** Every key version four records is
classified in advance as carried, renamed, or revised. The classification must
be total; a carried key must hold version four's exact value; a revised key
must hold a different one; a renamed key must be absent under its old name and
present under its new one carrying version four's value.

That is the answer to the negative claim, and it fails closed in both
directions. A change nobody declared lands in the carried set and its values
disagree. A key declared revised that did not actually move lands in the
revised set and its values agree. Both were demonstrated by mutation before
this was accepted.

The result: **409 carried, 30 revised, 2 renamed**, and the file records that no
envelope, admission, code-space, state-key, storage, or settlement vector is
among the revised — which is a sharper statement of "the bytes did not move"
than any derivation could make.

A second reading of the same claim runs over the two Python packages rather
than the two files, in
`tests/simulation/economy_transition_v5_carryover_test.py`. It catches the
different defect: a constant that moved without any vector reaching it.

### A boolean vector may only be true

Probing this slice's own evidence exposed a hole none of the above closes: a
defect present *before* the vector file was first written is recorded at its
wrong value and then faithfully reproduced, so nothing ever fails. Two forms of
it appeared here.

A derivation that returns `False` is faithfully recorded as `false`. That is
precisely the defect M3.8b found in an accepted file —
`state.no_entry_is_keyed_by_seat_cycle=false` records the negation of what its
own name asserts — and it survived because nothing said a boolean vector cannot
be false. So `Checker.equal` now treats a derived `False` as a failure rather
than a value. Neither this file nor version four's records a single `false`, so
the rule costs nothing and closes the hole; negative properties are phrased
positively instead.

And a value derived twice from two restatements of the same formula proves only
that the two restatements agree. The account derivation is therefore checked
against `test-vectors/protocol-primitives-v1.txt`, which records the identifier
of the exact public key the fixture sends from. With the domain octet changed in
*both* the model and the derivation, generation itself now refuses.

Both rules, and the naming rule that a vector must assert no more than its value
establishes, are recorded in `docs/engineering/verification.md` so the next
version inherits them.

## Consequences

**Version five's carried values rest on version four's accepted file.** That is
a real dependency and it is stated rather than hidden: if
`test-vectors/economy-transition-v4.txt` were ever edited, version five's
carryover check would move with it. Version four is retained unedited for
exactly this kind of reason, and its own specification and the documentation
index both record that it is superseded and must not be picked up as the newest
contract.

**The slice adds one derivation the repository did not have.** Version five is
the first transition contract whose evidence needs the accepted version-one
account derivation, `H(D("protocol-stack:v1:account") || 0x01 || public_key)`,
because it is the first in which a signed message is built from the sender
rather than from an argument the caller supplies. Version four's fixture could
declare account identifiers as constants precisely because nothing derived
them, and that is not a coincidence: **the defect and the missing derivation are
the same fact seen from two sides.**

**One table is new and is not a relabelling.** `MESSAGE_IDENTITY_SOURCE` records,
for each of the eight HUB messages, where a chain obtains the identity the
message binds — the body, the sender's address entry, the named account's
address entry, or the seat entry. Version four's address add had no answer, and
the table records that too. ADR 0037's second review claim was that no
comparable gap remains in the other eleven kinds, checked by reading; the table
is that reading written down where the next reader can check it in one place.
It is still a claim asserted by the specification rather than one executed by
anything, and the execution model is what will confirm it by running.

**The C++ codec now has a target with evidence behind it.** M3.9d updates
`src/v4/` to version five, and the vectors it must reproduce exist.

## Compatibility and independent review

No accepted artifact changes. `simulation/economy_transition/`,
`simulation/economy_transition_v3/`, `simulation/economy_transition_v4/`, their
vectors, their verifiers, and the version-four C++ codec are in place, passing,
and unedited; all four earlier vector files verify at their recorded counts.

Two claims need review.

**That importing version four's derivation is independence rather than
circularity.** The derivation and the model now share an ancestor: both reach
version four. They reach it differently — the model imports version four's
*implementation* and the derivation imports version four's *hand restatement of
the documents* — and the two were written by different means and are checked
against each other. But a defect present in both version four's model and
version four's derivation would be invisible to version five as it was to
version four, and the only thing standing against that is version four's own
third-source checks against `protocol-primitives-v1` and
`economy-transition-v3`.

**That the carryover classification is the right granularity.** It compares
recorded values, so it proves that two files agree about a value. It cannot
prove that a value means the same thing in both, and one case in this slice
shows the limit: `envelope.roundtrip.hub_add_address` is `true` in both files
and the transaction behind it is not the same transaction. The claim the
classification supports is about the recorded surface, and the model-level
carryover test is what covers the rest.
