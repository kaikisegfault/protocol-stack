# Economy transition v8

Status: Accepted M3 consensus transition contract; model, execution, vectors,
and C++20 kernel implementation still owed

This document defines the version-eight Founder Economy consensus transition. It
is [`economy-transition-v7`](economy-transition-v7.md) with **an on-chain
carrier for [`uptime-measurement-v1`](uptime-measurement-v1.md)**, so that the
cycle assignment a block writes is derived from evidence the chain itself
recorded rather than from a schedule a caller supplies.

The change is classified as encoding, state-transition shape, authority, and
compatibility.
[ADR 0063](../decisions/0063-the-version-eight-uptime-carrier.md) records the
decisions and the alternatives rejected.

It satisfies requirement 5 of [`first-goal.md`](../project/first-goal.md) for the
uptime pipeline, completes the on-chain half of requirement 7, and re-satisfies
requirement 6 under an eighth chain identity.

## Relationship to version seven

[`economy-transition-v7.md`](economy-transition-v7.md) is not edited, retracted,
or reinterpreted, and `test-vectors/economy-transition-v7.txt` and
`test-vectors/economy-transition-v7-execution.txt` remain normative and passing.
Version seven's own versioning section fixes its state key space, its result
codes, and its fourteen transaction kinds as immutable, so adding a kind, an
entry, a code, and a genesis field is a new version rather than a repair.

**Everything else in version seven carries over unchanged and is incorporated by
reference**: the recovery pool and its entry; the extended cycle assignment
record and its 64-octet fixed part; the settlement's eight steps and their order;
both conservation identities; the two seat sets and the rule that neither may be
narrowed to the other; the account architecture of identities, keyless escrows,
and revocable signers; all fourteen transaction kinds with their bodies,
authorities, and ordered rejection conditions; the six HUB messages and their
labels; the per-escrow security posture and both posture predicates; the
accumulation cap; the bounded mint walk; the referral accrual and the unreferred
pool; every other economy state key and value encoding; the RFC 9162 tree shape;
the receipt layout; the thirty-three result codes and their meanings; and every
founder-directed figure in the accepted manifest.

**Five things change, and this document defines exactly those five.** The state
gains entry kinds 18 and 19. Two transaction kinds are added, 20 and 21. Twelve
result codes are added, 33 through 44. Genesis gains one field. And block
execution gains two steps, an issue step before the transactions and an expiry
step after them, while the assignment prologue stops taking a schedule and
derives one.

## What version eight changes

| | v7 | v8 |
| --- | --- | --- |
| Where the cycle schedule comes from | an `UptimeSchedule*` parameter a caller supplies | derived from chain state at the assignment prologue |
| Uptime evidence | none is representable on-chain | open challenges and per-seat window records |
| Challenge selection | not performed | performed in the block prologue against the previous state root |
| A challenge response | not representable | transaction kind 20 |
| An AI dispute | not representable | transaction kind 21, relayed, with a detached authority signature |
| Genesis fields | eight | nine, gaining `dispute_authority_key` |
| Genesis prefix | 110 octets | 142 octets |
| Result codes | 33 | 45 |
| Block execution | prologue, transactions | prologue, issue, transactions, expiry |

## Scope

Version eight defines the two new transaction kinds and their bodies,
authorities, and ordered rejection conditions; the two new state entries and
their exact keys and values; challenge selection in canonical octets; the four
ordered steps of block execution and what each reads and writes; the derivation
of the cycle schedule from state; the twelve new numeric result codes; the
version-eight genesis field table, chain identity, and state root; the resource
bounds the pipeline introduces; and the exact compatibility boundary against
versions one through seven.

It does not define the challenge's content, which
[`uptime-measurement-v1`](uptime-measurement-v1.md) places in its own
"explicitly not in scope" list as a founder-reserved resource commitment and
treats as an abstract predicate; the deterministic active-set protocol that
assigns validator duties, which that specification also scopes out and never
computes; direct-channel eligibility, which remains reserved; the calendar
month, the consensus timestamp, and the unreferred pool's payout, which are
`calendar-v1`; or anything else version seven leaves unestablished, all of which
is inherited unchanged.

## Bindings

This specification holds no second copy of any founder-directed value.

**The measurement contract** is the accepted
[`uptime-measurement-v1`](uptime-measurement-v1.md). The slot grid, the
challenge period, the response deadline, the dispute window, the dispute cap,
the credit rule, finalisation by expiry, and record completeness are read from it
and are not restated as independent figures.

**The window grid and the issuance span** are
[`cycle-boundary-v1`](cycle-boundary-v1.md)'s, including
`first_cycle_window(a) = window_of_height(a) + 1` and the 731-window span, which
is where in-scope and in-span are derived from rather than being supplied.

**The manifest layer, the settlement, the accumulation cap, the mint walk, and
the two conservation identities** are version seven's, imported unchanged.

## Constants

| Name | Value | Source |
| --- | ---: | --- |
| `CYCLE_BLOCKS` | 28,800 | `cycle-boundary-v1` |
| `SLOT_BLOCKS` | 1,200 | `uptime-measurement-v1` |
| `SLOTS_PER_WINDOW` | 24 | `uptime-measurement-v1` |
| `SLOT_SECONDS` | 3,600 | `uptime-measurement-v1` |
| `RESPONSE_DEADLINE_BLOCKS` | 20 | `uptime-measurement-v1` |
| `CHALLENGE_PERIOD_BLOCKS` | 1,200 | `uptime-measurement-v1` |
| `CHALLENGEABLE_HEIGHTS_PER_SLOT` | 1,180 | `uptime-measurement-v1` |
| `DISPUTE_CAP_SLOTS_PER_SEAT` | 6 | `uptime-measurement-v1` |
| `ASSIGNMENT_LAG_WINDOWS` | 2 | `economy-transition-v7` |
| `ANSWER_BYTES` | 32 | this document |

## Challenge selection

At every height, every in-scope seat is independently selected or not:

```text
beacon(h)            = the version-eight state root at height h - 1
preimage(seat, h)    = beacon(h):32 || u32_be(seat_id) || u64_be(h)
selection(seat, h)   = u64_be( first 8 octets of
                         H( D("protocol-stack:v8:challenge") || preimage ) )

challengeable(h)     = h <= slot_last_height(h) - RESPONSE_DEADLINE_BLOCKS
selected(seat, h)    = challengeable(h)
                       and selection(seat, h) mod CHALLENGE_PERIOD_BLOCKS == 0
```

`D` is `protocol-primitives-v1`'s domain separator and `H` is its digest, used
exactly as every other version-seven construction uses them. No cryptographic
primitive is implemented.

**The height is bound into the preimage** even though the beacon already varies
with it, so that a selection value is unique to one height and cannot be
presented as belonging to another.

**Truncating the digest to eight octets biases selection by less than one part
in `2^54`.** `2^64 mod 1200` is 1,216, so 1,216 of the 1,200 residues occur once
more often than the rest over the full 64-bit range. The alternative — reducing
the whole 256-bit digest — requires big-integer arithmetic on a consensus path
to remove a bias no observer could measure, and version eight declines it.

**The preimage is not `uptime-measurement-v1`'s.** That model digests an RFC 8785
JSON object, as every accepted model in this repository does. A consensus kernel
that canonicalised JSON to decide who is audited would put a parser on the most
adversarial path the pipeline has. **So the chain and the model select different
heights for the same beacon, and that is intended**: what the two share is the
rule — the beacon is the previous state root, the period is one challenge per
slot in expectation, and the final twenty heights of every slot are excluded —
and every property the accepted specification argues from is a property of the
rule rather than of the byte layout.

## Canonical economy state

Version seven's key space with two entry kinds added. Every other kind, key
width, and value width is unchanged.

| Kind | Entry | Key | Key bytes | Value | Value bytes |
| ---: | --- | --- | ---: | --- | ---: |
| 18 | open challenge | `u8(18) \|\| challenge_height:u64 \|\| seat_id:u32` | 13 | `state:u8` | 1 |
| 19 | seat window record | `u8(19) \|\| cycle_window:u64 \|\| seat_id:u32` | 13 | `credited:u32 \|\| disputed:u32` | 8 |

Every integer is big-endian, as version one fixed and every version since has
kept.

### The open challenge

One entry per issued, unresolved challenge. `state` is `0` while the challenge
is outstanding and `1` once it has been answered; it is never any other value,
and a decoder refuses one that is.

The entry is written by the issue step at its own challenge height, set to `1`
by an accepted kind-20 transaction, and read and deleted by the expiry step at
`challenge_height + RESPONSE_DEADLINE_BLOCKS`. It is therefore live at the end of
at most `RESPONSE_DEADLINE_BLOCKS` blocks, and it never crosses a slot boundary,
because selection excludes the final `RESPONSE_DEADLINE_BLOCKS` heights of every
slot.

**An answered challenge is kept until expiry rather than deleted**, so that a
second response to it reports `RESPONSE_REPLAY` rather than the false
`CHALLENGE_NOT_ISSUED`.

### The seat window record

One entry per seat per window **that has lost or had a slot voided**. Both
fields are 24-bit bitmaps in the low bits of a `u32`; bit `i` is slot `i`. The
upper eight bits of each are pad and must be clear, and a decoder that finds one
set refuses the value.

- `credited`: bit `i` set means slot `i` is credited on the seat's own evidence.
- `disputed`: bit `i` set means slot `i` was voided by a finalised dispute.

**An absent record for an in-scope seat reads as `credited` with all
twenty-four bits set and `disputed` empty.** A slot bit begins set and evidence
only ever removes credit, which is invariant 3 of the accepted measurement, so a
machine that answers every challenge writes nothing at all and the storage the
pipeline adds is proportional to failure rather than to population.

The record is created the first time the expiry step clears a bit or a dispute
sets one, and deleted by the assignment prologue once its window's record has
been consumed.

**A dispute sets a bit in `disputed` and does not clear one in `credited`.** The
record keeps what the seat's own evidence said, so the final credit is
`popcount(credited & ~disputed)` and the containment invariant — that a
maximally disputed perfect seat still meets its cycle — stays checkable against
the evidence rather than against a bitmap a dispute has already edited.

`disputed & ~credited` is therefore always empty, because a dispute may only
void a slot the seat was credited for. The two steps that write these bitmaps
can never touch the same bit: expiry clears bits only in the executing height's
own window, and a dispute reaches only a window that has already closed.

## Transaction kind 20: challenge response

| Field | Bytes | Offset |
| --- | ---: | ---: |
| `seat_id` | 4 | 0 |
| `challenge_height` | 8 | 4 |
| `answer` | 32 | 12 |

Body 44 octets. Scheme 1 — a signer resolves the acting escrow — and any other
scheme is `MALFORMED_TRANSACTION` at admission step 1. The transaction carries
no HUB signature: a response is evidence about a machine rather than a movement
of value or a change in an identity's standing, and one HUB interaction per hour
per seat forever is a cost with no corresponding claim.

**`answer` is opaque to version eight.** The predicate that decides whether an
answer is *correct* is the content of a challenge, which
[`uptime-measurement-v1`](uptime-measurement-v1.md) reserves to the founder and
treats as abstract. Version eight instantiates it as the weakest predicate
available: an answer of the defined width is accepted. **So version eight
measures liveness of a responder within sixty seconds and not possession of a
resource**, which is the limit the accepted specification already states about
itself. It follows that no path produces the model's `RESPONSE_INVALID`, so
version eight does not declare a code for it.

Rejection conditions, in this order, after version seven's shared envelope
checks:

1. A `seat_id` above `MAX_SEAT_ID` is `CYCLE_RANGE`, which is what version seven
   already reports for an out-of-range seat.
2. A `seat_id` with no seat record is `SEAT_NOT_PURCHASED`.
3. A seat that is not activated is `SEAT_NOT_ACTIVATED`.
4. An acting escrow whose owning identity is not the seat's recorded
   `hub_identity_hash` is `UNAUTHORIZED`.
5. A seat whose `first_cycle_window` is above the executing height's window is
   `SEAT_NOT_IN_SCOPE`.
6. A `challenge_height` at or above the executing height, or in a different slot
   from it, is `CHALLENGE_NOT_OPEN`.
7. An executing height above `challenge_height + RESPONSE_DEADLINE_BLOCKS` is
   `RESPONSE_TOO_LATE`.
8. No open challenge entry for `(challenge_height, seat_id)` is
   `CHALLENGE_NOT_ISSUED`.
9. An open challenge entry already in state `1` is `RESPONSE_REPLAY`.

On acceptance the entry's state becomes `1` and the fixed fee is charged. No
other state is written; a credited slot is not *added* by a response, because a
slot bit is already set and only expiry or a dispute ever clears one.

**Condition 7 precedes condition 8, and the accepted model orders them the other
way.** The model recomputes selection from beacons it retains for the open slot,
so it can distinguish "issued, and you are late" from "never issued". Version
eight deletes an open challenge at expiry, so after the deadline the entry is
gone and checking issuance first would report `CHALLENGE_NOT_ISSUED` about a
challenge that was issued. The reordering makes the report true; it changes no
accepted outcome, because both are refusals that write nothing.

Conditions 8 and 9 are the containment conditions the model names. A seat cannot
manufacture credit by answering a challenge it was never issued, and cannot
cover a missed challenge by answering an issued one twice.

## Transaction kind 21: file dispute

| Field | Bytes | Offset |
| --- | ---: | ---: |
| `seat_id` | 4 | 0 |
| `cycle_window` | 8 | 4 |
| `slot_index` | 1 | 12 |
| `reason_code` | 1 | 13 |
| `authority_signature` | 64 | 14 |

Body 78 octets. Scheme 1. **The envelope's authority is any signer**, who pays
the fee and supplies the nonce; the dispute authority signs the body instead.
This is kind 10's pattern, where a `verifier_signature` in the body is checked
against a recorded key while an ordinary signer carries the transaction, and it
is the right shape here rather than merely a familiar one: under
[ADR 0047](../decisions/0047-the-founder-machine-runs-the-ecosystem-ai.md) the
deciding machine "issues one signed, bounded decision" and someone submits it. A
scheme in which the authority were itself the envelope's signer would give the
ecosystem AI a chain account, a nonce sequence, a balance, and a fee obligation,
none of which any accepted document gives it.

The signed message is:

```text
dispute_message = D("protocol-stack:v8:dispute")
               || chain_id:32
               || u32_be(seat_id)
               || u64_be(cycle_window)
               || u8(slot_index)
               || u8(reason_code)
               || u64_be(valid_until_height)
```

`chain_id` binds the dispute to one chain and `valid_until_height` bounds how
long a signature may be held before it is relayed. The reason code is an audit
trail and carries no protocol effect, as the measurement contract states: every
dispute inside the bounds has the same effect on the result, so a mis-stated
reason cannot change what is paid. It is bound into the message anyway, so that
a relayer cannot alter the stated reason of a decision it did not make.

Rejection conditions, in this order:

1. An `authority_signature` that does not verify against the recorded
   `dispute_authority_key` over `dispute_message` is `UNAUTHORIZED_DISPUTE`.
2. A `seat_id` above `MAX_SEAT_ID` is `CYCLE_RANGE`.
3. A `seat_id` with no seat record is `SEAT_NOT_PURCHASED`.
4. A `slot_index` above `MAX_SLOT_INDEX` is `SLOT_RANGE`.
5. A `cycle_window` at or above the executing height's window is
   `WINDOW_NOT_CLOSED`.
6. A `cycle_window` more than one window below the executing height's window is
   `DISPUTE_WINDOW_CLOSED`.
7. A seat whose `first_cycle_window` is above `cycle_window` is
   `SEAT_NOT_IN_SCOPE`.
8. A slot already set in `disputed` is `DISPUTE_REPLAY`.
9. A slot not set in `credited` is `DISPUTE_SLOT_NOT_CREDITED`.
10. A `disputed` bitmap already holding `DISPUTE_CAP_SLOTS_PER_SEAT` bits is
    `DISPUTE_CAP_EXCEEDED`.

On acceptance the slot's bit is set in `disputed`, the record is created if
absent, and the fixed fee is charged to the relaying escrow. `credited` is not
changed, for the reason the record's definition gives.

Conditions 5 and 6 together are finalisation by expiry stated as a pair of
bounds: window `w` is disputable exactly while the executing height is inside
window `w + 1`, which is `ASSIGNMENT_LAG_WINDOWS` restated from the dispute
side. No signature, liveness, quorum, or acknowledgement is required at any
point, so an outage of the dispute authority of any length delays nothing and
withholds nothing.

**The dispute may only subtract, and only this far.** There is no transition by
which a dispute adds credit, and the cap is the founder-directed grace
allowance, so a seat credited for every slot still meets its cycle after a
maximal dispute. A compromised or captured authority key can reduce a result and
never manufacture one; it cannot mint, cannot move value to a chosen recipient,
and cannot fail a machine that was fully operational. That containment is the
measurement contract's and version eight preserves it exactly, which is what
makes the interim single key tolerable while
[ADR 0048](../decisions/0048-hub-verification-runs-locally-with-an-ai-integrity-monitor.md)'s
per-machine attestation registry is still owed.

## Block execution

Version seven's block transition with two steps added. The order is normative:

```text
1. prologue   assign the due window, then discard its evidence
2. issue      write an open challenge for every selected in-scope seat
3. transactions
4. expiry     resolve the challenges issued RESPONSE_DEADLINE_BLOCKS ago
5. conservation, roots, header
```

Everything version seven states about the block transition is unchanged: the
only valid next height is `h + 1`, admission failures are omitted from execution
and from the transaction root, every admitted transaction appends a receipt
whether it succeeds or fails, ordinary transaction results never reject a block,
and an internal invariant failure, height error, or resource-bound violation
rejects the whole proposed block and restores the pre-block state exactly.

### 1. The prologue assigns the due window and derives its schedule

The prologue runs at a height that opens a window, exactly where version seven
runs it: at `h` with `h mod CYCLE_BLOCKS == 0` and
`window_of_height(h) >= ASSIGNMENT_LAG_WINDOWS`, the due window is
`window_of_height(h) - ASSIGNMENT_LAG_WINDOWS`.

**Version eight removes the supplied schedule.** The due window's measured seats
are derived from state, in ascending seat order, one entry per in-scope seat:

```text
first_cycle_window(seat) = window_of_height(activation_height) + 1
in_scope(seat, w)        = seat is activated and first_cycle_window(seat) <= w
in_span(seat, w)         = in_scope(seat, w)
                           and w - first_cycle_window(seat) < 731
record(seat, w)          = the kind-19 entry for (w, seat), or
                           credited = all 24 bits, disputed = empty
credited_slots(seat, w)  = popcount( credited & ~disputed )
uptime_seconds(seat, w)  = credited_slots(seat, w) * SLOT_SECONDS
```

The result is version seven's `SeatCycle` sequence — seat, uptime, in-span — and
it is handed to version seven's `derive_assignment` unchanged. **The collection
mark and the recorded referrer are still read from the seat entry**, as ADR 0055
requires and version seven's settlement performs; nothing in the derived
schedule can supply either.

**Record completeness is structural.** The seat set is derived from the seat
table rather than supplied, so a seat cannot be omitted, and a seat with no
window record is present with a full credit rather than absent. This is the gap
`founder-economy-simulator-v2` and `cycle-boundary-v1` both record, closed by
construction rather than by validation.

After the assignment is applied, **every kind-19 entry for the due window is
deleted**. Two windows are retained at every height — the open one and the one
inside its dispute window — which is `uptime-measurement-v1`'s `RETAINED_WINDOWS`
of 2 obtained by deletion at a fixed point rather than by a retention rule.

A due window with no in-scope seats writes no assignment record, which is
version seven's behaviour for an absent measurement and the same fact as a
record with every bit clear.

### 2. The issue step writes the selected challenges

At every height `h`, for every in-scope seat of `window_of_height(h)` in
ascending seat order, `selected(seat, h)` is evaluated against
`beacon(h)`, which is the block's `previous_state_root` and is already computed.
Each selected seat gets a kind-18 entry at `(h, seat)` with `state = 0`.

The beacon is read once, at the height it belongs to, and never stored. A
retained ring of past roots would be new consensus state whose only purpose is
to re-derive something already derived, and materialising the selection makes
every downstream check a state lookup instead.

An entry that already exists at `(h, seat)` is an invariant failure and rejects
the block, because a height is written once.

### 3. The transactions

Version seven's execution, with kinds 20 and 21 added. A response can therefore
answer a challenge issued in the same block, which is what the strict inequality
of condition 6 permits: the model requires a response at a height in
`(c, c + 20]` and version eight's issue step precedes the transactions, so the
first height at which a challenge may be answered is `c + 1`.

### 4. The expiry step clears what was not answered

At every height `h` above `RESPONSE_DEADLINE_BLOCKS`, every kind-18 entry whose
`challenge_height` is `h - RESPONSE_DEADLINE_BLOCKS` is resolved and deleted, in
ascending seat order:

- `state = 1`: the challenge was answered in time. Nothing else is written.
- `state = 0`: the seat's bit for `slot_of_height(challenge_height)` is cleared
  in `credited`, creating the kind-19 record if it is absent. A bit already
  clear stays clear, which is what makes two lost challenges in one slot cost
  one slot.

**This is the model's slot-close sweep, made incremental and exact.** The model
clears a slot's bit at slot close when `slot_issued` exceeds `slot_answered`.
Selection excludes the final `RESPONSE_DEADLINE_BLOCKS` heights of every slot,
so every challenge issued in a slot has been answered or has expired before that
slot ends, and clearing at expiry gives the same bitmap with no per-seat
counters, no per-slot state, and no sweep over the population at a slot
boundary.

A slot bit belonging to a window earlier than the executing height's window is
never reached, because a challenge and its expiry are always inside one slot and
therefore inside one window.

### The two orderings that are consensus-visible

**The prologue precedes the issue step**, so a window's evidence is consumed
before the block that consumes it issues new challenges. The alternative writes
a challenge into a window whose record is being deleted in the same block.

**The expiry step follows the transactions**, so a response arriving in block
`c + RESPONSE_DEADLINE_BLOCKS` is counted. Expiring first would discard the last
admissible response to every challenge and shorten the deadline to nineteen
blocks without saying so.

## Result codes

Version seven's flat space extended contiguously. Codes 0 through 32 keep their
exact version-seven meanings, and 0 through 8 their version-one meanings.

| Code | Name | Produced by |
| ---: | --- | --- |
| 33 | `SEAT_NOT_IN_SCOPE` | kinds 20, 21 |
| 34 | `CHALLENGE_NOT_ISSUED` | kind 20 |
| 35 | `CHALLENGE_NOT_OPEN` | kind 20 |
| 36 | `RESPONSE_TOO_LATE` | kind 20 |
| 37 | `RESPONSE_REPLAY` | kind 20 |
| 38 | `UNAUTHORIZED_DISPUTE` | kind 21 |
| 39 | `SLOT_RANGE` | kind 21 |
| 40 | `WINDOW_NOT_CLOSED` | kind 21 |
| 41 | `DISPUTE_WINDOW_CLOSED` | kind 21 |
| 42 | `DISPUTE_REPLAY` | kind 21 |
| 43 | `DISPUTE_SLOT_NOT_CREDITED` | kind 21 |
| 44 | `DISPUTE_CAP_EXCEEDED` | kind 21 |

The space is 45 codes. Version seven's three frozen unreachable codes — 4, 23,
and 25 — keep their numbers and remain unreachable.

**Five of the measurement model's codes are deliberately not in this table**, and
each is absent for a stated reason rather than by oversight:

- `SCHEDULE_NOT_BOUND` and `INVALID_BOUND_SCHEDULE`: the model binds an external
  activation table and can be handed one that does not reproduce its digest. The
  chain's schedule is its own seat table, so there is nothing to bind and nothing
  that can fail to bind.
- `HEIGHT_RANGE` and `HEIGHT_NOT_MONOTONIC`: these are block-level conditions.
  `ledger-transition-v1` already rejects the whole block for both, and a block
  rejection is not a transaction result.
- `RESPONSE_INVALID`: the answer predicate is the challenge's content, which is
  founder-reserved and abstract under this version, so no path produces it.
  Declaring a code no path produces would claim coverage the vectors could not
  show.

`INVALID_DUTY_KIND`, `DUTY_REPLAY`, `RECORD_NOT_FINAL`, and
`WINDOW_HAS_NO_SEATS` are likewise absent: the first two belong to the duty
report, which this version does not encode, and the last two belong to the
model's `emit record` query, which is a derivation inside the prologue here
rather than a transaction anyone submits.

## Receipts

Version seven's receipt layout with the version field at `8`. A kind-20 or
kind-21 receipt issues nothing, so its issued amount is zero and its fee is the
fixed fee.

## Resource bounds

Two costs are consensus-visible in the sense that every node pays them at every
height, and they are stated here rather than discovered in an implementation.

**The issue step evaluates one digest per in-scope seat per height.** At the
100,000-seat capacity that is 100,000 digests, each over a 28-octet domain
separator and a 44-octet preimage, so about 7.2 MB of digest input per block.
Twenty of every 1,200 heights are not challengeable and issue nothing, so the
cost is paid at 1,180 heights in every 1,200. It is the direct
cost of `uptime-measurement-v1`'s per-seat independent selection, which is what
makes a challenge unpredictable until one block before it must be answered; a
formulation that selected a residue class in one digest would be cheaper and
would correlate the fate of every seat in the class. The evaluation is
order-independent and may be parallelised, but the entries it writes are in
ascending seat order.

**Open challenge entries are bounded by the deadline window.** Selection is one
in `CHALLENGE_PERIOD_BLOCKS`, so about 83 seats are selected per height at
capacity and about 1,667 entries are live at once. The structural worst case is
`in_scope * RESPONSE_DEADLINE_BLOCKS`, which no beacon reaches and which
no adversary can steer to, because influencing selection for one seat at one
height is the bias `uptime-measurement-v1` already refers to independent review.

**Seat window records are bounded by failure.** A record exists only for a seat
that lost or had a slot voided, at 21 octets of key and value, for at most two
windows. At capacity, with every seat losing at least one slot in both retained
windows, that is 4.2 MB. `uptime-measurement-v1`'s bound of 800,000 bytes counts
the model's per-seat evidence and not a keyed state entry; the two figures
measure different things and neither supersedes the other.

**The prologue's window boundary is the same order as the record it already
writes.** It reads at most one record per in-scope seat, derives the schedule,
and deletes them. Version seven's assignment record at capacity is already about
25 KB and its backing identity already walks every seat's assignments, which
[ADR 0055](../decisions/0055-the-version-seven-execution-model.md) records as an
implementation cost rather than a contract defect. Nothing here is
consensus-visible beyond its result, so a node may cache or incrementalise the
walk.

## Invariants

Version seven's invariants unchanged, with six added. Each is checked rather
than assumed.

1. An open challenge entry's `state` is `0` or `1`.
2. At the end of a block at height `h`, every open challenge entry has a
   `challenge_height` in `[h - RESPONSE_DEADLINE_BLOCKS + 1, h]`, so the
   pipeline retains no challenge whose deadline has passed.
3. Both bitmaps of a seat window record have their upper eight bits clear, and
   `disputed & ~credited` is empty.
4. `popcount(disputed)` never exceeds `DISPUTE_CAP_SLOTS_PER_SEAT`.
5. At the end of a block at height `h`, a seat window record exists only for
   `window_of_height(h)` and the window before it. Exactly two are retained at
   every height, including a boundary height, because the prologue deletes the
   due window's records before anything in that block can write to the window
   that just opened.
6. A seat credited for every slot has `uptime_seconds` at or above the
   founder-directed activity threshold after any admissible set of disputes,
   which is the measurement contract's containment theorem restated over the
   encoded state.

Invariant 6 is the one that makes the interim dispute authority safe, so it is
asserted after every accepted dispute rather than left to the cap arithmetic.

## Version-eight genesis

Version seven's field table with the schema version at `8` and one field added.

| Field | Bytes |
| --- | ---: |
| `network_id` | 4 |
| `supply_limit` | 8 |
| `fixed_transfer_fee` | 8 |
| `manifest_digest` | 32 |
| `verifier_key` | 32 |
| `dispute_authority_key` | 32 |
| `total_supply` | 8 |
| `initial_fee_pool` | 8 |
| `account_count` | 4 |

The prefix is 142 octets rather than 110, and the account bound that follows
from the 1,048,576-octet object limit falls from 21,843 to 21,842. It remains
unreachable, because zero genesis accounts is still required rather than
expected.

```text
chain_id = H(D("protocol-stack:v8:chain-id") || canonical_genesis_v8_bytes)
```

**`dispute_authority_key` is separate from `verifier_key` rather than reusing
it.** Whoever attests HUB identities should not thereby acquire the power to void
a machine's uptime; least privilege costs 32 octets here. It is the pre-pivot
single-key shape that `uptime-measurement-v1` names, and ADR 0048's registry of
per-machine attestation keys replaces it in a later transition version. The
replacement changes who signs, not what a signature can do.

**Genesis writes the same fourteen economy entries version seven writes.** The
dispute authority key is a genesis field bound into the chain identity, not a
state entry, exactly as `network_id` and `supply_limit` are. It writes no open
challenge and no seat window record.

## Version identity

| Construction | Version eight |
| --- | --- |
| chain ID | `protocol-stack:v8:chain-id` |
| state root | `protocol-stack:v8:state-root`, version field `8` |
| economy tree | `protocol-stack:v8:economy-empty`, `-leaf`, `-node` |
| genesis schema version | `8` |
| receipt version | `8` |
| challenge selection | `protocol-stack:v8:challenge` |
| dispute message | `protocol-stack:v8:dispute` |

**Every other label keeps the version that accepted it**, for the reason version
seven gives: a label names the artifact it derives. The account derivation stays
`protocol-stack:v1:account`, the escrow derivation stays
`protocol-stack:v6:escrow`, the two transaction signing labels stay at
`protocol-stack:v1:`, the six HUB messages keep their `protocol-stack:v6:`
labels, and the ordered transaction tree and the 146-octet block header stay
version one's, including its schema version field of `1`.

The two new labels are version eight's because both derive artifacts that did
not exist before.

## Compatibility boundary

**Transaction bytes.** A version-one signed transfer is a version-eight kind-1
transaction, byte-for-byte, with the same signing message, transaction ID, and
execution result numbers. A version-seven transaction of any kind is a
version-eight transaction of that kind by shape and belongs to a different chain
by binding. A version-seven node presented with a kind-20 or kind-21 transaction
rejects it at admission step 1 as `MALFORMED_TRANSACTION`.

**State.** A version-seven state is not a version-eight state and the converse
holds too: a version-eight state carries entries under kinds 18 and 19 that
version seven's decoder refuses. There is no upgrade block, no migration, and no
state translation, exactly as between every earlier pair.

**Genesis.** A version-seven genesis file is 110 octets and a version-eight file
is 142, so neither decodes as the other, and the schema version field differs
independently of the length.

**Roots and genesis identity.** The version-eight state root, chain ID, and
economy tree have distinct labels and version fields from all seven
predecessors, so no earlier root is reinterpreted and no version-eight root
collides with one. Each non-collision is required separately, because distinct
labels are strings rather than a chain.

**What is not claimed.** No accepted M1 or version-two through version-seven
vector, digest, receipt, root, or recorded devnet result changes, and none is
recomputed under this specification.

## Versioning and compatibility of this document

Everything version seven fixes as immutable is immutable here too, with the
state key space, the result code space, the kind space, and the genesis field
table taking their version-eight forms. The two new labels, the selection
preimage, the two new bodies and their field offsets, the ordered rejection
conditions, the four execution steps and their order, and the twelve new codes
are normative. A changed field, code, order, or semantic rule requires a new
transition version and an ADR; it must not reinterpret a version-eight
identifier.

Versions one through eight coexist as documents; every earlier artifact remains
in place, passing, and unedited.

## What this specification does not establish

Everything version seven does not establish is inherited unchanged. **Four
limits are new and belong to this version, and each is a bound on what the
recorded evidence means rather than a gap in the encoding.**

**The duty layer is vacuous.** `uptime-measurement-v1` produces a duty report
only for a duty a seat was *assigned*, and the deterministic active-set protocol
that assigns duties is outside that specification's scope and does not exist. An
empty assignment is satisfied vacuously, so under version eight no duty evidence
removes credit from any seat and **a seat's credit rests on the challenge layer
alone.** Version eight encodes no duty report, because a report signed by a
proposer is a value one node supplies and another cannot reproduce, a report
signed by the seat inverts the one property the measurement contract names, and
a reserved encoding no conforming chain can produce is what version seven
declined for the ADR 0049 pool lifecycle.

**An answered challenge proves liveness and not possession.** The challenge's
content is founder-reserved; until it is decided, an accepted answer establishes
that something able to produce thirty-two octets was reachable within sixty
seconds. Every anti-gaming claim in the measurement contract is bounded by this,
and version eight adds no claim of its own. A later version binding a real
predicate can only tighten what an answer must satisfy.

**The dispute authority is one key during an interim it names.** ADR 0047
distributes ecosystem AI judgment across Founder Machines and ADR 0048 replaces
the single verifier key with a per-machine attestation registry, and neither is
built here. The containment that makes the interim tolerable rests on the cap
and the subtract-only direction rather than on who holds the key.

**Sampling catches a dishonest machine probabilistically.** A seat down for `D`
challengeable heights escapes with probability `(1 - 1/1200)^D`; a full lost
slot is caught with probability about 0.63 and a full lost window with
probability above 0.999999. Those are properties of the sampling rate rather
than proofs about an adversary, and the concrete security margin needs the
independent review of requirement 15. The beacon's bias — a proposer with
influence over the state root at `h - 1` has some influence over who is
challenged at `h` — is the same adversary ADR 0027 already refers to that review.

## The one founder-reserved value this document defaults

**A challenge response charges the version-seven fixed fee**, because every
version-seven kind charges it and applying an accepted uniform rule to a new
kind invents nothing while carving out the contract's first exemption would.

The consequence is recorded rather than hidden. A seat expects one challenge per
slot, so a machine pays about twenty-four fixed fees per cycle to prove the
uptime it is paid for, and at the 100,000-seat capacity the population offers
about 2.4 million fee-paying transactions per day. Whether answering a mandatory
audit should cost an operator anything is a question about what a participant
must do in order to be paid, which is founder-reserved and is asked rather than
settled here.

**Nothing else in this document depends on the answer.** The rule is one
sentence in one transition, and it is settled before the model, the vectors, and
the kernel exist. If the answer is an exemption, the exemption is bounded by
construction: a response is accepted at most once per issued challenge, and the
chain itself decides how many challenges are issued.

## Required vectors and evidence

`test-vectors/economy-transition-v8.txt` will be normative. It must fix:

- **the version identity** — the two re-versioned constructions and the two new
  labels, the seven root non-collisions, and the 142-octet genesis prefix, each
  predecessor construction first required to reproduce its own accepted empty
  root so the comparison is against the real one;
- **the state surface** — kind 18's and kind 19's key and value widths, the
  rejection of an open challenge state above 1, the rejection of a window record
  with a pad bit set, the rejection of a record whose `disputed` holds a bit its
  `credited` does not, and the reading of an absent record as fully credited;
- **selection** — determinism against a fixed beacon, the excluded final twenty
  heights of a slot, the per-slot expectation over a recorded run, and the
  height binding, with the model's own selection *not* compared because the two
  preimages are different functions;
- **kind 20** — every one of its nine rejection conditions produced by executing
  a minimally mutated input against a positive control, including the reordered
  pair at the deadline boundary at `c + 20` and `c + 21`, and a response in the
  same block as its challenge refused as `CHALLENGE_NOT_OPEN`;
- **kind 21** — every one of its ten rejection conditions produced the same way,
  the dispute message's binding of the chain, the seat, the window, the slot,
  the reason, and the expiry, and a maximal six-slot dispute against a perfect
  seat leaving it above the activity threshold;
- **the execution order** — a response accepted in the expiry block and refused
  one height later, a challenge issued and expired across a slot boundary, and
  the prologue consuming a window whose records the same block would otherwise
  have written to;
- **the schedule derivation** — record completeness against a seat table with
  seats in and out of scope, a seat past its own 731 cycles present with
  `in_span` false, and a derived schedule reproducing a recorded version-seven
  assignment record exactly when the same seats and uptimes are measured, which
  is what proves the carrier changed no settlement.

`docs/engineering/verification.md`'s rules apply: a boolean vector may only be
true, a name asserts no more than its value establishes, and a claim is checked
against something other than itself.

**A second file must record what a chain conforming to this document does.**
`test-vectors/economy-transition-v8-execution.txt`, on version seven's pattern,
holds the recorded scenarios: a window measured entirely on-chain producing an
assignment record, a machine losing slots to unanswered challenges and failing
its cycle, a dispute voiding a slot and changing a winner set, and every
version-seven kind still executing unchanged against a version-eight ledger.

**The carryover claim is checked over the packages rather than over the vector
files**, as version seven established: a test must classify every constant
version seven exports as carried or revised, require the classification to be
total, and fail if the revised set is not exactly what this document lists.

Acceptance of the recorded artifacts requires full GitHub-hosted verification on
the exact commit that adds them.
