---
name: proceed-project
description: Continue autonomous work in protocol-stack when the owner says "proceed", "continue", or asks to resume from a clean Claude Code session. Reconstruct verified repository state, execute the next unblocked milestone slice, verify it, update the handoff, and keep working while safe work and execution capacity remain.
---

# Proceed with the project

1. Read `CLAUDE.md`, `docs/project/current-state.md`,
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
   Then run the founder-decision gate below before doing any of its work.
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
`CLAUDE.md`. Do not manufacture activity with empty commits or vanity issues.

## Founder-decision gate

Run this after selecting a slice and before starting its work, every time. It
is a step with an output, not a disposition. Skipping it silently is the
failure it exists to prevent: the owner cannot distinguish a gate that passed
from a gate that never ran.

**Enumerate.** List every decision the slice must settle to be implementable —
each value, threshold, boundary, beneficiary, ordering rule, and rule about
what a participant must do, own, or receive. Enumerate before judging. A slice
assessed as a whole reliably hides the one reserved decision inside it.

**Classify each one, with its evidence.** A decision is *delegated* when the
Founder Constitution, `first-goal.md`, or an accepted ADR already decides it,
or explicitly names it specification, mechanism, or engineering work. Cite
where. A decision is *founder-reserved* when either test holds:

- it appears under "Explicitly unresolved founder details" in
  `docs/project/founder-constitution.md`, or under the founder-decision gate of
  `docs/project/first-goal.md`; or
- settling it would set or change supply, allocation, beneficiaries, Founder
  ownership, creator hierarchy, commercial routing, AI institutional authority,
  bridge scope, content permanence, or what an end user must do, own, run, or
  receive in order to participate or be paid.

Deducing an answer from decided principles is delegated work and is expected.
Choosing among answers the decided principles do not distinguish, where the
choice changes what a participant gets or must do, is reserved. When a
classification is genuinely unclear, treat it as reserved and ask.

**When every decision is delegated**, report the gate result: name the
decisions considered and where each is already decided, then continue without
pausing. Do not manufacture a question to demonstrate the gate ran.

**When a founder-reserved decision blocks the slice**, do not start it, do not
invent a value, and do not substitute a research fixture for a missing founder
answer. Complete every other unblocked slice first, then ask.

**When a founder-reserved decision is real but not yet blocking**, record it
and keep working. Raise it in the same batched call once it becomes the nearest
dependency, and say which slice it blocks.

### How to ask

Questions use the selectable-option tool, never prose, so the owner sees
unmistakably that the session is waiting on them.

- **Batch every open question into one call.** Do not ask across several turns.
- **Place that call at the very end of the response**, after the work report,
  the gate result, and every other statement. Never mid-response, where it can
  be missed.
- **Give each question concrete selectable answers**, not an open prompt. Each
  option states a specific value or rule and the consequence of choosing it.
  Put the researched recommendation first and mark it as such. The owner can
  always answer outside the options, so options are a starting point rather
  than a restriction.
- **Say what is blocked** by each question and what proceeds regardless.
- Supply the research the choice needs: what the constitution already fixes,
  what each option would cost or enable, and what becomes irreversible.

The standing delegation still makes ordinary owner approval unnecessary. Do not
pause for technical, product-mechanism, protocol, dependency, merge, release,
or deployment approval within the Founder Constitution. Stop only when
execution limits are exhausted or progress requires a reserved answer,
unavailable credentials or infrastructure, an independent external review, or
resolution of conflicting unexplained user work. Complete all other unblocked
work first.

Never use chat history as the authoritative handoff. Never claim continuous
background execution after the current Claude Code run ends. Never leave detached
local work running. At each phase boundary, cancel obsolete GitHub runs, audit
local processes, and remove reproducible artifacts with
`tools/clean-local.sh`.
