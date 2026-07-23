# Protocol primitive vector harness

Run both independent-language checks from the repository root:

```sh
tools/protocol-vectors/verify.sh
```

The script builds the C++20 harness in a temporary directory, runs it against
the normative vector file, and then runs the independent Python model. It
leaves no build artifacts in the repository.

Current prototype prerequisites:

- a C++20 compiler;
- the libsodium ABI 23 runtime;
- Python 3.11 or newer;
- the Python `cryptography` package.

The C++ harness calls libsodium for strict Ed25519 verification and SHA-256.
The Python harness independently implements PSCE, domain separation, Bech32m,
and Merkle commitments with `hashlib`; it uses Python `cryptography` for
positive RFC 8032 interoperability and libsodium for the consensus-required
strict verification decision.

The vectors include positive, mutation, length, checksum, non-canonical scalar,
small-order, supply-bound, conservation, and ordering cases. This is a
decision-prototype harness, not a production decoder or ledger. The M1 build
bootstrap must replace the runtime-ABI assumption with a pinned dependency and
compiler matrix.
