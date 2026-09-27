# M3 exit audit: Founder Economy Devnet

Date: 2026-09-27. Audited commit: `3c5347b` on `main`.

This audit is [`first-goal.md`](first-goal.md)'s requirement 16 attempted. Every
requirement is stated here against three things: the accepted artifact that
defines it, the executed check that tests it, and the hosted run that ran the
check. **Fourteen of the sixteen are met, two of them with recorded limits.
Requirement 14 is not met against the current contract. Requirement 16 is the
closing act, and it waits on 14. So M3 does not close yet.** The slice that
meets requirement 14 is named below.

The hosted evidence is two runs over one tree:

- run 36349364692, which passed all six checks on the PR head `30e13c1`;
- push run 36350191741 on `3c5347b`, the same tree merged by rebase.

Under the GCC presets ctest ran 168 entries, and under `clang-sanitizers` 177.
All five CometBFT integration runs passed.

## The sixteen requirements

"Met with a limit" means the requirement's words are satisfied, and something
the reader might assume they cover is not. The limit is stated under the table,
never folded into "met".

| # | Requirement | Status | Evidence on `main` |
| ---: | --- | --- | --- |
| 1 | `founder-economy-manifest-v2`, ten caps summing to 56,993,950,100 at eight decimals, vectors and digest | Met | `test-vectors/founder-economy-manifest-v2.txt` and its v3 rename (a channel identifier only; ADR 0053); ctest `founder-economy-v2-manifest`, `founder-economy-v2-vectors`, `founder-economy-manifest-v3`, `founder-economy-manifest-v3-vectors` |
| 2 | Revised independent Python model: unconditional direct-mint referral and unreferred pool | Met | `simulation/founder_economy_v2`, `founder_economy_v3`; the contract models `economy_transition_v3` through `v9`; ctest `founder-economy-v2-*`, `founder-economy-v3-*` |
| 3 | Seat, routing, escrow, and scenario models re-verified against v2, digests regenerated, verifiers fail closed | Met | ctest `founder-seat-*`, `revenue-routing-*`, `escrow-payout-v2`, `escrow-payout-v3`, `scenario-suite-v2-vectors`, `scenario-suite-v3-vectors` |
| 4 | An exact cycle boundary in heights, no wall clock reachable from a transition | Met | `cycle-boundary-v1`; `calendar-v1` for months, read from an attested consensus timestamp; ctest `cycle-boundary-*`, `calendar-*` |
| 5 | Canonical keys, encodings, and numeric receipt codes for the named transitions | Met | `economy-transition-v9`, incorporating versions three to eight; ctest `economy-transition-v9-cpp`, `economy-transition-v9-vectors` |
| 6 | An exact compatibility boundary against M1 bytes, state, and roots | Met | `economy-transition-v9` §Compatibility boundary; the codec suite reproduces the M1 accounts tree root |
| 7 | A deterministic uptime record: validator duties, challenge-response, a bounded AI dispute window | Met with a limit | `uptime-measurement-v1`; kinds 20 and 21 executed in C++ and Python; ctest `uptime-measurement-*`, `economy-transition-v9-execution-cpp` |
| 8 | Activity at 18 hours per cycle with a fragmentable 6-hour grace | Met | `uptime-measurement-v1` fixes it as 18 of 24 slots; decided from measured evidence from version eight onward, where the recorded `measured` scenario fails a seat on its evidence alone |
| 9 | Performance reallocation to exact ties, remainder and zero-winner cycles to the recovery pool | Met | `economy-transition-v7` onward (ADR 0054); ctest `economy-transition-v7-settlement`, `economy-transition-v9-execution-cpp` |
| 10 | C++20 implementation, checked integer arithmetic, no floating point | Met | `src/v9/`; no `float` or `double` in any consensus source |
| 11 | Cross-language fixed vectors both implementations reproduce | Met | `economy-transition-v9.txt` and `-execution.txt` reproduced by `economy-transition-v9-cpp`, `-execution-cpp`, and the Python verifiers |
| 12 | Storage bounds at 100,000 seats | Met | `economy-transition-v3.txt` `storage.*`; `economy-transition-v8` seat-window bound; `economy-transition-v9` §Resource bounds |
| 13 | Adversarial four-node scenarios through restart and recovery | Met with a limit | ADR 0090, ADR 0091; the two version-nine four-validator integration runs |
| 14 | Positive, negative, boundary, replay, overflow, atomicity, and multi-year scenarios at the M2 standard | **Not met against the current contract** | see below |
| 15 | ADRs stating transition shape, encoding, compatibility boundary, and remaining independent review | Met | ADRs 0077 to 0081; each specification's "does not establish" section, consolidated below |
| 16 | Hosted verification on the accepted commit, and a handoff naming the first M4 slice | Open | waits on requirement 14 |

## Requirement 14 is the one not met

**The multi-year leg ran against a contract that no longer exists.** The M2
standard is a population run over every seat's 731 cycles, with multi-year,
market, and property tests. `economy-scenario-suite-v3` does that against
`founder-economy-simulator-v3`, which still carries `performance_carry_atomic`.
Three later changes are not modelled there:

- the recovery pool that replaced the carry (ADR 0049, ADR 0054);
- activity derived from measured uptime (version eight);
- the unreferred pool paid by calendar month (`unreferred-pool-payout-v1`,
  version nine).

The current contract's models reach long horizons only in targeted scenarios.
Version seven records an eight-cycle settlement schedule and one machine past
its own 731 cycles. Version nine's settlement machine runs a sampled sequence up
to window 155. **Neither is a population run over the whole distribution.** So
the claim the M2 standard exists to make — that every channel ends exactly where
the manifest says, across every seat's whole life — has not been made for the
rules the chain now executes.

**The other legs are met against the current contract**, with one limit:

- positive and negative: 239 contract vectors and 125 execution vectors;
- boundary: the calendar's C1 to C5 edges;
- replay: `REPLAY` and `NONCE_MISMATCH` on a four-validator network;
- atomicity: a refused block writes nothing, in the driven replica;
- overflow: covered only by inherited evidence. No version-nine vector
  exercises overflow in version nine's own additions. Version six's execution
  vectors and version three's contract carry the inherited cases.

**The slice that meets it** is a fourth scenario suite that drives the current
contract's window-level settlement, as the M2 suite drove its simulator. The
chain itself cannot be driven over a whole distribution. Version nine's
`advance_to` refuses to skip heights once a seat is active, because every height
audits.

The settlement can be driven instead. Version nine's own `_assignment`, in
`simulation/economy_transition_v9/block.py`, handles one due window. It
composes four pieces:

- `derive_assignment`, version seven's step with the recovery pool;
- `referral_accrual`;
- `close_month`, `unreferred-pool-payout-v1`'s monthly payout;
- `Ledger.apply_assignment`.

It reads the window's uptime records from the ledger. So a suite can supply
those records per window and assign every window of every seat's life. The run
must show four things across the whole distribution:

- every Founder Node channel delivers exactly what the manifest promised for
  the cycles that ran, with the recovery pool at zero once a winning cycle takes
  it;
- the referral channel's identity holds at every window;
- every calendar month's pool is paid to that month's best performers;
- no unit is issued twice or lost.

Its fixture is a research population and a stated uptime pattern. Neither is a
founder value.

## Recorded limits

- **Requirement 7.** Validator-duty evidence is satisfied vacuously.
  `uptime-measurement-v1` consumes a duty assignment and never computes one, and
  no active-set protocol assigns duties yet (ADR 0063). The challenge's answer is
  an abstract predicate, because its content sets what an operator must own to
  be paid, and that is founder-reserved.
- **Requirement 13.** A network whose quorum is down for more than 60 seconds
  never produces another block under the accepted C5 (ADR 0089). Every restart in
  the evidence falls inside that window. A partition is not produced, because the
  harness cannot block a peer's port (ADR 0073).
- **Requirement 14.** The overflow limit stated above.

## Three open items, and where each belongs

- **ADR 0048's threat model** for local HUB verification belongs to M4.
  `first-goal.md` places identity decisions and biometric capture outside M3,
  and no requirement names it.
- **ADR 0089's outage wall** is a limit on requirement 13, not a failure of it.
  It must be settled before any network is expected to survive an outage, which
  is the public testnet's M10 at the latest. It needs a new contract version.
- **ADR 0071's audit on a network** is outside M3 by ADR 0071's own decision.
  Reaching it needs a nonzero initial height or a snapshot-seeded devnet, and
  either is its own slice.

## Independent review owed, in one place

Requirement 15 asks the ADRs to state what remains for independent review. They
do, one specification at a time. These are the items:

1. **The challenge sampling rate's security margin.**
   `uptime-measurement-v1`, `economy-transition-v8`.
2. **The beacon's bias.** A proposer can influence who is challenged. ADR 0027,
   `economy-transition-v8`, `economy-transition-v9`, and
   `consensus-application-v2` record it, and the timestamp widens a quiet
   block's grinding surface by about 2^16.9.
3. **Duty-report completeness**, once an active-set protocol exists.
   `uptime-measurement-v1`.
4. **An operator's self-directed allocation.** ADR 0034.
5. **The HUB-key lockout trade.** ADR 0036.
6. **The biometric stabilisation scheme**, for cryptographic review before
   anything rests on it. ADR 0048.
7. **Escrow payout, revenue routing, and seat custody**, which are
   founder-reserved and later-milestone work. `escrow-payout-v1`,
   `revenue-routing-v1`, `founder-seat-schedule-v1`.
8. **The protocol, cryptography, economics, biometrics, bridges, AI,
   reproducible builds, recovery, and operations as a whole.** The charter's
   safety position requires this before any production readiness claim.

## The founder-decision gate of `first-goal.md`

It held. No eligibility or anti-abuse mechanic was invented for the
liquidity-mining, impermanent-loss, HUB-verified-user, or mini-gamified
channels:

- kind 6, `direct_issue`, refuses every sender while its authority predicate
  is undecided;
- the HUB-verified-user rate and entry airdrop are founder answers (ADR 0042);
- no AI funding framework exists in any source.
