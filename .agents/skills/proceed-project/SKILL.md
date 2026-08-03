---
name: proceed-project
description: Continue autonomous work in protocol-stack when the owner says "proceed", "continue", or asks to resume from a clean Codex session. Reconstruct verified repository state, execute the next unblocked milestone slice, verify it, update the handoff, and keep working while safe work and execution capacity remain.
---

# Proceed with the project

1. Read `AGENTS.md`, `docs/project/current-state.md`,
   `docs/project/founder-constitution.md`, `docs/project/charter.md`, and
   `docs/project/first-goal.md`.
2. Read only the roadmap, ADRs, specifications, and engineering documents
   relevant to the recorded next action.
3. Inspect the current branch, recent commits, working tree, and available test
   evidence. Preserve unexplained changes.
4. If the handoff conflicts with Git or tests, reconstruct the truth and repair
   the handoff before relying on it.
5. Select the smallest unblocked outcome that advances the active milestone.
   Do not stop after planning when implementation is authorized and safe.
6. For consensus, tokenomics, encoding, cryptography, authority, or
   compatibility work, invoke `change-protocol`, research alternatives, record
   the autonomous decision, and specify behavior first.
   Treat founder-directed values as fixed inputs. Do not substitute a research
   fixture or autonomous preference for a missing beneficiary, authority, or
   constitutional rule.
7. Implement the slice, use focused local checks, inspect the full diff, and
   update affected documentation plus `current-state.md`.
8. Commit and push each clean, independently complete candidate under the
   configured owner identity. Do not wait for the session to end.
9. Require the risk-proportionate `verify-project` path on GitHub-hosted
   runners for that exact commit before merge or completion. Use focused
   metadata verification for pure documentation or skill metadata and the
   heavy matrix for code, executable, build, workflow, dependency, protocol,
   configuration, or unclassified changes. Record the results in the pull
   request and repair any failure.
10. Merge and clean the completed phase, then repeat from step 5 while
    execution capacity remains. A completed slice is not a reason to yield.

Use meaningful issues, focused branches, and evidence-bearing PRs as defined in
`AGENTS.md`. Do not manufacture activity with empty commits or vanity issues.

The repository's standing delegation makes ordinary owner approval
unnecessary. Do not pause for technical, product-mechanism, protocol,
dependency, merge, release, or deployment approval within the Founder
Constitution. Ask one focused question only when the nearest action requires a
missing founder-reserved value or authority decision; never invent it. Stop
only when execution limits are exhausted or progress requires that answer,
unavailable credentials or infrastructure, an independent external review, or
resolution of conflicting unexplained user work. Complete all other unblocked
work first.

Never use chat history as the authoritative handoff. Never claim continuous
background execution after the current Codex run ends. Never leave detached
local work running. At each phase boundary, cancel obsolete GitHub runs, audit
local processes, and remove reproducible artifacts with
`tools/clean-local.sh`.
