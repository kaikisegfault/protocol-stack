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
2. Verify GitHub access, fetch and prune, then inspect Git divergence, active
   issues and PRs, branches, worktrees, and generated build directories before
   assuming the handoff is current.
3. Reconstruct and repair the handoff if it conflicts with repository or test
   evidence; identify and resolve leftovers from prior sessions.
4. Select the nearest runnable vertical outcome that materially advances the
   first operational goal.
5. Write or update a specification before consensus-critical code.
6. Implement using focused local checks, then inspect and document the slice.
7. Update `current-state.md` with what works, the remaining gap, and the exact
   next outcome.
8. Commit and immediately push each clean atomic candidate or tightly coupled
   pair.
9. Run the required heavy completion matrix on GitHub-hosted Actions for that
   exact commit, record its terminal results in the pull request, and repair
   any failure.
10. Merge reviewable PRs when their evidence gates pass, update local `main`,
    cancel obsolete remote runs, audit local repository processes, then remove
    merged or obsolete local/remote branches, worktrees, stale refs, temporary
    files, caches, and generated build copies after proving that no required
    unique work remains.
11. Continue with another bounded slice while time, context, and tools remain.

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

## Result and cleanup discipline

Process artifacts are useful only when they protect or accelerate a working
outcome. Prefer production code and runnable integration over speculative
frameworks, redundant test environments, or documentation that does not
clarify implemented behavior.

Use the smallest relevant local check while iterating. Risk-proportionate
GitHub-hosted Actions on the exact candidate commit remain a completion gate.
Pure documentation and repository-skill metadata use the focused metadata
path; code, executable, build, workflow, dependency, protocol, configuration,
and unclassified changes use the compiler and sanitizer matrix. Do not
duplicate the heavy matrix locally without a concrete workflow or diagnostic
reason.

Never detach repository work or leave a local watcher, server, build, test, or
helper running across a phase boundary. Once evidence is recorded, use bounded
status checks, cancel obsolete GitHub runs, audit local processes, and run
`tools/clean-local.sh`. Resolve unexplained artifacts individually.

A finished branch is not durable project state. Merge it when its evidence
gates pass, then delete local and remote branch references and any linked
worktree unless unique work has been deliberately retained. Keep a branch only
while its documented outcome remains active.

At handoff, fetch and prune again. Local `main` must equal `origin/main`; every
retained feature branch must be clean, pushed, and equal to its upstream; and
the only remote branch besides `main` may be the single documented active
delivery branch. Any exception is a primary blocker, not routine leftover
state.

## Session close

Before yielding:

- run the relevant verification matrix;
- review `git diff` and `git status`;
- prove local/remote branch equality and reconcile GitHub issue and PR state;
- update specifications and ADRs affected by the change;
- update `current-state.md` using only verified facts;
- state the exact next action and any genuine external blocker.
