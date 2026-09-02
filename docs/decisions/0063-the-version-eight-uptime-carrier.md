# ADR 0063: The version-eight uptime carrier

- Status: Accepted
- Date: 2026-09-02

## Context

[ADR 0061](0061-the-version-seven-abci-adapter.md) and
[ADR 0062](0062-the-version-seven-chain-fixture.md) completed a version-seven
chain that four replicas run and agree on. **They agree about blocks that pay
nobody.** `execute_block` takes an `UptimeSchedule*`, every caller in the
repository passes `nullptr`, and so no cycle assignment record is ever written
and no seat accrues anything. That is the whole remaining distance between what
runs today and the word *economic* in requirement 13 of
[`first-goal.md`](../project/first-goal.md).

The missing piece is not plumbing. A schedule is
[`uptime-measurement-v1`](../specifications/uptime-measurement-v1.md)'s measured
seats for a window, and a node cannot invent one: every validator must reach the
same assignment record or the state roots diverge. So the schedule has to be
data the chain agrees on, and **none of version seven's fourteen transaction
kinds carries it.** They are the transfer and the confirmed transfer,
registration, the seat purchase and activation, the direct issue, the three
mints, the two escrow and two signer operations, and the posture change. Not one
submits an uptime claim.

**The measurement itself is not owed.** `uptime-measurement-v1` is accepted and
599 lines long. It settles the slot grid and its correspondence to the
founder-directed 24-, 18-, and 6-hour figures, the two evidence sources,
challenge selection and its response deadline, the conjunctive
no-partial-credit slot credit rule, the dispute window and how far a dispute may
reach, finalisation by expiry, record completeness, and the 100,000-seat storage
bound. `simulation/uptime_measurement/` executes it and
`test-vectors/uptime-measurement-v1.txt` records it.

What that specification puts in its own "explicitly not in scope" list is what
this ADR decides: **"the numeric consensus receipt codes and transaction
encodings for a C++ transition, which are requirement 5."**

## Decision

### 1. The carrier is economy transition version eight, not an edit

[`economy-transition-v7`](../specifications/economy-transition-v7.md) fixes its
state key space, its result codes, and its fourteen transaction kinds as
immutable, and states that "a changed field, code, order, or semantic rule
requires a new transition version and an ADR". Adding transaction kinds, state
entry kinds, result codes, and a genesis field is all four at once.

So version eight is a new chain identity with its own labels, genesis schema
version, and receipt version, exactly as version seven was to version six.
Everything else in version seven carries over unchanged and by reference.

**The cost is honest and it is large.** A new chain identity re-versions the
snapshot, the owning store, the application layer, the transport dispatcher, the
node process, and the ABCI adapter, which took ten slices for version seven.
This ADR does not pretend otherwise. What it buys is the only thing that makes
the economy real: a schedule the chain derives rather than a caller supplies.

### 2. Two transaction kinds, not three, because a duty report has no honest signer

The obvious reading is three kinds — a duty report, a challenge response, and a
dispute. **The duty report cannot be one of them.**

`uptime-measurement-v1` is explicit that a duty report "is an observation rather
than a claim, needs no attestation, and cannot be forged by the seat it
concerns", because the chain produces it "from records it already keeps".
A transaction has a signer. Whoever signs a duty report is asserting something
no other node can independently reproduce, which makes the schedule a
proposer's opinion — a consensus fork with extra steps, and the exact failure
the slice exists to avoid.

The mechanism that *would* be honest is
[ADR 0050](0050-the-block-timestamp-is-the-ecosystem-clock.md)'s rule 2: an
attested claim consensus agrees on, read deterministically afterwards. For
validator duties that claim is the previous height's commit, which every replica
sees identically. **It cannot be produced today**, because a duty report "is only
ever produced for a duty the seat was *assigned*", and the deterministic
active-set protocol that assigns duties is out of `uptime-measurement-v1`'s
scope and does not exist. That specification already states the consequence: a
seat "is credited for the duties it was assigned, and an empty assignment is
satisfied vacuously".

So under version eight **every seat's assigned duty set is empty and the duty
layer removes no credit**, which is the accepted specification's own stated
behaviour rather than an omission. Version eight encodes no duty report, on
version seven's own precedent: it declined to encode the ADR 0049 pool lifecycle
because no transition could ever set it, and a duty report no conforming chain
can produce is the same case.

**Rejected: a duty report signed by the block proposer.** It is the shortest
path to a non-empty duty layer and it is the forbidden one. A value one node
supplies and another cannot reproduce is not evidence.

**Rejected: a duty report signed by the seat itself.** It inverts the one
property the accepted specification names — that a report cannot be forged by
the seat it concerns.

**Rejected: reserving the encoding now and leaving it unproducible.** It costs a
kind byte and a result code that no vector could ever reach, which
`verification.md` and version seven both refuse.

The consequence is stated plainly in the specification's limits: under version
eight a seat's credit rests on the challenge layer alone.

### 3. A challenge is materialised into state at the height it is issued

`uptime-measurement-v1` derives selection from a beacon:
`selected(seat, h)` is a digest over `beacon(h)` and the seat, where
`beacon(h)` is the canonical state root at `h - 1`.

A node executing block `h` has that root in hand: it is `previous_state_root`,
which `execute_block` already computes before anything else. But a response
arriving up to twenty heights later would need the beacon of a past height, and
a version-seven `Ledger` retains no root history.

**So the chain writes the selection down.** In the block prologue at height `h`,
every in-scope seat the predicate selects gets an *open challenge* state entry
keyed by the challenge height and the seat. A response is then a state lookup
rather than a beacon recomputation, and expiry is an incremental sweep of the
entries issued twenty heights earlier.

Three things follow, and each is why this is the shape rather than a convenience:

- **No beacon retention.** The root is read once, at the height it belongs to,
  and never stored. A retained ring of past roots would be new consensus state
  whose only purpose is to re-derive something already derived.
- **`CHALLENGE_NOT_ISSUED` becomes checkable rather than recomputable.** A seat
  cannot manufacture credit by answering a challenge it was never issued,
  because the entry either exists or it does not.
- **The per-slot counters of the model disappear.** The model clears a seat's
  slot bit at slot close when `slot_issued` exceeds `slot_answered`. Selection
  excludes the final twenty heights of every slot, so every challenge issued in
  a slot has been answered or has expired before that slot ends. Clearing the
  bit at expiry is therefore exactly equivalent, and it is incremental: there is
  no slot-close sweep over the population at all.

**The preimage is octets, and it is not the model's.**
`uptime-measurement-v1` digests an RFC 8785 JSON object, because every accepted
model in this repository works in canonical JSON. A consensus kernel that
canonicalised JSON to decide who is audited would put a parser on the most
adversarial path the pipeline has, and every version-seven construction is
octets for that reason. Version eight therefore defines its own fixed-width
preimage and its own label.

**The consequence is that the chain and the measurement model select different
heights for the same beacon, and that is intended.** What the two share is the
rule — the beacon is the state root at `h - 1`, the period is one challenge per
slot in expectation, and the final twenty heights of every slot are excluded —
and every property the accepted specification argues from is a property of the
rule rather than of the byte layout. The vectors record the properties and do
not compare the two selections, because they are not the same function and
claiming they were would be the kind of name that asserts more than its value
establishes.

### 4. A window record is sparse, and absence means a fully credited seat

A slot bit begins set and evidence only ever removes credit, which is invariant
3 of the accepted model. Version eight encodes that directly: a seat has a
window record **only once it has lost or had a slot voided**, and an absent
record for an in-scope seat reads as all twenty-four slots credited and nothing
disputed.

A healthy machine therefore writes nothing at all, and the storage the pipeline
adds is proportional to failure rather than to population.

The record carries the credited bitmap and the disputed bitmap **separately**
rather than folding a dispute into a cleared credit bit. Folding is smaller by
three octets per record and it makes `DISPUTE_REPLAY` unreachable — a second
dispute against the same slot would report `DISPUTE_SLOT_NOT_CREDITED`, which is
false about what happened. A result code the encoding makes unproducible is
coverage the vectors cannot show, so the two bitmaps stay separate.

### 5. A response is authorized by the seat's owning identity, not by a HUB signature

Kinds 2, 3, 4, 5, 17, 18, and 19 all carry a HUB signature, because each of them
moves value or changes an identity's standing. A challenge response does
neither: it is evidence about a machine.

Requiring a HUB signature would mean one HUB interaction per hour per seat, for
every seat, forever. Version eight instead resolves the acting escrow the way
every version-seven transaction does and requires that escrow's owning identity
to equal the seat's recorded `hub_identity_hash`. The authority is already in
state and needs no new attestation.

### 6. A dispute is relayed, and its authority signs the body

`uptime-measurement-v1` refuses a dispute from "a signer other than the recorded
Ecosystem AI key". Under [ADR 0047](0047-the-founder-machine-runs-the-ecosystem-ai.md)
the ecosystem AI no longer has one holder: a judgment is issued by the assigned
machine, which "issues one signed, bounded decision", and
[ADR 0048](0048-hub-verification-runs-locally-with-an-ai-integrity-monitor.md)
replaces the single genesis `verifier_key` with a registry of per-machine
attestation keys — while stating that the registry "is a genesis and state-layout
change" belonging to a later version.

Version eight does not build that registry, and it does not pretend the single
key is the final shape. It takes the pattern version seven already uses for
exactly this situation. **Kind 10 carries a `verifier_signature` in its body**,
verified against the recorded ecosystem verifier key, while the envelope's own
authority is an ordinary signer who pays the fee and supplies the nonce. A
dispute is encoded the same way: any signer may relay it, and the body carries
the dispute authority's detached signature over a canonical dispute message.

That is also the right shape under ADR 0047 rather than merely a convenient one.
A deciding machine issues a signed bounded decision; **someone submits it**. A
scheme in which the authority must itself be a chain account would give the AI a
nonce sequence, a balance, and a fee obligation, none of which any accepted
document gives it.

Genesis therefore gains one `dispute_authority_key` field beside the existing
verifier key. It is **separate rather than reused**: whoever attests HUB
identities should not thereby acquire the power to void a machine's uptime, and
least privilege is free here.

**The interim single key is safe in the only direction that matters.** A dispute
can subtract and never add, it is capped at the founder-directed six-slot grace
allowance per seat per window, and expiry finalises a window with no signature
at all. A holder of that key cannot manufacture a payment, cannot direct value
anywhere, and cannot fail a seat that was fully operational. Replacing it with
ADR 0048's registry is a later transition version, and the replacement changes
who signs rather than what a signature can do.

### 7. `RESPONSE_INVALID` is not encoded, because the predicate is founder-reserved

`uptime-measurement-v1` puts **the content of a challenge** in its own "explicitly
not in scope" list: what a node must hold, compute, or serve is the concrete
resource commitment, it sets what an operator must own in order to be paid, and
it is founder-reserved. The model treats the answer as an abstract predicate.

Version eight instantiates that predicate as the weakest one available: an
answer of the right width is accepted. **So version eight measures liveness of a
responder and not possession of a resource**, which is exactly the limit the
accepted specification already states about itself, and the limit is repeated in
the specification rather than buried here.

It follows that no execution path can produce `RESPONSE_INVALID`, so version
eight does not declare it. The founder answer that settles the challenge content
is what adds both the predicate and its code, in the transition version that
binds it.

**This cannot pre-empt the founder's answer**, because the weakest predicate is a
lower bound: a later version can only tighten what an answer must satisfy, and
tightening removes credit from machines that were never doing the work.

### 8. The schedule is derived at the prologue, from state, with no second derivation

Version eight removes the `UptimeSchedule*` parameter from `execute_block`
entirely. At the first height of window `w + 2` — the point
[ADR 0045](0045-the-version-six-execution-model-and-three-derived-rules.md)
fixed and version seven inherited — the prologue derives window `w`'s record
from the seat table and the window records, hands it to `derive_assignment`
unchanged, and then discards window `w`'s evidence.

The in-scope set, the credited slots, and the in-span flag are all read from
chain state rather than supplied: in-scope and in-span both follow from the
seat's recorded `activation_height` through
[`cycle-boundary-v1`](../specifications/cycle-boundary-v1.md)'s
`first_cycle_window`, and the credited count is a population count over the
window record. A parameter a caller may supply is a parameter a caller may
supply *differently*, which is the whole failure mode.

### 9. The response is fee-exempt, and that is a founder answer rather than a default

Every version-seven kind charges the same `fixed_fee`. Version eight first
applied that rule to both new kinds, as a **default rather than a decision**,
because inheriting an accepted uniform rule invents nothing and carving out the
contract's first exemption would.

**What the default implied was recorded rather than hidden.** A seat expects one
challenge per slot, so a machine would have paid about twenty-four fixed fees
per cycle to prove the uptime it is paid for, and at the 100,000-seat capacity
the population would have offered about 2.4 million fee-paying transactions per
day. Whether answering a mandatory audit should cost an operator anything is a
question about what a participant must do in order to be paid, which is
founder-reserved, so it was asked at the specification stage rather than
settled.

**On 2026-09-02 the owner answered: the challenge response is fee-exempt.**
Answering a mandatory audit costs an operator nothing.

Two encoding consequences follow, and they are deliberately not symmetric with
kind 10, the other fee-exempt kind:

- **The fee limit must be zero**, and a nonzero one is refused at admission
  rather than ignored at execution. That is kind 10's rule and its reason: a
  second encoding of "not applicable" is the non-minimal representation
  `protocol-primitives-v1` forbids. `FEE_LIMIT_TOO_LOW` becomes unreachable for
  this kind.
- **The nonce is kept**, which kind 10 drops. A registration has no escrow and
  therefore no nonce sequence; a response has both, so replay protection is
  doubled rather than replaced. An operator who does not want the audit path
  advancing the nonce their wallet uses may dedicate an escrow to the machine,
  which decision 5's authority rule already permits — any escrow the seat's
  identity owns may answer.

**The exemption is bounded by the chain rather than by a fee.** A response is
accepted at most once per challenge the chain itself issued, so the free
accepted traffic is about 83 transactions per block at capacity and no
participant can inflate it. A refused response was already free under either
answer, because version seven charges no fee for any non-success result.

**The dispute is not exempt.** A response is a machine answering an audit the
chain demanded of it; a dispute is a third party relaying someone else's
judgment, and nothing about the ecosystem AI's decision reaching the chain is
free.

**The timing is the argument for asking at all.** The rule is one sentence in
one transition and it was answered before the execution model, the execution
vectors, and the kernel depended on it. The same question answered after a
kernel exists is a re-versioning.

## Consequences

**The economy becomes reachable.** With the carrier in place, a version-eight
chain writes assignment records because it measured seats, not because a test
harness handed it a map. Requirement 13's adversarial scenarios then have
something economic to disagree about.

**Two resource bounds become consensus-visible and are stated in the
specification.** Issuing challenges evaluates the selection predicate once per
in-scope seat per height — about 100,000 digests over roughly 6.4 MB of preimage
at full capacity, per block. And the assignment prologue at a window boundary
reads and then discards the window's records, which is the same order as the
assignment record it already writes.

**Version eight measures less than the pipeline eventually will.** The duty
layer is vacuous until the active-set protocol exists, and the challenge
predicate is the weakest one until the founder settles the resource commitment.
Both limits are stated in the specification's own "what this does not establish",
and neither is a defect in the carrier: a carrier that waited for them would
leave the chain paying nobody in the meantime.

**The dispute authority is a single key during an interim it names.** ADR 0048's
per-machine attestation registry replaces it, and until then the containment
argument rests on the cap and the subtract-only direction rather than on the
holder.

**Six downstream layers will need version-eight forms.** The snapshot, the store,
the application, the transport, the node process, and the ABCI adapter each
carry a version number. That is the recurring cost of a new chain identity and
it is the reason this ADR states the alternative it did not have: version seven
cannot be edited.
