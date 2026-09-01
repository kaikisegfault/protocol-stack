#!/usr/bin/env python3

"""Four independent version-seven replicas, through a full restart.

This is requirement 13's central claim asked of version seven: four processes
that were never told each other's answer must hold the same state root at the
same height, through a restart, having each executed the same blocks
independently.

**Three transactions enter through three different replicas.** A node that
agreed only with the peer it heard from would pass a single-submitter run.
Alice registers through node 0, Bob registers through node 1, the network is
stopped and started, and Alice pays Bob through node 2 — and after every stop
all four databases are opened directly and required to report the same head.

**The model is driven alongside the network rather than precomputed.** A
consensus engine decides how many blocks a chain has, and an empty version-seven
block still moves the state root because the root commits to the height, so the
session is advanced to whatever height the network reports before the next
transaction is executed against it.
"""

from __future__ import annotations

import base64
import pathlib
import sys
import tempfile

REPOSITORY = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY / "tests" / "differential"))

from cometbft_devnet import (  # noqa: E402
    Network,
    audit_durable_heads,
    reserve_port_block,
    run_transaction,
    start_network,
    stop_network,
)
from pinned_sodium import Sodium  # noqa: E402
from version_seven_chain import Block, Session  # noqa: E402

PROTOCOL_VERSION = 7


class Chain:
    """The session and the root every height produced, in one place.

    `roots[h]` is the state after height `h`, and `roots[0]` is the genesis
    root, so the app hash a header carries at height `h` is `roots[h - 1]`.
    """

    def __init__(self, sodium: Sodium) -> None:
        self.session = Session(sodium)
        self.roots = [self.session.genesis_root]

    def advance_to(self, height: int) -> None:
        if height < self.session.height:
            raise RuntimeError("observed devnet height moved backwards")
        while self.session.height < height:
            self.roots.append(self.session.apply_empty().state_root)

    def execute(self, raw: bytes, height: int) -> Block:
        self.advance_to(height - 1)
        block = self.session.apply(raw)
        if block.height != height:
            raise RuntimeError("the model and the network disagree on height")
        self.roots.append(block.state_root)
        return block


def check_health(chain: Chain, health: dict[str, str]) -> None:
    height = int(health["height"])
    chain.advance_to(height)
    header_root = b"" if height == 0 else chain.roots[height - 1]
    if (
        int(health["header_height"]) != height
        or bytes.fromhex(health["header_app_hash"]) != header_root
        or bytes.fromhex(health["app_hash"]) != chain.roots[height]
    ):
        raise RuntimeError("health command differs from the model")
    # The engine names a chain the way `nodeconfig.Identity.CometChainID` does:
    # `ps-` and the protocol chain identity in unpadded URL-safe base64.
    expected = "ps-" + base64.urlsafe_b64encode(
        chain.session.chain_id).rstrip(b"=").decode("ascii")
    if health["chain_id"] != expected:
        raise RuntimeError("health command reports a different chain identity")


def submit(
    network: Network,
    workspace: pathlib.Path,
    chain: Chain,
    node_index: int,
    raw: bytes,
) -> None:
    """Submit through one replica and require the whole network to agree."""
    result = run_transaction(network, workspace, node_index, raw)
    if result.height <= chain.session.height:
        raise RuntimeError("transaction did not advance the devnet height")
    block = chain.execute(raw, result.height)
    if result.application_root != block.state_root:
        raise RuntimeError(
            f"node {node_index} reported root "
            f"{result.application_root.hex().upper()} for "
            f"{block.state_root.hex().upper()}"
        )
    if result.receipt != block.receipts[0]:
        raise RuntimeError(
            f"node {node_index} reported a receipt the model did not produce"
        )


def audit(network: Network, workspace: pathlib.Path, chain: Chain) -> None:
    audit_durable_heads(
        network,
        workspace,
        chain.session.height,
        chain.roots[chain.session.height],
    )


def verify(
    application: pathlib.Path,
    bridge: pathlib.Path,
    node: pathlib.Path,
    devnet: pathlib.Path,
    sodium_library: pathlib.Path,
    parent: pathlib.Path,
) -> None:
    sodium = Sodium(str(sodium_library))
    chain = Chain(sodium)
    register_alice = chain.session.register_alice()
    register_bob = chain.session.register_bob()
    alice_pays_bob = chain.session.alice_pays_bob(1)

    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="cometbft-four-validator-v7-", dir=parent
    ) as temporary, tempfile.TemporaryDirectory(
        prefix="protocol-stack-devnet-v7-sockets-"
    ) as socket_temporary:
        workspace = pathlib.Path(temporary)
        root = workspace / "network"
        socket_root = pathlib.Path(socket_temporary) / "network"
        genesis = workspace / "protocol.genesis"
        genesis.write_bytes(chain.session.genesis)
        network = Network(
            devnet,
            application,
            bridge,
            node,
            root,
            socket_root,
            genesis,
            reserve_port_block(),
            PROTOCOL_VERSION,
        )

        first, initial_health = start_network(network, workspace)
        try:
            check_health(chain, initial_health)
            submit(network, workspace, chain, 0, register_alice)
            submit(network, workspace, chain, 1, register_bob)
            stop_network(first, network)
        finally:
            first.kill()
        audit(network, workspace, chain)

        second, restart_health = start_network(network, workspace)
        try:
            check_health(chain, restart_health)
            submit(network, workspace, chain, 2, alice_pays_bob)
            stop_network(second, network)
        finally:
            second.kill()
        audit(network, workspace, chain)

    print(
        "CometBFT four-validator version-seven integration: passed "
        "(4 independent replicas, 2 registrations and 1 confirmed transfer "
        "through 3 different nodes, full restart, 4 durable C++ audits per stop)"
    )


def main() -> int:
    if len(sys.argv) != 7:
        raise RuntimeError(
            "usage: cometbft_four_validator_v7_test "
            "<application-v7> <bridge> <node> <devnet> "
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
            "CometBFT four-validator version-seven integration: "
            f"failed: {error}",
            file=sys.stderr,
        )
        raise SystemExit(1)
