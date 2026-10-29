#!/usr/bin/env python3

"""Four independent version-ten replicas, through restarts and a departure.

This is `cometbft_four_validator_v9_test.py` asked of version ten. Four
processes that were never told each other's answer must hold the same height,
the same stamp, and the same root, through restarts, having each executed the
same blocks independently.

**The same scenario as version nine's, so a difference is the version's.**
Transactions enter through four different replicas:

- Alice registers, then Bob, both under the launch key, and the network is
  stopped and started.
- Alice buys seat 0 and activates it, then pays Bob.
- Four transactions, through all four replicas, must each be refused by name:
  a transfer at a consumed nonce, a second purchase of the seat Alice owns,
  Alice's confirmation re-signed under the next nonce, and a confirmation whose
  approval would outlive its slot. Each must land on the root an empty block at
  that height and stamp would produce.
- While the network is down, one replica's own store is driven directly. It is
  interrupted mid-block and handed two blocks its peers never proposed. Then
  one replica leaves a network that keeps committing, catches up, and proposes
  the next block.

After every stop, all four stores are opened directly and must report the
model's height, stamp, and root, and name protocol version 10.

**The last two refusals are version ten's own**, and requirement 5's network
evidence: one is replay protection and the other expiry.

- **The re-signed confirmation is a replay version nine executed.** Its
  confirmation bound the escrow, the recipient, the amount, and the expiry, but
  no nonce. Version ten's approval signs the whole transaction, so a
  confirmation moved to another nonce verifies over nothing and is refused as
  `UNAUTHORIZED`. The republished bytes themselves cannot be shown, because the
  engine's mempool drops a hash it has seen.
- **The last confirmation expires two slots after the height it is built for**,
  so wherever inside a slot it lands it is refused as
  `APPROVAL_LIFETIME_EXCEEDED`. It carries the unconsumed nonce, so no earlier
  condition can refuse it first.

**Every transaction is built when it is submitted, for the next height the
model has not seen.** A transaction that carries a HUB proof must expire within
one slot of the height it executes at, and a network closes a block about every
three seconds whether or not anyone sends one, so no transaction can be built
before the run for a height it is known to land at. Built for height `h`, it is
admitted at every height from `h` to one slot past it, and it lands at `h` or
after.

The engine chooses every stamp, the genesis is minted at launch, and every full
stop must end inside the tolerance, for version nine's reasons (ADRs 0088 and
0089). The driven replica is asked version nine's question: a decided block
whose stamp runs backwards must be refused with status `8`.
"""

from __future__ import annotations

import base64
import pathlib
import sys
import tempfile
import time
from typing import Callable

REPOSITORY = pathlib.Path(__file__).resolve().parents[2]
for _entry in (
    REPOSITORY,
    REPOSITORY / "tests" / "application",
    REPOSITORY / "tests" / "differential",
):
    if str(_entry) not in sys.path:
        sys.path.insert(0, str(_entry))

import application_driver_v2 as driver  # noqa: E402

from cometbft_devnet import (  # noqa: E402
    Network,
    audit_durable_heads,
    control_replica,
    reserve_port_block,
    run_health,
    run_refused_transaction,
    run_transaction,
    start_network,
    stop_network,
)
from cometbft_rpc import committed_block  # noqa: E402
from pinned_sodium import Sodium  # noqa: E402
from simulation.economy_transition_v8.slots import (  # noqa: E402
    first_cycle_window,
    window_first_height,
)
from simulation.economy_transition_v10 import contract as c  # noqa: E402
from version_ten_chain import (  # noqa: E402
    SEAT_ID,
    Block,
    Session,
    engine_millis,
)

PROTOCOL_VERSION = 10

NONCE_MISMATCH = c.CODE_NUMBER["NONCE_MISMATCH"]
REPLAY = c.CODE_NUMBER["REPLAY"]
UNAUTHORIZED = c.CODE_NUMBER["UNAUTHORIZED"]
APPROVAL_LIFETIME_EXCEEDED = c.CODE_NUMBER["APPROVAL_LIFETIME_EXCEEDED"]
LIFETIME = c.APPROVAL_LIFETIME_BLOCKS

# How much of the tolerance must remain once a network reports ready. The
# engine proposes one commit timeout after it starts, and this leaves five
# times that.
LAUNCH_MARGIN_MILLIS = 15_000

# The replica whose headers the model reads. It never departs, so it is running
# whenever the model is advanced.
READER = 0

# The replica driven directly while the network is down, and the one that
# leaves while it runs. They are version nine's choices.
DRIVEN_NODE = 2
DEPARTING_NODE = 3
REMAINING_NODES = (0, 1, 2)

# Builds one transaction for the height it is handed.
Build = Callable[[int], bytes]


def now_millis() -> int:
    return time.time_ns() // 1_000_000


class Chain:
    """The session, the root and stamp of every height, and where stamps come from.

    `roots[h]` is the state after height `h`, and `roots[0]` is the genesis
    root, so the app hash a header carries at height `h` is `roots[h - 1]`.
    `stamps[h]` is the head stamp after height `h`, the genesis stamp at zero.
    """

    def __init__(self, sodium: Sodium, genesis_timestamp: int) -> None:
        self.session = Session(sodium, genesis_timestamp)
        self.roots = [self.session.genesis_root]
        self.stamps = [genesis_timestamp]
        self.rpc_port = 0

    @property
    def next_height(self) -> int:
        """The first height the model has not seen, which every build targets."""
        return self.session.height + 1

    def stamp(self, height: int, transactions: int) -> int:
        """The committed stamp at `height`, converted, and the block's size checked.

        Block 1's is the one stamp nobody proposed: the engine takes it from the
        genesis, and the bridge must convert it exactly.
        """
        (seconds, nanos), count = committed_block(self.rpc_port, height)
        if count != transactions:
            raise RuntimeError(
                f"height {height} holds {count} transactions, not {transactions}")
        stamp = engine_millis(seconds, nanos)
        if height == 1 and (
            nanos % 1_000_000 != 0 or stamp != self.session.genesis_timestamp
        ):
            raise RuntimeError(
                f"block 1 is stamped {seconds}s {nanos}ns, not the genesis "
                f"stamp {self.session.genesis_timestamp} ms"
            )
        return stamp

    def advance_to(self, height: int) -> None:
        if height < self.session.height:
            raise RuntimeError("observed devnet height moved backwards")
        while self.session.height < height:
            at = self.stamp(self.session.height + 1, 0)
            self._record(self.session.apply_empty(at), self.session.height)

    def execute(self, raw: bytes, height: int) -> Block:
        self.advance_to(height - 1)
        block = self.session.apply(raw, self.stamp(height, 1))
        return self._record(block, height)

    def execute_refused(self, raw: bytes, height: int, expected: int) -> Block:
        """The same, for a transaction the contract must refuse by name.

        The empty-block root is taken at the **same stamp** before the block
        runs, because that is the claim: a refusal writes no state and charges
        no fee, so the block must land on exactly the root an empty block at
        that height and stamp would have produced.
        """
        self.advance_to(height - 1)
        at = self.stamp(height, 1)
        if_empty = self.session.block_if_empty(at).state_root
        block = self.session.apply_refused(raw, at, expected)
        if block.state_root != if_empty:
            raise RuntimeError(
                f"the refusal at height {block.height} moved state: root "
                f"{block.state_root.hex().upper()} for an unchanged "
                f"{if_empty.hex().upper()}"
            )
        return self._record(block, height)

    def _record(self, block: Block, height: int) -> Block:
        if block.height != height:
            raise RuntimeError("the model and the network disagree on height")
        self.roots.append(block.state_root)
        self.stamps.append(block.timestamp)
        return block


def require_inside_window(chain: Chain, what: str) -> None:
    """Refuse to go on once the next block's stamp can no longer be accepted.

    The model's head stamp is at or before the network's, so a head still well
    inside the tolerance means the network's next block is too.
    """
    elapsed = now_millis() - chain.session.timestamp
    if elapsed > c.TIMESTAMP_TOLERANCE_MILLIS - LAUNCH_MARGIN_MILLIS:
        raise RuntimeError(
            f"{what} came {elapsed} ms after the stamp the next block builds "
            f"on; C5 refuses a stamp more than "
            f"{c.TIMESTAMP_TOLERANCE_MILLIS} ms behind a machine's clock, so "
            "the network could not continue"
        )


def start(network: Network, workspace: pathlib.Path, chain: Chain, what: str):
    """Start the whole network and report a closed window by name.

    The supervisor's readiness bound is 90 seconds and the tolerance is 60, so
    a network that missed its window fails readiness with a timeout that names
    nothing. It is renamed here when that is what happened.
    """
    try:
        process, health = start_network(network, workspace)
    except RuntimeError as error:
        late = now_millis() - chain.session.timestamp
        if late > c.TIMESTAMP_TOLERANCE_MILLIS:
            raise RuntimeError(
                f"{what} failed {late} ms after the stamp the next block "
                "builds on, past the tolerance; the network cannot continue"
            ) from error
        raise
    try:
        require_inside_window(chain, what)
        check_health(chain, health)
    except Exception:
        process.kill()
        raise
    return process


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
    expected = "ps-" + base64.urlsafe_b64encode(
        chain.session.chain_id).rstrip(b"=").decode("ascii")
    if health["chain_id"] != expected:
        raise RuntimeError("health command reports a different chain identity")


def submit(
    network: Network,
    workspace: pathlib.Path,
    chain: Chain,
    node_index: int,
    build: Build,
    running: tuple[int, ...] | None = None,
) -> bytes:
    """Build for the next height, submit through one replica, and require
    the running replicas to agree. Returns the transaction, for a replay."""
    raw = build(chain.next_height)
    result = run_transaction(network, workspace, node_index, raw, running)
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
    return raw


def submit_refused(
    network: Network,
    workspace: pathlib.Path,
    chain: Chain,
    node_index: int,
    build: Build,
    expected: int,
) -> None:
    """Provoke a refusal through one replica and require all four to agree on it."""
    raw = build(chain.next_height)
    result = run_refused_transaction(network, workspace, node_index, raw)
    if result.height <= chain.session.height:
        raise RuntimeError("the refused transaction did not advance the height")
    block = chain.execute_refused(raw, result.height, expected)
    if result.application_root != block.state_root:
        raise RuntimeError(
            f"node {node_index} converged on root "
            f"{result.application_root.hex().upper()} for "
            f"{block.state_root.hex().upper()} after a refusal"
        )
    if result.receipt != block.receipts[0]:
        raise RuntimeError(
            f"node {node_index} reported a refusal receipt the model did not "
            "produce"
        )


def audit(network: Network, workspace: pathlib.Path, chain: Chain) -> None:
    audit_durable_heads(
        network,
        workspace,
        chain.session.height,
        chain.roots[chain.session.height],
        chain.session.timestamp,
    )


def require_replica_head(
    connection: driver.Connection, index: int, chain: Chain, height: int
) -> None:
    """A replica's protocol version and durable height, stamp, and root."""
    info = connection.info()
    if not isinstance(info, driver.Info):
        raise RuntimeError(f"node {index} refused info while driven: {info!r}")
    if info.application_version != PROTOCOL_VERSION:
        raise RuntimeError(
            f"node {index} reports protocol version {info.application_version}")
    expected = (height, chain.stamps[height], chain.roots[height])
    if (info.height, info.timestamp, info.state_root) != expected:
        raise RuntimeError(
            f"node {index} holds height {info.height} stamp {info.timestamp} "
            f"root {info.state_root.hex().upper()}, for the network's height "
            f"{expected[0]} stamp {expected[1]} root {expected[2].hex().upper()}"
        )


def require_terminal(connection: driver.Connection, index: int, what: str) -> None:
    if connection.info() is not driver.Error.SEQUENCE_FAILURE:
        raise RuntimeError(f"node {index} kept answering after refusing {what}")


def drive_one_stopped_replica(
    network: Network, chain: Chain, index: int
) -> None:
    """Interrupt one replica mid-block, lie to it twice, and leave its store untouched.

    This runs while the network is down, against one replica's own database.
    `finalize_block` writes nothing, so terminating the process between it and
    `commit` is the interruption. The block staged is the empty one at the next
    height and one millisecond after the head's stamp, which the model predicts
    whole. Then a block two heights past the head, a sequence failure, and one
    at the right height a millisecond **before** the head's stamp, which C2
    refuses as status `8`. Both latch the application terminal. A fourth
    process then opens the same store and must find the head the network left.
    """
    stamp = chain.session.timestamp
    predicted = chain.session.block_if_empty(stamp + 1)
    database = network.root / f"node{index}" / "ledger.db"
    socket_path = network.socket_root / "driven.sock"

    def run(ask) -> None:
        process = driver.start(
            network.application, database, network.genesis, socket_path)
        try:
            with driver.Connection(socket_path) as connection:
                require_replica_head(
                    connection, index, chain, chain.session.height)
                if ask is not None:
                    ask(connection)
        finally:
            driver.stop(process, socket_path)

    def stage(connection: driver.Connection) -> None:
        staged = connection.finalize_block(predicted.height, predicted.timestamp)
        if not isinstance(staged, driver.Finalized) or (
            staged.state_root != predicted.state_root
            or staged.block_id != predicted.block_id
            or staged.results != ()
        ):
            raise RuntimeError(
                f"node {index} staged {staged!r} at height {predicted.height}, "
                "which the model did not produce"
            )

    def too_far(connection: driver.Connection) -> None:
        refused = connection.finalize_block(predicted.height + 1, stamp + 1)
        if refused is not driver.Error.SEQUENCE_FAILURE:
            raise RuntimeError(
                f"node {index} answered a block two heights ahead with {refused!r}")
        require_terminal(connection, index, "a block two heights ahead")

    def backwards(connection: driver.Connection) -> None:
        refused = connection.finalize_block(predicted.height, stamp - 1)
        if refused is not driver.TimestampFailure.DECIDED_BLOCK_FAILED_MONOTONICITY:
            raise RuntimeError(
                f"node {index} answered a stamp below its head with {refused!r}")
        require_terminal(connection, index, "a stamp below its head")

    network.socket_root.mkdir(mode=0o700)
    try:
        # Terminated with the block staged and uncommitted, which is the whole
        # point: nothing after this may find it.
        run(stage)
        run(too_far)
        run(backwards)
        run(None)
    finally:
        network.socket_root.rmdir()


def require_departed_replica_is_behind(
    network: Network, index: int, chain: Chain, height: int
) -> None:
    """Open the stopped replica's own store and require it to be where it left."""
    socket_path = network.socket_root / "departed.sock"
    process = driver.start(
        network.application,
        network.root / f"node{index}" / "ledger.db",
        network.genesis,
        socket_path,
    )
    try:
        with driver.Connection(socket_path) as connection:
            require_replica_head(connection, index, chain, height)
    finally:
        driver.stop(process, socket_path)


def one_replica_leaves_and_returns(
    network: Network,
    workspace: pathlib.Path,
    chain: Chain,
    pay: Callable[[int], Build],
    first_nonce: int,
) -> int:
    """Take one replica down, keep committing, and require it to catch up.

    Three of four validators hold thirty of forty voting power, which is more
    than two thirds and so exactly enough. The departed replica has no window:
    it catches up through block sync, which never applies C5. `pay` builds
    Alice's transfer at a nonce, and the three here take three consecutive
    nonces from `first_nonce`.

    Returns the height the network reached while the replica was away.
    """
    departure_height = chain.session.height

    control_replica(network, "stop", DEPARTING_NODE)
    check_health(chain, run_health(network, REMAINING_NODES))

    submit(network, workspace, chain, 0, pay(first_nonce), REMAINING_NODES)
    submit(network, workspace, chain, 2, pay(first_nonce + 1), REMAINING_NODES)
    reached = chain.session.height
    if reached <= departure_height:
        raise RuntimeError(
            "the remaining replicas committed nothing while node "
            f"{DEPARTING_NODE} was down"
        )
    require_departed_replica_is_behind(
        network, DEPARTING_NODE, chain, departure_height)

    control_replica(network, "start", DEPARTING_NODE)
    caught_up = run_health(network)
    if int(caught_up["height"]) < reached:
        raise RuntimeError(
            f"node {DEPARTING_NODE} rejoined at height {caught_up['height']}, "
            f"behind the {reached} its peers reached"
        )
    check_health(chain, caught_up)

    submit(network, workspace, chain, DEPARTING_NODE, pay(first_nonce + 2))
    return reached


def check_the_seat_is_sold_and_unaudited(chain: Chain) -> int:
    """What the run proved about the seat, and what it could not have proved."""
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

    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="cometbft-four-validator-v10-", dir=parent
    ) as temporary, tempfile.TemporaryDirectory(
        prefix="protocol-stack-devnet-v10-sockets-"
    ) as socket_temporary:
        workspace = pathlib.Path(temporary)
        # Minted as late as the run allows: everything between here and the
        # network's first proposal spends the launch window.
        chain = Chain(sodium, now_millis())
        session = chain.session

        def pay(
            nonce: int, amount: int = 1_000_000, lifetime: int = LIFETIME
        ) -> Build:
            return lambda height: session.alice_pays_bob(
                nonce, height, amount, lifetime)

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
            PROTOCOL_VERSION,
        )
        chain.rpc_port = network.rpc_port(READER)

        first = start(network, workspace, chain, "the launch")
        try:
            submit(network, workspace, chain, 0,
                   lambda height: session.register(session.alice, height))
            submit(network, workspace, chain, 1,
                   lambda height: session.register(session.bob, height))
            stop_network(first, network)
        finally:
            first.kill()
        audit(network, workspace, chain)

        second = start(network, workspace, chain, "the first restart")
        try:
            submit(network, workspace, chain, 2,
                   lambda height: session.alice_buys_seat(1, height))
            submit(network, workspace, chain, 3,
                   lambda height: session.alice_activates_seat(2, height))
            confirmed = submit(network, workspace, chain, 0, pay(3))
            submit_refused(
                network, workspace, chain, 1, pay(3, amount=7), NONCE_MISMATCH)
            submit_refused(
                network, workspace, chain, 2,
                lambda height: session.alice_buys_seat(4, height), REPLAY)
            submit_refused(
                network, workspace, chain, 3,
                lambda _height: session.resigned(confirmed, 4), UNAUTHORIZED)
            submit_refused(
                network, workspace, chain, 0,
                pay(4, lifetime=2 * LIFETIME),
                APPROVAL_LIFETIME_EXCEEDED)
            stop_network(second, network)
        finally:
            second.kill()
        audit(network, workspace, chain)

        drive_one_stopped_replica(network, chain, DRIVEN_NODE)

        third = start(network, workspace, chain, "the second restart")
        try:
            submit(network, workspace, chain, DRIVEN_NODE, pay(4))
            height_without_it = one_replica_leaves_and_returns(
                network, workspace, chain, pay, 5)
            stop_network(third, network)
        finally:
            third.kill()
        audit(network, workspace, chain)
        activation_height = check_the_seat_is_sold_and_unaudited(chain)

    print(
        "CometBFT four-validator version-ten integration: passed "
        "(4 independent replicas, genesis stamped at launch and carried by "
        "block 1, 2 launch-key registrations, 1 seat bought and activated at "
        f"height {activation_height}, 5 confirmed transfers, and 4 refusals -- "
        "NONCE_MISMATCH, REPLAY, UNAUTHORIZED for a confirmation re-signed "
        "under the next nonce, and APPROVAL_LIFETIME_EXCEEDED for one that "
        "outlives its slot -- through 4 different nodes, 2 full restarts "
        f"inside the window, node {DRIVEN_NODE} interrupted mid-block and fed "
        "a block two heights ahead and a stamp below its head, node "
        f"{DEPARTING_NODE} stopped while the other 3 committed to height "
        f"{height_without_it} and caught up on return, protocol version, "
        "durable height, stamp and root audited in all 4 stores per stop)"
    )


def main() -> int:
    if len(sys.argv) != 7:
        raise RuntimeError(
            "usage: cometbft_four_validator_v10_test "
            "<application-v10> <bridge> <node> <devnet> "
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
            "CometBFT four-validator version-ten integration: "
            f"failed: {error}",
            file=sys.stderr,
        )
        raise SystemExit(1)
