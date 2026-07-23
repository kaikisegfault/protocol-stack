# Protocol primitives v1

Status: Accepted for M1

This document is normative for version-one primitive values, signatures,
canonical bytes, addresses, transaction commitments, and state roots. A node
must reject any byte sequence that this document does not assign exactly one
meaning.

## Selected suite

| Purpose | Version-one choice |
| --- | --- |
| Signature | PureEdDSA Ed25519 from RFC 8032 |
| Hash | SHA-256 from FIPS 180-4 |
| Binary encoding | Protocol Stack Canonical Encoding v1 (PSCE) |
| Account identifier | Domain-separated SHA-256 of scheme and public key |
| Text address | Lowercase Bech32m with a chain-configured HRP |
| Merkle construction | RFC 9162-style ordered binary trees |

The numeric algorithm identifier `0` is always invalid. Version one assigns
`1` to Ed25519, SHA-256, and the address payload format. Unknown identifiers
must be rejected rather than interpreted as a known algorithm.

## Primitive values

- `byte`: one unsigned octet.
- `u8`, `u16`, `u32`, and `u64`: unsigned integers of the stated width.
- All multi-byte integers use big-endian network byte order.
- `bytes<N>`: exactly `N` uninterpreted octets with no prefix.
- `bytes`: a `u32` byte length followed by exactly that many octets.
- `list<T>`: a `u32` item count followed by canonical encodings of the items.
- `bool`: one byte; only `0x00` and `0x01` are valid.
- `enum`: a `u8`; only values assigned by the containing schema are valid.

Floating point, platform-sized integers, native struct layout, maps, sets,
implicit defaults, null values, and text normalization are not canonical
types. Consensus schemas must fix every field order and bound every variable
field. A version-one decoder must reject:

- truncated values or trailing bytes;
- non-minimal, alternative, or out-of-order representations;
- unknown versions, message kinds, algorithms, enums, or flags;
- lengths above the schema bound before allocating memory;
- duplicate items where a schema requires unique values;
- lists that are not in their required canonical order.

The generic maximum canonical object size is 1,048,576 bytes and the generic
maximum list count is 65,535. A schema may impose a smaller bound.

## Domain separation

For an ASCII label `L`, define:

```text
D(L) = u8(byte_length(L)) || ascii(L)
```

Every version-one label in this specification is shorter than 256 bytes.
Labels are case-sensitive and include their version. A hash or signature
preimage must use the exact label shown; implementations must not substitute a
hash of a label or a NUL-terminated string.

## Keys and signatures

An Ed25519 public key is the exact 32-octet RFC 8032 compressed point encoding.
A signature is the exact 64-octet RFC 8032 `R || S` encoding. Private seeds are
32 octets but are never canonical ledger data.

Version-one transaction signatures use PureEdDSA Ed25519 over the entire
bounded signing message. They do not sign a caller-supplied digest and do not
use Ed25519ctx or Ed25519ph.

Verification must:

1. require an algorithm identifier of `1`, a 32-byte public key, and a 64-byte
   signature;
2. require canonical encodings of the public point and `R`;
3. require `S` to be less than the Ed25519 group order;
4. reject small-order public keys and small-order `R` values;
5. apply RFC 8032 verification to the exact signing message;
6. return one invalid-signature result without revealing parsing distinctions
   to a transaction submitter.

Cryptographic arithmetic must come from a pinned, reviewed provider. Version
one requires verification acceptance behavior matching libsodium's strict
Ed25519 verifier, including its canonical and small-order checks. Cryptographic
arithmetic must not be implemented in the ledger.

## Hashes and identifiers

`H(x)` is SHA-256 over the exact octets `x` and returns 32 octets.

```text
chain_id =
  H(D("protocol-stack:v1:chain-id") || canonical_genesis_without_chain_id)

account_id =
  H(D("protocol-stack:v1:account") || 0x01 || ed25519_public_key)
```

An account identifier, chain identifier, transaction identifier, block
identifier, and state root are each exactly 32 octets. They are distinct types
even though their widths match.

## Canonical transfer transaction

The only version-one public transaction kind is native transfer, kind `1`.
Its unsigned canonical encoding is exactly 136 bytes:

| Offset | Size | Field | Required value or range |
| ---: | ---: | --- | --- |
| 0 | 4 | magic | ASCII `PSTX` |
| 4 | 2 | schema version | `1` |
| 6 | 1 | transaction kind | `1` |
| 7 | 32 | chain ID | configured chain |
| 39 | 1 | signature scheme | `1` |
| 40 | 32 | sender public key | canonical Ed25519 key |
| 72 | 8 | nonce | `u64` |
| 80 | 32 | recipient account ID | 32 octets |
| 112 | 8 | amount | `u64`; semantic validation requires nonzero |
| 120 | 8 | fee limit | `u64` |
| 128 | 8 | valid-until height | `u64` |

The signing message is:

```text
D("protocol-stack:v1:tx-sign") || unsigned_transaction
```

The signed transaction is the 136-byte unsigned transaction followed by the
64-byte signature and is therefore exactly 200 bytes.

```text
transaction_id =
  H(D("protocol-stack:v1:tx-id") || signed_transaction)
```

The chain ID prevents cross-chain signature replay. The nonce and
valid-until height are signed; their stateful acceptance rules are specified
with the ledger transition. A failed decode or signature check performs no
state read or write and has no receipt or state-root effect.

## Application block header

The application-owned block header is exactly 146 bytes:

| Offset | Size | Field | Required value or range |
| ---: | ---: | --- | --- |
| 0 | 4 | magic | ASCII `PSBL` |
| 4 | 2 | schema version | `1` |
| 6 | 32 | chain ID | configured chain |
| 38 | 8 | height | `u64` |
| 46 | 32 | previous state root | 32 octets |
| 78 | 32 | ordered transaction root | 32 octets |
| 110 | 32 | resulting state root | 32 octets |
| 142 | 4 | transaction count | `u32` |

```text
block_id = H(D("protocol-stack:v1:block-id") || application_block_header)
```

Consensus-adapter metadata is not part of this header. A replaceable adapter
may commit additional data, but it cannot change these application bytes.

## Text addresses

The binary address payload is:

```text
0x01 || account_id
```

Encode the 33-byte payload from 8-bit groups to 5-bit groups with zero padding,
then encode it with the Bech32m checksum constant from BIP 350. The
human-readable prefix is a lowercase chain parameter. M1 devnet uses `psdev`.

A canonical text address:

- is entirely lowercase;
- has an HRP of 1 through 20 ASCII lowercase letters or digits;
- is at most 90 characters;
- has a valid Bech32m checksum;
- decodes with no nonzero padding;
- contains exactly version `1` and a 32-byte account identifier;
- matches the configured chain HRP.

Text form is an input and display format. Consensus state stores the 32-byte
account identifier, never the text address.

## Merkle commitments

Trees use the recursive shape from RFC 9162. For `n > 1`, split the ordered
leaves at the largest power of two strictly less than `n`, recursively hash
both sides, and hash the two child roots. No leaf is duplicated and no padding
leaf is inserted.

Account state entries are exactly:

```text
account_id[32] || balance:u64 || nonce:u64
```

Entries must be sorted by unsigned lexicographic account ID and must not
contain duplicates.

```text
accounts_tree({}) =
  H(D("protocol-stack:v1:state-empty"))

accounts_tree({entry}) =
  H(D("protocol-stack:v1:state-leaf") || entry)

accounts_tree(left || right) =
  H(D("protocol-stack:v1:state-node") || left_root || right_root)
```

The canonical state root is:

```text
H(
  D("protocol-stack:v1:state-root") ||
  u16(1) ||
  chain_id ||
  height:u64 ||
  supply_limit:u64 ||
  total_supply:u64 ||
  fee_pool_balance:u64 ||
  account_count:u64 ||
  accounts_tree_root
)
```

Before computing a state root, the caller must establish:

- `total_supply <= supply_limit`;
- checked addition of every balance and the fee pool equals total supply;
- account IDs are strictly increasing;
- all integer values fit `u64`.

The ordered transaction tree uses the same shape:

```text
tx_tree({})       = H(D("protocol-stack:v1:tx-empty"))
tx_tree({tx_id})  = H(D("protocol-stack:v1:tx-leaf") || tx_id)
tx_tree(L || R)   = H(D("protocol-stack:v1:tx-node") || L_root || R_root)
```

The transaction order is the committed execution order. Sorting transactions
before hashing is forbidden.

## Versioning and migration

Version-one bytes are immutable. A protocol upgrade may add new algorithm,
address-payload, transaction, or state-schema identifiers but must never
reinterpret an existing identifier.

A signature migration must define an overlap interval, explicit authorization
for key rotation, replay behavior across schemes, fixed cross-scheme vectors,
and removal conditions. Post-quantum or hybrid signatures are expected to use
a new transaction version because their key and signature sizes do not fit the
version-one layout.

There is no in-place migration of a state root. An upgrade block commits the
last old-schema root and the first new-schema root under an accepted migration
specification.

## Required vectors

`test-vectors/protocol-primitives-v1.txt` is normative and covers:

- the RFC 8032 empty-message Ed25519 vector;
- account-ID and Bech32m address derivation;
- unsigned and signed transaction bytes, signature, and transaction ID;
- empty and three-account state roots;
- empty and three-transaction Merkle roots;
- malformed length, checksum, signature, ordering, and trailing-byte rejection.

The C++ and Python harnesses must both reproduce every positive vector and
reject the negative cases before a version-one implementation is accepted.
