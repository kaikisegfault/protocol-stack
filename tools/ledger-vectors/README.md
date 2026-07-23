# Ledger transition vector harness

The normative ledger scenario is
`test-vectors/ledger-transition-v1.txt`. Run the C++20 and independent Python
models with the repository entry point:

```sh
tools/verify.sh
```

The synthetic genesis has two funded accounts and a 7,000,000-atomic-unit
supply so every value is readable in the fixture. It uses the same
constitutional cap and fixed fee as M1 but is not the default four-account
devnet allocation.

The ordered block exercises ordinary transfer, replay, self-transfer,
recipient creation, zero amount, low fee limit, expiry, absent sender, nonce
mismatch and exhaustion, debit overflow, insufficient balance, malformed
length, invalid signature, wrong chain, and unknown transaction kind behavior.
It fixes exact admission results, receipts, state entries, state roots,
transaction root, application header, and block ID.

These are decision harnesses, not the production kernel. The C++ kernel must
consume the same frozen vectors and the Python model must remain independent
for randomized differential tests.
