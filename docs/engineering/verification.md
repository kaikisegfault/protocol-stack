# Verification

## Foundation checks

Before completing F0:

- validate each repository skill with the official skill validator;
- ensure no skill contains template TODO markers;
- inspect all Markdown links and referenced paths;
- parse `.codex/config.toml`;
- verify Git author and committer identity;
- inspect the complete staged diff and confirm no secrets or unrelated changes;
- confirm a clean status after commit and push.

## Future source checks

The build bootstrap must provide one clean-clone verification entry point. It
will orchestrate:

- format and static analysis;
- GCC and Clang builds;
- unit, property, and integration tests;
- Python reference-model tests;
- sanitizer builds;
- bounded CI fuzz smoke tests;
- deterministic replay and restart tests.

Long-running fuzzing, economic simulations, and multi-platform reproducibility
checks may run separately, but their commands and latest evidence must be
documented.

## Evidence rule

Do not claim a check passed without running it in the current working state.
Record the exact command and concise result in the relevant PR or
`current-state.md`. If a required check cannot run, describe why and do not
silently downgrade the definition of done.
