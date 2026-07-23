# Ledger kernel boundary

Status: M1 implementation architecture

The version-one ledger kernel is the application-state authority described by
`sovereign-core.md`. Its consensus-visible behavior is defined by
`../specifications/protocol-primitives-v1.md` and
`../specifications/ledger-transition-v1.md`; this document defines the C++
ownership, concurrency, and failure boundary around that behavior.

## Public ownership model

`load_genesis` validates canonical genesis bytes and, on success, returns a
`Ledger` that owns the resulting state. The input byte span is borrowed only
for the duration of the call. The ledger does not retain a pointer into caller
storage.

A `Ledger` exclusively owns its mutable `State`. Its `state()` accessor returns
a read-only borrowed view whose lifetime cannot exceed the ledger's lifetime.
The caller must not retain that view across a mutation such as
`apply_block`. `current_state_root()` computes a typed commitment to the
ledger's current state.

`apply_block` borrows each raw input span only while the call is active. A
successful call returns a `BlockCommit` that owns its transaction identifiers,
typed receipts, canonical encoded receipts, roots, application header bytes,
and block identifier. None of those outputs refer to the submitted input
buffers or to mutable ledger storage.

Copy construction creates an independent deterministic ledger fork. Move
construction transfers ownership. Assignment is intentionally unavailable so
an already-published ledger instance cannot silently change identity or
invalidate references through assignment.

## Operational state restoration

`restore_ledger` is the only public path for constructing a ledger from an
already-materialized live `State`. It accepts the state by value, so an lvalue
is independently copied and an rvalue transfers ownership. Expected parameters
and the expected root are borrowed only for the call and are never retained.

The factory validates in this fixed order:

1. the existing state-commitment validation must accept the materialized
   state;
2. every state parameter must equal a trusted `Parameters` value derived by
   successfully loading the canonical genesis;
3. the computed state root must equal the caller's expected root.

No ledger is constructed on failure. The three failures are returned as
`LedgerRestoreError::invalid_state`,
`LedgerRestoreError::immutable_parameters_mismatch`, and
`LedgerRestoreError::state_root_mismatch`, in that precedence order. The
factory applies live-state invariants rather than genesis-only constraints:
zero-balance accounts and nonzero account nonces remain valid.

The trusted parameter anchor is mandatory because the frozen version-one state
root does not include `fixed_fee`. Snapshot or database metadata must never
provide that anchor. An adapter derives it from caller-configured canonical
genesis bytes whose identity is trusted outside the database, exact-compares
the persisted genesis copy, and passes the independently derived value into the
factory. Restoration does not change commitment bytes or consensus-visible
transition behavior.

## Caller synchronization

The kernel contains no locks and does not schedule work. A caller must serialize
all operations that can mutate one `Ledger` and must prevent a mutation from
overlapping any read of that ledger or of a view borrowed from it. Independent
ledger instances, including copies used for proposal evaluation, may be
processed independently.

This keeps thread scheduling outside consensus meaning. A future node adapter
may use a mutex, a single-owner event loop, or another synchronization
mechanism, but it cannot change the order supplied to `apply_block`.

## Atomic block application

`apply_block` first validates the raw-input bound, the current state, and the
exact next height. It then copies the state and performs admission and
execution in input order against that tentative copy.

Ordinary admission failures and transfer-result failures are deterministic
per-input outcomes. An internal invariant failure, invalid height,
height exhaustion, invalid current state, or input-bound violation rejects the
whole block. In every such case, the owned pre-block state remains unchanged.

Only after all inputs, commitments, canonical receipt bytes, and canonical
application-header bytes have been produced successfully does the ledger
replace its state with the tentative result. The final state transfer uses a
non-throwing move, so there is one atomic commit point from the public API's
perspective. Operational exceptions before that point also leave the ledger
unchanged.

## Ordered result alignment

`BlockCommit::admissions` has exactly one element for every raw input, in raw
input order:

- an admission error identifies an omitted input;
- an empty optional identifies an admitted input.

`transaction_ids`, `receipts`, and `encoded_receipts` contain only admitted
inputs. All three have the same length and use admitted execution order,
including duplicates. Element `i` in each sequence describes the same
admitted transaction. An admission failure has no application receipt and no
transaction-root leaf.

This dual alignment lets an adapter report raw submission outcomes without
allowing adapter metadata to enter the canonical application commitment.

## Canonical byte authority

Typed results make in-process inspection explicit, but the kernel-produced
byte sequences are the persistence and interoperability authority:

- each `encoded_receipts` element is the exact canonical 47-byte receipt;
- `header` is the exact canonical 146-byte version-one application header;
- `block_id` is derived from that exact header.

Adapters should persist or transmit these bytes directly. They must not use
native struct layout, platform serialization, or independently reorder and
re-encode fields. If an adapter also stores typed projections, it must treat
the canonical bytes as the value against which those projections are checked.
Consensus-engine metadata may wrap these outputs but cannot alter them.

## Deterministic errors and operational failure

Protocol failures are closed typed values:

- `GenesisError` reports deterministic canonical-genesis rejection;
- `BlockError` reports deterministic whole-block rejection;
- `AdmissionError` is aligned with a raw input;
- `TransferResult` is committed through an admitted transaction's receipt.

Given the same prior state, height, parameters, and ordered bytes, every
correct node must produce the same typed values and canonical outputs.

Resource exhaustion and implementation-provider failure are not protocol
results. Memory-allocation exceptions and failures reported by the pinned
libsodium boundary can depend on local process state, so the kernel does not
translate them into `GenesisError`, `BlockError`, `AdmissionError`, or a
receipt result. They propagate as local operational failures while the public
ledger state remains unchanged.

A `LedgerRestoreError` is also not a consensus rejection. It reports that
locally supplied persistence state failed the operational reconstruction
boundary, and the adapter must fail closed rather than expose that state.

A future node adapter must catch such failures at its process boundary, record
diagnostics, fail closed, and stop or halt the affected proposal-processing
path. It must not invent a consensus-visible rejection code and continue as
though peers necessarily observed the same condition. No C++ exception may
cross a C ABI; an adapter exposing a C boundary must catch every exception
before returning through that boundary.

## Text address boundary

`encode_address` derives the canonical lowercase Bech32m text form of a typed
account identifier for a validated chain HRP. `decode_address` accepts only
that canonical form, requires the configured HRP and version-one 33-byte
payload, and rejects bad checksums, nonzero padding, mixed or uppercase text,
unknown payload versions, and noncanonical HRPs. Both operations return an
empty optional for invalid text or configuration rather than defining new
protocol error codes.

Text addresses are an input and display boundary only. The ledger, canonical
transactions, and commitments continue to store the typed 32-byte account
identifier. A caller must supply the HRP selected by its validated network
configuration; address text does not select or override a ledger chain ID.

## Tagged protocol values

The kernel represents `AccountId`, `ChainId`, `TransactionId`, `StateRoot`,
`TransactionRoot`, and `BlockId` as distinct tagged 32-byte types. Their
canonical widths and bytes are unchanged, but C++ does not implicitly convert
one role into another.

Conversions at hashing, encoding, and decoding boundaries are explicit. This
prevents equal-width values from being accidentally substituted in header,
state, transaction, or account operations while preserving the immutable
version-one wire format.
