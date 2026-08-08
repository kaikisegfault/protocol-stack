# Economy scenario suite v2

Status: Accepted M3 evidence contract; not a consensus transition and not a
new model

This document fixes the deterministic multi-year and adversarial scenarios that
the accepted models must survive under the direction the Founder Constitution
adopted on 2026-08-07, completing requirement 3 of
[`first-goal.md`](../project/first-goal.md).

The change is classified as evidence, not economics.
[ADR 0026](../decisions/0026-dependent-model-rebinding-to-economy-v2.md) records
the alternatives and decision. It changes no M1 bytes, C++ state, configured
devnet supply, and no accepted schema, vector, or digest of
`founder-economy-manifest-v1`, `founder-economy-simulator-v1`,
`founder-economy-manifest-v2`, `founder-economy-simulator-v2`,
`founder-seat-schedule-v1`, `revenue-routing-v1`, `escrow-payout-v1`,
`escrow-payout-v2`, or `economy-scenario-suite-v1`.

## Relationship to version one

[`economy-scenario-suite-v1.md`](economy-scenario-suite-v1.md) is not edited. It
already records that its scenario parameters were superseded on 2026-08-07 and
that a version two suite derives them instead of supplying them, and its
versioning section requires a new suite version for a changed scenario
parameter. `test-vectors/economy-scenario-suite-v1.txt` remains normative and
passing, because `simulation/founder_economy/` is untouched.

Scenarios 2 and 3 are shared between the versions without a parameter. The
Founder Seat sale and revenue routing models import nothing from either economy
package and carry no supply figure, channel cap, channel identifier, referral
amount, or issuance-cycle count, so they are identical under both economy
contracts. Their generators, digests, and recorded values are the same in both
vector files, which the two files show directly.

Scenarios 1 and 4 change. Scenario 1's generator changes shape rather than
parameters, and scenario 4 binds the version-two economy state through the
`escrow-payout-v2` binding.

## What changed in scenario 1

| | v1 | v2 |
| --- | --- | --- |
| Cycle activity | supplied `activity_result` | derived from a cycle uptime record |
| Failed-cycle recipient | supplied allocation list | derived same-window winner set |
| Referral | `evaluate_referral_permission` plus an exercise | one unconditional `accrue_referral` |
| Referral of an unreferred seat | not created | credited to the unreferred performance pool |
| Exercise | carries `permission_kind` | no permission kind |
| Boundary probes | 5 | 9 |

Two supplied research decisions disappear entirely. Version one supplied the
activity verdict and the performance recipient because the Founder Constitution
had not yet decided them; both are now decided, so this suite supplies
measurements and the model derives the answers.

### The tick is the shared cycle window

At tick `t` the seat activated at tick `k * STAGGER` evaluates its own cycle
`t - k * STAGGER`, with `STAGGER = 61`. The tick is the `cycle_window`.

This is the reason a window is a separate field from a seat's `cycle_index`.
Three seats staggered 61 ticks apart hold different cycle indices in the same
window, and reallocation to "the highest uptime in that same cycle" is only
meaningful against a shared one. A suite that reused `cycle_index` as the window
would have asserted that every seat's cycles coincide, which the constitution's
own activation rule contradicts.

### The uptime record carries measurements only

Every population seat is listed in every window, whether or not it is inside its
own issuance window, because uptime measures a running node while the issuance
window is an accounting concept.

Uptimes are assigned by a pure function of the tick, which is what lets every
seat evaluating in one window present the identical record. A record is bound by
digest on first reference, so any disagreement would be rejected rather than
silently accepted.

| seat in the window | uptime, seconds |
| --- | --- |
| the failing seat | 3,600 |
| the intended winner | 86,400 |
| every other seat | 64,800 |

The intended winner holds the only maximal uptime, so the derived winner set is
a single seat, the equal split has no remainder, and the performance carry ends
the run at zero. Every other seat sits exactly on the 64,800-second threshold,
so the founder-directed boundary is exercised in every reallocating window
rather than only in a dedicated unit test.

The phase shift keeps the three seats' inactive cycles disjoint in every window.
The generator asserts this rather than assuming it: two failures in one window
would make the winner set depend on evaluation order and would quietly change
what the recorded totals mean.

### An unevaluated key for the uptime probes

A fourth seat is activated and never evaluates a cycle, because all three
population seats consume their whole 731-cycle windows. Three probes share that
seat's cycle 0 and are ordered so each reaches a later rejection than the last:
a missing record, then a record omitting the evaluated seat, then a well-formed
record contradicting the one already bound to window zero.

## Required scenarios

1. **Population.** Three seats, staggered 61 ticks, each completing all 731
   cycles, with disjoint failed cycles, derived reallocation, unconditional
   accrual for every seat-cycle, and nine boundary probes.
2. **Seat concentration.** Exactly 100 principals at the 1,000-seat bound
   absorbing the whole 100,000-seat capacity. Unchanged from version one.
3. **Routing population.** 122 accounting cycles over a changing active
   population, 25 of them empty. Unchanged from version one.
4. **Escrow drain.** Every escrow drained and every envelope exhausted against
   custody the version-two population run itself issued, bound through the
   `escrow-payout-v2` binding.

## Invariants this suite requires

- Issued plus outstanding plus remaining capacity equals 5,699,395,010,000,000,000
  atomic units in every run.
- Typed custody equals issued supply.
- `issued(founder_operator) + outstanding(founder_operator) + performance_carry`
  equals the evaluated permission count times 34,200,000,000.
- Referrer custody plus the unreferred performance pool equals the referral
  channel's whole issuance, which is what "consumed exactly" means.
- No channel exceeds its manifest cap.
- A rejected event writes nothing and journals nothing.
- Each escrow conserves independently, and no payout touches two escrows.
- Restart equivalence: a replayed prefix reaches the digest the full run held at
  that point.

## Versioning and compatibility

This suite is additive evidence over accepted contracts. Changing a scenario
parameter changes its recorded digests and requires a new suite version; it does
not affect any model's schema or vectors.

If a future change to an accepted model's canonical state shape alters a digest
recorded here, this suite must fail rather than adapt. That is the intended
coupling: the scenarios exist to notice such a change.

## Required vectors and evidence

[`economy-scenario-suite-v2.txt`](../../test-vectors/economy-scenario-suite-v2.txt)
is normative. `tools/scenario-suite-vectors/expected_v2.py` imports nothing from
`simulation/`; it restates the revised constitution's literals by hand and
re-uses `expected.py` only for the seat schedule and routing shares, which no
economy revision touches.

Every monetary total must agree with that closed-form derivation before it is
compared with the recorded file, so a vector only the model reproduces is a
failure rather than evidence.

The verifier must fail when a recorded key is never derived, when a derived key
is not recorded, and when any recorded value is tampered with. All three, plus
running the v2 verifier against the v1 vector file, are confirmed by execution;
the last fails first on the superseded maximum supply.

## Open gaps this suite does not close

Every gap named in version one's corresponding section remains open, and two are
sharpened rather than closed:

- The uptime record is supplied. Nothing here proves an `uptime_seconds` value
  reflects a real machine, and a record that omits seats yields a winner set over
  the seats it does list. The challenge construction, sampling rate, dispute
  window, and dispute resolution are M3.4 work.
- The `cycle_window` is supplied and unchecked. The model cannot verify that a
  window is the correct one for a seat's cycle index, because the cycle boundary
  in heights or epochs is undefined.
- Accrual into the unreferred performance pool is modelled; paying it out is
  not, because the month definition and the pool's tie and remainder rules
  remain open founder decisions.
- The seat sale, the economy simulator, and the routing model remain unjoined.
- Restart equivalence is state equivalence under replay, not persistence,
  crash-consistency, or a snapshot format.
- A long run that conserves value proves accounting. It proves nothing about
  activity fairness, snapshot honesty, creator legitimacy, or approval quality.
