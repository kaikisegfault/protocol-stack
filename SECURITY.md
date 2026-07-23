# Security policy

## Project status

`protocol-stack` is pre-alpha research software. It is not ready to hold real
funds or support production infrastructure.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability that could endanger
funds, keys, consensus, supply, authority, bridge behavior, or node operators.

Use the repository's private GitHub security-advisory reporting flow. Include:

- affected commit and component;
- prerequisites and impact;
- minimal reproduction or test case;
- whether exploitation has been observed;
- any proposed mitigation.

Avoid including real secrets, personal data, or live production targets.

## Scope

Security-sensitive areas include canonical encoding, cryptography integration,
state transition, monetary arithmetic, supply, fee routing, treasury, escrow,
staking, validator and node rewards, persistence, consensus adapters, AI
authority envelopes, upgrades, and bridges.

There is no bug bounty unless the repository owner publishes one separately.
