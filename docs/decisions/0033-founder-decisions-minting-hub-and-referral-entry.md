# ADR 0033: Founder decisions on minting, HUB verification, and referral entry

- Status: Accepted
- Date: 2026-08-14

## Context

`economy-transition-v2` and [ADR 0032](0032-economy-consensus-transition-and-compatibility.md)
were accepted on 2026-08-13 and merged the same day. Their acceptance rested on
founder answers given during that slice: a seat is purchased and activated under
an off-chain biometric verifier signature, the chain assigns mint permissions
daily by itself, a mint takes everything, and referral is a separate pool.

Two questions remained that the encoding could not answer for itself, and one
concern the specification recorded rather than resolved:

- where minted value lands — a spendable balance or a holding place requiring a
  separate withdrawal;
- how the unreferred performance pool's monthly payout is divided;
- what stops a referrer address from being mistyped, which would strand that
  referrer's whole 731-cycle benefit at an address nobody controls; and
- that a mint after a long wait walks every cycle since the last one, so the
  work in a single transaction grows with how long a founder waits.

The owner answered all four on 2026-08-14 and, in answering, supplied
direction that reaches beyond this milestone.

## Decision

### Minted value lands on the seat's own address

A mint credits the founder's ordinary spendable account. There is no separate
withdrawal step and no second balance type. The founder signs from the seat's
original purchased address **or from an additional manager address added
later**, and can spend, transfer, or bridge the value immediately with an
ordinary wallet signature.

This replaces `economy-transition-v2`'s rule that only the recorded purchaser
account may act for a seat. Manager addresses are a recorded set, and any member
of it may mint.

**Biometric verification on minting is an option the founder switches on**, not
a protocol requirement. Off by default, a mint needs only the address signature;
switched on, it needs the address signature and a fresh biometric approval. The
constitution's containment argument is preserved either way, because a founder
who has not switched it on is never blocked by verifier availability, and one
who has has chosen that trade deliberately.

**The switch is asymmetric, and that asymmetry is the whole protection.**
Turning it on requires only the address signature. Turning it **off** requires a
biometric approval. A stolen wallet key can therefore neither mint against a
protected seat nor remove the protection first, which is exactly the attack the
option exists to defeat; a symmetric switch would have protected against
nothing.

### Accumulated mint permissions are capped, and the excess is reallocated

A seat may accumulate at most a bounded number of unminted cycles — the owner
named roughly thirty days, and the exact figure is delegated as engineering.
Once a seat is at the cap, **further permissions are not added to it even while
its node continues to meet the requirement**; they go to that cycle's best
performers instead, by the same path a failed cycle takes.

**The whole permission moves, not only the Founder portion.** The escrows and
the System Creator receive their legs from the winner's mint, exactly as they do
for a failed cycle. That is one rule rather than two: a capped cycle and a failed
cycle are handled identically, the escrows never lose value because an operator
was slow to press a button, and the only party that loses anything is the seat
that did not collect.

The same rule applies to **referral earnings**. A referrer who does not collect
within the window forfeits the excess, and the forfeited value stays inside the
`founder_referral` channel and routes to the **unreferred performance pool**,
which the constitution already defines as that channel's second destination and
already pays to the month's best performer. Routing it there rather than into
the daily node pool is a mechanism choice with one defensible answer: every
issued unit stays attributed to exactly one channel forever, which the accepted
manifest requires, and the pool is a destination that already exists rather than
a new path.

The rule is founder-directed and its purpose is stated: Founder Seats should be
active, and pressing the button once a month is a reasonable expectation of an
active operator.

**This is not a monetary penalty and does not contradict the constitution's
no-slashing rule.** An unminted permission's units do not exist and are not
circulating; the constitution says so directly and already accepts that a failed
cycle's portion moves to other seats and "the original inactive seat cannot
recover that benefit later". Forfeiting an unclaimed entitlement is the same
class of event. Nothing already owned is burned, seized, or reduced.

It also bounds a cost `economy-transition-v2` recorded and could not close. That
specification notes that a mint walks every cycle since the last one, so the
work in a single transaction grows with the wait. The cap turns that growth into
a constant.

### The unreferred pool pays the single best performer, and exact ties share

At the end of a monthly cycle the accumulated unreferred pool is assigned to the
Founder Seat with the best performance over that month. If several seats are at
**exactly** the same top figure — whatever that figure is, whether a perfect
month or 95% — they share it equally.

The rule is deliberately "one winner, unless there is an exact tie for first",
not "a top group". It is the same shape as the daily failed-cycle reallocation,
so the economy has one ranking rule rather than two.

### Referrers must be HUB verified

A referrer must be a **HUB-verified** account: Human Uniqueness Biometric
verification. This is mandatory, and it resolves the stranded-value problem at
its root rather than by validating an address format — a HUB-verified account
exists, is reachable, and belongs to a distinct human.

It also settles a question the Founder Constitution listed as open. That
document asks "whether a referrer must itself hold a Founder Seat"; the answer
is no, and the requirement is HUB verification instead. Holding a seat is
neither required nor relevant.

The selection experience is decided at the interface rather than in consensus. A
buyer chooses a referrer from a search over usernames, identifiers, or
addresses, with completion suggestions, rather than typing an address freehand.
A referrer may also share a purchase link that pre-selects them; **a purchase
opened through such a link cannot have its referrer changed, removed, or
replaced**, and manual selection is available only when the raw purchase page is
opened directly. None of that is a consensus rule; what consensus enforces is
that the named referrer is HUB verified.

### HUB verification is a foundational ecosystem layer

This is the direction that reaches furthest beyond the current milestone, and it
is recorded here because it changes what several later milestones must build.

HUB verification is **one system, available at every point in the ecosystem**,
not a founder-seat feature. It must serve any participant who registers —
Founder Seat holders, project and product creators, ordinary users, and
developers — as a single source of truth the company can switch on at any place
it judges reasonable.

Each verification produces a **signature unique to that person**, derived from
their personal secret, usable across ecosystem and blockchain operations. The
owner was explicit that the cryptographic construction — what is hashed, what is
signed, how uniqueness is represented — is engineering work and is delegated.
What is founder-directed is the shape: one identity layer, one source of truth,
switchable per integration point, serving every participant class.

**HUB-verified users earn from a direct-mint channel.** The accepted manifest
already carries `hub_verified_user_incentives` at 1,250,010,000 display units,
and its eligibility was listed among the constitution's "explicitly unresolved
founder details". That eligibility is now decided: being HUB verified. The
*rate* — how much a verified human receives, once or recurring — remains open.

The reason given is that biometric verification is becoming an essential
identity and security primitive, so the ecosystem should hold it at its most
foundational level rather than bolting it onto one feature.

### The owner specifies user-facing logic; Claude specifies the mechanism

The owner stated the division explicitly and it is recorded because it governs
how future questions should be asked and answered. They decide what a
participant experiences — that one press mints everything accumulated within the
cap, that biometric on minting is optional, that a referrer must be verified.
The technical layer beneath — hashes, signature schemes, encodings, storage
shapes — is Claude's.

Questions to the owner should therefore be phrased end-to-end from the
participant's side, in ordinary language. Internal model vocabulary is not a
useful question: the owner pushed back on "evaluate", "exercise", and "accrue"
during this slice and asked for plainer wording, and the plainer question got a
better answer.

## Consequences

**`economy-transition-v2` is superseded in four places and needs a version
three.** It is not edited: it is the accepted record of what was verified on
2026-08-13, its 238 vectors and their digests are that evidence, and the
repository's rule — applied for `founder-economy-manifest-v2`,
`escrow-payout-v2` and `v3`, and `founder-economy-simulator-v3` — is that a
changed transition is a new version rather than an edit.

The four changes are:

| | v2 | v3 |
| --- | --- | --- |
| Who may act for a seat | the recorded purchaser only | any recorded manager address |
| Biometric on minting | never | optional, per seat |
| Permission accumulation | unbounded | capped, excess reallocated |
| Referrer | any 32-byte account | must be HUB verified |

Version three also gains the state a HUB registry needs, a per-seat manager set,
a per-seat biometric-on-mint flag, and an unminted-cycle count. The envelope
factoring, the kind-1 byte identity, the compatibility boundary, the receipt,
the trees, and the roots are unaffected.

**Requirement 10 is unblocked and its scope moved.** The C++ implementation must
target version three rather than version two, so the encoding slice comes first.

**The three questions this decision raised were answered the same day** and are
recorded above rather than left open: the whole permission moves on a capped
cycle, disabling biometric-on-mint requires a biometric approval, and the cap
applies to referral earnings as well.

The third was answered against the recommendation offered. The case for
exempting referrers was that the cap exists to keep Founder Nodes running and a
referrer runs no node. The owner chose one uniform rule instead, and the
consequence is recorded plainly rather than argued: a referrer who does not
collect within the window forfeits value for inactivity that was never asked of
them. What the choice buys is a single collect-or-lose rule across the whole
economy, no abandoned account holding value indefinitely, and one bounded
accumulation shape for every participant rather than two.

**Two constitutional entries move.** Referral-channel eligibility for referrers
is decided, and `hub_verified_user_incentives` eligibility is decided while its
rate stays open. Both are updated in
[`founder-constitution.md`](../project/founder-constitution.md).

**HUB verification becomes a cross-milestone dependency.** It is currently
specified nowhere. M4 is where the identity layer is built, and the direction
here widens that milestone from a founder-seat biometric verifier to an
ecosystem identity service with a per-participant-class incentive attached. The
threat model, unlinkability, retention, and independent review requirements the
constitution already records apply to the widened scope, not the narrow one.

## Compatibility and independent review

No accepted artifact changes. `economy-transition-v2`, its vectors, its model,
and every earlier contract remain in place, passing, and unedited.

Three claims here need review before value depends on them.

**That the accumulation cap is not a penalty path.** The argument is that an
unminted permission's units do not exist, which the constitution states and
which its own failed-cycle rule already relies on. A reviewer should confirm
that the two cases are genuinely the same class, because the cap differs in one
respect: a seat losing a cycle to the cap **met** the requirement and lost the
permission for not collecting it, where a failed seat did not meet it.

**That optional biometric-on-mint preserves the constitution's containment.** It
does for a founder who leaves it off. For one who switches it on, verifier
availability becomes a precondition for their own income, which is the coupling
the constitution refuses to impose — reintroduced here by the operator's own
choice rather than by the protocol. Whether an operator can choose that for
themselves without recreating the failure mode institutionally is a question for
review.

**That HUB verification can be one layer for every participant class.** It is
stated as direction and specified nowhere. Whether one identity primitive can
serve founder admission, creator approval, user incentives, and developer
programmes without either weakening the strongest use or over-burdening the
weakest is exactly what the identity milestone must establish.
