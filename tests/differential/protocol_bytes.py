"""Canonical byte and hash helpers for the independent Python model."""

from __future__ import annotations

import hashlib

MAX_U64 = (1 << 64) - 1
MAX_GENESIS_ACCOUNTS = 21_844
MAX_CANONICAL_BYTES = 1_048_576
MAX_BLOCK_INPUTS = 65_535


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def domain(label: str) -> bytes:
    encoded = label.encode("ascii")
    require(len(encoded) < 256, "domain label too long")
    return bytes([len(encoded)]) + encoded


def digest(label: str, payload: bytes = b"") -> bytes:
    return hashlib.sha256(domain(label) + payload).digest()


def merkle(leaves: list[bytes], kind: str) -> bytes:
    prefix = f"protocol-stack:v1:{kind}"
    if not leaves:
        return digest(f"{prefix}-empty")
    if len(leaves) == 1:
        return digest(f"{prefix}-leaf", leaves[0])
    split = 1 << ((len(leaves) - 1).bit_length() - 1)
    return digest(
        f"{prefix}-node",
        merkle(leaves[:split], kind) + merkle(leaves[split:], kind),
    )


def account_id(public_key: bytes) -> bytes:
    require(len(public_key) == 32, "public key size")
    return digest("protocol-stack:v1:account", b"\x01" + public_key)


def encode_receipt(
    transaction_id: bytes, result: int, fixed_fee: int
) -> bytes:
    return (
        b"PSRC"
        + (1).to_bytes(2, "big")
        + transaction_id
        + bytes([result])
        + (fixed_fee if result == 0 else 0).to_bytes(8, "big")
    )
