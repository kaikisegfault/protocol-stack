# ADR 0062: The version-seven chain fixture, and why it signs for real

- Status: Accepted
- Date: 2026-09-01

## Context

[ADR 0061](0061-the-version-seven-abci-adapter.md) completed the structural
stack: kernel, store, application, transport, node process, and ABCI adapter.
Nothing had run. Requirement 13 of [`first-goal.md`](../project/first-goal.md)
asks for adversarial four-node economic scenarios, and a single node committing
blocks under a real engine is the step before that.

The obstacle was not the adapter, and finding what it actually was is most of
this decision.

## The finding

**Every recorded version-seven transaction is signed with a stand-in.**
`simulation/economy_transition_v7/trace.py` states it outright: no signature is
computed anywhere, a stand-in is an eight-octet counter padded to 64 octets,
recorded in an oracle that verifies by exact-match lookup. `Signatures` in
`tests/kernel/economy_v7_execution_fixture.hpp` issues byte-identical tokens so
the C++ trace reproduces the model's exact transaction bytes, because a
transaction identifier is a digest over the signed bytes.

**That is the right decision for a contract fixture and it is worth keeping.**
Exact-match lookup makes every message-binding claim in the contract testable —
a signature presented over any other message is simply absent from the table —
without the model implementing cryptography it would then have to be trusted
about.

**And it means nothing recorded could ever be broadcast to a node.**
`protocol-application-v7` opens its store through `open_sqlite_ledger_v7`, whose
verifier defaults to `protocol::v7::ed25519_verifier()`. Every recorded input
would be refused as `invalid_signature`. Emitting the recorded blocks' raw
octets into a vector file — the step the handoff first recorded as next — would
have produced a fixture no chain can accept.

## Decision

### A second fixture that signs for real, beside the one that does not

`tests/integration/version_seven_chain.py` derives keys from labelled seeds
through the pinned libsodium, builds version-seven transactions, and runs the
same octets through the independent Python model to learn what each block
produces. It is version one's `tests/differential/cases.py` shape, which is the
shape that already works: build, model, broadcast, compare.

**The model needed no change.** `execute_block` takes the signature oracle as an
argument and only ever calls `verify(public_key, message, signature)`, so a
libsodium-backed object is a drop-in for the recorded table. That the seam was
already there is why this is a fixture slice rather than a model slice.

The recorded traces keep their stand-ins. Two fixtures is not duplication: they
answer different questions. The recorded one asks whether the contract binds a
message to a key; this one asks whether a node running real cryptography accepts
what the contract produces.

### One transaction per block

A state root commits to the whole block. Reproducing a recorded block that holds
four transactions requires all four to land in one block in the recorded order,
and broadcasting through a mempool does not give you that — `CreateEmptyBlocks`
is already false, and version one's integration gets one transaction per block
precisely because it submits one at a time.

So the fixture is built for the run rather than adapted to it. This is the
constraint that decided the whole shape, and it is why the existing `carried`
blocks could not have been used even with real signatures.

### Three blocks, and why each is there

Two registrations, because a transfer to an unregistered recipient is refused
and the recipient has to exist. Then a confirmed transfer, because it is the
first block that moves value and charges the fee: a node that agreed to two
airdrops and then disagreed about a fee would pass a two-block fixture.

### The integration claim is agreement between two implementations

The fixture derives the chain identity, the height-zero root, and each block's
root from the Python model. The binary derives the same two figures from that
same genesis file through `--genesis-identity`. The running node derives each
block's root by executing the octets. Every comparison in the test is one
against the other, never a value against itself.

**Three things are checked at every height because they are three claims.**
`/status` reports the app hash embedded in the latest header, which at a height
`H` is the state after `H - 1`; `/abci_info` reports the application's own
durable head, which is the root this block produced; and `block_results` must
publish the recorded block identifier as the `protocol_block` event ADR 0061
introduced, which is what proves an identifier ABCI has no field for survived
the whole path rather than being decoded and dropped.

### The restart is the third block, not a separate case

The third block is committed by a process that did not execute the first two, so
its root depends on a state read back out of SQLite rather than one held in
memory. That is the half of requirement 13's "through restart" that a single run
cannot show, and making it the fixture's last block costs nothing.

### The fixture is a live session, not a frozen list

*Amended 2026-09-01, when the four-replica run needed it.*

A consensus engine decides how many blocks a chain has. A frozen list of blocks
is enough for a single node driven one transaction at a time; it is not enough
for a network that may close a block the fixture did not ask for, because **an
empty version-seven block still moves the state root** — the root commits to the
height.

So `Session` holds the ledger live: the caller advances it to whatever height
the network reports, then executes the next transaction against it, and the
model and the chain stay at the same height for the same reason rather than by
luck. `build_chain` is three lines over it and produces the blocks it always
did.

### The harness is parameterized rather than copied

`start_stack`, `stop_stack`, and `application_info` take a protocol version, and
`inspect_identity` and `initialize_home` move out of version one's test into the
shared harness, so both versions drive the same three processes through one code
path. `application_info` previously required the application to report version
one; it now requires the version asked for, which turns a stack wired to the
wrong binary into an error rather than a confusing mismatch later.

## Evidence

`version-seven-chain-fixture` is a registered ctest entry that runs in
milliseconds and states what a node is being asked to reproduce: 110 canonical
genesis octets, three contiguous heights, one input and one 56-octet
version-seven receipt per block with a SUCCESS result byte, four distinct state
roots and three distinct block identifiers, byte-identical reproduction on a
second build, and a trailing signature that is not a stand-in.

**Six mutation probes, and the first is the argument for the slice.** Making
`Signer.sign` issue stand-ins is refused by the model itself at admission with
code 3, `invalid_signature` — the finding demonstrated rather than asserted. A
stand-in shape spliced into a raw input, two blocks sharing a root, and a
version-six receipt version are each caught by the check that names them.

**One probe passed uncaught and was re-aimed.** A key that drifts only after the
fifth derivation never reached the executed path, because a rebuild derives
exactly five keys. Drifting from the first is caught, and the re-aimed probe
reports how many times it ran so a later reader can see the mutation executed.
A sixth probe moves the genesis's network identifier and is caught by the same
check.

The integration run itself is the remaining evidence and it is hosted: it needs
the built `protocol-application-v7`, three Go binaries, the pinned CometBFT, and
the pinned libsodium.

## Owed, and recorded rather than implied

- ~~**The four-validator devnet is still version one.**~~ Delivered on
  2026-09-01. `devnet.Run` takes the version and hands it to both
  `Devnet.Ensure` and every bridge from one place, and four replicas are
  required to agree on version-seven roots through a restart with three
  transactions entering through three different nodes.
- **The uptime schedule is still `nullptr`.** This chain executes correctly and
  pays nobody. Three blocks over three heights open no cycle window, so the
  fixture is honest about what it shows; four nodes agreeing on blocks that pay
  nobody would still satisfy the word "four-node" and not the word "economic".
- **The fixture exercises three of fourteen kinds.** Registration and the
  confirmed transfer are what a chain needs to move value at all. The recorded
  vectors already execute all fourteen; this one is not a second coverage claim
  and should not grow into one without a reason.

## Alternatives considered

**Emit the recorded blocks' raw inputs into a vector file.** Rejected on the
finding above: those octets carry stand-in signatures, so the fixture would be
refused by any node running the default verifier.

**Give the recorded traces real signatures.** Rejected. The oracle is what lets
the model state message-binding claims without implementing cryptography, and
the C++ trace reproduces the model's exact bytes on purpose. Changing it would
move every recorded root in both accepted version-seven vector files to buy a
property only the integration run needs.

**Drive the fixture through the adapter's client instead of a real engine.**
Rejected: that tests the adapter, which the transport suite already does, and
would not put a mempool, a proposer, or a restart handshake anywhere near it.
