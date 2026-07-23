---
name: verify-project
description: Run and evaluate protocol-stack quality gates before completion, commit, push, or handoff. Use for documentation, C/C++, Go, Python, protocol, integration, security-sensitive, and release-related changes; select all checks required by changed behavior and report exact evidence.
---

# Verify the project

1. Read `docs/engineering/verification.md` and inspect the complete change.
2. Classify affected surfaces: documentation, build, kernel, protocol,
   persistence, adapter, network, Python model, or operations.
3. Run every available required check for those surfaces in the current working
   state. Do not substitute a narrower test merely because it is faster.
4. For consensus-visible changes, require fixed vectors, negative and boundary
   cases, property invariants, and differential evidence from an independent
   model.
5. For untrusted bytes, require a fuzz target or a documented reason it does
   not apply.
6. For C/C++, require the configured compiler matrix and sanitizers when the
   build bootstrap provides them.
7. Inspect the full diff, Git status, generated artifacts, documentation, and
   dependency changes.
8. Report exact commands and results. Distinguish passed, failed, and
   unavailable checks.

Do not claim completion when a required check fails or cannot run. Record the
gap and next action in `docs/project/current-state.md`.
