#!/usr/bin/env python3

"""A replica fed blocks its peers never proposed.

`ledger-transition-v1` has three refusal classes and this repository had tested
two of them against a running node. An **admission** failure omits the
transaction from execution and from the transaction root. An **execution**
failure admits it, gives it a receipt with a nonzero code, and leaves the block
valid — M3.14b made four replicas agree about two of those. The third rejects
the **whole proposed block** and restores the pre-block state, and nothing here
had ever made a running application produce one.

**A mempool cannot deliver the third, and that is the shape of this test rather
than a footnote.** CometBFT gossips every transaction to every replica and each
replica builds its own block from its own mempool, so no devnet fixture can hand
one node a block the others would refuse. The honest route is to drive
`protocol-application-v8` directly, over the private Unix socket it already
serves, and hand it blocks no proposer on its chain could have built.

**What the refusals have to prove is not that they happen.** Three things are
claimed of every one of them, and the third is the one requirement 13 needs:

* the refusal carries the *named* status, because two different defects both
  refuse and only one refuses for the stated reason — and the two wrong-height
  cases here answer with two different statuses, so a change that collapsed them
  into one would be reported rather than absorbed;
* the refusal is **terminal**. A deterministic application that has told the
  network one thing and found another stops answering rather than guessing which
  was right, so every later request on the same process is refused too;
* the refusal **wrote nothing**. Each scenario opens on the durable head the
  previous one left, so a refusal that had written would be reported by the
  process that came after it rather than by the one that caused it.

**And one refusal is not the application's at all.** A block past the wire's
bounds never reaches it: the frame decoder enforces the same three block bounds
first and the server drops the connection, so the peer sees a close rather than
a status and the application never latches. That layering is checked here
because it is the difference between "the node refused" and "the node never
heard", and ADR 0072 records why the application's own copy of those bounds
cannot be reached from outside.

**Two determinism claims fall out of the restarts and are worth naming.** The
same block executed by two different processes from the same durable head
produces the identical root, block identifier and receipt; and a chain whose
replica refused a block is still usable afterwards, because the honest block at
that height finalizes and commits on the very next process.

The transactions are the version-eight chain fixture's, signed with real
Ed25519 through the pinned libsodium, because the application opens its store
with `protocol::v8::ed25519_verifier()` and would refuse a stand-in signature as
`INVALID_SIGNATURE` before any of this became reachable.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
from collections.abc import Callable

REPOSITORY = pathlib.Path(__file__).resolve().parents[2]
for _entry in (
    REPOSITORY,
    REPOSITORY / "tests" / "application",
    REPOSITORY / "tests" / "differential",
):
    if str(_entry) not in sys.path:
        sys.path.insert(0, str(_entry))

import application_driver as driver  # noqa: E402

from pinned_sodium import Sodium  # noqa: E402
from version_eight_chain import RESULT_OFFSET, Block, Session  # noqa: E402

PROTOCOL_VERSION = 8
APP_STATE = b'"protocol-stack-v8"'
# Version seven's, which is the string a stale deployment would still be
# sending and the neighbour `init_chain` exists to tell apart from its own.
FOREIGN_APP_STATE = b'"protocol-stack-v7"'
# `kMaximumAdapterHeight` is `INT64_MAX`, and the first height past it is the
# one `finalize_block` refuses before it has read a head at all.
FIRST_HEIGHT_PAST_THE_ADAPTER_BOUND = 2**63


class Replica:
    """The paths one application process is started and restarted against."""

    def __init__(
        self,
        executable: pathlib.Path,
        database: pathlib.Path,
        genesis: pathlib.Path,
        socket_path: pathlib.Path,
    ) -> None:
        self.executable = executable
        self.database = database
        self.genesis = genesis
        self.socket_path = socket_path

    def start(self) -> subprocess.Popen[bytes]:
        return driver.start(
            self.executable, self.database, self.genesis, self.socket_path
        )

    def stop(self, process: subprocess.Popen[bytes]) -> None:
        driver.stop(process, self.socket_path)


def expected_results(block: Block) -> tuple[tuple[int, bytes], ...]:
    """The `(code, receipt)` pairs the application must report for a block.

    `application_code` leaves a success at zero and offsets every other result
    by 256, so the code and the receipt's own result octet are one fact rather
    than two. Deriving it here rather than writing zeros means a block whose
    transaction was refused would be compared just as exactly.
    """
    return tuple(
        (0 if receipt[RESULT_OFFSET] == 0 else 256 + receipt[RESULT_OFFSET],
         receipt)
        for receipt in block.receipts
    )


def check_head(
    connection: driver.Connection, height: int, state_root: bytes
) -> None:
    info = connection.info()
    if not isinstance(info, driver.Info):
        raise RuntimeError(f"a started replica refused info: {info!r}")
    if info.application_version != PROTOCOL_VERSION:
        raise RuntimeError("the replica reports a foreign protocol version")
    if info.height != height or info.state_root != state_root:
        raise RuntimeError(
            f"the replica opened at height {info.height} root "
            f"{info.state_root.hex().upper()}, for height {height} root "
            f"{state_root.hex().upper()}"
        )


def check_block(answer: object, block: Block, what: str) -> driver.Finalized:
    if not isinstance(answer, driver.Finalized):
        raise RuntimeError(f"{what} was refused: {answer!r}")
    if answer.state_root != block.state_root:
        raise RuntimeError(
            f"{what} produced root {answer.state_root.hex().upper()} for the "
            f"model's {block.state_root.hex().upper()}"
        )
    if answer.block_id != block.block_id:
        raise RuntimeError(f"{what} produced a block identifier the model did not")
    if answer.results != expected_results(block):
        raise RuntimeError(f"{what} produced results the model did not")
    return answer


def check_latched(connection: driver.Connection, what: str) -> None:
    """Every later request is refused, whatever it asks.

    `info` reads nothing and writes nothing and is still refused, which is what
    makes this the application's latch rather than the store's condition.
    """
    for name, answer in (
        ("info", connection.info()),
        ("commit", connection.commit()),
        ("finalize_block", connection.finalize_block(1)),
    ):
        if answer is not driver.Error.SEQUENCE_FAILURE:
            raise RuntimeError(
                f"{what} left {name} answering {answer!r} rather than a latched "
                "refusal"
            )


def build_the_chain(replica: Replica, session: Session) -> list[Block]:
    """Three honest blocks, and the operations that must not latch a replica.

    This is the head every refusal below is provoked against, and it is built
    the way a consensus engine builds one: `finalize_block` then `commit`, one
    block at a time, with the model executing the same octets beside it.
    """
    blocks: list[Block] = []
    process = replica.start()
    try:
        with driver.Connection(replica.socket_path) as connection:
            check_head(connection, 0, session.genesis_root)
            root = connection.init_chain(session.chain_id, 1, APP_STATE)
            if root != session.genesis_root:
                raise RuntimeError(f"init_chain answered {root!r}")

            for raw in (
                session.register_alice(),
                session.register_bob(),
                session.alice_pays_bob(1),
            ):
                block = session.apply(raw)
                blocks.append(block)
                answer = connection.finalize_block(block.height, (raw,))
                check_block(answer, block, f"block {block.height}")
                # CometBFT may ask twice, and a second execution that disagreed
                # with the first would be a defect this layer must not hide. The
                # identical repeat returns the staged answer and does not latch.
                if connection.finalize_block(block.height, (raw,)) != answer:
                    raise RuntimeError(
                        f"a repeated finalize_block at height {block.height} "
                        "answered differently"
                    )
                committed = connection.commit()
                if committed != driver.Committed(block.height, block.state_root):
                    raise RuntimeError(
                        f"commit at height {block.height} answered {committed!r}"
                    )

            head = blocks[-1]
            # Voting against a proposal is not a refusal and must never latch:
            # a replica that stopped every time a peer proposed the wrong height
            # would be trivially killable by one bad proposer.
            for height, verdict in (
                (head.height + 2, False),
                (head.height, False),
                (head.height + 1, True),
            ):
                answer = connection.process_proposal(height)
                if answer is not verdict:
                    raise RuntimeError(
                        f"process_proposal at height {height} answered "
                        f"{answer!r} rather than {verdict}"
                    )
            check_head(connection, head.height, head.state_root)

            # A chain is initialised once in its life rather than once per
            # process, so this is the last thing asked of this process.
            again = connection.init_chain(session.chain_id, 1, APP_STATE)
            if again is not driver.Error.SEQUENCE_FAILURE:
                raise RuntimeError(f"a second init_chain answered {again!r}")
            check_latched(connection, "a second init_chain")
    finally:
        replica.stop(process)
    return blocks


def refuse(
    replica: Replica,
    head: Block,
    what: str,
    provoke: Callable[[driver.Connection], object],
    expected: driver.Error,
) -> None:
    """Open a replica at `head`, provoke one refusal, and require the latch.

    The head check is the claim that the *previous* scenario's refusal wrote
    nothing: this process opened the same store and found the same height and
    the same root. That is why every refusal below is its own process rather
    than another request on one connection.
    """
    process = replica.start()
    try:
        with driver.Connection(replica.socket_path) as connection:
            check_head(connection, head.height, head.state_root)
            answer = provoke(connection)
            if answer is not expected:
                raise RuntimeError(
                    f"{what} answered {answer!r} rather than {expected!r}"
                )
            check_latched(connection, what)
    finally:
        replica.stop(process)


def check_the_wire_refuses_first(replica: Replica, head: Block) -> None:
    """A block past the bounds is dropped by the wire, not refused by the node.

    Both cases are well-formed frames carrying a block no proposer could build,
    and both are refused by the frame decoder before any application sees them:
    the peer's connection closes and it receives no status at all. The process
    survives it — a peer that speaks nonsense loses its connection and nothing
    else — and the proof is that a second connection finds the same head and an
    application that never latched.
    """
    cases = {
        "one input past the block-input bound": tuple(
            b"" for _ in range(driver.MAXIMUM_BLOCK_INPUTS + 1)
        ),
        "one octet past the transaction bound": (
            bytes(driver.MAXIMUM_TRANSACTION_BYTES + 1),
        ),
    }
    process = replica.start()
    try:
        for what, transactions in cases.items():
            with driver.Connection(replica.socket_path) as connection:
                check_head(connection, head.height, head.state_root)
                try:
                    answer = connection.finalize_block(
                        head.height + 1, transactions
                    )
                except driver.Disconnected:
                    continue
                raise RuntimeError(f"{what} was answered with {answer!r}")
        with driver.Connection(replica.socket_path) as connection:
            check_head(connection, head.height, head.state_root)
            # The application never saw either frame, so it cannot have latched.
            if connection.process_proposal(head.height + 1) is not True:
                raise RuntimeError("the wire's refusal reached the application")
    finally:
        replica.stop(process)


def check_a_staged_block_is_not_replaced(
    replica: Replica, head: Block, block: Block, raw: bytes
) -> None:
    """The sharpest block a peer never proposed: the staged height, other content.

    A staged block is the one this node has already told the network it would
    produce. Being asked to finalize a *different* block at that height is the
    case where continuing would mean having said two things about one height, so
    it latches rather than restaging.

    **The second process is the half that makes the latch a safety property
    rather than a denial of service.** It opens the store the refused one left,
    finds the same head, executes the same block from it, and produces the
    identical root, identifier and receipt — so two processes that were never
    told each other's answer agree about a block — and then commits it. A stage
    that had written would make every one of those figures wrong.
    """
    process = replica.start()
    try:
        with driver.Connection(replica.socket_path) as connection:
            check_head(connection, head.height, head.state_root)
            staged = connection.finalize_block(block.height, (raw,))
            check_block(staged, block, f"the staged block {block.height}")
            answer = connection.finalize_block(block.height)
            if answer is not driver.Error.SEQUENCE_FAILURE:
                raise RuntimeError(
                    f"an empty block at the staged height answered {answer!r}"
                )
            check_latched(connection, "a second block at the staged height")
    finally:
        replica.stop(process)

    process = replica.start()
    try:
        with driver.Connection(replica.socket_path) as connection:
            check_head(connection, head.height, head.state_root)
            answer = connection.finalize_block(block.height, (raw,))
            if answer != staged:
                raise RuntimeError(
                    f"a second process executed block {block.height} differently"
                )
            check_block(answer, block, f"the reexecuted block {block.height}")
            committed = connection.commit()
            if committed != driver.Committed(block.height, block.state_root):
                raise RuntimeError(f"the honest commit answered {committed!r}")
            check_head(connection, block.height, block.state_root)
    finally:
        replica.stop(process)


def check_the_commit_is_durable(replica: Replica, block: Block) -> None:
    """One more process, for the one commit no later scenario would re-open.

    Every earlier commit is checked across a process boundary for free, because
    the next scenario opens the store and requires the head it left. The last
    one has nothing after it, and a `commit` that answered the staged figures
    without writing them would pass every check in this file without it. A
    mutation probe found exactly that, which is why this is its own scenario
    rather than another request on the connection that committed.
    """
    process = replica.start()
    try:
        with driver.Connection(replica.socket_path) as connection:
            check_head(connection, block.height, block.state_root)
    finally:
        replica.stop(process)


def check_init_chain_identity(replica: Replica, session: Session) -> None:
    """A node started against the wrong chain, height or engine must not join.

    **The latch is the process's rather than the store's**, and these three are
    where that distinction is visible: `init_chain` writes nothing whether it is
    accepted or refused, so a refused one leaves a home that is still exactly a
    genesis. Each case is its own process because each latches the one that
    asked, and the fourth process initialises the chain normally — which is the
    claim that a refusal did not poison the home the next start would open.
    """
    foreign_chain = bytes(octet ^ 0xFF for octet in session.chain_id)
    cases = {
        "a foreign chain identity": (foreign_chain, 1, APP_STATE),
        "an initial height that is not one": (session.chain_id, 2, APP_STATE),
        "version seven's app state": (
            session.chain_id, 1, FOREIGN_APP_STATE),
    }
    for what, (chain_id, initial_height, app_state) in cases.items():
        process = replica.start()
        try:
            with driver.Connection(replica.socket_path) as connection:
                check_head(connection, 0, session.genesis_root)
                answer = connection.init_chain(
                    chain_id, initial_height, app_state)
                if answer is not driver.Error.INVALID_REQUEST:
                    raise RuntimeError(
                        f"init_chain with {what} answered {answer!r}")
                check_latched(connection, f"init_chain with {what}")
        finally:
            replica.stop(process)

    process = replica.start()
    try:
        with driver.Connection(replica.socket_path) as connection:
            check_head(connection, 0, session.genesis_root)
            root = connection.init_chain(session.chain_id, 1, APP_STATE)
            if root != session.genesis_root:
                raise RuntimeError(
                    f"the chain would not initialise afterwards: {root!r}")
    finally:
        replica.stop(process)


def verify(
    executable: pathlib.Path,
    sodium_library: pathlib.Path,
    directory: pathlib.Path,
) -> None:
    if directory.exists():
        for entry in sorted(directory.iterdir()):
            entry.unlink()
    directory.mkdir(parents=True, exist_ok=True)

    session = Session(Sodium(str(sodium_library)))
    genesis = directory / "g"
    genesis.write_bytes(session.genesis)
    socket_path = directory / "s"
    chain = Replica(executable, directory / "c", genesis, socket_path)
    # A second home, kept at genesis, because `init_chain` is answerable only
    # there and every one of its refusals latches the process that asked.
    fresh = Replica(executable, directory / "f", genesis, socket_path)

    blocks = build_the_chain(chain, session)
    head = blocks[-1]

    # Two wrong heights, refused by two different guards. The bound is checked
    # before a head is read and answers `INVALID_REQUEST`; the successor rule is
    # checked against the durable head and answers `SEQUENCE_FAILURE`. A change
    # that collapsed them would be reported here rather than absorbed.
    refuse(
        chain, head, "a block from the future",
        lambda connection: connection.finalize_block(head.height + 2),
        driver.Error.SEQUENCE_FAILURE)
    refuse(
        chain, head, "a block at a committed height",
        lambda connection: connection.finalize_block(head.height),
        driver.Error.SEQUENCE_FAILURE)
    refuse(
        chain, head, "a block past the adapter's height bound",
        lambda connection: connection.finalize_block(
            FIRST_HEIGHT_PAST_THE_ADAPTER_BOUND),
        driver.Error.INVALID_REQUEST)
    refuse(
        chain, head, "a commit with nothing staged",
        lambda connection: connection.commit(),
        driver.Error.SEQUENCE_FAILURE)

    check_the_wire_refuses_first(chain, head)

    raw = session.alice_pays_bob(2)
    next_block = session.apply(raw)
    check_a_staged_block_is_not_replaced(chain, head, next_block, raw)
    check_the_commit_is_durable(chain, next_block)

    check_init_chain_identity(fresh, session)

    for entry in sorted(directory.iterdir()):
        entry.unlink()
    print(
        "version-eight driven application: passed "
        f"({len(blocks) + 1} committed blocks, 5 latched block refusals, 4 "
        "latched init_chain refusals, 2 wire-dropped blocks, and a chain still "
        f"usable at height {next_block.height})"
    )


def main() -> int:
    if len(sys.argv) != 4:
        raise RuntimeError(
            "usage: driven_application_v8_test "
            "<application-v8> <libsodium> <directory>"
        )
    executable = pathlib.Path(sys.argv[1]).resolve()
    sodium_library = pathlib.Path(sys.argv[2]).resolve()
    for required in (executable, sodium_library):
        if not required.is_file():
            raise RuntimeError(f"missing input {required}")
    verify(executable, sodium_library, pathlib.Path(sys.argv[3]).resolve())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(
            f"version-eight driven application: failed: {error}",
            file=sys.stderr,
        )
        raise SystemExit(1)
