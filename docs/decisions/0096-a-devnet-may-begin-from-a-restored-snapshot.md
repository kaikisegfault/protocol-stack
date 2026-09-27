# ADR 0096: A devnet may begin from a restored snapshot

- Status: Accepted
- Date: 2026-09-27
- Takes up: [ADR 0071](0071-a-devnet-cannot-reach-the-uptime-audit.md)'s two named
  routes, and chooses one
- Serves: requirement 2 of [`first-goal.md`](../project/first-goal.md), a mint on
  a network

## Context

A version-nine network begun at genesis cannot reach a mint in a test's
lifetime:

- a kind-18 mint first has anything to collect at height 57,600, about two days
  at the commit target;
- a kind-4 mint, for a seat activated in window 0, first has anything at height
  86,400, about three days.

ADR 0071 named two ways past that wall and built neither:

- **A chain begun at a nonzero initial height.** Three layers refuse any initial
  height but 1, and they do so on purpose. The state root commits to the height,
  so a genesis at height 28,780 is a different state from the same genesis
  octets at height zero. Admitting one is a contract change needing
  `change-protocol`.
- **A devnet stood up on a restored snapshot.** The snapshot can express a
  ledger at any height, and the restore gates check it, but nothing could start
  a node from one.

## What CometBFT already does

**The second route needs no contract change, and the engine already supports
it.** CometBFT v0.39.4's handshake is in `consensus/replay.go`, lines 317 to 377
of `Handshaker.ReplayBlocks`:

- it sends `InitChain` only when the application reports height 0;
- when its own block store is empty and the application reports a nonzero
  height, it takes the `storeBlockHeight == 0` branch, asserts that the
  application's app hash equals the one its state carries from the genesis
  document, and proceeds.

So a network whose genesis document says `initial_height = H + 1` and
`app_hash = root(H)`, over applications that report height H with that root,
proposes block H + 1 and never asks anyone to initialise a chain.

**The version-nine application already behaves that way over a seeded store.**
`ApplicationV9` is ready when its opened store's height is nonzero
(`application_v9.cpp`, `ready = initial.ledger.height != 0`). Opening a store
reads only its head, never its block rows, so a store whose head is at H with no
blocks below it opens through the ordinary restore path.

## Decision

**A devnet may begin from a restored snapshot, and the chain's genesis stays at
height zero.** Two heights are kept apart:

- the **chain's genesis**, which the contract fixes at height zero and which
  names the chain;
- the **network's launch height**, which is where a particular engine begins
  proposing.

Nothing in the contract changes: every root, every rule, and the refusal of any
initial height other than 1 in `init_chain` stay exactly as they are. A seeded
network never calls `init_chain`.

**A seed is a state that real blocks produced, and the restore gates are what
say so.** The seed history is executed as ordinary blocks by the version-nine
model: registrations, a purchase, an activation, the challenge responses that
credit the seat, and the quiet heights between them. The model's ledger at H is
then encoded as a version-nine snapshot payload. A C++ node accepts it only
through `decode_snapshot_v9`, whose three gates are:

- the rebuilt ledger's root;
- the payload's own root;
- the kernel's invariant set.

A payload encoded wrongly by Python, or describing a state no block sequence
reaches, is refused before a store exists. That also makes every seeding a
cross-language check of the snapshot encoding: the C++ decoder must reproduce,
from Python's octets, the root Python's model computed.

**Seeding is an operator act with its own entry point, never a startup option.**
It is refused unless all of these hold:

- the path does not exist;
- the payload passes every gate under the parameters the genesis fixes;
- the payload's height is at least 1, since a height-zero seed is just a
  genesis;
- the payload re-encodes to exactly its own octets.

A seeded store then opens and runs exactly like any other.

**The slices, in order.**

1. **M4.2a:**
   - `seed_sqlite_ledger_v9` in the owning store;
   - `protocol-application-v9 --seed <database> <genesis> <snapshot>`, which
     prints the height, stamp, and root a launcher needs;
   - a Python encoder for the payload;
   - tests that seed from the model's recorded chain and refuse every bad seed.
2. **M4.2b:** the CometBFT adapter accepts a seeded launch. The genesis
   document takes `initial_height = H + 1`, the seeded root as `app_hash`, and
   a genesis time no earlier than the seeded head's stamp. It is accepted only
   when all three come from one seeded head, never as independent options.
3. **M4.2c:** a four-validator run seeded past the assignment lag, in which a
   kind-18 and a kind-4 mint execute and every replica agrees.

## Alternatives rejected

- **The nonzero initial height**, for ADR 0071's reason: it changes what a
  genesis is, and the snapshot route needs no such change.
- **Seeding by replaying the history into each node over its socket.** It needs
  no new entry point, but every one of some 90,000 blocks would be a durable
  SQLite commit on four nodes, which costs minutes a hosted job cannot spare.
  The seed would also be the network's own execution rather than evidence
  handed to it.
- **A C++ tool that executes the seed history itself.** The seat must answer
  challenges to be credited, and a challenge depends on the previous block's
  root. So that tool would need to sign responses live, with signing keys, in a
  consensus binary. The model already has a responder and a real signer.
- **Shortening `CYCLE_BLOCKS` for tests**, which ADR 0071 refused outright: a
  fixture that agreed with itself about a chain nobody operates.

## Consequences

- A node can be started at any height a model can reach, and the restore gates
  still decide whether the state is one a chain could hold. The gates are
  therefore now on the path of every seeded network, and ADR 0093's two rules
  run on every seed.
- A seeded store has no block rows below its head. Nothing reads them to open
  a store, but a tool that later audits block history must say it starts at the
  seed.
- A seeded network's first block carries the engine's genesis time, which must
  be no earlier than the seeded head's stamp (C2) and within the tolerance of
  every node's clock (C5). M4.2b records how the launcher meets both.
