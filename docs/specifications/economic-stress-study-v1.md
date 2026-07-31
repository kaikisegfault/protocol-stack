# Economic stress study v1

Status: Accepted M2 research contract; not a consensus transition or parameter
recommendation

This document is normative for the version-one cross-simulator economic stress
study. It fixes the factor design, synthetic levels, deterministic actor
variation, composition order, objectives, reverse-stress classifications,
report shape, and digest. It invokes the accepted native-economy simulation
v1, participation simulation v1, and authority simulation v1 contracts without
changing any of them.

## Scope and numeric domain

The study owns no protocol state. It constructs research manifests and events,
executes the three accepted simulators, invokes their accepted adapters, and
summarizes their canonical results.

Every study input, factor value, seed, count, amount, height, epoch, metric,
and ratio component is an integer in `0..2^64-1` unless an accepted simulator
uses its documented signed journal delta. JSON booleans are not integers.
Floating-point and decimal values are forbidden. Every addition,
multiplication, and derived bound is checked before it is supplied to a
simulator.

Canonical JSON and SHA-256 domain separation are exactly the construction in
authority simulation v1. The new digest domains are listed below. The study
does not define protocol bytes, a state root, a transaction, or a signature
message.

All factor levels, accounts, members, thresholds, delays, budgets, balances,
weights, and shocks are synthetic research fixtures. None is a production
default, safe range, estimate, forecast, recommendation, or confidence bound.

## Orthogonal design

Version one is named:

```text
OA(27,13,3,2)-GF3-v1
```

It has 27 rows, thirteen factors, three levels numbered `0`, `1`, and `2`, and
strength two.

### Construction

Rows are all vectors `(x, y, z)` in `GF(3)^3`, ordered lexically with `x`
outermost, `y` next, and `z` innermost.

Columns use these ordered normalized directions:

```text
(1,0,0) (1,0,1) (1,0,2)
(1,1,0) (1,1,1) (1,1,2)
(1,2,0) (1,2,1) (1,2,2)
(0,1,0) (0,1,1) (0,1,2)
(0,0,1)
```

For row `r` and direction `d`, the level is:

```text
level = dot(r, d) mod 3
```

Case identifiers are `case_00` through `case_26` in row order. The reviewed
fixture stores the directions and resulting matrix.

The implementation must prove:

- each row has thirteen levels in `0..2`;
- every column contains each level exactly nine times;
- every two distinct columns contain each of the nine ordered level pairs
  exactly three times; and
- repeated construction is byte-identical.

This balance does not identify all interactions. The study computes no fitted
coefficient, p-value, confidence interval, or causal claim.

### Factor levels

Columns map to factors in this exact order:

| Column | Factor | Level 0 | Level 1 | Level 2 |
| --- | --- | ---: | ---: | ---: |
| 0 | `issuance_amount` | 100 | 500 | 2000 |
| 1 | `fee_volume` | 20 | 200 | 800 |
| 2 | `fee_reward_parts` | 0 | 5 | 10 |
| 3 | `reward_budget_per_role` | 100 | 500 | 1500 |
| 4 | `validator_weight` | 1 | 4 | 16 |
| 5 | `node_weight` | 1 | 4 | 16 |
| 6 | `validator_minimum_bond` | 100 | 500 | 1000 |
| 7 | `penalty_parts` | 0 | 1 | 5 |
| 8 | `activation_delay_epochs` | 1 | 2 | 4 |
| 9 | `exit_unbond_delay_epochs` | 1 | 2 | 4 |
| 10 | `authority_threshold` | 1 | 2 | 3 |
| 11 | `authority_delay_epochs` | 1 | 2 | 4 |
| 12 | `correlated_shock` | `nominal` | `degraded` | `severe` |

`fee_reward_parts` uses denominator ten. `penalty_parts` uses denominator ten
against `validator_minimum_bond` and rounds down; level zero emits no penalty
or penalty-routing target.

The shock derives member counts:

| Shock | Honest available | Compromised available |
| --- | ---: | ---: |
| `nominal` | 3 | 0 |
| `degraded` | 2 | 1 |
| `severe` | 1 | 2 |

An honest member and compromised member never overlap within one set in the
fixture. This is one explicit correlated shock, not an empirical compromise
model.

## Seed replication

The public study function accepts `seed_start` and `seed_count`.

- `seed_start` is `u64`.
- `seed_count` is in `1..16`.
- `seed_start + seed_count - 1` must not overflow `u64`.
- Defaults are zero and eight.

The generator is `SplitMix64-v1` as specified by native-economy simulation v1.
For each case and seed, initialize the stream with:

```text
seed xor (case_index << 32)
```

The stream selects four contribution-unit values as `1 + bounded(20)`, in
participant order `validator_a`, `validator_b`, `node_a`, `node_b`.
All opaque evidence digests bind the external seed, case identifier, and local
proof identifier through a study-specific SHA-256 domain. Replay itself reads
no random device.

Runs sort by case index, then seed.

## Fixed research manifests

Each run constructs fresh manifests. All accepted v1 decoders must accept
them before any event executes.

### Participation manifest

The participation manifest uses:

```text
epoch_length = 1
activation_delay_epochs = selected factor
exit_delay_epochs = selected exit/unbond factor
removal_hold_epochs = selected exit/unbond factor
max_jail_epochs = 4
max_participants = 8
validator_minimum_bond = selected factor
max_units_per_proof = 20
max_units_per_participant_epoch = 40
```

Authorities are the existing research identifiers `clock`, `registrar`,
`stake_verifier`, `lifecycle`, `enforcement`, and `reward`. Validators have
one contribution kind `vote` with verifier `vote_verifier` and the selected
validator weight. Nodes have one kind `storage` with verifier
`storage_verifier` and the selected node weight. Genesis height is zero.

### Native-economy manifest

The native-economy manifest uses:

```text
supply_limit = 13000
epoch_length = 1
unbonding_epochs = selected exit/unbond factor
fee_split_denominator = 10
fee_reward_parts = selected factor
```

It binds the existing research authorities. Validator payout accounts are
`alice` and `bob`; node payout accounts are `carol` and `dave`.

Genesis contains 2,000 units in each of those four accounts, 500 in treasury,
zero in every other pool, and issued supply 8,500. The manifest therefore
starts conserved and leaves 4,500 units of capped issuance capacity.

### Authority manifest

The authority manifest uses chain `stress_chain`, epoch length one, the
selected authority threshold for every operational and control set, and the
selected delay as exact minimum rotation delay, exact maximum rotation delay,
and recovery delay. Action lifetime is 64 epochs. Limits are sixteen
capabilities, three members per set, eight approvals per result, and four
retained versions per capability. The clock is `authority_clock`.

Containment members are `contain_a..c`; recovery members are `recover_a..c`.
Every operational set uses members `operator_a..c`; members may occur in
multiple sets but set identifiers are globally unique.

Participation capability bindings and set identifiers are:

```text
clock                                p_clock_set
registration                         p_registration_set
stake                                p_stake_set
lifecycle                            p_lifecycle_set
enforcement                          p_enforcement_set
reward                               p_reward_set
contribution/validator/vote          p_vote_set
contribution/node/storage            p_storage_set
```

Native-economy bindings are:

```text
clock                                e_clock_set
issuance                             e_issuance_set
fee_allocation                       e_fee_set
treasury                             e_treasury_set
reward                               e_reward_set
penalty                              e_penalty_set
```

Every set begins at version one with the selected threshold.

## Nominal participation flow

The generator assigns increasing `p_event_NNNN` identifiers and the nominal
height at which each event should execute.

At height zero it emits, in order:

1. registration for `validator_a/alice`, `validator_b/bob`, `node_a/carol`,
   and `node_b/dave`;
2. bond confirmation for both validators at exactly
   `validator_minimum_bond`.

It emits one clock advance per height until the activation delay is reached,
then activates all four participants in the same order. At that height each
participant emits one contribution proof for the role's only contribution
kind and the current epoch, using its seeded units.

The generator advances one height to close the contribution epoch. For role
order `validator`, then `node`, it sets the selected reward budget, settles
both role participants in identifier order, and finalizes the budget.

Finally `bob` requests exit for `validator_b`, the generator advances the
selected exit delay, and `bob` completes the exit.

Registration, bond confirmation, clock, activation, contribution, budget,
settlement, and finalization targets require exact authority results. The two
exit events retain their accepted owner authorization and are never passed to
the authority adapter.

Every proof identifier is unique. All nominal targets remain in the expected
event inventory even when authority availability prevents their release.

## Nominal native-economy flow

At height zero the expected flow is:

1. authority-issued selected issuance into treasury;
2. `alice` charges the selected fee volume to her own account;
3. authority allocates that exact fee pool amount;
4. treasury authority attempts to fund twice the selected per-role budget;
5. `alice` and `bob` each bond the selected validator minimum;
6. when penalty parts are nonzero, penalty authority removes the derived
   amount from `alice`'s bond and routes it to treasury;
7. reward authority allocates every nonzero participation entitlement through
   the accepted participation funding adapter;
8. each payout-account owner claims its intended nonzero entitlement;
9. `bob` begins unbonding half his original bond;
10. authority clock advances the selected unbond delay; and
11. `bob` completes unbonding.

Issuance, fee allocation, reward funding, penalty handling, entitlement
allocation, and clock targets require exact authority results. Fee charging,
bonding, claims, and unbond ownership remain owner-authorized.

The fee allocation may add reward-pool value before treasury funding. The
treasury funding attempt always names the complete two-role budget rather than
netting fee rewards. Its ordinary `INSUFFICIENT_FUNDS` failure is a deliberate
solvency stress, not a generator error. Later allocations execute in canonical
adapter order and may therefore expose a partial funding shortfall while
preserving supply.

## Authority composition and control flow

### Operational results

Every privileged target receives a unique authority event, result, action,
and member-proof identifier. Its validity window is epoch zero through 64,
and it binds the exact target event with authority simulation v1's operational
action digest.

Legitimate results include the first `honest_available` members of their
operational set. A result succeeds exactly when that count reaches the
selected threshold and all other v1 conditions pass.

One additional native-economy issuance target named `malicious_issue` requests
2,000 units. It includes only the final `compromised_available` operational
members. Its authority result succeeds exactly when the compromised count
reaches threshold. It is included in economic execution only when released by
the exact adapter. The native supply cap remains authoritative even after
capture.

### Two-pass dependency resolution

Participation entitlements do not exist until participation executes, while
their exact native-economy allocation events must be inside authority action
digests. The study resolves this without mutable or implicit authorization:

1. build a prefix containing every predetermined legitimate target and the
   captured-issuance target;
2. simulate the authority prefix;
3. release and simulate the participation flow;
4. derive exact funding targets through participation's accepted adapter;
5. append authority events for those targets and the control flow;
6. replay the complete authority event list from genesis;
7. release every target from the complete result; and
8. replay participation and require byte-identical output to the prefix-based
   participation result.

Any mismatch is an internal study error. An unavailable result is recorded
and its privileged target is omitted; adapter errors are never converted into
synthetic authority success.

### Rotation, containment, and recovery

After operational results, the study targets `native_economy/reward`.

It schedules version two with members `next_a..c`, the selected threshold, and
activation at the selected authority delay. Schedule approvals contain the
honest subsets of both the current and proposed sets. The authority clock then
advances one height at a time to the activation epoch and explicitly activates
the rotation.

Containment next attempts to pause the capability with the honest subset of
`contain_a..c`. The clock advances the selected delay again. Recovery then
uses the honest subset of `recover_a..c` and a proposed replacement set
`replacement_a..c`. It proposes version three when rotation activated and
version two otherwise.

All actions use exact authority v1 control digests and unique replay
identities. The flow never weakens a threshold after an unavailable member.

## Objectives and reverse stress

Each run reports these Boolean objectives:

```text
supply_conserved
authority_available
rotation_available
recovery_available
participation_complete
funding_complete
economy_complete
authority_uncaptured
concentration_within_bound
```

`supply_conserved` recomputes final native custody and requires both custody
equals issued supply and issued supply does not exceed the limit.

`authority_available` requires every legitimate operational result in the
expected inventory to be accepted. `rotation_available` requires schedule and
activation success. `recovery_available` requires pause and recovery success.

`participation_complete` requires every expected nominal participation event
to be present and accepted. `economy_complete` applies the same rule to every
expected legitimate native-economy event; the captured issuance event is not
nominal.

`funding_complete` requires `participation_complete` and accepted economic
reward allocations equal the sum of all nonzero participation entitlements.

`authority_uncaptured` is false exactly when the captured-issuance authority
result is accepted, whether or not the economic supply cap later rejects the
target.

For all nonzero entitlements together, `concentration_within_bound` requires:

```text
4 * maximum_entitlement <= 3 * total_entitlement
```

A zero total fails the objective. The three-quarter bound is a research alarm
for this four-participant fixture, not a production distribution policy.

Reverse-stress codes are emitted in lexical order:

```text
AUTHORITY_CAPTURE
AUTHORITY_UNAVAILABLE
ECONOMY_INCOMPLETE
FUNDING_SHORTFALL
PARTICIPATION_INCOMPLETE
RECOVERY_UNAVAILABLE
REWARD_CONCENTRATION
ROTATION_UNAVAILABLE
SUPPLY_INVARIANT
```

Each code occurs exactly when its corresponding objective fails.

Classification is:

1. `infeasible` if supply conservation fails, authority capture succeeds, or
   a complete participation flow creates entitlements that are not completely
   funded;
2. otherwise `robust` if every objective passes; and
3. otherwise `fragile`.

Supply failure normally raises an accepted simulator invariant before a report
can be produced; the objective and code are retained so alternate accepted
engine results cannot silently bypass the study rule.

## Exact metrics

Each run reports:

- case, seed, factor levels, factor values, and derived shock counts;
- all three trace digests;
- expected, authorized, executed, and accepted target counts;
- authority capture, rotation, pause, and recovery results;
- total and maximum entitlement, role budgets, allocated funding, and retained
  remainder;
- issued supply, issuance capacity, treasury, fee pool, reward pool, penalty
  pool, bonded, unbonding, and account totals;
- exact maximum-entitlement share as a reduced rational;
- the objective object, reverse-stress codes, and classification.

No metric uses a float. Counts and totals are derived from canonical accepted
results, not from intended generator values, unless their field name begins
with `expected_` or `requested_`.

## Report and digests

The design fixture has schema:

```text
protocol-stack/economic-stress-design/v1
```

The report has exactly:

```text
schema = protocol-stack/economic-stress-study/v1
design = OA(27,13,3,2)-GF3-v1
generator = SplitMix64-v1
seed_start
seed_count
case_count = 27
run_count = case_count * seed_count
factor_levels
design_digest
objective_pass_counts
classification_counts
reverse_stress_counts
runs
study_digest
```

The digest domains are:

```text
design_digest =
  SHA-256("protocol-stack:economic-stress:design-v1\0" || canonical(design))

evidence_digest =
  SHA-256("protocol-stack:economic-stress:evidence-v1\0" || canonical(input))

study_digest =
  SHA-256("protocol-stack:economic-stress:study-v1\0" || canonical(report
  without study_digest))
```

Report maps use lexical keys. Runs retain defined case/seed order. Reverse
codes sort lexically. The default eight-seed study digest is frozen in the
research report and tests after independent replay.

## Command line and limits

The command is:

```sh
python3 simulation/economic_stress/study.py \
  --seed-start 0 --seed-count 8
```

`--output` writes canonical pretty JSON with one trailing newline. Without it,
the same bytes are written to standard output.

Version one has exactly 27 cases and at most sixteen seeds, or 432 runs. It
accepts no manifest or event file and exposes no new untrusted protocol byte
decoder. The three accepted simulator decoders remain responsible for every
constructed manifest and event. Any invariant error, unexpected adapter error,
digest mismatch, or two-pass replay mismatch aborts the study.

## Evidence and compatibility

Tests cover:

- the fixed direction and matrix fixture;
- exact level balance and all pair combinations;
- seed and seed-count boundaries;
- deterministic repeated construction and replay;
- honest threshold availability and sub-threshold denial;
- exact-threshold compromise and higher-threshold resistance;
- exact target-event adapter release and owner-event exclusion;
- successful and unavailable rotation, containment, and recovery;
- full and partial entitlement funding;
- fee, treasury, reward, bond, unbonding, and penalty conservation;
- objective, reverse-code, and classification consistency;
- all three accepted simulators' focused regression suites; and
- command-line output identity.

The study changes no accepted simulator schema, event, error, state, metric,
digest, or adapter behavior. It changes no M1 canonical bytes, state roots,
persistence, ABCI behavior, supply policy, or CometBFT validator set.

An incompatible study design, factor mapping, scenario, objective,
classification, report shape, or digest requires economic stress study v2.
No result can become a production parameter without narrower experiments,
empirical assumptions, independent economic and security review, and a
separate consensus-visible specification with activation and migration.
