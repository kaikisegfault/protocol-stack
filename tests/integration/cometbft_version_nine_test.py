#!/usr/bin/env python3

"""A version-nine chain through a real CometBFT process.

Everything below this has been exercised against recorded vectors and test
drivers, in C++, Go, and Python, and none of it had met a consensus engine. This
is the first time a version-nine block is proposed, voted on, finalized, and
committed by one, with every figure the node reports compared against the
independent Python model.

**The engine chooses every stamp, and the model is told it afterwards.** A
version-nine root commits to the head's timestamp, so a block's expected root
cannot be known until the block has committed. Each step therefore commits
first, reads the committed header's time, converts it with
`consensus-application-v2`'s rule, and only then asks the model what that block
produces. The comparison is an end-to-end check of the bridge's conversion as
well as of the kernel, because the model's figure and the node's agree only if
both derived the same millisecond.

**The genesis is minted when the run starts.** CometBFT `v0.39.4` stamps block 1
with the genesis time exactly, and C5 refuses that stamp in every round once
civil time is 60 seconds past it (ADR 0088). So the stamp is the current time,
block 1 is required to carry it to the nanosecond, and the harness refuses to
launch, or to relaunch, once the stamp the next block will carry is too old to
be accepted — which reports a closed window by name instead of as a timeout.

**The restart has the same window, at every height.** After block 1 the engine
stamps a block with the median of the previous height's precommit times, and a
restarted node rebuilds those precommits from its stored commit, so the first
block after a restart carries a stamp taken before the stop. A node that stays
down longer than the tolerance comes back to a proposal every correct machine
refuses, forever. ADR 0089 records that as a property of the chain rather than
of this harness.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass

REPOSITORY = pathlib.Path(__file__).resolve().parents[2]
for _entry in (REPOSITORY, REPOSITORY / "tests" / "differential"):
    if str(_entry) not in sys.path:
        sys.path.insert(0, str(_entry))

from cometbft_process import (  # noqa: E402
    ManagedProcess,
    initialize_home,
    inspect_identity_v9,
    reserve_ports,
    start_stack,
    stop_stack,
)
from cometbft_rpc import (  # noqa: E402
    abci_info,
    commit_transaction,
    committed_block,
    rpc_call,
    status,
)
from pinned_sodium import Sodium  # noqa: E402
from simulation.economy_transition_v9 import contract as c  # noqa: E402
from version_nine_chain import (  # noqa: E402
    BLOCKS_BEFORE_RESTART,
    Block,
    Session,
    Step,
    engine_millis,
    script,
)

PROTOCOL_VERSION = 9

# How much of the tolerance must remain when a node is started. The engine
# proposes one commit timeout after it starts, three seconds, and this leaves
# five times that for a slow runner to reach the proposal.
LAUNCH_MARGIN_MILLIS = 15_000

# How long to wait for the engine to close a block nobody sent a transaction
# for. It closes one a commit timeout after any block that moved the root.
EMPTY_BLOCK_WAIT_SECONDS = 15


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


def now_millis() -> int:
    return time.time_ns() // 1_000_000


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


def require_inside_window(stamp: int, what: str) -> None:
    """Refuse to go on once the next block's stamp can no longer be accepted.

    `stamp` is the head's. The next block's stamp is at least that, so if the
    head's is still well inside the tolerance so is the next one's, and a run
    that is not has missed the window for good rather than being slow.
    """
    elapsed = now_millis() - stamp
    if elapsed > c.TIMESTAMP_TOLERANCE_MILLIS - LAUNCH_MARGIN_MILLIS:
        raise RuntimeError(
            f"{what} came {elapsed} ms after the stamp the next block builds "
            f"on; C5 refuses a stamp more than "
            f"{c.TIMESTAMP_TOLERANCE_MILLIS} ms behind a machine's clock, so "
            "the chain could not continue"
        )


def block_identity(rpc_port: int, height: int) -> bytes:
    """The block identifier the adapter published as a block event."""
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


def engine_stamp(rpc_port: int, height: int, transactions: int) -> int:
    """The committed stamp at `height`, converted, and the block's size checked."""
    (seconds, nanos), count = committed_block(rpc_port, height)
    if count != transactions:
        raise RuntimeError(
            f"height {height} holds {count} transactions, not {transactions}")
    return engine_millis(seconds, nanos)


def require_reported(stack: Stack, block: Block, previous: bytes) -> None:
    """Every figure the node reports about a block, against the model's.

    `/status` reports the app hash in the latest header, which at height `H` is
    the state after `H - 1`; `/abci_info` reports the application's own durable
    head; the block event carries the identifier, which commits to the header
    and so to the stamp. Each is a different claim.
    """
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


def commit_transaction_step(stack: Stack, session: Session, raw: bytes) -> Block:
    expected_height = session.height + 1
    height, receipt = commit_transaction(stack.rpc_port, raw)
    if height != expected_height:
        raise RuntimeError(
            f"transaction committed at height {height}, not {expected_height}")
    stamp = engine_stamp(stack.rpc_port, height, 1)
    previous = session.state_root()
    block = session.apply(raw, stamp)
    if receipt != block.receipts[0]:
        raise RuntimeError(f"height {height} receipt differs from the model's")
    require_reported(stack, block, previous)
    return block


def commit_empty_step(stack: Stack, session: Session) -> Block:
    """Wait for the engine to close a block on its own, then check it.

    CometBFT `v0.39.4` proposes without waiting for a transaction whenever the
    last block changed the app hash (`needProofBlock`), and a version-nine block
    always does. The wait polls the application's head rather than the block
    store's, because the store records a block before the application commits it.
    """
    height = session.height + 1
    deadline = time.monotonic() + EMPTY_BLOCK_WAIT_SECONDS
    while abci_info(stack.rpc_port)[0] < height:
        if time.monotonic() > deadline:
            raise RuntimeError(f"the engine did not close height {height}")
        time.sleep(0.05)
    stamp = engine_stamp(stack.rpc_port, height, 0)
    previous = session.state_root()
    block = session.apply_empty(stamp)
    require_reported(stack, block, previous)
    return block


def commit_steps(stack: Stack, session: Session, steps: tuple[Step, ...]) -> None:
    for step in steps:
        if step.raw is None:
            commit_empty_step(stack, session)
        else:
            commit_transaction_step(stack, session, step.raw)


def require_durable(processes: list[ManagedProcess], stack: Stack,
                    session: Session) -> None:
    durable = stop_stack(processes, stack.application_socket, PROTOCOL_VERSION)
    if durable != (session.height, session.state_root()):
        raise RuntimeError(
            f"durable head after {session.height} blocks: height={durable[0]} "
            f"root={durable[1].hex().upper()}"
        )


def commit_before_restart(
    stack: Stack, session: Session, steps: tuple[Step, ...]
) -> None:
    """Block 1 carries the genesis stamp, to the nanosecond.

    It is the one stamp nobody proposed: the engine takes it from the genesis
    every validator agreed on, and the bridge must convert it exactly rather
    than by truncation. A sub-millisecond remainder here would mean the
    initializer wrote a genesis time the canonical genesis does not name.
    """
    processes = launch(stack)
    try:
        require_inside_window(session.genesis_timestamp, "the launch")
        commit_steps(stack, session, steps[:1])
        (seconds, nanos), _ = committed_block(stack.rpc_port, 1)
        if nanos % 1_000_000 != 0 or engine_millis(seconds, nanos) != (
            session.genesis_timestamp
        ):
            raise RuntimeError(
                f"block 1 is stamped {seconds}s {nanos}ns, not the genesis "
                f"stamp {session.genesis_timestamp} ms"
            )
        commit_steps(stack, session, steps[1:BLOCKS_BEFORE_RESTART])
        require_durable(processes, stack, session)
    finally:
        for process in reversed(processes):
            process.kill()


def commit_after_restart(
    stack: Stack, session: Session, steps: tuple[Step, ...]
) -> None:
    """The remaining blocks run on a process that executed none of the first.

    Their roots therefore depend on a state read back out of SQLite, including
    the durable stamp C2 compares the first of them against. That first block's
    own stamp was taken before the stop, which is why the window is checked
    again here.
    """
    processes = launch(stack)
    try:
        require_inside_window(session.timestamp, "the restart")
        restarted = abci_info(stack.rpc_port)
        if restarted != (session.height, session.state_root()):
            raise RuntimeError(
                f"restart handshake head: height={restarted[0]} "
                f"root={restarted[1].hex().upper()}"
            )
        commit_steps(stack, session, steps[BLOCKS_BEFORE_RESTART:])
        require_durable(processes, stack, session)
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
    sodium = Sodium(str(sodium_library))

    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="cometbft-v9-", dir=parent
    ) as temporary, tempfile.TemporaryDirectory(
        prefix="ps-cb9-socket-"
    ) as socket_temporary:
        workspace = pathlib.Path(temporary)
        genesis = workspace / "protocol.genesis"
        database = workspace / "ledger.db"
        application_socket = pathlib.Path(socket_temporary) / "app.sock"
        home = workspace / "cometbft"

        # Minted as late as the run allows: everything between here and the
        # node's first proposal spends the launch window.
        session = Session(sodium, now_millis())
        steps = script(session)
        genesis.write_bytes(session.genesis)

        chain_id, initial_root, stamp = inspect_identity_v9(application, genesis)
        if (chain_id, initial_root, stamp) != (
            session.chain_id, session.genesis_root, session.genesis_timestamp
        ):
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
                genesis_timestamp=stamp,
            )

        # Twice, because the second call must exact-validate the home the first
        # wrote, genesis time included, rather than rewrite it.
        initialize()
        initialize()
        commit_before_restart(stack, session, steps)

        initialize()
        commit_after_restart(stack, session, steps)

    print(
        "CometBFT version-nine integration: passed "
        "(genesis stamped at launch and carried by block 1, 2 registrations, "
        "1 empty block, 1 seat sold and activated, 1 confirmed transfer, "
        f"restart at height {BLOCKS_BEFORE_RESTART}, "
        f"durable height {session.height})"
    )


def main() -> int:
    if len(sys.argv) != 7:
        raise RuntimeError(
            "usage: cometbft_version_nine_test "
            "<application-v9> <bridge> <initializer> <node> "
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
            f"CometBFT version-nine integration: failed: {error}",
            file=sys.stderr,
        )
        raise SystemExit(1)
