# ADR 0053: `founder-economy-manifest-v3` carries the channel rename

- Status: Accepted
- Date: 2026-08-19

## Context

The 2026-08-19 founder pivot renames issuance channel 9 from
`initial_mystery_box_incentives` to `mini_gamified_incentives`.
[ADR 0049](0049-the-recovery-pool-and-permanent-best-performer-ranking.md)
records the pivot the rename belongs to, and the Founder Constitution's
direct-mint allocation table already reads "Initial mini-gamified incentives".

A channel identifier looks like the cheapest possible change and is not. It is a
string inside the manifest JSON; the manifest digest is a hash over that JSON;
the digest is a genesis field; the chain ID is a hash of genesis. So the rename
moves the manifest digest, then genesis bytes, then the chain ID, then every
recorded vector that embeds any of them.

`founder-economy-manifest-v2` additionally fixes its schema string, identifiers,
values, domain label, and digest as immutable, and requires a new schema and ADR
for any change to them.

Three decisions follow: whether to version the manifest at all, how version
three's contract table should relate to version two's, and whether the loader
should be copied.

## Decision

### 1. The rename is a new manifest version

`founder-economy-manifest-v3` is a separate accepted contract with schema string
`protocol-stack/founder-economy-manifest/v3`, domain label
`protocol-stack:founder-economy:manifest-v3`, canonical length 2,261 bytes, and
digest `af153c99adf7c49e5a92563946cf0e60dfd7a58785462530988f661aa68faaa7`.
Versions one and two remain in place, passing, and unedited.

**Rejected: rename in place and recompute version two's digest.** It is one
line of diff and it silently reinterprets an accepted digest, which is exactly
what version two's immutability clause exists to prevent. Every model, vector,
and report that cites `84cca098…` would then describe bytes that no longer
exist, and nothing would fail to say so.

**Rejected: treat the old identifier as an accepted alias.** Two spellings of
one channel is two spellings in the canonical bytes, so it is two digests and
two chain IDs. A canonical encoding with a synonym is not canonical.
`initial_mystery_box_incentives` is retired: a manifest carrying it is rejected
with `MANIFEST_MISMATCH`.

### 2. Version three's table is derived from version two's, not restated

The contract table applies exactly one substitution to version two's table.
A cap, leg, kind, order, or bound that moved cannot be expressed.

**Rejected: hand-write the full table a third time.** It is what versions one
and two did, and it was right when they did it, because version two genuinely
changed founder-directed values and a hand-written table is where such a change
is stated. Version three changes none, so a third copy would turn "and nothing
else moved" into a claim a reader has to verify by eye across ten caps, five
legs, a denomination, and two subtotals.

The independence this could have cost is supplied from outside the models
instead: the verifier's `expected.py` converts the Founder Constitution's two
allocation tables by hand and imports nothing from `simulation/`. The
constitution states the economy twice — as per-cycle amounts and as channel
totals — without deriving either from the other, so requiring them to agree
checks the manifest against its source.

### 3. One loader, bound to each version's table

The ordered acceptance stages, their order, the field inventory, and the checked
derivations carry no founder-directed value. They move to
`simulation/founder_economy_manifest/` and each version binds them to its own
contract table, keeping its own module names and public functions.

**Rejected: copy the loader for version three.** It is roughly 450 lines for a
one-string change, and it is the failure mode M3.10c named when it deleted
version four's codec: two implementations of one rule are two places to drift,
and the drift is silent because each copy agrees with itself.

The refactor is behavior-preserving and was proved so before version three
existed: version two's 154 vectors — its canonical length, its digest, and every
ordered failure code — its 23 manifest tests, its 38 error tests, and every
dependent model, scenario, and verifier in the repository passed unchanged.

### 4. The rename is accounted for in both directions

The vectors record that exactly one identifier changed, that zero caps, kinds,
legs, and totals changed, that the retired identifier occurs zero times in the
accepted canonical bytes, and that the change in canonical byte length equals
the identifier's own change in length — 30 bytes to 24 — which holds only
because the two schema strings and the two domain labels are each the same
length as their counterpart.

That last identity is what makes "and nothing else" checkable in bytes rather
than by reading a table.

## Consequences

**Nothing downstream is rebound yet, deliberately.** No simulator, transition
model, or C++ kernel loads version three. `economy-transition-v6` and every
model that binds version two continue to bind version two, and they remain
correct against it. The settlement respecification and `economy-transition-v7`
are where the rename reaches execution, and each is its own slice.

**The four direct-mint channels the research placeholder covers are unchanged in
number and one of them is renamed.** Direct-channel eligibility remains
founder-reserved.

**Three of seven mutation probes were caught by a stage earlier than the one
they were aimed at, and that is recorded rather than counted as success.**
Making version three rename nothing, making it rename a second channel, and
adding a byte to a fixed string were all caught by the loader's fixed-value
comparison before the `rename.` group ran, so they establish that the loader
works and say nothing about the group under test.

The probe that reached it was a *self-consistent* version three: the renamed
channel's cap raised by one display unit, with the direct-mint subtotal and both
maximum-supply figures raised to match, in both the contract table and the
manifest JSON. Every loader stage and every checked derivation accepted it. It
was caught by the constitution comparison and by three values in the `rename.`
group at once. A cap moved by a single atomic unit is caught earlier still,
because a display maximum that is not an integer number of display units fails
the derivation stage.

**A probing hazard is recorded because it silently favours false success.**
Python's bytecode cache validates on source mtime in whole seconds plus size, so
a probe edit and its restore that land in the same second with the same file
size can leave a stale `.pyc` in place. Every probe here was re-run with
bytecode writing disabled. A probe that appears to *pass* is where this matters:
the mutation may never have been compiled.

**One thing this does not do.** Renaming a channel says nothing about what that
channel pays, to whom, or on what proof. Channel 9's eligibility was reserved
before the rename and is reserved after it.
