# Repository instructions

## Mission

Build a sovereign, deterministic, single-native-asset protocol stack. The
current operational objective and completion evidence are defined in
`docs/project/first-goal.md`.

Do not treat chat history or model memory as project state. The repository is
the source of truth.

## Start every session

1. Read `docs/project/current-state.md`.
2. Read `docs/project/charter.md` and `docs/project/first-goal.md`.
3. Read only the roadmap, specifications, ADRs, and architecture documents
   relevant to the next action.
4. Inspect the current branch, recent commits, and working tree before editing.
5. When the owner says `proceed`, use the `proceed-project` skill.

If repository state disagrees with `current-state.md`, trust Git and verified
test evidence, then repair the state document.

## Work loop

- Select the smallest unblocked slice that advances the active milestone.
- Specify consensus-critical behavior before implementing it.
- Implement, test, inspect the diff, and update affected documentation.
- Update `current-state.md` only with verified facts and an exact next action.
- Continue with another bounded slice while time and context remain.
- Do not end after a plan when an authorized, unblocked implementation step is
  available.

## Architectural constraints

- Consensus-critical application logic is original C++20.
- C is allowed for audited libraries and hardware-facing boundaries.
- Python is allowed for independent reference models, simulation, and tests.
- Go is allowed for replaceable infrastructure and non-critical services.
- Solidity is deferred until explicitly accepted by an ADR.
- Do not add JavaScript, TypeScript, Node.js, React, or npm tooling.
- The ledger has exactly one protocol-native asset and no public asset-creation
  operation.
- Staking, escrow, fees, treasury, validator, and node-distribution rules are
  native protocol modules, not publicly deployed contracts.
- Never implement cryptographic primitives from scratch.
- Never run AI inference inside consensus. AI may submit signed, bounded
  decisions that deterministic protocol rules verify.
- Do not use floating-point arithmetic for monetary or consensus state.
- Initial consensus and storage integrations must remain replaceable adapters.

## Engineering rules

- Prefer explicit, auditable code over clever abstractions.
- Keep modules cohesive. Aim for 100-250 lines per handwritten source file and
  functions below roughly 50 lines, but do not fragment coherent logic merely
  to satisfy a line count.
- Generated, vendored, and data-table files are exempt from size targets.
- Pin dependencies and justify every consensus-path dependency in an ADR.
- Add negative, boundary, replay, overflow, restart, and determinism tests for
  affected protocol behavior.
- Use the `change-protocol` skill for consensus, state-transition, encoding,
  cryptography, tokenomics, authority, or compatibility changes.
- Use the `verify-project` skill before claiming completion.

## Autonomy and owner gates

Proceed autonomously with reversible implementation that follows accepted
specifications and ADRs. Stop and ask the owner before:

- changing a constitutional or economic invariant;
- selecting or replacing cryptographic primitives or canonical encoding;
- adding a production dependency;
- changing the long-term consensus strategy;
- enabling public contract deployment or secondary assets;
- changing AI authority, treasury, mint, bridge, or upgrade powers;
- handling secrets, deploying externally, publishing a release, or touching a
  public testnet/mainnet;
- destructive operations or changes that conflict with unexplained user work.

Questions should present a recommended default, alternatives, consequences,
and the smallest decision needed.

## Git and authorship

- Preserve unrelated and pre-existing changes.
- Follow `docs/engineering/git-workflow.md`.
- Use focused branches and commit each independently complete, verified chunk.
  Do not wait until the end of a session to commit several unrelated chunks.
- Push atomic commits promptly so cross-session recovery does not depend on one
  machine.
- Map meaningful work to an issue, use a focused branch for the issue or
  milestone slice, and open a PR with verification evidence when that slice is
  coherent. Do not create vanity issues or empty commits.
- Do not add Codex or any AI as an author, committer, co-author, or PR
  participant.
- Do not add `Co-authored-by` trailers for AI tools.
- Keep the configured repository identity:
  `Giorgi Chomakhashvili <133794518+kaikisegfault@users.noreply.github.com>`.
- Bot-authored dependency and platform automation is allowed.
- Push verified work to the current feature branch. Do not merge, tag, release,
  or deploy without the owner or an explicit repository policy authorizing it.

## Definition of done

Work is done only when relevant verification passes, the diff is self-reviewed,
documentation matches behavior, and `docs/project/current-state.md` records the
evidence and next unblocked action.
