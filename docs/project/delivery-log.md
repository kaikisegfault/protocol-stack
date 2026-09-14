# Delivery log

Every `How ... was delivered` record this project has written, moved here from
[`current-state.md`](current-state.md) on 2026-09-14 **verbatim**: not one line
is reworded, reordered, summarised, or dropped.

**What this document is for.** It is the per-slice account of how each piece was
built — the decisions taken, the alternatives rejected, the defects found, and
the lessons that outlived the slice. It is evidence and it is worth reading when
a question is about *why* something is the way it is.

**What it is not.** It is not the handoff. `current-state.md` remains the single
place that says what the project is now, what works, what is missing, what the
next unblocked action is, and what is blocked. **Read the handoff first**; come
here when it points you here, or when you need the history behind one of its
claims.

**Why the split happened.** `current-state.md` had reached 8,140 lines and
roughly half a megabyte, and every session is instructed to read it first. The
handoff had recorded the cost as its own slice for several sessions. Forty-seven
per cent of the document was this history, and it sat in exactly two contiguous
runs, each the tail of its parent section, so the cut ran along the document's
own structure rather than through any paragraph.

**A record here may describe superseded state.** It says what was true when the
slice landed. Where it disagrees with `current-state.md`, the handoff is
current; where both disagree with Git and verified test evidence, those win and
the handoff is what gets repaired.

## Delivery records

Newest first. Every record from `M3.15a` downward was moved verbatim out of the
handoff; `M3.15b` and anything after it was written here.

### How M3.16a was delivered

**Candidate run 34896935985 on `92eb982` passed all five jobs**, and the branch merged
by rebase as `b05f09a`. Issue #294 and PR #295 accepted
[`unreferred-pool-payout-v1`](../specifications/unreferred-pool-payout-v1.md).

**What it closes.** The unreferred performance pool has accrued since
`economy-transition-v3` — an unreferred seat's 34.2 units per cycle route to it,
version six gave it entry kind 12, and version seven's genesis writes it — and
**nothing has ever taken value out of it**. This is the rule that does: the
monthly candidate set, the ranking figure and which month a window's uptime
counts toward, the exact-tie split and the remainder, the carry, the point in the
sequence at which a month is paid, the quantities a binding ledger version must
carry, and when a referral benefit begins for a seat purchased and never
activated.

**Two findings in it are worth more than the arithmetic.**

**The payout does not fire in the block that opens a month, and that was this
specification's first rule.** `calendar-v1` establishes that the opening block is
the only point at which a *month* is final, and that is true of the month. It is
not true of the month's **figures**: a window is assigned `ASSIGNMENT_LAG_WINDOWS`
windows after it opens, so a month's last two windows are still unassigned when
the next month begins. Paying at the opening block would have ranked every seat
on a month with its last two days missing, **every month, silently**. The right
sequence is the **window-assignment** sequence, in which `month_of_window` is
monotone, so the first assigned window of a later month is exactly the point at
which every earlier month's figures are complete — `calendar-v1`'s own argument
applied to the sequence in which the inputs actually arrive rather than to the
sequence of heights. **It was found by checking a resource bound**, not by
reviewing the rule.

**The carry ADR 0075 decided is unreachable rather than merely unlikely.**
In-span implies in-scope by construction — `economy-transition-v8` defines
in-span as in-scope plus a span test — and in-scope has no upper bound, because
ADR 0049's rule 3 makes ranking permanent. So a month that accrued always has
someone to pay, and the zero-candidate case arises only before the first
activation, when the pool is empty. **That also closes the one question ADR 0075
deliberately left open** — a final accrual at the end of the distribution with no
later month to pay it — by derivation rather than by another founder decision.
The model checks the implication on **every** settlement rather than asserting it
once, so a later change that made in-scope expire fails a test instead of quietly
turning a safety net into a policy.

**Measuring a bound rather than asserting it corrected the specification twice.**
The document said two months accumulate at once, reasoning from the assignment
lag; the model measured **one**, because window assignment is ordered and
`month_of_window` is monotone, so a month's figures are complete and deleted
before its successor accumulates anything. And the per-month figure bound turned
out to depend on the **block rate**, which no consensus rule bounds from above —
`calendar-v1` bounds the timestamp against civil time and nothing bounds how fast
blocks are produced — so the accumulation is a **checked** addition rather than an
argued-safe one. **A bound that depends on an operational rate is not a bound.**

**One deduction closed a constitutional specification item almost for free.** The
constitution asks when a referral benefit begins for a seat purchased and never
activated. `cycle-boundary-v1` fixes `first_cycle_window` from the activation
height and the referral leg accrues per contributing cycle, so a seat with no
activation has no first cycle, is in no contributing set, and generates no leg to
route anywhere. It accrues **nothing, ever** — the question reads as though such
a seat might accrue to somewhere, and it does not.

**The evidence method is two constructions rather than one stated twice.** The
model is a machine: it consumes windows one at a time and carries a balance.
`tools/unreferred-pool-payout-vectors/expected.py` imports nothing from
`simulation/` and settles the whole sequence in **closed form**, grouping windows
by month and folding the balance forward. 116 vectors are recorded and every one
is produced by both.

**Seventeen mutation probes were run and every one was caught**, including the
rejected last-height attribution, the settlement order reversed, the accrual
applied before the payout, `in_scope` given an upper bound, the candidate set
read from the figures instead of the seat table, the remainder swept to the
winners, and three that drifted only the independent side. **The seventeenth
initially passed**, and what it found was that `assign`'s own conservation guard
had no test that could fail it: every other check called `assert_conserved`
directly. A test that corrupts the balance between two assignments now exercises
it, rather than the guard being recorded as untestable.

**The fixture's genesis sits deliberately off a day boundary.** At the commit
target a window is exactly one day, so a genesis at midnight would make every
window exactly one calendar day and **the straddling case would be unreachable**.
Six hours of offset is what makes window 1 begin on 28 February and end on
1 March, and the vector records the February figures the rejected last-height
rule would have produced beside the real ones, so the two attribution rules are
distinguishable rather than merely described.

**Facts a later session should not rediscover.** The model is
`simulation/unreferred_pool/`: `contract.py` the constants and three agreement
guards, `ledger.py` the `UnreferredPool` machine and `month_of_window`,
`scenario.py` the fixture. It **binds** `calendar-v1` rather than restating it —
a window's month comes from `simulation.calendar` via the timestamp of the
window's first height — and it owns no clock, no block rate, and no opinion about
a date. The two ctest entries are `unreferred-pool-payout-vectors` and
`unreferred-pool-payout`, and `verify.py --emit` rewrites the vector file through
the same agreement gate.

### How M3.15b was delivered

**This document is what M3.15b delivered.** Issue #290 and PR #291 moved every
`How ... was delivered` record out of `current-state.md`, which had reached
**8,140 lines** and roughly half a megabyte and which every session is
instructed to read first. The handoff had recorded the cost as its own slice for
several sessions, and M3.15a had just made it 250 lines worse.

**The cut ran along the document's own structure rather than through prose.**
The fifty records held 3,883 lines — **47% of the file** — and they sat in
exactly two contiguous runs, each of which was the *tail* of its parent section
and ended precisely at a `##` heading: lines 420-3936 closed `## Phase`, and
lines 4348-4713 closed `## What works now`. Nothing had to be cut mid-paragraph
and no record had to be separated from a neighbour it refers to.

**Nothing was reworded, reordered, summarised, or dropped, and that is
measured rather than asserted.** The split script counts the lines of the
original, of the two files it produces, and of the two pointer paragraphs it
adds, and requires the multiset identity to hold exactly; it raises and writes
nothing if a single line is unaccounted for. The two runs were **not** merged
into one ordered sequence either, because several records refer to the one above
or below them and reordering would have broken those references silently.

**The instruction that would have regrown it was changed in the same slice.**
`CLAUDE.md`'s work loop now says to write a slice's record in `delivery-log.md`
rather than in the handoff, and its first session step says the handoff is what
says what is true now while this document is history to be read on demand.
Splitting a file without moving the rule that fills it buys one session of
relief.

**Result: `current-state.md` is 4,270 lines**, a little over half what it was,
and it now holds only Phase, What works now, Adopted founder direction,
Repository state, Remaining gap, Exact next action, and Blockers.

### How M3.15a was delivered

**Candidate run 34889245697 on `def33fd` passed all five jobs**, and the branch
merged by rebase as `a5c3527`, `31e048b`, `9d5ccbe` and `0a54f22`. Issue #287 and PR #288 accepted
[`calendar-v1`](../specifications/calendar-v1.md) and
[ADR 0074](../decisions/0074-the-consensus-timestamp-and-the-calendar-month.md).
It is the first `change-protocol` slice in six, and the first contract accepted
since `economy-transition-v8`.

**What it closes.** ADR 0050 decided on 2026-08-19 that the ecosystem's clock is
the consensus timestamp in the block header and that a month is a real calendar
month beginning on the 1st, then named four things it deliberately did not fix:
the mapping, the boundary rule, the acceptance tolerance, and the derivation from
the header field. Four weeks later nothing had fixed them and
`economy-transition-v8` scoped them out by name. All four are now fixed.

**The four decisions, and the one that took the most research.**

* **The unit is a `u64` of milliseconds since the Unix epoch**, bounded at the
  last millisecond of 9999 so that every derivation below it is total. Seconds
  were reached for first — every founder-directed duration is stated in seconds
  and `cycle-boundary-v1` is denominated in them throughout — and were rejected
  because a chain catching up after a halt produces blocks faster than one a
  second, so a seconds field could satisfy a non-decreasing rule and could never
  satisfy a strict one. **The unit is permanent and the monotonicity rule may
  not be.** Nanoseconds end in 2262.
* **Monotonicity is non-decreasing.** A strict rule is a liveness hazard exactly
  when a network is already in trouble, and nothing here needs one: a height,
  not a timestamp, identifies a block.
* **The tolerance is 60 seconds and two-sided.** One-sided is unsound and it is
  the tempting simplification: a colluding proposer set stamping far *behind*
  would hold the chain's clock back indefinitely, never cross a month boundary,
  and pay nobody while satisfying every other rule. The floor is about 38
  seconds — twice a generous 10-second consumer clock skew, plus BFT time's
  one-commit-interval lag, plus CometBFT's own 15-second default `MessageDelay`
  — and the ceiling is ADR 0050's, that a proposer can move a month boundary by
  exactly the tolerance. 60 clears the floor by more than half again and is 24
  parts per million of the shortest month: at most 20 blocks of the 806,400 in a
  28-day month. **CometBFT's PBTS defaults were rejected deliberately**: a
  505-millisecond precision is right for a datacentre validator set and wrong for
  a consumer machine in a home, and the cost of excluding honest machines from a
  network whose purpose is that ordinary people run it is larger than 20 blocks
  of boundary.
* **The month is the proleptic Gregorian month in UTC**, index
  `(year - 1970) * 12 + (month - 1)`.

**Two findings in it are worth more than the constants.**

**C5 is not re-applied on replay, and C1 and C2 are.** The tolerance is the only
rule whose input is not in the block. A machine replaying history, restoring a
snapshot, or reconstructing state must re-check the range and the monotonicity
and must **not** re-check the tolerance, because the clock it would read is not
the clock that agreed the block — applying it would make a correct chain
unverifiable one tolerance-width after it was produced. The model exposes
`accept` and `replay` as separate entry points and the vector file records **one
stamp ten days out offered to both**, accepted by the replay path and refused by
the admission path, so the separation is falsifiable rather than described.

**A block closes a closed-open range of months, not one predecessor.**
Monotonicity requires only that time not go backwards, so a chain halted across a
month boundary resumes with a jump and every index between is an **empty month**
holding no heights at all. An opening block therefore closes every index in
`[month_of(h - 1), month_of(h))`. An implementation assuming a single predecessor
would silently skip a month's accrual the first time a network was down across a
boundary, which is the shape of defect that stays invisible until it is
expensive. The fixture halts across March and April 2026 so the case is a
recorded vector rather than a sentence.

**And one derivation that is a consequence rather than a choice.** A month's last
height cannot be recognised when it executes, because whether a later block falls
in the same month is not yet known. **The block that opens a month is the only
recognisable point**, so a transition acting on a completed month — the
unreferred pool's payout is the one this work exists for — executes there. No
other height is available.

**The evidence method is two algorithms rather than one stated twice.** The model
uses the closed-form era arithmetic; `tools/calendar-vectors/expected.py` imports
nothing from `simulation/` and builds the calendar by accumulating month lengths
from 1970, finding a month by binary search. 165 vectors are recorded and every
one is produced by both. **Four probes that drifted only `expected.py`** — its
leap rule, its month table, its tolerance, its rejection order — were each caught
by the agreement gate alone, which is what makes the independence a measurement.

**Twenty mutation probes were run and every one was caught.** The closed interval
opened, both tolerance edges made exclusive, monotonicity made strict, the
opening predicate made non-strict, the rejection order permuted, `replay`
re-applying the tolerance, the range check removed, the abbreviated leap rule,
the era arithmetic shifted, the day-index truncation changed, the range bound off
by one, the tolerance changed, and the epoch anchor moved. The probe harness
requires each mutation's text to occur **exactly once** in its file before
running, so a probe that silently changed nothing is reported as a miss rather
than as a pass — which is the M3.13l lesson made structural.

**The whole range is walked rather than sampled**: 2,932,897 days and 96,360
months, reported as mismatch counts. **2000 and 2100 are recorded** because they
are the pair the abbreviated "divisible by four" leap rule gets wrong in opposite
directions; a model tested only against 2024 would agree with the abbreviation.

**What it deliberately did not do.** The unreferred pool's payout — the candidate
set, the ranking snapshot, the height at which the payout executes, and the
treatment of an accrual with no candidate. It is the immediate successor, and it
carried two founder-reserved questions this slice did not. **Both were raised at
its close and answered the same day**; ADR 0075 records them, so the payout is
unblocked rather than waiting.

**Facts a later session should not rediscover.** The model is
`simulation/calendar/`: `civil.py` is the closed-form Gregorian pair, `months.py`
the timestamp-to-month derivation and its inverse, `chain.py` the ordered
acceptance rules and the month over a chain, `contract.py` the constants and
three guards, `scenario.py` the fixture. `tools/calendar-vectors/verify.py
--emit` rewrites the vector file through the same agreement gate, so a recorded
value is never transcribed; it takes about three seconds, and the cost is the
four-century walk that derives the 25-month seat-span bound. The three ctest
entries are `calendar-vectors`, `calendar-civil`, and `calendar-chain`.
**`simulation/calendar` does not shadow Python's `calendar` module**, because
only the repository root is ever added to `sys.path` and absolute imports resolve
`import calendar` to the standard library.

### How M3.14e was delivered

**Candidate run 34776763041 on `140ce72` passed all five jobs**, and the branch
merged by rebase as `453a9f5`, `b3a6a63`, `d088744` and `923d2d3`. Every preset
reports the grown claim:

```text
CometBFT four-validator version-eight integration: passed (4 independent
replicas, 2 registrations, 1 seat bought and activated at height 5, 5 confirmed
transfers, and 2 refusals -- NONCE_MISMATCH and REPLAY -- through 4 different
nodes, 2 full restarts, node 2 interrupted mid-block and fed a block its peers
never proposed, node 3 stopped while the other 3 committed to height 11 and
caught up on return, 4 durable C++ audits per stop)
```

The ctest suite is unchanged at **159** entries in the debug presets and **167**
under `clang-sanitizers`, because this slice adds no entry: it grows the hosted
integration that `tools/verify.sh` runs after ctest. Post-merge run 34777514884
on `923d2d3` passed all five jobs on its second attempt.

**Its first attempt was cancelled, and the reason is a process trap worth
avoiding rather than a defect.** `verify.yml`'s concurrency group is
`${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}`
with `cancel-in-progress: true`, so **merging a code PR and its documentation
closeout back to back cancels the code PR's post-merge run**: both pushes land
on `refs/heads/main` and the second evicts the first. The closeout's own run
then classifies `metadata` and skips the matrix, so `main` is left with no
completed full-matrix result even though nothing failed. Nothing was actually
unverified here — `git rev-parse` shows `140ce72` and `923d2d3` share tree
`e28e0b7e`, so the candidate matrix ran on exactly this code — but the evidence
a later reader looks for was missing until the run was restarted. **Either wait
for the code merge's post-merge run to finish before merging the closeout, or
re-run it afterwards.**

**This is the last piece of requirement 13, and its cost was in the Go harness
rather than in the test.** Three properties of `adapter/cometbft/internal/devnet`
made the scenario inexpressible, and M3.14d had already established all three by
reading the code: `Run`'s final `select` treated any child exit as fatal,
`compareHeads` required all four replicas converged, and `devnet transaction`
waited for that same health after broadcasting.

**The supervisor now accepts control requests on a Unix socket** at
`control.sock` in the socket root — `stop <index>` and `start <index>`, one line
each way — **and the request is executed inline on the main loop.** That is the
load-bearing choice rather than an implementation detail. `awaitUnix` and
`awaitTCP` read from the same `events` channel the watch loop reads, so a
handler running in the accept goroutine would race the watch loop for a child
exit and one of them would silently lose it: either a crash would go unnoticed
or a readiness wait would hang. The accept goroutine parses and forwards; the
loop runs the work and replies; there is exactly one reader of `events` at every
moment.

**A child the supervisor stopped is marked, and three places read the mark.**
The watch loop skips its exit and stays fatal for every other one;
`awaitEndpoint` and `awaitHealthy` skip it too, so a readiness wait during a
restart is not aborted by the exit of the child that restart replaced; and
`stopPhase` skips it at teardown, because its `done` value has already been
consumed and its log already closed, so reaping it twice would block until the
15-second shutdown timeout. The mark is written and read only on the main loop,
so it needs no synchronisation.

**Health now takes a replica subset**, threaded through `CheckHealth`,
`WaitForHealth`, `Broadcast`, and a `-nodes` flag on `health` and `transaction`.
**The subset is the set of replicas expected to be running**, not the set that
happens to be asked, and that distinction is what keeps the observation a check
rather than a relaxation:

| comparison | narrows with the subset? | why |
| --- | --- | --- |
| heads, roots, catching-up | yes | only a running replica has a head to report |
| peer sets | yes | three running replicas must see exactly two peers each, so a stopped replica still gossiping **fails** |
| validator set | **no** | it comes from a genesis file four homes share, and stopping a process does not retire its validator |
| genesis files on disk | **no** | read from disk rather than from an RPC |

[ADR 0073](../decisions/0073-the-devnet-supervisor-accepts-control-requests.md)
records all of it, including four rejected alternatives — signals instead of a
socket, a handler goroutine synchronising on `events`, stopping only the
CometBFT process, and letting health silently ignore unreachable replicas.

**The scenario is what all of that was for.** Node 3 is stopped alone; the
remaining three are required to be a healthy network in their own right; two
transfers commit through nodes 0 and 2; **node 3's own SQLite store is opened
directly and required to still hold the head it left at**; it comes back, all
four are required to agree on one head, and it submits the next transaction
itself. The durable audit afterwards covers its own database.

**Catching up is the claim, and it is the only path in this repository that
makes a replica execute a block it never saw proposed and never voted on.**
Every other execution any fixture produces is a block the replica participated
in agreeing. The store check while it is away is what makes the catch-up a real
claim rather than a restatement of health: a replica that had somehow kept up is
reported there instead of passing quietly.

**Three of four validators is the whole margin**, and the fixture says so.
Each holds ten voting power and CometBFT commits on more than two thirds, so
thirty of forty is exactly enough. A second departure would halt the chain
rather than test anything, and the control channel makes that easy to ask for by
accident.

**A stopped replica is not a partition, and this is now stated rather than
implied.** Blocking a peer's P2P port needs privileges the harness does not
have, and a two-two split would commit nothing on either side. **A genuine
partition therefore remains untested**, and the fixture, the ADR and this
document all say so in the same words rather than leaving prose beside them to
suggest otherwise.

**`tools/devnet.sh` gained the same three commands**, because it would otherwise
have dead-ended for exactly the operator who had just used one: its `health`
always asked about all four, and all four had stopped being the answer.
`health` takes an optional running-node list and `transaction` an optional third
argument, both defaulting to the whole network, so every existing invocation is
unchanged.

**Two defects the local checks caught, and both would otherwise have cost a
hosted round trip.** A divergence fixture that moved only the ABCI height was
actually testing *inconsistent head metadata*, because a node reporting two
different heights about itself is refused before the convergence comparison is
reached — **and the pre-existing `head` case had the same latent flaw**,
asserting only `err != nil` and therefore never noticing. Both now move both
heights and the metadata case is separate and named. And the catch-up health
call first asked for a 120-second budget inside a subprocess
`COMMAND_TIMEOUT_SECONDS` kills at 100, which would have reported a clean
failure as a `TimeoutExpired`.

**What the local evidence was, and what it was not.** `go build`, `go vet`, and
`go test -race -count=1` ran for `internal/devnet` and the devnet command,
offline against stubbed `nodeconfig` and CometBFT `config` packages with
**`GOPROXY=off`**, and all 12 tests passed — including a control round trip over
a real Unix socket in both directions, and an unreadable request that must get
one error line and leave the accept loop serving. Separately, the
ten-transaction sequence was executed end to end against the Python kernel with
a **stub signature oracle**, confirming that Alice's balance and nonces carry
the three new transfers at nonces 5, 6 and 7. The pinned libsodium 1.0.22 is not
built on this machine and the system copy is refused by `pinned_sodium`, so only
the signature octets differed; the economic path is identical. **None of that
touched a real devnet**, which the hosted matrix is for.

**The stub module is worth rebuilding rather than rediscovering.** It is a
scratch Go module declaring `go 1.23` and the real module path, with
`replace github.com/cometbft/cometbft => ./stub/cometbft` and a hand-written
`internal/nodeconfig` carrying only the surface the devnet package uses. Go
1.23 is what this machine has and the real module needs 1.25.7, so the test
files need one shim: `t.Context()` arrived in Go 1.24, and replacing it with
`context.Background()` in the scratch copy lets everything else compile and run.
Bootstrapping the real toolchain would be a 75 MB download `CLAUDE.md` rules
out.

### How M3.14d was delivered

**Candidate run 34720531772 on `745be42` passed all five jobs**, and the branch
merged by rebase as `6edd868` and `a958f82`. Every preset reports the grown
claim:

```text
CometBFT four-validator version-eight integration: passed (4 independent
replicas, 2 registrations, 1 seat bought and activated at height 5, 2 confirmed
transfers, and 2 refusals -- NONCE_MISMATCH and REPLAY -- through 4 different
nodes, 2 full restarts, node 2 interrupted mid-block and fed a block its peers
never proposed, 4 durable C++ audits per stop)
```

The ctest suite is unchanged at **159** entries in the debug presets and **167**
under `clang-sanitizers`, because this slice adds no entry: it grows the hosted
integration that `tools/verify.sh` runs after ctest. Post-merge run 34721129866
on `a958f82` passed all five jobs.

**M3.14c drove an application beside a fixture chain; this drives one replica of
a real one.** The store is node 2's own SQLite database from the four-validator
version-eight devnet, opened between the second and third runs of the network,
and it is asked two things no consensus engine on its chain would ask.

**The first is the mid-block interruption, and it needs no fault injection at
all.** `finalize_block` copies the durable head, executes the block in memory,
and stages what it produced; only `commit` writes. So terminating the process
between the two *is* the interruption requirement 13 names — exactly, and
without a test-only seam in production code. The block staged is the empty one
at the next height, which the model predicts **whole** through the new
`Session.block_if_empty`: root, identifier and receipt count. This devnet runs
with `create_empty_blocks = false` and commits only blocks that carry a
transaction, so it is a block **the network will never produce**, and the replica
and the model agree about it anyway.

**The second is a block its peers never proposed**, at a height two past the
head, refused by name and latching the node terminal.

**Neither claim is made by the process that provoked it.** A third process opens
the same store and must find the head the network left, so a stage or a refusal
that had written is reported there. Then the network starts again, converges on
that head, and commits a further transaction **entered through the replica that
was interrupted** — so a store it had damaged is reported by the block it
proposes rather than by a quiet disagreement four replicas never notice.

**One fixture addition, and the reason is that two callers want different
parts.** `Session.block_if_empty` returns the whole prospective empty block and
`root_if_empty` is one line over it. A refusal is a claim about the **state**
root; a replica staging a block nobody asked for is a claim about the **block**,
and the identifier commits to the header where the root commits to the state.
`_apply` and `block_if_empty` now build their `Block` through one `_block`
helper, so the two cannot drift.

**What the slice found about the next one, recorded rather than rediscovered.**
The obvious next scenario — a replica that goes down *while the other three keep
committing* — is blocked by two properties of the Go harness, and both were
confirmed by reading it rather than guessed. `compareHeads` requires **all four**
replicas to report the same height and root and none to be catching up, so
`devnet health` fails while any replica is down; and `devnet transaction` waits
for that same health after broadcasting, so nothing can be submitted while one
is down either. On top of that, `Run`'s final `select` treats **any** child exit
as fatal and tears the whole network down, so a replica cannot be stopped without
stopping the network. M3.14e therefore needs three things in
`adapter/cometbft/internal/devnet`: a control channel so the supervisor can stop
and start one replica, a watch loop that tolerates a deliberately stopped child,
and a health path that can be asked about a named subset. **All of it is
verifiable only on the hosted matrix**, because `internal/devnet` reaches
CometBFT through `nodeconfig`.

**And one local-verification attempt is on the record because it cost
something.** A scratch Go module was built to type-check `internal/devnet`
against a stubbed `nodeconfig`, and the first attempt ran with `GOFLAGS=-mod=mod`
and no `GOPROXY` guard. `health.go` imports `github.com/cometbft/cometbft/config`
under a **named** import, which a survey of unnamed import lines had missed, so
Go went and resolved the CometBFT module graph — 173 MB of module cache, which
`CLAUDE.md` forbids on this machine. It was removed immediately, and the home
caches were never touched. The second attempt stubbed the CometBFT `config`
package too and ran with **`GOPROXY=off`**, which makes an accidental download
fail instead of succeed, and it type-checked the package offline in seconds.
**`GOPROXY=off` is the guard worth keeping**; a grep for import lines is not.

**The slice's first candidate failed, and the failure was worth more than the
slice.** `clang-sanitizers` reported `RPC broadcast_tx_commit: context deadline
exceeded` — the message this document had twice called a flake — while the other
three presets ran the new scenario in full. It is not a flake; see the
correction below. The repair is the branch's second commit, and the new
scenario's three passing presets are what made it safe to conclude the failure
was not the slice's: the timeout fired roughly nineteen seconds into a
thirty-one-second test, in a submission that predates this slice, before the
third network run had begun.

**What the local evidence was, and what it was not.** The new scenario ran end
to end against a stand-in application implementing `application_v8.cpp`'s
sequencing over the Python kernel, and **five mutations of it were each reported
by name**: a stage that writes before the commit, a missing successor rule, a
refusal that does not latch, a staged block reported with another root, and a
replica that opens at a different head. `block_if_empty` was checked against
`apply_empty` for whole-block equality and checked not to spend the height, and
M3.14c's scenario and its ten mutations were re-run against the changed fixture.
**None of that touched a real devnet or the real application**, which the hosted
matrix is for.

### How M3.14c was delivered

**Candidate run 34716727961 on `c1e7a7c` passed all five jobs**, and the branch
merged by rebase as `648b576` and `c545b84`. Every preset reports the new entry
passing — `version-eight-driven-application`, entry 35, 0.39 seconds under
`gcc-debug` and 1.17 under `clang-sanitizers` for sixteen real process starts —
and the suite goes from 158 to **159** entries in the debug presets and from 166
to **167** under `clang-sanitizers`. All four hosted integrations still pass
unchanged.

**The slice's subject is the refusal class no fixture in this repository could
reach.** `ledger-transition-v1` has three. Admission failures and execution
failures were both already produced by a running node — M3.14b made four
replicas agree about two execution refusals. The third rejects the **whole
proposed block** and restores the pre-block state, and a mempool cannot deliver
one: CometBFT gossips every transaction to every replica and each replica builds
its own block, so no devnet can hand one node a block the others would refuse.

**So the block comes from beside the network.**
`tests/integration/driven_application_v8_test.py` drives a real
`protocol-application-v8` over its private Unix socket, carries it to height 3
with signed version-eight transactions from the chain fixture — `finalize_block`
then `commit`, with the independent Python model executing the same octets
beside it — and then hands it blocks no proposer on its chain could have built.
Seven refusals, each with its named status:

| provoked | answer |
| --- | --- |
| a block from the future | `SEQUENCE_FAILURE` |
| a block at a committed height | `SEQUENCE_FAILURE` |
| a block past `kMaximumAdapterHeight` | `INVALID_REQUEST` |
| a second block at a staged height | `SEQUENCE_FAILURE` |
| a commit with nothing staged | `SEQUENCE_FAILURE` |
| `init_chain` naming a foreign chain, height, or app state | `INVALID_REQUEST` |
| a second `init_chain` on a chain past genesis | `SEQUENCE_FAILURE` |

**The two wrong heights answer with two different statuses on purpose.** The
adapter bound is checked before a head is read and answers `INVALID_REQUEST`;
the successor rule is checked against the durable head and answers
`SEQUENCE_FAILURE`. A change that collapsed them into one guard would be
reported rather than absorbed.

**Every refusal is required to be terminal and to have written nothing, and the
second half is checked across a process boundary.** Each scenario is its own
process and opens on the head the previous one left, so a refusal that had
written is reported by the process that came *after* it. Two determinism claims
fall out of that and are stated rather than implied: two processes that were
never told each other's answer produce the identical root, block identifier and
receipt for the same block from the same durable head; and the chain is still
usable after a refusal, because the honest block at the refused height finalizes
and commits on the very next process. **`process_proposal` must not latch**, and
that is checked too — a replica that stopped every time a peer proposed a wrong
height would be trivially killable by one bad proposer.

**The slice found one thing it did not go looking for, and
[ADR 0072](../decisions/0072-the-wire-refuses-a-block-before-the-application-does.md)
records it.** The plan named `within_block_bounds` as a subject, and **from
outside the process that guard cannot be reached**. `read_transactions` enforces
the same three block bounds the application holds — 65,535 inputs, 1 MiB per
transaction, 16 MiB per block — and answers a violation with a `WireError`,
which `serve_with` turns into `protocol_failure` and `main_v8` answers by
dropping the connection and continuing. So a peer meets a **closed socket**
rather than a status, and the application never latches because it never saw the
request. All three copies of the bounds stay: the wire bounds what a peer may
make the process allocate, the application bounds what an in-process caller may
stage — `application_v8_test.cpp` reaches it — and only the kernel's is part of
the consensus contract.

**The wire framing became one description instead of two.**
`tests/application/application_driver.py` holds the frame format, the seven
message kinds, the three bounds, and the process lifecycle;
`headless_process_v8_test.py` was ported onto it and keeps every assertion it
had. Two of those now compare by type as well as by value, because
`ApplicationError::invalid_request` and the malformed-transaction admission code
are both 1 and an `IntEnum` would have equated them.

**A mutation probe found a real gap and the finding is why one scenario
exists.** Every commit but the last is checked across a process boundary for
free, because the next scenario opens the store and requires the head it left.
The last commit had nothing after it, so a `commit` that answered the staged
figures without writing them would have passed the whole file.
`check_the_commit_is_durable` is that missing process, and a stand-in store made
to drop exactly that one commit is reported by it and by nothing else.

**What the local evidence was, and what it was not.** `CLAUDE.md` forbids
compiling libsodium 1.0.22 and the C++ matrix on this machine, so **no local
check touched the real application**. What ran locally was a stand-in server
written from `wire_v1.cpp` and `response_v8.cpp` rather than from the driver, to
round-trip every request encoder and response decoder; and a stand-in
application implementing `application_v8.cpp`'s sequencing over the Python
kernel, against which the whole scenario ran end to end and **ten mutations were
each reported by name**. Those prove the scenario's control flow and that its
assertions are not vacuous. The C++ guards themselves are exercised only by the
hosted matrix on this commit, which is the evidence that matters and the reason
the branch was pushed before it was believed.

### How M3.14b was delivered

**Candidate run 34631946173 on `7347803` passed all five jobs**, and the
branch merged as `f88bcf7`. Every preset reports:

```text
CometBFT four-validator version-eight integration: passed (4 independent
replicas, 2 registrations, 1 seat bought and activated at height 5, 1 confirmed
transfer, and 2 refusals -- NONCE_MISMATCH and REPLAY -- through 4 different
nodes, full restart, 4 durable C++ audits per stop)
```

**One Go change was needed and it is in the harness rather than the protocol.**
`devnet.Broadcast` returned early on a nonzero `TxResult.Code` and skipped
`WaitForHealth`, so a refused transaction reported no `app_hash` — the one figure
the claim needs. It now waits for convergence on that path too. A **CheckTx**
rejection still reports none, deliberately: it never reached a block, so there is
no convergence to report. The command still exits nonzero for a refusal, because
for an operator it is still an error, which is why `run_refused_transaction`
expects the failure and parses its output rather than using `check=True`.

**A mutation probe passed, and the passing was the finding.** Making
`NONCE_MISMATCH` advance the nonce before refusing — a refusal that writes state
— **passed**, which would have been evidence of nothing. An instrumented re-run
showed the mutated line lives in `_fee_exempt_envelope_checks`, which only runs
for the challenge-response kind, so a transfer never executes it. Mutating the
real check in version six's `_envelope_checks` fails at once with `InvalidBlock:
a refused transaction changed the state`. **This is the third time this
repository has been caught by a probe that passed against code the test never
runs**, and the first time instrumenting rather than trusting it is what found
the truth.

**The finding changed what the new check claims.** `_execute_block` already
compares the state root across each transaction and raises on a refusal that
wrote, so the empty-block comparison in `execute_refused` is the same property
restated about the block the *network* committed, after the version-eight steps
ran — not an isolated guard. Today the two coincide because no seat is in scope.
The docstring says so rather than implying isolation it does not have.

**One local mistake is recorded rather than hidden.** `go vet` was run once in
the adapter directory; it resolved the module graph and populated about a
gigabyte of caches, which `CLAUDE.md` forbids on this machine. Both were removed
immediately with `go clean -modcache -cache`. **The lesson for a future session
is that `gofmt` is local-safe and every other Go command is not** — `go vet`,
`go build`, and `go test` all resolve the graph, and the hosted matrix runs all
three.

### How M3.14a was delivered

**The evidence is the four hosted integrations' own output.** Candidate run
**34629392463** on `5d450b8` passed all five jobs — the scope classifier and the
four-preset matrix — and the branch was merged by rebase, landing as `c7ac63b`
through `604ae9c` on `main`. Every preset reports the same two new lines:

```text
CometBFT version-eight integration: passed (2 registrations, 1 seat sold and
activated, 1 confirmed transfer, restart at height 2, durable height 5)
CometBFT four-validator version-eight integration: passed (4 independent
replicas, 2 registrations, 1 seat bought and activated at height 5, and 1
confirmed transfer through 4 different nodes, full restart, 4 durable C++
audits per stop)
```

**The devnet activated the seat at height 5** rather than at the fixture's
height 4, which is the fixture design working as intended: the model is driven
to whatever height the network reports rather than told, because a consensus
engine closes blocks the fixture did not ask for and an empty version-eight
block still moves the state root. The ctest suite stays at **158** entries in
the debug presets and **166** under `clang-sanitizers` — the fixture's own test
is entry 101, `version-eight-chain-fixture`, and it grew checks rather than
becoming a second entry.

**Three mutation probes were run against the new checks before the branch was
pushed, each naming a different one.** Dropping the `+ 1` from
`first_cycle_window` fails with "a seat activated in window 0 was reported as in
scope for window 0"; returning `{}` from `Session.activations()` fails with "the
recorded activation height is not the height the block ran at"; and reporting
every seat as activated fails with "the purchase at height 3 did not write one
unactivated seat". The four-validator check was probed the same way with three
constructed states. **This is the standing lesson applied rather than restated**:
a probe that passes has proved nothing until you have checked that it changed
the code the test runs.

**The probes ran under a deliberately fake signature provider and that is worth
knowing.** `pinned_sodium` requires libsodium **1.0.22**, which the CMake build
compiles from source, and `CLAUDE.md` forbids heavy local builds when a hosted
job can do the work. So the local probes used a hash-based stand-in in the
scratchpad — enough to exercise the transitions' acceptance, useless as
cryptography — and the real Ed25519 run is the hosted matrix's. Nothing of the
stand-in entered the repository.

**Four independent replicas sold and activated a Founder Seat on 2026-09-11.**
M3.14a put version eight's two seat transitions — kind 2 `purchase_seat` and
kind 3 `activate_seat` — under a real consensus engine for the first time. They
existed in the C++ kernel, in the independent Python model, and in recorded
vectors, and in nothing a CometBFT-driven node had ever executed: every
four-node run before it registered identities and moved value, and none sold a
seat. Both blocks land after a full restart, so the registry entry the purchase
reads is a row recovered from SQLite, and the five transactions enter through
four different replicas.

**The slice's more valuable output is a refusal.** A chain with an activated
seat reads as exercising version eight's uptime audit, and it does not. A seat
is in scope only from the window *after* the one it activated in, and
`CYCLE_BLOCKS` is **28,800**, so a seat a genesis-begun devnet can activate is
first audited at a height that devnet will not commit — and activating later
only pushes it further away. **This document asserted the opposite twice**, as a
claim about what the next slice would observe, and a slice planned against it
would have spent itself discovering a constant.
[ADR 0071](../decisions/0071-a-devnet-cannot-reach-the-uptime-audit.md) records
the wall and refuses all three ways across it: a nonzero initial height, because
the state root commits to the height and three layers reject anything but 1 on
purpose; a snapshot-seeded devnet, because no supported path exists to start
from one; and a shortened `CYCLE_BLOCKS`, because a fixture running against a
different cycle length agrees with itself about a chain nobody operates. **Two
fixture checks now derive the figure from the contract rather than transcribing
it**, so the claim cannot rot a third time.

### How M3.13j was delivered

**The version-eight uptime carrier is specified and none of it is implemented.**
`docs/specifications/economy-transition-v8.md` and ADR 0063 are accepted, and
they are the contract that lets a chain derive a cycle schedule instead of being
handed one. Documentation only: no source, build, workflow, dependency,
configuration, or vector file changed.

**The obvious three transaction kinds turned out to be two, and finding that is
most of the slice.** The handoff recorded a duty report, a challenge response,
and a dispute. A duty report cannot be a transaction: `uptime-measurement-v1`
states that a report "cannot be forged by the seat it concerns" *because the
chain produces it*, so whoever signs one asserts something no other node can
reproduce — which is the schedule-as-a-proposer's-opinion the slice was told not
to build. The honest mechanism is ADR 0050's attested claim and it cannot be
produced today, because a report is only ever produced for a duty the seat was
*assigned* and the active-set protocol that assigns duties is outside that
specification's scope and does not exist. The accepted specification already
states the consequence — an empty assignment is satisfied vacuously — so version
eight encodes no duty report at all, on version seven's own precedent of
declining to encode the ADR 0049 pool lifecycle because no transition could ever
set it.

**The storage design fell out of one observation.** A slot bit begins set and
evidence only ever removes credit, so a window record is written only for a seat
that lost or had a slot voided and an absent record reads as fully credited: a
healthy machine writes nothing. And because the chain materialises each
challenge into an entry at the height it is issued, the beacon — the previous
state root, which the block already holds — is read once and never retained, a
response becomes a state lookup, and the model's per-slot counters disappear
entirely. Selection excludes the final twenty heights of every slot, so clearing
a bit when a challenge expires is *exactly* equivalent to the model's
slot-close sweep, and there is no sweep over the population at a slot boundary.

**A dispute is relayed rather than signed by its authority's own account.** The
body carries a detached signature checked against a new genesis
`dispute_authority_key` and an ordinary signer pays the fee, which is kind 10's
`verifier_signature` pattern and the right shape under ADR 0047, where a
deciding machine issues one signed bounded decision and someone submits it. The
alternative would have given the ecosystem AI a chain account, a nonce sequence,
a balance, and a fee obligation that no accepted document gives it.

**Two departures from the accepted model are stated with their reasons.**
`RESPONSE_TOO_LATE` precedes `CHALLENGE_NOT_ISSUED`, because version eight
deletes an open challenge at expiry and checking issuance first would report
that a challenge which *was* issued never was. And the selection preimage is
octets rather than the model's RFC 8785 JSON, because a kernel canonicalising
JSON to decide who is audited would put a parser on the pipeline's most
adversarial path — so the chain and the model select different heights for the
same beacon, which the specification says outright and the vectors must not
paper over by comparing two functions that are not the same function.

**Two limits are recorded in the contract rather than discovered later.** The
duty layer is vacuous, so a seat's credit rests on the challenge layer alone.
And the answer predicate is the weakest available, because a challenge's content
is founder-reserved, so **version eight measures liveness of a responder and not
possession of a resource** — which is why `RESPONSE_INVALID` is deliberately not
declared: no path could produce it, and a later version binding a real predicate
can only tighten what an answer must satisfy.

**The cost is honest and large.** A new chain identity re-versions the snapshot,
the store, the application, the transport, the node process, and the ABCI
adapter, which took ten slices for version seven. Version seven cannot be edited
— its own versioning section fixes the kind space, the code space, and the state
key space as immutable — so the alternative was not available rather than
rejected.

### How M3.13k was delivered

**The version-eight carrier now executes in Python, and the first thing the
model did was find a defect in the specification it was built from.** The
genesis field table listed nine fields in the order a reader would name them and
omitted the two the encoding actually writes. The canonical order is the
encoder's — magic, schema version, network identifier, supply limit, **total
supply, then the fixed fee**, the initial fee pool, the manifest digest, the
verifier key, and the account count last. `total_supply` before
`fixed_transfer_fee` is the one a reader gets wrong from the struct declaration,
and version seven's decoder refuses a genesis whose re-encoding differs, which is
what makes the mistake loud. The addition was unchanged in substance and the
prefix is still 142 octets.

**`simulation/economy_transition_v8/` is eight modules and no copied table.**
`contract.py` classifies every name version seven exports — 100 carried, 16
revised, 18 added, and version seven's own five provenance names replaced — and
`tests/simulation/economy_transition_v8_carryover_test.py` requires the four sets
to partition that surface exactly and to say the truth about every member. That
catches the defect no derivation can: a value that moved without any vector
reaching it.

**`test-vectors/economy-transition-v8.txt` records 177 vectors**, every value
derived twice: once by a `tools/economy-transition-v8-vectors/expected.py` that
imports nothing from `simulation/`, and once by a live model run. The file is
produced by the verifier's `--emit`, which runs the same derivations through the
same agreement gate, so a file and its derivations cannot disagree at birth.

**The load-bearing vector is settled by version *seven's* model.** The derived
schedule is compared to an independently stated seat list, and that list is then
run through `simulation/economy_transition_v7/settlement.py` and its assignment
record recorded — so "the carrier changed no settlement" is evidence rather than
an assertion version eight makes about itself.

**Six aimed mutation probes, and the one that passed is the one worth
recording.** A probe making a dispute clear the credited bit passed uncaught,
because the encoder refuses the resulting state before any vector can compare —
so it proved nothing about the rule it named. Re-aimed at the *folded* bitmap
design ADR 0063 rejects, it fails four vectors at once, including
`kind21.refuses.dispute_replay`: folding makes that result code unreachable,
which the ADR argued and the probe now demonstrates. The other five — a changed
label, a dispute cap of seven, a dropped pad-bit check, an off-by-one deadline,
and the genesis keys transposed — fail between two and seven vectors each.

**The containment theorem is recorded at its exact boundary.** A seat credited
for every slot, after a maximal six-slot dispute, holds 64,800 seconds, which is
the founder-directed activity threshold to the second.

**The recorded plan for the C++ side was corrected on 2026-09-03 before anything
was built on it.** It read the version-eight kernel as the atomic replacement
ADR 0046 fixed for versions four and six, and that reading does not survive the
dependency graph: **twenty-three files outside `src/v7/` and
`include/protocol/v7/` now name `protocol::v7`**, so an atomic move is about
14,000 lines in one commit with nothing buildable until the last of them.
[ADR 0065](../decisions/0065-a-kernel-replacement-may-be-staged-across-a-stack-migration.md)
amends ADR 0046 to permit a **staged** replacement under a stated end, enumerates
the seven slices, and puts the deletion of version seven's kernel in slice seven
so a session reaching slice six finds it recorded as its next action.

### How ADR 0065 was delivered

**It is a planning correction found by attempting the work rather than by
reading about it.** The session created the kernel issue, branched, and began the
port; the dependency graph is what stopped it. `grep -rl 'protocol::v7'` over
`src/`, `include/`, and `tests/` returns twenty-three files outside the kernel —
the snapshot, the owning store, the application, the transport dispatcher and
responses, the node binary, two fuzz targets, and five test fixtures — none of
which existed when ADR 0046 was written, because the storage and application
layers were version one's until M3.13a through M3.13g.

**The amendment is narrow and its end is enumerated rather than intended.**
ADR 0046 refused keeping a *superseded* contract, and version seven is not
superseded during the migration: it is the contract six live layers are written
against and the only kernel a running node in this repository can use until slice
six. ADR 0046 also refused "retire it later", and the retirement here is a
numbered slice with stated content — and if the migration is abandoned part-way,
slice seven still runs and deletes `src/v8/` instead.

**One consequence is a slice the atomic reading had taken away.**
`economy-transition-v8.txt`'s 183 vectors split at **121 a codec can reproduce**
— the result-code space, the state key space, selection, the kind space, genesis,
the version identity, the roots, and the manifest binding — and **62 that need a
ledger**. So the kernel becomes the codec-then-execution pair versions four and
six were given, and M3.13n is the codec alone.

**One doubt was raised and resolved against itself rather than left open.**
Requirement 13's adversarial four-node scenarios were considered as an earlier
slice, on the ground that a disagreement test needs no version eight. They cannot
be: requirement 13 says *economic*, and the version-seven ABCI path hands
`execute_block` a null uptime schedule, so a chain driven through it writes no
cycle assignment and accrues nothing to any seat. Version eight is what removes
the parameter.

**The session ended here on a `conclude` instruction.** The kernel port was begun
— nine codec sources and the public header copied and rebound to `protocol::v8`,
with the header's constants, labels, kind space, entry space, code space, body
record, genesis field, and the selection and dispute declarations written — and
**it was removed rather than committed**, because M3.13n is the recorded next
slice and a conclusion does not begin one. Nothing of it is in the tree. What it
established and a fresh session should not re-derive is recorded under the exact
next action below.

### How M3.13l was delivered

**A version-eight chain runs, and it measures its own machines.**
`simulation/economy_transition_v8/` gained `ledger.py`, `execution.py`,
`transitions.py`, `receipt.py`, `block.py`, and `trace.py`, and
`test-vectors/economy-transition-v8-execution.txt` records **434 vectors over
four scenarios reaching all sixteen transaction kinds**. Every value two sources
can reach is derived twice, and the settlement claim is checked against version
*seven's* accepted derivation rather than against version eight's own model.

**The result worth reading is the `measured` scenario.** Alice answers every one
of fifty-four challenges the chain issues her across windows one and two and
writes **no window record at all**; Bob answers none, loses fifteen slots, and
fails his cycle at nine credited slots against the eighteen the founder-directed
threshold requires. Window one's assignment then makes Alice the sole winner:
she collects her own base permission and the one Bob failed to earn, plus the
referral leg his purchase accrued to her, and the recovery pool ends at zero on
every channel. **Nothing anywhere had to be told that Bob was offline.**

**The `disputed` scenario runs the containment theorem at its exact boundary.**
Six disputes are accepted against a machine that answered everything, a seventh
is refused by the cap, and a replay, a foreign authority key, and an open window
are each refused by name. The disputed seat keeps 18 slots — 64,800 seconds, the
activity threshold to the second — so it still meets its cycle and loses only its
place in the winner set. **The counterfactual is a fork of the very ledger the
dispute block executed against**, so "the dispute moved the winner set" is a
comparison of two real chains rather than an assertion: `(0, 1)` becomes `(1,)`.

**One rule had to be derived and it is the fee exemption's third consequence.**
The specification states two — a zero fee limit refused at admission, and a kept
nonce — and leaves the third to execution because it belongs to version seven's
shared envelope checks: **what the acting escrow must cover**. It is zero, so
`DEBIT_OVERFLOW` and `INSUFFICIENT_BALANCE` join `FEE_LIMIT_TOO_LOW` as
unreachable for kind 20. The alternative is not neutral — charging the fixed fee
would refuse a response from an escrow holding less than one fee, so an operator
would have to keep a balance in order to prove the uptime they are paid for,
which is exactly the cost the founder answer removes. The specification now
states the consequence in place and a vector records that fifty-four accepted
responses cost nothing at all.

**Three findings, each recorded as a vector rather than a sentence.**

1. **The prologue-before-issue order is normative and, at the accepted lag,
   unobservable.** A challenge issued at height `h` belongs to
   `window_of_height(h)` and the prologue deletes records for
   `window_of_height(h) - 2`, so with `ASSIGNMENT_LAG_WINDOWS` at 2 the two steps
   provably cannot touch the same entry. `issue_before_prologue` runs the
   alternative on a copy of the boundary block and the vectors record that both
   commit the same root. **A later version shortening the lag to one window would
   make that vector false first**, which is where it should be noticed.
2. **The expiry-after-transactions order *is* observable.** The same response
   accepted at `c + 20` is refused as `CHALLENGE_NOT_ISSUED` under the rejected
   order **and the seat loses the slot it had just proved**. One height later, at
   `c + 21`, it is `RESPONSE_TOO_LATE` and the entry is already gone — which is
   why condition 7 precedes condition 8.
3. **An unactivated seat's default activation height is zero**, so
   `first_cycle_window(0)` is 1 and such a seat reads as in scope for every
   window unless the issue step checks activation separately. A probe removing
   that check went **uncaught** until `measured` sold Bob a second seat he never
   runs; it now fails twenty-three vectors. The general form is the lesson this
   record already carries: a probe that passes is a question about the fixture.

**`advance_to` is refused once any seat is activated, and that is the habit a
version-seven reader has to unlearn.** Version six's shorthand stands in for a
run of empty blocks on the argument that such a block "changes height and
nothing else"; under version eight that is false, because the issue step and the
expiry step run at every height. It is still exactly true while no seat is in
scope, so the shorthand survives for the setup segment and raises everywhere
else. `block.run_quiet_heights` replaces it and executes every height —
**57,609 of them** in `measured`, which is the tail of window zero plus windows
one and two, because window one's assignment is not due until the first height
of window three. It costs about a second.

**What makes that affordable is `state.state_root_frame`**, which splits the root
preimage around its one field a quiet height changes. `state_root` is *defined*
through it, so there is one preimage in the module and the fast path cannot drift
from the root it stands in for; the economy tree is rebuilt only when the issue
step or the expiry step writes, which no transaction can do at a quiet height
because there are none. Recomputing the root from scratch at every height would
cost about 100 microseconds against 2.5.

**Three things are restated rather than imported, and each because a table
moved.** Version seven imported version six's `Outcome`, `admit`, and
`require_consistent` unchanged because it changed neither the kind space nor the
code space. Version eight changes both: `Outcome.code` would raise on all twelve
added names, `admit` would refuse a kind-20 transaction as unknown, and
`require_consistent` would refuse a conforming kind-20 receipt. Everything else
delegates to version seven's own `dispatch` **function object**, which a test
requires by identity.

**The uptime evidence is one raw key-to-value map and not a typed shadow.**
`Ledger.uptime` holds every kind-18 and kind-19 entry and is handed directly to
the accepted contract model's `Context`, so `submit_response` and `file_dispute`
— the functions the 183 accepted contract vectors were recorded against — are
*the* implementation rather than siblings of one.

**Eight of nine mutation probes are caught and the ninth is a theorem.** Changing
which slot an expiry clears — the challenge's or the expiry's — is a no-op,
because selection excludes the final twenty heights of every slot and the two are
therefore always the same slot. **Two probes are caught by the model's own
invariants rather than by a vector mismatch, and each names the rule it broke**:
removing the prologue's deletion gives "a seat window record outlived its
retention", and widening the dispute cap by one slot gives "a maximal dispute
failed a fully credited seat", because seventeen slots is 61,200 seconds against
a threshold of 64,800.

**One probe had to be re-aimed for the reason M3.11c recorded.** Flipping the
default of `expire_before_transactions` passed uncaught, because the deadline
scenario passes the flag explicitly on every branch and the mutation never
reached the executed path. Moving the step itself made it fail five vectors.

### How M3.13i was delivered

**Requirement 13's central claim now holds for version seven.** Four processes
that were never told each other's answer hold the same state root at the same
height, through a restart, having each executed the same blocks independently.
Alice registers through node 0, Bob registers through node 1, the network is
stopped and started, and Alice pays Bob through node 2 — **three transactions
entering through three different replicas**, because a node that agreed only
with the peer it heard from would pass a single-submitter run. After every stop
all four databases are opened directly and required to report the same head,
which asks the claim of the store rather than of the engine.

**The version reaches the genesis and every bridge from one place, and that is
deliberate.** The application state `Devnet.Ensure` writes is what the
application requires at `InitChain`, so a home written for one ledger version
and bridges started for the other is refused there rather than at the first
block — and a version configured twice is a version that can disagree with
itself. `devnet.Run` takes it once and hands it to both.
`protocol-cometbft-devnet start -protocol-version N` is parsed through
`nodeconfig.ParseProtocolVersion`, so a mistyped version is an error rather than
a chain nobody joins, and it defaults to one so every existing caller is
unchanged.

**The fixture became a live session, and the reason is a fact rather than a
preference.** An empty version-seven block still moves the state root, because
the root commits to the height. A frozen list of blocks is enough for a single
node driven one transaction at a time and is not enough for a network that may
close a block the fixture did not ask for. `version_seven_chain.Session` holds
the ledger live and the caller advances it to whatever height the network
reports before executing the next transaction against it; `build_chain` is three
lines over it and produces the same three blocks it always did. ADR 0062 is
amended in place rather than given a successor that would restate it with one
addition.

**The devnet harness is shared and the model deliberately is not.**
`tests/integration/cometbft_devnet.py` holds what is a property of the network
— the port block, the supervisor, health, submitting exact bytes through one
node, auditing every replica's durable head, and stopping — with the protocol
version as one field reaching both the supervisor and the audit. Each version
drives its own model and compares it against what the network reports, which is
the whole point of running four of them.

**Almost all of it was verified locally**, which is now the pattern for anything
that touches the fixture: `build_chain` still passes its four checks after the
refactor, a session interleaved with empty blocks produces five distinct roots at
five contiguous heights, a transaction that lands at height 5 because the network
closed two blocks nobody asked for is executed at height 5 by the model, and a
health report that disagrees with the model is refused. Only the Go changes and
the run itself needed the matrix.

**One thing was measured rather than assumed before pushing.** The previous
matrix's slowest job was 10m53s against a 20-minute timeout, so a second
four-validator run had margin. A slice that adds an integration run should check
that rather than discover it.

### How M3.13h was delivered

**The slice changed shape before it started, and checking the recorded fixtures
is what changed it.** The handoff said the next step was to emit the recorded
blocks' raw inputs into a vector file. Reading
`simulation/economy_transition_v7/trace.py` first found the sentence that makes
that impossible: *no signature is computed anywhere*. Every recorded
version-seven transaction carries an eight-octet counter padded to 64 octets,
recorded in an oracle that verifies by exact-match lookup, and
`tests/kernel/economy_v7_execution_fixture.hpp` issues byte-identical tokens so
the C++ trace reproduces the model's exact bytes. **That is right for a contract
fixture** — it makes every message-binding claim testable without the model
implementing cryptography — and it means `protocol-application-v7`, which opens
its store with `ed25519_verifier()`, would refuse every recorded input as
`invalid_signature`.

**So the slice built a second fixture rather than emitting the first.**
`tests/integration/version_seven_chain.py` derives keys from labelled seeds
through the pinned libsodium, builds the transactions, and runs the same octets
through the independent Python model to learn what each block produces. It is
version one's `tests/differential/cases.py` shape, which is the shape that
already works.

**The model needed no change, and that is why this was a fixture slice rather
than a model slice.** `execute_block` takes the signature oracle as an argument
and only ever calls `verify(public_key, message, signature)`, so a
libsodium-backed object is a drop-in for the recorded table. The seam was already
there.

**One transaction per block is a requirement rather than a simplification.** A
state root commits to the whole block, so reproducing a recorded block that holds
four transactions needs all four in one block in one order, and a mempool does
not give you that. Three blocks: two registrations, because a transfer to an
unregistered recipient is refused, then a confirmed transfer, because it is the
first block that moves value and charges the fee — a node that agreed to two
airdrops and then disagreed about a fee would pass a two-block fixture.

**Every comparison in the run is one implementation against another.** The
fixture derives the chain identity, the height-zero root, and each block's root
from the Python model; the binary derives the same two figures from the same
genesis file through `--genesis-identity`; the running node derives each block's
root by executing the octets. Three RPC claims are checked at every height and
they are different claims: `/status` is the app hash in the latest header, which
at height `H` is the state after `H - 1`; `/abci_info` is the application's own
durable head; and `block_results` must publish the recorded block identifier as
the `protocol_block` event M3.13g's bridge emits, which is what proves an
identifier ABCI has no field for survived the whole path.

**The restart is the third block rather than a separate case.** It is committed
by a process that did not execute the first two, so its root comes from a state
read back out of SQLite rather than one held in memory.

**Six mutation probes, and the first is the argument for the whole slice.**
Making `Signer.sign` issue stand-ins is refused by the model itself at
admission with code 3, `invalid_signature` — the finding demonstrated rather
than asserted. A stand-in spliced into a raw input, two blocks sharing a root,
and a version-six receipt version are each caught by the check that names them.
**One probe passed uncaught and was re-aimed**: a key that drifts only after
the fifth derivation never reached the executed path, because a rebuild derives
exactly five keys.

**The local check that made this affordable is worth keeping.** This machine has
libsodium 1.0.18 and the repository pins 1.0.22, and `pinned_sodium.Sodium`
refuses anything else — correctly. Ed25519 is Ed25519, so a scratch copy that
relaxes the pin (never committed, and it must stay that way) runs the fixture and
all six probes against real signatures in under a second. **Almost none of this
slice needed the hosted matrix to find its bugs**, which is the opposite of
M3.13g.

### How M3.13g was delivered

**The slice's one real design question answered itself, and reading the engine
is what answered it.** ADR 0058 recorded that `ApplicationV7` refuses a
`finalize_block` at any height that is not its current plus one — including one
it has already committed — and that the refusal is terminal, so an adapter had
to decide what to do when CometBFT replays. **CometBFT v0.39.4 never asks.** In
`consensus/replay.go`, the one branch where the application is ahead of the
engine's state loads its **own saved** `FinalizeBlock` response and replays that
height against a *mock* application built from it; the source comment says it
does not want to call `Commit` twice for the same block on the real app. Every
other branch replays from `appBlockHeight + 1`, which is `current + 1` at each
step because `ExecCommitBlock` commits each replayed block before sending the
next, or returns `ErrAppBlockHeightTooHigh` at the handshake without sending a
request at all.

**So the adapter reconciles nothing, and that is the finding rather than a
shortcut.** A reconciliation would have had to reproduce per-transaction
receipts that the stage no longer holds after `commit` and that the store never
recorded, so anything it answered would have been synthesised — the fabricated
agreement `ApplicationV7` exists to refuse. What the adapter adds instead is a
**guard**: a `FinalizeBlock` at a height at or below the one the application has
said it committed is refused before it is forwarded. The height comes only from
the application's own answers to `Info` and `Commit`, never from counting here,
so it can never exceed the height the application would accept and can never
refuse a legitimate `current + 1`. The cost is one comparison per block; the
benefit is that a version change or a misconfiguration produces an error the
engine stops on rather than a node bricked on a contradiction it did not commit.

**The Go client is version one's client and one different answer.** `ClientV7`
embeds `Client` and declares `FinalizeBlock`. The connection, the
request-identifier discipline, the terminal latch, the frame codec, and all five
request encoders are shared, for the reason ADR 0059 gives on the C++ side: a
second copy would be a second place for a framing rule to be wrong, kept in step
by discipline alone.

**Both shapes refuse each other, which is what makes `-protocol-version` safe.**
Version seven's decoder refuses version one's finalized block because the count
it would read is the identifier's leading octets, and version one's refuses
version seven's for the same reason in reverse. A client dialled at the wrong
version fails closed rather than misreading a block, and both directions are
tested.

**One `Application`, parameterized, rather than two.** Six of the seven ABCI
conversions name no ledger version, so `New` and `NewV7` differ by the codespace
and by whether a finalized block arrives with an identifier. That identifier is
a **pointer** in the bridge's own `FinalizedBlock`, because a zero hash would
have been emitted and indexed as though it named something.

**The block identifier becomes an indexed block event.** ABCI has no field for a
second identifier, and a value that crosses a process boundary and is then
discarded is the one a later simplification deletes. It is observable rather
than consensus-visible: a block event is not hashed into anything CometBFT
agrees on, and only a transaction result's code and data reach
`LastResultsHash`.

**The genesis application state is what pairs a home with a ledger version.**
`ApplicationV7` requires `"protocol-stack-v7"` at `init_chain`, so a mismatched
pair is refused there rather than at the first block. `protocol-cometbft-init`
takes `-protocol-version`, and its parser compares as the wider type, because
`ProtocolVersion(257)` truncates to one.

**The local check that mattered was a scratch module.** `internal/localapp`
imports no third-party code, so copying the package into a stdlib-only module
with `go 1.23` type-checks and runs it under the machine's own Go in under a
second — `go vet ./...` and `go test` both clean — without downloading the
CometBFT module graph the repository's resource rules forbid pulling locally.
The `bridge` and `nodeconfig` packages import CometBFT and could only be
verified on the hosted matrix. **The engine's own source was read the same
way**: two files fetched over HTTPS into the scratchpad rather than a module
download.

### How M3.13f was delivered

**Settling recovery corrected the fault contract.** The store poisoned itself on
any write failure, which was safe and wrong: everything before the commit rolls
back and writes nothing, so a fault there is an ordinary refusal — the durable
head is the one it already was and the same store accepts the same block once the
fault is gone. **A refusal that wrote nothing is not a reason to stop
answering**, and the test says so by clearing each fault and requiring the next
block's recorded root.

**Only the commit can leave a head this process cannot name.** There the store
poisons itself and then reads the file again: closes the connection, reopens it,
runs the same four validation steps an ordinary open runs, and adopts whatever
head the file holds. That head is the block's or its predecessor's because
SQLite's transaction is what decides, and nothing between is reachable.

**Recovery is allowed to fail and then the store stays poisoned.** It is
`noexcept` and answers `false`; a store that could not read its own file back
refuses to read a head, refuses to hand out a payload, and refuses every later
block. Worse state, honest answer, and it is tested by denying recovery through
`before_recovery_open`.

**The two termination cases are the property rather than an extra.** The process
is killed at `after_commit_before_publication` and at `after_publication` by a
re-executed child, and in both the parent must find the committed block durable
at its recorded root **and** continue the chain to the next block's recorded
root. Together with the rolled-back faults that is the whole claim: **a fault
anywhere in the write path leaves the durable head at the pre-block root or the
post-block root, never at anything between.**

**Version one's recovery suite was re-run locally**, because the fault seams this
slice wires are the ones it drives. Sharing a seam means sharing a blast radius.

### How M3.13e was delivered

**The decoder is the encoder's inverse and checks itself.** It reads the 110
canonical octets and then re-encodes what it read, returning a genesis only when
the result equals the input octet for octet. **The validity rule is therefore
stated exactly once**, in `encode_genesis` — a nonzero supply limit, a zero total
supply, a zero fee pool, no accounts — and a decoder with its own copy of those
four conditions would be a second opinion kept in step by discipline. The round
trip also catches what a restatement would not: a trailing octet, an
unrecognised schema version, and a field read at the wrong offset.

**That last one is not hypothetical.** `total_supply` is encoded *before*
`fixed_transfer_fee` while the struct declares them the other way round, so a
decoder reading in declaration order puts the fee where the supply belongs. The
test uses a distinctive nonzero fee for exactly that reason; a zero fee would
hide it, and the probe that swaps the two offsets fails.

**The binary opens before it creates**, because a create over an existing path is
refused by the store, so a restart is the ordinary case rather than a special
one. Its evidence checks it as a process against figures no process produced:
the recorded chain identity, and a height-zero root read **out of the recorded
`carried.block0.header`** — a header commits to its previous state root, and at
height one that is the genesis root.

**The hosted matrix caught something no local check could, and the shape
generalises.** `protocol_application_server_v7` was declared as a target and
never added to `PROTOCOL_STACK_TARGETS`, **which is the only place this project
applies the C++ standard, the warning flags, `-Werror`, and the sanitizers**. It
built at the compiler's default standard, so `operator<=>` and `std::span` in
long-standing headers stopped parsing and all four jobs failed on a tree that
compiled clean locally. **The scratch harness passes `-std=c++20` on every
invocation, so it can never reproduce this class at all.**
`test_every_built_target_takes_the_project_build_flags` now requires every target
the project builds itself to appear in that list, and removing the entry was
checked to make it fail. **Add a target in four places or the guard will tell
you**: `add_executable`, its properties, its link libraries, and
`PROTOCOL_STACK_TARGETS`.

**Two probes passed and neither was a gap.** Widening the genesis file's size
check from "exactly 110 octets" to "at most 4,096" broke nothing, because that
check is an **allocation bound** and not a validity rule — the comment now says
so instead of claiming a better error message. And accepting version one's app
state at `init_chain` is invisible to the process test; it fails in
`version-seven-application`, which owns that rule, and **that was re-run to
confirm the coverage rather than assumed**.

### How M3.13d was delivered

**The wire is version one's, reused unchanged, and that is the whole decision.**
The 20-octet header, the seven message kinds, the seven wire errors, and the five
request payloads carry no ledger-version meaning — a height, a transaction list,
a byte budget, an app state, a raw transaction. A second frame format would
differ from the first in nothing but its name while doubling the places a framing
rule can be wrong. The same argument reduces the socket to one connection loop
over a dispatcher.

**The responses are the version-specific half.** A finalized block carries a
**block identifier** version one's does not, because an adapter that could not
name the block it just executed could not tell a peer which one it agreed to; its
receipts are version seven's fifty-six octets with a version field of 7; and its
result codes are version seven's thirty-three.

**Every response is validated on the way out.** A receipt whose declared code and
encoded result byte disagree, a mempool answer carrying a receipt, a response of
the wrong type for its kind — each is refused rather than written. The adapter
has no ledger, no kernel, and no vectors, so the encoder is the last place a
disagreement can be caught, and catching it costs one comparison per result.

**The chain identity is converted explicitly.** `InitChainRequest::chain_id` is a
`TaggedHash` and therefore a distinct type from version seven's `Octets32`. Do
not "fix" that by loosening either type: the tag is what stops a state root being
passed where a chain identity belongs.

**Two of four probes found tests that did not exist.** A dispatcher that ignored
the application and always accepted a proposal passed, because the suite only
ever sent proposals that *should* be accepted; the fix is a proposal one height
ahead that must come back as a vote against, **sent before the block is staged**,
because a staged block refuses the same call for a different reason and the test
would then pass for the wrong one. And a socket wired to the wrong dispatcher
**aborted rather than failed** — an assertion inside the client block left the
server thread unjoined and `std::thread`'s destructor called `std::terminate`,
hiding the message. The block now captures the exception, lets the client's
destructor close the socket so the server returns, joins, and rethrows. **A test
that aborts instead of reporting is a test that will one day hide a real
failure**, and this is the pattern to check for wherever a thread outlives an
assertion.

### How M3.13c was delivered

**`finalize_block` is pure and `commit` is the check.** CometBFT calls the two
separately while `SQLiteLedgerV7::apply_block` writes the head and the block row
together and takes no target height beyond `current + 1`. Version one already
reconciles that and version seven keeps its answer: finalize copies the head,
executes in memory, writes nothing, and stages the root, the block identifier,
the per-input results, and the commit record it expects, answering an identical
repeat from the stage because CometBFT may ask twice. Commit replays the block
through the store, requires the store's commit record to equal the staged one,
then requires the durable head to be at the root the network was told. Anything
else latches the application terminal.

**Two refusals deliberately do not latch, and both are tested for it.** An
admission failure in `check_transaction` is a mempool answer, and a
`process_proposal` that votes against a peer's block is an ordinary answer about
a proposal. A node that bricked itself on a peer's bad block would be a liveness
hole rather than a safety property.

**`process_proposal` executes, where version one's only checks bounds.** The
reason is the kernel rather than taste: `execute_block` rejects whole blocks for
reasons version one's transfer kernel does not have, and meeting one at
`finalize_block` halts the node permanently. It needs no new store surface,
because `read_head` already returns a whole `v7::Ledger` by value — and **adding
a dry-run operation to the store would be a second way to execute a block**.
**No constructible input reaches that execution's own refusal today** and ADR
0058 says so outright: every whole-block rejection is either already refused by
the bounds check, since `kMaxRawInputs` and `kMaxAdmitted` are the same figure,
or is an invariant violation no conforming sequence reaches. It is insurance
against a kernel defect and it costs one execution of a block the node is about
to execute anyway. **The full cost is three executions per committed block** —
proposal, finalize, and the store's own — and each answers a different question;
the store must execute it because the store is what commits the head.

**One probe passed and that was the useful result.** Dropping rejected raw inputs
from the response was invisible to the whole suite, because **none of the
recorded blocks contains a rejected admission**. The fix was a better test, not a
better probe: appending eight zero octets to a recorded block must reproduce the
*same* recorded root and the *same* recorded block identifier — a refused
admission performs no state read or write and never enters the transaction root —
and differ only by one more result row carrying the admission code and no
receipt. Re-aimed against that case the probe fails, and so does a sixth that
offsets the rejected input's code into the execution range.

**A self-review before merge found the debt the ADR now records in place.** The
layer refuses, terminally, a `finalize_block` at any height that is not
`current + 1`, **including one it has already committed** — which is exactly what
CometBFT's replay handshake does to an application whose height is behind its
engine's. Version one behaves the same way. It is a property of the pair rather
than of either piece, so it is owed to the adapter slice rather than repaired
here.

### How M3.13b was delivered

**The head is one snapshot payload, not a row per entry.** Version one
decomposes its state into an `accounts` table; version seven stores the exact
bytes `encode_snapshot_v7` produces. The argument is the snapshot's own — it is
already the canonical projection of everything a state root commits to, already
checked against recorded roots, three gates, and a fuzz target — and a second
row-shaped projection would be a second opinion about what a state *is*, owed to
both sides for every future entry kind. What the schema keeps in its own columns
is only what a reopen must agree on *before* it trusts the payload: the canonical
genesis, the chain identity, the height, and the root. **The cost is accepted
deliberately**: a commit rewrites the whole head, which is `O(state)` per block,
and at the 100,000-seat capacity that is a large write. It is node-local, changes
no accepted state, and ADR 0007 reserves exactly that freedom for operational
data.

**The connection contract is version one's, reused unchanged.** Path reservation
and normalisation, the exclusive-create primitive, the lifetime lock, journal
handling, path-stability verification, the exclusive-transaction helpers, and the
fault-injection seams are all settled by ADR 0007 against the filesystem and
SQLite rather than against a ledger, so a second copy would be a second place for
a locking rule to be wrong. Version seven throws its own `FailureV7` and
translates version one's codes through an explicit mapping rather than a cast:
the two enumerations agree on every number they share, and the one they do not —
`invalid_archive`, which only the archive import raises — would become a value
outside the version-seven enumeration under a cast.

**The integrity check runs first and that ordering is load-bearing.** With it
removed, a database whose pages were overwritten reports `genesis_mismatch` —
which tells an operator they opened the wrong chain when in fact their disk is
failing. The check does not merely add a refusal; it is what keeps every later
comparison from lying about why an open failed.

**Two of its mutation probes found tests that did not exist rather than tests
that were wrong.** Nothing exercised a block the *kernel* rejects whole — every
other refusal returns before `execute_block` is reached — so a store that
committed a rejected block passed the whole suite; offering more raw inputs than
`kMaxRawInputs` is the cheapest such block and closes it. And nothing corrupted
the file in a way `PRAGMA integrity_check` could catch, because every
statement-level tamper leaves a database SQLite considers valid; overwriting a
b-tree page header does. ADR 0057 records ten probes in total; what is verified
here is that both closing cases exist and pass in every hosted job.

**Checking the stored transaction root found the store's one duplicated
derivation**, which is the finding worth carrying forward. The block header
already commits to that root, but `BlockOutcome` did not carry it, so the store
rebuilt the admitted identifier list from `executed` and ran the tree a second
time — two derivations that agree only because the kernel happens to push
`executed` and its identifier list in lockstep, a property nothing stated and
nothing checked. `execute_block` now carries the root it computed. **It changes
no encoding, no state, and no accepted vector**, and the proof is that every
recorded `block_id` still matches, because the header committed to this exact
value before and after.

**Only one recorded scenario could supply the evidence.** `carried` is the only
one with a contiguous run: the other four skip millions of heights between
segments, because the trace's `advance_to` sets the height rather than executing
the gap. A store that executes every height cannot replay a scenario that skips
5,846,395 of them, and giving the store a "jump to height" operation to make it
possible would be test-only machinery in production code answering to no chain
rule. The four blocks are asserted contiguous from genesis, and asserted to open
no assignment window, at the top of `main` rather than assumed.

**The two probes run at final review are the pattern, not an extra.** Each was
made to fail on purpose first, and each is caught by the check that names it:
zeroing the committed transaction root is refused by the commit comparison, and
storing the block identifier in the `transaction_root` column is refused by the
row comparison. A probe that passes has proved nothing until you have checked
that it changed the code the test runs.

**A failed write poisons the store; a state that cannot be encoded does not.**
The payload is built before the write path is entered, so an encode failure
leaves both the durable and the live head exactly where they were and is a
refusal. That keeps "poisoned" meaning *the durable head is unknown* rather than
*something went wrong*.

### How M3.13a was delivered

**Storage artifacts follow ADR 0007's precedent** — an ADR and an implementation
with evidence, not a transition specification — because a snapshot is node-local
and consensus-visible only through the root it must reproduce. No accepted vector
file changed and no new one was added: recording a snapshot's bytes would pin an
operational format as though it were a contract and oblige every future storage
change to re-version a normative file.

**The payload is the state root's own inputs and nothing else** — the summary,
the ordered account map, and the ordered economy map, in the shapes `state_root`
takes them, with the economy section using the accepted `bytes(x)` primitive so
it is literally the concatenation of the leaves the root is taken over. Encoding
a second projection would create a second opinion about what a state *is*, and
the root would then be checking the snapshot against itself. Two genesis
parameters ride beside the summary because a restored ledger has to keep
executing rather than merely verify: the fixed fee and the verifier key. The
verifier key is also an economy entry, so a payload carries it twice and the two
copies must agree.

**`assigned_permissions` is re-derived, never encoded**, and that is the load
bearing decision rather than a tidiness one. It is not a state entry, so nothing
in the root commits to it, and the channel identity is stated over exactly that
figure. A cycle's contributing count is its accrued seats plus its reallocated
ones, and the record commits to both.

**The restore ends with three gates and only the third is one an adversary cannot
defeat.** The rebuilt ledger's projection must reproduce the payload's root; the
payload's entries must produce the same root; and `conservation_failures` must be
empty. **An attacker who edits a state can recompute its root and reseal its
digest, so both root gates pass by construction.** Only an identity that must
still hold refuses an edited state — which is precisely why the permission count
has to be derived rather than read. Two tests are resealed payloads, and one of
them deletes an assignment record: a snapshot that carried the count could have
lowered it to match.

**Each value decoder fails closed on a value no transition could have written**,
not merely on the wrong width, and each refusal names its subject where a root
mismatch would say only that something is wrong. Refusing them is free: a
snapshot is node-local, so a rule stricter than the kernel's own decoder changes
no accepted state.

**One of those rules is stricter than the kernel and the difference is recorded
rather than fixed here.** `bitmap()` never sets a bit at or above `bitmap_bits`,
but `decode_cycle_assignment_value` does not require the pad bits to be clear and
`bit_is_set` bounds itself by the packed width rather than the recorded count —
so a record with a pad bit set would be read as an accrued seat by the mint's own
walk. **It is unreachable on-chain and reachable through a file.** The accepted
specification fixes the bitmap width and does not state the pad rule, so the
kernel is conforming and tightening its decoder would be a compatibility change
rather than a fix. The snapshot refuses it; a later transition version should
state the rule outright.

**Evidence is a third source rather than a second opinion of the encoder.** For
each of the five scenarios in `test-vectors/economy-transition-v7-execution.txt`
the final ledger is snapshotted, restored, and required to reproduce that
scenario's **recorded** `final_state_root` — a figure produced by a model that
knows nothing about snapshots. A round trip compared only against the encoder
would pass for a matched pair of mistakes. Each scenario also requires the
restored ledger to re-encode to identical bytes, to project entry-for-entry to
the payload it came from, and to execute the next block to the same block
identifier as the ledger it was taken from, which is the only question a matching
root cannot answer.

**Twenty-six mutation probes were run and three of them found a test that was
passing for the wrong reason.** A pad-bit case was caught by the contributing
bound rather than by the padding rule it named, so it now compensates the counts
the extra bit disturbs. A channel-index case renamed the tenth channel, which
left the manifest's tenth absent and was caught by the presence check, so it now
*adds* an eleventh — and that bound guards a write into a ten-element array, so
isolating it mattered. Two further probes confirm the suite reads the recorded
file rather than itself: corrupting one recorded root fails the round trip, and
making the test's own payload builder disagree with the encoder fails before any
refusal is constructed.

**Re-aiming the channel probe also showed the payload-root gate is not
decoration.** With the bound removed the eleventh channel is admitted, the
rebuilt ledger has nowhere to keep it, and that second gate is what refuses the
payload. That is the shape every future divergence between an entry kind and the
`Ledger` will have, and without the gate a reader would diagnose it as a
corrupted file.

**A self-review after the first green matrix found two more things.** The decoder
reads every prefix field at a literal offset and nothing checked that the encoder
wrote that many, so a field added or removed would have left those offsets
reading the wrong octets while the total-size check still passed; `encode_genesis`
guards its own prefix the same way and this one now does too. And the entry
decoders were over the size target with a real seam inside them, so the cycle
assignment and the permission count summed out of the same octets moved to their
own translation unit.

### How M3.12b was delivered

**It was one slice and the recorded decomposition was right to say so.** The
state root, the ledger, the settlement, and the four seat transitions could not
be separated: the recovery pool is a state entry, so a version-seven root
implies a version-seven ledger; the backing identity needs the mint walk; and
the mint walk is only reached by kind 4. Splitting it would have produced an
intermediate state nothing could verify.

**The mechanical half followed the recipe M3.12a wrote down, and it was worth
having.** `git mv` of the two directories, the thirteen kernel test files and
the fuzz target; then `protocol::v6` to `protocol::v7`, the include paths, and
the namespace aliases. Every translation unit compiled clean under
`-fsyntax-only` on the first attempt, which is what a reset attempt buys.

**The substantive half is four changes and their consequences.** The receipt,
genesis, and state-root schema versions go to 7 and the chain ID, state root,
and economy tree take version-seven labels; every other label keeps the version
that accepted it. Entry kind 7 is retired and entry kind 17 joins the space as
one entry of five `u64` legs. The cycle assignment record's fixed part goes from
24 octets to 64, and **both the encoder and the decoder refuse a nonzero
absorbed amount at a zero winner count**. `check_carry_identity` becomes
`check_channel_identities` and states both identities.

`split_permission`, `collect_node`, and `claimable` are new and sit in
`ledger.hpp` beside `base_permission_leg`, because they read the manifest
tables. `claimable` is `collect_node` run once per seat, which is ADR 0055's
second derived rule: a second walk written beside the first would make the
backing identity check the kernel against itself rather than against the mint.

**The prologue is genuinely new rather than moved.** Version six's C++ block
execution never wrote a cycle assignment at all. `execute_block` now writes the
due record before the block's transactions, reading the pool from the ledger and
each measured seat's collection mark and recorded referrer from the seat entry.
`SeatCycle` carries three fields, not five, so the kernel's type makes ADR 0055's
first derived rule unstateable rather than merely stated.

**The tests split along the line the contract splits.** Version seven records
only what version seven changes, so the codec tests read two files:
`economy-transition-v7.txt` for the re-versioned constructions, the state
surface, genesis, the settlement, and both identities, and
`economy-transition-v6.txt` for the surface version seven carries unchanged.
Re-recording that surface under a version-seven name would produce a second file
agreeing with the first and saying nothing. `economy_v7_version_test.cpp` is new
and checks the non-collision against version six's own accepted empty economy
root rather than a restatement of it.

**The execution tests reproduce all five recorded scenarios and consult every
vector in the file.** Version six's checks named three deferred sections because
the seat transitions and the settlement were unwritten; there is nothing left to
defer, so the coverage check now requires every key to have been reached.
`coverage.kinds_executed` is derived by counting what the scenarios actually
executed and requiring it to be every kind the codec admits.

**Thirteen mutation probes were run and all thirteen are caught**, each made to
fail on purpose first. Seven against the codec and settlement: dropping the pool
share from the mint walk, filtering the winner derivation by span, absorbing the
dust the cycle just produced, zeroing the five absorbed fields, accepting a
decoded absorption with no winner, un-retiring entry kind 7, and removing the
backing identity from the invariant. Six against execution: running the
assignment after the transactions, applying the cap against a supplied mark,
keeping version six's receipt version, committing the pool the cycle found,
omitting the recovery pool from the projection, and swapping the escrow-create
and escrow-delete handlers.

**Two of the thirteen are worth recording for what they found rather than what
they confirmed.**

The escrow-create and escrow-delete swap is the mutation ADR 0055's own
correction says passed uncaught under the three scenarios that record accepted.
It is caught here by the `carried` scenario, which is exactly what issue #197
added it for — the first time that correction has been shown to work rather than
argued.

Removing the backing identity from `conservation_failures` **passed at first**,
and that was a real gap rather than a bad probe. Both identities were checked by
the settlement test's own arithmetic and nowhere else, so the kernel's invariant
could have stopped stating either one silently. Each is now broken on purpose
and the invariant is required to report it by name.

**One probe of the seven was written wrong first and is worth naming.** An
attempt at "absorb after contributing" added the dust to the pool before
subtracting what was taken and dropped the later addition — which cancels
exactly, because a cycle absorbs either the whole pool or nothing. It passed,
and it proved nothing. The rule the handoff records held: a probe that passes
has proved nothing until you have checked that it changed the code the test
runs.

**The fixture detail that cost the most is a two-constant one.** Three builders
are version six's, imported rather than restated — the confirmed transfer, the
verified-user mint, and the posture change — and they carry version six's own
expiry default of 10,000,000 rather than version seven's 10,000,000,000. The
bytes a transaction commits to include the height it expires at, so unifying the
two constants produced identical state roots and different transaction roots.
The failure was legible only because the state root matched: everything the
transactions *did* was right and only their identity was wrong.

**A bounded local harness made the iteration possible.** The kernel plus one
test target compiles directly against a scratch `sodium.h` over the system
OpenSSL in about eleven seconds, which is what allowed thirteen probes to be run
and re-run without a hosted job. It is never committed and never part of the
build; `docs/project/current-state.md`'s next-action section describes how to
rebuild it.

### How M3.12a was delivered

Issue #197 and PR #198 gave version seven execution evidence for every
transaction kind it admits. It merged by rebase across commits `28567d1`
through `90e13a7` and edits no accepted artifact except ADR 0055, which it
corrects in place, and the specification's evidence section, which changes no
rule.

**It exists because the kernel move could not start.** M3.12 was recorded as "the
version-seven settlement and the four seat transitions in the C++20 kernel".
The kernel's execution tests reproduce `economy-transition-v6-execution.txt`,
and a kernel moved to version seven has nothing to reproduce for the ten kinds
no version-seven trace executes. The recorded decomposition was wrong and is
repaired below.

**The reasoning it corrects was wrong in a specific and instructive way.** ADR
0055 declined to re-record version six's scenarios because they are "fixed by
512 accepted vectors over transactions version seven does not touch". That is
right about the transactions and wrong about their commitments: version six's
file records version-six state roots and version-six receipts, and version
seven re-versions both. A registration under version seven is byte-for-byte a
registration under version six, lands in a different root, and produces a
different receipt, and nothing recorded what either is.

**The cost was measured rather than asserted.** Under the three scenarios ADR
0055 accepted, swapping version seven's escrow-create and escrow-delete
handlers in its own dispatch table passes all 412 vectors. Under the five now
recorded it is caught, as are swapping the two signer handlers, routing a
transfer to the refused direct issue, and routing the referral mint to the
verified-user mint.
**None of those four was reachable before**, and the demonstration was performed
by emitting a three-scenario file to a scratch path and running the mutation
against it rather than by reasoning about coverage.

**Two scenarios close it and every step builder is version six's.** `carried`
runs the ten kinds against a version-seven ledger — the unconfirmed transfer
refused by the opening posture and the confirmed one accepted, a transfer to an
unregistered recipient, a refused direct issue, an escrow created and deleted,
a signer assigned and revoked, a posture relaxed without a signature and then
with one and then tightened and then repeated, and a verified-user collection
forty windows after enrolment that forfeits ten. `referral` covers kind 5,
which nothing else reaches: a seat bought naming a referrer, and the leg minted
in the block the prologue accrued it in. What is version seven's is the ledger
they run against and the roots they commit; the fixtures are imported.

**All fourteen kinds now execute under version seven.** Version six's execution
file reaches eleven — it never exercised kind 6, 13, or 14 at all. The vector
file goes from 412 to 590 and records the coverage as a claim of its own, and a
test requires every receipt the trace produces to carry version seven's version
field.

**One cheap gate was learned the expensive way.** The classification job runs
`git diff --check` between the base and the head, and a trailing blank line an
edit script left at the end of `trace.py` failed it — after the branch had
already been pushed. `git diff --check main HEAD` is the same check, runs
locally in no time, and now belongs beside "run Clang locally before pushing".

### How M3.11c was delivered

Issue #192 and PR #193 gave `economy-transition-v7` a transaction ledger,
ordered block execution, a recorded three-scenario trace, 412 vectors, an
independent verifier, ADR 0055, and 73 tests across three modules. It merged by
rebase across commits `4aacbe6` through `63adcdd` and edits no accepted
artifact; the specification gains an evidence pointer and no rule in it
changes.

**Version seven changes no transaction, and the slice is shaped entirely by that
fact.** Thirteen of the fourteen transitions are version six's **own function
objects** rather than reimplementations, named one at a time in a dispatch
table so the audit is a list of thirteen identities and one exception.
Admission's four steps, the escrow resolution, the five shared envelope checks
in version one's order, and the receipt's consistency rules are imported for
the same reason — including two module-private helpers, because the alternative
is an eighty-line second copy of an accepted rejection order. `mint_node` is
the only transition that reads a surface version seven moved. **The test
requires object identity rather than equal behaviour**, so a copy that drifted
in a path no fixture reaches fails rather than passes.

**The ledger subclasses version six's rather than duck-typing it.** Version six's
transitions annotate their parameter `Ledger`, and a sibling class satisfying
the same attributes would make every one of those annotations a false statement
that happened to work. Six methods are overridden and they are exactly what
version seven changes: fourteen genesis entries instead of twenty-three, the
prologue writing the extended record and the pool it leaves, a projection that
emits kind 17 and never kind 7, the version-seven root, the channel cap read
from the version-three manifest, and the carry identity replaced by two
identities. The inherited `carry` map is **required to stay empty** rather than
left as dead state, so a regression is reported by the invariant that runs
after every block.

**The first derived rule is where a seat's collection mark comes from.** A
`SeatCycle` carries five fields and `uptime-measurement-v1` establishes three;
`minted_through_window` and the recorded referrer are seat-entry fields.
Version six's block execution took all five from its caller. Version seven
reads both from the seat entry, because ADR 0054 recorded that `claimable` is
exact rather than a bound and that the exactness rests on the accumulation cap
being applied at assignment against **the same mark the mint's walk uses**. A
measurement able to supply a different mark could set an accrued bit in a
window that seat can no longer reach, and the bit would be unclaimable while
`outstanding` still counted it — the stranding the backing identity exists to
prevent, reintroduced through the one input a chain does not derive. A
measurement naming a seat nobody bought rejects the whole block rather than
assigning against an invented zero.

**The second is that `claimable` is now the mint's own walk, run once per seat.**
A second walk beside the first would be a second implementation of the
contract's most load-bearing derivation, and the backing identity would then
check the model against itself rather than against the mint. The refactor is
behaviour preserving: version seven's 395 accepted settlement vectors and its
82 tests pass unchanged across it, which is what shows the two walks were equal
before one was deleted.

**The finding is that the rejected block ordering stopped being a matter of
cost.** ADR 0045 had to reject writing a cycle assignment after a block's
transactions by argument, because under version six that block produces a state
a node accepts and a founder loses a day to. Under version seven the window's
permissions enter `outstanding` while the only seat that could claim them is
already marked past them, so `claimable + recovery_pool` falls short on every
leg, the backing identity fails, and the block is rejected whole with the
pre-block state preserved. The trace runs both readings on two copies of one
state.

**Three scenarios were recorded and version six's five were not re-recorded.**
Registration, the recovery path, the accepted version-one transfer, and both
directions of a posture change are fixed by 512 accepted vectors over
transactions version seven does not touch; re-recording them would produce a
file that agrees with the first and says nothing about the pool. What is
recorded instead is the pool's round trip — a cycle nobody wins contributing
its whole permission, the next cycle absorbing it entire, and a real kind-4
mint collecting both — the two block orderings on identical inputs, and **a
machine past its own 731 issuance cycles draining a pool that no seat in that
cycle contributed to**. The last is the case that would strand the pool forever
if a later reader narrowed the winner set to the contributing set, and its
cycle has **no contributing seat at all**.

**Three trace steps exist to stop two claims being vacuous.** Bob's mint succeeds
and collects nothing, which makes the reallocation observable rather than
asserted — he generated two base permissions, met neither cycle, and every unit
went to Alice. A second mint in the same block is refused with
`NOTHING_TO_MINT`, which gives every scenario a refusal its atomicity claim is
actually about. And a registration bound to the version-six chain identity of
the same genesis is refused at admission, which records the compatibility
boundary as a fact rather than a sentence.

**Eight mutation probes ran under `python3 -B` and all eight were caught.**
Swapping the two block orderings; trusting the measurement's mark over the seat
entry's; dropping the pool share from the mint walk; keeping version six's
receipt version; removing the backing identity from the invariants; committing
the pool the cycle found rather than the one it left; omitting the recovery
pool entry from the projection; and filtering the winner derivation by span. A
ninth probe — flipping the default of `assignment_is_prologue` — **passed
uncaught and proved nothing**, because the trace passes the flag explicitly and
the mutation never reached the executed path. It was replaced by one that swaps
the two orderings inside the block, which is caught. That is the third time a
probe has had to be re-aimed after passing.

**Nothing in C++ executes a version-seven transition.** The kernel holds version
six's codec and its ten non-seat transitions, and the settlement plus the four
seat transitions against version seven are the next slice.

### How M3.11b was delivered

Issue #189 and PR #190 delivered `economy-transition-v7` — the specification,
ADR 0054, a sibling Python model, 395 vectors, an independent verifier, and 82
tests. It merged by rebase across commits `dbc1495` through `01527e5` and edits
no accepted artifact.

**Four things change and the specification defines exactly those four.** The
state loses entry kind 7 and gains entry kind 17. The cycle assignment record
gains five fields. Settlement steps 5 through 7 are respecified. And the
per-channel conservation identity loses its third term and gains a companion.
Everything else in version six carries over and is incorporated by reference.

**The recovery pool is one entry carrying five legs, and per-channel is derived
rather than chosen.** The five legs have five different beneficiaries — the
Founder operator's own escrow and four typed custody kinds — and five different
caps and identities, so a single scalar could not say which channel a recovered
unit belongs to and could not be paid out without inventing a split. The ten
`carry` entries collapse to one because one entry holds five fields; the five
fields do not collapse further. Five of those ten were structurally always zero.

**Entry kind 7 is retired permanently rather than reused**, joining 9 and 11.

**The cycle assignment record records what the cycle absorbed, and recording it
is forced rather than chosen.** The pool's balance at a window is a function of
every earlier cycle, so a mint that derived it would replay the whole assignment
history — unbounded work inside a transition that must stay `O(cap)`. The record
grows from 24 fixed octets to 64. The absorbed amount is recorded rather than the
per-winner share, because the residual returned to the pool is
`absorbed - winner_count * (absorbed // winner_count)` and a share alone cannot
express it.

**Step 6 reads the pool before step 7 writes it**, so a cycle's own reallocation
dust and the residual of the pool it just divided both belong to the cycle after.
That order is the difference between two self-consistent readings of ADR 0049's
own sentence, so it is stated rather than left to each implementation. A probe
that absorbs after contributing is caught.

**The identity that matters is the new one.** The channel identity becomes
`issued(c) + outstanding(c) = assigned * leg(c)` with nothing moved out, and the
pool becomes a named portion of `outstanding` rather than a term beside it — the
same shape the referral channel already uses for the unreferred pool. That alone
cannot catch a stranded unit, because `outstanding` is one number and a lost
claim simply leaves it larger. So version seven adds
`outstanding(c) = claimable(c) + recovery_pool(c)`, **which is the statement that
100% is assigned**, as an equality: value created without a claimant and a claim
destroyed without payment are two different failures against an exact figure.

`claimable` is exact rather than a bound, and the reason is worth not
rediscovering: the accumulation cap is applied at assignment against the same
mark the walk uses, so a seat over the cap accrues no bit and — because the
winner derivation filters on the same predicate — wins no bit. No bit can exist
outside the thirty windows a mint reaches, and the mark advance can never step
over an uncollected one.

**ADR 0049's premise about the winner set is wrong for the accepted model, and
checking it in code before acting on it is what made the slice smaller.** The ADR
says `derive_winner_set` considers only seats inside their own 731 cycles. It
does not: `derive_assignment` passes every in-scope seat to it, filtered only by
met-the-cycle and under-the-cap. The contributing set and the eligible set were
already two sets and the eligible one already included machines past their own
distribution. So version seven **states and guards** rules 2 and 3 rather than
implementing them. The rest of ADR 0049's premise holds exactly:
`split_permission(0)` does put the entire base permission into the carry, every
leg's remainder does accumulate there, and nothing anywhere released either.

**The recorded schedule was chosen to reach every branch**, and the two that
matter most are the ones a plausible schedule would miss. Window 3 is won
outright by a machine past its own distribution, which takes the whole pool and
accrues nothing. Window 8 has **no contributing seat at all** — every in-scope
seat is past its span — and still drains the pool, which is the case that would
strand it forever if the winner set were ever narrowed to the contributing set.
The others are a cycle nobody wins, a seven-way split leaving dust on all five
legs, an absorbed pool below its winner count returned whole, a single winner
draining it, and a residual of one atomic unit surviving to the cycle after. A
second schedule crosses the accumulation cap in both directions across
thirty-one windows.

**Seventeen mutation probes ran under `python3 -B` and all seventeen were
caught.** Absorbing after contributing; moving only the operator leg on a
zero-winner cycle — the v2-era rule ADR 0033 superseded; filtering the winner set
by span; keeping version six's subtraction in the outstanding delta; dropping the
pool share from the mint walk; encoding the pool legs in reverse; reusing entry
kind 7; recording the share instead of the absorbed amount; removing the
zero-winner absorption guard; omitting the pool term from `claimable`; keeping
version six's record width and root label; reverting the manifest binding;
writing the ten carry entries again; opening the pool nonempty; changing the
predecessor tree prefix; appending an undeclared constant; and removing the
out-of-span seat from the recorded fixture — the last turns the three set guards
**false**, which is what shows the fixture is load-bearing rather than
incidental.

**Two guards were strengthened after the first candidate because self-review
found them weaker than they read.** Version two's economy-tree restatement was
not checked against its accepted file, so its non-collision rested on a
restatement nothing had shown to be the real one; four of the six were checked
and it was not among them. And the carryover declaration covered version six's
public surface and said nothing about version seven's, so a name version seven
added quietly was classified by nothing. Both are fixed and both were probed.

**The carryover test is the answer to the negative half of the claim.**
`contract.py` declares four sets — carried, rebound, revised, added — and the
test requires them to partition both versions' public surfaces exactly, a carried
name to be identical, a revised name to have moved, and a removed name to be
gone. Writing it caught one omission, `VERIFIED_USER_COUNTER_ENTRY`, before the
slice was committed. That is the defect no derivation can reach: a value that
moved without any vector touching it.

**Nothing executes a transaction.** The model runs the settlement and the
identities; it does not run a block. The version-seven transaction ledger, its
execution, and its recorded trace are the next slice, mirroring how version six
separated M3.10a from M3.10b.

**One property of ADR 0049 is stated and deliberately not encoded.** The pool
lifecycle — a pool that can receive no further inflow is marked consumed and then
archived — has no version-seven encoding because the recovery pool can receive
inflow for as long as any cycle is assigned and therefore never reaches that
state. Adding a state bit no transition can ever set would be worse than
recording why it is unreachable.

### How M3.11a was delivered

Issue #184 and PR #185 delivered `founder-economy-manifest-v3`, ADR 0053, the
manifest JSON, 171 vectors, an independent verifier, the contract table with its
loader binding, and 31 tests. It merged by rebase across commits `ad88f0d`
through `57d6400`.

**Exactly one thing changed, and it is an identifier.** Channel 9 is
`mini_gamified_incentives`. Every cap, issuance kind, channel order, base leg,
subtotal, bound, the 56,993,950,100-display-unit maximum, the referral benefit
with both destinations, the denomination, the seat schedule, and the single
research placeholder are version two's. The schema string is
`protocol-stack/founder-economy-manifest/v3`, the domain label is
`protocol-stack:founder-economy:manifest-v3`, the canonical JSON is 2,261 bytes,
and the digest is
`af153c99adf7c49e5a92563946cf0e60dfd7a58785462530988f661aa68faaa7`.

**The rename is accounted for in both directions rather than asserted.** The
contract table is *derived* from version two's by applying the one substitution,
so a moved cap, leg, kind, order, or bound cannot be expressed at all; version
two hand-wrote its table because it genuinely changed founder-directed values,
and version three changes none. The `rename.` vector group then records exactly
one changed identifier, zero changed caps, kinds, legs, and totals, zero
occurrences of the retired identifier in the accepted canonical bytes, and a
canonical length 6 bytes shorter than version two's 2,267 — **which is the
identifier's own change in length, 30 bytes to 24**, and holds only because the
two schema strings and the two domain labels are each the same length as their
counterpart. That last identity is what makes "and nothing else" checkable in
bytes rather than by reading a table.

**Independence moved outside the models, which is what makes the derivation
safe.** `tools/founder-economy-manifest-v3-vectors/expected.py` converts the
Founder Constitution's two allocation tables by hand and imports nothing from
`simulation/`. The constitution states the economy both as per-cycle amounts and
as channel totals without deriving either from the other, so requiring them to
agree checks the manifest against its source rather than against a second
reading of a specification.

**The loader is now one implementation bound to each version's table.** The
ordered acceptance stages, the field inventory, and the checked derivations
carry no founder-directed value, so they moved to
`simulation/founder_economy_manifest/` and each version binds them. Copying
roughly 450 lines of acceptance order for a one-string change is the failure
mode M3.10c named when it deleted version four's codec. **The refactor is its
own commit and was proved behavior-preserving before version three existed**:
version two's 154 vectors — canonical length, digest, and every ordered failure
code — its 23 manifest tests, its 38 error tests, all 18 registered vector
verifiers, and every `tests/simulation` and `tests/tools` module passed
unchanged.

**Seven mutation probes ran and three of them proved nothing.** Making version
three rename nothing, making it rename a second channel, and adding a byte to a
fixed string were each caught by the loader's fixed-value comparison *before*
the group under test ran, so they establish that the loader works and say
nothing about the `rename.` group. They are recorded that way rather than
counted as successes, which is the discipline the M3.10d handoff asked for.

**The probe that reached the group was a self-consistent version three**: the
renamed channel's cap raised by one display unit, with the direct-mint subtotal
and both maximum-supply figures raised to match, in the contract table and in
the manifest JSON together. Every loader stage and every checked derivation
accepted it; the constitution comparison and three `rename.` values rejected it.
A cap moved by a single *atomic* unit is caught earlier, because a display
maximum that is not a whole number of display units fails the derivation stage.
The remaining probes confirm the verifier fails closed both ways — a tampered
recorded value, a deleted recorded key, an unreached recorded key, a reused
domain label, and an edit to the retained version-two canonical length.

**A probing hazard is recorded because it favours false success, which is the
dangerous direction.** Python validates its bytecode cache on whole-second
source mtime plus file size, so a probe edit and its restore landing in the same
second at the same size can leave a stale `.pyc` in place and the mutation is
never compiled. It was hit here during the probe cycle. Every probe was re-run
with `python3 -B`, and any future probe cycle on Python sources should be.

**Nothing downstream is rebound, deliberately.** No simulator, transition model,
or C++ kernel loads version three. `economy-transition-v6` and every model that
binds version two continue to bind version two and remain correct against it.
The rename reaches execution in `economy-transition-v7`.

### How M3.10d was delivered

Issue #180 and PR #181 delivered the version-six ledger and the ten transitions
that read no cycle assignment. It merged by rebase across commits `bb590c1`
through `13247b2`. PR run 32209825377 on the first head passed the complete
hosted matrix — scope classification `full`, GCC and Clang debug, both
sanitizers, and the aggregate required check — and run 32210502470 on the final
head `4f9561c` passed the same matrix. **One job in that second run hung for
twenty minutes on the runner's package-install step while its three siblings
cleared the same step in seconds**; it was cancelled and re-run, and the re-run
passed in 9m29s. That is runner infrastructure rather than a property of the
change, and it is recorded so a later session recognises the shape instead of
suspecting the code. It added `include/protocol/v6/ledger.hpp`, seven
sources under `src/v6/`, one internal header, and six test translation units,
and it added the CTest entry `economy-transition-v6-execution-cpp`.

**What executes now**: admission, escrow resolution under both authorization
schemes, the shared envelope checks in version one's order, ordered block
execution with failed-transition atomicity, and kinds 1, 6, 10, 13, 14, 15, 16,
17, 18, and 19.

**What deliberately does not**: kinds 2, 3, 4, and 5 read or write a cycle
assignment, and the version-three settlement that derives one is not in the
kernel. Dispatch returns an invariant failure for them rather than a result, so
a block containing one is rejected whole. An implementation that cannot execute
a transaction has no result to report, and the loud failure is the honest one;
no conforming chain can run those four kinds until the settlement lands.

**Evidence is 394 of the 512 vectors** in
`test-vectors/economy-transition-v6-execution.txt` — every vector in the
`construction`, `genesis`, `registration`, `millionth`, `recovery`,
`compatibility`, `posture`, `derived`, and `determinism` sections. The remaining
118 are `block`, `cycle`, and `ordering`, which are the boundary block and the
settlement it derives. Nothing derives a second set of expected values.

**Four checks reach a third source** rather than a second opinion of the
execution file: the ordered transaction tree and the accepted version-one
transfer against `protocol-primitives-v1.txt`, the block header and block
identifier against `ledger-transition-v1.txt`, the ten channel caps and five
base-permission legs against `founder-economy-manifest-v2.txt`, and the referral
leg against `economy-transition-v3.txt`.

**A coverage guard fails if any vector in a claimed section is never
consulted**, and it was demonstrated to fail — removing one `fee_pool`
comparison produces `vector compatibility.fee_pool was never consulted`. It also
fails if the three deferred sections ever become empty, which makes the slice
boundary itself checkable rather than a matter of description.

**Nine mutation probes ran and seven were caught. Two were not, and both are
recorded rather than buried.** One was an *equivalent* mutation that changed no
behaviour — moving the overflow test after the balance comparison, which still
returned the same code — which is exactly the failure mode the M3.10b handoff
warned about; rewritten to make the sum wrap, it was caught. The other genuinely
**passed**: making `signer_revoke` accept a signer assigned to a different
escrow changed nothing any recorded vector observes.

**That second one produced a whole test file.** Three kinds — escrow create,
escrow delete, and direct issue — appear in no recorded scenario at all, and
four shared envelope conditions are never exercised, so
`tests/kernel/economy_v6_transitions_test.cpp` checks them directly and derives
its own expectations because no vector records them. It is a separate
translation unit precisely so a reader never has to wonder which kind of
evidence an assertion carries. Every refusal there is additionally checked to
leave the state root unchanged, and every hand-built fixture is asserted to be a
conserved state first. The probe was re-run against it and now fails closed.

**Clang caught a portability defect GCC accepted**, in three places: capturing a
structured binding by reference in a lambda, which C++20 does not permit. It
would have failed the hosted matrix. Running both compilers locally before
pushing is what found it, and it is the reason to keep doing so.

### How M3.10c was delivered

Issue #177 and PR #178 delivered the version-six kernel codec and ADR 0046. It
added `include/protocol/v6/economy.hpp`, nine sources under `src/v6/`, five test
translation units over a shared fixture header, and
`tests/fuzz/economy_v6_fuzz.cpp`; it removed `include/protocol/v4/economy.hpp`,
the six sources under `src/v4/`, and `tests/kernel/economy_v4_test.cpp`. The
CTest entry `economy-transition-v4-cpp` became `economy-transition-v6-cpp` and
gained `economy-transition-v6-fuzz-smoke`. It merged by rebase across commits
`0563dab` through `5f6f70a`. PR run 32038739390 on the final head `ea7f916`
passed the complete hosted matrix — scope classification `full`, GCC and Clang
debug, both sanitizers, and the aggregate required check — and post-merge run
32039379092 on `5f6f70a` passed the same matrix. One earlier candidate run
failed and one was cancelled as obsolete; both are described above.

**Version four's codec is removed rather than kept beside version six's, and the
reason is what version four is.** The kernel was compiling exactly one economy
contract and it was the one already known to have no conforming implementation —
version four's kind 11 opens its rejection conditions with "an unregistered
`hub_identity_hash` is `NOT_HUB_VERIFIED`" over an identity the transaction never
carries, which is why versions five and six exist. Every Python model and vector
file is retained, because a model plus its vectors is the record of what the
hosted matrix verified and `tools/economy-transition-v4-vectors/` still verifies
its 441. A codec records nothing; it is one implementation of a byte surface.

**The accepted version-one account derivation is now defined once and shared.**
`H(D("protocol-stack:v1:account") || 0x01 || pk)` moved from a file-private
helper in `src/v1/admission.cpp` to `src/v1/account.hpp`, and version one's
admission path and version six's `signer_id` both call it. A second
implementation of one derivation is a second place for it to drift, and the drift
would be silent because both copies would agree with themselves.

**Of ADR 0045's four derived rules a codec can reach one, and it reaches it.**
`NOTHING_TO_MINT` is the empty walk range rather than the literal equality, so a
mark can never decrease; the test pins all three cases including the one the
literal reading gets wrong, a mark *above* the last assigned window. The other
three need a ledger this does not have.

**One of those three is pinned from the admitting side anyway, and a probe is the
only reason it is.** A mutation making the codec *refuse* a mint carrying a
nonzero confirmation field — the rule version six's text literally states, at
admission, under a code the result space does not contain — **passed**. Nothing
in the test or in either accepted vector file noticed an implementation stricter
than the contract can be. The test now requires such a mint to be admitted, which
is the only side a codec can fix that rule from.

**The populated economy root is what makes this more than a table of widths.**
The 44-entry fixture covers all fourteen assigned entry kinds, so one recorded
root constrains every value encoding at once. Two probes swapping adjacent
same-width fields — `signer_count` with `exempt_slot_mask` in the escrow record,
`next_escrow_index` with `escrow_count` in the identity record — failed there and
nowhere else. A width table would have accepted both.

**Three checks reach a third source rather than a second opinion of the
version-six file**: the kind-1 identity and the signer derivation against
`test-vectors/protocol-primitives-v1.txt`, the accounts tree against the same,
and the two cycle-assignment records against
`test-vectors/economy-transition-v3.txt`, because version six's settlement is
version three's imported rather than reimplemented.

**Nineteen mutation probes establish that the checks fail closed**, and one of
them found the gap above rather than confirming a check. Among the others: the
escrow domain label, the version-one account octet in the one place it now lives,
the state-root schema version — a *number*, which the M3.10b handoff warned would
not appear in a search for `v4` — the RFC 9162 split replaced by a halving, the
bitmap packed least-significant-bit first, a retired kind given a width, the
scheme rule dropped, and genesis admitting an account.

**The decoders gained the fuzz target the codec should always have had.** Three
entry points take untrusted bytes and M3.9a shipped with none, which was a gap in
required evidence rather than a judgement that one did not apply. It asserts that
decoding is deterministic and that decoding round-trips — anything accepted
re-encodes to exactly its own bytes, which is what makes a canonical encoding
canonical. A probe that dropped the non-minimal absent-referrer rule fails
against it. Locally it ran 300,000 iterations under libFuzzer with address and
undefined-behaviour sanitizers, from a seeded corpus of one well-formed instance
per kind, with no crash.

**Registering the fuzz target exposed that one is registered in four places, and
the hosted matrix caught the one omission that fails loudly.** The first
candidate left `economy_v6_fuzz` out of the loop applying `-fsanitize=fuzzer`, so
it had no libFuzzer `main` and `clang-sanitizers` failed at the link while the
two debug jobs passed. **The other two omissions are silent**: out of
`PROTOCOL_STACK_TARGETS` a target builds without `-Werror`, the sanitizer flags,
and the libsodium link — the M3.9a defect — and out of the instrumentation loop
it runs with no coverage feedback and explores nothing while reporting success.
`tests/tools/test_registration_test.py` now requires every file under
`tests/fuzz/` to appear in all four, and all five omissions were demonstrated to
fail it.

**That guard's first draft was vacuous in the exact shape it exists to catch, and
a probe is the only reason that is known.** It split `CMakeLists.txt` at the
first `PROTOCOL_STACK_TARGETS` and searched everything after it for an indented
name — which matched the target's own `add_executable` block, so it passed with
the target removed from the list entirely. The cause is that the `list(APPEND)`
block is nested inside `if(PROTOCOL_STACK_ENABLE_FUZZING)` and closes on an
*indented* paren, so a pattern anchored to column zero does not terminate there.
**That is the same defect M3.7a found in this file's `add_test` parser**, one
block later in the same file, and the guard now asserts that its own list parse
finds exactly two blocks.

**Twice is a rule, and `docs/engineering/verification.md` gained a Guards
section.** A guard's subject is the gate rather than the protocol, so the failure
it catches is silent and nothing else notices when the guard stops working. Two
rules: a guard must be run against the omission it exists to catch and be seen to
fail, because adding it and observing that the repository passes establishes
nothing — the repository passed before it was written; and a guard that parses
`CMakeLists.txt` must assert what its pattern reached, because both defects found
so far are a pattern that ran past a block nested inside `if(...)`.

**The test file was split by subject because one file reached 1,430 lines**, more
than twice the largest test in the repository. It is now four check units over a
shared fixture header, mirroring the Python verifier's own
`encoding_checks`/`registry_checks`/`state_checks` split, and `economy_state.cpp`
was likewise split from `economy_tree.cpp`. Every probe was re-run after both
splits.

**The local harness of M3.9a was reused and its one limit is now known.** A
scratch `sodium.h` backed by the system OpenSSL supplies the two entry points the
kernel uses, so the whole codec compiles and runs in about a second. It is never
committed and never part of the build. **It does not reproduce libsodium's
rejection of small-order public keys**, so `tests/kernel/primitives_test.cpp`
fails under it at exactly that assertion and passes under the hosted matrix.
That is a property of the harness, not of the kernel: `src/v1/crypto.cpp` is
byte-identical to `origin/main`.

**The two blocking founder questions M3.8a raised were answered the same day.**
Its gate found that all three authorization predicates the consensus encoding
names were founder-reserved. The owner settled seat purchase, activation, daily
permission assignment, minting, and referral on 2026-08-13, and the answers
changed the transaction set rather than only filling in predicates, so the
specification was rebuilt before being merged. Only direct-channel eligibility
remains reserved, and kind 6 is specified and refused because of it.

**On 2026-08-14 the owner supplied further direction that supersedes
`economy-transition-v2` in four places.** ADR 0033 records it: minted value
lands on the seat's own spendable address, any recorded manager address may act
for a seat, biometric verification on minting is an option the founder switches
on, accumulated unminted permissions are capped with the excess reallocating to
the day's best performers, the unreferred pool pays the single best performer
with exact ties sharing, and a referrer must be HUB verified. HUB — Human
Uniqueness Biometric verification — also becomes an ecosystem-wide identity
layer serving every participant class, with its own direct-mint incentive.

**M3.8b delivered `economy-transition-v3` on 2026-08-14** and merged at
`688efd0`. `economy-transition-v2` stays in place, passing, and unedited apart
from one storage figure that contradicted its own derivation and its own
vectors.

**Requirement 10's target moved again the same day, and the C++ kernel waits for
`economy-transition-v4`.** The owner answered M3.8b's four questions; three
confirmed what version three encodes and the fourth is new direction. HUB
verification survives the loss of any address and is the ecosystem's recovery
layer, and **HUB signing is what adds a Founder Seat address**. Version three
requires an existing manager's signature, so a founder holding no keys has no
path at all. Closing that changes an authorization rule, which is a new version
rather than an edit. ADR 0035 records the direction, and the kernel waits on the
same precedent M3.8a set: the encoding revision comes before the implementation,
because a kernel written against a contract already known to be superseded is
work that has to be done twice.

**Both questions were answered on 2026-08-14 and M3.8c delivered version four.**
Buying a seat requires HUB verification first and the seat is tied to that
identity; a HUB identity's address set lives in consensus state. Requirement 10
is now unblocked against a settled target, and nothing further is expected to
move it.

### How M3.10b was delivered

Issue #153 and PR #173 delivered the version-six execution model and its recorded
transition trace. It added `ledger.py`, `execution.py`, `transitions.py`,
`value_transitions.py`, `block.py`, and `trace.py` to
`simulation/economy_transition_v6/`, 512 normative vectors in
`test-vectors/economy-transition-v6-execution.txt`, a verifier in
`tools/economy-transition-v6-execution-vectors/`, ADR 0045, and 51 tests across
two modules.

**It comes before the C++ kernel because a codec never asks where a transaction
gets its arguments.** M3.9a implemented a version-four codec and M3.9b found that
two implementations agreed perfectly about a message neither could construct.
This is the first step that runs a transition, and it found four things a
byte-level cross-language check could not have.

**Three of them are places where the accepted contract admits two readings, and
one is a place where it is silent.** Every one is consensus-visible: two
conforming implementations that chose differently would return different result
codes, or pay a founder differently, for the same bytes against the same state.
None is founder-reserved — each is a rejection order or a code assignment, which
the constitution names as mechanism — and each is recorded with its alternative
in ADR 0045 rather than settled silently in code.

**Where a cycle assignment lands inside a block is worth more than the other
three together, and it is a decision about money.** `ledger-transition-v1` does
not say whether a record due at a window boundary is written before or after that
block's transactions. Version six's own sentence decides it — "the last assigned
window at any height `h` is `window_of_height(h) - 2`" is a statement about every
transaction executing at `h` — and the trace runs both readings against identical
inputs. Written first, a founder's mint at the boundary collects 114,860,000,000
atomic. Written after, the same mint **succeeds, collects zero, and advances its
mark to that window anyway**, so the cycle is forfeited permanently rather than
deferred. A referral mint in the same block is only deferred, because kind 5
advances its own mark on success alone. Both figures are recorded as vectors.

**`DEBIT_OVERFLOW` had to move to envelope check 8, and the reason is that the
literal order makes the specification contradict itself.** Check 8 is "escrow
balance is below what it must debit", and for a transfer that is
`amount + fixed_fee` — the exact sum kind 1's own condition 5 tests. Evaluating
the overflow test afterwards leaves check 8 undefined on a sum that does not fit
`u64`, and it would make code 7 unreachable in version six, while the
specification lists exactly three unreachable frozen codes and does not list it.
**One real divergence from version one survives and is recorded rather than
smoothed over**: `INSUFFICIENT_BALANCE` now precedes `ZERO_AMOUNT` for kind 1, so
a zero-amount transfer from an escrow that cannot pay the fee answers differently
under the two versions.

**The zero-confirmation-field rule is stated in a place that cannot evaluate it
and names a code that does not exist.** Whether an operation requires a
confirmation is a predicate over the escrow's stored posture, and the
specification says twice that admission reads no state; and the admission and
result code spaces are disjoint namespaces sharing numbers, so result `1` is
`ZERO_AMOUNT` and there is no result code named `MALFORMED_TRANSACTION` to put in
a receipt. It is refused at execution with `UNAUTHORIZED`. **This is the one
specification correction owed to a later version**, and it is the only one.

**`NOTHING_TO_MINT` is the empty walk range rather than an equality**, because a
seat activated in window `w` holds mark `w` while the last assigned window is
`w - 2`. Under the literal wording that mint would succeed, collect nothing, and
set the mark to `w - 2` — a mark that decreases, which destroys the exactness
argument the whole accumulation cap rests on. The trace exercises it directly:
Alice mints immediately after activating and is refused.

**One real defect was found by the tests rather than by the vectors, and it is
the same confusion the second derived rule turns on.** `admit` looked its three
codes up in the *result* code table, so `MALFORMED_TRANSACTION`, `WRONG_CHAIN`,
and `INVALID_SIGNATURE` all raised `KeyError`. The vectors passed anyway, because
the trace had no admission failure in it — so a second finding is that a trace
without a refused input never exercises admission at all. Two admission failures
are now in the fixture and their codes are recorded.

**The accepted version-one transfer is executed, not just encoded.** The exact
200 octets are admitted on a chain stamped with the accepted vectors' chain ID —
which is the only way those bytes reach execution rather than `WRONG_CHAIN` — and
refused with `RECIPIENT_NOT_REGISTERED`. The same transaction with only its 32
recipient octets replaced is accepted. **The byte identity is preserved and the
execution identity is not**, in one trace. The accepted recipient can never be a
registered escrow on any conforming chain, because an escrow identifier is a
digest of an identity and an index and reaching a chosen value is a SHA-256
preimage.

**Version six is the first contract under which a nonzero fixed fee is reachable
from genesis**, and the whole trace runs on the accepted version-one devnet fee
of 1,000 to demonstrate it. Version two derived that a conforming chain must
permit a zero fee, because a zero allocation and a nonzero fee leave nobody able
to pay for the first transaction. Registration is fee-exempt and pays the entry
airdrop, so the first transaction funds itself.

**A registration is exempt from the fee-limit floor as well as from the fee, and
that is forced rather than chosen.** Its fee-limit field is required to be zero,
so a `FEE_LIMIT_TOO_LOW` check would refuse every registration on any chain with
a nonzero fee — closing the ecosystem to new members, which is the opposite of
what exemption exists to guarantee. Expiry still applies.

**The millionth-and-first user is recorded as a consequence rather than argued
about.** They register successfully, receive no airdrop, and hold a zero-balance
escrow, so every transaction they can sign — including the kind-18 mint for a
permission they do not have — answers `INSUFFICIENT_BALANCE` until somebody
already inside the ecosystem sends them value. Only then does the refusal become
`NOT_ENROLLED`. That follows from two accepted decisions, ADR 0042's bounded
airdrop and the universal fee, and nothing in this slice changes it. **The owner
settled it the same day by leaving it as it stands**: the entry airdrop is a
launch incentive with a bound rather than the permanent funding path, and by a
million verified identities the native asset is purchasable outside the
ecosystem, so a newcomer funds their own escrow from outside or an existing
member sends them value.

**Every value two sources can reach is derived twice and recorded only when both
agree**, and `expected.py` imports nothing from `simulation/`. Three inherited
constructions are checked against a third source before anything rests on them:
the ordered transaction tree and the accepted signed transfer against
`test-vectors/protocol-primitives-v1.txt`, and the 146-byte block header and the
block ID against `test-vectors/ledger-transition-v1.txt`. **The block header and
the transaction tree are inherited unchanged, including the header's schema
version of `1`** — version six re-versions genesis, the receipt, and the state
root and says nothing about either, and it states that
`protocol-primitives-v1`'s definitions govern where it imposes no narrower rule.

**Six mutation probes establish that the verifier fails closed**: a re-versioned
block header (104 failures), the cycle assignment moved after the transactions
(33), an unrequested confirmation no longer refused (10), the literal
`NOTHING_TO_MINT` equality (36), a changed escrow domain label (116), and a
fixture that loses its last consecutive block pair (20). The second probe had to
be rewritten once: mutating the flag's *default* changed nothing, because the
fixture passes it explicitly, so the probe was measuring the argument rather than
the behaviour.

**The sixth probe exists because this slice's own file held a vacuous claim.**
Every block in the boundary scenario was separated by a height jump, so the
per-scenario "every consecutive block opens on its predecessor's root" was an
`all()` over an empty set — true forever, establishing nothing. That is exactly
the hazard `docs/engineering/verification.md`'s third rule names, found in the
file written by the person who applied the rule. The scenario gained a real
successor block at the very next height, which also demonstrates that the window
the boundary block assigned is not assigned a second time, and the checker now
**fails** rather than emitting a boolean over an empty set.

**Two states are stamped rather than executed, and both are recorded as stamps.**
The enrollment counter is set one short of the population before any block runs,
so the boundary is then crossed by a real registration; and a height jump between
segments stands in for a run of empty blocks, refusing to skip any window
boundary that would have written an assignment.

**Failed-transition atomicity is checked rather than asserted.** The block
executor commits the state root before every transaction and requires it
unchanged after any non-success result, and the count of refusals that check
covered is recorded per scenario. **Block-level atomicity is the separate rule
and it is implemented rather than described**: an invariant failure, a height
error, or a resource-bound violation restores the pre-block state before the
failure propagates, which is what `ledger-transition-v1` requires and what a
model that only raised would have left as prose.

**Nothing accepted was edited.** All five predecessor vector files verify at their
recorded counts — 238, 579, 441, 550, and 462 — and
`test-vectors/economy-transition-v6.txt` is byte-for-byte unchanged. The
specification gained an evidence pointer and no rule.

### How M3.10a was delivered

Issue #169 and PR #170 delivered `economy-transition-v6` and ADR 0044, merged by
rebase across commits `6fb57f6` through `15b5e90`. It added the specification,
the ADR, a sibling model in `simulation/economy_transition_v6/`, 462 normative
vectors, a verifier in `tools/economy-transition-v6-vectors/`, and four test
modules with 91 tests. The full hosted matrix passed on the exact candidate —
`gcc-debug` 8m33s, `clang-debug` 8m57s, `clang-sanitizers` 9m02s,
`gcc-sanitizers` 9m27s — and again post-merge on `main` in 9m48s.

**A verified identity is the root, an escrow is where value sits, and a signer is
who may act on one escrow.** Three objects, each answering exactly one question,
with the version-one account map holding an escrow's balance and nonce — so a
version-six state is still a version-one state plus an economy map and every
version-one invariant holds.

**The kind-1 bytes survive a fifth version and their execution does not**, and
the two facts have to be stated together or the compatibility section is wrong.
The accepted 136-byte unsigned and 200-byte signed transfer and its transaction
ID are reproduced exactly, and the same bytes are refused with
`RECIPIENT_NOT_REGISTERED` when the recipient is not a registered escrow. That
withdraws `ledger-transition-v1`'s recipient-creating transfer, which was the
last way an account could exist with no identity behind it, and makes **every
account is an escrow** a structural invariant rather than a policy.

**The signature-scheme byte carries the second authorization mode, and that is
what lets recovery pay a fee with no key.** Version one fixes the byte at `1` and
reads offset 40 as the sender's public key; version six reads it as an authority
public key and lets the scheme say whose — a signer key, or an identity's HUB
key. Both verify the envelope signature against the header key, so **admission
still reads no state**. An earlier draft put the identity hash in the header and
looked its key up in state; it works and would let an unsigned transaction reach
execution, so the key went in the header and the identity hash in the body.

**Recovery is not a transaction.** It is the ordinary `signer_add`, authorized by
the identity rather than by a key, against an escrow that already holds value.
The version-five dilemma — who may link an address to an identity — has no
subject here, because an escrow is created beneath an identity and never relinked.

**Registration is fee-exempt, against ADR 0042's stated preference, and the
reason is the millionth user.** The ADR prefers crediting the airdrop before the
fee because 1.71 units exceeds any plausible fee; that holds only while an
airdrop exists. The airdrop is bounded at 1,000,000 identities, so user
1,000,001 would create a zero-balance escrow and fail with
`INSUFFICIENT_BALANCE` — the ecosystem would close to new members at exactly the
point ADR 0042 says the problem stops recurring. Exemption works forever and its
anti-abuse bound is already non-monetary: only the verifier can sign a
registration.

**ADR 0040's two-signer question is answered by version one's own rule.** The
nonce belongs to the escrow rather than to the signer, so two signers race for
one sequence and the loser gets `NONCE_MISMATCH`. No new machinery.

**The escrow identifier is derived rather than allocated**, from the identity and
an index that never decreases. A wallet computes its own identifiers offline, and
a deleted escrow's identifier is never reissued — which is why the identity
record carries `next_escrow_index` and `escrow_count` separately. **The accepted
version-one account derivation survives with its subject moved** from an account
to a signer, which is what a public-key hash is, so the M1 primitive is extended
rather than replaced.

**The posture's direction is derived from the two stored postures**, because a
chain cannot read intent: turning confirmation off, raising the minimum, or
setting an exempt slot bit that was clear. Any one makes the change a relaxation
and requires the HUB signature, so a mixed change that weakens anything counts as
a weakening. Time windows are the accepted grid's 24 one-hour slots — heights,
never a clock.

**Two claims are checked against a third source.** The kind-1 identity and the
signer derivation both against `test-vectors/protocol-primitives-v1.txt`, and the
second matters most: a restatement checked only against its own formula agrees
with itself while both are wrong. **The probe was run with the account domain
octet changed in the model and in the independent derivation, and it still
fails.**

**Four mutation probes establish fail-closed behaviour**, and one of them is the
generator refusing to emit at all: a changed escrow label, a relaxation predicate
that lost its slot-mask disjunct, a removed accumulation cap, and the account
octet. **The boolean rule fired during generation and cost three renamings** —
three posture cases whose answer is "no confirmation" now record the negation
positively rather than recording `false` under a name asserting the opposite.

**The verified-user cap is applied at the mint rather than at assignment, and the
mechanism differs while the rule does not.** A seat's cap is applied when the
chain writes the assignment record, where a capped seat's permission moves to
that day's best performers; no per-window record for a million identities is
affordable at 25 kB a window. So a collection covers the most recent thirty
windows and the mark advances past everything older, which is what makes the
forfeiture permanent rather than deferred. **Channel 8 therefore satisfies an
inequality rather than an equality**: it has no accrual step and so no
`outstanding` term, and a chain whose users forfeit ends below the maximum supply
rather than holding the difference somewhere. ADR 0043 and the constitution were
corrected from "stays outstanding" to "never issued" on the same commit, because
the mechanism does not support the stronger wording.

**Five transaction kinds and two entry kinds are retired rather than reused.**
Each lost its subject, and reusing a number a reader associates with an accepted
contract is the cheapest way to create an auditing mistake. **Three frozen result
codes become unreachable** — `SENDER_NOT_FOUND`, `MANAGER_LIMIT`, and
`ADDRESS_LIMIT` — each because its subject is gone rather than its meaning.

**The seat family fell by an order of magnitude**, from version four's 71,600,000
bytes of seats and managers at capacity to 8,700,000 bytes of seats. **A new
unbounded term appears**: escrow and signer entries accumulate with adoption,
bounded only by the fee, at about 1.3 GB for ten million participants holding one
escrow each. That is recorded rather than solved.

**Nothing accepted was edited.** All five predecessor vector files verify at their
recorded counts — 238, 579, 441, 550 — and the version-one primitives.

### How M3.9c was delivered

Issue #157 and PR #158 delivered version five's evidence and ADR 0038. It added
`simulation/economy_transition_v5/`, 550 normative vectors, a verifier in
`tools/economy-transition-v5-vectors/`, and four test modules with 64 tests.
Version five's status line now says its model and vectors are recorded and its
C++ implementation is not.

**Almost nothing is duplicated, and that is the decision the slice turned on.**
Version five changes one field's meaning, eight labels, and four version fields.
The model imports version four's envelope, key space, registry, settlement,
genesis table, and receipt layout; the independent derivation loads version
four's accepted `expected.py` by path and overrides only what moved. Copying
twelve kind identifiers, twelve entry kinds, and twenty-six result codes to
change eight strings would be a second implementation of an accepted contract
with nothing keeping the two equal — the defect ADR 0026 and ADR 0029 exist to
avoid, and the condition ADR 0029 names for a sibling, a revised transition, is
not met by a relabelling.

**The claim that needed a new kind of evidence is the negative one.** "Everything
else in version four carries over unchanged" cannot be demonstrated by
deriving anything, because a width that moved is simply derived and recorded at
its new value and passes. So the whole vector file is read a second time
against `test-vectors/economy-transition-v4.txt`: every key that file records is
classified as carried, renamed, or revised, the classification must be total, a
carried key must hold version four's exact value, and a revised key must not.
**409 carried, 30 revised, 2 renamed**, and the file records that no envelope,
admission, code-space, state-key, storage, or settlement vector is among the
revised. It fails closed in both directions, and both were demonstrated by
mutation: an undeclared change lands in the carried set and disagrees, and a key
wrongly declared revised lands in the revised set and agrees.

**Kind 11 is now implementable, and the model makes that structural rather than
asserted.** `address_add_message_for` takes one decoded transaction and derives
every field from it — the identity from the body, the account from the sender —
so there is no argument through which a caller can supply an identity the
transaction does not carry. `apply_add_address` has no account parameter at all,
which is what makes squatting unrepresentable rather than merely refused.

**The squatting comparison runs both readings against one registry.** Under
version four's, an attacker links a stranger's account to their own identity and
that person's registration is `REPLAY` forever; under version five's, the same
attacker's transaction links only the attacker's own account and the victim
registers successfully. The superseded reading is kept in the model for exactly
this, labelled as not part of the contract.

**Version five is the first transition contract whose evidence needs the
accepted version-one account derivation**, `H(D("protocol-stack:v1:account") ||
0x01 || public_key)`, because it is the first in which a signed message is built
from the sender rather than from an argument. Version four's fixture could
declare account identifiers as constants precisely because nothing derived them.
**The missing derivation and the defect are the same fact seen from two sides**,
and that is worth carrying into M3.9e: a message assembled from arguments can
name something the transaction does not carry, and one assembled from the
transaction cannot.

**One table is new and is not a relabelling.** `MESSAGE_IDENTITY_SOURCE` records
where a chain obtains the identity each of the eight HUB messages binds — the
body, the sender's address entry, the named account's address entry, or the seat
entry — and records that version four's address add had none. ADR 0037's second
review claim was that no comparable gap remains in the other eleven kinds,
checked by reading; this is that reading written where the next reader can check
it in one place. It is still asserted by the specification rather than executed.

**The genesis fixture holds every field fixed on purpose.** The encoded object
differs from version four's in the schema-version field alone — one octet — and
the chain identifier derived from it differs entirely, which makes "the same
fields under a different label are a different chain" a demonstration rather
than a sentence.

**Three verification rules came out of probing the slice's own evidence, and
they are now repository rules in `docs/engineering/verification.md`.** All three
close the same hole from different sides: **a defect present before a vector
file is first written is recorded at its wrong value and then faithfully
reproduced, so nothing ever fails.**

1. **A boolean vector may only be true.** Its name is the claim, so recording
   `false` records the negation — which is exactly
   `state.no_entry_is_keyed_by_seat_cycle=false`, the defect M3.8b found in an
   accepted file and could only leave in place. A derived `False` is now a
   failure in the checker rather than a value, and it fails twice: once for
   being false and once for leaving its recorded key underived. Neither this
   file nor version four's records a single `false`, so the rule cost nothing.
2. **A name must assert no more than its value establishes.** Three keys in the
   first draft did not: `recovery.the_sender_pays_the_fee` recorded a fee
   *limit*, and two others recorded a hex field or a length under a name that
   claimed a property.
3. **A claim must be checked against something other than itself.** Two checks
   in the first draft were vacuous — one compared a fixture to itself and one
   checked a list against an inline copy of the same list — and both would have
   recorded `true` forever. The account derivation is now checked against
   `test-vectors/protocol-primitives-v1.txt` rather than only against its own
   second restatement, so a formula the model and the derivation got wrong the
   same way still fails.

Each was demonstrated by mutation rather than asserted, and with the account
domain octet changed in *both* sources the generator now refuses to emit a file
at all.

**Nothing accepted was edited.** `simulation/economy_transition/`,
`simulation/economy_transition_v3/`, `simulation/economy_transition_v4/`, their
verifiers, and the version-four C++ codec are untouched, and all four earlier
vector files verify at their recorded counts: 238, 579, 441, and now 550.

### How M3.9b was delivered

Issue #154 and PR #155 delivered `economy-transition-v5` and ADR 0037. It added
the specification and the ADR and nothing else; the model, the vectors, the
verifier, and the C++ update are the next slice and are recorded as absent.

**The slice exists because implementing version four stopped at kind 11.**
`hub_add_address` carries an account and a signature and nothing else, while its
ordered rejection conditions open with "an unregistered `hub_identity_hash` is
`NOT_HUB_VERIFIED`" and its message binds one. The transaction never carries that
identity, and the chain cannot derive it: version four makes the sender
deliberately unconstrained and says why — "a person who holds none of their
linked addresses can still act" — so there is no linked sender to resolve, and
trying every registered key is neither canonical nor bounded.

**No conforming implementation of kind 11 exists**, and the consequence is not a
missing convenience: a founder who has lost every address has no way back, which
is the one guarantee the founder direction of 2026-08-14 was answered into the
contract to provide.

**A byte-level cross-language check could not have caught it, and that is the
general lesson.** M3.9a implements bytes, not transitions. The vectors fix
`message.hex.address_add`, which is built from an identity supplied as an
argument, and nothing in a codec ever asks where a transaction gets that
argument. Two implementations agreed with each other perfectly about a message
neither could construct. The repository's own order — specification, model,
vectors, C++ — is what surfaces this class of defect, and it surfaced this one at
the first step that runs anything.

**The correction reads the 32-byte field as the identity and takes the linked
account from the sender.** The body stays 96 octets and the message keeps its
shape. The obvious repair — an identity field beside the account, widening the
body to 128 — works and leaves squatting open: with the account named in the body
and any sender permitted, anyone may link another person's address to their own
identity, after which that person can never register it and cannot call removal,
because removal is authorized by the identity the address is linked to. Requiring
the sender to be the address added makes squatting unrepresentable.

**It is a new version rather than a repair in place.** Version four's own
versioning section forbids reinterpreting a version-four identifier, and this
reinterprets one. That rule was written one slice earlier; overriding it the day
after, by its author, to save a version is a worse precedent than the version
costs. No recorded byte changes as a consequence — version four's vectors, model,
and C++ codec remain in place, passing, and unedited.

**Version five was accepted without its evidence, which was a departure and was
stated as one.** Every earlier transition contract arrived with its model and its
vectors in one slice. This one did not, because it exists to correct the
contract the repository then called newest, and recording that correction was
more urgent than recording it with its evidence. M3.9c closed that gap the same
day.

### How M3.9a was delivered

Issue #150 and PR #151 delivered the version-four codec in the C++20 kernel. It
added `include/protocol/v4/economy.hpp`, six sources under `src/v4/`, and
`tests/kernel/economy_v4_test.cpp`, registered as `economy-transition-v4-cpp`
beside `protocol-primitives-cpp`.

**This is the first C++ in the milestone, and it is the first time requirement
11 has anything to check.** Everything before it was specification and
independent Python evidence; the codec is the same byte surface written a second
time in the language consensus will run, and the test compares it against
`test-vectors/economy-transition-v4.txt` rather than deriving a second set of
expected values.

**It is a codec alone.** Every entry point is a pure function of its arguments,
it performs no state transition and reads no ledger, and decode failures are
`std::nullopt` rather than exceptions — matching the version-one kernel, where
admission judges shape and nothing else. The transitions are M3.9b and need
block execution and a state store this does not.

**Two things are checked against the accepted M1 file rather than against the
version-four vectors.** The kind-1 identity, because if the C++ encoder does not
emit the accepted transfer bytes the compatibility boundary is broken at its
narrowest point. And the accounts tree, which is what keeps this file's
restatement of the RFC 9162 construction equal to the version-one kernel's
file-private one — that check is the reason a copy is acceptable at all, since
the two produce the same recorded root or one of them fails.

**All four hazards the M3.8c handoff predicted were covered, and two were
demonstrated to be caught.** The bitmaps are packed most significant bit first
and indexed by seat identifier; the cycle-assignment value carries no bitmap
length prefixes, so a decoder must refuse a length that disagrees with its
recorded bit count; dispatch is on the kind byte, and a same-length relabelling
must decode as the kind its byte names and change the signing message; and the
HUB identity record packs 32 + 8 + 4 + 4 into 48 octets with no padding.
Mutating the bitmap packing to least-significant-first and narrowing the address
count to sixteen bits each failed the test, at exactly the check named for them.

**One build defect was found by reading rather than by a failing build.**
`economy_v4_codec_tests` was declared and registered but absent from
`PROTOCOL_STACK_TARGETS`, which is the list carrying `-Wall -Wextra -Wpedantic
-Werror`, the sanitizer flags, `_GLIBCXX_ASSERTIONS`, and the libsodium link.
It would not have linked — but the failure mode that matters is the other one: a
target outside that list builds and passes while held to weaker rules than
everything around it.

**The codec passed on its first run, and the local check that established that
is worth recording.** Building libsodium locally is the heavy operation
`CLAUDE.md` refuses, so the harness supplies the two entry points the kernel
uses and backs SHA-256 with the system OpenSSL — an existing audited
implementation rather than a second one, in a scratch file that is never
committed and never part of the build. That turned a ten-minute hosted iteration
into a one-second one, and it is why three passes were enough.

### How M3.8c was delivered

Issue #148 and PR #149 delivered `economy-transition-v4` and ADR 0036. It added
the specification, the ADR, a sibling model in
`simulation/economy_transition_v4/`, 441 normative vectors, a verifier in
`tools/economy-transition-v4-vectors/`, and 87 tests across four modules.

**HUB verification became the root of identity, and the architecture follows
from one decision.** A registration records the person's own public key, so
every later proof of that person — purchase, activation, a protected mint,
removing protection, adding a seat address, adding or removing an ordinary
address — is a signature by that key. **The ecosystem verifier signs exactly one
thing: a registration.** That is the one judgement no chain can make, and once
made nothing else needs the verifier.

**That restores a containment property version three had to concede.** Version
two could say the verifier gated entry and never payment; version three could
not, because a seat with protection switched on made verifier availability a
precondition for its own income. Version four restores it and widens it: an
unavailable verifier stops new people joining and stops no participant already
inside from doing anything at all.

**The constitution's per-human seat bound reached the chain for the first time.**
Version three records that the 1,000-seat limit "is not enforced by any
transition here, because enforcing it requires knowing that two biometric hashes
belong to one human, which is exactly what the chain cannot see." With one
identity per person in state it can, and `SEAT_LIMIT` is that rule enforced. The
vectors exercise it at 999, 1,000, and 1,001.

**Self-referral became checkable.** Version three compares two account
identifiers, so a buyer could refer themselves from a second address. Version
four compares two HUB identities, and one person has exactly one. The fixture
holds both addresses of one person and records that version three would have
accepted the referral.

**Referral earnings moved from an address to a person**, which is forced rather
than chosen: the whole point of the recovery direction is that losing an address
loses nothing, and a balance keyed by an address would be the one place it still
did over a 731-cycle benefit.

**Three kinds accept any sender, deliberately.** Adding a seat address, adding
an ordinary address, and removing one are exactly the transactions a person must
be able to make holding none of their own addresses, so the signature is the
authority and the sender only pays the fee.

**The settlement was imported rather than copied, and that is checked against
version three's own recorded file.** The accumulation cap, the cycle-assignment
record, and the bounded mint walk are unchanged, so a copy would be a second
implementation of one accepted contract with nothing keeping the two equal. The
vectors require the record version four writes for the same population to equal
`test-vectors/economy-transition-v3.txt` byte-for-byte, and the referral
accrual's re-keying from an account to an identity needed no new code, because
version three's referrer key is opaque bytes — which is itself evidence the
settlement did not move.

**The largest transaction shrank.** Purchase no longer carries a 32-byte
biometric identity hash, because the seat's identity is the purchaser's HUB
identity and the chain reads it from the registry rather than being told it. The
64-byte signature stays and changes hands, from the verifier's to the
purchaser's own. The protocol's largest transaction fell from 325 bytes to 293.

**Each of the three predecessor root constructions is required to reproduce its
own accepted vectors** before the four-way non-collision rests on it, because a
lookalike would make "the roots differ" trivially true. All four roots differ
over an identical account set and an empty economy.

### How M3.8b was delivered

Issue #144 and PR #145 delivered `economy-transition-v3` and ADR 0034. It added
the specification, the ADR, a sibling codec-and-settlement model in
`simulation/economy_transition_v3/`, 579 normative vectors, a verifier in
`tools/economy-transition-v3-vectors/`, and 125 tests across four modules.

**Four things changed and two followed from them.** Any recorded manager address
may act for a seat; a biometric approval on minting is a per-seat option with an
asymmetric switch; unminted permissions are capped at thirty windows with the
excess reallocating to the cycle's best performers; and a referrer must hold a
HUB registration. The two consequences of ADR 0033's first decision are that
minted value lands in an ordinary spendable account rather than typed custody,
and that the account credited is the signer's.

**Two answers were derived rather than chosen, and both decide who is paid.**
The mint must credit the signing manager, because the constitution makes adding
a verified manager the remedy for a lost address, and a mint that credited the
recorded purchaser would leave that remedy able to recover nothing. And a capped
seat must be excluded from the winner set, because it can accrue nothing, so
including it would divide a reallocated permission by a count containing a
recipient that cannot receive and send that fraction nowhere — making ADR 0033's
own sentence false for it and stranding the value as permanently unmintable.
ADR 0034 records both derivations rather than burying them in an encoding.

**The cap is measured in windows, and only that form bounds anything.** ADR 0033
states that the cap turns the growth of a mint's work into a constant. A counter
of accrued cycles does not: thirty accruals can be spread over any number of
windows, so a mint would still walk every window since the mark to find them.
Measuring in windows makes the walk `(mark, min(last, mark + 30)]`, and the bound
is exact rather than conservative — the mark changes only at a mint and a mint
sets it to the last assigned window, so every window in `(mark, last]` was
assigned while the mark held its current value and the assignment applied the
same predicate against that same mark.

**A mint that collects nothing still advances the mark, and that is forced.** A
seat that failed every cycle for two months would otherwise be permanently past
the cap with nothing to collect, so `NOTHING_TO_MINT` would refuse the one action
that could free it. The code is reserved for a mark already at the last assigned
window.

**The optional biometric is a second kind rather than an optional field, and
kinds 3 and 7 therefore share a body length.** That is the case version two
predicted when it required a decoder to dispatch on the kind byte rather than on
the length, so the collision is evidence the rule was right rather than a defect
it created. A single kind with a presence flag would have made every unprotected
mint 229 bytes instead of 164 and needed a rule for a signature the seat did not
require.

**HUB verification enters consensus as one registry entry and one transaction,
and no more.** ADR 0033 widens HUB into an ecosystem-wide identity layer, and
that layer is an M4 milestone specified nowhere. What consensus needs is a
registry a purchase can consult. **One-human-one-account is deliberately not
enforced**, because enforcing it decides what happens to a verified human who
loses their key, which is founder-reserved; the chain records what the verifier
attested, exactly as it does for the seat biometric hash.

**Five defects in version two were found by deriving version three, and three
are fixed by the new contract.** Its bitmaps are indexed by in-scope rank, so
reading one seat's bit requires deriving the whole in-scope set inside a
transition version two describes as `O(1)`; version three indexes by seat ID.
Its record carries no count of reallocated permissions, without which a winner's
entitlement is not computable from the record, and the count cannot be recovered
from the bitmaps. Its assignment adds the carried remainder beside outstanding
rather than out of it, so the carry identity it states as an equality does not
follow from its own steps.

The other two are evidence defects rather than contract ones. A storage figure —
the carry family recorded at 180 bytes beside the derivation `10 * (2 + 8)`,
which gives 100, and which `test-vectors/economy-transition-v2.txt` also records
as 100 — **is repaired in place**, because a figure contradicting its own
derivation is prose rather than a rule. And
`state.no_entry_is_keyed_by_seat_cycle=false` in the accepted vector file
**states the opposite of what its own name asserts**: the property is true and
the expression behind it is wrong, so the file records `false` for a design
property the specification claims. That one is left alone, because a vector file
is the artifact the hosted matrix verified rather than prose. Version three
replaces the check with one that cannot pass while being false: it restates each
key as its named fields, derives every key width from that table, and then asks
directly whether any key names both a seat and a cycle.

**Storage moves in two directions and the one unbounded term does not move.**
Typed custody collapses from 4,200,000 bytes at capacity to 168, because minted
value lands in accounts founders already hold in order to pay a fee; the manager
set adds a bounded 59,200,000-byte worst case at 16 managers per seat that no
plausible deployment reaches. Cycle assignment records still accumulate at
25,033 bytes per cycle — the same width as version two's while carrying one more
field, because the two bitmap length prefixes are gone. **The cap does not prune
them**: it bounds how many records a mint reads, not how old they are, and a seat
whose mark is a thousand windows behind still walks records a thousand windows
old.

**The fixture is a discriminator rather than a restatement.** Seat 11 holds the
cycle's maximum uptime and is over the cap, so under the rejected reading the
winner set would be that seat alone — and the accepted economy model, which
applies no cap, returns exactly that. Seat 23 is past its own 731 cycles and wins
without accruing; seat 15 sits exactly on the 18-hour threshold and accrues
without winning. A second cycle is a total outage, so the winner set is empty and
the whole permission carries, which is the founder-directed rule for that case
and the one path a busy cycle never reaches.

**The verifier's independence is now two-sided.** `expected.py` still builds the
version-one transfer as one flat 136-byte field table while the model builds it
from three parts, and it now also reimplements the cap predicate, the winner
rule, the split, and the mint walk from the specification's prose. A settlement
defect that produced a self-consistent record would have to produce the same
record twice. The version-two root restatement is checked against
`test-vectors/economy-transition-v2.txt` before any non-collision claim rests on
it, and all three state roots are required to differ over an identical account
set and an empty economy.

### How M3.8a was delivered

Issue #139 and PR #140 delivered `economy-transition-v2` and ADR 0032, merged by
rebase across commits `f8d6374` through `5f66c49`. It added
the specification, the ADR, the codec model in `simulation/economy_transition/`,
238 normative vectors, a verifier in `tools/economy-transition-vectors/`, and 91
tests. It satisfies requirements 5 and 6 of `first-goal.md`, and completes
requirement 12 as a consequence of fixing the state keys.

**The slice was specified twice, and the second version is the delivery.** The
first draft named three authorization predicates and defined none, and it
therefore had to guess at the shape of the transitions those predicates govern.
The owner settled them on 2026-08-13 and the answers changed the transaction set
rather than only filling in blanks. The draft was rebuilt in place rather than
merged, because merging would have accepted a contract as immutable while
already knowing three of its records were wrong.

**What the founder decided.** A seat is purchased in one atomic transaction that
registers its biometric hash and the purchaser's address, gated by an off-chain
verifier signature. Activation is separate, one-time, permanent, and triggered
by the purchaser. While a node is up the chain writes mint permissions daily by
itself. Minting takes everything — one button, no quantity — and is the only way
native units reach a founder. Referral is a separate pool on a separate button,
accruing daily regardless of any node's activity and paid to a user account
rather than to a seat. Minting needs only the wallet signature.

**The version-one transfer factors, and that survived the rewrite unchanged.**
Every version-two transaction is a shared 80-byte header, a kind-specific body,
a shared 16-byte trailer, and a signature. The header is exactly the accepted
transfer's first 80 bytes and the trailer exactly its last 16, so kind 1's
40-byte body is what remains and the accepted 136-byte unsigned and 200-byte
signed transfer are reproduced byte-for-byte, transaction ID included. The
schema version stays `1`, both signing labels stay unversioned because the kind
byte and chain ID are already inside every preimage, and version one's result
codes 0 through 8 apply to all six kinds because they are envelope conditions
rather than transfer conditions.

That claim is checked against a third source rather than against itself. The
verifier's `expected.py` builds the transfer as one flat 136-byte field table,
exactly as `protocol-primitives-v1` writes it, while the model builds it from
the three parts; both must then equal the bytes
`test-vectors/protocol-primitives-v1.txt` already records.

**No transaction records a cycle.** The chain writes each cycle's outcome itself
at a block boundary, so the draft's submitted evaluation transaction is gone and
five model rejection conditions go with it: a record nobody supplies cannot be
missing, invalid, incomplete, inconsistent, or out of scope. The two-cycle
settlement lag this needs is forced by the AI dispute window rather than chosen,
and is recorded as forced.

**A mint takes everything, and that is what bounds the state.** One
`minted_through_window` high-water mark per seat replaces what the draft stored
as one verdict entry per seat-cycle — 73,100,000 entries and about 585 MB, plus
512 MB of referral accrual keys. The mark is both the bookkeeping and the replay
protection. A design in which a founder could mint a chosen amount could not
have this property, so the founder rule is also the reason the state is bounded.

**The winner commitment is replaced by a winner bitmap.** The draft committed to
the winner set and required an exercise to carry it, reaching 400,170 bytes for
one fully tied cycle — which under a take-everything mint would have been that
many times the number of saved failed cycles. Each cycle's record now holds a met
bitmap, a winner bitmap, the per-winner share, and the counts, so the set is
readable from state and **the largest transaction in version two is 325 bytes**.
No kind is variable-length and no two kinds share a length.

**Every leg of a failed cycle's permission is divided, not only the operator
leg.** The whole permission moves to that cycle's winners, so the escrows and the
System Creator are paid at the winner's mint rather than at a mint the failed
seat may never make. Each of the five legs is divided by the winner count and
each can leave a remainder, so the carry is per channel.

**Eleven of the economy model's twenty-four result codes become unrepresentable,
in four groups with a reason each**: five because the uptime record is state the
chain writes, three because no transaction names a window, two because the
activation height is the executing block height, and one because a
take-everything mint has no per-cycle key to miss. Eleven are carried and two are
guards `ledger-transition-v1` already routes to block invalidation. The vectors
require the three sets to partition the model's own declared set.

**A Founder Economy chain is a new chain, not a migration.** Version-two genesis
takes schema version 2, binds both the accepted manifest digest and the ecosystem
verifier key as fields, and uses a distinct chain-ID label; the state root takes a
distinct label and version field. A version-one and a version-two root over an
identical account set and an empty economy are required to differ.

**The verifier key gates entry and never payment.** Kinds 2 and 3 carry an
Ed25519 signature by that key over a message binding the chain, the seat, the
purchaser, and an expiry, so an approval cannot be replayed onto another seat or
attempt. Kinds 4 and 5 carry no second factor, so an unavailable verifier stops
new seats and stops no income — the containment direction the constitution
insists on. A stolen wallet key can mint, and only to the seat's own recorded
account.

**Three genesis requirements relax, each forced, and the third exposed a gap.**
The constitution's no-genesis-allocation rule means a conforming chain opens with
zero supply and zero accounts, which version one forbids. The fixed fee then has
to permit zero as the consequence: with a zero allocation and a nonzero fee, no
account can pay for the first transaction, so the chain can never reach a state
in which any fee is payable.

**Kind 6 is specified and refused.** A conforming chain rejects every direct
issue with `UNAUTHORIZED` until the eligibility predicate is accepted, and the
vectors record the unreachability of its five inner conditions.

**One documentation gap was found and repaired.** ADR 0031 had never been indexed
in `docs/README.md`; M3.6c added the ADR and not its entry.

### How M3.7a was delivered

Issue #135 and PR #136 delivered the margin reclaim at merged commit `79d1c0f`,
in two commits. It changed no vector, model, source, specification, or ADR: the
whole diff is test scaffolding, build registration, `tools/verify.sh`, and
`docs/engineering/verification.md`.

**The test phase fell from 707.57s to 255.08s on the PR head and 286.64s
post-merge.** `ctest` was running perfectly serially, which the previous slice's
own measurement had already recorded without naming the cause: 105 tests, sum
707.5s, `Total Test time (real) = 707.57 sec`. Two equal figures are a run with
no concurrency in it.
`tools/verify.sh` now passes `--parallel` at `nproc`, and
`PROTOCOL_STACK_TEST_JOBS=1` restores the serial path for an ordering-sensitive
failure. The two CometBFT integrations run after CTest and stay serial, because
they bind real ports and supervise process groups.

**The slowest job margin went from 3m36s to about 10m.** Every preset roughly
halved. Taking the post-merge run as the conservative figure, `gcc-debug` went
14m30s to 8m28s, `clang-debug` 15m20s to 8m44s, `gcc-sanitizers` 16m24s to
9m17s, and `clang-sanitizers` 15m41s to 9m58s. The slowest is now
`clang-sanitizers` rather than `gcc-sanitizers`, leaving 10m02s against the
20-minute per-job timeout.

**The scheduling is within 3-5% of its floor, which is what the `COST` entries
buy.** Under 4-way contention the 106 entries sum to 992.0s on the PR head and
1096.7s post-merge, so the floor is `max(longest entry, sum / 4)` — 248s against
an actual 255.08s, and 274.2s against an actual 286.64s. Without a cost `ctest`
starts entries in registration order and the slowest are registered last, which
would have ended the run with one long test and three idle workers. The recorded
figures are a scheduling hint rather than a bound: a stale one costs packing
efficiency and never correctness, and a fresh checkout has no
`CTestCostData.txt` to use instead.

**The two runs differ by about 12%, which is runner variance rather than
anything the change controls.** The same 106 entries summed to 992.0s and
1096.7s on identical code, and `economic-envelope-study` alone moved from 143.8s
to 157.4s. Read the margin as roughly ten minutes, not as a precise figure.

**`scenario-v2` was rebuilding one population run three times.** It cost 107.9s
against `scenario-v3`'s 46.0s for strictly more work, because three separate
`setUpClass` bodies each built the complete 731-cycle run while
`scenario_v3_common` builds it once and deep-copies; the seeded property runs
were rebuilt six more times, once per test method. That is the defect PR #123
fixed for the uptime fixtures, in a module that predates the convention. The two
runs carrying a determinism claim still compute fresh: the prefix replays are
simulated per prefix and compared against the shared run, and
`test_the_same_seed_reproduces_the_same_digest` replays each seed against the
cached result rather than comparing a cached run to itself. Locally the module
fell from 70.3s to 32.0s and gained two tests guarding the risk the cache
introduces.

**The registration guard was registered in neither execution path, and that was
found by asking whether the new check would actually run.** The workflow runs
`unittest discover -s tests/tools` only when the scope classifies `lightweight`,
and `tests/tools/test_registration_test.py` had no `add_test`. A change that
adds a test or a verifier classifies `full`, so the one check that catches an
unregistered entry was skipped by exactly the pull requests able to introduce
one. The M3.6c handoff's claim that it "fires on every pull request including a
documentation-only one" was true only of documentation-only ones.

**That is the M3.6c defect one level up, and it is the same mistake a third
time: evidence counted from the command that happened to run rather than the
command the gate runs on the path that matters.** The guard is registered now,
and a new test requires every `tests/tools` module to be registered so the next
one cannot repeat it.

**The block parser was under-reaching in the same direction.** Anchored to a
closing paren in column zero, it silently swallowed all six nested fuzz entries
into the preceding match rather than failing. A test now requires the parse to
reach every `add_test(` in the file, because a pattern matching nothing would
pass the uniqueness check vacuously.

**The study entries were measured and correctly left alone.**
`economic-envelope-study` and `admission-cost-study` each call `run_study()`
three times — once in `setUpClass`, once in-process to prove reproducibility, and
once through the CLI as a subprocess to prove byte-identity. One envelope run is
16.0s against a 62.2s local entry and one admission run is 8.7s against 31.9s,
so all three are accounted for and every one is load-bearing. Unlike
`scenario_v2_test.py`, where three identical runs were rebuilt with nothing
asserting they agreed, there is nothing to reclaim here without deleting a
check.

### How M3.6c was delivered

Issue #131 and PR #132 delivered `economy-scenario-suite-v3` at merged commit
`c44c320`, in four commits. It added the specification, ADR 0031, a schedule, a
probe and a population module, a property generator, `expected_v3.py`, 158
normative vectors, and 51 tests — and repaired two evidence-gating defects left
by the two preceding slices.

**The activation heights are forced, not chosen.** Keeping the tick a shared
window is the property scenario 1 exists to demonstrate, and `cycle-boundary-v1`
then determines everything else: seat `k` activates inside window `k * STAGGER`,
opens at `k * STAGGER + 1`, and holds cycle `t - k * STAGGER` in window `t + 1`
for every seat and every one of its 731 cycles. The heights are non-decreasing in
seat order, so emitting the activations in that order satisfies the monotonicity
condition version three enforces at the writer. A test recomputes the whole
mapping from the grid rather than from the generator's arithmetic, so a generator
that agreed with itself and disagreed with the accepted grid fails.

**One early window has no eligible recipient, and the path was kept rather than
designed away.** A seat now enters a record when its own schedule opens, so seat
0 fails its cycle 0 while it is the only seat in scope: it cannot reward itself,
the derived winner set is empty, and the founder-directed rule carries the whole
342-unit portion forward. Version two's scenario never reached that path, and it
is the only place the suite reaches the empty-winner rule at population scale.
Moving the failure phase to avoid it, or activating every seat at one shared
height, were both rejected — the first deletes founder-directed coverage and the
second recreates the per-seat-window defect ADR 0027 records.

**The totals cannot reveal it, which is why it is a vector.** The carried portion
is delivered at tick 73 to the same seat that would otherwise have received it at
tick 0, so the three population seats' custody is byte-identical to version
two's. A closed form assuming every failed cycle pays a seat in its own window
reproduces every monetary total in the scenario. It is caught only because
`economy.unrewarded_windows` is derived from the trace on one side and from a
walk of the founder rule on the other, and the fail-closed evidence confirms that
mutation is rejected on that single vector and nothing else.

**A peer seat, because the window check now precedes the binding check.** A
contradictory record can only be presented inside a window the evaluating seat
genuinely holds, and a window is only bound by an accepted evaluation, which the
probe seat cannot supply for its own cycle without that being a replay. A second
seat sharing the probe seat's activation height is therefore required, and it
makes the probe sharper rather than merely possible: the refused event is a seat
claiming a higher uptime for itself than the window's bound record carries. A
third seat opening one window later supplies `SEAT_NOT_IN_SCOPE`. All three are
excluded from every population record by their heights rather than by event
order, so the totals stay statements about the three population seats.

**Scenarios 2 and 3 were re-proved, not inherited.** One test asserts the Founder
Seat sale and revenue routing packages contain no economy import, channel
identifier, or supply figure; another requires every `seats.` and `routing.`
vector to be byte-identical across all three accepted suite vector files.

**Two evidence-gating defects were found and fixed.** `CMakeLists.txt` registers
each test and verifier with an explicit `add_test`, and five test files and two
verifiers delivered by issues #125 and #128 had no entry, so the complete hosted
matrix those slices recorded as evidence never ran any of them. Registering them
exposed a second defect underneath: `ctest` invokes a test as `python3 <path>`,
and the four `founder_economy_v3` modules were written for `unittest discover` —
a package-relative import and no repository root on `sys.path` — so as scripts
they failed at import. Their recorded evidence came from a command the gate would
never issue. Both are now guarded by `tests/tools/test_registration_test.py`,
which runs under the focused metadata path and therefore fires on every pull
request including a documentation-only one.

**The two defects are the same mistake twice: evidence counted from the command
that happened to be run rather than from the command the gate runs.** A static
guard is the remedy because it is the *absence* of an invocation that must be
detected, and no run can detect its own absence.

### How M3.6b was delivered

Issue #128 and PR #129 delivered `escrow-payout-v3` at merged commit `93e782a`.
It added the specification, ADR 0030, a third `Binding`, the rebound fixture,
`--version v3` in the verifier, 174 normative vectors, and 14 tests.

**A third `Binding` rather than a package, and that is the same test ADR 0029
applied in the other direction.** ADR 0026 named the condition under which a
shared implementation becomes wrong: a version that revises a payout rule.
Version three does not meet it. What economy version three revised is the
*economy* model's transitions — an activation height, a window check, a
completeness check — and this model performs none of them; it reads one recorded
economy state by digest. A version owns what its own behavior changes, which is
why the economy model earned a sibling package and this one did not.

**Containment is checked against every predecessor, not only the immediate one.**
Extending version two's check to "replay v2 through v3" would have looked
complete and is not: the three economy state labels are distinct strings rather
than a chain, so refusing a v2 state implies nothing about refusing a v1 state,
and a defect with a fallback label, a truncated comparison, or a digest over the
wrong preimage would pass a check that only ever offered it v2 states. The
verifier replays both earlier fixtures through the v3 walk and records an offered
and a rejected count per predecessor, written over an ordered predecessor table
so a fourth version inherits it by adding one entry.

**The equivalence is asserted rather than assumed.** The scenario is held fixed
with only its four embedded economy states rebound, so a differing trace can only
mean a rebinding defect. All three runs produce identical result codes for all 39
events in identical order, and any two final states differ in exactly one member,
`bound_state_digest`.

**The opening custody coincides and its source does not.** The bind yields
34,200,000,000 / 6,840,000,000 / 3,420,000,000 atomic units under all three
versions, because the escrow legs are unrevised and all three fixtures accept two
base permissions. The state those amounts come from is not the same state: the v3
research scenario records activation heights, enforces the window check, and
requires complete records, so its final state has a different shape and digest.
Both facts are recorded separately, so the coincidence is evidence rather than
being read as continuity.

**`caps_agree()` now compares every registered binding instead of two.** The
recorded value does not change, so `escrow-payout-v2.txt` is byte-for-byte
unchanged, which the diff shows directly. Strengthening a check must not silently
rewrite accepted evidence.

### How M3.6a was delivered

Issue #125 and PR #126 delivered `founder-economy-simulator-v3` at merged commit
`271a173`. It added the specification, ADR 0029, the model in
`simulation/founder_economy_v3/`, a 62-event research fixture, 373 normative
vectors, a verifier in `tools/founder-economy-v3-vectors/`, and 63 tests.

**Three things change and nothing else does.** The seat record carries an
`activation_height`, `evaluate_base_permission` applies `cycle-boundary-v1`'s
window predicate, and a record must cover exactly its window's in-scope seat set.
The referral, the exercise, the direct-issuance transition, the carry and its
conservation identity, the journal buckets, the channel table, the base legs, the
activity threshold, and the winner, tie, and remainder rules are identical and
are incorporated by reference rather than restated.

**The manifest is not re-versioned.** No channel, cap, leg, denomination,
subtotal, beneficiary kind, seat capacity, per-person bound, or issuance-cycle
count moves, so version three loads the same 2,267-byte artifact with the same
digest. A third loader for a byte-identical accepted manifest would be a third
implementation of one contract with nothing keeping the three equal, so the
package binds the accepted v2 manifest layer instead of copying it.
`uptime-measurement-v1` likewise needs no version: the record's shape is
unchanged, which is what the M3.5 slice order was for.

**A sibling package rather than a `Binding`.** ADR 0026 chose one shared
implementation for `escrow-payout-v2` because the two versions differed in six
strings, and it named the condition under which that choice inverts: a version
that revises a transition. This slice meets it — a new transition input, a
changed state shape, six new rejection conditions — so a `Binding` would have to
select behavior rather than strings, which is a branch inside every affected
transition and exactly the drift the escrow decision avoided by having none.

**No cycle-boundary state is bound by digest, and that is the load-bearing
asymmetry.** `escrow-payout-v1` binds a foreign economy state because it reads
what another model wrote. Here the economy model is the **writer**:
`cycle-boundary-v1` says outright that it takes an activation height as given.
Binding a second activation table would create a schedule that could disagree
with the seat table this model already holds, and in a consensus implementation
the two are one chain state, so the disagreement would be unrepresentable there
and reachable only in the model. Agreement is required by construction and
proved externally: 45 cross-model probes require the accepted boundary model,
version three, and the founder restatement to give the same verdict, including
all three window rejection codes.

**Monotonicity moved to the writer.** `cycle-boundary-v1` states why an
activation height may not decrease and cannot enforce it against a seat table it
does not hold. Leaving it out would have left the containment stated in one
accepted artifact and applied in none.

**The in-scope set has no upper bound.** Bounding it at `last_cycle_window` is
the tempting narrowing and was rejected: the constitution ends a seat's issuance
period while keeping the seat permanent and its node running, and the
reallocation rule asks for the highest uptime in the window rather than the
highest among seats still issuing. Adding the bound would also make the producing
and consuming ends derive different sets from one schedule, which is the single
property that makes them agree.

**Completeness is two codes because the defects have opposite effects.** An
omission shrinks the population a reallocation ranks over and can send a failed
cycle's Founder portion to a seat that was not the best; an addition admits a
seat with no evidence for the window and could make it the winner.
`SEAT_NOT_IN_SCOPE` reuses the name `uptime-measurement-v1` already gives the
same concept, so both ends describe one condition with one word.

**The intrinsic checks precede the run-history check.** The boundary and
completeness checks are properties of the record, the seat, and the schedule
alone; `INCONSISTENT_UPTIME_RECORD` is a property of what an earlier event bound.
The other order would make one defect report as two different codes depending on
unrelated history. A rejected event binds nothing, so a defective record cannot
occupy a window and make a later correct one inconsistent with it.

**A height is a string and a window is a number, derived rather than chosen.**
`MAX_WINDOW` is 640,511,947,003,803, more than fourteen times below the largest
integer a conforming JSON stack represents exactly, so every window reachable
from a representable height is an exact JSON number while a `u64` height is not.
That is what keeps `cycle_window` a number inside the `cycle_uptime_record` and
therefore keeps the record byte-identical to the one `uptime-measurement-v1`
emits.

**Result-code coverage is partitioned rather than claimed whole.** Twenty-two
codes are event-reachable and all twenty-two are produced by execution; two are
guards. `ARITHMETIC_OVERFLOW` and `INVARIANT` are unreachable from any event
array at any representable scale, because every accumulated quantity is bounded
far below `u64` by a channel cap, so they are proved present by direct exercise
rather than deleted or claimed covered. M3.5 deleted its unreachable code because
no path produced it at all; these two are different, and the partition is what
makes both statements true at once.

**One limit was found by self-review and is recorded rather than asserted away.**
Completeness is measured against the seat table as it stands, and the model has
no current height for an evaluation, so it cannot require that every in-scope
seat has already activated. A chain closes that by ordering, because a record is
emitted only after its window is final. `HEIGHT_NOT_MONOTONIC` bounds the residue
to an event ordering a chain does not produce — once an activation lands at or
above a window's first height, no later one can join that window's in-scope set —
and both the vectors and a test derive that narrowing.

**Nothing accepted was edited.** `simulation/founder_economy/`,
`simulation/founder_economy_v2/`, `simulation/cycle_boundary/`, and
`simulation/uptime_measurement/` are untouched, and a test re-runs the v2
research scenario and requires its recorded state and result digests. No v1 or v2
artifact, C++, consensus, or devnet behavior changed.

On 2026-08-09 the owner also made the founder-decision gate an explicit step of
`proceed`. Issue #117 and PR #118 merged at `0b8c7c2`. The gate now runs after a
slice is selected and before its work begins, enumerates that slice's decisions
before judging them, classifies each with a citation, and reports a result even
when nothing is reserved, so a silent session is evidence that the check ran
rather than that it was skipped. Questions go in one batched selectable-option
call at the end of a response. `CLAUDE.md` gained one clause the reserved set was
missing: what an end user must do, own, run, or receive in order to participate
or be paid.

On 2026-08-07 the owner supplied the four outstanding founder decisions and
revised the economy. ADR 0023 records them: the maximum supply is now
56,993,950,100 display units, the Founder referral doubled to 34.2 units per
cycle and moved to the direct-mint channels as an unconditional benefit,
unreferred seats fund a monthly performance pool, a cycle is met at 18 hours of
fully operational uptime with a 6-hour fragmentable grace allowance, and a
failed cycle's 342 units go to the highest uptime that cycle.

**The accepted M2 models are therefore superseded as founder direction.** They
implement `founder-economy-manifest-v1` and remain exactly as verified; the
constitution now specifies a v2 that only the new economy model implements. The
seat, routing, escrow, and scenario-suite models still bind v1. Nothing about
what runs today changed, because none of it activates anything.

### How M3.5 was delivered

Issue #119 and PR #120 delivered `uptime-measurement-v1` at merged commit
`646cfb5`. It added the specification, ADR 0028, the model in
`simulation/uptime_measurement/`, 114 normative vectors, a verifier in
`tools/uptime-measurement-vectors/`, and 90 tests. It satisfies requirement 7 of
`first-goal.md` and the per-cycle uptime-record part of requirement 12.

**Credit is per slot, and a slot is one hour.** A window is 24 slots of 1,200
blocks, so the constitution's own 24-hour, 18-hour, and 6-hour figures are whole
slots and the rule is applied in the units it was written in. Crediting partial
slots was rejected: it needs evidence at a granularity the chain cannot supply
for a node holding no validator duty in the period, so it would interpolate
between two probes and credit blocks no evidence covers, and the constitution
states there is no partial-credit mode. The coarseness is paid for by the
founder-directed allowance, which is six whole slots.

**The record's shape did not change, which is what the slice order was for.**
`uptime_seconds = credited_slots * 3,600` lands exactly on the units
`founder-economy-simulator-v2` already validates, and whole hours are a strict
subset of the `0..86,400` range it checks. Had the economy model been rebound to
the cycle boundary first and the measurement then denominated in blocks, the
record's shape would have changed twice and two economy contract versions would
have been spent where one does. A cross-model test runs the accepted economy
model on a record this pipeline emits, reaching none of its three uptime-record
failures.

**A seat is credited for the duties it was assigned, not for signing.** The
constitution requires validator capability of every eligible node while stating
that this does not require all 100,000 machines to vote on every block and that
the protocol must select and rotate a bounded live signing set. Crediting only
seats that signed would fail every unselected seat in every slot and reallocate
essentially the whole population's Founder portion to that small set, which is
not a strict reading of the constitution but a contradiction of the sentence
bounding the signing set. An empty assignment is satisfied vacuously.

**Challenge selection is derived per height from a beacon nobody can predict.**
The beacon is the canonical state root at `height - 1`, so a seat learns of its
audit at most one block — three seconds — before it must answer and cannot
schedule uptime around it. `CHALLENGE_PERIOD_BLOCKS` equals `SLOT_BLOCKS`, so a
seat expects exactly one probe per credited unit: the sampling rate is one probe
per slot, which fixes the load at about 83 responses per block at full capacity
and adds nothing to an ordinary transaction. Selection excludes the final 20
heights of a slot, so a challenge and its 60-second deadline always lie inside
one slot, which is what makes the per-slot state disposable at the boundary.

**The dispute may only subtract, and only up to the grace allowance.** There is
no transition by which a dispute adds credit, so a captured Ecosystem AI key can
reduce a result and never manufacture one: it cannot mint, cannot direct value,
and cannot make a failed node appear to have met a cycle. The cap is 6 slots per
seat per window, and `24 - 6 = 18` is exactly the threshold, so **a seat credited
for every slot still meets its cycle after a maximal dispute.** The AI can
consume an operator's entire allowance and cannot by itself fail a fully
operational node. That is the constitution's own containment argument applied in
the second direction: it refuses to make the AI's signature a precondition for
payment because a company able to freeze income would own the reward path, and an
unbounded void power restores exactly that ownership through a different door.
The model asserts the theorem after every dispute rather than trusting the cap
arithmetic, and refuses a cap that would break it.

**Silence finalises after one window.** A window's dispute period is the whole of
the following window, and the result is final at the start of the window after
that regardless of AI availability. Reusing the existing grid makes finalisation
a window comparison rather than a second period, and delays a seat's exercise of
a cycle by at most two windows.

**Completeness is derived, not validated.** A record's seat set is every seat
activated strictly before the window's first height, derived from the bound
cycle-boundary activation table, so an omission is unrepresentable rather than
detected. This closes the gap `founder-economy-simulator-v2` and ADR 0027 both
record. The tests demonstrate it rather than describe it: the economy model
accepts a truncated record, and this pipeline has no way to emit one.

**Nothing is bound to this yet.** `simulation/founder_economy_v2/` and
`simulation/cycle_boundary/` are untouched. No v1 or v2 artifact, C++, consensus,
or devnet behavior changed.

### How M3.4 was delivered

Issue #114 and PR #115 delivered `cycle-boundary-v1` at merged commit `7dd6a84`.
It added the specification, ADR 0027, the model in `simulation/cycle_boundary/`,
101 normative vectors, a verifier in `tools/cycle-boundary-vectors/`, and 57
tests. It satisfies requirement 4 of `first-goal.md`.

A cycle is 28,800 block heights on one global grid. Window `w` is the inclusive
height span `[w * 28,800, w * 28,800 + 28,799]`, and a seat's 731 cycles are the
731 consecutive windows beginning with the first window that starts after its
activation height.

**The grid is shared, and that is the load-bearing decision.** Performance
reallocation sends a failed cycle's 342-unit Founder portion to the highest
uptime "in that same cycle", so a cycle must name a period several seats can be
compared over. With per-seat windows anchored at each seat's own activation, two
seats share a window only when their activation heights are congruent modulo
28,800, so essentially every reallocation would rank a population of one — the
failed seat, which cannot win. The winner set would be empty and the whole
portion would carry forward indefinitely, which is not a conservative reading of
the founder rule but the rule not running. The vectors record this as a derived
property rather than a claim: seats activated at genesis and at the last height
of the same window hold identical spans, and one block later shifts the span by
exactly one window.

**28,800 was chosen for exactness, not convenience.** The pinned M1
`timeout_commit = "3s"` divides all three founder-directed durations without
remainder, so 18 hours is exactly 21,600 blocks and the fragmentable 6-hour
allowance exactly 7,200. A grid leaving a remainder would put a founder-directed
threshold between two blocks, appliable only by rounding it toward the operator
or against them, which is a change to a founder-directed value that the standing
delegation does not authorize. The model computes each quotient and requires a
zero remainder rather than trusting the arithmetic to have worked out.

**A seat begins at the next full window.** Counting the activating window would
give a seat activated one block before a boundary a first cycle of one block, in
which the 18-hour threshold is unreachable; it would fail a cycle it was never
able to meet and have that cycle's Founder portion reallocated to other seats
purely because of where in a window its activation was included. The cost is at
most one window of delay, and the constitution fixes how many cycles a seat
receives rather than the height at which the first opens.

**The drift between a window and a day is stated rather than smoothed over.**
28,800 blocks is 24 hours only at exactly 3 seconds a block, so a slow chain
stretches a window in real time and a node up throughout it would accumulate more
wall-clock uptime than `founder-economy-simulator-v2` accepts in a record. The
grid is not what changes: a window's nominal duration is 86,400 seconds and a
measurement is a statement about a window rather than about a clock, so
`uptime_seconds = uptime_blocks * 3` for `0 <= uptime_blocks <= 28,800`, exact
because the divisions are exact. Widening the economy model's containment bound
to admit wall-clock seconds was rejected: it would let a slow chain inflate every
node's measured uptime against a fixed threshold.

Activation heights may not decrease, because a real activation executes inside
the block that includes it, so a replayed or reordered activation cannot install
a schedule in the past and claim windows the seat did not hold. Equal heights are
accepted, since one block may activate several seats.

**Nothing is bound to this yet.** Applying the check inside
`evaluate_base_permission` adds a rejection condition and requires the seat
record to carry an activation height, which under the rule ADR 0024 and ADR 0026
established is a new economy contract version rather than an edit.
`simulation/founder_economy_v2/` is untouched and its recorded gap stays
recorded. No v1 or v2 artifact, C++, consensus, or devnet behavior changed.

### How M3.3 was delivered

Issue #108 and PR #109 delivered `escrow-payout-v2` at merged commit `a8ea180`,
and issue #110 and PR #111 delivered `economy-scenario-suite-v2` at merged commit
`04cdd23`. Together they satisfy requirement 3 of `first-goal.md`: all four
dependent models are re-verified against version two, every recorded digest is
regenerated, and both verifiers still fail closed in both directions.

The slice was split because the suite binds the escrow model, so rebinding the
suite depends on the escrow model already having a v2 binding.

**Rebinding is a new version, not an edit, and the repository decided that rather
than the session.** `escrow-payout-v1.md` fixes its research-input shapes and
digest labels as immutable and requires a new schema and ADR to change them, and
`economy-scenario-suite-v1.md` already recorded that its scenario parameters were
superseded and that a version two suite would derive them. ADR 0026 records both
halves.

Escrow payout differs in exactly six strings: the five domain labels it writes
and the one founder-economy state label it reads. Every transition, rejection
condition, rejection order, journal bucket, and invariant is identical, so the
two versions share one implementation selected by a `Binding` record. A duplicate
package was rejected — `founder_economy_v2` earned one because its transition set
changed shape, while two copies of a thousand lines of identical payout logic
would have nothing to notice drift.

The escrow v2 fixture is the v1 scenario with only its four embedded economy
states rebound. Holding the scenario fixed is what makes the rebinding auditable:
the two runs produce identical result codes for all 39 events in identical order,
and their final states differ in exactly one member, `bound_state_digest`. That
equivalence is asserted, because a rebinding defect that altered a payout rule
would still produce a self-consistent vector file.

The opening custody is unchanged at 34,200,000,000 / 6,840,000,000 /
3,420,000,000 atomic units. The escrow legs are unrevised and both fixtures accept
two base permissions, so the amounts coincide while the state they come from does
not. Both facts are recorded rather than one being assumed.

**The suite's scenario 1 changed shape.** Version one supplied the activity
verdict and the performance recipient because the constitution had not decided
them; both are now decided, so the generator supplies measurements and the model
derives the answers. The tick is the shared `cycle_window`: three seats staggered
61 ticks apart hold different cycle indices at the same tick, and reallocation to
"the highest uptime in that same cycle" is only meaningful against a shared
window. Reusing `cycle_index` would have put exactly one seat in every window, so
no reallocation would ever have had a candidate.

The intended winner is given the only maximal uptime and the model derives the
winner set. Every other seat sits exactly on the 64,800-second threshold, so the
founder-directed boundary is exercised in every reallocating window rather than
only in a unit test. At most one seat may fail per window, which the generator
asserts rather than assumes: two would make the winner set depend on evaluation
order. A fourth seat is activated and never evaluates, because all three
population seats consume their whole 731-cycle windows and the three uptime
probes need an unevaluated key to reach `MISSING_UPTIME_RECORD`,
`INVALID_UPTIME_RECORD`, and `INCONSISTENT_UPTIME_RECORD` in order.

Scenarios 2 and 3 are proved version-independent rather than asserted to be: the
19 seat and 26 routing vectors are byte-identical in both vector files.

No v1 artifact, C++, consensus, or devnet behavior changed.
`simulation/founder_economy/` is untouched, and `escrow-payout-v1.txt`, its
fixture, and `economy-scenario-suite-v1.txt` are byte-for-byte unchanged and
still pass.

### How M3.2 was delivered

Issue #103 and PR #104 delivered `founder-economy-simulator-v2` at merged commit
`a0521d0`. It added the specification, ADR 0025, the executable model in
`simulation/founder_economy_v2/`, a research scenario fixture, 189 normative
vectors, and a second verifier entry point in `tools/founder-economy-v2-vectors/`.

The transition set changed shape, not only parameters. The referral left the
permission system entirely: `accrue_referral` is unconditional, direct-mint, and
keyed by `(referred_seat_id, cycle_index)`, with no activity and no eligibility
input. An unreferred seat credits `unreferred_performance_pool:global` rather
than being rejected, which is what consumes the channel exactly at capacity, so
`SEAT_NOT_REFERRED` is gone. The permission `kind` discriminator went with the
referral, and `INVALID_PERFORMANCE_ALLOCATION` went with the supplied allocation
list it validated.

`evaluate_base_permission` now derives the activity verdict and the winner set
from a cycle uptime record instead of reading two supplied fixtures.

**The record carries measurements only.** It cannot express a verdict, an
eligibility flag, a winner, a ranking, or an amount, and tests assert that a
record carrying an `active` flag or a `winners` list fails to parse. This is the
distinction the slice existed to preserve: a research placeholder stands in for
an undecided founder policy, while the record stands in for a rule ADR 0023 and
the Founder Constitution already decide but whose measurement pipeline is
unbuilt. `MISSING_UPTIME_RECORD`, `INVALID_UPTIME_RECORD`, and
`INCONSISTENT_UPTIME_RECORD` are deliberately distinct from the research codes so
a trace can tell a missing measurement from a missing founder decision.

A `cycle_window` is separate from a seat's `cycle_index`. A seat's 731 cycles
begin at its own first activation, so two seats' cycle 7 are different windows
and reallocation to "the highest uptime in that same cycle" is only meaningful
against a shared one. The model cannot verify that a supplied window is the
correct window for a seat's cycle — that is the deferred cycle-boundary rule — so
the separate field keeps the gap visible in every event rather than hiding it in
a coincidence of names.

The carry needed care. Carried value is unreserved channel capacity, not a fourth
ledger dimension, so folding it into the journal's channel balance would
double-count it and no accepted journal would balance. It is pinned by its own
identity instead, per event in the engine and cumulatively in the state
invariants:

```text
issued(founder_operator) + outstanding(founder_operator) + performance_carry
  = count(evaluated_permission_keys) * 34,200,000,000
 <= cap(founder_operator)
```

asserted as an equality rather than a bound, because a bound would admit a defect
that lost carried value.

`founder_referral` is rejected by `direct_issue`. That is containment rather than
tidiness: admitting it would let a supplied eligibility fixture mint referral
units outside the per-seat-cycle accounting and place a founder-decided channel
under an undecided placeholder.

No v1 artifact, C++, consensus, or devnet behavior changed.

### How M3.1 was delivered

Issue #99 and PR #100 accepted `founder-economy-manifest-v2` at merged commit
`0c05b52`. It added the specification, ADR 0024, the manifest JSON and its
digest, 154 normative vectors, a strict loader in `simulation/founder_economy_v2/`,
and a verifier in `tools/founder-economy-v2-vectors/`.

The contract fixes the 56,993,950,100 display maximum as
5,699,395,010,000,000,000 atomic under the unchanged eight-decimal
denomination, and the referral at 34,200,000,000 atomic per cycle as an
unconditional direct-mint channel capped at 250,002,000,000,000,000. The other
nine channel caps, the seat capacity, the per-person bound, the 731-cycle
schedule, and every base-permission leg are unchanged.

Version one was not edited. Its digest names the exact byte string the M2
evidence was verified against, and the two contracts differ in shape rather
than only in parameters: v2 has no `referral_permission` issuance kind, no
`referral_permission` object, and no permission `kind` discriminator. Each
loader rejects the other's manifest, the domain labels differ, and tests assert
both directions. ADR 0024 records that reasoning and four other structural
decisions.

No simulator, C++, consensus, devnet, or previously accepted v1 artifact
changed. v2 has no executable model and activates nothing.

### How M2 was delivered

Issue #71 and PR #72 adopted the first exact contract at merged commit
`14486cb`: an eight-decimal `u64` denomination, all ten fixed issuance-channel caps, the
731-cycle supply derivation, permission liabilities, research-only eligibility
placeholders, ADR 0017, and normative vectors.

Issue #77 then made that contract executable and is merged at `9aeac23`. It
added `founder-economy-simulator-v1`, ADR 0018, the independent
`simulation/founder_economy/` model, a second normative vector file, and a
verifier that derives every recorded value from the loaded manifest and live
runs.

Issue #79 delivered the Founder Seat sale model satisfying `goals/m2-founder-economy-proof.md`
requirement 8 and is merged at `c03262f`.

Issue #82 delivered commercial revenue and transaction-fee routing satisfying
`goals/m2-founder-economy-proof.md` requirements 9 and 10 and is merged at `5029c00`. It added
`revenue-routing-v1`, ADR 0020, the independent `simulation/revenue_routing/`
model, a third normative vector file, and a verifier whose `walk.py` is a
second implementation the recorded file and the model must both agree with.

Issue #85 delivered escrow payout capabilities satisfying `goals/m2-founder-economy-proof.md`
requirement 11. It added `escrow-payout-v1`, ADR 0021, the independent
`simulation/escrow_payout/` model, a fourth normative vector file, and a
verifier that both replays the scenario against an independent walk and proves
the fixture's opening custody is bound to a live `founder-economy-simulator-v1`
run.

Issue #88 delivered the multi-year and adversarial scenario suite satisfying
`goals/m2-founder-economy-proof.md` requirement 13. It added `economy-scenario-suite-v1`, ADR 0022,
the deterministic generators in `simulation/scenarios/`, a fifth normative
vector file, and a verifier whose independence is closed-form derivation from
Founder Constitution literals rather than a fifth walk. It added no model,
transition, event kind, or canonical label.

Issue #91 delivered `founder-economy-report-v1.md`, satisfying `goals/m2-founder-economy-proof.md`
requirement 14, and this handoff satisfies requirement 16. No C++, consensus,
devnet, or previously accepted simulator behavior changed in any of these
slices.

## Records moved from "What works now"

The version-eight stack slices were appended beside "What works now" rather than
under "Phase", so they sat in a second block. **The order within this section is
the order the handoff kept**, and the two sections are not merged, because
several records refer to the one above or below them and reordering would break
those references silently.

### How M3.13s was delivered

**Two halves and an end-to-end run.** `protocol-application-v8` is version
seven's binary with the version rebound and the genesis allocation bound moved
from 110 octets to 142; the normalising diff against `main_v7.cpp` is the
rebinding and the prose. `ClientV8`, `LocalV8`, `NewV8`, `ProtocolV8`, and
`-protocol-version 8` are the Go half. `version_eight_chain.py` and the two
CometBFT integrations are what make it a chain rather than two components.

**The bound moved, and so did two error messages that were not figures.** "not
the canonical 110 octets" became "not the canonical version-eight width". A
message is compiled against nothing, so a stale literal there survives every
test and lies to the first operator who reads it. Deleting the number rather
than updating it is what stops the next rebinding inheriting the problem; the
bound itself reads `v8::kGenesisPrefixBytes` and the file states no width.

**The finalized-block shape did not move, and that is a finding rather than an
omission.** Version eight changed what a block *does* — a prologue, an issue
step, an expiry step, two entry kinds, a per-seat digest — and changed nothing
about what a finalized block *is*. So `LocalV8` and `NewV8` differ from version
seven's by the codespace alone, and the identifier reaches the bridge by the
same route.

**ADR 0067's rule needed a third kind.** Four figures were on the list and three
behave as the rule predicts: the genesis bound, the app state, and the receipt
version all break the happy path if left stale — nothing starts, `init_chain`
refuses, no block decodes. **The result-code count does not.** It moves from 33
to 45, every test that uses it compares the constant to itself, and codes 33
through 44 appear in no fixture in this repository, so a stale 33 narrows the
accepted range silently. The third kind is a figure **checked everywhere and
pinned nowhere**, and its test is an assertion against the literal plus one
input on each side of the boundary, written out rather than derived.

**A fifth figure of that kind is not a constant.** The two genesis keys must be
two keys; a genesis carrying the verifier key twice encodes, derives an
identity, and executes every block, and the fixture, the node, the adapter, and
the engine all agree about it. `check_the_dispute_authority_is_its_own_key`
requires the pair adjacent in the encoded genesis exactly once, which also pins
the adjacency the specification states.

**Versions seven and eight must refuse each other's finalized blocks.** Versions
one and seven fail closed because their shapes differ; seven and eight share a
shape, so on a well-formed successful block the **only** octet separating them
is the receipt's version. Without that pair, `-protocol-version` set wrong would
misread a chain rather than fail to read it.

**Six mutation probes ran and each was checked to have changed the code the test
runs.** `resultCodeCountV8` at 33 is caught only by the new literal assertion;
`receiptVersionV8` at 7 is caught by that assertion **and** independently by the
cross-version pair; the fixture passing the verifier key twice is caught by the
adjacency check and **not** by the inequality beside it, because the session
still held two distinct keys and only the encoding was wrong; `GENESIS_BYTES` at
110 and the fixture's receipt prefix at version seven's are both caught
immediately. Every restored tree was re-run to green.

### How M3.13r was delivered

**A version-eight chain can be driven by a consensus engine.** `ApplicationV8`
and the version-eight response encoder are version seven's with five figures
moved and one parameter dropped: three public headers, four translation units,
and an internal header. The normalising diff against version seven is empty for
the dispatcher header, the response header, the internal header, and the
dispatcher translation unit.

**The owed uptime item is closed rather than satisfied.** ADR 0058 recorded
that `execute_block` takes an uptime schedule and version seven's application
does not supply one, so a chain driven entirely through `ApplicationV7` writes
no cycle assignment record and accrues nothing to any seat, and named wiring a
measurement to this layer as the dependency between it and a chain that pays
anyone. Version eight's prologue derives the schedule from the seat table and
the window records, so both call sites lose an argument and there is nothing
left to supply. The cost lands on `process_proposal`, which now evaluates one
selection digest per in-scope seat to decide a vote where at most heights it
evaluated nothing.

**The fifth moved figure was not on the list this slice started from, and it is
the finding.** The receipt magic prefix carries the receipt version as its last
octet — `{'P','S','R','C', 0, 7}` in version seven's encoder, written out as a
literal with a `static_assert(kReceiptVersion == 7)` two lines below that says
nothing about the array. A rebound version-eight encoder therefore compares
version-eight receipts, whose own bytes carry 8, against a version-seven prefix,
and **no finalized block encodes at all**. It is now derived from
`v8::kReceiptVersion` rather than restated, which is what makes the assertion
beside it cover the prefix instead of standing next to a second copy of the same
number.

**That is the opposite failure mode from M3.13q's, and the pair is the general
rule.** The store's `head_snapshot` minimum, left stale, moved a refusal one
layer later and was invisible to every test that only asked whether the refusal
happened. The receipt prefix, left stale, breaks the first block on the happy
path and was caught by an inherited test the moment it compiled. **A figure that
moves with a version is either checked on the happy path or it needs a boundary
case, and there is no third kind.** Ask which one you have before writing the
tests rather than after.

**Two boundary checks were added on that basis and one of them earns its place
by a probe.** The protocol version is pinned to its literal with a
`static_assert` in both suites, because comparing `info().application_version`
against `kApplicationProtocolVersionV8` is a claim that the value reaches the
caller and no claim about which value it is. And `init_chain` is refused with
**version seven's** app state beside version one's — the probe that leaves the
app state stale on *both* sides, which is the realistic blanket-rebinding error
where the happy path still agrees with itself, is caught by nothing else.

**Seven probes, six caught, and the seventh is recorded rather than patched.**
Removing `commit`'s requirement that the store's commit record equal the staged
one changes nothing any test observes, so **the equality ADR 0058 calls "the
whole safety argument" has no test that can fail it.** It is inherited from
version seven rather than introduced here, and constructing a violating input
would need a fault-injection seam that returns a corrupted commit record —
test-only machinery in production code, which ADR 0057 and ADR 0067 each
rejected. ADR 0068 records it, and records that deleting the guard would be the
mistake: it is the same shape as M3.13p's prefix-width assertion.

### How M3.13q was delivered

**A version-eight state survives its own process.** `SQLiteLedgerV8` is version
seven's store with four figures moved and one parameter dropped: one public
header, three translation units, and two internal headers, of which the schema
header, the internal header, and the open translation unit are version seven's
files with identifiers rebound and **nothing else at all** — the normalising
diff against each is empty.

**The four figures, and why one of them needed a test of its own.** The stored
canonical genesis is 142 octets rather than 110, `head_snapshot`'s minimum is
`snapshot_v8`'s own `kFixedSize` of 222 rather than 190, the pinned
`application_id` is `0x50534c38` with a `user_version` of 8, and the tables are
`ledger_meta_v8` and `blocks_v8`. The DDL is compared verbatim on every open,
so none of them is a comment about a width — each *is* the width. **They do not
fail the same way.** A stale genesis width fails the very first insert and
cannot reach a file. A stale `head_snapshot` minimum fails nothing: a short
blob reaches `decode_snapshot_v8` and comes back `invalid_snapshot` instead of
never being stored. That is a *weaker* refusal rather than a wrong one, and the
whole suite as version seven wrote it passes with the stale value in place —
which was established by running it, not argued. `check_column_bounds` pins the
boundary instead: 221 octets refused by SQLite's own CHECK and 222 admitted,
110 refused and 142 admitted, and the two admitted writes then leaving a file
the store must still refuse.

**`apply_block` lost a parameter rather than passing a null one.** Version
eight's prologue derives the uptime schedule from the seat table and the window
records, so there is nothing to hand over and **a node cannot be given a
different answer than its peers computed**. The three `BlockOrder` flags are not
exposed either: `ledger.hpp` states that none of them is a configuration a chain
has, so a store that surfaced them would be offering an operator a way to leave
consensus.

**One objection hardened from a preference into a rule.** ADR 0057 refused to
give the store a "jump to height" operation because it would be test-only
machinery answering to no chain rule. Under version eight it answers to a chain
rule and contradicts it — every height audits every in-scope seat, so a skipped
height is an audit that was owed and never performed. The `carried` scenario is
still the only recorded one with a contiguous run, and the entry point now
**requires** what makes it replayable rather than assuming it: no block in
heights 1 through 4 opens a window, audits a seat, or expires a challenge, and
the chain writes no uptime state at all.

**Fourteen mutation probes, each checked to have changed the code the test
runs, and all fourteen caught.** Two of them said something the others did not.
The first was re-run with `check_column_bounds` removed and the suite
**passed**, which is the proof behind the paragraph above. And the probe that
disables the `application_id` comparison disables only that half — `&&` binds
tighter than `||` — so the pre-existing `user_version` tamper case still passes
and the *only* thing catching it is the tamper case this slice added, which is
how a new case was shown not to be redundant with the one beside it.

**The local probe harness now covers a SQLite-dependent layer, which it did not
before.** M3.13p recorded that the snapshot suite links with no SQLite at all;
the store cannot. The amalgamation already present on this machine compiles once
at `-O0` in **3.4 seconds** into a 1.5 MB object, the 34 unchanged translation
units precompile in **11 seconds** across four jobs, and a probe relink is then
about four. No download, no dependency graph, and every artifact written outside
the repository and removed afterwards. That is what made fourteen probes
affordable, and it is worth rebuilding rather than rediscovering.

**One stale comment was found in version seven's header and deliberately left
alone.** It says the genesis is taken as a struct "because version seven
publishes `encode_genesis` and no inverse"; version seven has published
`decode_genesis` since the node process needed it. Version eight's header states
the actual reason instead, and version seven's text is left as it is because
ADR 0065's step 7 deletes the file. **A stale comment in a file scheduled for
deletion is not worth a commit, but carrying it forward into its replacement
is.**

### How M3.13p was delivered

**A version-eight state can leave memory.** `protocol::storage::snapshot_v8` is
version seven's snapshot with one subject added and one field widened: three
translation units and two headers, of which `snapshot_v8_assignments.cpp` is
version seven's file with three identifiers rebound and **nothing else** — the
normalising diff against it is empty, which is the strongest available statement
that nothing changed by accident.

**The two entry kinds are carried raw, and that is the whole design decision.**
`Ledger::uptime` is one raw key-to-value map, so the snapshot stores what
arrived. Decoding into fields and re-encoding on the way out would be a second
encoding of the key space the two version-eight transitions write, with nothing
keeping the two equal — the failure ADR 0026, ADR 0029, and ADR 0046 each
record. The entries are still *checked*: two rules are the kernel's own decoders,
reused rather than restated, and one of them closes ADR 0056's open note that a
later transition version should state the bitmap pad rule outright.

**`dispute_authority_key` is the one parameter with no second copy.** The
verifier key is also an economy entry, so a payload carries it twice and the
restore requires the two to agree. The dispute authority key is a genesis field
bound into the chain identity and appears in no economy key, so nothing in the
state root commits to it — and whoever holds it can void a machine's uptime. The
out-of-band comparison is the whole of what stops a restored node answering to a
different dispute authority than its peers, and a probe removing it reports "a
restore accepted it".

**One rule has no version-seven ancestor and one bound was deliberately left
out.** A window record equal to `full_seat_window()` is refused, because a
dispute sets a `disputed` bit and an expiry clears a `credited` one, so neither
writer can leave a fully credited, undisputed window behind; that value is what a
chain records by writing *nothing at all*, and carrying it would make one state
representable two ways under one root. A separate `kMaxSeatId` bound beside the
seat-existence rule was written, then removed before the commit: every seat the
chain sold is inside the capacity, so it would fire only where the existence rule
fires too, and a rule no test can isolate is the shape M3.13a and M3.13l were
each caught by.

**The evidence found something about the kernel rather than about the
snapshot.** Two of the six invariants M3.13o added — the window record's
retention bound and the open challenge's deadline bound — turn out to be the
*only* thing refusing a resealed payload that carries a well-formed entry in an
impossible place. Probes deleting either report "a restore accepted it". M3.13o
had already found that three of the six were unreachable by any recorded
scenario; this is the same finding one layer up, and the general rule it
suggests is that **every layer should ask which of its refusals survive a
reseal**, because those are the ones with nothing behind them.

**Thirteen mutation probes, and the one that passed was read rather than
patched.** Removing the encoder's own prefix-width assertion changed nothing,
because the prefix is in fact 158 octets — it is a tripwire for a later edit, not
a rule with a violating input. Giving it something to catch, by dropping a prefix
field instead, fails at "the final ledger must encode". A guard with no violating
input is not a defect, and mistaking one for a defect and deleting it would be.

### How M3.13o was delivered

**The kernel now runs version eight.** `src/v8/` gained version seven's seven
execution sources with three identifiers rebound,
`include/protocol/v8/ledger.hpp`, and `economy_uptime_transitions.cpp` for the
two transitions and the two block-step effects no transaction can request. The
whole version-eight kernel is nineteen sources and two headers.

**The block runs at every height, which version seven's does not**, and that one
sentence is most of the slice. The prologue assigns the due window and then
deletes its evidence unconditionally — which is what makes invariant 5 hold at a
boundary height without a second rule; the issue step audits every in-scope seat
against the block's own `previous_state_root`; the expiry step follows the
transactions. The three demonstration flags are one `BlockOrder` struct and none
is a configuration option a chain has.

**`run_quiet_heights` is what makes the recorded scenarios affordable.** They
run about 1.35 million heights between their recorded blocks, and the whole
suite — four scenarios executed twice for determinism, about 2.7 million heights
— takes 0.63 seconds. It works through a `state_root_frame` that `state_root` is
now *defined* through, so the fast path and the ordinary path are the same
preimage by construction rather than by agreement.

**The uptime invariants are split out as `uptime_failures`**, and the split is a
cost decision rather than a weakening: a quiet height can only break those six,
and the full conservation gate walks every seat's assignment records once per
seat, which ADR 0055 accepts at a block and which 1.35 million quiet heights
would not survive.

**Twenty-four mutation probes were run and five passed uncaught.** Four were the
same shape and it is the shape worth remembering: **an invariant nothing could
reach.** Three of the six version eight adds — the retention bound on a window
record, the deadline bound on an open challenge, and the open-challenge state
rule — could have been deleted outright with every recorded vector still
passing, and so could the quiet height's own gate. A recorded scenario cannot
reach them, because the steps that write these entries never produce the states
they forbid; that is what an invariant is *for*, and it is also why nothing was
testing them. Each is now checked by writing the forbidden state directly into
the raw uptime map and requiring the invariant to name the rule it broke, with a
positive control beside it so the refusal is about the state rather than about
the check.

**The fifth was a probe that mutated unreachable code rather than a gap**, which
is the other half of the same lesson. `derive_schedule`'s absent-record default
sits behind a branch `seat_window_record` never takes, so mutating it changed
nothing; re-aimed at the accessor every caller actually uses, it fails three
block roots.

**Two recorded lessons were paid again and both are worth re-reading before the
next layer.** The two expiry constants are not interchangeable — every builder
imported from version six carries version six's default, and unifying them
produces identical state roots and different transaction roots, so every block's
state matches and every header does not. And Clang refuses what GCC accepts: an
unused helper compiled clean under GCC 12 and would have failed two of the four
hosted jobs.

### How M3.13n was delivered

**Ten of the eleven sources are version seven's codec with three identifiers
rebound**, and nothing else: `namespace protocol::v7` to `protocol::v8`,
`protocol::v7::` to `protocol::v8::`, and `"protocol/v7/` to `"protocol/v8/`.
No blanket rewrite was run. After those three, **nine literal mentions of
version seven remained and every one was prose about history**, each kept or
rewritten deliberately — the three that survive are correct history about
version six's result codes, version six's retired entry kinds, and the genesis
requirement that has stood since version six.

**The eleventh source, `src/v8/economy_uptime.cpp`, is version eight's whole
addition to the state and its derivations in one translation unit**: the two
entry kinds, their value codecs, the window record's bitmap arithmetic, and
challenge selection. Putting it in one file rather than spreading it across the
other ten is what makes the difference between the two codecs auditable while
both are compiled, and it is what M3.13t will delete alongside `src/v7/`.

**The header's eight edits are the ones the plan enumerated**, and they landed
unchanged: the version constants and the 142-octet genesis prefix; the
measurement figures read from `uptime-measurement-v1`; twelve result codes and
the count at 45; the three re-versioned labels plus
`protocol-stack:v8:challenge` and `protocol-stack:v8:dispute`; two kinds and two
entry kinds; six `Body` fields; the `Genesis` field and its round-trip
consequence; and the new declarations. **`kFrozenUnreachableCodes` stayed at
three**, for the reason the plan recorded: the exemption makes three codes
unreachable for kind 20 only, and every other kind still produces all three.

**One correction to the recorded 9 / 8 file split.** `economy_settlement.cpp`
was written down as the execution half, but it implements only functions
`economy.hpp` declares — the bounded mint walk, `window_of_height`, and the
verified-user rate — so it is inside the codec's closure and moves with it.
**The codec slice is eleven sources, not nine**, and a session that had trusted
the recorded split would have found out at the linker.

**Twenty mutation probes were run and three found real gaps**, all fixed in the
same commit. Two of them are the same gap seen twice and they are worth reading
before writing another cross-version comparison:

* **A `predecessor_state_root` that wrote version eight's schema version into
  every preimage passed uncaught.** The labels still differed, so all seven
  predecessor roots still differed from version eight's *and from each other*,
  and every inequality comparison passed — about an artifact no chain ever had.
  Removing version one's economy-free preimage passed for the same reason. **An
  inequality between two digests proves nothing about either one.** The fix pins
  both ends of the range against the file that recorded it: version one's root
  against `protocol-primitives-v1.txt` and version seven's chain identity and
  root against `economy-transition-v7.txt`, over the fixture that file was
  recorded on. Both pins survive M3.13t, which a comparison against the live
  version-seven kernel would not. * **A `credited_slots` that ignored the
  disputed bitmap passed uncaught**, and it is M3.13l's shape exactly: every
  record the test built had an empty `disputed`, so the mutation never reached
  the executed path. The fix was a better test rather than a better probe — the
  disputed-record arithmetic is now checked, including the containment boundary
  at the cap — because the figures that distinguish the two live in the
  containment and kind-21 vector groups, which need a ledger and are M3.13o's.

**The carried surface is checked against the file that accepted it rather than
re-recorded.** `economy-transition-v6.txt` fixes the fourteen carried bodies,
their schemes, the thirty-three carried result codes, and one HUB message
reproduced as bytes; `economy-transition-v7.txt` fixes the carried entry widths
and the version-seven genesis this prefix is measured against. Re-recording
either under a version-eight name would have produced a file that agrees with
the first and says nothing.

**One check belongs to the port rather than to any vector group.** `src/v8/`'s
tree is version seven's copied, so it is required to reproduce the accepted M1
accounts tree root and empty tree root from `protocol-primitives-v1.txt`. A tree
that drifted in the copy would still produce self-consistent version-eight roots
and would fail there.
