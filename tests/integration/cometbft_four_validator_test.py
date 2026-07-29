#!/usr/bin/env python3

from __future__ import annotations

import pathlib
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass

REPOSITORY = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY / "tests" / "differential"))

from cases import make_fixture, transfer  # noqa: E402
from cometbft_process import (  # noqa: E402
    ManagedProcess,
    application_info,
    start_process,
)
from cometbft_rpc import abci_info, status  # noqa: E402
from model import ReferenceLedger  # noqa: E402
from pinned_sodium import Sodium  # noqa: E402

NODE_COUNT = 4
PORT_OFFSETS = tuple(
    offset
    for index in range(NODE_COUNT)
    for offset in (index * 10, index * 10 + 1, index * 10 + 2)
)


@dataclass(frozen=True)
class Network:
    devnet: pathlib.Path
    application: pathlib.Path
    bridge: pathlib.Path
    node: pathlib.Path
    root: pathlib.Path
    genesis: pathlib.Path
    base_port: int

    def common_arguments(self) -> list[str]:
        return [
            "-root",
            str(self.root),
            "-base-p2p-port",
            str(self.base_port),
        ]

    def application_socket(self, index: int) -> pathlib.Path:
        return self.root / f"node{index}" / "application.sock"

    def rpc_port(self, index: int) -> int:
        return self.base_port + index * 10 + 1


def reserve_port_block() -> int:
    for _ in range(100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as candidate:
            candidate.bind(("127.0.0.1", 0))
            base = candidate.getsockname()[1]
        if base > 65535 - max(PORT_OFFSETS):
            continue
        reservations: list[socket.socket] = []
        try:
            for offset in PORT_OFFSETS:
                reservation = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                reservation.bind(("127.0.0.1", base + offset))
                reservations.append(reservation)
            return base
        except OSError:
            pass
        finally:
            for reservation in reservations:
                reservation.close()
    raise RuntimeError("unable to reserve four-validator port block")


def start_network(network: Network, workspace: pathlib.Path) -> ManagedProcess:
    process = start_process(
        "four-validator-devnet",
        [
            network.devnet,
            "start",
            *network.common_arguments(),
            "-genesis",
            network.genesis,
            "-application",
            network.application,
            "-bridge",
            network.bridge,
            "-node",
            network.node,
        ],
        workspace,
    )
    try:
        run_health(network)
        return process
    except Exception:
        process.kill()
        raise process.failure()


def run_health(network: Network) -> dict[str, str]:
    result = subprocess.run(
        [
            network.devnet,
            "health",
            *network.common_arguments(),
            "-timeout",
            "45s",
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=50,
    )
    values: dict[str, str] = {}
    for line in result.stdout.decode("ascii").splitlines():
        key, value = line.split("=", 1)
        values[key] = value
    expected_keys = {
        "validators",
        "chain_id",
        "height",
        "app_hash",
        "header_height",
        "header_app_hash",
    }
    if set(values) != expected_keys or values["validators"] != "4":
        raise RuntimeError("unexpected devnet health output")
    return values


def run_transaction(
    network: Network,
    workspace: pathlib.Path,
    node_index: int,
    transaction: bytes,
    expected_height: int,
    expected_receipt: bytes,
    expected_root: bytes,
) -> None:
    transaction_path = workspace / f"transaction-{expected_height}.bin"
    transaction_path.write_bytes(transaction)
    result = subprocess.run(
        [
            network.devnet,
            "transaction",
            *network.common_arguments(),
            "-node-index",
            str(node_index),
            "-tx-file",
            transaction_path,
            "-timeout",
            "45s",
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=50,
    )
    values: dict[str, str] = {}
    for line in result.stdout.decode("ascii").splitlines():
        key, value = line.split("=", 1)
        values[key] = value
    if (
        set(values)
        != {
            "height",
            "check_code",
            "finalize_code",
            "receipt",
            "app_hash",
        }
        or int(values["height"]) != expected_height
        or values["check_code"] != "0"
        or values["finalize_code"] != "0"
        or bytes.fromhex(values["receipt"]) != expected_receipt
        or bytes.fromhex(values["app_hash"]) != expected_root
    ):
        raise RuntimeError("devnet transaction command returned wrong result")


def require_heads(
    network: Network,
    expected_height: int,
    expected_header_root: bytes,
    expected_application_root: bytes,
) -> None:
    health = run_health(network)
    if (
        int(health["height"]) != expected_height
        or bytes.fromhex(health["app_hash"]) != expected_application_root
        or int(health["header_height"]) != expected_height
        or bytes.fromhex(health["header_app_hash"]) != expected_header_root
    ):
        raise RuntimeError("health command returned unexpected network head")
    for index in range(NODE_COUNT):
        rpc_port = network.rpc_port(index)
        if status(rpc_port) != (expected_height, expected_header_root):
            raise RuntimeError(f"node {index} block-header head mismatch")
        if abci_info(rpc_port) != (
            expected_height,
            expected_application_root,
        ):
            raise RuntimeError(f"node {index} ABCI head mismatch")
        if application_info(network.application_socket(index)) != (
            expected_height,
            expected_application_root,
        ):
            raise RuntimeError(f"node {index} durable C++ head mismatch")


def stop_network(process: ManagedProcess, network: Network) -> None:
    process.stop()
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if all(
            not network.application_socket(index).exists()
            for index in range(NODE_COUNT)
        ):
            return
        time.sleep(0.02)
    raise RuntimeError("devnet retained an application socket after shutdown")


def verify(
    application: pathlib.Path,
    bridge: pathlib.Path,
    node: pathlib.Path,
    devnet: pathlib.Path,
    sodium_library: pathlib.Path,
    parent: pathlib.Path,
) -> None:
    sodium = Sodium(str(sodium_library))
    fixture = make_fixture(sodium)
    reference = ReferenceLedger(fixture.genesis, sodium)
    transaction_one = transfer(sodium, fixture, 0, 1, 1, 10_000)
    commit_one = reference.apply_block(1, [transaction_one])
    transaction_two = transfer(sodium, fixture, 0, 2, 2, 20_000)
    commit_two = reference.apply_block(2, [transaction_two])

    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="cometbft-four-validator-", dir=parent
    ) as temporary:
        workspace = pathlib.Path(temporary)
        root = workspace / "network"
        genesis = workspace / "protocol.genesis"
        genesis.write_bytes(fixture.genesis)
        network = Network(
            devnet,
            application,
            bridge,
            node,
            root,
            genesis,
            reserve_port_block(),
        )

        first = start_network(network, workspace)
        try:
            initial_health = run_health(network)
            if (
                int(initial_health["height"]) != 0
                or bytes.fromhex(initial_health["app_hash"])
                != commit_one.previous_state_root
            ):
                raise RuntimeError("initial four-validator head mismatch")
            run_transaction(
                network,
                workspace,
                0,
                transaction_one,
                1,
                commit_one.encoded_receipts[0],
                commit_one.resulting_state_root,
            )
            require_heads(
                network,
                1,
                commit_one.previous_state_root,
                commit_one.resulting_state_root,
            )
            stop_network(first, network)
        finally:
            first.kill()

        second = start_network(network, workspace)
        try:
            require_heads(
                network,
                1,
                commit_one.previous_state_root,
                commit_one.resulting_state_root,
            )
            run_transaction(
                network,
                workspace,
                1,
                transaction_two,
                2,
                commit_two.encoded_receipts[0],
                commit_two.resulting_state_root,
            )
            require_heads(
                network,
                2,
                commit_one.resulting_state_root,
                commit_two.resulting_state_root,
            )
            stop_network(second, network)
        finally:
            second.kill()

    print(
        "CometBFT four-validator integration: passed "
        "(4 independent replicas, 2 signed transfers, full restart at height 1)"
    )


def main() -> int:
    if len(sys.argv) != 7:
        raise RuntimeError(
            "usage: cometbft_four_validator_test "
            "<application> <bridge> <node> <devnet> "
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
            f"CometBFT four-validator integration: failed: {error}",
            file=sys.stderr,
        )
        raise SystemExit(1)
