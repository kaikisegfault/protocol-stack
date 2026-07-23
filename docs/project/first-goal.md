# First operational goal: Sovereign Devnet Alpha

## Objective

From a clean clone, one documented command starts a reproducible
four-validator local blockchain whose original C++20 deterministic
account-based ledger:

- processes signed native-asset transfers in approximately three-second
  blocks;
- maintains one native asset and a configured constitutional supply limit;
- rejects replay, invalid nonce, insufficient balance, overflow, malformed
  encoding, and unauthorized mint attempts;
- meters transactions and routes fees to a native protocol fee pool without
  implicit burning;
- persists committed state and recovers after node restarts;
- produces identical state roots for identical ordered inputs.

The proposed first network adapter uses CometBFT for BFT consensus and P2P while
the C++ application owns all state-transition and economic behavior.

## Required evidence

Completion requires all of the following:

1. A canonical specification for primitive types, amounts, accounts,
   signatures, transactions, blocks, encoding, hashing, and state roots.
2. A C++20 ledger library and headless application process.
3. Deterministic genesis, account, transfer, nonce, fee-pool, and supply-limit
   behavior.
4. Atomic persistent commits and verified restart/replay behavior.
5. A four-validator local devnet with a documented start, health, transaction,
   stop, and restart procedure.
6. Unit and boundary tests for every state-transition rule.
7. Property tests covering conservation, supply bounds, nonce monotonicity,
   deterministic replay, and failed-transaction atomicity.
8. Fuzz targets for canonical decoding and transaction validation.
9. AddressSanitizer and UndefinedBehaviorSanitizer verification.
10. Successful GCC and Clang builds.
11. An independent Python reference model that matches the C++ result and
    state root across at least 10,000 reproducibly seeded randomized
    transaction sequences.
12. A single documented verification command that passes from a clean clone.

Performance claims beyond the configured local block interval are not part of
this goal.

## Explicitly out of scope

- Final token allocation or production tokenomics.
- Staking, validator admission, slashing, node rewards, treasury allocation, or
  general escrow.
- Public testnet/mainnet, real assets, bridge, wallet, or graphical interface.
- Public contracts, EVM, Solidity, or arbitrary application execution.
- Production AI authority, distributed AI inference, or model training.
- Custom consensus, node OS, device, processor, or satellite work.

## Owner decision gates

Implementation must stop for owner acceptance of:

- the cryptographic and hashing suite;
- canonical encoding and address format;
- native denomination and constitutional supply values;
- any change to the single-asset, fee-routing, or AI authority constraints;
- replacing the proposed initial consensus strategy.
