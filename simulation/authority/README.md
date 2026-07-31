# Threshold-authority research simulator

This standard-library-only Python package implements the research contract in
`docs/specifications/authority-simulation-v1.md`. It counts distinct opaque
member-verification results, binds accepted actions to one capability and set
version, and models explicit rotation, containment, revocation, and recovery.
It contains no cryptographic primitive, key, signature parser, model inference,
native value, or consensus transition.

Replay the reviewed fixture:

```sh
python3 simulation/authority/run.py \
  simulation/authority/fixtures/research-manifest-v1.json \
  simulation/authority/fixtures/research-events-v1.json
```

Generate a deterministic scenario:

```sh
python3 simulation/authority/generate.py \
  --seed 0 --manifest /tmp/authority-manifest.json \
  --events /tmp/authority-events.json
```

Run the bounded adversarial study:

```sh
python3 simulation/authority/study.py --seed-start 0 --seed-count 24
```

Every fixture value is explicitly research-only and is not a production
principal, threshold, delay, digest, verifier, or cryptographic choice.
