# ADR 0004: Protocol primitives v1

- Status: Accepted
- Date: 2026-07-23

## Context

M1 needs a single cross-platform byte meaning for accounts, signatures,
transactions, addresses, block commitments, and state roots. The suite must be
small enough to audit, supported by mature implementations, and explicitly
versioned so the network can migrate without reinterpreting old bytes.

The project does not need compatibility with an existing chain and must not
implement cryptographic primitives.

## Decision

Adopt the suite specified in
[`protocol-primitives-v1.md`](../specifications/protocol-primitives-v1.md):

- PureEdDSA Ed25519 signatures from RFC 8032;
- SHA-256 hashes with protocol-owned domain separation;
- a fixed-width, big-endian Protocol Stack Canonical Encoding;
- 32-byte hashed account identifiers and lowercase Bech32m text addresses;
- sorted account leaves and RFC 9162-style binary Merkle tree shape.

Use numeric algorithm and schema identifiers in every compatibility boundary.
ADR 0005 pins libsodium 1.0.22 and the reproducible build integration.

## Alternatives

### Signatures

| Candidate | Strengths | Why not version one |
| --- | --- | --- |
| Ed25519 | Deterministic, 32-byte public keys, 64-byte signatures, broad implementations, about 128-bit security | Selected |
| secp256k1 Schnorr | Excellent audited implementation and wallet ecosystem | Bitcoin-specific interoperability is not required; key encodings and ecosystem conventions add migration constraints |
| P-256 ECDSA | Standards and hardware-token support | Nonce handling and signature normalization create more consensus edge cases |
| ML-DSA or a hybrid | Standardized post-quantum security and available in OpenSSL 3.5 | Kilobyte-scale keys/signatures and newer operational experience are disproportionate for M1 |

The transaction version and algorithm identifier preserve a route to a
post-quantum or hybrid upgrade. Ed25519 is not claimed to resist a
cryptographically relevant quantum computer.

The adversarial prototype found that OpenSSL 3.0.20, including through its
Python `cryptography` binding, accepts an identity-key/identity-`R` forgery
allowed by cofactored RFC verification. Libsodium's verifier explicitly
rejects non-canonical and small-order public keys and `R` values. Therefore
OpenSSL's Ed25519 verifier is not an acceptable consensus adapter without
additional reviewed point validation.

### Hashes

| Candidate | Strengths | Why not version one |
| --- | --- | --- |
| SHA-256 | NIST standard, ubiquitous implementations and acceleration, 32-byte output, security aligned with Ed25519 | Selected |
| BLAKE2b-256 | Standardized, fast software, built-in personalization | Less uniform hardware and ecosystem support |
| SHA3-256 | NIST standard and no length-extension property | Generally slower on common M1 hardware and less ubiquitous acceleration |
| BLAKE3 | Very fast and parallel | Not an RFC or NIST standard and adds another young dependency choice |

SHA-256 length extension is not exposed because every use has a fixed schema
and an explicit domain prefix. No construction treats a raw digest as a
secret-key MAC.

### Canonical encoding

| Candidate | Strengths | Why not version one |
| --- | --- | --- |
| PSCE fixed layouts | Tiny decoder, one byte form, direct bounds, no runtime dependency | Selected |
| Deterministic CBOR | Standard data model and extensibility | The protocol must still restrict multiple legal representations and a larger decoder surface |
| SSZ | Precise serialization and Merkleization | Brings Ethereum-specific type machinery unnecessary for the fixed M1 kernel |
| Protocol Buffers | Excellent tooling and schema evolution | Official documentation states deterministic serialization is not canonical |

### Address and state tree

Bech32m was selected over hexadecimal and Base58Check for its checksum,
human-readable alphabet, single canonical lowercase form, and chain-specific
HRPs.

An ordered RFC 9162-style tree was selected over a 256-level sparse Merkle tree
and SSZ merkleization. It has a uniquely defined shape without duplicate or
padding leaves and is sufficient for M1 deterministic roots. Efficient
key-value proofs are deferred until storage and proof requirements are known.

## Security and compatibility effects

- Strict parsing and signature checks are consensus rules.
- Domain labels prevent values from one commitment role being reused in
  another.
- Chain IDs, nonces, and expiry heights bind transaction replay domains.
- Existing algorithm identifiers can never be reassigned.
- Any signature, hash, encoding, or state-tree replacement requires a new
  version and fixed migration vectors.
- Production dependency pinning and provider configuration are governed by
  ADR 0005. Supply values remain a separate decision.

## Evidence

Primary references:

- [RFC 8032: EdDSA](https://www.rfc-editor.org/rfc/rfc8032.html)
- [FIPS 186-5: Digital Signature Standard](https://csrc.nist.gov/pubs/fips/186-5/final)
- [FIPS 180-4: Secure Hash Standard](https://csrc.nist.gov/pubs/fips/180-4/upd1/final)
- [FIPS 204: ML-DSA](https://csrc.nist.gov/pubs/fips/204/final)
- [BIP 350: Bech32m](https://github.com/bitcoin/bips/blob/master/bip-0350.mediawiki)
- [RFC 8949: CBOR](https://www.rfc-editor.org/rfc/rfc8949.html)
- [Protocol Buffers canonicalization warning](https://protobuf.dev/programming-guides/serialization-not-canonical/)
- [Ethereum SimpleSerialize](https://ethereum.github.io/consensus-specs/ssz/simple-serialize/)
- [RFC 9162 Merkle tree construction](https://www.rfc-editor.org/rfc/rfc9162.html)
- [OpenSSL Ed25519 provider documentation](https://docs.openssl.org/3.0/man7/EVP_SIGNATURE-ED25519/)
- [OpenSSL release roadmap](https://openssl-library.org/roadmap/index.html)
- [Libsodium public-key signature documentation](https://doc.libsodium.org/public-key_cryptography/public-key_signatures)
- [Libsodium strict Ed25519 verification source](https://github.com/jedisct1/libsodium/blob/master/src/libsodium/crypto_sign/ed25519/ref10/open.c)

The accepted evidence is the normative vector file and passing C++20 and
independent Python harnesses. These harnesses exercise only primitives; they
do not implement ledger transitions.

No fuzz target is included in this research slice because it introduces no
production decoder or untrusted-byte entry point. The first PSCE decoder change
must add a bounded fuzz target before it can be accepted.
