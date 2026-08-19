# Current operational goal: Founder Economy Devnet

## Objective

Make the founder-directed economy real consensus behavior. Specify the revised
economic contract, implement it in the C++20 ledger, and operate a
four-validator devnet that enforces the fixed cap and the accepted Founder,
referral, commercial, fee, and escrow accounting with deterministic replica
agreement across restart.

M2 proved the accounting in independent Python models that activate nothing.
This milestone turns that into a running network, under the direction revised on
2026-08-07 by
[ADR 0023](../decisions/0023-founder-decisions-activity-referrals-and-supply.md).

## What changed since M2

The accepted M2 models implement `founder-economy-manifest-v1`, which the
Founder Constitution has superseded. Before any C++ work, the contract must be
restated:

- the maximum supply is 56,993,950,100 display units, not 55,743,940,100;
- the Founder referral benefit is 34.2 units per cycle, not 17.1;
- the referral channel is a direct-mint channel capped at 2,500,020,000, not a
  Founder Node distribution channel capped at 1,250,010,000;
- a referral is unconditional, so `evaluate_referral_permission` and its
  `inactive_referral_result` research input disappear;
- an unreferred seat routes its referral allocation to a monthly performance
  pool; and
- activity and performance reallocation are derived rules rather than supplied
  research inputs.

## Required evidence

Completion requires all of the following:

1. An accepted `founder-economy-manifest-v2` whose ten channel caps sum
   exactly to 56,993,950,100 display units in the unchanged eight-decimal
   denomination, with fixed vectors and a digest.
2. A revised independent Python model implementing the v2 transitions,
   including the unconditional direct-mint referral and the unreferred
   performance pool, with the accepted M2 evidence method preserved.
3. Re-verified seat, routing, escrow, and scenario-suite models against v2,
   with every recorded digest regenerated and every verifier still failing
   closed.
4. An exact cycle boundary defined in chain heights or epochs, with no wall
   clock reachable from a transition.
5. Canonical state keys, transaction encodings, and numeric consensus receipt
   codes for seat activation, permission evaluation, permission exercise,
   referral issuance, and capped direct issuance, extending
   `protocol-primitives-v1` and `ledger-transition-v1`.
6. An exact compatibility boundary against accepted M1 transaction bytes,
   state, and roots.
7. A deterministic uptime record: validator duties derived from on-chain
   participation, resource provision proved by challenge-response, and a
   bounded AI dispute window whose expiry finalises a cycle without a
   signature.
8. Activity evaluated at 18 hours or more of cumulative fully operational
   uptime per cycle, with a fragmentable 6-hour grace allowance.
9. Performance reallocation to the highest uptime in the same cycle, split
   equally among exact ties, restricted to seats that met the cycle, with the
   integer remainder and any zero-winner cycle's whole permission going to the
   recovery pool, which the earliest subsequent winning cycle takes entirely.
   Revised on 2026-08-19 by ADR 0049; the requirement previously carried the
   remainder forward in a per-channel carry that nothing ever released.
10. C++20 implementation of the accepted v2 economy in the deterministic
    ledger kernel, with checked integer arithmetic and no floating point on any
    monetary or consensus path.
11. Cross-language fixed vectors that the C++ implementation and the
    independent Python model both reproduce exactly.
12. Storage bounds for per-seat balances, per-cycle uptime records, and
    recipient balances at 100,000 seats.
13. Adversarial four-node economic scenarios through restart and recovery,
    proving deterministic replica agreement on state roots.
14. Positive, negative, boundary, replay, overflow, atomicity, and multi-year
    scenarios against the v2 contract, at the standard the M2 suite set.
15. Accepted ADRs stating the selected consensus transition shape, encoding,
    compatibility boundary, and remaining independent review requirements.
16. Risk-proportionate GitHub-hosted verification on the exact accepted commit
    and a clean repository handoff naming the first M4 implementation slice.

## Founder-decision gate

The implementation must not invent eligibility or anti-abuse mechanics for the
liquidity-mining, impermanent-loss, HUB-verified-user, or mini-gamified
channels, nor the AI funding framework. If one is required to satisfy a test, use an
explicitly research-only bounded input and record the owner decision still
required.

Activity, performance ranking, referral treatment, and referral eligibility are
no longer open. They are decided in the Founder Constitution and ADR 0023 and
must be implemented as stated rather than re-litigated.

## Explicitly out of scope

- Production biometric capture, identity decisions, or private evidence
  storage.
- A production Founder Node installer, packaged all-in-one service, or
  validator-set change beyond the deterministic active-set protocol.
- AI inference, model serving, moderation, or real treasury authority.
- Controlled application execution or resource hosting.
- Real BTC, ETH, stablecoin custody, liquidity, pricing, or bridge proofs.
- Wallet, graphical interface, public testnet, mainnet, NodeOS, or hardware.

These systems remain roadmap commitments. Their constraints are inputs to this
goal, not premature implementation requirements.
