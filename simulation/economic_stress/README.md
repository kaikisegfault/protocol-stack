# Cross-simulator economic stress study

This standard-library-only package implements the research contract in
`docs/specifications/economic-stress-study-v1.md`. It composes the unchanged
native-economy, participation, and threshold-authority simulators across a
reviewed 27-case three-level orthogonal design.

Run the default 216-run study:

```sh
python3 simulation/economic_stress/study.py --seed-start 0 --seed-count 8
```

The study reports exact conservation, funding, lifecycle, availability,
capture, recovery, and concentration outcomes. Its factor levels and
classifications are synthetic research evidence, not production parameters or
mainnet-readiness claims.
