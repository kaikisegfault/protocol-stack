#!/usr/bin/env python3

"""Four version-nine replicas launched above height zero from one snapshot.

This is ADR 0097, the second of ADR 0096's three slices toward a mint on a
network. Every earlier network in this repository began at height one; this one
begins at `H + 1`, where `H` is the height of a state no replica executed.

**The seed history is executed by the model alone.** Alice and Bob register,
and Alice buys and activates seat 0: four blocks, one millisecond apart, stamped
from a genesis minted as the run starts. The model's ledger at height 4 is
encoded as a snapshot, and `protocol-cometbft-devnet start -seed` seeds all four
stores from it, through each application's restore gates, before any process
starts. The earlier head at height 3 is kept as a second snapshot.

**What the network must then show:**

- It launches, and its first block is at height 5. The engine stamps that block
  with its genesis time, and that time must be the seeded head's stamp to the
  nanosecond: the first block carries C2 with equality.
- Every block's root is the model's, continuing from the model's height-4 root,
  including a transfer Alice pays from the balance the seed left her.
- After a stop, all four stores hold the model's height, stamp, and root.

**A seeded home refuses every other launch**, and the refusal touches nothing.
Each is the supervisor exiting at once, before any application starts, with the
genesis file and all four stores byte-identical afterwards:

- a start that names no snapshot, which would be the chain's own genesis;
- a start from the height-3 snapshot, a different head of the same chain;
- a start from the snapshot with one octet changed, which the restore gates
  refuse before any genesis is derived.

**Then it restarts from the right snapshot**, which seeds nothing because every
store exists, and commits a second transfer. The launch and restart windows
are the four-validator run's (ADR 0088, ADR 0089): a seeded launch has the same
one-minute window as any other, counted from the seeded stamp.
"""

from __future__ import annotations

import hashlib
import pathlib
import subprocess
import sys
import tempfile
from dataclasses import replace

REPOSITORY = pathlib.Path(__file__).resolve().parents[2]
for _entry in (
    REPOSITORY,
    REPOSITORY / "tests" / "application",
    REPOSITORY / "tests" / "differential",
):
    if str(_entry) not in sys.path:
        sys.path.insert(0, str(_entry))

import cometbft_four_validator_v9_test as four  # noqa: E402

from cometbft_devnet import (  # noqa: E402
    NODE_COUNT,
    Network,
    reserve_port_block,
    start_arguments,
    stop_network,
)
from cometbft_rpc import committed_block  # noqa: E402
from pinned_sodium import Sodium  # noqa: E402
from version_nine_chain import engine_millis  # noqa: E402

REFUSAL_TIMEOUT_SECONDS = 60


def seed_history(chain: four.Chain) -> tuple[bytes, bytes]:
    """Execute the seed blocks in the model; return the height-3 and height-4 heads."""
    session = chain.session
    transactions = (
        session.register_alice(),
        session.register_bob(),
        session.alice_buys_seat(1),
        session.alice_activates_seat(2),
    )
    earlier = b""
    for offset, raw in enumerate(transactions, start=1):
        chain.execute_before_launch(raw, session.genesis_timestamp + offset)
        if offset == len(transactions) - 1:
            earlier = session.snapshot()
    return earlier, session.snapshot()


def require_first_block_carries_the_seed(chain: four.Chain, seeded: int) -> None:
    """The engine's first block is `H + 1`, stamped with the seeded head's stamp."""
    (seconds, nanos), count = committed_block(chain.rpc_port, seeded + 1)
    stamp = engine_millis(seconds, nanos)
    if count != 0 or nanos % 1_000_000 != 0 or stamp != chain.stamps[seeded]:
        raise RuntimeError(
            f"block {seeded + 1} is stamped {seconds}s {nanos}ns with {count} "
            f"transactions, not the seeded stamp {chain.stamps[seeded]} ms")


def on_disk(network: Network) -> dict[str, str]:
    """A digest of every home's genesis and every replica's store."""
    paths = [network.root / f"node{index}" / "ledger.db"
             for index in range(NODE_COUNT)]
    paths += [network.root / f"node{index}" / "cometbft" / "config" /
              "genesis.json" for index in range(NODE_COUNT)]
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths}


def require_refused_start(
    network: Network, workspace: pathlib.Path, message: str, what: str,
) -> None:
    before = on_disk(network)
    result = subprocess.run(
        [str(argument) for argument in start_arguments(network)],
        cwd=workspace, capture_output=True, text=True,
        timeout=REFUSAL_TIMEOUT_SECONDS, check=False,
    )
    if result.returncode == 0:
        raise RuntimeError(f"{what}: the network started")
    if message not in result.stderr:
        raise RuntimeError(
            f"{what}: refused for another reason: {result.stderr.strip()}")
    if on_disk(network) != before:
        raise RuntimeError(f"{what}: a refused start changed a home or a store")


def run(network: Network, workspace: pathlib.Path, chain: four.Chain,
        what: str, node: int, raw: bytes) -> None:
    process = four.start(network, workspace, chain, what)
    try:
        four.submit(network, workspace, chain, node, raw)
        stop_network(process, network)
    finally:
        process.kill()
    four.audit(network, workspace, chain)


def verify(
    application: pathlib.Path,
    bridge: pathlib.Path,
    node: pathlib.Path,
    devnet: pathlib.Path,
    sodium_library: pathlib.Path,
    parent: pathlib.Path,
) -> None:
    sodium = Sodium(str(sodium_library))
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="cometbft-seeded-launch-v9-", dir=parent
    ) as temporary, tempfile.TemporaryDirectory(
        prefix="protocol-stack-seeded-v9-sockets-"
    ) as socket_temporary:
        workspace = pathlib.Path(temporary)
        # Minted as late as the run allows, as for every launch: the seeded
        # stamp is four milliseconds later, and the first block carries it.
        chain = four.Chain(sodium, four.now_millis())
        earlier, payload = seed_history(chain)
        seeded = chain.session.height
        first_transfer = chain.session.alice_pays_bob(3)
        second_transfer = chain.session.alice_pays_bob(4)

        genesis = workspace / "protocol.genesis"
        genesis.write_bytes(chain.session.genesis)
        snapshot = workspace / "seed.snapshot"
        snapshot.write_bytes(payload)
        (workspace / "earlier.snapshot").write_bytes(earlier)
        tampered = bytearray(payload)
        tampered[len(tampered) // 2] ^= 0x01
        (workspace / "tampered.snapshot").write_bytes(bytes(tampered))

        network = Network(
            devnet, application, bridge, node,
            workspace / "network",
            pathlib.Path(socket_temporary) / "network",
            genesis, reserve_port_block(), four.PROTOCOL_VERSION,
            seed=snapshot,
        )
        chain.rpc_port = network.rpc_port(four.READER)

        process = four.start(network, workspace, chain, "the seeded launch")
        try:
            require_first_block_carries_the_seed(chain, seeded)
            four.submit(network, workspace, chain, 1, first_transfer)
            stop_network(process, network)
        finally:
            process.kill()
        four.audit(network, workspace, chain)

        require_refused_start(
            replace(network, seed=None), workspace,
            "genesis differs", "a start naming no snapshot")
        require_refused_start(
            replace(network, seed=workspace / "earlier.snapshot"), workspace,
            "genesis differs", "a start from the height-3 head")
        require_refused_start(
            replace(network, seed=workspace / "tampered.snapshot"), workspace,
            "not a state this chain can be seeded with",
            "a start from an altered snapshot")

        run(network, workspace, chain, "the seeded restart", 2, second_transfer)

    print(
        "CometBFT seeded-launch version-nine integration: passed (4 "
        f"independent replicas seeded at height {seeded} from a model-encoded "
        f"snapshot, first block {seeded + 1} stamped with the seeded head's "
        f"stamp, 2 transfers from the seeded balance, every root the model's "
        f"through height {chain.session.height}; 3 other launches refused "
        "with every home and store unchanged; 1 restart from the seed, durable "
        "height, stamp and root audited in all 4 stores per stop)"
    )


def main() -> int:
    if len(sys.argv) != 7:
        raise RuntimeError(
            "usage: cometbft_seeded_launch_v9_test "
            "<application-v9> <bridge> <node> <devnet> "
            "<libsodium> <temporary-parent>"
        )
    paths = [pathlib.Path(value).resolve() for value in sys.argv[1:]]
    for executable in paths[:5]:
        if not executable.is_file():
            raise RuntimeError(f"missing integration input {executable}")
    verify(*paths)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(
            f"CometBFT seeded-launch version-nine integration: failed: {error}",
            file=sys.stderr,
        )
        raise SystemExit(1)
