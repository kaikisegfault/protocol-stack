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
- `architecture/local-ai-authority.md`: future company-hosted logical AI
  authority, capability containment, and delegation stages.

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
  reference. It is the contract requirement 10's C++ kernel implements. Its
  model, vectors, and implementation are not yet recorded.
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
