# ADR 0090: The version-nine devnet follows the engine's stamps and audits the durable one

- Status: Accepted
- Date: 2026-09-24
- Bounds: [ADR 0079](0079-the-version-nine-application-contract.md)
- Follows: [ADR 0089](0089-a-version-nine-chain-resumes-only-inside-the-tolerance.md)
- Settles: [ADR 0087](0087-the-bridge-carries-the-engines-time.md)'s owed choice of
  where the health check reads the durable stamp
- Corrects: [`consensus-application-v2`](../specifications/consensus-application-v2.md)'s
  required evidence, for the kind-22 mint
- Relates to: `tests/integration/cometbft_four_validator_v9_test.py`,
  `tests/integration/cometbft_devnet.py`, `tests/integration/cometbft_process.py`,
  `tests/integration/version_nine_chain.py`, `tools/verify.sh`

## Context

`consensus-application-v2` lists the four-validator evidence a version-nine
network owes. The devnet commits a signed transfer and a kind-22 monthly pool
mint, and exposes the same height, **timestamp**, and root on all four replicas.
It then stops, restarts, audits every stopped ledger through an independent C++
process, and continues. A second test skews one replica's clock. The contract's
topology section also adds the durable timestamp to the values the health
observation compares.

Version eight's four-validator run already proves the rest of that list for
version eight. M3.20h ran version nine under one node and found that the first
block after any whole-network outage carries a stamp from before it (ADR 0089).

## Decision

### 1. The run is version eight's scenario, with the model following the engine's stamps

The same transactions enter through the same nodes, and the same refusals, restarts,
driven replica, and departure follow. Version eight advanced its model through
unrequested heights with empty blocks. Version nine does the same, but an empty
block's root depends on its stamp, so each height is applied with the stamp its
committed header carries. The header is read from a replica that never departs.
Each height's transaction count is checked too, so the model cannot treat a
block that held a transaction as empty. Block 1 must carry the genesis stamp
exactly.

**Rejected: a fresh scenario.** Keeping version eight's makes any difference
between the two runs a difference between the versions.

### 2. The durable stamp is compared by the audit, and the live check compares the root

ABCI's Info carries no stamp, so the Go health command cannot read one without a
second RPC per replica and a second conversion of the header time. The durable
stamp is where the durable head is, so it is compared there. At every stop,
`audit_durable_heads` opens each replica's own store with an independent C++
process and reads its height, stamp, and root over version two's Info. All three
must equal the model's. Between stops, the health observation compares roots,
which commit to the stamp. The model's root is derived from the committed header
time, so root agreement is stamp agreement.

**This is where `consensus-application-v2`'s topology delta is met.** It asks for
the durable timestamp among the values all nodes must report identically, and
the audit is the observation that reads it. ADR 0087 left the placement to this
slice.

**Rejected: adding a `timestamp` line to the Go health output.** It could only
report the header time converted again, which is the engine's value rather than
the application's durable one. And every replica that agrees on a block agrees on
its header by construction, so the comparison would be close to vacuous.

### 3. Every whole-network restart is checked against the window

Each restart checks, once the network reports ready, that the model's head stamp
is at least 15 seconds inside the tolerance. The model's head is at or before the
network's, so passing the check means the next block can still be accepted.
Readiness is bounded at 90 seconds, longer than the tolerance, so a readiness
failure that happens past the window is reported as a missed window rather than
as a timeout. A single departing replica is not checked. The chain stays live
without it, and it catches up through block sync, which never calls
`ProcessProposal`.

### 4. The driven replica is handed a stamp that runs backwards

Version eight's driven replica is interrupted mid-block and handed a block two
heights ahead. Version nine's is also handed a decided block at the right height
whose stamp is one millisecond before its head's. C2 refuses it as status `8`,
`DECIDED_BLOCK_FAILED_MONOTONICITY`, the application latches terminal, and a
fresh process must find the store where the network left it. It is the one
refusal only version nine can be handed.

### 5. The kind-22 mint's evidence stays below the engine

A kind-22 mint needs a seat to have been in scope during a calendar month that
has since closed. Two walls stand in the way on a devnet:

- **Height.** A seat is in scope only from the window after the one it activated
  in, and a window is `CYCLE_BLOCKS` = 28,800 heights (ADR 0071).
- **Clock.** After block 1, the engine stamps each block with the median of its
  validators' vote times, and C5 keeps that median within a minute of every
  application's clock. The node binary is statically linked, so no `LD_PRELOAD`
  shim reaches it (M3.20g).

Kind 22 already executes in the C++ kernel. `economy-transition-v9-execution-cpp`
reproduces all 125 recorded execution vectors, over chains of 115,200 and 144,000
heights, including the payout and the mint. **That is where its evidence lives.**
The contract's list carries a correction note saying so, as ADR 0071 gave version
eight's.

**Rejected: a devnet-only shortcut to reach a month's end**, such as a shorter
window or a clock-moving build of the engine. Either would put a second chain
configuration beside the real one, and the evidence it produced would be about
that configuration. That is the same reason ADR 0071 gave.

### 6. The skewed replica is its own slice

It needs a way to offset one application's clock. ADR 0085 owes that choice:
an operator option that offsets the reading, or an `LD_PRELOAD` shim. Either is
more than a test change, so it is not folded into a port.

## Consequences

- Version nine's four-validator evidence is met except for the kind-22 mint,
  which stays below the engine, and the skewed replica, which is the next slice.
- `audit_durable_heads` requires a durable stamp for a version-nine network and
  refuses one for any other, so an audit cannot silently skip the stamp.
- **No accepted vector file, specification rule, manifest, encoding, kernel
  source, or Go source changes.** One accepted document gains a correction note.
