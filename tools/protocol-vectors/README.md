# Protocol primitive vector harness

Run both cross-language checks from the repository root:

```sh
tools/protocol-vectors/verify.sh
```

This delegates to the repository's reproducible build and test entry point.
The exact tool and crypto dependency versions are documented in ADR 0005.

Current host prerequisites:

- Linux x86_64;
- Python 3.11 or newer with `venv`;
- GNU Make;
- a compiler selected by `PROTOCOL_STACK_PRESET`.

The C++ harness calls the pinned libsodium build for strict Ed25519
verification and SHA-256. The Python harness independently implements PSCE,
domain separation, Bech32m, and Merkle commitments with `hashlib`; it calls the
same pinned libsodium build for Ed25519 key derivation, signing, and strict
verification. It has no third-party Python runtime dependency.

The vectors include positive, mutation, length, checksum, non-canonical scalar,
small-order, supply-bound, conservation, and ordering cases. This is a
decision-prototype harness, not a production decoder or ledger.
