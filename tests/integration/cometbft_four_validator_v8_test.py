#!/usr/bin/env python3

"""Four independent version-eight replicas, through a full restart.

This is requirement 13's central claim asked of version eight: four processes
that were never told each other's answer must hold the same state root at the
same height, through a restart, having each executed the same blocks
independently.

**Seven transactions enter through four different replicas, and two of them are
refused.** A node that agreed only with the peer it heard from would pass a
single-submitter run. Alice registers through node 0 and Bob through node 1; the
network is stopped and started; then Alice buys seat 0 through node 2, activates
it through node 3, and pays Bob through node 0; and finally node 1 is handed a
transfer at a consumed nonce and node 2 a second purchase of the seat Alice
already owns. After every stop all four databases are opened directly and
required to report the same head.

**The seat is the point of this run.** Kinds 2 and 3 write the seat table, and
before this fixture grew them no consensus engine in this repository had
executed either: they existed in the C++ kernel, in the Python model, and in
recorded vectors, and nowhere in between. Four independent replicas now agree on
the roots a purchase and an activation produce, having each executed them from
octets rather than been told the answer. Both land after the restart, so the
registry entry the purchase reads is a row recovered from SQLite, and node 3 —
which has never submitted anything here — is the replica that activates.

**Two of the seven transactions are refused, and that is the other half of the
claim.** Every four-node run in this repository used to be four replicas
agreeing about a *success*: every receipt carried a zero, so nothing here had
ever required a network to say no and all four replicas to say the same no. The
deterministic-kernel argument rests on exactly that — a wrong transaction cannot
change state because every replica independently refuses it — and the sentence
was untested until a wrong transaction was produced.

**Each refusal is checked three ways.** The receipt must carry the *named* code,
because two different defects both refuse and only one refuses for the stated
reason; the four replicas must converge on one root; and that root must be the
one an empty block at the same height would have produced, which is the sharpest
form of "no state write and no fee", since the root moves only by the height it
commits to.

**A refused transaction still reaches a block, and that is what makes the claim
four-replica at all.** `ApplicationV8::check_transaction` refuses only oversized
input, so a stale nonce passes CheckTx, is gossiped, is proposed, and is
committed — and every replica executes and refuses it independently. A
transaction CheckTx rejected would be refused by one node's admission filter
instead, which is a much weaker statement; `run_refused_transaction` fails
closed on that case rather than accepting it as a refusal.

**It still does not exercise the uptime audit, and that is arithmetic.** A seat
is in scope only from the window *after* the one it activated in, and a window is
28,800 heights, so a seat this network can activate is first audited at a height
it will not reach: not because the fixture is weak but because a devnet begun at
genesis stays inside window 0. ADR 0071 records the wall and the two mechanisms
that would cross it, neither of which this slice adopts.

**Between the second and third runs, one replica is driven directly.** While the
network is down, node 2's own SQLite database is opened by a driven
`ApplicationV8` and asked two things no consensus engine would ask it: to stage
a block and then be terminated before committing it, which is the mid-block
interruption requirement 13 names and needs no fault injection at all; and to
finalize a block at a height its peers never proposed, which is the third
refusal class — a whole-block rejection rather than a per-transaction one. Then
the network is started again and required to converge on the head it had and
commit a further transaction. **That is the claim**: a replica that was
interrupted or lied to loses nothing and rejoins where its peers are.

**A genuine partition is still not tested**, and neither is a replica that goes
down while the other three keep committing. Both need the devnet supervisor to
survive one child exiting and to report the health of a named subset of
replicas, which is Go harness work with its own slice. Both are named here
rather than silently left out.

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
for _entry in (
    REPOSITORY,
    REPOSITORY / "tests" / "application",
    REPOSITORY / "tests" / "differential",
):
    if str(_entry) not in sys.path:
        sys.path.insert(0, str(_entry))

import application_driver as driver  # noqa: E402

from cometbft_devnet import (  # noqa: E402
    Network,
    audit_durable_heads,
    reserve_port_block,
    run_refused_transaction,
    run_transaction,
    start_network,
    stop_network,
)
from pinned_sodium import Sodium  # noqa: E402
from simulation.economy_transition_v8.contract import CODE_NUMBER  # noqa: E402
from simulation.economy_transition_v8.slots import (  # noqa: E402
    first_cycle_window,
    window_first_height,
)
from version_eight_chain import SEAT_ID, Block, Session  # noqa: E402

PROTOCOL_VERSION = 8

# Version-eight result codes, read from the contract rather than written down.
# They are named because a bare 6 or 12 at a call site would make this test say
# "it was refused" where it means "it was refused for this reason", and they are
# looked up because a transcribed number agrees with a renumbered code space.
NONCE_MISMATCH = CODE_NUMBER["NONCE_MISMATCH"]
REPLAY = CODE_NUMBER["REPLAY"]

# The replica driven directly between the second and third runs. Any of the four
# would do; it is node 2 because that is the one that submitted the last refused
# transaction, so the replica interrogated here is one that has already been
# asked to disagree with a submitter.
DRIVEN_NODE = 2


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
        return self._record(block, height)

    def execute_refused(self, raw: bytes, height: int, expected: int) -> Block:
        """The same, for a transaction the contract must refuse by name.

        The empty-block root is taken *before* the block runs, because that is
        the claim: every non-success result writes no state and charges no fee,
        so a block whose only transaction was refused must land on exactly the
        root an empty block at that height would have produced. The root still
        moves — it commits to the height — and it must move to that value and
        no other.

        **This overlaps a guard the model already has, and saying so is more
        useful than implying it does not.** `_execute_block` compares the state
        root across each transaction and raises `InvalidBlock` when a refusal
        changed it, so a refusal that writes state is caught there first — a
        probe that made `NONCE_MISMATCH` advance the nonce before refusing dies
        with "a refused transaction changed the state" rather than here. What
        this adds is the same property stated about the block the *network*
        committed, at the height it committed it, after the version-eight issue
        and expiry steps have run. Today those two are the same claim because no
        seat is in scope; they stop being the same the moment any step varies
        with block content.
        """
        self.advance_to(height - 1)
        if_empty = self.session.root_if_empty()
        block = self.session.apply_refused(raw, expected)
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


def submit_refused(
    network: Network,
    workspace: pathlib.Path,
    chain: Chain,
    node_index: int,
    raw: bytes,
    expected: int,
) -> None:
    """Provoke a refusal through one replica and require all four to agree on it.

    This is the same claim `submit` makes, asked of a *no* instead of a yes. The
    network still commits a block — the transaction passed CheckTx, entered a
    mempool, was gossiped, proposed and finalized — and every replica had to
    execute it, refuse it for the same stated reason, and arrive at the same
    root. The receipt is compared octet for octet, so "all four refused" is a
    claim about the reason and the figures rather than about a nonzero byte.
    """
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
    )


def require_replica_head(
    connection: driver.Connection, index: int, height: int, root: bytes
) -> None:
    info = connection.info()
    if not isinstance(info, driver.Info):
        raise RuntimeError(f"node {index} refused info while driven: {info!r}")
    if info.height != height or info.state_root != root:
        raise RuntimeError(
            f"node {index} holds height {info.height} root "
            f"{info.state_root.hex().upper()}, for the network's height "
            f"{height} root {root.hex().upper()}"
        )


def drive_one_stopped_replica(
    network: Network, chain: Chain, index: int
) -> None:
    """Interrupt one replica mid-block, lie to it, and leave its store untouched.

    This runs while the network is down, against one replica's own database, and
    it asks two things of it that no consensus engine on its chain would ask.

    **The first is the mid-block interruption, and it needs no fault injection.**
    `finalize_block` writes nothing: it copies the durable head, executes the
    block in memory, and stages what it produced, and only `commit` writes. So
    terminating the process between the two *is* the interruption requirement 13
    names, exactly and without a seam in production code. The block staged is the
    empty one at the next height, which the model predicts whole through
    `block_if_empty` — root, identifier and all — so the replica and the model
    agree about a block **the network will never produce**, because this devnet
    runs with `create_empty_blocks = false` and commits only blocks that carry a
    transaction.

    **The second is a block its peers never proposed**, at a height two past the
    head, which is refused by name and latches the application terminal. Both
    claims are then checked the only way that matters: a third process opens the
    same store and must find the head the network left, so a stage or a refusal
    that had written is reported here rather than by the network afterwards.
    """
    height = chain.session.height
    root = chain.roots[height]
    predicted = chain.session.block_if_empty()
    database = network.root / f"node{index}" / "ledger.db"
    socket_path = network.socket_root / "driven.sock"
    network.socket_root.mkdir(mode=0o700)
    try:
        process = driver.start(
            network.application, database, network.genesis, socket_path)
        try:
            with driver.Connection(socket_path) as connection:
                require_replica_head(connection, index, height, root)
                staged = connection.finalize_block(predicted.height)
                if not isinstance(staged, driver.Finalized):
                    raise RuntimeError(
                        f"node {index} refused an empty block at height "
                        f"{predicted.height}: {staged!r}"
                    )
                if (staged.state_root != predicted.state_root
                        or staged.block_id != predicted.block_id
                        or staged.results != ()):
                    raise RuntimeError(
                        f"node {index} staged a block at height "
                        f"{predicted.height} the model did not produce"
                    )
        finally:
            # Terminated with the block staged and uncommitted, which is the
            # whole point: nothing below may find it.
            driver.stop(process, socket_path)

        process = driver.start(
            network.application, database, network.genesis, socket_path)
        try:
            with driver.Connection(socket_path) as connection:
                require_replica_head(connection, index, height, root)
                foreign = connection.finalize_block(height + 2)
                if foreign is not driver.Error.SEQUENCE_FAILURE:
                    raise RuntimeError(
                        f"node {index} answered a block at height {height + 2} "
                        f"with {foreign!r}"
                    )
                if connection.info() is not driver.Error.SEQUENCE_FAILURE:
                    raise RuntimeError(
                        f"node {index} kept answering after refusing a block "
                        "its peers never proposed"
                    )
        finally:
            driver.stop(process, socket_path)

        process = driver.start(
            network.application, database, network.genesis, socket_path)
        try:
            with driver.Connection(socket_path) as connection:
                require_replica_head(connection, index, height, root)
        finally:
            driver.stop(process, socket_path)
    finally:
        network.socket_root.rmdir()


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
    # Two transactions the contract must refuse, and they are refused for two
    # different reasons so that "the network says no" is not one code path.
    #
    # A *stale nonce* is a replay in the only form a running network can carry
    # one: the same bytes broadcast twice never reach the application, because
    # CometBFT's mempool discards a transaction whose hash it has already seen.
    # A different amount at a consumed nonce has a different hash, passes the
    # cache, and is refused by the kernel instead -- which is the layer whose
    # refusal this slice exists to observe.
    #
    # A *second purchase of seat 0* is refused for a reason that is nothing to
    # do with nonces, and it is charged at the nonce the failed transfer did not
    # consume, because a non-success result performs no state write at all.
    stale_nonce_transfer = chain.session.alice_pays_bob(3, amount=7)
    seat_bought_twice = chain.session.alice_buys_seat(4)
    # The transaction the network commits after one of its replicas has been
    # interrupted and lied to. Nonce 4 is the next one Alice has, because
    # neither refusal above consumed hers.
    transfer_after_the_interruption = chain.session.alice_pays_bob(4)

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
            submit_refused(
                network, workspace, chain, 1, stale_nonce_transfer,
                NONCE_MISMATCH)
            submit_refused(
                network, workspace, chain, 2, seat_bought_twice, REPLAY)
            stop_network(second, network)
        finally:
            second.kill()
        audit(network, workspace, chain)

        drive_one_stopped_replica(network, chain, DRIVEN_NODE)

        # And the network still works. The replica that was interrupted and lied
        # to is the one the next transaction enters through, so a store it had
        # damaged would be reported by the block it proposes rather than by a
        # quiet disagreement four replicas never notice.
        third, resumed_health = start_network(network, workspace)
        try:
            check_health(chain, resumed_health)
            submit(
                network, workspace, chain, DRIVEN_NODE,
                transfer_after_the_interruption)
            stop_network(third, network)
        finally:
            third.kill()
        audit(network, workspace, chain)
        activation_height = check_the_seat_is_sold_and_unaudited(chain)

    print(
        "CometBFT four-validator version-eight integration: passed "
        "(4 independent replicas, 2 registrations, 1 seat bought and activated "
        f"at height {activation_height}, 2 confirmed transfers, and 2 refusals "
        "-- NONCE_MISMATCH and REPLAY -- through 4 different nodes, 2 full "
        f"restarts, node {DRIVEN_NODE} interrupted mid-block and fed a block "
        "its peers never proposed, 4 durable C++ audits per stop)"
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
