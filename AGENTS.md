# Repository instructions

## Mission

Build the complete sovereign, deterministic, single-native-asset ecosystem
defined in `docs/project/founder-constitution.md`. The current operational
objective and completion evidence are defined in `docs/project/first-goal.md`.

Do not treat chat history or model memory as project state. The repository is
the source of truth.

## Start every session

1. Read `docs/project/current-state.md`.
2. Read `docs/project/founder-constitution.md`, `docs/project/charter.md`, and
   `docs/project/first-goal.md`.
3. Read only the roadmap, specifications, ADRs, and architecture documents
   relevant to the next action.
4. Verify GitHub authentication, fetch and prune `origin`, then reconcile the
   current branch, recent commits, working tree, local and remote branches,
   worktrees, active issues, pull requests, GitHub Actions runs, repository
   processes, and generated directories before editing.
5. Prove every retained local branch has an upstream and identify any
   divergence or uncommitted work. Do not assume a VS Code branch list or a
   previous handoff is current.
6. When the owner says `proceed`, use the `proceed-project` skill.
7. When the owner says `conclude`, `wrap up`, or asks to finish the current
   slice and leave a clean handoff, use the `conclude-project` skill. Freeze
   scope at work already started, finish and publish it completely, and do not
   begin the recorded next slice.
8. When the owner says `status` or asks for a realistic plain-language project
   assessment, use the `status-project` skill. Reconstruct evidence and report
   it without changing project or GitHub state.

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

## Owner execution preferences

- Start every clean session by independently reconciling Git, tests, the
  handoff, active issues, branches, worktrees, and generated build directories.
  Do not inherit stale session assumptions merely because they are documented.
- Treat GitHub as the durable publication boundary. Push every verified atomic
  commit or tightly coupled pair immediately. Before every handoff, fetch and
  prune again and prove that `main` equals `origin/main` and every retained
  feature branch is clean and exactly equals its upstream.
- Keep at most one active delivery branch. At each completed slice or phase
  boundary, open its PR, monitor required checks to a terminal result, merge
  when green, update local `main`, and remove the merged local/remote branch,
  linked worktree, stale remote-tracking references, and redundant build trees.
  Never delete unexplained or unmerged work.
- A clean handoff has no unpushed commits, no unexplained tracked or untracked
  changes, no merged or obsolete branches, and no stale worktrees. The only
  remote branches should be `main` and, while genuinely necessary, the one
  documented active delivery branch.
- If GitHub authentication, network access, CI, or repository permissions
  prevent synchronization, preserve the exact commit, record it as the primary
  blocker, and make publishing and reconciliation the first action when access
  returns. Do not continue accumulating unpublished slices.
- Choose the nearest runnable vertical result that materially advances
  `docs/project/first-goal.md`. Before starting a slice, ask whether it moves
  the working application toward that outcome; defer speculative machinery
  that does not.
- Prioritize implementation and integration over process artifacts. Add only
  the design record and risk-proportionate tests needed to make behavior
  auditable and safe.
- During implementation, use only lightweight or focused local checks needed
  for prompt feedback. Push a clean candidate and use GitHub-hosted Actions on
  that exact commit. Pure Markdown, README, static documentation-asset, and
  repository-skill instruction/metadata changes use the focused metadata path;
  do not run the compiler/sanitizer matrix for them. Source, executable script,
  build, workflow, dependency, protocol, configuration, and unclassified
  changes fail closed to the full hosted matrix. Run a heavy gate locally only
  when the workflow is unavailable or under change, or when reproducing a
  failure requires it; record why. Do not duplicate the full remote matrix
  locally by default. Required risk-proportionate completion gates remain
  mandatory.
- Treat the owner's local machine as resource-constrained. Do not run the full
  verifier, populate large build/module/VCS caches, use direct VCS dependency
  retrieval, or resolve expanded dependency graphs locally when a
  GitHub-hosted job can do the work. Generate dependency locks and other large
  reproducible artifacts on GitHub-hosted runners, retrieve only the small
  reviewed result, and keep local checks narrowly focused. If an exceptional
  local heavy operation is unavoidable, state the expected resource cost
  first, bound it, and remove its reproducible artifacts immediately afterward.
- Never launch repository work as a detached or unattended local process.
  Prefer bounded GitHub status queries over persistent local watchers. Before
  each phase boundary and handoff, prove no repository build, test, monitor,
  server, or helper process remains; cancel obsolete remote runs; and remove
  reproducible build trees, caches, temporary files, merged branches, and stale
  worktrees. Use `tools/clean-local.sh` after preserving required evidence and
  inspect anything outside its narrow known-path scope rather than deleting it
  blindly. Report handoffs as: what works now, the nearest actual outcome, and
  the remaining gap.

## Architectural constraints

- Consensus-critical application logic is original C++20.
- C is allowed for audited libraries and hardware-facing boundaries.
- Python is allowed for independent reference models, simulation, and tests.
- Go is allowed for replaceable infrastructure and non-critical services.
- Solidity is deferred until explicitly accepted by an ADR.
- Do not add JavaScript, TypeScript, Node.js, React, or npm tooling.
- The ledger has exactly one protocol-native asset and no public asset-creation
  operation.
- BTC, ETH, and approved stablecoins may appear only at the restricted bridge
  boundary for Founder Seat purchase, liquidity, native swaps, and withdrawal;
  they are never general internal balances.
- Founder admission, escrow, fees, treasury, validator, and node-distribution
  rules are native protocol modules, not publicly deployed contracts. Do not
  introduce production staking, slashing, or monetary penalties without an
  explicit founder decision.
- Never implement cryptographic primitives from scratch.
- Never run AI inference inside consensus. AI may submit signed, bounded
  decisions that deterministic protocol rules verify.
- Do not require AI inference on Founder Nodes. The logical Ecosystem AI is a
  company-hosted control plane with separately bounded capabilities.
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

## Standing autonomous delegation

On 2026-07-23 the owner granted standing authority for end-to-end autonomous
project execution. A `proceed` instruction activates that authority for the
session; it does not require follow-up approval for technical, product,
protocol-mechanism, dependency, GitHub, release, or deployment decisions that
remain inside the Founder Constitution.

A `conclude` instruction activates the same authority only for completing,
publishing, verifying, documenting, and cleaning the slice or phase already in
progress. It does not authorize starting the next recorded slice.

For consequential engineering choices, research credible alternatives, record
the selected default and consequences in a specification or ADR, satisfy the
applicable verification and review gates, and continue. Evidence gates replace
approval pauses; they must not be bypassed merely to preserve momentum.

Do not autonomously change founder-directed supply, allocation, beneficiaries,
Founder ownership, creator hierarchy, commercial routing, AI institutional
authority, bridge scope, or content permanence. When an unresolved choice
would materially change those values, ask the owner one focused question at
the point it becomes the nearest dependency. Use explicit research-only inputs
and complete other safe work first when the question is not yet blocking.

Continue through bounded slices until execution limits or a genuine external
blocker prevent useful work. Do not stop to ask for ordinary approval. When one
path is blocked, complete other safe work first. Record a remaining blocker
only when it requires unavailable credentials, unavailable external
infrastructure, independent review that cannot be performed in-session,
resolution of conflicting unexplained user work, or a founder-reserved choice
that would otherwise be invented.

Use only credentials already configured for the repository, never expose or
commit secrets, and keep destructive actions narrowly scoped and recoverable
where practical.

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
- Push verified work to the current feature branch. The standing delegation
  authorizes opening and merging PRs, tagging, publishing releases, and
  deploying when the applicable repository evidence gates are satisfied.

## Definition of done

Work is done only when relevant verification passes, the diff is self-reviewed,
documentation matches behavior, and `docs/project/current-state.md` records the
evidence and next unblocked action.
