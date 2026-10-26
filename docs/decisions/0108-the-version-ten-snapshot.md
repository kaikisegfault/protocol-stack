# ADR 0108: The version-ten snapshot carries the build authority key and checks what one height can show of the retirement

- Status: Accepted
- Date: 2026-10-26
- Bounds: [ADR 0080](0080-the-version-nine-snapshot.md),
  [ADR 0066](0066-the-version-eight-state-snapshot.md),
  [ADR 0056](0056-the-version-seven-state-snapshot.md),
  [ADR 0007](0007-sqlite-ledger-persistence.md)
- Follows: [ADR 0104](0104-the-version-ten-kernel-is-staged-beside-version-nine.md),
  step 3
- Specification: [`economy-transition-v10`](../specifications/economy-transition-v10.md),
  which this record does not change
- Relates to: `include/protocol/storage/snapshot_v10.hpp`, `src/storage/snapshot_v10*.cpp`

## Context

[ADR 0104](0104-the-version-ten-kernel-is-staged-beside-version-nine.md) puts
the snapshot third in the version-ten migration, for ADR 0065's reason: a state
that cannot be written down cannot be stored, restored, or audited, so the
store, the application, and the node all wait on it.

A snapshot is node-local. It is consensus-visible only through the root it must
reproduce, so it follows ADR 0007's precedent of an ADR and an implementation
with evidence, and it may be stricter than the kernel's decoders without
changing any accepted state.

**Most of it needed no decision.** The framing, the digest, the two ordered
sections, the three restore gates, the re-derivation of `assigned_permissions`,
and every inherited value decoder are ADR 0056's, ADR 0066's, and ADR 0080's.
The assignment unit is version nine's with the namespace rebound, and the entry
unit differs from version nine's by one rename, the four new cases of its
dispatch, and one call in `complete`. A draft an agent began on 2026-10-21 supplied most of the source.
This slice verified it as new code, and changed it in one place, decision 5.

## Decisions

### 1. The build authority key is a snapshot parameter

The out-of-band parameters become six: the chain identity, the supply limit, the
fixed fee, the launch key, the dispute authority key, and the build authority
key. The key rides in the prefix at offset 150, immediately after the dispute
authority key, which is where genesis carries it. The prefix is 198 octets
rather than version nine's 166.

**It is a parameter for the dispute authority key's reason** (ADR 0080, decision
2): the ledger retains it, kind 23 reads it, and no root commits to it. So it is
the field version ten could lose in silence. A restore that dropped it would pass
all three gates, then refuse every machine key the network admits, and whoever
could substitute it would decide which machines may admit people.

The round trip therefore aims at it. The root of a ledger with the key zeroed
is required to equal the original's, which is why the gates cannot catch it. A
restored ledger is required to execute a kind-23 replacement exactly as the
original does. And the same block on a ledger that lost the key is required to
be refused as `UNAUTHORIZED`.

### 2. The launch key keeps the verifier key's place

Entry kind 8 keeps version six's name and holds the launch key, the same key in a
narrower role, so the payload carries it twice and the restore requires the two
copies to agree, as it did for the verifier key. It keeps the verifier key's
prefix offset, 86, as genesis keeps it.

### 3. The four registry kinds are decoded into typed maps

Version ten holds the machine keys, their inverse, the retirement, and the
founder counts as typed fields, and nothing reads their raw key space, so ADR
0080's rule (decision 3) gives the same answer for them as for version nine's
four. They live in their own unit, `snapshot_v10_registry.cpp`, which mirrors
the kernel's own split.

**Every value rule is the kernel's, called rather than restated** (ADR 0080,
decision 4). `decode_machine_key_value` refuses a key written at height 0,
`decode_launch_retirement_value` a retirement at height 0, and
`decode_founder_registrations_value` a count of 0 or above the limit.

### 4. The registry invariants are gate 3's

Version ten's `conservation_failures` carries invariants 1 to 6 and 8: every
machine key on an activated seat, the owner entries exactly the inverse, no key on
two seats, every mark at or below the assigned window, every founder count in a
window the head has reached and inside one to the limit, and every founder count
naming an identity that owns a seat with a machine key.

**None is restated in the decoder.** In particular a machine key does not add its
seat to `referenced_seats`, because invariant 1 already refuses a key on a seat
nobody bought, and a rule that never fires alone is one no test can isolate.

### 5. The restore checks what one height can show of the retirement

**Invariant 7 is the one registry invariant a restore cannot run.** It says a
retirement, once present, stays present with the same value. That compares two
heights, and a snapshot holds one. So a resealed payload that dropped the
retirement would pass all three gates, and a node restoring it would let the
launch key sign again: ADR 0100's "for good", undone by a file.

**This matters most for a seeded launch.** A node restoring alone from a tampered
payload holds a root its peers do not, and stops at the next block. But every
replica of a seeded network restores the same payload and takes its root as the
engine's `app_hash` ([ADR 0097](0097-a-seeded-launch-takes-its-genesis-from-one-head.md)),
so no peer disagrees.

One height can still show three things, and each follows from how the registry
step writes the retirement. `complete` refuses, as `invalid_state`, a state that
breaks any of them.

- **Present when the head's own count reached the cutoff.** Between assignments
  no transition makes a machine active, because a new key starts unmarked and a
  replacement keeps its seat's mark. So the machines active at the head are the
  ones the latest registry step counted. If there were 100, it wrote the
  retirement.
- **Present only when 100 machines were ever marked.** No key is removed and no
  mark returns to 0, so the 100 marks that retired the launch key are nonzero
  marks at every later height.
- **At an assignment the head has reached.** Only a registry step writes it, at
  the first height of window `w + 2`, which assigns window `w`. That window is at
  least 1, because a mark of 0 is never counted
  ([ADR 0103](0103-the-registry-count-excludes-an-unmarked-machine.md)).

**The draft had the first two and not the third**, so a retirement at a height
no step runs, or above the head, restored. This slice added it.

**What one height cannot show is a retirement dropped after the count fell below
the cutoff**, because a chain that never retired could hold the same state. A
stricter rule refusing any absent retirement once 100 machines were ever marked
would be wrong: 101 machines can each have met some window without 100 having met
the same one. So that case stays a two-height fact. Only the root exposes it,
compared with the root of the chain the payload claims to come from, which a
seeded launch must obtain from that chain rather than from the payload.

### 6. The fixed set is unchanged

Genesis writes version nine's sixteen entries and none of the four registry
entries, and the retirement is present or absent by design, so no completeness
flag is added.

## Evidence

`storage_snapshot_v10_tests`, CTest entry `version-ten-snapshot`, reuses the
kernel execution suite's fixtures and links no version-nine code (ADR 0104):

- **Round trips** over the chain of blocks, the 101-machine population, and the
  one-machine span run past 731 cycles. Each restored ledger must commit the
  final root `economy-transition-v10-execution.txt` records for it (`chain`,
  `cap`, and `span`), and the population's must hold the recorded retirement
  height. The four registry maps are compared whole, beside version nine's
  four, the raw uptime map, and the re-derived permission count. The three
  fixtures between them hold every entry kind version ten writes.
- **A registry sweep.** It covers each decoder rule at the payload level. It
  covers each of invariants 1 to 6 and 8 by mutating the typed ledger and
  requiring both `not_conserved` and that named invariant among the failures.
  And it covers the retirement rule at each of its conditions, with each case
  also requiring that gate 3 finds nothing. Two controls pin the rule's extent:
  a retirement at another lawful assignment restores, and so does a retirement
  dropped after the count fell.
- **Version eight's and version nine's sweeps, carried.** ADR 0092 found that a
  deletion by filename would have left inherited rules with no snapshot-level
  check, and ADR 0104's step 7 deletes version nine's suite. So
  `snapshot_v10_entry_refusals.cpp` carries version nine's four kinds and the
  widened pool, and `snapshot_v10_inherited_refusals.cpp` carries version
  eight's. The chain holds a real referral balance and real custody legs, so
  those cases mutate entries a block wrote, where version nine's suite had to
  insert them.
- **Mutation probes** against the decoder, run locally: removing the retirement
  rule, either count condition, the head bound, the window-0 exclusion, or the
  assignment-height condition; dropping or not comparing the build authority
  key; skipping the launch key's comparison; disabling gate 3; and replacing
  each kernel value decoder with a raw read. Each fails the suite, except one,
  described next.

**One probe passed, and the overlap is stated rather than hidden.** Replacing
the retirement decoder with a raw read still refuses a retirement at height 0,
because no assignment is at height 0 and decision 5 refuses it too. The decoder's
own rule is pinned where it is alone, in the codec target, as
`state.launch_retirement_refuses_zero`.

`storage_snapshot_v10_fuzz`, CTest entry `storage-snapshot-v10-fuzz-smoke`, is
`storage_snapshot_v9_fuzz`'s counterpart, which ADR 0104's step 7 must keep. **It
has two seeds**, because a genesis writes none of the registry entries. The second
is a hundred machines retired at the window-1 assignment, with one founder count,
built through the kernel with the trace's builder.

**Its cost was measured before it shipped.** That seed's root is about 10 ms
under the sanitizer preset, and checking both seeds after every input took 83
seconds for the 512-run smoke against a 60-second timeout. So the registry seed's
own restore is checked once, when it is built, and each input explores one seed's
neighbourhood, chosen by an input octet. The genesis seed keeps version nine's
checks after every input. The smoke then took 11 seconds locally. A
60-second session found nothing.

## Alternatives rejected

- **Commit the build authority key to the root.** That is a contract change.
  `economy-transition-v10` binds the key into the chain identity and writes it to
  no state entry, and a node-local format cannot change that.
- **Leave the retirement to the root.** It is what ADR 0080's shape would give,
  and it leaves a seeded network with no guard at all, because its replicas agree
  with each other.
- **Refuse any absent retirement once 100 machines were ever marked.** It refuses
  states a chain reaches, which no snapshot rule may do.
- **One seed for the fuzz target, the registry's.** Its neighbourhood is where
  the new decoders are, but its cost would have pushed the shared-state check off
  most inputs, and the genesis seed is what keeps that check cheap.

## Consequences

**A version-ten state can be written down and restored, and the next step is
`SQLiteLedgerV10`**, ADR 0104's step 4. Version nine's store derives a
restore's parameters from the genesis it is opened with, so the build authority
key reaches a restore the way the dispute authority key does.

**A seeded launch now refuses a seed that hides a retirement its own head
proves**, and still trusts the seed's root for the case one height cannot show.
That residual is the same as for every other value a seed carries: a seed is
only as good as the root it was checked against.
