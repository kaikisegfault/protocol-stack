# ADR 0034: Economy transition v3 — managers, the accumulation cap, and HUB entry

- Status: Accepted
- Date: 2026-08-14

## Context

[ADR 0033](0033-founder-decisions-minting-hub-and-referral-entry.md) records the
founder direction of 2026-08-14 and states that it supersedes
[`economy-transition-v2`](../specifications/economy-transition-v2.md) in four
places. That specification and
[ADR 0032](0032-economy-consensus-transition-and-compatibility.md) were accepted
and merged on 2026-08-13 and are the record of what the hosted matrix verified
on that commit, so they are not edited. A changed transition is a new version —
the rule ADR 0024 and ADR 0026 established and every economy contract has
followed since.

This ADR records the encoding decisions
[`economy-transition-v3`](../specifications/economy-transition-v3.md) makes, the
alternatives rejected, the two answers derived from decided principles rather
than chosen, and the four defects found in version two while deriving them.

## Decision

### Managers are presence-only entries, and the mint credits the signer

A manager set is a family of entries keyed by `(seat_id, manager_account_id)`
with an empty value, plus a `manager_count` in the seat record. Membership is
one lookup and addition is one write; the set has no order and no order enters a
transition.

A `manager_count` in the seat record rather than a range scan is the whole
reason the count is state: enforcing a per-seat bound by iterating a key prefix
inside a transition is the kind of implicit cost two implementations disagree
about.

**The mint credits the signing manager's account, and that is derived rather
than chosen.** The Founder Constitution makes adding a verified manager the
remedy for a lost address. If minted value went to the recorded purchaser, a
founder who lost that key could add a manager, mint, and still reach nothing, so
the remedy the constitution names would recover nothing. The only address a mint
transaction identifies that its signer can spend from is the sender.

The alternative — credit the recorded purchaser and add a separate transfer
authority — was rejected because it reintroduces the withdrawal step ADR 0033
removes and needs a second authorization rule for the same value.

**The bound is 16 managers per seat.** It is a resource limit, not a statement
about founders: each addition already costs a fee and a fresh biometric
approval, so the bound is not what makes abuse expensive; it is what turns the
per-seat state into a constant, which requirement 12 asks for. Sixteen is far
above any device set a founder plausibly holds. An unbounded set was rejected
because it leaves requirement 12 with no answer for the one entry family a user
controls the size of.

### Optional biometric on minting is a second kind, not an optional field

Version three has `mint_node` at a 4-byte body and `mint_node_verified` at 68.
The seat's flag makes the plain kind refuse with `BIOMETRIC_REQUIRED`; the
verified kind is accepted either way, because it proves strictly more and
refusing it would spend a result code on a transaction that over-delivered.

The alternative was one kind with a presence flag and a 64-byte field, which
would make every unprotected mint 229 bytes rather than 164 and would need a
rule for a signature the seat did not require. Two fixed-length kinds cost one
identifier and no ambiguity.

**Kinds 3 and 7 therefore share a body length, and that is the case version two
predicted.** Version two recorded that "a decoder must dispatch on the kind byte
because a later version may add a kind whose length coincides", and version
three is that later version. The vectors require the signing message to change
when a body is presented under another kind's identifier, so the collision is
evidence that the dispatch rule was right rather than a defect it created.

`set_mint_biometric` goes the other way: one kind with an `enable` byte, whose
signature field must be 64 zero octets when enabling. The asymmetry ADR 0033
directs is then half an admission rule — "zero when enabling" is a property of
the bytes — and half an execution rule, because verifying the disable signature
reads the verifier key from state.

### The accumulation cap is measured in windows, not in accrued cycles

`MINT_ACCUMULATION_CAP = 30`. A seat accrues in window `w` only when
`w <= minted_through_window + 30`, and a referrer only when
`w <= collected_through_window + 30`. ADR 0033 named roughly thirty days and
delegated the figure; a cycle is a 24-hour-target window, so thirty windows is
thirty days on the accepted grid.

**Measuring in windows rather than in accrued cycles is the load-bearing
choice, and it is what makes the cap bound anything.** ADR 0033 states the cap's
second purpose plainly: version two recorded that a mint walks every cycle since
the last one, so the work in a single transaction grows with the wait, and "the
cap turns that growth into a constant". A counter of accrued cycles does not
turn it into a constant. Thirty accruals can be spread over any number of
windows, so a mint would still have to walk every window since the mark to find
them, and the cost version three exists partly to close would be unchanged.

The window form bounds it exactly. A mint walks
`(mark, min(last_assigned, mark + 30)]`, and no window outside that range can
carry a bit for the seat, because the assignment that wrote it applied the same
bound against the same mark — the mark changes only at a mint, and a mint sets
it to the last assigned window. So every window in `(mark, last]` was assigned
while the mark held its current value, and the bound is exact rather than
conservative.

The two forms agree wherever a seat is running, because a seat that meets every
cycle accrues once per window. They differ only for a seat that has been
failing, and there the window form keeps the rule's stated promise: a founder
who has not pressed the button in a month is not accruing, whatever the reason.

**A mint that collects nothing still advances the mark.** Without that, a seat
that failed every cycle for two months would be permanently past the cap with
nothing to collect, so `NOTHING_TO_MINT` would refuse the one action that could
free it. The code is therefore reserved for a mark already at the last assigned
window — a genuinely empty action — and a mint that moves a stale mark succeeds,
charges the fee, and issues nothing.

**ADR 0033 anticipated a stored unminted-cycle count and version three stores
none.** `w - minted_through_window` is that count; a second field holding it
would be a second representation of a fact the mark already carries, and two
representations of one number are a thing to keep in agreement rather than a
thing to read.

### A capped seat is excluded from the winner set

ADR 0033 states that a capped seat's permissions "go to that cycle's best
performers instead, by the same path a failed cycle takes". A capped seat can
accrue nothing, so including it in the winner set would divide the reallocated
permission by a count that includes a recipient which cannot receive, and that
fraction would reach nobody — making the founder's own sentence false for it and
stranding the value as permanently unmintable outstanding supply.

**Excluding capped seats is the reading under which every reallocated unit
reaches a seat that can collect it.** It is derived from a decided principle
rather than chosen between alternatives the principle does not distinguish, and
it is recorded here because it decides who is paid and should be visible as a
derivation rather than buried in an encoding.

The rejected alternative is worth naming: rank purely by uptime and let a capped
winner's share stay outstanding forever. It preserves the winner rule's literal
wording — "the highest cumulative fully operational uptime in that same cycle" —
at the cost of the reallocation rule's purpose. The constitution already
restricts that candidate set once, with "a winner must itself have met the
cycle", so restricting it to seats that can actually receive is the same shape
of restriction rather than a new kind of one.

### HUB verification is one registry entry and one transaction, and no more

Kind 10 records an ecosystem-verifier attestation binding an account to a
uniqueness commitment. Kind 2 refuses a named referrer with no such record. That
is the whole of HUB in version three.

ADR 0033 widens HUB into an ecosystem-wide identity layer with its own
direct-mint incentive, and that layer is an M4 milestone specified nowhere.
Consensus needs a registry it can consult when a purchase names a referrer;
building anything more here would specify an identity service inside a
transaction encoding.

**The chain does not enforce one uniqueness hash per account.** Enforcing it
decides what happens to a verified human who loses the key to their registered
account, which sets what a user must own in order to keep participating and is
founder-reserved. Not enforcing it is the smaller claim: the chain records what
the verifier attested, exactly as it does for the seat biometric hash, and
version two already records that it establishes nothing about what such a hash
means.

The alternative — a second entry keyed by the uniqueness hash, refusing a second
registration — was rejected for that reason and not for cost. It is one entry
kind and would be easy; what it is not is decided.

### Minted value lands in the account map

The Founder operator leg and the whole referral credit ordinary account
balances. The four institutional legs stay in typed custody, because the
escrows and the System Creator are not accounts with keys on this chain and
`escrow-payout-v3` releases their value through capabilities rather than
signatures.

The typed-custody `beneficiary_kind` space is enumerated here for the first
time: version two used the byte and never fixed its values. With founder seats
and referrers moved to the account map, five codes remain and four of them are
singletons with a zero beneficiary ID.

### Everything the envelope already fixed carries over

The 80-byte header, the 16-byte trailer, the kind-1 body, the two version-one
signing labels, the admission order and its three codes, the RFC 9162 tree
shape, the genesis field table and its 21,843-entry bound, the receipt layout,
and result codes 0 through 20 with their exact meanings are unchanged. The
result-code space extends contiguously to 23.

Three things are re-versioned because nothing depends on their bytes: the
chain-ID label, the state-root label and version field, and the economy tree
prefix — which is what makes a version-three root collide with neither
predecessor — and the six verifier message labels, so a verifier implementation
can tell which contract a request belongs to without inspecting a chain ID. The
transaction signing and identity labels are deliberately *not* re-versioned,
because doing so would destroy the kind-1 byte identity that is the whole
compatibility argument.

The receipt version moves to 3 while its layout does not, because the admissible
kind and result-code ranges widen. Leaving it at 2 would make a version-two
reader classify a kind-7 receipt as invalid rather than as unknown, which is the
misreading a version field exists to prevent.

## Four defects in version two, found by deriving version three

None of these changes what version two's vectors verified, and version two is
not edited. They are recorded because version three fixes them and a reader
comparing the two documents will otherwise read the differences as arbitrary.

**The bitmaps were indexed by in-scope rank.** Version two says a seat "reads
its own bits" and calls the lookup `O(1)`. Reading bit *k* requires knowing the
seat's rank in the in-scope set for that window, which requires deriving the
whole in-scope set — an `O(n)` operation inside a transition described as
constant. Version three indexes by seat ID, so the lookup is a shift and a mask.
At capacity the record is the same size, because every seat ID is in scope.

**The record could not answer what a winner won.** A winner receives an equal
share of *every* reallocated permission for the cycle, and version two's record
holds no count of them. It cannot be recovered from the bitmaps either: a seat
with no met bit may be outside its own span or may have failed, and only the
second reallocates. Version three records `reallocated_count`.

**The carry identity did not follow from the assignment steps.** Version two
states `issued + outstanding + carry = assigned * leg` as an equality, and its
assignment adds remainders to the carry and separately adds one base permission
of outstanding per assigned permission — which counts the carried value twice.
Version three moves the remainder *out of* outstanding and into the carry, which
is what makes the equality hold.

**The storage table contradicts its own derivation and the accepted vectors.**
Version two's table records the carry family at "180 bytes" beside the
derivation `10 * (2 + 8)`, which is 100, and
`test-vectors/economy-transition-v2.txt` records
`storage.carries_bytes_at_capacity=100`. The normative artifact is right and the
prose cell was a transcription of the row above it. **This one is repaired in
place**, because it is a documentation defect rather than a contract change: no
byte, code, order, or rule moves, the verified vector file is unchanged, and
leaving an accepted specification stating a figure its own derivation and its
own vectors contradict would be worse than the repository's edit rule is
protecting against.

## Consequences

**Version two stays in place, passing, and unedited apart from that one
figure.** Its 238 vectors and their digests remain the accepted record of
2026-08-13, and `simulation/economy_transition/` continues to implement it. A
version-three model is a sibling package on the same test ADR 0029 states:
version three changes transitions, inputs, and the state shape, so a shared
implementation would have to branch inside every affected transition.

**Requirement 10 is now unblocked against a settled target.** The C++ kernel
implements version three, and its first check should be the kind-1 identity
vectors: if the C++ encoder does not emit the accepted M1 transfer bytes, the
compatibility boundary is broken at its narrowest point.

**One containment property is traded away deliberately.** Version two could say
that a stolen wallet key "can only mint to the seat's own recorded account, so
it redirects nothing". Version three cannot, because a manager mints to itself
and that is what makes manager addition a recovery. The replacement is the
optional biometric on minting, whose asymmetric switch a thief cannot undo.
Whether that is an adequate replacement is one of the review items below.

**The verifier now gates a payment path, by the operator's own choice.** In
version two the ecosystem verifier signed entry and never income. In version
three a seat that switches protection on has made verifier availability a
precondition for its own income.

**Storage moves in two directions.** Typed custody collapses from 4,200,000
bytes at capacity to 168, because minted value lands in accounts founders
already hold; the manager set adds a bounded 59,200,000-byte worst case that no
plausible deployment reaches. The one unbounded term — cycle assignment records
at 25,033 bytes per cycle — is unchanged, and the cap does not prune it.

**The unreferred pool now has a state entry and still has no payout.** Version
three specifies where its value comes from, including forfeited referral
accruals, and adds one 17-byte entry to hold it. The month definition and the
payout transition remain specification work.

## Compatibility and independent review

No accepted artifact changes behavior. `economy-transition-v2`, its vectors, its
model, and every earlier contract remain in place, passing, and unedited except
for the one corrected storage figure recorded above.

A version-three chain is a new chain. There is no upgrade block, no state
translation, and no migration from a version-two chain; the two are alternative
contracts and only one will ever carry value.

Five claims need review before value depends on them. The first two are
inherited from ADR 0033 and restated here with the encoding that realises them.

**That the accumulation cap is not a penalty path.** The argument is that an
unminted permission's units do not exist. A reviewer should confirm that a
capped cycle and a failed cycle are the same class of event, because they differ
in one respect: a seat losing a cycle to the cap **met** the requirement and lost
the permission for not collecting it.

**That optional biometric-on-mint preserves the constitution's containment.** It
does for a founder who leaves it off. For one who switches it on, verifier
availability becomes a precondition for their own income — the coupling the
constitution refuses to impose, reintroduced by the operator's own choice.

**That excluding capped seats from the winner set is the right derivation.** The
alternative preserves the winner rule's literal wording and strands value. If a
reviewer or the owner reads the founder rule the other way, the change is one
predicate in the assignment transition and a new contract version.

**That a permanent manager authority with no revocation is safe enough.** The
constitution decides that a recorded manager is never erased and names addition
as the remedy for loss. It decides nothing about theft, and version three
therefore leaves a compromised address able to mint until the founder switches
protection on.

**That 16 managers per seat is a limit and not a policy.** It is recorded as a
resource limit. If it turns out to constrain a legitimate founder, it is a
founder-facing value rather than an engineering one and belongs to the owner.

Two limits are inherited unchanged and are not new review items: that the
biometric hash and the HUB uniqueness hash mean anything is entirely the
off-chain verifier's, and the measurement pipeline's own unreviewed claims in
ADR 0027 and ADR 0028 are untouched by encoding their consequences.
