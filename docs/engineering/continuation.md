# Cross-session continuation

## Source of truth

New sessions do not rely on previous chat context. Durable state is divided as
follows:

- `vision.md`: stable long-term direction;
- `charter.md`: governing scope and constraints;
- `first-goal.md`: active operational outcome and evidence;
- `roadmap.md`: milestone order;
- ADRs and specifications: accepted technical meaning;
- `current-state.md`: short verified handoff and exact next action;
- Git history and tests: proof of what actually exists.

`current-state.md` is a baton, not a diary. Keep it short and replace stale
status rather than appending a long work log.

## Meaning of `proceed`

When the owner says `proceed`, the session should:

1. Load `AGENTS.md`, current state, charter, first goal, and relevant accepted
   decisions.
2. Inspect Git before assuming the handoff is current.
3. Reconstruct and repair the handoff if it conflicts with the repository.
4. Select the smallest unblocked outcome that advances the active milestone.
5. Write or update a specification before consensus-critical code.
6. Implement, test, inspect, and document the slice.
7. Commit and push each atomic verified chunk when repository policy allows.
8. Update `current-state.md` with evidence and the next action.
9. Open and merge reviewable PRs when their evidence gates pass.
10. Continue with another bounded slice while time, context, and tools remain.

The owner's 2026-07-23 standing delegation means `proceed` requires no
follow-up approval for project decisions or GitHub, release, and deployment
operations. Do not stop merely because one slice, PR, or milestone completed.
Stop only for exhausted execution limits or a genuine external blocker such as
unavailable credentials or infrastructure, required independent review, or
conflicting unexplained user work. Complete other unblocked work first.

## Autonomous decisions

For decisions that materially change architecture, economics, cryptography,
dependencies, authority, external state, or risk, research credible
alternatives and record the recommended choice, rejected alternatives,
consequences, and evidence in the relevant specification and ADR. Evidence
gates remain mandatory even though owner approval pauses do not.

## Interrupted work

If a prior session ended mid-change:

- preserve the working tree;
- inspect the diff and available test artifacts;
- do not assume incomplete code is correct;
- either finish and verify it or document why it must be reverted;
- never overwrite unexplained user changes.

## Session close

Before yielding:

- run the relevant verification matrix;
- review `git diff` and `git status`;
- update specifications and ADRs affected by the change;
- update `current-state.md` using only verified facts;
- state the exact next action and any genuine external blocker.
