# ADR 0002: Native single-asset economy

- Status: Accepted
- Date: 2026-07-23

## Context

The ecosystem is intended to use one native unit. Arbitrary stateful smart
contracts can create secondary balance systems even when they do not expose a
standard token interface.

## Decision

Implement accounts, supply, fees, treasury, venture escrow, general escrow,
staking, validator rules, node-distribution rules, authority, and future bridge
capabilities as native C++ protocol modules.

Do not provide public contract deployment, a public asset-issuance operation,
or an EVM in M1. Any later execution runtime requires an ADR addressing the
single-asset invariant and capability restrictions.

## Consequences

- Root economics are deterministic and directly auditable.
- Protocol upgrades carry greater responsibility because application behavior
  cannot be delegated to replaceable public contracts.
- Application extensibility is deliberately restricted.
- Exact economic parameters still require specifications, simulations, and
  owner acceptance before becoming immutable.
