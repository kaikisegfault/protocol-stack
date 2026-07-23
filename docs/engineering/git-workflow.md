# Git and GitHub workflow

## Traceability

Use this hierarchy:

```text
roadmap milestone
  └── meaningful issue
        └── focused branch
              ├── atomic verified commits
              └── pull request with evidence
```

Do not create an issue for a trivial typo or manufacture empty activity. Create
an issue when the work needs acceptance criteria, design discussion,
autonomous decision records, dependency tracking, or more than one
independently useful commit.

## Branches

- Protect `main` from direct development commits.
- Create branches from the current `main`.
- Use `type/issue-short-description` when an issue exists.
- Allowed type examples: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`,
  `security`, and `research`.
- Keep one branch focused on one issue or coherent milestone slice.

## Commits

Commit immediately after each independently complete and verified chunk. A
chunk may be a specification, ADR, build capability, protocol type, invariant,
test group, adapter behavior, or documentation unit.

Do not wait for the session to end. Do not commit knowingly broken or
half-implemented behavior merely to increase commit count.

Use Conventional Commit subjects:

```text
type(optional-scope): imperative summary
```

The body should explain why when the reason is not obvious and list protocol or
compatibility effects when applicable. Reference the issue where useful.

Push promptly after each atomic commit or tightly coupled pair of commits so a
new session can recover from GitHub.

## Pull requests

Open a PR when the branch forms a coherent reviewable outcome. Include:

- linked issue and milestone;
- outcome and scope;
- protocol, compatibility, economic, and security effects;
- exact verification commands and results;
- ADR and specification links;
- known limitations and follow-up work.

Prefer preserving clean atomic commits with a rebase merge. Squash only when a
branch contains fixup noise that has no durable review value.

The standing delegation in `AGENTS.md` authorizes merging, tagging, publishing
releases, and deploying externally once the applicable verification, review,
security, and production gates pass. Prefer rebase merges for clean atomic
history. Never weaken an evidence gate to make an autonomous action possible.

## Authorship

Human development activity uses the repository owner identity. Do not add AI
tools as authors, committers, co-authors, reviewers, assignees, or PR
participants. Automated GitHub and dependency bots may use their normal bot
identity.

## Project quality

A professional profile comes from useful public artifacts, coherent history,
reproducible evidence, responsive issue handling, and honest limitations—not
from maximizing raw activity counts.
