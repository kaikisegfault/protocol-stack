# ADR 0031: Rebinding the economy scenario suite to founder-economy-simulator-v3

- Status: Accepted
- Date: 2026-08-11

## Context

[ADR 0029](0029-founder-economy-simulator-v3-enforced-boundary.md) accepted
`founder-economy-simulator-v3`, which enforces the cycle boundary and record
completeness, and [ADR 0030](0030-dependent-model-rebinding-to-economy-v3.md)
rebound the escrow payout model to it. The scenario suite is the last accepted
model still binding version two, and it binds both of the others: its escrow
drain reads the escrow model, and its population run reads the economy model.

`economy-scenario-suite-v1.md` already records that a changed scenario parameter
requires a new suite version, and ADR 0026 applied that rule for version two. The
question this ADR settles is not whether to version, but what version three's two
enforcements do to a scenario that was written when neither existed.

## Decision

### The activation heights are forced, not chosen

Version two's population run supplied a `cycle_window` the model could not check.
Version three rejects any window that is not the one the accepted grid assigns to
a seat's `cycle_index`, so the scenario must now name an activation height per
seat, and the height is not free.

`economy-scenario-suite-v2.md` states why the tick must remain a *shared* window:
reallocation to "the highest uptime in that same cycle" is only meaningful
against a period several seats can be compared over, and per-seat windows would
rank a population of one. Holding that fixed, `cycle-boundary-v1` determines the
rest. A seat `k` activated inside window `k * STAGGER` opens at `k * STAGGER + 1`,
so at tick `t` it holds cycle `t - k * STAGGER` in window `t + 1`; window equals
tick plus one for every seat, no seat's first window is the unreachable 0, and
`k * STAGGER * CYCLE_BLOCKS` is non-decreasing in seat order, which satisfies the
monotonicity condition version three enforces at the writer by emitting the
activations in that order.

The heights are therefore a derivation from two accepted artifacts, not a
scenario parameter with alternatives. The suite records them and a test recomputes
the whole mapping from the grid rather than from the generator's arithmetic.

### An early window has no eligible recipient, and that is recorded rather than avoided

A record must now cover exactly its window's in-scope seat set, so a seat enters
the record at the tick its own schedule opens instead of appearing in every
window from the first. The consequence is concentrated in the first window: seat
0 fails its cycle 0 while it is the only seat in scope, so it cannot reward
itself, the derived winner set is empty, and the founder-directed rule carries
the whole 342-unit portion forward.

Three ways to avoid this were considered and rejected.

Moving the failure phase so the first cycle never fails would delete the only
path in the suite that reaches the empty-winner rule at population scale, which
is a founder-directed rule that version two's scenario never exercised.
Activating the population seats at one shared height would make every seat's
cycles coincide, which is the defect ADR 0027 records per-seat windows would
cause, in the other direction. Listing every seat from the first window — version
two's habit — is now simply rejected, which the fail-closed evidence demonstrates
by execution.

So the path is kept and the count is recorded as a vector. That matters because
the totals do not distinguish it: the carried portion is delivered at the next
reallocating window, to the same seat that would have received it, so every
monetary total in this scenario is what a closed form assuming no carry would
produce. Only `economy.unrewarded_windows` separates the two, and the fail-closed
evidence confirms that a closed form making version two's assumption reproduces
every amount and is still rejected on that one vector.

### A peer seat, because the window check now precedes the binding check

Version two reached `INCONSISTENT_UPTIME_RECORD` by presenting a record for a
foreign window. Version three checks the window first, so that event now reaches
a window code and the contradiction condition becomes unreachable by that route.

A contradictory record can only be presented inside a window the evaluating seat
genuinely holds, and a window is only bound by an accepted evaluation. The probe
seat cannot bind its own window and then contradict it, because the second
evaluation would be a replay. A second seat sharing the probe seat's activation
height is therefore required, and it makes the probe better rather than merely
possible: the refused event is now a seat presenting a higher uptime for itself
than the record already bound for that window says, which is the adversarial form
of the condition rather than a bookkeeping mismatch.

A third seat, activated one window later, supplies the out-of-scope seat that
`SEAT_NOT_IN_SCOPE` needs. All three probe seats are excluded from every
population record by their heights rather than by event order, so the population
totals remain statements about the three population seats.

### The probe block covers the seven added codes

Version two's suite had nine probes. Version three's has sixteen refusals and
three accepted peer events, and every result code version three added is reached
by one of them. The intrinsic checks are probed before the peer binds a record
and the contradiction after it, which is the order the model's own rejection
sequence requires; a rejected event binds nothing, so the six refused records
leave the probe window free.

### Scenarios 2 and 3 are re-proved, not inherited

ADR 0026 recorded that the Founder Seat sale and revenue routing models are
identical under any economy contract. That claim is re-established here by
execution rather than carried forward: a test asserts those two packages contain
no economy import, channel identifier, or supply figure, and a second test
requires every `seats.` and `routing.` vector to be byte-identical across all
three accepted suite vector files.

### Unregistered evidence is a gate, not a note

While registering the version-three verifier and tests, five test files and two
verifiers added by ADR 0029 and ADR 0030 were found to have no `add_test` entry
in `CMakeLists.txt`. They passed locally and were reported as slice evidence; the
hosted matrix never ran them.

Registering them exposed a second defect underneath the first. `ctest` invokes a
test as `python3 <path>`, and four of the five were written for
`unittest discover`: they used a package-relative import and inserted no
repository root on `sys.path`, so run as scripts they failed at import. The
recorded evidence for those 63 tests was therefore produced by a command the
gate would never issue. They are repaired here to the convention every other
registered test already follows, and all 63 pass both ways.

Both defects are now guarded by `tests/tools/test_registration_test.py`, which
requires every simulation test, every executable vector verifier, and every
recorded vector file to be reachable from a registered `ctest` entry, and every
simulation test to carry an entry point and no package-relative import. That
guard runs under the focused metadata path, so it fires on every pull request
including a documentation-only one, which is the case where the omission is
easiest to miss.

The two defects are the same mistake seen twice: evidence was counted from the
command that happened to be run rather than from the command the gate runs. A
static guard is the right remedy because it is the *absence* of an invocation
that has to be detected, and no run can detect its own absence.

## Consequences

- `economy-scenario-suite-v3` is accepted. `economy-scenario-suite-v1.txt` and
  `-v2.txt` are byte-for-byte unchanged and still pass, as do all three escrow
  versions and every earlier verifier.
- Scenario 1's recorded totals differ from version two's, because the run has one
  more evaluated seat-cycle: the peer seat's. The per-seat custody of the three
  population seats is unchanged, which is the carried portion being delivered
  rather than lost.
- The suite now binds three economy contracts through one `SuiteBinding` table.
  Version three loads the accepted version-two manifest through the version-two
  loader, because version three re-versioned no channel, cap, leg, or
  denomination.
- No v1 or v2 artifact, no C++, consensus, or devnet behavior, and no accepted
  model package changed. This slice adds evidence, not economics.

## Alternatives considered

- **Editing `economy-scenario-suite-v2` in place.** Refused by version one's own
  versioning section and by ADR 0024 and ADR 0026. The version-two vector file
  names the exact evidence the M3.3 slice was accepted against.
- **Bounding the in-scope set at a seat's last issuance window** so a finished
  seat leaves the records. Refused for the reason ADR 0029 records: the
  founder-directed rule asks for the highest uptime in the window rather than the
  highest among seats still issuing, and the bound would make the producing and
  consuming ends derive different sets from one schedule.
- **Dropping the contradiction probe** rather than adding a peer seat. Refused:
  the condition is still reachable in the model and a suite that stopped
  exercising it would lose coverage the previous version had.

## Compatibility and independent review

This ADR changes no consensus behavior, no canonical encoding, and no
founder-directed value. It settles no reserved decision: the activation heights
are derived from accepted artifacts, and an activation height is recorded rather
than earned.

The limits ADR 0027 and ADR 0028 record are not narrowed by this slice. Running a
longer scenario against an enforced schedule does not make the measurement
sound, and nothing here proves that a supplied `uptime_seconds` reflects a real
machine. Those remain part of the independent review requirement in
`first-goal.md` requirement 15.
