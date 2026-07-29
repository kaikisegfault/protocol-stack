# Consensus application contract v1

Status: Accepted for M1

This document is normative for the version-one boundary between an ordering
engine and the persistent protocol application. It does not change the
canonical genesis, transaction, execution, receipt, block, or state-root rules
in `protocol-primitives-v1.md` and `ledger-transition-v1.md`.

This is an adapter-only compatibility contract. The ordering adapter supplies a
height and ordered raw transaction bytes. The C++ application remains the only
authority for admission, execution, receipts, application hashes, and durable
state.

## Invariants

The boundary preserves all version-one ledger invariants:

1. there is exactly one protocol-native asset and total supply is conserved;
2. transaction signatures, chain binding, nonces, and ordered execution retain
   their specified replay protection;
3. the adapter cannot create a transaction, receipt, account write, fee, state
   root, or block result;
4. adapter metadata cannot enter canonical state;
5. failed admission and execution retain their specified atomicity;
6. no application state is durable before Commit;
7. Commit does not report success before the complete SQLite block transaction
   is durable;
8. one decided height is applied at most once;
9. restart exposes only a fully validated old or new durable head;
10. replacing the consensus adapter does not change canonical ledger bytes.

Proposer identity, block hash, vote data, timestamps, wall-clock values,
validator metadata, RPC metadata, connection order, and thread scheduling are
not application transition inputs.

## Deployment identity

The C++ application is configured with:

- an absolute SQLite database path;
- the exact canonical genesis byte file;
- an absolute local Unix-socket path.

Before listening, it loads and validates canonical genesis, derives the
32-byte protocol chain ID, and exclusively creates or opens the configured
SQLite ledger. A new database starts at height zero. An existing database must
pass the complete `SQLiteLedger::open` validation and recovery path.

The CometBFT genesis values are:

- `chain_id`: ASCII `ps-` followed by the RFC 4648 URL-safe base64 encoding of
  the derived 32-byte protocol chain ID, with no padding; this is exactly 46
  characters and preserves all 256 bits within CometBFT's 50-character limit;
- `initial_height`: decimal `1`;
- `app_hash`: the 64 uppercase hexadecimal characters of the version-one
  height-zero state root;
- `app_state`: the exact UTF-8 JSON string bytes `"protocol-stack-v1"`,
  including the two quote bytes.

The node launcher derives all four values from the same validated canonical
genesis and refuses an existing CometBFT genesis file that differs. ABCI
InitChain does not carry the configured genesis application hash. The Go
bridge therefore enforces the chain string's exact prefix, length, URL-safe
alphabet, absent padding, and canonical re-encoding, then passes its decoded
bytes to C++; C++ compares those bytes, the initial height, and the exact
application-state bytes, then returns its independently computed height-zero
root. Repeated initialization before the first committed block is idempotent
and performs no state write. Initialization after a nonzero durable height is
a sequence failure.

For the M1 four-validator network, the CometBFT genesis additionally contains
exactly four validators:

- node indices are the integers `0` through `3`;
- every validator has voting power `10`;
- validator entries appear in ascending node-index order;
- each entry uses the public key from that node's retained private-validator
  key;
- all four homes contain byte-identical genesis files.

Validator keys and node keys are generated once using the pinned CometBFT
implementation, stored only in their owning home with owner-only permissions,
and retained across restart. Repeated initialization loads and validates all
eight keys before accepting the existing common genesis. Missing, duplicated,
inconsistent, or replaced key material, a different validator order or power,
or any other genesis difference is fatal and is never repaired in place.

## M1 four-validator local topology

Every validator is an independent replica with its own:

- CometBFT home, block store, node key, and private-validator state;
- stateless Go ABCI bridge;
- C++ application process and absolute Unix-socket path;
- SQLite ledger database opened against the same canonical genesis bytes.

Application sockets are ephemeral deployment state. By default their
owner-only directory is a deterministic, short path below the platform
temporary directory, keyed by the absolute persistent devnet root; an operator
may instead provide another absolute short-lived directory. The complete
socket path must fit the platform Unix-domain address limit. Homes, databases,
keys, and logs remain under the persistent root, and no socket path enters
canonical application state.

The four legacy CometBFT P2P nodes form a complete loopback-only persistent-peer
mesh. For node `i`, `persistent_peers` contains the other three entries in
ascending node-index order as
`node_id@127.0.0.1:p2p_port`. The configuration requires
`allow_duplicate_ip = true`, `addr_book_strict = false`, `pex = false`, and
`p2p.libp2p.enabled = false`. `create_empty_blocks = false` suppresses
unnecessary proposals, but CometBFT may still commit an empty block after an
application-hash change. Because canonical state commits its height, every
such block changes the application root; operational checks therefore use the
observed committed height and independently replay any intervening empty
blocks rather than assuming transfers land at fixed heights.

With default base P2P port `27656`, node `i` uses:

```text
p2p  = 27656 + (10 * i)
rpc  = p2p + 1
abci = p2p + 2
```

An operator-selected base port is valid only if all twelve derived ports are
distinct, within `1..65535`, and bound to `127.0.0.1`. The base-port choice,
peer ordering, validator identities, and all connection metadata are
deployment configuration, not application transition inputs.

One foreground supervisor exact-validates or creates the complete topology
before starting any child. It starts and readiness-checks all four
applications, then all four bridges, then all four CometBFT nodes. An
unexpected child exit is fatal and triggers bounded teardown of the remaining
children. SIGINT and SIGTERM perform orderly bounded teardown in the reverse
phase order. The supervisor does not daemonize, write a detached process ID,
or report readiness while a replica is unavailable. Application and bridge
endpoint phases each have a 20-second bound; complete network convergence has
a 90-second bound so sanitizer instrumentation remains inside the same tested
lifecycle without making readiness unbounded.

Network health requires all of the following at one observation point:

- all four RPC `/health` requests succeed;
- every node reports that it is no longer catching up;
- all nodes report the same chain ID, block height, block-header application
  hash, ABCI Info height, and current application root;
- every node reports direct connections to the other three node IDs;
- every node reports the exact four-validator equal-power set;
- every application root is exactly 32 bytes.

A transaction operation submits caller-supplied exact raw transaction bytes to
one selected validator through `broadcast_tx_commit`. It reports the committed
height and exact CheckTx, FinalizeBlock, and receipt fields without signing,
rewriting, or interpreting canonical transaction bytes.

Stop preserves all four homes and databases. Restart repeats strict
initialization, starts the same topology, and requires a converged health
observation at or after the previously durable height before another
transaction is accepted. Orderly stop removes all application sockets and
their ephemeral directory. While running, all four ABCI Info heads must
converge to the same height and root. The hosted restart integration
independently replays any intervening empty blocks, then opens every stopped
ledger through an independent C++ application process and requires all four
durable heads to match before restart and after the continued transfer.

## Application lifecycle

The C++ process owns one live `SQLiteLedger` and, at most, one staged block.
The durable head contains a height and 32-byte state root. A staged block
contains its height, exact ordered raw inputs, raw-aligned application results,
candidate `BlockCommit`, and candidate ledger head.

All application operations are serialized. The Go bridge may serve CometBFT's
separate ABCI connections, but exactly one request may cross the local
application boundary at a time. Read-only admission is serialized with
Finalize and Commit so no response observes a partially changed lifecycle.

### Info

Info returns:

- application data: ASCII `protocol-stack`;
- application version: ASCII `1.0.0`;
- application protocol version: unsigned integer `1`;
- the last durable block height;
- the exact 32-byte durable state root as the last application hash.

The Go bridge requires the request's ABCI version to be exactly `2.0.0`.
An incompatible request is fatal rather than a downgraded response.

Info never exposes a staged candidate. After a process restart it opens and
validates SQLite before returning the old or new durable head. This is the
authoritative recovery handshake with the ordering engine.
The bridge cannot represent an application height above signed 64-bit maximum
and fails closed if one is ever observed.

CometBFT exposes this current durable result through `/abci_info`. Its
`/status` `latest_app_hash` has different, historical meaning: block header
height `H` contains the application hash produced after height `H - 1`.
Therefore the first block header contains the configured height-zero root,
while Info after committing height one contains the resulting height-one root.
Both views must be checked independently; neither value is recomputed by the
adapter.

### Check transaction

CheckTx invokes only the four ordered admission operations in
`ledger-transition-v1.md`: exact decoding, chain comparison, sender derivation,
and strict signature verification. It performs no execution-state read,
reservation, nonce prediction, fee check, or write.

The raw CheckTx byte string is limited to 1,048,576 bytes before allocation or
admission. A larger request is an adapter request failure, not a transaction
admission result.

The response mapping is:

| Admission outcome | ABCI code | Codespace |
| --- | ---: | --- |
| admitted | `0` | empty |
| malformed transaction | `1` | `protocol-stack-v1` |
| wrong chain | `2` | `protocol-stack-v1` |
| invalid signature | `3` | `protocol-stack-v1` |

Data, log, info, and events are empty. Gas wanted and gas used are zero. New
and recheck requests have identical application meaning.

A code-zero CheckTx response means only that the signed bytes pass admission.
FinalizeBlock remains authoritative for nonce, balance, expiry, fee, ordering,
and every other state-dependent result.

### Prepare proposal

Given the adapter's ordered candidate list and nonnegative `max_tx_bytes`,
PrepareProposal returns the longest exact prefix for which:

- the raw count is at most 65,535;
- each raw input is at most 1,048,576 bytes;
- the sum of raw input lengths is at most both `max_tx_bytes` and 16,777,216.

Selection stops before the first input or sum that would violate a bound.
Bytes are neither decoded nor reordered. A negative `max_tx_bytes`, an
unrepresentable sum, or a malformed list container is a request failure.
Proposal selection is not canonical ledger state.

### Process proposal

ProcessProposal deterministically accepts if and only if:

- no staged block exists;
- the proposed height is the durable height plus one without overflow;
- the proposed height is at most 9,223,372,036,854,775,807;
- the raw count is at most 65,535;
- every input length is at most 1,048,576 bytes;
- the checked sum of input lengths is at most 16,777,216 bytes.

It does not decode or execute transactions. Malformed, wrong-chain, invalidly
signed, or state-invalid transaction bytes do not reject a structurally
bounded proposal because FinalizeBlock has deterministic result rules for
them.

### Finalize block

FinalizeBlock accepts only the next durable height and a structurally bounded
ordered raw list. It constructs an independent in-memory ledger from the owned
durable head and calls the unchanged version-one ordered block transition.
It does not open a SQLite write transaction and does not modify the durable
ledger.

For every raw input, in the same position, it returns exactly one application
result:

| Kernel outcome | ABCI code | Data |
| --- | ---: | --- |
| admitted and execution success | `0` | exact 47-byte receipt |
| malformed transaction | `1` | empty |
| wrong chain | `2` | empty |
| invalid signature | `3` | empty |
| admitted, `ZERO_AMOUNT` | `257` | exact 47-byte receipt |
| admitted, `FEE_LIMIT_TOO_LOW` | `258` | exact 47-byte receipt |
| admitted, `EXPIRED` | `259` | exact 47-byte receipt |
| admitted, `SENDER_NOT_FOUND` | `260` | exact 47-byte receipt |
| admitted, `NONCE_EXHAUSTED` | `261` | exact 47-byte receipt |
| admitted, `NONCE_MISMATCH` | `262` | exact 47-byte receipt |
| admitted, `DEBIT_OVERFLOW` | `263` | exact 47-byte receipt |
| admitted, `INSUFFICIENT_BALANCE` | `264` | exact 47-byte receipt |

Codes `257` through `264` are `256 +` the one-byte canonical transfer result.
This keeps admission codes distinct without changing receipt bytes.

Code zero uses an empty codespace. Every nonzero code uses
`protocol-stack-v1`. Log, info, events, gas wanted, and gas used are empty or
zero for every result. An admitted result always contains its exact canonical
receipt, including failures; an admission failure never contains a receipt.

The response application hash is the exact 32-byte resulting state root.
Validator updates, consensus-parameter updates, and events are empty. The next
block begins according to the pinned CometBFT configuration; M1 sets
`timeout_commit = "3s"` and `skip_timeout_commit = false`. Timing is not an
application response or canonical ledger state.

An internal block failure, invalid next height, count violation, length
violation, arithmetic failure, or inability to construct the candidate is a
fatal application error. It is never converted to a transaction result or
partial block.

After a successful response, the application retains the exact stage. A
byte-identical repeated FinalizeBlock request returns the byte-identical staged
response. Any different FinalizeBlock or proposal request while a stage exists
is a sequence failure.

### Commit

Commit requires one staged block. It calls `SQLiteLedger::apply_block` with the
exact staged height and raw byte sequence. The resulting durable `BlockCommit`
and owned head must exactly equal the staged preview before success is
returned.

SQLite commits the whole block before the application publishes its new owned
head. Only after successful publication does the application clear the stage
and return success. The ABCI Commit response contains no application hash in
ABCI `2.0.0`; its retain height is zero. The next Info response exposes the
durable height and root.

A kernel rejection, preview mismatch, storage error, close error, recovery
error, missing stage, or duplicate Commit is fatal. The application never
advances to another height after a terminal storage failure.

## Crash, disconnect, and replay

The ordering engine persists a decided block before calling FinalizeBlock.
FinalizeBlock itself is non-durable. These cases are required:

| Interruption point | Durable application head after restart |
| --- | --- |
| before or during FinalizeBlock | old head |
| after FinalizeBlock, before Commit | old head |
| before SQLite durable commit | old head |
| after SQLite durable commit, before response | new head |
| after Commit response | new head |

No staged state survives process termination. When the durable head is old,
the ordering engine may replay the same height and the application must
reproduce byte-identical transaction results and application hash. When the
durable head is new, Info reports it and the decided height is not applied
again.

SQLite's fail-closed ambiguous-commit recovery governs interruptions inside
Commit. The process reports neither a stale cached head nor a speculative
stage after a commit error. A bridge disconnect closes the affected request;
it does not cancel or roll back a durable C++ commit. CometBFT and the
application must be restarted and reconciled through Info after an ambiguous
transport failure.

A CometBFT block store behind the application's durable height, a different
chain ID or genesis, a different application hash at an equal height, or a
noncontiguous replay is operator-visible divergence and fails closed.

## Local application protocol

The local protocol is operational framing, not canonical ledger encoding. Its
version-one byte order is nevertheless exact so the untrusted decoder can be
bounded and independently tested.

### Primitive encoding

- integers are unsigned fixed-width big-endian unless named `i64`;
- `i64` is an eight-byte two's-complement big-endian integer;
- `bytes32` is exactly 32 bytes;
- `blob` is `length:u32 || bytes[length]`;
- `blob_list` is `count:u32 || blob[count]`;
- Boolean is one byte and accepts only `0` or `1`;
- no field has padding and no payload permits trailing bytes.

The maximum outer payload is 33,554,432 bytes. A decoder checks the fixed
header, payload length, field counts, individual lengths, checked sums, exact
payload consumption, and message-specific limits before allocation.

### Frame

Every frame is:

```text
magic[4] || protocol_version:u16 || direction:u8 || kind:u8 ||
request_id:u64 || payload_length:u32 || payload[payload_length]
```

The magic is ASCII `PSAP`, protocol version is `1`, and direction is `0` for a
request or `1` for a response. Request IDs are chosen by the bridge, are
nonzero, and responses echo the exact ID and kind. Only one request is
outstanding. EOF within a frame, unknown direction or kind, zero or reused
request ID, oversized length, and trailing bytes close the connection.

Every response payload begins with `status:u16 || message:blob`. Status zero
requires an empty message and is followed by the kind-specific success
payload. Nonzero status permits a UTF-8 diagnostic of at most 4,096 bytes and
no following bytes:

| Status | Meaning |
| ---: | --- |
| `1` | invalid request |
| `2` | unsupported operation or version |
| `3` | application sequence failure |
| `4` | kernel block failure |
| `5` | storage or recovery failure |
| `6` | internal application failure |

Diagnostics are operational only. The bridge converts every nonzero status to
an ABCI exception and does not place its text in a consensus result.

### Message kinds and payloads

| Kind | Name | Request success fields | Response success fields |
| ---: | --- | --- | --- |
| `1` | Info | empty | `app_version:u64 || height:u64 || root:bytes32` |
| `2` | InitChain | `chain_id:bytes32 || initial_height:u64 || app_state:blob` | `root:bytes32` |
| `3` | CheckTx | `tx:blob` | `code:u32` |
| `4` | PrepareProposal | `max_tx_bytes:i64 || txs:blob_list` | `txs:blob_list` |
| `5` | ProcessProposal | `height:u64 || txs:blob_list` | `accept:Boolean` |
| `6` | FinalizeBlock | `height:u64 || txs:blob_list` | `root:bytes32 || result_count:u32 || result[result_count]` |
| `7` | Commit | empty | `height:u64 || root:bytes32` |

Each FinalizeBlock result is
`code:u32 || data:blob`. Its count must equal the request raw count.
Code/data combinations must match the normative result table exactly.

The chain ID in InitChain is decoded from the exact `ps-` plus unpadded
base64url CometBFT string by the Go bridge. The app-state blob is passed without
normalization. The bridge rejects a negative ABCI height, an application
height above signed 64-bit maximum, a noncanonical chain string, and an ABCI
response that cannot be represented exactly by this table.

## Unsupported ABCI features

M1 configuration disables the application mempool, vote extensions, state
sync, application snapshots, validator changes, and consensus-parameter
changes.

CometBFT configuration requires `mempool.type = "flood"` and
`p2p.libp2p.enabled = false`. The bridge fails if CometBFT invokes InsertTx or
ReapTxs, proving the application-mempool mode was not silently enabled. Query
returns code `1`, codespace `protocol-stack-v1`, and no state data. ExtendVote
returns empty bytes, and VerifyVoteExtension accepts only empty bytes; the
genesis consensus parameters must keep vote extensions disabled. State-sync
listing returns no snapshots, and offer, load, or apply requests are rejected.
The application never exposes its engine-independent SQLite snapshots through
ABCI v1.

## Versioning and migration

Application protocol version `1`, local frame version `1`, codespace
`protocol-stack-v1`, and every result code in this document are frozen for the
M1 network.

A replacement bridge may change transport implementation but must reproduce
this lifecycle and result mapping. A change to ordered input meaning, result
codes, application hashes, commit atomicity, or replay behavior requires a new
accepted application-contract version and coordinated activation. A database
or canonical ledger migration follows the separate storage and transition
compatibility rules.

## Required evidence

Before this contract is considered implemented:

- fixed C++ vectors cover every admission and execution result mapping;
- preview output equals durable kernel output for populated, empty, and
  entirely unadmitted blocks;
- duplicate Finalize, conflicting Finalize, missing Commit, duplicate Commit,
  wrong height, overflow, maximum count, maximum length, and total-length
  boundaries are covered;
- process termination covers every row in the crash table and continued next
  commit after reopen;
- decoder tests cover truncation at every field, trailing bytes, unknown
  version/direction/kind/status, zero/reused IDs, hostile counts and lengths,
  invalid Boolean, arithmetic overflow, and disconnects;
- a bounded sanitizer-backed fuzzer exercises raw and structured frames with
  valid seeds;
- Go tests prove exact ABCI conversion, unsupported-method failure, concurrent
  connection serialization, and lossless byte transport;
- the pinned CometBFT binary starts from a clean home, commits a signed native
  transfer, exposes the current C++ application hash through Info and the
  prior-height hash through the latest block header, stops, restarts, and
  continues at the next durable height;
- the foreground devnet command initializes four distinct validators with one
  byte-identical genesis and exact full-mesh peers, starts twelve independent
  child processes, passes the normative health checks, commits an independently
  modelled signed transfer through one validator, exposes the same current C++
  height and root on all four replicas, stops, restarts the retained homes and
  databases, audits every stopped ledger directly through the C++ process, and
  continues with a second transfer at a later committed height;
- unit coverage rejects partial homes, duplicate keys or endpoints, invalid
  derived port ranges, changed topology or genesis, and repeated initialization
  that is not byte-identical;
- existing GCC, Clang, AddressSanitizer, UndefinedBehaviorSanitizer, primitive,
  ledger, differential, persistence, snapshot, archive, recovery, and fuzz
  gates remain green.
