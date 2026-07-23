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

## Reproducible entry point

On supported Linux x86_64 hosts, run:

```sh
tools/verify.sh
```

The command installs hash-pinned CMake and Ninja tools in the ignored local
cache, integrity-checks and builds the pinned libsodium source, configures the
default GCC preset, and runs all registered C++ and Python tests through
CTest. See `build-toolchain.md` for host prerequisites, other presets, cache
behavior, and cleanup.

CI runs GCC and Clang debug builds plus AddressSanitizer and
UndefinedBehaviorSanitizer builds. The current suite includes unit and boundary
tests, deterministic properties, 10,000 seeded differential sequences, and
bounded libFuzzer smoke under the Clang sanitizer preset.

As production surfaces are added, this same entry point will expand to
orchestrate:

- format and static analysis;
- integration tests;
- deterministic replay and restart tests.

Long-running fuzzing, economic simulations, and multi-platform reproducibility
checks may run separately, but their commands and latest evidence must be
documented.

## Evidence rule

Do not claim a check passed without running it in the current working state.
Record the exact command and concise result in the relevant PR or
`current-state.md`. If a required check cannot run, describe why and do not
silently downgrade the definition of done.
