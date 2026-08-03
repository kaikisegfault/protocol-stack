# ADR 0002: Native single-asset economy

- Status: Accepted; production staking assumption superseded by ADR 0016
- Date: 2026-07-23

## Context

The ecosystem is intended to use one native unit. Arbitrary stateful smart
contracts can create secondary balance systems even when they do not expose a
standard token interface.

## Decision

Implement accounts, supply, fees, treasury, venture escrow, general escrow,
validator rules, node-distribution rules, authority, and future bridge
capabilities as native C++ protocol modules. Founder Seat admission is the
current validator direction. Production staking, slashing, or monetary
penalties require a separate founder decision under ADR 0016.

Do not provide public contract deployment, a public asset-issuance operation,
or an EVM in M1. Any later execution runtime requires an ADR addressing the
single-asset invariant and capability restrictions.

## Consequences

- Root economics are deterministic and directly auditable.
- Protocol upgrades carry greater responsibility because application behavior
  cannot be delegated to replaceable public contracts.
- Application extensibility is deliberately restricted.
- Exact economic parameters still require specifications, simulations, an
  accepted ADR, and independent review before becoming immutable.
