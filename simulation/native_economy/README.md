# Native-economy simulator

This standard-library-only Python package executes the research contract in
`docs/specifications/native-economy-simulation-v1.md`. It is independent of
the C++ ledger and does not define a consensus transition or production
parameter.

Run the reviewed fixed fixture:

```sh
python3 simulation/native_economy/run.py \
  simulation/native_economy/fixtures/research-manifest-v1.json \
  simulation/native_economy/fixtures/research-events-v1.json
```

Generate reviewable deterministic inputs. The command records the generator
algorithm in this versioned package and the seed in the invocation:

```sh
python3 simulation/native_economy/generate.py \
  0x5eed /tmp/manifest.json /tmp/events.json --rounds 6
python3 simulation/native_economy/run.py \
  /tmp/manifest.json /tmp/events.json --output /tmp/result.json
```

Run the bounded study used by the M2 evidence report:

```sh
python3 simulation/native_economy/study.py \
  --seed-start 0 --seed-count 24 --rounds 4
```

All commands emit JSON integers and reduced rational objects. The fixture and
generator values are test inputs, not recommended issuance, allocation, fee,
reward, staking, or penalty policy.
