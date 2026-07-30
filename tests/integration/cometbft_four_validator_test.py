#!/usr/bin/env python3

from __future__ import annotations

import pathlib
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
    await_unix_socket,
    reserve_non_ephemeral_port_block,
    start_process,
)
from model import BlockCommit, ReferenceLedger, state_root  # noqa: E402
from pinned_sodium import Sodium  # noqa: E402

NODE_COUNT = 4
COMMAND_TIMEOUT_SECONDS = 100
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
    socket_root: pathlib.Path
    genesis: pathlib.Path
    base_port: int

    def common_arguments(self) -> list[str]:
        return [
            "-root",
            str(self.root),
            "-socket-root",
            str(self.socket_root),
            "-base-p2p-port",
            str(self.base_port),
        ]

    def application_socket(self, index: int) -> pathlib.Path:
        return self.socket_root / f"node{index}.sock"

    def rpc_port(self, index: int) -> int:
        return self.base_port + index * 10 + 1


@dataclass(frozen=True)
class SubmittedTransaction:
    height: int
    receipt: bytes
    application_root: bytes


def reserve_port_block() -> int:
    return reserve_non_ephemeral_port_block(PORT_OFFSETS)


def start_network(
    network: Network,
    workspace: pathlib.Path,
) -> tuple[ManagedProcess, dict[str, str]]:
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
        return process, run_health(network)
    except Exception as error:
        shutdown_error = ""
        try:
            process.stop()
        except Exception as stop_error:
            shutdown_error = f"\nsupervisor shutdown error:\n{stop_error}"
        finally:
            process.kill()
        output = process.log_path.read_text(encoding="utf-8", errors="replace")
        child_outputs = []
        for path in sorted(network.root.glob("node*/logs/*.log")):
            child_outputs.append(
                f"{path.relative_to(network.root)}:\n"
                f"{path.read_text(encoding='utf-8', errors='replace')}"
            )
        children = "\n".join(child_outputs)
        raise RuntimeError(
            f"devnet readiness failed: {error}\n"
            f"supervisor output:\n{output}\n"
            f"child outputs:\n{children}"
            f"{shutdown_error}"
        ) from error


def run_health(network: Network) -> dict[str, str]:
    try:
        result = subprocess.run(
            [
                network.devnet,
                "health",
                *network.common_arguments(),
                "-timeout",
                "90s",
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.CalledProcessError as error:
        raise RuntimeError(
            error.stderr.decode("utf-8", errors="replace").strip()
        ) from error
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
) -> SubmittedTransaction:
    transaction_path = workspace / f"transaction-{node_index}.bin"
    transaction_path.write_bytes(transaction)
    try:
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
                "90s",
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.CalledProcessError as error:
        raise RuntimeError(
            "devnet transaction failed:\n"
            f"stdout:\n{error.stdout.decode('utf-8', errors='replace')}\n"
            f"stderr:\n{error.stderr.decode('utf-8', errors='replace')}"
        ) from error
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
        or values["check_code"] != "0"
        or values["finalize_code"] != "0"
    ):
        raise RuntimeError("devnet transaction command returned wrong result")
    height = int(values["height"])
    receipt = bytes.fromhex(values["receipt"])
    application_root = bytes.fromhex(values["app_hash"])
    if height < 1 or len(application_root) != 32:
        raise RuntimeError("devnet transaction returned an invalid head")
    return SubmittedTransaction(height, receipt, application_root)


def advance_empty_blocks(
    reference: ReferenceLedger,
    target_height: int,
    latest: BlockCommit | None,
) -> BlockCommit | None:
    if target_height < reference.state.height:
        raise RuntimeError("observed devnet height moved backwards")
    while reference.state.height < target_height:
        latest = reference.apply_block(reference.state.height + 1, [])
    return latest


def synchronize_reference(
    reference: ReferenceLedger,
    health: dict[str, str],
    latest: BlockCommit | None,
) -> BlockCommit | None:
    height = int(health["height"])
    latest = advance_empty_blocks(reference, height, latest)
    header_root = b"" if latest is None else latest.previous_state_root
    if (
        int(health["header_height"]) != height
        or bytes.fromhex(health["header_app_hash"]) != header_root
        or bytes.fromhex(health["app_hash"]) != state_root(reference.state)
    ):
        raise RuntimeError("health command differs from reference state")
    return latest


def apply_submitted_transaction(
    reference: ReferenceLedger,
    transaction: bytes,
    result: SubmittedTransaction,
    latest: BlockCommit | None,
) -> BlockCommit:
    if result.height <= reference.state.height:
        raise RuntimeError("transaction did not advance the devnet height")
    advance_empty_blocks(reference, result.height - 1, latest)
    commit = reference.apply_block(result.height, [transaction])
    if (
        result.receipt != commit.encoded_receipts[0]
        or result.application_root != commit.resulting_state_root
    ):
        raise RuntimeError("transaction result differs from reference model")
    return commit


def audit_durable_heads(
    network: Network,
    workspace: pathlib.Path,
    expected_height: int,
    expected_application_root: bytes,
) -> None:
    network.socket_root.mkdir(mode=0o700)
    try:
        for index in range(NODE_COUNT):
            socket_path = network.application_socket(index)
            process = start_process(
                f"node{index}-durable-audit-{expected_height}",
                [
                    network.application,
                    network.root / f"node{index}" / "ledger.db",
                    network.genesis,
                    socket_path,
                ],
                workspace,
            )
            try:
                await_unix_socket(process, socket_path)
                if application_info(socket_path) != (
                    expected_height,
                    expected_application_root,
                ):
                    raise RuntimeError(
                        f"node {index} durable C++ head mismatch"
                    )
            finally:
                try:
                    process.stop()
                finally:
                    process.kill()
    finally:
        network.socket_root.rmdir()


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
    transaction_two = transfer(sodium, fixture, 0, 2, 2, 20_000)
    for relative_path, expected in (
        ("protocol.genesis.hex", fixture.genesis),
        ("transaction-1.hex", transaction_one),
        ("transaction-2.hex", transaction_two),
    ):
        encoded = (
            REPOSITORY / "examples" / "devnet" / relative_path
        ).read_text(encoding="ascii")
        if bytes.fromhex(encoded) != expected:
            raise RuntimeError(f"bundled {relative_path} differs from fixture")

    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="cometbft-four-validator-", dir=parent
    ) as temporary, tempfile.TemporaryDirectory(
        prefix="protocol-stack-devnet-sockets-"
    ) as socket_temporary:
        workspace = pathlib.Path(temporary)
        root = workspace / "network"
        socket_root = pathlib.Path(socket_temporary) / "network"
        genesis = workspace / "protocol.genesis"
        genesis.write_bytes(fixture.genesis)
        network = Network(
            devnet,
            application,
            bridge,
            node,
            root,
            socket_root,
            genesis,
            reserve_port_block(),
        )

        first, initial_health = start_network(network, workspace)
        try:
            latest = synchronize_reference(reference, initial_health, None)
            first_result = run_transaction(
                network,
                workspace,
                0,
                transaction_one,
            )
            latest = apply_submitted_transaction(
                reference,
                transaction_one,
                first_result,
                latest,
            )
            stop_network(first, network)
        finally:
            first.kill()
        audit_durable_heads(
            network,
            workspace,
            latest.height,
            latest.resulting_state_root,
        )

        second, restart_health = start_network(network, workspace)
        try:
            latest = synchronize_reference(
                reference,
                restart_health,
                latest,
            )
            second_result = run_transaction(
                network,
                workspace,
                1,
                transaction_two,
            )
            latest = apply_submitted_transaction(
                reference,
                transaction_two,
                second_result,
                latest,
            )
            stop_network(second, network)
        finally:
            second.kill()
        audit_durable_heads(
            network,
            workspace,
            latest.height,
            latest.resulting_state_root,
        )

    print(
        "CometBFT four-validator integration: passed "
        "(4 independent replicas, 2 signed transfers, full restart, "
        "4 durable C++ audits per stop)"
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
