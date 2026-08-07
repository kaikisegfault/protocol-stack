# Completed operational goal: Founder Economy Proof

Status: complete; retained as the historical M2 acceptance contract

All sixteen requirements below passed against `founder-economy-manifest-v1` and
the five models built on it. The evidence and its limits are recorded in
[`../founder-economy-report-v1.md`](../founder-economy-report-v1.md).

The founder direction these requirements encode was revised on 2026-08-07 by
[ADR 0023](../../decisions/0023-founder-decisions-activity-referrals-and-supply.md):
the maximum supply became 56,993,950,100, the referral benefit doubled and moved
to the direct-mint channels, and the activity and performance rules that
requirements 3 and 6 left to supplied research inputs are now decided. The
figures below are therefore historical. They are retained unedited because they
state what was actually proved, and rewriting them would destroy that evidence.

## Objective

Produce an exact, reproducible, independent specification and simulator for
the founder-directed native economy before changing C++ consensus behavior.

From one reviewed manifest and deterministic event set, the model must prove
the 55,743,940,100-unit maximum, every channel cap, per-seat 731-cycle
issuance, commercial and fee routing, escrow conservation, inactive-seat
beneficiary change, accumulated permissions, and cap exhaustion without
floating point or mutable external inputs.

## Required evidence

Completion requires all of the following:

1. A canonical integer denomination whose atomic-unit maximum exactly
   represents 55,743,940,100 display units without overflow.
2. A versioned manifest containing every Founder Node and direct-mint channel
   cap from the Founder Constitution; its components sum exactly to the
   maximum.
3. Exact per-seat activation and 731-cycle eligibility semantics represented
   by deterministic heights or epochs rather than local time.
4. A 574.3-unit base-permission transition that atomically routes 171, 34.2,
   17.1, 10, and 342 display units to their typed beneficiaries.
5. Referred-seat permission accounting bounded by the 1,250,010,000-unit
   referral-channel cap.
6. Inactive-cycle behavior that preserves the non-Founder beneficiaries and
   changes only the 342-unit Founder beneficiary through a deterministic,
   separately supplied performance result.
7. Permission accumulation and later exercise where unexercised units are not
   issued supply and one exercise either completes every credit or changes no
   state.
8. Exact 100,000-seat and 1,000-seats-per-person limits plus price-schedule
   test vectors, including the USD 100 first block, USD 1,000 boundary, USD
   91,900 final block, and USD 4,231,855,000 derived full-sale proceeds.
9. Commercial-payment routing of 45% to eligible Founders, 45% to the creator
   side, and 10% to the System Creator, including the 22.5/22.5 project/product
   case and explicit integer remainder behavior.
10. Separate transaction-fee routing of 100% to eligible Founders without burn
    or deduction from commercial revenue.
11. Separate venture, community-grant, and developer escrows whose balances
    cannot be spent through the issuance capability and whose accepted payouts
    cannot exceed available custody.
12. Capped direct-mint transitions with deterministic placeholder eligibility
    evidence; unresolved real eligibility policy is not invented.
13. Positive, negative, boundary, replay, overflow, atomicity, population-
    change, inactivity, concentration, and complete multi-year scenarios.
14. An independent standard-library Python implementation, frozen fixtures and
    digests, and a report that distinguishes proved accounting from unresolved
    policy and production safety.
15. An accepted ADR stating the selected economic transition shape,
    alternatives, consequences, compatibility boundary, and remaining
    independent review requirements.
16. Risk-proportionate GitHub-hosted verification on the exact accepted commit
    and a clean repository handoff naming the first M3 implementation slice.

## Founder-decision gate

The implementation must not invent the activity grace period, performance
winner count or tie rule, inactive-seat referral treatment, direct-channel
eligibility, stablecoin governance, or legacy and AI frameworks. If one is
required to satisfy a test, use an explicitly research-only bounded input and
record the owner decision still required.

## Explicitly out of scope

- Changing C++ ledger bytes, state, roots, or devnet economics.
- Production biometric capture, identity decisions, or private evidence
  storage.
- A production Founder Node installer or validator-set change.
- AI inference, model serving, moderation, or real treasury authority.
- Controlled application execution or resource hosting.
- Real BTC, ETH, stablecoin custody, liquidity, pricing, or bridge proofs.
- Wallet, graphical interface, public testnet, mainnet, NodeOS, or hardware.

These systems remain roadmap commitments. Their constraints are inputs to this
goal, not premature implementation requirements.
