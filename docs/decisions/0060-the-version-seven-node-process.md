# ADR 0060: The version-seven node process, and a decoder that checks itself

- Status: Accepted
- Date: 2026-08-31

## Context

[ADR 0059](0059-the-version-seven-transport.md) put version seven's responses on
version one's wire and gave the socket a version-seven overload. What did not
exist was a **process**: `protocol-application` is version one's binary, so
nothing could be started, connected to, and shut down.

One obstacle sat in front of it. Version one's binary reads a genesis file and
hands the **bytes** to `create_sqlite_ledger`. `create_sqlite_ledger_v7` takes a
`v7::Genesis` **struct**, and version seven published `encode_genesis` with **no
inverse**, so a binary had nothing to turn a file into a genesis.

## Decision

### `decode_genesis` is defined as the encoder's inverse and checks itself

It reads the 110 canonical octets into a `Genesis` and then **re-encodes that
genesis and requires the result to equal the input octet for octet**. Only then
does it return.

**That is the whole validity rule and it is stated exactly once.** Version seven
already decides what a genesis may be — a nonzero supply limit, a zero total
supply, a zero initial fee pool, no accounts — inside `encode_genesis`, and a
decoder with its own copy of those four conditions would be a second opinion
about what a genesis *is*, to be kept in step by discipline. Re-encoding
delegates the question to the only code that answers it, and it catches more than
a restatement would: a field read at the wrong offset, a trailing octet, an
unrecognised schema version.

**The field order is the encoding's, not the struct's**, and that is exactly the
kind of mistake the round trip catches. `total_supply` is written *before*
`fixed_transfer_fee` while the struct declares them the other way round, so a
decoder reading in declaration order puts the fee where the supply belongs — and
a genesis with a nonzero total supply is one `encode_genesis` refuses to write.
The test uses a distinctive nonzero fee for that reason; a zero fee would hide it.

### The binary is version one's with three substitutions

`protocol-application-v7` reads the genesis file, decodes it, opens or creates
the store, makes the application, binds a private Unix socket, and serves in a
loop with a `signalfd` for `SIGINT` and `SIGTERM`. `--genesis-identity` prints
the chain identity and the height-zero application hash without touching a
database, which are the two figures an operator puts into a consensus engine's
configuration.

**Opening is attempted before creating.** A create over an existing path is
refused by the store, so asking to open first is what makes a restart the
ordinary case rather than a special one.

**The size check on the genesis file is an allocation bound, not a validity
rule.** A version-seven genesis is exactly `kGenesisPrefixBytes` octets, so
nothing larger is read into memory; what the file *means* is decided only by
`decode_genesis`. A probe that widened that bound to 4,096 octets passed, and it
was right to: it changed a bound and broke no rule.

**A peer that hangs up badly or speaks nonsense loses its connection and nothing
else.** The loop continues on `connection_failure` and `protocol_failure`, as
version one's does. The application's own terminal latch is what stops a node
that has contradicted itself, and it is deliberately not this loop's business.

## Evidence

`version-seven-headless-process` runs the built binary as a process and checks it
against `test-vectors/economy-transition-v7-execution.txt`, which knows nothing
about sockets or processes:

- `--genesis-identity` on the recorded `genesis.bytes` must print the recorded
  `genesis.chain_id`, and an application hash equal to the height-zero root read
  **out of the recorded `carried.block0.header`** — a block header commits to its
  previous state root, and at height 1 that is the genesis root, so the figure is
  a third source rather than a restatement.
- A genesis file that is short, or empty, is refused rather than becoming a
  chain.
- A first run creates its database, reports protocol version 7 at height 0 with
  the recorded genesis root, and refuses a premature `commit` with
  `sequence_failure` **in a well-formed response frame** rather than by breaking
  the connection.
- A second run **reopens** what the first created, accepts `init_chain` over the
  wire and answers the same root, and refuses rubbish as `malformed_transaction`.
- Both runs exit zero on `SIGTERM` and leave no socket behind, and the socket is
  mode 0600 while it exists.

Two probes are caught by the check that names them: a binary that always creates
rather than reopening fails the second run, and an identity mode that prints the
chain identity where the application hash belongs fails the recorded comparison.
A third — accepting version one's app state at `init_chain` — passed here and
**fails in the suite that owns that rule**, `version-seven-application`, which is
where it was checked rather than duplicated.

The decoder's own evidence is in `economy-transition-v7-cpp`: the round trip
field by field, the derived chain identity, a short file, a long file, a foreign
magic, an earlier schema version, and the four fields the encoder refuses —
each mutated in the *file* rather than in the struct, because a file is where
they come from.

## Consequences

- A version-seven node is a process that can be started, connected to, and shut
  down. The remaining piece before a running chain is the Go ABCI adapter.
- `protocol_application` gains no source; the binary is its own target.

## Owed, and recorded rather than implied

- **The Go ABCI adapter**, which must also answer the replay handshake ADR 0058
  records: the application refuses, terminally, a `finalize_block` at any height
  that is not `current + 1`, including one it has already committed.
- **The uptime schedule**, still `nullptr` at `execute_block`. A chain run
  through this process writes no cycle assignment and no seat accrues.
- **The socket pathname bound.** `sun_path` caps a pathname near 108 octets and
  nothing in the binary checks it; a bind failure is reported as "failed to
  create the private Unix socket" without naming the likely cause.
- **No fault injection through the process boundary.** The storage seams exist
  and nothing drives them from here.

## Alternatives considered

**Give the decoder its own copy of the validity rule.** Rejected: two statements
of what a genesis may be, kept in step by discipline, when re-encoding asks the
only code that decides.

**Read a bounded file and let the decoder refuse the size.** Rejected as the
*primary* bound — a genesis has exactly one length, so reading more than that is
never right — but it is the same thing in practice, which is why widening the
bound broke nothing.

**Extend `protocol-application` with a version flag.** Rejected: the two differ
in what a ledger *is*, not in a setting, and one binary would carry both stores,
both applications, and two genesis formats behind one argument.
