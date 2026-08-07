# Founder Economy proof report v1

Status: reproducible M2 evidence about deterministic accounting; not production
tokenomics, not an economic-safety assessment, and not a mainnet-readiness
claim

> **The direction this report measures was revised on 2026-08-07**, after the
> report was accepted, by
> [ADR 0023](../decisions/0023-founder-decisions-activity-referrals-and-supply.md).
> The maximum supply became 56,993,950,100, the referral benefit doubled and
> moved to the direct-mint channels, and the activity and performance rules
> that this report lists as unresolved are now decided. Every figure below
> remains an accurate statement about `founder-economy-manifest-v1` and the
> models built on it, which is what was actually proved. It is not rewritten,
> because a report edited to match a later decision would no longer be
> evidence of anything.

## Question

`m2-founder-economy-proof.md` asked for an exact, reproducible, independent specification and
simulator for the founder-directed native economy before any C++ consensus
behavior changes, and for a report that distinguishes proved accounting from
unresolved policy and production safety.

This report answers the second half. It states what six accepted contracts, five
verifiers, and a multi-year scenario suite actually establish, and — at greater
length, because it matters more — what they do not.

The distinction is the point. Every number below is reproducible from the
repository. None of them shows that the modelled economy is a good economy.

## What is accepted

| Contract | ADR | What it fixes |
| --- | --- | --- |
| `founder-economy-manifest-v1` | 0017 | the eight-decimal `u64` denomination, all ten issuance-channel caps, and the 731-cycle derivation |
| `founder-economy-simulator-v1` | 0018 | seat activation, base and referral permission evaluation, atomic exercise, and capped direct issuance |
| `founder-seat-schedule-v1` | 0019 | the 100,000-seat capacity, the block price schedule, and the 1,000-seat per-principal bound |
| `revenue-routing-v1` | 0020 | the 45/45/10 commercial split, the 22.5/22.5 creator case, and 100% transaction-fee routing |
| `escrow-payout-v1` | 0021 | the three escrows, bounded spending capabilities, and custody conservation |
| `economy-scenario-suite-v1` | 0022 | the multi-year and adversarial scenarios the other five must survive |

Each is an independent standard-library Python model with frozen fixtures,
normative vectors, and a verifier. None is a consensus transition. Together they
changed no M1 transaction bytes, no C++ state, no devnet supply, and no bridge,
wallet, AI, biometric, or resource behavior.

## Method

Five verifiers derive every recorded value from live runs and fail closed in
both directions: a derived key the file does not carry is a failure, and a
recorded key no implementation reproduces is also a failure.

Independence is established differently per contract, because the cheapest
honest check differs:

- the manifest verifier recomputes 2,297 canonical JCS bytes and the manifest
  digest from the checked-in file;
- the seat verifier walks the constitutional price rule block by block;
- the routing verifier replays the scenario through a `walk.py` that shares no
  code with the model and uses the naive share form;
- the escrow verifier does the same, carries the escrow caps as constitutional
  literals, recomputes the economy state digest with its own helper, and runs
  the economy simulator to prove the bound custody came from an accepted run;
  and
- the suite verifier re-derives every monetary total in closed form from Founder
  Constitution literals in a module that imports nothing from `simulation/`.

The last one is the strongest available check and the cheapest: a multi-year
total is fixed by multiplication, so arithmetic over the constitution beats a
second reading of the same specification.

The five verifiers need no build directory. Reproduce them with:

```sh
python3 tools/founder-economy-vectors/verify.py \
  --manifest-vectors test-vectors/founder-economy-manifest-v1.txt \
  --simulator-vectors test-vectors/founder-economy-simulator-v1.txt
python3 tools/founder-seat-vectors/verify.py \
  --vectors test-vectors/founder-seat-schedule-v1.txt
python3 tools/revenue-routing-vectors/verify.py \
  --vectors test-vectors/revenue-routing-v1.txt
python3 tools/escrow-payout-vectors/verify.py \
  --vectors test-vectors/escrow-payout-v1.txt
python3 tools/scenario-suite-vectors/verify.py
```

The scenario suite verifier takes about 24 seconds; the rest are near-instant.

## Evidence

| Contract | Tests | Vectors derived |
| --- | ---: | ---: |
| Founder Economy manifest and simulator | 67 | 204 |
| Founder Seat schedule | 49 | 96 |
| Revenue routing | 57 | 200 |
| Escrow payout | 57 | 169 |
| Scenario suite | 48 | 133 |
| **Total** | **278** | **802** |

The scenario suite derives its 133 vectors across 107,812 events in four
scenarios: a complete 731-cycle run over three staggered seats, the maximally
concentrated 100,000-seat sale across exactly 100 principals, a 122-cycle
routing run whose active population changes every cycle with 25 empty cycles,
and an escrow run that drains every escrow and exhausts every envelope.

Each verifier was confirmed to fail on a tampered value. The suite verifier was
additionally confirmed to fail when a recorded key is never derived, when a
derived key is absent from the file, and when a single constitutional literal in
its closed-form module is changed by one display unit — that last case fails
five vectors, including the maximum-supply accounting.

## What is proved

**The supply arithmetic is exact and closed.** 55,743,940,100 display units are
represented as 5,574,394,010,000,000,000 atomic units with no floating point
anywhere. Issued plus outstanding plus remaining capacity equals that maximum in
every run, and no channel's issued plus outstanding ever exceeds its cap. The
two constitutional subtotals add to the maximum exactly.

**Permissions are liabilities until exercised.** Unexercised units are not
issued supply, and one exercise either credits every beneficiary or changes no
state.

**A 731-cycle window ends at 731 cycles.** Three seats in different phases of
their windows each complete exactly 731 cycles, and cycle 731 is refused after
7,303 accepted events. Per-channel totals equal their closed forms, including
`3 × 731 × 34_200_000_000` for the Founder operator channel — a total unaffected
by inactivity, because a reallocation changes the beneficiary of the 342-unit
leg and never its amount.

**The seat bounds meet exactly.** 100,000 seats and 1,000 seats per principal
meet at exactly 100 principals, which is the smallest population that can absorb
the capacity. That sale yields exactly USD 4,231,855,000, derived independently
from the block schedule, and a saturated principal never consumes a seat.

**Routing conserves and its remainder is bounded by proof.** The remainder
depends only on `amount mod 200`, so scanning all 200 residues is complete: at
most 2 atomic units with one creator and 3 with two. Both pools conserve
independently, and an empty accounting cycle carries its whole pool forward
rather than burning it.

**Escrow containment is structural, not asserted.** Each escrow keeps its own
custody, paid-out total, and recipient balances, so no expression reads two
escrows together. Custody is fixed at the bind and non-increasing afterwards,
because `bind_opening_custody` is the only writer of a custody amount and
rejects once bound. Three conservation equations per escrow share no term, and
exhausted delegated authority and an emptied escrow report as distinct codes.

**Rejections are inert.** Across every run, a rejected event emits no journal
and leaves the state digest unchanged.

**Runs are reproducible and resumable under replay.** Identical ordered inputs
produce identical digests, a replayed prefix reaches the digest the complete run
recorded at that point, and a sequence applied in two parts reaches the digest
one call reaches.

## What is not proved

**No policy is validated.** Nothing here shows that the Founder activity metric
is fair, that an active-seat snapshot reflects a real machine, that a creator or
product is legitimately approved, that a payout recipient deserves funding, that
an AI evaluation is well made, that an approval threshold is safe, or that the
transaction-fee amount rule is sound. Conservation is indifferent to all of
these: value that is misdirected still balances.

**No provenance is established for supplied inputs.** Every activity result,
performance allocation, referral decision, eligibility result, active-seat
snapshot, payment settlement, and payout approval is a research fixture bound to
the action it authorizes. Binding proves a fixture cannot be reused elsewhere.
It does not make the fixture true.

**The escrow binding proves consistency, not provenance, inside the model.** The
model only recomputes the supplied economy state's digest, so a self-consistent
invented state would pass it. The verifier closes that gap from outside by
running the economy simulator itself; inside the model the manifest cap is the
only defence. That split is deliberate and is stated in ADR 0021 rather than
papered over.

**Restart equivalence is not persistence.** It is state equivalence under
replay. No model has storage, a snapshot format, crash-consistency, or a
recovery path, and this report claims none.

**Scale is bounded by what the models can run.** Three seats over complete
windows prove the per-seat and per-channel arithmetic; the full 100,000-seat
population over 731 cycles is 73.1 million cycles and was not run. The seat sale
is the only scenario executed at full constitutional scale.

**Nothing is a security claim.** Passing deterministic tests is necessary
evidence and never a bug-free, safe-custody, or production-readiness guarantee.
No independent protocol, cryptographic, economic, biometric, bridge, or
AI-authority review has occurred.

## Unresolved founder decisions

Four remain open and were deliberately not invented:

1. whether an inactive referred cycle creates the referral permission;
2. direct-mint channel eligibility and anti-abuse mechanics;
3. the Founder activity metric with its grace allowance, performance ranking,
   winner count, and tie rule; and
4. the AI funding framework with its evaluation criteria, milestone and tranche
   policy, and approval thresholds.

The scenario suite supplies thousands of instances of these from stated
deterministic rules recorded as scenario parameters — `(c + 7k) mod 73 == 0` for
inactivity, `(k + 1) mod 3` for the performance recipient, and so on. That is
volume, not resolution. A rule chosen to exercise both branches of an open
question is evidence that the model handles both; it is not an answer, and its
scale makes it more likely to be mistaken for one, which is why each rule is
written down as a parameter rather than buried in a fixture.

These become blocking at the M3 consensus transition.

## Remaining gaps

**The models are only partly joined.** `escrow-payout-v1` binds a recorded
`founder-economy-simulator-v1` state by digest, a one-way read the scenario
suite now exercises against a complete 731-cycle run. The rest remain unjoined:
a seat purchased in the sale model is not an activated seat in the economy
model, and a seat identifier in a routing snapshot is proved to be neither,
because the activation-height rule and the purchase-to-activation transition are
unsettled.

**Identity is absent.** Enrollment, biometric verification, managers, and
same-cycle liveness proof for a performance recipient are not modelled, and the
last cannot be without the unresolved performance policy. The per-principal seat
bound is not a per-human bound: nothing shows that two principal identifiers are
two people.

**Storage is unbounded.** The long runs make this concrete rather than
theoretical: the per-seat balance carry in `revenue-routing-v1` has no bound at
100,000 seats, and escrow recipient balances have none either.

**Credited value is not spendable.** No claim or push mechanism moves a credited
balance into an account that can spend it.

**A capability is a record.** The signed envelope, replay domain, and encoding
that would carry one on a real chain are undefined.

## What M3 must define

- the cycle boundary in chain heights or epochs, since local wall clocks cannot
  decide consensus;
- the purchase-to-activation transition that joins the sale to issuance;
- the signed capability envelope, its replay domain, and the AI decision receipt
  and audit trail;
- storage bounds for per-seat and per-recipient balances, and the path from a
  credited balance to a spendable account;
- persistence and the crash-consistency claim that replay equivalence only
  gestures at; and
- consensus receipts and numeric result codes, since every code in these models
  is a simulator result rather than a consensus receipt.

## Interpretation

The honest summary is narrow. Six contracts fix an exact integer economy; five
verifiers prove that independent implementations and closed-form arithmetic
agree with every recorded value; and a scenario suite shows the accounting holds
across 107,812 events, complete issuance windows, a full-capacity sale, an
absent population, and drained escrows.

That is a foundation for consensus work, not a validated economy. The arithmetic
is exact and the policy is open, and this report exists so the second fact stays
as visible as the first.
