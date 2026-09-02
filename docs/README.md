# Documentation index

## Project

- `project/founder-constitution.md`: authoritative founder intent, fixed
  end-state requirements, decision ownership, and unresolved founder gates.
- `project/vision.md`: long-term direction and boundaries.
- `project/charter.md`: current architecture and governing principles.
- `project/first-goal.md`: current operational outcome and acceptance evidence.
- `project/goals/m1-sovereign-devnet-alpha.md`: retained acceptance contract
  for the completed first runnable devnet milestone.
- `project/goals/m2-founder-economy-proof.md`: retained acceptance contract for
  the completed Founder Economy proof milestone, whose figures predate the
  2026-08-07 direction revision.
- `project/roadmap.md`: ordered milestones.
- `project/current-state.md`: verified handoff between sessions.
- `project/native-economy-simulation-report-v1.md`: reproducible M2 seeded
  accounting study and its explicitly non-production interpretation.
- `project/participation-simulation-report-v1.md`: reproducible M2 validator
  and node lifecycle, entitlement, and claim-funding study.
- `project/authority-simulation-report-v1.md`: reproducible M2 threshold
  result, rotation, containment, recovery, and shared-adapter study.
- `project/economic-stress-report-v1.md`: reproducible M2 orthogonal
  cross-simulator parameter-family and reverse-stress study.
- `project/economic-envelope-report-v1.md`: exact M2 reward-funding and
  within-role concentration boundaries around the screened survivor families.
- `project/reward-distribution-report-v1.md`: exact M2 payout-cap,
  credit-liveness, and same-principal identity-split evidence.
- `project/admission-cost-report-v1.md`: exact M2 cross-principal split,
  operating-cost, refundable-bond, lock, churn, and honest-entry boundaries.
- `project/minimum-entitlement-report-v1.md`: exact M2 strictly funded floor,
  smallest-honest-entry, and hidden-principal split boundaries.
- `project/founder-economy-report-v1.md`: the accepted M2 milestone report,
  separating what the six Founder Economy contracts and their verifiers prove
  about deterministic accounting from the policy, provenance, identity,
  storage, and production-safety claims none of them establishes.

## Architecture

- `architecture/sovereign-core.md`: system layers and replaceable boundaries.
- `architecture/ledger-kernel.md`: ledger ownership, atomic block application,
  canonical outputs, and failure boundaries.
- `architecture/sqlite-ledger.md`: owning persistence boundary, durable
  height-zero creation, and validated reopen behavior.
- `architecture/local-ai-authority.md`: the logical AI authority served by the
  Founder Machines, capability containment, and delegation stages.

## Decisions

Architecture decision records live in `decisions/`. Proposed records are not
irreversible commitments. Accepted records govern implementation until
superseded.

ADR 0016 adopts the Founder Constitution and staged realization order. It
changes project direction but does not activate production economics or alter
current consensus behavior.

ADR 0017 selects the eight-decimal `u64` Founder Economy denomination, fixed
manifest encoding, and outstanding-permission liability shape for M2. It does
not activate those values in the M1 devnet.

ADR 0018 selects the Founder Economy simulator's transition set, bound
research-input encoding, creation-time beneficiary resolution, journal
conservation rules, and digest labels. It accepts a research model contract,
not a consensus transition.

ADR 0019 selects the Founder Seat sale denomination, the exact tier boundary of
the constitutional price schedule, pure-handler failure atomicity, and the
separation of the seat sale model from the economy simulator. It accepts a
research model contract, not a consensus transition.

ADR 0020 selects the integer remainder rule for the commercial split, the
creator sub-split shape, overflow-free share arithmetic, per-cycle Founder
distribution with a carry, and separate fee accounting. It accepts a research
model contract, not a consensus transition.

ADR 0021 selects the separation of escrow payouts from the economy simulator,
the digest-bound opening custody, the two-bound revocable spending capability,
authority-before-funds rejection ordering, and the reconciliation of custody
against capability accounting. It accepts a research model contract, not a
consensus transition.

ADR 0022 selects closed-form derivation over a second model walk as the
independence argument for the multi-year scenario suite, defines restart
equivalence as state equivalence under replay, and requires seeded property
tests to assert published values rather than a model's own invariants. It
accepts an evidence contract, not a consensus transition.

ADR 0023 records the founder decisions of 2026-08-07: the maximum supply
revised to 56,993,950,100 before any issuance, the doubled unconditional
referral benefit relocated to the direct-mint channels, the unreferred
performance pool that keeps that channel exactly consumed, the 18-hour activity
threshold with its 6-hour fragmentable grace allowance, highest-uptime
performance reallocation with equal splitting among ties, and an uptime path
that derives validator duties on-chain, proves resource provision by
challenge-response, and gives the Ecosystem AI a dispute window rather than a
signature that could freeze payment. It supersedes the economic figures in ADR
0017 and the unresolved markers in ADRs 0018 and 0022, and activates nothing.

ADR 0024 accepts a second Founder Economy manifest rather than editing the
first, because the M2 evidence is evidence about a specific contract and the two
differ in shape rather than only in parameters. It separates the versions at the
digest domain label, orders the channels as the Founder Constitution's two
allocation tables read, describes the referral by its two destinations so the
exact-consumption claim is machine-checkable, keeps the 18-hour activity
threshold out of the canonical bytes until the cycle boundary is defined, and
makes the verifier's independence a hand-restated constitution rather than a
second model. It accepts an economic contract, not a consensus transition.

ADR 0025 makes that contract executable. It supplies the cycle uptime record as
measurements only, so the activity verdict and the winner set are derived rather
than supplied; separates a shared `cycle_window` from a seat's own
`cycle_index`; binds a window's record by digest on first reference; carries the
integer remainder and the whole pot of an empty winner set forward; replaces the
conditional referral permission with an unconditional direct-mint accrual with
two destinations; and keeps `founder_referral` out of `direct_issue` so a
supplied eligibility fixture cannot mint referral units. It accepts a research
model contract, not a consensus transition.

ADR 0026 rebinds the dependent models to version two. It records that rebinding
is a new version rather than an edit, because `escrow-payout-v1` fixes its
research-input shapes as immutable; that one implementation selected by a
`Binding` is preferred to a duplicate package, because the two versions'
transitions are identical and duplication has no mechanism to notice drift; that
the research scenario is held fixed so a rebinding defect is distinguishable
from an intended scenario difference; and that a cross-version state reuses
`INVALID_RESEARCH_INPUT` rather than gaining a code of its own. It accepts a
compatibility boundary, not a consensus transition.

ADR 0027 defines the cycle boundary in chain heights. It records that a cycle is
28,800 blocks on one global grid rather than a per-seat grid, because
reallocation to the highest uptime "in that same cycle" needs a window several
seats share; that 28,800 is chosen because the pinned 3-second commit interval
divides all three founder-directed durations exactly, so no threshold is
rounded; that a seat's cycles begin at the next full window, because counting the
activating window would fail a seat for where in a window its activation landed;
that activation heights may not decrease; and that a window's nominal duration is
86,400 seconds, so a measurement is denominated against the window rather than a
clock. It defines a schedule and a check, not a consensus transition.

ADR 0028 defines the uptime measurement pipeline. It records that credit is per
one-hour slot, because all three founder-directed figures are whole slots and
partial credit would interpolate between probes; that a seat is credited for the
duties it was assigned rather than for signing, because the constitution bounds
the live signing set; that challenges are selected from the previous height's
state root, so a seat cannot schedule uptime around its own audit; that the
Ecosystem AI's dispute may only subtract and only up to the grace allowance, so
a captured key cannot fail a fully operational node; that silence finalises a
window after one further window; and that a record's seat set is derived from
the bound activation schedule, so an omission is unrepresentable. It measures
and settles no value.

ADR 0029 enforces the cycle boundary and record completeness in the economy
model. It records that one economy version carries both, because the record's
denomination is stable; that the manifest is not re-versioned, because no
founder-directed figure moves; that a sibling package is preferred to a
`Binding` here, on the condition ADR 0026 itself named for when that choice
inverts; that the manifest layer and the window grid are bound rather than
copied; that monotonicity moves to the writer of activation heights; that the
in-scope seat set has no upper bound, because a seat past its issuance span
still runs a node and may still win a reallocation; that an omitted and an
added seat are two codes because they have opposite economic effects; and that
the intrinsic record checks precede the run-history binding check so a code
means one thing. It accepts a research model contract, not a consensus
transition.

ADR 0030 rebinds the escrow payout model to economy version three. It records
that a third `Binding` is correct where the economy model earned a sibling
package, because economy version three revised the economy model's transitions
and not this model's, which is the same test ADR 0026 stated and ADR 0029
applied in the other direction; that containment is checked against every
predecessor rather than only the immediate one, because the three economy
labels are distinct strings and not a chain; that the scenario is held fixed
again so a rebinding defect stays distinguishable from a scenario difference;
and that the cap agreement is now derived across every registered binding
without rewriting the accepted version-two vectors. It accepts a compatibility
boundary, not a consensus transition.

ADR 0031 rebinds the economy scenario suite to economy version three. It records
that the activation heights are forced rather than chosen, because holding the
tick a shared window lets `cycle-boundary-v1` determine the rest; that one early
window reaches the founder-directed empty-winner rule with a complete population
rather than in a unit test, and that the path was kept rather than designed
away; that the totals cannot reveal it, so it is caught only by deriving the
unrewarded windows from two independent sides; that a peer seat is required
because the window check now precedes the binding check; and that scenarios 2
and 3 are re-proved version-independent rather than inherited. It accepts a
research scenario contract, not a consensus transition.

ADR 0032 settles the economy consensus transition surface and the M1
compatibility boundary. It records that the version-one transfer is factored
into a shared header, a kind-specific body, and a shared trailer rather than
replaced, so the kind-1 instance reproduces the accepted bytes exactly and the
version-one result numbers keep their meanings across all six kinds; that
reading the uptime record and the cycle window from state rather than from the
transaction makes ten of the economy model's result codes unrepresentable, and
that the removal is recorded as a total three-way partition so no check is lost
silently; that the performance winner set is committed at window finalisation
and carried by the exercise, because resolving it at evaluation is a
population-scale write and computing it lazily would break
`uptime-measurement-v1`'s retention bound; that a Founder Economy chain is a new
chain rather than a migration of the M1 devnet; that three genesis relaxations
are forced by the constitution's no-genesis-allocation rule, including a zero
fee, whose bootstrap consequence is recorded rather than closed; and that all
three authorization predicates are founder-reserved and none is filled, so kind
6 is specified and refused. It accepts an encoding and a compatibility boundary,
not an implementation.

ADR 0033 records the founder decisions of 2026-08-13 and 2026-08-14 on minting,
HUB verification, and referral entry. It records that minted value lands on the
seat's own spendable address with no separate withdrawal, that any recorded
manager address may act for a seat, that biometric verification on minting is an
option the founder switches on rather than a protocol requirement, that
accumulated unminted permissions are capped with the excess reallocating to the
day's best performers, that the unreferred pool pays the single best performer
with exact ties sharing equally, and that a referrer must be HUB verified. It
also records HUB — Human Uniqueness Biometric verification — as one ecosystem-wide
identity layer serving every participant class rather than a Founder Seat
feature, with its own direct-mint incentive. It supersedes `economy-transition-v2`
in four places and requires a version three; it edits no accepted artifact.

ADR 0034 settles the version-three encoding of that direction. It records that a
manager set is a family of presence-only entries and that the mint therefore
credits the signing manager's own account, because crediting the recorded
purchaser would leave the constitution's own remedy for a lost address able to
recover nothing; that the optional biometric on minting is a second transaction
kind rather than an optional field, which makes kinds 3 and 7 share a body length
and turns version two's dispatch-on-kind rule into the thing that saves it; that
the accumulation cap is measured in windows since the last collection rather than
in accrued cycles, because only the window form bounds the mint walk and that
bound is the cost ADR 0033 says the cap exists to close; that a capped seat is
excluded from the winner set, derived from the founder rule's own wording rather
than chosen; and that HUB verification enters consensus as one registry entry and
one transaction, with one-human-one-account deliberately unenforced because
enforcing it would decide what happens to a verified human who loses their key.
It also records five defects in version two that deriving version three exposed
— three that version three fixes by construction, one storage figure repaired in
place because it contradicts its own derivation rather than a rule, and one
recorded vector that states the opposite of what its own name asserts and is
left alone because a vector file is accepted evidence rather than prose.

ADR 0035 records the founder answers of 2026-08-14 to the four questions M3.8b
raised. Three confirm what version three encodes: a mint credits the address
that signed it, sixteen manager addresses per seat, and a capped seat excluded
from the winner set — the last restated more simply by the owner as one rule,
that a cycle a seat cannot collect because it is full **is** a cycle it failed,
so both consequences follow from the failed-cycle rules already written. The
fourth is new direction and supersedes version three in one place: HUB
verification survives the loss of any address and is the recovery layer for the
whole ecosystem, a verified person may add and remove their own addresses
through it, and Founder Seat addresses are the exception — permanent, never
removable, and added by HUB signing. Version three requires an existing manager's
signature to add one, so a founder holding no keys has no path; closing that is
an authorization change and therefore `economy-transition-v4`. Two questions must
be settled before that version can be written, and both are recorded as blocking
it.

ADR 0036 settles version four, once those two questions were answered the same
day. It records that a HUB registration holds the person's own public key, so
the ecosystem verifier signs registrations and nothing else — a stronger
containment story than any earlier version, because an unavailable verifier now
stops new people joining and stops no participant already inside; that a seat is
owned by a person rather than an address, so losing every address does not lose
the seat; that the constitution's 1,000-seat-per-human bound becomes enforceable
and is therefore enforced, which version three records outright that it cannot
do; that self-referral is now compared between people rather than between
accounts, closing a gap two addresses could walk through; that referral earnings
are keyed by identity, so a referrer who changes addresses keeps everything
accrued; and that removing an address unlinks an identity claim and moves no
value, because making a HUB signature able to move funds would be a far larger
authority than the direction grants. It also records four review items, the
sharpest being that adding a seat address now needs one factor where version
three needed two.

ADR 0037 records a defect in version four found by implementing it, and the
version-five correction. Kind 11 carries an account and a signature and nothing
else, while its rejection conditions and its message both require a HUB identity
hash the transaction never carries — and the sender is deliberately
unconstrained, so the chain cannot derive one either. **No conforming
implementation of kind 11 exists**, which disables exactly the recovery path the
founder direction was answered into the contract to provide. It records that a
byte-level cross-language check could not have caught it, because neither
implementation executes anything; that the correction reads the 32-byte field as
the identity and the added account as the sender, which keeps the body at 96
octets and closes a squatting hole the obvious repair leaves open; and that this
is a new version rather than a repair in place, because version four's own rule
forbids reinterpreting a version-four field and overriding that rule the day
after writing it is a worse precedent than the version costs.

ADR 0038 records how version five is evidenced, and the one thing about it that
is genuinely new. Version five changes one field's meaning, eight labels, and
four version fields, so its central claim is negative — everything else carries
over unchanged — and no derivation can demonstrate that a width did *not* move,
because a width that moved is simply derived and recorded at its new value. So
the model imports version four rather than restating it, the independent
derivation loads version four's accepted one rather than transcribing the same
documents a second time, and the whole vector file is read a second time against
`test-vectors/economy-transition-v4.txt`: every key that file records is
classified as carried, renamed, or revised, the classification must be total, a
carried key must hold version four's exact value, and a revised key must not.
It also records that version five is the first transition contract whose
evidence needs the accepted version-one account derivation, because it is the
first in which a signed message is built from the sender — the missing
derivation and the defect being the same fact seen from two sides.

ADR 0039 records a founder pivot that arrived as the answer to a narrow
question and rejected its premise. M3.9c closed by asking which of three
recovery flows the owner wanted for a person who had lost every address; the
answer is that the architecture underneath the question is wrong. **HUB
verification is mandatory for anyone who registers and for interacting with any
part of the ecosystem**, an address is an operational tool rather than an
identity root, recovery is direct between the owner and their own recorded
biometric data with no third party at any step, and biometric confirmation is
on by default for every financial transaction and every mint, with each person
free to set a minimum amount, set time windows, or turn it off entirely. The ADR
records why the previous architecture produced the dilemma at all — an address
could exist and hold value with no identity behind it, so the chain had to
reason about linking two separately real things — and that the C++ codec slice
is withdrawn rather than built against a contract already superseded. It leaves
three things undecided, of which one blocks the next contract version: how a
person who holds nothing pays for their first transaction.

ADR 0040, ADR 0041, and ADR 0042 complete the account architecture the
mandatory-HUB pivot began, and each was answered the same day it was raised.
ADR 0040 replaces addresses-as-identity with a verified identity holding as many
keyless asset escrows as the person wants, signers assigned to those escrows
separately and revocably, and the identity as the admin over both — which
settles recovery funding, because regaining an identity regains escrows that
already hold value. ADR 0041 closes the conflict that left open, by naming what
the permanent add-only seat-address rule was *for*: non-sellability. Tying the
seat to the HUB verified data serves that purpose better, so a Founder Seat has
no address at all and the rule loses its subject, along with the 16-manager
limit. ADR 0042 closes the last question — entry funding — from tokenomics that
already existed: the first 1,000,000 verified users receive 1.71 native units a
day for 731 days, the first day arriving as an entry airdrop at registration so
a brand-new account can transact. That rate is derived rather than chosen, and
the three founder-supplied figures reproduce the accepted channel cap to the
atomic unit.

ADR 0043 records the four answers that unblocked `economy-transition-v6`, and
they exist because the founder-decision gate **stopped** that slice rather than
clearing it — the second time it has, after M3.8a. Enumerating thirty-six
decisions before judging any showed that two items the constitution had listed
as unresolved since the pivot sit inside the contract rather than beside it.
Verification is the entry point and reaches the recipient, so a transfer to an
unregistered holding address is refused rather than creating one, and no account
exists that is not an escrow beneath a registered identity. The security
asymmetry that protected a Founder Seat's minting generalises to every
participant: relaxing a posture requires a biometric approval, tightening it
requires only a signer signature. A verified user's uncollected incentive is
never issued, because that channel is the one with no second destination. And a
signer key belongs to exactly one holding address, which is what keeps the
kind-1 transaction bytes identical for a fifth version — while answer one gives
those unchanged bytes a new rejection condition, so the byte identity is
preserved and the execution identity is not.

ADR 0044 records `economy-transition-v6` — the contract that encodes all of it —
and the decisions the direction did not make. The escrow identifier is derived
from the identity and a never-decreasing index rather than allocated, so a wallet
can compute it offline and a deleted escrow's identifier is never reissued. The
accepted version-one account derivation survives by changing what it names, from
an account to a signer, which is why the pivot is cheaper at the primitive layer
than ADR 0040 expected. The signature-scheme byte carries the second
authorization mode, with the key in the header and the identity hash in the body
specifically so admission still verifies a signature without reading state. The
nonce belongs to the escrow, which answers ADR 0040's two-signer question with
version one's own rule. Registration is fee-exempt against ADR 0042's stated
preference, because credit-before-fee closes the ecosystem to new members at user
1,000,001. And the verified-user cap is applied at the mint rather than at
assignment, because no per-window record for a million identities is affordable.

ADR 0045 records the version-six execution model and the three rules it had to
derive, because building the first thing that *runs* a version-six transition
reached three places where the accepted contract admits two readings. Version one
puts the debit-overflow test before the balance comparison and version six's
shared-envelope sentence appears to move it after, which would leave the balance
check undefined on its own input and make a frozen code unreachable that the
specification does not list as unreachable. The rule that a confirmation field
must be zero when no confirmation is required is placed at admission and named a
code the result space does not contain, and admission cannot read the stored
posture the predicate needs. And `NOTHING_TO_MINT`'s literal wording would let a
freshly activated seat's mint lower its own accumulation mark by two windows.
The fourth decision is where a cycle assignment lands inside a block, and it is
worth more than the other three together: written before the block's
transactions a founder's mint at the boundary collects the cycle, and written
after it succeeds, collects nothing, and forfeits that day permanently.

ADR 0046 records that the C++20 kernel's economy codec is now version six's and
that version four's is removed rather than kept beside it. The kernel had been
compiling exactly one economy contract and it was the one contract already known
to have no conforming implementation, because version four's kind 11 names an
identity the transaction never carries. Every Python model and vector file is
retained, because a model plus its vectors is the record of what the hosted
matrix verified; a codec is one implementation of a byte surface and records
nothing. The accepted version-one account derivation is now defined once and
shared by the version-one admission path and the version-six signer derivation,
rather than copied. Of the four rules ADR 0045 derived, a codec can reach one —
`NOTHING_TO_MINT` as the empty walk range — and it does; a mutation probe then
showed that nothing anywhere would have caught an implementation that refused an
unrequested confirmation field at admission, which is stricter than the contract
can be, so the test now requires such a transaction to be admitted.

ADRs 0047 through 0052 record the architecture pivot the owner directed on
2026-08-19, and it changes where the ecosystem runs rather than what it pays.
The ecosystem AI moves off company-operated infrastructure onto the Founder
Machines themselves and the company runs no backend of any kind (0047); HUB
verification becomes a local deterministic process supervised by a node-local
model, with the deterministic verdict separated from a non-deterministic
integrity monitor (0048); the per-channel carry is replaced by a recovery pool
and best-performer ranking becomes permanent infrastructure rather than an
artifact of the 731-cycle distribution (0049); months become real calendar
months read from a consensus block timestamp (0050); bridges run on Founder
Machines behind light clients and a machine quorum (0051); and the Founder
Machine gains a specification with a 512 GB unified-memory floor (0052). ADR
0053 then delivers `founder-economy-manifest-v3`, which renames issuance channel
9 to `mini_gamified_incentives` and changes nothing else.

ADR 0054 records `economy-transition-v7`, the contract that encodes the recovery
pool, and the four things ADR 0049 left a contract to settle. One entry carrying
five legs replaces ten carry entries, because the legs have five beneficiaries
and five caps and five of the ten were structurally always zero. The cycle
assignment record grows by what that cycle absorbed, because the pool's balance
at a window is a function of every earlier cycle and a mint must stay bounded.
The per-channel identity loses its third term and gains a backing identity that
names claimable and the pool, which is what turns "100% is assigned" into an
equality rather than a description. And the settlement reads the pool before it
writes it, so a cycle never pays itself its own dust. It also records that ADR
0049's premise about the winner set is wrong for the accepted model — every
in-scope seat is already ranked, in span or not — so version seven states and
guards that rule rather than rewriting a correct derivation on a premise that
could not be reproduced.

ADR 0055 records the version-seven execution model and the two rules it had to
derive. Version seven changes no transaction, so thirteen of the fourteen are
version six's own function objects rather than reimplementations, and a test
requires object identity so a copy that drifted in an unreached path would fail
rather than pass. The first derived rule is that a seat's collection mark and
its recorded referrer are read from the seat entry rather than from the uptime
measurement, because ADR 0054's claim that `claimable` is exact rests on the
accumulation cap being applied against the same mark the mint's walk uses, and a
measurement able to supply a different one could set an accrued bit in a window
that seat can no longer reach. The second is that `claimable` is the mint's own
walk run once per seat, so the identity that says nothing was stranded cannot
drift from what a mint actually pays. It also records a finding rather than a
choice: the assignment ordering ADR 0045 had to reject by argument is
unconstructible under version seven, because a boundary block whose mint runs
before the assignment leaves `outstanding` above `claimable + recovery_pool` and
the backing identity refuses the block whole. **One of its rejected alternatives
was corrected on 2026-08-20 and the record says so in place.** It declined to
re-record version six's execution scenarios on the ground that they are fixed by
512 accepted vectors over transactions version seven does not touch — right
about the transactions and wrong about their commitments, because those vectors
record version-six roots and version-six receipts and version seven re-versions
both. Ten of the fourteen kinds had no version-seven execution evidence, and
swapping two handlers in version seven's own dispatch table passed every vector
until the two scenarios that close the gap were added.

ADR 0056 records the version-seven state snapshot, which is the first artifact
that lets a version-seven state leave memory and the first dependency
requirement 13 was actually waiting for. The payload is the state root's own
inputs and nothing else, so the root cannot end up checking the snapshot against
itself, and `assigned_permissions` is re-derived from the assignment records
rather than encoded, because nothing in the root commits to it and the channel
identity is stated over exactly that figure. Its two findings are worth more than
the format. **The conservation gate is the only one an adversary cannot defeat**:
an edited state can have its root recomputed and its digest resealed, so both
root gates pass by construction, and only an identity that must still hold
refuses it — which is why the permission count must be derived rather than read.
And the kernel's cycle-assignment decoder does not require the bitmap pad bits to
be clear, while the mint's own walk would read a set pad bit as an accrued seat;
it is unreachable on-chain and reachable through a file, the accepted
specification fixes the bitmap width without stating the rule, so the snapshot
refuses it and a later transition version should state it outright.

ADR 0057 records the version-seven owning store, which is what makes a
version-seven state survive the process that built it. **The head is one
snapshot payload rather than a row per entry**, because the snapshot is already
the canonical projection of everything a state root commits to and a second
row-shaped projection would be a second opinion about what a state *is*; what
the schema keeps in its own columns is only what a reopen must agree on before
it trusts the payload. The connection, locking, journal, and path-stability
contract is version one's, reused unchanged, since ADR 0007 settles all of it
against the filesystem and SQLite rather than against a ledger. Its evidence is
the question ADR 0056 could not ask: the `carried` scenario's four contiguous
blocks are replayed through a database **closed and reopened between each
pair**, and every block must reproduce its recorded `block_id` and
`resulting_state_root`. Two findings are worth more than the schema. **The
integrity check is what keeps every later comparison from lying about why an
open failed** — with it removed, a database whose pages were overwritten reports
`genesis_mismatch`, which tells an operator they opened the wrong chain when in
fact their disk is failing, and that is why it runs first. And two of the ten
mutation probes found tests that did not exist rather than tests that were
wrong: nothing exercised a block the *kernel* rejects whole, so a store that
committed a rejected block passed the whole suite. Checking the stored
transaction root also found the store's one duplicated derivation — it rebuilt a
root the block header already commits to — and `execute_block` now carries that
root out of the block, which changes no encoding, no state, and no accepted
vector. **It was amended in place on 2026-09-01** when the two things it recorded
as owed were delivered, and the contract turned out narrower than its first text
implied: everything before the commit rolls back and is an ordinary refusal that
leaves the store usable, only the commit can leave a head the process cannot
name, and there the store poisons itself and reads the file again — recovering to
the block's root or its predecessor's and never to anything between, which is the
property requirement 13 names when it says "through restart *and recovery*".

ADR 0058 records the version-seven application layer, which is the first piece
that turns the store into something a consensus engine can drive. **Its whole
safety argument is that `finalize_block` writes nothing.** It copies the durable
head, executes the block against the copy, and stages the root it produced;
`commit` then replays the same block through the store and requires the store to
reproduce exactly what was staged, which is what makes the root a node told the
network and the root it persisted one fact rather than two. The candidate *state*
is deliberately not kept — only its root, because the root commits to every entry
and keeping the state would invite a later change to commit it instead of
replaying the block. Version seven's `process_proposal` also executes, where
version one's only checks bounds, because `execute_block` rejects whole blocks
for reasons version one's kernel cannot and meeting one at `finalize_block` halts
the node permanently; the ADR records honestly that no constructible input
reaches that refusal today. **Two things it owes are worth reading before the
next slice**: the uptime schedule is `nullptr`, so a chain driven through this
layer writes no cycle assignment and accrues nothing to any seat, and nothing yet
speaks to CometBFT.

ADR 0059 records the version-seven transport, and its decision is mostly what it
declines to add. **The frame format is version one's, reused unchanged**, because
the header and all five request payloads carry no ledger-version meaning — a
height, a transaction list, a byte budget — so a second wire would differ in
nothing but its name while doubling the places a framing rule can be wrong. The
same argument makes the socket's connection loop one function over a dispatcher,
and the `V1` in `UnixSocketServerV1` the *wire's* version rather than the
ledger's. What is genuinely version-specific is the response half: a finalized
block carries a block identifier version one's does not, and its receipts are
version seven's fifty-six octets. **Every response is validated on the way out
rather than merely serialised** — a declared code that disagrees with the receipt
beside it is refused rather than written — because the adapter on the other side
has no ledger, no kernel, and no vectors, and cannot tell a wrong answer from a
right one. Two of its four probes found missing tests: one because the suite only
ever sent proposals that should be accepted, and one because an assertion inside
the socket test aborted the process instead of reporting.

ADR 0060 records the version-seven node process and the decoder that made it
possible. **`decode_genesis` is defined as `encode_genesis`'s inverse and checks
itself against that claim**: it reads the 110 canonical octets, re-encodes what
it read, and returns a genesis only when the result equals the input octet for
octet. The validity rule — a nonzero supply limit, a zero total supply, a zero
fee pool, no accounts — is therefore stated exactly once, in the encoder, and the
round trip catches more than a restatement would, including a field read at the
wrong offset. That is not hypothetical: `total_supply` is encoded *before*
`fixed_transfer_fee` while the struct declares them the other way round. The
binary is version one's with three substitutions, opens before it creates so that
a restart is the ordinary case, and is checked as a **process** — started,
connected to, shut down — against the recorded chain identity and a genesis root
read out of a recorded block header, since a header commits to its previous state
root and at height 1 that is the genesis root.

ADR 0061 records the version-seven ABCI adapter, and its one real question was
not encoding. **`ApplicationV7` refuses a `finalize_block` at any height that is
not its current plus one — including one it has already committed — and that
refusal is terminal**, so ADR 0058 owed this slice an answer about what the
adapter does when a consensus engine replays a block. The answer turned out to
be a fact about the pinned engine: CometBFT v0.39.4 replays exactly that case
against a **mock** application built from its own saved response, saying in as
many words that it will not call `Commit` twice for one block on the real app,
and every other branch sends only `current + 1`. So the adapter reconciles
nothing — and inventing a reconciliation would have been worse than useless,
since answering a repeat honestly means reproducing receipts the application no
longer holds and the store never recorded. What it adds is a **guard**: a
finalize at an already-committed height is refused before it is forwarded, using
a height taken only from the application's own answers, so it can never refuse a
legitimate block. On the Go side the client is version one's client and one
different answer, the two finalized-block shapes refuse each other so a client
dialled at the wrong version fails closed, and the block identifier — which ABCI
has no field for — is emitted as an indexed block event rather than decoded and
discarded, because a value that crosses a process boundary and is then thrown
away is the one a later simplification deletes.

ADR 0062 records the version-seven chain fixture, and the decision came out of a
finding rather than a preference. **Every recorded version-seven transaction is
signed with a stand-in** — an eight-octet counter padded to 64 octets, recorded
in an oracle that verifies by exact-match lookup — which is the right decision
for a contract fixture, because it makes every message-binding claim testable
without the model implementing cryptography. It also means nothing recorded
could ever be broadcast to a node: `protocol-application-v7` opens its store
with `ed25519_verifier()` and would refuse all of it as `invalid_signature`. So
the plan of emitting the recorded blocks' raw octets into a vector file was
abandoned for a second fixture that **signs for real**, in the shape version
one's already has. The model needed no change, because `execute_block` already
takes the signature oracle as an argument. **One transaction per block is a
requirement rather than a simplification**: a state root commits to the whole
block, and broadcasting through a mempool will not put a chosen set into one
block in a chosen order. The run's claim is agreement between two
implementations — the model's root, the binary's genesis identity, and the
node's executed root — never a value against itself, and the third block is
committed by a process that did not execute the first two, so its root comes
from a state read back out of SQLite.

ADR 0063 records the version-eight uptime carrier, and the finding that shaped
it is that **the obvious three kinds are two**. A duty report cannot be a
transaction: `uptime-measurement-v1` states that a report "cannot be forged by
the seat it concerns" because the chain produces it, and whoever signs one is
asserting something no other node can reproduce — a proposer's opinion, which is
a consensus fork with extra steps. The honest mechanism is ADR 0050's attested
claim, and it cannot be produced today because the active-set protocol that
assigns duties does not exist; the accepted specification already says an empty
assignment is satisfied vacuously, so version eight encodes no duty report at
all, on version seven's own precedent of declining to encode what no transition
can set. The other decisions follow from storage and from authority. A challenge
is **materialised into state at the height it is issued**, so the beacon is read
once and never retained, `CHALLENGE_NOT_ISSUED` becomes a lookup, and the
model's per-slot counters disappear — clearing a bit at expiry is exactly
equivalent to the slot-close sweep, because selection excludes the final twenty
heights of every slot. A dispute is **relayed** rather than signed by its
authority's own account, which is kind 10's pattern and the right one under ADR
0047, where a deciding machine issues a signed bounded decision that someone
submits; giving the ecosystem AI a nonce sequence, a balance, and a fee
obligation is what the alternative would have cost. `RESPONSE_INVALID` is
deliberately not declared, because the answer predicate is founder-reserved and
no path could produce the code. **One value was defaulted and asked rather than
settled, and the asking changed it**: a response would have charged the
inherited fixed fee, about twenty-four fees per cycle for a machine proving the
uptime it is paid for, and
the owner answered it on 2026-09-02 and the response is **fee-exempt**, because
whether a mandatory audit should cost an operator anything is a question about
what a participant must do in order to be paid. The exemption is bounded by the
chain rather than by a fee: a response is accepted at most once per challenge
the chain itself issued.

## Engineering

- `engineering/continuation.md`: the cross-session `proceed` protocol.
- `engineering/standards.md`: language, modularity, determinism, and dependency
  standards.
- `engineering/build-toolchain.md`: reproducible build, test, dependency, and
  cache commands.
- `engineering/verification.md`: required evidence and quality gates.
- `engineering/git-workflow.md`: issues, branches, atomic commits, PRs, and
  authorship.

## Specifications

Canonical protocol specifications live in `specifications/` and must define
consensus-critical behavior before implementation. An accepted version is
immutable; compatible changes require a new version.

- `specifications/protocol-primitives-v1.md`: canonical version-one encoding,
  cryptography, identifiers, addresses, transactions, and commitments.
- `specifications/ledger-transition-v1.md`: M1 genesis, native transfer, fee,
  receipt, and ordered block semantics.
- `specifications/consensus-application-v1.md`: adapter-neutral ordering
  lifecycle, application results, durable commit, restart, and local framing.
- `specifications/founder-economy-manifest-v1.md`: exact eight-decimal
  denomination, ten issuance-channel caps, 731-cycle derivation,
  permission-liability semantics, unresolved-policy placeholders, and fixed
  M2 manifest digest; it is not a consensus transition.
- `specifications/founder-economy-manifest-v2.md`: the same denomination under
  the 2026-08-07 founder direction — the 56,993,950,100 maximum, the referral
  channel doubled and moved to direct-mint, both referral destinations, one
  remaining research placeholder, and a fixed M3 manifest digest; it supersedes
  version one as direction, retains it as evidence, and is not a consensus
  transition.
- `specifications/founder-economy-simulator-v1.md`: strict manifest loading,
  the five Founder Economy transitions, bound research inputs, journal
  conservation, digest labels, and vector obligations for the independent
  Python model; it is not a consensus transition.
- `specifications/founder-economy-simulator-v2.md`: the same model under the
  2026-08-07 direction — the cycle uptime record carrying measurements only, the
  derived activity verdict and winner set, the unconditional direct-mint
  referral with its two destinations, and the performance carry with its
  conservation identity; it is not a consensus transition.
- `specifications/founder-economy-simulator-v3.md`: the same accounting with the
  cycle boundary and record completeness enforced — an `activation_height` on
  the seat record, the window check applied inside base permission evaluation,
  and a record required to cover exactly its window's in-scope seat set; it
  binds the accepted v2 manifest and the accepted window grid rather than
  restating either, and is not a consensus transition.
- `specifications/founder-seat-schedule-v1.md`: integer USD denomination, the
  100,000-seat capacity, the block price schedule, the per-principal ownership
  bound, and the seat purchase transition; it is not a consensus transition.
- `specifications/revenue-routing-v1.md`: the 45/45/10 commercial split, the
  22.5/22.5 creator case, the proved integer remainder rule, separate 100%
  transaction-fee routing, and per-cycle Founder distribution with a carry; it
  is not a consensus transition.
- `specifications/escrow-payout-v1.md`: the three founder-directed escrows,
  bounded escrow-scoped spending capabilities, custody conservation, and the
  ordered payout rejection conditions; it is not a consensus transition.
- `specifications/escrow-payout-v2.md`: the same transitions binding
  `founder-economy-simulator-v2`, differing in exactly five domain labels and
  the bound economy state label, with the cross-version compatibility boundary
  and the unchanged escrow caps; it is not a consensus transition.
- `specifications/escrow-payout-v3.md`: the same transitions binding
  `founder-economy-simulator-v3`, again differing in exactly five domain labels
  and the bound economy state label, with containment proved against both
  earlier economy versions rather than only the immediate one; it is not a
  consensus transition.
- `specifications/economy-scenario-suite-v1.md`: the multi-year and adversarial
  scenarios the four accepted M2 models must survive, their restart-equivalence
  method, and the seeded property tests; it defines no model or transition.
- `specifications/economy-scenario-suite-v2.md`: the same four scenarios with
  the population run rebound to `founder-economy-simulator-v2` and the escrow
  drain to `escrow-payout-v2`, supplying a cycle uptime record instead of a
  supplied activity verdict and performance recipient; it defines no model or
  transition.
- `specifications/economy-scenario-suite-v3.md`: the same four scenarios rebound
  to `founder-economy-simulator-v3` and `escrow-payout-v3`, where the enforced
  schedule forces the activation heights, a record covers exactly its window's
  in-scope seat set, and one early window reaches the founder-directed
  empty-winner rule at population scale; it defines no model or transition.
- `specifications/cycle-boundary-v1.md`: the 28,800-block window grid a cycle is
  cut from, the mapping from a seat's activation height to its 731-window
  issuance span, the ordered conditions of the window check, and the exact block
  equivalents of the founder-directed activity threshold and grace allowance; it
  defines a schedule and measures nothing.
- `specifications/uptime-measurement-v1.md`: the 24-slot grid a window is
  subdivided into, the two evidence sources, challenge selection from an
  unpredictable beacon and its response deadline, the conjunctive slot credit
  rule, the bounded Ecosystem AI dispute window that finalises by expiry, and
  record completeness at the producing end; it measures and settles no value.
- `specifications/economy-transition-v2.md`: the canonical economy consensus
  surface — the shared transaction envelope and its five new kinds, the economy
  state key space, version-two genesis, chain identity, and state root, the
  56-byte receipt, the flat numeric result-code space, the reallocation
  commitment, and the exact compatibility boundary against accepted M1
  transaction bytes, state, and roots. It is a contract for an implementation
  that does not yet exist, and three named authorization predicates are
  deliberately left undefined.
- `specifications/economy-transition-v3.md`: the same surface revised by the
  founder direction of 2026-08-14 — a per-seat manager set that may act for the
  seat and receives what it mints, an optional per-seat biometric on minting
  whose switch is asymmetric, a thirty-window accumulation cap whose excess
  reallocates to the cycle's best performers, and a HUB-verified referrer. It
  adds four transaction kinds, three state entry kinds, and three result codes,
  and keeps the kind-1 byte identity and every version-two result number. One
  authorization predicate remains deliberately undefined, and a second — who may
  add a seat address — was superseded the same day by the HUB recovery direction
  ADR 0035 records, so requirement 10's C++ kernel targets a version four rather
  than this one.
- `specifications/economy-transition-v4.md`: the same surface with HUB
  verification as the root of identity — a registration holding the person's own
  public key, an address set the person manages, a seat owned by a person rather
  than an address, HUB signing as what adds a seat address, referral earnings
  keyed by identity, and the constitution's 1,000-seat-per-human bound enforced
  for the first time. The ecosystem verifier signs registrations and nothing
  else. It adds two transaction kinds and two result codes, keeps the kind-1 byte
  identity and every version-three result number, imports version three's
  settlement unchanged. One authorization predicate remains deliberately
  undefined, and its kind 11 has no conforming implementation, which
  `economy-transition-v5.md` corrects.
- `specifications/economy-transition-v5.md`: version four with one field's
  meaning corrected — kind 11's 32-byte field is the HUB identity hash and the
  account being linked is the sender — because version four's kind 11 names an
  identity it does not carry. Everything else in version four is incorporated by
  reference. Its model and vectors are recorded; its C++ implementation is not,
  and the founder direction of 2026-08-15 superseded it before one was written.
- `specifications/economy-transition-v6.md`: the account architecture the
  mandatory-verification pivot requires. A verified identity is the root, an
  escrow with no key of its own is where value sits, and a revocable signer
  assigned to exactly one escrow is who may act on it. Registration creates all
  three atomically, is fee-exempt, and pays the entry airdrop; a Founder Seat has
  no address and a mint names a destination escrow the chain checks; a transfer
  refuses an unregistered recipient, which withdraws `ledger-transition-v1`'s
  recipient-creating transfer and makes "every account is an escrow" a structural
  invariant. The signature-scheme byte carries a second authorization mode so
  that identity administration works with no key at all.
  `simulation/economy_transition_v6/` both encodes and executes it. **Its C++
  kernel was replaced by version seven's**, under ADR 0046's rule that the
  kernel compiles exactly one economy contract; its Python model and both
  accepted vector files remain in place, passing, and unedited.
- `specifications/economy-transition-v7.md`: version six with the per-channel
  carry deleted from state and replaced by a recovery pool, so the node
  distribution assigns 100% of the permissions the manifest promises. A
  zero-winner cycle contributes its whole base permission and an indivisible
  remainder contributes its dust; the earliest subsequent cycle with any winner
  takes the pool entire, on top of its own reallocation. Entry kind 7 is retired
  permanently, one entry carrying five legs replaces its ten, the cycle
  assignment record grows by what that cycle absorbed, and the per-channel
  identity loses its third term and gains a backing identity that names
  claimable and the pool — which is the statement that nothing is stranded. It
  binds `founder-economy-manifest-v3`. `simulation/economy_transition_v7/` now
  both encodes and executes it, and
  `test-vectors/economy-transition-v7-execution.txt` records a pool filled by an
  unwon cycle, absorbed whole by the next, and minted — ending with outstanding
  and the pool both at zero — over five scenarios that execute **all fourteen**
  transaction kinds, where version six's execution file reaches eleven. **It is
  the contract requirement 10's C++ kernel implements**: `src/v7/` and
  `include/protocol/v7/` hold the byte surface, the settlement, all fourteen
  transitions, and the assignment prologue, and reproduce both version-seven
  vector files.
- `specifications/economy-transition-v8.md`: version seven with an on-chain
  carrier for `uptime-measurement-v1`, so a cycle assignment is derived from
  evidence the chain recorded rather than from a schedule a caller supplies.
  `execute_block` loses its `UptimeSchedule*` parameter; block execution gains
  an issue step that writes one open challenge entry per selected in-scope seat
  against the previous state root, and an expiry step that clears a slot bit
  twenty heights later for a challenge nobody answered. A seat window record is
  sparse — absent means fully credited — so a healthy machine writes nothing.
  Kind 20 is a challenge response authorized by the seat's owning identity with
  no HUB signature; kind 21 is a dispute any signer may relay, carrying the
  dispute authority's detached signature on kind 10's pattern, and genesis gains
  a `dispute_authority_key` separate from the verifier key. Twelve result codes
  are added and the space becomes 45. **Two limits are stated rather than
  papered over**: the duty layer is vacuous because no active-set protocol
  assigns duties, and the answer predicate is the weakest one available because
  a challenge's content is founder-reserved, so version eight measures liveness
  of a responder rather than possession of a resource.
  `simulation/economy_transition_v8/` executes the codec, both transitions, the
  expiry step, and the schedule derivation, and
  `test-vectors/economy-transition-v8.txt` records 177 vectors over them. Its
  load-bearing one is settled by version *seven's* accepted model: a schedule
  derived from state reproduces a version-seven assignment record exactly, which
  is how "the carrier changed no settlement" becomes evidence rather than a
  claim version eight makes about itself. **A challenge response is fee-exempt**
  on the founder answer of 2026-09-02: answering a mandatory audit costs an
  operator nothing. It carries a zero fee limit, refused at admission rather
  than ignored at execution, and unlike the registration it keeps its nonce,
  because a response has an escrow and a nonce sequence and a registration has
  neither. The relayed dispute is not exempt.
- `specifications/native-economy-simulation-v1.md`: versioned integer-only
  accounting, authority, event, trace, and metric contract for the independent
  M2 research simulator; it is not a consensus transition.
- `specifications/participation-simulation-v1.md`: validator and resource-node
  lifecycle, bounded verifier-result, entitlement, and native-claim funding
  contract for M2 research.
- `specifications/authority-simulation-v1.md`: capability-scoped
  distinct-member thresholds, action results, rotation, containment, recovery,
  and shared simulator adapters for M2 research.
- `specifications/economic-stress-study-v1.md`: deterministic three-level
  orthogonal parameter screening across the accepted M2 simulators.
- `specifications/economic-envelope-study-v1.md`: exact high-resolution
  reward-funding and within-role concentration boundaries around the screened
  M2 survivor families.
- `specifications/reward-distribution-study-v1.md`: deterministic proportional,
  participant-cap, and principal-cap mechanism comparison contract.
- `specifications/admission-cost-study-v1.md`: deterministic hidden-principal
  work split, integer utility, operating-cost, refundable-bond capital-time,
  and churn study contract.
- `specifications/minimum-entitlement-study-v1.md`: deterministic zero-floor,
  per-participant, and work-proportional reserve comparison contract.

The corresponding executable research tools and reviewed fixtures live in
`../simulation/native_economy/`, `../simulation/participation/`,
`../simulation/authority/`, `../simulation/economic_stress/`, and
`../simulation/reward_distribution/`, `../simulation/admission_cost/`, and
`../simulation/minimum_entitlement/`.

The fixed Founder Economy manifest and derivation vectors live in
`../test-vectors/founder-economy-manifest-v1.json`,
`../test-vectors/founder-economy-manifest-v1.txt`, and
`../test-vectors/founder-economy-simulator-v1.txt`. The independent simulator
that consumes them is `../simulation/founder_economy/`, and
`../tools/founder-economy-vectors/verify.py` derives every recorded value from
the loaded manifest and a live run.

The revised contract is `../test-vectors/founder-economy-manifest-v2.json` with
vectors in `../test-vectors/founder-economy-manifest-v2.txt`. Its strict loader
is `../simulation/founder_economy_v2/`, and
`../tools/founder-economy-v2-vectors/verify.py` derives every recorded value
from the loaded manifest and from `expected.py`, which imports nothing from
`../simulation/` and restates the Founder Constitution's allocation tables by
hand. Every recorded failure code is produced by a live loader run over a
mutated manifest. No revised model exists yet.

The Founder Seat sale model is `../simulation/founder_seats/` with vectors in
`../test-vectors/founder-seat-schedule-v1.txt`.
`../tools/founder-seat-vectors/verify.py` rederives the whole schedule by
walking the constitutional rule and requires the walk, the model, and the
recorded file to agree.

The revenue and transaction-fee routing model is
`../simulation/revenue_routing/` with vectors in
`../test-vectors/revenue-routing-v1.txt`.
`../tools/revenue-routing-vectors/verify.py` replays the whole scenario against
an independent implementation in `walk.py` that uses the naive share form, and
requires that replay, the model, and the recorded file to agree.

The escrow payout model is `../simulation/escrow_payout/` with vectors in
`../test-vectors/escrow-payout-v1.txt` and `../test-vectors/escrow-payout-v2.txt`.
`../tools/escrow-payout-vectors/verify.py` replays the whole scenario against an
independent implementation in `walk.py` that carries the escrow caps as
constitutional literals and recomputes the founder-economy state digest with its
own helper. It additionally runs the founder-economy simulator of the selected
version on that model's accepted fixture and requires the escrow fixture's
opening custody to be bound to that run, which is provenance the model itself
cannot check. `--version` selects the accepted contract; version one binds
`founder-economy-simulator-v1` and version two binds
`founder-economy-simulator-v2`, and the v2 vectors additionally derive that no
version-one economy state can satisfy a version-two bind.

The multi-year and adversarial scenarios over all four models are
`../simulation/scenarios/` with vectors in
`../test-vectors/economy-scenario-suite-v1.txt`,
`../test-vectors/economy-scenario-suite-v2.txt`, and
`../test-vectors/economy-scenario-suite-v3.txt`. They add no model, transition,
or canonical label; every event parses under an accepted model's schema.
`--version` selects the suite. Version two rebinds the population run to
`founder-economy-simulator-v2` and the escrow drain to `escrow-payout-v2`, and
supplies a cycle uptime record from which the model derives the activity verdict
and the winner set. Version three rebinds both to the enforced schedule, so each
seat carries the activation height its windows are derived from and each record
covers exactly its window's in-scope set. Scenarios 2 and 3 record identical
values under all three versions, because the Founder Seat sale and revenue
routing models carry no supply or channel figure.
`../tools/scenario-suite-vectors/verify.py` runs all four scenarios and requires
each recorded total to match both the live run and a closed-form derivation from
Founder Constitution literals that imports nothing from `../simulation/`.

The cycle boundary model is `../simulation/cycle_boundary/` with vectors in
`../test-vectors/cycle-boundary-v1.txt`.
`../tools/cycle-boundary-vectors/verify.py` derives every recorded value twice,
once from a live model run and once from an `expected.py` that imports nothing
from `../simulation/` and restates the Founder Constitution's 24, 18, and 6
hours and the pinned M1 commit interval by hand. It holds a seat activation
table and answers whether a window is the window for a seat's cycle; it measures
no uptime and is not bound by any economy model yet.

Shared deterministic primitives used by these models live in
`../simulation/common/`.
