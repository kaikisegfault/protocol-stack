"""The accepted RFC 9162 ordered binary tree, parameterised by domain prefix.

`protocol-primitives-v1` fixes the shape: for `n > 1` split the ordered leaves at
the largest power of two strictly less than `n`, recurse, and hash the two child
roots. No leaf is duplicated and no padding leaf is inserted. The economy tree
and the winner tree are two instances of this one construction under different
labels, so neither holds a second opinion about the shape.
"""

from __future__ import annotations

import hashlib

from simulation.common.canonical import label_prefix


def digest(label: str, payload: bytes = b"") -> bytes:
    return hashlib.sha256(label_prefix(label) + payload).digest()


def split_point(count: int) -> int:
    """The largest power of two strictly less than `count`, for `count > 1`."""
    if count < 2:
        raise ValueError(f"split point is undefined for {count} leaves")
    return 1 << ((count - 1).bit_length() - 1)


def root(leaves: list[bytes], prefix: str) -> bytes:
    if not leaves:
        return digest(f"{prefix}-empty")
    if len(leaves) == 1:
        return digest(f"{prefix}-leaf", leaves[0])
    split = split_point(len(leaves))
    return digest(
        f"{prefix}-node",
        root(leaves[:split], prefix) + root(leaves[split:], prefix),
    )
