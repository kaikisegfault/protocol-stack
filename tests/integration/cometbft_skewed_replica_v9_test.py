#!/usr/bin/env python3

"""One version-nine replica on a wrong clock, and three that carry on without it.

This is the last item of `consensus-application-v2`'s devnet evidence: *a devnet
test moves one replica's clock beyond the tolerance and proves the remaining
three continue while the skewed replica votes against proposals the others
accept.*

**The clock is moved below the process, where a real machine's clock is
wrong.** The skewed replica runs the binary that ships, with
`libprotocol-clock-offset.so` preloaded (ADR 0091), and the run rewrites the
offset while the network runs. So one network passes through all three states a
machine's clock can be in:

- **120 seconds ahead.** Every stamp the engine proposes is more than a minute
  behind this machine's clock, so it answers decision `5`,
  `TIMESTAMP_BEHIND_TOLERANCE`.
- **120 seconds behind.** Every stamp is more than a minute ahead of it, so it
  answers decision `4`, `TIMESTAMP_AHEAD_OF_TOLERANCE`.
- **Corrected.** It rejects nothing, with no restart and no repair, because it
  never stopped agreeing.

Throughout, the other three validators hold thirty of forty voting power. That
is more than two thirds, so every height commits without the skewed vote. The
skewed replica applies each decided block through `FinalizeBlock`, which applies
no tolerance, so it holds the model's root at every height. Its own proposals
are committed too, because a block's stamp is the engine's median of vote times
and not the proposer's clock. Transactions enter through it as through any node,
because `CheckTx` reads no clock.

**Which heights a clock governed is read from the skewed replica itself.** Its
`ProcessProposal` for height `h` runs while its committed height is `h - 1`. So
every vote at or below the height it reports just before the offset is rewritten
was cast on the old clock. Every vote two or more past the height it reports just
afterwards was cast on the new one. The height or two in between are not
asserted.

The evidence is the bridge's `rejected proposal` line, which names the decision
(ADR 0087). A correct replica must never write one.
"""

from __future__ import annotations

import dataclasses
import pathlib
import re
import sys
import tempfile
import time

REPOSITORY = pathlib.Path(__file__).resolve().parents[2]
for _entry in (
    REPOSITORY,
    REPOSITORY / "tests" / "application",
    REPOSITORY / "tests" / "differential",
):
    if str(_entry) not in sys.path:
        sys.path.insert(0, str(_entry))

import clock_offset  # noqa: E402
import cometbft_four_validator_v9_test as four  # noqa: E402

from cometbft_devnet import (  # noqa: E402
    Network,
    reserve_port_block,
    run_health,
    stop_network,
)
from cometbft_rpc import block_proposer, status, validator_address  # noqa: E402
from pinned_sodium import Sodium  # noqa: E402
from simulation.economy_transition_v9 import contract as c  # noqa: E402

SKEWED_NODE = 3
CORRECT_NODES = (0, 1, 2)
# Twice the tolerance, so the engine's stamps, which trail real time by a commit
# timeout or two, are well outside it in either direction.
SKEW_MILLIS = 2 * c.TIMESTAMP_TOLERANCE_MILLIS
# Heights each clock must govern beyond doubt. Four is one full rotation of four
# equal-power proposers, so each skewed clock governs a height a correct node
# proposed and, together, heights the skewed replica proposed.
PHASE_HEIGHTS = 4
# A skewed clock must have voted against at least this many of its heights.
# Fewer than all of them, because a replica that has not received a proposal
# when its propose step times out votes nil without asking the application.
MINIMUM_REJECTIONS = 2
# The devnet commits roughly every three seconds, so this is many heights.
HEIGHT_WAIT_SECONDS = 60

_REJECTION = re.compile(r"\bheight=(\d+)\b.*\bdecision=([A-Z0-9_]+)")


@dataclasses.dataclass(frozen=True)
class Phase:
    name: str
    offset: int
    # The decision the skewed replica must name, or None for none at all.
    decision: str | None


PHASES = (
    Phase("120 s ahead", SKEW_MILLIS, "TIMESTAMP_BEHIND_TOLERANCE"),
    Phase("120 s behind", -SKEW_MILLIS, "TIMESTAMP_AHEAD_OF_TOLERANCE"),
    Phase("corrected", 0, None),
)
SKEW_DECISIONS = {phase.decision for phase in PHASES} - {None}


@dataclasses.dataclass
class Governed:
    """The heights one clock decided every vote for, `first` to `last`."""

    phase: Phase
    first: int
    last: int = 0


def skewed_height(network: Network) -> int:
    return status(network.rpc_port(SKEWED_NODE))[0]


def await_skewed_height(network: Network, height: int) -> None:
    deadline = time.monotonic() + HEIGHT_WAIT_SECONDS
    while skewed_height(network) < height:
        if time.monotonic() > deadline:
            raise RuntimeError(
                f"node {SKEWED_NODE} did not reach height {height} within "
                f"{HEIGHT_WAIT_SECONDS} s; the network stopped committing"
            )
        time.sleep(0.5)


def rejections(network: Network, index: int) -> list[tuple[int, str]]:
    """Every `rejected proposal` one replica's bridge has logged, in order."""
    log = network.root / f"node{index}" / "logs" / "bridge.log"
    found = []
    for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
        if "rejected proposal" not in line:
            continue
        match = _REJECTION.search(line)
        if match is None:
            raise RuntimeError(f"node {index} logged an unreadable rejection: {line!r}")
        found.append((int(match.group(1)), match.group(2)))
    return found


def run_phases(
    network: Network,
    workspace: pathlib.Path,
    chain: four.Chain,
    offset_file: pathlib.Path,
    transactions: tuple[tuple[tuple[int, bytes], ...], ...],
) -> list[Governed]:
    """Move the skewed clock through every phase, submitting as it goes.

    The first phase's offset was written before the network started, so it
    governs from block 1. Each later one is bracketed by two reads of the skewed
    replica's height, and each ends with all four replicas agreeing with the
    model.
    """
    governed = [Governed(PHASES[0], 1)]
    for position, phase in enumerate(PHASES):
        if position > 0:
            governed[-1].last = skewed_height(network)
            clock_offset.set_offset(offset_file, phase.offset)
            governed.append(Governed(phase, skewed_height(network) + 2))
        for node_index, raw in transactions[position]:
            four.submit(network, workspace, chain, node_index, raw)
        await_skewed_height(network, governed[-1].first + PHASE_HEIGHTS - 1)
        four.check_health(chain, run_health(network))
    governed[-1].last = skewed_height(network)
    return governed


def check_votes(network: Network, governed: list[Governed]) -> int:
    """Hold every replica's votes to its clock, and return a skewed proposal.

    Returns a height the skewed replica proposed while its clock was wrong, and
    which the network committed.
    """
    for index in CORRECT_NODES:
        found = rejections(network, index)
        if found:
            raise RuntimeError(
                f"node {index}, whose clock is correct, voted against "
                f"{len(found)} proposals, first at height {found[0][0]} as "
                f"{found[0][1]}"
            )
    skewed = rejections(network, SKEWED_NODE)
    for height, decision in skewed:
        if decision not in SKEW_DECISIONS:
            raise RuntimeError(
                f"node {SKEWED_NODE} voted against height {height} as {decision}, "
                "which no clock explains"
            )
    reader = network.rpc_port(four.READER)
    skewed_address = validator_address(network.rpc_port(SKEWED_NODE))
    skewed_proposals = []
    for period in governed:
        if period.last - period.first + 1 < PHASE_HEIGHTS:
            raise RuntimeError(
                f"the clock {period.phase.name} governed only heights "
                f"{period.first} to {period.last}"
            )
        inside = [(h, d) for h, d in skewed if period.first <= h <= period.last]
        wrong = [(h, d) for h, d in inside if d != period.phase.decision]
        if wrong:
            raise RuntimeError(
                f"with its clock {period.phase.name}, node {SKEWED_NODE} voted "
                f"against height {wrong[0][0]} as {wrong[0][1]}"
            )
        if period.phase.decision is None:
            continue
        rejected = sorted({height for height, _ in inside})
        proposed_by_a_peer = [
            height
            for height in rejected
            if block_proposer(reader, height) != skewed_address
        ]
        if len(rejected) < MINIMUM_REJECTIONS or not proposed_by_a_peer:
            raise RuntimeError(
                f"with its clock {period.phase.name}, node {SKEWED_NODE} voted "
                f"against only heights {rejected} of {period.first} to "
                f"{period.last}, and none a peer proposed"
            )
        skewed_proposals += [
            height
            for height in range(period.first, period.last + 1)
            if block_proposer(reader, height) == skewed_address
        ]
    if not skewed_proposals:
        raise RuntimeError(
            f"no block node {SKEWED_NODE} proposed was committed while its "
            "clock was wrong"
        )
    return skewed_proposals[0]


def verify(
    application: pathlib.Path,
    bridge: pathlib.Path,
    node: pathlib.Path,
    devnet: pathlib.Path,
    sodium_library: pathlib.Path,
    shim: pathlib.Path,
    parent: pathlib.Path,
) -> None:
    sodium = Sodium(str(sodium_library))
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="cometbft-skewed-replica-v9-", dir=parent
    ) as temporary, tempfile.TemporaryDirectory(
        prefix="protocol-stack-skew-v9-sockets-"
    ) as socket_temporary:
        workspace = pathlib.Path(temporary)
        offset_file = workspace / "skew"
        # Written before the network starts: a missing offset is an unreadable
        # clock, and the skewed application would refuse to start.
        clock_offset.set_offset(offset_file, PHASES[0].offset)
        chain = four.Chain(sodium, four.now_millis())
        session = chain.session
        transactions = (
            ((SKEWED_NODE, session.register_alice()), (0, session.register_bob())),
            ((SKEWED_NODE, session.alice_pays_bob(1)),),
            ((1, session.alice_pays_bob(2)),),
        )

        genesis = workspace / "protocol.genesis"
        genesis.write_bytes(session.genesis)
        network = Network(
            devnet,
            application,
            bridge,
            node,
            workspace / "network",
            pathlib.Path(socket_temporary) / "network",
            genesis,
            reserve_port_block(),
            four.PROTOCOL_VERSION,
            tuple(
                (SKEWED_NODE, name, value)
                for name, value in clock_offset.environment(shim, offset_file).items()
            ),
        )
        chain.rpc_port = network.rpc_port(four.READER)

        process = four.start(network, workspace, chain, "the launch")
        try:
            governed = run_phases(network, workspace, chain, offset_file, transactions)
            proposed = check_votes(network, governed)
            stop_network(process, network)
        finally:
            process.kill()
        four.audit(network, workspace, chain)

    spans = ", ".join(
        f"{period.phase.name} over heights {period.first}-{period.last}"
        for period in governed
    )
    entries = [index for phase in transactions for index, _ in phase]
    print(
        "CometBFT skewed-replica version-nine integration: passed "
        f"(node {SKEWED_NODE}'s clock {spans}; it named "
        "TIMESTAMP_BEHIND_TOLERANCE while ahead and TIMESTAMP_AHEAD_OF_TOLERANCE "
        "while behind and nothing once corrected, the other 3 never voted "
        f"against a proposal, its own block at height {proposed} was committed, "
        f"{entries.count(SKEWED_NODE)} transactions entered through it and "
        f"{len(entries) - entries.count(SKEWED_NODE)} elsewhere, and all 4 held "
        "the model's height, stamp and root)"
    )


def main() -> int:
    if len(sys.argv) != 8:
        raise RuntimeError(
            "usage: cometbft_skewed_replica_v9_test "
            "<application-v9> <bridge> <node> <devnet> "
            "<libsodium> <clock-offset-shim> <temporary-parent>"
        )
    paths = [pathlib.Path(value).resolve() for value in sys.argv[1:]]
    for required in paths[:6]:
        if not required.is_file():
            raise RuntimeError(f"missing integration input {required}")
    verify(*paths)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(
            "CometBFT skewed-replica version-nine integration: "
            f"failed: {error}",
            file=sys.stderr,
        )
        raise SystemExit(1)
