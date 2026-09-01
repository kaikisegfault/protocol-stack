#!/usr/bin/env python3

from __future__ import annotations

import pathlib
import sys
import tempfile

REPOSITORY = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY / "tests" / "differential"))

from cases import make_fixture, transfer  # noqa: E402
from cometbft_devnet import (  # noqa: E402
    Network,
    SubmittedTransaction,
    audit_durable_heads,
    reserve_port_block,
    run_transaction,
    start_network,
    stop_network,
)
from model import BlockCommit, ReferenceLedger, state_root  # noqa: E402
from pinned_sodium import Sodium  # noqa: E402


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
