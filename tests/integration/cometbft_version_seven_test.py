#!/usr/bin/env python3

"""A version-seven chain through a real CometBFT process.

Everything below this has been exercised against recorded vectors, in C++ and in
Python, and none of it has ever met a consensus engine. This is the first time a
version-seven transaction is signed for real, broadcast to a CometBFT node,
gossiped through a mempool, proposed, finalized, and committed, with the engine
required to report the state root the independent Python model says that block
produces.

**The claim is agreement between two implementations, not self-consistency.**
`version_seven_chain` derives the chain identity, the height-zero root, and each
block's root from the Python model; the binary derives the same two figures from
the same genesis file through `--genesis-identity`, and the running node derives
each block's root by executing the octets. Every comparison here is one against
the other.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile
from dataclasses import dataclass

REPOSITORY = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY / "tests" / "differential"))

from cometbft_process import (  # noqa: E402
    ManagedProcess,
    initialize_home,
    inspect_identity,
    reserve_ports,
    start_stack,
    stop_stack,
)
from cometbft_rpc import abci_info, broadcast, rpc_call, status  # noqa: E402
from pinned_sodium import Sodium  # noqa: E402
from version_seven_chain import Chain, build_chain  # noqa: E402

PROTOCOL_VERSION = 7


@dataclass(frozen=True)
class Stack:
    application: pathlib.Path
    bridge: pathlib.Path
    node: pathlib.Path
    workspace: pathlib.Path
    database: pathlib.Path
    genesis: pathlib.Path
    application_socket: pathlib.Path
    home: pathlib.Path
    abci_port: int
    rpc_port: int


def launch(stack: Stack) -> list[ManagedProcess]:
    return start_stack(
        stack.application,
        stack.bridge,
        stack.node,
        stack.workspace,
        stack.database,
        stack.genesis,
        stack.application_socket,
        stack.home,
        stack.abci_port,
        stack.rpc_port,
        protocol_version=PROTOCOL_VERSION,
    )


def block_identity(rpc_port: int, height: int) -> bytes:
    """The block identifier the adapter published as a block event.

    ABCI has no field for a second block identifier, so the version-seven bridge
    emits version seven's as an indexed `protocol_block` event. Reading it back
    over RPC is what proves the identifier survived the whole path rather than
    being decoded and dropped.
    """
    results = rpc_call(rpc_port, "block_results", {"height": str(height)})
    events = results.get("finalize_block_events") or []
    found: list[bytes] = []
    for event in events:
        if event.get("type") != "protocol_block":
            continue
        for attribute in event.get("attributes") or []:
            if attribute.get("key") == "id":
                found.append(bytes.fromhex(attribute["value"]))
    if len(found) != 1:
        raise RuntimeError(
            f"height {height} published {len(found)} block identifiers")
    return found[0]


def commit_block(
    stack: Stack,
    chain: Chain,
    index: int,
) -> None:
    """Broadcast one block's transaction and require every reported figure.

    CometBFT's `/status` reports the app hash embedded in the latest header,
    which at height `H` is the state after `H - 1`; `/abci_info` reports the
    application's own durable head. Both are checked, because they are different
    claims and only the second is the root this block produced.
    """
    block = chain.blocks[index]
    previous = (
        chain.genesis_root if index == 0 else chain.blocks[index - 1].state_root
    )
    broadcast(
        stack.rpc_port,
        block.raw_inputs[0],
        block.height,
        block.receipts[0],
    )
    reported = status(stack.rpc_port)
    if reported != (block.height, previous):
        raise RuntimeError(
            f"height {block.height} header hash mismatch: "
            f"height={reported[0]} hash={reported[1].hex().upper()}"
        )
    head = abci_info(stack.rpc_port)
    if head != (block.height, block.state_root):
        raise RuntimeError(
            f"height {block.height} application head mismatch: "
            f"height={head[0]} root={head[1].hex().upper()}"
        )
    published = block_identity(stack.rpc_port, block.height)
    if published != block.block_id:
        raise RuntimeError(
            f"height {block.height} published block identifier "
            f"{published.hex().upper()} for {block.block_id.hex().upper()}"
        )


def commit_first_two(stack: Stack, chain: Chain) -> None:
    processes = launch(stack)
    try:
        commit_block(stack, chain, 0)
        commit_block(stack, chain, 1)
        durable = stop_stack(
            processes, stack.application_socket, PROTOCOL_VERSION)
        if durable != (chain.blocks[1].height, chain.blocks[1].state_root):
            raise RuntimeError(
                f"durable head after two blocks: height={durable[0]} "
                f"root={durable[1].hex().upper()}"
            )
    finally:
        for process in reversed(processes):
            process.kill()


def commit_after_restart(stack: Stack, chain: Chain) -> None:
    """The third block is committed by a process that did not execute the first two.

    Its root therefore depends on a state read back out of SQLite rather than one
    held in memory, which is the half of requirement 13's "through restart" that
    a single run cannot show.
    """
    processes = launch(stack)
    try:
        restarted = abci_info(stack.rpc_port)
        if restarted != (chain.blocks[1].height, chain.blocks[1].state_root):
            raise RuntimeError(
                f"restart handshake head: height={restarted[0]} "
                f"root={restarted[1].hex().upper()}"
            )
        commit_block(stack, chain, 2)
        durable = stop_stack(
            processes, stack.application_socket, PROTOCOL_VERSION)
        if durable != (chain.blocks[2].height, chain.blocks[2].state_root):
            raise RuntimeError(
                f"durable head after three blocks: height={durable[0]} "
                f"root={durable[1].hex().upper()}"
            )
    finally:
        for process in reversed(processes):
            process.kill()


def require_pinned_node(node: pathlib.Path) -> None:
    version = subprocess.run(
        [node, "version"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if version.stdout != b"0.39.4\n":
        raise RuntimeError("node does not report pinned CometBFT v0.39.4")


def verify(
    application: pathlib.Path,
    bridge: pathlib.Path,
    initializer: pathlib.Path,
    node: pathlib.Path,
    sodium_library: pathlib.Path,
    parent: pathlib.Path,
) -> None:
    require_pinned_node(node)
    chain = build_chain(Sodium(str(sodium_library)))

    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="cometbft-v7-", dir=parent
    ) as temporary, tempfile.TemporaryDirectory(
        prefix="ps-cb7-socket-"
    ) as socket_temporary:
        workspace = pathlib.Path(temporary)
        genesis = workspace / "protocol.genesis"
        database = workspace / "ledger.db"
        application_socket = pathlib.Path(socket_temporary) / "app.sock"
        home = workspace / "cometbft"
        genesis.write_bytes(chain.genesis)

        chain_id, initial_root = inspect_identity(application, genesis)
        if chain_id != chain.chain_id or initial_root != chain.genesis_root:
            raise RuntimeError("C++ and independent genesis identities differ")

        abci_port, rpc_port, p2p_port = reserve_ports(3)
        stack = Stack(
            application,
            bridge,
            node,
            workspace,
            database,
            genesis,
            application_socket,
            home,
            abci_port,
            rpc_port,
        )

        def initialize() -> None:
            initialize_home(
                initializer,
                home,
                chain_id,
                initial_root,
                abci_port,
                rpc_port,
                p2p_port,
                protocol_version=PROTOCOL_VERSION,
            )

        # Twice, because the second call must exact-validate the home the first
        # wrote rather than rewrite it: a version-seven genesis that a repeated
        # initialization silently replaced would be a chain nobody else joins.
        initialize()
        initialize()
        commit_first_two(stack, chain)

        initialize()
        commit_after_restart(stack, chain)

    print(
        "CometBFT version-seven integration: passed "
        "(2 registrations, 1 confirmed transfer, restart at height 2, "
        "durable height 3)"
    )


def main() -> int:
    if len(sys.argv) != 7:
        raise RuntimeError(
            "usage: cometbft_version_seven_test "
            "<application-v7> <bridge> <initializer> <node> "
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
            f"CometBFT version-seven integration: failed: {error}",
            file=sys.stderr,
        )
        raise SystemExit(1)
