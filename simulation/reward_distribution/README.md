# Reward distribution study v1

This directory contains the deterministic, integer-only M2 comparison of the
accepted proportional entitlement, a four-epoch participant-scoped credit cap,
and the same cap grouped by registered principal. It is research tooling, not a
consensus transition or production parameter recommendation.

Generate and check the reviewed design:

```sh
python3 simulation/reward_distribution/design.py
```

Run the exact support and trajectory study:

```sh
python3 simulation/reward_distribution/study.py
```

The normative contract is
`../../docs/specifications/reward-distribution-study-v1.md`. The implementation
reuses accepted participation and native-economy engines only for independent
cross-checks. Pending credit is not a native claim and capped outputs are not
called accepted participation-v1 entitlements.
