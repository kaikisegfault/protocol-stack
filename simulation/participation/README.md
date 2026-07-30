# Participation simulator

This standard-library-only Python package executes the research contract in
`docs/specifications/participation-simulation-v1.md`. It models validator and
resource-node lifecycle, bounded appraised contribution units, and reward
entitlements. It owns no native value and defines no consensus transition or
production parameter.

Run the reviewed fixed fixture:

```sh
python3 simulation/participation/run.py \
  simulation/participation/fixtures/research-manifest-v1.json \
  simulation/participation/fixtures/research-events-v1.json
```

Generate deterministic reviewable inputs and replay them:

```sh
python3 simulation/participation/generate.py \
  0x5eed /tmp/participation-manifest.json /tmp/participation-events.json \
  --rounds 4
python3 simulation/participation/run.py \
  /tmp/participation-manifest.json /tmp/participation-events.json
```

Run the bounded study:

```sh
python3 simulation/participation/study.py \
  --seed-start 0 --seed-count 24 --rounds 4
```

The study independently converts finalized entitlements to native-economy v1
`allocate_reward` events and requires every claim funding event to succeed.
Manifest delays, caps, stake amounts, weights, budgets, verifiers, and actors
are test fixtures, not production recommendations.
