# ADR 0066: The version-eight state snapshot, and the three rules its two new entry kinds need

- Status: Accepted
- Date: 2026-09-05
- Follows: [ADR 0056](0056-the-version-seven-state-snapshot.md)

## Context

[ADR 0065](0065-a-kernel-replacement-may-be-staged-across-a-stack-migration.md)
enumerates seven slices, and `snapshot_v8` is the third: **a version-eight ledger
cannot be written down at all until the two entry kinds version eight adds can
be encoded**, so no store, application, or node can hold one before this exists.

[ADR 0056](0056-the-version-seven-state-snapshot.md) already decided what a
snapshot *is* — the state root's own inputs and nothing else, `assigned_permissions`
re-derived rather than encoded, value decoders that fail closed on states no
transition could have written, ordering checked on the way in, and three restore
gates ending in `conservation_failures`. **All of it carries over unchanged**,
and this ADR records only what version eight makes different. Where the two
disagree about version eight, this one governs.

## Decision

### `dispute_authority_key` rides in the prefix and in the restore parameters

It is a genesis field bound into the chain identity rather than a state entry, so
it appears in no economy key and nothing in the state root commits to it. It goes
immediately after `verifier_key`, which is where `encode_genesis` carries it and
where a reader will look for it. The prefix therefore widens from 126 octets to
158 and `kFixedSize` from 190 to 222.

**It joins `SnapshotParametersV8` for the reason the other four are there**, and
one more. A snapshot that could redefine a genesis parameter is a snapshot that
could move a node to a different chain — and unlike the verifier key, this one has
**no second copy in the payload** to disagree with. The out-of-band comparison is
the whole of what stops a restored node answering to a different dispute
authority than its peers, and whoever holds that key can void a machine's uptime.

### The uptime carrier's two entry kinds are carried raw

`Ledger::uptime` is one raw key-to-value map holding every kind-18 and kind-19
entry, so the snapshot stores what arrived rather than decoding into fields and
re-encoding on the way out. **A typed shadow would be a second encoding of the
key space the two version-eight transitions write**, with nothing keeping the two
equal — the failure mode ADR 0026, ADR 0029, and ADR 0046 each record. The round
trip asserts the restored map equals the snapshotted one, which today follows
from the projection comparison and exists to catch exactly that change of shape.

### Three rules, and only one of them is new to the family

The entries are still *checked*. Two of the three rules are the kernel's own
decoders, reused rather than restated so the snapshot and the invariant that
re-reads the entry after a restore cannot disagree: an open challenge state is
`0` or `1`, and a window record has both bitmaps' upper eight bits clear with
`disputed` a subset of `credited`. **That second one closes ADR 0056's open
note.** ADR 0056 recorded that version seven's specification fixes the assignment
bitmap's width and does not state its pad rule, that the kernel is therefore
conforming, and that "a later transition version should state the rule outright".
Version eight does, for its own record — while version seven's older laxity is
left exactly as it was accepted.

**The third rule has no version-seven ancestor.** A window record equal to
`full_seat_window()` — every slot credited, nothing disputed — is refused,
because no writer can produce one. A record comes into existence one of two ways:
a dispute sets a bit in `disputed`, or an expiry clears one in `credited`.
Neither leaves a fully credited, undisputed window behind. That value is exactly
the state a chain records by *writing nothing at all*, so carrying it would make
one state representable two ways under one root.

A fourth rule is about a pair rather than a value: **an uptime entry must name a
seat the chain sold.** Both writers resolve the seat from the seat table before
they write. It is checked once the whole economy section is in rather than as each
entry arrives, so no value decoder has to depend on kind 1 sorting before kinds 18
and 19 — which is true, and is not a fact worth resting a decoder on.

### The seat-identifier bound was considered and deliberately not added

A separate `seat_id > kMaxSeatId` check, on the shape of the seat entry's own,
would be shadowed by the rule above in every reachable case: every seat the chain
sold is already inside the bound, so an identifier past it fails the existence
check too. Two rules where one fires is a rule that cannot be tested in isolation,
and this project has paid twice for probes caught by a different rule than the one
they named. One rule, one refusal, one test.

## Evidence

For each of the four scenarios in `test-vectors/economy-transition-v8-execution.txt`,
the final ledger is snapshotted, restored, re-encoded, and required to reproduce
that scenario's **recorded** `final_state_root`. `measured` and `deadline` retain
uptime entries — `deadline` one of each kind — and the round trip requires at
least two scenarios to have retained one, so a later scenario change that stopped
carrying them fails rather than quietly emptying the evidence.

**Three refusals are resealed, and that is what makes them worth having.** A
resealed payload defeats both root gates by construction, and the conservation
invariants say nothing about the absent-record reading or about an uptime entry's
seat — so for those three, the decoder rule is the only refusal there is. Mutation
probes that delete each rule report *"a restore accepted it"* rather than a root
mismatch.

**Two further refusals reach the conservation gate instead, and prove the same
thing about version eight's added invariants.** A resealed payload retaining a
window record past its retention, and one retaining a challenge past its response
deadline, are both well-formed entries in impossible places. Probes deleting
either invariant report *"a restore accepted it"*, which is what carries M3.13o's
finding — that three of version eight's six added invariants were unreachable by
any recorded scenario — one layer up into storage.

No new vector file is added, for ADR 0056's reason: a snapshot payload is not
consensus-visible, and recording its bytes would pin an operational format as
though it were a contract.

## Consequences

- `protocol_storage` compiles two snapshot formats until
  [ADR 0065](0065-a-kernel-replacement-may-be-staged-across-a-stack-migration.md)'s
  step 7 deletes version seven's, which is the cost that ADR already states.
- M3.13q has a canonical version-eight payload to persist. `SQLiteLedgerV8`'s
  `head_snapshot` column check moves from `length >= 190` to `length >= 222`, and
  the schema DDL and column names are compared verbatim on every open — so the
  rename is a store that will not reopen if it is done carelessly.
- A snapshot at the 100,000-seat capacity is larger than version seven's by the
  uptime map, which is proportional to *failure* rather than to population: a
  machine that answers every challenge writes no record at all. The conservation
  gate's `O(seats x 30)` cost that ADR 0056 recorded is unchanged, and the new
  invariants add one pass over the uptime map.
- The interim single `dispute_authority_key` now has a second artifact naming it.
  ADR 0048's per-machine attestation registry is what ends the interim, and this
  parameter moves with it when it does.

## Alternatives considered

**Decode the uptime entries into typed records, as every other kind is.**
Rejected above: it makes the snapshot a second implementation of the key space
the two transitions write.

**Put `dispute_authority_key` in the economy map as an entry, beside the verifier
key.** Rejected: it is a genesis field, the state root does not commit to it, and
adding an entry for it would be a consensus-visible change to the state — a
storage decision reaching into the contract, which ADR 0007 forbids.

**Restate version eight's six added invariants in the entry decoders.** Rejected:
`conservation_failures` already checks them over the encoded state, and a second
copy in the decoder would be two statements of one rule with nothing keeping them
equal. What the decoders check is what is local to an entry's own octets and what
the invariants do not say.
