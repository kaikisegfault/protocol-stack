# Economy transition v10

Status: Accepted M4 consensus transition contract. The independent model's
contract half and its 107 contract vectors are recorded. The execution model,
kernel, snapshot, store, application, and node are not.

This document defines the version-ten Founder Economy consensus transition. It
is [`economy-transition-v9`](economy-transition-v9.md) with **a registry of
attested machine keys in place of the single verifier key, and HUB approvals
that can be used once.** It is the contract version that carries requirements 3
and 5 of [`first-goal.md`](../project/first-goal.md).

The change is classified as encoding, validation, state transition, authority,
and compatibility.
[ADR 0102](../decisions/0102-economy-transition-v10-the-registry-and-single-use-approvals.md)
records the decisions and the alternatives rejected.

**It exists for two reasons, and each has evidence behind it.**

- **Admission rests on one key.** Version nine accepts a registration only
  under the genesis `verifier_key`. That one key can admit anyone and can stop
  anyone from ever joining. ADR 0048 replaces it with a registry of per-machine
  attestation keys. ADRs 0100 and 0101 record the owner's answers on who
  verifies, how the first registrations happen, what counts as an active
  machine, and how many registrations one machine may sign.
- **A HUB approval can be used twice.** `hub-test-verifier-v9` executes it. A
  published posture relax undoes a later tightening with a signer key alone,
  and one transfer confirmation moves value twice. No version-nine HUB message
  binds a nonce, and nothing bounds `valid_until_height` from above.
  [`hub-verification-threat-model.md`](../architecture/hub-verification-threat-model.md)
  records it as T1.

## Relationship to version nine

[`economy-transition-v9.md`](economy-transition-v9.md) is not edited, retracted,
or reinterpreted. `test-vectors/economy-transition-v9.txt` and
`test-vectors/economy-transition-v9-execution.txt` remain normative and passing.
Version nine fixes its key space, result codes, kind space, genesis field
table, and HUB messages as immutable. So adding entry kinds, result codes, a
transaction kind, and a genesis field, and replacing five messages, is a new
version rather than a repair.

**Everything else in version nine carries over unchanged and is incorporated by
reference.** That includes:

- the block header, its timestamp, and where each of `calendar-v1`'s five rules
  is applied;
- the monthly settlement and kind 22;
- the uptime carrier, challenge selection, and kinds 20 and 21;
- the account architecture of identities, keyless escrows, and revocable
  signers, and the security posture and its asymmetry;
- the settlement's eight steps, the recovery pool, the accumulation cap, and
  the bounded mint walk;
- the receipt layout, the forty-five result codes, and every founder-directed
  figure in the accepted manifest.

**Five things change, and this document defines exactly those five:**

1. Genesis's `verifier_key` becomes the `launch_key`, and genesis gains a
   `build_authority_key`.
2. The state gains three entry kinds: a machine key per seat, its inverse, and
   the launch key's retirement.
3. Kind 10's body names the seat whose machine attested the registration, and a
   new kind 23 registers a seat's machine key.
4. Every HUB approval signs the whole transaction it approves, and its life is
   bounded.
5. The prologue gains a registry step at every assignment, which marks the
   machines whose seats met the cycle and retires the launch key at the cutoff.

## What version ten changes

| | v9 | v10 |
| --- | --- | --- |
| Who signs a registration | the genesis `verifier_key` | an active machine's registered key, or the launch key until it retires |
| Genesis fields | ten | eleven, gaining `build_authority_key` |
| Genesis prefix | 150 octets | 182 octets |
| Entry kinds | 22 | 25, gaining 24, 25, and 26 |
| Transaction kinds | 17 assigned | 18 assigned, gaining kind 23 |
| Kind-10 body | 128 octets | 132 octets |
| HUB approval message | five per-action messages binding listed fields | one message binding the whole unsigned transaction |
| An approval's life | until the transaction's own `valid_until_height` | at most `APPROVAL_LIFETIME_BLOCKS` above the executing height |
| Result codes | 45 | 50, gaining 45 through 49 |
| Block header | 154 octets, schema version 9 | unchanged |
| Prologue at an assignment height | settle, pay the closing month, accrue, accumulate figures, discard evidence | the same, with the **registry step** before evidence is discarded |

## Scope

Version ten defines:

- the machine-key entry, its inverse, and the retirement entry;
- kind 23's body, authority, and ordered rejection conditions;
- kind 10's new body and its ordered rejection conditions;
- the attestation, registration, and approval messages;
- the approval lifetime rule and which transactions it governs;
- the registry step;
- the version-ten genesis, chain identity, and state root;
- the five new result codes;
- the resource bounds;
- the compatibility boundary against versions one through nine.

It does not define:

- **how the build authority decides to attest a machine.** Remote attestation
  of a running build is off chain, and the threat model's T4 owes it review;
- **the threshold secret** behind a HUB key (ADR 0100), which is invisible to
  consensus;
- **legacy records** (requirement 6). The constitution reserves "conflicting
  statement precedence, and reclaim transitions", which are most of what a
  legacy transition would decide;
- **rotating or revoking the launch key, the build authority key, or a person's
  HUB key.** Each is founder-reserved (threat model T8 and T9);
- **the application-contract version** that carries version ten, which is
  named under [Compatibility boundary](#what-the-application-contract-must-gain);
- anything else version nine leaves unestablished.

## Bindings

This specification holds no second copy of any founder-directed value.

**The answers** are [ADR 0100](../decisions/0100-founder-answers-on-who-verifies-and-how-registration-starts.md)
and [ADR 0101](../decisions/0101-founder-answers-on-the-launch-cutoff-an-active-machine-and-the-registration-limit.md).
The cutoff of 100 active machines, the meaning of an active machine, and the
limit of 1,000 registrations a day are read from them.

**The meaning of "met"** is `cycle-boundary-v1`'s `ACTIVITY_THRESHOLD_SECONDS`,
applied to version eight's uptime figure for the seat and the window. Version
seven's settlement step 2 derives the same fact.

**Everything carried from version nine** is imported unchanged.

## Constants

| Name | Value | Source |
| --- | ---: | --- |
| `CYCLE_BLOCKS` | 28,800 | `cycle-boundary-v1` |
| `SLOT_BLOCKS` | 1,200 | `uptime-measurement-v1` |
| `ACTIVITY_THRESHOLD_SECONDS` | 64,800 | `cycle-boundary-v1` |
| `ASSIGNMENT_LAG_WINDOWS` | 2 | `economy-transition-v7` |
| `MAX_SEAT_ID` | 99,999 | Founder Constitution |
| `LAUNCH_RETIREMENT_ACTIVE_MACHINES` | 100 | ADR 0101 |
| `MACHINE_REGISTRATIONS_PER_WINDOW` | 1,000 | ADR 0101 |
| `APPROVAL_LIFETIME_BLOCKS` | 1,200 | this document |
| `LAUNCH_ATTESTER` | 4,294,967,295 | this document |
| `GENESIS_PREFIX_BYTES` | 182 | this document |

**`LAUNCH_ATTESTER` is `u32` maximum**, a value no seat identifier can take,
because `MAX_SEAT_ID` is 99,999. A registration names it to say that the launch
key signed rather than a machine.

**`APPROVAL_LIFETIME_BLOCKS` is one slot**, about an hour at the commit target.
It is engineering's to choose: the constitution requires a "fresh" approval and
fixes no figure. It is long enough to cover inclusion under ordinary load, and
short enough that a withheld approval dies within the hour.

All three ADR 0101 figures are **consensus parameters of this version and not
deployment options**, for the reason `TIMESTAMP_TOLERANCE_MILLIS` is one: two
machines applying different values disagree about which blocks are acceptable.

## The machine-key registry

### Canonical economy state

Version nine's key space with three entry kinds added. Every other kind, key
width, and value width is unchanged.

| Kind | Entry | Key | Key bytes | Value | Value bytes |
| ---: | --- | --- | ---: | --- | ---: |
| 24 | machine key | `u8(24) \|\| seat_id:u32` | 5 | see below | 92 |
| 25 | launch retirement | `u8(25)` | 1 | `retired_at_height:u64` | 8 |
| 26 | machine-key owner | `u8(26) \|\| machine_public_key:32` | 33 | `seat_id:u32` | 4 |

The machine-key value, in this order:

| Field | Bytes | Meaning |
| --- | ---: | --- |
| `machine_public_key` | 32 | the Ed25519 key this seat's machine signs registrations with |
| `build_digest` | 32 | the attested build the key was registered under |
| `registered_at_height` | 8 | the height of the kind-23 transaction that last wrote the key |
| `last_met_window` | 8 | the most recent assigned window in which the seat met the cycle, or 0 for none |
| `registration_window` | 8 | the window the count below belongs to |
| `registrations_in_window` | 4 | registrations this seat's key signed that executed in that window |

Every integer is big-endian.

**The entry is keyed by the seat**, because every ADR 0101 rule is about a
machine, and a machine is a seat. Activity is the seat's cycle, and the limit is
the machine's count. **The inverse entry exists so that one key serves one
seat.** Without it, one key registered on two seats would sign under two
limits, and a compromised machine would double what ADR 0101 caps.

**`last_met_window` of 0 means none, and is unambiguous.** A seat is in scope
only from the window after its activation, so no seat is in scope in window 0,
and no window-0 assignment can mark a machine.

**The retirement entry is present or absent, and is never removed.** Its value is
the height of the block that retired the launch key. Absence means the launch
key may still sign. A zero value would be a second encoding of absence, which
`protocol-primitives-v1` forbids, and no height that runs a registry step is 0.

### An active machine

At height `h`, let `assigned(h) = window_of_height(h) - 2` when
`window_of_height(h) >= 2`, and none otherwise. That is the most recently
assigned window at every height, because window `w` is assigned in the prologue
of the first height of window `w + 2`.

A seat's machine is **active at `h`** when it has a machine-key entry, and that
entry's `last_met_window` is nonzero and equals `assigned(h)`.

This is ADR 0101's answer encoded: the seat met its most recently assigned
cycle. **"Met" is the uptime test, whatever the accumulation cap says**, because
ADR 0101 reads the answer as the uptime record and not the distribution. A
capped seat whose machine ran all day is active. So is a seat past its 731
cycles, which ADR 0049 keeps in scope and measured.

**Version nine does not hold this fact, which is why the entry does.** The
assignment record's `accrued` bit means met, in span, and under the cap, and its
`winner` bit means won. The window's uptime records are deleted in the same
prologue that assigns it. So the registry step records the fact for the seats
that have a machine key before the evidence goes.

### Kind 23: register machine key

| Field | Bytes | Offset |
| --- | ---: | ---: |
| `seat_id` | 4 | 80 |
| `machine_public_key` | 32 | 84 |
| `build_digest` | 32 | 116 |
| `attestation_signature` | 64 | 148 |
| `hub_signature` | 64 | 212 |

Body 196 octets; unsigned 292; signed 356. Scheme 1: a signer resolves the
acting escrow. Any other scheme is `MALFORMED_TRANSACTION` at admission step 1.

The build authority signs the attestation:

```text
attestation_message =
  D("protocol-stack:v10:machine-attestation") ||
  chain_id || u32(seat_id) || machine_public_key || build_digest ||
  u64(valid_until_height)
```

`valid_until_height` is the transaction's own, so the attestation and the
transaction expire together. The approval lifetime rule then bounds both.

Rejection conditions, in this order, after the shared envelope checks and the
approval lifetime rule:

1. a `seat_id` above `MAX_SEAT_ID` is `CYCLE_RANGE`;
2. an unpurchased seat is `SEAT_NOT_PURCHASED`;
3. an unactivated seat is `SEAT_NOT_ACTIVATED`;
4. a seat whose identity is not the acting escrow's owner is `UNAUTHORIZED`;
5. a `machine_public_key` that a machine-key owner entry already names, for any
   seat including this one, is `REPLAY`;
6. an attestation that does not verify over the attestation message, against
   the genesis `build_authority_key`, is `UNAUTHORIZED`;
7. a `hub_signature` of 64 zero octets is `BIOMETRIC_REQUIRED`, and one that
   does not verify over the approval message against the seat identity's
   recorded `hub_public_key` is `UNAUTHORIZED`.

On success, if the seat has no machine-key entry, the transition writes one with
the key, the digest, `registered_at_height = h`, and every other field zero.
**If it has one, it replaces the key, the digest, and `registered_at_height`, and
keeps the other three fields.** It deletes the old key's owner entry, writes the
new key's, and charges the fixed fee to the acting escrow. It is atomic.

**A replacement keeps the count and the activity**, and both are deliberate.
Activity belongs to the seat's cycle, not to the key, so a machine that replaces
its key mid-window stays active. **The count must not reset**, or rotating keys
would bypass ADR 0101's limit. Replacing a key is how a founder retires a
compromised one, and nothing else in this version revokes a key.

**The HUB approval is always required, and the posture does not waive it.**
Installing a key that can admit people is authority over the ecosystem, not
movement of the founder's own value. The constitution's rule for sensitive
Founder actions requires an accepted signature and a fresh biometric approval
together, so a stolen signer key cannot install a rogue verifier on a founder's
seat.

### Kind 10: HUB register

The body gains the attesting seat, and the registration message binds it.

| Field | Bytes | Offset |
| --- | ---: | ---: |
| `hub_identity_hash` | 32 | 80 |
| `first_signer_public_key` | 32 | 112 |
| `attesting_seat_id` | 4 | 144 |
| `attestation_signature` | 64 | 148 |

Body 132 octets; unsigned 228; signed 292. Scheme 2, nonce 0, and fee limit 0,
as in version nine. The HUB key signs the envelope, as in version nine.

```text
registration_message =
  D("protocol-stack:v10:hub-registration") ||
  chain_id || u32(attesting_seat_id) || hub_identity_hash || hub_public_key ||
  first_signer_public_key || u64(valid_until_height)
```

`hub_public_key` is the envelope's authority key. **Binding the attesting seat
means one machine's signature cannot be presented as another's**, so each
registration counts against the limit of the machine that actually signed it.

Rejection conditions, in this order, after `EXPIRED` and the approval lifetime
rule:

1. an already-registered `hub_identity_hash` is `REPLAY`;
2. a first signer key already assigned to any escrow is `REPLAY`;
3. when `attesting_seat_id` is `LAUNCH_ATTESTER`:
   - a present retirement entry is `LAUNCH_KEY_RETIRED`;
   - an attestation that does not verify over the registration message, against
     the genesis `launch_key`, is `UNAUTHORIZED`;
4. otherwise:
   - a `seat_id` above `MAX_SEAT_ID` is `CYCLE_RANGE`;
   - a seat with no machine-key entry is `MACHINE_KEY_NOT_FOUND`;
   - a machine that is not active at `h` is `MACHINE_NOT_ACTIVE`;
   - an attestation that does not verify over the registration message, against
     the entry's `machine_public_key`, is `UNAUTHORIZED`;
   - a machine whose count for `window_of_height(h)` already stands at
     `MACHINE_REGISTRATIONS_PER_WINDOW` is `REGISTRATION_LIMIT`;
5. an entry airdrop that does not fit channel 8 is `CHANNEL_CAP`.

On success it performs version nine's four writes. When a machine attested, it
also sets that entry's `registration_window` to `window_of_height(h)`. It sets
`registrations_in_window` to one more than its stored value when the stored
window equals `window_of_height(h)`, and to 1 otherwise. It is atomic.

**The limit is checked after the signature**, so that a refusal for the limit is
only ever given for a registration that was otherwise valid. A forgery naming a
full machine is `UNAUTHORIZED`, which is the true reason.

**The launch key has no daily limit.** ADR 0101 makes it the only signer until
it retires, and a limit would only slow the launch.

**A machine that is active at `h` may register its own seat's owner's second
identity**, and the chain cannot tell. Uniqueness is the sandbox's to decide.
The chain checks the signature, never the capture, as the threat model's trust
boundary states.

## Single-use HUB approvals

### One message for every approval

Version nine's five HUB messages, for purchase, activation, mint, posture relax,
and transfer confirmation, are replaced by one:

```text
approval_message =
  D("protocol-stack:v10:hub-approval") || approved_bytes
```

`approved_bytes` is the transaction's unsigned encoding, with its 64-octet
`hub_signature` field set to zero octets. It verifies against the acting
escrow's owning identity's recorded `hub_public_key`.

The kinds that carry a body HUB approval are 2, 3, 4, 5, 17 (when it relaxes),
18, 19, 22, and 23. Kinds 13 through 16 are already signed by the HUB key over
their whole envelope, and are unchanged. Kind 10 is signed by the HUB key over
its envelope, and by an attester over the registration message.

**The approval binds everything the transaction says**: its kind, chain, signer,
nonce, fee limit, validity, and every body field. **The escrow's nonce therefore
makes it single-use.** A transaction at nonce `n` executes successfully at most
once. Any other transaction differs in at least the nonce, so it is not what was
approved. A refused transaction writes nothing and does not advance the nonce,
so its approval stays valid for exactly that transaction until it expires.

Version nine's own builders bind lists of fields, one list per kind. Binding the
whole transaction makes that per-kind work unnecessary. It is also exactly what
ADR 0099's verifier already sees: the person approves a transaction, and the
verifier signs that transaction.

**The domain label separates it from the envelope signature.** An envelope is
signed over `protocol-stack:v1:` labels, and an approval over
`protocol-stack:v10:hub-approval`. So a signer signature can never pass as an
approval, and an approval can never pass as a signer signature, even when a
person's HUB key and a signer key coincide.

### The approval lifetime rule

A transaction that carries a HUB proof, with `valid_until_height` above
`h + APPROVAL_LIFETIME_BLOCKS`, is `APPROVAL_LIFETIME_EXCEEDED`. That covers:

- kinds 10, 13, 14, 15, 16, and 23, always;
- kinds 2, 3, 4, 5, 17, 18, 19, and 22, when their `hub_signature` is not 64
  zero octets.

The rule is applied immediately after `EXPIRED`, in the shared envelope checks.
A transaction with no HUB proof is not governed by it: kinds 1, 6, 20, and 21,
and a body-carried kind presented with the field absent.

**The nonce makes an approval single-use. The lifetime makes a withheld one
die.** Without the lifetime, an approval for nonce `n` that was never submitted
stays valid until the escrow's nonce moves. A hostile wallet could hold one for
months. Both rules are needed, and neither implies the other.

### What this closes

Each of version nine's executed replays is refused under version ten, for a
stated reason:

- **A republished posture relax** carries the old nonce, so it is
  `NONCE_MISMATCH`. Re-signing it under a new nonce makes it a different
  transaction, whose approval verifies against nothing the owner signed, so it
  is `UNAUTHORIZED`.
- **A second transfer under one confirmation** is the same case, in both of its
  forms.

`hub-test-verifier-v9`'s replay check records version nine's acceptance. Its
version-ten successor must record both refusals.

## Block execution

Version nine's block transition, with one step added to the prologue.

### The registry step

At an assignment height, after version nine's figure accumulation and **before
the due window's kind-19 entries are deleted**:

1. For every machine-key entry, in ascending seat order, whose seat met the due
   window, set `last_met_window` to the due window. A seat meets the window when
   it is in scope for it, and `uptime_seconds(seat, due)` is at least
   `ACTIVITY_THRESHOLD_SECONDS`.
2. Count the machine-key entries whose `last_met_window` equals the due window.
3. If no retirement entry is present, and the count is at least
   `LAUNCH_RETIREMENT_ACTIVE_MACHINES`, write the retirement entry with
   `retired_at_height = h`.

**The count is computed, never stored.** It is needed only at an assignment, and
every machine it counts has just been marked, so storing it would add a
quantity that could disagree with the entries. Between assignments no
transition makes a machine active. A new key starts at `last_met_window = 0`,
and a replacement keeps its seat's mark.

**Retirement happens at an assignment, and nowhere else.** The cutoff is a count
of machines that met a cycle, and that count changes only when a cycle is
assigned. Once written, the entry is never removed, so a later fall below 100
never revives the launch key. That is ADR 0100's "for good".

**A newly activated seat's machine is not active for two to three days.** It
enters scope in the window after its activation, and that window is assigned
two windows later. So the launch key signs at least through the network's
first measured windows, whatever sells first. ADR 0101 records it.

**The step writes nothing on a chain with no machine keys**, which is every
chain version nine's fixtures build. It adds one ordered pass over the
machine-key entries per assignment.

## Result codes

Version ten adds five codes. Codes 0 through 44 keep their version-nine meanings.

| Code | Name | Raised by |
| ---: | --- | --- |
| 45 | `LAUNCH_KEY_RETIRED` | kind 10 naming `LAUNCH_ATTESTER` after the retirement entry is written |
| 46 | `MACHINE_KEY_NOT_FOUND` | kind 10 naming a seat with no machine-key entry |
| 47 | `MACHINE_NOT_ACTIVE` | kind 10 naming a machine that is not active at `h` |
| 48 | `REGISTRATION_LIMIT` | kind 10 naming a machine at its count for the window |
| 49 | `APPROVAL_LIFETIME_EXCEEDED` | any transaction the lifetime rule governs |

**Each new code names a fact a person can act on.** "The launch is over, ask a
machine." "This seat has no machine." "That machine is down." "That machine is
full today, try the next one." "Your wallet asked for too long." Folding any of
them into `UNAUTHORIZED` would make a person's next step guesswork.

## Receipts

Version nine's receipt layout, with the version field at `10`.

## Resource bounds

| Entry | Octets each | Bound at capacity |
| --- | ---: | ---: |
| machine key (24) | 97 | 100,000 |
| machine-key owner (26) | 37 | 100,000 |
| launch retirement (25) | 9 | 1 |

**The standing cost is about 13.4 MB at the 100,000-seat capacity.** It is paid
only by a chain on which every seat has registered a machine. Version ten adds
no entry per identity, so the 1,000,000-identity bound adds nothing.
Requirement 8 is met for every entry this version adds.

**The peak block is an assignment on a chain where every seat has a machine
key.** It rewrites up to 100,000 machine-key values, one `u64` each, which is
the cost version nine already pays to read every in-scope seat's uptime. A
registration writes one machine-key value, and kind 23 writes two owner entries
and one machine-key entry.

## Invariants

Version nine's invariants are unchanged, and seven are added. Each is checked,
never assumed.

1. Every machine-key entry's seat is purchased and activated.
2. The machine-key owner entries are exactly the inverse of the machine-key
   entries. Every owner entry names a seat whose entry holds that key, and every
   machine-key entry's key has an owner entry naming its seat.
3. No two machine-key entries hold the same key.
4. Every `last_met_window` is 0 or at most `assigned(h)`.
5. Every `registration_window` is at most `window_of_height(h)`.
6. Every `registrations_in_window` is at most
   `MACHINE_REGISTRATIONS_PER_WINDOW`.
7. A retirement entry, once present, is present at every later height with the
   same value.

## Version-ten genesis

Version nine's field table, with the schema version at `10`, one field renamed,
and one added. **The order below is the encoding's.**

| Field | Bytes | Offset |
| --- | ---: | ---: |
| magic `PSGN` | 4 | 0 |
| `schema_version` = 10 | 2 | 4 |
| `network_id` | 4 | 6 |
| `genesis_timestamp` | 8 | 10 |
| `supply_limit` | 8 | 18 |
| `total_supply` | 8 | 26 |
| `fixed_transfer_fee` | 8 | 34 |
| `initial_fee_pool` | 8 | 42 |
| `manifest_digest` | 32 | 50 |
| `launch_key` | 32 | 82 |
| `dispute_authority_key` | 32 | 114 |
| `build_authority_key` | 32 | 146 |
| `account_count` | 4 | 178 |

The prefix is **182 octets**. The account bound that follows from the
1,048,576-octet object limit falls from 21,842 to **21,841**. It stays
unreachable, because zero genesis accounts is still required.

**`launch_key` keeps `verifier_key`'s offset**, because it is the same key in a
narrower role. Version nine's key signed every registration for the chain's
whole life. Version ten's signs only until retirement.

**`build_authority_key` is a third, separate key.** The launch key admits
people. The build authority admits machines. ADR 0048 names whoever signs the
build as the root of trust, and keeping that apart from the launch key means
retiring the launch key changes nothing about which machines are admitted. The
dispute authority stays separate for version eight's reason.

```text
chain_id = H(D("protocol-stack:v10:chain-id") || canonical_genesis_v10_bytes)
```

**Genesis writes version nine's sixteen economy entries and no others.** It
writes no machine key, no owner entry, and no retirement entry. Entry kind 8,
which version six named the verifier key, holds the launch key. The build
authority key is not written to state: like the dispute authority key, it is a
genesis field bound into the chain identity.

## Version identity

| Construction | Version ten |
| --- | --- |
| chain ID | `protocol-stack:v10:chain-id` |
| state root | `protocol-stack:v10:state-root`, version field `10` |
| economy tree | `protocol-stack:v10:economy-empty`, `-leaf`, `-node` |
| genesis schema version | `10` |
| receipt version | `10` |
| block ID | `protocol-stack:v9:block-id`, unchanged |
| block header schema version | `9`, unchanged |

**The block header is not re-versioned, because its bytes do not change.** It
carries a state root, and the root's own label and version field already
separate a version-ten root from every earlier one. The precedent is versions
two through eight, which all inherited version one's header. So every component
that parses a header keeps version nine's parser.

**Every other label keeps the version that accepted it.** The kind-22 mint
keeps no message of its own: kind 22 now carries the version-ten approval, like
every other body-carried kind.

## Compatibility boundary

**Transaction bytes.** A version-one signed transfer is still a version-ten
kind-1 transaction, byte for byte. Kinds 2, 3, 4, 5, 17, 18, 19, and 22 keep
their version-nine shapes, and **their HUB field's meaning changes**. A
version-nine approval in a version-ten transaction does not verify, because it
signed a different message. That is the second divergence between bytes and
behavior in the project's history; version six's kind 1 was the first. Kind
10's body grows by four octets, so neither version decodes the other's kind 10.
A version-nine node refuses kind 23 at admission step 1 as
`MALFORMED_TRANSACTION`.

**State.** A version-nine state is not a version-ten state, and the converse
holds too. Version nine's decoder refuses entry kinds 24 through 26. There is no
upgrade block, no migration, and no state translation, as between every earlier
pair.

**Genesis.** A version-nine genesis is 150 octets and a version-ten genesis is
182, so neither decodes as the other.

**Roots and identity.** The chain ID, state root, and economy tree have
distinct labels and version fields from all nine predecessors. Each
non-collision is required separately.

**What is not claimed.** No accepted vector, digest, receipt, root, or recorded
devnet result of any earlier version changes, and none is recomputed under this
specification.

### What the application contract must gain

`consensus-application-v2` is accepted for version nine. It maps execution
results 1 through 44 to ABCI codes 257 through 300, under the
`protocol-stack-v9` codespace. A version-ten application needs a contract that:

- names `economy-transition-v10` as the ledger it drives;
- maps results 1 through 49, so the range reaches 305;
- reads a 182-octet genesis.

The header, the timestamp, and every rule about proposals carry over unchanged,
because version ten changes none of them. Whether that is a new contract version
or a stated rebinding is the application slice's to decide, as it was for
version nine.

## The founder-decision gate this document ran

Every decision this document makes was enumerated before it was judged.

- **Delegated, with their source:**
  - who may sign a registration (ADRs 0048 and 0100);
  - the launch key and its retirement at 100 active machines (ADRs 0100 and
    0101);
  - what an active machine is, and the per-window limit (ADR 0101);
  - that "met" is the uptime test (ADR 0101's own reading);
  - that the build authority attests machines (ADR 0048: the company during
    initialization);
  - that a sensitive action needs a fresh biometric approval (the
    constitution).
- **Mechanism, recorded in ADR 0102:**
  - the entry shapes and the inverse index;
  - the attesting seat in kind 10;
  - kind 23, and that a replacement keeps its count;
  - the whole-transaction approval;
  - the one-slot lifetime;
  - the five result codes;
  - the registry step's place;
  - the separate build authority key;
  - the unchanged header.
- **Not decided, because each is reserved:**
  - legacy precedence and reclaim;
  - rotation and revocation of the launch key, the build key, and a HUB key;
  - coercion controls.

None of the mechanism sets a value or changes what a participant must do, own,
run, or receive.

## Required vectors and evidence

A version-ten model and kernel must reproduce recorded vectors that show at
least:

- **genesis**: the 182-octet prefix, the chain ID, and the sixteen entries;
- **kind 23**: success, replacement keeping the count and the mark, and every
  rejection in order, including a key already owned by another seat and by the
  same seat;
- **kind 10**:
  - under the launch key before and after retirement;
  - under an active machine, an inactive one, and a seat with no key;
  - at the 1,000th and 1,001st registration in one window, and the count
    resetting in the next;
  - a signature presented under another seat's identifier;
- **the approval**: each body-carried kind approved over the whole
  transaction; a version-nine-style approval refused; the republished relax
  and the reused transfer confirmation refused, each in both forms;
- **the lifetime**: valid at exactly `h + 1,200`, and
  `APPROVAL_LIFETIME_EXCEEDED` at `h + 1,201`, for a body-carried kind and for
  a scheme-2 kind; ungoverned when the field is absent;
- **the registry step**:
  - a seat that met, one that failed, one at the cap, and one past its span;
  - the count reaching 99 and then 100;
  - retirement written exactly once, and not revived when the count falls;
- **invariants**: each of the seven, by a probe that breaks it;
- **non-collision** of every re-versioned construction with all nine
  predecessors.
