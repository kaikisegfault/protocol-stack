#!/usr/bin/env python3

from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile
from dataclasses import dataclass

REPOSITORY = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY / "tests" / "differential"))

from cases import make_fixture, transfer  # noqa: E402
from cometbft_process import (  # noqa: E402
    ManagedProcess,
    initialize_home,
    inspect_identity,
    reserve_ports,
    start_stack,
    stop_stack,
)
from cometbft_rpc import abci_info, broadcast, status  # noqa: E402
from model import ReferenceLedger  # noqa: E402
from pinned_sodium import Sodium  # noqa: E402


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
    )


def commit_first_height(
    stack: Stack,
    transaction: bytes,
    receipt: bytes,
    initial_root: bytes,
    resulting_root: bytes,
) -> None:
    processes = launch(stack)
    try:
        broadcast(stack.rpc_port, transaction, 1, receipt)
        first_status = status(stack.rpc_port)
        if first_status != (1, initial_root):
            raise RuntimeError(
                "first CometBFT block-header hash mismatch: "
                f"height={first_status[0]} "
                f"hash={first_status[1].hex().upper()}"
            )
        if abci_info(stack.rpc_port) != (1, resulting_root):
            raise RuntimeError("first CometBFT application head mismatch")
        if stop_stack(processes, stack.application_socket) != (
            1,
            resulting_root,
        ):
            raise RuntimeError("first durable C++ head mismatch")
    finally:
        for process in reversed(processes):
            process.kill()


def commit_after_restart(
    stack: Stack,
    transaction: bytes,
    receipt: bytes,
    initial_root: bytes,
    previous_root: bytes,
    resulting_root: bytes,
) -> None:
    processes = launch(stack)
    try:
        restart_status = status(stack.rpc_port)
        if restart_status != (1, initial_root):
            raise RuntimeError(
                "restart block-header hash mismatch: "
                f"height={restart_status[0]} "
                f"hash={restart_status[1].hex().upper()}"
            )
        if abci_info(stack.rpc_port) != (1, previous_root):
            raise RuntimeError("restart handshake application head mismatch")
        broadcast(stack.rpc_port, transaction, 2, receipt)
        continued_status = status(stack.rpc_port)
        if continued_status != (2, previous_root):
            raise RuntimeError(
                "continued CometBFT block-header hash mismatch: "
                f"height={continued_status[0]} "
                f"hash={continued_status[1].hex().upper()}"
            )
        if abci_info(stack.rpc_port) != (2, resulting_root):
            raise RuntimeError("continued CometBFT application head mismatch")
        if stop_stack(processes, stack.application_socket) != (
            2,
            resulting_root,
        ):
            raise RuntimeError("continued durable C++ head mismatch")
    finally:
        for process in reversed(processes):
            process.kill()


def verify(
    application: pathlib.Path,
    bridge: pathlib.Path,
    initializer: pathlib.Path,
    node: pathlib.Path,
    sodium_library: pathlib.Path,
    parent: pathlib.Path,
) -> None:
    version = subprocess.run(
        [node, "version"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if version.stdout != b"0.39.4\n":
        raise RuntimeError("node does not report pinned CometBFT v0.39.4")

    sodium = Sodium(str(sodium_library))
    fixture = make_fixture(sodium)
    reference = ReferenceLedger(fixture.genesis, sodium)
    transaction_one = transfer(sodium, fixture, 0, 1, 1, 10_000)
    commit_one = reference.apply_block(1, [transaction_one])
    transaction_two = transfer(sodium, fixture, 0, 2, 2, 20_000)
    commit_two = reference.apply_block(2, [transaction_two])

    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="cometbft-single-node-", dir=parent
    ) as temporary, tempfile.TemporaryDirectory(
        prefix="ps-cb-socket-"
    ) as socket_temporary:
        workspace = pathlib.Path(temporary)
        genesis = workspace / "protocol.genesis"
        database = workspace / "ledger.db"
        application_socket = pathlib.Path(socket_temporary) / "app.sock"
        home = workspace / "cometbft"
        genesis.write_bytes(fixture.genesis)

        chain_id, initial_root = inspect_identity(application, genesis)
        if (
            chain_id != fixture.chain_id
            or initial_root != commit_one.previous_state_root
        ):
            raise RuntimeError("C++ and independent genesis identities differ")

        abci_port, rpc_port, p2p_port = reserve_ports(3)
        initialize_home(
            initializer,
            home,
            chain_id,
            initial_root,
            abci_port,
            rpc_port,
            p2p_port,
        )
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
        commit_first_height(
            stack,
            transaction_one,
            commit_one.encoded_receipts[0],
            initial_root,
            commit_one.resulting_state_root,
        )

        initialize_home(
            initializer,
            home,
            chain_id,
            initial_root,
            abci_port,
            rpc_port,
            p2p_port,
        )
        commit_after_restart(
            stack,
            transaction_two,
            commit_two.encoded_receipts[0],
            initial_root,
            commit_one.resulting_state_root,
            commit_two.resulting_state_root,
        )

    print(
        "CometBFT single-node integration: passed "
        "(2 signed transfers, restart at height 1, durable height 2)"
    )


def main() -> int:
    if len(sys.argv) != 7:
        raise RuntimeError(
            "usage: cometbft_single_node_test "
            "<application> <bridge> <initializer> <node> "
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
        print(f"CometBFT single-node integration: failed: {error}", file=sys.stderr)
        raise SystemExit(1)
