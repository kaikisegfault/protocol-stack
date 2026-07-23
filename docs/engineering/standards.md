# Engineering standards

## Languages

- C++20: canonical kernel and node application.
- C: audited low-level libraries and hardware boundaries.
- Python: independent models, simulation, test generation, and tooling.
- Go: replaceable infrastructure and non-consensus services.
- Solidity: prohibited until an accepted ADR enables a constrained use.
- JavaScript, TypeScript, Node.js, npm, and React: prohibited.

Allowed does not mean required. Avoid adding a language without a concrete
architectural role.

## C++ structure

- Prefer value types, RAII, explicit ownership, and narrow interfaces.
- Avoid exceptions crossing protocol or C ABI boundaries.
- Avoid global mutable state.
- Avoid undefined and implementation-defined behavior in canonical logic.
- Use fixed-width integer types and checked monetary arithmetic.
- Make canonical order explicit.
- Keep platform, storage, consensus, and cryptography code outside kernel
  modules.

Handwritten source files should normally remain between 100 and 250 lines.
Files above roughly 300 lines deserve a cohesion review, not an automatic
split. Functions should normally remain below roughly 50 lines. Generated
code, vendored code, tables, fixtures, and protocol vectors are exempt.

## Specifications and compatibility

Every consensus-visible type or transition defines:

- canonical byte representation;
- validity and rejection conditions;
- numeric ranges and overflow behavior;
- state reads and writes;
- deterministic receipt and error semantics;
- replay and authorization behavior;
- compatibility and migration rules;
- positive, negative, boundary, and differential test vectors.

Changing any of these is a protocol change, not a refactor.

## Dependencies

- Never implement custom cryptography.
- Prefer small, mature, actively maintained dependencies with suitable
  licensing and security history.
- Pin exact versions or immutable revisions.
- Wrap protocol-critical dependencies behind narrow adapters.
- Record reason, alternatives, license, determinism impact, update policy, and
  removal path in an ADR.
- Do not add package-manager bootstrap scripts that require Node.js.

## Testing

Use multiple independent evidence types:

- unit and boundary tests;
- property and invariant tests;
- differential tests against the Python reference model;
- canonical cross-language test vectors;
- fuzzing of untrusted decoders and validators;
- sanitizer builds;
- restart, replay, corruption, and fault-injection tests;
- multi-node integration tests;
- reproducible builds with GCC and Clang.

Coverage numbers do not replace invariant coverage or adversarial cases.

## Documentation

Keep repository instructions concise. Put stable facts in project documents,
technical meaning in specifications, choices in ADRs, and only the current
handoff in `current-state.md`.
