# Economy transition v7

Status: Accepted M3 consensus transition contract; model and vectors recorded,
transaction ledger and C++ implementation not yet updated

This document defines the version-seven Founder Economy consensus transition. It
is [`economy-transition-v6`](economy-transition-v6.md) with **the per-channel
carry deleted from state and replaced by a recovery pool**, so that the node
distribution assigns 100% of the permissions the manifest promises rather than
leaking two silent remainders into a term nothing ever releases.

The change is classified as encoding, state-transition shape, economics, and
compatibility.
[ADR 0049](../decisions/0049-the-recovery-pool-and-permanent-best-performer-ranking.md)
directs the behaviour and
[ADR 0054](../decisions/0054-economy-transition-v7-the-recovery-pool.md) records
the contract decisions it left open.

It satisfies requirement 9 of [`first-goal.md`](../project/first-goal.md) as
revised on 2026-08-19, and re-satisfies requirements 5 and 6 under a seventh
chain identity.

## Relationship to version six

[`economy-transition-v6.md`](economy-transition-v6.md) is not edited, retracted,
or reinterpreted, and `test-vectors/economy-transition-v6.txt` and
`test-vectors/economy-transition-v6-execution.txt` remain normative and passing.
Version six's own versioning section fixes its entry kinds, its state values, and
its settlement as immutable, so deleting an entry kind and changing what a cycle
does with an indivisible remainder is a new version rather than a repair.

**Everything else in version six carries over unchanged and is incorporated by
reference**: the account architecture of identities, keyless escrows, and
revocable signers; the escrow and signer derivations; the canonical envelope, its
two authorization schemes, and all fourteen transaction kinds with their bodies
and their ordered rejection conditions; the six HUB messages and their labels;
the per-escrow security posture and both posture predicates; the entry airdrop,
the daily verified-user permission, and its thirty-window cap; the accumulation
cap and its window measurement; the bounded mint walk's range and its mark
advance; the referral accrual and the unreferred pool; every other economy state
key and value encoding; the beneficiary space; the RFC 9162 tree shape; the
genesis field table and its 21,843-entry bound; the receipt layout; the
thirty-three result codes and their meanings; and every founder-directed figure
in the accepted manifest.

**Four things change, and this document defines exactly those four.** The state
loses entry kind 7 and gains entry kind 17. The cycle assignment record gains
five fields. The settlement's steps 5 through 7 are respecified. And the
per-channel conservation identity loses its third term and gains a companion.

## What version seven changes

| | v6 | v7 |
| --- | --- | --- |
| An unclaimable remainder | ten `carry` entries, added to and never released | one `recovery_pool` entry, taken whole by the next winning cycle |
| A zero-winner cycle | the whole base permission enters the carry | the whole base permission enters the pool |
| An indivisible remainder | enters the carry | enters the pool |
| Where the remainder sits | moved **out of** `outstanding` | left **inside** `outstanding` and named by the pool |
| The per-channel identity | `issued + outstanding + carry = assigned * leg` | `issued + outstanding = assigned * leg` |
| What backs `outstanding` | not stated for a node channel | `claimable + recovery_pool`, an equality |
| The cycle assignment record | 24 fixed octets | 64 fixed octets |
| A winner's collection | `reallocated_count * share` | `reallocated_count * share` plus the cycle's pool share |
| Genesis economy entries | 23 | 14 |
| Manifest binding | `founder-economy-manifest-v2` | `founder-economy-manifest-v3` |

## Scope

Version seven defines the recovery pool's state entry, the extended cycle
assignment record, the respecified settlement, the two conservation identities,
the version-seven chain identity and state root, version-seven genesis, and the
exact compatibility boundary against versions one through six.

It does not define the version-seven transaction ledger and its block execution,
which mirror how version six separated its contract from its execution; the C++20
kernel implementation, which is requirement 10; the four-node adversarial
scenarios, which are requirement 13; direct-channel eligibility, which remains
reserved; or anything else version six leaves unestablished, all of which is
inherited unchanged.

## Bindings

This specification holds no second copy of any founder-directed value.

**The manifest layer** is the accepted `founder-economy-manifest-v3` contract,
whose digest is bound into version-seven genesis. Its only difference from
version two is channel 9's identifier, so no cap, leg, subtotal, bound, or total
moves.

**The window grid**, **the measurement**, **the activity verdict**, **the winner
rule**, and **the tie rule** are unchanged and are read from the same contracts
version six reads them from.

**The accumulation cap, the cycle-assignment record's meaning, the bounded mint
walk's range, and the referral accrual** are `economy-transition-v3`, imported
rather than restated, with the record's encoding extended and the winner's
collection extended by this document and nothing else changed.

## The two seat sets

Version seven names two sets that version six's settlement already
distinguishes, because ADR 0049 makes the distinction load-bearing and a name is
what stops it being collapsed by a later reader.

**The contributing set** is the in-scope seats that are **in span** — inside
their own 731 issuance cycles. Every seat in it generates one base permission for
the cycle, whether it accrues that permission or reallocates it.

**The eligible set** is **every** in-scope seat that met the cycle's duty
threshold and is under the accumulation cap, in span or not. It is the candidate
set for the winner derivation, so it is what competes for the daily reallocation,
for the recovery pool, and for the monthly unreferred pool.

**A seat past its own 731 cycles is in the eligible set and not in the
contributing set.** It generates nothing and can win everything. That is ADR
0049's rule 3 — the 731 cycles bound the distribution and not the machine's
operating life — and it is what makes the recovery pool unstrandable: for as long
as any machine is operating and meeting its duty, a subsequent cycle with a
winner exists.

**Neither set may be narrowed to the other.** In particular the winner derivation
must not filter by span. A conforming implementation that did would strand the
pool the moment the last in-span machine finished, and the failure would be
silent because every identity would still hold. This is stated as a requirement
rather than left implied, and the recorded vectors fail if it is violated.

## Canonical economy state

Version six's key space with one entry kind removed and one added. Every other
kind, key width, and value width is unchanged.

| Kind | Entry | Key | Key bytes | Value | Value bytes |
| ---: | --- | --- | ---: | --- | ---: |
| 3 | cycle assignment | `u8(3) \|\| cycle_window:u64` | 9 | see below | 64 + 2⌈b/8⌉ |
| 17 | recovery pool | `u8(17)` | 1 | five `u64` legs | 40 |

**Entry kinds 7, 9, and 11 are retired and permanently unassigned.** Kind 7 held
the ten per-channel carries; kinds 9 and 11 held the seat manager set and the HUB
address set. A retired number is never reused, because assigning a new meaning to
a number a reader associates with an accepted contract is the cheapest way to
create an auditing mistake.

### The recovery pool record

```text
recovered_founder_operator      : u64
recovered_venture_escrow        : u64
recovered_community_grants      : u64
recovered_developer_incentives  : u64
recovered_system_creator        : u64
```

40 bytes, in channel order 0 through 4, which is the accepted manifest's order
for the five Founder Node legs of a base permission. **Exactly one such entry
exists on any chain**, written at genesis with all five legs zero and updated by
the assignment prologue.

The five legs are separate because they have five different destinations — the
Founder operator's own escrow and four typed custody kinds — and five different
channel caps and identities. A single total could not say which channel a
recovered unit belongs to.

The ten channels that are not Founder Node legs have no pool term, because they
have no base permission and therefore no remainder. That is why one entry with
five fields replaces ten entries of which five were structurally always zero.

### The cycle assignment record

```text
share_per_winner_atomic : u64
reallocated_count       : u32
winner_count            : u32
in_scope_count          : u32
bitmap_bits             : u32
pool_absorbed_atomic    : u64 * 5, in channel order 0 through 4
accrued_bitmap          : ⌈bitmap_bits / 8⌉ octets, one bit per seat ID
winner_bitmap           : ⌈bitmap_bits / 8⌉ octets, one bit per seat ID
```

The five `pool_absorbed_atomic` fields are new; every other field is version
three's, at its version-three width and meaning. The fixed part is 64 octets
rather than 24, and the five new fields sit after `bitmap_bits` so that every
fixed-width field stays contiguous ahead of the variable-length tail.

**The record states what the cycle took from the pool, not what a winner
receives.** A winner's pool share is `pool_absorbed_atomic(c) / winner_count`,
integer division, derived at the mint exactly as the reallocation share is
derived from `reallocated_count` and `winner_count`.

**Recording it is forced rather than chosen.** The pool's balance at a window is
a function of every earlier cycle, so a mint that derived it would replay the
whole assignment history. A mint reads at most thirty records and must remain
`O(cap)`.

**A record whose `winner_count` is zero must carry five zero
`pool_absorbed_atomic` fields**, because a cycle with no winner absorbs nothing.
A record that carried a nonzero absorbed amount with a zero winner count would
describe value divided by nobody, and it is rejected as a malformed record rather
than executed.

## Cycle assignment and settlement

At the first height of window `w + 2`, when `uptime-measurement-v1` finalises
window `w`, ordered block execution writes window `w`'s cycle-assignment record.
Steps 1 through 4 are version three's, unchanged:

1. derive the in-scope seat set and `bitmap_bits`;
2. read each in-scope seat's uptime and derive whether it met the cycle;
3. derive the **winner set** — the highest uptime among the eligible set, which
   is every in-scope seat that met the cycle and is under the accumulation cap,
   **in span or not**;
4. set the accrued bit of each **contributing** seat that met the cycle and is
   under the cap, and count every other contributing seat's permission as
   reallocated.

Steps 5 through 7 are version seven's:

5. add one base permission's `outstanding` per contributing seat, per leg, **in
   full**. Nothing is moved out.
6. **absorb the pool.** If the winner set is non-empty, `pool_absorbed(c)` is the
   recovery pool's whole balance in channel `c` **as it stood before this
   cycle**, and the pool's balance in every leg becomes zero. If the winner set
   is empty, `pool_absorbed(c)` is zero for every leg and the pool is untouched.
7. **divide and return.** For each leg `c` with per-cycle amount `leg(c)`:
   - the reallocation share is `leg(c) / winner_count`, integer division, or zero
     when there is no winner;
   - the reallocation remainder is `leg(c) - winner_count * share(c)`, which is
     the whole of `leg(c)` when there is no winner;
   - the pool share is `pool_absorbed(c) / winner_count`, integer division, or
     zero when there is no winner;
   - the pool residual is `pool_absorbed(c) - winner_count * pool_share(c)`;
   - the recovery pool's balance in `c` becomes
     `reallocated_count * remainder(c) + pool_residual(c)`.

Step 8 is version three's step 7, unchanged: accrue the referral leg for each
contributing seat, to the seat's recorded referrer identity when it has one and
that identity is under the cap, and to the unreferred pool otherwise.

**Step 6 reads the pool before step 7 writes it.** A cycle's own reallocation
dust, and the residual of the pool it just took, both belong to the pool for the
cycle after. Absorbing after contributing would let a cycle pay itself its own
dust and is a different contract; the order is stated here so two implementations
cannot each read ADR 0049's sentence a different way.

**Having any winner is the trigger.** A cycle in which every contributing seat
accrued has a winner set and a zero `reallocated_count`, and it still takes the
whole pool. The pool is value looking for the best performer, not a share of this
cycle's reallocation.

**A cycle with no contributing seat and a non-empty eligible set still absorbs.**
Every machine on the chain being past its own 731 cycles is the case ADR 0049's
permanence rule exists for, and it is the one in which the pool would otherwise
strand forever.

### What a mint collects

The mint walk's range, its per-window read, and its mark advance are version
three's, unchanged. For each window in the range that has a record:

- if the seat's **accrued** bit is set, add `leg(c)` for every leg;
- if the seat's **winner** bit is set, add
  `reallocated_count * (leg(c) / winner_count)` for every leg, **and add
  `pool_absorbed(c) / winner_count`**.

The second term of the winner branch is the only change. A seat with both bits
set in one window collects both.

**A seat past its own 731 cycles may hold a winner bit and must be able to mint
it.** Kind 4 is not gated on span in any version, and version seven states that
as a requirement rather than an accident: a mint by a seat whose distribution has
finished, collecting only reallocation and pool shares, is a conforming
transaction.

## Invariants

Version one's state invariants hold, extended by version two's typed custody
term, exactly as in version six.

The manifest's invariants hold at every accepted state. **The carry identity is
replaced by two identities**, both equalities, and both required at every
accepted state.

**The channel identity**, for each Founder Node channel `c` with per-cycle amount
`leg(c)`:

```text
issued(c) + outstanding(c) = assigned_cycle_permissions * leg(c)
```

Nothing is moved out of `outstanding`, so the identity has two terms rather than
three. `assigned_cycle_permissions` is the running count of base permissions the
chain has assigned, which is the sum over assignment records of the contributing
count.

**The backing identity**, for the same channels:

```text
outstanding(c) = claimable(c) + recovery_pool(c)
```

where `claimable(c)` is the sum, over every seat and over every window strictly
after that seat's `minted_through_window` that has an assignment record, of what
that record still owes the seat: `leg(c)` for a set accrued bit, plus
`reallocated_count * (leg(c) / winner_count) + pool_absorbed(c) / winner_count`
for a set winner bit.

**The backing identity is the statement that 100% is assigned.** The channel
identity alone cannot catch a stranded unit, because `outstanding` is one number
and a lost claim simply leaves it larger. Naming both halves makes value created
without a claimant and a claim destroyed without payment two different failures,
each an inequality against an exact figure.

**`claimable(c)` is exact rather than a bound.** The accumulation cap is applied
at assignment against the same mark the walk uses, so a seat over the cap accrues
no bit and — because the winner derivation filters on the same predicate — wins
no bit. No bit can therefore exist in a window outside the thirty a mint reaches,
and the mark advance can never step over an uncollected bit.

**The referral channel keeps version six's identity unchanged**, including the
unreferred pool term, because the referral leg has no winner split and therefore
no remainder.

**Channel 8 keeps version six's inequality unchanged.** Its forfeiture is a
different mechanism from the recovery pool and version seven does not touch it:
the verified-user channel has no second destination, so uncollected value there
is never issued and total supply ends below the maximum by exactly that amount.
The recovery pool closes a gap between what the manifest promises and what the
chain *creates*; it says nothing about what participants choose to collect.

## Version-seven genesis

Version six's field table with the schema version at `7` and the manifest digest
at `founder-economy-manifest-v3`'s. The prefix is still 110 octets, the
21,843-entry account bound is inherited and unreachable, and zero genesis
accounts is still required rather than expected.

```text
chain_id = H(D("protocol-stack:v7:chain-id") || canonical_genesis_v7_bytes)
```

**Genesis writes fourteen economy entries**: the ten channel entries with both
amounts zero, the recovery pool entry with all five legs zero, the ecosystem
verifier key, the unreferred pool entry with both amounts zero, and the
verified-user counter at zero. Version six wrote twenty-three; the nine that go
are the ten carry entries less the one pool entry that replaces them.

It writes no seat, no identity, no escrow, no signer, no enrollment, no referral
balance, no custody entry, and no cycle assignment.

## Version identity

| Construction | Version seven |
| --- | --- |
| chain ID | `protocol-stack:v7:chain-id` |
| state root | `protocol-stack:v7:state-root`, version field `7` |
| economy tree | `protocol-stack:v7:economy-empty`, `-leaf`, `-node` |
| genesis schema version | `7` |
| receipt version | `7` |

**Every other label keeps the version that accepted it.** The account derivation
stays `protocol-stack:v1:account`, the escrow derivation stays
`protocol-stack:v6:escrow`, the signer derivation stays version one's account
derivation over the signer key, the two transaction signing labels stay at
`protocol-stack:v1:`, and the six HUB messages keep their `protocol-stack:v6:`
labels. A label names the artifact it derives, and none of those artifacts
changed. Version six retains version one's account label for the same reason.

**A version-six signature is nonetheless not replayable onto a version-seven
chain**, because every signed message binds `chain_id`, and the chain identity is
derived over genesis bytes whose schema version and label both differ. The
separation the version labels would have provided is already inside every
preimage; re-versioning the message labels would additionally destroy the kind-1
byte identity, which every version since two has declined to do.

## Compatibility boundary

**Transaction bytes.** A version-one signed transfer is a version-seven kind-1
transaction, byte-for-byte, with the same signing message, transaction ID, and
execution result numbers. A version-one node presented with any other kind
rejects it at admission step 1 as `MALFORMED_TRANSACTION`.

**A version-six transaction of any kind is a version-seven transaction of that
kind by shape and belongs to a different chain by binding.** The two are
alternative chains; no version-six byte sequence is executed under version-seven
rules.

**State.** A version-six state is not a version-seven state. It carries ten
entries under a retired kind and no entry under kind 17, and its cycle assignment
records are 40 octets short in their fixed part. There is no upgrade block, no
migration, and no state translation, exactly as between every earlier pair.

**Roots and genesis.** The version-seven state root, chain ID, and economy tree
have distinct labels and version fields from all six predecessors, so no earlier
root is reinterpreted and no version-seven root collides with one. Each
non-collision is required separately, because distinct labels are strings rather
than a chain.

**What is not claimed.** No accepted M1 or version-two through version-six
vector, digest, receipt, root, or recorded devnet result changes, and none is
recomputed under this specification.

## Versioning and compatibility of this document

Everything version six fixes as immutable is immutable here too, with the state
key space, the cycle assignment record, and settlement steps 5 through 7 taking
their version-seven forms. A changed field, code, order, or semantic rule
requires a new transition version and an ADR; it must not reinterpret a
version-seven identifier.

Versions one through seven coexist as documents; every earlier artifact remains
in place, passing, and unedited.

## What this specification does not establish

Everything version six does not establish is inherited unchanged: direct-channel
eligibility and the refusal of kind 6; that a HUB identity is a distinct human,
which rests entirely on the ecosystem verifier's attestation; what a coerced HUB
signature can do; verifier key rotation; the payment behind a seat purchase; the
bootstrap; distribution; the unreferred pool's payout; and the HUB capture
pipeline and its threat model.

**Three limits are new and belong to this version.**

**Nothing here executes a transaction.** The model runs the settlement and the
conservation identities and the vectors record their outcomes, which establishes
that the arithmetic is right and the state encodes. It does not establish that a
block containing a mint charges a fee and commits a root under version seven;
that is the version-seven ledger, and it is the next slice.

**The pool lifecycle of ADR 0049 has no encoding here, because it is
unreachable.** A pool that can receive no further inflow is to be marked consumed
and then archived. The recovery pool can receive inflow for as long as any cycle
is assigned, so it never reaches that state, and version seven declines to add a
state bit that no transition can ever set. The lifecycle is a property of later
pools.

**Assigning 100% of the permissions is not issuing 100% of the supply.** A
permission nobody collects is still uncollected. The backing identity closes the
gap between what the manifest promises and what the chain creates; the
verified-user channel's inequality and every founder's own choice about when to
mint remain exactly as they were.

## Required vectors and evidence

`test-vectors/economy-transition-v7.txt` is normative. It fixes:

- **the version identity** — the five re-versioned constructions, the five
  retained labels, the manifest digest, and the six root non-collisions, each
  predecessor construction first required to reproduce its own accepted empty
  root so the comparison is against the real one;
- **the state surface** — kind 7's retirement, kind 17's key and value widths,
  the recovery pool record's five legs, the extended cycle assignment record's
  64-octet fixed part and its exact field offsets, the rejection of a record with
  a nonzero absorbed amount and a zero winner count, and the fourteen genesis
  entries;
- **the settlement** — a zero-winner cycle's whole contribution, a dust cycle's
  remainder, absorption before contribution, the pool share and its residual, a
  cycle with winners and no reallocation still absorbing, and a cycle with an
  empty contributing set and a non-empty eligible set still absorbing;
- **the two seat sets** — that the eligible set contains a seat the contributing
  set does not, and that a winner derivation filtered by span would change a
  recorded winner set, which is the regression guard rule 3 requires;
- **the collection** — a winner's pool share at the mint, a seat holding both
  bits in one window, and a mint by a seat past its own 731 cycles;
- **the conservation identities** — both, over a recorded multi-cycle schedule
  that crosses the accumulation cap in both directions, with the assigned total
  and the pool balance recorded at every step, and with 100% of every leg
  accounted for at the end.

The settlement's carried half is checked against
`test-vectors/economy-transition-v3.txt`, which every version since four has used
to keep an imported settlement honest, and the ten channel caps and five base
permission legs are checked against
`test-vectors/founder-economy-manifest-v3.txt`.

`docs/engineering/verification.md`'s rules apply: a boolean vector may only be
true, a name asserts no more than its value establishes, and a claim is checked
against something other than itself.

**The negative half of this version's claim is checked over the two Python
packages rather than over the two vector files.**
`tests/simulation/economy_transition_v7_carryover_test.py` classifies every
constant version six exports as carried or revised, requires the classification
to be total, requires a carried constant to be identical and a revised one to
differ, and fails if the revised set is not exactly what this document lists.
That catches the defect no derivation can: a value that moved without any vector
reaching it.

Acceptance of the recorded artifacts requires full GitHub-hosted verification on
the exact commit that adds them.
