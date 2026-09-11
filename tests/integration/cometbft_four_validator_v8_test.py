#!/usr/bin/env python3

"""Four independent version-eight replicas, through a full restart.

This is requirement 13's central claim asked of version eight: four processes
that were never told each other's answer must hold the same state root at the
same height, through a restart, having each executed the same blocks
independently.

**Five transactions enter through four different replicas.** A node that agreed
only with the peer it heard from would pass a single-submitter run. Alice
registers through node 0 and Bob through node 1; the network is stopped and
started; then Alice buys seat 0 through node 2, activates it through node 3, and
pays Bob through node 0 — and after every stop all four databases are opened
directly and required to report the same head.

**The seat is the point of this run.** Kinds 2 and 3 write the seat table, and
before this fixture grew them no consensus engine in this repository had
executed either: they existed in the C++ kernel, in the Python model, and in
recorded vectors, and nowhere in between. Four independent replicas now agree on
the roots a purchase and an activation produce, having each executed them from
octets rather than been told the answer. Both land after the restart, so the
registry entry the purchase reads is a row recovered from SQLite, and node 3 —
which has never submitted anything here — is the replica that activates.

**It still does not exercise the uptime audit, and that is arithmetic.** A seat
is in scope only from the window *after* the one it activated in, and a window is
28,800 heights, so a seat this network can activate is first audited at a height
it will not reach: not because the fixture is weak but because a devnet begun at
genesis stays inside window 0. ADR 0071 records the wall and the two mechanisms
that would cross it, neither of which this slice adopts.

**The model is driven alongside the network rather than precomputed.** A
consensus engine decides how many blocks a chain has, and an empty version-eight
block still moves the state root because the root commits to the height, so the
session is advanced to whatever height the network reports before the next
transaction is executed against it.

**Under version eight a quiet height is not a no-op**, which is why the session
is advanced one whole block at a time rather than through the ledger's
shorthand: every height runs the prologue, the issue step, and the expiry step
against whatever seats are in scope. None is in scope here, so those steps
evaluate nothing — but the code path a replica runs at a quiet height is version
eight's, and that is what four replicas are being required to agree about.
"""

from __future__ import annotations

import base64
import pathlib
import sys
import tempfile

REPOSITORY = pathlib.Path(__file__).resolve().parents[2]
for _entry in (REPOSITORY, REPOSITORY / "tests" / "differential"):
    if str(_entry) not in sys.path:
        sys.path.insert(0, str(_entry))

from cometbft_devnet import (  # noqa: E402
    Network,
    audit_durable_heads,
    reserve_port_block,
    run_transaction,
    start_network,
    stop_network,
)
from pinned_sodium import Sodium  # noqa: E402
from simulation.economy_transition_v8.slots import (  # noqa: E402
    first_cycle_window,
    window_first_height,
)
from version_eight_chain import SEAT_ID, Block, Session  # noqa: E402

PROTOCOL_VERSION = 8


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


def check_the_seat_is_sold_and_unaudited(chain: Chain) -> int:
    """What the run proved about the seat, and what it could not have proved.

    The first half is the slice's outcome: the network executed a purchase and
    an activation, so exactly one seat exists and it is activated at a height
    the engine chose rather than one this fixture predicted.

    The second half keeps the docstring above honest. An activated seat reads as
    putting version eight's issue and expiry steps under a real subject, and it
    does not, because a seat is in scope only from the window after the one it
    activated in. That is derived here from the contract's own rule rather than
    asserted, so a network that somehow *did* reach its seat's first window
    would fail this rather than pass it quietly.
    """
    activations = chain.session.activations()
    if activations.keys() != {SEAT_ID}:
        raise RuntimeError(
            f"the devnet activated {sorted(activations)} rather than [{SEAT_ID}]"
        )
    activation_height = activations[SEAT_ID]
    first_audited = window_first_height(first_cycle_window(activation_height))
    if first_audited <= chain.session.height:
        raise RuntimeError(
            f"the seat activated at height {activation_height} is audited from "
            f"height {first_audited}, which this devnet reached"
        )
    return activation_height


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
    # Every transaction is built before the network starts, because none of the
    # five binds a height: a nonce is per-signer and consecutive, and the seat
    # messages bind the seat identifier rather than the block it lands in. What
    # the engine chooses is which height each one lands at, which is exactly the
    # figure the model is driven to rather than told.
    register_alice = chain.session.register_alice()
    register_bob = chain.session.register_bob()
    alice_buys_seat = chain.session.alice_buys_seat(1)
    alice_activates_seat = chain.session.alice_activates_seat(2)
    alice_pays_bob = chain.session.alice_pays_bob(3)

    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="cometbft-four-validator-v8-", dir=parent
    ) as temporary, tempfile.TemporaryDirectory(
        prefix="protocol-stack-devnet-v8-sockets-"
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
            submit(network, workspace, chain, 2, alice_buys_seat)
            submit(network, workspace, chain, 3, alice_activates_seat)
            submit(network, workspace, chain, 0, alice_pays_bob)
            stop_network(second, network)
        finally:
            second.kill()
        audit(network, workspace, chain)
        activation_height = check_the_seat_is_sold_and_unaudited(chain)

    print(
        "CometBFT four-validator version-eight integration: passed "
        "(4 independent replicas, 2 registrations, 1 seat bought and activated "
        f"at height {activation_height}, and 1 confirmed transfer through 4 "
        "different nodes, full restart, 4 durable C++ audits per stop)"
    )


def main() -> int:
    if len(sys.argv) != 7:
        raise RuntimeError(
            "usage: cometbft_four_validator_v8_test "
            "<application-v8> <bridge> <node> <devnet> "
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
            "CometBFT four-validator version-eight integration: "
            f"failed: {error}",
            file=sys.stderr,
        )
        raise SystemExit(1)
