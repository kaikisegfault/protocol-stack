# ADR 0056: The version-seven state snapshot, and what a restore must refuse

- Status: Accepted
- Date: 2026-08-30

## Context

The C++20 kernel executes [`economy-transition-v7`](../specifications/economy-transition-v7.md)
against an **in-memory** `Ledger`. Nothing it produces survives a restart, so
requirement 13 of [`first-goal.md`](../project/first-goal.md) — "adversarial
four-node economic scenarios through restart and recovery, proving deterministic
replica agreement on state roots" — cannot begin. It is the largest remaining
piece of the first goal and it is blocked on a state that cannot be written down.

[`docs/project/current-state.md`](../project/current-state.md) recorded
`calendar-v1` as the next slice and called it "the only [contract] requirement 13
depends on". **That was wrong.** Version seven mentions a month in one
descriptive sentence and executes nothing against one; the unreferred pool's
payout is explicitly unestablished in version six and version seven alike. A
calendar written before the payout that needs it is machinery with no caller.
`calendar-v1` is still owed; it is not what requirement 13 is waiting for.

[ADR 0007](0007-sqlite-ledger-persistence.md) already fixes how a
storage artifact is recorded: "Storage rows, files, schemas, and snapshot formats
are operational compatibility data. They never define transaction, receipt,
state-root, or block meaning." A snapshot therefore gets an ADR and an
implementation with evidence rather than a transition specification, and
`protocol::storage::snapshot_v1` is the shape to follow.

## Decision

### The payload is the state root's own inputs and nothing else

`encode_snapshot_v7` writes the summary, the ordered account map, and the ordered
economy map, in the shapes `protocol::v7::state_root` takes them. The economy
section uses the accepted `bytes(x)` primitive for both halves of every entry, so
it is literally the concatenation of the leaf preimages the root is taken over,
in the same order.

**Encoding a second projection was rejected.** A snapshot that carried its own
view of a state — a decoded seat table, a channel summary — would create a second
opinion about what a state *is*, and the root it claims would then be checking
the snapshot against itself rather than against the contract.

Two genesis parameters ride beside the summary because a restored ledger has to
keep executing rather than merely verify: the fixed fee and the ecosystem
verifier key. Both, with the chain identity and the supply limit, are supplied
out of band at restore and compared, for the reason version one supplies its own:
a snapshot that could redefine them would be a snapshot that could move a node to
a different chain. The verifier key is *also* an economy entry, so a payload
carries it twice and the restore requires the two copies to agree.

The magic is version one's `PSSN` with a version field of 7. One snapshot family
discriminated by version is what a version field is for: version one's decoder
reads these bytes, recognises the family, and answers `unsupported_version`
rather than `malformed`.

### `assigned_permissions` is re-derived, never encoded

It is not a state entry, so nothing in the root commits to it — and the channel
identity is stated over exactly this figure. A payload that carried it could
disagree with the records it sits beside, and a snapshot forger could lower it to
match a state they had edited.

The restore sums, over every assignment record, the reallocated count plus the
population of the accrued bitmap. Both are terms the record commits to, so the
figure the identity is stated over is derived from the same bytes the identity is
checked against.

### Each value decoder fails closed on a value no transition could have written

Not merely on the wrong width. A seat carrying a referrer identity while its flag
is clear; an unactivated seat with a nonzero activation height; a flag octet that
is neither zero nor one; a seat past the founder capacity; a channel index no
manifest defines; an identity whose next escrow index is below its live count or
holding more seats than the limit; an exempt slot mask naming a slot past the
twenty-fourth; an escrow over the signer limit; a balance that minted more than
it accrued; a counter above the verified-user population; a custody entry naming
a beneficiary no leg credits; an assignment record whose winner count is not its
own bitmap, whose share is not the one its winner count determines, or which
contributes more seats than it measured.

Each is a state the conservation invariants forbid and each has exactly one
encoding a transition produces. **Refusing them here is free**: a snapshot is
node-local, so a rule stricter than the kernel's own decoder changes no accepted
state. And each refusal names its subject, where a root mismatch would tell a
reader that something is wrong and nothing about what.

**One of those rules is stricter than the kernel and the difference is worth
recording.** `bitmap()` never sets a bit at or above `bitmap_bits`, but
`decode_cycle_assignment_value` does not check that the pad bits are clear, and
`bit_is_set` bounds itself by the packed width rather than by the recorded count.
A record with a pad bit set would therefore be read as an accrued seat by the
mint's own walk. It is unreachable on-chain, because every record a block writes
comes from `bitmap()`; it is reachable through a file. The snapshot decoder
refuses it. **The accepted specification fixes the bitmap width and does not
state the pad rule, so the kernel is conforming and tightening its decoder would
be a compatibility change rather than a fix.** A later transition version should
state the rule outright; until then this ADR is where it is written down.

### Ordering is checked on the way in

Account identifiers must strictly increase and economy keys must strictly
increase. Both trees are over ordered sets, so a payload that repeated or
reordered one could not produce the root it claims — but catching it at the parse
is cheaper than at the root, names its subject, and makes duplicate detection
unnecessary in every individual value decoder.

### The restore ends with three gates, in this order

1. the rebuilt ledger's own projection must reproduce the payload's root;
2. the payload's entries must produce the same root;
3. `conservation_failures` must be empty.

A restore hands back a state some sequence of blocks could have produced, or it
hands back nothing.

**The third gate is the one that does the work, and the reason is that the first
two are defeated by construction.** An adversary who edits a state can recompute
its root and reseal the digest; both root gates then pass. Only an identity that
must still hold — supply against balances, `issued + outstanding` against
`assigned_permissions * leg`, `outstanding` against `claimable + pool` — refuses
an edited state. That is why the permission count is re-derived rather than read:
the conservation gate is only as good as the figure it is stated over.

**The second gate is unreachable through today's decoders and is kept anyway.**
The rebuild is lossless, so the payload's entry list and the restored ledger's
projection are the same bytes — a property the tests assert rather than assume,
for each of the five recorded scenarios.

It fires the moment a decoder admits an entry the projection will not write back,
which is a real failure rather than a hypothetical one: a mutation probe that
removes the channel-index bound admits an eleventh channel, the rebuilt ledger
has nowhere to keep it, and **this gate is what refuses the payload**. That is
the shape every future divergence will have — a `Ledger` field or an entry kind
added on one side and forgotten on the other — and without the gate a reader
would diagnose it as a corrupted file.

### Evidence is the recorded execution scenarios

For each of the five scenarios in
`test-vectors/economy-transition-v7-execution.txt`, the final ledger is
snapshotted, restored, and required to reproduce that scenario's **recorded**
`final_state_root`. That is a third source rather than a second opinion of the
encoder: the figure is produced by a model that knows nothing about snapshots,
and a round trip compared only against the encoder would pass for a matched pair
of mistakes.

No new vector file is added. A snapshot payload is not consensus-visible, so
recording its bytes would pin an operational format as though it were a contract
and would oblige every future storage change to re-version a normative file.

## Consequences

- Requirement 13 is unblocked on its first dependency. A version-seven state can
  be written down, moved, and read back, which is what a four-node restart
  scenario needs before it can compare two replicas.
- `protocol_storage` gains two translation units and no new dependency. The
  snapshot performs no cryptography of its own beyond the accepted `hash`
  primitive and touches no SQLite.
- The next storage slice — a version-seven owning store — has a canonical payload
  to persist rather than a `Ledger` to serialise ad hoc.
- The snapshot is **not** a portable archive: it carries one state at one height
  and no block history. ADR 0007's archive remains the artifact for that, and a
  version-seven archive is not written here.
- A snapshot of a state at the 100,000-seat capacity is large — the cycle
  assignment records dominate — and the conservation gate runs `claimable`, which
  is `O(seats x 30)`. Both costs are node-local and neither is consensus-visible.
  Nothing yet runs at capacity; the handoff records the cost so it is paid
  deliberately rather than discovered.

## Alternatives considered

**Serialise the `Ledger` struct directly.** Rejected: the struct is an
implementation of the state, not the state. Its field order is a C++ decision, a
snapshot written from it would change whenever the struct did, and it would carry
`assigned_permissions` — the one field an adversary most wants to choose.

**Store the snapshot inside the SQLite owning store and skip the standalone
format.** Rejected: ADR 0007 already says a raw SQLite file is not a portable
snapshot, and requirement 13 compares replicas across processes.

**Add a `restore_ledger` entry point to the kernel, as version one has.**
Rejected for now: version one's restore exists because its ledger enforces
invariants through a constructor, and version seven's `Ledger` is a plain struct
whose invariants are checked by `conservation_failures`. Putting the gates in the
storage adapter keeps the kernel independent of who is loading it, which
`CLAUDE.md` requires of storage integrations.

**Record snapshot bytes as an accepted vector file.** Rejected above: it would
pin operational data as a contract.
