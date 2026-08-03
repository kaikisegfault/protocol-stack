---
name: conclude-project
description: Conclude active work in protocol-stack when the owner says "conclude", "wrap up", "finish the current slice", or asks to close, merge, clean, and leave a pristine handoff. Freeze scope at the work already started, finish and publish it completely, verify candidate and post-merge commits, reconcile every issue, PR, run, branch, worktree, process, artifact, and handoff fact, and do not begin the recorded next slice.
---

# Conclude the project session

Treat conclusion as a delivery workflow, not a summary request. Finish all
in-scope work already started and leave the repository safe for a clean Claude
Code session. Do not start the next roadmap slice, even when it is unblocked.

## 1. Freeze and reconstruct scope

1. Read `CLAUDE.md`, `docs/project/current-state.md`,
   `docs/project/founder-constitution.md`, `docs/project/charter.md`, and
   `docs/project/first-goal.md`.
2. Fetch and prune `origin`, verify GitHub authentication, and inspect the
   current branch, upstreams and divergence, recent commits, working tree,
   worktrees, issues, pull requests, Actions runs, repository processes, and
   generated directories.
3. Define the conclusion scope as every issue, branch, commit, PR, check,
   documentation update, or cleanup action belonging to the slice or phase
   already in progress. Include partially started work that is required for
   that outcome to be correct.
4. Exclude the next action recorded for a future session. Do not create its
   issue, branch, design, or implementation.
5. Preserve and report unrelated or unexplained user work. Never delete or
   absorb it merely to make the tree look clean.

If repository state disagrees with the handoff, trust Git and verified test
evidence, then repair the handoff within the frozen scope.

## 2. Finish the active outcome

1. Complete missing implementation, tests, specifications, ADRs, reports, and
   review fixes required by the active issue or PR.
2. Invoke `change-protocol` for any remaining consensus-visible work and
   `verify-project` before claiming the candidate complete.
3. Use focused local checks for prompt feedback, inspect the complete diff,
   and remove secrets, debug residue, and accidental generated files.
4. Update `docs/project/current-state.md` with verified behavior and evidence,
   the nearest actual project outcome, the remaining gap, and one exact next
   action for a fresh session.
5. Commit and push every finished atomic change under the configured owner
   identity. Never leave a required local-only commit.

Do not replace incomplete implementation with a plan or handoff note. A
handoff records the finished state; it does not excuse unfinished safe work.

## 3. Publish to a terminal result

1. Open or update the linked PR with scope, effects, limitations, and exact
   verification evidence. Keep the meaningful issue linked to the PR.
2. Monitor every required check on the exact candidate commit to a terminal
   result. Repair failures within scope, push the repair, and require the new
   exact candidate to pass.
3. Merge only after required checks pass. Prefer the repository's normal
   rebase merge and delete the delivery branch.
4. Fetch and prune, switch to `main`, fast-forward it, and identify the exact
   merged commit.
5. Monitor required post-merge checks on that exact `main` commit to terminal
   success. Treat a post-merge failure as unfinished work: repair, republish,
   merge, and verify again.
6. Ensure linked issues are closed and no obsolete PR remains open.

When merge or post-merge facts cannot be written before the delivery PR
merges, publish a bounded handoff-doc PR after the delivery merge. Verify and
merge that PR and require its post-merge check to pass. Do not create an
infinite documentation chain solely to record the closeout PR's own merge or
post-merge run; report those final facts in the session response.

## 4. Prove the clean boundary

After all merges, fetch and prune again and prove all of the following:

- local `main` is clean and exactly equals `origin/main`;
- every retained local branch has an upstream at the same commit, and only a
  genuinely necessary documented delivery branch remains;
- remote branches contain only `main`, unless an explicitly documented active
  branch is unavoidable;
- there is one expected worktree and no stale or abandoned worktree;
- active issue and PR state agrees with `current-state.md`;
- required candidate and post-merge runs succeeded, with no obsolete queued
  or in-progress run left behind;
- no repository build, test, watcher, server, or helper process remains;
- known reproducible artifacts are removed with `tools/clean-local.sh`, and
  anything outside its narrow scope has been inspected rather than deleted;
- there are no unexplained tracked or untracked changes, unpushed commits,
  stale remote-tracking references, or open dependency alerts attributable to
  the concluded work.

Delete only branches and worktrees proven merged or obsolete. Cancel only runs
proven obsolete. Never use destructive cleanup against an unresolved target.

## 5. Handle genuine blockers

Use the repository's standing authority for technical decisions, fixes,
publication, merging, and cleanup. Do not pause for approval while safe
in-scope work remains.

Stop incomplete only for unavailable credentials or infrastructure, required
independent external review, or conflicting unexplained user work. First
finish every other unblocked closeout action. Preserve the exact commit and
branch, record the blocker as the primary fact in `current-state.md`, and state
precisely which invariant remains unsatisfied. Never describe a blocked state
as clean or concluded.

## 6. Report the conclusion

Lead with the outcome. Include the final `main` commit, merged and closed
issue/PR identifiers, exact candidate and post-merge run results, cleanup and
reconciliation proof, what works now, and the next action already recorded for
the fresh session. Mention warnings only when they require future action.

Do not claim background work will continue after the session ends.
