# Economy scenario suite v3

Status: Accepted M3 evidence contract; not a consensus transition and not a
new model

This document fixes the deterministic multi-year and adversarial scenarios that
the accepted models must survive under `founder-economy-simulator-v3` and
`escrow-payout-v3`, completing the dependent rebinding M3.6 began.

The change is classified as evidence, not economics.
[ADR 0031](../decisions/0031-scenario-suite-rebinding-to-economy-v3.md) records
the alternatives and decision. It changes no M1 bytes, C++ state, configured
devnet supply, and no accepted schema, vector, or digest of any earlier
contract.

## Relationship to version two

[`economy-scenario-suite-v2.md`](economy-scenario-suite-v2.md) is not edited.
Its versioning section requires a new suite version for a changed scenario
parameter, and version three changes two.
`test-vectors/economy-scenario-suite-v2.txt` remains normative and passing,
because `simulation/founder_economy_v2/` is untouched.

Scenarios 2 and 3 are shared between all three versions without a parameter, and
that is re-proved rather than inherited. The Founder Seat sale and revenue
routing models import nothing from any economy package and carry no supply
figure, channel cap, channel identifier, referral amount, or issuance-cycle
count, so their generators, digests, and recorded values are identical in all
three vector files, which the three files show directly.

Scenarios 1 and 4 change. Scenario 1 must now name an activation height per seat
and emit records that cover exactly each window's in-scope set; scenario 4 binds
the version-three economy state through the `escrow-payout-v3` binding.

## What changed in scenario 1

| | v2 | v3 |
| --- | --- | --- |
| Seat record | referrer only | referrer and activation height |
| `cycle_window` | supplied, unchecked | the window the accepted grid assigns |
| Record seat set | every population seat, every window | exactly the window's in-scope set |
| Seats activated | 4 | 6 |
| Evaluated seat-cycles | 2,193 | 2,194 |
| Windows with an empty winner set | 0 | 1 |
| Boundary probes | 9 | 16 refusals plus 3 accepted peer events |

### The activation heights are forced

The tick remains the shared `cycle_window`, because that is the property
scenario 1 exists to demonstrate. Holding it fixed, `cycle-boundary-v1`
determines the heights:

```text
activation_height(k) = k * STAGGER * CYCLE_BLOCKS,  STAGGER = 61
first_cycle_window(k) = k * STAGGER + 1
window_for_cycle(k, t - k * STAGGER) = t + 1
```

Window equals tick plus one for every seat and every cycle it evaluates. No
seat's first window is the unreachable 0, and the heights are non-decreasing in
seat order, which satisfies the monotonicity condition version three enforces at
the writer when the activations are emitted in that order.

### A seat enters the record when its own schedule opens

The in-scope set of window `w` is every seat activated strictly before `w`'s
first height, so at tick `t` the record lists `{ k : k * STAGGER <= t }`. It has
no upper bound: seat 0 stops issuing at tick 730 and remains in every later
record, because the reallocation rule asks for the highest uptime in the window
rather than the highest among seats still issuing.

| seat in the window | uptime, seconds |
| --- | --- |
| the failing seat | 3,600 |
| the intended winner | 86,400 |
| every other seat | 64,800 |

Every other seat sits exactly on the 64,800-second threshold, so the
founder-directed boundary is exercised in every reallocating window rather than
only in a dedicated unit test.

### One window has no eligible recipient

Seat 0 fails its cycle 0 at tick 0, where it is the only seat in scope. It cannot
reward itself, the derived winner set is empty, and the founder-directed rule
carries the whole 342-unit portion forward to the next reallocating window.

This is the only such window, and the count is a recorded vector rather than a
remark. It has to be, because the monetary totals do not reveal it: the carried
portion is delivered at tick 73 to the same seat that would otherwise have
received it at tick 0, so every channel total and every per-seat custody figure
is exactly what a closed form assuming no carry would produce. The three
population seats' custody is identical to version two's for that reason.

### The probe block

`PROBE_SEAT` opens in the first window after the run's last and never evaluates
successfully, so it supplies the unevaluated key every uptime and window probe
uses. `PEER_SEAT` shares its activation height, and `LATE_SEAT` opens one window
later.

`PEER_SEAT` exists because version three checks a window before it checks the
binding. A contradictory record can only be presented inside a window the
evaluating seat genuinely holds, and a window is only bound by an accepted
evaluation, which `PROBE_SEAT` cannot supply for its own cycle without that being
a replay. The peer's three accepted events bind a record at the probe window; the
contradiction probe then presents a higher uptime for `PROBE_SEAT` than the bound
record carries, and is refused.

The four intrinsic checks are probed before the peer binds anything and the
contradiction after it, which is the model's own rejection order. A rejected
event binds nothing, so the refused records leave the window free.

Every result code version three added is reached by one of these probes.

## Required scenarios

1. **Population.** Three seats, staggered 61 ticks, each completing all 731
   cycles from a recorded activation height, with disjoint failed cycles,
   derived reallocation, one window with no eligible recipient, unconditional
   accrual for every seat-cycle, and nineteen appended boundary events.
2. **Seat concentration.** Exactly 100 principals at the 1,000-seat bound
   absorbing the whole 100,000-seat capacity. Unchanged from version one.
3. **Routing population.** 122 accounting cycles over a changing active
   population, 25 of them empty. Unchanged from version one.
4. **Escrow drain.** Every escrow drained and every envelope exhausted against
   custody the version-three population run itself issued, bound through the
   `escrow-payout-v3` binding.

## Invariants this suite requires

- Issued plus outstanding plus remaining capacity equals 5,699,395,010,000,000,000
  atomic units in every run.
- Typed custody equals issued supply.
- `issued(founder_operator) + outstanding(founder_operator) + performance_carry`
  equals the evaluated permission count times 34,200,000,000.
- The performance carry ends at zero, including after a window that carried its
  whole portion.
- Referrer custody plus the unreferred performance pool equals the referral
  channel's whole issuance.
- Every accepted `cycle_window` is the window the accepted grid assigns to its
  seat's `cycle_index`, and every record covers exactly its window's in-scope set.
- One record is bound per window and shared by every seat evaluating in it.
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

[`economy-scenario-suite-v3.txt`](../../test-vectors/economy-scenario-suite-v3.txt)
is normative. `tools/scenario-suite-vectors/expected_v3.py` imports nothing from
`simulation/`. It re-uses `expected_v2.py` for the revised constitution's
economy literals and `expected.py` through it for the seat schedule and routing
shares, and loads the window grid from
`tools/cycle-boundary-vectors/expected.py`. What it adds is version three's own
consequences: the forced activation heights, the in-scope set per window, and a
walk of the founder-directed reallocation rule that carries an unrewarded
window's portion forward rather than assuming every failed cycle finds a
recipient.

Every monetary total must agree with that closed-form derivation before it is
compared with the recorded file, so a vector only the model reproduces is a
failure rather than evidence.

The verifier must fail closed in six ways, all confirmed by execution at exit 1
with the unmutated run as a positive control:

1. a tampered recorded value;
2. a recorded key no derivation reaches;
3. a derived key the file does not carry;
4. the v3 verifier run against the v2 vector file;
5. a closed form that assumes every failed cycle pays a seat in its own window;
6. a generator that lists every seat in every window, as version two did.

The fifth is the informative one. It reproduces every monetary total in the
scenario and is still rejected, because the run reaches the empty-winner path
once and `economy.unrewarded_windows` records that it did.

Every accepted verifier and simulation test must be registered as a `ctest`
entry, which `tests/tools/test_registration_test.py` requires directly. A test
that runs only locally is not evidence a hosted matrix produced.

## Open gaps this suite does not close

Every gap named in version two's corresponding section remains open except the
two the enforced schedule closes, and the rest are unchanged:

- The uptime record is still supplied. Nothing here proves an `uptime_seconds`
  value reflects a real machine. Completeness is now enforced, so a record can no
  longer omit an in-scope seat, but a supplied measurement is still a fixture.
- The `cycle_window` is no longer unchecked. It must be the window the accepted
  grid assigns, which is the gap version two recorded and this version closes.
- Accrual into the unreferred performance pool is modelled; paying it out is
  not, because the month definition and the pool's tie and remainder rules
  remain open founder decisions.
- The seat sale, the economy simulator, and the routing model remain unjoined. A
  seat's schedule is now defined given an activation height; what authorizes an
  activation — the payment, enrollment, and biometric preconditions — is not.
- Restart equivalence is state equivalence under replay, not persistence,
  crash-consistency, or a snapshot format.
- A long run that conserves value proves accounting. It proves nothing about
  activity fairness, snapshot honesty, creator legitimacy, or approval quality.
