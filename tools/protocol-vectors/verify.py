#!/usr/bin/env python3

from __future__ import annotations

import ctypes
import ctypes.util
import os
import sys
from pathlib import Path

from vector_common import (
    bech32m,
    decode_address,
    digest,
    domain,
    load_values,
    merkle,
    require,
    state_root,
    transfer,
    valid_signed_transaction_shape,
)


class Sodium:
    def __init__(self) -> None:
        library_name = os.environ.get(
            "PROTOCOL_STACK_LIBSODIUM"
        ) or ctypes.util.find_library("sodium")
        require(library_name is not None, "libsodium runtime not found")
        self.library = ctypes.CDLL(library_name)
        self.library.sodium_init.restype = ctypes.c_int
        require(self.library.sodium_init() >= 0, "libsodium init")
        self.library.sodium_version_string.restype = ctypes.c_char_p
        self.library.crypto_sign_seed_keypair.argtypes = (
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
        )
        self.library.crypto_sign_seed_keypair.restype = ctypes.c_int
        self.library.crypto_sign_detached.argtypes = (
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_ulonglong),
            ctypes.c_void_p,
            ctypes.c_ulonglong,
            ctypes.c_void_p,
        )
        self.library.crypto_sign_detached.restype = ctypes.c_int
        self.library.crypto_sign_verify_detached.argtypes = (
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_ulonglong,
            ctypes.c_void_p,
        )
        self.library.crypto_sign_verify_detached.restype = ctypes.c_int

    def public_key(self, seed: bytes) -> bytes:
        require(len(seed) == 32, "wrong Ed25519 seed size")
        public_key = ctypes.create_string_buffer(32)
        secret_key = ctypes.create_string_buffer(64)
        require(
            self.library.crypto_sign_seed_keypair(
                public_key, secret_key, seed
            )
            == 0,
            "libsodium key derivation failed",
        )
        return public_key.raw

    def sign(self, seed: bytes, message: bytes) -> bytes:
        require(len(seed) == 32, "wrong Ed25519 seed size")
        public_key = ctypes.create_string_buffer(32)
        secret_key = ctypes.create_string_buffer(64)
        require(
            self.library.crypto_sign_seed_keypair(
                public_key, secret_key, seed
            )
            == 0,
            "libsodium key derivation failed",
        )
        signature = ctypes.create_string_buffer(64)
        signature_size = ctypes.c_ulonglong()
        require(
            self.library.crypto_sign_detached(
                signature,
                ctypes.byref(signature_size),
                message,
                len(message),
                secret_key,
            )
            == 0,
            "libsodium signing failed",
        )
        require(signature_size.value == 64, "wrong signature size")
        return signature.raw

    def verify(
        self, public_key: bytes, message: bytes, signature: bytes
    ) -> bool:
        if len(public_key) != 32 or len(signature) != 64:
            return False
        return (
            self.library.crypto_sign_verify_detached(
                signature, message, len(message), public_key
            )
            == 0
        )

    def version(self) -> str:
        return self.library.sodium_version_string().decode("ascii")


def verify_crypto_and_address(
    values: dict[str, str], sodium: Sodium
) -> None:
    seed = bytes.fromhex(values["rfc8032.seed"])
    public_key = bytes.fromhex(values["rfc8032.public_key"])
    derived_public = sodium.public_key(seed)
    require(derived_public == public_key, "RFC public key mismatch")
    empty_signature = sodium.sign(seed, b"")
    require(
        empty_signature.hex() == values["rfc8032.empty_signature"],
        "RFC signature mismatch",
    )
    require(
        sodium.verify(public_key, b"", empty_signature),
        "RFC signature rejected",
    )

    account_id = digest("protocol-stack:v1:account", b"\x01" + public_key)
    require(account_id.hex() == values["account_id"], "account ID mismatch")
    address_payload = b"\x01" + account_id
    address = bech32m("psdev", address_payload)
    require(address == values["address"], "address mismatch")
    require(
        decode_address(address, "psdev") == address_payload,
        "address decode mismatch",
    )
    try:
        decode_address(values["invalid.address_checksum"], "psdev")
    except ValueError:
        pass
    else:
        raise ValueError("bad address checksum accepted")


def verify_transaction(values: dict[str, str], sodium: Sodium) -> None:
    seed = bytes.fromhex(values["rfc8032.seed"])
    public_key = bytes.fromhex(values["rfc8032.public_key"])
    unsigned_tx = transfer(values)
    require(unsigned_tx.hex() == values["unsigned_tx"], "transaction bytes")
    signing_message = domain("protocol-stack:v1:tx-sign") + unsigned_tx
    require(
        signing_message.hex() == values["signing_message"], "signing message"
    )
    signature = sodium.sign(seed, signing_message)
    require(signature.hex() == values["signature"], "transaction signature")
    require(
        sodium.verify(public_key, signing_message, signature),
        "strict transaction signature rejected",
    )
    for invalid in (
        bytes.fromhex(values["invalid.signature"]),
        bytes.fromhex(values["invalid.noncanonical_s_signature"]),
        signature[:-1],
    ):
        require(
            not sodium.verify(public_key, signing_message, invalid),
            "invalid signature accepted",
        )
    require(
        not sodium.verify(
            bytes.fromhex(values["invalid.small_order_public_key"]),
            signing_message,
            bytes.fromhex(values["invalid.small_order_signature"]),
        ),
        "small-order forgery accepted",
    )
    signed_tx = unsigned_tx + signature
    require(
        valid_signed_transaction_shape(signed_tx)
        and signed_tx.hex() == values["signed_tx"],
        "signed transaction",
    )
    trailing = signed_tx + bytes.fromhex(
        values["invalid.signed_tx_trailing_suffix"]
    )
    truncated = signed_tx[: -int(values["invalid.signed_tx_truncated_bytes"])]
    require(
        not valid_signed_transaction_shape(trailing),
        "trailing transaction byte accepted",
    )
    require(
        not valid_signed_transaction_shape(truncated),
        "truncated transaction accepted",
    )
    require(
        digest("protocol-stack:v1:tx-id", signed_tx).hex() == values["tx_id"],
        "transaction ID",
    )


def verify_trees(values: dict[str, str]) -> None:
    chain_id = bytes.fromhex(values["chain_id"])
    require(
        merkle([], "state").hex() == values["state.empty_tree_root"],
        "empty state tree",
    )
    require(
        state_root(chain_id, [], 0, 1000, 0, 0).hex()
        == values["state.empty_root"],
        "empty state root",
    )
    entries = [
        bytes.fromhex(values[f"state.account{index}"]) for index in range(3)
    ]
    require(
        merkle(entries, "state").hex() == values["state.accounts_tree_root"],
        "account tree",
    )
    require(
        state_root(chain_id, entries, 7, 1000, 640, 40).hex()
        == values["state.root"],
        "state root",
    )
    try:
        state_root(chain_id, entries, 7, 639, 640, 40)
    except ValueError:
        pass
    else:
        raise ValueError("supply limit violation accepted")
    try:
        state_root(
            chain_id, [entries[1], entries[0], entries[2]], 7, 1000, 640, 40
        )
    except ValueError:
        pass
    else:
        raise ValueError("unsorted accounts accepted")

    transaction_ids = [
        bytes.fromhex(values[f"tx.item{index}"]) for index in range(3)
    ]
    require(
        merkle([], "tx").hex() == values["tx.empty_root"],
        "empty transaction tree",
    )
    require(
        merkle(transaction_ids, "tx").hex() == values["tx.root"],
        "transaction tree",
    )


def main() -> int:
    require(len(sys.argv) == 2, "usage: verify.py VECTOR_FILE")
    values = load_values(Path(sys.argv[1]))
    sodium = Sodium()
    verify_crypto_and_address(values, sodium)
    verify_transaction(values, sodium)
    verify_trees(values)
    print(
        "Python protocol primitive vectors: passed "
        f"(libsodium {sodium.version()})"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, ValueError, OSError) as error:
        print(
            f"Python protocol primitive vectors: failed: {error}",
            file=sys.stderr,
        )
        raise SystemExit(1) from error
