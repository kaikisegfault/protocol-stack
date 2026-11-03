# Parallel agents lessons

On 2026-10-21 the owner asked to use spare capacity with parallel agents, then
asked to conclude the session "without agents". Three workers (snapshot_v10,
HUB verifier v10, scenario suite v10) were stopped twice by usage limits and
left only uncommitted drafts, now kept in `.claude/drafts/` (ignored, not
repository state).

**Why:** the work produced no commits, so nothing was delivered. Two worktrees
also started on stale `main` while the shared kernel objects came from the PR
head, which would have mismatched struct layouts. The owner forwarded a side
agent's warning that worker drafts existed only on local disk.

**How to apply:**
- Verify every worktree's base commit before workers build or link.
- Have workers commit small verified pieces and push their branch after each
  one. A branch push starts no CI here; only PRs and `main` do.
- Give workers slices small enough to reach a commit before a usage limit.
- Publish PRs one at a time, as `run-only-necessary-hosted-checks.md` and the
  one-active-branch rule require.
- Only spawn agents when the owner asks.
