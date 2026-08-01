# ADR 0013: Reward-distribution cap and identity-split study

- Status: Accepted for M2 research
- Date: 2026-08-01

## Context

ADR 0012 resolved exact funding and participant-concentration surfaces around
the six screened economic survivor families. Every one of the 1,536 weight
cells was mixed across complete contribution support: no proportional
configuration guaranteed the accepted three-quarter maximum-share alarm.
Changing a contribution weight therefore cannot by itself provide a complete
support concentration bound.

The accepted participation contract permits multiple participant identifiers
to name the same owner and payout account. A per-participant reward cap can
therefore improve an identity-level metric while one principal receives the
same or more value by splitting work across identifiers. A mechanism study
must compare both identity and principal outcomes before proposing consensus
behavior.

Primary-source review informed the decision:

- Douceur shows that distinct remote identities cannot generally be assumed
  to represent distinct entities without an identification authority or
  strong resource assumptions. The study therefore treats the existing
  `owner` field as an experimental grouping, not proof of a unique person,
  organization, or machine. Source: [The Sybil Attack][sybil].
- Deficit Round Robin carries unused service credit across scheduling rounds
  to improve fairness under variable demand. That motivates testing bounded
  multi-epoch credit, but the network scheduler and its packet quantum are not
  adopted as an economic rule. Source: [Shreedhar and Varghese][drr].
- Cosmos F1 fee distribution calculates rewards over periods and deletes
  historical records only when no live reference can require them. This
  supports making history and pruning explicit, while its decimal arithmetic,
  delegation, commission, and distribution rules are not adopted. Source:
  [Cosmos distribution module][cosmos-distribution].
- Ethereum caps and rounds effective balance per validator and uses integer
  reward arithmetic. This illustrates that an identity-scoped cap is separate
  from principal uniqueness; no Ethereum balance, deposit, reward, or
  validator rule is adopted. Source: [Ethereum Phase 0][ethereum].

These sources are comparative evidence only. The study is original,
standard-library-only Python research tooling.

## Classification

This is an economics and mechanism-design research change. It changes no
consensus transition, canonical encoding, cryptography, compatibility surface,
accepted simulator-v1 behavior, actor, rate, weight, budget, or identity
policy.

## Decision

### Compare three mechanisms

Add `reward-distribution-study-v1` over the unchanged participation and
native-economy contracts:

1. `proportional`: the accepted per-epoch floor entitlement, paid immediately;
2. `participant_cap`: accumulate those floor amounts by participant and cap
   each payout vector at the three-quarter participant-share alarm; and
3. `principal_cap`: accumulate and cap by the registered owner, then consume
   that owner's participant buckets in deterministic oldest-first order.

The latter two mechanisms create research credit, not a native-asset claim.
Only a nonzero amount selected for payout becomes an ordinary native-economy
`allocate_reward` event. Expiration or backlog therefore cannot debit an
account, mint value, or become an unfunded native liability. The report must
still expose all delayed and expired credit because calling it non-claim state
does not remove the incentive or expectation risk.

### Fix integer entitlement and cap arithmetic

For role budget `B`, participant score `s`, and positive total score `S`, the
new study first reproduces the accepted entitlement exactly:

```text
q, r = divmod(B, S)
credit = q * s + floor(r * s / S)
```

All arithmetic is checked `u64`. The floor remainder stays in the reward pool.

At allocation epoch `E`, capped mechanisms expire old buckets, add the current
credits, and set `A = min(B, total_credit)`. Credits are grouped by participant
or owner. Each scope receives a floor candidate proportional to accumulated
credit. If the largest candidate `L` and all other candidates `O` violate
`L <= 3 * O`, reduce only the largest candidate to `3 * O`. This produces the
maximal payout obtainable from that candidate vector under the three-quarter
alarm. If `O = 0`, no capped payout is possible.

Scope keys, participants, and buckets use ascending identifier order. Credit
is consumed by `(source_epoch, participant)` order. Ties for the largest scope
use the ascending scope key, although two tied largest candidates cannot
violate a three-quarter bound. No largest-remainder redistribution occurs.

### Bound history and expose liveness loss

A credit bucket has four allocation opportunities including its source epoch.
It expires before allocation at `source_epoch + 4`. Paid buckets and zero
buckets are deleted immediately; expired buckets are deleted and counted.
This bounds retained history to four buckets per contributing participant.

Each eight-epoch trajectory is followed by four funded drain epochs with no
new contribution. Bounded liveness passes only when no credit expires. Useful
credit retention is exact paid credit divided by created credit after the
drain. The report also records zero-payout epochs, maximum pending credit,
expired credit, and retained budget. These synthetic objectives make the
safety/liveness tradeoff visible; they do not assert that four epochs is a
production-safe expiration period.

### Exercise exact support and named trajectories

For each ADR 0012 survivor family and each role, enumerate selected weight
`1..16` and ordered contribution units `1..20` for a selected and baseline
participant. Evaluate unsplit and deterministically split forms of the same
selected work. This is 6 families times 2 roles times 16 weights times 400
ordered unit pairs, or 76,800 role points per mechanism and identity form.

The split form assigns `floor(units / 2)` and `ceil(units / 2)` to two
participant identifiers with the same principal. Zero halves create no
credit. Record nonzero concentration passes, zero-payout points, credit paid,
and whether the split principal receives more than its unsplit counterpart.

Also run five reviewed twelve-epoch trajectories: honest variance,
intermittent availability, population change, an unsplit dominant principal,
and the same dominant principal split across two identities. The first eight
epochs add contribution and the last four only drain retained credit.

### Cross-check accepted boundaries and funding

Cross-check representative proportional points through the unchanged
participation engine and `build_funding_events` adapter, including multiple
participants with one owner. Compare exact entitlement amounts and require all
ordinary native-economy allocation events to succeed.

For every mechanism trajectory, independently pre-fund a native-economy reward
pool with `budget * total_epochs`. Emit only nonzero calculated payouts as
ordinary reward allocations. Require every event to succeed and final reward
pool plus claims to equal initial funding. This proves the finite study emits
no unfunded native claim; it does not select a production funding source.

The normative contract is
`../specifications/reward-distribution-study-v1.md`.

## Alternatives not selected

- **Choose the best ADR 0012 weight:** no tested weight guaranteed the alarm.
- **Cap only contribution input:** an operator can still split an identity,
  and a fixed unit cap does not directly bound reward share.
- **Redistribute clipped value to smaller participants:** this exhausts the
  budget but pays value not derived from their accepted floor entitlement.
- **Discard clipped credit immediately:** it hides the amount of useful work
  whose reward was suppressed and makes intermittent availability harder to
  evaluate.
- **Retain credit forever:** participant tombstones make that state and its
  implied expectation unbounded.
- **Treat owner as a verified unique principal:** the current registrar
  contract supplies an identifier binding, not real-world uniqueness or
  Sybil-proof admission.
- **Change participation simulation v1:** its accepted digest and transition
  boundary remain useful as an independent cross-check.

## Consequences

- M2 gains an exact comparison of concentration, liveness, retention, funding,
  and identity-split behavior.
- A participant cap can be distinguished from a principal cap instead of
  silently assuming identifiers are independent.
- Four-epoch expiry bounds research state and deliberately exposes lost credit
  when concentration and liveness cannot both hold.
- Principal grouping removes advantage only for identities already bound to
  the same registered owner. It is not a general Sybil defense.
- Any production mechanism still requires identity and admission policy,
  empirical work and cost inputs, strategic analysis, independent review, a
  consensus ADR, migration, and activation rules.

[sybil]: https://www.microsoft.com/en-us/research/wp-content/uploads/2002/01/IPTPS2002.pdf
[drr]: https://openscholarship.wustl.edu/cse_research/339/
[cosmos-distribution]: https://docs.cosmos.network/sdk/latest/modules/distribution/README
[ethereum]: https://ethereum.github.io/consensus-specs/phase0/beacon-chain/
