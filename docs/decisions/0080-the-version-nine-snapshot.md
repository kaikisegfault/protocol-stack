# ADR 0080: The version-nine snapshot carries the head's second scalar, and needs no new parameter to do it

- Status: Accepted
- Date: 2026-09-17
- Bounds: [ADR 0066](0066-the-version-eight-state-snapshot.md),
  [ADR 0056](0056-the-version-seven-state-snapshot.md), [ADR 0007](0007-sqlite-ledger-persistence.md)
- Follows: [ADR 0065](0065-a-kernel-replacement-may-be-staged-across-a-stack-migration.md),
  [ADR 0078](0078-the-version-nine-execution-model.md)
- Relates to: `include/protocol/storage/snapshot_v9.hpp`, `src/storage/snapshot_v9*.cpp`

## Context

[ADR 0065](0065-a-kernel-replacement-may-be-staged-across-a-stack-migration.md)
puts the snapshot third in a stack migration, and the reason is mechanical: a
state that cannot be written down cannot be stored, restored, or audited, so the
store, the application, and the node all wait on it. Version nine has a codec, a
ledger, and an accepted application contract; this is what lets one of its states
leave memory.

**Most of the snapshot needed no decision.** The framing, the digest domain, the
two ordered sections, the three restore gates, the re-derivation of
`assigned_permissions`, and every inherited value decoder are
[ADR 0056](0056-the-version-seven-state-snapshot.md)'s and
[ADR 0066](0066-the-version-eight-state-snapshot.md)'s. The assignment translation unit
is a **provably empty normalising diff** against version eight's. What follows is
the set this slice had to settle, and the finding that outranks it.

## Decision

### 1. The payload carries the timestamp, beside the height

`Ledger::timestamp` is a field rather than a parameter because C2 compares a
block's stamp with its predecessor's, so a machine that restored from a snapshot
must hold one. The payload carries it at a fixed offset immediately after the
height, which makes the prefix 166 octets rather than version eight's 158.

**Beside the height rather than among the monetary fields**, because the two are
the head. `StateSummary` already orders them that way and a reader looking for
one should not have to step over the supply to find the other.

**This is the field version nine could lose in silence**, which is why the
evidence aims at it rather than relying on the gates. A restore that dropped the
stamp would hand back a ledger whose next block commits a root naming a height
the stamp does not belong to — and **every later block would still satisfy C2**,
because the stale stamp is smaller than anything that follows. The failure is a
wrong root rather than a refusal.
[ADR 0078](0078-the-version-nine-execution-model.md) records the same shape of
defect against `advance_to` and `consensus-application-v2` records its boundary
form; this is its storage form, and each needs its own vector because the
argument does not transfer.

The round trip therefore makes two claims rather than one. The restored stamp
equals the original, and **a payload that keeps every other field and zeroes only
the stamp reaches a different root.** Without the second, the first could hold
while the field was decorative.

### 2. Version nine adds no snapshot parameter

The out-of-band parameters stay at five: the chain identity, the supply limit,
the fixed fee, the verifier key, and the dispute authority key.

Version nine's one new genesis field is the genesis timestamp, and a restored
ledger does not need it. C2's genesis case applies only at height one, the ledger
keeps no separate copy of it, and `chain_id` — which *is* compared — is
`H(label || genesis bytes)` and therefore commits to it.

**The dispute authority key needed a parameter for exactly the opposite
reasons**, and stating them together is what makes the asymmetry a rule rather
than an inconsistency: the ledger retains it, transitions read it, and no state
root commits to it, so a payload could otherwise move a restored node to another
dispute authority unnoticed.

### 3. The four new kinds are decoded into fields; the two older ones are not

Version eight stores its uptime entries raw, because
`Ledger::uptime` is one raw key-to-value map and decoding them here would be a
second encoding of the key space its two transitions write.

Version nine's four kinds are decoded into `window_months`, `figures`, `claims`,
and `accumulating_month`. **The rule is the same rule and it produces the
opposite answer**, which is the point:
[ADR 0078](0078-the-version-nine-execution-model.md) already decided that nothing
in version nine reads that raw space — the settlement is arithmetic over decoded
figures — so a raw map here would be the second encoding instead. Which side
reads the key space is the whole of the difference.

### 4. The four value decoders are the kernel's own, called rather than restated

`decode_window_month_value`, `decode_monthly_figure_value`,
`decode_monthly_claim_value`, and `decode_settlement_cursor_value` already refuse
what their encoders refuse to write: a month index past the calendar, a figure of
zero seconds, a claim that minted more than it accrued. Calling them is what
stops the snapshot and the invariant that re-reads these entries after the
restore from ever disagreeing. It is the pattern version eight set with
`decode_recovery_pool_value` and the failure mode ADR 0026, ADR 0029, and ADR 0046
each record.

**One key rule has no value decoder to delegate to**, and it is the monthly
figure's month. The month lives in the *key*, so the entry decoder rebuilds the
key with `monthly_figure_key` and requires it to equal the one that arrived. Gate
3 would refuse an out-of-range month too, one layer later — every figure must
equal the cursor's month and the cursor is bounded by its own decoder — but it
would refuse it as an unconserved state rather than as a bad entry. **A parse
error names its subject; a failed invariant names a payload.**

### 5. The fixed set gains the settlement cursor and not the window month

Genesis writes sixteen entries where version eight wrote fourteen. Only one of
the two is *fixed*: the cursor, which no transition removes. Window zero's month
entry is genesis's too, but every assignment deletes one, so its presence is the
retention invariant's business and not a completeness flag.

`Rebuild::uptime_seats` becomes `referenced_seats`, because kinds 21 and 22 name
a seat for the same reason kinds 18 and 19 do. A name that said "uptime" would
have been wrong the moment the monthly figure used it.

## The finding

**A timestamp with no month cannot reach the conservation gate, and the reason is
not the one the slice expected.**

The kernel's first clock invariant is that the state's stamp is inside
`calendar-v1`'s accepted range, so the obvious negative case is a resealed
payload carrying an out-of-range stamp — resealed, because the root commits to
the stamp and an unresealed payload would stop at gate 1 and prove nothing about
the invariant.

**That payload cannot be built.** `state_root` returns `nullopt` for a stamp C1
would have refused, so there is nothing to reseal *with*. The restore therefore
refuses at **gate 1**, because the rebuilt ledger commits no root at all, and the
conservation invariant is **unreachable through a snapshot** rather than merely
redundant with an earlier check.

That is a stronger property than the one the test set out to record — the range
rule is enforced by the root's own totality rather than by a gate that could be
removed — and it was found by writing the test, predicting `not_conserved`, and
checking the prediction against `state_root` before running anything. The test
now asserts both halves: that the stamp has no root, and that the refusal is gate
1's. Asserting only the refusal would not say which gate fired or why the other
cannot.

## Consequences

**A version-nine state can be persisted, and the next slice is `SQLiteLedgerV9`.**
After it, the application layer and the transport responses — which now have
`consensus-application-v2` to satisfy — the node process and the Go client, and
then the deletion of `src/v8/`.

**One dead constant did not survive the port.** Version eight's
`kFixedEntryCount` is declared in its internal header and referenced nowhere; the
completeness check is a set of named flags, which is what a reader should be
looking at. Carrying it forward would have made a figure that is wrong for
version nine — fourteen against sixteen — sit unused beside a check that does not
consult it. Version eight's copy is left alone: an unused constant is not worth a
commit against a delivered version.

**The refusal suite is weighted rather than swept.** The inherited kinds get a
sample and the four new kinds, the widened pool value, and the new fixed entry get
the sweep. `storage_snapshot_v8_tests` holds the full inherited set and it is
still green; what a sample establishes here is that the port did not lose them.

**One inherited case could not be ported and the substitution is recorded.**
Version eight's suite refuses a referral balance that minted more than it
accrued; the version-nine trace purchases every seat with `has_referrer` clear,
so no kind-4 entry exists to mutate. The identity index rule stands in its place,
over an entry this trace does produce.

## Owed

**The store, and the restore path that reads these payloads back.** ADR 0066's
restore gates are checked here against in-memory ledgers; nothing yet writes one
of these payloads to disk under version nine. That is `SQLiteLedgerV9`'s, and it
is the recorded next action rather than a gap in this one.
