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
9. Continue with another bounded slice while time, context, and permissions
   remain.

Do not stop merely because one small slice completed. Do stop for an owner gate,
an unrecoverable external blocker, a safety boundary, or exhausted execution
limits.

## Questions

Questions are reserved for decisions that materially change architecture,
economics, cryptography, dependencies, authority, external state, or risk.
Before asking, complete all safe research and unblocked work. Present one
recommended option and the consequence of each alternative.

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
- state the exact next action and any owner decision required.
