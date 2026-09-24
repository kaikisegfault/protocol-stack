#!/usr/bin/env python3

"""The version-nine fixture's own contract.

The integration run would catch a broken fixture, but only after a build, four
Go binaries, a CometBFT node, and two process lifecycles, and only on the stamps
one run happened to get. This checks the same claims in well under a second, on
stamps chosen to make each claim sharp.

**The claims are the ones version nine adds.** The genesis stamp names the chain,
so a fixture minted at one instant signs transactions no other instant's chain
accepts. A block's stamp moves its root, which is what makes the integration
run's comparisons a check of the engine's time as well as of the kernel. The
first block may carry the genesis stamp itself, because the engine gives it
exactly that; a stamp below its predecessor's is refused whole. And the two
conversions the harness restates — the header time's text and its millisecond
count — truncate where the contract truncates and refuse what it refuses.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

REPOSITORY = pathlib.Path(__file__).resolve().parents[2]
_HERE = pathlib.Path(__file__).resolve().parent
for _entry in (REPOSITORY, REPOSITORY / "tests" / "differential", _HERE):
    if str(_entry) not in sys.path:
        sys.path.insert(0, str(_entry))

from cometbft_rpc import parse_header_time  # noqa: E402
from pinned_sodium import Sodium  # noqa: E402
from simulation.calendar.civil import days_from_civil  # noqa: E402
from simulation.economy_transition_v8.slots import (  # noqa: E402
    first_cycle_window,
    window_first_height,
)
from simulation.economy_transition_v9 import contract as c  # noqa: E402
from simulation.economy_transition_v9.block import InvalidBlock  # noqa: E402
from version_nine_chain import (  # noqa: E402
    BLOCKS_BEFORE_RESTART,
    SEAT_ID,
    Session,
    Signer,
    engine_millis,
    script,
)

GENESIS_BYTES = 150
# magic, schema, network identifier: the genesis stamp starts here.
GENESIS_TIMESTAMP_OFFSET = 4 + 2 + 4
RECEIPT_BYTES = 56
RECEIPT_PREFIX = b"PSRC\x00\x09"
RECEIPT_RESULT_OFFSET = 39

# 2026-09-24T00:00:00.123Z, a stamp with a millisecond remainder so a fixture
# that rounded it to a second would be caught.
STAMP = days_from_civil(2026, 9, 24) * 86_400_000 + 123
# Three seconds and a millisecond a block, roughly the engine's own pace.
PACE = 3_001


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def run(sodium: Sodium, stamp: int = STAMP):
    """The whole script, block 1 at the genesis stamp as the engine does it."""
    session = Session(sodium, stamp)
    blocks = []
    for index, step in enumerate(script(session)):
        at = stamp + index * PACE
        blocks.append(
            session.apply_empty(at) if step.raw is None
            else session.apply(step.raw, at)
        )
    return session, blocks


def check_shape(sodium: Sodium) -> None:
    session, blocks = run(sodium)
    require(len(session.genesis) == GENESIS_BYTES, "genesis is not 150 octets")
    stamp = session.genesis[GENESIS_TIMESTAMP_OFFSET:GENESIS_TIMESTAMP_OFFSET + 8]
    require(
        int.from_bytes(stamp, "big") == STAMP,
        "the genesis does not carry the stamp it was minted with",
    )
    require(len(session.chain_id) == 32, "chain identity is not 32 octets")
    require(len(session.genesis_root) == 32, "genesis root is not 32 octets")
    steps = script(session)
    require(len(blocks) == len(steps), "the script did not close every block")
    for index, (step, block) in enumerate(zip(steps, blocks)):
        where = f"block {block.height} ({step.label})"
        require(block.height == index + 1, f"{where} is not contiguous from one")
        expected = 0 if step.raw is None else 1
        require(
            len(block.raw_inputs) == expected and len(block.receipts) == expected,
            f"{where} does not hold {expected} input and receipt",
        )
        for receipt in block.receipts:
            require(len(receipt) == RECEIPT_BYTES, f"{where} receipt width")
            require(
                receipt[: len(RECEIPT_PREFIX)] == RECEIPT_PREFIX,
                f"{where} receipt is not a version-nine receipt",
            )
            require(receipt[RECEIPT_RESULT_OFFSET] == 0, f"{where} did not succeed")
    require(
        script(session)[BLOCKS_BEFORE_RESTART - 1].raw is None,
        "the restart does not follow the empty block",
    )
    roots = [session.genesis_root] + [block.state_root for block in blocks]
    require(len(set(roots)) == len(roots), "two blocks produced the same root")
    require(
        len({block.block_id for block in blocks}) == len(blocks),
        "two blocks share an identifier",
    )


def check_the_stamp_moves_the_root(sodium: Sodium) -> None:
    """One millisecond of stamp changes a block's root and identifier.

    Checked on an empty block, whose root depends on nothing but its height, its
    stamp, and the state before it, so the difference has only one cause. The
    same stamp twice is the control: without it, a root that differed on every
    call would pass.
    """
    first = Session(sodium, STAMP)
    second = Session(sodium, STAMP)
    same = Session(sodium, STAMP)
    at = STAMP + PACE
    one, other, again = (
        first.apply_empty(at), second.apply_empty(at + 1), same.apply_empty(at)
    )
    require(one.state_root != other.state_root, "the stamp does not move the root")
    require(one.block_id != other.block_id, "the stamp does not move the identifier")
    require(one == again, "an empty block is not deterministic")


def check_the_genesis_stamp_names_the_chain(sodium: Sodium) -> None:
    """A fixture minted one millisecond later is a different chain.

    The transactions bind the chain identity, so the run's transactions are
    valid on exactly the chain its genesis names and no other; minting the
    genesis at launch therefore mints a new chain, as ADR 0088 says a missed
    window costs.
    """
    early, late = Session(sodium, STAMP), Session(sodium, STAMP + 1)
    require(early.chain_id != late.chain_id, "the stamp does not name the chain")
    require(
        early.genesis_root != late.genesis_root,
        "the genesis root does not commit to the stamp",
    )
    require(
        early.register_alice() != late.register_alice(),
        "a transaction does not bind the chain its genesis names",
    )


def check_the_first_block_may_carry_the_genesis_stamp(sodium: Sodium) -> None:
    """Equality is admitted at height one and a lower stamp is refused whole.

    The engine stamps block 1 with the genesis time exactly, so C2 admitting
    equality is what lets any chain under it start. One millisecond earlier is
    refused as a block, not as a transaction, and leaves the ledger untouched.
    """
    session = Session(sodium, STAMP)
    raw = session.register_alice()
    root = session.state_root()
    try:
        session.apply(raw, STAMP - 1)
    except InvalidBlock as refusal:
        require(
            "TIMESTAMP_NOT_MONOTONIC" in str(refusal),
            f"a stamp below genesis was refused for another reason: {refusal}",
        )
    else:
        raise RuntimeError("a first block stamped before its genesis was accepted")
    require(
        (session.height, session.state_root()) == (0, root),
        "a refused block moved the ledger",
    )
    block = session.apply(raw, STAMP)
    require(
        (block.height, block.timestamp) == (1, STAMP),
        "block 1 did not accept the genesis stamp",
    )


def check_the_conversions(sodium: Sodium) -> None:
    """The header text and its millisecond count, at their edges."""
    del sodium
    epoch = days_from_civil(2026, 9, 24) * 86_400
    for text, expected in (
        ("1970-01-01T00:00:00Z", (0, 0)),
        ("2026-09-24T00:00:00Z", (epoch, 0)),
        ("2026-09-24T00:00:00.1Z", (epoch, 100_000_000)),
        ("2026-09-24T00:00:00.123Z", (epoch, 123_000_000)),
        ("2026-09-24T00:00:00.123999999Z", (epoch, 123_999_999)),
    ):
        require(parse_header_time(text) == expected, f"{text} parsed wrongly")
    for text in (
        "2026-09-24T00:00:00+00:00",
        "2026-09-24T00:00:00.1234567890Z",
        "2026-09-24T00:00:00.Z",
        "2026-09-24 00:00:00Z",
    ):
        try:
            parse_header_time(text)
        except RuntimeError:
            continue
        raise RuntimeError(f"{text!r} was parsed")

    require(engine_millis(epoch, 123_999_999) == epoch * 1000 + 123,
            "a block time does not truncate")
    require(engine_millis(epoch, 999_999) == epoch * 1000,
            "a sub-millisecond time rounds up")
    require(engine_millis(0, 0) == 0, "the epoch is not zero")
    for seconds, nanos in ((-1, 0), (0, -1), (0, 1_000_000_000)):
        try:
            engine_millis(seconds, nanos)
        except ValueError:
            continue
        raise RuntimeError(f"({seconds}, {nanos}) was converted")


def check_the_seat_table_was_written(sodium: Sodium) -> None:
    """The purchase writes one unactivated seat, and the activation activates it.

    The roots agree about both without saying which of them happened, so the
    table is read directly, and the recorded activation height must be the
    height the block ran at.
    """
    session = Session(sodium, STAMP)
    stamps = iter(range(STAMP, STAMP + 8 * PACE, PACE))
    session.apply(session.register_alice(), next(stamps))
    session.apply(session.register_bob(), next(stamps))
    require(session.seats() == {}, "a seat existed before one was bought")

    session.apply(session.alice_buys_seat(1), next(stamps))
    require(session.seats() == {SEAT_ID: False}, "the purchase wrote no seat")
    require(session.activations() == {}, "a purchased seat was reported active")

    activation = session.apply(session.alice_activates_seat(2), next(stamps))
    require(session.seats() == {SEAT_ID: True}, "the seat was not activated")
    require(
        session.activations() == {SEAT_ID: activation.height},
        "the activation height is not the block's",
    )


def check_refusals_land_on_the_empty_root(sodium: Sodium) -> None:
    """Both refusals the devnet provokes, each at the root an empty block makes.

    A stale nonce and a second purchase of an owned seat are refused for
    unrelated reasons, and each must write nothing and charge nothing, so the
    block holding it lands on the root the same height and stamp would produce
    empty. Asking for that root must not spend the height, which is checked by
    asking twice.
    """
    session, blocks = run(sodium)
    at = blocks[-1].timestamp + PACE
    predicted = session.block_if_empty(at)
    require(
        session.block_if_empty(at) == predicted and session.height == len(blocks),
        "predicting an empty block spent the height",
    )
    stale = session.apply_refused(
        session.alice_pays_bob(3, amount=7), at, c.CODE_NUMBER["NONCE_MISMATCH"])
    require(stale.state_root == predicted.state_root,
            "a stale nonce moved the state")
    at += PACE
    predicted = session.block_if_empty(at)
    twice = session.apply_refused(
        session.alice_buys_seat(4), at, c.CODE_NUMBER["REPLAY"])
    require(twice.state_root == predicted.state_root,
            "a second purchase of an owned seat moved the state")
    try:
        session.apply_refused(session.alice_pays_bob(4), at + PACE, 6)
    except RuntimeError:
        pass
    else:
        raise RuntimeError("a transfer that succeeds was accepted as a refusal")


def check_the_audit_is_out_of_reach(sodium: Sodium) -> None:
    """Version eight's wall, derived again: the run's seat is never audited.

    ADR 0071 records why a devnet begun at genesis cannot reach a seat's first
    audited window, and version nine keeps `CYCLE_BLOCKS`. Derived from the
    contract rather than restated, so a changed constant is reported as one.
    """
    session, blocks = run(sodium)
    activation_height = session.activations()[SEAT_ID]
    window = first_cycle_window(activation_height)
    require(window > 0, "a seat was in scope for the window it activated in")
    require(
        window_first_height(window) > blocks[-1].height,
        "the run's seat reaches its first audited window",
    )


def check_signatures_are_real(sodium: Sodium) -> None:
    """A recorded vector's stand-in signature ends in 56 zero octets."""
    session, blocks = run(sodium)
    for block in blocks:
        for raw in block.raw_inputs:
            require(raw[-64:][8:] != bytes(56), f"block {block.height} is a stand-in")
    signer = Signer(sodium)
    key = signer.derive("probe")
    signature = signer.sign(key, b"a message")
    require(signer.verify(key, b"a message", signature), "the signer cannot verify")
    require(
        not signer.verify(key, b"another message", signature),
        "the signer verifies a signature over a different message",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--libsodium", required=True)
    arguments = parser.parse_args()

    sodium = Sodium(arguments.libsodium)
    for check in (
        check_shape,
        check_the_stamp_moves_the_root,
        check_the_genesis_stamp_names_the_chain,
        check_the_first_block_may_carry_the_genesis_stamp,
        check_the_conversions,
        check_the_seat_table_was_written,
        check_refusals_land_on_the_empty_root,
        check_the_audit_is_out_of_reach,
        check_signatures_are_real,
    ):
        check(sodium)
    print("version-nine chain fixture: passed (9 checks)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"version-nine chain fixture: failed: {error}", file=sys.stderr)
        raise SystemExit(1)
