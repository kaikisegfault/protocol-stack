---
name: status-project
description: Report the realistic plain-language status of protocol-stack when the owner says "status", asks what has actually been built, asks how close the project or first milestone is to completion, or requests a concise product, value, differentiation, quality, maintainability, clutter, handoff, risk, and remaining-work assessment. Reconstruct evidence from the repository and GitHub, clearly separate runnable product behavior from simulations and plans, and do not change project state.
---

# Report project status

Treat `status` as a read-only reality check, not a progress or conclusion
workflow. Do not create issues, branches, commits, PRs, or documentation edits.

## Reconstruct the evidence

1. Read `CLAUDE.md`, `docs/project/current-state.md`,
   `docs/project/founder-constitution.md`, `docs/project/charter.md`,
   `docs/project/first-goal.md`,
   `docs/project/roadmap.md`, `docs/project/vision.md`, and `README.md`.
2. Fetch and prune `origin`, then inspect the current commit, working tree,
   branches, worktrees, open issues and PRs, recent and active Actions runs,
   dependency alerts, repository processes, and generated directories.
3. Inspect the top-level source, test, simulation, documentation, and tooling
   layout. Check for TODO/FIXME markers, unexplained files, unusually large
   handwritten files, duplicated responsibilities, and obvious naming or
   navigation problems. Use recent exact-commit verification rather than
   launching the full local matrix merely to produce a status report.
4. If documentation conflicts with Git or verified evidence, report the
   discrepancy. Do not repair it unless the owner separately authorizes a
   change.

## Classify what exists

Keep these categories distinct:

- **Runnable now:** a user or operator can start it and observe the behavior.
- **Implemented for development:** real code works, but only under the stated
  local or research constraints.
- **Simulated only:** executable research tests ideas but does not affect the
  running chain.
- **Specified only:** behavior is documented but not implemented.
- **Not built:** roadmap intent without a delivered implementation.

Never describe a simulator, ADR, specification, test fixture, or architectural
intention as final-product functionality.

## Judge quality honestly

- State what recent builds, integration tests, restart tests, differential
  checks, fuzzing, sanitizers, and clean-state evidence support.
- Never call software bug-free. Explain the strongest remaining uncertainty,
  especially missing independent review, public operation, hostile-network
  exposure, performance evidence, platform coverage, and production economics.
- Distinguish harmless historical documentation from clutter that would slow
  development. Name concrete oversized or confusing areas only when current
  inspection supports the claim.
- Answer whether an experienced team can continue from the present structure,
  whether foundational redesign appears necessary, and which bounded
  refactors would reduce future risk.

## Explain value and differentiation

Describe why the completed work saves future engineering or research effort.
Compare the project with commonly available Web3 stacks without marketing
hype. Separate individually common ingredients from the distinctive
combination: original deterministic application rules, one native asset,
native rather than public-contract economics, permanent Founder
infrastructure, controlled full-stack applications, replaceable infrastructure,
and one company-hosted AI authority outside consensus with protocol-enforced
limits. State what is constitutional direction rather than delivered
differentiation, and what the project does not yet compete with, such as
production networks, wallet ecosystems, application clouds, bridges, or
mature operational tooling.

## Response format

Use simple language and lead with the bottom line. Default to roughly 600-900
words unless the owner asks for another depth. Use this compact structure:

1. **Bottom line** — what the project is today in two or three sentences.
2. **What works now** — observable product-level behavior, followed by what is
   simulation or design only.
3. **Milestone position** — completed M1 evidence, the current operational
   goal, and the full Founder-Constitution production finish line.
4. **Why it matters** — practical value and honest differentiation.
5. **Quality and handoff** — confidence, known limits, clutter, refactor need,
   and whether experienced developers can continue smoothly.
6. **What remains** — the nearest gap, major later milestones, blockers, and
   the exact recorded next action.

Prefer a small milestone table when it makes progress clearer. Avoid protocol
acronyms, exhaustive test counts, digests, commit histories, and file-by-file
inventories unless one materially changes the judgment. Link the first-goal,
roadmap, current-state, and any report needed to substantiate the summary.
