# ADR 0072: The wire refuses an oversized block before the application does

- Status: Accepted
- Date: 2026-09-12
- Bounds: [ADR 0068](0068-the-version-eight-application-layer.md), [ADR 0069](0069-the-version-eight-node-process-and-adapter.md)
- Relates to: `docs/project/first-goal.md` requirement 13

## Context

M3.14c set out to make a running application produce the third of
`ledger-transition-v1`'s refusal classes: the one that rejects a **whole
proposed block** and restores the pre-block state. The plan named three subjects
and one of them was the resource bound — `ApplicationV8::finalize_block` refuses
a block past `within_block_bounds` with `invalid_request`, and
`process_proposal` votes against one.

**From outside the process that guard cannot be reached, and the reason is
layering rather than a defect.** `protocol-application-v8` is spoken to over one
private Unix socket. Every frame is decoded by `decode_request_frame` before any
application sees it, and `read_transactions` enforces the same three figures the
application holds:

| bound | wire (`wire_v1.cpp`) | application (`application_v8.cpp`) |
| --- | --- | --- |
| inputs per block | `count > kMaximumBlockInputs` → `resource_limit` | `size() > kMaximumBlockInputsV8` |
| octets per transaction | `blob(kMaximumTransactionBytes)` → `resource_limit` | `> kMaximumTransactionBytes` |
| octets per block | `> kMaximumBlockBytes - total` → `resource_limit` | `> kMaximumBlockBytes - total` |

`kMaximumBlockInputsV8` *is* `protocol::v8::kMaxRawInputs`, and both are 65,535,
which is also the kernel's own `kMaxRawInputs` check at the top of
`execute_block`. So the same figure is enforced at three layers, and a peer only
ever meets the first.

**A wire refusal is not a refusal.** `serve_with` answers a `WireError` by
returning `protocol_failure`, and `main_v8` treats that as a peer that spoke
nonsense: the connection is dropped and the serve loop continues. The peer
receives no status at all, and the application — which was never handed the
request — does not latch terminal. That is a materially different event from
`invalid_request`, and a test that accepted either would not notice the two
swapping places.

## Decision

**All three bounds stay at all three layers, and the duplication is deliberate.**

Each layer bounds what it is responsible for. The wire bounds what a peer may
make this process *allocate* before anything is parsed. The application bounds
what it will *stage* against a head, and is reachable by an in-process caller —
`tests/application/application_v8_test.cpp` exercises it through
`process_proposal` with `kMaximumBlockInputsV8 + 1` inputs. The kernel bounds
what it will *execute*, and is the only one of the three that is part of the
consensus contract; the other two are this node's, and another node's adapter
may choose different ones without changing a single accepted state.

**The distinction is checked rather than described.**
`check_the_wire_refuses_first` in
`tests/integration/driven_application_v8_test.py` hands a running node a block
one input past the input bound and a block one octet past the transaction bound,
requires each to arrive as a dropped connection rather than as a status, and
then requires the same process to answer the next connection at the same head
with an application that never latched.

## Consequences

- A future session that expects `invalid_request` for an oversized block over
  the socket will find a closed connection instead. That is correct, and this
  ADR is where it is written down.
- The third refusal class of `ledger-transition-v1` is **not** reachable through
  the socket against a healthy store. The reachable whole-block refusals are the
  application's own sequencing and identity guards — a height that is not
  `h + 1`, a height past `kMaximumAdapterHeight`, a second block at a staged
  height, a commit with nothing staged, and an `init_chain` naming a foreign
  chain, initial height, or app state. Those are what M3.14c exercises, and each
  latches the node terminal and writes nothing.
- Deleting the application's copy of the three bounds would pass every test that
  drives it over the wire, and would fail `application_v8_test.cpp`. Do not
  delete it. `ApplicationV8` is a class with a public header, and the Unix
  server takes one by reference rather than owning the only way to reach it, so
  a caller that holds one directly — every C++ test here does — would otherwise
  stage a block nothing had bounded.
- Nothing here is consensus-visible. The kernel's `kMaxRawInputs` is the
  contract; the two bounds in front of it are node policy that happens to agree
  with it.
