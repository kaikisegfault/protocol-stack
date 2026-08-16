# ADR 0045: The version-six execution model, and three rules it had to derive

- Status: Accepted
- Date: 2026-08-16

## Context

[`economy-transition-v6`](../specifications/economy-transition-v6.md) and
[ADR 0044](0044-economy-transition-v6-the-identity-account.md) were accepted on
2026-08-15 with a codec, commitment, and registry model, 462 vectors, and a
verifier. None of it **runs** a transition. `simulation/economy_transition_v6/`
said so in its own first sentence: "This is a codec, commitment, and registry
model, not an execution model."

The repository's order — specification, model, vectors, C++ — exists because of
what M3.9b found. M3.9a implemented a version-four codec and two implementations
agreed perfectly about a message neither could construct, because **a codec
never asks where a transaction gets its arguments**. The execution model is the
first step that runs a transition, and version six has more transitions with more
state behind them than any predecessor.

Building it reached three places where the accepted contract admits two readings
and only one leaves the contract self-consistent. Each is consensus-visible: two
conforming implementations that chose differently would return different result
codes, or pay a founder differently, for the same bytes against the same state.
None is founder-reserved — every one is a rejection order or a code assignment,
which `founder-constitution.md` lines 883-886 name as mechanism — but every one
has to be pinned somewhere a second implementation can find it, and that is what
this record is for.

## Decision

### The execution model extends the version-six package rather than siblings it

`ledger.py`, `execution.py`, `transitions.py`, `value_transitions.py`,
`block.py`, and `trace.py` join `simulation/economy_transition_v6/`.

ADR 0029's test asks whether a version revises a transition, and it separates
*versions*, not *layers of one version's evidence*. There is one version-six
contract; a sibling package would hold a second copy of its kind identifiers,
its state keys, its postures, and its messages with nothing keeping the two
equal — the defect ADR 0026 and ADR 0029 both exist to avoid. The settlement is
imported from `simulation/economy_transition_v3/` for exactly the same reason,
which is what the accepted vectors already require by making version six's
assignment records reproduce version three's byte-for-byte.

The evidence goes in a **new** vector file,
`test-vectors/economy-transition-v6-execution.txt`, rather than into the accepted
one. `test-vectors/economy-transition-v6.txt` is the artifact the hosted matrix
verified at 462 vectors on 2026-08-15, and the repository's rule is that an
accepted vector file is not edited.

### 1. `DEBIT_OVERFLOW` is returned at envelope check 8

Version six says every kind "first applies the shared envelope checks in version
one's order and with version one's codes and meanings, then its own conditions",
and lists five shared checks: `FEE_LIMIT_TOO_LOW`, `EXPIRED`, `NONCE_EXHAUSTED`,
`NONCE_MISMATCH`, and `INSUFFICIENT_BALANCE`. Kind 1 then lists `DEBIT_OVERFLOW`
as its own condition 5, after the recipient and posture checks.

Taken literally that is not implementable. Check 8 is "escrow balance is below
what it must debit", and for a transfer what it must debit is
`amount + fixed_fee` — the exact sum kind 1's condition 5 tests. Evaluating the
overflow test after the balance comparison leaves the balance comparison
undefined on a sum that does not fit `u64`.

**Deciding it by the literal order would also make code 7 unreachable in version
six**, because a balance is bounded by `total_supply`, which is bounded by the
supply limit — 5,699,395,010,000,000,000 atomic, well below `2^64 - 1` — so
`INSUFFICIENT_BALANCE` would fire first for every overflowing amount. The
specification lists exactly three frozen-and-unreachable codes, `4`, `23`, and
`25`, and does not list `7`.

**Chosen:** the overflow test is part of check 8 and precedes it, which is where
version one puts it. That keeps the specification's unreachable-code list exactly
right, keeps version one's codes and meanings, and makes check 8 well-defined.

**Rejected:** the literal order, which contradicts the specification's own
result-code section and leaves a check undefined on its own input.

The consequence that remains is real and is recorded rather than smoothed over:
`INSUFFICIENT_BALANCE` now **precedes** `ZERO_AMOUNT` for kind 1, so a
zero-amount transfer from an escrow that cannot pay the fee answers
`INSUFFICIENT_BALANCE` under version six and `ZERO_AMOUNT` under version one.
That follows from the shared-envelope sentence, which is unambiguous, and the
trace records it as a divergence vector rather than leaving it to be discovered.

### 2. An unrequested confirmation field is refused at execution with `UNAUTHORIZED`

Version six requires the 64-octet confirmation field to be 64 zero octets when
the operation requires no confirmation, places the rule at admission, and names
`MALFORMED_TRANSACTION`. Neither survives contact with the rest of the contract.

**Admission cannot evaluate it.** Whether a confirmation is required is a
predicate over the escrow's stored posture and the executing height, and the
specification states twice — once in Admission and once in Two authorization
schemes — that admission reads no state. The same is true of kind 17: whether a
posture change tightens is relative to the stored posture.

**The named code does not exist in the space that could return it.** Admission
codes and result codes are disjoint namespaces that share numbers: admission `1`
is `MALFORMED_TRANSACTION` and result `1` is `ZERO_AMOUNT`. There is no result
code named `MALFORMED_TRANSACTION` to put in a receipt.

**Chosen:** refuse at execution with `UNAUTHORIZED`, the code version six assigns
to "a key the applicable rule refuses". A HUB signature presented where the
applicable rule requires none is exactly that.

**Rejected:** ignoring the field. The rule exists to close a malleability — two
byte strings with different transaction IDs and identical effects — and dropping
a stated rule is a larger deviation than routing it to the nearest applicable
existing code.

This is the one place where a version-seven contract should state a rule outright
rather than leave it derived, and the handoff records it as such.

### 3. `NOTHING_TO_MINT` is the empty walk range, not an equality

Kinds 4 and 5 refuse when the mark "already equals the last assigned window, or
no window assigned yet".

A seat activated at a height in window `w` takes mark `w`, while the last
assigned window at that height is `w - 2`. The mark is **above** the last
assigned window, so the literal condition does not hold, so the mint would
proceed, walk an empty range, collect nothing — and then set the mark to `w - 2`,
because the transition sets it to the last assigned window whatever the walk
found. **A mark that decreases destroys the exactness argument the whole
accumulation cap rests on**, which version three states as: the mark changes only
at a mint, a mint sets it to the last assigned window, so every window in
`(mark, last]` was assigned while the mark held its current value.

**Chosen:** the condition is `walk_range(mark, last_assigned) is None`, of which
"already equal" is one case and "no window assigned yet" is the other.

**Rejected:** the literal equality, which lets a mint lower a mark two windows
and would have shipped as a silent difference between two implementations.

### The cycle assignment is a prologue, and that is a decision about money

`ledger-transition-v1` does not say whether a cycle assignment due at a window
boundary is written before or after that block's transactions, and version six
inherits the silence.

The specification's own sentence decides it: "the last assigned window at any
height `h` is `window_of_height(h) - 2`". That is a statement about every
transaction executing at `h`, and it is false under the other reading for every
transaction in a boundary block.

**The trace runs both readings against identical inputs, and the difference is
not stylistic.** Under the prologue reading a founder's mint at the boundary
collects 114,860,000,000 atomic. Under the other it succeeds, collects **zero**,
and advances the mark to the assigned window anyway — so the cycle is forfeited
permanently rather than deferred. A referral mint in the same block is only
deferred, because kind 5 advances its own mark on success alone and the accrual
survives in the balance entry. Both figures are recorded.

### The block header and the transaction tree are inherited unchanged

Version six re-versions genesis to schema `6`, the receipt to version `6`, and
the state root to a version-six label and version field. It says nothing about
`protocol-primitives-v1`'s 146-byte application block header or its ordered
transaction tree, and it states that definitions there govern unless it imposes a
narrower rule. **Both are therefore version one's, including the header's schema
version field of `1`.**

A version-six header is already unmistakable without a new number: the chain ID
it carries is derived under a version-six label and both state roots it carries
are version-six constructions. The verifier requires the restated header and the
restated tree to reproduce `ledger-transition-v1.txt`'s recorded `block_header`
and `block_id` and `protocol-primitives-v1.txt`'s recorded `tx.root` before any
version-six block's commitments rest on them, because a restatement that had
drifted would otherwise agree only with itself.

### The model implements no cryptography, and a signature is a recorded table

A `SignatureOracle` maps `(public key, message) -> signature`, so verification is
exact-match lookup and a signature over any other message is simply absent. The
one real signature in the trace is the accepted version-one transfer's, taken
from `test-vectors/protocol-primitives-v1.txt`; every other is an eight-octet
counter padded to 64 octets, which no reader can mistake for Ed25519.

## Consequences

**Requirement 10's target is unchanged and the C++ kernel is next.** Nothing here
revises `economy-transition-v6`; it implements it and records where implementing
it required a reading. The three derived rules are exactly what the C++ codec and
its transitions must reproduce, and they are the kind of thing a byte-level
cross-language check cannot catch — which is the lesson M3.9b paid for.

**The accepted contract is not edited.** Its specification gains an evidence
pointer to the execution model and this ADR, and nothing else. All five
predecessor vector files verify at their recorded counts — 238, 579, 441, 550,
462 — and `test-vectors/economy-transition-v6.txt` is byte-for-byte unchanged.

**A specification correction is owed to version seven**, and only one: the
zero-confirmation-field rule should name an execution result code rather than an
admission code it cannot return. The other two derivations are readings the
accepted text supports; this one is a rule the accepted text states in a place it
cannot hold.

**A vacuous claim was found in this slice's own vector file, which is the third
rule of `docs/engineering/verification.md` catching its own author.** Every block
in the boundary scenario was separated by a height jump, so the per-scenario
root-chaining claim was an `all()` over an empty set. The scenario gained a real
successor block at the next height and the checker now fails rather than emitting
a boolean over an empty set.

**The trace does not prove the chain reachable end to end.** Two states are
stamped rather than executed, and both are recorded as stamps: the enrollment
counter one short of the population, because reaching 999,999 needs 999,999
registrations; and the height between segments, which stands in for a run of
empty blocks and refuses to skip a window boundary that would have written an
assignment.

**A consequence of the accepted rules is now visible, and the owner settled it
the same day by leaving it as it stands.** The millionth-and-first verified
person registers successfully, receives no entry airdrop, and holds an escrow
with a zero balance — so every transaction they can sign, including the one that
would collect a verified-user permission they do not have, answers
`INSUFFICIENT_BALANCE` until they are funded. That follows from two accepted
decisions, the bounded airdrop of ADR 0042 and the universal fee, and nothing in
this slice changes it.

**The founder answer of 2026-08-16 is that the entry airdrop is a launch
incentive with a bound rather than the permanent funding path.** By a million
verified identities the native asset is purchasable outside the ecosystem through
bridges and external venues, so a new participant funds their own escrow from
outside or an existing member sends them value. No rule moves. What the answer
adds is a sequencing constraint the protocol cannot enforce and the roadmap must
carry: **external purchasability has to exist before the airdrop bound is
reached**, because until then the airdrop is the only funding path a newcomer
has.
