# ADR 0023: Founder economy cycle boundary and consensus encoding

- Status: Accepted for M3 specification; no implementation exists yet
- Date: 2026-08-07

## Context

M2 closed with six accepted contracts, five verifiers, and a multi-year scenario
suite proving exact integer accounting for the Founder economy. Every number is
fixed and none of it is consensus. `founder-economy-report-v1.md` names the cycle
boundary first among the M3 obligations, and `current-state.md` records it as the
next action, for one reason: the Founder Constitution states that local wall
clocks cannot decide consensus, and every other Founder transition is defined in
terms of a cycle.

Seven questions had to be settled before any C++ could be written:

1. what a cycle is, given only block height;
2. whether the Founder chain migrates the M1 devnet or replaces it;
3. how pending permissions are stored, given that the M2 model's key set is up
   to 1,462 entries per seat and 146.2 million entries at full capacity;
4. how four explicitly deferred founder decisions reach a deterministic state
   machine without being invented;
5. who authorizes each transition, on a chain whose genesis holds no supply;
6. how the constitutional transaction fee is charged when no account can exist
   before the first issuance; and
7. what the numeric receipt codes are, since every code in the M2 models is a
   simulator result rather than a consensus receipt.

## Decision

### A cycle is a global epoch grid with a per-seat offset

`epoch_index(h) = h / epoch_blocks`, and a seat activated in epoch `a` holds the
731 epochs `a + 1` through `a + 731`. A cycle is evaluable only once
`epoch_index(h)` has passed it, so no evaluation observes a partial epoch.

Cycle zero starts at the next boundary rather than at the activation height. Had
it started at the height, the first cycle's block count would depend on where
inside an epoch the seat activated, and two seats with equal windows would
measure unequal work. The boundary rule makes all 731 cycles exactly
`epoch_blocks` blocks for every seat while preserving the constitutional rule
that different activation dates give different windows.

`epoch_blocks` is genesis configuration, not a protocol constant. The
constitution's "24-hour-target" is a target realized by choosing it against the
accepted block interval, and a halt or a slow period changes a cycle's
wall-clock duration with no consensus rule detecting it. That limit is stated
rather than engineered around, because the alternative is to admit time into
consensus.

### A new chain, not a migration

ADR 0017 already required either a new genesis or an explicit versioned
migration, because the Founder denomination is eight decimals and M1 is nine. A
version-two genesis schema produces a different chain identifier through the
unchanged derivation rule, so the Founder chain is a separate chain and no M1
byte, state, root, or receipt is reinterpreted.

The version-two genesis fixes total supply, the initial fee pool, and the account
count at exactly zero, turning the constitution's "no founder-directed genesis
allocation" from a promise into a decoder check.

The version-one 200-octet transfer remains valid on the version-two chain with
its own signing label, transaction-ID label, and result codes. Preserving it
unchanged is the strongest available compatibility statement and costs nothing:
the transfer encoding is denomination-agnostic, and the chain identifier already
prevents cross-chain replay.

### Pending permissions are watermarks, and only exceptions cost a record

Four `u16` watermarks per seat — evaluated and exercised, base and referral —
replace the M2 model's evaluated-key set and pending-permission map. The cycles
in `[exercised_next, evaluated_next)` are exactly the pending permissions, and
both evaluation and exercise proceed in cycle order.

This works because the four non-Founder base legs and the referral leg are
constants. Only two facts are not implied by a cycle index: which seats received
a reallocated Founder leg from an inactive cycle, and which inactive referred
cycles the supplied policy declined. Those get records; nothing else does.

The result is that a seat's entire accumulation history costs 8 octets on the
active path. Unconditional economy state at full capacity is 200,018 records and
6,800,388 octets — the whole seat population, all ten channels, all custody, and
all four sequences.

Requiring cycle order costs nothing the constitution grants. Permissions may
still be exercised immediately or accumulated across the whole window; only the
settlement order is fixed, and out-of-order evidence succeeds on resubmission.

### Deferred founder decisions travel as signed attestations, and are labelled

Three transitions carry a decision consensus cannot compute. Each takes a
106-octet attestation whose signature covers the transaction's own payload
octets, the chain identifier, the transaction kind, the policy identifier, and an
expiry height. Because the attestation signs the payload, no subject field and no
subject-mismatch failure exist: it authorizes exactly those bytes on exactly that
chain, or it does not verify.

The specification fixes the carrier, not the policy. The genesis-configured
attester keys are devnet stand-ins with total control over the outcomes the
unresolved policies would decide, and the specification says so in those words.
The Founder Constitution permits deterministic stand-ins on a testnet provided
they are labelled; this is that label, and no production network may configure
them.

What consensus contains regardless of the attester is stated positively: no
attestation can change a leg amount, the 57,430,000,000-atomic base total, a
channel cap, or the supply limit; create a permission for an unelapsed,
out-of-order, or out-of-window cycle; name a recipient that is not an activated
seat, repeat one, or produce allocations whose checked sum is not exactly the
Founder leg; exceed a direct-channel cap or reuse a sequence; or spend typed
custody, which no version-two transition spends.

Three separate keys, one per evidence kind, satisfy the charter requirement that
one logical authority never holds a combined capability. Activity and performance
share a key because the constitution treats them as one unresolved policy area.

### Exercise is permissionless because it has no discretion

The beneficiaries and amounts of a pending permission are fixed at evaluation.
Exercise produces the same result whoever submits it, so requiring authorization
would be authority with no decision attached — and worse, it would let a seat
withhold a Founder leg that an inactive cycle already reallocated to a rival.
Permissionless exercise means a reallocation recipient never depends on the
inactive seat to collect.

Evaluation is permissionless for the same class of reason inverted: an inactive
seat cannot submit its own evaluation, so making the transition depend on the
seat's participation would strand every offline seat's reallocated leg.

### Replay protection is ordinal, never a growing set

Evaluation replay is the evaluated watermark, so an already-evaluated cycle and
an out-of-order cycle are one condition with one code. Direct issuance replay is
a strict per-channel `u64` sequence rather than the M2 model's free-form decision
identifiers, because an unbounded set of accepted identifiers is a state-growth
attack: amounts may be as small as one atomic unit, so the set is bounded only
by the channel caps.

### Fees follow the constitution, with one bootstrap exception

The constitution names issuance exercise as fee-bearing, so exercise carries an
explicit fee payer, nonce, fee limit, and expiry, and reuses the version-one fee
and nonce semantics exactly.

Direct issuance is feeless. It is the only transition that credits a spendable
balance, so on a genesis with zero supply it is the only transition that can
execute before any fee payer exists. The deviation is bounded by the eligibility
attestation, the strict sequence, and the channel cap. The alternative —
deducting the fee from the issued amount — conserves value and charges the fee,
but it reduces what an incentive channel pays its beneficiary, which is a
founder-reserved monetary choice. It is recorded here and not made.

Seat activation and both evaluations are also feeless: each is gated by an
attestation and bounded by a fixed count, and requiring a fee would make seat
admission depend on a balance that cannot exist until a direct issuance has
occurred.

### Result codes extend the version-one space rather than replacing it

Codes 0 through 8 keep their version-one numbers and meanings, with code 4
renamed to cover a fee payer generally, so a version-one transfer produces the
same numeric result on either chain. Codes 9 through 15 are reserved. Economy
codes occupy 16 through 36, and the receipt carries the transaction kind so a
code is always read against the kind that produced it.

Each kind's check order is normative and listed in its section. Attested kinds
check authority before any parameter, following the authority-before-funds
ordering accepted in ADR 0021, so an unauthorized submitter never learns which
parameter would have failed; static ranges then precede state lookups, and state
lookups precede arithmetic.

The base and referral channel caps are exactly 100,000 seats times 731 cycles
times their per-cycle legs, and each `(seat, cycle, kind)` reserves at most once,
so permission evaluation and exercise can never exhaust a channel. `CHANNEL_CAP`
is therefore a receipt code for direct issuance alone; a cap violation reached
any other way is an internal invariant failure that rejects the block, matching
how version one treats an impossible recipient or fee-pool overflow.

## Alternatives not selected

- **Block timestamps or a consensus adapter's median time as the cycle
  boundary:** the constitution forbids local wall clocks from deciding
  consensus, the M1 application header carries no timestamp, and adding one
  would change accepted M1 bytes to import a value the protocol is supposed to
  exclude.
- **A per-seat block counter anchored at the activation height:** makes the
  first cycle's length depend on the activation offset, so equal windows measure
  unequal work, and gives no shared boundary for the activity snapshots and
  bounded settlement that later slices need.
- **Migrating the M1 devnet in place:** requires old and new state-root
  commitments, a rollback story, and cross-boundary replay vectors, all to carry
  forward a research devnet with no value and the wrong denomination. ADR 0017
  already permitted a new genesis.
- **Reusing schema version 1 for the new transaction kinds:** would extend a
  frozen version's meaning, which `protocol-primitives-v1` forbids.
- **Storing pending permissions as explicit records, as the M2 model does:**
  146.2 million records at full capacity, roughly 2 GB of leaf bytes that every
  node must commit whether or not any seat was ever inactive, to represent
  information that four watermarks already carry.
- **A per-seat bitmap over the 731 cycles:** 92 octets per seat, more compact
  than explicit records but less auditable than a watermark, and it still cannot
  represent a reallocation. The watermark is both smaller and simpler.
- **Allowing out-of-order evaluation and exercise:** restores the unbounded key
  set the watermark exists to remove, in exchange for sparing a resubmission.
- **Free-form direct-issuance decision identifiers:** an accepted-identifier set
  that grows without bound and is attacker-controlled at one atomic unit per
  entry.
- **Crediting direct-mint beneficiaries to typed custody, as the M2 model
  does:** leaves a zero-supply genesis with no path to a spendable balance, so
  no fee could ever be paid and the chain could not bootstrap. The four direct
  channels pay users who hold ordinary balances, and nothing in the constitution
  requires their proceeds to be unspendable.
- **Making every version-two transition feeless:** simpler, but the constitution
  explicitly names issuance exercise as fee-bearing, and a blanket deviation is
  worse than one stated exception.
- **Deducting the direct-issuance fee from the issued amount:** conserves value
  and satisfies the fee rule, but reduces an incentive channel's payment to its
  beneficiary, which is founder-reserved.
- **Requiring the seat to authorize its own exercise:** lets a seat withhold a
  Founder leg already reallocated to another seat, and attaches authority to a
  transition that has no decision to make.
- **Deciding the activity metric, performance winner count, tie rule, referral
  treatment, or direct-channel eligibility to make the encoding concrete:**
  every one is an explicitly deferred founder decision, and a consensus
  specification is the worst place to invent one because acceptance would make
  the invention normative.
- **Leaving the evidence field opaque and unverified:** an unverified consensus
  input is worse than a labelled stand-in, because nothing then bounds who may
  supply it.
- **Specifying commercial routing, fee distribution, escrow payouts, the claim
  path, or the seat-purchase join in the same document:** each needs its own
  transitions and evidence, and none of them can be specified before the cycle
  representation they all depend on.

## Consequences

- M3 has a cycle rule that depends on nothing but block height, and every later
  Founder transition can now be specified against it.
- The Founder chain is a new chain. M1 bytes, state, roots, receipts, devnet
  supply, and adapter behavior are untouched, and the version-one transfer runs
  unchanged on the version-two chain.
- Unconditional economy state at full seat capacity is 200,018 records and
  6,800,388 octets. Reallocation and referral-skip records are the only
  unbounded growth, and their worst case is large: 1,973,700,000 octets with
  single-recipient reallocations and 57,237,300,000 at the 64-recipient ceiling.
  Incentive bounds it in practice — exercise is permissionless and deletes the
  record while paying its recipient — but incentive is not containment, and a
  consensus bound must be selected in the implementation slice. That choice
  depends on the founder-reserved winner count.
- The economy commitment must be maintained incrementally. A full tree
  recomputation per block is not viable at the stated bound, and the
  specification fixes the commitment rather than the method.
- Three genesis-configured stand-in authorities exist, and their power is stated
  plainly rather than softened. No production network may configure them, and
  each must be replaced by an accepted policy with its own specification.
- Total supply now changes, replacing a version-one invariant. It rises only
  through exercise and direct issuance, bounded by channel caps whose checked sum
  is exactly the supply limit. There is still no burn, confiscation, or public
  asset-creation operation.
- The four unresolved founder decisions are now visible in the encoding as three
  attester keys and two supplied policy results. They are no longer deferrable
  much further: the next slice implements these bytes, and the slice after it
  needs the winner count to bound reallocation storage.
- The M2 schemas, vectors, and digests stay frozen. Six narrowings against the
  models are recorded in the specification rather than by editing an accepted
  contract, and the extended Python model must implement the consensus rules
  rather than the model's.
- No code changes. Nothing in this repository executes these bytes, and the
  normative vector file does not exist yet.

## Compatibility and independent review

This ADR accepts a specification. It activates no transition, creates no native
units, changes no accepted digest, and adds no runnable behavior. The
version-one primitives, transfer, genesis, accounts tree, state root, and receipt
are unchanged.

The implementation slice must produce
`test-vectors/founder-economy-consensus-v1.txt` and independent C++20 and Python
harnesses that both reproduce every positive vector and reject every negative
case, including the cycle boundary, every numeric result code, the economy leaf
and root construction, and state-root equality across failed transitions.

Later slices must define commercial and transaction-fee distribution, escrow
payout capabilities and their signed envelopes, the claim path from typed custody
to a spendable account, the seat-purchase join, persistence and
crash-consistency, and the replacement of each stand-in authority.

An exact encoding is not a safe one. Independent protocol, cryptographic, and
economic review remains required, and the stand-in authorities in particular
must not survive into any public network.
