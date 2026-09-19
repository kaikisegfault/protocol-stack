# Current state

Last updated: 2026-09-17

## Phase

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

### The per-slice delivery records moved out of this document

Every `How ... was delivered` record is now in
[`delivery-log.md`](delivery-log.md), moved there verbatim on 2026-09-14 because
this document had reached 8,140 lines and every session is instructed to read it
first. **Nothing was reworded, reordered, or dropped.** Read that document when
you need the history behind a claim here; read this one for what is true now.

## What works now

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
  **No engine drives it yet** — the response encoder, the node process and the
  ABCI adapter are still owed — so this is a driveable application rather than a
  running node.
- **The local application protocol has a version-two frame.** As of 2026-09-19
  `wire_v2` decodes a request at protocol version `2`, with the genesis timestamp
  in kind 2 and the block timestamp in kinds 5 and 6. **Nothing serves it yet** —
  the response encoder is the next slice — so this is a codec rather than a
  running transport. What it already establishes is the
  cross-version refusal in both directions: each decoder refuses the other's
  frame at the header, on the first frame, rather than several fields into a
  payload.
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

### The version-eight stack records moved out of this document

They are in [`delivery-log.md`](delivery-log.md), in its second section,
verbatim.

## Adopted founder direction

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

## Repository state

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

## Remaining gap

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

## Exact next action

**Write `response_v9` and `dispatcher_v9`.** `ApplicationV9` produces
`ApplicationInfoV9`, `FinalizedBlockV9`, `CommittedHeadV9` and a
`ProposalDecision`; `wire_v2` can carry a request to it; nothing turns its
answers into version-two frames.

**What the response encoder owes that version eight's did not.** Kind 1 and kind
7 responses gain a timestamp, kind 5's response becomes a `decision:u8` rather
than an `accept:Boolean`, kind 6's carries the block identifier the message table
now records, and the status space gains `7` and `8` — reachable **only** from
kind 6, because kind 5 reports the same two conditions as decisions `2` and `3`
under a zero status. `consensus-application-v2`'s decoder and fuzz requirements
for the six changed payloads are this slice's; the rest of its
required-evidence section belongs to the node process and the adapter.

**Its contract is written and its acceptance criteria are already enumerated.**
[`consensus-application-v2`](../specifications/consensus-application-v2.md)'s
required-evidence section is the list; do not re-derive it. The parts that belong
to this slice rather than to the node or the adapter are the eight-value decision
space and the eight statuses, `calendar-v1`'s first-condition-wins ordering, both
sides of C5 with a supplied clock, the test that `FinalizeBlock` accepts a stamp
`ProcessProposal` would have refused for tolerance, the proof that no path from
`FinalizeBlock`, Commit, restart, or reconstruction reaches the bound clock
source, the timestamp-conversion cases, the InitChain cases, and the decoder and
fuzz cases for the six changed payloads.

**Two things the store slice settled that the application must not re-open.**
The store applies C1 and C2 and **never C5** — it executes blocks the network
already decided, and a store that re-applied the proposal tolerance would refuse
the chain's own past one tolerance-width after producing it. And `apply_block`
takes the agreed stamp as a parameter, so the application supplies it and the
store never reads a clock; `SQLiteLedgerV9::apply_block` has no clock to read,
which is the enforcement rather than the convention.

**The frame version is the one trap already identified and not yet sprung.**
M3.19a found that version seven added a block identifier to the finalize response,
version eight kept it, the frame version stayed at `1`, and no contract document
recorded it. Version nine changes six payloads, so this is the slice where the
frame version has to move and where version one's decoder must refuse a
version-two frame at the **frame** rather than at the first block as a generic
protocol failure.

**The contract the remaining ports must satisfy is now written.**
[`consensus-application-v2`](../specifications/consensus-application-v2.md) and
[ADR 0079](../decisions/0079-the-version-nine-application-contract.md) were
accepted on 2026-09-17, so the application layer, the transport, the node process
and the ABCI adapter each have a stated shape and a stated evidence list rather
than one to invent. Its required-evidence section is the acceptance criteria for
those four slices; do not re-derive them.

**One verification gap is recorded and open.** `tools/verify_metadata.py`
validates that a Markdown link's file exists and **does not validate its anchor
fragment**, so a broken `#section` link passes every gate in the repository.
M3.19a swept all **41** anchored links in tracked Markdown with a throwaway
script: one was genuinely dead — a link in this document pointing at a heading the
M3.15b split had moved to `delivery-log.md` — and it is fixed. The rest resolve.

**Whoever closes the gap should know the one thing that makes it subtle.** The
first sweep reported a second failure in `economy-transition-v6.md` and **the
document was right and the checker was wrong**: GitHub's slugger replaces *each*
space with a hyphen, so `### Kind 10 — \`hub_register\`` becomes
`kind-10--hub_register` with two hyphens, because removing the em-dash leaves two
spaces. A checker that collapses whitespace runs reports false positives against
every heading containing a dash, which is most of them here. Closing the gap is a
Python source change that fails closed to the full matrix, so it is a candidate
slice rather than a fold-in.

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
  `ApplicationV9`, both on 2026-09-19. **The nearest slice is `response_v9` and
  `dispatcher_v9`**, then the node process and the ABCI adapter — still version
  eight's, and holding an accepted contract that states what each must satisfy. The paragraphs that stood here enumerating what the binding version had
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

## Blockers

**There is no blocker.** Every remaining version-nine slice is a port with an
accepted contract behind it.

**One piece of accepted required evidence cannot be produced, and it is recorded
rather than waived.** `consensus-application-v2` asks for a vector for every
`ProcessProposal` decision `0` through `7`. **Decision `7`, `NOT_EXECUTABLE`, is
not reachable from a proposal's contents**: the kernel turns every
transaction-level problem into a result, and the whole-block rejections that
remain are chain-state failures no peer can induce by choosing bytes. M3.20b
established this with a probe rather than a reading and records the absence as a
measurement. It is not a blocker — the decision stays implemented because the
failures it guards are real — but a later session should not spend the slice
hunting for the vector.

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

### What remains open in the constitution and is genuinely not this milestone's

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
