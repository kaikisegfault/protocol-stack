# ADR 0097: A seeded launch takes its genesis from one head, and the launcher writes the engine's first state

- Status: Accepted
- Date: 2026-09-29
- Implements: [ADR 0096](0096-a-devnet-may-begin-from-a-restored-snapshot.md)'s
  second slice, M4.2b
- Corrects: ADR 0096's "What CometBFT already does"
- Extends: [`consensus-application-v2`](../specifications/consensus-application-v2.md)'s
  five derived genesis values
- Relates to: `adapter/cometbft/internal/nodeconfig/launch.go`,
  `adapter/cometbft/internal/nodeconfig/launch_state.go`,
  `adapter/cometbft/internal/devnet/seed.go`, `src/application/main_v9.cpp`

## Context

M4.2a made a store that begins at a model's head. M4.2b is the network: four
such stores under an engine that begins proposing at `H + 1`. ADR 0096 fixed
the rule to keep. The initial height, the application hash, and the genesis
time come from one seeded head, never as independent options.

## Decision

### 1. The three values are read from the head, and nothing else changes

For a seeded head at height `H` with root `r` and stamp `t`, the engine's
genesis document takes:

- `initial_height = H + 1`;
- `app_hash = r`;
- `genesis_time = t`, exactly, at millisecond precision.

The chain ID, application state, validators, and consensus parameters stay the
chain's own. `nodeconfig.Launch` carries one head or none, and its zero value is
the chain's genesis. No field can be set alone, so a document naming a height,
root, and time from different heads cannot be written.

**The genesis time is the seeded stamp, not merely no earlier than it.** The
engine stamps its first block with the genesis time (ADR 0088). So block
`H + 1` carries `t(H + 1) = t(H)`, which is C2 with equality. It also means a
seeded network has the same one-minute launch window as any other, counted
from the seeded stamp: C5 refuses the first block once civil time is more than
60 seconds from `t`. A seed must therefore be made just before the launch.

**Rejected: a genesis time chosen at launch, such as the clock.** It would give
more room than a fixed stamp, but it is a fourth value that is not in the head.
A restart would then need it persisted somewhere, or passed as the independent
option ADR 0096 forbids.

### 2. The snapshot is an input to every start

The devnet's `start` takes `-seed <snapshot>`, and a seeded network needs it on
every start. The engine's genesis is derived from the seeded head, and each
restart re-derives the document and compares every home against it exactly.
After the first block the stores have moved past `H` and cannot say what it
was.

So the application gains `--inspect-seed <genesis> <snapshot>`. It runs exactly
the checks `--seed` runs, writes nothing, and prints the same four lines:
`chain_id`, `height`, `timestamp`, `app_hash`. Both modes call one storage
function, `check_seed`, so a launcher cannot be shown a head that the seed would
then refuse.

**Rejected alternatives:**

- **Persisting the head beside the homes.** The comparison would then be
  against a file the launcher wrote itself.
- **Seeding into a temporary path to learn the head.** It copies the whole
  state on every restart to read four numbers.

### 3. Stores are seeded all four or none, after the homes and before any process

On a first start, no store exists. The launcher seeds all four and requires each
to print exactly the head the genesis was derived from. On a restart, all four
exist and nothing is seeded, because the engine's handshake compares each
store's head with its own state.

Any other count is refused. A replica started without a store would create one
at height zero and never join. Seeding follows the homes, so no store is written
for a launch the homes refused. It precedes every process, so no application
creates a height-zero store where a seeded one belongs.

### 4. The launcher writes the engine's first state, because the engine does not

**This corrects ADR 0096.** Its reading of the handshake was right:

- CometBFT `v0.39.4` sends `InitChain` only at application height zero;
- with an empty block store, it takes the `storeBlockHeight == 0` branch, which
  compares app hashes and returns.

What it did not read was the next line of `NewNodeWithContext`. After the
handshake, the node **reloads its state from the state store**. Only the
`InitChain` path saves one. So a seeded node reloads an empty state,
`logNodeStartupInfo` dereferences a nil validator set, and the node panics
before it serves anything. The first network run of this slice found it.

For a seeded launch, the launcher writes into each home's state store the state
the `InitChain` path would have saved:

- the genesis document's state;
- with the empty results hash that the handshake records.

It writes only into an empty store. Every restart finds the engine's own state
and leaves it alone. A launch at the chain's genesis writes nothing, and
`InitChain` initialises it as before.

**Rejected: patching or forking the engine.** The pinned module is a reviewed
dependency, and one stored state reaches the same result from outside it.

### 5. A genesis document above height one is read, and the comparison decides

`readGenesis` refused any `initial_height` other than 1, as a stand-in for
"this is the document we wrote". It now refuses only an absent height, which the
engine would read as 1. The exact comparison against the expected document
decides everything else. So a seeded home refuses:

- a start that names no snapshot;
- a start from any other head of the same chain;
- a start from a snapshot the restore gates refuse, before any genesis is
  derived.

A genesis home refuses a seeded launch the same way.

## Evidence

- `cometbft_seeded_launch_v9_test.py`, in `tools/verify.sh`:
  - Four replicas are seeded at height 4 from a model-encoded snapshot.
  - The first block is 5, stamped with the seeded stamp to the nanosecond.
  - Two transfers commit from the seeded balance, and every root is the
    model's.
  - Three other launches are refused, with every home and store byte-identical
    afterwards.
  - The network restarts from the seed, and all four stores are audited after
    each stop.
  - A launcher whose genesis time was 1 ms late was refused by name.
- Go unit tests:
  - the derived document;
  - every refused launch, with nothing written;
  - the engine state, written once and never over a moved one;
  - the exact key set of the printed head;
  - all-or-none seeding.
- The store suite and `version-nine-seed` require inspection to agree with
  seeding in both directions.

## Consequences

- A seeded network's first block carries the seeded head's stamp. So a seed
  for M4.2c must be encoded with its head stamp within the launch window: the
  model's seed history ends at the moment of launch, not at an arbitrary past
  time.
- A seeded home holds an engine state before its engine first runs. A tool that
  treats an empty state store as the mark of a fresh home must not be pointed at
  a seeded one.
- No contract, root, rule, encoding, or accepted vector changes. A seeded
  network never calls `InitChain`, and `init_chain` still refuses any initial
  height but 1.
