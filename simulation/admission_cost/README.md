# Admission-cost study

This standard-library-only package implements ADR 0014 and the normative
`admission-cost-study-v1` research contract. It composes the accepted
participation, reward-distribution, and native-economy models without changing
their schemas or behavior.

Generate the reviewed design or complete deterministic report with:

```sh
python3 simulation/admission_cost/design.py
python3 simulation/admission_cost/study.py
```

The outputs are mechanism-design evidence only. They do not select a
production identity system, admission fee, bond, duration, price, reward rule,
or consensus transition.
