# Current state

Last updated: 2026-09-01

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

**M3.13a delivered the version-seven state snapshot on 2026-08-30**, which is the
first artifact that lets a version-seven state leave memory. ADR 0056 records it.
**It also corrected the recorded next action.** M3.12b's closeout named
`calendar-v1` "the only [contract] requirement 13 depends on"; version seven
mentions a month in one descriptive sentence and executes nothing against one, so
what requirement 13 was actually waiting for was a state that can be written
down. `calendar-v1` is still owed and is not it.

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

**A chain still does not run, and exactly one structural piece is missing.**
There is **no Go ABCI adapter carrying version-seven transactions**; the existing
`adapter/cometbft` speaks version one's responses and cannot read a finalized
block that carries a block identifier. **And one debt inside the stack still
matters as much.** The uptime schedule handed to `execute_block` is `nullptr`, so
a chain driven through this process writes **no cycle assignment record and
accrues nothing to any seat**. Every root in the evidence is the recorded one
because the recorded contiguous run opens no window — the stack executes blocks
correctly and cannot yet run a chain past a cycle boundary and mean it.

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
- **A version-seven state can be written down and read back.**
  `protocol::storage::snapshot_v7` encodes a whole `Ledger` to canonical bytes
  and restores it to a ledger that keeps executing: the summary, the ordered
  account map, and the ordered economy map, with `assigned_permissions`
  re-derived from the assignment records rather than encoded. A restore hands
  back a state some sequence of blocks could have produced or it hands back
  nothing, and the conservation gate is the only one a resealed forgery does not
  defeat. The payload is what the owning store below makes durable.
- **A version-seven chain survives the process that ran it.**
  `protocol::storage::SQLiteLedgerV7` keeps the head as one snapshot payload
  inside a SQLite database, executes each block against a candidate copy, and
  writes the new head and the block's row in one exclusive transaction, so a
  reader can never see a state no block produced. A reopen runs
  `PRAGMA integrity_check` first, then the pinned `application_id` and
  `user_version` with the DDL compared verbatim, then the stored canonical
  genesis, then the snapshot's own three gates and the conservation invariants,
  and finally requires the height and root columns to agree with what the payload
  restored to. Its evidence is the `carried` scenario's four contiguous blocks
  replayed through a database **closed and reopened between each pair**, every
  block reproducing its recorded `block_id`, `resulting_state_root`, and
  `transaction_root`, with the rows read back through a bare SQLite connection.
  **It is a store rather than a node**: nothing yet carries version-seven
  transactions over consensus.
- **That store survives a fault in its own write path.** Everything before the
  commit rolls back and is an ordinary refusal that leaves the store usable; a
  commit that fails poisons the store and then makes it read the file again,
  recovering to the block's root or its predecessor's; and a recovery that itself
  fails leaves the store refusing every later call rather than guessing. Its
  evidence drives all seven fault points, fails a commit through the fault VFS,
  and **kills the process at both post-commit points from a re-executed child**,
  requiring the durable head to be the recorded one and the chain to continue.
  That is requirement 13's "through restart **and recovery**" on the storage
  side.
- **A consensus engine's block pipeline can drive that store.**
  `protocol::application::ApplicationV7` has the seven operations an ABCI adapter
  needs. `finalize_block` copies the durable head, executes the block against the
  copy, writes nothing, and stages what it produced; `commit` replays the same
  block through the store and requires the store to reproduce exactly what was
  staged, then requires the durable head to be at the root the network was told.
  `process_proposal` executes the block against a candidate and votes against one
  this node cannot execute, rather than meeting it at `finalize_block` where the
  refusal would halt the node. Its evidence is the `carried` scenario's four
  contiguous blocks driven as `process_proposal` → `finalize_block` → `commit`,
  **with the application and its store destroyed and reopened between every
  pair**, against the recorded roots and block identifiers. **Nothing yet speaks
  to CometBFT**, and **the uptime schedule is `nullptr`**, so a chain driven
  through it writes no cycle assignment and accrues nothing to any seat.
- **That pipeline answers over a Unix socket.** Version seven's responses are
  encoded over version one's frame format, reused unchanged because its header
  and all five request payloads carry no ledger-version meaning, and
  `UnixSocketServerV1::serve_connection` has an overload that hands a decoded
  request to the version-seven dispatcher. Its evidence is the recorded blocks
  driven through the whole frame pipeline as the octets an adapter would send,
  and one of them driven over a real socket, against the recorded roots and block
  identifiers.
- **A version-seven node is a process.** `protocol-application-v7` reads a
  canonical genesis file, decodes it, opens or creates its store, binds a private
  Unix socket at mode 0600, and serves until `SIGTERM`, and
  `--genesis-identity` prints the chain identity and height-zero application hash
  an operator puts into a consensus engine's configuration. It is checked as a
  process — started, connected to, restarted, shut down — against the recorded
  chain identity and a genesis root read out of a recorded block header.
  `decode_genesis` is what made it possible and is defined as `encode_genesis`'s
  inverse, checking itself by re-encoding. **There is still no Go ABCI adapter
  carrying version-seven transactions**, so nothing yet joins a network.
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
- **The C++20 kernel implements `economy-transition-v7` in full**, and it is the
  only economy contract the kernel compiles. `protocol::v7` encodes and decodes
  all fourteen transaction kinds and refuses the five retired numbers, builds all
  six HUB messages, derives escrow and signer identifiers, evaluates the posture's
  two predicates, derives every state key and value including the recovery pool
  and the extended cycle assignment record, computes the economy tree and the
  version-seven state root, encodes genesis and derives the chain identifier, and
  encodes and decodes the receipt.
  **It also runs the contract.** All fourteen transitions execute in their
  accepted rejection orders; `execute_block` writes the due cycle assignment as a
  prologue, reading the pool and each measured seat's mark and recorded referrer
  from the chain rather than from the measurement; and every accepted state
  satisfies both the channel identity and the backing identity. It reproduces
  `test-vectors/economy-transition-v7.txt` and
  `test-vectors/economy-transition-v7-execution.txt` in full, consulting every
  vector in the second, and reaches four third sources: the kind-1 identity, the
  signer derivation, and the accounts tree against the accepted M1 file; the
  ordered transaction tree, the block header, and the block identifier against
  `ledger-transition-v1.txt`; the ten channel caps and five base permission legs
  against `founder-economy-manifest-v3.txt`; and the referral leg against version
  three's. **What it still does not do is persist or gossip**: it executes blocks
  against an in-memory ledger, so no chain runs on it yet.
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

**What is missing now is everything between a block and a network.** The kernel
executes blocks against an in-memory ledger. It is not wired to the SQLite
owning store, to the archive, or to the CometBFT adapter, so no state it produces
survives a restart and no two nodes agree on one. That wiring is requirement 13's
four-node adversarial scenarios, which have not started, and it is the largest
single remaining piece of `first-goal.md`.

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

**What is missing is the Go ABCI adapter.** `adapter/cometbft` exists and speaks
version one: `internal/localapp` is the socket client and frame codec and
`internal/bridge` is the ABCI application over it, together about 1,800 lines
with their tests. **It cannot read a version-seven finalized block**, because
that response carries a block identifier version one's does not, and it sends
version one's app state at `InitChain`, which `ApplicationV7` refuses by design.

**And one gap inside the stack is larger than the adapter.** Every layer hands
`execute_block` a null uptime schedule, so a chain run end to end writes no cycle
assignment record and no seat accrues anything. Requirement 13 asks for
adversarial *economic* scenarios; four nodes agreeing on blocks that pay nobody
would satisfy the word "four-node" and not the word "economic".

**And one gap inside the layer is larger than the transport.** `ApplicationV7`
hands `execute_block` a null uptime schedule, so a chain driven through it writes
no cycle assignment record and no seat accrues anything. Requirement 13 asks for
adversarial *economic* scenarios; four nodes agreeing on empty blocks would meet
the word "four-node" and not the word "economic".

**Two contracts are also still owed, and neither blocks requirement 13.** That
was recorded the other way round at the close of M3.12b and M3.13a corrected it.
`calendar-v1` has to fix the consensus timestamp's monotonicity rule and
acceptance tolerance and the calendar-month boundary derived from it, because
the tolerance is consensus-visible and a proposer can move a month boundary
within it. **Nothing executable uses a month yet**: version seven mentions one
in a single descriptive sentence, and the unreferred pool's payout — the month,
the ranking snapshot, and the payout transition — is unestablished in version
six and version seven alike, so the calendar and that payout belong together
rather than apart. The HUB verification architecture of ADR 0048 needs its
threat model, with the biometric stabilisation scheme named as requiring
independent cryptographic review before anything rests on it.

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

Milestone slice **M3.13g: the version-seven ABCI adapter**, which is the last
structural piece between the stack that exists and a network that runs it.

**The letter moved and the reason is worth one line.** This entry was recorded as
M3.13f at the close of M3.13e. The slice actually taken next was the store's
fault and recovery work — the two debts ADR 0057 carried, and the half of
requirement 13's "through restart **and recovery**" that was unbuilt — so that
took M3.13f and the adapter is M3.13g. Nothing about the adapter's content
changed.

**`adapter/cometbft` exists and speaks version one.** `internal/localapp` is the
Unix socket client and frame codec; `internal/bridge` is the ABCI application
over it; `cmd/protocol-cometbft-node`, `-init`, `-devnet`, and `-bridge` are the
binaries. About 1,800 lines with their tests, and **the frame format is the one
version seven already uses**, so the codec's header, kinds, and request encoders
are shared rather than replaced.

**Three things actually differ and each is small.** The finalized-block response
carries a **block identifier** after the state root, which version one's decoder
does not expect; the app state at `InitChain` is `"protocol-stack-v7"`; and the
per-transaction result codes are version seven's, so an adapter that maps them to
names needs the wider table. Everything else — the header, the request payloads,
the status-and-reserved prefix, the commit and info shapes — is unchanged.

**Two things it must answer that are not encoding.** First, the **replay
handshake** ADR 0058 records: `ApplicationV7` refuses, terminally, a
`finalize_block` at any height that is not `current + 1`, *including one it has
already committed*, which is exactly what CometBFT does to an application whose
height is behind its engine's. Deciding what the adapter does about that — and
whether the application should answer a repeat rather than halt — is the slice's
one real design question, and it is mechanism rather than a founder decision.
Second, the socket pathname bound: `sun_path` caps it near 108 octets and the
binary reports only "failed to create the private Unix socket".

**Then, in order, each its own slice:**
* **the uptime schedule, which is the gap that decides whether requirement 13
  measures anything.** `ApplicationV7` hands `execute_block` a `nullptr`, so a
  chain driven through it writes no cycle assignment and no seat accrues. Four
  nodes agreeing on blocks that pay nobody would satisfy the word "four-node" and
  not the word "economic". Where an uptime measurement enters consensus is ADR
  0028's attested-claim pipeline; wiring it is mechanism, but note that **the
  concrete resource commitment behind it is founder-reserved** and becomes the
  nearest dependency at the Founder Machine milestone rather than at this one;
* requirement 13 proper, the four-node adversarial scenarios;
* `calendar-v1`, which must fix the consensus timestamp's monotonicity rule and
  acceptance tolerance and the calendar-month boundary derived from them. **The
  tolerance is consensus-visible**: a proposer can move a month boundary within
  it, so it must be a stated parameter rather than an adapter default, and the
  rule must be statable in a form any consensus adapter can satisfy, because
  CometBFT's own time is a median of validator clocks. It belongs with the
  unreferred pool's payout — the month, the ranking snapshot, and the payout
  transition — which is unestablished in version six and version seven alike;
* the HUB verification architecture of ADR 0048, which needs its threat model,
  with the biometric stabilization scheme named as requiring independent
  cryptographic review before anything rests on it.

**One consensus-visible rule M3.13a found and deliberately did not fix.**
`decode_cycle_assignment_value` does not require an assignment record's bitmap
pad bits to be clear, and `bit_is_set` bounds itself by the packed width rather
than by the recorded bit count, so a record with a pad bit set would be read as
an accrued seat by the mint's own walk. It is **unreachable on-chain** — every
record a block writes comes from `bitmap()`, which never sets one — and reachable
through a file, which is why the snapshot decoder refuses it. The accepted
specification fixes the bitmap width and does not state the pad rule, so the
kernel is conforming and tightening its decoder would be a compatibility change
rather than a fix. ADR 0056 records it; **a later transition version should state
the rule outright**, and that is a `change-protocol` slice rather than a repair.

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

**What the snapshot looks like now, so a later session does not rediscover it.**
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

**What the store's failure contract looks like now, so a later session does not
rediscover it.** All seven of version one's fault points are live in
`SQLiteLedgerV7::apply_block`. The four before the commit **throw** and roll
back, and the store is left usable; the two after it are **invoked and ignored**
so a test can terminate the process there; `before_recovery_open` fires only
during recovery. A commit failure sets `poisoned` and immediately calls
`Impl::recover_durable_head`, which clears it on success. **Do not "simplify"
that into poisoning on every write failure** — that is what it was, and it made
an ordinary rolled-back refusal permanent.

**What the node process looks like now, so a later session does not rediscover
it.** `src/application/main_v7.cpp` is the `protocol-application-v7` target and
takes `<absolute-database> <absolute-genesis> <absolute-socket>`, or
`--genesis-identity <absolute-genesis>`. The genesis file is exactly 110 octets
and nothing else; the size check in the binary is an **allocation bound**, and
the validity rule lives only in `decode_genesis`. Opening the store is attempted
before creating it. A `connection_failure` or a `protocol_failure` continues the
serve loop; only the application's own terminal latch stops a node that has
contradicted itself.

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
it.** `protocol::application::ApplicationV7` is one public header, two
translation units, and one internal header: `application_v7.cpp` owns
construction and the five operations that do not write, `application_block_v7.cpp`
owns `finalize_block` and `commit` and the per-input result rows, and
`application_v7_internal.hpp` holds the `Impl` with its staged block. It reuses
version one's `ApplicationError`, `TransactionResult`, and `PreparedProposal`
unchanged, because none of those six codes or two shapes names a ledger version.
The stage holds the candidate **root** and not the candidate ledger, on purpose.
`init_chain` is idempotent at genesis because CometBFT calls it again on a node
that crashed before its first block, and an application opened on a store already
past genesis comes back ready without it.

**What the store looks like now, so a later session does not rediscover it.**
`protocol::storage::SQLiteLedgerV7` is one public header and three translation
units with two internal headers: `sqlite_ledger_v7.cpp` owns what a live store
does, `sqlite_ledger_v7_open.cpp` owns how one comes into existence and holds
every validation step, `sqlite_schema_v7.cpp` owns the DDL and the two rows a
commit writes, `sqlite_ledger_v7_internal.hpp` is the seam between the first two,
and `sqlite_schema_v7.hpp` declares the schema surface. The schema is two tables
— `ledger_meta_v7`, a singleton, and `blocks_v7` — both `STRICT, WITHOUT ROWID`,
with the DDL stored and compared verbatim on every open. Heights are stored as
fixed-width big-endian octets **on purpose**: `ORDER BY height` over a blob column
is then numeric order, which is what lets the history be read back in block order
by a bare connection. The `head_snapshot` column's `length >= 190` is the
snapshot's own `kFixedSize`, the 126-octet prefix plus a root plus a digest, so
the column check and the decoder cannot drift apart.

**What the kernel looks like now, so a later session does not rediscover it.**
`src/v7/` holds seventeen sources and `include/protocol/v7/` two headers.
`economy_assignment.cpp` is the newest and is the only one with no version-six
ancestor: it derives a cycle and applies it, and `execute_block` calls it as a
prologue. `Assignment` and `SeatCycle` live in `ledger.hpp`; `SeatCycle` carries
**three** fields on purpose, because the mark and the recorded referrer are
chain state and a four-field version would make ADR 0055's first derived rule
optional.

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
mutation probes affordable in M3.12b and twenty-six in M3.13a**; without it each
probe is a hosted run.

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
Both are now written to compensate whatever else the mutation disturbs, so only
the rule under test can refuse them. **A probe that passes has proved nothing
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

**One fixture rule the kernel tests now depend on.** Three builders in
`economy_v7_trace.cpp` are version six's, imported rather than restated — the
confirmed transfer, the verified-user mint, and the posture change — and they
carry `kInheritedValidUntil` (10,000,000) rather than `kValidUntil`
(10,000,000,000). The bytes a transaction commits to include the height it
expires at, so unifying the two constants produces identical state roots and
different transaction roots. Do not tidy them into one.

**One sequencing rule an earlier slice learned the hard way.** Let the merge's
own `main` push run finish before pushing the closeout documentation commit.
M3.11c pushed the closeout while the merge run was still building and the
workflow's concurrency group cancelled it, which leaves a cancelled run and a
failed aggregate check on `main`'s history for a commit whose tree had already
passed the matrix in full on the pull request.

**Two generation details.** Both version-seven vector files are produced by their
verifier's `--emit`, which runs the same derivations through the same agreement
gate as the checking mode, so a file and its derivations cannot disagree at
birth; the section comments are emitted with them, so regenerating is one
command rather than a transcription. And **the coverage claim is a vector of its
own**: `coverage.every_kind_version_seven_admits_is_executed` fails if a later
scenario change stops reaching one, and the C++ execution checks now derive the
same count rather than reading it back.


## Blockers

**None for M3.13g.**

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
[What the M3.10a gate's enumeration found](#what-the-m310a-gates-enumeration-found).

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
