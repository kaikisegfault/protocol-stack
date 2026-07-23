"""Minimal ctypes binding to the repository-pinned Ed25519 provider."""

from __future__ import annotations

import ctypes
import ctypes.util
import os

from protocol_bytes import require


class Sodium:
    """Expose only the Ed25519 operations used by the differential harness."""

    def __init__(self, library_name: str | None = None) -> None:
        selected = (
            library_name
            or os.environ.get("PROTOCOL_STACK_LIBSODIUM")
            or ctypes.util.find_library("sodium")
        )
        require(selected is not None, "libsodium runtime not found")
        self.library = ctypes.CDLL(selected)
        self.library.sodium_init.restype = ctypes.c_int
        self.library.sodium_version_string.restype = ctypes.c_char_p
        require(self.library.sodium_init() >= 0, "libsodium init failed")
        require(
            self.library.sodium_version_string().decode("ascii") == "1.0.22",
            "differential model requires pinned libsodium 1.0.22",
        )
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
        self._keypairs: dict[bytes, tuple[bytes, bytes]] = {}

    def keypair(self, seed: bytes) -> tuple[bytes, bytes]:
        require(len(seed) == 32, "Ed25519 seed size")
        cached = self._keypairs.get(seed)
        if cached is not None:
            return cached
        public_key = ctypes.create_string_buffer(32)
        secret_key = ctypes.create_string_buffer(64)
        require(
            self.library.crypto_sign_seed_keypair(
                public_key, secret_key, seed
            )
            == 0,
            "Ed25519 key derivation failed",
        )
        result = (public_key.raw, secret_key.raw)
        self._keypairs[seed] = result
        return result

    def sign(self, seed: bytes, message: bytes) -> bytes:
        _, secret_key = self.keypair(seed)
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
            == 0
            and signature_size.value == 64,
            "Ed25519 signing failed",
        )
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
