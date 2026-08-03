# ADR 0016: Founder constitution and staged realization

- Status: Accepted project direction; not production protocol acceptance
- Date: 2026-08-03

## Context

The repository completed the Sovereign Devnet Alpha and then built several
independent M2 research models before the owner supplied the complete Founder
Seat, fixed-allocation, commercial-revenue, centralized AI, controlled-
application, and bridge direction. Existing documents correctly describe the
runnable research stack but contain older assumptions: production economics
are wholly open, node and validator roles may be unrelated, AI verifiers may
run on general nodes, and the bridge is a distant optional program.

Continuing those assumptions would let autonomous sessions optimize a research
model that is not the intended product. Directly treating the new figures as
live protocol constants would be equally unsound because their encoding,
transition rules, edge cases, simulations, and reviews do not yet exist.

## Decision

Adopt `../project/founder-constitution.md` as the authoritative statement of
founder intent. It fixes the desired product and names the owner-reserved
decisions. It does not override accepted bytes or claim unimplemented
behavior.

Realize the constitution in dependency order:

1. preserve and reconcile direction;
2. specify and independently simulate the complete Founder economy;
3. implement accepted economic behavior in the C++ devnet;
4. add Founder identity, seat, and node capability workflows;
5. package the all-in-one Founder service;
6. implement the bounded company-hosted AI control plane;
7. add the controlled application and resource network;
8. add the externally audited bridge, liquidity, wallet, and public testnet;
   and
9. pass the integrated production gate before a public launch.

The existing M2 simulators and ADRs remain accepted research evidence. Their
fixture values, generic participants, penalties, stake, threshold sets, and
reward mechanisms do not define production policy. New work should reuse their
auditable accounting and test methods where compatible and replace their
research assumptions through a new specification rather than rewriting their
frozen version-one contracts.

One logical Ecosystem AI runs on company-hosted infrastructure, never inside
consensus or on Founder Nodes. It may ultimately be the sole case-specific
decision source for a delegated workflow, while the deterministic protocol
still separates and bounds each capability. Redundant inference replicas are
an availability mechanism, not Founder or community voting.

All Founder Nodes carry full-node, validator, and resource-service capability.
A bounded deterministic active signer set remains necessary for scalable
consensus; being outside one signing round does not make validator capability
an optional service.

The bridge is specified early because Founder Seat enrollment and external
liquidity depend on it, but real custody is implemented late. BTC, ETH, and
approved stablecoins remain boundary inputs to a purchase, liquidity, swap, or
withdrawal workflow and never become general ledger currencies.

## Consequences

- Clean sessions have a durable north star and cannot replace founder choices
  with research defaults.
- The next milestone changes from open-ended reward-mechanism exploration to
  exact Founder-economy specification and proof.
- Existing runnable code and reproducible research are retained rather than
  falsely relabeled or discarded.
- Later AI, biometric, application, resource, and bridge interfaces influence
  today's specifications without forcing premature service implementation.
- Exact founder-directed amounts still require integer encoding, canonical
  transitions, failure behavior, deterministic models, threat analysis, and
  independent review before production acceptance.
- Autonomous development stops for the owner only when an unresolved choice
  would change constitutional value or authority and no other milestone work
  can safely continue.

## Supersession and compatibility

This ADR supersedes conflicting long-term topology or product assumptions in
project prose and proposed ADR 0003. It also supersedes ADR 0002 only where
that earlier record listed staking as an already intended production module;
Founder Seat admission is the current direction, and production staking or
slashing now requires a new founder decision. ADR 0002's one-native-asset,
native-module, and no-public-deployment decisions remain accepted.

This ADR does not change M1 transaction bytes, state roots, the configured
devnet supply, the research simulator schemas or digests, CometBFT behavior,
or any C++ transition.
