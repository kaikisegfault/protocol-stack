# ADR 0107: The registration count is the founder's

- Status: Accepted
- Date: 2026-10-21
- Specification: [`economy-transition-v10`](../specifications/economy-transition-v10.md),
  revised in place
- Carries: the founder answer in
  [ADR 0106](0106-founder-answer-the-registration-limit-counts-per-founder.md)
- Amends: [ADR 0102](0102-economy-transition-v10-the-registry-and-single-use-approvals.md)
  decisions 1 and 2, where they place the count on the machine-key entry

## Context

ADR 0106 answers that one founder's machines together register at most 1,000
people a window. It fixes who a founder is, the window, the launch key's
exemption, and the check's place after the signature. It leaves two things to
the revision: how the count is encoded, and whether the machine-key entry keeps
its own.

**Nothing stores a version-ten state yet.** No snapshot, store, application,
or network carries one. So the contract is revised in place rather than by a
new version, as ADR 0103 repaired the registry step before anything implemented
it.

## Decisions

### 1. A founder-registrations entry, keyed by the identity

Entry kind 27 is `u8(27) || hub_identity_hash`. Its value is the window and the
count in it, 12 octets. Kind 10 reads the founder from the attesting seat's
entry, and writes the founder's entry when a machine attests.

**Rejected: a field in the HUB identity entry.** It would change version six's
identity layout, carried unchanged through version nine, for every identity, to
serve at most 100,000 founders.

**Rejected: summing counts kept on the founder's machine-key entries.** A
founder may hold 1,000 seats, so one registration would read up to 1,000
entries, and the count the limit is about would be stored nowhere.

**Rejected: an entry per founder per window.** It grows for the chain's whole
life, or needs a sweep to remove it. Keeping only the latest window's count,
and reading an earlier window's as zero, is the shape the machine-key entry's
count already had.

### 2. The machine-key entry keeps no count

Its value falls from 92 octets to 80: the key, the build digest, the registered
height, and the last met window.

**Rejected: keeping a per-machine count beside the founder's.** One machine's
registrations in a window are a subset of its founder's, so the founder check
refuses at or before the point a machine check would. The machine check could
never decide an outcome. A rule no outcome depends on is one no vector can show,
and a mutation that deleted it would survive every recorded run.

The machine count would also keep alive the rule that a key replacement must
preserve it, which exists only to stop key rotation resetting a count. On the
founder's entry, the count is out of kind 23's reach, so that rule has nothing
left to protect.

ADR 0106's per-machine reading stays true as a consequence: no machine can sign
more than its founder's 1,000.

### 3. The entry is written by a registration and never removed

A count from an earlier window reads as zero, so no prologue step clears one.

**Rejected: deleting stale entries at each window's opening.** That is a sweep
of up to 100,000 entries per window, to free storage that invariant 8 already
bounds.

### 4. A count of 0 is refused

Only a registration writes the entry, and it leaves the count at 1 or more. A
count of 0 would be a second encoding of absence, which `protocol-primitives-v1`
forbids. So the decoder refuses it, as it refuses a machine key written at
height 0 and a retirement at height 0.

### 5. Invariant 8 bounds the entries by the seats

Every founder-registrations entry names an identity that owns a seat holding a
machine key. It is true when an entry is written, because the attesting seat
holds a key and the founder owns that seat. It stays true, because seats are
never removed or transferred and machine keys are only ever replaced.

It is what makes the storage bound 100,000 rather than the identity count. A
restore runs it through the conservation check, so a snapshot cannot carry a
count for someone who holds no machine.

**Invariants 5 and 6 keep their numbers and move to the new entry**, and 6 gains
the lower bound of decision 4. Invariant 7 keeps its number, so every reference
to the retirement's persistence stays correct.

### 6. The code and the constant follow the limit

`REGISTRATION_LIMIT`, code 48, keeps its number and now names a full founder. A
wallet that receives it should try another founder's machine, not just another
machine. `MACHINE_REGISTRATIONS_PER_WINDOW` becomes
`FOUNDER_REGISTRATIONS_PER_WINDOW`, with the same 1,000.

## Consequences

- **Every version-ten vector that reads the registry is re-recorded**, through
  the same agreement gate, and the kernel reproduces them. The population gains
  a second founder, so a full founder's machines can be refused while another
  founder's still signs.
- **The standing cost rises from about 13.4 MB to about 16.7 MB** at capacity.
  Twelve octets leave each machine key, and a 45-octet entry joins for each
  founder.
- **The peak block does not change.** A registration through a machine writes
  one 12-octet founder value where it wrote one 92-octet machine-key value.
- **`snapshot_v10`, M4.3g, encodes the revised registry once.** Its restore runs
  invariant 8 with the others.
- **Owed to independent review**, in place of ADR 0102's item on the kept count:
  that the founder count and the inverse entry together close the limit's
  bypasses. Key rotation no longer reaches the count, and the registration
  message's seat binding stops a signature being presented under another
  founder's seat.
- **When legacy succession is specified, it must say what a seat's change of
  identity does to the window's count.** A seat moved to another founder
  mid-window would carry its machine under a second count. Nothing builds
  succession yet, and its limits are founder-reserved.
