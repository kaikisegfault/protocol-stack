# ADR 0073: The devnet supervisor accepts control requests on a Unix socket

- Status: Accepted
- Date: 2026-09-13
- Bounds: [ADR 0069](0069-the-version-eight-node-process-and-adapter.md), [ADR 0071](0071-a-devnet-cannot-reach-the-uptime-audit.md)
- Relates to: `docs/project/first-goal.md` requirement 13

## Context

Requirement 13 asks for adversarial four-node scenarios through restart and
recovery. Every scenario the repository could express stopped the **whole**
network or drove one replica while all four were down. The one shape left —
a replica that goes down while the others keep committing — was unreachable,
and three properties of `adapter/cometbft/internal/devnet` were why:

* `Run`'s final `select` treated **any** child exit as fatal and tore the
  network down, so a replica could not be stopped without stopping the network;
* `compareHeads` required **all four** replicas to report the same height and
  root with none catching up, so `devnet health` failed while any was down;
* `devnet transaction` waited for that same health after broadcasting, so
  nothing could be submitted while one was down either.

The scenario matters because **catching up is the only path in this repository
that makes a replica execute a block it never saw proposed and never voted on**.
Every other execution the fixtures produce is a block the replica participated
in agreeing. A deterministic kernel is supposed to reach the same state either
way, and that sentence was untested.

## Decision

The supervisor listens on a **Unix stream socket** at `control.sock` in the
socket root, accepting one request per connection: `stop <index>` or
`start <index>`, answered with `ok` or `error <message>`, one line each.

**The request is executed inline on the supervisor's main loop**, never in the
accept goroutine. This is the load-bearing choice. The readiness helpers a
restart needs — `awaitUnix`, `awaitTCP` — read from the same `events` channel
the watch loop reads, so a handler running concurrently would race the watch
loop for a child exit and one of them would silently lose it: either a crash
would go unnoticed or a readiness wait would hang. The accept goroutine
therefore parses a line and hands it over an unbuffered channel; the loop runs
the work and replies. There is exactly one reader of `events` at every moment.

**A child the supervisor stopped is marked, and the watch loop skips its exit.**
Every other exit is still fatal. The mark is written and read only on the main
loop, so it needs no synchronisation, and teardown reads it too — a stopped
child's `done` value has already been consumed and its log already closed, so
reaping it twice would block until the shutdown timeout.

**A replica is its three processes.** A stop takes the CometBFT node, the
bridge, and the application, in that order; a start brings them back in the
reverse one, waiting for the application socket and the ABCI port. An
application left holding its socket while its node and bridge are gone is a
state no operator produces, and the claim being tested is that a *machine* left
the network.

**Health takes a subset of replicas**, threaded through `CheckHealth`,
`WaitForHealth`, `Broadcast`, and the `-nodes` flag on `health` and
`transaction`. The subset is the set of replicas **expected to be running**,
not merely the set that happens to be asked, and that distinction is what keeps
the observation a real check rather than a relaxed one:

| comparison | narrows with the subset? | why |
| --- | --- | --- |
| heads, roots, catching-up | yes | only running replicas have a head to report |
| peer sets | yes | three running replicas must see exactly two peers each, so a stopped replica that is still gossiping fails |
| validator set | **no** | it comes from a genesis file four homes share, and stopping a process does not retire its validator |
| genesis files on disk | **no** | read from disk, not from an RPC; a devnet whose homes disagree is broken whatever is running |

`Broadcast` refuses a submission through a replica outside the subset, so a
caller's mistake is reported as its own error rather than as a connection
failure from a port nobody is listening on.

## Consequences

**Three of four validators is the whole margin.** Each holds ten voting power
and CometBFT commits on more than two thirds, so thirty of forty is exactly
enough. A second departure halts the chain rather than testing anything, and
the control channel makes that easy to ask for by accident.

**Blocks a departed replica missed cost a round.** Heights whose proposer is
down time out at `TimeoutPropose` and advance to the next round, so each
transaction submitted while a replica is away takes seconds longer than one
submitted to a whole network. The standing 90-second budgets absorb it.

**The socket is protected by its directory and nothing else.** The socket root
is created at mode 0700 and removed on exit, which is the same protection the
four application sockets already have: any process that can read that directory
can stop a replica. That is the right bound for a loopback development network
and it is not a bound for anything else. `protocol-cometbft-devnet` is a
development command; it is not part of a Founder Machine's runtime.

**The control socket's path is bounded explicitly.** `control.sock` is two
octets longer than the `node%d.sock` paths `nodeconfig` already checks against
the platform's 107-octet limit, so a devnet root deep enough to overflow is
refused at startup rather than surfacing much later as a confusing connection
error.

**A stopped replica is not a network partition**, and the fixtures say which is
meant rather than leaving prose beside them to imply otherwise. Blocking a
peer's P2P port needs privileges this harness does not have, and a two-two
split would commit nothing on either side. **A genuine partition therefore
remains untested**, and this ADR does not claim otherwise.

## Alternatives considered

**Signals rather than a socket.** `SIGUSR1` to the supervisor could stop a
replica, but a signal carries no index and no answer, so a second channel would
be needed to say which replica and whether it worked. A request-response socket
is one mechanism instead of two.

**A control handler in its own goroutine, synchronising on `events`.** Wrapping
the channel in a mutex or multiplexing it through a broker would work, and both
add a concurrency structure to a supervisor that currently has exactly one.
Running the work on the loop keeps the invariant statable in a sentence.

**Stopping only the CometBFT process.** Cheaper and faster to restart, but it
leaves the application and bridge running, which is not a machine leaving the
network. It would also have made the "still holds the head it left at" check
impossible, because the store would still be open.

**Letting health ignore unreachable replicas instead of naming a subset.** This
was rejected outright: an observation that silently tolerates a replica it
cannot reach would pass for a network that had genuinely lost one, which is the
opposite of what requirement 13 asks. Naming the subset makes every run state
what it expects.
