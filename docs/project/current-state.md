# Current state

Last updated: 2026-10-09

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
| 3 | The per-machine attestation-key registry | Open; two owner questions first |
| 4 | A deterministic test verifier as a replaceable component | Met 2026-10-09, M4.4, for version nine's proofs |
| 5 | Sensitive-action authorization with expiry and replay protection | Open, unblocked |
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
The repository compiles it and the M1 version-one ledger, and nothing between.
Every layer is built:

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

- **Requirement 3's two questions, which are the nearest.** ADR 0048 makes a
  registration valid only under an active, attested machine's key, and the
  constitution runs capture on the founder's own machine. Neither says whose
  machine verifies a person who owns none: an ordinary user, a creator, or a
  developer. Neither says how the first registrations happen before any seat
  is active, given that buying a seat requires HUB verification first.
- **Legacy limits**: inactivity bounds, dispute evidence, conflicting-statement
  precedence, and reclaim transitions. Requirement 6 builds the mechanics
  without them.
- **Inactivity**, and what an inactive seat or identity loses or keeps.
- **Verifier key rotation**, and who holds the build-signing authority before
  ADR 0047's end of initialization. The threat model adds who may revoke a
  registry key, and who may re-bind a person whose HUB key can no longer be
  produced (T8 and T9).
- **The threat model's other surfaced items**: coercion controls (T7), what
  follows repeated rejection by the monitor (T10), and the value of any
  per-machine registration bound (T8).
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

- `kaikisegfault/protocol-stack`. Issue #378 is M4.7, on
  `docs/378-hub-threat-model`. Every other issue is closed, and `main` is the
  only other branch.
- **The last full hosted verification** is candidate run 37950293612, on
  M4.4's tree, which `main` holds byte for byte at `aad3fd5`.
- `verify.yml` classifies the changed paths with `tools/verification_scope.py`.
  Markdown and skill metadata take the lightweight path:
  `tools/verify_metadata.py` and the `tests/tools` suites. Everything else takes
  the full path, `tools/verify.sh`, on four presets: `gcc-debug`,
  `gcc-sanitizers`, `clang-debug`, and `clang-sanitizers`.
- The full path verifies and tests the Go module and builds with CMake. It runs
  175 CTest entries, or 184 on `clang-sanitizers`, which adds nine fuzz smokes,
  and then the eight network runs. "Verification required" gates the merge.
- The owner's machine is resource-constrained. Run focused local checks, leave
  the matrix to the hosted runners, and remove local build trees with
  `tools/clean-local.sh`.
- `.claude/RESUME.md` is a Claude Code checkpoint from 2026-08-19, ignored
  through `.git/info/exclude`. It is not repository state.

## Remaining gap

**Not built at all:** a production biometric verifier, the packaged Founder
Machine (M5), the AI runtime (M6), a controlled application runtime, the
resource network, bridges and liquidity (M9), the wallet (M10), a public
testnet, and a mainnet. Revenue routing and escrow payouts exist only as Python
models.

**M4's requirements 3, 5, 6, and 8 to 11.** Four findings bear on them.

- **Version nine accepts a HUB approval twice, and `hub-test-verifier-v9`
  executes it.** Each of the five HUB messages binds the transaction's
  `valid_until_height`, which the kernel checks only from below, and none binds
  a nonce. So when an owner relaxes with a HUB approval and then tightens with
  a signer, the published relax is accepted again under a new nonce. A signer
  key alone undoes the tightening, which is the weakening ADR 0043's asymmetry
  exists to prevent. One kind-19 confirmation also moves value twice.
  Requirement 5's contract must refuse both, and that check will flip.
- **Requirements 3 and 5 both change the HUB signature family or genesis**, so
  one new contract version should carry both, rather than one version each.
- **A HUB key derived from a face alone is only as secret as the face.**
  Anyone holding a good enough image could compute it offline, with no
  liveness check, so the derivation must also depend on a secret only an
  attested sandbox holds (threat model T3). Where that secret lives for a
  person with no Founder Machine is requirement 3's first question again.
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

## Exact next action

**Ask the owner requirement 3's two questions**, in one batched call at the
end of the session. Requirement 3 is not started before they are answered.

**Then the contract version that carries requirements 3 and 5**, under the
threat model's four obligations:

- single-use approvals with a protocol-bounded validity window;
- the attestation-key registry;
- registry-key revocation;
- an evaluated per-machine registration bound, whose value is asked.

Requirement 6's legacy records can join it: statements, nomination,
supersession, and the reclaim right need no reserved value. The inactivity
trigger stays reserved.

**Unblocked while the answers are pending**, nearest first:

- the kind-22 mint on a seeded network, as above;
- driving the C++ kernel over the `economy-scenario-suite-v4` population
  against its seven pinned roots;
- ADR 0089's outage wall.

Moving the network fixtures onto `protocol-hub-test-verifier-v9` waits for the
contract version that carries requirements 3 and 5, because that version
changes what they build anyway.

## Blockers

**No blocker.** Requirement 3 waits on two founder answers, and everything
else listed above is unblocked.
