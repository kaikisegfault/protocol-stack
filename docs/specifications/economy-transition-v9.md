# Economy transition v9

Status: Accepted M3 consensus transition contract; independent model,
execution model, vectors, and the C++20 kernel's **codec** recorded; the C++20
kernel's ledger, the snapshot, the store, the application, the transport, the
node process, and the application-contract version below are not

This document defines the version-nine Founder Economy consensus transition. It
is [`economy-transition-v8`](economy-transition-v8.md) with **a clock and a
monthly settlement**, so that the two accepted contracts that today describe
rules no chain applies — [`calendar-v1`](calendar-v1.md) and
[`unreferred-pool-payout-v1`](unreferred-pool-payout-v1.md) — become behaviour
independent nodes reproduce exactly.

The change is classified as primitive, encoding, state-transition shape,
economics, and compatibility.
[ADR 0077](../decisions/0077-the-version-nine-clock-and-monthly-settlement.md)
records the decisions and the alternatives rejected.

It re-satisfies requirement 6 of [`first-goal.md`](../project/first-goal.md)
under a ninth chain identity, and it is the first version in which the
unreferred performance pool of requirement 9's lineage pays anybody.

**It exists because two accepted specifications are unenforced.** `calendar-v1`
defines a consensus timestamp no header carries and a month no transition reads.
`unreferred-pool-payout-v1` defines a ranking over figures no state holds and a
payout no block performs. Both took the posture
[`cycle-boundary-v1`](cycle-boundary-v1.md) and
[`uptime-measurement-v1`](uptime-measurement-v1.md) took before version eight:
the rules moved from undefined to unenforced. This is the version that closes
that gap, and it is the last such gap the Founder Economy has.

## Relationship to version eight

[`economy-transition-v8.md`](economy-transition-v8.md) is not edited, retracted,
or reinterpreted, and `test-vectors/economy-transition-v8.txt` and
`test-vectors/economy-transition-v8-execution.txt` remain normative and passing.
Version eight's own versioning section fixes its state key space, its result
codes, its kind space, and its genesis field table as immutable, so adding a
header field, a genesis field, four entry kinds, a transaction kind, and a step
of block execution is a new version rather than a repair.

**Everything else in version eight carries over unchanged and is incorporated by
reference**: the uptime carrier and both of its entry kinds; challenge selection
and its preimage; transaction kinds 20 and 21 with their bodies, authorities, and
ordered rejection conditions; the issue step and the expiry step; the derivation
of the cycle schedule from state; the dispute authority key and its containment;
and through version eight, every rule of versions one through seven — the
settlement's eight steps and their order, the recovery pool, the two seat sets,
the account architecture of identities, keyless escrows, and revocable signers,
the six HUB messages, the accumulation cap, the bounded mint walk, the RFC 9162
tree shape, the receipt layout, the forty-five result codes, and every
founder-directed figure in the accepted manifest.

**Six things change, and this document defines exactly those six.** The block
header gains a timestamp. Genesis gains a timestamp. The state gains entry kinds
20 through 23, and entry kind 12 gains a third quantity. One transaction kind is
added, 22. Block execution's prologue gains a monthly settlement between
settlement steps 7 and 8, and a figure accumulation after step 8. And the state
root commits to the timestamp, which re-versions the header, the chain identity,
the root, and the block identifier.

## What version nine changes

| | v8 | v9 |
| --- | --- | --- |
| Block header | 146 octets, schema version `1` | 154 octets, schema version `9` |
| A block's time | not represented | `timestamp:u64` in the header |
| Genesis fields | nine | ten, gaining `genesis_timestamp` |
| Genesis prefix | 142 octets | 150 octets |
| The calendar | defined by `calendar-v1`, applied nowhere | C1 and C2 in execution, C5 at admission |
| A month | derivable from a field no header carries | derived from the agreed header field |
| The unreferred pool | `accrued`, `minted`; nothing takes value out | `accrued`, `payable`, `minted`; a monthly payout takes value out |
| Entry kinds | 18 | 22, gaining 20, 21, 22, and 23 |
| Monthly uptime | not represented | per-seat figures for the accumulating month |
| A pool winner's award | not representable | a per-seat claim it mints |
| Transaction kinds | 16 assigned | 17 assigned, gaining kind 22 |
| Result codes | 45 | 45; version nine adds none |
| Prologue steps at an assignment height | settle, discard evidence | settle, **pay the closing month**, accrue, **accumulate figures**, discard evidence |

## Scope

Version nine defines the block header's timestamp field and the genesis
timestamp; where each of `calendar-v1`'s five rules is applied and which of them
a replaying machine must not re-apply; the four new state entries and the
extended pool entry with their exact keys and values; the derivation of a
window's month and the state that carries it; the monthly settlement — which
month closes, who competes, what each winner receives, and what happens to the
part that does not divide; the new transaction kind and its ordered rejection
conditions; the version-nine genesis field table, chain identity, state root, and
block identifier; the resource bounds the settlement introduces; and the exact
compatibility boundary against versions one through eight.

It does not define the challenge's content, the deterministic active-set
protocol, or direct-channel eligibility, all of which remain reserved and are
inherited unchanged; the **application-contract version** that carries a
timestamp from a consensus adapter into the application, which is named under
[Compatibility boundary](#what-the-application-contract-must-gain) and belongs to
its own slice on version eight's precedent; the adapter's algorithm for choosing
a proposed timestamp, which `calendar-v1` places outside consensus; or anything
else version eight leaves unestablished.

## Bindings

This specification holds no second copy of any founder-directed value.

**The clock** is [`calendar-v1`](calendar-v1.md). The unit, the epoch, the
accepted range, the five rules, the tolerance, the proleptic Gregorian
derivation, the month-opening predicate, and the boundary-shift bound are read
from it and are not restated as independent figures.

**The payout** is [`unreferred-pool-payout-v1`](unreferred-pool-payout-v1.md).
The candidate set, the ranking figure, the attribution rule, the exact-tie split,
the remainder, the carry, the settlement point, and the three quantities the pool
must carry are read from it. Through it,
[ADR 0075](../decisions/0075-founder-answers-on-the-monthly-pool-candidate-set-and-carry.md)
and [ADR 0076](../decisions/0076-the-monthly-pool-ranks-every-in-scope-seat.md)
are the founder answers this version implements rather than re-decides.

**The measurement, the window grid, the manifest layer, the settlement, the
accumulation cap, the mint walk, and the conservation identities** are versions
six through eight's, imported unchanged.

## Constants

| Name | Value | Source |
| --- | ---: | --- |
| `CYCLE_BLOCKS` | 28,800 | `cycle-boundary-v1` |
| `SLOT_SECONDS` | 3,600 | `uptime-measurement-v1` |
| `SLOTS_PER_WINDOW` | 24 | `uptime-measurement-v1` |
| `ASSIGNMENT_LAG_WINDOWS` | 2 | `economy-transition-v7` |
| `MAX_SEAT_ID` | 99,999 | Founder Constitution |
| `MILLIS_PER_DAY` | 86,400,000 | `calendar-v1` |
| `MIN_TIMESTAMP_MILLIS` | 0 | `calendar-v1` |
| `MAX_TIMESTAMP_MILLIS` | 253,402,300,799,999 | `calendar-v1` |
| `MAX_MONTH_INDEX` | 96,359 | `calendar-v1` |
| `TIMESTAMP_TOLERANCE_MILLIS` | 60,000 | `calendar-v1` |
| `GENESIS_PREFIX_BYTES` | 150 | this document |
| `BLOCK_HEADER_BYTES` | 154 | this document |

`TIMESTAMP_TOLERANCE_MILLIS` is a **consensus parameter of this version and not a
deployment option**, which is what ADR 0050 requires and `calendar-v1` restates:
two machines applying different tolerances disagree about which blocks are
acceptable, which is a fork. It appears in no genesis field and no configuration
file, exactly as `CYCLE_BLOCKS` does not.

## The consensus timestamp

### The block header gains a timestamp

The application-owned block header is **154 bytes**, which is
`protocol-primitives-v1`'s 146-byte header with one field inserted:

| Offset | Size | Field | Required value or range |
| ---: | ---: | --- | --- |
| 0 | 4 | magic | ASCII `PSBL` |
| 4 | 2 | schema version | `9` |
| 6 | 32 | chain ID | configured chain |
| 38 | 8 | height | `u64` |
| 46 | 8 | **timestamp** | `u64` milliseconds, `calendar-v1`'s unit and range |
| 54 | 32 | previous state root | 32 octets |
| 86 | 32 | ordered transaction root | 32 octets |
| 118 | 32 | resulting state root | 32 octets |
| 150 | 4 | transaction count | `u32` |

```text
block_id = H(D("protocol-stack:v9:block-id") || application_block_header)
```

**The timestamp is inserted after the height rather than appended**, and the
schema version changes with it. Appending would have kept every existing offset
identical, which is not a benefit here but a hazard: a decoder that read the
length loosely would parse a version-nine header as a version-one header with
eight trailing octets and agree with itself about every field. Moving the offsets
makes a mis-versioned decode produce a chain ID mismatch at the first comparison
rather than a plausible header. The height and the timestamp are also the two
fields that place a block on the two grids this ecosystem runs on — heights for
cycles, milliseconds for months — and a reader that stops before the roots should
have both.

**The block identifier is re-versioned** because it derives a different artifact.
Version eight kept `protocol-stack:v1:block-id` for the reason it kept every
other inherited label: the bytes it hashed were version one's. These are not.

### Where each of `calendar-v1`'s five rules is applied

`calendar-v1`'s central rule is that C5 reads a clock and the other four do not,
and that a machine replaying history must re-check C1 and C2 and must **not**
re-check C5. Version nine states where each is applied, because getting it wrong
is silent: a machine that re-applied C5 on replay would reject the chain's own
past one tolerance-width after it was produced.

| Rule | Applied by | On replay | Failure is |
| --- | --- | --- | --- |
| C1 range | deterministic execution | re-applied | a block rejection |
| C2 monotonicity | deterministic execution | re-applied | a block rejection |
| C3 height | deterministic execution, version one's | re-applied | a block rejection |
| C4 execution reads the field | the whole of this document | — | not a check |
| C5 tolerance | **admission only**, before a block is committed | **never re-applied** | a refused proposal |

**C1 and C2 are block-level conditions and produce no result code**, exactly as
`ledger-transition-v1`'s height rule does and for the same reason version eight
gives for `HEIGHT_RANGE` and `HEIGHT_NOT_MONOTONIC`: a block rejection is not a
transaction result. A block whose timestamp is out of range or below its
predecessor's is rejected whole, and the pre-block state is restored exactly.

**C5 is applied by the node once, at the point it first validates a height, and
is never part of the transition.** It is therefore not reachable from any
function this document defines, and a conforming implementation exposes it as a
separate entry point rather than as a branch inside execution. What the
consensus adapter must call, and when, is under
[What the application contract must gain](#what-the-application-contract-must-gain).

`calendar-v1`'s ordered rejection table governs which condition a machine
reports when more than one holds.

### The state commits to the timestamp

The version-nine state carries `timestamp` beside `height`, and the state root
commits to it:

```text
state_root =
  H(
    D("protocol-stack:v9:state-root") ||
    u16(9) || chain_id || height:u64 || timestamp:u64 || supply_limit:u64 ||
    total_supply:u64 || fee_pool_balance:u64 || account_count:u64 ||
    accounts_tree_root || economy_entry_count:u64 || economy_tree_root
  )
```

**This is forced rather than chosen, and the forcing argument is restart.** C2
compares `t(h)` with `t(h - 1)`. A machine that restarted, restored from a
snapshot, or reconstructed state from the durable head must know its predecessor's
timestamp in order to validate the next block at all; a value held only in a
header the node did not keep is not available to it. And a value two machines
could hold differently without their roots differing is a fork that no gate
catches, which is why it is committed rather than merely stored. It is version
one's argument for committing to `height`, applied to the second field that
orders blocks.

At genesis the state's `timestamp` is `genesis_timestamp`.

### The beacon widens, and the cost is stated rather than discovered

Version eight's challenge selection reads `beacon(h)`, the state root at
`h - 1`. Version nine's state root commits to the timestamp, so the beacon now
varies with it.

**A proposer's influence over who is challenged at the next height therefore
widens from the state it can shape to the state it can shape plus its own
timestamp.** Within C5 the proposer may choose any millisecond in a
120,000-value window, so on a block it could otherwise not vary — a quiet height
with no transactions, where version eight's root at `h - 1` was fully determined
— it gains about `2^16.9` grinding attempts at one digest each.

**The marginal risk is small and is the same risk already referred to
independent review.** A challenge harms only a seat that cannot answer it; a
proposer grinding to spare one colluding seat at one height improves odds that
were already 1,199 in 1,200, and sparing it across a whole slot requires
proposing at essentially every height. The beacon's bias — that a proposer with
influence over the state root at `h - 1` has some influence over who is
challenged at `h` — is stated by `uptime-measurement-v1`, referred to review by
ADR 0027, and restated by version eight. Version nine widens it on quiet blocks
and refers it to the same review rather than claiming it is new or claiming it
is nothing.

**The cheap mitigation is recorded and deliberately not taken.** A beacon that
excluded the timestamp would remove the new freedom, and it would cost a second
root construction on the most adversarial path the pipeline has: the beacon would
stop being a value the block header already carries and would have to be
recomputed at every height. Version nine keeps `previous_state_root` and states
the consequence. A later version that binds a real challenge predicate should
revisit the beacon as one decision rather than two.

## The calendar over this chain

Every derivation below is `calendar-v1`'s, read rather than restated:
`month_index(t)`, `month_start_millis(i)`, `month_end_millis(i)`, and
`month_of_height(h) = month_index(t(h))`.

### A window's month

```text
month_of_window(w) = month_of_height(w * CYCLE_BLOCKS)
```

which is `unreferred-pool-payout-v1`'s attribution rule: a window's whole uptime
counts toward the month its **first** height fell in.

**A chain cannot evaluate that rule when it needs it**, which is why version nine
carries the value in state. Window `w` opens at height `w * CYCLE_BLOCKS` and is
assigned at height `(w + ASSIGNMENT_LAG_WINDOWS) * CYCLE_BLOCKS`, two windows and
57,600 blocks later, and the timestamp of a height that far back is not in the
block doing the work. Version nine therefore writes the month at the opening
height and reads it at the assignment height. The alternative — reading the month
from the assigning block — is the systematic two-day distortion
`unreferred-pool-payout-v1` rejects by name.

### Window 0's month is genesis's, and genesis is its opening height

Height 0 does not exist: `ledger-transition-v1` starts a chain at height 1, and
three layers of the implementation refuse any other initial height. Window 0's
opening height is therefore genesis, and

```text
month_of_window(0) = month_index(genesis_timestamp)
```

is not a special case but the general rule reaching the one height that is a
genesis rather than a block. Genesis writes window 0's month entry exactly as
every later window-opening height writes its own.

**No seat is ever in scope for window 0**, because `first_cycle_window` is
`window_of_height(activation_height) + 1` and is therefore at least 1. Window 0
accrues nothing, has no candidates, and its assignment at height 57,600 is a
complete no-op for everything in this document.

### A chain cannot outlive the calendar

`calendar-v1` stops defining the calendar at the last millisecond of the year
9999, and C1 refuses a timestamp above it. A correct machine's stamp must also be
within `TIMESTAMP_TOLERANCE_MILLIS` of civil time, so once civil time passes
`MAX_TIMESTAMP_MILLIS` no acceptable stamp exists and **the chain stops producing
blocks**. This is a bound rather than a defect: it is 7,973 years away, every
derivation in this document is total inside it, and the alternative — a calendar
that runs out during execution — would have an undefined case to guess at.

### A genesis timestamp far from civil time

`calendar-v1` leaves this to the binding version, and version nine answers it in
two parts.

**Genesis validation applies C1 and reads no clock.** A genesis file whose
timestamp is outside the accepted range is malformed; one inside it is
well-formed regardless of what any machine's clock says. This is forced: the
chain identity is `H(label || genesis bytes)`, so a validity rule that read a
clock would make two machines disagree about a chain's own identifier.

**A genesis in the future halts the chain at its first block, and the refusal is
`TIMESTAMP_NOT_MONOTONIC`.** C2 requires `t(1) >= g` and C5 requires `t(1)` within
tolerance of civil time; while `g` exceeds civil time plus the tolerance, no value
satisfies both. `calendar-v1`'s ordered conditions reach monotonicity before
tolerance, so an honest proposer stamping its own clock is refused for being below
genesis, which is the true reason and the one an operator can act on: the chain
starts when civil time reaches its genesis.

**A genesis far in the past starts normally.** The first block's stamp is near
civil time and above `g`, both rules hold, and the only consequence is that the
chain's first month index is an old one. The cost that reading would otherwise
have imposed — a first settlement closing tens of thousands of months — is
removed by the single-pass rule below rather than by a bound on genesis.

## Canonical economy state

Version eight's key space with four entry kinds added and one value extended.
Every other kind, key width, and value width is unchanged.

| Kind | Entry | Key | Key bytes | Value | Value bytes |
| ---: | --- | --- | ---: | --- | ---: |
| 12 | unreferred pool | `u8(12)` | 1 | `accrued:u64 \|\| payable:u64 \|\| minted:u64` | **24** |
| 20 | window month | `u8(20) \|\| cycle_window:u64` | 9 | `month_index:u32` | 4 |
| 21 | monthly uptime figure | `u8(21) \|\| month_index:u32 \|\| seat_id:u32` | 9 | `uptime_seconds:u64` | 8 |
| 22 | monthly pool claim | `u8(22) \|\| seat_id:u32` | 5 | `accrued:u64 \|\| minted:u64` | 16 |
| 23 | settlement cursor | `u8(23)` | 1 | `accumulating_month:u32` | 4 |

Every integer is big-endian, as version one fixed and every version since has
kept. A `month_index` above `MAX_MONTH_INDEX` is refused by a decoder wherever it
appears, which makes every derivation reading one total.

### The unreferred pool gains `payable`

`unreferred-pool-payout-v1` names three quantities and version nine encodes them
in the order the units travel: a unit arrives and raises `accrued` and `payable`
together; it is assigned to a winner and leaves `payable` for a claim; the winner
mints it and it raises `minted`.

**`payable` is inserted rather than appended**, for the reason the header's
timestamp is: the value's width changes, so no decoder can read both layouts, and
moving `minted` means a version-eight decoder pointed at a version-nine value
produces an obvious mismatch rather than a plausible pair of numbers.

The entry is a singleton and is written at genesis with all three quantities
zero.

### The window month

One entry per window whose opening height has passed and whose assignment has
not. It is written at the window's opening height — at genesis for window 0 —
and deleted when that window is assigned, so an entry exists exactly for the open
window and the two inside the assignment lag.

`month_index` is the month the window's first height fell in. It is never
recomputed, because the height it was derived from is no longer reachable.

### The monthly uptime figure

One entry per seat per month **that accumulated uptime**, holding the sum of
`uptime_seconds(seat, w)` over the windows attributed to that month.

**Only nonzero figures are written.** A candidate with no entry has a figure of
zero by absence, which `unreferred-pool-payout-v1` states outright and which is
the difference between writing as many entries as ran and writing 100,000 every
window. A transition never writes a zero value here, and a decoder refuses one:
a zero figure is a second encoding of absence, which `protocol-primitives-v1`
forbids.

**The month is in the key even though only one month ever accumulates.** The key
could have been the seat alone, with the cursor saying which month the figures
belong to, and it would be four octets shorter. It is not, for the reason version
eight put the window in a seat window record's key while retaining only two
windows: a stale entry from another month is then visibly wrong rather than
silently counted, and the invariant that catches it can be stated over the state
instead of over the history that produced it.

Accumulation is a **checked** addition into a `u64`.
`unreferred-pool-payout-v1` gives the reason and it is worth keeping: a month
holds about thirty-one windows only at the commit target, and no consensus rule
bounds the block rate from above, so the comfortable bound is nominal. A bound
that depends on an operational rate is not a bound.

### The monthly pool claim

One entry per seat that has won a month and not yet minted everything it won. It
is the referral balance's shape — an `accrued` that only rises and a `minted`
that follows it — keyed by the seat rather than by the identity.

**It is a running balance and not a per-month award.** A seat that wins in two
months before minting holds one entry whose `accrued` is the sum, and one
transaction collects both. This is the founder-directed mint shape applied rather
than a storage choice: **a mint takes everything with no quantity choice**, which
the owner decided in M3.8a and which kinds 4, 5, and 18 all implement. A
per-month award would make collecting `n` months cost `n` transactions and `n`
fees, would need the mint to name a month or walk one, and would hold an entry
per win forever for a seat that never collects. The reasoning the owner gave in
M3.8a — that a mint which can take a chosen amount must record what it took — is
the same reasoning, and it reaches the same answer here.

**It is keyed by the seat because the winner is a seat.** The referral balance is
an identity's because a referral is a person's; a monthly pool win is a machine's
performance, and two seats of one owner can both win in a tie. Keying by seat
keeps that legible in state and costs nothing: the mint's authority is still the
seat's identity and the destination is still any escrow that identity owns, which
is kind 4's rule unchanged.

The entry is created the first time a seat wins **something**, and is **not**
deleted when it is emptied, exactly as a referral balance is not: the pair is the
audit trail of what a machine earned and what it took. A win whose share rounds
to zero creates no entry, because a zero `accrued` is absence rather than a
record of a win.

### The settlement cursor

A singleton holding `accumulating_month`, the month index whose figures are
currently accumulating. Genesis writes `month_index(genesis_timestamp)`. Each
assignment sets it to the assigned window's month.

**It is a separate entry rather than a fourth field on the pool**, because it
would still be needed on a chain whose pool was permanently empty: it describes
where the window grid has reached on the calendar, not what the pool holds. Five
octets is the whole cost of keeping the two subjects apart.

## Transaction kind 22: mint monthly pool

| Field | Bytes | Offset |
| --- | ---: | ---: |
| `seat_id` | 4 | 80 |
| `destination_escrow_id` | 32 | 84 |
| `hub_signature` | 64 | 116 |

Body 100 octets; unsigned 196; signed 260. Scheme 1 — a signer resolves the
acting escrow — and any other scheme is `MALFORMED_TRANSACTION` at admission step
1. **The shape is kind 4's exactly**, and so is every authority rule it carries.

The HUB signature is version six's `mint_message`, which already binds
`u8(transaction_kind)`:

```text
mint_message =
  D("protocol-stack:v6:mint-confirm") ||
  chain_id || hub_identity_hash || u8(22) || u32(seat_id) ||
  destination_escrow_id || u64(valid_until_height)
```

**No new domain-separated label is needed and none is added.** Version six's
message binds the kind precisely so that a confirmation obtained for one mint
cannot be replayed onto another, and the kind byte separates kind 22 from kinds
4, 5, and 18 with no further construction. The vectors are required to show that
the four differ on identical remaining fields.

Rejection conditions, in this order, after the shared envelope checks:

1. a `seat_id` above `MAX_SEAT_ID` is `CYCLE_RANGE`;
2. an unpurchased `seat_id` is `SEAT_NOT_PURCHASED`;
3. an unactivated seat is `SEAT_NOT_ACTIVATED`;
4. a seat whose identity is not the acting escrow's owner is `UNAUTHORIZED`;
5. a destination escrow that does not exist is `ESCROW_NOT_FOUND`;
6. a destination escrow owned by another identity is `ESCROW_NOT_OWNED`;
7. no claim entry for the seat, or one whose `accrued` equals its `minted`, is
   `NOTHING_TO_MINT`;
8. the confirmation conditions of kind 4's step 8 — a total the destination's
   posture requires a confirmation for, presented with 64 zero octets, is
   `BIOMETRIC_REQUIRED`, and a confirmation that does not verify over the mint
   message is `UNAUTHORIZED`;
9. an amount that does not fit the referral channel is `CHANNEL_CAP`.

On success the transition credits `accrued - minted` to the destination escrow's
balance, sets the claim's `minted` equal to its `accrued`, adds the same amount to
the pool entry's `minted`, moves that amount from the referral channel's
`outstanding` to its `issued`, increases `total_supply`, and charges the fixed
fee to the acting escrow. It is atomic.

**Condition 3 is reachable and is kept even though condition 7 would catch it.**
A seat cannot hold a claim without having been in scope, and cannot have been in
scope without activation, so an unactivated seat always has an empty claim. The
condition is kept because it names the real reason: a refusal that says
`NOTHING_TO_MINT` about a seat nobody ever switched on is true and useless.

**Condition 9 is structurally unreachable and is checked rather than assumed.**
The units were counted into the referral channel's `outstanding` when they
accrued, and the mint moves them to `issued` without creating any, so the channel
identity forbids the overflow the condition tests for. It is declared because
kind 5 declares it, and because an invariant that cannot fail is cheaper to check
than to argue about.

**The mint charges the fixed fee, like every other mint**, and version nine adds
no exemption. Version eight's exemption for kind 20 was a founder answer about a
cost a machine bears every hour to prove uptime it is paid for; collecting an
award is the ordinary shape, and every accepted mint charges. The consequence is
worth recording: **a winner with an empty escrow cannot collect until it holds
one fixed fee.** That is already true of kinds 4, 5, and 18, and ADR 0042's entry
airdrop is what funds a person's first action, so version nine inherits the
situation rather than creating it.

**A seat past its own 731 cycles may hold a claim and must be able to mint it.**
In-scope is permanent under ADR 0049's rule 3, so a seat whose distribution has
finished still competes for the monthly pool and still wins. Kind 22 is not gated
on span, and version seven already states the same requirement about kind 4 for
the same reason.

## Block execution

Version eight's block transition, with the timestamp rules around it and two
steps inserted into the prologue. The order is normative:

```text
0. timestamp   C1 and C2 against the agreed header field
1. prologue    assign the due window, settle the closing month, accrue,
               accumulate the month's figures, discard the window's evidence,
               and record the opening window's month
2. issue       write an open challenge for every selected in-scope seat
3. transactions
4. expiry      resolve the challenges issued RESPONSE_DEADLINE_BLOCKS ago
5. conservation, roots, header
```

Everything version eight states about the block transition is unchanged: the only
valid next height is `h + 1`, admission failures are omitted from execution and
from the transaction root, every admitted transaction appends a receipt whether
it succeeds or fails, ordinary transaction results never reject a block, and an
internal invariant failure, height error, timestamp error, or resource-bound
violation rejects the whole proposed block and restores the pre-block state
exactly.

### 0. The timestamp rules run before anything reads the field

C1 and C2 are evaluated against `t(h)` and the state's `timestamp`, in
`calendar-v1`'s order, before any step derives a month from the field. This is
what keeps every derivation total: a value outside the accepted range has no
month, and no step should ever be handed one.

### 1. The prologue

At every height `h` with `h mod CYCLE_BLOCKS == 0`:

**1a.** When `window_of_height(h) >= ASSIGNMENT_LAG_WINDOWS`, let
`due = window_of_height(h) - ASSIGNMENT_LAG_WINDOWS`, and:

1. derive the due window's seat sequence from state, exactly as version eight
   does: `in_scope`, `in_span`, the window record or its absent full-credit
   reading, `credited_slots`, and `uptime_seconds`;
2. run version seven's settlement steps 1 through 7 unchanged — the assignment
   record, the winner set, the base permissions, the recovery pool's absorption
   and its residual;
3. **settle the closing month**, defined below;
4. run version seven's settlement step 8 unchanged — the referral accrual, to a
   recorded referrer under the cap where there is one and **to the unreferred
   pool otherwise**, with the pool's `payable` now raised by exactly what its
   `accrued` is raised by;
5. **accumulate the figures**: for every seat in the sequence of step 1 with
   `uptime_seconds(seat, due) > 0`, add that figure to its kind-21 entry for
   month `month_of_window(due)`, creating the entry if absent, in ascending seat
   order;
6. delete every kind-19 entry for `due` and the kind-20 entry for `due`.

**1b.** At every window-opening height, including those below the assignment lag,
write the kind-20 entry for `window_of_height(h)` with the value
`month_index(t(h))`. An entry that already exists for that window is an invariant
failure and rejects the block, because a window opens once.

**The figures are accumulated from the same sequence the settlement derived**, in
the same prologue, so version nine adds no second walk over the seat table at a
window boundary. Step 5 reads what step 1 already produced.

**Step 6 must follow step 5**, because the figures are computed from the kind-19
records step 6 deletes. Version eight deletes them immediately after the
assignment; version nine moves the deletion to the end of the prologue and
changes nothing else about it.

### The month that closes, and the single pass that closes it

Let `m = month_of_window(due)`, read from `due`'s kind-20 entry, and let `a` be
the settlement cursor.

**`m < a` is an invariant failure and rejects the block.** `month_of_window` is
non-decreasing in the window index, because `month_index` is non-decreasing in
the timestamp, C2 makes the timestamp non-decreasing in the height, and window
opening heights increase. A chain that reached this state has a corrupted cursor
or a corrupted month entry, and there is no correct way to continue from it.

**When `m == a`, nothing closes.** The assigned window belongs to the month
already accumulating, its figures join that month's, and `payable` is untouched.
This is every assignment but roughly one a month.

**When `m > a`, exactly one month closes and it is `a`.** The months in
`(a, m)` are **empty** — no window is attributed to any of them — because window
attribution is non-decreasing and consecutive assigned windows `due - 1` and
`due` carry months `a` and `m` with nothing between them. An empty month has no
windows, therefore no accrual and no candidates, so
`unreferred-pool-payout-v1`'s pass over it is a no-op that leaves `payable`
exactly as it found it. Version nine therefore **pays month `a` and advances the
cursor to `m` in one pass**, rather than iterating `m - a` indices.

**That is a derivation and it is also a bound.** `m - a` is not bounded by
anything a chain controls: a chain halted for a year resumes with twelve empty
months between, and a chain whose genesis timestamp is decades in the past would
close hundreds at its first assignment. Iterating them would make one block's
work proportional to how long the network was down. Paying `a` and jumping is
exact and costs the same on every assignment.

**The ascending-order rule is preserved and is not decorative.**
`unreferred-pool-payout-v1` makes the order normative so that a carry from an
earlier month reaches a later one. Under version nine only one index can carry,
so the order is satisfied trivially — but the theorem it rests on is that **an
empty month accrues nothing**, and that is structural rather than incidental:
accrual happens only at an assignment, and an assignment attributes to
`month_of_window(due)`, which is by definition not empty. A later change that
gave a month an accrual with no window would have to restore the loop.

**The equivalence is required as evidence rather than asserted.** No invariant
over a single accepted state can catch it, because the single pass and the loop
agree on every state they both produce; what distinguishes them is a scenario.
The vectors below therefore require a multi-month halt settled both ways — once
by this rule and once by an explicit per-index loop over the same scenario — and
require the two to agree state for state.

### The payout

To close month `a`:

```text
last_window(a) = due - 1
candidates(a)  = { seat : is_activated and first_cycle_window(seat) <= due - 1 }
figure(seat)   = the kind-21 entry for (a, seat), or 0 if absent
best           = max over candidates(a) of figure(seat)
winners        = { seat in candidates(a) : figure(seat) == best }
payable        = the pool entry's payable, read before step 8 raises it
share          = payable / |winners|                      (truncating)
remainder      = payable - |winners| * share
```

1. if `candidates(a)` is empty, nothing is paid, `payable` is untouched, and the
   month carries to the earliest subsequent month that has a candidate, which is
   ADR 0075's rule;
2. otherwise, **when `share` is nonzero**, add `share` to each winner's kind-22
   claim's `accrued` in ascending seat order, creating the entry if absent; and
   set the pool's `payable` to `remainder` whether `share` was zero or not;
3. delete every kind-21 entry whose month is `a`.

**The candidate set is derived from the seat table and not from the figures**,
which is `unreferred-pool-payout-v1`'s observation that in-scope is monotone in
the window: a seat is a candidate for month `a` exactly when its first cycle
window is at or below the last window attributed to `a`, and `due - 1` is that
window because the cursor was set to `a` at `due - 1`'s assignment. Deriving the
set from the kind-21 entries instead would silently exclude every seat that ran
nothing, which is the whole reason zero-figure candidates exist.

**`best` may be zero, and then every candidate wins.** ADR 0075 declined a duty
gate and ADR 0076 declined an accumulation-cap filter, so a month in which no
in-scope seat was credited for a single slot splits `payable` across every
in-scope seat. It is reachable — the referral leg accrues for contributing seats
regardless of their uptime — and it is the largest single block this transition
can produce. It is not an error and it is not to be filtered.

**`share` may be zero**, when `payable` is below the winner count. Nothing is
assigned, `remainder` equals `payable`, and the whole balance carries.

**A zero share therefore writes no claim entry, and that is a rule rather than an
optimisation.** A claim is a balance, and a balance of zero is absence — the same
rule the monthly figure follows and the same rule `protocol-primitives-v1`
imposes everywhere, that a value has one encoding. Adding zero to an absent entry
would create one, and in the zero-best month that is up to 100,000 entries
recording that nobody was paid anything. The winners are still the winners; there
is simply nothing for them to collect, and the next month that pays will divide a
balance that includes what this one could not.

**The deletion in part 3 is the largest state change this rule makes** — up to
100,000 entries in one block at capacity, though only for seats that actually
ran. An implementation may spread it only if doing so changes no accepted state,
which it does not, because no later step reads a month the cursor has passed.

### The zero-candidate case is unreachable once any seat is activated

`unreferred-pool-payout-v1` proves it and version nine restates the conclusion
because its own invariants depend on it: an accrual in month `a` implies some
seat was in span in a window attributed to `a`, in-span implies in-scope by
construction, and in-scope has no upper bound, so `candidates(a)` is non-empty
whenever there is anything to pay. Part 1 is therefore a safety net reachable
only before the first activation, when the pool is empty, and **not an
operational path.** It is checked on every settlement rather than asserted once,
so a later change that made in-scope expire fails a test instead of quietly
turning a safety net into a policy.

### Why the payout precedes step 8 and follows step 7

**It precedes the accrual**, which `unreferred-pool-payout-v1` makes normative
and which is forced rather than chosen: the window being assigned belongs to
month `m`, so its referral accrual belongs to `m`, and letting it land first
would pay the closing month one window of its successor's accrual — "only one
month's accrual is distributed per month" would be false by a day every month.
Placing it between steps 7 and 8 makes that adjacency visible in the step list
rather than stated at a distance.

**It follows the recovery pool's absorption**, which touches only the Founder
Node distribution channels and never the referral channel, so the two settlements
are independent. Version nine states the position anyway, for the reason version
seven states that its step 6 reads the pool before step 7 writes it: two
implementations can each read a sentence about a pool a different way, and an
ordering is invisible in every test that does not put both in one block.

## Result codes

**Version nine adds no result code and the space stays at 45.** Every refusal
kind 22 can produce is one an accepted version already assigned: `CYCLE_RANGE`
(10), `SEAT_NOT_ACTIVATED` (13), `SEAT_NOT_PURCHASED` (14), `NOTHING_TO_MINT`
(15), `CHANNEL_CAP` (20), `BIOMETRIC_REQUIRED` (22), `ESCROW_NOT_FOUND` (28),
`ESCROW_NOT_OWNED` (29), and `UNAUTHORIZED` (9). Codes 0 through 44 keep their
exact version-eight meanings, 0 through 32 their version-seven meanings, and 0
through 8 their version-one meanings.

That is a property of reusing kind 4's ladder rather than an accident, and it is
stated because the opposite would be worth noticing: a new mint that needed a new
refusal would be a mint whose authority rules differ from every other mint's.

**The timestamp conditions produce no result code**, for the reason given in
[Where each rule is applied](#where-each-of-calendar-v1s-five-rules-is-applied).
`calendar-v1` names `TIMESTAMP_RANGE`, `TIMESTAMP_NOT_MONOTONIC`,
`TIMESTAMP_AHEAD_OF_TOLERANCE`, and `TIMESTAMP_BEHIND_TOLERANCE`; all four are
block-level and belong to the application contract's status space, not to this
document's transaction result space.

## Receipts

Version eight's receipt layout with the version field at `9`. A kind-22 receipt
records the fixed fee and the amount minted, so the issuing kinds become 4, 5, 6,
10, 18, and **22**.

## Resource bounds

| Entry | Octets each | Bound at capacity | When |
| --- | ---: | ---: | --- |
| window month (20) | 13 | 2 | always, once the first window has opened |
| monthly figure (21) | 17 | 100,000 | one month, seats that ran |
| pool claim (22) | 21 | 100,000 | seats that have ever won |
| settlement cursor (23) | 5 | 1 | always |
| pool (12) | +8 | 1 | always |

**Two window month entries are live and not the three
`unreferred-pool-payout-v1` sized for**, and the difference is where the deletion
falls rather than a disagreement. That document counts the open window and the two
inside the assignment lag; version nine deletes the oldest of the three in the
same prologue that assigns it, so at every point inside a block the entries are
the open window's and its predecessor's. Invariant 2 states it over the state, and
the smaller figure is the encoded one.

**The standing cost is about 3.8 MB at the 100,000-seat capacity**, and it is
paid only by a chain in which every seat both ran and has won. A realistic chain
holds one figure per seat that ran in the current month and one claim per seat
that has ever won a month, which is at most twelve seats a year.

**The peak block is the settlement**, and it has two parts. It deletes up to
100,000 figure entries, and in the zero-best month it writes up to 100,000 claim
entries — about 3.8 MB of state change at one height, once a month. Every other
height in the month pays nothing at all for this document: there is no per-block
monthly work, no per-block calendar state, and `CALENDAR_STATE_BYTES` is 0 as
`calendar-v1` states.

**The candidate walk is one pass over the seat table per month**, to find the
maximum, and one more to collect the winners. At capacity that is 200,000 seat
reads once a month, which is three orders of magnitude below the per-block costs
version eight already pays and which ADR 0055 already records as an
implementation cost rather than a contract defect.

**Exactly one month accumulates figures at a time.** Window assignment is
ordered and `month_of_window` is monotone in the window index, so every window of
a month is assigned before any window of the next, and a month's figures are
complete and deleted before its successor accumulates anything. The lag moves
*when* a settlement happens; it does not interleave two months' figures.
`unreferred-pool-payout-v1` measured this rather than asserting it, and invariant
7 below is what keeps it true.

## Invariants

Version eight's invariants unchanged, with seven added. Each is checked rather
than assumed.

1. The state's `timestamp` is inside `calendar-v1`'s accepted range and is at or
   above its value at the previous height, or equals `genesis_timestamp` at
   genesis.
2. A kind-20 entry exists for exactly `window_of_height(h)` and, once
   `window_of_height(h) >= 1`, for `window_of_height(h) - 1`, and for no other
   window, at the end of every block.
3. Every recorded `month_index`, in a kind-20 key's value, a kind-21 key, and the
   cursor, is at most `MAX_MONTH_INDEX`.
4. The cursor is non-decreasing across heights, and equals the month of the most
   recently assigned window once any window has been assigned.
5. Every kind-21 value is nonzero.
6. Every kind-21 entry's `month_index` equals the cursor.
7. `month_of_window(due) >= accumulating_month` at every assignment.
8. For every kind-22 claim, `accrued` is nonzero and `minted <= accrued`. A
   claim of zero is absence and a transition never writes one.

**The pool conservation identity**, required at every accepted state:

```text
pool.accrued = pool.payable + sum over seats of claim.accrued
pool.minted  = sum over seats of claim.minted
```

The first is `unreferred-pool-payout-v1`'s identity encoded: every unit the pool
has received is either still undistributed or is owed to a named winner, and none
is anywhere else. The second is the identity that specification names for
completeness and leaves to the version that implements a mint; version nine
implements it and states it as an equality rather than the bound
`minted <= accrued - payable`, because an equality catches a unit minted twice
and the bound does not.

**The referral channel identity is unchanged and is refined rather than
replaced.** Version six's

```text
outstanding(founder_referral)
  = sum over identities of (accrued - minted) + (pool.accrued - pool.minted)
```

still holds exactly, because the two identities above give

```text
pool.accrued - pool.minted
  = pool.payable + sum over seats of (claim.accrued - claim.minted)
```

so version nine splits the pool's outstanding term into a balance and a set of
claims without changing its total. **That is the substance of the whole
settlement**: value already counted against the referral channel's cap moves from
undistributed to owed to collected, and no step in this document creates or
destroys a unit. The manifest layer's invariants and both of version seven's
identities are untouched.

## Version-nine genesis

Version eight's field table with the schema version at `9` and one field added.
**The order below is the encoding's.**

| Field | Bytes | Offset |
| --- | ---: | ---: |
| magic `PSGN` | 4 | 0 |
| `schema_version` = 9 | 2 | 4 |
| `network_id` | 4 | 6 |
| `genesis_timestamp` | 8 | 10 |
| `supply_limit` | 8 | 18 |
| `total_supply` | 8 | 26 |
| `fixed_transfer_fee` | 8 | 34 |
| `initial_fee_pool` | 8 | 42 |
| `manifest_digest` | 32 | 50 |
| `verifier_key` | 32 | 82 |
| `dispute_authority_key` | 32 | 114 |
| `account_count` | 4 | 146 |

The prefix is **150 octets** rather than 142. The account bound that follows from
the 1,048,576-octet object limit stays 21,842, because 48-octet account entries
absorb the eight additional prefix octets without crossing an entry boundary. It
remains unreachable, because zero genesis accounts is still required rather than
expected.

**`genesis_timestamp` sits with `network_id` rather than among the monetary
fields**, because it is part of what identifies this chain rather than part of
what it is worth, and `account_count` stays last, which it must: the account
entries follow it.

```text
chain_id = H(D("protocol-stack:v9:chain-id") || canonical_genesis_v9_bytes)
```

**A genesis timestamp outside `calendar-v1`'s accepted range is malformed**, and
no other rule applies to it; see
[A genesis timestamp far from civil time](#a-genesis-timestamp-far-from-civil-time).

**Genesis writes sixteen economy entries** rather than version eight's fourteen:
the fourteen unchanged, plus the settlement cursor at
`month_index(genesis_timestamp)` and window 0's month entry at the same value.
The unreferred pool entry is written with `accrued`, `payable`, and `minted` all
zero. It writes no figure, no claim, no open challenge, and no seat window
record.

## Version identity

| Construction | Version nine |
| --- | --- |
| chain ID | `protocol-stack:v9:chain-id` |
| state root | `protocol-stack:v9:state-root`, version field `9` |
| economy tree | `protocol-stack:v9:economy-empty`, `-leaf`, `-node` |
| block ID | `protocol-stack:v9:block-id` |
| block header schema version | `9` |
| genesis schema version | `9` |
| receipt version | `9` |

**The block identifier and the header schema version are re-versioned for the
first time since version one**, because version nine is the first version to
change the header's bytes. Every earlier version inherited both, and version
eight says so outright.

**Every other label keeps the version that accepted it.** The account derivation
stays `protocol-stack:v1:account`, the escrow derivation stays
`protocol-stack:v6:escrow`, the two transaction signing labels stay at
`protocol-stack:v1:`, the six HUB messages keep their `protocol-stack:v6:`
labels including the mint message kind 22 uses, the ordered transaction tree
stays version one's, and version eight's challenge and dispute labels are
unchanged. A label names the artifact it derives, and none of those artifacts
changed.

## Compatibility boundary

**Transaction bytes.** A version-one signed transfer is a version-nine kind-1
transaction, byte-for-byte, with the same signing message and transaction ID. A
version-eight transaction of any kind is a version-nine transaction of that kind
by shape and belongs to a different chain by binding. A version-eight node
presented with a kind-22 transaction rejects it at admission step 1 as
`MALFORMED_TRANSACTION`.

**Block headers.** A version-eight header is 146 octets with schema version 1 and
a version-nine header is 154 with schema version 9, so neither decodes as the
other, and the schema version differs independently of the length. **This is the
first header change in the project's history**, so every component that reads a
header — the application, the store, the snapshot, the transport, and the ABCI
adapter — parses a different shape under version nine.

**State.** A version-eight state is not a version-nine state and the converse
holds too: a version-nine state carries entries under kinds 20 through 23 that
version eight's decoder refuses, and a kind-12 value of 24 octets that it refuses
by width. There is no upgrade block, no migration, and no state translation,
exactly as between every earlier pair.

**Genesis.** A version-eight genesis file is 142 octets and a version-nine file is
150, so neither decodes as the other.

**Roots and identity.** The version-nine state root, chain ID, economy tree, and
block ID have distinct labels and version fields from all eight predecessors, so
no earlier root is reinterpreted and no version-nine root collides with one. Each
non-collision is required separately, because distinct labels are strings rather
than a chain.

**What is not claimed.** No accepted M1 or version-two through version-eight
vector, digest, receipt, root, or recorded devnet result changes, and none is
recomputed under this specification.

### What the application contract must gain

`consensus-application-v1` states that timestamps "are not application transition
inputs" and freezes its local protocol at frame version 1. **Both become false of
version nine**, and closing that is a separate accepted contract rather than
something this document may assume.

A conforming application contract for version nine must:

- carry the proposed timestamp in the requests that validate and execute a
  height — `ProcessProposal` and `FinalizeBlock` — and the genesis timestamp in
  `InitChain`;
- apply C1, C2, and **C5** in `ProcessProposal`, which is where a machine first
  validates a height and the only place a clock may be read;
- apply C1 and C2 and **never C5** in `FinalizeBlock`, which is the path a
  replaying or restoring machine takes;
- report a timestamp failure as a block-level status rather than as a
  transaction result, distinguishing at least the four conditions
  `calendar-v1` names so each can be tested on its own; and
- leave the proposer's algorithm for choosing a value unconstrained beyond the
  accepted value, so that a machine reading its own clock and CometBFT's BFT
  time both satisfy it.

`calendar-v1`'s argument that BFT time satisfies C5 under the standard
assumption behind the rest of the consensus layer is what makes the last point
safe, and it is that specification's rather than this one's.

## Versioning and compatibility of this document

Everything version eight fixes as immutable is immutable here too, with the state
key space, the result code space, the kind space, the genesis field table, and
now the block header taking their version-nine forms. The header field and its
offset, the genesis field and its offset, the four entry kinds with their keys
and values, the extended pool value, kind 22's body and ordered rejection
conditions, the prologue's six ordered steps and its window-month write, the
single-pass closing rule, the payout arithmetic, and the two pool identities are
normative. A changed field, code, order, or semantic rule requires a new
transition version and an ADR; it must not reinterpret a version-nine
identifier.

Versions one through nine coexist as documents; every earlier artifact remains in
place, passing, and unedited.

## What this specification does not establish

Everything version eight does not establish is inherited unchanged, including the
vacuous duty layer, the liveness-not-possession limit on an answered challenge,
the interim single dispute authority, and the probabilistic nature of sampling.
**Four limits are new and belong to this version.**

**The chain's clock is only as good as its proposers' clocks.** C5 bounds an
accepted stamp against a correct machine's own reading, and `calendar-v1` shows
the error does not accumulate, but nothing here proves that a set of proposers
has correct clocks. A network whose machines are uniformly wrong by more than the
tolerance cannot make progress at all, which is the safe failure, and one wrong
by less simply runs a chain whose months begin within a minute of civil time.

**A proposer can move a month boundary by up to 20 blocks**, which is
`calendar-v1`'s bound, and version nine is the first artifact for which that bound
has a price. **The price is quantifiable and it is small.** A window's month is
fixed by the timestamp of its opening height, so moving the boundary changes an
attribution only when the boundary and a window's opening height are within 20
blocks of each other — about one window in 1,440 at the commit target. When it
does happen, one window's uptime moves between two months **for every candidate
at once**, because every seat shares the same window grid, so it shifts each
candidate by its own uptime in one shared window rather than favouring anyone.
That is the same argument `unreferred-pool-payout-v1` makes about the straddling
window it declined to split, and the remedy it declined — splitting a window at
the month's first height — is the remedy version nine declines here, for the same
reason: the split point is a timestamp and slots are height ranges.

**The beacon's grinding surface widens on quiet blocks**, as stated above, and is
referred to the independent review requirement 15 already owes.

**A month's ranking is only as honest as the measurement beneath it.** Version
eight measures liveness of a responder rather than possession of a resource, so
the figure this document ranks on is a count of answered audits. Every claim about
what the monthly pool rewards is bounded by that, and a later version binding a
real challenge predicate tightens this document's meaning without changing a rule
in it.

## The founder-decision gate this document ran

**Twenty-two decisions were enumerated before any was judged, and every one is
delegated.** Three were already decided by founder answers this document
implements rather than revisits — the candidate set and the carry by
[ADR 0075](../decisions/0075-founder-answers-on-the-monthly-pool-candidate-set-and-carry.md),
and the accumulation cap's exclusion from the ranking by
[ADR 0076](../decisions/0076-the-monthly-pool-ranks-every-in-scope-seat.md).
Six are fixed by accepted specifications: the unit, range, tolerance, and the
five rules by `calendar-v1`; the attribution rule, the tie split, the remainder,
and the settlement point by `unreferred-pool-payout-v1`. The remaining thirteen
are encoding, storage, ordering, packaging, and naming, which the Founder
Constitution places outside the reserved set.

**One was close enough to reserved to be worth naming.** Whether a winner's award
is a per-seat running balance or a per-month award decides how many transactions
and fees a participant needs in order to collect, which is a question about what
an end user must do to be paid. It is **delegated because the owner already
answered it**: "a mint takes everything with no quantity choice" is the
founder-directed rule M3.8a established and kinds 4, 5, and 18 implement, and
applying an existing founder answer to a new subject is deduction rather than
invention. Had no such answer existed, this document would have stopped and asked.

Nothing in this specification set or changed supply, allocation, beneficiaries,
Founder ownership, creator hierarchy, commercial routing, AI institutional
authority, bridge scope, content permanence, or what an end user must do, own,
run, or receive beyond applying rules already decided.

## Required vectors and evidence

`test-vectors/economy-transition-v9.txt` will be normative.
`simulation/economy_transition_v9/` must execute this document's codec, its
timestamp rules, its calendar derivation over chain state, its monthly
settlement, and kind 22, and `tools/economy-transition-v9-vectors/` must derive
every recorded value twice — once from an `expected.py` that imports nothing from
`simulation/`, and once from a live model run. It must fix:

- **the version identity** — the four re-versioned constructions, the eight root
  non-collisions, the 150-octet genesis prefix, and the 154-octet header, each
  predecessor construction first required to reproduce its own accepted empty
  root so the comparison is against the real one;
- **the header and genesis** — both widths, both schema versions, the inserted
  offsets, and a version-eight header and genesis file refused by width and by
  schema version independently;
- **the timestamp rules** — C1 and C2 accepted and refused at each boundary, two
  consecutive equal timestamps accepted, C5 refused on each side separately, and
  **a clockless replay of an accepted chain agreeing height for height**, which is
  the evidence that C5 is not on the replay path;
- **the state surface** — each new kind's key and value width, a zero figure
  refused, a `month_index` above `MAX_MONTH_INDEX` refused, a 16-octet kind-12
  value refused, a version-eight decoder refusing each, and the live window-month
  entry count **measured over a recorded run** rather than asserted, as
  `unreferred-pool-payout-v1` measured the accumulating-month count;
- **the calendar over a chain** — a window's month read from its opening height
  and not its assignment height, with the figures a last-height attribution would
  have produced recorded beside the real ones so the two rules are
  distinguishable; a window straddling a month boundary; and window 0's month
  taken from genesis;
- **the settlement** — a single winner, an exact tie of two and of three with the
  share and remainder at each, a remainder arriving in the next month's payout, a
  month with candidates and no accrual, a zero-best month in which every
  candidate wins, a `share` of zero carrying the whole balance **and writing no
  claim entry**, a seat joining mid-month and a seat whose span ended mid-month
  both competing, and a seat at the accumulation cap winning;
- **the single pass** — a halt spanning three months settled in one assignment
  with the carry reaching the correct month, checked against an explicit
  per-index loop over the same scenario so the two are proved equal rather than
  asserted equal; and a chain whose genesis is decades in the past settling in
  constant work;
- **the orderings** — the payout and the accrual in the same block in both
  orders, the figure accumulation before and after the kind-19 deletion, and the
  cursor advanced before and after the accumulation, each pair producing
  different accepted state so the stated order is normative rather than
  decorative;
- **kind 22** — every one of its nine rejection conditions produced by executing
  a minimally mutated input against a positive control, the mint message's four
  constructions differing only in the kind byte, a seat past its 731 cycles
  minting a claim, and a second mint immediately after a first refused as
  `NOTHING_TO_MINT`;
- **the identities** — both pool identities checked after every step of every
  scenario, and version six's referral channel identity re-derived from them and
  shown unchanged; and
- **the carryover claim** — checked over the packages rather than over the vector
  files, as versions seven and eight established: a test must classify every
  constant version eight exports as carried or revised, require the
  classification to be total, and fail if the revised set is not exactly what
  this document lists.

A second file, `test-vectors/economy-transition-v9-execution.txt`, must record
what a chain conforming to this document does, on versions seven and eight's
pattern, over at least: a month measured entirely on-chain and paid to its best
performer; a network halted across a month boundary; a month whose last two
windows are assigned after the next month has begun, paying on the complete
figure, with the figure a month-opening-block trigger would have ranked on
recorded beside it; and every version-eight kind still executing unchanged
against a version-nine ledger.

`docs/engineering/verification.md`'s rules apply: a boolean vector may only be
true, a name asserts no more than its value establishes, and a claim is checked
against something other than itself.

Acceptance of the recorded artifacts requires full GitHub-hosted verification on
the exact commit that adds them.

**What the recorded files now hold.** `test-vectors/economy-transition-v9.txt`
holds 239 vectors and `test-vectors/economy-transition-v9-execution.txt` holds
125. The C++20 codec reproduces every vector in the first that does not need a
ledger, a chain, or the Python package's own surface, and names each one it does
not reach together with what owes it.
