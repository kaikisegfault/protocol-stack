# Run only necessary hosted checks

Run, and wait for, only the GitHub Actions a change actually needs. A
Markdown/skill-only change takes the metadata path (seconds, Linux matrix
skipped). After a rebase merge, compare `git rev-parse <candidate>^{tree}` with
`main^{tree}`. If they are identical, the candidate run is the evidence, so
don't wait on the push run.

**Why:** On 2026-10-03 the owner interrupted a wait on a full-matrix push run
under a `docs(project)` tip commit and asked why docs needed the Linux
verifiers. That push carried the C++ fix, so it ran the full matrix. But its
tree was byte-identical to the passed candidate's, so it added nothing. The
rule is now step 5 of `conclude-project`.

**How to apply:**
- Explain a full run under a docs-titled tip by the pushed range, not the tip.
- `verify.yml` cancels in-progress runs on `main` when a new push lands. A
  redundant push run may end "cancelled", and that is expected.
- Workflow-level skipping of identical-tree push runs was offered, not built.

Related: `owner-invites-surface-logic-questions.md`, `owner-prefers-prose-for-broad-questions.md`
