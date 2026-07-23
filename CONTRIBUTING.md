# Contributing

This repository is early research software. It does not yet secure production
assets.

Before contributing, read:

- `docs/project/charter.md`;
- `docs/project/first-goal.md`;
- `docs/engineering/standards.md`;
- `docs/engineering/git-workflow.md`.

Use the relevant GitHub issue form before substantial work. Consensus,
encoding, cryptography, economics, authority, bridge, and compatibility changes
must begin with a specification or ADR and identify affected invariants.

Contributions must:

- avoid JavaScript, TypeScript, Node.js, npm, and React;
- preserve the single-native-asset design;
- keep AI inference outside consensus;
- include relevant negative, boundary, property, differential, and fuzz
  evidence;
- document dependency and compatibility effects;
- pass all available repository verification.

By contributing, you agree that your contribution is licensed under the
Apache License 2.0 in this repository.
