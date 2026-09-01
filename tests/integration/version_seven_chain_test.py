#!/usr/bin/env python3

"""The version-seven fixture's own contract.

The integration run would catch a broken fixture, but it would catch it after a
build, four Go binaries, a CometBFT node, and two process lifecycles. This
checks the same claims in a few milliseconds, and it states them: what a node is
being asked to reproduce, and that a real signature is what makes it reproducible.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

REPOSITORY = pathlib.Path(__file__).resolve().parents[2]
_HERE = pathlib.Path(__file__).resolve().parent
for _entry in (REPOSITORY / "tests" / "differential", _HERE):
    if str(_entry) not in sys.path:
        sys.path.insert(0, str(_entry))

from pinned_sodium import Sodium  # noqa: E402
from version_seven_chain import Signer, build_chain  # noqa: E402

RECEIPT_BYTES = 56
RECEIPT_PREFIX = b"PSRC\x00\x07"
RECEIPT_RESULT_OFFSET = 39
GENESIS_BYTES = 110


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def check_shape(chain) -> None:
    require(len(chain.genesis) == GENESIS_BYTES, "genesis is not 110 octets")
    require(len(chain.chain_id) == 32, "chain identity is not 32 octets")
    require(len(chain.genesis_root) == 32, "genesis root is not 32 octets")
    require(len(chain.blocks) == 3, "the fixture is not three blocks")
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
            f"{where} receipt is not a version-seven receipt",
        )
        require(
            receipt[RECEIPT_RESULT_OFFSET] == 0,
            f"{where} transaction did not succeed",
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


def check_deterministic(sodium: Sodium, chain) -> None:
    """A fixture a second run does not reproduce cannot be an expectation."""
    again = build_chain(sodium)
    require(again.genesis == chain.genesis, "the genesis is not deterministic")
    require(
        again.chain_id == chain.chain_id,
        "the chain identity is not deterministic",
    )
    for first, second in zip(chain.blocks, again.blocks):
        require(first == second, f"block {first.height} is not deterministic")


def check_signatures_are_real(sodium: Sodium, chain) -> None:
    """The point of the fixture: a real node's verifier must accept these.

    A recorded version-seven vector is signed with an eight-octet counter padded
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
    check_distinct(chain)
    check_deterministic(sodium, chain)
    check_signatures_are_real(sodium, chain)
    print(
        "version-seven chain fixture: passed "
        f"(3 blocks, {sum(len(b.raw_inputs[0]) for b in chain.blocks)} "
        "signed octets)"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"version-seven chain fixture: failed: {error}", file=sys.stderr)
        raise SystemExit(1)
