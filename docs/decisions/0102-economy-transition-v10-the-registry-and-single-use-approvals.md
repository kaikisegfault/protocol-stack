# ADR 0102: Economy transition v10, the registry and single-use approvals

- Status: Accepted
- Date: 2026-10-09
- Specification: [`economy-transition-v10`](../specifications/economy-transition-v10.md)
- Implements: [ADR 0048](0048-hub-verification-runs-locally-with-an-ai-integrity-monitor.md)
  section 3, and the founder answers in
  [ADR 0100](0100-founder-answers-on-who-verifies-and-how-registration-starts.md)
  and [ADR 0101](0101-founder-answers-on-the-launch-cutoff-an-active-machine-and-the-registration-limit.md)
- Meets, at the specification level: `first-goal.md` requirements 3 and 5

## Context

Two things had to change, and both had evidence behind them.

- **Admission rested on one key.** Version nine's genesis `verifier_key` signs
  every registration, which ADR 0048 called the most centralized point in the
  design. The owner's answers fix every rule a participant would feel:
  - the nearest active machine verifies, and the launch key retires at 100
    active machines;
  - an active machine is one whose seat met its most recently assigned cycle;
  - a machine may register 1,000 people a day.
- **A HUB approval could be used twice.** `hub-test-verifier-v9` executes a
  republished posture relax and a reused transfer confirmation, and both are
  accepted. The threat model records it as T1.

Everything left was mechanism. This record states each choice and what it was
chosen over.

## Decisions

### 1. The registry is keyed by seat, with an inverse entry

A machine-key entry per seat holds the key, the attested build digest, the last
window the seat met, and the window count of registrations it signed. An owner
entry per key names its seat.

**Rejected: keying by the key alone.** Every ADR 0101 rule is about a machine,
and a machine is a seat. Activity is the seat's cycle, and the limit is the
machine's count. Reading them through a key would need the inverse anyway.

**Rejected: no inverse.** Then one key could sit on two seats, sign under two
limits, and double what ADR 0101 caps for a compromised machine.

### 2. A key enters by kind 23, with an attestation and a HUB approval

A seat's owner submits the key, and the transaction carries two proofs. The
build authority's signature attests the machine runs an attested build. The
owner's fresh HUB approval says the owner installed it.

**Rejected: the build authority alone.** The company could then install keys on
any founder's seat.

**Rejected: the owner alone.** Then nothing says the key belongs to an attested
build, which is the whole of threat model T4's defense.

**Rejected: folding the key into activation (kind 3).** A key must be
replaceable, so a second path would exist anyway. A rented machine may also be
provisioned after the seat is activated.

**A replacement keeps the count and the activity mark.** Activity is the
seat's. The count must survive, or rotating keys would bypass the limit.
Replacement is also how a founder retires a compromised key, and it is the only
revocation this version has. Revocation by the build authority is
founder-reserved (threat model T8).

### 3. Activity is recorded per machine, at the registry step

Version nine deletes a window's uptime records in the same prologue that
assigns it. The assignment record keeps only `accrued` (met, in span, and under
the cap) and `winner` bits. So nothing in version nine says "met" afterwards.
The registry step writes `last_met_window` for each seat that has a machine key,
before the evidence is deleted.

**Rejected: a third bitmap in every assignment record.** It would add about
12.5 kB per window for the chain's whole life, and reading it would mean
reading history.

**Rejected: a field in every seat record.** It would rewrite 100,000 seats at
every assignment, including seats with no machine key, and change version
nine's seat value for a fact only machines need.

### 4. The active count is computed and retirement is recorded

The count is computed at the registry step and never stored. Retirement is a
present-or-absent entry holding the height that retired the key.

**Rejected: a stored count.** It would be a second quantity that could disagree
with the entries it counts, and only the assignment reads it.

### 5. A registration names the machine that signed it

Kind 10 gains `attesting_seat_id`, and the registration message binds it.
`LAUNCH_ATTESTER`, `u32` maximum, names the launch key.

**Rejected: trying every active key.** At capacity that is up to 100,000
signature checks per registration.

**Rejected: a separate kind for launch registrations.** That would make two
kinds for one act, and the second would die at retirement.

### 6. An approval signs the whole transaction

One message replaces version nine's five:
`D("protocol-stack:v10:hub-approval")` followed by the unsigned transaction,
with its HUB field zeroed. The escrow's nonce makes it single-use, and every
field is bound at once.

**Rejected: adding the nonce to each of the five messages.** Per-kind field
lists are where version nine's gap came from. Five constructions would have to
stay consistent with five bodies for every future change.

**Rejected: a decision identifier recorded in state**, as kind 6's is. It would
be unbounded storage for a property the nonce already provides.

**Rejected: keeping field lists and adding only a lifetime.** A replay inside
the lifetime would still succeed.

**This is also what ADR 0099's verifier already sees.** The person approves a
transaction, and the verifier signs it. The verifier's `approve` becomes one
construction instead of eight.

### 7. An approval lives at most one slot

A transaction carrying a HUB proof is refused when its `valid_until_height` is
more than 1,200 heights above the executing height.

**Rejected: no bound.** The nonce alone leaves a withheld approval valid until
the escrow next moves, which could be months.

**Rejected: a much shorter bound.** Under load, an approval could die before
inclusion, and the person would have to verify again.

### 8. Five result codes, not `UNAUTHORIZED`

`LAUNCH_KEY_RETIRED`, `MACHINE_KEY_NOT_FOUND`, `MACHINE_NOT_ACTIVE`,
`REGISTRATION_LIMIT`, and `APPROVAL_LIFETIME_EXCEEDED` each tell a wallet what
to do next. Folding them into `UNAUTHORIZED` would leave it guessing.

### 9. The header is unchanged, and the build authority is a separate key

The header's bytes do not change, so its schema version and the block
identifier keep version nine's, as versions two through eight kept version
one's. Every parser of a header is unaffected.

`build_authority_key` joins genesis separately from the `launch_key`. Retiring
the key that admits people then changes nothing about who admits machines.

### 10. Legacy records wait

Requirement 6 could have joined this version. The constitution reserves "dispute
evidence, conflicting statement precedence, and reclaim transitions". With
those excluded, a legacy transition could record statements and nothing that
acts on them. It waits for a version that can carry the whole mechanism.

## Consequences

- **Requirements 3 and 5 are specified, not met.** Meeting them needs the
  version-ten model, vectors, kernel, and the stack that runs them, as version
  nine needed.
- **`hub-test-verifier-v9`'s replay check is the one that flips.** Its
  version-ten successor must record the refusals the specification names.
- **The test verifier rebinds and does not change shape.** `approve` signs the
  approval message over the transaction, and `register_person` names an
  attesting seat. The interface ADR 0099 drew already takes a capture and a
  transaction.
- **The network fixtures move onto the verifier with this version.** Its
  identities and approvals change what they build anyway.
- **Owed to independent review**, adding to the threat model's list:
  - that binding the whole unsigned transaction is a sound single-use
    construction, including for a refused transaction whose approval stays
    valid;
  - that one slot is the right lifetime;
  - that the inverse entry and the kept count close the limit's bypasses;
  - that a seat-keyed registry with self-registered keys, under one build
    authority, is the right shape before hardware attestation exists.
