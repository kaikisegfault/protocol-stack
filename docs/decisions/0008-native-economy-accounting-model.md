# ADR 0008: Native-economy accounting model

- Status: Accepted for M2 research
- Date: 2026-07-29

## Context

ADR 0002 requires one protocol-native asset and native modules for supply,
fees, treasury, escrow, staking, rewards, and penalties. M1 deliberately
implements only fixed-fee transfers and a fee pool. M2 needs a complete,
independently executable accounting model before any new consensus transition
or production economic parameter can be accepted.

The model must make custody and liabilities visible, preserve the
constitutional supply limit, use checked integer arithmetic, give every
privileged operation an explicit capability, and remain deterministic under
replay. It must also distinguish structural decisions from numerical policy:
research fixtures may exercise values, but they must not silently become
production issuance, fee, staking, reward, or penalty rules.

Primary-source review informed the decision:

- The Cosmos SDK represents protocol custody with module-owned accounts that
  have no private key. Its bank module counts those holdings in total supply
  and grants distinct mint, burn, and staking permissions. This is preferable
  to burning deposits and reminting them when a module later pays out.
  Sources: [accounts][cosmos-accounts], [bank module][cosmos-bank].
- The Cosmos distribution module pools fees, records reward entitlements, and
  lets participants withdraw independently. It also sends integer-rounding
  remainder to an explicit community pool rather than losing it.
  Source: [distribution module][cosmos-distribution].
- The Cosmos mint module demonstrates both a capped issuance parameter and a
  configurable, decimal, per-block inflation mechanism. The cap is relevant;
  its dynamic decimal policy is not suitable for this integer-only research
  contract and is not adopted. Source: [mint module][cosmos-mint].
- Ethereum consensus derives validator lifecycle, reward, and penalty
  processing from slots and epochs and expresses balances in integer Gwei.
  Its immediate balance decreases and burn-oriented slashing path are useful
  alternatives, but do not require this project to burn penalties.
  Source: [phase-zero beacon-chain specification][ethereum-phase0].
- Capability-scoped authorization is preferable to a single omnibus protocol
  key. The Cosmos authorization ADR similarly binds grants to message types
  and optional limits. Source: [authorization ADR][cosmos-authz].

These sources are comparative evidence, not dependencies. The resulting model
and implementation are original and use neither SDK code nor external runtime
state.

## Decision

### Typed custody and liabilities

Represent each issued atomic unit in exactly one typed bucket:

- spendable account balances;
- fee pool;
- treasury;
- open escrows;
- bonded stake;
- unbonding stake;
- reward pool;
- claimable validator rewards;
- claimable node rewards; or
- penalty pool.

These are protocol-owned accounting domains, not ordinary accounts with
private keys and not secondary assets. Typed domains prevent public transfers
from bypassing the native module that owns a liability.

At every accepted state:

```text
issued_supply =
  accounts
  + fee_pool
  + treasury
  + escrows
  + bonded
  + unbonding
  + reward_pool
  + validator_claims
  + node_claims
  + penalty_pool

issued_supply + issuance_capacity = supply_limit
```

Every term is an unsigned integer count of the single native atomic unit.
Every intermediate and stored value is bounded by `u64`.

### Issuance and treasury

Issuance is a privileged, explicit event. It consumes issuance capacity,
increases issued supply, and credits treasury in one atomic journal. There is
no public mint, implicit inflation, direct issuance to an account, or
unbounded supply sentinel. Treasury can then fund an account, escrow, or the
reward pool through separately authorized flows.

This establishes an auditable separation between the authority to increase
supply and the authority to spend issued protocol funds. No production
issuance schedule or amount is selected by this ADR.

### Fees and rewards

Fees first enter a dedicated fee pool. An explicit fee-allocation capability
moves a requested amount to reward pool and treasury using integer parts from
a manifest. Reward share rounds down and treasury receives the exact
remainder. No atomic unit becomes rounding dust.

The reward capability moves funded value from reward pool to a typed
validator or node claim. Participants pull claims into their configured payout
account. Pull claims avoid consensus work proportional to every participant
at each block or epoch, separate entitlement from payout, and make outstanding
liabilities directly measurable. Automatic rebonding is not part of this
model.

### Height, epochs, and locks

Height is advanced only by an explicit clock capability, one height at a time.
Epoch is derived as integer division `height / epoch_length`; wall-clock time
never enters the model. Escrow release and unbond completion are explicit
events permitted only at or after their recorded release epoch. Epoch
boundaries do not trigger hidden iteration or automatic transfers.

### Stake and penalties

Bonded and unbonding amounts remain part of issued supply and retain an
explicit owner. Beginning unbonding moves value to a separate timed liability;
completion returns it to the owner.

A penalty capability may move value from a bonded or unbonding position into
a penalty pool. Version-one research does not burn penalties. The pool
quarantines assessed value until a separate privileged event routes it to
treasury. This closed accounting path makes the cost to the owner and the
protocol disposition independently observable. Burning, victim compensation,
reward recycling, and other destinations remain policy alternatives for later
simulation and review.

### Authority and execution

The research manifest names distinct clock, issuance, fee-allocation,
treasury, escrow, reward, and penalty principals. A manifest may deliberately
assign multiple capabilities to the same principal, but no capability is
implicit. Account-funded transfers, fees, escrows, bonds, unbonds, and reward
claims require the event actor to be the affected account owner.

Events are processed in their provided order. Shape-invalid input aborts the
simulation. A well-shaped event produces either an accepted balanced journal
or a typed ordinary failure. Ordinary failure changes no economic state and
does not consume the event identifier. An accepted identifier cannot be
accepted again.

### Independent simulator boundary

Implement the model in standard-library-only Python. It must:

- accept a versioned, integer-only, explicitly research-only manifest;
- accept a deterministic ordered event list;
- reject unknown fields and non-integer monetary values;
- use checked `u64` arithmetic despite Python's wider integers;
- emit canonical JSON state and trace digests;
- emit exact integer or rational metrics, never floating point;
- expose every accepted event as a balanced journal; and
- never call the C++ kernel, a node, a network service, mutable external data,
  or wall-clock/random APIs during replay.

A versioned deterministic generator may create research scenarios from an
explicit seed, but generated events become ordinary fixed simulator input.
Generator randomness is never protocol state.

The exact contract is `native-economy-simulation-v1.md`. It is normative for
the M2 research tool only. It does not change M1 consensus.

## Alternatives not selected

- **One undifferentiated public account map:** synthetic module addresses make
  custody less visible and could admit transfers that bypass module rules.
  Typed buckets preserve the useful module-account accounting pattern while
  narrowing each transition.
- **Burn deposits and remint payouts:** this obscures held liabilities and
  creates unnecessary supply transitions.
- **Direct global reward payout:** iterating all participants couples block or
  epoch work to population and obscures unpaid liabilities. Explicit claims
  are bounded per event.
- **Automatic dynamic inflation:** no credible production target, curve, or
  rate is yet accepted. A supply cap plus explicit issuance lets simulations
  compare schedules without promoting one.
- **Decimal or floating-point shares:** platform-independent integer parts and
  an explicit remainder destination are simpler to audit.
- **Immediate burn on penalty:** burn is irreversible supply policy.
  Quarantine and explicit routing preserve a closed research model while burn
  remains measurable as a later alternative.
- **Wall-clock release schedules:** local time is not a deterministic
  consensus input. Height-derived epochs provide replayable ordering.

## Consequences

- Conservation can be checked after every event, including issuance.
- Locked, bonded, claimable, and protocol-owned exposure cannot disappear
  behind a single aggregate balance.
- Research traces can explain every change as a debit and credit.
- The model deliberately has more explicit transitions and state categories
  than an omnibus balance table.
- Pull claims postpone payouts and require an account action.
- Treasury routing of integer remainder and penalties is a structural default,
  not a claim that production treasury policy is settled.
- A later C++ implementation needs a new consensus specification, canonical
  encoding, activation rule, migration vectors, security review, parameter
  evidence, and compatibility decision. Simulator version one cannot itself
  authorize a protocol upgrade.

[cosmos-accounts]: https://docs.cosmos.network/sdk/latest/learn/concepts/accounts
[cosmos-bank]: https://docs.cosmos.network/sdk/latest/modules/bank/README
[cosmos-distribution]: https://docs.cosmos.network/sdk/latest/modules/distribution/README
[cosmos-mint]: https://docs.cosmos.network/sdk/latest/modules/mint/README
[cosmos-authz]: https://docs.cosmos.network/sdk/latest/reference/architecture/adr-030-authz-module
[ethereum-phase0]: https://ethereum.github.io/consensus-specs/phase0/beacon-chain/
