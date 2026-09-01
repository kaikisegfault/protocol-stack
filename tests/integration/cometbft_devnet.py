#!/usr/bin/env python3

"""Driving the four-replica devnet, for whichever ledger version it runs.

Everything here is a property of the network rather than of a ledger: reserving
a port block, starting the supervisor, asking it for health, submitting exact
transaction bytes through one node, auditing every replica's durable head, and
stopping the whole thing. The one version-specific value is which protocol the
supervisor is started for, and it reaches the genesis and every bridge from the
same field — a home written for one ledger version and bridges started for the
other is refused at `InitChain` rather than at the first block.

What is *not* here is the model. Each version's test drives its own and compares
it against what the network reports, which is the whole point of running four of
them.
"""

from __future__ import annotations

import pathlib
import subprocess
import time
from dataclasses import dataclass

from cometbft_process import (
    ManagedProcess,
    application_info,
    await_unix_socket,
    reserve_non_ephemeral_port_block,
    start_process,
)

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
    protocol_version: int = 1

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
            "-protocol-version",
            str(network.protocol_version),
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


def audit_durable_heads(
    network: Network,
    workspace: pathlib.Path,
    expected_height: int,
    expected_application_root: bytes,
) -> None:
    """Open every replica's own database and require the same head from each.

    This is the claim requirement 13 is about, and it is asked of the store
    rather than of the engine: four processes that were never told each other's
    answer must hold the same root at the same height.
    """
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
                if application_info(
                    socket_path, network.protocol_version
                ) != (expected_height, expected_application_root):
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
