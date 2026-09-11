#!/usr/bin/env python3

"""The version-eight fixture's own contract.

The integration run would catch a broken fixture, but it would catch it after a
build, four Go binaries, a CometBFT node, and two process lifecycles. This
checks the same claims in a few milliseconds, and it states them: what a node is
being asked to reproduce, and that a real signature is what makes it reproducible.

**One check here is about what the fixture does not prove.** The chain now sells
and activates a seat, which reads as exercising version eight's uptime audit and
does not, because a seat is in scope only from the window after the one it
activated in. `check_the_audit_is_out_of_reach` derives that from the contract's
own constants rather than restating it, so the file cannot quietly outlive the
arithmetic it depends on.
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

from pinned_sodium import Sodium  # noqa: E402
from simulation.economy_transition_v8.slots import (  # noqa: E402
    first_cycle_window,
    window_first_height,
)
from version_eight_chain import (  # noqa: E402
    SEAT_ID,
    Session,
    Signer,
    build_chain,
)

RECEIPT_BYTES = 56
RECEIPT_PREFIX = b"PSRC\x00\x08"
RECEIPT_RESULT_OFFSET = 39
GENESIS_BYTES = 142
BLOCKS = 5


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def check_shape(chain) -> None:
    require(
        len(chain.genesis) == GENESIS_BYTES,
        f"genesis is not {GENESIS_BYTES} octets",
    )
    require(len(chain.chain_id) == 32, "chain identity is not 32 octets")
    require(len(chain.genesis_root) == 32, "genesis root is not 32 octets")
    require(len(chain.blocks) == BLOCKS, f"the fixture is not {BLOCKS} blocks")
    for index, block in enumerate(chain.blocks):
        where = f"block {index}"
        require(block.height == index + 1, f"{where} is not contiguous from one")
        # One transaction per block is the requirement the whole fixture exists
        # to satisfy: a root commits to the whole block, and a mempool will not
        # put a chosen set into one block in a chosen order.
        require(len(block.raw_inputs) == 1, f"{where} does not hold one input")
        require(len(block.receipts) == 1, f"{where} does not hold one receipt")
        for name, value in (
            ("state root", block.state_root),
            ("block identifier", block.block_id),
            ("transaction root", block.transaction_root),
        ):
            require(len(value) == 32, f"{where} {name} is not 32 octets")
        receipt = block.receipts[0]
        require(
            len(receipt) == RECEIPT_BYTES,
            f"{where} receipt is not 56 octets",
        )
        require(
            receipt[: len(RECEIPT_PREFIX)] == RECEIPT_PREFIX,
            f"{where} receipt is not a version-eight receipt",
        )
        require(
            receipt[RECEIPT_RESULT_OFFSET] == 0,
            f"{where} transaction did not succeed",
        )


def check_the_dispute_authority_is_its_own_key(chain) -> None:
    """The one version-eight claim nothing else in this file would notice.

    A fixture that passed the verifier key twice would still encode, still
    derive a chain identity, and still execute every block — so the two keys
    being two keys is checked here or nowhere. The field is specified as sitting
    immediately after the verifier key, and that adjacency is checked too:
    a decoder reading the two at swapped offsets produces a genesis that
    re-encodes identically only when they are equal.
    """
    require(
        chain.verifier_key != chain.dispute_authority_key,
        "the fixture used one key for both genesis authorities",
    )
    pair = chain.verifier_key + chain.dispute_authority_key
    require(
        chain.genesis.count(pair) == 1,
        "the dispute authority key does not follow the verifier key exactly once",
    )


def check_distinct(chain) -> None:
    """Every block must move the state, or agreeing about it proves nothing."""
    roots = [chain.genesis_root] + [block.state_root for block in chain.blocks]
    require(len(set(roots)) == len(roots), "two blocks produced the same root")
    identifiers = {block.block_id for block in chain.blocks}
    require(
        len(identifiers) == len(chain.blocks),
        "two blocks share an identifier",
    )


def check_the_seat_table_was_written(sodium: Sodium) -> None:
    """The purchase and the activation are two writes, and the roots cannot say so.

    `build_chain` freezes its blocks and discards the states between them, so
    this drives its own session: the claim is about what the seat table held
    after each of the two blocks, which the five roots agree about without
    distinguishing.

    Four things are checked and each of them is a different way for the fixture
    to have become a weaker statement than it reads as. The chain holds no seat
    before the purchase; it holds exactly one afterwards, unactivated; that same
    seat is activated afterwards without a second seat appearing; and the
    activation height the ledger recorded is the height the block ran at rather
    than any other.
    """
    session = Session(sodium)
    session.apply(session.register_alice())
    session.apply(session.register_bob())
    require(session.seats() == {}, "a seat existed before one was bought")

    purchase = session.apply(session.alice_buys_seat(1))
    require(
        session.seats() == {SEAT_ID: False},
        f"the purchase at height {purchase.height} did not write one unactivated seat",
    )
    require(
        session.activations() == {},
        "a purchased seat was reported as activated",
    )

    activation = session.apply(session.alice_activates_seat(2))
    require(
        session.seats() == {SEAT_ID: True},
        f"the activation at height {activation.height} did not activate the seat",
    )
    require(
        session.activations() == {SEAT_ID: activation.height},
        "the recorded activation height is not the height the block ran at",
    )


def check_the_audit_is_out_of_reach(chain) -> None:
    """The fixture's own statement of what it does not prove, derived not asserted.

    Version eight audits in-scope seats at every height, and this chain now has
    an activated seat — so the natural reading is that the run exercises the
    issue and expiry steps against a real subject. It does not. A seat is in
    scope only from the window *after* the one it activated in, and a window is
    `CYCLE_BLOCKS` heights, so the fixture's seat is first audited at a height
    no devnet begun at genesis will commit.

    Both figures are read from the contract rather than written down here, so a
    changed constant is reported as a changed constant instead of silently
    making this file wrong. ADR 0071 records why the wall is not built around.
    """
    require(
        chain.activations.keys() == {SEAT_ID},
        "the chain did not activate exactly the seat it sold",
    )
    activation_height = chain.activations[SEAT_ID]
    window = first_cycle_window(activation_height)
    first_audited = window_first_height(window)
    require(
        window > 0,
        "a seat activated in window 0 was reported as in scope for window 0",
    )
    reached = chain.blocks[-1].height
    require(
        first_audited > reached,
        f"the seat activated at height {activation_height} is audited at height "
        f"{first_audited}, which this fixture's chain reaches at {reached}",
    )


def check_deterministic(sodium: Sodium, chain) -> None:
    """A fixture a second run does not reproduce cannot be an expectation."""
    again = build_chain(sodium)
    require(again.genesis == chain.genesis, "the genesis is not deterministic")
    require(
        again.chain_id == chain.chain_id,
        "the chain identity is not deterministic",
    )
    require(
        again.activations == chain.activations,
        "the activation heights are not deterministic",
    )
    for first, second in zip(chain.blocks, again.blocks):
        require(first == second, f"block {first.height} is not deterministic")


def check_signatures_are_real(sodium: Sodium, chain) -> None:
    """The point of the fixture: a real node's verifier must accept these.

    A recorded version-eight vector is signed with an eight-octet counter padded
    to 64 octets, which is unmistakably not an Ed25519 signature and which
    `ed25519_verifier()` refuses. The transaction's trailing 64 octets are its
    signature, so a fixture whose signature has 56 trailing zeros has silently
    become a recorded vector again.
    """
    for block in chain.blocks:
        signature = block.raw_inputs[0][-64:]
        require(len(signature) == 64, "a transaction carries no signature")
        require(
            signature[8:] != bytes(56),
            f"block {block.height} carries a stand-in signature",
        )
    signer = Signer(sodium)
    public_key = signer.derive("probe")
    signature = signer.sign(public_key, b"a message")
    require(
        signer.verify(public_key, b"a message", signature),
        "the signer cannot verify what it signed",
    )
    require(
        not signer.verify(public_key, b"another message", signature),
        "the signer verifies a signature over a different message",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--libsodium", required=True)
    arguments = parser.parse_args()

    sodium = Sodium(arguments.libsodium)
    chain = build_chain(sodium)
    check_shape(chain)
    check_the_dispute_authority_is_its_own_key(chain)
    check_distinct(chain)
    check_the_seat_table_was_written(sodium)
    check_the_audit_is_out_of_reach(chain)
    check_deterministic(sodium, chain)
    check_signatures_are_real(sodium, chain)
    print(
        "version-eight chain fixture: passed "
        f"({BLOCKS} blocks, 1 seat sold and activated, "
        f"{sum(len(b.raw_inputs[0]) for b in chain.blocks)} signed octets)"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"version-eight chain fixture: failed: {error}", file=sys.stderr)
        raise SystemExit(1)
