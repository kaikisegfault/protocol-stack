---
name: proceed-project
description: Continue autonomous work in protocol-stack when the owner says "proceed", "continue", or asks to resume from a clean Codex session. Reconstruct verified repository state, execute the next unblocked milestone slice, verify it, update the handoff, and keep working while safe work and execution capacity remain.
---

# Proceed with the project

1. Read `AGENTS.md`, `docs/project/current-state.md`,
   `docs/project/charter.md`, and `docs/project/first-goal.md`.
2. Read only the roadmap, ADRs, specifications, and engineering documents
   relevant to the recorded next action.
3. Inspect the current branch, recent commits, working tree, and available test
   evidence. Preserve unexplained changes.
4. If the handoff conflicts with Git or tests, reconstruct the truth and repair
   the handoff before relying on it.
5. Select the smallest unblocked outcome that advances the active milestone.
   Do not stop after planning when implementation is authorized and safe.
6. For consensus, tokenomics, encoding, cryptography, authority, or
   compatibility work, invoke `change-protocol` and specify behavior first.
7. Implement the slice, run the relevant `verify-project` gates, inspect the
   full diff, and update affected documentation.
8. Commit and push each independently complete, verified chunk under the
   configured owner identity. Do not wait for the session to end.
9. Update `current-state.md` with verified facts, evidence, blockers, and one
   exact next action.
10. If no owner gate or blocker exists and execution capacity remains, repeat
    from step 5 with another bounded slice.

Use meaningful issues, focused branches, and evidence-bearing PRs as defined in
`AGENTS.md`. Do not manufacture activity with empty commits or vanity issues.

Stop and ask only at an owner gate, for conflicting user work, unavailable
authority or secrets, or when safe progress is no longer possible. Complete
independent research and other unblocked work before asking.

Never use chat history as the authoritative handoff. Never claim continuous
background execution after the current Codex run ends.
