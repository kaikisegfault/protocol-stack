---
name: verify-project
description: Run and evaluate protocol-stack quality gates before completion, commit, push, or handoff. Use for documentation, C/C++, Go, Python, protocol, integration, security-sensitive, and release-related changes; select all checks required by changed behavior and report exact evidence.
---

# Verify the project

1. Read `docs/engineering/verification.md` and inspect the complete change.
2. Classify affected surfaces: documentation, build, kernel, protocol,
   persistence, adapter, network, Python model, or operations.
3. For changes limited to Markdown, static documentation assets, `SKILL.md`,
   and skill `agents/openai.yaml`, use the focused repository-metadata path.
   Do not run the compiler/sanitizer matrix. Any executable script, source,
   build, workflow, dependency, protocol, configuration, or unclassified path
   fails closed to full verification.
4. Run lightweight and focused checks locally when they provide prompt
   feedback. Push a clean candidate, then use the selected GitHub-hosted path
   on that exact commit. Use the full path for builds, compiler and sanitizer
   matrices, fuzzing, simulations, packaging, and other heavy gates. Do not
   duplicate heavy remote work locally by default.
5. For consensus-visible changes, require fixed vectors, negative and boundary
   cases, property invariants, and differential evidence from an independent
   model.
6. For untrusted bytes, require a fuzz target or a documented reason it does
   not apply.
7. For C/C++, require the configured compiler matrix and sanitizers. GitHub
   Actions on the exact commit is the default evidence. Run the full matrix
   locally only if the workflow is unavailable or under change, or local
   reproduction is needed; record the reason.
8. Inspect the full diff, Git status, generated artifacts, documentation, and
   dependency changes.
9. Report exact local commands and exact GitHub check results. Distinguish
   passed, failed, and unavailable checks.
10. At every phase boundary, use bounded status queries, cancel obsolete remote
   runs, audit for repository build/test/watch/server processes, and remove
   reproducible local artifacts with `tools/clean-local.sh`. Preserve and
   investigate anything unexplained.

Do not claim completion when a required check fails or cannot run. Record the
gap and next action in `docs/project/current-state.md`.
