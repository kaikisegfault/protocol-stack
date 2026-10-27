# Current state

Last updated: 2026-10-28

This is the handoff. It says what is true now, and nothing else. How each slice
was delivered is in [`delivery-log.md`](delivery-log.md), newest first, and
the handoff as it stood before this rewrite is that log's final section.
`tools/verify_metadata.py` refuses this file above 600 lines. A slice rewrites
the sentences here that it makes false. Its narrative, its gate result, and
the alternatives it rejected go in its delivery record.

## Phase

**M4, Founder identity, seats, and authority, is the active milestone.** It
began when M3 closed on 2026-09-27. [`first-goal.md`](first-goal.md) states
its eleven requirements, and four are met.

| # | Requirement | Status |
| ---: | --- | --- |
| 1 | A test Founder's lifecycle on the four-validator devnet | Met 2026-09-27, M4.1 |
| 2 | A kind-4 and a kind-18 mint on a network | Met 2026-10-03, M4.2a to M4.2c |
| 3 | The per-machine attestation-key registry | Specified in `economy-transition-v10`, M4.3a, and revised per founder, M4.3f; executes in Python and in the C++ kernel, M4.3b to M4.3f; no network runs it |
| 4 | A deterministic test verifier as a replaceable component | Met 2026-10-09, M4.4, for version nine's proofs |
| 5 | Sensitive-action authorization with expiry and replay protection | Specified in `economy-transition-v10`, M4.3a; executes in Python and in the C++ kernel, M4.3b to M4.3e; no network runs it |
| 6 | Legacy succession mechanics | Open; the values are founder-reserved |
| 7 | The threat model for local HUB verification | Met 2026-10-09, M4.7; its review is owed |
| 8 | Storage bounds for every new entry | Open; due with each new entry |
| 9 | Cross-language vectors for every new transition | Open; due with each transition |
| 10 | Accepted ADRs for every new transition | Open; due with each transition |
| 11 | Hosted verification and a handoff naming M5's first slice | The closing act |

**Requirement 1's evidence** is `cometbft_founder_lifecycle_v9_test.py`. Alice
enrolls, buys and activates a seat, admits a signer, and funds a holding
escrow. Her HUB key revokes every signer she has, and after a restart it
recovers her. Eighteen blocks run on four replicas through two full restarts.
Another person's HUB key, and her own signer posing as the authority, are both
refused, so no wallet key alone rewrites an identity.

**Requirement 2's evidence** is `cometbft_seeded_mints_v9_test.py`. Four
replicas are seeded from one snapshot at height 86,400, which the Python model
reaches alone (ADRs 0096 and 0097). Alice's kind-18 mint issues 3.42 units and
her kind-4 mint 574.3, and every receipt and root is the model's. Its first
hosted run found a kernel defect: an unsigned wrap paid 51.3 units for any
kind-18 mint before window 31.
[ADR 0098](../decisions/0098-a-kind-18-mint-before-window-31-collects-what-was-earned.md)
repairs it inside version nine.

**Requirement 4's evidence** is `hub-test-verifier-v9` and its cross-check.
[ADR 0099](../decisions/0099-the-hub-verifier-is-one-interface-with-a-deterministic-test-implementation.md)
defines `protocol::hub::VerifierV9`. It takes a capture and the transaction a
person approves, and builds every message it signs itself. `TestVerifierV9`
derives the identity and the HUB key from one 32-octet secret, as a labelled
stand-in for a face. The version-nine kernel accepts its registration and
every approvable kind through admission and execution, with real Ed25519. The
Python model verifies every decision the command prints. Requirements 3 and 5
will rebind what it signs, and the network fixtures still sign by hand.

**Requirements 3 and 5 execute in both languages and are not met**, because no
network runs version ten yet.
[`economy-transition-v10`](../specifications/economy-transition-v10.md) and
[ADR 0102](../decisions/0102-economy-transition-v10-the-registry-and-single-use-approvals.md)
define them:

- a machine-key registry keyed by seat, filled by kind 23 under the build
  authority's attestation and the owner's HUB approval;
- registrations signed by an active machine, or by the launch key until 100
  machines are active;
- at most 1,000 registrations per window across all of one founder's
  machines, kept on a count per founder (entry kind 27);
- a registry step that records each machine's last met window;
- one approval message that signs the whole transaction, with a one-slot life.

The owner's answers in ADRs 0100, 0101, and 0106 fix every participant-facing
value. [ADR 0107](../decisions/0107-the-registration-count-is-the-founders.md)
records how the per-founder limit is kept: the count is the founder's, keyed by
the identity that owns the attesting seat, and the machine-key entry keeps none.
Invariant 8 bounds the founder counts by the seats.
**The independent Python model executes all of it** (M4.3b, M4.3c, and M4.3f).
`simulation/economy_transition_v10/` imports version nine and declares exactly
what it carries, revises, withdraws, and adds. Kinds 10 and 23 are its own;
every other kind runs on version nine's handlers, with a body approval verified
over the whole transaction. The prologue runs the registry step.

- `test-vectors/economy-transition-v10.txt` records 114 contract vectors.
- `test-vectors/economy-transition-v10-execution.txt` records 198 execution
  vectors, from a chain of blocks, from 101 machines of two founders driven
  through version nine's evidence harness, and from a five-height run
  contiguous from genesis for the layers that replay blocks. They show every refusal in order,
  the launch key retiring at 100 active machines and staying retired, and both
  of version nine's executed replays refused in both forms. One founder's
  1,000 registrations in a window are spread across two machines. The 1,001st
  is refused, including on a machine of theirs that attested nobody, while the
  other founder's machine still signs. A key one founder released and the other
  re-registered signs only for its new seat.
- Every value two sources can reach is agreed with an independent derivation
  that imports nothing from `simulation/`.

**The C++ kernel executes version ten, beside version nine's.**
`include/protocol/v10/economy.hpp`, `include/protocol/v10/ledger.hpp`, and 23
translation units under `src/v10/` compile beside version nine's kernel, under
[ADR 0104](../decisions/0104-the-version-ten-kernel-is-staged-beside-version-nine.md).
Everything version ten adds is in two of them, `economy_registry.cpp` for the
codec and `economy_registry_transitions.cpp` for execution.

- `economy-transition-v10-cpp` reproduces 106 of the 114 contract vectors. Its
  guard names the other eight: seven describe the Python package's own surface,
  and the eighth, what a genesis writes, the execution target consults.
- `economy-transition-v10-execution-cpp` reproduces all 198 execution vectors:
  the chain of blocks, the restart run, and the 101-machine population through
  `open_window`,
  the prologue alone at a window opening
  ([ADR 0105](../decisions/0105-the-kernel-runs-the-prologue-alone-for-the-evidence-harness.md)).
  Three targeted checks cover rules no vector reaches, each found by a
  mutation probe the vectors let pass.
- Every claim about what version ten carries is pinned to an accepted
  version-six to version-nine file, never to the version-nine kernel.

**A version-ten ledger can be written down and restored** (M4.3g,
[ADR 0108](../decisions/0108-the-version-ten-snapshot.md)). `snapshot_v10`
carries the build authority key as a sixth parameter and decodes the four
registry entries through the kernel's own decoders. A restore refuses a
retirement that one height proves wrong: absent while the head's own count
reached 100, present with fewer than 100 machines ever marked, or at a height no
registry step runs. Invariant 7 compares two heights, so this is the only guard
a seeded network has, because its replicas agree with each other.
`version-ten-snapshot` round-trips the chain, the population, and the span run
against their recorded final roots, and carries version eight's and version
nine's refusal sweeps for ADR 0104's deletion step.

**A version-ten ledger survives a restart** (M4.3h,
[ADR 0109](../decisions/0109-the-version-ten-owning-store.md)).
`SQLiteLedgerV10` is version nine's store with the namespace rebound, a
182-octet genesis column, a head column of at least 262 octets, and the marker
`PS10` at schema version 10. `version-ten-owning-store` replays the model's
five-height `restart.` run through a database reopened before every block, and
its fifth block's kind-23 registrations show the build authority key came back
from the genesis. `version-ten-store-recovery` carries the fault matrix.

**A version-ten chain can be driven through the application layer** (M4.3i,
[ADR 0110](../decisions/0110-the-version-ten-application-contract.md)).
[`consensus-application-v3`](../specifications/consensus-application-v3.md)
inherits version two by reference and states nine differences, among them
results 1 to 49 mapped to ABCI codes 257 to 305 and Info protocol version `10`.
The frame stays at version two, because no payload changes shape, and a
version-ten bridge must refuse an Info that does not say `10`. `ApplicationV10`,
`response_v10`, and `dispatcher_v10` are version nine's, rebound over
`SQLiteLedgerV10`, and a socket overload serves them. `version-ten-application`
and `version-ten-transport` replay the `restart.` run across a reopen before
every block, the fifth block's kind-23 registrations included. A registration
past its approval lifetime returns code `305` end to end.

**A version-ten node runs as a process** (M4.3j). `protocol-application-v10`
is version nine's node process rebound. It binds the platform real-time clock
(ADR 0085), opens `SQLiteLedgerV10`, and serves `ApplicationV10`, with the
identity, seed, and inspection modes over `snapshot_v10` heads.
`version-ten-headless-process` carries version nine's process suite: the real
clock, the clock-offset shim, Info's protocol version `10`, and version nine's
application state and genesis width refused. In `version-ten-seed`, four
Python-encoded model ledgers seed C++ stores through the snapshot's gates,
byte for byte. They are the restart run, the recorded chain, that chain at its
first outstanding challenge, and the cutoff population with the launch key
retired, and between them they carry all 23 writable entry kinds.
`tests/integration/version_ten_snapshot.py` is the encoder a seeded
version-ten network will start from.

The Go adapter and the network still run version nine.

**The model found a specification defect, repaired before anything implemented
it.** The registry step counted a mark of 0, which means never met, as meeting
window 0. So 100 keys registered in the first two windows retired the launch key
at height 57,600, before any machine had met a cycle.
[ADR 0103](../decisions/0103-the-registry-count-excludes-an-unmarked-machine.md)
excludes an unmarked machine from the count.

**Requirement 7's evidence** is
[`hub-verification-threat-model.md`](../architecture/hub-verification-threat-model.md).
It sets out what is protected, who attacks, and where the trust boundaries
are. It covers eleven threats, each with what stops it in version nine, what
the next contract version must add, and what review is owed. It also lists what
version nine already handles and the obligations of the next contract version.

## What works now

**One economy contract runs, and it runs on a network.** Version nine is
[`economy-transition-v9`](../specifications/economy-transition-v9.md) under
[`consensus-application-v2`](../specifications/consensus-application-v2.md).
The repository compiles it, the M1 version-one ledger, and version ten's kernel,
snapshot, owning store, application, transport, and node process staged beside
it (ADR 0104).
Every layer of version nine is built:

- the C++20 kernel, `include/protocol/v9/` and 21 translation units under
  `src/v9/`;
- `snapshot_v9` and the owning store `SQLiteLedgerV9`, which can also be
  seeded from a snapshot;
- `ApplicationV9`, the version-two frame `wire_v2`, and the node process
  `protocol-application-v9`. The process binds `CLOCK_REALTIME` in
  milliseconds, and only the proposal check reads it;
- the Go adapter: `ClientV9`, `bridge.LocalV9`, `protocol-cometbft-init`, and
  `protocol-cometbft-devnet`, which can launch above height zero from a seed;
- pinned CometBFT `v0.39.4`.

**What a version-nine chain executes.** Seventeen transaction kinds, of which
kind 6, `direct_issue`, is specified and refuses every sender:

- a HUB registration under the genesis verifier key, with the 1.71-unit entry
  airdrop;
- keyless holding escrows and revocable signers, one escrow per signer key;
- a security posture per escrow, which only a HUB signature relaxes;
- transfers, refused to an unregistered recipient;
- seat purchase and activation under the owner's HUB signature, tied to the
  identity, at most 1,000 per identity;
- an uptime audit of every in-scope seat each window, through challenges and
  disputes (kinds 20 and 21);
- a cycle assignment every 28,800 heights, the failed-cycle reallocation, the
  recovery pool, and the thirty-window accumulation cap;
- the node, referral, and verified-user mints (kinds 4, 5, and 18);
- the monthly unreferred pool, settled by calendar month from the block
  timestamp and minted with kind 22.

**The independent Python model agrees with the C++ kernel.** The model is
`simulation/economy_transition_v9/`. `economy-transition-v9.txt` holds 239
contract vectors and `economy-transition-v9-execution.txt` holds 162 execution
vectors. The kernel reproduces every one of both.
`economy-scenario-suite-v4` drives the model through every window of six
research seats' 731 cycles, and checks the exit audit's four claims at every
window.

**Eight network runs gate every full verification**, in `tools/verify.sh`:

- `cometbft_single_node_test.py` and `cometbft_four_validator_test.py`, the
  version-one devnet;
- `cometbft_version_nine_test.py`, one node, six blocks, and a restart;
- `cometbft_four_validator_v9_test.py`: transactions through all four nodes,
  two named refusals, two full restarts, a driven replica refusing a bad block,
  and a replica that leaves and catches up;
- `cometbft_skewed_replica_v9_test.py`, one replica's clock 120 seconds ahead,
  then behind, while the chain keeps committing;
- `cometbft_founder_lifecycle_v9_test.py`, requirement 1;
- `cometbft_seeded_launch_v9_test.py`, a launch from a seeded head and three
  refused wrong launches;
- `cometbft_seeded_mints_v9_test.py`, requirement 2.

Every version-nine run compares each receipt and root with the model. The
multi-replica runs then audit every store's durable height, stamp, and root
through an independent process.

**Older evidence is kept, not compiled.** The economy models and accepted
vector files of versions two to eight stay and pass, and version nine's
predecessor constructions are pinned to them. The research models stay too:
the seat sale, revenue routing, escrow payout, the economy simulators, and the
first three scenario suites. They are Python and execute no consensus.

**A test HUB verifier stands where the production one will.**
`protocol-hub-test-verifier-v9` prints the verifier key a genesis carries, a
whole signed registration, and the proof any HUB-approved transaction needs. It
reads no clock, file, or network, and no node links it.

**The `proceed`, `conclude`, and `status` workflows** reconstruct, deliver, and
report repository state. `proceed` runs a founder-decision gate before every
slice and reports its result.

## Founder direction

[`founder-constitution.md`](founder-constitution.md) is authoritative. As it
stands, the rules that shape M4's work are these.

- **HUB verification is mandatory for everyone** (ADR 0039). An identity is the
  person's HUB biometric data, never an address. Recovery is re-verifying, with
  no third party. Biometric confirmation is on by default for every financial
  transaction and every mint. Relaxing it needs a biometric approval and
  tightening it needs only a signer, so a stolen signer key cannot weaken it
  (ADR 0043).
- **Value sits in keyless holding escrows**, and an identity may hold any
  number. Signer keys are revocable, and each belongs to exactly one escrow
  (ADRs 0040 and 0043). A transfer to an unregistered recipient is refused.
- **A Founder Seat has no address.** It is tied to the owner's HUB identity, so
  it cannot be sold or transferred, and the old manager-address set and its
  limit of sixteen are superseded (ADR 0041). Legacy succession is the one path
  by which a seat's identity changes. One human holds at most 1,000 seats.
- **HUB verification runs locally on the founder's own Founder Machine**, as
  deterministic software in a sandbox. The local model monitors the process's
  integrity and never decides identity. Genesis's single verifier key becomes a
  registry of per-machine attestation keys, and a registration is valid only
  under a key of an active, attested machine (ADR 0048).
- **Every Founder Machine runs an open-weight model, and the company runs no
  backend** of any kind (ADR 0047). The machine's specification is
  founder-directed (ADR 0052). Bridges run on Founder Machines with their own
  light clients (ADR 0051).
- **One native asset**, at most 56,993,950,100 units, issued only through the
  fixed channels. There is no genesis allocation, no burn, and no slashing.
- **Each seat earns 574.3 units per met cycle for 731 cycles.** A cycle is met
  at 18 hours of fully operational uptime. A failed or capped cycle's
  permission settles at the mint of that cycle's best performers, and its
  Founder portion becomes theirs. Split remainders, and a cycle nobody met, go
  to the recovery pool (ADR 0049).
- **A referral earns 34.2 units per cycle, unconditionally**, to a HUB-verified
  referrer. An unreferred seat's share pays the month's best performer, ranked
  by calendar month from the block timestamp (ADRs 0050, 0075, and 0076).
- **The first 1,000,000 verified users earn 1.71 units a day for 731 days.**
  The first day is an entry airdrop. What is not collected in time is never
  issued (ADRs 0042 and 0043).

## Founder-reserved and open

None of these may be invented. Each is asked when it becomes the nearest
dependency.

- **Legacy limits**: inactivity bounds, dispute evidence, conflicting-statement
  precedence, and reclaim transitions. Requirement 6 builds the mechanics
  without them.
- **Inactivity**, and what an inactive seat or identity loses or keeps.
- **Verifier key rotation**, and who holds the build-signing authority before
  ADR 0047's end of initialization. The threat model adds who may revoke a
  registry key, and who may re-bind a person whose HUB key can no longer be
  produced (T8 and T9).
- **The threat model's other surfaced items**: coercion controls (T7), and
  what follows repeated rejection by the monitor (T10).
- **Seat payment**: which chains, assets, and prices prove a purchase. This is
  bridge scope, M9.
- **Production biometrics**: the camera verifier, capture threshold, and
  uniqueness commitment. ADR 0048's stabilization scheme needs independent
  cryptographic review first.
- **`direct_issue_authority`**, the eligibility and anti-abuse rules for the
  liquidity-mining, impermanent-loss, and mini-gamified channels. Kind 6 stays
  refused.
- **The final unreferred-pool accrual** at the end of the distribution, with no
  later month (ADR 0075).
- **The concrete resource commitment** a challenge is answered against, at the
  resource-network milestone (ADR 0028).
- The constitution's own list: stablecoin governance, the AI frameworks, and
  whether the assistant's one-profile entitlement is protocol-enforced.

## Repository and verification

- `kaikisegfault/protocol-stack`. Issue #420 is open for the next action,
  M4.3k. Every other issue is closed, and `main` is the only branch.
- **The last full hosted verification** is candidate run 40602254819, on
  M4.3i's tree, which `main` holds byte for byte at `c4b0810`.
- `verify.yml` classifies the changed paths with `tools/verification_scope.py`.
  Markdown and skill metadata take the lightweight path:
  `tools/verify_metadata.py` and the `tests/tools` suites. Everything else takes
  the full path, `tools/verify.sh`, on four presets: `gcc-debug`,
  `gcc-sanitizers`, `clang-debug`, and `clang-sanitizers`.
- The full path verifies and tests the Go module and builds with CMake. It runs
  188 CTest entries, or 199 on `clang-sanitizers`, which adds eleven fuzz smokes,
  and then the eight network runs. "Verification required" gates the merge.
- The owner's machine is resource-constrained. Run focused local checks, leave
  the matrix to the hosted runners, and remove local build trees with
  `tools/clean-local.sh`.
- `.claude/RESUME.md` is a Claude Code checkpoint from 2026-08-19, ignored
  through `.git/info/exclude`. It is not repository state.
- `.claude/drafts/` holds two partial drafts that agents began on 2026-10-21
  and did not finish: a version-ten HUB test verifier and a version-ten
  scenario suite. M4.3g started from the third, `snapshot_v10`, and removed it. It is ignored through `.git/info/exclude`, exists
  only on the owner's machine, and passed no check. It is not repository state:
  a slice may start from a draft, and must verify it as new code.

## Remaining gap

**Not built at all:** a production biometric verifier, the packaged Founder
Machine (M5), the AI runtime (M6), a controlled application runtime, the
resource network, bridges and liquidity (M9), the wallet (M10), a public
testnet, and a mainnet. Revenue routing and escrow payouts exist only as Python
models.

**M4's requirements 3, 5, 6, and 8 to 11.** Three findings bear on them.

- **Version nine accepts a HUB approval twice, and `hub-test-verifier-v9`
  executes it.** Each of the five HUB messages binds the transaction's
  `valid_until_height`, which the kernel checks only from below, and none binds
  a nonce. So when an owner relaxes with a HUB approval and then tightens with
  a signer, the published relax is accepted again under a new nonce. A signer
  key alone undoes the tightening, which is the weakening ADR 0043's asymmetry
  exists to prevent. One kind-19 confirmation also moves value twice.
  The version-ten model refuses both, in both forms. The verifier's check
  flips when the kernel runs version ten.
- **A HUB key derived from a face alone is only as secret as the face.**
  Anyone holding a good enough image could compute it offline, with no
  liveness check, so the derivation must also depend on a secret only an
  attested sandbox holds (threat model T3). ADR 0100 places it: split across
  several machines, so no single machine holds it.
- **Only the registration message verifies against the verifier key.** The
  other five verify against the person's own HUB key. So requirement 3's
  registry governs admission, and requirement 5's envelope governs everything
  after it.

**ADR 0089's outage wall.** Under CometBFT `v0.39.4`, the first block after an
outage carries the median of precommits cast before it. So a version-nine
network whose quorum is down for more than 60 seconds never produces another
block under C5. ADR 0089 records three candidate repairs. Each needs a new
contract version, and no network may be claimed to survive an outage until one
lands.

**The kind-22 monthly pool mint has not run on a network.** The C++ execution
vectors cover it. A seed history whose early windows open a month before its
head can close that month, by about height 144,000. M4.2c showed that a seed's
stamps below its head are free while C2 holds, because a restore never applies
C5.

**M3's recorded limits stand** ([audit](founder-economy-devnet-audit-v1.md)):

- validator-duty evidence is vacuous until an active-set protocol exists;
- a partition cannot be produced by this harness;
- the multi-year suite supplies uptime and drives the Python model, not the
  kernel.

The audit also lists, in one place, the independent review the ADRs owe. Until
the resource commitment is decided, an answered challenge proves that a
responder was live, not that a resource was held.

**External purchasability must exist before the millionth identity
registers.** Until then, the entry airdrop is a newcomer's only way to pay a
first fee. No transition can enforce that order, so the bridge milestones must.

**A seeded launch trusts its seed's own root.** Every replica restores the same
payload and takes its root as `app_hash` (ADR 0097), so the replicas agree with
each other whatever the payload holds. The restore gates refuse what one height
proves wrong, the retirement rule included (ADR 0108). They cannot refuse a
retirement dropped after the active count fell below 100, which only the source
chain's root exposes. Today's seeds are model-encoded fixtures. A launch from a
real chain's state must take the seed's root from that chain, and no tool does
that yet.

## Exact next action

**Connect CometBFT to version ten: the Go adapter's version-ten client, bridge,
and launcher version, M4.3k**, the second slice of step 6 of ADR 0104's
enumeration, issue #420. Without it no engine can drive
`protocol-application-v10`.

- `localapp`'s version-ten client over the version-two frame. Its finalize
  decoder admits receipt version 10 and 50 result codes. Its Info refuses a
  protocol version other than `10`, which is how `consensus-application-v3`
  names a mismatched pairing on the first frame.
- `bridge.NewV10` with codespace `protocol-stack-v10` and Info version string
  `10.0.0`, and `LocalV10`.
- `protocol-cometbft-bridge` choosing it for protocol version 10.
- `nodeconfig.ProtocolV10`, whose application state is `"protocol-stack-v10"`
  and whose genesis binds a timestamp.
- Go tests at the depth of version nine's, against a hand-written frame server.

Step 6 ends with the version-ten devnet runs, the HUB test verifier moved onto
version ten, and the network fixtures moved onto it. Then step 7 deletes
version nine's stack.

**Unblocked candidates behind it:**

- the kind-22 mint on a seeded network;
- ADR 0089's outage wall.

**Driving the C++ kernel over `economy-scenario-suite-v4`** now has its entry
point in version ten, `open_window` (ADR 0105). The suite's seven pinned roots
are version nine's, though, and version nine's kernel will not gain the entry
point, so that evidence waits for the suite to be rebound to version ten. An
unverified partial draft is in `.claude/drafts/404-scenario-suite-v10/`.

Moving the network fixtures onto `protocol-hub-test-verifier-v9` waits for
version ten to run on a network, because version ten changes what they build.
A version-ten verifier depends only on the kernel and can be built first; an
unverified partial draft is in `.claude/drafts/403-hub-test-verifier-v10/`.

## Blockers

**No blocker.** Every founder value version ten needs is answered (ADRs 0100,
0101, and 0106), and the specification, the model, and the kernel carry them
all.
