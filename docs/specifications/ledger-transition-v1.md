# Ledger transition v1

Status: Accepted for M1

This document is normative for version-one genesis state, native-asset
transfers, ordered block execution, receipts, and deterministic failure
behavior. It extends `protocol-primitives-v1.md`; definitions there govern
unless this document imposes a narrower rule.

## Devnet constants

All monetary values are unsigned `u64` atomic units. Consensus never parses or
stores decimal values.

| Parameter | Version-one devnet value |
| --- | ---: |
| Native unit display symbol | `PSU` |
| Atomic precision | 9 decimal places |
| Atomic units per display unit | 1,000,000,000 |
| Constitutional supply limit | 1,000,000,000,000,000,000 |
| Default genesis supply | 100,000,000,000,000,000 |
| Default bootstrap allocation count | 4 |
| Default allocation per bootstrap account | 25,000,000,000,000,000 |
| Fixed successful-transfer fee | 1,000 |
| Post-genesis issuance in M1 | none |

The symbol and decimal precision are display metadata; atomic values alone
enter canonical state. The four bootstrap account IDs are deployment inputs
and must be distinct. Their private keys are never genesis data.

M1 has no mint, burn, public asset-creation, account-deletion, or balance
adjustment transaction. The genesis supply therefore remains constant. The
supply limit is a constitutional upper bound, not permission to issue the
difference. Any later issuance requires a new accepted transition version and
native authorization rule.

## Canonical genesis

The version-one canonical genesis bytes are:

| Field | Encoding | Required value |
| --- | --- | --- |
| magic | `bytes<4>` | ASCII `PSGN` |
| schema version | `u16` | `1` |
| network ID | `u32` | `1` for M1 devnet |
| supply limit | `u64` | configured, nonzero |
| total supply | `u64` | configured, nonzero and at most the limit |
| fixed transfer fee | `u64` | configured, nonzero |
| initial fee pool | `u64` | configured |
| account count | `u32` | 1 through 21,844 |
| accounts | repeated 48-byte state entries | exactly `account count` entries |

Each account entry has the layout specified by ADR 0004:

```text
account_id[32] || balance:u64 || nonce:u64
```

Genesis account IDs must be strictly increasing, every genesis balance must be
nonzero, and every genesis nonce must be zero. Checked addition of all balances
and the initial fee pool must equal total supply. No trailing bytes are
allowed.

The generic maximum canonical-object size is 1,048,576 bytes. The genesis
prefix through `account count` is 46 bytes, so at most 21,844 48-byte entries
fit: `46 + 48 * 21,844 = 1,048,558`. A decoder must reject a declared count
above 21,844 before allocating account storage or deriving the expected byte
length. A count of 21,845 would require 1,048,606 bytes and is invalid.

```text
chain_id =
  H(D("protocol-stack:v1:chain-id") || canonical_genesis_bytes)
```

The initial state has height zero and its state root is computed with the
version-one state-root construction. The configured address HRP for network ID
`1` is `psdev`.

## State

A valid ledger state consists only of:

- the immutable chain ID, supply limit, total supply, and fixed transfer fee;
- a height;
- a fee-pool balance;
- a strictly ordered map of account ID to balance and nonce.

The state invariants are:

1. `total_supply <= supply_limit`;
2. checked addition of all account balances and the fee pool equals
   `total_supply`;
3. account IDs are unique and strictly ordered in commitments;
4. every value fits its canonical integer width;
5. height never decreases;
6. total supply and the fixed fee never change in M1.

Accounts are never implicitly deleted, including when their balance becomes
zero, because their nonce remains replay-protection state. A successful
transfer to an absent recipient creates it with nonce zero.

## Admission

Admission operates on raw transaction bytes before ledger state is read. Apply
these checks in order:

1. decode exactly one 200-byte signed version-one transfer with no trailing
   bytes;
2. require the configured chain ID;
3. derive the sender account ID from the encoded public key;
4. strictly verify the Ed25519 signature over the version-one signing message.

Step 1 classifies a wrong length, magic, schema version, transaction kind, or
signature-scheme identifier as `MALFORMED_TRANSACTION`. The fixed-width public
key and signature fields remain uninterpreted bytes during shape decoding.
At step 4, a non-canonical or small-order public key or `R`, a non-canonical
`S`, or a failed signature equation all return `INVALID_SIGNATURE`; these
cryptographic distinctions are never malformed-transaction results.

A failure returns the first applicable admission error:

| Code | Name |
| ---: | --- |
| 1 | `MALFORMED_TRANSACTION` |
| 2 | `WRONG_CHAIN` |
| 3 | `INVALID_SIGNATURE` |

Admission failures perform no state read or write, produce no application
receipt, and do not enter the application transaction root. Consensus or RPC
adapters may report the admission error outside canonical application state.

## Transfer execution

An admitted transaction executes against the current tentative block state.
Apply these checks in order and return the first failure:

| Result | Name | Condition |
| ---: | --- | --- |
| 0 | `SUCCESS` | all checks pass |
| 1 | `ZERO_AMOUNT` | amount is zero |
| 2 | `FEE_LIMIT_TOO_LOW` | fee limit is below the fixed fee |
| 3 | `EXPIRED` | valid-until height is below the executing block height |
| 4 | `SENDER_NOT_FOUND` | sender account does not exist |
| 5 | `NONCE_EXHAUSTED` | stored sender nonce is `u64` maximum |
| 6 | `NONCE_MISMATCH` | transaction nonce is not stored nonce plus one |
| 7 | `DEBIT_OVERFLOW` | amount plus fixed fee does not fit `u64` |
| 8 | `INSUFFICIENT_BALANCE` | sender balance is below amount plus fixed fee |

For distinct sender and recipient, a successful transition atomically:

1. subtracts `amount + fixed_fee` from the sender;
2. adds `amount` to the recipient, creating it with nonce zero if absent;
3. sets the sender nonce to the transaction nonce;
4. adds `fixed_fee` to the fee pool.

For a self-transfer, the sender must still cover `amount + fixed_fee`, but the
amount cancels atomically: subtract only the fixed fee and advance the nonce.

Recipient addition and fee-pool addition cannot overflow in a valid
conserved-supply state: each result is bounded by `total_supply`, which is a
`u64`. Implementations must nevertheless use checked arithmetic and treat a
violation as an internal invariant failure that invalidates the proposed
block, not as a transaction result.

Every non-success result performs no state write and charges no fee. It still
produces a receipt and enters the application transaction root because the
canonical signed transaction passed admission.

## Receipt

Each admitted transaction produces exactly one 47-byte receipt:

| Offset | Size | Field |
| ---: | ---: | --- |
| 0 | 4 | ASCII `PSRC` |
| 4 | 2 | receipt version `1` |
| 6 | 32 | transaction ID |
| 38 | 1 | transfer result code |
| 39 | 8 | fee charged; fixed fee on success, otherwise zero |

Unknown result codes and nonzero failed fees are invalid. Receipt order is the
admitted transaction order. Receipts are deterministic outputs but are not
part of the version-one state-root preimage.

## Ordered block execution

Given a valid state at height `h`, the only valid next block height is `h + 1`;
height overflow invalidates the block. Execute raw transaction inputs in their
provided order:

1. omit admission failures from application execution;
2. append each admitted transaction ID to the transaction commitment list;
3. execute it against the state produced by preceding successful
   transactions;
4. append its receipt, whether execution succeeds or fails;
5. after all inputs, set state height to the block height.

Compute the ordered transaction root from admitted transaction IDs, including
duplicates. The application block header's transaction count is the admitted
count. Its previous and resulting state roots use heights `h` and `h + 1`
respectively. An empty or entirely unadmitted block still advances height and
commits the empty transaction root.

The block transition is atomic: an internal invariant failure, height error,
or resource-bound violation rejects the whole proposed block and preserves the
pre-block state. Ordinary transaction results do not reject the block.

Version one permits at most 65,535 raw inputs and at most 65,535 admitted
transactions per block.

## Determinism and compatibility

Validation order, result numbers, receipt bytes, successful writes, and
failure atomicity are consensus rules. Implementations must not consult wall
clock, locale, filesystem order, host integer width, or adapter-specific
metadata.

Version-one genesis and transition meaning is immutable. A later fee policy,
issuance rule, receipt layout, transaction kind, or account lifecycle requires
a new schema or transition version with explicit activation and migration
vectors. A different genesis creates a different chain ID; it is not a
migration of this chain.

## Required vectors

`test-vectors/ledger-transition-v1.txt` is normative. The vector suite must
cover canonical genesis and chain ID, success, self-transfer, recipient
creation, replay, zero amount, low fee limit, expiry, absent sender, nonce
mismatch, debit overflow, insufficient balance, malformed bytes, invalid
signature, unknown transaction kinds, nonce exhaustion, ordered receipts,
transaction root, final state, header, and block ID. Independent C++20 and
Python harnesses must reproduce the vectors.
