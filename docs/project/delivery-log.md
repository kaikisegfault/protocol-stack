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

**The rest of the handoff followed on 2026-10-09.** It had regrown to 5,623
lines, not from records but from the narrative around them. Its whole body is
the [final section](#the-handoff-as-it-stood-on-2026-10-03), moved verbatim
with its headings demoted one level, and the handoff was rewritten to the
present under a line limit `tools/verify_metadata.py` enforces.

**A record here may describe superseded state.** It says what was true when the
slice landed. Where it disagrees with `current-state.md`, the handoff is
current; where both disagree with Git and verified test evidence, those win and
the handoff is what gets repaired.

## Delivery records

Newest first. Every record from `M3.15a` downward was moved verbatim out of the
handoff; `M3.15b` and anything after it was written here.

### How M4.4 was delivered

**Requirement 4 was taken before requirement 3, because 3 waits on the owner.**
Issue #376. The registry needs answers to two founder-reserved questions, and
the test verifier needs none. Requirements 3 and 5 will rebind what it signs,
so the interface takes a capture and a transaction rather than any one
message.

**The interface is C++, and the verifier builds what it signs.**
[ADR 0099](../decisions/0099-the-hub-verifier-is-one-interface-with-a-deterministic-test-implementation.md)
records the choice. A Python class would have been cheaper, but a production
verifier could not implement it, and it would have been a third construction of
the HUB messages. A verifier that signed an opaque digest, as a WebAuthn
assertion does, would give a compromised wallet a HUB signature for anything.
So `approve` decodes the transaction and calls the kernel's own builders.

**Reading the fixtures changed the interface.** A registration is kind 10
under scheme 2, so the person's HUB key signs its envelope as well as the
verifier key signing its body. The first draft returned a signature. It now
returns the whole signed transaction for the five kinds the HUB key authorizes,
and a body signature for the eight it confirms.

**The test found a defect in the verifier before any run.** The constructor
derived the verifier keypair in its initializer list, into `secret_key_`.
`secret_key_` is declared after `public_key_`, so its own `{}` initializer ran
next and zeroed the key. The chain refused the first registration as
`UNAUTHORIZED`, and a one-file probe printed the code. The derivation is now in
the constructor body, with a comment saying why.

**Requirement 5's finding is now executed, not read.** The handoff trim had
recorded, from the specification and the kernel, that a HUB approval appears
reusable. `check_version_nine_accepts_a_replayed_approval` runs it. Alice
relaxes with an approval and tightens with her signer. The published relax is
then accepted again under a new nonce, and one transfer confirmation moves value
twice. The check asserts that version nine accepts both, so requirement 5's
contract will flip it.

**Three mutation probes each fail a check.** Dropping the posture's minimum
amount from the relax message passes the C++ test and fails the cross-check.
That is why the cross-check uses a nonzero minimum and mask. Deleting the
`not_the_person` comparison fails both. Renaming the identity label fails the
cross-check, which restates the derivation from the ADR rather than reading it
from the command.

**It was built locally without CMake.** The host has no `cmake` or `ninja`, and
`tools/verify.sh` would install them into a venv cache. Instead, the 28 kernel
sources and the three new translation units were compiled with `g++` and `-Werror` against a
scratch `sodium.h` that declares the six symbols in use. They were linked to the
system's libsodium 1.0.18 runtime. The cross-check ran through a scratch runner
that relaxes only `pinned_sodium`'s 1.0.22 version check, and Clang 14 checked
the new files' syntax. Nothing scratch was committed. The hosted matrix is the
gate, on the pinned 1.0.22.

**The founder-decision gate passed.** Six decisions were enumerated:

1. what the verifier produces;
2. how a test identity maps to its commitment and key;
3. the interface;
4. the language;
5. the stand-in "is this the person" check;
6. the order in which a person acts.

The first is requirement 4 and the version-nine authorization table. The
second and fifth are labelled test stand-ins, and the production derivation and
match threshold stay reserved under ADR 0048. The third and fourth are
mechanism within `CLAUDE.md`'s language rules. The sixth is ADRs 0039, 0043,
and 0048, unchanged. None sets a value or changes what a participant must do,
own, run, or receive.

### How the handoff trim was delivered

**The handoff named the plan, and it was taken whole.** Issue #373. Everything
from `## Phase` to the end of `current-state.md` moved to this log's final
section, and a script did the move. Reversing the heading demotion reproduces
the 5,619 moved lines byte for byte. No anchored link pointed into the
handoff, and the moved relative links resolve from the same directory, so
nothing else changed.

**The rewrite carries only what was checked against the tree or GitHub.** It is
301 lines. The figures were taken again rather than copied:

- 162 execution vectors in version nine's file, not 125;
- 21 translation units under `src/v9/`, where "What works now" still gave
  the twenty-two sources of 2026-09-16;
- 173 CTest entries, or 182 on `clang-sanitizers`, from candidate run
  37078876254's own logs;
- the eight network runs `tools/verify.sh` names.

Its founder direction is the constitution's as it now reads. So the seat has no
address and the sixteen-manager limit is gone, which the old "Adopted founder
direction" still stated.

**The audit carried the same stale figure.** The execution file held 162 vectors
at `3c5347b`, the audited commit, because M3.19c had added 37 on 2026-09-18. The
audit said 125, as the handoff did. It now carries a dated correction, and the
leg's status does not move.

**The bound is mechanical.** `tools/verify_metadata.py` refuses the handoff
above 600 lines, and runs on both verification paths. Its test pins the limit
as a literal and checks 600 and 601 lines. Appending 300 lines to the real
handoff failed the verifier by name. `CLAUDE.md` and the conclude skill now say
that a slice rewrites the sentences it makes false. The first split had only
said where records go, and the handoff regrew through narrative instead.

**Rewriting found what appending had hidden.** Stating requirement 5 in the
present tense meant reading version nine's HUB messages again. None binds a
nonce, and the kernel checks `valid_until_height` only from below. So a
published posture-relax approval appears reusable after its owner tightens
again, by anyone holding that escrow's signer key. That is the weakening ADR
0043's asymmetry forbids. The handoff records it as a reading for requirement 5
to confirm with a vector, not as a demonstrated defect.

**The founder-decision gate passed.** Seven decisions were enumerated:

1. where the history goes;
2. whether it moves verbatim;
3. the line limit;
4. what the handoff carries;
5. the new `CLAUDE.md` rule;
6. the audit correction;
7. the order of the next actions.

The first two follow M3.15b and `CLAUDE.md`. The third is engineering, and the
handoff's plan named it. The fourth is `CLAUDE.md`'s "verified facts and an
exact next action". The fifth is process, and the owner flagged the regrowth on
2026-10-03. The sixth is a fact, and the seventh is sequencing. Requirement
3's two questions are founder-reserved, and this slice asks them rather than
answering them. None sets a value or changes what a participant must do, own,
run, or receive.

**Merged and verified.** PR #374 merged by rebase as `02711af` and `91f8067`,
closing #373. Run 37946120672 on the PR head `c88fda8` passed all six checks:
173 CTest entries on three presets and 182 on `clang-sanitizers`, with
`repository-metadata` and `verify-metadata` passing in every job, and all eight
network runs. `main`'s tree at `91f8067` is byte-identical to the candidate's,
so that run is `main`'s evidence.

### How M4.2c was delivered

**The handoff's plan was taken, except for how the history is stamped.** It
suggested stamping the history three days back at the commit target's pace. That
would look like a real network, but whether the history crossed a month boundary
would then depend on the run's date. Today's date, 2026-10-03, would have
crossed one. The model would still agree with the C++ either way, but a failure
on the 2nd of a month might not reproduce on the 15th. At one millisecond a
block, the 86,400 heights fit inside two minutes of the launch, so every window
opens in the launch's month and the run's path is the same on every date.
Neither mint reads a stamp, so their amounts are unaffected. The contract sets
no minimum time per block, and C2 allows equal stamps.

**Measuring the model first made the hosted budget a non-question.** The trace's
fast path, `run_quiet_heights`, ran 57,615 heights of the two-seat trace in 2.4
seconds. The seed history, 86,400 heights with one seat, takes about two.

**The head is the block that assigns window 1.** A seat activated in window 0
is first audited in window 1, and window 1 is assigned at height 86,400, the
first height of window 3. The history ends there, so both mints have something
to collect from the network's first block.

**The model's fast path forced two small choices:**

- `run_quiet_heights` refuses to end while holding an input. So the machine
  does not answer an audit issued at the last quiet height, whose answer could
  only land in the head. In the local runs no audit fell there.
- The fast path computes no root for a height it passes. `Chain` records those
  heights as unknown. A seeded network never reports a root below its head,
  because readiness waits for the engine's first block.

**Kind 20 needed the fixture's builder fixed.** `_build` gave a fee limit of
zero only to registrations, and admission requires zero for every exempt kind,
which includes the challenge response.

**The exact amounts turned "more than zero" into an equality.** The first
offline run issued 57,430,000,000 atomic for the kind-4 mint, which is
`BASE_PERMISSION_TOTAL`: the constitution's 574.3-unit permission per cycle. Seat
0 met the cycle and is the only seat, so it neither gains nor loses a
reallocation, and the check now requires that figure exactly. The kind-18 mint
issues `2 × VERIFIED_USER_DAILY_ATOMIC` for windows 1 and 2, and is required
exactly too.

**The refusals were chosen for what a network can say about rights:**

- a repeat of each mint is refused as `NOTHING_TO_MINT`, which is "one button,
  everything" observed by four replicas;
- Bob minting Alice's seat into his own escrow is refused as `UNAUTHORIZED`,
  because a seat's rights belong to its identity.

A refusal consumes no nonce, so both repeats carry the same nonce and differ
by kind.

**The first candidate ran the model and the offline check locally, and nothing
else.** This machine had no pinned libsodium 1.0.22, so both used a stand-in
signer, which checks the script's logic but not its signatures. The network run
needs the C++ application, four Go binaries, and CometBFT, so it went to the
hosted matrix.

**Hosted run 37077096306 on `8c0fb15` failed all four jobs, on the new run
alone.** All 173 ctest entries and the seven other network runs passed. The
seeded launch was accepted, block 86,401 carried the head's stamp, and the
empty blocks agreed with the model. Then Alice's kind-18 mint committed, and
node 0 reported a root the model did not produce.

**The defect was isolated without a network.** Only the application target was
built locally: the pinned cmake and ninja in the toolchain venv, then
`protocol_application_server_v9` in 80 seconds. A scratch script seeded a store
from the same model history and drove the application block by block over its
socket. `FinalizeBlock` applies no clock tolerance, so there was no launch
window to race. The launch block and twenty-five empty blocks agreed. The mint
issued 5,130,000,000 atomic in C++ and 342,000,000 in the model.

5,130,000,000 is thirty daily permissions, which pointed at the cap.
`verified_user_collection` computed `collectable_end - kMintAccumulationCap` in
unsigned arithmetic. At `collectable_end = 2` that wraps, the wrapped value wins
the maximum against the mark, and `count` comes out as thirty modulo `2^64`. The
specification states the maximum over integers, and the Python model computes
it that way. So every kind-18 mint before window 31 had over-issued in C++.

**ADR 0098 repairs it inside version nine**, as ADR 0094 repaired the referral
mark. The capped start is the difference when positive and zero otherwise. Every
other subtraction in the kernel's window arithmetic was checked, and each is
already guarded. `economy_v9_verified_user_collection.cpp` pins eleven
collections at figures the Python model produced, written as literals. It fails
on "one window completed" against the unrepaired line, which was checked by
restoring it, and passes against the repair.

With the repaired application, every block of the scratch run agreed with the
model, both mints and all three refusals included. The pinned libsodium came
with the build, so the offline fixture check and `version-nine-seed` were then
run with real signatures, and both passed. The build tree was removed with
`tools/clean-local.sh`.

**No recorded vector could have found it.** Version six's trace mints kind 18
in window 0, which the kernel returns early from, and again after the cap. No
recorded kind-18 mint at any version falls in windows 1 to 30, and before M4.2c
no network reached a window past 0. It is the first defect in this repository
that a network found rather than a model.

It merged by rebase on 2026-10-03 through PR #371 as `c599440`, `6cf877a`,
`d6798f7`, and `f97b190`, closing issue #370. Candidate run 37078876254 on the
PR head `775b29a` passed all six checks. The debug and GCC sanitizer jobs ran
173 ctest entries and `clang-sanitizers` 182, all passing. Every job then ran
every network run, including "CometBFT seeded-mints version-nine integration:
passed". The merged tree, `54b55b4`, is byte-identical to the candidate's, so
that run is the evidence for `main`. Push run 37079796947 re-verifies the same
tree and was not waited on, under `conclude-project`'s step 5 as revised on
2026-10-03.

### How M4.2b was delivered

**The restart question decided the design.** The first draft seeded node 0 and
read the head from what `--seed` printed. Then came the restart: after one block
the stores are past the seeded head and cannot say what it was, yet the
launcher re-derives the engine's genesis on every start and compares it with
every home. Three ways to recover the head were weighed:

- persist it beside the homes, which compares the homes against the launcher's
  own file;
- seed into a temporary path on each start, which copies the whole state to read
  four numbers;
- give the application a mode that runs the seed's checks and writes nothing.

The third won, as `--inspect-seed`. Its checks and the seed's are one function,
`check_seed`, factored out of `seed_sqlite_ledger_v9`, so they cannot drift.

**The genesis time was taken as the seeded stamp exactly**, not "no earlier
than" it, as the handoff had put it. A time chosen at launch would be a fourth
value outside the head, which a restart would need persisted or passed in. The
cost is that a seeded network has the same one-minute window as any other,
counted from the seeded stamp, and M4.2c's plan now says so.

**The first network run found what reading the engine had missed.** Unit tests
covered:

- the derived genesis document;
- the refused launches;
- the exact key set of the printed head;
- all-or-none seeding.

All passed. Then the first local four-validator run failed readiness, and node
3's log showed a panic in `logNodeStartupInfo` on a nil validator set. The
engine source in the module cache showed why. `NewNodeWithContext` reloads its
state store after the handshake, and only the `InitChain` path saves one. ADR
0096 had read the handshake branch correctly and stopped one call short.

The fix writes the state the `InitChain` path would have saved: the genesis
document's state with the empty results hash. It writes into a fresh seeded home
only and never over a state the engine has moved. ADR 0096 gained a correction
note pointing to ADR 0097.

**The run was taken locally before any hosted cycle**, with the Go binaries and
the gcc-debug application built in the scratchpad, and a scratch copy of the
tests with the libsodium pin relaxed. The second run passed:

- block 5 was stamped with the seeded stamp;
- two transfers landed on the model's roots;
- three wrong launches were refused, with homes and stores byte-identical;
- the restart worked.

A devnet binary whose seeded genesis time was 1 ms late failed the run by name
at block 5. The source was restored and compared byte for byte with a saved
copy.

**One test fixture was wrong and was fixed.** The engine-state test first
faked a moved state by raising `LastBlockHeight` alone. The engine refuses to
load a state above height zero without a last validator set, so the fixture
now sets one, which is what a real state after one block holds.

**The mutation run exposed a harness defect, shared by every network test.**
Four applications and four bridges from the failed run were still alive
afterwards. The test's `finally: process.kill()` had SIGKILLed the supervisor,
which then could not tear down its children. `ManagedProcess.kill` now sends
SIGTERM first and allows the supervisor's own teardown bound, 50 seconds for
its three phases of 15, before it kills. Every caller uses `kill()` as cleanup
after `stop()` rather than to simulate a crash, so only failure paths change. A
rerun of the failing mutant left no process behind. Hosted runners are
ephemeral, which is why this had never shown there.

It merged by rebase on 2026-09-29 through PR #368 as `a134435` and `17e51c9`,
closing issue #367. Candidate run 36602233169 on the PR head `0c030cb` passed
all six checks. The run on the first head, `8272c0f`, was cancelled by the
workflow's concurrency rule when the harness fix was pushed. The gcc-debug job
ran 173 ctest entries, all passing, and then every network run, including
"CometBFT seeded-launch version-nine integration: passed". Push run 36604219737
on `17e51c9` passed all six jobs.

### How M4.2a was delivered

**The route was chosen by reading the engine, not the ADR that named it.**

- ADR 0071 left two routes open, and one of them, a nonzero initial height,
  is a contract change.
- CometBFT v0.39.4's `Handshaker.ReplayBlocks` in `consensus/replay.go` was
  read from the module cache. It sends `InitChain` only at application height
  0. When its own store is empty and the application reports a nonzero height,
  it only compares app hashes.
- `ApplicationV9` is ready whenever its store's height is nonzero, and opening
  a store never reads its block rows.

So the snapshot route needs no contract change, and ADR 0096 records that with
the line numbers.

**The seed's provenance question was settled before the code.** The candidate
sources were:

- the model executing real blocks;
- the network replaying the history into each node over its socket, about
  90,000 durable commits on four nodes;
- a C++ tool that would sign challenge responses live.

The model won. It already has a real signer and a responder, and the C++
restore gates, not the harness, decide whether its state is one a chain could
hold.

**The encoder was checked by the path that uses it.** A seed succeeds only if
the C++ decoder accepts the Python octets through all three gates and
re-encodes the decoded state to the same octets. The first run passed on the
restart and settled chains.

**The test's own claim was then found false and fixed.** Its docstring said
the two chains covered every entry kind. They carried 16 of 20: no referral
balance, typed custody, open challenge, or direct decision. Two ledgers were
added:

- a seated chain stopped at the first outstanding challenge;
- the M3.21c population at window 200, labelled as encoding coverage rather
  than provenance, because its uptime was supplied.

The test now requires all 19 writable kinds. Kind 5 is excluded because kind 6
refuses every sender.

**Three mutations each failed by name:**

- dropping the store's height-zero refusal;
- swapping two prefix fields in the encoder, which made the real seed refuse;
- a stale `.pyc` from that second mutation, found while restoring it. The
  mutated and restored files had the same size and the same second, so Python
  reused the bytecode. The cache was cleared and the test re-run.

It merged by rebase on 2026-09-27 through PR #366 as `44f0978`, closing issue
#365. Run 36357752278 on the PR head `dddbd89` passed all six checks. The
gcc-debug job ran 173 ctest entries, M4.1's 172 plus `version-nine-seed`, all
passing, and then every network run.

**ADR 0096's account of the engine was incomplete, and M4.2b found it.** The
handshake branch it read is real, but a seeded node also needs the state that
only `InitChain` saves (ADR 0097).

### How M4.1 was delivered

**The lifecycle was proved on the model first, then on the C++ application, and
only then written as a network run.**

1. A scratchpad prototype ran the whole script through the version-nine model
   with stand-in signatures. It confirmed the three refusal names the run would
   assert: `SIGNER_NOT_FOUND` for a revoked key, `UNAUTHORIZED` for a foreign
   or signer authority, and `ESCROW_NOT_EMPTY`. It also confirmed that
   revoking an identity's last signer is permitted and leaves recovery open.
2. The builders went into `version_nine_chain.Session`, and the script into
   `founder_lifecycle_v9.py`, so the network run and the offline check read
   one list.
3. `version_nine_chain_test.py` gained a tenth check that runs it with real
   Ed25519.
4. A scratch driver started the locally built `protocol-application-v9` over
   its socket and finalized and committed all eighteen blocks. It restarted the
   process where the network run restarts the network, and compared every
   receipt and root with the model's. All eighteen matched byte for byte.

That last step is what makes the first hosted run a confirmation rather than a
discovery. The network run adds consensus, four replicas, and the engine's
stamps, but the transitions it exercises were already shown to agree across
languages.

**The run asks nothing the contract does not already decide.** Signers and
holding escrows are ADR 0040's. Recovery is an ordinary `signer_add` under the
identity, which is ADR 0044's. The keys are fixtures, as the roadmap's
deterministic-test-verifier line directs.

**Two local limits were worked around, not hidden.**

- The pinned-libsodium check refuses this container's system library. The
  offline check ran against a scratch copy with the pin relaxed, and CI runs
  the pinned build.
- CometBFT does not run here, so the network run itself is the hosted matrix's.

It merged by rebase on 2026-09-27 through PR #364 as `f6a06d6`, closing issue
#363. Run 36356341647 on the PR head `42585c9` passed all six checks. The
gcc-debug job's log shows the network run's own line, "CometBFT founder-lifecycle
version-nine integration: passed", with its eighteen transactions and five
refusals on four replicas, beside the 172 ctest entries.

### How M3.21d was delivered

**Requirement 16 is three acts, and none of them is code.** Its evidence is:

- push run 36354823837 on `e79ea4d`, M3.21c's merge;
- `roadmap.md`, which marks M3 complete and M4 active;
- the handoff, which names M4.1.

**The M3 goal was retired by the M2 precedent.** `first-goal.md` moved to
`goals/m3-founder-economy-devnet.md` under a "Completed operational goal"
header. Its body is unedited except for the relative links the move broke.
That is what `goals/m2-founder-economy-proof.md` did.

**The new `first-goal.md` is drafted, not dictated, and says so.** It restates
the roadmap's M4 scope, and the accepted identity ADRs 0039 to 0048, as eleven
requirements. It starts from what the chain already executes. Every value the
constitution reserves is gated:

- legacy limits, precedence, and reclaim;
- inactivity;
- verifier key rotation;
- seat payment proofs;
- production biometrics.

**The first M4 slice was chosen by reading what the network has never done,
not what the kernel lacks.** The version-nine kernel executes escrow creation,
signer addition and revocation, and recovery under the HUB key. No integration
run has submitted one of them. So M4.1 needs no contract, only a lifecycle on
four validators. Its founder-decision gate held: every step is an accepted
transition, and the keys are test fixtures the roadmap directs.

It merged by rebase on 2026-09-27 through PR #362 as `155ae65`, closing issue
#361. Run 36355082297 on the PR head `6d1dc18` took the metadata path and
passed. Push run 36354823837 on `e79ea4d`, which requirement 16 cites, had
passed all six jobs before the merge.

### How M3.21c was delivered

**The suite drives the contract itself, not a fourth simulator**, and ADR 0095
gives the three options. Every quantity the audit's four claims are about
changes only in a window's prologue or in an executed transaction. So the run
does exactly two things:

- it opens each window through `block.open_window`, a new public function that
  calls the existing `_prologue`;
- it executes each participant's signed transactions at their own heights.

The kind-19 records are the only thing supplied, because they are the only
state the skipped heights write that the settlement reads. The whole run takes
about two seconds.

**The fixture was prototyped in the scratchpad before any of it entered the
tree.** The first prototype's 800-window loop showed the approach was cheap.
The second showed the population reaching every path the claims need: windows
with no winner, multi-winner windows, both caps, monthly ties, and a drain to
zero. Working out its referral schedule is what found the ADR 0094 defect,
which became M3.21b before this slice went on.

**The closed form and the run were made to disagree before they were made to
agree.** The first comparison failed on `over_cap_seat_windows`: 50 in the walk
and 47 in the run. The walk counted every in-span seat past its cap. The run
counted seats that met the cycle and still accrued nothing. The second is what
the cap alone decides, so the walk took that definition. The property tests
then found a live-side count that assumed every seat lived all 731 cycles,
which a run stopped at a horizon does not. It now counts the unreferred cycles
actually assigned.

**The fixture became a parameter object so the property tests could be
differential.** `Fixture` in the model and `Params` in the walk restate the same
table independently. The 32 seeded draws vary people, seats, the referral
graph, stagger, the uptime table, outages, collection periods on both sides of
the cap, lapses, genesis dates, and block rates up to a window every 200 days.
Every figure agrees on every draw. The test requires the draws to reach every
path it exists for, so it cannot pass vacuously.

**One spec claim was corrected before commit.** The draft said a nonzero monthly
remainder was covered by `economy-transition-v9-execution.txt`. That file
records only zero remainders. The property draws reach 85, and the test now
requires one.

**February 2028 splits its pool six ways, and that is arithmetic, not a
coincidence.** It has 29 windows, and 29 is the uptime pattern's modulus, so
every seat passes through every residue once and all six figures are equal.

The verifier refuses seven mutations. They include ADR 0094's zero mark
restored in the model, and a walk that ignores the cap, which reproduces every
channel total and is still refused on the count of cycles the cap cost.

It merged by rebase on 2026-09-27 through PR #360 as `e79ea4d`, closing issue
#359. Run 36353987502 on the PR head `c6797cf` passed all six checks, and push
run 36354823837 on `e79ea4d` is the hosted verification M3.21d cites for
requirement 16.

### How M3.21b was delivered

**The fourth scenario suite found a consensus defect before any of its code was
written.** Its design needed a closed form for what each referrer accrues, so
the version-three rule for a new referral balance was read against the code
that executes it. The rule starts the referrer's mark at the window before
their first accrual. Every implementation starts it at zero. A scratch run on
the version-nine model settled it: a seat activated in window 100 credited its
referrer once, and sent every later leg to the unreferred pool.

**The first question was whether the rule is still normative, and it is.**
Version six carries cycle assignment "unchanged from version three in every
respect", and version nine incorporates "every rule of versions one through
seven" by reference. No later ADR or founder answer revisits the starting
mark. So the chain is not following its accepted contract, and the
repair changes no rule.

**The second was whether any accepted artifact recorded the defect.** The
corrected Python models were run against every vector file from version six to
version nine, 2,977 vectors in eight files, first in a scratch copy and then in
the tree. All pass unchanged. The recorded referral scenario mints in the block
that makes its first accrual, so the zero mark never reaches a root.

**That made it a repair inside version nine rather than a version ten**, and
[ADR 0094](../decisions/0094-a-new-referral-balance-starts-at-the-window-before.md)
gives the reasoning. The repair is `first_referral_balance` in version six's
ledger, called by the version-six and version-seven ledgers, and a
`try_emplace` in `src/v9/economy_assignment.cpp`. Both refuse a zero window
rather than wrapping it.

**Each test was shown to fail on the defect before it was trusted.**

- The C++ check drives the kernel's own `derive_schedule`,
  `derive_assignment`, and `apply_assignment` over windows 101 to 131. Built
  against the unrepaired kernel, it failed on its first assertion.
- The Python test runs a chain with signed registrations, a referred purchase,
  and an activation in window 100, then opens windows through the version-nine
  prologue. Restoring the zero mark in version seven's ledger alone failed four
  of its nine tests. The other five pass either way: they cover the helper's
  own arithmetic, the channel identity, and a referrer who mints at once, none
  of which the defect touches.

Locally, under `gcc-debug`, every suite that restores or replays a recorded
version-nine chain passed against the repaired kernel: the snapshot, the owning
store, the application, the transport, and both headless processes. The socket
tests needed a short path to run, and the two failures left were the known
container limits: the SQLite version pin and the pinned-libsodium differential.

It merged by rebase on 2026-09-27 through PR #358 as `c40c150`, closing issue
#357. Run 36352857899 on the PR head `26d1899` passed all six checks.

### How M3.21a was delivered

**The exit audit exists because no single place stated all sixteen requirements
against their evidence**, and the one leg it found unmet had been reported met.
It is a documentation slice:
[`founder-economy-devnet-audit-v1.md`](founder-economy-devnet-audit-v1.md), a
pointer to it from `first-goal.md`, and its entry in the documentation index.
It uses the metadata path. **It closes nothing**: M3 stays active.

**Each requirement was checked in three places**:

- the accepted artifact that defines it;
- the ctest entry that runs it, taken from the 168-entry inventory of a scratch
  build of `main`;
- the hosted run that executed that entry.

Where a requirement's words were met and something a reader might assume was
not, the audit says "met with a limit" and states the limit.

**Requirement 14 was found by reading what the multi-year suite imports, not
what the handoff said about it.** `economy-scenario-suite-v3` imports
`founder-economy-simulator-v3`, whose state still has
`performance_carry_atomic`. The recovery pool replaced that carry on 2026-08-19.
Version seven's contract vectors record an eight-cycle schedule. Version nine's
settlement machine runs a sampled sequence to window 155. So the contract the
chain executes has never been run over a whole distribution. The handoff's
"requirement 14 is met against the v3 contract" was true when written and
stopped being the requirement's subject when the contract changed.

**Three checks guarded against over-claiming.**

- **Requirement 8's row was corrected before the first push.** It said
  "enforced from version seven". The 18-of-24 rule is `uptime-measurement-v1`'s,
  and a cycle is decided from *measured* evidence only from version eight.
- **The next slice's wording was narrowed twice.** A research population does
  not bring a channel to its cap, so the claim became "delivers what the
  manifest promised for the cycles that ran". And the chain cannot be driven
  over a whole distribution, because `advance_to` refuses once a seat is
  active. Scouting then found that version nine's own `_assignment` is already
  the window-level composition the suite needs, so the handoff points there
  instead of at two older models stitched together.
- **The first-goal's own founder-decision gate was checked against the
  code**, not assumed. Kind 6 refuses every sender while its predicate is
  undecided, so no eligibility mechanic was invented for the reserved
  channels.

It merged by rebase on 2026-09-27 through PR #356 as `23384bb`, closing issue
#355. Run 36350685138 on the PR head `ce28a9a` took the metadata path and
passed, as a documentation-only change should.

### How M3.20l was delivered

**The two gaps the handoff recorded are closed, and each closed with its own
evidence.** Issue #353 delivered two independent fixes. The first is a restore
rule, recorded in
[ADR 0093](../decisions/0093-a-restore-refuses-an-orphan-referral-balance.md).
The second is a metadata check. `tools/verification_scope.py` classifies the
change `full`, because it touches C++ and Python sources. **No accepted vector
file, specification rule, manifest, encoding, or kernel source changed**, and
ctest counts are unchanged.

**The restore rule was placed by asking what execution reads.** The orphan
referral balance M3.20k found could have been refused in
`conservation_failures`. That function is the kernel's invariant set, and
execution reads it too, so a stricter clause there is a consensus-visible
change. `snapshot_v9`'s `complete` step already refuses uptime entries,
figures, and claims that name an unsold seat. The orphan rule sits beside
those, so it can only refuse a payload no block wrote.

**Reading the one writer settled what "unreachable" means.**
`apply_assignment` is the only code that writes a referral balance. It accrues
whole legs to a seat's `referrer_hub_identity`. No transition erases a seat or
rewrites its referrer, and a purchase refuses self-referral. So there are two
unreachable states, not one: a balance no seat's referrer owns, and a balance
that accrued nothing. The second became a value rule, the monthly claim's zero
rule applied to the balance that claim was modelled on.

**The positive control needed a seat no recorded chain has.** The trace buys
every seat without a referrer. The test therefore gives the settled chain's last
seat one, naming a registered identity other than its owner, and reseals the
payload. It requires that payload to restore before any case uses it. The pair
that proves the rule differs in that seat's flag and nothing else: a fully
minted balance restores beside a referring seat and is refused without one. The
inherited minted-above-accrued case moved onto the referring payload, because
the orphan rule would otherwise have refused its control first. **The orphan
rule broke that control on the first run, which is the evidence that it
reaches.** Removing either rule fails its case by name. The snapshot, store,
recovery, application, transport, and headless process suites all restore
recorded version-nine chains and still pass.

**The anchor check followed the one subtlety the handoff recorded.** GitHub
turns each space into a hyphen and does not collapse runs. So "Kind 10 —
`hub_register`" anchors as `kind-10--hub_register`, and a collapsing checker
reports that heading as broken when it is not. The check computes anchors for
ATX headings, skips fenced code, numbers repeats `-1`, `-2`, and so on, and now
checks same-file `#section` links too. That raises the checked-link count from
615 to 652. All 41 fragment links in the tree resolve. That is the same number
M3.19a swept by hand. Two probes bit: a collapsing slugger fails the repository
sweep at exactly `economy-transition-v6.md`'s `#kind-10--hub_register`, and a
broken real anchor is reported by name. `docs/engineering/verification.md` now
says what the metadata path checks.

**Both were prepared while M3.20k's hosted run was still going**, on local
branches, and replayed onto the recreated delivery branch once PR #352 merged.
So the repository never had more than one remote delivery branch.

### How M3.20k was delivered

**Version eight is deleted, and the repository compiles one economy contract
again.** Issue #351 delivered the deletion under ADR 0070's method, recorded in
[ADR 0092](../decisions/0092-the-version-eight-deletion.md). It removed version
eight's C++ kernel, owning store, snapshot, application, transport, and node
process. It removed their tests, targets, CTest entries, and two `tools/verify.sh`
runs. The Go adapter lost its version-eight client, decoder, bridge constructor,
codespace, protocol version, and application state. ctest falls from 178 to 168
under the GCC presets and from 188 to 177 under `clang-sanitizers`.
`tools/verification_scope.py` classifies it `full`. **No accepted vector file,
specification rule, manifest, encoding, or version-nine kernel source changed.**
The code and its record were pushed together, so one hosted run covers the
final head. Run 36348371153 on `290b2fc` passed all six checks. ctest printed
168 under the GCC presets and 177 under `clang-sanitizers`, and all five
integration runs passed. It merged by rebase on 2026-09-27 through PR #352 as
`f750ecc` and `31f1d18`: two commits, 120 files, **1,573 insertions and 20,695
deletions**.

**The handoff named two traps and there were five, and the larger two were
evidence version nine had borrowed.** The two named ones were `economy_v8_fuzz`
and ADR 0082's line about `wire_v1`. The survey then checked every deleted item
for a version-nine counterpart, as that handoff asked. It found three more:

- three version-nine kernel test files that included `protocol/v8/economy.hpp`;
- a version-nine snapshot suite whose header said version eight's suite "holds
  the full set" of the inherited refusals;
- `receiptResultOffset` declared in `wire_v8.go` and read by `wire_v9.go`.

**The re-pin used files, not a surviving kernel.** Nineteen checks now read
version six's, seven's, and eight's accepted files through
`economy_v9_carried.hpp`. Two of them are stronger than what they replaced.
**Version nine's kind and entry tables must now equal the recorded
predecessor's plus exactly what version nine adds**, where before the suite
asked only that each new number was unassigned. And the mint message is
compared with version six's *recorded* bytes, rather than with a sibling kernel
that was itself a port. One old comment said version eight's file "does not
record the count". It does, as `result.code_count=45`, and that is now the pin.
**Six claims are behaviour of version eight**, such as that it refuses a kind-22
transaction. No C++ can answer those any more. The coverage guard hands them to
`tools/economy-transition-v9-vectors/verify.py`, which already ran all six
against the version-eight Python model. Fifteen probes each corrupted one
recorded figure in a scratch copy, and each failed the suite by name.

**The snapshot sweep needed a fixture version nine did not have.** Version
eight's uptime cases ran on its `deadline` scenario, the one state holding an
open challenge beside a window record. No recorded version-nine height holds
one. A probe over the settled chain's audit heights found the first audit after
setup does, so the new file rebuilds the chain to
`settled.audit_blocks[1].height` rather than naming a height. Referral balances
and custody entries appear in no version-nine chain at all. Their cases insert a
resealed entry, and each is paired with a lawful twin that must fail at gate 3.

**Writing that control is what found the orphan balance.** Its first draft was a
fully minted balance, and the restore accepted it. A probe then showed the gap
is narrow. An inserted balance that owes anything is refused, and so is one for
an unregistered identity. Only an orphan that owes nothing passes. It is
recorded, not fixed here, and it is the next action.

**The driven-application test was mapped, not ported.** Each of its scenarios
has a version-nine counterpart in the four-validator driven replica, the
headless process test, or the transport suite over a real socket. ADR 0092
lists them.

**The local evidence ran in this container against system libraries**, because
the pinned libsodium and SQLite hosts are unreachable from it. `libsodium-dev`
and Clang's runtime were installed for the purpose. The scratch build copied the
tree, swapped the two external projects for system libraries, and built every
target under GCC. All tests passed except three kinds, each for an environmental
reason that was checked:

- the SQLite pin assertion;
- the two suites that require libsodium 1.0.22;
- four socket suites whose scratch path exceeds `sun_path`. All four pass when
  run from the repository's own `out/` directory.

The Go module builds, vets, and passes its tests with the pinned toolchain. The
new fuzz target and version nine's snapshot target were built under
`clang-sanitizers`. Both smoke entries passed, now under the `fuzz` label, and a
200,000-run pass of `economy_v9_fuzz` was clean. The hosted matrix is the
evidence of record.

### How M3.20j was delivered

**One replica of a version-nine network runs on a wrong clock, and the network
does not notice.** Issue #348 delivered
`tests/integration/cometbft_skewed_replica_v9_test.py` in `tools/verify.sh`, the
test-only `libprotocol-clock-offset.so` and its Python helper, the devnet
supervisor's `-application-env`, two RPC helpers, the headless process test's
two clock-failure paths, and
[ADR 0091](../decisions/0091-the-skewed-replica-is-skewed-below-the-process.md).
`tools/verification_scope.py` classifies it `full`. The code and its record were
pushed together, so one hosted run covers the final head. Run 36067243440 on
`aab7993` passed all six jobs. Each preset printed "CometBFT skewed-replica
version-nine integration: passed", in about 46 seconds under each sanitizer
preset. ctest stayed at 178 and 188, because the slice adds a build target and
an argument to an existing entry rather than an entry. Merged by rebase as
`7de55e2` and `fa68b69` on 2026-09-24 through PR #349. Two commits, nineteen
files, **1,330 insertions and 60 deletions**. **No accepted vector file, specification
rule, manifest, encoding, kernel source, or production process changed.**
`protocol-application-v9` is untouched.

**The decision was where to move the clock, and the answer was below the
process.** ADR 0085 had left two candidates: an operator option that offsets
the reading, and an `LD_PRELOAD` shim. The option contradicts two accepted
statements as written. The contract says a deployment's clock *is* the platform
real-time clock, and ADR 0085 §5 says the process takes no flag that moves it.
It would also put the skew arithmetic in the shipped binary. A shim of one
function, built in the repository, leaves both statements true. It skews the
binary that ships, at the level where a real machine's clock is wrong.
`libfaketime` would have been an unpinned dependency installed on every runner,
and a Linux time namespace cannot move `CLOCK_REALTIME` at all.

**The shim re-reads its offset on every call, and that is what made one run
cover three clocks.** Replica 3 starts 120 s ahead, moves to 120 s behind, and
is corrected, all while the network runs. Which heights each clock governed is
read from the replica's own committed height before and after each rewrite. Its
`ProcessProposal` for `h` runs while it stands at `h - 1`, so the bracket is
exact rather than timed. **An unreadable offset is an unreadable clock**, never
real time, so a misconfigured run cannot pass as a skewed one. That same
property let the headless process test reach the startup refusal and the
runtime stop ADR 0085 recorded as unreachable. Two shim mutants were each
caught, one falling back to real time and one ignoring the offset.

**The sanitizer interplay was found before the first push, not by the matrix.**
This container cannot reach the pinned libsodium and SQLite hosts. The two
targets were built in a scratch copy against the system libraries, the Go
binaries with the pinned toolchain through the module proxy, and both new tests
run there under a debug and a GCC sanitizer build. GCC's dynamic ASan runtime
refuses to start behind any preloaded library. The harness sets
`verify_asan_link_order=0`, which is safe because the shim defines no function
that check protects. Clang's static runtime intercepts `clock_gettime` itself and
chains to the shim. The guard that every target take the project's flags then
failed on the first draft, which had kept the shim out of
`PROTOCOL_STACK_TARGETS`. Moving it in gave its parser UBSan coverage, and an
instrumented shim loads cleanly into an instrumented application under both
compilers.

**The run found what the contract predicted, and one thing it did not say.** In
the first local run, replica 3 voted against every proposal from height 1 to 9,
by the right name on each side, and against none from 10 to 14. The other three
voted against nothing, and all four held the model's root throughout. **It also
voted against its own blocks** at heights 1, 5, and 9, because the pinned engine
asks a proposer to process its own proposal. All three were committed by the
other three, because a block's stamp is the engine's median of vote times and
not the proposer's clock.

**The deletion that follows is set with the trap M3.13t found.** Surveying
`src/v8/` for the handoff showed `economy_v8_fuzz` has no version-nine
counterpart. It also showed that ADR 0082's "`wire_v1` goes when `src/v8/` does"
is wrong, because version one still serves `wire_v1`. The handoff records both.

### How M3.20i was delivered

**A four-validator version-nine network runs.** Issue #345 and PR #346 delivered
`tests/integration/cometbft_four_validator_v9_test.py` in `tools/verify.sh`, a
durable-stamp audit in `cometbft_devnet.audit_durable_heads` over the new
`cometbft_process.application_head_v9`, the fixture's refused and predicted
empty blocks with a ninth check, and
[ADR 0090](../decisions/0090-the-version-nine-devnet.md).
`tools/verification_scope.py` classifies it `full`. The record commit was pushed
while the code candidate `e306ba0`'s run was still in progress, which cancelled
it. The final head carries the same code. Run 35946403883 on the final head
`9bee8e7` then passed all six jobs. Each preset printed "CometBFT four-validator
version-nine integration: passed", in about 44 seconds under each sanitizer
preset. ctest stayed at 178 and 188, because the slice adds no entry. Merged by
rebase as `009be9c` and `89f5a6b` on 2026-09-24. Two commits, ten files,
**1,040 insertions and 81 deletions**. **No accepted vector file, specification rule, manifest, encoding, kernel source,
or Go source changed.** One accepted document gained correction notes.

**It is version eight's scenario on purpose.** The same transactions go through
the same nodes, and the same refusals, restarts, driven replica, and departure
follow. So anything that differs between the two runs is the version's doing.
What version nine changes is how the model keeps up. Every block moves the root,
so the network closes one roughly every three seconds. The model follows it one
height at a time, reading each committed header for its stamp and its
transaction count, so an empty height cannot hide a transaction. Before spending
a hosted cycle, that following logic was driven offline against a fake header
source through five transactions, two refusals, and interleaved empty heights.
It caught both faults it was handed: a transaction at a height it expected
empty, and a block 1 one millisecond away from its genesis stamp.

**The durable stamp is compared where the durable head is.** The contract asks
for the stamp among the values all four replicas report identically, and ABCI's
Info carries none. The Go health command could only have reported the header
time converted a second time, and replicas that agree on a block agree on its
header by construction. So the independent C++ audit reads each store's height,
stamp, and root over version two's Info, and requires all three. The live check
keeps comparing roots, which commit to the stamp. `audit_durable_heads` refuses
to audit a version-nine network without a stamp, so a caller cannot skip it by
omission.

**The driven replica is asked the one thing only version nine can be asked**: a
decided block at the right height whose stamp is one millisecond before its
head's. It must answer status `8` and latch terminal, and a fresh process must
find its store untouched.

**Two items of the contract's devnet evidence are not in the run, and each is
recorded rather than waived.** The kind-22 mint stands behind the height wall
(ADR 0071) and the clock wall (M3.20g), so its evidence stays with the 125
execution vectors the C++ kernel reproduces. The contract's list carries a
correction note, as ADR 0071 gave version eight's. The skewed replica needs ADR
0085's owed way to offset one application's clock, which is more than a port, so
it is the next slice.

### How M3.20h was delivered

**A version-nine chain runs under CometBFT.** Issue #342 and PR #343 delivered
`tests/integration/version_nine_chain.py` and its own contract as the ctest
entry `version-nine-chain-fixture`. They also delivered
`tests/integration/cometbft_version_nine_test.py` in `tools/verify.sh`, the
version-nine identity, stamp, and `Info` in the integration helpers, and
[ADR 0089](../decisions/0089-a-version-nine-chain-resumes-only-inside-the-tolerance.md).
`tools/verification_scope.py` classifies it `full`. On the code candidate
`56f16d2`, run 35943159888 passed gcc-debug, clang-debug, and clang-sanitizers
before the record commit was pushed. Each printed "CometBFT version-nine
integration: passed" at durable height 6, about eighteen seconds after the
version-eight run. ctest reached **178** in the debug presets and **188** under
`clang-sanitizers`, one more than M3.20g because the slice adds exactly one
entry, `version-nine-chain-fixture`. The record commit's push cancelled that
run's last job, gcc-sanitizers. Run 35944130993 on the final head `6cb74b7`
then passed all six jobs, gcc-sanitizers included, and each preset printed the
same version-nine line. Merged by rebase as `9833369` and `10ee8bd` on
2026-09-24. Two commits, thirteen files, **1,649 insertions and 66 deletions**.
**No accepted vector
file, specification rule, manifest, encoding, kernel source, or Go source
changed.** Three accepted documents gained correction notes.

**The empty block was the one assumption only a node could confirm.** It rests
on reading `needProofBlock`, and the run waited for the engine to close height 3
on its own. It did in every preset, well inside the 15-second wait.

**Nothing about a version-nine block is known before it commits.** Version
eight's fixture froze five blocks before any node ran. Version nine cannot,
because its root commits to the head's stamp and the engine chooses the stamp.
So the fixture is a live ledger that is handed each stamp. The run commits
first, reads the header's time, and converts it by the contract's rule, restated
in Python. Only then does it ask the model. The model and the node agree only if
both derived the same millisecond, so every comparison checks the bridge's
conversion without a line of code aimed at it. The genesis is stamped with the
harness's clock when the run starts, a few seconds **behind** the node's start
rather than ahead of it, as the handoff had suggested. A future genesis makes
`Node.OnStart` sleep before its RPC server exists, and C5 already allows 60
seconds behind.

**The empty block is the sharpest check the run makes, and the engine supplies
it.** CometBFT proposes without waiting for a transaction whenever the last
block changed the app hash (`needProofBlock`). A version-nine block always
changes it, so the engine closes a block three seconds after every block,
whether or not anyone sent anything. Its root depends on its height, its stamp,
and the state before it, so a mismatch there has one cause. The fixture's own
probes confirm the checks bite. Rounding up instead of truncating, reading the
header's fraction from the wrong end, and an empty block ignoring its stamp were
each caught by the check written for them.

**The finding came from asking what the restart costs.** The first block after a
restart carries the median of the previous height's precommit times. A restarted
node rebuilds those from its stored commit (`reconstructLastCommit`), no
validator re-signs a committed height, and every validator runs
`ProcessProposal`. So that block's stamp is always from before the stop. Under
C5, once a quorum has been down for longer than 60 seconds, every correct machine
refuses that block in every round, and the chain never produces another.
**ADR 0088's height-one halt is one instance of this.** At height one the
"outage" is the time before the network first starts. The run restarts in
seconds and is unaffected. A devnet that stops every replica must restart inside
the window, and one that stops a single replica is unaffected, because block
sync never calls `ProcessProposal`. A production network cannot promise to be
down for less than a minute. ADR 0089 records the source evidence and three
candidate fixes, and takes none of them. Every candidate is a new contract
version, and no current slice depends on the choice.

### How M3.20g was delivered

**A CometBFT home can be initialised for version nine.** Issue #339 and PR #340
delivered `ProtocolV9` and the `"protocol-stack-v9"` app state, a genesis stamp
on `nodeconfig.Identity`, `genesis_time` in both genesis writers, the exact
per-version identity parse, `-genesis-timestamp` on the initializer, version 9
on both commands, and
[ADR 0088](../decisions/0088-the-launcher-derives-the-genesis-time-and-the-first-block-carries-it.md).
Merged by rebase as `389739a` and `2a85baa` on 2026-09-22. Two commits,
seventeen files, **1,017 insertions and 108 deletions**.
`tools/verification_scope.py` classifies it `full`, and no ctest entry is added.
Run 35752400239 on the final head passed all six jobs, with `internal/nodeconfig`
and `internal/devnet` passing and ctest at **177** in the three debug and
gcc-sanitizer presets and **187** under `clang-sanitizers`. The code candidate's
run was cancelled by the concurrency group when the record commit was pushed,
and the final head carries the same Go source. **No accepted vector file,
specification rule, manifest, encoding, or kernel source changed**; three
accepted documents gained correction notes, and versions one and eight write
exactly the octets they did.

**Absence is not a number.** `calendar-v1`'s range starts at zero, so a stamp of
zero is a real chain's, and the identity's `GenesisTimestamp` is a value whose
zero means "none" rather than a `uint64` with a sentinel. `genesisTime` is the
one place a version and a stamp become a genesis time, and it refuses the pairing
both ways. Both `Ensure` functions ask it **before writing anything**, because
the devnet's `preflight` treats keys without a genesis as an incomplete home and
refuses it on every later start, so a late refusal would have needed someone to
delete the home by hand.

**The identity parse is exact per version rather than "read the stamp when it
is printed"**, which is how the handoff put it. The looser rule would let a
version-nine binary started as version eight write a version-eight home, which
the application would then refuse at InitChain with a vaguer error. Exact key
sets refuse both mismatches before a home exists.

**The finding is worth more than the code.** Writing `genesis_time` meant asking
what the engine does with it, and CometBFT `v0.39.4` answers precisely:
`state.MakeBlock` stamps the initial block with the genesis time,
`state.validateBlock` refuses any other value, and `Node.OnStart` sleeps until a
future genesis time. So `t(1) = g` always, and C5 at height one becomes
`|g − own_clock| <= 60,000` ms. **A network that has not decided its first block
within a minute of its genesis stamp never will**, since every round re-proposes
a block stamped `g` and every correct machine refuses it as decision `5`.
`economy-transition-v9` said a genesis far in the past "starts normally", and
`calendar-v1`'s BFT-time argument for C5 silently assumed a median at every
height. Both were reasoned from the contract without reading the engine. The
rule is unchanged and the documents carry correction notes. The exemption that
would change it — a first-block stamp equal to the agreed genesis value is not a
proposer's reading — is named in ADR 0088 and not taken, because the current
rule keeps every committed stamp near civil time and a missed launch window
costs only a new genesis before any block exists.

**It changes the next two slices, not this one.** A recorded vector genesis can
never start a real network, so the single-node chain and the devnet both mint
their genesis at run time. Following the same thread showed that the devnet's
kind-22 evidence needs the chain's clock to cross a calendar month, and that
the engine's clock is a statically linked Go binary's, which no `LD_PRELOAD`
shim reaches. **At closeout a second wall turned up in front of the same
evidence**, and it was already on record: ADR 0071 found that a seat is in scope
only from height 28,800, and version nine keeps `CYCLE_BLOCKS` at 28,800, so no
seat can be a monthly candidate on a devnet begun at genesis whatever its clock
does. `consensus-application-v2`'s evidence list was written without either
wall. The handoff records both.

### How M3.20f was delivered

**The bridge drives version nine.** Issue #336 and PR #337 delivered the
engine's time on the bridge's local-application interface, `bridge.LocalV9`
and `bridge.NewV9`, the timestamp conversion, the logged decision,
`--protocol-version 9`, and
[ADR 0087](../decisions/0087-the-bridge-carries-the-engines-time.md).
Merged by rebase as `d17e7fb` and `e771929` on 2026-09-21. Two commits, twelve
files, **829 insertions and 64 deletions**. `tools/verification_scope.py`
classifies it `full`, and no ctest entry is added. Run 35619188290 on the final
head passed all six jobs, with `internal/bridge` passing and ctest at **177** in
the three debug and gcc-sanitizer presets and **187** under `clang-sanitizers`.
**No accepted vector file, specification, manifest, encoding, or kernel source
changed.**

**The time is on every version's interface and only version nine reads it.**
That kept one bridge for every ledger version. The conversion runs in `LocalV9`
rather than in the bridge, so versions one and eight gain no refusal, reachable
or not. The rule itself is one pure function, because Go's ABCI types deliver a
`time.Time` that cannot hold an out-of-range nanosecond: the contract's refusal
for one is tested where it can be reached.

**A vote now has a reason.** `consensus-application-v2` expects an operator to
diagnose a skewed clock from decisions `4` and `5` in "the application log", and
the C++ application writes none. The bridge is the first process that holds both
the decision and a logger, so `Vote` carries the decision's name and the bridge
logs a rejection with it at info level.

**It is the first slice whose main package could not be built locally.** The
bridge imports CometBFT, and resolving that dependency graph is what the owner's
resource rules keep on hosted runners. `gofmt` and a careful read are all it had
before the matrix. The read found one real defect: a data race in the proposal
test, where the stand-in server read a value the test goroutine rewrote between
calls with only a socket between them. **The code candidate `fb8aa13` then
built and passed on its first hosted run**, 35617556732, in all six jobs:
`internal/bridge` and `internal/localapp` passed under the pinned toolchain with
`go vet` clean, and ctest stayed at 177 and 187.

### How M3.20e was delivered

**The Go adapter can talk to version nine.** Issue #333 and PR #334 delivered
`localapp.ClientV9`, the version-nine response decoders, their decoder and pipe
tests, a fuzz target, and
[ADR 0086](../decisions/0086-the-go-local-client-speaks-the-version-two-frame.md).
Merged by rebase as `1a3b719` and `22529a9` on 2026-09-21. Two commits, nine
files, **1,151 insertions and 50 deletions**. `tools/verification_scope.py`
classifies it `full`. The hosted matrix runs `go test ./...` and `go vet ./...`
under the pinned toolchain in every preset job, so no ctest entry is added.
Run 35615255336 on the final head passed all six jobs, with `internal/localapp`
passing and ctest at **177** in the three debug and gcc-sanitizer presets and
**187** under `clang-sanitizers`. **No accepted vector file, specification,
manifest, encoding, or kernel source changed**, and versions one and eight write
and require exactly the octets they did.

**The frame version became a field of the client rather than a constant.**
That is the whole of the change to the shared code. `Dial` and `newClient` set
version one's; `newClientV9` sets version two's before the first call. It is
the Go form of the Python driver's class attribute from M3.20d, and it means the
adapter can hold a version-eight client and a version-nine client in one process
while the devnet migrates.

**The client does not believe a status the contract says cannot be sent.**
`maximumStatus(version, kind)` admits `7` and `8` only on a finalize over
version two. Either one anywhere else ends the connection as a protocol failure,
because the C++ encoder cannot write them on any other kind (ADR 0084) and a
peer that does is not the application this client was dialled at.

**This slice could be probed locally, and the probing found a real gap.** The
package is standard-library-only, so it was copied into a scratch module and
built with the local Go 1.23 toolchain, without the module's pinned toolchain
or its dependency graph. Reading the pipe tests with probes in mind showed they
computed the expected request **with the encoder under test**, so a swapped
height and stamp would have passed. They now hand-write the octets, and ten
mutation probes were all caught. The first probe run hung and had to be stopped
by process ID, because a refused request left the client blocked on a pipe
until `go test`'s ten-minute timeout. The test server now closes its end on a
mismatch, and such a probe fails in under a second.

### How M3.20d was delivered

**A version-nine node runs against a real clock.** Issue #330 and PR #331
delivered `src/application/main_v9.cpp` and the `protocol-application-v9`
binary, a version-two mode of the Python application driver, a headless process
test, one CTest entry, and
[ADR 0085](../decisions/0085-the-version-nine-node-process-binds-the-platform-clock.md).
Merged by rebase as `720a843`, `ab54ddd`, and `0d0b288` on 2026-09-21. Three
commits, eight files, **1,038 insertions and 64 deletions**.
`tools/verification_scope.py` classifies it `full`. Run 35610013449 on the final
head passed all six jobs, with **177** ctest entries in the three debug and
gcc-sanitizer presets and **187** under `clang-sanitizers`, one more than M3.20c
in each because the slice adds exactly one entry and no fuzz target. **No
accepted vector file, specification, manifest, encoding, or kernel source
changed.**

**The first candidate failed, and again the fault was the suite's.** Run
35608609748 on `f24b94e` failed `version-nine-headless-process` in both debug
presets, and nothing else, of 177. The test read the vector file as ASCII, and
version nine's vector file carries em-dashes in its section comments;
version eight's does not, which is why the loader it was copied from had never
met one. The binary had built and every other entry passed. **The loader was
the one part of the suite that needed no binary and it had not been run
locally**, so the repair was followed by running the whole suite against a
throwaway stand-in server in the session scratchpad. That checks the test's
own plumbing, not the C++, and it passed before the repair was pushed.

**It is the first binary in this repository that reads a clock**, and the three
questions a real clock raises were answered once each. The clock is
`CLOCK_REALTIME` in milliseconds, truncated as the contract truncates a block
stamp, because `calendar-v1` names the POSIX convention; `CLOCK_TAI` would sit
37 seconds off every peer. It is read before anything is opened, so a machine
without one never gets far enough to be asked for a vote. And a clock that stops
being readable throws out of `ProcessProposal`, which has written and staged
nothing by then, and stops the process. **Every substitute value was rejected
for a named reason**: `0` would log a clock fault as `AHEAD_OF_TOLERANCE`, a
peer's fault; the maximum the same as `BEHIND`; and the last good reading is
exactly the assumed value the contract forbids.

**The recorded chain placed the real clock without a fake one.** Its stamps are
January 2026, so a proposal carrying the first recorded stamp is behind the
tolerance and one carrying 2100 is ahead of it, and the two decisions bound this
process's clock between them. A zero, frozen, or missing clock cannot produce
that pair. `FinalizeBlock` then accepts January, which is ADR 0083's central test
observed through a process. So the binary needed no clock-injection option, and
the choice of how to skew one replica is left to the devnet slice that first
needs it.

**The same chain could not be replayed, and why is worth knowing.** It is signed
under a stand-in verifier table and this binary verifies with Ed25519, so the
recorded transactions would be refused as results. The test therefore finalizes
an **empty** block and checks what needs no recorded root: two databases agree
on it, the stamp survives a restart, and **one millisecond of stamp moves its
root** — the stamp entering the state root, observed from outside the process.

**The Python driver gained a wire version rather than a copy.**
`application_driver.Connection` names its frame version in a class attribute
and shares its finalize parser. `application_driver_v2.Connection` overrides
the attribute and the five operations whose payloads changed. It treats a status
`7` or `8` on any kind but a finalize as a malformed response rather than an
answer, because the contract makes them unreachable anywhere else.

### How M3.20c was delivered

**A version-nine application answers on a socket.** Issue #327 and PR #328
delivered `response_v9` and `dispatcher_v9` with their headers, a version-nine
`serve_connection` overload, a transport suite over three translation units and
a support header, one CTest entry, and
[ADR 0084](../decisions/0084-the-version-nine-transport.md), merged by rebase
as `07b55dc`, `a51f94d`, and `3841ec5` on 2026-09-21. Three commits, fourteen
files, **1,949 insertions and 88 deletions**. `tools/verification_scope.py`
classifies it `full`. Run 35606241208 on the final head passed all six jobs,
with **176** ctest entries in the three debug and gcc-sanitizer presets and
**186** under `clang-sanitizers`, one more than M3.20b in each because the slice
adds exactly one entry and no fuzz target. **No accepted vector file,
specification, manifest, encoding, or kernel source changed**, and versions one
and eight read exactly the decoders they read before.

**The first candidate failed, and the fault was the suite's.** Run 35604687902
on `09c0c89` failed `version-nine-transport` in all four presets and **no other
ctest entry**, of 176 in the debug and gcc-sanitizer presets and 186 under
`clang-sanitizers`. The debug presets reported `expected decision 0, got 107`
and `got 228`; both sanitizer presets named it exactly, a heap-use-after-free in
`Reader::number`. The suite's `Reader` held a `std::span`, and the cases
construct one straight from a returned response —
`Reader reader(require_ok(...).body)` — so the view dangled the moment the
declaration ended. `-fsyntax-only` cannot see a lifetime. The repair makes the reader own a
copy, which closes every such call site at once rather than the one the run
happened to reach first.

**Statuses `7` and `8` are written through a signature.**
`encode_timestamp_failure_v9` takes no `MessageKind`, so it writes a finalize
response or nothing. That is the contract's rule that the two statuses belong to
kind 6 alone, stated as a function's shape. It is the move ADR 0083 made for the
clock. The version-one error path refuses the same two values cast into an
`ApplicationError`, because otherwise the kind-free function would be a
convention that the other path could bypass.

**The socket had to learn which wire it reads, and its header said the
opposite.** `unix_server_v1.hpp` said the `V1` was the frame version and that "a
new ledger version adds an overload here and not a wire". That held through
version eight and is false of version nine. `serve_with` now takes a wire policy
beside its dispatcher, each overload names its wire, and the header says the
`V1` is the socket's. A server that picked its decoder from each frame's version
octet was rejected, because it would let a version-one bridge talk to a
version-nine application, which is the pairing the frame version exists to stop.

**The finding is that `RESOURCE_BOUND` cannot arrive over the wire.** The
transport suite set out to produce decisions `1` through `6` from frames, and
`6` cannot be produced. `wire_v2`'s request decoder enforces the same three
bounds as the application's `within_block_bounds` and refuses the frame as
`resource_limit` before it is dispatched. The Go bridge's `validateBlock` votes
REJECT before it builds a frame at all. With M3.20b's finding about `7`, both
whole-block decisions are defence in depth. The suite measures the absence: it
builds the over-count and over-length frames, requires the decoder to refuse
them, and requires the clock to be untouched. It proves both bytes at the
encoder.

**The clock is counted over the wire, not only in-process.** M3.20b's counter
measured the application. This suite measures the dispatcher with it. A
dispatcher that asked for a vote before finalizing, or checked a proposal on the
way to Info, would move the count. Each decided proposal frame reads it once. A
proposal while a block is staged answers status `3` without reading it. Every
other frame reads it zero times.

**Every refusal has an accepted control beside it.** The receipt cases take one
real version-nine receipt and require it to be written beside its own code
before requiring each mutation of it to be refused. A suite of refusals alone
would pass against an encoder that refused everything.

**What could not be done locally, and why that is recorded rather than
hidden.** The dependencies are built from source by CMake. Building libsodium,
SQLite, and the kernel is what the owner's resource rules reserve for hosted
runners. The new sources and all three test units were checked with
`-fsyntax-only` under GCC 12 and Clang with the project's warnings, against stub
dependency headers in the session scratchpad. No mutation probes were run,
because they need a built suite. Every runtime claim is the hosted matrix's.

### How M3.20b was delivered

**Something drives a version-nine chain.** Issue #324 and PR #325 delivered
`include/protocol/application/application_v9.hpp`, an internal header, two
translation units, a 693-line suite, one CTest entry, and
[ADR 0083](../decisions/0083-the-version-nine-application-reads-one-clock.md),
merged by rebase as `cc3fd8d` and `45e1fd4` on 2026-09-19. Two commits, nine
files, **1,820 insertions and 21 deletions**.
`tools/verification_scope.py` classifies it `full`. Candidate run 35459907355
passed all six jobs, with **175** ctest entries in the three debug and
gcc-sanitizer presets and **185** under `clang-sanitizers`, one more than M3.20a
in each because the slice adds exactly one entry and no fuzz target. **No
accepted vector file, specification, manifest, encoding, or kernel source
changed**, version eight's application is untouched, and `CMakeLists.txt` only
gains registrations.

**The clock is the whole of what version nine adds here, and it is the first
non-deterministic input this repository has admitted into a consensus-adjacent
path.** It is bound at construction with **no default**, because a defaulted
system clock would make "this deployment cannot read a clock" unrepresentable and
an assumed clock makes C5 pass on every proposal, silently. `process_proposal`
reads it once; reading twice would let two conditions of one evaluation disagree
about the time.

**`finalize_block` cannot apply C5 and the enforcement is a signature.** It calls
`replay_timestamp`, which takes no clock argument, so there is no value a caller
could pass and no branch a maintainer could add without changing a signature. The
kernel had already made the separation structural by offering two entry points
differing in exactly this respect; this layer's contribution is to call the right
one and to **prove by counting** that it reaches no other. The bound clock
increments a counter, and every operation but `process_proposal` must leave the
count where it found it — which is a measurement rather than an assertion, and it
is what the contract's "exposes no path" requirement actually asks for.

**`init_chain` compares four values and stores none of them.** The genesis stamp
is read from the durable head rather than kept as a member, because `init_chain`
is only reachable while the durable height is zero and **at height zero the
head's stamp is the genesis stamp**. ADR 0080 reached the same answer for the
snapshot; here the reason is sharper, because the one operation that needs the
value is the one operation that can only run where the value is still in the
head.

**The first finding is that the contract asks for one piece of evidence that
cannot be produced.**
[`consensus-application-v2`](../specifications/consensus-application-v2.md)
requires a vector for every `ProcessProposal` decision `0` through `7`, each on
its own. Seven are straightforward. **Decision `7`, `NOT_EXECUTABLE`, is not
reachable from a proposal's contents**, and establishing that took a probe rather
than a reading. The kernel turns every transaction-level problem into a
**result**: `debit_of` returning `nullopt` becomes `Result::debit_overflow`, and
`envelope_checks` refuses `insufficient_balance` *before* `charged` runs, so
`collect_fee` cannot fail afterwards. The remaining whole-block rejections are
chain-state failures — a prologue, issue, expiry, or conservation failure — that
no peer can induce by choosing bytes, and the two bounds that could disagree, the
application's `kMaximumBlockInputsV9` and the kernel's `kMaxRawInputs`, are the
same constant by construction.

Four candidate transactions were built and offered to `execute_block` directly: a
transfer at the `u64` maximum, a node mint with nothing to collect, a node mint
naming a seat that does not exist, and a monthly pool mint with no claim. **All
four were accepted as blocks and refused as results.** The suite therefore
records the absence as a measurement rather than skipping it — a block of
transactions the kernel refuses for several different reasons is offered and
required to be `ACCEPTED`. Decision `7` stays implemented, because the
chain-state failures it guards are real; what is now written down is that it is
defence in depth rather than a vote a peer can provoke.

**The second finding is that the probe which passed was the useful one.** Seven
mutation probes were run against the finished suite and six failed it
immediately. **The seventh — moving the resource-bound check in front of
`calendar-v1`'s ordered conditions — passed.** That ordering's entire
justification in the contract is that the vote is identical either way, so the
order decides only what is *reported* and therefore what is testable — and
nothing reported was being compared. Four cases were added, each violating a
bound and a timestamp rule at once and each required to report the timestamp
rule, and the probe then failed as it should. **A rule whose whole justification
is "this is what makes it testable" is a rule whose test is worth checking for
existence**, and the reading that produced the implementation did not produce the
test.

**One behaviour reads as a bug and is not.** A chain whose first block was
finalized but never committed comes back at height zero, so the next process must
call `init_chain` again. That is correct — `init_chain` happens once per chain,
and a chain whose first block never committed has not had one — and a CometBFT
node in exactly that state does call it again. It is recorded because the suite's
first draft assumed otherwise and failed on it.

**All seven probes are now caught**: applying C5 in `finalize_block`,
regenerating the stamp at commit, reordering the bounds, dropping the
genesis-stamp comparison, dropping Info's timestamp, reading the clock twice, and
reporting C2's status for a C1 failure.

### How M3.20a was delivered

**The local protocol finally uses the field that announces a shape change.**
Issue #322 and PR #323 delivered `include/protocol/application/wire_v2.hpp`,
`src/application/wire_v2.cpp`, a codec suite, a fuzz target, two CTest entries,
and [ADR 0082](../decisions/0082-the-version-two-application-frame.md).
`tools/verification_scope.py` classifies it `full`. Candidate run 35456872018
passed all six jobs, with **174** ctest entries in the three debug and
gcc-sanitizer presets and **184** under `clang-sanitizers` — one and two more than
M3.19c's 173 and 182, because the slice adds `application-wire-v2` everywhere and
`application-wire-v2-fuzz-smoke` only where fuzzing is enabled. **No accepted
vector file, specification, manifest, encoding, or kernel source changed**,
`wire_v1` is untouched, and `CMakeLists.txt` only gains registrations.

**The reason this is a slice at all is one octet that had never moved.** Version
seven added a block identifier to the finalized-block response, version eight
kept it, and the protocol version stayed at `1` through both with no contract
document recording the change. The consequence is not a misparse — both decoders
are correct — but the refusal lands in the wrong place: a version-one reader
paired with a version-eight writer refuses the response **at the result count, as
a generic protocol failure, on the first block**, rather than at the header, as an
unsupported version, on the first frame. M3.19a found it while writing the
contract; this is where it stops being true.

**What version two changes is two request payloads, and a third that must not
change is checked precisely because it must not.** Kind 2 gains
`genesis_timestamp` **before** `app_state`, because every fixed-width field
precedes the one variable-length field — version one's own layout rule, and what
lets a decoder bound a frame before it allocates. Kinds 5 and 6 gain a timestamp
after the height. **Kind 4 gains nothing**: PrepareProposal names no block, and
`economy-transition-v9` requires the proposer's algorithm for choosing a value to
stay unconstrained, so a port that stamped every block-shaped payload would have
stamped the one payload that must not carry one. The absence is a case rather
than an omission.

**Version two is a module of its own rather than a version parameter on version
one, and the reason is the migration rather than taste.** Parameterising
`wire_v1` by accepted version would mean editing a decoder that version one and
version eight both depend on — the change that makes version two reachable is the
same change that could make version one accept a frame it did not accept before.
What *is* shared is everything that is genuinely one fact: the header size, the
magic, the direction and kind enumerations, the wire-error set, the frame and
header structs, and the three unchanged request payloads, all declared once in
`wire_v1.hpp`. What is copied is the primitive reader and the payload decoder,
because that is what version two edits, and the duplication is bounded by the
deletion already owed — `wire_v1` goes when `src/v8/` does.

**The finding is that the cross-version refusal had to be tested in both
directions, and only one of them is the direction this slice created.** That
version two refuses a version-one frame is the new behavior and the obvious case.
That version one refuses a version-two frame is what makes the change *useful* —
it is the deployment failure the field exists to name — and it needed no code at
all, because version one already compares against its own constant. **A suite
that tested only the new direction would have proved version two is strict and
proved nothing about whether the drift is closed.** The pair is checked,
including a version-one finalize frame carrying a whole well-formed version-one
block body, which is refused on its sixth octet rather than at the result count
several fields later. That case states the whole point of the version: the body
never reaches a payload decoder.

**One figure is derived rather than restated, and it is the M3.13r lesson applied
before the fact.** `kMaximumBlockInputsV2` is `v9::kMaxRawInputs`, with a static
assertion that it still equals version one's `kMaximumBlockInputs`. The two are
the same number today. Deriving it means a version that moved the kernel's bound
stops this file compiling rather than leaving a transport that admits a block the
kernel will refuse. M3.13r's rule was that a figure moving with a version is
either checked on the happy path or needs a boundary case; a figure **derived**
from its source needs neither.

**The frozen header bytes are pinned as bytes.** A test that encoded with
`kWireVersionV2` and then asserted the octet equalled `kWireVersionV2` would pass
against any value, including `1` — which is exactly the failure this whole slice
exists to prevent, so the suite spells the twenty octets out.

**Five mutation probes were run against the finished suite and all five were
caught**: keeping version one's number in the encoder, accepting either version in
the decoder, reading the InitChain stamp after the blob, dropping the block stamp,
and restating the raw-input bound as a literal.

**The fuzz target was driven before it was registered.** Its seed is a *block
request* rather than version one's empty Info frame, because that is the payload
that gained a field and therefore the one whose decoder has something to get
wrong. It was compiled under AddressSanitizer and UndefinedBehaviorSanitizer and
run over its seed and 255 structured single-octet mutations, so the
`require_valid_seed` trap is known to hold rather than assumed — a fuzz target
whose own seed does not decode traps on the first input of every smoke run.

### How M3.19c was delivered

**A version-nine chain survives the process that built it.** Issue #319 and
PR #320 delivered `include/protocol/storage/sqlite_ledger_v9.hpp`, three sources
and two internal headers under `src/storage/`, a four-file test suite, two CTest
entries, and
[ADR 0081](../decisions/0081-the-version-nine-owning-store.md), merged by rebase
as `159eb27`, `e0000d6` and `dc9818c` on 2026-09-19. Three commits, twenty-three
files, **2,892 insertions and 39 deletions** — of which the code is twenty-one
files, 2,696 insertions and 4 deletions, and the rest is this record and the
handoff.
`tools/verification_scope.py` classifies it `full`. Candidate run 35454011324 on
the store commit passed all six jobs, with **173** ctest entries in the debug presets
and **182** under `clang-sanitizers` — two more than M3.19b's 171 and 180 in each,
because the slice adds exactly two entries, `version-nine-owning-store` and
`version-nine-store-recovery`, and no fuzz target. **No accepted vector rule,
specification, manifest, encoding, or existing kernel source changed** — every
source file is new, `CMakeLists.txt` only gains registrations, `src/v8/` is
untouched, and `test-vectors/economy-transition-v9-execution.txt` grew
additively, 125 vectors becoming 162.

**The suite replays a run that had to be recorded first.** Every other recorded
version-nine chain jumps from height 2 to the activation height with
`advance_to`, and a store cannot follow that: it commits one height at a time.
Under version seven that was a design objection —
[ADR 0057](../decisions/0057-the-version-seven-owning-store.md) refused a "jump
to height" operation as test-only machinery answering to no chain rule. **Under
version nine it answers to a chain rule and contradicts it**: every height audits
every in-scope seat and every height's stamp is a value C2 compared, so a skipped
height is an audit that was owed and a comparison that never happened. So the
first commit records a four-block contiguous `restart` run — Python derives every
stamp, transaction root, header and identifier, the C++ kernel reproduces all 37
new vectors, and only then does a store replay them.

**The head keeps a timestamp column although the payload already carries the
stamp**, and the handoff had deliberately left that choice to this slice. It is
not kept for the cheap read. A file whose columns named the height and the root
would be **stating half of a head it holds whole**, and the half it omitted would
be the one version nine added. What the column buys is a comparison the root's
does not imply: the root refuses a *payload* whose stamp was changed alone, and
cannot refuse a **column** that disagrees with an unchanged payload — which is
exactly what a later reader, or a later version of this store, would be tempted
to trust without decoding anything. The restore still reads the payload; the
column is a claim the file makes about itself, checked and then discarded.

**The column could not be called `current_timestamp`, and the reason is a
clock.** `CURRENT_TIMESTAMP` is an SQL keyword, and SQLite resolves a bare
`current_timestamp` in an expression to its own wall-clock reading rather than to
a column of that name. The `CREATE TABLE` succeeds, the name is legal, and only
an expression over it misbehaves: `typeof` returns `'text'` and `length` returns
19, so the column's own CHECK refused **every** insert, on the first genesis this
store ever wrote. A `SELECT` of the head would have returned the time of day.
**The CHECK is what caught it** — a schema without one would have stored the
column and read back the clock, in the single component of this repository whose
whole job is to hold the chain's stamp rather than the machine's. The column is
`current_timestamp_millis`; the block row's is plain `timestamp`, because no
keyword shadows it, and renaming both to match would have hidden the reason.

**Three DDL literals move with the version and each is pinned at the octet.**
Genesis **150**, head snapshot **230**, block header **154** — and the header is
the first of the three ever to move at all, unchanged from version one through
version eight. One octet below each is refused by SQLite's own CHECK and exactly
the width is admitted, because a tamper case proves only that *some* blob the
column admits is refused by the decoder and would still pass against a stale
literal. **The header literal has the worst failure shape of the three**: a store
that creates a genesis and then refuses every block.

**The restart evidence aims at the stamp rather than only at the root.** A root
comparison proves agreement without ever showing which stamp came back, and a
store that reopened with a stamp belonging to an earlier height would still admit
every later block, because C2 only refuses a stamp that goes *backwards* and a
stale one is smaller than anything that follows — a wrong root rather than a
refusal. So between the run's two equal-stamped heights the reopened store is
offered height 3 one millisecond below block 2's stamp, which it must refuse, and
then at exactly that stamp, which it must admit. **A store that restored a
smaller stamp admits both; one that restored a larger stamp admits neither.**

**Four mutation probes were run against the finished suite and all four were
caught**, which is what distinguishes a check that is load-bearing from one that
is decorative. Dropping the restored-stamp comparison, rewinding the header
column to version one's 146, advancing the head's height while leaving its stamp
column behind, and writing the predecessor's stamp into the block row each turned
a green suite red. The third is the defect this version could actually hide, and
it is refused by the shape of the write as well: `persist_block_v9` advances the
height, the stamp, the root and the payload in **one** `UPDATE`, so the defect
would need two statements to exist.

**The store applies C1 and C2 and never C5.** A store executes blocks the network
already decided — a commit, a replay, a recovery — and one that re-applied the
proposal tolerance would refuse the chain's own past one tolerance-width after
producing it. `apply_block` therefore takes the agreed stamp as a parameter and
has no clock to read, which is the enforcement rather than the convention. The
same argument refuses an uptime-schedule parameter and a `BlockOrder` parameter:
the prologue derives the schedule from the seat table and the window records, and
the `BlockOrder` flags are demonstration flags rather than a configuration a
chain has, so a store that exposed them would be offering an operator a way to
leave consensus.

**`sqlite_ledger_v9_open.cpp` is a provably empty normalising diff against
version eight's**, and it is the one file of this slice where that was
predictable in advance: reopening is validation, a store is validated once and
then trusted for its lifetime, and none of that is version-specific.

**One handoff defect was repaired on the way.** `current-state.md`'s "What works
now" still said the snapshot was version eight's, which M3.19b had made untrue
two days earlier. Git and the passing `version-nine-snapshot` entry are what
settled it, and the bullet now covers the whole version-nine storage layer.

### How M3.19b was delivered

**A version-nine state can leave memory.** Issue #316 and PR #317 delivered
`include/protocol/storage/snapshot_v9.hpp`, three sources under `src/storage/`,
a five-file test suite, a fuzz target, and
[ADR 0080](../decisions/0080-the-version-nine-snapshot.md), merged by rebase as
`ad7d717` and `d658251` on 2026-09-17. Candidate run 35233176131 passed the
complete hosted matrix with **171** ctest entries in the debug presets and
**180** under `clang-sanitizers` — one and two more than M3.18b, because the
slice adds `version-nine-snapshot` to every preset and
`storage-snapshot-v9-fuzz-smoke` only where fuzzing is enabled.

**The payload carries the head's timestamp beside its height**, which makes the
prefix 166 octets rather than version eight's 158. That field is the one version
nine could lose in silence: a restore that dropped it hands back a ledger whose
next block commits a root naming a height the stamp does not belong to, and
**every later block still satisfies C2** because the stale stamp is smaller. The
failure is a wrong root rather than a refusal.

**So the round trip makes two claims rather than one.** The restored stamp
equals the original, and a payload that keeps every other field and zeroes only
the stamp reaches a **different** root. Without the second, the first could hold
while the field was decorative — the root would be carrying the stamp without
committing to it, and no test would say so.

**Version nine adds no snapshot parameter, and the asymmetry is the interesting
part.** Its one new genesis field is the genesis timestamp and a restored ledger
does not need it: C2's genesis case applies only at height one, the ledger keeps
no separate copy, and `chain_id` — which *is* compared — is a digest over the
genesis bytes. The dispute authority key needed a parameter for exactly the
opposite reasons: the ledger retains it, transitions read it, and no root commits
to it. Stating the two together is what makes the difference a rule rather than
an inconsistency.

**The four new kinds are decoded into fields where version eight's two are stored
raw, and it is the same rule producing the opposite answer.** Version eight holds
its uptime entries raw because its two transitions read that key space directly,
so holding it raw makes them *the* implementation. ADR 0078 already established
that nothing in version nine reads that space — the settlement is arithmetic over
decoded figures — so a raw map here would be the second encoding instead. Which
side reads the key space is the whole of the difference.

**One key rule had no value decoder to delegate to.** The monthly figure's month
lives in the *key*, and `decode_monthly_figure_value` knows only about seconds.
The entry decoder therefore rebuilds the key with `monthly_figure_key` and
requires equality. Gate 3 would refuse an out-of-range month too, one layer
later — every figure must equal the cursor's month and the cursor is bounded by
its own decoder — but it would refuse it as an unconserved state rather than as a
bad entry. **A parse error names its subject; a failed invariant names a
payload.**

**Writing the negative case found something better than the case.** The obvious
test for the kernel's first clock invariant is a resealed payload carrying an
out-of-range stamp. **It cannot be built.** `state_root` returns `nullopt` for a
stamp C1 would have refused, so there is nothing to reseal *with*, and the
restore refuses at **gate 1** because the rebuilt ledger commits no root at all.
The range rule is enforced by the root's own totality rather than by a gate that
could be removed, which is a stronger property than the one the test set out to
record. It was caught by predicting `not_conserved` and checking the prediction
against `state_root` before running anything; the test now asserts both halves,
because the refusal alone would not say which gate fired or why the other cannot.

**The first candidate failed all four presets and the fixture was wrong rather
than the decoder.** Every preset reported the same assertion — "a resealed
payload must commit a root" — and the cause was eleven `reseal()` calls the port
added that version eight's suite does not have. Resealing exists to carry a
mutation *past* the earlier gates so it reaches the one under test; every one of
those cases is refused by `read_economy`, `apply_entry` or `complete`, which all
run **before** any gate. Three could not be resealed at all: `economy_root`
returns `nullopt` for a duplicate key and for an entry whose kind or width is not
one a transition writes, which is exactly the shape a duplicate-key case, a
resized pool value and an unknown-kind entry have. Eleven calls became one — the
window-month retention case, the only case here that must reach gate 3.

**The lesson is narrower than "run the tests".** Version eight's suite already
encoded the right rule by not resealing its ordering cases, and the port added
calls rather than inheriting them. Reading the neighbour's *omissions* is harder
than reading its code, and this is the second time in two slices that the useful
signal was in what an existing artifact declined to do.

**`snapshot_v9_assignments.cpp` is a provably empty normalising diff** against
version eight's: `diff` under a mechanical `v8`→`v9` rebind produces nothing.
That is the strongest available statement that the one variable-width record and
the permission re-derivation did not move.

**Version eight's `kFixedEntryCount` did not survive the port.** It is declared in
that internal header and referenced nowhere — the completeness check is a set of
named flags — and carrying it forward would have put a figure that is wrong for
version nine, fourteen against sixteen, beside a check that does not consult it.
Version eight's copy is left alone; an unused constant is not worth a commit
against a delivered version.

**Two smaller things the port had to decide rather than inherit.**
`Rebuild::uptime_seats` becomes `referenced_seats`, because kinds 21 and 22 name
a seat for the same reason kinds 18 and 19 do and a name that said "uptime" would
have been wrong the moment the monthly figure used it. And one inherited refusal
could not be ported: the version-nine trace purchases every seat with
`has_referrer` clear, so there is no kind-4 entry to mutate, and the identity
index rule stands in its place.

### How M3.19a was delivered

**The last contract version nine owed is accepted.** Issue #313 and PR #314
delivered `docs/specifications/consensus-application-v2.md` and
[ADR 0079](../decisions/0079-the-version-nine-application-contract.md), merged by
rebase as `7f29e22` and `b7ff578` on 2026-09-17. Documentation only, so the
focused repository-metadata path: candidate run 35228541977 passed
`Classify and verify change scope` and the aggregate `Verification required`,
and the compiler/sanitizer matrix reported `skipping`, which is the classifier
doing its job rather than a gate being missed.

**The slice existed because two sentences were false.**
`consensus-application-v1` lists timestamps among the values that are "not
application transition inputs" and freezes its local frame at version 1.
`economy-transition-v9` makes both false and deliberately stopped at naming five
requirements a conforming contract must satisfy, on the grounds that a boundary
contract is a separate accepted artifact. This settled them.

**The central decision is where the clock is read, and the reason is not the one
the slice started with.** C5 is the only `calendar-v1` rule whose input is not in
the block, so exactly one component must read a clock. The obvious cheap answer
is the Go bridge: it already speaks to CometBFT, and a clock reading is
operational rather than canonical. It is wrong, and the decisive argument is not
the invariant citation. A clock reading decides a vote, and **C5 is never
re-checked on any later path**, so a bridge that supplied a wrong reading would
produce a machine that silently votes against its own rules for as long as the
bridge is wrong — with no root mismatch, no failed check, and nothing downstream
to notice. The application reads it, once per `ProcessProposal`, before any
condition is evaluated.

**A second argument arrived late and would have settled it alone.**
`calendar-v1`'s five conditions are *ordered*, and the order is normative. A
bridge-side clock puts the first three in C++ and the last two in Go, so a split
implementation could not report the first condition that fired without a round
trip, or would have to duplicate the durable head across the boundary to avoid
one. The ordering constraint is the kind of thing that looks like a detail until
it decides the architecture.

**Two reporting spaces, because the two paths have opposite correct responses.**
This is the part a single status space would have got wrong while satisfying the
requirement's letter. `ProcessProposal` returns a decision **under a status of
zero**: a peer proposing a bad timestamp is an ordinary event on a live network,
the bridge converts every nonzero status to an ABCI exception, and a contract
that reported it as a status would let **one malformed proposal from one peer
stop a correct machine**. `FinalizeBlock` returns a nonzero status and is fatal,
because it only ever runs on a block the network already decided, where a C1 or
C2 failure means this machine's rules and the network's decision disagree about
history.

**The decision space extends the kernel's condition space rather than
re-encoding it.** Values `0`–`5` are `protocol::v9::TimestampCondition` in its own
numbering; `6` and `7` are the contract's own and are numbered after the kernel's
last. The contract requires a static assertion that the kernel's condition count
is 6, so a later version adding a sixth breaks the build rather than silently
aliasing `RESOURCE_BOUND`.

**The absence of two statuses is the evidence, not the presence of eight.** There
is deliberately no status for either C5 condition, and a conforming test asserts
that absence: an implementation whose status space contains a tolerance value has
a tolerance reachable on the replay path, which is the defect the whole
separation exists to prevent. The single test that distinguishes a conforming
implementation from a broken one is in the required evidence — the same height,
the same bytes, one clock moved, accepted by `FinalizeBlock` and refused by
`ProcessProposal`.

**The conversion needed two rules and one of them is counterintuitive.** A block
timestamp truncates, because BFT time is nanosecond-precision and is not a whole
number of milliseconds, so an exactness rule would reject essentially every real
block; truncation is safe because a monotone map preserves C2 and the
at-most-0.999 ms shift is four orders of magnitude inside a 60,000 ms tolerance.
A genesis timestamp must have a **zero** nanosecond remainder, because the
launcher writes that file and exactness makes the comparison injective — a
truncating genesis conversion would accept two distinct CometBFT genesis files
for one canonical chain.

**The bridge refuses only what it cannot represent**, which is the rule that
keeps C1 testable. A timestamp above `MAX_TIMESTAMP_MILLIS` is representable, so
it reaches the application and is refused there as `TIMESTAMP_RANGE`. A bridge
that pre-filtered the range would make `calendar-v1`'s first timestamp condition
unreachable end to end, and it would exist only in a unit test.

**One thing found, and it is narrower than it first looked.** Version seven added
a block identifier to the finalized-block response, version eight kept it, the
frame version stayed at `1`, and no contract document ever recorded it. It was
found by reconciling version one's message table against `response_v8.cpp` rather
than against version one's prose. The first draft of the ADR called it a silent
misparse. **It is not**, and checking rather than asserting it is what caught
that: both decoders are correct and both say so in comments — version one's
refuses at the result count, because the block identifier displaces every field
after the root. What is actually wrong is *where* the refusal happens. It is a
generic protocol failure on the first block where it should have been an
unsupported version on the first frame, so the diagnosis available to an operator
is one layer further from the cause than it needs to be. Version nine is the
first version in the project's history to move the field that exists for exactly
this.

**Two smaller corrections the slice made rather than deferred.** The architecture
note said CometBFT "timestamp" types must not leak into the kernel, which became
misleading the moment a block carried one — it now separates the protobuf type,
which does not cross the boundary, from the `u64` millisecond value, which does.
And the determinism boundary's "wall-clock time" bullet now says outright that an
agreed block timestamp is not wall-clock time, because that is the
attested-claim rule rather than an exception to it, and a reader hitting the
bullet after version nine would reasonably have concluded otherwise.

**One verification gap was found, and sweeping it found a real defect.**
`tools/verify_metadata.py` validates that a Markdown link's *file* exists and
does not validate its **anchor fragment**, so a throwaway script swept all 41
anchored links in tracked Markdown. One was genuinely dead:
`current-state.md` linked to `#what-the-m310a-gates-enumeration-found`, a heading
the M3.15b split had moved into `delivery-log.md` six sessions earlier. It now
points at the delivery record and the slice fixed it.

**The sweep also produced a false positive, and that is the part worth carrying
forward.** It flagged `economy-transition-v6.md`'s `#kind-10--hub_register`, and
**the document was right and the checker was wrong.** GitHub's slugger replaces
*each* space with a hyphen rather than collapsing runs, so
`### Kind 10 — \`hub_register\`` slugs to `kind-10--hub_register` with two
hyphens, because removing the em-dash leaves two spaces behind. A checker that
collapses whitespace reports a false positive against every heading containing a
dash, which is most headings in this repository. Checking the heading before
editing an accepted specification is what caught it. Closing the gap properly is
a Python source change that fails closed to the full matrix, so it was left as a
candidate slice rather than folded into a documentation change.

**What it deliberately did not do.** It implemented nothing. The snapshot, the
owning store, the application layer, the transport, the node process, and the
ABCI adapter are all still version eight's, and each is a separate port. The
contract states required evidence for all of them so that each port has something
to satisfy rather than a shape to invent.

### How M3.18b was delivered

**A version-nine chain runs in C++, and it closes a month.** Issue #310 and PR
#311 delivered `include/protocol/v9/ledger.hpp` and ten more sources under
`src/v9/`, merged by rebase as `52065a1` and `7dabe5d` on 2026-09-16. Candidate
run 35159501140 passed the complete hosted matrix with **170** ctest entries in
the debug presets and **178** under `clang-sanitizers`, one more than M3.18a
because the slice adds exactly one, `economy-transition-v9-execution-cpp`.

**Eight of the ten sources are version eight's execution with three identifiers
rebound, and three have an empty normalising diff** —
`economy_execution.cpp`, `economy_uptime_transitions.cpp`, and
`economy_ledger_internal.hpp`. Together with M3.18a's four, **seven of the
kernel's nineteen carried translation units are provably unchanged by the port**,
which is the strongest available statement that nothing moved by accident. The
ninth new source, `economy_monthly.cpp`, holds what version nine adds to
execution: the settlement arithmetic, the single-pass closing rule, and the two
pool identities.

**Kind 22 is in `economy_value_transitions.cpp` beside kind 4, and the placement
is the argument.** Its body, scheme, authority, destination rule, posture
confirmation, channel and fixed fee are all kind 4's, and what differs is which
balance it empties; a reader checking that claim reads the two functions side by
side. Putting it in version nine's own translation unit would have made the claim
something to take on trust, and it would have needed kind 4's file-private
helpers exported to get there.

**Three mutation probes passed and every one named a real gap rather than a bad
probe.** The recorded chains never produce a nonzero remainder, never have a
candidate that ran nothing lose to one that did, and never reach a share that
rounds to zero — so discarding a carry, deriving the candidate set from the
figures, and writing a zero claim all changed no recorded value. **A fixture that
cannot see a rule is not evidence for it**, and the first attempt to close this
was itself wrong: derived checks against the pure `settle_month` left all three
probes passing, because the mutations were in `settlement_candidates` and
`apply_settlement`, which that function does not call. The second attempt builds
a ledger by hand and drives `close_month` against it, and all three then fail
closed — the carry probe inside `close_month`'s own conservation gate, which is
the strongest form of catch available.

**The hand-built settlement fixture is asserted to be conserved before anything
settles against it**, so a fixture that was itself impossible could not make a
settlement look correct. That is the habit M3.10d recorded and it earns its place
here: the pool identity is what catches the carry probe, and a fixture that did
not satisfy it to begin with would have caught nothing.

**Seven probes were caught at once**, and two are worth naming. Reading the
window's month from the assigning block rather than from the entry written at its
opening height changes `audit.alice_challenged` from 69 to 81 — the systematic
two-day distortion `unreferred-pool-payout-v1` rejects by name, showing up as a
different audit count rather than as a wrong month. And a quiet path that
advances the height and leaves the stamp behind changes it to 74: the beacon
moves, so who is challenged moves, which is a louder failure than the wrong root
it would also commit.

**Both orderings ADR 0078 distinguishes are executed on chains rebuilt to the
height before the settlement**, rather than on copies taken from the recorded
run: a copy would share whatever that run had already decided, and a chain built
the same way from genesis is the same chain reached independently. The payout
before the accrual reaches a different root; the accumulation before the deletion
reaches the same one, and the vector records the equality with its reason.

**The first candidate failed both GCC presets and both Clang presets accepted
it.** `-Werror=dangling-reference` is a GCC 13 warning and this machine has GCC
12, so no local check could have produced it — the mirror of the portability
defect M3.10d records Clang catching and GCC accepting. **Running one compiler
locally is not evidence about the other**, and the version-eight execution
fixture had already recorded this exact shape at every one of its call sites. The
repair returns a pointer and takes a `string_view`, which removes the question
and the temporary that raised it.

**One local practice carried over from M3.18a and paid again.** A scratch shim
forwarding `crypto_hash_sha256` to the already-installed OpenSSL let the whole
execution target compile, link and **run locally with real digests** — about
600,000 block transitions in 1.2 seconds — on a machine with neither CMake nor
libsodium. Everything except the GCC 13 warning was found and fixed before
anything was pushed.

### How M3.18a was delivered

**The first C++ in this repository that encodes a version-nine artifact.**
Issue #307 and PR #308 delivered `include/protocol/v9/economy.hpp` and twelve
sources under `src/v9/`, merged by rebase as `4c46e56` on 2026-09-16. Candidate
run 35152873997 passed the complete hosted matrix — scope classification `full`,
GCC and Clang debug, both sanitizers, and the aggregate required check — with
**169** ctest entries in the debug presets and **177** under `clang-sanitizers`,
one more than M3.17c because the slice adds exactly one, `economy-transition-v9-cpp`.

**Eleven of the twelve sources are version eight's codec with three identifiers
rebound**, and four of them have an **empty normalising diff** against their
originals — `economy_envelope.cpp`, `economy_identity.cpp`,
`economy_messages.cpp` and `economy_settlement.cpp`. That is the strongest
available statement that nothing changed by accident, and it is why the file
split matters: version nine's own addition lives in `economy_calendar.cpp`, so
the difference between two codecs is a file rather than a diff spread across
eleven. It is the shape M3.13n established for version eight and the reason a
reader can audit the port while both kernels compile.

**The other seven carried files change only where the contract does**, and the
list is short enough to state: the widened kind-12 value and its new decoder in
`economy_state.cpp`; the genesis timestamp, its offset shifts and a predecessor
range that now runs to eight in `economy_genesis.cpp`; kind 22 in three tables in
`economy_contract.cpp` and one shared decoder arm in `economy_body.cpp`; the
timestamp in the root preimage in `economy_tree.cpp`; and prose in
`economy_receipt.cpp` and `economy_internal.hpp`. **Thirteen literal mentions of
version eight survived the rebinding and every one was read rather than
rewritten**; the five that remain are correct history about version six's result
codes, version eight's two kinds, and the port itself.

**`accept_timestamp` and `replay_timestamp` differ in exactly one respect**, and
that is the structural half of `calendar-v1`'s separation rather than a
convenience: there is no argument to the second that could make a replaying,
restoring or reconstructing machine check a tolerance. The behavioural half is a
vector — the accepted chain re-run through the clock-reading path with a reading
ten tolerances stale must refuse **every** height, which is what "a machine that
re-applied C5 on replay would reject the chain's own past" means as a check
instead of a warning.

**The contract vector file did not hold the state-root non-collisions its own
specification asks for**, and the slice added them rather than working around
them. `economy-transition-v9.txt` had the seven chain-identity non-collisions and
nothing about the root; it now records the version-nine root, the eight
predecessor roots, their eight non-collisions, each predecessor's empty economy
tree root pinned against the file that accepted it, and **a pair of states
differing only in the timestamp**. That last pair is the one that matters:
without it the root could ignore the field entirely and every other vector would
still pass, because they all hold one timestamp. 213 vectors become 239.

**The far end of the compatibility range is pinned to an accepted artifact.**
`economy-transition-v8.txt` records the root of an empty state under version
eight's chain identity, and this kernel's predecessor construction must reproduce
it exactly. That is M3.13n's finding applied rather than rediscovered: an
inequality between two digests proves nothing about either one, so a construction
that wrote version nine's schema version into all eight preimages would still
satisfy every non-collision. A probe doing exactly that fails on the pin.

**A recorded boolean was named for a count it did not establish.**
`genesis.twelve_entries_are_version_eights_unchanged` compares thirteen entries —
ten channels, the recovery pool, the verifier key and the verified-user counter —
and is renamed for thirteen. `docs/engineering/verification.md` requires a name
to assert no more than its value establishes, and a name asserting a *different*
number is the same defect seen from the other side.

**Six mutation probes ran and five were caught immediately**: a state root that
drops the timestamp, a predecessor preimage that writes version nine's schema
version, a header whose timestamp and height swap places, an encodable zero
figure, and a kind-12 value left at version eight's width. **The sixth passed and
was re-aimed rather than accepted.** It changed `146'096` to `146'095` inside the
era arithmetic, which is an *equivalent* mutation over the accepted range — the
M3.10b lesson exactly. Re-aimed at the **century correction**, by zeroing the
`day_of_era / 36'524` term, it fails on `century_common_march_first`: 2100-03-01,
the case an abbreviated leap rule gets wrong. A probe that passes is a question
about the probe before it is a question about the code.

**The calendar is checked against `calendar-v1`'s own file rather than against
version nine's restatement of it.** Twelve recorded derivations, both sides of
three month boundaries, two leap-year Februaries, the century that is not one,
the last millisecond the calendar defines, five February lengths derived from
month edges rather than from a table, and the ordered rejection conditions read
out as a list. Those vectors were recorded by driving the accepted calendar
model; reproducing them is agreement with the specification this version binds.

**The coverage guard fails both ways and that is the point.** A claimed vector
never consulted fails, and a deferral that matches no unconsulted vector fails
too, so an exemption cannot outlive what it excused. Five deferrals are recorded:
`attribution.` and `settlement.` to the ledger slice, `carryover.` and the
per-predecessor empty roots to the Python verifier, `kind22.is_confirmable_mint`
to the ledger because confirmation is a predicate over a stored posture rather
than a codec table, and `genesis.refuses_a_timestamp_below_the_range` **to
nobody** — a timestamp below zero is unrepresentable in the `u64` this kernel
carries, so recording the case would mean constructing a value the type forbids.
Naming that as unrepresentable rather than deferred is the honest classification;
calling it deferred would promise a later slice something no slice can deliver.

**One local practice is worth repeating.** This machine has no CMake and no
libsodium, and building either is the heavy local operation the repository
instructions forbid. A scratch shim forwarding `crypto_hash_sha256` to the
already-installed OpenSSL let the whole codec target compile, link and **run
locally with real digests** before anything was pushed — which is what caught
three recorded-fixture mistakes that would each have cost a hosted round trip:
`header.timestamp_field` is a boolean and not the timestamp, the kind-22 body's
destination and signature octets were transposed, and the four mint messages use
one seat rather than two.

### How M3.17c was delivered

**The unreferred performance pool pays somebody, and it is the first time.** It
has accrued since `economy-transition-v3` — an unreferred seat's 34.2 units per
cycle route to it, version six gave it entry kind 12, version seven's genesis
writes it — and **nothing had ever taken value out of it**.
`simulation/economy_transition_v9/` gained `ledger.py`, `receipt.py`,
`execution.py`, `transitions.py`, `block.py` and `trace.py`, and
`test-vectors/economy-transition-v9-execution.txt` records 125 vectors over two
scenarios. Two ctest entries gate them. No accepted vector, model, manifest,
encoding or kernel source changed, and the version-eight, payout and calendar
suites all still pass unchanged.

**The recorded run.** Two unreferred machines run a window the chain measures.
Alice answers all **69** challenges she is issued; Bob answers none of his **75**.
At the assignment of the window that opens March, February closes on the uptime
accumulated *during it*, Alice wins the whole balance as a claim, and she mints it
with kind 22. An unconfirmed mint is refused `BIOMETRIC_REQUIRED` and the
confirmed one succeeds **on the same nonce in the same block**, so the refusal is
shown to write nothing; a second mint collects nothing; a stranger minting another
seat's award is `UNAUTHORIZED`. A second scenario jumps the same chain's stamps
ninety days between two window openings, and one assignment closes March while
skipping April, May and June in a single pass.

**A probe found a coverage gap and it was the defect this slice's own commit
message had just described.** `advance_to` carrying the timestamp is the thing
the setup shorthand must get right: one that advanced the height and left the
stamp behind would commit a root naming a height the stamp does not belong to,
and **every later block would still satisfy C2**, because a stale stamp is
smaller than the next one — a wrong root rather than a refusal, which is the
direction that hides. **No vector caught it.** The consequence is observable in
exactly one place, the root the shorthand leaves behind and the next block
carries as its `previous_state_root`, and nothing recorded that root. **Writing a
guard and describing it in a commit message is not evidence that the guard
works**; the probe is what turns the description into a vector.

**A second probe found something better than a defect.** The specification says
the figure accumulation must precede the deletion *because the figures are
computed from the records the deletion removes*. That is true of an
implementation that reads those records **lazily**, and **vacuous** for one that
derives the window's seat sequence once before either step — which every
conforming implementation does, because the settlement needs the same sequence the
assignment does. So the two orders commit to the same root. The vector records
the **equality with its reason** rather than asserting a difference that is not
there, which is the shape ADR 0064 already used for version eight's
prologue-before-issue ordering, and it is the place a later lazy implementation
would be noticed. **Deleting the vector because it proves nothing would remove
the only place that change is visible.** The other new ordering — the payout
before the accrual — **is** observable: running the rejected one reaches a
different root.

**ADR 0078 records four rules that outlive the slice.** The four new maps are
typed fields projected into entries, which is version six's and version seven's
pattern rather than version eight's: version eight held a raw key map because its
uptime transitions read that key space directly, and nothing in version nine
does. `advance_to` takes the timestamp as a **required** argument for the reason
above. `block.py` binds `timeline.replay` and never binds `timeline.accept`, so
the C5 separation is structural rather than a nullable argument a caller might
fill in. And a timestamp failure raises the block transition's own rejection,
restoring the pre-block state through the snapshot `execute_block` already takes.

**The trace runs at ninety seconds a block and the reason is worth keeping.** At
the commit target a window is exactly one day, so a month is about thirty windows
and 864,000 heights — more than a recorded trace can run. At ninety seconds a
window is exactly thirty days, every window opens in a new month, and a
settlement is reachable inside three. Nothing in the contract bounds the block
rate from above, and a seat's figure is `credited_slots * SLOT_SECONDS`, a
function of **heights**, so a slower chain changes when a month closes and
changes nothing about what a machine earned. That is what makes the fixture a
chain rather than a contrivance.

**Facts a later session should not rediscover.** The ledger extends version
eight's and overrides six things: genesis, `apply_assignment` (which raises
`pool_payable` beside `pool_accrued`), the projection, the root, the invariants,
and `advance_to`. `block.execute_block` takes the timestamp as its second
argument, and `run_quiet_heights` takes a `timestamp_of_height` callable — which
is the one place a trace decides how fast its chain runs and is what makes a halt
expressible, since a halt is a discontinuity in that function and nothing else:
heights stay consecutive because a network that is down produces no heights at
all. `BlockOutcome` carries `timestamp`, `due_month`, `settled` and
`skipped_months` beside version eight's fields. The two ctest entries are
`economy-transition-v9-execution-vectors` and `economy-transition-v9-execution`,
and the execution test caches both scenarios at module level because each is a
real chain of over a hundred thousand heights.

### How M3.17b was delivered

**The version-nine contract half executes in Python and 213 vectors record it.**
`simulation/economy_transition_v9/` is eight modules and no copied table,
`test-vectors/economy-transition-v9.txt` is normative, and every value in it is
derived twice — once by an `expected.py` that imports nothing from `simulation/`
and computes the calendar by **accumulating month lengths from 1970** rather than
by the closed form the model uses, and once by a live run. Two ctest entries are
registered. No accepted vector, model, manifest, encoding, or kernel source
changed, and the accepted calendar, payout and version-eight suites all still
pass unchanged.

**The first thing the slice did was find a defect in the specification it was
built from, and it found it by reading rather than by running.** M3.16a's payout
model writes no claim when the share rounds to zero; `economy-transition-v9` said
to add the share to each winner's claim "creating the entry if absent", without
qualification, and **adding zero to an absent entry creates one**. A claim is a
balance and a balance of zero is absence — the rule the monthly figure already
follows and the one `protocol-primitives-v1` imposes everywhere. In the zero-best
month that would be up to 100,000 entries recording that nobody was paid
anything. It was corrected before the model existed, which is the cheapest point
it could have been corrected at and the reason to read the accepted models before
writing a new one.

**A mutation probe found a coverage gap the vectors could not have found on
their own.** The independent header derivation could **lose the timestamp
entirely** and every one of the 207 vectors still passed, because nothing called
it: the header was checked by its widths and offsets and never by its bytes.
**A derivation no vector reaches is not evidence, it is decoration**, and the
only thing that distinguishes the two is a probe. `header.py` now holds the
154-octet header and its identifier, and it lives in the **contract half rather
than beside block execution** — what a block header *is* is an encoding and
belongs with the state keys and the genesis bytes; what a block *does* belongs
with the transition.

**Sixteen probes were run and every one that changed behaviour was caught**,
against a no-op control that was not. Among them: a zero share writing a claim
entry, the share dividing by one winner fewer, the candidate set excluding its
last window, replay applying the tolerance, the mint message dropping the kind
byte, the header swapping height and timestamp, the block-id label left at
version one's, a paid month's figures left undeleted, and **the accrual applied
before the payout, which fails 23 vectors** — so the normative ordering is
evidence rather than decoration. The candidate-set probe is worth naming
separately: it was caught by the model's **own accrual theorem**, reporting
"month 673 accumulated uptime and has no candidate", which is the theorem firing
exactly where `unreferred-pool-payout-v1` says it should.

**Three modules bind an accepted model rather than restating its judgement, and
each carries the guard that keeps the binding honest.** `timeline` drives
`simulation.calendar` over the same proposals and requires the same condition to
fire at every height — merely accepting the same blocks would not be checked,
because the **ordered conditions** are the part a second implementation gets
wrong. `settlement` drives `simulation.unreferred_pool` over the same month and
requires the same winners, share and remainder; over the whole recorded run the
two reach **identical claims**, and version nine's *skipped* months are exactly
the payout model's *carried* ones, which is the single-pass equivalence
demonstrated against an accepted artifact rather than against a loop written for
the occasion. `envelope`'s mint message reproduces version six's construction
byte for byte on all three of version six's kinds.

**Two restatements were unavoidable and are named rather than hidden.** Version
six's `mint_message` guards its `kind` argument against version six's three
confirmable mints, which is correct there and wrong for a version with four; and
a ledger holds a head rather than every block it has seen, so `calendar-v1`'s
conditions are restated over two scalars rather than driven through a chain of
`Block` objects. **A restatement is only safe if something keeps the two equal**,
which is what the guards above are for.

**The carryover classification produced a correction of its own.**
`MAX_GENESIS_ACCOUNTS` does **not** move — 48-octet account entries absorb eight
more prefix octets without crossing an entry boundary — so it is carried as
version eight's own object and the recomputation under the wider prefix is a
**guard** rather than a redefinition. A later version that widened the prefix
past an entry boundary fails there instead of silently admitting one account
fewer than its own table says. The final classification is 119 carried, 15
revised, 20 added, and five of version eight's own provenance names replaced.

**Facts a later session should not rediscover.** The package is
`simulation/economy_transition_v9/`: `contract.py` the classification and the
new constants, `state.py` the four entry kinds and the root that commits to the
timestamp, `genesis.py` the 150-octet genesis and its sixteen entries,
`header.py` the 154-octet header, `envelope.py` kind 22's body, `timeline.py`
the five calendar rules as **two entry points that differ in exactly one
respect**, `settlement.py` the ranking and the single-pass rule, `scenario.py`
the fixture. The fixture is **bound** from `simulation/unreferred_pool`'s rather
than invented beside it, so one genesis timestamp and one window sequence drive
both models. **That sequence is sampled rather than consecutive** — 0, 1, 2, 3,
4, 33, 63, 155 — which is legitimate for a fixture about arithmetic and is not a
claim about a chain: a real chain assigns every window, because heights are
consecutive and a halt moves the timestamps rather than the heights. The
execution fixture cannot sample, and the one place the sampling shows is
`close_month`'s `last_window` argument, which a real chain fills with `due - 1`. The seam to the execution half is that `settlement.py` operates on
plain decoded dicts — `{(month, seat): seconds}`, `{seat: (accrued, minted)}`,
and a `Pool` triple — so `block.py` wires it to the ledger's encoded maps without
either half reaching into the other. The two ctest entries are
`economy-transition-v9-vectors` and `economy-transition-v9-contract`, and
`verify.py --emit` rewrites the vector file through the same agreement gate.

### How M3.17a was delivered

**The version-nine clock and monthly settlement are specified and none of it is
implemented.** `docs/specifications/economy-transition-v9.md` and ADR 0077 are
accepted, and they are the contract that turns two accepted-but-unenforced
specifications into behaviour independent nodes reproduce. Documentation only:
no source, build, workflow, dependency, configuration, or vector file changed,
and the only edits to accepted documents are three cross-reference passages.

**What it closes.** `calendar-v1` fixed a consensus timestamp **no block header
carried** and a month **no transition read**; `unreferred-pool-payout-v1` fixed a
ranking over figures **no state held** and a payout **no block performed**. Both
took the posture `cycle-boundary-v1` and `uptime-measurement-v1` took, and left
the same gap. Version nine adds the header field, the genesis field, the state
root's commitment to the timestamp, four entry kinds, a third quantity on the
unreferred pool, one transaction kind, and two steps of the prologue.

**Two findings are worth more than the encoding.**

**The winner's award is a per-seat running balance and not a per-month claim**,
which is how the handoff had provisionally described it. A per-month award would
make collecting `n` months cost `n` transactions and `n` fees, would need the
mint to name a month or walk a range, and would hold an entry per win forever for
a seat that never collects. **The owner had already decided it**: "a mint takes
everything with no quantity choice" is the M3.8a answer that kinds 4, 5, and 18
all implement, and the reasoning the owner gave then is the same reasoning here —
a mint that can take a chosen amount must record what it took. That is why the
decision was classified delegated rather than sent back as a question, and the
specification cites the answer rather than restating the preference.

**Exactly one month can close per assignment, so the settlement is a single pass
rather than a loop over the closed indices.** `unreferred-pool-payout-v1` says
the payout runs once per closed index in ascending order, which reads as a loop.
Window attribution is non-decreasing and consecutive assigned windows carry the
cursor's month and the new one with nothing between them, so every index strictly
between is an **empty** month — no window attributed, therefore no accrual and no
candidates, therefore a pass that leaves the balance exactly as it found it.
**It matters because the gap is bounded by nothing a chain controls**: a network
halted for a year resumes with twelve empty months between, and a genesis
timestamp decades in the past would close hundreds at the first assignment.
Iterating them makes one block's work proportional to how long the network was
down, which is a denial of service reachable by an outage rather than by an
attacker.

**The equivalence had to be stated as evidence rather than as an invariant, and
noticing that is part of the finding.** The first draft claimed an invariant
would catch a later change that broke the theorem. None can: the single pass and
the loop agree on every state they both produce, so nothing over a single
accepted state separates them. What separates them is a scenario, so the required
vectors settle a multi-month halt **both ways** and require the two to agree
state for state.

**Committing the timestamp to the state root is forced, and its cost is the
beacon.** C2 compares `t(h)` with `t(h - 1)`, so a machine that restarted or
restored from a snapshot must know its predecessor's stamp, and a value two
machines could hold differently without their roots differing is a fork no gate
catches. The consequence is that version eight's `beacon(h)` — the state root at
`h - 1` — now varies with the timestamp, so on a **quiet** block, where the root
was previously fully determined, a proposer gains about `2^16.9` values inside C5
to grind over. The specification quantifies it, argues the marginal risk is small
(a challenge harms only a seat that cannot answer, and sparing one across a slot
needs essentially every proposal), refers it to the review ADR 0027 already owes,
and **records the cheap mitigation it declines** — a beacon excluding the
timestamp would cost a second root construction on the pipeline's most
adversarial path.

**Measuring a bound rather than inheriting it corrected one figure.**
`unreferred-pool-payout-v1` sized the live window-month records at **three** —
the open window and the two in the assignment lag. Version nine deletes the
oldest of the three in the same prologue that assigns it, so the encoded count is
**two** at every point inside a block. The input document was sizing before the
binding version decided where the deletion falls; the smaller figure is the real
one, invariant 2 states it over the state, and the vectors measure it over a
recorded run rather than asserting it.

**Version nine adds no result code, and that is a property rather than an
accident.** Kind 22 reuses kind 4's ladder exactly, so every refusal it can
produce already has a number and the space stays at 45. The opposite would have
been worth noticing: a new mint needing a new refusal would be a mint whose
authority rules differ from every other mint's. The four conditions `calendar-v1`
names are block-level and belong to the application contract's status space.

**One open item of `calendar-v1`'s is answered rather than inherited.** A genesis
timestamp far from civil time: genesis validation applies C1 and **reads no
clock**, because the chain identity is a hash of the genesis bytes and a validity
rule that read a clock would make two machines disagree about a chain's own
identifier. A genesis in the future halts the chain at its first block reporting
`TIMESTAMP_NOT_MONOTONIC`, which is what the ordered conditions reach first and
is the reason an operator can act on.

**Facts a later session should not rediscover.** The four new entry kinds are 20
window month (`u8(20) || cycle_window:u64` to `month_index:u32`), 21 monthly
uptime figure (`u8(21) || month_index:u32 || seat_id:u32` to `uptime_seconds:u64`,
**nonzero only**), 22 monthly pool claim (`u8(22) || seat_id:u32` to
`accrued:u64 || minted:u64`), and 23 settlement cursor (`u8(23)` to
`accumulating_month:u32`). Kind 12's value becomes `accrued || payable || minted`
at 24 octets. The header is 154 octets with the timestamp **inserted at offset
46**, after the height; genesis is 150 with `genesis_timestamp` **inserted at
offset 10**, after `network_id`; both insert rather than append so a mis-versioned
decode fails at the first comparison instead of producing a plausible header. The
prologue's order at an assignment height is: derive the sequence, version seven's
settlement steps 1 through 7, **settle the closing month**, settlement step 8,
**accumulate the figures**, then delete the kind-19 and kind-20 entries for the
due window — the deletion moves to the end because the figures are computed from
the records it deletes. Genesis writes **sixteen** economy entries, the fourteen
plus the cursor and window 0's month, both at `month_index(genesis_timestamp)`,
because height 0 does not exist and genesis is window 0's opening height.

**What the slice deliberately did not write.** `consensus-application-v1` says
timestamps are not application transition inputs and freezes its frame at version
1; both become false under version nine. The specification states exactly what a
conforming application contract must gain — the timestamp in `ProcessProposal`,
`FinalizeBlock` and `InitChain`, C5 applied in the first and **never** in the
second, and a block-level status rather than a transaction result — and stops
there. Writing both in one document would put a wire encoding inside a consensus
transition, and version eight's layering is what says so.

### How M3.16a was delivered

**Candidate run 34896935985 on `92eb982` passed all five jobs**, and the branch
merged by rebase as `b05f09a`. Issue #294 and PR #295 accepted
[`unreferred-pool-payout-v1`](../specifications/unreferred-pool-payout-v1.md).
**Run 34898156677 then re-ran the full matrix on `b05f09a` itself** and passed
all five, because the post-merge run had been cancelled by the next push to
`main` before it finished. The rebase preserves the tree, so the candidate run
was already evidence about these bytes; the second run makes the commit on
`main` carry it directly rather than by that argument.

**The cancellation is the workflow's concurrency group doing its job and it is
worth knowing about.** `verify.yml` groups by ref with `cancel-in-progress`, so
a push to `main` cancels the matrix still running for the previous push to
`main`. Pushing a closeout immediately after a merge therefore leaves the code
commit unverified on `main` unless the run is restarted. Either wait for the
post-merge matrix before pushing the closeout, or re-run it afterwards as this
slice did.

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

## The handoff as it stood on 2026-10-03

Everything below is [`current-state.md`](current-state.md) from its `## Phase`
heading to its end, moved here on 2026-10-09 **verbatim**. Every heading is
demoted one level so that it nests under this one, and nothing else changed:
not one line is reworded, reordered, summarised, or dropped.

**Why it moved.** The first split, on 2026-09-14, left the handoff a little
over 4,300 lines. Nineteen days later it was 5,623, and every session is told
to read it first. The `How ... was delivered` records had stayed out, as
`CLAUDE.md` asks. What grew instead was the narrative around them: each slice
added a dated paragraph to "Phase", "Remaining gap", "Exact next action", and
"Blockers", and marked the paragraph it superseded as history rather than
deleting it. The handoff was
rewritten to the present, and `tools/verify_metadata.py` now refuses it above
600 lines.

**"This document" below means the handoff**, as it did when each sentence was
written. A passage here may describe superseded state, as every record in this
log may. Where it disagrees with `current-state.md`, the handoff is current.

### Phase

**M4.2c minted on a network on 2026-10-03.** It is the last of ADR 0096's three
slices and meets requirement 2 of [`first-goal.md`](first-goal.md): a kind-4
mint and a kind-18 mint execute on four replicas. No network in this repository
had minted before.

**Its first hosted run found a consensus defect in the C++ kernel, and it is
repaired.** `verified_user_collection` computed `collectable_end - 30` in
unsigned arithmetic. Before window 31 it wrapped, so every kind-18 mint in a
chain's first thirty windows issued thirty daily permissions, 51.3 units,
whatever it had earned. All four replicas issued that for Alice's two windows,
where the model issued 3.42 units. The specification and the model were right.
[ADR 0098](../decisions/0098-a-kind-18-mint-before-window-31-collects-what-was-earned.md)
repairs it inside version nine, as ADR 0094 did the referral mark. A new
kernel check pins eleven collections at the model's figures and fails on the
unrepaired line. No recorded vector reaches the case, so this is the first
defect a network found rather than a model.

**The model runs the history alone, and the network begins at its head.**
`tests/integration/seeded_mints_v9.py` is the script:

- Alice and Bob enroll, and Alice buys and activates seat 0 in window 0.
- Seat 0's machine answers every audit it is issued through windows 1 and 2.
- Block 86,400 opens window 3 and assigns window 1. It is the seed's head,
  stamped with the clock. Every height below it is one millisecond apart and
  ends before the run starts. So the whole history falls in the launch's
  month, and no settlement depends on the date of the run.

The model runs those 86,400 heights in about two seconds.

**`cometbft_seeded_mints_v9_test.py`, in `tools/verify.sh`, is the evidence:**

- four replicas are seeded at 86,400, and block 86,401 carries the head's stamp;
- Alice's kind-18 mint issues two daily permissions, 3.42 units;
- her kind-4 mint issues one whole base permission, 574.3 units, because seat 0
  met the cycle and is the only seat;
- every receipt and root on all four replicas is the model's;
- a second mint of each kind is refused as `NOTHING_TO_MINT`, and Bob minting
  her seat is refused as `UNAUTHORIZED`, each on the empty-block root;
- all four stores are audited after the stop.

`version_nine_chain_test.py` runs the same script offline as its eleventh check
and requires both amounts exactly. No contract, encoding, or vector changed.
On the hosted runners it passed in all four jobs of candidate run 37078876254,
whose tree `main` holds byte for byte at `f97b190`, M4.2c's merge.

**M4.2b launched a four-validator network above height zero on 2026-09-29**,
the second of three slices toward a mint on a network.
[ADR 0097](../decisions/0097-a-seeded-launch-takes-its-genesis-from-one-head.md)
records the rules. `protocol-cometbft-devnet start -seed <snapshot>` does the
following:

- seeds all four stores from one snapshot on the first start, and none on a
  restart;
- derives the engine's genesis from the snapshot's head, which the new
  `protocol-application-v9 --inspect-seed` prints without writing anything:
  `initial_height = H + 1`, the head's root as `app_hash`, and the head's stamp
  as `genesis_time`, exactly.

No option sets one of the three alone. A seeded home refuses any start that
names no snapshot, another head, or a snapshot the restore gates refuse.

**The slice found and corrected a gap in ADR 0096's reading of the engine.**
CometBFT v0.39.4 does skip `InitChain` over a nonzero application height. But
`NewNodeWithContext` reloads its state store after the handshake, and only
`InitChain` saves one. So the first seeded network panicked on a nil validator
set. The launcher now writes each fresh seeded home's genesis state, the one
`InitChain` would have saved, and never overwrites a state the engine has moved.

**`cometbft_seeded_launch_v9_test.py`, in `tools/verify.sh`, is the evidence:**

- four replicas are seeded at height 4 from a model-encoded snapshot;
- block 5 is stamped with the seeded stamp to the nanosecond;
- two transfers from the seeded balance land on the model's roots;
- three wrong launches are refused, with every home and store byte-identical
  afterwards;
- a restart from the seed works, and all four stores are audited after each
  stop.

It passed locally before any hosted run. A launcher whose genesis time was 1 ms
late failed it by name. On the hosted runners it passed in candidate run
36602233169 and again in push run 36604219737 on `17e51c9`, M4.2b's merge.

**M4.2a made a store seedable from a snapshot on 2026-09-27**, which is the
first of three slices toward a mint on a network.
[ADR 0096](../decisions/0096-a-devnet-may-begin-from-a-restored-snapshot.md)
chose ADR 0071's snapshot route, so a network launches at `H + 1` over seeded
stores with no contract change. The chain's genesis stays at height zero. The
slice added:

- `seed_sqlite_ledger_v9`, which accepts a payload only through the
  snapshot's three gates, refuses height zero and non-canonical octets, and
  leaves no file when it refuses;
- `protocol-application-v9 --seed <database> <genesis> <snapshot>`, which prints
  the chain identity, height, stamp, and root a launcher needs;
- `tests/integration/version_nine_snapshot.py`, a Python encoder for the
  payload.

**Every successful seed is a cross-language check of that encoder.** The C++
seed re-encodes the decoded state and requires the same octets.
`version-nine-seed` seeds four model ledgers, up to height 5,760,000, which
carry all 19 entry kinds a block can write. It also refuses four bad seeds.

**M4.1 put a test Founder's lifecycle on the four-validator devnet on
2026-09-27.** This is requirement 1 of [`first-goal.md`](first-goal.md). The
run is `tests/integration/cometbft_founder_lifecycle_v9_test.py`, and
`tools/verify.sh` runs it after the four-validator run. It asks four independent
replicas for eighteen blocks, through all four nodes and two full restarts:

- Alice enrolls, buys a seat, and activates it.
- Her HUB key admits a second signer, creates a holding escrow, and funds it.
  The holding escrow gets its own signer and pays.
- The HUB key revokes every signer she has, and each revoked key is refused as
  `SIGNER_NOT_FOUND`.
- After a restart during which she holds no signer, the HUB key recovers her,
  and the new signer pays.

Another person's HUB key, and her own signer presented as the authority, are
both refused as `UNAUTHORIZED` to admit a signer, so no wallet key alone
rewrites an identity. A holding escrow with value cannot be deleted. The script
is `founder_lifecycle_v9.lifecycle`, and `version_nine_chain_test.py` checks it
offline as its tenth check.

No contract changed, because the kernel already executed every step. **Before
any hosted run, the locally built `protocol-application-v9` reproduced all
eighteen receipts and roots byte for byte**, through two process restarts. It
was driven directly over its socket.

**M3 is complete: M3.21d met requirement 16 on 2026-09-27, and M4 is the
active milestone.** Requirement 16 asks for three things, and each is done:

- hosted verification on the accepted commit, `e79ea4d`, M3.21c's merge;
- M3 marked complete in the roadmap;
- a handoff naming the first M4 implementation slice.

All sixteen M3 requirements are met, three with recorded limits: 7, 13,
and 14.
[`founder-economy-devnet-audit-v1.md`](founder-economy-devnet-audit-v1.md)
states each against its evidence. The M3 goal is retained unedited as
[`goals/m3-founder-economy-devnet.md`](goals/m3-founder-economy-devnet.md), as
M1's and M2's were. [`first-goal.md`](first-goal.md) now states M4's
operational goal, drafted from the roadmap's M4 scope and ADRs 0039 to 0048,
with the founder-reserved legacy, inactivity, key-rotation, payment, and
biometric details gated.

**M3.21c met requirement 14's multi-year leg on 2026-09-27 against the contract
the chain executes.** `economy-scenario-suite-v4` runs six research seats
through every window of their 731 cycles. It uses version nine's own prologue,
exposed as `block.open_window`, and signed transactions. The run covers:

- 1,068 windows and 4,386 seat-cycles;
- 668 signed transactions;
- 35 calendar months, a leap February among them.

It checks the exit audit's four claims at every window. All 263 recorded
vectors except seven state roots agree with `expected_v4.py`, a walk of the
settlement that imports nothing from `simulation/`. That walk also runs
differentially against 32 random populations.
[ADR 0095](../decisions/0095-the-fourth-scenario-suite-drives-the-chains-contract.md)
records it. Its limits: the uptime record is supplied, the run drives the
Python model and not the C++ kernel, and the audit's overflow limit stands.
**Fifteen of the sixteen requirements are now met, and requirement 16, the
closing act, is next.**

**M3.21b repaired a consensus defect on 2026-09-27: a new referral balance now
starts its mark at the window before its first accrual.** Version three states
that rule, and every later version carries it unchanged. Every executed
implementation instead started the mark at zero: the Python models from version
six on, and the version-nine C++ kernel. So a referrer whose first accrual
landed after window 30 was capped from their second accrual onward, and every
later leg went to the unreferred pool until they minted.

No accepted vector recorded the defect. All 2,977 vectors from version six to
version nine pass unchanged against the repaired models, so the repair is made
inside version nine and is not a new version.
[ADR 0094](../decisions/0094-a-new-referral-balance-starts-at-the-window-before.md)
records it. A Python test and a C++ check each fail on the zero mark.

The defect was found while designing `economy-scenario-suite-v4`, which is
still the next action.

**M3.21a ran M3's exit audit on 2026-09-27, and M3 does not close yet.**
[`founder-economy-devnet-audit-v1.md`](founder-economy-devnet-audit-v1.md)
states all sixteen `first-goal.md` requirements against the accepted artifact,
the executed check, and the hosted run on `main` at `3c5347b`. **Fourteen are
met, two of them with recorded limits.** Requirement 16, the closing act, waits
on requirement 14.
**Requirement 14's multi-year leg is not met against the contract the chain now
executes.** `economy-scenario-suite-v3` runs every seat's 731 cycles against
`founder-economy-simulator-v3`, which still has the per-channel carry. It has
none of the three rules added since:

- the recovery pool;
- activity decided from measured uptime;
- the calendar-month unreferred pool payout.

The current contract's models reach long horizons only in targeted scenarios.
This handoff recorded requirement 14 as "met against the v3 contract", and that
was true of a contract since replaced.

**The audit settled three open items as not M3's.**

- ADR 0048's threat model belongs to M4.
- ADR 0089's outage wall is a limit on requirement 13, to be settled before any
  network is expected to survive an outage.
- ADR 0071's audit on a network is outside M3 by its own decision.

It also consolidates, in one list, the independent review requirement 15 says
the ADRs owe.

**M3.20l closed the two gaps the handoff recorded on 2026-09-27.** First, a
restore now refuses a referral balance that no seat's referrer owns, and one
that accrued nothing. Both are storage rules in `snapshot_v9`, so no block's
acceptance moves.
[ADR 0093](../decisions/0093-a-restore-refuses-an-orphan-referral-balance.md)
records them. Second, `tools/verify_metadata.py` now checks the heading every
`#fragment` link names, using GitHub's slug rule exactly. All 41 fragment links
in the tree resolve.

**The version-nine migration is complete, and nothing recorded is owed to it.**
What remains is the milestone's exit audit. The paragraph below states the
M3.20k finding as it stood before M3.20l closed it.

**M3.20k deleted version eight on 2026-09-27, and the repository compiles one
economy contract again.** Version eight's C++ kernel, owning store, snapshot,
application, transport, and node process are gone, with their tests, targets,
and CTest entries. The Go adapter no longer bridges version eight, and
`-protocol-version 8` is refused beside 7. Version eight's accepted vector
files, its Python model, and its specification stay. Version nine is pinned
against the first two and built on the third.
[ADR 0092](../decisions/0092-the-version-eight-deletion.md) records it.

**Version nine was borrowing evidence from version eight in three places the
handoff had not listed, and each is now version nine's own.**

- **Nineteen checks in version nine's codec suite ran against the live
  version-eight kernel.** Each is now pinned to the accepted version-six,
  version-seven, or version-eight file that recorded the fact. Six are claims
  only an implementation can answer: that version eight *refuses* a
  version-nine artifact. They are owed to the Python verifier, which still runs
  version eight's model. Fifteen mutation probes of the recorded figures each
  fail the suite by name.
- **Version nine's snapshot suite sampled the inherited value rules** and left
  the full sweep to version eight's suite. Twenty-three refusals are ported, two
  of them over synthetic entries with a control that must reach gate 3. Seven
  decoder mutants each fail the suite.
- **`receiptResultOffset` lived in `wire_v8.go`**, which is ADR 0070's trap
  exactly, one version on.

The two traps the handoff did name are closed. `economy_v9_fuzz` replaces
`economy_v8_fuzz` with six new entry points, and ADR 0082 carries a correction:
`wire_v1` stays. **The omission ADR 0070 found happened again**:
`storage-snapshot-v9-fuzz-smoke` had never been given the fuzz label and the
60-second bound. It has both now.

**One finding is recorded rather than fixed.** A snapshot restore accepts a
referral balance that owes nothing, keyed to an identity that referred no seat.
No block writes one. Gate 3 checks the referral channel against what balances
*owe*, so an orphan that owes anything is refused and **no unit can be minted
from it**. The invariant is version eight's, ported unchanged. It is the exact
next action, and it belongs in the snapshot's `complete` step, where an uptime
entry naming an unsold seat is already refused.

**M3.20j ran the skewed replica on 2026-09-24, and with it
`consensus-application-v2`'s devnet evidence is met** apart from the kind-22
mint, which stays below the engine. One replica of a four-validator version-nine
network runs its clock 120 seconds ahead, then 120 seconds behind, then
corrected, while the network runs. Ahead, it votes against every proposal it
processes as `TIMESTAMP_BEHIND_TOLERANCE`; behind, as
`TIMESTAMP_AHEAD_OF_TOLERANCE`; corrected, against none. The other three never
vote against anything. The chain keeps committing and all four keep the model's
root. The skewed replica's own blocks are committed, and transactions enter
through it. [ADR 0091](../decisions/0091-the-skewed-replica-is-skewed-below-the-process.md)
records it.

**The clock is moved below the process, not by an option on it.** A test-only
`LD_PRELOAD` library offsets `CLOCK_REALTIME` by a figure it re-reads from a
file on every call. So the binary that ships is the one skewed, and the
contract's "a deployment's clock is the platform real-time clock" stays true
without amendment. The same library let the headless process test reach the two
paths ADR 0085 recorded as unreachable: a clock unreadable at startup, and one
that stops being readable under a running process. **One finding:** the pinned
engine asks a proposer to process its own proposal, so a skewed replica votes
against its own blocks too, and they still commit.

**M3.20i ran the version-nine four-validator devnet on 2026-09-24.** Four
independent replicas run version eight's whole scenario:

- transactions through all four nodes, including two refusals by name;
- two full restarts, each inside the window;
- a replica interrupted mid-block and handed blocks its peers never proposed;
- a replica that leaves while three keep committing, then catches up.

At every stop, each store must report the model's height, **stamp**, and root.
The model follows every height the engine closes, using each block's committed
stamp. [ADR 0090](../decisions/0090-the-version-nine-devnet.md) records it.
Two items of `consensus-application-v2`'s devnet evidence are not in the run. The
kind-22 mint is covered by the C++ execution vectors instead, behind two recorded
walls. The skewed replica was the next slice, and M3.20j delivered it.

**M3.20h ran a version-nine chain under one CometBFT node on 2026-09-24**, and
it is the first time a version-nine block was decided by anything but a test
driver. The genesis is stamped with the harness's clock when the run starts.
Every block is compared with the independent Python model: its receipt, its
root, its header hash, and its published identifier. The model computes each
from the stamp the engine committed, so every comparison is also an end-to-end
check of the bridge's time conversion.
[ADR 0089](../decisions/0089-a-version-nine-chain-resumes-only-inside-the-tolerance.md)
records it.

**Its finding outweighs the run.** Under CometBFT `v0.39.4` the first block
after an outage carries the median of precommits cast **before** the outage,
because a restarted node rebuilds them from its stored commit. So under the
accepted C5, **a version-nine chain whose quorum is down for more than 60 seconds
never produces another block**. ADR 0088's height-one halt is the special case
where the outage is the time before the network first starts. The run restarts
within seconds and is unaffected. The devnet can restart a whole network inside
the window. **A production network cannot promise that**, so the rule's cost is
recorded under "Remaining gap" as the thing to settle before any network is
expected to survive an outage.

**The owner directed a second, larger pivot on 2026-08-19, and it changes the
architecture rather than the milestone.** The ecosystem AI moves off
company-operated infrastructure and onto the Founder Machines themselves, which
reverses a constitutional clause standing since M1 and a `CLAUDE.md` constraint;
the company runs no backend of any kind, from the beginning; HUB verification
becomes a local deterministic process supervised by the local model; the
per-channel carry is replaced by a recovery pool so that 100% of the node
distribution is assigned; best-performer ranking becomes permanent
infrastructure rather than an artifact of the 731-cycle distribution; months
become real calendar months read from a consensus timestamp; bridges run on
Founder Machines with light clients and a machine quorum; and channel 9 is
renamed from `initial_mystery_box_incentives` to `mini_gamified_incentives`.
**Six ADRs — 0047 through 0052 — record it, and the constitution, `CLAUDE.md`,
and `first-goal.md` now state it.**

**None of it invalidates the C++ kernel delivered so far.** Escrows, signers,
identities, transfers, admission, and block execution are indifferent to who
runs AI. What it does change is the settlement — the carry, the winner rule, and
the in-scope derivation — which is exactly the slice that had not been started,
so the pivot arrived before its cost rather than after it.

**M3.10d put the version-six ledger and its ten non-seat transitions into the
C++20 kernel on 2026-08-19.** It is the first time anything in the repository
executes a version-six transition in C++ rather than encoding one.

**M3.11a delivered `founder-economy-manifest-v3` the same day**, which is the
first piece of the pivot to become an accepted contract. It renames issuance
channel 9 from `initial_mystery_box_incentives` to `mini_gamified_incentives`
and changes nothing else, which is why it is a whole manifest version: a channel
identifier sits inside the manifest JSON, the digest is a hash over that JSON,
the digest is a genesis field, and the chain ID is a hash of genesis.
[ADR 0053](../decisions/0053-founder-economy-manifest-v3-the-channel-rename.md)
records it.

**M3.11b delivered `economy-transition-v7` the same day**, which is the piece of
the pivot that changes behaviour rather than an identifier. The per-channel carry
is deleted from state and replaced by a recovery pool, so the node distribution
assigns 100% of the permissions the manifest promises instead of leaking two
silent remainders into a term nothing ever released.
[ADR 0054](../decisions/0054-economy-transition-v7-the-recovery-pool.md) records
the four decisions ADR 0049 left a contract to settle, and one thing ADR 0049
got wrong.

**M3.11c made version seven execute on 2026-08-20**, which is what M3.10b was to
version six: a ledger state, the assignment prologue, ordered block execution,
a recorded trace, 412 vectors, and a verifier. **It is the first time anything
in the repository carries a recovery pool from an unwon cycle to a mint.** The
recorded schedule ends with `outstanding` at zero and the pool at zero on every
Founder Node channel — 100% of what the manifest promised for those cycles
reached a beneficiary, where version six leaves four base permissions in a
carry nothing releases.
[ADR 0055](../decisions/0055-the-version-seven-execution-model.md) records the
two rules it had to derive and one finding worth more than either: the
assignment ordering ADR 0045 could only reject by argument is
**unconstructible** under version seven, because the backing identity refuses
the block whole.

**M3.12a closed a gap M3.11c left, and the way it was found is the point.**
Attempting the kernel move showed that ADR 0055's reason for not re-recording
version six's execution scenarios is half wrong: those 512 vectors record
version-**six** roots and version-**six** receipts, and version seven
re-versions both, so ten of the fourteen kinds had no version-seven execution
evidence at all. Under the three scenarios ADR 0055 accepted, **swapping
version seven's escrow-create and escrow-delete handlers in its own dispatch
table passes every one of the 412 vectors.** Two scenarios close it, the file
holds 590 vectors, and all fourteen kinds now execute under version seven where
version six's file reaches eleven. ADR 0055 carries the correction in place.

**M3.12b moved the C++20 kernel to version seven on 2026-08-29, and it is the
first time a chain in this repository can run the recovery pool in C++.** The
kernel compiled `economy-transition-v6`: its byte surface, its ledger, and ten
of its fourteen transitions. It now compiles `economy-transition-v7` — the byte
surface, the settlement, **all fourteen** transitions, and the assignment
prologue it never had at any version. Following ADR 0046, version seven
*replaces* version six rather than sitting beside it; version six's Python model
and both of its accepted vector files remain in place, passing, and unedited.
**Requirement 10 is met.**

M3 — Founder Economy devnet, in progress. Slice M3.1 delivered the revised
economic contract, M3.2 made it executable, and M3.3 rebound every dependent
model to it, all on 2026-08-08. M3.4 defined the cycle boundary in chain heights
and M3.5 defined the uptime measurement pipeline, both on 2026-08-09. M3.6a
enforced both inside the economy model and M3.6b rebound the escrow payout
model to it, both on 2026-08-10. M3.6c rebound the scenario suite on 2026-08-11
and closed the dependent rebinding. M3.7a reclaimed the hosted matrix margin on
2026-08-12 and changed no protocol behavior. M3.8a defined the consensus
transaction and state surface on 2026-08-13, M3.8b revised it to
`economy-transition-v3` on 2026-08-14, M3.8c settled it as
`economy-transition-v4` on 2026-08-15, M3.9a put that contract's codec into the
C++20 kernel the same day, M3.9b accepted `economy-transition-v5` after
implementing version four exposed a transition with no conforming
implementation, and M3.9c gave version five its model, vectors, and verifier.

**The owner directed a pivot at the close of M3.9c on 2026-08-15, and it changes
the next action.** HUB verification becomes mandatory for anyone who registers
and for interacting with any part of the ecosystem, an address becomes an
operational tool rather than an identity root, and biometric confirmation
becomes the default on every financial transaction and every mint.
[ADR 0039](../decisions/0039-hub-verification-is-mandatory-for-everyone.md)
records it and the constitution now fixes it. **Three further ADRs the same day
completed the architecture and closed every founder question it raised**:
ADR 0040 replaced addresses-as-identity with keyless asset escrows and revocable
signers, ADR 0041 tied the Founder Seat to the identity rather than to any
address, and ADR 0042 funded a brand-new account's first action from the
verified-user channel. The C++ codec slice is withdrawn; the next slice is the
contract that encodes the direction. **Its founder-decision gate stopped it on
2026-08-15 with four reserved decisions**, two of which the constitution had
listed as unresolved since the pivot; the owner answered all four the same day
and [ADR 0043](../decisions/0043-founder-answers-on-reach-asymmetry-forfeiture-and-signers.md)
records them. **M3.10a then delivered `economy-transition-v6` the same day** —
the specification, ADR 0044, a sibling model, 462 vectors, a verifier, and 91
tests — so requirement 10's target is settled again and the C++ kernel has a
contract the direction does not supersede. **M3.10b then made that contract
execute on 2026-08-16** — a ledger state, the fourteen transitions in their
rejection orders, ordered block execution with the cycle-assignment prologue, a
recorded six-scenario trace, 512 vectors, a verifier, and 51 tests. It is the
first time anything in the repository *runs* a version-six transition rather
than encoding one, and it settled four execution rules the accepted contract
left to be derived. ADR 0045 records them. **M3.10c then put version six's byte
and derivation surface into the C++20 kernel on 2026-08-17**, replacing version
four's codec rather than adding beside it, and gave the decoders the fuzz target
the codec should always have had. ADR 0046 records both decisions.

**M3.13n opened the stack migration on 2026-09-04**, and it is the first slice
in this repository to add a kernel beside another rather than in place of it.
[ADR 0065](../decisions/0065-a-kernel-replacement-may-be-staged-across-a-stack-migration.md)
amended ADR 0046 to permit that under a stated end, and the end is enumerated:
`src/v8/` and `include/protocol/v8/` arrive at step 1 and **M3.13t deletes
`src/v7/` and the six layers written against it at step 7**. What the codec
slice delivers is the byte and derivation surface of `economy-transition-v8` —
two transaction kinds, two state entry kinds, twelve result codes, one genesis
field, and the two signed constructions — verified against 121 of that
contract's 183 vectors. The other 62 need a ledger and are M3.13o's.

**M3.13o completed the kernel on 2026-09-05**, which is step 2 of the seven the
migration enumerates. `execute_block` loses its `UptimeSchedule*` parameter and
derives the schedule from the seat table and the window records instead, so a
node cannot be handed a different answer than its peers computed; the block
gains the issue step and the expiry step and now runs at every height. **It is
the first time the C++20 kernel has run a chain that measures its own machines
and pays one of them**, and all 617 of `economy-transition-v8`'s recorded
vectors — 183 contract and 434 execution — are reproduced in C++.

**M3.13p carried the migration into storage on 2026-09-05**, which is step 3.
`snapshot_v8` is what lets a version-eight state leave memory at all: the ledger
holds two entry kinds no version-seven snapshot has a place for, so no store,
application, or node could hold a version-eight state before it existed. ADR 0066
records it. **Its sharpest result is about version eight's own invariants rather
than about the snapshot.** Two of the six M3.13o added — the window record's
retention bound and the open challenge's deadline bound — are the *only* thing
refusing a resealed payload that carries a well-formed entry in an impossible
place; probes deleting either report "a restore accepted it". That carries
M3.13o's finding, that three of the six were unreachable by any recorded
scenario, one layer up into storage.

**M3.13q made a version-eight state durable on 2026-09-06**, which is step 4.
`SQLiteLedgerV8` is the store around the payload `snapshot_v8` produces, so a
version-eight chain can now be stopped and resumed without changing where it is
going. ADR 0067 records it. **Its sharpest result is about how a width fails
rather than about the store.** Two literals moved with the version and they
fail differently: a stale `canonical_genesis` width is caught by the very first
insert, and a stale `head_snapshot` minimum is caught by *nothing* — a short
blob would simply reach `decode_snapshot_v8` and come back `invalid_snapshot`
instead of never being stored, which is a weaker refusal rather than a wrong
one. The suite as version seven wrote it passes with the stale value in place;
that was checked by running it. `check_column_bounds` pins the figure at its
boundary instead, and it is the general lesson of the slice: **a figure that
moves with a version needs a test at its boundary, because a figure that
degrades a refusal rather than admitting a state is invisible to every test
that only asks whether the refusal happened.**

**M3.13r made a version-eight state reachable on 2026-09-06**, which is step 5.
`ApplicationV8` and the version-eight response encoder are what let a consensus
engine drive a version-eight chain, and ADR 0068 records them. **It closes an
owed item rather than satisfying one.** ADR 0058 recorded that version seven's
application passes a null uptime schedule, so a chain driven entirely through
`ApplicationV7` writes no cycle assignment record and accrues nothing to any
seat, and named wiring a measurement in as the dependency between that layer and
a chain that pays anyone. Version eight's prologue derives the schedule, so
there is no parameter left and the item disappears.

**Its sharpest result is the pair it forms with M3.13q's.** A fifth figure moved
that the slice's own survey had missed — the receipt magic prefix carries the
receipt version as its last octet, written out as a literal — and a rebound
encoder therefore compared version-eight receipts against a version-seven prefix
so that **no finalized block encoded at all**. That is the opposite failure mode
from the store's stale column width, which merely moved a refusal one layer
later and was invisible to every test. **A figure that moves with a version is
either checked on the happy path or it needs a boundary case, and there is no
third kind** — knowing which one you have is the question worth asking before
the tests are written rather than after.

**M3.13t deleted the version-seven stack on 2026-09-09**, which is step 7, the
last step ADR 0065 enumerates, and the slice that makes six slices of
coexistence legitimate retrospectively. `src/v7/`, `include/protocol/v7/`, the
version-seven snapshot, owning store, application, transport, and node process,
their tests and CTest entries, the Go adapter's version-seven client, and the
`serve_connection(ApplicationV7&)` overload are gone. **The repository compiles
exactly one economy contract again** and ADR 0046's rule applies unamended. ADR
0070 records it and ADR 0065 is expired.

**The enumeration was wrong about exactly one item, and a deletion slice found
it.** ADR 0065 listed `economy_v7_fuzz` for removal, and the handoff asserted
every deleted item had a version-eight counterpart already carrying its
evidence. That held for every item but this one: no `economy_v8_fuzz` was ever
added, so deleting version seven's as listed would have left the live contract
with **no economy-codec fuzz target at all**. ADR 0065's own cost section rules
that out — dropping coverage is the thing it says not to do — so the harness was
migrated rather than deleted, and the two uptime values version eight adds were
added to it. **The lesson is that a deletion enumerated in advance still has to
be re-checked against what actually exists when it runs**, because the
enumeration was written before three of the six slices it depends on had landed.

**A cross-version refusal test needs rewriting rather than halving when one
version goes.** `TestVersionsSevenAndEightRefuseEachOther` checked both
directions through two live decoders. One direction lost its implementation; the
other — a bridge pointed at a stale version-seven node must fail closed on the
first block — is the one that matters, and it survives with the version-seven
receipt written as a **literal** rather than read from a sibling, plus a
positive
control. This is M3.13n's rule one layer up: a pin that dies with the artifact
it
pins proves nothing afterwards.

**M3.13s ran a version-eight chain end to end on 2026-09-07**, which is step 6
and the first time anything in this repository executed a version-eight block
under a real consensus engine. `protocol-application-v8` serves `ApplicationV8`
on a socket, `ClientV8` speaks to it, and `-protocol-version 8` selects the pair
in the bridge, the initializer, and the devnet supervisor. ADR 0069 records it.
**Four independent replicas now agree on version-eight roots through a full
restart**, with three transactions entering through three different nodes.

**It found the third kind the previous slice said did not exist.** ADR 0067's
rule — happy path or boundary case, no third kind — holds for the genesis width,
the app state, and the receipt version, all of which break the happy path if
left stale. It does not hold for the **result-code count**, which moves from 33
to 45 while every test that uses it compares the constant to itself, and whose
new codes appear in no fixture. So the third kind is a figure **checked
everywhere and pinned nowhere**, and the test for it is an assertion against the
literal plus one input on each side, written out rather than derived. A probe
setting it back to 33 passes the entire inherited suite and fails only the new
assertion.

**A fifth figure of that kind is not a constant at all.** The two genesis keys
must be two keys, and a genesis carrying the verifier key twice encodes, derives
an identity, and executes every block — so the fixture requires the pair to
appear adjacent in the encoded genesis exactly once. The probe that passed the
verifier key twice was caught by that adjacency check and **not** by the
inequality beside it, because the session still held two distinct keys and only
the encoding was wrong.

**Requirement 10 is satisfied.** The kernel compiles `economy-transition-v7` in
full: the byte and derivation surface, the ledger, all fourteen transitions,
ordered block execution with the cycle-assignment prologue, and both
conservation identities. Before M3.10c it compiled `economy-transition-v4`,
which is the one economy contract already known to have no conforming
implementation; before M3.12b it compiled a contract the pivot had superseded
and executed ten of fourteen kinds.

Requirements 3, 4, 5, 6, 7, and 12 of `first-goal.md` are satisfied;
requirements 8 and 9 moved from specified to enforced; and requirement 14 is met
against the v3 contract at the standard the M2 suite set.
M2 completed on 2026-08-05 with all sixteen requirements of
`goals/m2-founder-economy-proof.md` passing.

**The remaining M3 work is no longer the C++ half.** Requirements 10 and 11 are
met against version seven: the kernel executes the contract, and the C++ and the
Python model reproduce both `test-vectors/economy-transition-v7.txt` and
`test-vectors/economy-transition-v7-execution.txt`. What remains is
`calendar-v1`, the HUB verification architecture of ADR 0048, and requirement
13 — the four-node adversarial scenarios, which has not started.
**Two of those three are now closed.** Requirement 13 closed with M3.14e on
2026-09-13, and `calendar-v1` was accepted by M3.15a on 2026-09-14. The HUB
verification architecture of ADR 0048 is the only one of the three still owed.

**M3.13a delivered the version-seven state snapshot on 2026-08-30**, which is the
first artifact that lets a version-seven state leave memory. ADR 0056 records it.
**It also corrected the recorded next action.** M3.12b's closeout named
`calendar-v1` "the only [contract] requirement 13 depends on"; version seven
mentions a month in one descriptive sentence and executes nothing against one, so
what requirement 13 was actually waiting for was a state that can be written
down. `calendar-v1` is still owed and is not it.
**M3.15a delivered it on 2026-09-14**, four weeks after requirement 13 stopped
waiting for it, which is the order that sentence predicted.

**M3.13b delivered the version-seven owning store on 2026-08-31**, and with it
"no state survives a restart" stops being true of this repository. ADR 0057
records it. The head is one snapshot payload inside a SQLite database rather than
a row per entry, and the evidence is the one thing the snapshot alone could not
establish: **mid-scenario restart equivalence**. The `carried` scenario's four
contiguous blocks are replayed through a database closed and reopened between
each pair, and every block reproduces its *recorded* `block_id`,
`resulting_state_root`, and `transaction_root`.

**M3.13c delivered the version-seven application layer the same day.** ADR 0058
records it. `ApplicationV7` has version one's seven ABCI operations over the
version-seven kernel and store, and its whole safety argument is that
**`finalize_block` writes nothing**: it copies the durable head, executes the
block against the copy, and stages the root it produced, and `commit` replays
that block through the store and requires the store to reproduce exactly what was
staged. That equality is what makes the root a node *announced* and the root it
*persisted* one fact rather than two. The stage keeps the candidate root and
deliberately not the candidate state, because the root commits to every entry and
keeping the state would invite committing it instead of replaying the block.

**M3.13d delivered the version-seven transport the same day.** ADR 0059 records
it, and most of its decision is what it declines to add: **no new frame format**,
because the header and all five request payloads carry no ledger-version
meaning, and **no second connection loop**, because accepting, framing, and the
duplicate-request-identifier rule are properties of the wire. What version seven
adds is the response half — a finalized block carrying a block identifier version
one's does not, and receipts of version seven's fifty-six octets — and a
dispatcher. `UnixSocketServerV1::serve_connection` gains an overload, and the
`V1` in that name is the wire's version rather than the ledger's. **Every
response is validated on the way out rather than merely serialised**, because the
adapter on the other side has no ledger, no kernel, and no vectors and cannot
tell a wrong answer from a right one.

**A version-seven application now answers over a real Unix socket**, and the
recorded blocks were driven through one to prove it.

**M3.13e delivered the version-seven node process the same day.** ADR 0060
records it. `protocol-application-v7` reads a canonical genesis file, opens or
creates its store, binds a private Unix socket, and serves until `SIGTERM`; it is
checked as a **process**, started and connected to and shut down, against the
recorded chain identity and a genesis root read out of a recorded block header.
The piece that made it possible is `decode_genesis`, which is **defined as
`encode_genesis`'s inverse and checks itself against that claim** by re-encoding
what it read and requiring the octets back — so the validity rule is stated
exactly once, in the encoder, and a field read at the wrong offset is caught
along with everything else.

**M3.13f closed the two debts ADR 0057 recorded as owed**, and requirement 13's
own words are now met on the storage side: "through restart **and recovery**".
Everything before the commit rolls back and is an ordinary refusal that leaves
the store usable; only the commit can leave a head the process cannot name, and
there the store poisons itself and **reads the file again**, recovering to the
block's root or its predecessor's and never to anything between. **The process is
killed at both post-commit points by a re-executed child** and the parent must
find the committed block durable at its recorded root and continue the chain.
ADR 0057 is amended in place with the contract, which came out narrower than its
first text implied.

**M3.13g completed the structural stack on 2026-09-01.** `adapter/cometbft`
now reads a version-seven finalized block, bridges it to ABCI, and initialises a
home for a version-seven chain, so every layer between a signed transaction and a
consensus engine exists. **Its one real design question answered itself**:
`ApplicationV7` refuses a repeated `finalize_block` terminally, and CometBFT
v0.39.4 turns out never to ask — it replays an already-committed height
against a *mock* application built from its own saved response. The adapter
reconciles nothing and guards the case instead.

**A version-seven chain runs as of 2026-09-01.** M3.13h drove three
contiguous blocks — two registrations and a confirmed transfer — through a
real CometBFT process, with the engine required to report the state root the
independent Python model says each block produces, and the third block committed
by a process that did not execute the first two. **What made it possible was a
fixture that signs for real**: every recorded version-seven transaction carries
an eight-octet stand-in an oracle verifies by lookup, and a node runs
`ed25519_verifier()`, so nothing recorded could ever have been broadcast to one.

**One debt inside the stack now matters more than anything structural.** The
uptime schedule handed to `execute_block` is `nullptr`, so a chain driven
through this process writes **no cycle assignment record and accrues nothing to
any seat**. Every root in the evidence is the recorded one because the recorded
contiguous run opens no window — the stack executes blocks correctly and cannot
yet run a chain past a cycle boundary and mean it.

**A chain measures its own machines and pays one of them as of 2026-09-03.**
M3.13l gave `economy-transition-v8` its execution model and 434 execution
vectors. It is the first time in this repository that a node reward is derived
from evidence the chain itself recorded rather than from a schedule handed to
`execute_block`, and the recorded scenario is a whole 28,800-height window run
block by block: one machine answers all fifty-four audits it is issued and
writes no state at all, another answers none and fails its cycle, and the
assignment pays the first without anything anywhere being told the second was
offline. [ADR 0064](../decisions/0064-the-version-eight-execution-model.md)
records the one rule the model had to derive and three findings.

**Four independent replicas refused a transaction on 2026-09-11**, which is
the other half of requirement 13 and the first time anything in this repository
required a network to say *no*. Every four-node run before it was four replicas
agreeing about a **success**: every receipt in every integration carried a zero.
The deterministic-kernel argument rests on the opposite case — a wrong
transaction cannot change state because every replica independently refuses it —
and that sentence was untested because no wrong transaction had ever been
produced.

**Two are now, refused for two unrelated reasons.** A transfer at a consumed
nonce gives `NONCE_MISMATCH`, and a second purchase of seat 0 gives `REPLAY`. The
second is charged at the nonce the first did not consume, because a non-success
result performs no state write at all. Each is checked three ways: the receipt
carries the *named* code, because two defects both refuse and only one refuses
for the stated reason; the four replicas converge on one root and one
octet-identical receipt; and that root equals the one an empty block at the same
height would produce.

**A replay in the only form a running network can carry one.** The same bytes
broadcast twice never reach the application — CometBFT's mempool discards a
transaction whose hash it has seen — so a byte-identical replay is refused by the
mempool cache rather than by the kernel. A different amount at the same consumed
nonce has a different hash, passes the cache, is gossiped, proposed and
committed, and is refused by the layer the claim is about. **This is worth
knowing before any future replay test is written.**

**What makes the claim four-replica at all is that `check_transaction` refuses
almost nothing.** It rejects oversized input and that is all, so nearly every
refusal is an *execution* refusal: the transaction is admitted, committed in a
block, and refused independently by all four replicas. A transaction CheckTx
rejected would be refused by one node's admission filter, which is a much weaker
statement — `run_refused_transaction` fails closed on that case rather than
accepting it.

#### The per-slice delivery records moved out of this document

Every `How ... was delivered` record is now in
[`delivery-log.md`](delivery-log.md), moved there verbatim on 2026-09-14 because
this document had reached 8,140 lines and every session is instructed to read it
first. **Nothing was reworded, reordered, or dropped.** Read that document when
you need the history behind a claim here; read this one for what is true now.

### What works now

- **The repository compiles one economy contract, version nine**, as of
  2026-09-27 (ADR 0092). The bullets below that describe a version-eight
  network, kernel, store, or process record what version eight's stack did
  before it was deleted. None of them can be run now. What carries their
  evidence forward is version nine's own, and every figure version nine is
  measured against is pinned to version eight's accepted vector files, which
  stay.
- The completed M1 C++20 ledger processes canonical signed native transfers,
  exact nonces, and fixed fees while rejecting malformed, replayed,
  unauthorized, overflowing, and insufficient-balance transactions.
- SQLite persistence, atomic commit, restart, deterministic state roots, a
  stateless Go ABCI adapter, and pinned CometBFT operate as a reproducible
  four-validator local devnet.
- Independent Python differential testing covers at least 10,000 seeded
  sequences; GCC, Clang, sanitizer, bounded fuzz, single-node, and
  four-validator hosted verification passed on the last merged executable
  state.
- Accepted M2 research models cover native custody, escrow, claims,
  participation, bounded authority, economic stress, concentration,
  identity-split incentives, and minimum entitlements. Their schemas and
  results remain research evidence, not production Founder economics.
- The accepted `founder-economy-manifest-v2` contract represents the
  56,993,950,100-unit maximum as 5,699,395,010,000,000,000 eight-decimal atomic
  units, fixes a canonical ten-channel manifest at 2,267 JCS bytes with digest
  `84cca09865b6c62bf09d3f6bc3821a2527c7a4835652cffdc0ebefa34b314ce5`, and puts
  the referral in the direct-mint group at 250,002,000,000,000,000 atomic. Its
  strict loader enforces the eight ordered failure codes and rederives every
  product and subtotal.
- The accepted `founder-economy-manifest-v3` contract is version two with one
  channel identifier renamed — `mini_gamified_incentives` in place of
  `initial_mystery_box_incentives` — at 2,261 JCS bytes with digest
  `af153c99adf7c49e5a92563946cf0e60dfd7a58785462530988f661aa68faaa7`. Every
  founder-directed figure is version two's, and its table is derived from
  version two's rather than restated so a moved one could not be written. Both
  versions coexist and neither loader accepts the other's manifest.
  `economy-transition-v7` is the first contract to bind version three; every
  other simulator, transition model, and kernel path still binds version two,
  which remains correct against it.
- **The unreferred performance pool pays somebody.** As of 2026-09-16 a
  version-nine chain runs in Python across a month boundary, ranks a completed
  month on the uptime accumulated during it, writes the winner a claim, and lets
  that winner mint it with transaction kind 22. The pool has accrued since
  `economy-transition-v3` and **nothing had ever taken value out of it**. In the
  recorded trace one machine answers all 69 audits it is issued and the other
  answers none of its 75, February closes at the assignment of the window that
  opens March, and the whole balance goes to the better machine. A second
  scenario jumps the chain's stamps ninety days and one assignment closes a month
  while skipping three. **The settlement is Python only**: no C++ executes a
  version-nine transition, and no network can run one until the application
  contract can carry a timestamp.
- **A version-nine chain runs in C++20, and the unreferred pool pays somebody
  there too.** As of 2026-09-16 the whole version-nine kernel is in C++:
  `include/protocol/v9/economy.hpp` and `ledger.hpp` with twenty-two sources
  under `src/v9/`. The codec encodes every version-nine artifact — the 154-octet
  header and its re-versioned identifier, the 150-octet genesis with its
  timestamp, the four entry kinds and the widened unreferred pool, kind 22's
  body and the mint message it reuses, the state root that commits to the
  timestamp, the eight predecessor constructions, and `calendar-v1`'s derivation
  from a millisecond count to a calendar month. The ledger executes the timestamp
  rules, the six-step prologue, the monthly settlement and its single pass, and
  kind 22. Two ctest entries gate it: `economy-transition-v9-cpp` reproduces
  every contract vector that needs no chain, and
  `economy-transition-v9-execution-cpp` reproduces **all 125 execution vectors**
  over two chains of 115,200 and 144,000 heights. **What is still version
  eight's** is the application layer, the transport, the node process and the
  ABCI adapter — so no network can run version nine yet.
- **A version-nine chain survives the process that built it.** As of 2026-09-19
  the storage layer is version nine's. `protocol::storage::snapshot_v9` turns a
  whole version-nine state into canonical bytes — a 230-octet fixed part over a
  166-octet prefix that carries the head's timestamp beside its height, three
  restore gates, and a fuzz target — and `SQLiteLedgerV9` writes one to a file
  and reads it back. The store is version eight's with `apply_block` taking the
  agreed timestamp, a `current_timestamp_millis` column beside the height and
  the root, and three DDL literals pinned at the octet: genesis **150**, head
  snapshot **230**, block header **154**. Four ctest entries gate the pair.
  **The store applies C1 and C2 and never C5**: a store executes blocks the
  network already decided, so the proposal tolerance stays at `ProcessProposal`
  and this signature has no clock to give it.
- **A version-nine chain can be driven through an application, and it reads a
  clock in exactly one operation.** As of 2026-09-19 `ApplicationV9` runs the
  seven operations over `SQLiteLedgerV9`: `process_proposal` returns an
  eight-value decision under a zero status and is the only operation that reads
  the bound clock, `finalize_block` applies C1 and C2 through an entry point that
  takes **no clock argument**, and `commit` replays the staged block with its
  staged stamp. The suite drives the recorded four-block run through
  propose-finalize-commit across three real restarts and **counts** the clock:
  every operation but `process_proposal` must leave the count where it found it.
  **No engine drives it yet** — the node process and the ABCI adapter are still
  owed — so this is a driveable application rather than a running node.
- **A version-nine application answers version-two frames on a socket.** As of
  2026-09-21 `response_v9` and `dispatcher_v9` turn `ApplicationV9`'s answers
  into version-two frames, and `UnixSocketServerV1::serve_connection` has a
  version-nine overload that reads them. Info and Commit report the durable
  **timestamp**, a proposal answers a `decision:u8`, and statuses `7` and `8` are
  written by a function that **takes no kind**, so they cannot be written for
  anything but a finalize. `version-nine-transport` drives the recorded
  four-block run over frames and a real socket and counts the clock over the
  wire. `wire_v2`'s request decoder, delivered on 2026-09-19, is what the socket
  reads, and **each version's socket refuses the other's frame at the header**
  with nothing written.
- **A version-nine node process runs against the platform clock.** As of
  2026-09-21 `protocol-application-v9` puts the store, the application, and the
  version-two socket in one process and binds `CLOCK_REALTIME` in milliseconds.
  It reads the clock before opening anything and refuses to start without one,
  and a clock that stops being readable stops the process rather than voting on
  an assumed value. `--genesis-identity` prints the genesis stamp beside the
  chain identity and the height-zero root. `version-nine-headless-process`
  starts it six times. Against the real clock, the recorded January block is
  behind the tolerance and 2100 is ahead of it, while FinalizeBlock accepts
  January; the stamp survives a restart; and one millisecond of stamp moves an
  empty block's root. **Since M3.20j it also reaches both clock-failure paths**
  through the clock-offset shim. With no readable clock the process exits before
  creating a database or a socket. Moved onto January, it accepts the January
  stamp. When its clock becomes unreadable under it, the next proposal stops it
  nonzero and leaves the store at genesis.
- **The Go adapter's local client speaks version two.** As of 2026-09-21
  `localapp.ClientV9` writes and requires version-two frames. It carries the
  stamp in InitChain, ProcessProposal and FinalizeBlock, and reads Info's and
  Commit's stamp, a `Decision` octet, and version-nine receipts. It admits
  statuses `7` and `8` only on a finalize and treats either anywhere else as a
  protocol failure. The frame version is a field of the client, so versions one
  and eight are unchanged.
- **The bridge drives version nine.** As of 2026-09-21 the bridge carries the
  engine's time into InitChain, ProcessProposal and FinalizeBlock.
  `bridge.LocalV9` converts it by `consensus-application-v2`'s rule — checked,
  three refusals, block times truncated, genesis times exact, a stamp past the
  calendar passed through — and votes ACCEPT only on decision `0`. A rejection
  is logged by the decision's name. `protocol-cometbft-bridge
  --protocol-version 9` dials it.
- **A CometBFT home can be initialised for version nine.** As of 2026-09-22
  `protocol-cometbft-init -protocol-version 9 -genesis-timestamp <millis>` and
  `protocol-cometbft-devnet start -protocol-version 9` write
  `"protocol-stack-v9"` and a `genesis_time` that is the canonical stamp at
  exactly millisecond precision, and refuse an existing genesis that differs in
  it. The devnet reads the stamp from the application's identity mode and
  requires exactly the keys the version prints, so the wrong binary for the
  version is refused before a home exists.
- **A version-nine chain runs under one CometBFT node.** As of 2026-09-24
  `cometbft_version_nine_test.py` mints a genesis stamped with the current time.
  It commits six blocks through a real node, restarting it after the third, and
  compares every receipt, root, header hash and block identifier with the Python
  model. The model derives each from the header time the engine committed.
  Block 1 carries the genesis stamp to the nanosecond. Block 3 is one the engine
  closed with no transaction, and its root is the model's for its height and
  stamp alone. `version-nine-chain-fixture` checks the fixture's own contract in
  under a second.
- **A four-validator version-nine network runs, restarts, and audits its stamp.**
  As of 2026-09-24 `cometbft_four_validator_v9_test.py` runs version eight's
  scenario over version nine: two registrations, a seat bought and activated,
  five confirmed transfers, and two named refusals, through four nodes. It
  covers two full restarts, a driven replica, and a departure and return.
  Every height the network closes is computed by the model from its committed
  stamp. Every stop is followed by an audit that reads each store's durable
  height, **stamp**, and root through an independent C++ process. The driven
  replica refuses a block two heights ahead as a sequence failure, and a stamp
  below its head as status `8`, and its store is unchanged afterwards.
- **A version-nine network carries on around a replica with a wrong clock.** As
  of 2026-09-24 `cometbft_skewed_replica_v9_test.py` preloads
  `libprotocol-clock-offset.so` into replica 3's application only, through the
  devnet's new `-application-env`, and moves its clock three times while the
  network runs. At 120 s ahead it names `TIMESTAMP_BEHIND_TOLERANCE`; at 120 s
  behind, `TIMESTAMP_AHEAD_OF_TOLERANCE`; corrected, nothing. Which heights each
  clock governed is read from the replica's own committed height. The three
  correct replicas never vote against a proposal. The chain commits throughout,
  and all four keep the model's root and pass the durable audit. A block the
  skewed replica proposed is committed. Two of the four transactions enter
  through it.
- **A four-node version-eight network refuses a transaction, and all four
  replicas refuse it identically.** As of 2026-09-11 two transactions the
  contract must reject — a transfer at a consumed nonce and a second purchase of
  an owned seat — are committed into blocks, executed independently by four
  CometBFT-driven replicas, and refused by each with the same named result code,
  the same octet-identical receipt, and one converged state root equal to what an
  empty block at that height would produce. It is the first evidence in this
  repository for the claim the whole deterministic-kernel argument rests on.
  **What is still untested is a replica refusing a peer's whole block**, which is
  a different refusal class and needs a driven `ApplicationV8` beside the network.
- **A four-node version-eight network sells and activates a Founder Seat.** As
  of 2026-09-11 the two transitions that write the seat table — kind 2
  `purchase_seat` and kind 3 `activate_seat` — are executed by four independent
  CometBFT-driven replicas, after a full restart, with every replica's durable
  head required to match the independent Python model's root. Five transactions
  enter through four different nodes. **It does not exercise the uptime audit**
  and no document here may say it does: a seat is in scope only from the window
  after the one it activated in, so a devnet begun at genesis is 28,800 heights
  short of its own seat's first audit. ADR 0071 records that, and two fixture
  checks derive it rather than restating it.
- **A version-eight chain measures its own machines and pays one from that
  measurement, in Python.** `simulation/economy_transition_v8/` runs the four
  ordered steps — the prologue that derives a window's schedule from state, the
  issue step that audits every in-scope seat against the previous state root, the
  transactions, and the expiry step that clears a slot bit for a challenge nobody
  answered — and `test-vectors/economy-transition-v8-execution.txt` records 434
  vectors over four scenarios reaching all sixteen kinds. A whole 28,800-height
  window is executed block by block in each. **The C++ kernel now runs the same
  contract** — the bullet below — `snapshot_v8` can write its state down, and
  `SQLiteLedgerV8` makes that state survive the process that produced it, while
  the application, transport, node process, and adapter all still name version
  seven.
- **A version-eight chain runs in C++20 as of 2026-09-05, and it measures its
  own machines.** `src/v8/` compiles the whole contract: the ledger, the four
  ordered block steps, both new transitions, the schedule derivation, and the
  six added invariants. `economy_v8_execution_tests` reproduces every one of
  `test-vectors/economy-transition-v8-execution.txt`'s 434 vectors and the 62
  contract vectors a ledger is needed for. In the recorded `measured` scenario
  one machine answers all fifty-four audits the chain issues it across a whole
  28,800-height window and writes no window record at all, another answers none
  of its fifty-two and fails its cycle, and the window's assignment pays the
  first — **with nothing anywhere told that the second was offline**. At that
  date every layer above the
  store was still version seven's — the application, the transport, the node
  process, and the adapter — and all four were version eight's by M3.13s and
  version seven's were deleted by M3.13t.
- **The version-eight byte and derivation surface compiles in C++20 as of
  2026-09-04.** `src/v8/` and `include/protocol/v8/economy.hpp` hold the
  envelope with its sixteen bodies, the six HUB messages and the dispute
  message, challenge selection, the economy state key space with entry kinds 18
  and 19, the economy tree and the version-eight state root, genesis with
  `dispute_authority_key` at a 142-octet prefix, the receipt at version 8, and
  the result-code space at 45. `economy_v8_codec_tests` reproduces the 121
  vectors of `test-vectors/economy-transition-v8.txt` a codec can derive.
  At that date **nothing executed a version-eight transition** — no ledger, no
  block steps, no transitions, no schedule derivation — and every layer above
  the kernel still named version seven. M3.13o supplied the execution and
  M3.13p through M3.13s the layers.
- **A version-eight state can be written down and read back, as of
  2026-09-05.** `protocol::storage::snapshot_v8` encodes a whole version-eight
  `Ledger` to canonical bytes and restores it to a ledger that keeps executing,
  including the uptime carrier's two entry kinds — which it carries **raw**,
  because the ledger holds them raw and a typed shadow would be a second
  encoding of the key space the two version-eight transitions write.
  `dispute_authority_key` rides in the prefix beside `verifier_key`, taking it
  from 126 octets to 158, and joins the restore parameters: unlike the verifier
  key it has no second copy in the payload, so that comparison is the whole of
  what stops a restored node answering to a different dispute authority than its
  peers. Each of the four recorded scenarios is snapshotted, restored,
  re-encoded, and required to reproduce its *recorded* `final_state_root`.
- **A version-eight state survives the process that produced it, as of
  2026-09-06.** `protocol::storage::SQLiteLedgerV8` executes a block against a
  candidate copy of the durable head and commits the new head and the block row
  in one exclusive transaction, or leaves both heads exactly as they were. The
  `carried` scenario's four contiguous blocks are replayed through a database
  **closed and reopened between each pair**, and every block reproduces its
  *recorded* `block_id`, `resulting_state_root`, and `transaction_root`. A fault
  anywhere in the write path leaves the durable head at the pre-block root or
  the post-block root and never at anything between, including when the process
  is **killed** between the commit and the publication.
- **A version-eight chain can be driven by a consensus engine, as of
  2026-09-06.** `protocol::application::ApplicationV8` answers the seven ABCI
  operations over `SQLiteLedgerV8`: `finalize_block` copies the durable head,
  executes in memory, writes nothing, and stages what it produced; `commit`
  replays that block through the store and requires the store to reproduce
  exactly what was staged; any refusal once the chain is ready is terminal. The
  `carried` scenario's four contiguous blocks are driven through all seven with
  the application **rebuilt from the file between each pair**, and again as
  request and response frames over a real Unix socket. **There is no
  version-eight wire**: `wire_v1` decodes every request for both versions, so
  version eight adds a response encoder, a dispatcher, and a third
  `serve_connection` overload. **`ApplicationV8` takes no uptime schedule**,
  which closes ADR 0058's owed item rather than satisfying it — the prologue
  derives the schedule, so a chain driven entirely through this layer now writes
  cycle assignment records and accrues to seats where version seven's wrote
  none.
- **A version-eight chain runs under a real consensus engine, as of
  2026-09-07.** `protocol-application-v8` reads a canonical 142-octet genesis,
  opens or creates its store, binds a private Unix socket at mode 0600, and
  serves until `SIGTERM`; `--genesis-identity` prints the two figures an
  operator configures. `ClientV8` reads a version-eight finalized block over
  version one's frames and `bridge.NewV8` turns it into ABCI responses under the
  `protocol-stack-v8` codespace. `tests/integration/version_eight_chain.py`
  signs for real, and three contiguous blocks — two registrations and a
  confirmed transfer — are broadcast to a CometBFT v0.39.4 node and committed,
  with the third committed by a process that did not execute the first two.
  **Four independent replicas agree on those roots through a full restart**,
  with three transactions entering through three different nodes and all four
  databases opened directly after every stop. **The chain sells no seat**, so
  the issue and expiry steps evaluate nothing: what runs under the engine is the
  version-eight code path at every height, not the audit it would perform.
  **Nothing in the repository is version seven's any more**: step 7 landed on
  2026-09-09 and one stack remains.
- The accepted `economy-transition-v7` contract is version six with the
  per-channel carry deleted from state and replaced by a recovery pool. Its
  independent Python model runs the respecified settlement — a zero-winner
  cycle contributing its whole base permission, an indivisible remainder
  contributing its dust, and the earliest subsequent cycle with any winner
  taking the pool entire on top of its own reallocation — and checks two
  conservation identities after every cycle and every mint:
  `issued(c) + outstanding(c) = assigned * leg(c)` and
  `outstanding(c) = claimable(c) + recovery_pool(c)`. The second is the
  statement that 100% of the node distribution is assigned, and it is an
  equality rather than a bound.
- **`simulation/economy_transition_v7/` also executes that contract.** It holds a
  version-seven ledger carrying the recovery pool where version six's holds ten
  carries, dispatch over the fourteen kinds — thirteen of them version six's own
  function objects — and ordered block execution that writes the 64-octet cycle
  assignment record at a window boundary before the block's transactions, charges
  the fixed fee, advances the escrow's nonce, produces one 56-byte version-seven
  receipt per admitted transaction, and commits a state root, a transaction root,
  a 146-byte header, and a block ID. Three recorded scenarios carry a pool from a
  cycle nobody won to a mint that collects it, run the rejected block ordering
  against the accepted one on identical inputs, and pay a machine past its own 731
  issuance cycles out of a cycle with no contributing seat at all.
  `test-vectors/economy-transition-v7-execution.txt` fixes 590 vectors over five
  scenarios that execute **all fourteen transaction kinds** — where version six's
  execution file reaches eleven — and twelve mutation probes establish that the
  verifier fails closed. **The pool
  scenario ends with `outstanding` at zero and the pool at zero on every Founder
  Node channel**, which is the first end-to-end demonstration that 100% of what
  the manifest promised for those cycles reached a beneficiary. It is still Python
  and it activates no chain.
- The `founder-economy-simulator-v2` model executes that contract. It runs seat
  activation, base permission evaluation, unconditional referral accrual, atomic
  exercise, and capped direct issuance with deterministic trace, state, and
  result digests. A cycle is met at 64,800 seconds of cumulative fully
  operational uptime, checked in both of the constitution's stated forms; the
  failed-cycle winner set is the highest uptime among seats that met the same
  window, split equally with the remainder carried; an empty winner set carries
  the whole portion. A window's record is bound by digest on first reference, so
  the window's uptime is one fact for a run rather than a per-event opinion. It
  is research software and activates nothing.
- A complete 731-cycle single-seat run reproduces the v2 per-seat schedule
  exactly, including 25,000,200,000,000 Founder-operator, 12,500,100,000,000
  venture-escrow, and 2,500,020,000,000 unreferred-pool atomic units.
- The accepted Founder Economy manifest exactly represents the
  55,743,940,100-unit maximum as 5,574,394,010,000,000,000 eight-decimal atomic
  units, fixes a canonical ten-channel manifest and digest, and proves every
  per-cycle, per-seat, and complete-population supply product without
  activating it. That maximum is the superseded v1 figure; the constitution now
  directs 56,993,950,100.
- The independent Founder Economy simulator executes that contract. It loads
  the manifest under the ordered failure codes, tracks per-channel issued and
  outstanding amounts with checked `u64` arithmetic, and runs seat activation,
  base and referral permission evaluation, atomic exercise, and capped
  direct-channel issuance with deterministic trace, state, and result digests.
  It is research software and activates nothing. Its referral transition is
  superseded: a referral is now unconditional and direct-mint.
- The Founder Seat sale model derives the complete constitutional price
  schedule and runs the full 100,000-seat sale end to end to exactly USD
  4,231,855,000, enforcing the 100,000-seat capacity and the 1,000-seat
  per-principal bound at their boundaries. It models the sale only; a purchased
  seat is not yet an activated seat.
- The revenue routing model splits a native commercial payment 45/45/10, halves
  the creator share for the 22.5/22.5 product-creator case, routes the floored
  shares' remainder to the Founder pool under a bound proved by exhaustive scan
  of all 200 residues, routes 100% of a transaction fee to a separate Founder
  fee pool, and distributes both pools per accounting cycle over a bound
  active-seat snapshot while carrying each residue forward. It creates no
  native units and routes value a constitutional channel already issued.
- The escrow payout model holds the three founder-directed escrows separately,
  takes opening custody from a recorded `founder-economy-simulator-v1` state by
  recomputing that model's digest, and releases value only through a capability
  bound to exactly one escrow and bounded by a per-payout maximum, a cumulative
  envelope, an expiry, and revocation. Each escrow conserves independently, and
  a second capability-side account of the same value must agree. It creates no
  native units: custody is fixed at the bind and non-increasing afterwards.
- The scenario suite runs those four models at multi-year scale. Three seats
  staggered 61 ticks apart each complete all 731 cycles with disjoint inactive
  cycles and performance reallocation; exactly 100 principals at the 1,000-seat
  bound absorb the whole 100,000-seat capacity; 122 routing cycles change their
  active population every cycle, 25 of them empty; and every escrow is drained
  and every envelope exhausted against custody the population run itself issued.
  Restart equivalence holds under prefix replay and split resume, and seeded
  property tests assert each model's conservation equations against its
  published results rather than its recorded totals.
- The escrow payout model implements two accepted contracts. `escrow-payout-v2`
  binds `founder-economy-simulator-v2` and differs from version one in exactly
  six strings; a state recorded under either economy version is rejected by the
  other's bind with `INVALID_RESEARCH_INPUT`, derived in the vectors rather than
  asserted. Both versions' transitions are identical, which the two runs' equal
  trace codes prove.
- The scenario suite runs under either binding. `economy-scenario-suite-v2`
  reruns all four scenarios against the revised economy: a complete 731-cycle
  staggered population run with derived activity and derived performance
  winners, the 100,000-seat concentrated sale, 122 routing cycles, and an escrow
  drain bound to the v2 population run's own state digest. The referral channel
  is consumed exactly by its two destinations — 5,000,040,000,000 atomic units of
  referrer custody plus a 2,500,020,000,000 unreferred pool equal its whole
  issuance — and the performance carry ends at zero.
- The cycle boundary model holds a seat activation table and answers whether a
  supplied window is the window for a supplied cycle index. A cycle is 28,800
  block heights on one global grid shared by every seat, a seat's 731 cycles are
  the 731 consecutive windows beginning after its activation height, activation
  heights may not decrease, and a wrong window yields three distinct codes for
  before the span, after it, and inside it but attached to another cycle. It
  derives no measurement and no economy model is bound to it yet.
- The uptime measurement model turns evidence into a finalised record. It
  subdivides a window into 24 one-hour slots, credits a slot only when every
  assigned duty in it was performed and every challenge issued in it was answered
  correctly and on time, selects challenges from a beacon no participant can
  compute before the block commits, applies bounded Ecosystem AI disputes that
  can only subtract, finalises by expiry without any signature, and emits the
  `cycle_uptime_record` shape `founder-economy-simulator-v2` accepts unchanged. It
  observes no real machine: the challenge protocol is defined and the challenge
  content is not.
- The escrow payout model implements three accepted contracts. `escrow-payout-v3`
  binds `founder-economy-simulator-v3` and differs from version two in exactly six
  strings; a state recorded under any one economy version is rejected by both
  other binds, derived in the vectors against each predecessor separately rather
  than asserted. All eighteen strings across the three bindings are distinct.
- The `founder-economy-simulator-v3` model enforces what the two preceding slices
  only defined. A seat records the activation height its 731-window schedule is
  derived from; a base permission is rejected when its `cycle_window` is not the
  window the accepted grid assigns to its `cycle_index`, with the three codes
  `cycle-boundary-v1` distinguishes; and an uptime record is rejected when its
  seat set is not exactly the window's in-scope set, in either direction. It
  reuses the accepted v2 manifest and the accepted window grid rather than
  holding a copy of either, and refuses to run at all if they have drifted. It is
  research software and activates nothing.
- The scenario suite runs under all three bindings. `economy-scenario-suite-v3`
  reruns every scenario against the enforced schedule: each seat carries the
  activation height its 731 windows are derived from, every record covers exactly
  its window's in-scope set, and one early window reaches the founder-directed
  empty-winner rule with a complete population rather than in a unit test. The
  performance carry survives that window and still ends at zero. Scenarios 2 and
  3 record byte-identical values under all three versions.
- Every simulation test, every executable vector verifier, every recorded vector
  file, and every `tests/tools` module is reachable from a registered `ctest`
  entry, and every simulation test runs the way `ctest` invokes it.
  `tests/tools/test_registration_test.py` enforces all of that, and it is now
  registered itself, so it runs on both verification paths rather than only the
  lightweight one. Until 2026-08-12 it ran only when the scope classified
  `lightweight`, which excluded every pull request able to add an unregistered
  entry.
- The hosted test phase runs concurrently at `nproc` jobs, and no two registered
  entries are handed the same path under the build directory, which is checked
  statically rather than left to an intermittent race.
  `PROTOCOL_STACK_TEST_JOBS=1` restores serial execution.
- `economy-transition-v2` is the accepted consensus surface the economy must be
  implemented against. It fixes a shared transaction envelope whose kind-1
  instance reproduces the accepted M1 transfer byte-for-byte; five new kinds —
  purchase, activate, mint node, mint referral, and direct issue; the biometric
  verifier signature that gates entry and never payment; the per-cycle assignment
  the chain writes at a block boundary; the economy state key space; version-two
  genesis and chain identity; the state-root extension; a 56-byte receipt; and a
  flat 21-code result space whose first nine are version one's frozen meanings.
  It is a contract for an implementation that does not exist: no C++ executes it.
  Kind 6 is specified and refused, because direct-channel eligibility is the one
  authorization predicate still founder-reserved.
- The codec model in `simulation/economy_transition/` encodes and decodes every
  kind, derives every state key, computes the economy tree and both state roots,
  encodes the receipt, derives a cycle's winner set, and splits every leg of a
  failed cycle's permission. It implements no cryptographic primitive: a
  signature is carried as recorded bytes and never computed. Its verifier derives
  the version-one transfer twice from two different shapes and checks both
  against the accepted `protocol-primitives-v1` vectors.
- `economy-transition-v3` is the accepted consensus surface the C++ kernel must
  be implemented against, and it supersedes version two as the implementation
  target. It adds four transaction kinds — a biometrically approved mint, the
  per-seat protection switch, manager addition, and HUB verification — three
  state entry kinds, three result codes, and six domain-separated verifier
  messages. Any recorded manager may act for a seat and receives what it mints; a
  seat may require a fresh biometric approval to mint, and removing that
  requirement itself needs one; unminted permissions are capped at thirty windows
  and the excess reallocates to the cycle's best performers by the same path a
  failed cycle takes; and a named referrer must hold a HUB registration. The
  kind-1 byte identity, the shared envelope, the admission order, the genesis
  field table, the receipt layout, and result codes 0 through 20 are unchanged.
  Kind 6 is still specified and refused.
- `economy-transition-v6` is the accepted consensus surface the C++ kernel must
  be implemented against. A verified identity is the root of every account, a
  keyless escrow is where value sits, and a revocable signer assigned to exactly
  one escrow is who may act on it; an escrow's balance and nonce stay in the
  version-one account map, so a version-six state is a version-one state plus an
  economy map. Registration is fee-exempt and creates the identity, escrow zero,
  the first signer, and the entry airdrop in one atomic execution. A Founder Seat
  has no address and a mint names a destination escrow the chain checks. A
  transfer refuses an unregistered recipient, which withdraws
  `ledger-transition-v1`'s recipient-creating transfer and makes **every account
  is an escrow** a structural invariant. The signature-scheme byte carries a
  second authorization mode so that identity administration works with no key at
  all, and admission still verifies a signature without reading state. It has a
  model, 462 vectors, a verifier, and 91 tests; **what it does not yet have is
  the C++ implementation**, which still targets version four.
- **`economy-transition-v6` also executes, in Python.** The same package now
  holds a version-six ledger state, escrow resolution under both authorization
  schemes, the shared envelope checks, the fourteen transitions in their
  specified rejection orders, and ordered block execution that writes a cycle
  assignment at a window boundary, charges the fixed fee, advances the escrow's
  nonce, produces one 56-byte receipt per admitted transaction, and commits a
  state root, a transaction root, a 146-byte header, and a block ID. A recorded
  six-scenario trace walks registration and its entry airdrop, a forfeiting
  verified-user collection thirty windows later, the millionth-and-first user,
  recovery with no signer at all, the accepted version-one transfer admitted and
  refused for its recipient, both directions of a posture change, and a mint that
  collects the cycle the block it is in just assigned.
  `test-vectors/economy-transition-v6-execution.txt` fixes 512 vectors over it
  and five mutation probes establish that the verifier fails closed. It is still
  Python that activates nothing; what changed is that the evidence is now about
  transitions rather than about bytes.
- `economy-transition-v5` is accepted, fully evidenced, and superseded as
  direction hours after it was evidenced. It is version four with one field's
  meaning corrected — kind 11's 32-byte field is the HUB identity hash and the
  account being linked is the sender — because version four's kind 11 names an
  identity it does not carry and therefore cannot be implemented. Its model, 550
  vectors, and verifier remain in place and passing. No C++ was ever written
  against it, which is the precedent working rather than failing.
- `economy-transition-v4` is accepted, fully evidenced, and superseded in one
  place. HUB verification is the root of identity: a
  registration records the person's own public key and the ecosystem verifier
  signs registrations and nothing else; a person holds a set of up to 16
  addresses and manages it themselves; a seat is owned by a person rather than
  an address, so losing every address does not lose the seat; HUB signing is
  what adds a seat address, and seat addresses stay permanent and add-only;
  referral earnings are keyed by identity; self-referral is compared between
  people; and the constitution's 1,000-seat-per-human bound is enforced. The
  kind-1 byte identity, the shared envelope, the admission order, the genesis
  field table, the receipt layout, result codes 0 through 23, and the whole
  settlement carry over. Kind 6 is still specified and refused.
- **Version seven's codec is gone from the kernel and its Python evidence is
  intact.** `src/v7/`, `include/protocol/v7/`, and the version-seven storage,
  application, transport, and node sources are removed by ADR 0070, restoring
  ADR 0046's rule that the kernel compiles exactly one economy contract;
  `simulation/economy_transition_v7/`, both accepted version-seven vector files,
  their verifiers, and their eight CTest entries remain in place, passing, and
  unedited. **`economy-transition-v8-cpp` still reads
  `economy-transition-v7.txt`**, because version eight's predecessor
  constructions are pinned against it.
- **Version six's codec is gone from the kernel and its Python evidence is
  intact.** `src/v6/` and `include/protocol/v6/` are removed under ADR 0046's
  rule that the kernel compiles exactly one economy contract;
  `simulation/economy_transition_v6/` and both accepted version-six vector files
  remain in place, passing, and unedited.
- **Version four's codec is gone from the kernel and its Python evidence is
  intact.** `src/v4/` is removed, because it implemented the one economy
  contract already known to have no conforming implementation;
  `tools/economy-transition-v4-vectors/` still verifies its 441 vectors.
- The model in `simulation/economy_transition_v4/` encodes and decodes all
  twelve kinds, builds all eight HUB messages, derives every state key, computes
  the economy tree and all four versions' state roots, encodes the receipt, and
  runs the HUB registry with its two counts. It imports version three's
  settlement rather than copying it, and the vectors require the record it
  writes to equal version three's recorded bytes exactly.
- The codec-and-settlement model in `simulation/economy_transition_v3/` encodes
  and decodes all ten kinds, builds all six verifier messages, derives every
  state key, computes the economy tree and all three versions' state roots,
  encodes the receipt, derives a cycle's assignment under the cap, and walks a
  bounded mint. It implements no cryptographic primitive. Its verifier derives
  every value twice — structurally for the compatibility claim and behaviourally
  for the settlement — and fails closed on a tampered value, a missing key, and
  an invented key alike.
- The one-word `proceed`, `conclude`, and `status` workflows reconstruct,
  deliver, and report repository state. `proceed` runs an explicit
  founder-decision gate before starting a slice and reports its result whether or
  not anything is reserved.

#### The version-eight stack records moved out of this document

They are in [`delivery-log.md`](delivery-log.md), in its second section,
verbatim.

### Adopted founder direction

- **The ecosystem AI runs on the Founder Machines and the company runs no
  backend.** Directed 2026-08-19, reversing the original placement of one
  ecosystem AI on company data centres. Every machine serves an open-weight
  model continuously; a judgment is made by the machine nearest the requester
  after reading the reasoning of up to six nearest neighbours, seven models in
  total; each identity has one personal assistant whose parallel live sessions
  equal its seat count. The company operates no server or hosted service of any
  kind, from the beginning, and buys seats where it needs capacity.
- **HUB verification is local, deterministic, and sandboxed on the founder's own
  machine**, with the local model as the process's integrity monitor rather than
  its verifier — it never decides identity, and it may dispute a run and force
  re-initialization. The single genesis verifier key becomes a registry of
  per-machine attestation keys.
- **An initialization stage of roughly one to two years** in which the company
  fixes the model, framework, protocol, and update schedule, after which a
  self-improving model is deployed and everyone including the company renounces
  total control. A founder never chooses the model or framework at any point.
- **The Founder Machine specification is founder-directed**: an x86_64
  Xeon-class server tier of 8 vCPU, 64 GiB, 1 TB NVMe, 12.5 Gbps, and
  **separately 512 GB of unified memory** for the model. Renting is permitted
  and expected early. Every seat eventually receives the same machine, funded
  from pooled proceeds, distributed in stages as the ecosystem grows.
- **A month is a real calendar month beginning on the 1st**, read from the
  consensus timestamp in the block header rather than counted in cycles.
- **731 cycles bound the native asset distribution and nothing else.** Machines
  keep operating, keep being ranked, and remain eligible for every pool after
  their own distribution ends; the best-performer mechanism never deprecates.
- **Bridges run on Founder Machines** with their own light clients and a machine
  quorum attesting inbound value. No third-party endpoint is ever in the path.
- Channel 9 is `mini_gamified_incentives`; the name "mystery box" is retired
  everywhere.

- One native asset with an intended fixed maximum of 56,993,950,100 display
  units and no burn, secondary internal currency, or public asset creation. The
  maximum was raised from 55,743,940,100 on 2026-08-07, before any issuance, to
  fund the doubled referral channel; it becomes immutable at genesis.
- Exactly 100,000 permanent biometric Founder Seats, all-in-one Founder Nodes,
  731-cycle issuance, fixed allocation channels, 45/45/10 commercial routing,
  and 100% Founder transaction-fee routing.
- A cycle is met at 18 hours or more of cumulative fully operational uptime,
  where fully operational means every node component healthy at once. The
  6-hour grace allowance is cumulative and fragmentable.
- A failed cycle's whole 574.3-unit permission goes to the highest cumulative
  uptime in that same cycle, shared equally among exact ties, restricted to
  seats that met the cycle, with the integer remainder and any zero-winner
  cycle's whole permission going to the **recovery pool**, which the earliest
  subsequent winning cycle takes entirely. Revised on 2026-08-19; the remainder
  previously carried forward per channel in a carry nothing ever released. It settles at the winner's mint rather than at a mint the failed seat
  may never make, which is the 2026-08-13 revision of the constitution's original
  "when the failed seat next exercises a permission".
- The Founder referral benefit is 34.2 units per cycle, unconditional, and a
  direct-mint channel capped at 2,500,020,000. A seat bought without a recorded
  referrer routes its allocation to a monthly unreferred performance pool, so
  the channel is consumed exactly. A referrer must be HUB verified.
- A seat is controlled by a recorded set of at most 16 manager addresses rather
  than by one purchase address, a mint credits the address that signed it, and
  minted value is spendable immediately with no withdrawal step. A founder may
  require a fresh biometric approval on every mint; switching that on needs only
  an address signature and switching it off needs a biometric approval. A seat's
  addresses are permanent and add-only, and **HUB signing is what adds one**, so
  a founder who has lost every key still has a path back.
- Unminted permissions accumulate for at most thirty cycles after the last
  collection. Past that, **a cycle a seat cannot collect is a cycle it failed**:
  the day's generation goes to the best performers, and the full seat is not one
  of them, because a failed seat never rewards another failed seat. What the seat
  has already earned is untouched, and one collection restores both the room and
  the eligibility. The same bound applies to a referrer's accrual, whose
  forfeited value routes to the unreferred pool. It is a collect-or-lose rule
  rather than a penalty: an unminted permission's units do not exist and are not
  circulating.
- **HUB verification is the ecosystem's recovery layer as well as its identity
  layer.** It survives the loss of any address, so a registered person can always
  sign back in, and a verified person may add and remove their own addresses
  through it. Founder Seat addresses are the stated exception: add-only, never
  removed.
- Buying a Founder Seat requires HUB verification first, and the seat is tied to
  that identity. One human may hold at most 1,000 seats, which the chain now
  enforces because it can finally tell that two addresses are one person.
- Uptime reaches consensus without trusting self-reports: validator duties are
  derived on-chain, resource provision is proved by challenge-response, and the
  Ecosystem AI holds a bounded dispute window rather than a signature that
  could freeze payment.
- One logical Ecosystem AI outside consensus, with separately bounded
  biometric, moderation, project, treasury, and developer-program capabilities.
  It runs on the Founder Machines rather than on company infrastructure as of
  2026-08-19; a judgment is made by the machine nearest the requester after
  reading up to six neighbours' reasoning.
- AI-approved controlled full-stack applications, one project creator plus at
  most one product creator, immutable accepted history, and Founder-only
  resource infrastructure.
- BTC, ETH, and approved stablecoins restricted to Founder Seat purchase,
  liquidity, native swaps, and withdrawal; they never become general internal
  balances.

These are target requirements, not runnable Founder behavior. Issue #71 added a
specification, JSON manifest, and fixed vectors; issues #77, #79, #82, and #85
each added a specification, ADR, Python model, vectors, and verifier for part of
them; issue #88 added a specification, ADR, deterministic generators, vectors,
and verifier that exercise all four at multi-year scale. Issue #99 restated the
contract under the revised direction and issue #103 made that restatement
executable. None changed current transaction bytes, C++ state, devnet supply,
previously accepted simulator schemas, bridge, wallet, AI, biometric, or resource
behavior.

### Repository state

- Repository: `kaikisegfault/protocol-stack`.
- Issue #310 and PR #311 are the M3.18b delivery, merged by rebase as `52065a1`
  and `7dabe5d` on 2026-09-16. Two commits, eighteen files, **5,202 insertions
  and 14 deletions**: `include/protocol/v9/ledger.hpp`, ten sources and one
  internal header under `src/v9/`, four test translation units and one test
  header under `tests/kernel/`, `CMakeLists.txt`, and the specification's status
  line. **No accepted vector file, specification rule, manifest, encoding, or
  existing kernel source changed**, and `src/v8/` is untouched.
  `tools/verification_scope.py` classifies it `full`. **The first candidate
  `6ba82a3` failed both GCC presets** on `-Werror=dangling-reference`, a GCC 13
  warning this machine's GCC 12 does not have and both Clang presets accepted;
  the repair is `7dabe5d` and candidate run 35159501140 on that exact head passed
  all five jobs, with **170** ctest entries in the debug presets and **178** under
  `clang-sanitizers`, one more than M3.18a because the slice adds exactly one
  entry, `economy-transition-v9-execution-cpp`.
- Issue #307 and PR #308 are the M3.18a delivery, merged by rebase as `4c46e56`
  on 2026-09-16. One commit, twenty-five files, **5,604 insertions and 7
  deletions**: `include/protocol/v9/economy.hpp`, twelve sources and one internal
  header under `src/v9/`, six test translation units under `tests/kernel/`,
  `CMakeLists.txt`, the specification's status line, and the two files of
  `tools/economy-transition-v9-vectors/` that record the added root section.
  **`test-vectors/economy-transition-v9.txt` is the one accepted vector file that
  changed**, and it changed additively: 213 vectors become 239, with one boolean
  renamed for the count it establishes. No specification rule, manifest,
  encoding, or existing kernel source changed, and `src/v8/` is untouched.
  `tools/verification_scope.py` classifies it `full`. Candidate run 35152873997
  on the branch head passed all five jobs, with **169** ctest entries in the
  debug presets and **177** under `clang-sanitizers`, one more than M3.17c's 168
  and 176 because the slice adds exactly one entry, `economy-transition-v9-cpp`.
- Issue #283 and PR #284 are the M3.14e delivery, merged by rebase as
  `453a9f5`, `b3a6a63`, `d088744` and `923d2d3` on 2026-09-13. Four commits,
  seventeen files, **1,709 insertions and 269 deletions**: eleven Go files in
  `adapter/cometbft` for the control channel, the tolerant watch loop and the
  replica subset, two Python integration files, `tools/devnet.sh`, the adapter
  README, and ADR 0073. **No accepted vector file, specification, manifest,
  encoding, or kernel source changed**, and every Go change is to the devnet
  harness rather than to the bridge, the node, or any consensus path.
  `tools/verification_scope.py` classifies it `full`. Candidate 34776763041 on
  `140ce72` passed all five jobs, with **159** ctest entries in the debug
  presets and **167** under `clang-sanitizers`, both unchanged because the
  slice grows the hosted integration rather than adding an entry.
- Issue #280 and PR #281 are the M3.14d delivery, merged by rebase as `6edd868`
  and `a958f82` on 2026-09-12. Two commits, five files, **206 insertions and 21
  deletions**: two Python integration files, and three Go files in
  `adapter/cometbft/internal/devnet` for the RPC-timeout repair its own first
  candidate exposed. **No accepted vector file, specification, manifest,
  encoding, or kernel source changed**, and the Go change is to the devnet
  harness rather than to the bridge, the node, or any consensus path.
  `tools/verification_scope.py` classifies it `full`. Candidate `5e0f6ea` failed
  one preset on the RPC timeout; candidate 34720531772 on `745be42` passed all
  five jobs, with **159** ctest entries in the debug presets and **167** under
  `clang-sanitizers`, unchanged from M3.14c because this slice adds no ctest
  entry.
- Issue #277 and PR #278 are the M3.14c delivery, merged by rebase as `648b576`
  and `c545b84` on 2026-09-12. Two commits, five files, **995 insertions and 194
  deletions**: a new wire driver and a new integration test, the headless-process
  test ported onto the driver, one ctest entry, and
  `docs/decisions/0072-the-wire-refuses-a-block-before-the-application-does.md`.
  **No accepted vector file, specification, manifest, encoding, workflow,
  dependency, or kernel source changed**, so the branch widens nothing a node
  accepts. `tools/verification_scope.py` classifies it `full` and that is right:
  a CMake change and a new process-driving test are exactly what the matrix is
  for. The suite is **159** ctest entries in the debug presets and **167** under
  `clang-sanitizers`. Candidate run 34716727961 on `c1e7a7c` and post-merge run
  34717489030 on `c545b84` both passed all five jobs.
- Issue #274 and PR #275 are the M3.14b delivery, merged as `f88bcf7`. One
  commit, five files, **312 insertions and 28 deletions**: three Python
  integration files and two Go files in the devnet harness. **No accepted vector
  file, specification, manifest, encoding, or kernel source changed**, and the
  Go change is to `protocol-cometbft-devnet`'s reporting rather than to the
  bridge, the node, or any consensus path — the refusals it exercises are the
  contract's existing ones.
- Issue #271 and PR #272 are the M3.14a delivery. Five commits, five files,
  **458 insertions and 44 deletions**: four Python integration files and
  `docs/decisions/0071-a-devnet-cannot-reach-the-uptime-audit.md`. **No accepted
  vector file, specification, manifest, encoding, workflow, dependency, or
  kernel source changed**, so the branch widens nothing a node accepts. It is
  nonetheless classified `full` by `tools/verification_scope.py` and that is
  right: the four changed files *are* the hosted integrations, so the matrix is
  what runs them.
- Issue #267 and PR #268 are the gRPC advisory bump, merged by rebase across
  commits `2d1e4ad` and `974138b` on `main` on 2026-09-10. Two commits: a
  one-line request file, and the hosted resolver's own
  `build(deps): resolve hosted Go module graph`. It changes `go.mod` and `go.sum`
  and nothing else — `google.golang.org/grpc` 1.83.1 → **1.83.2**, plus
  `golang.org/x/crypto` 0.55.0, `golang.org/x/net` 0.58.0, and
  `golang.org/x/text` 0.41.0 that `go mod tidy` carried with it. All four are
  indirect; no module was added or removed. Candidate run **34531476798** on
  `39d2c54` and post-merge run **34533172402** on `974138b` both passed the full
  hosted matrix.
- Issue #264 and PR #265 are the M3.13t delivery, merged by rebase across
  commits `0463fd6` through `13d6e9c` on `main`. It is the seventh and last step
  of
  ADR 0065's stack migration and it is **a deletion**: 99 files changed, 443
  insertions and **17,012 deletions** — 79 files removed, two added
  (`tests/fuzz/economy_v8_fuzz.cpp` and ADR 0070), and 18 modified.
  It removes `src/v7/` (17 sources), `include/protocol/v7/` (2 headers), the
  version-seven snapshot, owning store, schema, application, dispatcher,
  responses, and node process with their five public headers; every
  `tests/kernel/economy_v7_*`, `tests/storage/*_v7_*`, and
  `tests/application/*_v7*` file; the four version-seven integration Python
  files; both version-seven fuzz harnesses; and the Go adapter's `wire_v7.go`,
  `client_v7.go`, their tests, and `application_v7_test.go`. **It removes eight
  CMake targets and eleven ctest entries and adds one**, so the suite goes from
  167 to **158** in the debug presets and from 176 to **166** under
  `clang-sanitizers`. Nine of the eleven removals are non-fuzz, which is why the
  debug presets fall by nine and the fuzzing preset by ten. It removes **two
  hosted integrations** from `tools/verify.sh`, which now runs four: version one
  single-node and
  four-validator, and version eight single-node and four-validator.
  **Five shared files change**: `unix_server_v1.hpp` and
  `unix_connection_v1.cpp`
  lose the `serve_connection(ApplicationV7&)` overload, which is the one place
  the deletion touches version one; `bridge/local.go`, `bridge/application.go`,
  and `nodeconfig/config.go` lose their version-seven members. **No accepted
  vector file changes**, and both version-seven vector files, their verifiers,
  `simulation/economy_transition_v7/`, and the eight CTest entries that read
  them are deliberately untouched — `economy-transition-v8-cpp` still passes
  `economy-transition-v7.txt`, because version eight's predecessor constructions
  are pinned against it.
  **One item in ADR 0065's enumeration was wrong and the slice caught it**:
  `economy_v7_fuzz` was listed for removal on the stated precondition that every
  deleted item had a version-eight counterpart, and it was the one item with
  none, so the harness was migrated to `economy_v8_fuzz` — gaining the two
  uptime entry points version eight adds — rather than deleted. Two snapshot
  smoke entries were also found missing from `set_tests_properties`, which had
  cost them the 60-second bound.
  Run 34387349756 on head `13d6e9c` passed the complete hosted matrix: 158 ctest
  entries under
  `gcc-debug`, `clang-debug`, and `gcc-sanitizers` and 166 under
  `clang-sanitizers`, with all four integrations passing — `CometBFT
  single-node`, `CometBFT version-eight`, `CometBFT four-validator`, and
  `CometBFT four-validator version-eight integration: passed (4 independent
  replicas, 2 registrations and 1 confirmed transfer through 3 different nodes,
  full restart, 4 durable C++ audits per stop)`.
  **The first attempt on this branch failed all four jobs at `Install host
  prerequisites` with apt's exit code 100**, roughly twenty seconds in and
  before any compilation, which is an infrastructure failure a deletion cannot
  cause; re-running the failed jobs was the correct response and is the second
  recorded instance of a hosted-runner failure unrelated to the change.
  Local evidence: `python3 -B tests/tools/test_registration_test.py` (14 tests,
  OK) after every CMake edit, `-fsyntax-only` at `-Werror` on the new harness
  and both edited transport files, `go vet` and `go test` on `internal/localapp`
  in a scratch module, and a probe that weakens version eight's receipt prefix
  check to ignore the version octet, which fails the new refusal test by name.
- Issue #261 and PR #262 are the M3.13s delivery, merged by rebase across
  commits `3df3d81` through `47d0a8c` on `main`. It adds
  `src/application/main_v8.cpp`, `tests/application/headless_process_v8_test.py`,
  four files under `adapter/cometbft/internal/localapp/`, one test translation
  unit under `adapter/cometbft/internal/bridge/`, four Python files under
  `tests/integration/`, and ADR 0069. It adds one CMake target,
  `protocol_application_server_v8`, and two ctest entries —
  `version-eight-headless-process` and `version-eight-chain-fixture` — so the
  suite goes from 165 to **167** entries in the debug presets and from 174 to
  **176** under `clang-sanitizers`. It adds **two hosted integrations** to
  `tools/verify.sh`, which now runs five: version one single-node and
  four-validator, version seven single-node and four-validator, and version
  eight single-node and four-validator. **Six shared files change**:
  `bridge/local.go`, `bridge/application.go`, `nodeconfig/config.go`, and the
  three `cmd/` binaries' `-protocol-version` handling, none of which alters
  version one's or version seven's behavior. **No accepted vector file
  changes**, and no version-seven source, header, or test was touched. Run
  34088805350 on head `e136ab8` passed the complete hosted matrix; the job logs
  confirm `version-eight-headless-process` and `version-eight-chain-fixture`
  running and passing, `CometBFT version-eight integration: passed (2
  registrations, 1 confirmed transfer, restart at height 2, durable height 3)`,
  and `CometBFT four-validator version-eight integration: passed (4 independent
  replicas, 2 registrations and 1 confirmed transfer through 3 different nodes,
  full restart, 4 durable C++ audits per stop)`. **Six mutation probes** were
  run and each was checked to have changed the code the test runs; all six are
  caught, and two of them are caught by checks this slice added and nothing else
  would have.
- Issue #258 and PR #259 are the M3.13r delivery, merged by rebase across
  commits `f92c402` through `ac7f831` on `main`. It adds three headers under
  `include/protocol/application/`, four translation units and an internal header
  under `src/application/`, two test translation units under
  `tests/application/`, and ADR 0068. It adds two CMake targets,
  `application_v8_tests` and `application_transport_v8_tests`, and two ctest
  entries — `version-eight-application` and `version-eight-transport` — so the
  suite goes from 163 to **165** entries in the debug presets and from 172 to
  **174** under `clang-sanitizers`. **Two shared version-one files change**:
  `unix_server_v1.hpp` and `unix_connection_v1.cpp` gain a third
  `serve_connection` overload, because the `V1` in `UnixSocketServerV1` is the
  frame format's version rather than the ledger's. **No accepted vector file
  changes**, and no version-seven source, header, or test was touched. Version
  seven's transport suite was rebuilt and re-run locally after the shared
  overload was added and passes unchanged. Run 34062431677 on head `71b438b`
  passed the complete hosted matrix and both new entries are confirmed running
  and passing in the job logs. **Seven mutation probes** were run and each was
  checked to have changed the code the test runs; six are caught and one passed
  uncaught and is recorded in ADR 0068 rather than patched.
- Issue #255 and PR #256 are the M3.13q delivery, merged by rebase across
  commits `2b56c6a` through `95be298` on `main`. It adds
  `include/protocol/storage/sqlite_ledger_v8.hpp`, three translation units and
  two internal headers under `src/storage/`, four test translation units under
  `tests/storage/`, and ADR 0067. It adds two CMake targets,
  `storage_sqlite_ledger_v8_tests` and `storage_sqlite_recovery_v8_tests`, and
  two ctest entries — `version-eight-owning-store` and
  `version-eight-store-recovery` — so the suite goes from 161 to **163** entries
  in the debug presets and from 170 to **172** under `clang-sanitizers`. **No
  accepted vector file changes and no new one is added**, for ADR 0057's reason:
  a storage schema is operational data rather than a contract. **No
  version-seven source, header, or test was touched.** Run 34059985762 on head
  `7d80e64` passed the complete hosted matrix and both new entries are confirmed
  running and passing in the job logs. **Fourteen mutation probes** were run and
  each was checked to have changed the code the test runs; all fourteen are
  caught and each names its own subject. Two say more than that: the stale
  `head_snapshot` width probe was re-run with `check_column_bounds` removed and
  the suite passed, and the `application_id` probe is caught only by the tamper
  case this slice added.
- Issue #252 and PR #253 are the M3.13p delivery, merged by rebase across
  commits `cdf37a4` through `f0aa720` on `main`. It adds
  `include/protocol/storage/snapshot_v8.hpp`, three translation units and an
  internal header under `src/storage/`, five test translation units under
  `tests/storage/`, one fuzz target, and ADR 0066. It adds one CMake target,
  `storage_snapshot_v8_tests`, one fuzz target, `storage_snapshot_v8_fuzz`, and
  two ctest entries —
  `version-eight-snapshot` and `storage-snapshot-v8-fuzz-smoke` — so the suite
  goes from 160 to **161** entries in the debug presets and from
  168 to **170** under `clang-sanitizers`. **No accepted vector file
  changes and no new one is added**, for ADR 0056's reason: recording a
  snapshot's bytes would pin an operational format as though it were a
  contract. **No version-seven source, header, or test was touched.** Run
  33973333160 on head `6e437b1` passed the complete hosted matrix. **Thirteen
  mutation probes** were run and each was checked to have changed the code the
  test runs; six report "a restore accepted it" without their rule, six are
  caught naming the rule they broke, and one passed uncaught and was read
  rather than patched — removing the encoder's own prefix-width assertion
  changes nothing while the prefix is in fact 158 octets, and dropping a prefix
  field instead is what that guard is for.
- Issue #249 and PR #250 are the M3.13o delivery, merged by rebase across
  commits `389e819` through `10fcc23` on `main`. It adds
  `include/protocol/v8/ledger.hpp`, `src/v8/`'s seven execution sources plus
  `economy_uptime_transitions.cpp` and `economy_ledger_internal.hpp`, and the
  six `tests/kernel/economy_v8_*execution*`, `*trace*`, `*scenarios*`,
  `*derived*`, and `*transitions*` translation units. It adds one CMake target,
  `economy_v8_execution_tests`, and one ctest entry,
  `economy-transition-v8-execution-cpp`, so the suite goes from 159 to **160**
  entries in the debug presets and from 167 to **168** under
  `clang-sanitizers`. **No accepted vector file changes** and **no
  version-seven source, header, or test was touched**. Run 33919528555 on head
  `7823ee7` passed the complete hosted matrix, and the merged tree is
  byte-identical to the verified one (`ca94043`).
- Issue #244 and PR #247 are the M3.13n delivery, merged by rebase across
  commits `2675c2f` through `f33890b` on `main`. It adds
  `include/protocol/v8/economy.hpp` and `src/v8/`'s eleven sources plus
  `economy_internal.hpp`, and the six `tests/kernel/economy_v8_*` translation
  units; it adds one CMake target, `economy_v8_codec_tests`, and one ctest
  entry, `economy-transition-v8-cpp`, so the suite goes from 158 to **159**
  entries in the debug presets and from 166 to **167** under
  `clang-sanitizers`. **No accepted vector file changes**: version eight's 183
  contract vectors and 434 execution vectors, version seven's 395 and 590, and
  every earlier file are unchanged and passing, and **no version-seven source,
  header, or test was touched**. Run 33911161934 on head `a85c8a2` passed the
  complete hosted matrix with all four jobs reporting every ctest entry
  passing. **Two commits after the first candidate came from self-review.**
  `6489c86` moved the exclusion check ahead of the selection digest, because
  the accepted resource bound is 1,180 heights of every 1,200 and the first
  version paid it at all 1,200; nothing consensus-visible changes, and it is
  fixed before M3.13o's ledger calls it per seat per height. `f33890b`
  corrected an arithmetic error in three places — the specification, the
  model's docstring, and the kernel comment that had copied it — recorded in
  the truncation-bias note further down. **Coverage was measured rather than
  asserted**: a scratch build with the fixture's vector accessors instrumented
  reads 121 of the 121 codec vectors, touches 0 of the 62 ledger vectors, and
  reads 95 further keys from the four supporting accepted files. All 41 boolean
  vectors are paired with a live check.
- PR #245 is the ADR 0065 delivery, merged by rebase as commit `b0a17b0` on
  `main`. It adds
  `docs/decisions/0065-a-kernel-replacement-may-be-staged-across-a-stack-migration.md`,
  amends ADR 0046 in place with a pointer to it, and rewrites this document's
  exact next action to carry the seven-slice enumeration. **Pure Markdown**, so
  it took the focused metadata path: run 33788599501 passed with the compiler
  matrix correctly skipped and `Classify and verify change scope` and
  `Verification required` both green in seconds. Issue #244 is **open on
  purpose** and is the recorded next slice, retitled to the codec scope; it is
  the only open item and it agrees with the next action below.
- Issue #241 and PR #242 are the M3.13l delivery, merged by rebase across
  commits `e455f66` through `af9a5e9` on `main`. It adds
  `simulation/economy_transition_v8/{ledger,execution,transitions,receipt,block,trace}.py`,
  `tools/economy-transition-v8-execution-vectors/`,
  `test-vectors/economy-transition-v8-execution.txt` at 434 vectors,
  `tests/simulation/economy_transition_v8_{execution,block}_test.py`, and ADR
  0064; it adds `open_challenge_parts`, `seat_window_parts`, `state_root_frame`,
  and `state_root_from_frame` to `simulation/economy_transition_v8/state.py`,
  with `state_root` refactored to be *defined* through the last two so the quiet
  path cannot drift from it. **No accepted vector file changes**: version eight's
  183 contract vectors, version seven's 395 and 590, and every earlier file are
  unchanged and passing. Three ctest entries are added —
  `economy-transition-v8-execution`, `economy-transition-v8-block`, and
  `economy-transition-v8-execution-vectors` — so the suite goes from 155 to 158
  entries in the debug presets and from 163 to 166 under `clang-sanitizers`. No
  CMake target is added, because the whole slice is Python and Markdown. PR run
  33784677110 on head `2e930af` passed the complete hosted matrix with all four
  jobs reporting every ctest entry passing.
  **Two commits after the first green run came from self-review and both are
  worth knowing about.** `5be885a` renamed four vectors that asserted more than
  their values established — two carried a result string under a name ending
  `_is_accepted` or `_is_refused`, and two carried counts under names asserting
  an equality — and replaced one claim checked against a rearrangement of
  itself: `measured.bob_failed_the_cycle` compared the same inequality over the
  same number twice and is now checked from two directions, the arithmetic and
  the accrued bitmap the chain itself wrote. `af9a5e9` removed a dead parameter
  and an unused return and corrected three docstrings that had gone stale. **Run
  33783743738 shows cancelled**: it was superseded on the branch by the second of
  those pushes before it finished, which is what the concurrency group does, and
  no `main` history is affected.
- Issue #228 and PR #229 are the M3.13i delivery, merged by rebase across
  commits `2a32be3` through `e543681` on `main`. It gives `devnet.Run` and
  `protocol-cometbft-devnet start` a protocol version, extracts the devnet
  harness into `tests/integration/cometbft_devnet.py`, turns the fixture into a
  live `Session`, adds `cometbft_four_validator_v7_test.py`, amends ADR 0062,
  and adds the run to `tools/verify.sh`. **No accepted vector file changes and
  no ctest entry changes**: the new run is an integration script like the other
  three, so the suite stays at 153 entries in the debug presets and 161 under
  `clang-sanitizers`. PR run 33506987240 on head `ae5e3e1` passed the complete
  hosted matrix, with all four job logs reporting all four integrations passing,
  which is what proves the shared-harness extraction left version one's two
  alone. The four integrations cost 36 seconds combined and the matrix came in
  at 8m35s-9m00s per job against a twenty-minute timeout, faster than the
  previous run despite the addition.
- Issue #225 and PR #226 are the M3.13h delivery, merged by rebase across
  commits `8857acc through 9c733e4` on `main`. It adds
  `tests/integration/version_seven_chain.py`, its registered contract test,
  `tests/integration/cometbft_version_seven_test.py`, and ADR 0062; it moves
  `inspect_identity` and `initialize_home` into `cometbft_process.py` and gives
  `start_stack`, `stop_stack`, and `application_info` a protocol version; and it
  adds the run to `tools/verify.sh`. **No accepted vector file changes and no new
  one is added** — the fixture is computed at test time from the independent
  model, which is what version one's integration already does. One ctest entry is
  added, `version-seven-chain-fixture`, so the suite goes from 152 to 153 entries
  in the debug presets and from 160 to 161 under `clang-sanitizers`. PR run
  33504060503 on head `7b7ba55` passed the complete hosted matrix, with all
  four job logs reporting `CometBFT version-seven integration: passed (2
  registrations, 1
  confirmed transfer, restart at height 2, durable height 3)` and both existing
  integrations still passing, which is what proves the harness parameterization
  left version one's path alone.
- Issue #222 and PR #223 are the M3.13g delivery, merged by rebase across
  commits `6193a91 through ecd3fcf` on `main`. It adds
  `adapter/cometbft/internal/localapp/wire_v7.go` and `client_v7.go`,
  `adapter/cometbft/internal/bridge/local.go`, `NewV7` and the committed-height
  guard in `bridge/application.go`, `nodeconfig.ProtocolVersion` threaded through
  `Ensure`, `-protocol-version` on the bridge and initializer binaries, and ADR
  0061. **No accepted vector file changes, no CMake target is added, and no ctest
  entry changes**: the whole slice is Go and Markdown, so the suite stays at 152
  entries in the debug presets and 160 under `clang-sanitizers`. PR run
  33500977481 on head `142f750` passed the complete hosted matrix, which is what
  verifies the
  `bridge` and `nodeconfig` packages — they import CometBFT and cannot be
  compiled on the owner's machine, where Go is 1.23.6 against a module requiring
  1.25.7.
- Issue #219 and PR #220 are the M3.13f delivery, merged by rebase across
  commits `73955eb` through `a30a997` on `main`. It wires version one's seven
  fault points into `SQLiteLedgerV7::apply_block`, adds
  `Impl::recover_durable_head`, adds
  `tests/storage/sqlite_recovery_v7_test.cpp`, and **amends ADR 0057 in place**
  rather than adding a document, because the store's contract belongs in one. **No
  accepted vector file changes and no new one is added.** One ctest entry is
  added, `version-seven-store-recovery`, so the suite goes from 151 to 152
  entries in the debug presets and from 159 to 160 under `clang-sanitizers`. PR
  run 33448781878 on head `c8ad4ae` passed the complete hosted matrix with those
  counts and all four job logs confirming the new entry, so the fork/exec
  termination cases and the fault-VFS commit failure ran under both sanitizers.
- Issue #216 and PR #217 are the M3.13e delivery, merged by rebase across
  commits `cf1d28c` through `8ffc2bd` on `main`. It adds `decode_genesis` to
  `include/protocol/v7/economy.hpp` and `src/v7/economy_genesis.cpp`,
  `src/application/main_v7.cpp` as the `protocol-application-v7` target, and
  `tests/application/headless_process_v7_test.py`, plus ADR 0060. **No accepted
  vector file changes and no new one is added**, and nothing that existed before
  behaves differently: the decoder is additive. One ctest entry is added,
  `version-seven-headless-process`, so the suite goes from 150 to 151 entries in
  the debug presets and from 158 to 159 under `clang-sanitizers`.
  **The slice's first matrix failed and the reason is worth keeping.** Run
  33441137560 on head `611e7b6` failed in all four jobs because the new binary
  was never added to `PROTOCOL_STACK_TARGETS` and therefore built at the
  compiler's default standard; the final commit fixes it and adds the guard that
  makes it non-repeatable. Run 33442267440 on head `b388656` then passed the
  complete hosted matrix with the counts above and all four job logs confirming
  the new entry, so the binary is sanitizer-clean as a process rather than only
  as a translation unit.
- Issue #213 and PR #214 are the M3.13d delivery, merged by rebase across
  commits `cc8b9c0` through `115c295` on `main`. It adds
  `include/protocol/application/response_v7.hpp` and `dispatcher_v7.hpp`, two
  translation units under `src/application/`, one test translation unit under
  `tests/application/`, and ADR 0059. `unix_connection_v1.cpp`'s loop becomes one
  function over a dispatcher and `serve_connection` gains a version-seven
  overload; **version one's behaviour is unchanged and both of its suites were
  re-run locally to prove it**. **No accepted vector file changes and no new one
  is added.** One ctest entry is added, `version-seven-transport`, so the suite
  goes from 149 to 150 entries in the debug presets and from 157 to 158 under
  `clang-sanitizers`. PR run 33438537070 on head `440c214` passed the complete
  hosted matrix with those counts and all four job logs confirming the new entry
  — which means the socket case ran under both sanitizers as well as the plain
  builds.
- Issue #210 and PR #211 are the M3.13c delivery, merged by rebase across
  commits `8a3b345` through `62941c2` on `main`. It adds
  `include/protocol/application/application_v7.hpp`, two translation units and
  one internal header under `src/application/`, one test translation unit under
  `tests/application/`, and ADR 0058. `SQLiteLedgerV7` gains `verifier()` and
  `BlockCommitV7` gains a defaulted equality, neither of which changes any
  behaviour of the store. **No accepted vector file changes and no new one is
  added.** One ctest entry is added, `version-seven-application`, so the suite
  goes from 148 to 149 entries in the debug presets and from 156 to 157 under
  `clang-sanitizers`.
  PR run 33434821050 on head `7dd1d82` passed the complete hosted matrix — scope
  classification `full`, GCC and Clang debug, both sanitizer presets, and the
  aggregate required check — with **149 of 149** and **157 of 157** entries
  passing and all four job logs confirming the new entry. An earlier run on
  `56df84e` was superseded and cancelled by the concurrency group when a
  self-review found the replay-handshake debt worth recording before merge.
- Issue #207 and PR #208 are the M3.13b delivery, merged across commits
  `5f5b731` through `aca7b5b` on `main`. It adds
  `include/protocol/storage/sqlite_ledger_v7.hpp`, three translation units and
  two internal headers under `src/storage/`, three test translation units under
  `tests/storage/`, and ADR 0057. It also carries the transaction root out of
  `BlockOutcome` in `src/v7/economy_block.cpp`, which removes the store's one
  duplicated derivation, and retains each block's raw inputs on the kernel
  trace's `Scenario` so a caller outside the fixture can execute a recorded
  block. **No accepted vector file changes and no new one is added**, which is
  the check that the kernel change is inert: the header committed to the same
  transaction root before and after, so every recorded `block_id` still matches.
  One ctest entry is added, `version-seven-owning-store`, so the suite goes from
  147 to 148 entries in the debug presets and from 155 to 156 under
  `clang-sanitizers`.
  **The slice has two green matrices rather than one**, for the same reason
  M3.13a did. PR run 33430999790 on head `db750e7` passed the complete hosted
  matrix — scope classification `full`, GCC and Clang debug, both sanitizer
  presets, and the aggregate required check — with **148 of 148** entries passing
  in the debug presets and **156 of 156** under `clang-sanitizers`, and all four
  job logs confirm the new entry running and passing. **A self-review against
  `docs/engineering/verification.md` on that green tree then found one thing**:
  the rule requiring a fuzz target for untrusted bytes *or a documented reason
  one does not apply* had been reasoned about and never written down, so the
  final commit records the reason in ADR 0057. PR run 33432019705 on head
  `886dec6` passed the same complete matrix with the same counts.
- Issue #202 and PR #205 are the M3.13a delivery, merged by rebase across
  commits `8d491b2` through `61064ab` on `main`. It adds
  `include/protocol/storage/snapshot_v7.hpp`, four translation units under
  `src/storage/`, five test translation units under `tests/storage/`, one fuzz
  target, and ADR 0056. `kChannelCount` moves from `include/protocol/v7/ledger.hpp`
  to `include/protocol/v7/economy.hpp`, because it bounds a channel *key* before
  it bounds a channel *balance*. **No accepted vector file changes and no new one
  is added.** Two ctest entries are added — `version-seven-snapshot` and
  `storage-snapshot-v7-fuzz-smoke` — so the suite goes from 146 to 147 entries in
  the debug presets and from 153 to 155 under `clang-sanitizers`.
  **The slice has two green matrices rather than one.** PR run 33333211282 on head
  `3679635` passed the complete hosted matrix — scope classification `full`, GCC
  and Clang debug, both sanitizers, and the aggregate required check — with
  **147 of 147** ctest entries passing in the debug presets and **155 of 155**
  under `clang-sanitizers`, and the job logs confirm both new entries running and
  passing. **A self-review on that green tree then found four things**, so the
  final commit adds the prefix width guard, splits the assignment record out of
  the entry decoders, and re-aims two refusal tests that were passing for the
  wrong reason. PR run 33333784418 on head `abc1591` passed the same complete
  matrix on that tree, with the same counts and the same two entries confirmed in
  the logs. Push run 33334302566 then passed the same matrix on the merged
  commit `61064ab`.
- Issue #196 and PR #200 are the M3.12b delivery, merged by rebase across
  commits `ad4c59a` through `9538174` on `main`. It moves the C++20 kernel from
  `economy-transition-v6` to `economy-transition-v7`: `src/v6/` becomes
  `src/v7/` and gains `economy_assignment.cpp`, `include/protocol/v6/` becomes
  `include/protocol/v7/`, and the thirteen kernel test files and the fuzz target
  take version seven's names. `tests/kernel/economy_v7_version_test.cpp` is new.
  Version six's C++ kernel is **removed** under ADR 0046; its Python model and
  both of its accepted vector files remain in place, passing, and unedited.
  The codec target now takes a fifth argument — version six's own vector file,
  for the surface version seven carries unchanged — and both kernel targets
  bind `founder-economy-manifest-v3`. No ctest entry is added or removed; two
  are renamed to version seven, and the fuzz smoke entry with them.
  PR run 33269693064 on head `7774df5` passed the complete hosted matrix —
  scope classification `full`, GCC and Clang debug, both sanitizers, and the
  aggregate required check — in 10m02s, with **153 of 153 ctest entries
  passing**. The job
  logs confirm `economy-transition-v7-cpp`,
  `economy-transition-v7-execution-cpp`, `economy-transition-v7-fuzz-smoke`,
  `test-registration`, and all seven version-six entries running and passing,
  which is what makes "version six's evidence is intact" a checked claim rather
  than an assertion.
  **The first candidate failed the matrix for two independent reasons and both
  are recorded in the next-action section**: a blanket rename reached version
  six's own Python verifier registrations, which `test-registration` caught as a
  vector file no registered verifier reads; and GCC 13's `-Wdangling-reference`
  rejected seven call sites that compile clean under the GCC 12 on this machine.
  Run 33269243050 then passed the full matrix on the repaired tree before the
  last three commits were pushed, so the slice has two green matrices rather
  than one.
- Issue #197 and PR #198 are the M3.12a delivery, merged by rebase across commits
  `28567d1` through `90e13a7` on `main`. It adds two trace scenarios and takes
  `test-vectors/economy-transition-v7-execution.txt` from 412 vectors to 590, so
  that all fourteen transaction kinds execute under version seven; it corrects ADR
  0055 in place, updates the specification's evidence section and
  `docs/README.md`, and adds three tests. It registers no new ctest entry, so the
  suite stays at 146 entries in the debug presets and 153 under
  `clang-sanitizers`. PR run 32393306408 on head `1e36a5b` passed the complete
  hosted matrix — scope classification `full`, GCC and Clang debug, both
  sanitizers, and the aggregate required check — in 8m01s to 9m06s per job, and
  all eight version-seven ctest entries were confirmed to run and pass in the job
  logs. Push run 32394434657 then passed the same matrix on the merged commit,
  which is what M3.11c's closeout cancelled by pushing too early.
  **An earlier candidate run failed the classification job**, on a trailing blank
  line at the end of `trace.py` that `git diff --check` refuses; the fix is one
  line and the lesson is recorded in the next-action section.
- Issue #192 and PR #193 are the M3.11c delivery, merged by rebase across commits
  `4aacbe6` through `63adcdd` on `main`. It gives `economy-transition-v7`
  its transaction ledger, dispatch, ordered block execution, a recorded
  three-scenario trace, 412 vectors, an independent verifier, ADR 0055, and 73
  tests across three modules; it indexes ADR 0055 in `docs/README.md` and edits no
  accepted artifact beyond an evidence pointer in the version-seven
  specification, which changes no rule. Four ctest entries were added —
  `economy-transition-v7-execution`, `-ledger`, `-block`, and
  `-execution-vectors` — taking the suite from 142 to 146 entries in the debug
  presets and 149 to 153 under `clang-sanitizers`. PR run 32384372907 on head
  `4874e7d` passed the complete hosted matrix — scope classification `full`, GCC
  and Clang debug, both sanitizers, and the aggregate required check — and all
  four new entries were confirmed to run and pass in the job logs.
  No job stalled and none came near the twenty-minute per-job timeout: 8m52s
  and 8m57s for the two debug presets, 9m41s and 10m22s for the two sanitizer
  presets. An earlier candidate run on the same tree took 15m28s in
  `clang-sanitizers` alone, so the run-to-run variance M3.7a measured is still
  the dominant term and a single slow run is not evidence of a regression. The
  merge is a rebase, and the resulting tree on `main` is byte-identical to the
  verified head — both are tree `a1c5087` — so the matrix result transfers
  exactly, and the PR run is the acceptance evidence rather than a `main` push
  run. **The `main` push run on the merged code commit, 32385650335, was
  cancelled** — the closeout documentation commit landed on `main` while it was
  still building and the workflow's concurrency group cancelled it, which also
  marks its aggregate check failed. Nothing regressed and nothing needs
  re-running: the tree it was building is `a1c5087`, the tree PR run 32384372907
  passed in full, and the commit that superseded it changes Markdown only and
  correctly took the focused metadata path. **The lesson is about sequencing
  rather than about evidence** — a documentation closeout pushed to `main` while
  the merge's own matrix is still running will cancel it, so let the merge run
  finish before pushing the closeout. Two candidate runs on the branch were also
  superseded: one passed the whole matrix and was made obsolete by three
  self-review fixes, and one was cancelled when the documentation reflow was
  pushed.
- Issue #189 and PR #190 are the M3.11b delivery, merged by rebase across
  commits `dbc1495` through `01527e5` on `main`. It adds
  `economy-transition-v7` — the specification, ADR 0054, the sibling model, 395
  vectors, an independent verifier, and three test modules — indexes the
  contract and the seven undocumented ADRs behind it in `docs/README.md`, and
  edits no accepted artifact. Four ctest entries were added,
  `economy-transition-v7-vectors`, `-carryover`, `-state`, and `-settlement`,
  taking the suite from 138 to 142 entries in the debug presets and 145 to 149
  under `clang-sanitizers`. PR run 32287855271 on the final head `0b425936`
  passed the complete hosted matrix — scope classification `full`, GCC and Clang
  debug, both sanitizers, and the aggregate required check — and all four new
  entries were confirmed to run and pass in the job logs. Two earlier candidate
  runs were cancelled as obsolete when the two strengthened guards were pushed.
- **No job stalled in that run, which is the first time in three slices.** The
  four preset jobs took 8m29s to 9m58s against the 20-minute per-job timeout,
  inside the run-to-run variance M3.7a measured. The slice adds no translation
  unit, only four Python entries that finish in about a sixth of a second each.
- Issue #184 and PR #185 are the M3.11a delivery, merged by rebase across
  commits `ad88f0d` through `57d6400` on `main`. It adds
  `founder-economy-manifest-v3` — the specification, ADR 0053, the manifest
  JSON, 171 vectors, a verifier, the contract table with its loader binding, and
  31 tests — and edits no accepted artifact. It also refactors the ordered
  manifest loader into `simulation/founder_economy_manifest/` so both accepted
  versions bind one implementation; that refactor is its own commit and version
  two's complete evidence passed unchanged on it. Two ctest entries were added,
  `founder-economy-manifest-v3-vectors` and `founder-economy-manifest-v3`,
  taking the suite from 136 to 138 entries in the debug presets and 143 to 145
  under `clang-sanitizers`. PR run 32279213408 on head `8723149` passed the
  complete hosted matrix — scope classification `full`, GCC and Clang debug,
  both sanitizers, and the aggregate required check — and both new entries were
  confirmed to run and pass in all four preset jobs. Post-merge run 32281261842
  on `57d6400` passed the same matrix with no re-run needed.
- **One job in that run hung on runner infrastructure and it is the second time
  this shape has appeared.** `gcc-sanitizers` sat on the runner's `Install host
  prerequisites` step for twelve minutes while its three siblings cleared the
  same step in seconds. M3.10d recorded the identical shape. The remedy is the
  same and it worked: cancel the run, `gh run rerun --failed`, which re-runs
  only the hung job and leaves the three successes in place. The re-run passed
  in 5m35s. **Twice is a pattern**: a single job stalled on package install,
  with siblings past it, is the runner rather than the change, and should be
  cancelled and re-run rather than waited out to the 20-minute timeout.
- **M3.11a's margin is about ten and a half minutes, and the candidate run is
  the wrong place to read it from.** Against the 20-minute per-job timeout, the
  candidate gave `clang-sanitizers` 5m31s, `gcc-sanitizers` 5m35s on the re-run,
  `clang-debug` 10m11s, and `gcc-debug` 10m56s — a spread far wider than the
  roughly 12% run-to-run variance M3.7a measured on identical code. The
  post-merge run on the same tree gave `clang-sanitizers` 7m42s, `gcc-debug`
  8m20s, `clang-debug` 9m06s, and `gcc-sanitizers` 9m31s, which sits inside that
  variance against M3.10c's figures. **Same code, two runs, a five-and-a-half
  minute swing on `gcc-debug`**, so a single run's timing is not a measurement.
  Take the post-merge figures as the baseline: the slowest job is 9m31s and the
  slice adds no translation unit, only two Python entries that finish in about a
  tenth of a second each.
- Issue #153 and PR #173 are the M3.10b delivery, merged by rebase across
  commits `19107df` through `cc2e8fc` on `main`. It adds the version-six
  execution model, 512 vectors, a verifier, ADR 0045, and two test modules, and
  edits no accepted artifact. PR run 31952597793 on the final head `66fcab8`
  passed the complete hosted matrix — scope classification `full`, GCC and Clang
  debug, both sanitizers, and the aggregate required check — and post-merge run
  31953123699 on `cc2e8fc` passed the same matrix.
- **The margin is about ten and a half minutes, and the slice moved it very
  little.** Per-job durations on the candidate against the 20-minute per-job
  timeout: `gcc-debug` 5m48s, `clang-sanitizers` 7m21s, `clang-debug` 8m45s,
  `gcc-sanitizers` 9m21s. Post-merge on `main`: `clang-debug` 8m15s, `gcc-debug`
  8m17s, `clang-sanitizers` 8m50s, `gcc-sanitizers` 9m20s. The slice adds no
  translation unit and two fast Python entries that `ctest --parallel` absorbs,
  so the spread sits inside the roughly 12% run-to-run variance M3.7a measured
  on identical code. **M3.10c was the one to watch**, and the figure below is
  the answer.
- **M3.10c's margin is about eleven minutes, and replacing a codec cost nothing
  measurable.** Per-job durations on the candidate `ea7f916` against the
  20-minute per-job timeout: `gcc-sanitizers` 7m38s, `clang-debug` 8m07s,
  `gcc-debug` 8m22s, `clang-sanitizers` 8m48s. The slice removed six translation
  units and added ten, plus five test units in one executable and one fuzz
  target, and the slowest job moved from 9m21s to 8m48s — inside the roughly 12%
  run-to-run variance M3.7a measured on identical code, and in the direction that
  says the exchange was roughly even. **`clang-sanitizers` remains the slowest**
  and is the only preset that builds the fuzz targets at all, so it is where
  M3.10d's transitions will show first.
- Issue #153's scope has been rebound twice. It was opened as M3.9b against
  version four, renumbered M3.9e and rebound to version five when version four's
  kind-11 defect pushed three slices in front of it, and finally rebound to
  version six after the pivot of 2026-08-15. It closed as M3.10b, and its
  recorded requirement that the trace walk the recovery path is satisfied by the
  `recovery` scenario.
- Issue #169 and PR #170 are the M3.10a delivery, merged by rebase across
  commits `6fb57f6` through `15b5e90` on `main`, with PR #171 closing out the
  handoff at `07afe4c`. The complete hosted matrix passed on the exact candidate
  — `gcc-debug` 8m33s, `clang-debug` 8m57s, `clang-sanitizers` 9m02s,
  `gcc-sanitizers` 9m27s — and again post-merge in 9m48s.
- Issue #154 and PR #155 are the M3.9b delivery, merged by rebase at commit
  `fa1907f` on `main`. It is documentation only — a specification and an ADR —
  so it took the focused metadata path rather than the matrix: scope
  classification passed, the preset matrix was skipped as designed, and the
  aggregate required check passed. Post-merge run 31872875912 on `fa1907f`
  passed the same path.
- Issue #157 and PR #158 are the M3.9c delivery, merged by rebase across commits
  `0f93026` through `c1e9ee4` on `main`. It adds the version-five model, 550
  vectors, a verifier, four test modules, and ADR 0038, and edits no accepted
  artifact. PR run 31880586047 on the final head `13c8229` passed the complete
  hosted matrix — scope classification `full`, GCC and Clang debug, both
  sanitizers, and the aggregate required check.
- **The margin is unchanged at about eleven minutes**, which is the expected
  result and is recorded so the next slice has a baseline. Per-job durations
  against the 20-minute per-job timeout: `gcc-sanitizers` 6m15s, `clang-debug`
  8m06s, `gcc-debug` 8m16s, `clang-sanitizers` 8m51s. The slice adds no
  translation unit, and `ctest --parallel` absorbs four fast Python entries, so
  the figures sit inside the roughly 12% run-to-run variance M3.7a measured on
  identical code. **M3.9d is the one to watch**: it is C++, and build time is
  the larger half of each job.
- **Version five's evidence gap is closed and its implementation gap is now
  moot.** M3.9d — the kernel updated to version five — was withdrawn on
  2026-08-15, because the direction of that day superseded version five as the
  kernel's target. The kernel carried version four's codec until M3.10c replaced
  it with version six's on 2026-08-17.
- Issue #150 and PR #151 are the M3.9a delivery, merged by rebase. The slice is
  commits `f457ca2` through `ab1e036` on `main`. PR Actions run 31849896862 on
  the final head `2c8d0fa` passed the complete hosted matrix — scope
  classification `full`, GCC and Clang debug, both sanitizers, and the aggregate
  required check.
- **The margin is about eleven minutes, and the first C++ of the milestone moved
  it very little.** Per-job durations on that run against the 20-minute per-job
  timeout: `gcc-debug` 5m39s, `clang-debug` 8m13s, `gcc-sanitizers` 9m06s,
  `clang-sanitizers` 9m08s. The slice added six translation units and one test
  executable, and the slowest job is within the roughly 12% run-to-run variance
  M3.7a measured on identical code. That is the figure to watch as M3.9b adds
  the transitions, because build time is the larger half of each job and
  `ctest --parallel` does not touch it.
- Issue #148 and PR #149 were the M3.8c delivery, merged by rebase across
  commits `225c7b0` through `7d6a69f`. PR run 31846053158 on head `3b8b944` and
  post-merge run 31846841502 on `7d6a69f` both passed the complete matrix.
- Issue #144 and PR #145 were the M3.8b delivery, merged by rebase across
  commits `b04575d` through `688efd0`. PR run 31823949771 on head `a98ac85` and
  post-merge run 31825463939 on `688efd0` both passed the complete matrix.
- Issue #139 and PR #140 were the M3.8a delivery, merged by rebase across
  commits `f8d6374` through `5f66c49`. PR run 31744378969 on head `6ced9f7` and
  post-merge run 31745207592 on `5f66c49` both passed the complete matrix.
- **The C++ codec reproduces the recorded vectors on every hosted preset.** The
  `economy-transition-v6-cpp` entry runs under GCC and Clang, debug and
  sanitized, and compares against `test-vectors/economy-transition-v6.txt` and,
  for the four claims checked against a third source, against
  `test-vectors/protocol-primitives-v1.txt` and
  `test-vectors/economy-transition-v3.txt`. `economy-transition-v6-fuzz-smoke`
  runs the decoders under libFuzzer on the fuzzing preset.
- The kind-1 identity is exact. The version-two encoder reproduces
  `test-vectors/protocol-primitives-v1.txt`'s recorded `unsigned_tx`,
  `signed_tx`, and `tx_id`
  (`df2372fa965e33a7e6b871ac07acc2e2a0cb29c32939808cc6d9e1893d6d0997`)
  byte-for-byte, and the header and trailer are proved to be slices of the
  accepted bytes rather than a re-encoding of them.
- The version-one state root the non-collision claim is measured against is the
  real one, not a lookalike. Self-review found that comparing a version-two root
  against a merely plausible restatement would make "the roots differ" trivially
  true and prove nothing, so the restatement is first required to reproduce the
  accepted `state.empty_tree_root`, `state.accounts_tree_root`, `state.root`,
  `tx.empty_root`, and `tx.root` exactly. All five reproduce.
- Signed transaction lengths are 200, 325, 228, 164, 160, and 265 bytes for kinds
  1 through 6. Every kind is fixed-length, no two share a length, and **the
  largest transaction in version two is 325 bytes**, because nothing a
  transaction carries scales with the seat population.
- Version-two genesis is 110 bytes of prefix — version one's 46 plus the manifest
  digest and the ecosystem verifier key — so the object bound admits 21,843
  account entries against version one's 21,844. Version two adds 64 bytes and
  loses exactly one entry, clearing the bound by two bytes. Every figure is
  derived.
- Storage bounds at the founder-directed capacity, which complete requirement
  12: 11,900,000 bytes of seats, 180 bytes of channels, 100 bytes of carries, 49
  bytes per referrer, 4,200,000 bytes of typed custody, and 25,033 bytes per
  cycle assignment. **The per-seat-cycle population is absent from the state
  entirely** — the take-everything mint rule collapses 73,100,000 would-be
  entries into 800,000 bytes of high-water marks.
- The cycle-assignment growth is the one bound that is not a constant and is the
  weakest result in the slice: 25,033 bytes per cycle at capacity, about
  9,137,045 bytes per year at the pinned three-second commit interval, never
  deleted because a seat may mint at any time. Three mitigations are named and
  refused: expiring an uncollected cycle would decide a seat's entitlement by
  inaction, pruning past every seat's mint does not help because one seat that
  never mints holds everything after its own last mint, and a run-length form of
  the ordinary all-ones day must be the record's single canonical encoding rather
  than a second one. It belongs in requirement 15's independent review as a limit
  rather than as a figure.
- The verifier records 238 vectors and fails closed three ways, each confirmed
  by execution against the unmutated run as a positive control: a tampered
  value, a derived key the file omits, and a recorded key no derivation reaches.
- The four test modules run 91 tests. The economy model's twenty-four declared
  result codes partition exactly 11 carried, 2 guards, and 11 unrepresentable,
  checked against `simulation/founder_economy_v3`'s own declared set rather than
  a copy of it.
- No accepted artifact changed. `simulation/founder_economy*/`,
  `simulation/cycle_boundary/`, `simulation/uptime_measurement/`,
  `simulation/escrow_payout/`, and `simulation/scenarios/` are untouched, and
  every previously recorded `test-vectors/` file is byte-for-byte unchanged.
- Issue #135 and PR #136 are the M3.7a delivery, merged by rebase at `79d1c0f`.
  PR Actions run 31608054054 and post-merge run 31609094115 on `79d1c0f` both
  passed the complete hosted matrix — scope classification `full`, GCC and Clang
  debug, both sanitizers, and the aggregate required check. No run on that branch
  was superseded.
- **The margin measurement, which is the point of the slice.** Per-job durations
  against the workflow's 20-minute per-job timeout. The baseline is post-merge
  run 31495429227 on `c44c320`:

  | preset | before | PR 31608054054 | post-merge 31609094115 |
  | --- | --- | --- | --- |
  | `gcc-debug` | 14m30s | 7m40s | 8m28s |
  | `clang-debug` | 15m20s | 8m50s | 8m44s |
  | `gcc-sanitizers` | 16m24s | 8m32s | 9m17s |
  | `clang-sanitizers` | 15m41s | 9m23s | 9m58s |

  The slowest job is now `clang-sanitizers` at 9m58s post-merge, so the margin is
  about 10m rather than 3m36s.
- The `gcc-sanitizers` job records `100% tests passed out of 106` with
  `Total Test time (real) = 255.08 sec` on the PR head and `286.64 sec`
  post-merge, against 105 tests and 707.57s before. The 106 entries sum to 992.0s
  and 1096.7s under 4-way contention, so both wall times are within 3-5% of their
  `max(longest entry, sum / 4)` floor of 248s and 274.2s. `scenario-v2` and
  `scenario-v3` are now 76.0s and 72.3s, having been 107.9s and 46.0s.
- **The two runs differ by about 12% on identical code**, so the margin is
  roughly ten minutes rather than a precise figure. Treat a single hosted timing
  as an estimate and re-measure after the next slice.
- M3.7a local evidence: `scenario_v2_test.py` falls from 70.3s to 32.0s and
  gains two tests, 31 to 33. The 81 Python entries invoked the way `ctest`
  invokes them take 475.0s serially and 209.1s at `-j4` with zero failures, which
  is what established that no entry contends for a port, a fixed path, or a
  shared temp directory. Peak RSS of the heaviest entry is 139 MB, so four
  concurrent jobs are not a memory constraint.
- All three scenario-suite verifiers pass unchanged at 133 v1, 138 v2, and 158
  v3, and every `test-vectors/` file is byte-for-byte unchanged, which the diff
  shows directly. No vector, model, source, specification, or ADR changed.
- The registration guard fails closed four ways, each confirmed by execution
  against the unmutated run as a positive control: a duplicated build-directory
  path, a duplicated entry name, an unparsable registration, and an unregistered
  `tests/tools` module. The third is the informative one — it is what makes the
  uniqueness check non-vacuous, and the parser it guards was in fact missing all
  six fuzz entries when written.
- Issue #131 and PR #132 are the M3.6c delivery, merged by rebase at `c44c320`.
  PR final-head Actions run 31493856438 on `0be7b05` and post-merge run
  31495429227 on `c44c320` both passed the complete hosted matrix — scope
  classification `full`, GCC and Clang debug, both sanitizers, and the aggregate
  required check. No run on that branch was superseded.
- **The CI margin moved, and this is the measurement M3.6b asked for.** The
  slowest job, `gcc-sanitizers`, took 16m24s post-merge and 16m55s on the PR head,
  against the workflow's 20-minute per-job timeout. The margin is therefore about
  3m36s, down from 5m12s at M3.6a. Roughly a minute and a half of that is the
  newly gated evidence — 63 economy and 14 escrow tests plus two verifiers that
  had never run at all — and the rest is the second complete 731-cycle population
  run. 16m55s is the exact figure that triggered issue #122 and PR #123, which
  reclaimed the margin by caching a rebuilt fixture.
- M3.6c local evidence: the suite verifier derives 158 v3 vectors and 51 new
  tests pass — 40 scenario and 11 property. All three suite verifiers pass at 133
  v1, 138 v2, and 158 v3, and `economy-scenario-suite-v1.txt` and `-v2.txt` are
  byte-for-byte unchanged. The 63 v3 economy tests, the 14 escrow v3 tests, the
  373-vector economy v3 verifier, and the 174-vector escrow v3 verifier now run
  in the matrix for the first time and all pass.
- The v3 suite verifier fails closed six ways, each confirmed by execution at
  exit 1 with the unmutated run as a positive control: a tampered recorded value,
  a recorded key no derivation reaches, a derived key the file does not carry, the
  v3 verifier run against the v2 vector file, a closed form assuming every failed
  cycle pays a seat in its own window, and a generator listing every seat in every
  window as version two did.
- **The fifth is the informative one.** It reproduces every monetary total in the
  scenario and is still rejected, on the single vector `economy.unrewarded_windows`
  and nothing else. That is the whole reason the count is recorded: the amounts
  cannot distinguish a portion delivered late from one never carried.
- `random_economy_v3` installs an accepted schedule first and aims each later
  event at one condition, because a purely random window and seat set would now be
  refused almost always. Every hostile activation is refused by construction, and
  a test requires that no run ever records a seat the generator did not install,
  so the schedule it aims against is never disturbed. The eight seeds reach 18
  result codes, a strict superset of the 11 `random_economy_v2` reaches.
- Issue #128 and PR #129 are the M3.6b delivery, merged by rebase at `93e782a`.
  PR Actions run 31395311829 and post-merge run 31396835571 on `93e782a` both
  passed the complete hosted matrix — scope classification `full`, GCC and
  Clang debug, both sanitizers, and the aggregate required check.
- M3.6b local evidence: the escrow verifier derives 174 v3 vectors and 14 new
  tests pass, alongside the 76 retained escrow tests. All three escrow versions
  verify — 169 v1, 172 v2, 174 v3 — and both scenario-suite verifiers pass
  unchanged at 133 v1 and 138 v2, which is the focused check that the changed
  `caps_agree()` and `custody_key()` disturbed nothing that binds through them.
- The v3 escrow verifier fails closed four ways, each confirmed by execution: a
  tampered recorded value, a recorded key no derivation reaches, a derived key the
  file does not carry, and the v3 verifier run against the v2 vector file.
- `test-vectors/escrow-payout-v1.txt`, `escrow-payout-v2.txt`, and both earlier
  fixtures are byte-for-byte unchanged.
- Issue #125 and PR #126 are the M3.6a delivery, merged by rebase at `271a173`.
  PR final-head Actions run 31391379966 on `b06557b` passed the complete hosted
  matrix — scope classification `full`, GCC and Clang debug, both sanitizers,
  and the aggregate required check. Post-merge run 31392793631 on `271a173`
  passed the same complete matrix. Run 31391091746 was superseded by the
  self-review push to the same branch and was cancelled.
- **The CI margin held.** That run took 15m03s with its slowest job,
  `gcc-sanitizers`, taking 14m48s against the workflow's 20-minute per-job
  timeout, which is the same margin PR #123 reclaimed at 14m52s. A new economy
  version, 373 vectors, and 63 tests cost no measurable hosted time, because
  the matrix is dominated by the C++ builds rather than by the Python models.
  M3.6c adds a second complete 731-cycle population run and should re-measure
  rather than assume this holds.
- M3.6a local evidence: the v3 verifier derives 373 vectors and 63 new tests pass
  — 22 schedule, 16 model, 13 error, and 12 scenario. The complete local
  simulation suite is 816 tests in 6m3s. All ten retained verifiers pass
  unchanged: economy v1 derives 139 manifest and 65 simulator values, manifest v2
  154, simulator v2 189, seat 96, routing 200, escrow v1 169 and v2 172, the
  suite 133 v1 and 138 v2, the cycle boundary 101, and the uptime pipeline 114.
  The M2 and M3.1 through M3.5 evidence is intact.
- The v3 verifier fails closed seven ways, each confirmed by execution at exit 1
  with the unmutated run as a positive control: a tampered recorded value, a
  recorded key no derivation reaches, a derived key the file does not carry, a
  boundary check that always accepts, a disabled completeness check, an in-scope
  set given an upper bound at `last_cycle_window`, and a model holding a second
  opinion about a founder figure.
- The sixth is the informative one. Bounding the in-scope set at a seat's last
  issuance window is the plausible narrowing — a seat that no longer issues looks
  like a seat that no longer needs measuring — and it leaves the model internally
  self-consistent. It is caught because `expected.py` derives the set from
  `uptime-measurement-v1`'s rule independently, so the producing and consuming
  ends stop agreeing.
- The seventh is the containment working rather than a check firing. A drifted
  binding makes the run refuse to start, so there is no result to compare, and
  the verifier reports that as its failure.
- `walk.py` is a second implementation of the transitions rather than a wrapper.
  It keeps its own channel, custody, permission, and carry state, reads the
  scenario as plain JSON so it shares no parser with the model, and stands in for
  the record digest with an injective rendering rather than recomputing the
  model's label. A recorded trace is therefore agreement between two
  implementations.
- `expected.py` restates nothing already hand-restated. It reads the economy
  tables from the v2 verifier's closed form and the grid from the cycle-boundary
  verifier's, and requires those two independent restatements to agree with each
  other before any vector is checked, so a divergence between them surfaces as an
  evidence defect rather than a confusing model mismatch.
- Issue #117 and PR #118 are the founder-decision gate change, merged by rebase
  at `0b8c7c2`. PR run 31317461354 and post-merge run 31317481539 both passed the
  focused metadata path; the hosted matrix was correctly skipped for a
  documentation and skill-instruction change.
- Issue #119 and PR #120 are the M3.5 delivery, merged by rebase at `646cfb5`.
  PR final-head Actions run 31319226328 on `5c91dc3` passed the complete hosted
  matrix — scope classification `full`, GCC and Clang debug, both sanitizers, and
  the aggregate required check. Runs 31318883966 and 31319061179 were superseded
  by later pushes to the same branch and were cancelled.
- **That run took 16m55s against the workflow's 20-minute per-job timeout, and
  issue #122 and PR #123 reclaimed the margin at `a38598f`.** The M3.5 fixtures
  rebuilt the scenario in `setUp` rather than once, running a complete
  28,800-block window for a single assertion. Each run shape is now executed once
  and deep-copied per use in `tests/simulation/uptime_measurement_common.py`,
  matching the convention the economy, escrow, and authority suites already use.
  The model test fell from 58.2s to 13.4s and the cross-model test from 8.2s to
  4.5s, about 49 seconds per preset.
- The measurement that matters is the hosted one. PR run 31321119542 completed in
  15m14s with its slowest job, `clang-sanitizers`, taking 14m52s, so the per-job
  margin is about five minutes rather than three. No assertion, boundary,
  rejection condition, or result code moved, and the suite gained one test rather
  than losing any.
- Two tests deliberately do not use the shared fixture. `test_two_runs_agree` and
  `test_a_prefix_reproduces_the_state_it_held` exist to prove a run is
  deterministic, and a cached run would make both tautologies. The one added test
  guards the risk the change introduces: two callers get distinct objects from the
  same state, and mutating one leaves the other whole.
- M3.5 local evidence: the uptime verifier derives 114 vectors and 91 tests pass
  — 22 slot-grid, 60 model, and 9 cross-model. All ten retained verifiers pass
  unchanged: economy v1 derives 139 manifest and 65 simulator values, manifest v2
  154, simulator v2 189, seat 96, routing 200, escrow v1 169 and v2 172, the suite
  133 v1 and 138 v2, and the cycle boundary 101. The M2 and M3.1 through M3.4
  evidence is intact.
- The uptime verifier fails closed five ways, each confirmed by execution at exit
  1 with the unmutated run as a positive control: a tampered recorded value, a
  recorded key no derivation reaches, a derived key the file does not carry, a
  slot count that disagrees with the founder derivation, and a dispute cap one
  above the grace allowance. The last is the informative one. Raising the cap to
  seven leaves the model internally self-consistent and is still refused, because
  a maximal dispute would then leave a perfect seat 17 slots against an 18-slot
  threshold, and the model asserts that theorem rather than trusting its own
  arithmetic.
- `expected.py` reimplements challenge selection from the specification rather
  than importing it, so a recorded selection is agreement between two
  implementations of the rule. It walks the whole scenario independently and
  derives the credited slots the model must also produce.
- The sampling claim is recorded as a measurement rather than as a probability. A
  seat that answers no challenge at all is still credited for the slots it
  happened not to be sampled in, and that is 9 of 24 in the scenario, 9 slots
  below the threshold, so sampling alone fails a fully absent node.
- One defect was found by self-review before merge and fixed at `646cfb5`. The
  result-code table declared `ARITHMETIC_OVERFLOW` and no path could return it:
  every accumulated quantity is bounded far below `u64` by an earlier condition,
  so an overflow there is a defect rather than a rejectable input and the checked
  arithmetic raises. The code was removed rather than given a fabricated path, and
  result-code coverage is now a recorded vector — the declared count, the count
  produced by execution, and their equality — so a later change cannot quietly
  lose a code or add one no path reaches.
- Issue #114 and PR #115 are the M3.4 delivery, merged by rebase at `7dd6a84`.
  PR final-head Actions run 31308600720 on `7d812bd` and post-merge run
  31309236144 on `7dd6a84` both passed the complete hosted matrix — scope
  classification `full`, GCC and Clang debug, both sanitizers, and the aggregate
  required check. Runs 31308454760 and 31308516536 were superseded by later
  pushes to the same branch and were cancelled. The post-merge run was allowed to
  reach a terminal result before the handoff branch was merged, which is the
  procedure the M3.3b cancellation established.
- M3.4 local evidence: the cycle-boundary verifier derives 101 vectors and 57 new
  tests pass — 24 grid and 33 model. All nine retained verifiers pass unchanged:
  economy v1 derives 139 manifest and 65 simulator values, manifest v2 154,
  simulator v2 189, seat 96, routing 200, escrow v1 169 and v2 172, and the suite
  133 v1 and 138 v2. The M2 and M3.1 through M3.3 evidence is intact.
- The cycle-boundary verifier fails closed four ways, each confirmed by execution
  at exit 1 with the unmutated run as a positive control: a tampered recorded
  value, a recorded key no derivation reaches, a derived key the file does not
  carry, and a model constant that disagrees with the founder derivation. The
  last is the informative one. Forcing the model's commit interval to four
  seconds leaves it internally self-consistent — every division stays exact, both
  identities still hold, and the model's own `assert_exact_derivation` passes —
  and the run is still rejected, because `expected.py` reaches three seconds from
  the pinned M1 configuration without importing anything from `simulation/`.
- One containment vector was corrected during self-review before merge. It
  compared two separately built models, which proves the model is deterministic
  rather than that a rejected activation writes nothing, so it would have passed
  a defect that wrote a height before raising. It now measures one instance
  before and after the rejection attempts; forcing a replayed activation to
  record its height was confirmed to fail the corrected derivation and to pass
  the old one. The recorded value never changed, only the derivation's ability to
  fail. The model test already measured this correctly on a single instance.
- Issue #108 and PR #109 are the M3.3a delivery, merged by rebase at `a8ea180`.
  PR final-head Actions run 31268938270 on `0076d4f` and post-merge run
  31269458528 on `a8ea180` both passed the complete hosted matrix — scope
  classification `full`, GCC and Clang debug, both sanitizers, and the aggregate
  required check. Run 31268730543 was superseded by a later push and was
  cancelled.
- Issue #110 and PR #111 are the M3.3b delivery, merged by rebase at `04cdd23`.
  PR final-head Actions run 31270415727 on `5ba7b14` passed the complete hosted
  matrix; no run on that branch was superseded. Post-merge run 31271049373 on
  `04cdd23` was cancelled mid-flight and re-run to a complete pass — scope
  classification `full`, GCC and Clang debug, both sanitizers, and the aggregate
  required check.
- **`verify.yml` sets `cancel-in-progress: true` on a concurrency group keyed by
  `github.ref`, so pushing the handoff commit to `main` cancels the post-merge
  matrix of the slice just merged.** That is what cancelled run 31271049373; no
  operator cancelled it, and nothing was wrong with the commit. Merge a slice,
  let its post-merge run reach a terminal result, and only then push the handoff.
  A cancelled post-merge run is not evidence of a pass, and re-running it is the
  repair.
- PR #112 recorded this handoff and merged by rebase at `848ba36`, with
  post-merge run 31271183838 passing the focused metadata path; the hosted matrix
  was correctly skipped for a documentation-only change.
- M3.3 local evidence: eight verifiers pass. The suite derives 133 v1 and 138 v2
  vectors; escrow payout derives 169 v1 and 172 v2; the economy derives 139
  manifest and 65 simulator v1 values, 154 manifest v2 and 189 simulator v2; the
  seat verifier derives 96 and the routing verifier 200, both unchanged. 50 new
  tests pass — 19 escrow v2 and 31 scenario v2 — alongside the 57 existing escrow
  and 48 existing scenario tests, all unchanged.
- Both v2 verifiers fail closed four ways, each confirmed by execution at exit 1
  with the unmutated run as a positive control: a tampered recorded value, a
  recorded key no derivation reaches, a derived key the file does not carry, and
  the v2 verifier run against the v1 vector file. The last is the informative
  one for the suite: it fails first on the superseded maximum supply.
- Issue #103 and PR #104 are the M3.2 delivery, merged by rebase at `a0521d0`.
  PR final-head Actions run 31266418185 on `4392d15` and post-merge run
  31266927181 on `a0521d0` both passed the complete hosted matrix — scope
  classification `full`, GCC and Clang debug, both sanitizers, and the aggregate
  required check.
- PR #105 recorded this handoff and merged by rebase at `3d23416`, with
  post-merge run 31267484643 passing the focused metadata path; the hosted matrix
  was correctly skipped for a documentation-only change.
- M3.2 local evidence: the simulator verifier derives 189 vectors and the
  manifest verifier still derives 154; 96 new tests pass — 38 model, 39
  transition-error, and 19 scenario — alongside the 61 existing v2 manifest and
  loader tests. All five retained v1 verifiers pass unchanged, so the M2 evidence
  is intact.
- The simulator verifier fails closed five ways, each confirmed by execution: a
  tampered recorded value, a recorded key no derivation reaches, a derived key
  the file does not carry, a Founder Constitution literal that no longer spans a
  cycle, and a model constant that disagrees with the constitution. The last is
  the informative one: shrinking the model's threshold to 64,500 seconds does not
  merely change a number, it makes the constitution's two stated forms of the
  cycle rule disagree and turns an accepted evaluation into a rejection.
- The research scenario reaches all fourteen modelled result codes, and the
  verifier records that as a derived claim so a later scenario cannot quietly
  lose coverage. Every prefix of a mixed scenario reproduces the state the full
  run held at that point.
- Two guards are unreachable at real scale and are proved present rather than
  reached. A zero equal-split share requires the Founder portion shrunk below the
  winner count, because the smallest possible share at the full 100,000-seat
  capacity is 342,000 atomic units. Arithmetic overflow requires a carry near the
  `u64` maximum, because every channel cap leaves more than double its own size
  in headroom.
- Issue #99 and PR #100 are the M3.1 delivery, merged by rebase at `0c05b52`.
  PR final-head Actions run 31262789135 on `e9de7a7` and post-merge run
  31263319868 both passed the complete hosted matrix — scope classification
  `full`, GCC and Clang debug, both sanitizers, and the aggregate required
  check. Runs 31262577723 and 31262627548 were superseded by later pushes to the
  same branch and were cancelled.
- PR #101 recorded this handoff and merged by rebase at `852e289`, with
  post-merge run 31263846117 passing the focused metadata path; the hosted
  matrix was correctly skipped for a documentation-only change.
- Issues #71, #77, #79, #82, #85, #88, and #91 are the M2 deliveries; PRs #72,
  #78, #80, #83, #86, #89, and #92 are merged.
- After PR #72, commits `de9903e` and `4947c46` replaced the Codex agent layout
  with Claude Code and simplified the authorship rules.
- Issue #77 and PR #78 merged at `9aeac23`. PR final-head Actions run
  30849218092 and post-merge run 30850030514 both passed the complete hosted
  matrix — scope classification, GCC and Clang debug, both sanitizers, and the
  aggregate required check.
- Issue #79 and PR #80 merged at `c03262f`. PR final-head Actions run
  30852439693 and post-merge run 30853305170 both passed the complete hosted
  matrix — scope classification, GCC and Clang debug, both sanitizers, and the
  aggregate required check.
- Issue #82 and PR #83 merged by rebase at `5029c00`. PR final-head Actions run
  30896652965 and post-merge run 30897473243 both passed the complete hosted
  matrix. Squash merge is disabled on this repository; use `--rebase`.
- Issue #85 and PR #86 merged by rebase at `512dc0c`. PR final-head Actions run
  30900989541 and post-merge run 30901790621 both passed the complete hosted
  matrix — scope classification, GCC and Clang debug, both sanitizers, and the
  aggregate required check.
- Issue #88 and PR #89 merged by rebase at `20f7fcf`. PR final-head Actions run
  31012045337 and post-merge run 31013129150 both passed the complete hosted
  matrix — scope classification, GCC and Clang debug, both sanitizers, and the
  aggregate required check. Runs 31011546356 and 31011900980 were superseded by
  later pushes to the same branch and were cancelled.
- Issue #91 and PR #92 merged by rebase at `7b4cd6a`, with post-merge run
  31015245429 passing the focused metadata path; the hosted matrix was correctly
  skipped for a documentation-only change. The preceding handoff merged at
  `bc4272a` with post-merge run 31014389973.
- No delivery branch, open PR, additional worktree, or generated build
  directory remains from any delivery.
- M3.1 local evidence: the v2 verifier derives 154 vectors; 23 manifest and 38
  error tests pass; all five v1 verifiers pass unchanged, so the retained M2
  evidence is intact.
- The v2 verifier fails closed five ways, each confirmed: a tampered recorded
  value, a recorded key never derived, a derived key the file does not carry, a
  manifest that disagrees with the Founder Constitution, and an edit to the
  retained v1 contract table down to one atomic unit.
- The fourth of those is the load-bearing one. `expected.py` imports nothing
  from `simulation/` and restates the constitution's two allocation tables by
  hand in tenths of a display unit. The constitution states the economy twice —
  as per-eligible-cycle amounts and as maximum channel totals — and derives
  neither from the other, so requiring them to agree checks the manifest against
  the founder document rather than against a second reading of the
  specification. A forged manifest and contract table raising the referral to
  34.3 units per cycle, propagated consistently through the referral cap, the
  direct-mint subtotal, and the maximum supply, passes every loader stage and is
  still rejected by four `expected.py` comparisons.
- Every recorded v2 rejection is produced by a live loader run over a minimally
  mutated manifest rather than named, and five pairs carrying two defects at
  once prove which stage reports first. A positive control asserts the same
  entry point accepts the unmutated manifest.
- The vectors prove the supply revision is accounted to the referral channel
  alone: the maximum rose by 1,250,010,000 display units, the referral channel
  rose by exactly that, and the summed change across the other nine channels is
  zero. That sum is taken in atomic units against the retained v1 contract
  table, because summing in display units divided a one-atomic-unit divergence
  to zero and hid what the check exists to find.
- Local evidence: 67 Founder Economy tests, 49 Founder Seat tests, 57 revenue
  routing tests, and 57 escrow payout tests pass; the economy verifier derives
  139 manifest and 65 simulator values, the seat verifier derives 96 values
  while confirming an independent walk of the constitutional rule agrees with
  the model on all 1,000 blocks, the routing verifier derives 200 values while
  confirming an independent replay agrees with the model and with 2,400
  contract share computations, and the escrow verifier derives 169 values while
  confirming an independent walk agrees with the model on all 39 events and
  that three caps match the Founder Constitution; repository metadata and link
  validation, `git diff --check`, and the focused verifier unit tests pass.
- The scenario suite adds 48 tests — 14 multi-year, 15 market, 19 property — and
  133 vectors derived across 107,812 events in four scenarios. Every monetary
  total agrees with a closed-form derivation in
  `tools/scenario-suite-vectors/expected.py`, which imports nothing from
  `simulation/`; changing one constitutional literal there was confirmed to fail
  five vectors, including the maximum-supply accounting.
- All five verifiers fail closed when a recorded vector key is never derived.
  The economy, routing, and escrow verifiers were each confirmed to fail on a
  tampered recorded value. The suite verifier was confirmed to fail three ways:
  a tampered value, a recorded key never derived, and a derived key the file
  does not carry.
- The escrow drain scenario binds the population run's own state digest, so the
  escrows are proved drained of exactly what three seats issued into them across
  their complete 731-cycle windows. The empty-cycle count is recorded three
  times: from the generator's population rule, from the verifier's independent
  restatement of it, and from the trace as closes that credited no seat. The
  third agrees with the other two only because every pool in that scenario
  exceeds its active seat count, which the specification states rather than
  assumes.
- The routing remainder bound is proved, not asserted: the remainder depends
  only on `amount mod 200`, so scanning all 200 residues in both creator cases
  is complete. It is at most 2 atomic units with one creator and 3 with two.
- Routing share arithmetic uses the amount's quotient and remainder. The direct
  `45 * amount / 100` form leaves `u64` above roughly 7.4% of maximum supply,
  so it would have rejected a representable payment as an overflow.
- Escrow custody is fixed at the bind and never rises afterwards, because
  `bind_opening_custody` is the only writer of a custody amount and rejects once
  bound. The vectors record `containment.custody_increases_after_bind=0` and
  `containment.multi_escrow_payouts=0`, both derived by the independent walk.
- The escrow binding proves consistency, not provenance: the model only
  recomputes the supplied economy state's digest, so a self-consistent invented
  state would also pass it. The verifier closes that gap by running the economy
  simulator on its accepted fixture and requiring the escrow fixture to bind
  that exact run. Inside the model, the manifest cap is the defence, and a
  `CUSTODY_ABOVE_CAP` vector exercises it. The specification and ADR 0021 both
  state this split rather than overclaiming the digest check.
- `ARITHMETIC_OVERFLOW` is unreachable through escrow events because the caps
  are far below `u64`. The checked arithmetic is still exercised directly by
  the tests so the guard is proved present rather than assumed.
- The verifier reproduces 2,297 canonical JCS bytes and manifest digest
  `2a8923d40615589cc9c9ef90598c0cec56b72a7efa103cf8c05aceb5b54dc698` from the
  checked-in manifest, and fails closed when a recorded vector key is never
  derived or when any recorded value is tampered with.
- The 731-cycle single-seat scenario reproduces the recorded per-seat schedule
  exactly, including 25,000,200,000,000 Founder-operator and
  1,250,010,000,000 referral atomic units.
- Scope classification correctly selects `full` because Python source, CMake,
  and vector paths are not lightweight metadata.
- No dependency, workflow, C++ source, generated build directory, or additional
  worktree is part of any M2 result.

### Remaining gap

No production escrow, biometric verifier, packaged Founder Node, AI service,
controlled application runtime, resource cloud, bridge, liquidity system,
wallet, public testnet, or mainnet is implemented. Revenue routing and escrow
payouts exist only as independent Python models, not as C++ consensus behaviour.

**The Founder Seat and the issuance schedule are no longer in that list.** As of
2026-08-29 the C++20 kernel executes the seat purchase, the activation, the node
mint, the referral mint, and the cycle assignment that drives them, against
`economy-transition-v7`.

**Version seven's Python evidence is now complete in the sense that matters for
a second implementation.** Every transaction kind it admits has a recorded
version-seven state root and a recorded version-seven receipt, which is the
claim a kernel has to reproduce. That was not true before 2026-08-20 and its
absence is what stopped the kernel move.

**The C++ half is closed and the gap has moved.** The kernel compiles
`economy-transition-v7` in full — the byte and derivation surface, the ledger,
all fourteen transitions, the assignment prologue, and both conservation
identities — and reproduces both version-seven vector files. Requirements 10 and
11 are met.

**As of 2026-09-03 the uptime pipeline is no longer in that list on the Python
side.** `economy-transition-v8` is specified, modelled, and executed, and a
recorded chain derives a cycle assignment from evidence it recorded itself.

**As of 2026-09-05 the whole version-eight kernel exists and nothing above it
does.** M3.13n added `src/v8/` beside `src/v7/` under ADR 0065's staged
replacement and M3.13o completed it, so the kernel compiles two whole economy
contracts and a version-eight chain runs in C++ — measuring its own machines,
deriving a cycle from that evidence, and paying a winner from it. M3.13p then
added `snapshot_v8`, so a version-eight state can be written down, and M3.13q
added `SQLiteLedgerV8`, so one survives the process that produced it, and
M3.13r added `ApplicationV8`, so a consensus engine can drive one, M3.13s added
`protocol-application-v8` and the Go adapter's version-eight client, so an
engine is wired to one, and M3.13t deleted version seven. **All seven enumerated
steps have landed and the repository compiles exactly one economy contract.**

**What is missing now is everything between a durable head and a network.** The
version-eight kernel is wired to a SQLite owning store as of 2026-09-06, so a
state it produces survives a restart. It is not wired to the archive or to the
CometBFT adapter, so no two nodes agree on one. That wiring is requirement 13's
four-node adversarial scenarios, and **both halves landed on 2026-09-11**. Four
replicas agree on the roots a seat purchase and a seat activation produce, and
four replicas independently refuse two transactions the contract rejects.

**Requirement 13 closed on 2026-09-13.** What remained after 2026-09-11 was a
replica refusing a peer's whole *block*, a node restarted mid-block, a partition,
and a replica down while the others kept committing. M3.14c and M3.14d delivered
the first two with a driven `ApplicationV8` beside the network, and M3.14e
delivered the fourth by giving the supervisor a control channel. **The partition
is the one that stays open, and it is a permission rather than a gap in the
work**: blocking a peer's P2P port needs privileges this harness does not have,
and a two-two split would commit nothing on either side, so a stopped replica is
the only fault of that shape a devnet can produce. ADR 0073 records it and the
fixture says which is meant.

**As of 2026-08-31 the first two bricks of it are laid and the gap is two steps
narrower.** A version-seven state can be encoded to canonical bytes and restored
to a ledger that keeps executing, which is what "two replicas agree on one state"
needs before it can be asked; and the owning store makes one durable, so a chain
stopped in the middle of its history resumes on the same trajectory. "Survives a
restart" is now evidence rather than a claim, and the evidence is against
recorded roots rather than against the store's own arithmetic.

**What is left between a node process and a network is one adapter.**
As of 2026-08-31 the whole C++ side exists: the kernel executes version-seven
blocks, the store makes a state durable across a restart, `ApplicationV7`
reconciles a consensus engine's block pipeline with that store and requires the
two to agree about what it did, the transport carries it in frames, and
`protocol-application-v7` is a process that serves them on a socket.

**As of 2026-09-01 the storage side also satisfies the words "and recovery".** A
fault anywhere in the write path leaves the durable head at the pre-block root or
the post-block root, a failed commit recovers by reading the file again, and a
process killed between the commit and its return leaves a state some sequence of
blocks produced. That was the last thing ADR 0057 owed.

**As of 2026-09-01 the Go ABCI adapter exists too, and the gap is no longer
structural.** `adapter/cometbft` reads a version-seven finalized block, bridges
it to ABCI under its own codespace, and initialises a home whose genesis
application state names the ledger version. Every layer between a signed
version-seven transaction and a consensus engine is now built.

**What is missing is the run, and what blocks it is the signatures.** Nothing
has driven a version-seven chain through a real CometBFT process, and no
recorded version-seven transaction could be broadcast to one if it tried:
**every recorded transaction is signed with a stand-in**, an eight-octet counter
padded to 64 octets and recorded in an oracle that verifies by exact-match
lookup. Both traces do it deliberately, so the model implements no cryptography
and every message-binding claim stays testable. But `protocol-application-v7`
opens its store with `ed25519_verifier()` and would refuse every one of them as
`invalid_signature`. Emitting the recorded raw inputs into a vector file would
produce a fixture no chain can accept, so what is owed is a fixture that **signs
for real** — which is what version one has in `tests/differential/cases.py` and
`pinned_sodium`, and what version seven has never needed until now.

**And one gap inside the stack was larger than the adapter, and is now closed.**
Every version-seven layer hands `execute_block` a null uptime schedule, so a
chain run end to end through *that* stack writes no cycle assignment record and
no seat accrues anything: four nodes agreeing on blocks that pay nobody would
satisfy the word "four-node" and not the word "economic". Version eight removed
the parameter rather than supplying it, and as of M3.13s the whole version-eight
stack is wired.

**M3.13j specified the carrier that closes it, M3.13k and M3.13l made it
executable in Python, and M3.13n began putting it into the kernel.**
`economy-transition-v8` and ADR 0063 are accepted: two transaction kinds, two
state entries, twelve result codes, one genesis field, and a block execution of
four ordered steps in which the prologue derives the schedule from state and
`execute_block` loses its `UptimeSchedule*` parameter. A Python model executes
all of it and 617 vectors record it — 183 for the contract and 434 for the
execution — and **as of 2026-09-05 the C++20 kernel reproduces every one of
them**, the codec's 121 and the ledger's 496.

**As of 2026-09-07 a version-eight chain runs under a real consensus engine, and
the stack gap is closed.** M3.13s added `protocol-application-v8` and the Go
adapter's version-eight client, so every layer between a signed version-eight
transaction and CometBFT v0.39.4 exists and is exercised: one node commits three
blocks through a restart, and four independent replicas agree on the roots
through a full restart with three transactions entering through three different
nodes.

**What remains is not a layer but a scenario.** M3.13s's fixture sells no seat,
so the issue and expiry steps evaluate nothing at any height — the version-eight
code path runs, the audit it would perform has nothing in scope. Requirement 13
asks for adversarial *economic* scenarios, and both halves of that are still
owed: **an economic chain** that sells and activates a seat so the pipeline has
subjects, and **disagreement** — a replica fed a block the others refuse, a
partition, a node restarted mid-block. Neither is blocked any more. The
`execute_block` parameter that made an economic chain impossible through the
ABCI path is gone: version eight's prologue derives the schedule, so a chain
driven end to end writes cycle assignment records where version seven's wrote
none.

**Both halves are now delivered and this paragraph is history.** M3.14a built
the economic chain, M3.14b and M3.14c the disagreement, M3.14d the mid-block
restart, and M3.14e the replica down while the others kept committing. Only the
partition remains, and it is a permission this harness does not have rather than
work left undone — see the requirement 13 paragraph above.

**Two contracts were also still owed, and neither blocked requirement 13.**
That was recorded the other way round at the close of M3.12b and M3.13a
corrected it. **One of the two is now delivered.** `calendar-v1` and ADR 0074
fix the consensus timestamp's unit, range, monotonicity rule and two-sided
60-second acceptance tolerance, the proleptic Gregorian derivation from it to a
calendar month, and the rule that the block opening a month is the block closing
every earlier one. The HUB verification architecture of ADR 0048 still needs its
threat model, with the biometric stabilisation scheme named as requiring
independent cryptographic review before anything rests on it.

**What `calendar-v1` does not do is the half that is still owed, and the
division is deliberate.** It derives a month and binds no ledger version, so
**nothing executable uses a month yet** — the rule moved from undefined to
unenforced, which is exactly the posture `cycle-boundary-v1` took and the same
gap it left. The unreferred pool's payout — the candidate set, the ranking
snapshot, the height the payout executes at, and an accrual with no candidate —
is unestablished in versions six, seven and eight alike and is the immediate
successor slice. It is separated from the calendar rather than folded into it
because the calendar's decisions were all delegated and the payout's were not:
two of them were founder-reserved, both were answered on 2026-09-14, and ADR
0075 records them.

**That paragraph is history as of 2026-09-15 and is kept for its reasoning.**
M3.16a accepted `unreferred-pool-payout-v1` and M3.17a accepted
`economy-transition-v9`, which binds both it and `calendar-v1`. **The gap is
therefore no longer that no ledger version applies a month; it is that no code
executes the version that does.** What is owed is the execution model, the
kernel, the stack, and the application-contract version that carries a timestamp
into the application — all of it under "Exact next action".

**As of 2026-09-17 that list is down to the stack alone.** M3.17b and M3.17c
delivered the execution model, M3.18a and M3.18b the kernel, and M3.19a the
application contract. What remains is `snapshot_v9`, the owning store, the
application layer, the transport, the node process and the ABCI adapter — six
ports, no contracts.

**As of 2026-09-19 it is three.** M3.19b delivered `snapshot_v9`, M3.19c the
owning store, M3.20a the transport's request half as `wire_v2`, and M3.20b
`ApplicationV9`. What is left is the transport's **response** encoder and its
dispatcher, the node process, and the ABCI adapter — and all three have
`consensus-application-v2` to satisfy rather than a shape to invent.

**As of 2026-09-21 it is two.** M3.20c delivered the response encoder, its
dispatcher, and the socket overload that serves them. What is left is the node
process and the ABCI adapter.

**Later the same day it is one, and it is all Go.** M3.20d delivered
`protocol-application-v9`, so every C++ piece of a version-nine node exists.
What is left is the adapter's version-two client, its ABCI conversion and
launcher values, and the devnet that runs them. M3.20e delivered the client,
M3.20f the bridge, and M3.20g the launcher values, so what is left is running
it: a version-nine chain under CometBFT, then the four-validator devnet.

**As of 2026-09-24 nothing of the port is left.** M3.20h ran the chain under one
node, M3.20i the four-validator devnet, and M3.20j the skewed replica. What
follows is deleting `src/v8/`.

**One gap is not a port, and it must be settled before any network is expected
to survive an outage.** Under CometBFT `v0.39.4` the first block after an outage
carries the median of precommits cast before the outage. Under the accepted C5,
a version-nine chain whose quorum is down for more than 60 seconds therefore
halts at its next height for good.
[ADR 0089](../decisions/0089-a-version-nine-chain-resumes-only-inside-the-tolerance.md)
records the pinned-source evidence and three candidates. The first takes C5's
behind side from BFT time rather than the machine's clock. The second moves to
an engine whose proposer stamps its own clock. The third is ADR 0088's
exemption generalised, which collapses into the first. Each is a new contract
version, because `consensus-application-v2` freezes the acceptance rules. It
blocks no current slice: the devnet can restart a network inside the window.
**It blocks any claim that a version-nine network recovers from an outage.**

**One of those absences now carries a dependency rather than only a roadmap
position.** The founder answer of 2026-08-16 makes external purchasability the
permanent funding path for a new participant once the entry airdrop's
1,000,000-identity bound is reached. Until a bridge or an external venue exists,
the airdrop is the *only* path by which a person who holds nothing can make their
first transaction, so **external purchasability has to exist before the millionth
identity registers**. No transition can enforce that ordering; it is a sequencing
constraint on the bridge and liquidity milestones, and it is recorded here so a
later session does not rediscover it from an `INSUFFICIENT_BALANCE` vector.

All sixteen requirements of `goals/m2-founder-economy-proof.md` passed against
`founder-economy-manifest-v1`. What that does and does not establish is stated
in `founder-economy-report-v1.md` rather than summarized here.

Two qualifiers mattered for M3, and both are now closed as specifications. The
models represented a cycle as a deterministic integer index with no wall clock
reachable from a transition, but that index was not bound to a chain-defined
quantity; M3.4 defines the binding. And the direction the M2 models implement was
superseded on 2026-08-07, so their accepted schemas, vectors, and digests are
evidence about a contract the constitution no longer directs; M3.1 through M3.3
restated it.

Closing them as specifications is not the same as closing them in the models.
`cycle-boundary-v1` defines the mapping and the check, and nothing applies it
yet, so `founder-economy-simulator-v2` still cannot tell whether a supplied
window is the correct one for a seat's cycle. The gap moved from undefined to
unenforced.

M3.1 restated that contract, M3.2 made it executable, and M3.3 rebound every
dependent to it, which closes the second qualifier. `escrow-payout-v2` and
`economy-scenario-suite-v2` bind version two; the seat and revenue-routing models
needed no change, which was re-proved rather than assumed — neither imports either
economy package, and neither carries a supply figure, channel cap, channel
identifier, referral amount, or issuance-cycle count. The retained v1 contracts,
models, vectors, and digests remain in place and passing as the M2 evidence.

M3.2 supplies the activity and reallocation computation that three removed
placeholders used to stand in for, and M3.5 supplies the measurement that
computation reads. The challenge construction, sampling rate, dispute window
length, dispute resolution, and record completeness are now specified, and the
cycle boundary was specified by M3.4. The month definition for the unreferred
pool and that pool's payout, tie, and remainder rules remain unspecified; accrual
into the pool is modelled and paying it out is not.

**What M3.5 does not establish is one undecided value, not an oversight.** The
challenge *protocol* is specified and the challenge *content* is not, so an
answered challenge proves that something able to produce it was reachable within
sixty seconds. That is liveness of a responder rather than possession of a
resource, and every anti-gaming property the specification claims inherits that
limit. The concrete resource commitment — what a Founder Node must prove it holds
— sets what an operator must own in order to be paid, so it is founder-reserved
and belongs to the Founder Node and resource-network milestone rather than being
invented here.

Three further claims are design intent rather than proof and go to the
independent review of requirement 15. The pipeline consumes duty reports and does
not derive them, so a chain that fails to report an assigned duty credits a seat
that did not perform it. A proposer with influence over the state root at
`h - 1` has some influence over who is challenged at `h`, which is the same
adversary ADR 0027 refers to review for the block production rate. And whether a
sampling margin that catches a lost slot about 63% of the time is adequate
against a founder with physical machine access is the question ADR 0023 already
records as unreviewed.

M3.3 exercised that input at multi-year scale without narrowing the gap. The
scenario suite supplies a `cycle_window` by generator convention — the tick — and
supplies every `uptime_seconds` value it then derives verdicts from. A suite that
conserves value under supplied measurements is evidence about the derivation, not
about the measurements. Its winner is also deliberately unique in every window,
so the tie and remainder paths of the reallocation rule are covered by
`founder-economy-simulator-v2`'s own vectors rather than by the suite.

M3.4 made that tick convention checkable without yet checking it, and M3.6c
turned it into a checked rule. The generator now supplies an activation height
per seat and derives every window from the accepted grid, and a window it got
wrong would be rejected rather than ranked. **The supplied `uptime_seconds`
values are unchanged in status.** Completeness is enforced, so a record can no
longer omit an in-scope seat, but every measurement in the suite is still a
fixture and nothing here shows one reflects a real machine.

M3.6b narrows nothing about that. The escrow model reads one recorded economy
state by digest and evaluates no window, so rebinding it proves that escrow
accounting survives an enforced schedule and proves nothing about the suite's
supplied windows.

M3.4 established nothing about measurement and M3.5 does. The grid states how
many blocks a window holds; the pipeline states how a seat earns them. Requirement
12 is now answered in two parts — 800,000 bytes for the activation schedule and
800,000 bytes for per-cycle uptime records at full seat capacity — leaving
per-seat balances and escrow recipient balances open.

**Specified became enforced on 2026-08-10, and only for the newest contract.**
`founder-economy-simulator-v3` applies `cycle-boundary-v1`'s window check and
rejects a record whose seat set is not its window's in-scope set, in either
direction, so the two gaps M3.4 and M3.5 each closed at one end are now closed at
both. `founder-economy-simulator-v2` is unchanged and still records them, which
is correct: it states what the M3.2 and M3.3 evidence proves, and that evidence
was taken against a model that did not check.

What enforcement does not do is make a schedule right. Version three proves that
a supplied window is the window the accepted grid assigns and that a record covers
the population the accepted schedule says was running. It proves nothing about
whether that population was operational, whether the duty reports behind a
measurement are complete, or whether the beacon that selected a challenge was
unbiasable.

One residue is recorded rather than closed. Completeness is measured against the
seat table as it stands, and the model has no current height for an evaluation,
so it cannot require that every in-scope seat has already activated. A chain
closes that by ordering, since a record is emitted only after its window is
final; the activation-height monotonicity rule bounds the residue to an event
ordering a chain does not produce.

**M3.8a moved the whole milestone from modelled to specified-for-consensus, and
that is a different kind of claim.** Everything before it was a Python model
that activates nothing; `economy-transition-v2` states what independent nodes
must reproduce byte-for-byte. What it does not do is execute: no C++ implements
it, no node has run it, and the cross-language agreement of requirement 11 is
exactly the check that would catch an encoding defect the code mapping cannot
see. The encoding is checked against the accepted M1 vectors and against the
economy model's declared code set; it is not checked against an implementation,
because there is none.

**And it is specified into a state that cannot be operated.** All three
authorization predicates are named and undefined, so on a conforming chain no
seat can be activated and no permission can be evaluated, exercised, or accrued.
That is a deliberate refusal rather than an oversight: which senders a predicate
accepts sets what an end user must do and own in order to participate and be
paid, which is founder-reserved. Two consequences are worth separating. The
economy's *accounting* is now proved at four levels — contract, model, enforced
schedule, and canonical bytes — and its *access* has never been specified at
any level.

**M3.8b closed that access gap for every path except one, and it is still not
execution.** `economy-transition-v3` defines who may act for a seat, what a mint
credits, when a seat stops accruing, and what a referrer must hold, so a
conforming version-three chain can be operated end to end apart from kind 6.
What version three does not do is execute: no C++ implements it, no node has run
it, and the cross-language agreement of requirement 11 is still exactly the check
that would catch an encoding defect the code mapping cannot see.

**Three limits version three adds are recorded rather than closed.** A
compromised manager address keeps mint authority permanently, because the
constitution names manager addition as the remedy for a *lost* address and
decides nothing about a *stolen* one; the founder's only defence is to switch
protection on, and only for value not yet minted. The chain does not check that a
HUB uniqueness hash reaches at most one account, so HUB verification is exactly
as strong as the off-chain verifier — where the seat biometric hash already
stands. And the ecosystem verifier key now gates protected mints and manager
additions as well as entry, so its unavailability stops more than it did in
version two, though only for seats whose operators chose that.

The bootstrap is a second gap of the same kind, found while deriving genesis. A
chain with no genesis allocation and a nonzero fee cannot execute its first
transaction, and every path to a first payable balance is external, so the fee
policy and the funding path are bridge-milestone work rather than settled here.

Restart equivalence is state equivalence under replay. It is not persistence,
crash-consistency, or a snapshot format, and no model has any of those.

The four models are only partly joined. The escrow model is the only one that
binds another: it takes opening custody from a recorded founder-economy state by
digest, a one-way read that changes nothing in the economy model, and the
scenario suite exercises that binding against a complete 731-cycle population run
rather than a small fixture. Versions two and three of both preserve exactly
this, and no more. The
others remain unjoined. A seat purchased in the sale model is not an activated
seat in the economy model, and a seat identifier in a routing snapshot is not
proved to be either. M3.4 narrowed that and M3.6a narrows it further: a seat's
schedule given an activation height is defined, and the economy model now records
that height, so what remains unsettled is only what authorizes an activation —
the payment, enrollment, and biometric preconditions. Enrollment, biometric
identity, managers, and same-cycle liveness proof for a performance recipient
are not modelled, and the last of those cannot be without the unresolved
performance policy. The per-principal seat bound is not yet a per-human bound.

Routing and escrow payouts prove accounting, not policy. Nothing shows that the
activity metric is fair, that a snapshot reflects a real machine, that a creator
or product is legitimately approved, that the transaction-fee amount rule is
sound, that any AI evaluation is well made, that an approval threshold is safe,
or that a payout recipient is legitimate. The per-seat balance carry has no
storage bound at 100,000 seats, escrow recipient balances have no storage bound
either, and no claim or push mechanism moves a credited balance into a spendable
account. An escrow capability is modelled as a record; the signed envelope,
replay domain, and encoding that would carry one on a real chain are undefined.

### Exact next action

**Trim this document.** It is over 5,500 lines, the owner flagged its regrowth
on 2026-10-03, and every session must read it first. The plan that fits:

- Move everything from `## Phase` to the end into a new final section of
  [`delivery-log.md`](delivery-log.md), verbatim, with each heading demoted one
  level. No anchored link points into this document, and its relative links
  resolve from the log's directory.
- Rewrite this document to the present, in about 300 lines: M4's requirements
  as a status table, what works now, the founder direction as the constitution
  now states it, the repository and verification facts, the remaining gap, the
  next action, and the current founder-reserved list. Several passages here are
  stale and must not be carried over: "What works now" gives
  `economy-transition-v9-execution.txt` 125 vectors where it holds 162, and
  "Adopted founder direction" still describes seat addresses and sixteen
  managers, which ADR 0041 superseded.
- Make the bound mechanical. `tools/verify_metadata.py` should refuse this
  file above a line limit, such as 600, and `CLAUDE.md` should say that a slice
  rewrites the sentences it makes false and records its narrative and gate
  result in its delivery record. The audit's 125-vector figure needs the same
  dated correction.

It is a Python source change, so it takes the full matrix.

**Then M4's next slice, and two questions for the owner.** ADR 0048 makes a
registration valid only under the key of an active, attested Founder Machine,
and the constitution says capture runs "on the founder's own Founder Machine".
Neither says whose machine verifies a person who owns no Founder Machine — an
ordinary user, a creator, or a developer, all of whom must be verified — nor how
the first registrations happen before any seat is active. Both decide what a
participant must do or own to join, so ask them, batched, when requirement 3's
registry becomes the nearest slice. Requirement 7's threat model and
requirement 4's test verifier are unblocked meanwhile.

**One finding from M4.2c bears on a later slice.** A seed's stamps below its
head are free as long as C2 holds, because a restore never applies C5. That
also removes the clock wall from the kind-22 monthly pool mint, the M3 evidence
ADR 0090 left below the engine. A seed history whose early windows open in an
earlier month than its head can close that month, by about height 144,000, and
leave a claim for a network to mint.

**The candidates behind those are unchanged and none is blocked**:

- drive the C++ kernel over the `economy-scenario-suite-v4` population against
  its seven pinned roots;
- ADR 0089's outage wall.

**M4.2c delivered what stood here before it**: a kind-4 and a kind-18 mint
on a seeded four-validator network.

**M4.2b delivered what stood here before it**: a four-validator network
launched from a seeded head, ADR 0097.

**M4.2a delivered what stood here before it**: choosing a route and seeding
a store from a snapshot, ADR 0096.

**M4.1 delivered what stood here before it**: a test Founder's lifecycle on
the four-validator devnet.

**M3.21d delivered what stood here before it**: requirement 16, closing M3.

**M3.21c delivered what stood here before it**: `economy-scenario-suite-v4`,
meeting requirement 14's multi-year leg.

**M3.21b was inserted ahead of it**: the referral-mark repair that designing
the suite surfaced.

**M3.21a delivered what stood here before it**: M3's exit audit, which found
requirement 14 unmet.

**M3.20l delivered what stood here before it**: the orphan referral balance
refused at restore, and the anchor-fragment gap in `tools/verify_metadata.py`
closed.

**M3.20k delivered what stood here before it**: deleting `src/v8/`, with
`economy_v9_fuzz` added first and ADR 0082 corrected.

**Everything below this paragraph is the accumulated history of how the slices
that led here were chosen, newest reasoning last.** It is kept because the
reasoning outlives the slices, and it is *not* a list of what to do next: the
sentence directly above is. Several passages in it name a "nearest slice" that
has since been delivered, and each says so where it stands.

Requirement 13 is **complete** and `calendar-v1` is **accepted**. The nearest
slice that moves the product is the **unreferred pool's payout**, and it is
**unblocked**: all three of its founder-reserved decisions were answered on
2026-09-14. Two were raised at the close of M3.15a and
[ADR 0075](../decisions/0075-founder-answers-on-the-monthly-pool-candidate-set-and-carry.md)
records them — the candidate set is every seat in scope at any point in the
month, ranked on the uptime it accumulated during that month, and an accrual
with no candidate carries to the earliest subsequent month that has one. **The
third was found while reading `economy-transition-v7` to start the slice**, was
not surfaced when the first two were asked, and is the accumulation cap: it does
**not** filter the monthly ranking, so a seat at the cap competes and can win.
[ADR 0076](../decisions/0076-the-monthly-pool-ranks-every-in-scope-seat.md)
records it and corrects the two accepted forward references that said otherwise.

**The complete monthly candidate set, stated once so the payout slice does not
reassemble it from three ADRs:** every seat whose 731-cycle span overlapped the
month, ranked on the uptime it accumulated during that month, exact ties sharing
equally, **no minimum, no duty gate, no accumulation-cap filter**. An accrual
with no candidate carries to the earliest subsequent month that has one.

**M3.15b split this document.** Every `How ... was delivered` record is now in
[`delivery-log.md`](delivery-log.md), moved verbatim, and this file is a little
over 4,300 lines rather than 8,140. `CLAUDE.md` now says to write a slice's
record there rather than here, so the document does not regrow.

**M3.16a delivered the payout on 2026-09-14**, so the sentence above about it
being the nearest slice is history. `unreferred-pool-payout-v1` is accepted: the
candidate set, the ranking figure, the attribution rule, the tie split, the
remainder, the carry, the settlement point, and the quantities a binding version
must carry. **The nearest slice is now the ledger version that binds both it and
`calendar-v1`**, described below.

**Two things M3.16a found are worth carrying forward rather than rediscovering.**
The payout fires at the first assigned window of a later month and **not** at the
block that opens a month — a window is assigned two windows after it opens, so a
month's last windows are unassigned when the next month begins, and the obvious
rule would rank every seat on a month missing its last two days. And the carry
ADR 0075 decided is **unreachable** once a seat is activated, because in-span
implies in-scope and in-scope never expires; that also closes by derivation the
one case ADR 0075 left open.

**M3.17a specified the binding version on 2026-09-15**, so the sentence above
about it being the nearest slice is history too.
[`economy-transition-v9`](../specifications/economy-transition-v9.md) and
[ADR 0077](../decisions/0077-the-version-nine-clock-and-monthly-settlement.md)
are accepted.

**M3.17b made its contract half execute the same day.**
`simulation/economy_transition_v9/` is eight modules, 213 vectors are recorded,
and two ctest entries gate them.

**M3.17c made a chain run it on 2026-09-16, and the unreferred pool paid somebody
for the first time.** It has accrued since `economy-transition-v3` and nothing
had ever taken value out of it. Six more modules, 125 execution vectors over two
scenarios, and [ADR 0078](../decisions/0078-the-version-nine-execution-model.md).

**M3.18a put the codec into the C++20 kernel the same day and M3.18b put the
ledger there**, so the sentence that stood here calling the kernel the nearest
slice is history: the kernel is delivered and **the nearest slice is the
application contract**. Twenty-two sources under `src/v9/`, of which nineteen are
version eight's rebound and **seven have an empty normalising diff** against
their originals.

**M3.19a accepted that contract on 2026-09-17**, so the sentence above is history
too and **M3.19b delivered `snapshot_v9` the same day**, which makes this sentence
history in turn: **the nearest slice is `SQLiteLedgerV9`**.
[`consensus-application-v2`](../specifications/consensus-application-v2.md) and
[ADR 0079](../decisions/0079-the-version-nine-application-contract.md) settle all
five requirements `economy-transition-v9` left open, and **version nine now owes
no contract at all** — everything remaining is a port.

**M3.19c delivered the store on 2026-09-19**, so that sentence is history too and
the nearest slice is the application layer, which the paragraph at the head of
this section states. Three sources, two suites, two ctest entries, and
[ADR 0081](../decisions/0081-the-version-nine-owning-store.md).

**M3.20b delivered the application on 2026-09-19**, so the sentence naming it the
nearest slice is history: two translation units, a 693-line suite, one ctest
entry, and
[ADR 0083](../decisions/0083-the-version-nine-application-reads-one-clock.md).

**M3.20a took the frame off the front of that slice the same day.** `wire_v2` is
the version-two local application frame and
[ADR 0082](../decisions/0082-the-version-two-application-frame.md) records it.
**It is the first version of this protocol ever to use its own version field** —
version seven changed the finalize response's shape, version eight kept it, and
the version stayed at `1` through both, so the refusal landed at the result count
on the first block rather than at the header on the first frame. It lands at the
header now, and version one's decoder refuses a version-two frame for the same
reason without a line of new code.

**M3.20c delivered the transport on 2026-09-21**, so the sentence that stood at
the head of this section naming `response_v9` and `dispatcher_v9` is history:
two sources and two headers, a socket overload that reads version-two frames,
a transport suite over three translation units, one ctest entry, and
[ADR 0084](../decisions/0084-the-version-nine-transport.md).

**M3.20d delivered the node process the same day**, so the sentence that stood
at the head of this section naming `protocol-application-v9` is history: one
source, a version-two Python driver, a headless test that starts the binary six
times against the real clock, one ctest entry, and
[ADR 0085](../decisions/0085-the-version-nine-node-process-binds-the-platform-clock.md).

**M3.20e delivered the Go local client the same day**, so the sentence that
stood at the head of this section naming it is history: `ClientV9`, the
version-two decoders, their tests and fuzz target, and
[ADR 0086](../decisions/0086-the-go-local-client-speaks-the-version-two-frame.md).

**M3.20f delivered the bridge's conversion the same day**, so the sentence
that stood at the head of this section naming it is history: the time on the
local interface, the conversion and `LocalV9`, the logged decision, and
[ADR 0087](../decisions/0087-the-bridge-carries-the-engines-time.md).

**M3.20g delivered the launcher values on 2026-09-22**, so the sentence that
stood at the head of this section naming `nodeconfig` and the identity is
history: `ProtocolV9`, the stamp on the identity, `genesis_time` in both genesis
writers, the exact per-version identity parse, `-genesis-timestamp`, and
[ADR 0088](../decisions/0088-the-launcher-derives-the-genesis-time-and-the-first-block-carries-it.md). **Reading the pinned engine to write it found that block 1's stamp is
the genesis time itself**, which the paragraph at the head of this section
carries forward.

**M3.20h delivered the single-node chain on 2026-09-24**, so the sentence that
stood at the head of this section naming it is history. Delivered: a live
fixture over a caller-stamped genesis and its own ctest entry, a run that
computes every block from the engine's committed stamp, the helpers' version-nine
identity and `Info`, and
[ADR 0089](../decisions/0089-a-version-nine-chain-resumes-only-inside-the-tolerance.md).
**Reading the pinned engine for its restart found that ADR 0088's height-one
halt holds at every height after an outage of a quorum**, which "Remaining gap"
now carries.

**M3.20i delivered the four-validator devnet the same day**, so the sentence
that stood at the head of this section naming it is history. The run is version
eight's scenario with the model following each committed stamp. Every audit now
compares the durable stamp in all four stores. The driven replica also refuses a
stamp that runs backwards as status `8`.
[ADR 0090](../decisions/0090-the-version-nine-devnet.md) records it. **It also
settled the devnet's one open question the way the handoff recommended:** the
kind-22 mint's evidence stays in `economy-transition-v9-execution-cpp`, below the
engine, behind the height wall (ADR 0071) and the clock wall (M3.20g), and
`consensus-application-v2`'s evidence list carries a correction note. It also
settled ADR 0087's owed choice: the durable stamp is compared by the independent
audit, which reads it over version two's Info, and the live health check
compares the root, which commits to the stamp.

**Three things M3.19a settled that the ports must not re-open.** The C++
application reads its own clock, once per `ProcessProposal`, and the local
protocol never carries a clock reading — a bridge-supplied reading could make a
machine silently vote against its own rules forever, because C5 is never
re-checked. A timestamp failure reaches **two** spaces, not one: an eight-value
decision under a zero status at `ProcessProposal`, because a bad stamp from a
peer is ordinary and a nonzero status would let one malformed proposal stop a
correct machine; and a fatal status `7` or `8` at `FinalizeBlock`, because that
path only runs on a block the network already decided. And there is deliberately
**no status for either C5 condition**, so a conforming test asserts an absence.

**One thing M3.19a found is worth carrying forward.** Version seven added a block
identifier to the finalize response, version eight kept it, **the frame version
stayed at `1`, and no contract document recorded it.** It is not a silent
misparse — both decoders are correct and version one's refuses at the result
count — but the refusal lands on the first block as a generic protocol failure
where it should have landed on the first frame as an unsupported version. It was
found by reconciling version one's message table against `response_v8.cpp` rather
than against version one's prose, which is the second time a figure that looked
like framing turned out to move with the version; ADR 0068's receipt magic prefix
was the first.

**M3.19b put a version-nine state on disk on 2026-09-17.** Three sources, a
five-file suite, a fuzz target, ADR 0080, and two new ctest entries — 171 in the
debug presets and 180 under `clang-sanitizers`. **Version nine adds no snapshot
parameter**, because the one genesis field it adds is committed to by `chain_id`,
which is already compared; the dispute authority key needed one for exactly the
opposite reasons, and ADR 0080 states the two together so the asymmetry reads as
a rule.

**Two things M3.19b found are worth carrying forward.** An out-of-range timestamp
**cannot reach the conservation gate at all**: `state_root` refuses to compute a
root over a stamp C1 would have refused, so the payload cannot be built and the
restore refuses at gate 1 instead. The range rule is enforced by the root's own
totality rather than by a gate that could be removed. And the first candidate
failed all four presets on a fixture defect — eleven `reseal()` calls the port
added that version eight's suite deliberately does not have, three of them on
payloads with no root to seal with. **Version eight had already encoded the right
rule by omission**, and reading a neighbour's omissions is harder than reading
its code.

**M3.18b delivered the ledger on 2026-09-16.** Ten more sources, a second ctest
entry, and the first C++ chain that closes a month. **Three of its mutation
probes passed and each named a real gap rather than a bad probe**: the recorded
chains never produce a nonzero remainder, never have a candidate that ran nothing
lose to one that did, and never reach a share that rounds to zero — so discarding
a carry, deriving the candidate set from the figures, and writing a zero claim
all changed no recorded value. Two functions of derived checks close that, and
they are the reason to keep running probes against a fixture rather than only
against code.

**Two things M3.18a found are worth carrying forward.** The contract vector file
did not hold the **state-root non-collisions** the specification's own
required-vector list asks for — it had the seven chain-identity ones and none for
the root — so the slice added them, together with the pair of states differing
only in the timestamp. Without that pair the root could ignore the field
entirely and every other vector would still pass, because they all hold one
timestamp. And a recorded boolean was named for a count it did not establish:
`genesis.twelve_entries_are_version_eights_unchanged` compares thirteen entries,
and is now named for thirteen.

**Three things M3.17a found are worth carrying forward rather than
rediscovering.** The winner's award is a **per-seat running balance** rather than
the per-month claim this document had recorded, because the owner's M3.8a rule
already decides how many transactions a participant needs in order to be paid.
**Exactly one month can close per assignment**, so the settlement is a single
pass rather than a loop over closed indices — iterating them would make one
block's work proportional to how long the network was down. And **committing the
timestamp to the state root is forced by restart** and costs the challenge
beacon: a proposer gains about `2^16.9` timestamp values to grind over on a quiet
block, which is quantified, referred to the review ADR 0027 already owes, and
**not** mitigated by excluding the timestamp from the beacon, because that would
cost a second root construction on the pipeline's most adversarial path.

**M3.14e is delivered and merged.** Issue #283 and PR #284 stopped one replica
of the real four-node chain, required the remaining three to be a healthy
network in their own right, committed two transfers through two of them, opened
the departed replica's own store to prove it was genuinely behind, brought it
back, required all four to agree, and had the returning replica submit the next
transaction itself. The details are under "How M3.14e was delivered".

**What requirement 13 now has, stated once so no later slice re-proves it.**
Four independent replicas agreeing on a success and on two named refusals;
two full restarts with four durable C++ audits per stop; one replica interrupted
mid-block and fed a block its peers never proposed; and one replica down while
the others committed, catching up on return. **The only fault of this shape left
untested is a genuine network partition**, which needs privileges to block a
peer's P2P port that this harness does not have — recorded in ADR 0073 and in
the fixture rather than left to be rediscovered.

**The recorded successors, in order, each its own slice:**

* **The binding version is specified and it executes in Python.** M3.17a
  accepted [`economy-transition-v9`](../specifications/economy-transition-v9.md)
  and [ADR 0077](../decisions/0077-the-version-nine-clock-and-monthly-settlement.md)
  on 2026-09-15, M3.17b modelled the codec, the calendar rules and the settlement
  arithmetic the same day, and M3.17c made a chain run the whole transition on
  2026-09-16, and M3.18a and M3.18b put the whole kernel into C++20 the same day.
  **M3.19a accepted the application contract on 2026-09-17, M3.19b delivered
  `snapshot_v9` the same day, and M3.19c delivered `SQLiteLedgerV9` on
  2026-09-19**, so the three sentences that stood here naming each of them the
  nearest slice are history; M3.20a delivered the version-two frame and M3.20b
  `ApplicationV9`, both on 2026-09-19, and M3.20c the transport — `response_v9`,
  `dispatcher_v9`, and the socket overload — M3.20d the node process, and M3.20e
  the Go local client, and M3.20f the bridge on 2026-09-21, and M3.20g the
  launcher values on 2026-09-22, and M3.20h a version-nine chain under one
  CometBFT node, M3.20i the four-validator devnet, and M3.20j the skewed replica
  on 2026-09-24, the last item of `consensus-application-v2`'s devnet evidence.
  **The nearest slice is deleting `src/v8/`.** The
  paragraphs that stood here enumerating what the binding version had
  to add are superseded by the specification itself and are not restated; three
  of them were **wrong**, and the corrections are the reason to read the
  document rather than this list.

  **Three things this document told the binding slices that were wrong, and all
  three are now corrected in place.** The winner's award is a **per-seat
  running balance**, not the per-month-per-seat claim recorded here — the owner's
  M3.8a rule that a mint takes everything with no quantity choice already decides
  how many transactions a participant needs in order to be paid, so a per-month
  award would have charged `n` fees for `n` months. And the live window-month
  records number **two**, not the three `unreferred-pool-payout-v1` sized for,
  because version nine deletes the oldest in the same prologue that assigns it.
  And the specification's own first draft said to add a winner's share to its
  claim "creating the entry if absent" without qualification, which **creates a
  zero-valued entry when the share rounds to zero** — up to 100,000 of them in
  the zero-best month. M3.17b found it by reading the payout model before
  writing a new one, and corrected it before anything depended on it.

  **What the kernel must reproduce, because the Python model already fixes it.**
  The four entry kinds, the widened kind-12 value, the 150-octet genesis and its
  sixteen entries, the 154-octet header and its re-versioned identifier, kind
  22's body, ladder and mint message, the five calendar rules, the settlement
  arithmetic, the six-step prologue, and the root that commits to the timestamp —
  all in `simulation/economy_transition_v9/`, with **364 vectors** behind them
  across two files. **Version nine adds no result code.** Every item in that list
  is delivered: M3.18a is the codec and M3.18b is the ledger.

  **The prologue at an assignment height runs:** derive the sequence, version
  seven's settlement steps 1–7, settle the closing month, settlement step 8,
  accumulate the figures, then delete the kind-19 **and kind-20** entries for the
  due window. At every window-opening height, including those below the
  assignment lag, the opening window's month is written. **A C++20 implementation
  may hold its state however it likes**; what it must reproduce is the
  projection, the root, and the order.

  **Two of those orderings behave differently and ADR 0078 says which.** The
  payout before the accrual is **observable** — running the rejected one reaches a
  different root, and a vector records it. The accumulation before the deletion is
  normative and **unobservable** under any implementation that derives the
  window's seat sequence once, which every conforming one does; the vector records
  the equality with its reason, and that is the place a lazy implementation would
  be noticed.

  **`advance_to` carrying the timestamp is the shape of defect to watch for in
  the kernel too.** A path that advances a height and leaves the stamp behind
  commits a root naming a height the stamp does not belong to, and every later
  block still satisfies C2 because the stale stamp is smaller — a wrong root
  rather than a refusal. The Python model records the one place it is observable;
  a kernel needs its own.

  **The settlement is a single pass and M3.17b proved it rather than assuming
  it.** Exactly one month can close per assignment, because every index between
  the cursor's month and the new one is empty by construction. No invariant over
  a single accepted state separates the single pass from the loop — they agree on
  every state both produce — so the vectors settle a multi-month halt **both
  ways** and require agreement state for state. **The stronger evidence is
  against an accepted artifact**: version nine's *skipped* months are exactly the
  accepted payout model's *carried* ones over the recorded run, and the two reach
  identical claims.

  **One thing about the contract fixture the execution half cannot inherit.**
  The recorded window sequence is **sampled** — 0, 1, 2, 3, 4, 33, 63, 155 —
  which is legitimate for a fixture about arithmetic and is not a claim about a
  chain. A real chain assigns **every** window, because heights are consecutive
  and the prologue runs at every window-opening height; a halt moves the
  timestamps and not the heights. The execution fixture cannot sample.

  **Two figures the two input specifications still hand it**, so it does not
  recompute them: a proposer can move a month boundary by at most **20 blocks**,
  and a seat's 731-cycle span touches at most **25** calendar months.
* ~~An application-contract version is owed~~ — **delivered by M3.19a on
  2026-09-17.** `consensus-application-v2` and ADR 0079 are accepted, so the
  entry that stood here calling it a real dependency is closed. What it settled
  and what the remaining ports must not re-open is under "Exact next action";
  its required-evidence section is the acceptance criteria for the application
  layer, the transport, the node process and the ABCI adapter;
* the two slices **ADR 0071 named and deliberately did not start**, either of
  which would let a network reach the uptime audit. A **nonzero initial height**
  is a `change-protocol` matter: the state root commits to the height, three
  layers refuse anything but 1 on purpose, and admitting another value means
  deciding what a genesis at a nonzero height *is*. A **snapshot-seeded devnet**
  is a node-process matter: `snapshot_v8` can already express a ledger at any
  height and ADR 0066's restore gates already check one, but
  `protocol-application-v8` takes a database, a genesis, and a socket, so there
  is no supported path to start from a restored state. Neither is urgent; both
  are written down so a later session does not rediscover them as obstacles;
* the HUB verification architecture of ADR 0048, which needs its threat model,
  with the biometric stabilization scheme named as requiring independent
  cryptographic review before anything rests on it. **It now has a dependency
  pointing at it**: version eight's `dispute_authority_key` is a single key
  standing in for the per-machine attestation registry that ADR 0048 defers, and
  the registry is what ends the interim.

**What the devnet harness can now do, so the next slice does not re-read it.**
`adapter/cometbft/internal/devnet` is seven files. `supervisor.go` holds the
`supervisor` struct, `Run`, the `supervise` loop, and the per-replica lifecycle;
`readiness.go` holds the four `await*` helpers, **every one of which reads from
`events` and may therefore only be called on the main loop**; `control.go` holds
the socket, the line parser and `SendControl`; `replicas.go` holds the subset
type. A replica's three children are addressable as `phases[phase][index]`. To
stop one from a test, call `control_replica(network, "stop", index)` in
`tests/integration/cometbft_devnet.py`, and pass `running=(...)` to
`run_health`, `run_transaction` and `run_refused_transaction` for as long as it
is down.

**The offline Go check is worth rebuilding rather than re-deriving.** A scratch
module declaring `go 1.23` and the real module path, with
`replace github.com/cometbft/cometbft => ./stub/cometbft` and a hand-written
`internal/nodeconfig` stub, type-checks and **runs** the devnet package's tests
in seconds. Two things make it work: **`GOPROXY=off`**, so an accidental
resolution fails instead of downloading 173 MB, and a one-line shim for
`t.Context()`, which needs Go 1.24 and is the only thing in the test files this
machine's Go 1.23 cannot compile. It caught two defects in M3.14e that would
each have cost a hosted round trip.


**What this document twice called a flake was a defect, and M3.14d fixed it.**
Three hosted runs have failed with `devnet transaction failed: RPC
broadcast_tx_commit: context deadline exceeded` — M3.13k's merge commit on
`main` in `clang-debug`, M3.13q's merge commit `95be298` in `gcc-sanitizers`,
and M3.14d's first candidate `5e0f6ea` in `clang-sanitizers` — and the standing
advice recorded here was to re-run the job and treat it as a defect only if it
reproduced. **It reproduced on the third occurrence, and the cause was in the
message all along.**

`newRPCClient` set `http.Client{Timeout: 4 * time.Second}`.
**`http.Client.Timeout` bounds the whole request and wins over a longer
context**, so the `-timeout 90s` every caller passes could never apply — the
error says `Client.Timeout exceeded`, not that the context was cancelled.
`broadcast_tx_commit` blocks until the transaction is in a committed block, and
`TimeoutCommit` is **three** seconds, so a transaction arriving just after a
commit spent most of the four before the engine had begun the next block. On a
loaded or sanitized runner it needed more than four, and the request was already
over. The client now imposes no timeout and the caller's context governs.

**The health loops needed the other half of the fix, and the asymmetry between
them is what hid this for three occurrences.** A health observation is a *poll*
rather than a wait: both loops around it expect it to fail fast so they can try
again. `awaitHealthy` bounded each attempt at three seconds; `WaitForHealth` did
not, and leaned on the client cap instead. Removing the cap without fixing that
would have let one probe consume a caller's whole budget and turned a retry loop
into a single attempt. Both now share one named `healthProbeTimeout`.

**The general lesson is worth more than the fix.** A re-run that passes is not
evidence that nothing is wrong; it is evidence that the thing that is wrong is
marginal. Twice this repository read a green re-run as absolution, wrote
"timing-sensitive network on a shared runner" into the handoff, and moved on —
and the third occurrence cost a candidate round trip to diagnose something the
error message had named from the start. **Read the error before reaching for the
re-run button**, especially when the same message returns.

**Two local checks this slice will want, and one lesson about them.** The
verifier's `--emit` regenerates the vector file from the derivations, so a
recorded value is never transcribed; and `python3 -B` is mandatory on every
Python run, because a stale bytecode cache can make a mutation probe appear to
pass without ever compiling the mutation. **A probe that passes has proved
nothing until you have checked that it changed the code the test runs.** M3.13l
ran one that flipped `expire_before_transactions`' default and passed, because
the deadline scenario passes the flag explicitly on every branch — the same
shape M3.11c hit with `assignment_is_prologue`. Moving the step itself made it
fail five vectors. **And a probe that passes may be a question about the
fixture rather than about the code**: M3.13l's activation-check probe passed
because every seat in every scenario was activated, and the fix was a scenario
that sells a seat nobody runs.

**One figure is already settled and should not be re-litigated.**
`kActivityThresholdSeconds` in `economy_assignment.cpp` is 64,800 seconds, 18
hours per cycle, founder-directed, read from the accepted manifest layer, and
checked against `test-vectors/economy-transition-v3.txt`. Version eight's
containment vectors record the same figure reached from two other directions: a
perfect seat after a maximal six-slot dispute, and a widened cap of seven slots
producing 61,200 seconds and an invariant failure by name.

**Note that the transaction-kind constants collide numerically with the state
entry-kind constants** — `TRANSFER` and `SEAT_ENTRY` are both 1 — so enumerate
them through `KIND_SCHEME` rather than by reversing a name table, which is how a
first attempt produced a list that looked right and was not.

**One consensus-visible rule M3.13a found and deliberately did not fix.**
`decode_cycle_assignment_value` does not require an assignment record's bitmap
pad bits to be clear, and `bit_is_set` bounds itself by the packed width rather
than by the recorded bit count, so a record with a pad bit set would be read as
an accrued seat by the mint's own walk. It is **unreachable on-chain** — every
record a block writes comes from `bitmap()`, which never sets one — and reachable
through a file, which is why the snapshot decoder refuses it. The accepted
specification fixes the bitmap width and does not state the pad rule, so the
kernel is conforming and tightening its decoder would be a compatibility change
rather than a fix. ADR 0056 records it. **Version eight states the pad rule
outright for its own window record**, so the version-eight kernel must enforce it
there while leaving the assignment record's older laxity alone.

**One cost requirement 13 will hit, recorded now rather than discovered then.**
`conservation_failures` calls `claimable`, which is the mint's walk run once per
seat over up to thirty assignment records each. That is ADR 0055's decision and
it is right — a second walk would make the backing identity check the kernel
against itself — but it is `O(seats x 30)` per block, and a cycle assignment
record at the 100,000-seat capacity is about 25 KB. At capacity the invariant
would decode on the order of gigabytes per block. **The snapshot restore now runs
that same walk once per restore**, which is the right place for it and the same
cost. **Nothing about it is consensus-visible**: the identity either holds or it
does not, so a node may cache or incrementalise the walk without changing a
single accepted state. It is an implementation cost rather than a contract
defect, and it has not been paid because no fixture yet runs at capacity. Do not
"fix" it by writing a second walk.

**Version eight adds a second cost of the same kind, and it is larger.** The
issue step evaluates one digest per in-scope seat per height — 100,000 digests
and about 7.2 MB of digest input per block at capacity, paid at 1,180 heights in
every 1,200. It is the direct cost of per-seat independent selection, which is
what makes a challenge unpredictable until one block before it must be answered,
and the specification states it rather than leaving it to be discovered. **The
evaluation is order-independent and may be parallelised**; the entries it writes
are in ascending seat order.

**What the version-eight Python execution model looks like, so the kernel slice
does not rediscover it.** `ledger.py` subclasses version seven's `Ledger` and
overrides four things: genesis binds the dispute authority key, the projection
adds `self.uptime`, the root is version eight's, and `conservation_failures`
appends six invariants. **`Ledger.uptime` is one raw key-to-value map holding
every kind-18 and kind-19 entry**, handed directly to the accepted contract
model's `Context`, so the two transitions the 183 contract vectors were recorded
against are the implementation rather than siblings of one. `block.py` holds the
four steps plus `run_quiet_heights`, which executes transaction-free heights with
a beacon built from `state.state_root_frame` — the same preimage `state_root` is
*defined* through, with only the height field varying. `Ledger.advance_to`
**raises** once any seat is activated, because a version-eight block with no
transactions still audits every in-scope seat.

**What the version-eight snapshot looks like now, so a later session does not
rediscover it.** `protocol::storage::snapshot_v8` is one public header, one
internal header, and three translation units, on version seven's shape with a
single subject added: `snapshot_v8_entries.cpp` carries `apply_open_challenge`
and `apply_seat_window` beside the twelve fixed-width decoders, and
`snapshot_v8_assignments.cpp` is version seven's file with three identifiers
rebound and **nothing else at all** — the normalising diff against it is empty.
The prefix is **158 octets** and `kFixedSize` **222**. The two uptime kinds are
stored raw and checked rather than decoded into fields, `dispute_authority_key`
is prefix field nine and restore parameter five, and the seat-existence rule runs
in `complete()` so no value decoder depends on kind 1 sorting before kinds 18 and
19.

**Four rules the version-eight decoder enforces and where each is caught.** A
challenge state that is not `0` or `1` and a window record with a pad bit or a
dispute of an uncredited slot are the kernel's own decoders, reused so the
snapshot and the invariant that re-reads the entry cannot disagree; each is also
refused by `conservation_failures` a step later, so what the decoder buys is a
named subject. **The other two have nothing behind them.** A record equal to
`full_seat_window()` and an uptime entry naming an unsold seat both survive a
reseal and both root gates, and the conservation invariants say nothing about
either — so the decoder rule is the only refusal there is, which is why those
tests reseal and why deleting either rule reports "a restore accepted it".

**And a separate `kMaxSeatId` bound was considered and deliberately left out.**
Every seat the chain sold is inside the capacity, so it would fire only where the
existence rule fires too, and a rule no test can isolate is the shape this
project has twice been caught by. ADR 0066 records the reasoning.

**What the version-seven snapshot looks like, which step 7 deletes.**
`protocol::storage::snapshot_v7` is one public header and four translation
units: `snapshot_v7.cpp` owns the framing and the three gates,
`snapshot_v7_entries.cpp` the fixed-width value decoders and the dispatch,
`snapshot_v7_assignments.cpp` the one variable-width record and the permission
count summed back out of the same octets, and `snapshot_v7_internal.hpp` the
seam. The payload's magic is version one's `PSSN` with a version field of 7, so
version one's decoder recognises the family and answers `unsupported_version`
rather than `malformed`. The prefix is 126 octets and the encoder checks that it
wrote exactly that many, because the decoder reads every prefix field at a
literal offset.

**What the Go adapter looks like now, so a later session does not rediscover
it.** `internal/localapp` holds **two files per ledger version and no wire**:
`wire_v7.go` / `wire_v8.go` hold each finalized-block decoder and its receipt
rule, and `client_v7.go` / `client_v8.go` hold `ClientV7` and `ClientV8`, each
of which **embeds `Client` and declares exactly one method**.
`internal/bridge/local.go` holds `LocalV1`, `LocalV7`, and `LocalV8` — three
embeddings that give each client the shape the bridge consumes — and
`application.go` holds `New`, `NewV7`, `NewV8`, a `codespace` field, and a
`committedHeight`. **That height is never counted here**: it is raised only by
the application's own answers to `Info` and `Commit`, which is what makes the
finalize guard incapable of refusing a legitimate block. Do not "simplify" the
bridge's `FinalizedBlock` by giving version one a zero `BlockID` instead of a
nil pointer — the pointer is what stops a zero hash being emitted and indexed as
though it named a block.

**Three figures live in the Go half and one of them has no constant behind it.**
`receiptVersionV8` is 8 and is **named rather than written into the prefix
array**, which is what version seven's file does not do; `resultCodeCountV8` is
45; and `appStateV8` is `"protocol-stack-v8"`. Only the middle one can go stale
quietly — the other two break the first block or the handshake — so it is pinned
to its literal, with results 44 and 45 exercised by hand. **Versions seven and
eight share a finalized-block shape**, so the only octet separating them on a
well-formed block is the receipt's version, which is why each decoder is
required to refuse the other's payload rather than merely to accept its own.

**One local check that is worth rebuilding rather than rediscovering.**
`internal/localapp` imports no third-party code, so copying its `*.go` into a
scratch module with `go 1.23` and running `go vet ./...` and `go test`
type-checks and exercises the whole package under this machine's own Go in
under a second —
no CometBFT module graph, which the repository's resource rules forbid pulling
locally. `internal/bridge` and `internal/nodeconfig` import CometBFT and can only
be verified on the hosted matrix, so **write those two carefully the first
time**: a compile error there costs a full matrix round trip. The engine's own
source is worth reading the same way — `curl` one file from
`raw.githubusercontent.com/cometbft/cometbft/v0.39.4/` beats a module download,
and `consensus/replay.go` is where the replay handshake is decided.

**What the store's failure contract looks like now, so a later session does not
rediscover it.** All seven of version one's fault points are live in
`SQLiteLedgerV8::apply_block`, and in version seven's beside it until ADR
0065's step 7. The four before the commit **throw** and roll back, and the
store is left usable; the two after it are **invoked and ignored** so a test
can terminate the process there; `before_recovery_open` fires only during
recovery. A commit failure sets `poisoned` and immediately calls
`Impl::recover_durable_head`, which clears it on success. **Do not "simplify"
that into poisoning on every write failure** — that is what it was, and it made
an ordinary rolled-back refusal permanent. **None of this contract is
version-specific**, which is why ADR 0067 re-establishes it against a
version-eight chain rather than restating it.

**What the node process looks like now, so a later session does not rediscover
it.** `src/application/main_v8.cpp` is the `protocol-application-v8` target and
`main_v7.cpp` is version seven's beside it until ADR 0065's step 7. Each takes
`<absolute-database> <absolute-genesis> <absolute-socket>`, or
`--genesis-identity <absolute-genesis>`. The genesis file is exactly
`kGenesisPrefixBytes` octets and nothing else — **142 for version eight, 110 for
version seven** — and the size check in the binary is an **allocation bound**
while the validity rule lives only in `decode_genesis`. Version eight's file
**states no width at all**: the bound reads the constant and the two error
messages name the rule rather than a number, because a message is compiled
against nothing and a stale literal in one survives every test. Opening the
store is attempted before creating it. A `connection_failure` or a
`protocol_failure` continues the serve loop; only the application's own terminal
latch stops a node that has contradicted itself.

**What the transport looks like now, so a later session does not rediscover it.**
There is no version-seven wire. `wire_v1` decodes every request for both
versions, and version seven adds `response_v7.cpp` and `dispatcher_v7.cpp` only.
`unix_connection_v1.cpp` holds one templated `serve_with` over a dispatcher and
two thin `serve_connection` overloads; **the `V1` in `UnixSocketServerV1` is the
wire's version, not the ledger's**, and the header says so. The response layout
is version one's status-and-reserved prefix followed by the body, and the one
shape that differs is `finalize_block`, which carries the state root, **then the
block identifier**, then one `{code, receipt}` pair per raw input.

**What the application looks like now, so a later session does not rediscover
it.** `protocol::application::ApplicationV8` is one public header, two
translation units, and one internal header: `application_v8.cpp` owns
construction and the five operations that do not write,
`application_block_v8.cpp` owns `finalize_block` and `commit` and the per-input
result rows, and `application_v8_internal.hpp` holds the `Impl` with its staged
block. Version seven's four files sit beside them until ADR 0065's step 7. It
reuses version one's `ApplicationError`, `TransactionResult`, and
`PreparedProposal` unchanged, because none of those six codes or two shapes
names a ledger version. The stage holds the candidate **root** and not the
candidate ledger, on purpose. `init_chain` is idempotent at genesis because
CometBFT calls it again on a node that crashed before its first block, and an
application opened on a store already past genesis comes back ready without it.
**`apply_block` and `execute_block` are both called with no uptime schedule**,
which is what closed ADR 0058's owed item.

**Two figures live in this layer and one of them is not where a survey looks.**
`kApplicationProtocolVersionV8` is 8 and the expected app state is
`"protocol-stack-v8"`; both are operator-visible and both are pinned by tests.
The third is **inside the response encoder**: `kReceiptPrefixV8` is the
receipt's six-octet magic and its last octet *is* the receipt version, derived
from `v8::kReceiptVersion` rather than written out. Version seven's encoder
writes it out, which is why a rebound version-eight encoder refuses every
finalized block until it is fixed. **A later version must check this first**,
because it fails on the happy path rather than in a refusal.

**One guard in this layer has no test that can fail it, and that is recorded
rather than hidden.** `commit` requires the store's returned commit record to
equal the one `finalize_block` staged — the equality ADR 0058 calls "the whole
safety argument" — and a probe removing it passes the entire suite. Constructing
a violating input would need a fault-injection seam returning a corrupted commit
record, which is test-only machinery in production code. **Do not delete the
guard**; ADR 0068 records why.

**What the store looks like now, so a later session does not rediscover it.**
`protocol::storage::SQLiteLedgerV8` is one public header and three translation
units with two internal headers: `sqlite_ledger_v8.cpp` owns what a live store
does, `sqlite_ledger_v8_open.cpp` owns how one comes into existence and holds
every validation step, `sqlite_schema_v8.cpp` owns the DDL and the two rows a
commit writes, `sqlite_ledger_v8_internal.hpp` is the seam between the first
two, and `sqlite_schema_v8.hpp` declares the schema surface. `src/storage/`
holds version seven's five files beside them until ADR 0065's step 7. The
schema is two tables — `ledger_meta_v8`, a singleton, and `blocks_v8` — both
`STRICT, WITHOUT ROWID`, with the DDL stored and compared verbatim on every
open. Heights are stored as fixed-width big-endian octets **on purpose**:
`ORDER BY height` over a blob column is then numeric order, which is what lets
the history be read back in block order by a bare connection. The
`head_snapshot` column's `length >= 222` is the snapshot's own `kFixedSize`,
the 158-octet prefix plus a root plus a digest; the stored canonical genesis is
142 octets; the pinned `application_id` is `0x50534c38` and the `user_version`
8; and the block header column stays 146 octets, because version eight inherits
version one's header unchanged. **`apply_block` takes a height and raw
transactions and nothing else** — no uptime schedule, because version eight's
prologue derives it, and no `BlockOrder`, because those flags are not a
configuration a chain has.

**What the version-eight codec looks like now, so a later session does not
rediscover it.** `src/v8/` holds eleven sources and `include/protocol/v8/` one
header. Ten of the sources are version seven's codec with three identifiers
rebound and nothing else, so a diff against `src/v7/` under a `protocol::vX`
normalisation is the whole review. The eleventh, `economy_uptime.cpp`, is
version eight's entire addition — entry kinds 18 and 19, their value codecs, the
window record's bitmap arithmetic, and challenge selection — deliberately in one
file so that the difference between the two codecs is one file rather than ten.
**`economy_settlement.cpp` is in the codec half**, despite the recorded 9 / 8
split placing it in the execution half: it implements only functions
`economy.hpp` declares. The two predecessor constructions,
`predecessor_chain_id` and `predecessor_state_root`, exist so that each of the
seven non-collisions is a claim about two derived artifacts; **they are pinned
against `protocol-primitives-v1.txt` and `economy-transition-v7.txt` at the two
ends of their range**, because an inequality between two digests proves nothing
about either one.

**What the version-seven kernel looks like now, so a later session does not
rediscover it.**
`src/v7/` holds seventeen sources and `include/protocol/v7/` two headers.
`economy_assignment.cpp` is the newest and is the only one with no version-six
ancestor: it derives a cycle and applies it, and `execute_block` calls it as a
prologue. `Assignment` and `SeatCycle` live in `ledger.hpp`; `SeatCycle` carries
**three** fields on purpose, because the mark and the recorded referrer are
chain state and a four-field version would make ADR 0055's first derived rule
optional. **Version eight makes that shape structural rather than disciplined**:
its `derive_schedule` returns three fields, so a measurement cannot supply the
other two even by accident.

**One class of failure the local harness cannot reproduce at all, learned in
M3.13e.** Every target this project builds must appear in
`PROTOCOL_STACK_TARGETS`, which is the **only** place the C++ standard, the
warning flags, `-Werror`, and the sanitizers are applied. A target left out still
builds — at the compiler's default standard — and the scratch harness passes
`-std=c++20` explicitly on every invocation, so it compiles clean locally and
fails in all four hosted jobs with errors pointing at headers that have not
changed in months. `test_every_built_target_takes_the_project_build_flags` now
catches it, and `python3 -B tests/tools/test_registration_test.py` is where it
runs. **Adding an executable means four edits**: `add_executable`, its
properties, its link libraries, and that list.

**Local checks worth running, and one worth running first.** `git diff --check
main HEAD` is exactly the whitespace gate the classification job runs; it costs
nothing and M3.12a lost a full matrix run to a trailing blank line without it.

**`python3 -B tests/tools/test_registration_test.py` is the second, and M3.12b
lost a matrix run to skipping it.** It runs in nine milliseconds and it checks
things no compiler can: that every accepted vector file is read by some
registered ctest entry, that every verifier has an `add_test`, and that no two
entries share a write path. Retargeting the kernel's ctest arguments left
`economy-transition-v6-execution.txt` read by nothing, and its message is the
rule — *a recorded vector file no registered verifier reads is not evidence*.
Run it after **any** CMake edit.

**A blanket `sed` over `CMakeLists.txt` is how that happened, and the shape of
the mistake generalises.** Rewriting `economy-transition-v6*.txt` to version
seven's also rewrote the arguments of version six's *own* Python verifiers,
which are registered in the same file and are not the kernel's. After a
rename, read `git diff main -- CMakeLists.txt | grep test-vectors` and check
every changed line is one you meant.

**Local `-Wall -Wextra -Wpedantic -Werror` is not the matrix's gate.** This
machine has GCC 12; the matrix runs a newer GCC whose `-Wdangling-reference`
rejected seven call sites that compile clean here, and the warning does not
exist locally at all. It was pointing at something real — `run` returns a
reference into a vector a later `run` may reallocate — but no local invocation
could have found it. Push a candidate and let the matrix answer; the local pass
is still worth running, because it is the cheap half.

**The scratch C++ harness is worth rebuilding rather than rediscovering.** It is
a `sodium.h` backed by the system OpenSSL — `crypto_hash_sha256` over
`EVP_sha256`, `crypto_sign_verify_detached` over `EVP_PKEY_ED25519`, a
`sodium_init` returning zero, and `sodium_memcmp`/`sodium_memzero` — never
committed and never part of the build. With it,

```
g++ -std=c++20 -O0 -I include -I src -I tests -I <shim> \
  src/v7/*.cpp src/v1/*.cpp tests/kernel/economy_v7_<target>*.cpp \
  -lcrypto -o <binary>
```

links either kernel test target in about eleven seconds, and the binary takes
the same vector-file arguments CMake passes it. **That is what made thirteen
mutation probes affordable in M3.12b, twenty-six in M3.13a, and twenty in
M3.13n**; without it each probe is a hosted run. The version-eight form
substitutes `src/v8/*.cpp` and `tests/kernel/economy_v8_*.cpp`, and links in
about four seconds because the codec pulls in no storage.

**M3.13n's probe harness is worth rebuilding rather than rediscovering, and it
answers a question the probes themselves cannot.** A shell script that copies
the source, applies one textual substitution, refuses to run at all when the
pattern is not found, rebuilds, runs, and restores — so a probe that never
applied reports `PATTERN NOT FOUND` instead of a false pass. Three of M3.13n's
twenty probes found real gaps and two of those three would have been read as
successes without it.

**The version-eight snapshot suite links with no SQLite at all**, because the
snapshot touches none: `src/v8/*.cpp src/v1/*.cpp src/storage/snapshot_v8*.cpp
tests/storage/snapshot_v8_*.cpp tests/kernel/economy_v8_trace.cpp
tests/kernel/economy_v8_scenarios_test.cpp` builds from cold in about
twenty-five seconds, and **compiling the stable translation units to objects in
parallel once takes a probe relink to about four**. That is what made thirteen
probes affordable in M3.13p. The whole suite runs in 2.7 seconds because
`run_quiet_heights` executes the scenarios' 1.35 million heights.

**The store suites need SQLite and it is already on this machine, which M3.13q
established rather than assumed.** The repository fetches SQLite through an
ExternalProject, which the resource rules forbid locally — but a 3.53.0
amalgamation is present at
`~/.bun/install/cache/better-sqlite3@12.9.0@@@1/deps/sqlite3/sqlite3.c`, and
`gcc -O0 -w -DSQLITE_DQS=0 -DSQLITE_TRUSTED_SCHEMA=0 -DSQLITE_ENABLE_API_ARMOR
-DSQLITE_THREADSAFE=1 -c` turns it into a 1.5 MB object in **3.4 seconds**. No
download and no dependency graph. With it, `src/v1/*.cpp src/v8/*.cpp
src/storage/snapshot_v8*.cpp src/storage/sqlite_connection.cpp
src/storage/sqlite_fault_injection.cpp src/storage/sqlite_*_v8*.cpp
tests/storage/sqlite_ledger_v8_*.cpp tests/kernel/economy_v8_trace.cpp
tests/kernel/economy_v8_scenarios_test.cpp` links in 28 seconds cold; the 34
unchanged translation units precompile in 11 across four parallel jobs, which
puts a probe relink at about four. **The shim also needs Ed25519**, which the
snapshot suite does not: `crypto_sign_verify_detached` over
`EVP_PKEY_new_raw_public_key(EVP_PKEY_ED25519, ...)` and `EVP_DigestVerify`,
plus `crypto_sign_PUBLICKEYBYTES` and `crypto_sign_BYTES`. The pinned version is
3.53.3 and the cached one 3.53.0; that is fine for a probe harness and the
hosted matrix remains the authority.

**The application suites link with the same harness and one more object set.**
`application_v8_tests` needs no version-seven code at all — `src/v1/*.cpp
src/v8/*.cpp src/storage/snapshot_v8*.cpp src/storage/sqlite_connection.cpp
src/storage/sqlite_fault_injection.cpp src/storage/sqlite_*_v8*.cpp
src/application/{application,application_block,dispatcher,response}_v8.cpp
src/application/response_v1.cpp src/application/wire_v1.cpp` plus the two
scenario translation units links in 35 seconds cold, and 38 stable objects
precompile in 19 across four jobs. **`application_transport_v8_tests` needs
everything**, including `src/v7/*.cpp` and the version-one and version-seven
application sources, because `unix_connection_v1.cpp` holds all three
`serve_connection` overloads; that link is about 70 seconds and is worth doing
once rather than per probe.

**One probe-writing trap M3.13q hit and used.** Disabling a condition by
prefixing `false && ` disables **only the first conjunct** of an
`A != B || C != D`, because `&&` binds tighter than `||`. That made the probe
*more* precise than intended — it isolated one half of the schema comparison and
proved which tamper case catches it — but a probe written that way and read as
covering the whole condition would be a false negative.

**M3.13a extended it to the storage tests and the pattern is worth keeping.**
Adding `src/storage/snapshot_v7*.cpp tests/storage/snapshot_v7_*.cpp
tests/kernel/economy_v7_trace.cpp tests/kernel/economy_v7_scenarios_test.cpp`
links the snapshot suite with no SQLite at all, because the snapshot touches
none. **Compile the stable translation units to objects once and recompile only
the mutated one**, which takes a probe from about twenty seconds to about four
and is what made twenty-six of them affordable in one session. Beware deleting
the cached objects with a glob: `rm obj/snapshot_v7*.o` also removes the test
entry point and the fixture, and the relink then fails for a reason that has
nothing to do with the probe.
**M3.13b extended it again, to the tests that need SQLite, and the cost is
lower than it looks.** A SQLite amalgamation already on this machine —
`sqlite3.c` and `sqlite3.h` under
`~/.bun/install/cache/better-sqlite3@*/deps/sqlite3/`, version 3.53.0 against the
repository's pinned 3.53.3 — compiles in **about three seconds** with the
project's own flags (`-DSQLITE_DQS=0 -DSQLITE_TRUSTED_SCHEMA=0
-DSQLITE_ENABLE_API_ARMOR`) and links straight into the scratch harness, so no
`ExternalProject` download is needed to run the storage suite locally. Copy
`sqlite3.h` next to the `sodium.h` shim and add `sqlite3.o` to the link. The
whole store suite builds from cold in about fifteen seconds and each mutation
probe relinks in about four.
Its one known limit is that it does not reproduce libsodium's rejection of
small-order public keys, so `tests/kernel/primitives_test.cpp` fails under it at
that assertion and passes on the hosted matrix. **Run Clang locally before
pushing**: it caught a structured-binding capture GCC accepts and the matrix
rejects. **On Python sources use `python3 -B`**, because a stale bytecode cache
can make a mutation probe appear to pass without ever compiling the mutation.

**An invariant nothing can reach is an invariant nothing is testing**, and
M3.13o found four of them in one slice. Three of the six version eight adds —
the retention bound on a seat window record, the deadline bound on an open
challenge, and the open-challenge state rule — could have been deleted outright
with every one of 434 recorded execution vectors and 62 contract vectors still
passing, and so could the quiet height's own conservation gate. **A recorded
scenario cannot reach them by construction**: the steps that write these entries
never produce the states they forbid, which is what an invariant is *for* and is
also exactly why nothing exercised them. The fix is to write the forbidden state
directly into the raw map and require the invariant to name the rule it broke,
with a positive control beside it so the refusal is about the state rather than
about the check. **Every future layer that adds an invariant needs this same
pass**, and a probe that deletes the invariant is the cheapest way to find out.

**And re-aim a probe that mutated unreachable code**, which is the other half of
the same lesson. M3.13o's absent-record probe changed a ternary's else-branch
that `seat_window_record` never takes, so it proved nothing; re-aimed at the
accessor every caller actually uses, it fails three block roots. A probe that
passes has proved nothing until you have checked that it changed the code the
test runs, and "the code the test runs" excludes a defensive branch no caller
reaches.

**An inequality between two digests proves nothing about either one**, and
M3.13n paid for that twice in one slice. `predecessor_state_root` was written to
recompute an earlier version's root so that each of the seven non-collisions is
a claim about two real artifacts. A mutation that wrote version eight's schema
version into every predecessor preimage **passed uncaught**: the labels still
differed, so all seven digests differed from version eight's *and from each
other*, and every comparison the test made passed — about an artifact no chain
ever had. Removing version one's economy-free preimage passed for the same
reason. The fix is to pin the construction at each end of its range against the
file that recorded it, and the pins must be recorded files rather than the live
predecessor kernel, or they die with `src/v7/` at M3.13t.

**A stated resource bound is a claim the implementation can falsify.**
`economy-transition-v8` states that the pipeline pays one digest per in-scope
seat at 1,180 heights in every 1,200. M3.13n's first `is_selected` derived the
selection value and *then* checked the exclusion, which pays it at all 1,200 —
100,000 wasted digests at twenty heights of every slot at capacity. Nothing
about it was consensus-visible and no vector could have caught it, because the
predicate's value is identical either way. **Read a specification's resource
bounds as assertions about the code, not as commentary**, and put the cheap test
before the expensive one.

**And re-aim a probe that passes.** M3.11c ran a probe that flipped the default
of `assignment_is_prologue` and it passed uncaught, because the trace passes the
flag explicitly and the mutation never reached the executed path. M3.12a ran one
that substituted a line for itself. **M3.12b ran a third**: an "absorb after
contributing" probe that added the dust before subtracting what was taken and
dropped the later addition, which cancels exactly because a cycle absorbs either
the whole pool or nothing. **M3.13a ran two more, and both were tests caught by a
*different* rule than the one they named**: a bitmap pad bit that the
contributing bound refused first, and a channel index that the fixed-entry
presence check refused first because renaming the tenth channel also removed it.
**M3.13l ran two more of a third kind.** One repeated M3.11c's mistake exactly,
on a different flag. The other passed because of the *fixture* rather than the
code — no scenario had a purchased, unactivated seat, so removing the issue
step's activation check changed nothing — and the fix was a scenario that sells
a seat nobody runs, not a better probe. **A probe that passes has proved nothing
until you have checked that it changed the code the test runs**, and the cheapest
way to check is to make it fail on purpose first.

**M3.13a's second re-aim paid twice, which is the argument for doing it at all.**
Isolating the channel-index case did not only fix the test: with the bound
removed, the eleventh channel is admitted, the rebuilt ledger has nowhere to keep
it, and the snapshot's *second* root gate is what refuses the payload — which
demonstrated that a gate the session had written down as unreachable is the one
that catches an entry kind the `Ledger` cannot hold.

**One probe in M3.12b passed for a better reason and it is the pattern to
repeat.** Removing the backing identity from `conservation_failures` passed,
because both identities were checked by the settlement test's own arithmetic and
nowhere else. The fix was not a better probe but a better test: each identity is
now broken on purpose and the kernel's invariant is required to report it by
name. A probe that passes is a question about the tests, not only about itself.

**The strongest probe result is "a restore accepted it", and it is worth
building tests that can produce it.** M3.13p ran thirteen probes and six report
exactly that, because the test that catches them reseals the payload first. A
resealed forgery defeats both root gates by construction, so a probe against a
resealed case answers a sharper question than "is this rule enforced": it answers
"is this rule the only thing enforcing it". Two of the six were about version
eight's *added invariants* rather than about the snapshot — the window record's
retention bound and the challenge's deadline bound — which is M3.13o's finding
about unreachable invariants carried one layer up. **Every layer that adds a rule
should ask which of its refusals survive a reseal**, because those are the ones
with nothing behind them.

**And one probe that "passed uncaught" was read rather than patched.** Removing
the encoder's own prefix-width assertion changed nothing, because the prefix is
in fact 158 octets: it is a tripwire for a later edit, not a rule with a
violating input. The way to test such a guard is to give it something to catch —
dropping a prefix field instead, which fails at "the final ledger must encode".
**A guard with no violating input is not a defect; mistaking it for one and
deleting it is.**

**A probe caught by an invariant rather than by a vector is a stronger result,
not a weaker one.** Two of M3.13l's nine are refused before any comparison
happens, and each names the rule it broke: "a seat window record outlived its
retention" and "a maximal dispute failed a fully credited seat". Check that the
message is the expected one — a crash for an unrelated reason reports the same
non-zero exit.

**One fixture rule the kernel tests now depend on.** Three builders in
`economy_v7_trace.cpp` are version six's, imported rather than restated — the
confirmed transfer, the verified-user mint, and the posture change — and they
carry `kInheritedValidUntil` (10,000,000) rather than `kValidUntil`
(10,000,000,000). The bytes a transaction commits to include the height it
expires at, so unifying the two constants produces identical state roots and
different transaction roots. Do not tidy them into one. **The Python version-eight
trace has the same split for the same reason**: its own builders use
10,000,000,000 and the version-six builders it imports use 10,000,000.

**One sequencing rule an earlier slice learned the hard way.** Let the merge's
own `main` push run finish before pushing the closeout documentation commit.
M3.11c pushed the closeout while the merge run was still building and the
workflow's concurrency group cancelled it, which leaves a cancelled run and a
failed aggregate check on `main`'s history for a commit whose tree had already
passed the matrix in full on the pull request.

**One arithmetic error in an accepted specification was found and corrected in
M3.13n, and the shape of it generalises.** `economy-transition-v8` argued for
truncating the selection digest by saying "`2^64 mod 1200` is 1,216, so 1,216 of
the 1,200 residues occur once more often than the rest". A remainder modulo
1,200 is below 1,200, so the sentence refutes itself in its own second clause;
the figure is **16**, the relative bias is 6.42e-17, and the stated bound of
`2^54` is therefore also wrong where `2^53` holds. It had been repeated in three
places — the specification, the model's docstring, and the kernel comment that
copied it — and **nothing normative depended on it**, which is exactly why it
survived a specification, a model, 183 vectors, and a review. The likeliest
origin is `docs/project/reward-distribution-report-v1.md`, which carries an
unrelated 1,216. **A figure no vector records is a figure nothing checks**, so
read the arithmetic in explanatory prose rather than trusting that the gates
would have caught it.

**Two generation details.** Every version-seven and version-eight vector file is
produced by its verifier's `--emit`, which runs the same derivations through the
same agreement gate as the checking mode, so a file and its derivations cannot
disagree at birth; the section comments are emitted with them, so regenerating is
one command rather than a transcription. And **the coverage claim is a vector of
its own**: `coverage.every_kind_version_eight_admits_is_executed` fails if a
later scenario change stops reaching one.

### Blockers

**There is no blocker.** Every candidate under "Exact next action" is unblocked.

**M3.21a ran the founder-decision gate and passed it.** Three decisions were
enumerated: each requirement's status, where three open items belong, and
whether M3 closes. The first follows from evidence, and the audit shows it. The
second follows from `first-goal.md`'s scope and ADR 0071's own words. The third
follows from the first, read fail-closed: a requirement met only against a
replaced contract is not met. None sets a value or changes what a participant
must do. The next slice's fixture, a research population and uptime pattern, is
not a founder value either.

**M3.20l ran the founder-decision gate and passed it.** Four decisions were
enumerated before any was judged:

1. where the orphan rule lives;
2. whether a zero balance is refused too;
3. how the positive control gets a referring seat;
4. which slug rule the anchor check follows.

The first is a storage placement chosen so that no block's acceptance can move.
The second follows from the one code path that writes a balance. The third is
test construction. The fourth is GitHub's own rule. None sets or changes a value,
a beneficiary, or what a participant must do, own, run, or receive.

**M3.20k ran the founder-decision gate and passed it.** Six decisions were
enumerated before any was judged:

1. whether to delete version eight;
2. what the deletion keeps;
3. what becomes of `-protocol-version 8`;
4. how the version-nine checks pinned to version eight are re-pinned;
5. what replaces the economy fuzz target and the inherited snapshot sweep;
6. what becomes of the orphan referral balance the port found.

**The first is decided by ADRs 0080 through 0085**, each of which names this
deletion as the migration's end, and ADR 0070 is the method. The second follows
ADR 0070's rule and the repository's own dependencies. The third is the
adapter's compatibility mechanism for a devnet tool, and it changes nothing a
participant must do, own, run, or receive. The fourth and fifth are test
engineering. The sixth is a restore-validation rule over a state no block writes.
It moves no value, and it is recorded as the next slice rather than settled
inside a deletion. Nothing founder-reserved is touched.

**Two pieces of accepted required evidence cannot be produced over the wire, and
both are recorded rather than waived.** The second is M3.20c's: **decision `6`,
`RESOURCE_BOUND`, cannot arrive over the wire**, because `wire_v2`'s request
decoder enforces the same three bounds and refuses the frame before dispatch,
and the Go bridge's `validateBlock` votes REJECT before building one at all. The
application produces it in-process and the encoder proves the byte. The first
is M3.20b's, and the rest of this paragraph is about it.
`consensus-application-v2` asks for a vector for every `ProcessProposal`
decision `0` through `7`. **Decision `7`, `NOT_EXECUTABLE`, is not reachable
from a proposal's contents**: the kernel turns every transaction-level problem
into a result, and the whole-block rejections that remain are chain-state
failures no peer can induce by choosing bytes. M3.20b established this with a
probe rather than a reading and records the absence as a measurement. It is not a blocker — the decision stays implemented because the
failures it guards are real — but a later session should not spend the slice
hunting for the vector.

**M3.20j ran the founder-decision gate and passed it.** Eight decisions were
enumerated before any was judged:

1. how one application's clock is offset;
2. the size of the skew;
3. which replica is skewed;
4. whether both directions and a correction are run;
5. how the supervisor hands one replica a different environment;
6. what counts as a vote against;
7. the thresholds a run must meet;
8. the packaging.

**The first was named as this slice's by ADR 0085 and ADR 0090 §6**, and
[ADR 0091](../decisions/0091-the-skewed-replica-is-skewed-below-the-process.md)
records the choice. The sixth is ADR 0087's logged decision. The rest are test
mechanism and packaging. The one close to reserved is that a participant must
run a roughly correct clock to vote. It is not new here: `calendar-v1`'s C5 made
it a precondition, and `consensus-application-v2`'s own gate classified it
delegated for that reason. This slice tests the rule and sets none. Nothing
founder-reserved is touched.

**M3.20i ran the founder-decision gate and passed it.** Nine decisions were
enumerated before any was judged:

1. the evidence set;
2. where the kind-22 mint's evidence lives;
3. whether the skewed replica is in scope;
4. where durable-stamp agreement is read;
5. the transactions and which nodes submit them;
6. how the genesis is stamped;
7. how the restart window is guarded;
8. how unrequested heights are followed;
9. the packaging.

**The second was already classified by the handoff** as evidence method rather
than founder-reserved, and it was settled as the handoff recommended. It changes
where a piece of evidence is produced, not what any participant gets. The sixth
and seventh follow ADR 0088 and ADR 0089. The rest are test mechanism and
packaging, which
[ADR 0090](../decisions/0090-the-version-nine-devnet.md) records. Nothing
founder-reserved is touched.

**M3.20h ran the founder-decision gate and passed it.** Seven decisions were
enumerated before any was judged:

- the fixture genesis's figures;
- which transitions the run commits, and in what order;
- where the restart falls;
- how the genesis is stamped and when;
- how an engine time becomes the model's millisecond;
- the launch and restart margin; and
- the packaging: the helpers, the file, test, ADR, issue, branch and PR shape.

**The figures are the version-nine trace's**, reused rather than chosen. The
order is the only one the contract admits. The conversion is
`consensus-application-v2`'s rule, restated rather than re-chosen. The stamp's
timing follows from ADR 0088. The rest are test mechanism and packaging, which
[ADR 0089](../decisions/0089-a-version-nine-chain-resumes-only-inside-the-tolerance.md)
records.

**One finding was close enough to name.** A version-nine chain cannot resume
from an outage of a quorum longer than the tolerance. It is classified as
delegated for four reasons: it is a consequence of the accepted C5 under the
pinned engine rather than a new rule, no rule changed, every candidate fix is a
consensus mechanism, and none of them changes what a participant must do, own,
run, or receive. Nothing founder-reserved is touched.

**M3.20g ran the founder-decision gate and passed it.** Nine decisions were
enumerated before any was judged: the `genesis_time` derivation; the app-state
string; the refusal of an existing genesis that differs; versions one and eight
keeping the epoch; how the identity represents a missing stamp; refusing the
version and stamp pairing, and when; the exact per-version identity key set; the
stamp's operator spelling and range; and the flag name and the file, test, ADR,
issue, branch and PR shape. **The first four are fixed by
[`consensus-application-v2`](../specifications/consensus-application-v2.md)**
and were cited rather than re-chosen; the range is `calendar-v1`'s C1. The rest
are mechanism, encoding of an operator input, and packaging, which [ADR 0088](../decisions/0088-the-launcher-derives-the-genesis-time-and-the-first-block-carries-it.md)
records. **One was close enough to name**: the finding that a version-nine
network must decide its first block within 60 seconds of its genesis stamp is a
statement about what a launcher must do. It is classified delegated because it
is a consequence of `calendar-v1`'s accepted C5 rather than a new rule, it binds
whoever launches a network rather than a participant, and no rule changed.
Nothing founder-reserved is touched.

**M3.20f ran the founder-decision gate and passed it.** Eight decisions were
enumerated before any was judged: the conversion formula; its three refusals;
truncation for a block time and exactness for a genesis time; passing a
representable out-of-range stamp through; voting ACCEPT only on decision `0`;
the version-nine codespace; where the conversion runs and whether a rejection is
logged; and the file, test, ADR, issue, branch and PR shape. **Six are fixed by
[`consensus-application-v2`](../specifications/consensus-application-v2.md)**
and were cited rather than re-chosen. The rest are mechanism and packaging that
[ADR 0087](../decisions/0087-the-bridge-carries-the-engines-time.md) records.
Nothing founder-reserved is touched.

**M3.20e ran the founder-decision gate and passed it.** Six decisions were
enumerated before any was judged: the request and response payload shapes of
kinds 1, 2, 5, 6 and 7; the rule that statuses `7` and `8` belong to kind 6
alone; the version-nine receipt prefix and result table; whether a ninth
decision is refused; where the frame version lives; and the file, test, ADR,
issue, branch and PR shape. **Three are fixed by
[`consensus-application-v2`](../specifications/consensus-application-v2.md)
and `economy-transition-v9`**, and the rest are mechanism and packaging that
[ADR 0086](../decisions/0086-the-go-local-client-speaks-the-version-two-frame.md)
records. Nothing founder-reserved is touched.

**M3.20d ran the founder-decision gate and passed it.** Seven decisions were
enumerated before any was judged: which platform clock and in what unit; what a
process does when it cannot read one at startup; what it does when one stops
being readable; the genesis width and its C1-only validation; what identity mode
prints; whether the process takes a clock-injection option; and the binary,
driver, test, CTest, ADR, issue, branch and PR shape. **Three are fixed by
[`consensus-application-v2`](../specifications/consensus-application-v2.md),
`calendar-v1`, and `economy-transition-v9`** — the platform real-time clock in
milliseconds since the Unix epoch, the refusal to start without one, and the
genesis rule — and were cited rather than re-chosen. The runtime stop is deduced
from the same refusal. The rest are mechanism and packaging, and
[ADR 0085](../decisions/0085-the-version-nine-node-process-binds-the-platform-clock.md)
records each. **Requiring a machine to hold a roughly correct clock is not new
here**: `calendar-v1`'s C5 made it a precondition for voting, and the contract's
own gate classified it delegated for that reason.

**M3.20c ran the founder-decision gate and passed it.** Eight decisions were
enumerated before any was judged: the seven response payload shapes; the
decision byte's eight values; the status space and the rule that `7` and `8`
belong to kind 6 alone; the response frame version; the result-code mapping and
the receipt version; whether a diagnostic is written; how the socket chooses its
wire; and the module, suite, CTest, ADR, issue, branch and PR shape. **Five are
fixed by [`consensus-application-v2`](../specifications/consensus-application-v2.md),
[ADR 0082](../decisions/0082-the-version-two-application-frame.md), and
`economy-transition-v9`** and were cited rather than re-chosen; the remaining
three are mechanism and packaging. Nothing in the slice sets or changes a
founder-reserved value, and **no accepted vector file, specification, manifest,
encoding, or kernel source changed**.

**M3.20b ran the founder-decision gate and passed it.** Eleven decisions were
enumerated before any was judged: the clock's binding point; whether it has a
default; whether it is reachable from the replay path; the eight decision values
and their order; the kernel-condition-count assertion; InitChain's four compared
values and its C1-never-C5 rule; the app-state string; Info's and Commit's added
timestamp; the reported application and protocol versions; the module split; and
the suite, CTest, ADR, issue, branch and PR shape. **Nine are fixed by
[`consensus-application-v2`](../specifications/consensus-application-v2.md) and
[ADR 0079](../decisions/0079-the-version-nine-application-contract.md)** and were
cited rather than re-chosen; the remaining two are module structure and
packaging.

Nothing in the slice set or changed supply, allocation, beneficiaries, Founder
ownership, creator hierarchy, commercial routing, AI institutional authority,
bridge scope, content permanence, or what an end user must do, own, run, or
receive. **No accepted vector file, specification, manifest, encoding, or kernel
source changed**, version eight's application is untouched, and `CMakeLists.txt`
only gains registrations.

**M3.20a ran the founder-decision gate and passed it.** Nine decisions were
enumerated before any was judged: the frame's protocol version; the magic; the
field order of kind 2's genesis timestamp; the placement of kinds 5 and 6's block
timestamp; whether kind 4 gains one; the primitive encoding and framing rules;
whether version two is a module or a parameter on version one; the raw-input
bound's source; and the suite, fuzz, CTest, ADR, issue, branch and PR shape.
**Five are fixed by
[`consensus-application-v2`](../specifications/consensus-application-v2.md)** —
the version, the magic, both payload layouts, and kind 4's deliberate exemption —
and were cited rather than re-chosen. The remaining four are module structure,
derivation and packaging.

**The local protocol cannot reach a founder-reserved value by construction**, and
the specification says so: it "remains operational framing rather than canonical
ledger encoding". Nothing in the slice set or changed supply, allocation,
beneficiaries, Founder ownership, creator hierarchy, commercial routing, AI
institutional authority, bridge scope, content permanence, or what an end user
must do, own, run, or receive, and **no accepted vector file, specification,
manifest, encoding, or kernel source changed** — `wire_v1` is untouched and
`CMakeLists.txt` only gains registrations.

**M3.19c ran the founder-decision gate and passed it.** Nine decisions were
enumerated before any was judged: whether `ledger_meta_v9` carries a timestamp
column at all; what that column is named; whether the stamp is written in the
same statement as the height; whether `apply_block` takes the stamp, a clock, or
neither; whether the store applies C5; whether it exposes an uptime schedule or a
`BlockOrder`; the three DDL width literals; the `application_id` and
`user_version` pair; and the suite, CTest, ADR, issue, branch and PR shape.
**Four are fixed by accepted documents** — the three widths by
`v9::kGenesisPrefixBytes`, `snapshot_v9`'s `kFixedSize` and
`v9::kBlockHeaderBytes`, and the C5 placement by
[`consensus-application-v2`](../specifications/consensus-application-v2.md) and
[ADR 0079](../decisions/0079-the-version-nine-application-contract.md) — and were
cited rather than re-chosen. The remaining five are storage layout, naming,
mechanism and packaging, which
[ADR 0007](../decisions/0007-sqlite-ledger-persistence.md) and the standing
delegation place outside the reserved set. The one the previous handoff left
explicitly open — the timestamp column — is storage layout by that same ADR,
which fixes a storage layout as operational data that never defines transaction,
receipt, state-root, or block meaning.

Nothing in the slice set or changed supply, allocation, beneficiaries, Founder
ownership, creator hierarchy, commercial routing, AI institutional authority,
bridge scope, content permanence, or what an end user must do, own, run, or
receive, and **no accepted vector file, specification, manifest, encoding, or
kernel source changed** — every source file is new, `CMakeLists.txt` only gains
registrations, and the two kernel test files change only to expose the raw inputs
each recorded block was offered.

**M3.19b ran the founder-decision gate and passed it.** Fourteen decisions were
enumerated before any was judged: the payload schema version; whether the summary
carries the timestamp and where; whether the genesis timestamp joins the
out-of-band parameters; the four new entry-kind decoders and their refusals; the
widened kind-12 value; the fixed-entry set; the month-index bound; whether the
three restore gates change; the module split; the test and fixture shape; the
fuzz registration; the CMake and CTest naming; the ADR number; and the issue,
branch and PR shape. **Six are fixed by `economy-transition-v9`** — the entry
table, the genesis field table, the sixteen genesis entries, and the month-index
bound — and were cited rather than re-chosen. The remaining eight are storage,
mechanism, testing and packaging, which the founder constitution places outside
the reserved set.

Nothing in the slice set or changed supply, allocation, beneficiaries, Founder
ownership, creator hierarchy, commercial routing, AI institutional authority,
bridge scope, content permanence, or what an end user must do, own, run, or
receive, and **no accepted vector file, specification, manifest, encoding, or
kernel source changed** — every file is new except `CMakeLists.txt`, which only
gains registrations.

**M3.19a ran the founder-decision gate and passed it.** Eighteen decisions were
enumerated before any was judged: the document version and name; the frame
version; which component reads the clock and how it is bound; the conversion and
its two truncation rules; what the bridge may refuse; the decision space and its
eight values; the two added statuses and the deliberate absence of a third and
fourth; whether `InitChain` carries a genesis timestamp and what a mismatch does;
whether `genesis_time` is derived and enforced; whether `Info` and `Commit`
expose the timestamp; whether `PrepareProposal` changes; whether `CheckTx`
changes; the app-state string and the `Info` version fields; the result-code
mapping; the three topology deltas; the required-evidence list; whether the
topology section is restated; and the ADR, issue, branch and PR shape.

**Five are fixed by accepted specifications** and were cited rather than
re-chosen: the unit, range, tolerance, five rules and their normative order by
`calendar-v1`; and the placement of C1, C2 and C5, the genesis timestamp's
C1-only validation, and the absence of a new result code by
`economy-transition-v9`. **The remaining thirteen are mechanism, encoding,
framing, status-space, packaging and naming**, which the founder constitution
places outside the reserved set.

**One was close enough to reserved to be worth naming, and it is recorded rather
than left implicit.** The third topology delta records that a replica whose clock
is outside the tolerance votes against proposals it should accept — a statement
about what a participant must *run* in order to participate. It was classified
**delegated because the requirement is already accepted**: `calendar-v1`'s C5 is
what makes a roughly correct clock a precondition for voting, and M3.19a places
the rule rather than creating it. **Had C5 not already been accepted, choosing to
require a clock at all would have been reserved and the slice would have stopped
and asked**, and `consensus-application-v2` says so, so a later reader can see
which way the classification went and why.

Nothing in the slice set or changed supply, allocation, beneficiaries, Founder
ownership, creator hierarchy, commercial routing, AI institutional authority,
bridge scope, content permanence, or what an end user must do, own, run, or
receive, and **no accepted vector file, specification, manifest, encoding, or
kernel source changed** — every edit outside the two new documents is a
cross-reference or an index entry.

**M3.17c ran the founder-decision gate and passed it.** Twelve decisions were
enumerated before any was judged: the ledger's field shape and its override set;
how the timestamp reaches the block transition; where C1 and C2 run and what a
failure does; the prologue's step order; `run_quiet_heights`' timestamp source;
kind 22's handler and its ladder; which scenarios the vectors record; whether the
execution fixture may sample windows; the receipt's issued amount; and the ADR,
branch and ctest naming. **Five are fixed by `economy-transition-v9`** and were
cited rather than re-chosen. **One is forced** by the chain's own rule that
heights are consecutive, so the execution fixture cannot sample. The rest are
mechanism, storage, testing and packaging, which the founder constitution places
outside the reserved set.

**M3.17b ran it and passed it.** Seven decisions: the package layout; whether the
model subclasses or binds; the fixture's provenance; the vector file's name and
its emitter; which cases the vectors record; where the block header encoder
lives; and the ctest entry names. Every one is packaging, testing or mechanism,
and every value the model carries is fixed by an accepted specification.

Neither slice set or changed supply, allocation, beneficiaries, Founder
ownership, creator hierarchy, commercial routing, AI institutional authority,
bridge scope, content permanence, or what an end user must do, own, run, or
receive, and **no accepted vector file, specification, manifest, encoding, or
kernel source changed** in either.

**M3.17a ran the founder-decision gate and passed it.** Twenty-two decisions were
enumerated before any was judged. **Three are already founder-decided** and were
cited rather than re-chosen: the candidate set and the carry by ADR 0075, and the
accumulation cap's exclusion from the monthly ranking by ADR 0076. **Six are
fixed by accepted specifications**: the unit, the range, the tolerance and the
five rules by `calendar-v1`; the attribution rule, the tie split, the remainder
and the settlement point by `unreferred-pool-payout-v1`. **The remaining thirteen
are encoding, storage, ordering, packaging and naming**, which the founder
constitution places outside the reserved set — the header and genesis field
offsets, the state root's commitment to the timestamp, the four entry kinds and
their key and value layouts, the extended pool value, the transaction kind and
its ladder, the prologue's order, the single-pass closing rule, the label set,
the ADR number, and the issue, branch and PR shape.

**One was close enough to reserved to be worth naming, and it is recorded rather
than left implicit.** Whether a winner's award is a per-seat running balance or a
per-month award decides how many transactions and fees a participant needs in
order to collect, which is a question about what an end user must do to be paid.
It was classified **delegated because the owner had already answered it**: "a
mint takes everything with no quantity choice" is the M3.8a rule that kinds 4, 5
and 18 all implement, and applying an existing founder answer to a new subject is
deduction rather than invention. **Had no such answer existed the slice would
have stopped and asked**, and both the specification and ADR 0077 say so, so a
later reader can see which way the classification went and why.

Nothing in the slice set or changed supply, allocation, beneficiaries, Founder
ownership, creator hierarchy, commercial routing, AI institutional authority,
bridge scope, content permanence, or what an end user must do, own, run, or
receive beyond applying rules already decided, and **no accepted vector file,
manifest, encoding, or kernel source changed** — the slice is additive in every
file it touches except three cross-reference passages.

**The grpc slice ran the founder-decision gate and passed it.** Five decisions
were enumerated before any was judged: the module version to request; whether to
resolve locally or on a hosted runner; whether the bump needs an ADR; the branch,
issue, and PR shape; and the verification path. **Every one is already decided.**
The advisory names `1.83.2` as the first patched version; `CLAUDE.md` requires
dependency locks to be generated on GitHub-hosted runners; `CLAUDE.md` requires
an ADR for **consensus-path** dependencies and gRPC is an indirect dependency of
the replaceable CometBFT adapter that no file here imports; and a dependency
change fails closed to the full hosted matrix. Nothing in the slice set or
changed supply, allocation, beneficiaries, Founder ownership, creator hierarchy,
commercial routing, AI institutional authority, bridge scope, content permanence,
or what an end user must do, own, run, or receive.

**M3.14a ran the founder-decision gate at the start of its session and passed
it.** Nine decisions were enumerated before any was judged: which transactions
the economic chain executes; the seat id and the absence of a referrer; which
replica submits which transaction; whether the audit is exercised; whether to
add initial-height or snapshot-seeded devnet support; the ADR number; Alice's
nonce renumbering; whether the seat blocks land before or after the restart; and
whether the single-node fixture grows them too. **Seat purchase and activation
as biometric-gated transactions are explicitly resolved** — the founder
constitution records them under the 2026-08-13/14 round in ADR 0033 — so
exercising them is delegated work rather than a decision. Whether the audit is
exercised is not a choice at all but the arithmetic finding above, re-derived
against the model rather than trusted: activation at heights 4, 100, and 28,799
all give first cycle window 1 and first audited height 28,800. Adding
initial-height support **would** be a compatibility change needing
`change-protocol` and an ADR, which is precisely why the slice did not quietly
do it and why ADR 0071 says so outright. The remaining six are testing,
packaging, and numbering choices the founder constitution places outside the
reserved set. Nothing in the slice set or changed supply, allocation,
beneficiaries, Founder ownership, creator hierarchy, commercial routing, AI
institutional authority, bridge scope, content permanence, or what an end user
must do, own, run, or receive, and **no accepted vector file, specification,
manifest, encoding, or kernel source changed**.

**M3.13t ran the founder-decision gate and passed it.** Ten decisions were
enumerated before any was judged: the deletion's file set; retention of the two
accepted version-seven vector files; retention of
`simulation/economy_transition_v7/`;
retention of version one; whether `ProtocolV7` stays selectable; the
`serve_connection(ApplicationV7&)` overload; the `economy_v7_fuzz` target; the
two version-seven integrations in `tools/verify.sh`; ADR 0065's expiry; and the
new ADR's number. **Every one is already decided by an accepted document or is
engineering work**: the file set and `ProtocolV7`'s removal by ADR 0065 step 7,
which permits coexistence exactly until this slice and states outright that the
deletion is not optional; the three retentions by that ADR's silence on version
one together with the predecessor pinning M3.13n recorded; and the ADR
numbering, the fuzz-harness migration, and the test rewrites by the founder
constitution's placement of packaging, testing, and engineering choices outside
the reserved set. Nothing in the slice set or changed supply, allocation,
beneficiaries, Founder ownership, creator hierarchy, commercial routing, AI
institutional authority, bridge scope, content permanence, or what an end user
must do, own, run, or receive, and **no accepted vector file changed**.

**M3.14e ran the founder-decision gate and passed it.** Fourteen decisions were
enumerated before any was judged: whether the supervisor gains a control channel
at all; its shape, its wire format and its request bound; that a stop takes all
three of a replica's processes rather than only its consensus node; how the
watch loop distinguishes a deliberate stop from a crash; that a request executes
on the main loop rather than in the accept goroutine; which health comparisons
narrow with the replica subset and which do not; the CLI surface on both the
command and the wrapper script; which replica departs, how many transactions
commit while it is away and through which replicas; what catching up is required
to reach; and every timeout. **Every one is delegated by
`founder-constitution.md` lines 1093-1096**, which place mechanism, encoding,
storage, consensus scheduling, networking, testing, packaging, and operational
choices outside the reserved set. No consensus-visible behaviour changed at all
— the kernel, the contracts, the encodings and the genesis are untouched — which
is why `change-protocol` was not invoked. An ADR *was* written this time, unlike
M3.14d, because the slice records rules that outlive it: what the control
channel is, what the subset does and does not narrow, and why a partition stays
untested. Nothing in the slice set or changed supply, allocation, beneficiaries,
Founder ownership, creator hierarchy, commercial routing, AI institutional
authority, bridge scope, content permanence, or what an end user must do, own,
run, or receive.

**M3.14d ran the founder-decision gate and passed it.** Nine decisions were
enumerated before any was judged: which replica is driven and at what point;
whether the mid-block interruption needs a fault-injection seam; which block is
staged and which is refused; whether the fixture gains a whole-block accessor or
only a root; whether the network is started a third time and what it must then
commit; whether the RPC-timeout repair belongs in this slice or another; what
the health probe's per-attempt bound should be; whether an ADR is needed; and
the issue, branch and PR shape. **Every one is testing, harness, or engineering
work.** The refusal and the staging semantics are the accepted application
contract's and are *exercised* rather than chosen. The Go change alters how long
a devnet client waits for its own RPC and nothing a node accepts; `CLAUDE.md`
places Go in replaceable infrastructure and this is the harness rather than the
bridge or the node. No ADR was written because the slice records no rule that
outlives it: what it found about the Go harness is a description of code the
next slice changes, which belongs in this document rather than in a decision
record. Nothing in the slice set or changed supply, allocation, beneficiaries,
Founder ownership, creator hierarchy, commercial routing, AI institutional
authority, bridge scope, content permanence, or what an end user must do, own,
run, or receive.

**M3.14c ran the founder-decision gate and passed it.** Eight decisions were
enumerated before any was judged: which refusals the driven application is made
to produce; whether it is driven as a process over the socket or in C++ beside
the kernel; whether the wire framing becomes a shared module; where the test
lives and what its ctest entry is called; whether the terminal latch and the
recovery a restart gives are choices or observations; whether an ADR is needed;
the issue, branch and PR shape; and whether the slice also attempts the
partition and the mid-block restart. **Every one is testing, packaging, or
scoping work.** The refusal semantics are decided by the accepted application
contract and are *exercised* rather than chosen — the slice adds, removes, and
widens nothing a node accepts, and each status is compared by name so a
renumbered error space would be reported instead of agreed with. The ADR records
a layering the slice observed rather than a rule it chose. Nothing in the slice
set or changed supply, allocation, beneficiaries, Founder ownership, creator
hierarchy, commercial routing, AI institutional authority, bridge scope, content
permanence, or what an end user must do, own, run, or receive.

**M3.14b ran the founder-decision gate and passed it.** Nine decisions were
enumerated before any was judged: which refusals the network is made to
exercise; whether each is an admission or an execution refusal; whether the
devnet CLI and `Broadcast` must change to report convergence after a refusal;
what the Python helper for a refused submission returns; which replica submits
each refused transaction; whether the refusals go in the existing four-validator
test or a new one; whether the slice also attempts a partition or a mid-block
restart; whether an ADR is needed; and what the fixture affordance is called.
**Every one is testing, harness, or scoping work.** The refusal codes themselves
are decided by the accepted `economy-transition-v8` contract and are *exercised*
rather than chosen — the slice adds, removes, and widens nothing a node accepts,
and `CODE_NUMBER` is read rather than transcribed so a renumbered code space
would be reported instead of agreed with. `CLAUDE.md` places Go in replaceable
infrastructure, and the change is to the devnet harness's reporting rather than
to the bridge, the node, or any consensus path. Nothing in the slice set or
changed supply, allocation, beneficiaries, Founder ownership, creator hierarchy,
commercial routing, AI institutional authority, bridge scope, content
permanence, or what an end user must do, own, run, or receive.

**M3.15a ran the founder-decision gate and passed it.** Twelve decisions were
enumerated before any was judged: the canonical unit; the epoch; the calendar
system; the zone the 1st is read in; leap-second treatment; the monotonicity
rule; the tolerance's value and the fact that it is two-sided; the month
identifier's encoding; the accepted timestamp range and its year bound; the
genesis-timestamp requirement; the chain's partial first month; and the
packaging — the model layout, the vector method, the ctest entries, and the ADR
number. **Every one is delegated.** ADR 0050 names the mapping, the boundary
rule, the acceptance tolerance and the derivation from the header field as
`calendar-v1`'s to fix, and requires only that the tolerance be small relative to
a month and be a consensus parameter rather than an adapter default; the Founder
Constitution decided the month itself on 2026-08-19 and places mechanism,
encoding, storage, consensus scheduling, networking, testing and packaging
outside the reserved set. **UTC was deduced rather than chosen** — a consensus
timestamp is one global value and there is no participant zone consensus could
read — and the specification states the participant-visible consequence outright
rather than burying it in the arithmetic. Nothing in the slice set or changed
supply, allocation, beneficiaries, Founder ownership, creator hierarchy,
commercial routing, AI institutional authority, bridge scope, content
permanence, or what an end user must do, own, run, or receive, and **no accepted
vector file, specification, manifest, encoding, or kernel source changed** — the
slice is additive in every file it touches except two cross-reference lines.

**Two founder-reserved decisions were raised at the close of M3.15a and were
answered the same day.** Both are inside the unreferred pool's payout and both
decide who receives value, which is the test that made them reserved rather than
mechanism. They were enumerated during M3.15a's gate, recorded as not-yet-
blocking, and raised the moment `calendar-v1` was accepted and they became the
nearest dependency. **The answers are founder-directed inputs to the payout
slice and are recorded in ADR 0075 and in the Founder Constitution**; they are
restated here only because this document is what the next session reads first.

* **The candidate set is every seat in scope at any point in the month**, ranked
  on uptime accumulated during that month. The owner's reasoning is the one the
  question named: a seat that ran 29 of 30 days and whose 731-cycle span ended
  on the 30th is exactly the machine the pool exists to reward, and a
  month's-end snapshot would pay a worse performer instead. **It also removes a
  failure mode at the end of the distribution**, where a month's-end rule would
  shrink the candidate set toward empty as spans expire.
* **An accrual with no candidate carries to the earliest subsequent month that
  has one**, which takes it entirely. This is ADR 0049's recovery-pool shape
  applied to the monthly pool rather than a second mechanism invented for it,
  and it keeps the monthly accrual inside the monthly ranking instead of letting
  a day's best performer collect what a month's ranking was meant to award.

**One consequence of the second answer is recorded rather than left to be
discovered**: a final accrual at the very end of the distribution may have no
later month at all. The carry rule does not say where that goes, the question
put it as the option's cost, and it is the payout slice's to raise again if its
own model shows the case is reachable rather than theoretical.

The remaining payout decisions are **not** reserved and must not be sent to the
owner as though they were: the constitution names the pool's remainder rule, the
storage bound on accrued referral balances at 100,000 seats, and when a referral
benefit begins for a seat purchased but never activated as specification work
outright.

**A third founder-reserved decision was found while starting the payout slice,
and it was answered the same day.** It was not surfaced when the first two were
asked, and it was recorded rather than resolved in-session because resolving it
would have decided who receives value.

**`economy-transition-v7` said what competes for the monthly pool, and the
answer of 2026-09-14 did not match it.** The accepted text is: "The eligible set
is **every** in-scope seat that met the cycle's duty threshold and is under the
accumulation cap, in span or not... it is what competes for the daily
reallocation, for the recovery pool, **and for the monthly unreferred pool**."
That sentence is a pointer rather than a complete rule — it is defined per cycle
and says nothing about how thirty cycle-sets combine into a month — which is why
the question of whose figure is compared over a month was real and was answered.
But it carried **two filters the answer did not**, and both are now settled.

* **The duty filter** was put to the owner as an option and declined, so ADR
  0075 supersedes version seven on it. The effect is small: a seat that met no
  cycle has a figure of zero and wins only where every candidate is at zero,
  which "whatever that figure is" contemplates.
* **The accumulation cap does not filter the monthly ranking.** A seat at the
  thirty-window cap competes and can win. The owner's reasoning is that the cap
  exists to stop unminted permissions piling up, and a monthly pool payout is a
  claim the seat has **never been offered** rather than one it declined to
  collect, so ADR 0035's daily rule does not reach it. ADR 0076 records it.

**One thing about how this was found is worth keeping.** ADR 0049 — the decision
version seven implements — makes the same forward reference with the duty filter
and **without** the cap. The cap entered the monthly clause in version seven's
*restatement* rather than in the decision it restated, and it went unnoticed for
two weeks because nothing executes the clause. **A forward reference in an
accepted document is checked by no test**, because there is nothing to test
until the thing it points at is built; the slice that builds it is the first
reader since the author. Reading the accepted contracts *before* asking the
founder-decision questions, rather than after, would have put all three in one
batch instead of two.

**M3.16a ran the founder-decision gate and passed it.** Thirteen decisions were
enumerated before any was judged. **Three are already founder-decided** and were
cited rather than re-chosen: the candidate set and the carry by ADR 0075 and ADR
0076, and the single-best-plus-exact-ties rule by the constitution. **Three the
constitution names as specification work outright**: the pool's remainder rule,
the storage bound on accrued referral balances, and when a referral benefit
begins for a seat purchased but never activated. **Four are decided by accepted
specifications**: the month and the finality argument by `calendar-v1` and ADR
0074, and the figure, `in_scope` and `in_span` by `economy-transition-v8` and
`cycle-boundary-v1`. **The remaining three are mechanism** the constitution
places outside the reserved set: the attribution granularity, the step ordering,
and the storage layout. **The claim shape is a deduction rather than a choice** —
ADR 0041 ties a seat to an identity rather than an address, so there is no
address a payout could credit and it has to be a claim the winner mints.
Nothing in the slice set or changed supply, allocation, beneficiaries, Founder
ownership, creator hierarchy, commercial routing, AI institutional authority,
bridge scope, content permanence, or what an end user must do, own, run, or
receive, and **no accepted vector file, specification, manifest, encoding, or
kernel source changed**.

**No blocker requires an owner answer.** The successors under "Exact next
action" — the version-nine C++20 kernel and the stack behind it, the
application-contract version that carries a timestamp, the nonzero initial
height, the snapshot-seeded devnet, and ADR 0048's threat model — are all
unblocked. **The kernel and the contract have since been delivered**, by M3.18a,
M3.18b and M3.19a; the rest of the sentence still holds.

**One case ADR 0075 left open is closed by derivation rather than by an
answer, and it must not be re-asked.** It asked what becomes of a final accrual
at the end of the distribution with no later month that has a candidate. M3.16a
proved the case unreachable: in-span implies in-scope, in-scope never expires,
so every month that accrued has a candidate and is paid in the month after it.
**Raising it again would be asking the owner to decide something the accepted
contracts already settle.**

**The following paragraph is M3.14e's and is retained as history.** The next
slice, M3.14e, is unblocked,
and unusually well specified for one that has not started: the three properties
of the Go harness that block it are named above, established by reading
`adapter/cometbft/internal/devnet` rather than guessed, and the one design trap
in it — two readers on the supervisor's `events` channel — is named with its
answer. Nothing it needs is a founder-reserved value. Its cost is that
`internal/devnet` reaches CometBFT through `nodeconfig`, so every behavioural
check is a hosted matrix round trip; type-check it offline against stubs with
`GOPROXY=off` first.

**One correction is on the record and matters more than a blocker would, and it
is now closed.** This document told two sessions in a row that a chain selling a
seat would give the uptime audit subjects. It does not, and the reason is a
constant rather than a defect. A slice planned against that sentence would have
spent itself discovering the 28,800-block wall. **M3.14a closed it in the only
durable way**: ADR 0071 records the finding, and two fixture checks —
`check_the_audit_is_out_of_reach` and `check_the_seat_is_sold_and_unaudited` —
derive the first audited height from the contract's own rule, so a network that
did reach its seat's first window fails rather than passing while the prose
beside it goes quietly wrong. **The general lesson is the one M3.13t already recorded in
a different form**: a plan written before its dependencies landed must re-derive
its own preconditions rather than trust the sentence that authorised it — and a
claim about what a fixture will *observe* is worth probing against the model
before it is worth building.

**One standing operational note rather than a blocker.** This document is
7,000-plus lines and roughly half a megabyte. It is the first thing every
session is instructed to read, and it can no longer be read in full efficiently;
several passages were already describing superseded state before M3.13t touched
them. Splitting the accumulated per-slice lessons out of the live handoff facts
would be its own slice, and it is worth doing before the document costs a
session more than it saves.

**M3.13s ran the founder-decision gate and passed it.** Eleven decisions were
enumerated before any was judged: the genesis allocation bound of 142 octets;
the binary's name and its two argument forms; the app state string a home is
initialised with; the codespace name for version eight's result codes; the
`ProtocolV8` value and whether version seven stays selectable while the
migration is in flight; the receipt version octet and the result-code count in
the Go decoder; whether `FinalizedBlockV8` carries a block identifier; the
`-protocol-version 8` flag value; which scenarios the two integrations run;
the fixture's key labels and transaction set; and whether the version-eight
fixture needs a second genesis authority key of its own. **Every one is already
decided by an accepted document or is engineering work**: the bound, the receipt
figures, and the result count by `include/protocol/v8/economy.hpp` and the
accepted `economy-transition-v8` contract; the app state by ADR 0068, which
`ApplicationV8::init_chain` already enforces; the finalized-block shape by ADR
0059 and ADR 0068, since version eight adds no field to it; version seven
remaining selectable by ADR 0065, which permits coexistence exactly until step
7; and the naming, flag values, and test scenarios by the founder constitution's
placement of packaging, operational, and testing choices outside the reserved
set. The dispute authority key is a *genesis field the accepted contract already
decided*; this slice writes one into a fixture and never chooses what it
authorizes. Nothing in the slice set or changed supply, allocation,
beneficiaries, Founder ownership, creator hierarchy, commercial routing, AI
institutional authority, bridge scope, content permanence, or what an end user
must do, own, run, or receive, and **no accepted vector file changed**.

**M3.13r ran the founder-decision gate and passed it.** Thirteen decisions were
enumerated before any was judged: `kApplicationProtocolVersionV8`; the expected
app state string; the receipt width and version assertions; the seven
operations and their sequencing; `finalize_block` pure and `commit` replaying
and comparing; the terminal latch; `process_proposal` executing against a
candidate copy; the frame format and whether a version-eight wire exists; the
finalized block's root-then-identifier order; the store taken by value; the
verifier taken from the store; target names and ctest arguments; and whether
version eight's per-height audit changes this layer. **Every one is already
decided by an accepted document or is engineering work**: the first two by ADR
0058's own convention that the application protocol version is the ledger
version, which makes deducing version eight's values delegated work rather than
a choice; the receipt figures by `v8::economy.hpp`; the operations, sequencing,
latch, and candidate copy by ADR 0058; the frame format and response shape by
ADR 0059; the store by value by ADR 0007; the verifier by ADR 0045; and the
rest by this repository's conventions. The last is a derived fact rather than a
decision: nothing under `src/application/` names a schedule, a seat, or a
window. Nothing in the slice set or changed supply, allocation, beneficiaries,
Founder ownership, creator hierarchy, commercial routing, AI institutional
authority, bridge scope, content permanence, or what an end user must do, own,
run, or receive, and **no accepted vector file changed**.

**M3.13q ran the founder-decision gate and passed it.** Twelve decisions were
enumerated before any was judged: the SQLite `application_id` and
`user_version`; the two table names; the `canonical_genesis` width; the
`head_snapshot` minimum; the block header column's width; whether `apply_block`
keeps an uptime parameter; whether the store exposes `BlockOrder`; whether it
gains a jump-to-height operation; the error enumeration's numbers and meanings;
the four validation steps and their order; the seven fault points and the
recovery contract; and whether the slice records an ADR or a transition
specification. **Every one is already decided by an accepted document or is
engineering work**: the schema figures by ADR 0007, which classifies storage
rows, files, schemas, and snapshot formats as operational compatibility data
that "never define transaction, receipt, state-root, or block meaning"; the two
widths derived from `v8::kGenesisPrefixBytes` and `snapshot_v8`'s `kFixedSize`
rather than chosen; the dropped parameter by `v8::execute_block`'s own signature
under ADR 0064; the absent `BlockOrder` by `ledger.hpp`'s statement that none of
those flags is a configuration a chain has; and the rest by ADR 0057. Nothing in
the slice set or changed supply, allocation, beneficiaries, Founder ownership,
creator hierarchy, commercial routing, AI institutional authority, bridge scope,
content permanence, or what an end user must do, own, run, or receive, and **no
accepted vector file changed**.

**M3.13p's gate result is not recorded here and should have been.** The slice
touched no reserved surface — a snapshot format is operational data by the same
ADR 0007 clause — so the omission is a reporting gap rather than a skipped
check, and it is recorded as a gap rather than back-filled from memory. The
repository is the source of truth, and what the repository can show is that no
accepted vector file changed in PR #253 and that ADR 0066 records only
mechanism.

**M3.13o ran the founder-decision gate and passed it.** Fourteen decisions were
enumerated before any was judged: whether `include/protocol/v8/ledger.hpp` is a
copy or a new design; the two transitions' ordered rejection conditions; the
four block steps and what each reads and writes; the schedule derivation; the
six added invariants; kind 20's debit; whether `execute_block` keeps an uptime
parameter; how the uptime evidence is held on the C++ ledger; where the three
demonstration flags live; whether the uptime invariants are split from the
conservation gate; the quiet-height runner and its beacon; the test target's
name and vector arguments; which mutation probes to run; and where
`kActivityThresholdSeconds` is declared. **Every one is already decided by an
accepted document or is engineering work**: the transitions, the steps, the
derivation, and the invariants by `economy-transition-v8.md`; kind 20's debit by
ADR 0064's derivation from the owner's answer of 2026-09-02; the parameter's
removal by the specification's own "what version eight changes" table; and the
rest by this repository's conventions. Nothing in the slice set or changed
supply, allocation, beneficiaries, Founder ownership, creator hierarchy,
commercial routing, AI institutional authority, bridge scope, content
permanence, or what an end user must do, own, run, or receive, and **no accepted
vector file changed**.

**M3.13n ran the founder-decision gate and passed it.** Fifteen decisions were
enumerated before any was judged: whether `src/v8/` sits beside `src/v7/` or
replaces it; which of version seven's sources are the codec half; the two kind
numbers and their body layouts; the two entry kinds, their widths, and the pad
rule; the twelve result codes and the count at 45; the ninth genesis field, its
offset, and the 142-octet prefix; the three re-versioned labels and the two new
ones; the selection preimage, its truncation, and its modulus; the dispute
message's preimage; whether `kFrozenUnreachableCodes` grows; whether selection
gets its own translation unit; the test target's name and vector arguments;
whether the codec declares the two predecessor constructions; the encoding
consequence of the fee exemption; and the slot-index bound. **Every one is
already decided by an accepted document or is engineering work**: the first by
ADR 0065, the next nine by `economy-transition-v8.md` and its recorded vectors,
the fourteenth by the owner's own answer of 2026-09-02 as recorded in ADR 0063
and ADR 0064, and the rest by `uptime-measurement-v1` or by this repository's
own conventions. Nothing in the slice set or changed supply, allocation,
beneficiaries, Founder ownership, creator hierarchy, commercial routing, AI
institutional authority, bridge scope, content permanence, or what an end user
must do, own, run, or receive, and **no accepted vector file changed**.

**None. The one founder question this milestone raised was asked and
answered on the same day.** M3.13j ran the founder-decision gate over twelve
decisions, eleven were delegated, and the twelfth was the fee treatment of a
challenge response. `economy-transition-v8` carried the version-seven fixed fee
as a *default rather than a decision* — applying an accepted uniform rule to a
new kind invents nothing while carving out the contract's first exemption
would — and named it as the one defaulted reserved value. Under that default a
machine would have paid about twenty-four fixed fees per cycle to prove the
uptime it is paid for, and at the 100,000-seat capacity the population would
have offered about 2.4 million fee-paying transactions per day.

**On 2026-09-02 the owner answered: the challenge response is fee-exempt.**
M3.13m implemented it. Kind 20 charges nothing and carries a zero fee limit,
refused at admission rather than ignored at execution, on kind 10's precedent;
unlike kind 10 it **keeps its nonce**, because a registration has no escrow and
therefore no nonce sequence while a response has both. The relayed dispute is
not exempt: a response is a machine answering an audit the chain demanded of it,
and a dispute is a third party relaying someone else's judgment.

**The timing is the argument for asking at the specification stage.** The rule
was one sentence in one transition and it was settled before the execution
model, the execution vectors, and the kernel depended on it. The same question
answered after a kernel exists is a re-versioning.

**The rest of M3.13j was unblocked on the founder side, and that is a finding
rather than an assumption**: `uptime-measurement-v1` puts *the content of a
challenge* — the concrete resource commitment — in its own "explicitly not in
scope" list and treats the answer as an abstract predicate, so a transition
version can bind the pipeline without settling it. Version eight instantiates
that predicate as the weakest one available and says so, which cannot pre-empt
the founder's answer because a later version can only tighten it.

**M3.13l ran the founder-decision gate and passed it.** Fifteen decisions were
enumerated before any was judged: whether the execution model extends version
seven's ledger or restates it; how the two new entry kinds reach the projection;
whether `Outcome`, `admit`, and `require_consistent` are imported or restated;
what the acting escrow must cover for a fee-exempt kind; whether `execute_block`
keeps an uptime parameter; where the six added invariants run; whether the uptime
evidence is typed or raw; whether `advance_to` survives; how a trace answers a
challenge it could not predict; the fixture's keys, seats, heights, and windows;
which scenarios the file records; whether the vector file is emitted or
transcribed; which mutations the probes make; how the settlement claim is
checked; and whether the two step orderings get demonstration flags. **Fourteen
are model, fixture, encoding, or engineering work.**

**The fifteenth is the one worth naming, and it is a derivation rather than a
choice.** What a fee-exempt challenge response's acting escrow must cover touches
what an end user must own in order to be paid, which is reserved — but the owner
already answered the question it belongs to on 2026-09-02: answering a mandatory
audit costs an operator nothing. A nonzero debit would contradict that answer by
requiring a balance, so the value is not among the ones the decided principle
leaves open. It is recorded in ADR 0064 and added to the accepted specification
as a stated consequence rather than a new rule. Nothing else in the slice set or
changed supply, allocation, beneficiaries, Founder ownership, creator hierarchy,
commercial routing, AI institutional authority, bridge scope, or content
permanence, and **no accepted vector file changed**.

**M3.13k ran the founder-decision gate and passed it.** Eight decisions were
enumerated before any was judged: whether the model is a new package or an
extension of version seven's; how the carried surface is declared; the fixture's
keys, seats, and heights; whether the vector file is emitted or transcribed;
which source each vector's second derivation comes from; how the settlement
claim is checked; which mutations the probes make; and where the two transitions
live in the package. **Every one is model, fixture, or engineering work.**
Nothing in the slice set or changed supply, allocation, beneficiaries, Founder
ownership, creator hierarchy, commercial routing, AI institutional authority,
bridge scope, content permanence, or what an end user must do, own, run, or
receive, and no accepted vector file changed. **One correction was made to an
accepted document rather than a decision taken**: the genesis field table's
order, which the encoder already fixed and the specification had stated wrongly.

**M3.13j ran the founder-decision gate and recorded its result.** Twelve
decisions were enumerated before any was judged: whether the carrier is a new
transition version or an edit; the numeric assignment of the two kinds and two
entries; whether a duty report gets a carrier; the response's authority; the
dispute's authority and whether it is relayed; whether the dispute key is
separate from the verifier key; the selection preimage; the sparse window
record; the block-step order; the twelve result codes and the five deliberately
absent ones; the retention rule; and the response's fee. **Eleven are delegated
and each is cited in ADR 0063** — to `uptime-measurement-v1`, to
`cycle-boundary-v1`, to ADR 0045, 0047, 0048, 0049, 0050, and 0055, or to
version seven's own immutability clause. The twelfth is the one above.

**M3.13i ran the founder-decision gate and passed it.** Six decisions were
enumerated before any was judged: which protocol version the devnet defaults to;
how that version reaches the supervisor, the genesis, and each bridge; which
application binary the supervisor starts; whether the devnet harness is shared
or copied; whether the fixture stays a frozen list or becomes a live session;
and what the four-node scenario asserts. **Every one is operational,
engineering, or testing work.** Nothing in the slice sets or changes supply,
allocation, beneficiaries, Founder ownership, creator hierarchy, commercial
routing, AI institutional authority, bridge scope, content permanence, or what
an end user must do, own, run, or receive, and no accepted vector file changed.
**One decision was settled by measurement rather than preference**: the fixture
became a live session because an empty version-seven block moves the state root,
which was demonstrated locally before the design changed.

**M3.13h ran the founder-decision gate and passed it.** Six decisions were
enumerated before any was judged: whether the real-signing fixture is Python or
C++; how its keys are derived; the scenario's shape and which kinds it
exercises; whether the record is a new vector file or an addition to an accepted
one; which genesis parameters the fixture opens on; and whether the C++ kernel
also checks it. **Every one is fixture, encoding, or engineering work**, and the
trace genesis's existing figures were reused rather than any being chosen. No
accepted vector file changed, because the fixture is computed at test time from
the independent model, which is what version one's integration already does.

**M3.13g ran the founder-decision gate and passed it.** Nine decisions were
enumerated before any was judged: whether the Go client reuses version one's
frame codec or gets its own; how the version-seven finalized block decodes; what
the adapter does with the block identifier ABCI has no field for; the replay
handshake; whether the finalize guard applies to version one as well; the ABCI
codespace for version seven's result codes; the genesis application state; one
bridge binary with a flag against two binaries; and which version that flag
defaults to. **Every one is encoding, mechanism, operational, or engineering
work**, which `founder-constitution.md` places outside the reserved set: ADR 0058
already fixes the application state, ADR 0059 already fixes the wire, and the
rest are adapter internals. Nothing in the slice sets or changes supply,
allocation, beneficiaries, Founder ownership, creator hierarchy, commercial
routing, AI institutional authority, bridge scope — the asset-bridge sense, not
the ABCI process that shares the word — content permanence, or what an end user
must do, own, run, or receive, and **no accepted vector file changed**.

**One decision was settled by reading the engine rather than by choosing.** The
replay handshake looked like a design question and was a question of fact:
CometBFT v0.39.4 never asks the real application to finalize a height it has
committed. Fetching `consensus/replay.go` and `state/execution.go` over HTTPS
cost seconds and replaced a guess that would have shaped the whole slice.

**M3.13f ran the founder-decision gate and passed it.** Six decisions were
enumerated before any was judged: which of version one's fault points the
version-seven write path raises at and which it merely invokes; whether a
pre-commit failure poisons the store or is an ordinary refusal; what recovery
does and whether it may throw; what a store whose recovery failed answers; how a
terminated process is exercised; and whether the contract is recorded in a new
ADR or as an amendment to ADR 0057. **Every one is storage, operational, or
testing work**, which `founder-constitution.md` places outside the reserved set,
and version one already answers four of them by precedent. Nothing in the slice
sets or changes supply, allocation, beneficiaries, Founder ownership, creator
hierarchy, commercial routing, AI institutional authority, bridge scope, content
permanence, or what an end user must do, own, run, or receive, and no accepted
vector file changed. **One correction was made rather than a choice invented**:
the original poison-on-any-write-failure behaviour was wrong against ADR 0057's
own text, which said the store is poisoned "if the write itself fails".

**M3.13e ran the founder-decision gate and passed it.** Five decisions were
enumerated before any was judged: whether the decoder restates the validity rule
or delegates it to the encoder; the genesis file's format and the bound on
reading it; the binary's command surface and whether it is a separate executable
or a mode of version one's; whether opening precedes creating; and what the serve
loop does with a failed connection. **Every one is encoding, packaging, or
operational work**, which `founder-constitution.md` places outside the reserved
set. The eight values inside a genesis are founder-directed and **already
fixed** — the slice reads them from a file and changes none of them, and the
recorded `genesis.bytes` is what it is checked against. Nothing in the slice sets
or changes supply, allocation, beneficiaries, Founder ownership, creator
hierarchy, commercial routing, AI institutional authority, bridge scope, content
permanence, or what an end user must do, own, run, or receive, and no accepted
vector file changed.

**M3.13d ran the founder-decision gate and passed it.** Six decisions were
enumerated before any was judged: whether the frame format is reused or
re-versioned; the response payload layout for the three responses that differ,
including whether the finalized block carries a block identifier; what the
encoder validates before writing rather than merely serialising; whether the
socket grows an overload, a second loop, or a renamed class; how the tagged chain
identity is converted; and whether the server binary and the Go adapter are in
scope. **Every one is transport encoding or packaging**, which
`founder-constitution.md` places outside the reserved set alongside mechanism,
storage, consensus scheduling, and networking. Nothing in the slice sets or
changes supply, allocation, beneficiaries, Founder ownership, creator hierarchy,
commercial routing, AI institutional authority, bridge scope, content
permanence, or what an end user must do, own, run, or receive, and no accepted
vector file changed.

**M3.13c ran the founder-decision gate and passed it.** Ten decisions were
enumerated before any was judged: whether version seven gets its own application
class or version one's is parameterised; whether the error enumeration is reused
or restated; how the `finalize_block`/`commit` split reconciles with a store that
writes the head and the block row together; whether the stage holds the candidate
state or only its root; whether `process_proposal` executes or checks bounds
only, and whether the store grows a dry-run operation for it; the
`prepare_proposal` policy; the app-state string and the `init_chain` predicates;
where the verifier comes from; the response code scheme; and whether the wire and
the Go adapter are in scope.

**Every one is delegated.** `founder-constitution.md` places mechanism, encoding,
storage, consensus scheduling, networking, and packaging outside the reserved
set, and an ABCI adapter's operation sequencing is squarely networking and
scheduling. ADR 0007 fixes the persistence boundary the layer sits on and ADR
0045 fixes that the layer never chooses a verification rule, which is what makes
"take it from the store" a deduction rather than a choice. **One decision was
examined closely rather than waved through**: `prepare_proposal`'s ordering
policy could have economic consequences, and the answer — keep the order the
engine handed us, truncated at the budget — invents nothing and is version one's.
A reordering policy *would* need asking, and none is introduced. Nothing in the
slice sets or changes supply, allocation, beneficiaries, Founder ownership,
creator hierarchy, commercial routing, AI institutional authority, bridge scope,
content permanence, or what an end user must do, own, run, or receive, and no
accepted vector file changed.

**One founder-reserved decision moved closer and does not block M3.13d.** The
concrete resource commitment — what a Founder Machine must prove it holds — is
what an uptime measurement is a measurement *of*. `ApplicationV7` hands
`execute_block` a null uptime schedule, so nothing in the repository yet needs
the answer; the moment a chain is asked to accrue to seats through this layer, it
does. Ask it when a challenge must actually be constructed, as recorded below,
and not before.

**M3.13b ran the founder-decision gate and passed it.** Twenty decisions were
enumerated before any was judged: whether the store is a new adapter or a version
parameter on `SQLiteLedger`; the persistence engine; whether the connection,
locking, journal, and path contract is reused or restated; the head's
representation as a payload rather than rows; the DDL, the table names, the
column types and their `CHECK` constraints, and the big-endian height encoding;
the pinned `application_id` and `user_version`; the error enumeration and its
numbers including `invalid_snapshot` at 13; the mapping from version one's codes;
the four reopen validation steps and their order; whether the height and root
columns must agree with the restored payload; whether a block at a wrong height
is a rejection or a storage error; whether a failed write poisons the store and
whether an encode failure does; whether recovery after poisoning is implemented
now; where the signature verifier comes from; which recorded scenario supplies
the evidence and how many of its blocks are contiguous; whether the store gains a
"jump to height" operation to make the other four replayable; whether block
history is replayed on open; the block row's columns; whether concurrent readers
are supported; and retaining each block's raw inputs on the kernel trace.

**Every one is delegated and the evidence is in three places.**
`founder-constitution.md` places mechanism, encoding, storage, consensus
scheduling, networking, packaging, and testing outside the reserved set. ADR 0007
fixes the persistence boundary and states outright that "storage rows, files,
schemas, and snapshot formats are operational compatibility data" which "never
define transaction, receipt, state-root, or block meaning" — which is what makes
the head's representation an engineering choice rather than a contract one. ADR
0045 fixes that the layer never chooses a verification rule, which is why the
verifier is supplied at construction. Nothing in the slice sets or changes supply,
allocation, beneficiaries, Founder ownership, creator hierarchy, commercial
routing, AI institutional authority, bridge scope, content permanence, or what an
end user must do, own, run, or receive. **No accepted vector file changed and no
new one was added**, and the one kernel edit is inert by the same evidence: the
header committed to the same transaction root before and after.

**M3.13a ran the founder-decision gate and passed it.** It enumerated seventeen
decisions the slice had to settle — whether the snapshot is a storage artifact or
a kernel one; whether it is recorded by an ADR or a transition specification;
whether a new accepted vector file is added; the magic, the version
discriminator, the prefix layout, and the field order; which genesis parameters
ride beside the summary and whether the verifier key's two copies must agree;
whether `assigned_permissions` is encoded or re-derived; the strictness rule each
value decoder enforces; whether the assignment record's bitmap pad bits are
refused; whether ordering is checked at the parse or at the root; the three
restore gates and their order; the error enumeration; the digest domain label;
which vector file the tests read and what they compare against; whether
`kChannelCount` moves to the codec header; the test target and CMake
registration; and the fuzz target's shape. **Every one is fixed by ADR 0007's
precedent, issue #202's recorded design, the accepted `economy-transition-v7`
specification, `docs/engineering/verification.md`, or `CLAUDE.md`'s rule that
storage integrations remain replaceable adapters — or is encoding, mechanism, or
layout**, which `founder-constitution.md` names as engineering work. **None is
consensus-visible at all**: a snapshot is node-local and reaches consensus only
through a root it must reproduce, so none of them sets or changes supply,
allocation, beneficiaries, Founder ownership, creator hierarchy, commercial
routing, AI institutional authority, bridge scope, content permanence, or what a
participant must do, own, run, or receive. No question was asked because none was
reserved.

**One decision inside that set was classified deliberately rather than by
default, and it is the one worth naming.** Refusing an assignment record whose
bitmap pad bits are set makes the snapshot stricter than the kernel's own
decoder. That would be a compatibility decision if it were made in the kernel —
and it is not made there for exactly that reason. In a node-local decoder it
changes no accepted state, so it is engineering work; in `decode_cycle_assignment_value`
it would be a `change-protocol` slice against an accepted specification that
fixes the bitmap width without stating the pad rule.

M3.12b ran the founder-decision gate and **passed** it. It
enumerated eighteen decisions the slice had to settle — whether version seven
replaces version six in the kernel or sits beside it; which constructions
re-version and which keep the version that accepted them; the retirement of
entry kind 7 and the widths of entry kind 17; the cycle assignment record's
layout and its 64-octet fixed part; whether the encoder, the decoder, or both
refuse a nonzero absorbed amount at a zero winner count; the order of steps 6
and 7; whether the winner derivation may filter by span; how `claimable` is
derived; where the assignment reads a seat's mark and recorded referrer; whether
the assignment is a prologue or an epilogue; what a measurement naming an unsold
seat does to a block; the manifest binding; the three schema versions; whether
the block header and transaction tree re-version; which vector files each test
target reads; whether version six's execution tests are retargeted or kept; the
module layout and file names; and the fate of the inherited carry field.
**Every one is fixed by the accepted `economy-transition-v7` specification, ADR
0045, ADR 0046, ADR 0049, ADR 0053, ADR 0054, ADR 0055, or
`docs/engineering/verification.md`, or is encoding, mechanism, or layout**,
which `founder-constitution.md` names as engineering work. None sets or changes
supply, allocation, beneficiaries, Founder ownership, creator hierarchy,
commercial routing, AI institutional authority, bridge scope, content
permanence, or what a participant must do, own, run, or receive: every
founder-directed figure is read from the accepted manifest rather than restated.
No question was asked because none was reserved.

**M3.12a ran the same gate and passed it.** It
enumerated seven decisions the slice had to settle — which kinds the added
scenarios must reach; whether the step fixtures are imported from version six
or restated; the block and nonce ordering each scenario needs; which refusals
belong in it; whether ADR 0055 is corrected in place or superseded by a new
record; where the coverage claim is asserted; and the vector layout. **Every
one is fixed by the accepted version-seven specification, version six's
rejection orders, or `docs/engineering/verification.md`, or is encoding,
mechanism, or layout**, which `founder-constitution.md` names as engineering
work. None sets or changes supply, allocation, beneficiaries, Founder
ownership, creator hierarchy, commercial routing, AI institutional authority,
bridge scope, content permanence, or what a participant must do, own, run, or
receive: every founder-directed figure is read from the accepted manifest
rather than restated. No question was asked because none was reserved.

**M3.11c ran the same gate and passed it.** It enumerated fourteen decisions the
slice had to settle — whether the execution half is imported or reimplemented;
whether the ledger subclasses version six's
or siblings it; where a seat's collection mark and recorded referrer come from
at an assignment; what happens to a measurement naming an unsold seat; how
`claimable` is derived; what the inherited carry map means under version seven;
whether the block header and transaction tree re-version; the receipt's version
field; which scenarios are recorded and which of version six's are not
re-recorded; which refusals the trace must contain for its atomicity claim to
be non-vacuous; where the vectors live; whether the accepted specification is
edited; the ctest registration; and the module layout. **Every one is fixed by
the accepted version-seven specification, ADR 0045, ADR 0046, ADR 0049, ADR
0054, or `docs/engineering/verification.md`, or is encoding, mechanism, or
layout**, which `founder-constitution.md` names as engineering work. None sets
or changes supply, allocation, beneficiaries, Founder ownership, creator
hierarchy, commercial routing, AI institutional authority, bridge scope,
content permanence, or what a participant must do, own, run, or receive: every
founder-directed figure is read from the accepted manifest rather than
restated. No question was asked because none was reserved.

**One rule the slice had to derive is consensus-visible and is recorded as
needing outside review.** That a conforming implementation must read the
collection mark from the seat entry rather than from the uptime measurement
follows from two sentences of the accepted settlement — the accumulation cap is
defined against `minted_through_window`, and the referral leg accrues to "the
seat's recorded referrer identity" — but the specification does not say it
outright. Two implementations that disagreed would write different accrued
bitmaps for the same measured cycle. ADR 0055 and the specification's evidence
section both state it, and a later transition version should put it in the
settlement steps.

**M3.11b ran the same gate and passed it.** It
enumerated sixteen decisions the slice had to settle — whether the carry is
deleted; what a zero-winner cycle contributes and what an indivisible remainder
contributes; which cycle takes the pool and how much; who receives it and how a
tie and a residual are handled; whether a cycle may consume its own dust; the
contributing and eligible sets; the permanence of ranking past 731 cycles; the
pool lifecycle; the pool's granularity; the entry number and kind 7's
retirement; the assignment record's extension; whether the pool sits inside
`outstanding`; the manifest rebinding; the label and schema bumps; and the
package, tool, and test layout. **Every one is fixed by ADR 0049, ADR 0033, ADR
0053, `first-goal.md` requirement 9, or the Founder Constitution, or is
encoding, mechanism, or layout**, which `founder-constitution.md` names as
engineering work. None sets or changes supply, allocation, beneficiaries,
Founder ownership, creator hierarchy, commercial routing, AI institutional
authority, bridge scope, content permanence, or what a participant must do, own,
run, or receive: every founder-directed figure is read from the accepted
manifest rather than restated. No question was asked because none was reserved.

**One recorded ambiguity was resolved by reading rather than by asking, and it
is recorded so the reading is auditable.** ADR 0049 says a cycle with any winner
takes the pool and that "its own dust simply returns to the pool for the cycle
after". That sentence fixes the order — absorb before contributing — and the
alternative reading is self-consistent, so ADR 0054 states the order, the
specification states it, and both record that if the owner intended the other
order the difference is one cycle of latency on dust and is a specification edit
rather than a redesign.

**M3.11a ran the same gate and passed it.** It
enumerated eleven decisions the slice had to settle — channel 9's new
identifier, the ten caps and two subtotals, the maximum supply, the base
permission legs and total, the referral amount with its destinations and
unconditionality, the denomination and seat schedule, the research placeholder
set, whether the recovery pool belongs in the manifest, the schema string and
domain label and digest and canonical length, whether version two is retired or
coexists, and the package, tool, and test layout including the loader
extraction. **Every one is fixed by the Founder Constitution, an accepted
specification, or an accepted ADR, or is encoding, mechanism, or layout**, which
`founder-constitution.md` names as engineering work. None sets or changes
supply, allocation, beneficiaries, Founder ownership, creator hierarchy,
commercial routing, AI institutional authority, bridge scope, content
permanence, or what a participant must do, own, run, or receive. No question was
asked because none was reserved.

**The question M3.11a's handoff named for M3.11b is answered and was never
reserved.** A zero-winner cycle forfeits the whole 574.3-unit permission, all
five legs. ADR 0033 settled it on 2026-08-13 and `economy-transition-v3`
implements it; the constitution had been left stating the superseded rule, which
issue #187 repaired. Deciding it required citing an accepted ADR rather than
choosing, so it was delegated work throughout.

**The 2026-08-19 pivot raised eight founder-reserved questions and the owner
answered all of them the same day.** Where AI runs; whether a Founder Machine
must serve a model to be paid; how a node-local AI judgment becomes
authoritative; whether verification runs on the founder's own machine; what
forfeits when a referrer is over the accumulation cap; how the node distribution
reaches 100% assignment; what a month is; and the unified-memory floor. ADRs
0047 through 0052 record the answers.

**Three of the owner's answers went further than filling in a blank**, which is
the fourth time the standing invitation has produced that. Separating the
deterministic verification verdict from a non-deterministic *integrity monitor*
is a better construction than the one proposed here, which was to verify on
somebody else's machine. Using the machine's own clock as a consensus input
removes a drift this handoff would otherwise have had to record forever.
And the observation that 731 cycles bound only the distribution — so ranking and
pools outlive it — made a terminal rule for stranded value unnecessary and
deleted it from the design.

**One recommendation made here was wrong and is recorded as such.** A 128 GB
unified-memory floor was recommended and the owner raised it to 512 GB. The
recommendation optimized for entry price against a requirement that exists to
buy capability, on a machine whose whole purpose is to be an AI home.

**Two things are open and neither blocks the next slice.** Whether the
assistant's one-profile-per-identity and seats-as-parallel-sessions entitlement
is protocol-enforced or application policy is now listed in the constitution's
unresolved set, and it blocks nothing until an assistant is built. And the
biometric stabilization scheme requires independent cryptographic review, which
cannot be performed in-session; nothing may rest on it until it exists.

**A business fact the owner has accepted knowingly**, recorded so it is not
rediscovered: the machine obligation is linear in seats sold and the revenue is
quadratic, so they cross at seat 54,800 and the promise is underfunded before
that, worst at about 30,000 seats at roughly −$355M. Staged distribution against
later proceeds is what makes it work.

#### What remains open in the constitution and is genuinely not this milestone's

Eligibility and anti-abuse for the liquidity-mining, impermanent-loss, and
mini-gamified channels; legacy inactivity bounds; stablecoin allowlist
governance; the AI frameworks; verifier key rotation; and whether the personal
assistant's one-profile-per-identity entitlement is protocol-enforced or
application policy. Kind 6 stays specified and refused
because of the first, which costs one transaction kind rather than a milestone.

Superseded, and kept for the record: **how a person who holds nothing pays for
their first transaction.** The mandatory-verification direction of 2026-08-15 says
registration and recovery involve no helper and no third party, and every
transaction costs a fee paid by a sender. The three candidate answers —
fee-exempt identity transactions, a fee drawn from value the identity already
holds on chain, or registration performed by the company-hosted HUB service —
each change what a participant must do and own, so none may be invented. ADR 0040
answered it for recovery and ADR 0042 for entry, and it no longer blocks
anything.

**The two questions this entry filed beside it as blocking nothing are
blockers 1 and 2 above**, and the reclassification is the correction rather than
new information. They were recorded as "answerable alongside" the entry-funding
question while it was the nearest dependency; once it closed, the next slice
became the contract, and the contract reaches both. Neither moved — the slice
moved toward them.

Requirement 10's target is no longer settled. It was `economy-transition-v5` for
one day; the direction of 2026-08-15 supersedes it, and the C++ kernel waits for
the contract that encodes the direction. **That is a change of target, not lost
work**: the envelope, the key space, the settlement, the receipt, and the tree
constructions are unaffected, and version five's model and vectors are what make
a successor's carryover check possible.

> **Settled on 2026-08-29.** The target moved twice more — to
> `economy-transition-v6` on 2026-08-15 and to `economy-transition-v7` on
> 2026-08-19 — and M3.12b implemented version seven in the kernel.
> Requirement 10 is met and the kernel waits for nothing.

**The evidence debt M3.9b took on is repaid.** `economy-transition-v5` has a
model, 550 vectors, and a verifier as of M3.9c. It is a fully evidenced contract
that was superseded as direction hours after it was evidenced — which is the
same thing that happened to versions two, three, and four, and is the reason the
repository evidences a contract before implementing it in C++ rather than after.

**One accepted contract cannot be implemented and stays in the tree.**
`economy-transition-v4`'s kind 11 has no conforming implementation; version five
corrects it and version four is retained unedited because its 441 vectors are
the record of what the hosted matrix verified on 2026-08-15. Its specification
and the documentation index both say so, so a reader cannot pick it up as the
newest contract by accident.

M3.10a ran the founder-decision gate and **did not pass it**, which is the second
time the gate has stopped a slice rather than clearing it; M3.8a was the first,
and that slice's specification had to be rebuilt because the answers changed the
transaction set rather than filling in blanks. **The answers arrived the same day
and the slice was then delivered in full**, so the stop cost a question rather
than a session.

Thirty-six decisions were enumerated before any was judged. Thirty-two are
delegated. Mandatory registration, the address as an operational tool, direct
recovery, and biometric-by-default are ADR 0039 and the constitution. The
identity as admin, escrows that hold no keys, revocable per-escrow signers, and
unlimited escrows per person are ADR 0040 and the constitution's uniform-model
paragraph. A seat with no address, the removal of kind 9 and the manager set, and
a mint naming a destination escrow the chain checks belongs to the minting
identity are ADR 0041, the last recorded there as a derivation. The entry
airdrop, its 171,000,000-atomic rate, its one-per-identity bound, the
1,000,000-identity enrollment, the 731-cycle period, and who submits a
registration are ADR 0042. The escrow identifier derivation and the two-signer
ordering rule are named as engineering by ADR 0040 in those words. The version
labels, kind identifiers, body layouts, entry kinds, result codes, storage
shapes, receipt version, genesis fields, and root constructions are mechanism,
encoding, and storage under `founder-constitution.md` lines 883-886.

Six were deductions from decided principles, which the gate treats as delegated
and expected: that registration must create the identity, its first escrow, and
its first signer in one atomic execution or the airdrop has nowhere to land; that
registration is better made fee-exempt than credit-before-fee, because the
airdrop is bounded at a million identities and the fee is not; that the accepted
version-one account derivation becomes the *signer* identifier; that the nonce
belongs to the escrow rather than the signer; that escrow deletion requires a zero
balance; and that a policy's time windows are block heights, because a transition
may not read a wall clock. All six are recorded under
[How M3.10a was delivered](delivery-log.md#how-m310a-was-delivered). **The
anchor this sentence carried pointed inside this document and had been dead since
the M3.15b split moved the record out**; it was found by M3.19a and is the reason
the anchor-validation gap is recorded under "Exact next action" rather than only
noted.

**The four reserved ones were asked in one batched call and all four were
answered the same day**, and ADR 0043 records them. Two — the reach of mandatory
verification into a transfer, and what "off entirely" means for a seat's
protection asymmetry — had been in the constitution's unresolved list since the
pivot was recorded, and enumerating is what showed they are inside the contract
rather than beside it. Assessed whole, "specify the account architecture the four
ADRs settled" reads as pure engineering, and both reserved decisions are inside
it. That is the same failure mode M3.8a's gate caught, in the same place.

**The gate's own record is the point.** It stopped a slice for the second time in
the milestone, the answers changed the contract rather than filling blanks in it,
and the specification was not started before they arrived — which is what the
gate exists to produce.

M3.9c ran the founder-decision gate and passed it. Every decision the slice had
to settle was already decided or delegated: the corrected field meaning, the
sender as the linked account, the rejection order, and the eight labels by the
accepted `economy-transition-v5` and ADR 0037; the package layout by ADR 0026
and ADR 0029; and the evidence method, the fixture, the vector names, and the
test registration as engineering under `founder-constitution.md` lines 772-775.
Nothing in it set or changed supply, allocation, beneficiaries, ownership,
creator hierarchy, commercial routing, AI authority, bridge scope, content
permanence, or what an end user must do, own, run, or receive.

**One consequence of the accepted contract is worth the owner's eye even though
it blocks nothing, and the gate flagged it rather than passing over it.**
Requiring the sender to be the address being added means a person recovering
from total address loss must first fund a fresh account themselves, and no third
party can perform the addition on their behalf. ADR 0037 records that trade and
lists it for review; it is stated here because it is the kind of thing the
standing invitation of 2026-08-13 covers — a rule about what an end user must do
to be paid — and because the moment to revisit it was before the C++ codec was
rewritten against it, not after.

**Asking it was the right call, and the answer went further than the question.**
The owner rejected all three offered flows and directed the pivot ADRs 0039
through 0042 record. The consequence flagged here no longer exists: a recovering
person regains escrows that already hold value, and a brand-new one is funded by
the entry airdrop. That is the second time the standing invitation of 2026-08-13
produced a materially better design than inference would have — the first was
M3.8a, which the invitation itself cites.

M3.9b ran the founder-decision gate and passed it. Every decision the slice had
to settle was mechanism: which of two repairs to make, whether to version or
repair in place, and the version-five labels. Nothing in it set or changed
supply, allocation, beneficiaries, ownership, creator hierarchy, commercial
routing, AI authority, bridge scope, content permanence, or what an end user must
do, own, run, or receive. The correction restores a capability the founder
direction already granted rather than granting a new one.

**Six answers arrived on 2026-08-14 and all six are now encoded.** A mint credits
the address that signed it; sixteen manager addresses per seat; a cycle a seat
cannot collect because it is full **is** a cycle it failed, so the day's
generation goes to the best performers and the full seat is not one of them;
buying a seat requires HUB verification first, with the seat tied to that
identity; a HUB identity's address set lives in consensus state, HUB-signed on
both add and remove; and the accumulation limit stays measured as time since the
last collection.

**One founder-reserved decision remains and it blocks nothing.**
`direct_issue_authority` — the eligibility and anti-abuse mechanics for the
`liquidity_mining`, `impermanent_loss_protection`,
`hub_verified_user_incentives`, and `initial_mystery_box_incentives` channels,
and the rate of the one whose eligibility ADR 0033 settled. Kind 6 is specified
and refused rather than given an invented predicate, which costs one transaction
kind rather than a milestone.

**Four claims in version four need independent review before value depends on
them**, and ADR 0036 records each with its reasoning. The sharpest is that adding
a seat address now needs one factor where version three needed two: version three
requires a key the founder already holds *and* a fresh approval, and version four
requires only the HUB signature so that a founder holding no keys is not locked
out — so a coerced or spoofed HUB signature can add an address to a seat, and
seat addresses are permanent. The others are that one identity layer is asked to
carry both uniqueness, which wants a binding that cannot move, and recovery,
which requires one that can; that **no transition rotates a HUB public key**, so
a person who loses the secret behind it loses every proof version four depends
on and the chain offers no remedy; and that the verifier's narrower reach cuts
both ways, since it can no longer help anyone either.

**One residual gap is worth naming for the identity milestone.** Every guarantee
version four adds — one person one identity, the per-human seat bound,
self-referral refusal — rests on the ecosystem verifier's attestation that a
registration is a distinct live human, and is exactly as strong as it. The chain
verifies signatures by a key it was told to trust; it establishes nothing about
the capture behind it.

The three questions the founder decisions of 2026-08-14 themselves raised are
settled and recorded in ADR 0033, and all three are now encoded in
`economy-transition-v3`:

1. **A capped cycle moves its whole permission**, escrow and System Creator legs
   included, exactly as a failed cycle does. One rule rather than two, and the
   escrows never lose value because an operator was slow to collect.
2. **Disabling biometric-on-mint requires a biometric approval**, while enabling
   it requires only the address signature. The asymmetry is the protection: a
   stolen key can neither mint against a protected seat nor remove the protection
   first.
3. **The cap applies to referral earnings too.** The forfeited value stays inside
   the `founder_referral` channel and routes to the unreferred performance pool,
   which is already that channel's second destination and already pays the
   month's best performer. This was chosen against the recommendation offered;
   the consequence is that a referrer forfeits value for inactivity that was
   never asked of them, and what it buys is one collect-or-lose rule across the
   whole economy with no account holding value indefinitely.

One founder-reserved decision is narrowed rather than closed:
**`direct_issue_authority`**. The `hub_verified_user_incentives` channel's
eligibility is now decided — being HUB verified — but its *rate* is not, and the
`liquidity_mining`, `impermanent_loss_protection`, and
`initial_mystery_box_incentives` channels are unchanged. Kind 6 stays specified
and refused.

Two further decisions are recorded rather than blocking. **The concrete resource
commitment** — what a Founder Node must prove it holds — becomes the nearest
dependency at the Founder Node and resource-network milestone. **Verifier key
rotation** is recorded from M3.8a: the ecosystem verifier key is written at
genesis and no transition changes it, so a compromised or retired key can only be
replaced by a new chain. Rotation decides who controls admission to the economy,
so it is not invented.

**The bootstrap gap is a bridge dependency, not a founder question.** A chain
with no genesis allocation and a nonzero fee cannot execute its first
transaction, and every path to a first payable balance is external.

**HUB verification is now a cross-milestone dependency and is specified
nowhere.** ADR 0033 widens M4 from a founder-seat biometric verifier to an
ecosystem identity service serving every participant class, with a direct-mint
incentive attached. The constitution's existing threat-model, unlinkability,
retention, and independent-review requirements apply to the widened scope.

M3.8c ran the founder-decision gate and passed it. Every decision the slice had
to settle was already decided or delegated: that a changed authorization is a
new version by ADR 0024, ADR 0026, and version three's own versioning section;
HUB-first purchase, the on-chain address set, and the cap's measurement by the
owner's answers of 2026-08-14; HUB signing for seat addresses and their
permanence by ADR 0035; the construction of a person's HUB signature by the
constitution's own statement that "the cryptographic construction is engineering
work"; the per-human seat bound by the constitution, which fixes 1,000 and which
version four is the first contract able to enforce; and the version labels, kind
identifiers, body layouts, entry kinds, message shapes, result codes, and the
16-address bound as mechanism, encoding, and storage under
`founder-constitution.md` lines 712-715. Two deductions were recorded rather
than invented: that removal unlinks without moving value, which is the smaller
claim, and that removing an address from an identity does not remove it from a
seat, which follows from seat addresses being permanent. `direct_issue_authority`
stayed reserved and kind 6 stayed refused. Nothing in the slice set or changed
supply, allocation, beneficiaries, ownership, creator hierarchy, commercial
routing, AI authority, bridge scope, or content permanence.

M3.8b ran the founder-decision gate and passed it. Twenty-five decisions were
enumerated before any was judged. Twenty are delegated: that a changed transition
is a new version by ADR 0024, ADR 0026, and `economy-transition-v2`'s own
versioning section; the manager rule, the optional biometric and its asymmetry,
the cap and its reallocation path, the referral cap and its destination, and the
HUB requirement by ADR 0033 and the constitution; that a manager may not be
removed by the constitution's own "remains in the historical ledger forever";
that HUB eligibility is "any participant who registers" and that its
cryptographic construction is engineering work, both stated in the constitution;
and the version number, labels, kind identifiers, body layouts, entry kinds,
beneficiary numbering, result codes, cap figure, manager bound, and storage
shapes as mechanism, encoding, and storage under `founder-constitution.md`
lines 712-715.

Three are deductions from decided principles, which the gate treats as delegated
and expected: that a mint credits its signer, that a capped seat is not a winner,
and that `mint_referral` gains no biometric option because the option is a
property of a seat and a referrer need not hold one. The first two are raised
above for confirmation because they decide who is paid.

Two remain founder-reserved and neither blocks: `direct_issue_authority`, which
keeps kind 6 refused, and **whether the chain enforces one HUB registration per
human**. The second is new, and version three deliberately does not enforce it:
doing so would decide what happens to a verified human who loses the key to
their registered account, which sets what a user must own in order to keep
participating. Not enforcing it is the smaller claim and leaves HUB exactly as
strong as the off-chain verifier, where the seat biometric hash already stands.

M3.8a ran the founder-decision gate and **it did not pass silently — it is what
found the two blocking questions above.** Eighteen decisions were enumerated
before any was judged. Fifteen are delegated: the transition version, the kind
identifiers and their bodies, the byte layouts, the signing labels, the state
keys, the state-root extension, the receipt layout, the numeric receipt codes,
the activation rule, the per-block resource limits, where the uptime record
enters consensus, and the fee treatment are mechanism, encoding, and storage
under `founder-constitution.md` lines 669-672, and `first-goal.md` requirement 5
names the first group as the deliverable while requirement 15 requires an ADR
stating the transition shape, encoding, and compatibility boundary. The
compatibility boundary is delegated by requirement 6 and by
`ledger-transition-v1`'s own rule that a later issuance rule requires a new
transition version. The denomination boundary is delegated by
`founder-economy-manifest-v2`'s versioning section, which names the new-genesis
or migration choice as engineering work with required evidence. The supply limit
is founder-directed and already fixed at 5,699,395,010,000,000,000 atomic.

The remaining three are the authorization predicates, and enumerating before
judging is what surfaced them: assessed as a whole, "specify the transaction
encoding" reads as pure engineering, and the reserved decision is inside it.
Only `direct_issue_authority` was previously on the list. Nothing in the slice
sets or changes supply, allocation, beneficiaries, ownership, creator hierarchy,
commercial routing, AI authority, bridge scope, or content permanence.

M3.7a ran the founder-decision gate and passed it. Five decisions were
enumerated — whether `ctest` runs entries concurrently and at what job count,
how that count is derived and whether a serial path is kept, the scheduling
order, which runs a shared fixture may cache, and which guards run on which
verification path — and every one is autonomous engineering work under
`founder-constitution.md` lines 669-672, which place testing and operational
choices outside the reserved set alongside mechanism, encoding, storage,
consensus scheduling, networking, and packaging. Nothing in the slice set or
changed supply, allocation, beneficiaries, ownership, creator hierarchy,
commercial routing, AI authority, bridge scope, content permanence, or what an
end user must do, own, run, or receive; it changed no vector, model, source,
specification, or ADR at all.

Two were already recorded: eligibility and anti-abuse mechanics for the
liquidity-mining, impermanent-loss, HUB-verified-user, and mystery-box
direct-mint channels, and the AI funding framework with its evaluation criteria,
milestone and tranche policy, and approval thresholds. Both are still supplied to
the models as bound research inputs, and `founder-economy-manifest-v2` keeps
`direct_channel_eligibility_result` as its single research placeholder for
exactly that reason.

**M3.5 identified a third: the concrete resource commitment.** What a Founder
Node must prove it holds — the storage, compute, and delivery capacity a
challenge is answered against — sets what an operator must own in order to be
paid, which is founder-reserved under the clause added to `CLAUDE.md` on
2026-08-09. It is not in the constitution's list of explicitly unresolved details
and is recorded here and in ADR 0028 rather than added to that document.

It becomes the nearest dependency at the Founder Node and resource-network
milestone, not at M3.6, which consumes a record and never issues a challenge.
M3.6a confirmed that by execution rather than by assumption: version three reads
a record's measurements and has no transition that issues, answers, or disputes a
challenge.
Until it is decided, `uptime-measurement-v1` proves liveness of a responder
rather than possession of a resource, and says so. Ask the owner when a challenge
must actually be constructed, and do not invent a minimum specification to make
one testable — use an abstract answer predicate, as the model already does.

The other two closed on 2026-08-07. Activity, grace, performance ranking, tie
handling, inactive-seat referral treatment, and referral-channel eligibility are
now decided in the Founder Constitution and ADR 0023, and must be implemented as
stated rather than re-litigated or re-supplied as fixtures.

Ask the owner at the point where a specific transition would otherwise have to
invent one of the three that remain, using the founder-decision gate in the
`proceed-project` skill.

M3.6c ran that gate and passed it. Eight decisions were enumerated and every one
was already decided elsewhere: that rebinding is a new suite version by
`economy-scenario-suite-v1.md`'s versioning section and ADR 0024 and ADR 0026;
the activation heights by `cycle-boundary-v1` once the shared window is held
fixed, which is arithmetic rather than a choice; the in-scope rule by
`uptime-measurement-v1`; the record's three uptime values and the 64,800-second
threshold by `economy-scenario-suite-v2.md` and ADR 0023; the empty-winner
carry-forward rule by ADR 0023; the escrow binding by ADR 0030; and the version
independence of scenarios 2 and 3 by ADR 0026. The probe seats' heights and the
peer seat are fixture engineering that changes no cap, channel, or entitlement.
Nothing in the slice sets or changes supply, allocation, beneficiaries,
ownership, creator hierarchy, commercial routing, AI authority, bridge scope,
content permanence, or what an end user must do, own, run, or receive.

M3.6b ran that gate and passed it. Every decision it settled was already decided:
that rebinding is a new version by ADR 0024 and ADR 0026, which six strings change
by version two's own table, and that a `Binding` rather than a package is correct
by ADR 0026's stated condition. The escrow caps agreeing across three contracts is
a derived fact about ADR 0023's revision, not a choice.

M3.6a ran that gate and passed it. Every decision the slice had to settle is
already decided elsewhere: the window mapping and its three rejection codes by
`cycle-boundary-v1` and ADR 0027, the in-scope rule by `uptime-measurement-v1`
and ADR 0028, the requirement that the seat record carry an activation height by
`cycle-boundary-v1`'s own closing section, and that a changed transition is a new
version by ADR 0024 and ADR 0026. Nothing in the slice sets or changes supply,
allocation, beneficiaries, ownership, creator hierarchy, commercial routing, AI
authority, bridge scope, content permanence, or what an end user must do, own,
run, or receive: an activation height is *recorded*, not earned, and what
authorizes an activation stays M4 and was not touched.

M3.5 ran that gate and passed it. It touches the Ecosystem AI without reaching
the reserved AI question: ADR 0023 and the Founder Constitution already decide
that the AI reviews and may dispute, that its signature is deliberately not a
precondition for payment, and that silence finalises a result, and the
constitution states outright that the challenge construction, sampling rate,
dispute window length, and dispute resolution are specification work rather than
founder decisions. The AI *funding* framework is the reserved one and M3.5 did
not touch it. The dispute cap was derived from the founder-directed grace
allowance rather than chosen, which is why it needed no decision.

ADR 0027 and ADR 0028 together record five claims that are design intent rather
than proof and need independent review before the pipeline carries value. From
ADR 0027: that the grid is safe against an adversary able to influence block
production rate, since a slow chain stretches every window in real time while the
nominal accounting stays fixed; and the interaction between the schedule and the
measurement pipeline. From ADR 0028: that an answered challenge reflects a real
machine, which is bounded by the undecided resource commitment; that the sampling
margin is adequate against a founder with physical machine access; and that
beacon bias is tolerable, since a proposer with influence over the state root at
`h - 1` has some influence over who is challenged at `h`. The last should be
reviewed together with ADR 0027's block-production-rate adversary, because they
are the same adversary. None blocks M3.7a, and all belong in the independent
review requirement of `first-goal.md` requirement 15. None of M3.6a, M3.6b, or
M3.6c narrows any of them: enforcing a schedule against a measurement does not
make the measurement sound, rebinding an escrow model to that schedule does not
either, and running a longer scenario against it does not either. ADR 0029, ADR
0030, and ADR 0031 record the limits rather than leaving them to be inferred.
