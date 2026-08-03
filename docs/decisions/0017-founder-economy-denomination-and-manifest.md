# ADR 0017: Founder Economy denomination and fixed manifest

- Status: Accepted for M2 specification; not a consensus activation
- Date: 2026-08-03

## Context

The Founder Constitution fixes a 55,743,940,100-display-unit maximum, ten
issuance-channel caps, and per-cycle amounts down to one tenth of a display
unit. M1 uses nine decimal places and unsigned 64-bit monetary state, but the
founder-fixed maximum multiplied by `10^9` is
55,743,940,100,000,000,000, which exceeds `u64` maximum
18,446,744,073,709,551,615. Reusing the M1 denomination would therefore make
the intended maximum unrepresentable in the accepted primitive type.

M2 also needs one reviewed machine-readable manifest before an independent
simulator can consume the founder values. Its amounts exceed the integer range
that generic JSON implementations reliably preserve, so a bare JSON number is
not an interoperable monetary representation.

Primary specifications informed the alternatives:

- Cosmos SDK ADR 024 separates the smallest state-machine denomination from
  client display denominations and assigns an explicit exponent. This supports
  making the atomic/display relationship manifest data rather than an implicit
  wallet assumption. Source: [Cosmos SDK ADR 024][cosmos-denomination].
- Ethereum consensus represents Gwei balances as typed integers and uses
  `uint64`-bounded state rather than floating-point monetary values. This is
  comparative evidence for a fixed integer denomination, not a dependency or
  adoption of Ethereum economics. Source: [Ethereum Phase 0][ethereum-phase0].
- RFC 8785 defines deterministic JSON Canonicalization Scheme bytes and
  recommends JSON strings for integers that need more precision than IEEE 754
  binary64 can reliably provide. Source: [RFC 8785][rfc8785].

## Decision

### Atomic denomination

Use 100,000,000 atomic units per display unit for the Founder Economy target:

```text
decimal places                 = 8
atomic units per display unit  = 100,000,000
maximum supply atomic          = 5,574,394,010,000,000,000
u64 maximum                    = 18,446,744,073,709,551,615
```

Eight decimal places is the greatest base-10 precision that fits the
founder-fixed maximum in `u64`: integer division gives
`u64_max / 55,743,940,100 = 330,919,271`, so `10^8` fits and `10^9` does not.
It exactly represents every founder-fixed whole and tenth-display-unit amount
while retaining more granularity than the current schedule requires.

All stored, journaled, compared, and hashed monetary values are unsigned atomic
integers. Display decimals are presentation only. Every conversion and derived
product uses checked arithmetic and rejects overflow; no implementation may
use floating point to recreate an atomic value.

### Fixed manifest

Adopt
[`founder-economy-manifest-v1.json`](../../test-vectors/founder-economy-manifest-v1.json)
as the one fixed M2 input containing:

- the denomination and maximum;
- the 100,000-seat, 1,000-seats-per-person, and 731-cycle limits;
- all ten channel identifiers, issuance kinds, and atomic caps;
- every leg of the 574.3-unit base permission;
- the 17.1-unit referral permission; and
- explicit names for the four unresolved research inputs.

The pretty-printed checked-in JSON is transport text. Canonical bytes are its
RFC 8785 JCS representation. Monetary values are shortest unsigned base-10
strings without leading zeroes so parsers cannot first round them through a
JSON number. Counts that never exceed 100,000 remain JSON integers.

The manifest digest is SHA-256 over the protocol `D(label)` encoding for
`protocol-stack:founder-economy:manifest-v1` followed by the canonical JSON
bytes. This reuses the accepted hash primitive and domain-separation shape; it
does not introduce cryptography.

### Permission liabilities

An unexercised Founder permission is reserved issuance capacity, not issued
supply. Each channel tracks issued atomic units and outstanding permission
liabilities such that:

```text
channel_issued + channel_outstanding <= channel_cap
```

Creating a permission reserves every included leg atomically. Exercising it
decreases every matching outstanding amount, increases every matching issued
amount, and credits all typed beneficiaries in one balanced operation. A
failed or replayed operation changes neither value nor replay state. A
permission has no expiry in this contract, so accumulated value is neither
issued early nor silently discarded.

Base and referral permissions are separate records. Referral-cap failure can
therefore never cancel a valid base permission. Direct channels issue through
a separately replay-protected transition and never share the Founder
permission authority.

### Unresolved eligibility

The fixed manifest names, but does not decide, the activity result,
inactive-cycle performance allocation, inactive referral eligibility, and
direct-channel eligibility. M2 simulation must receive these as explicit,
bounded, deterministic research inputs. M3 cannot treat those fixtures as
production policy or allow mutable external data, wall time, or model inference
to decide consensus.

## Alternatives not selected

- **One decimal place:** this is the minimum precision needed by the current
  schedule and maximizes numeric headroom, but prematurely prevents smaller
  future fees and application prices even though `u64` safely permits eight
  places.
- **Six decimal places:** this common compromise fits and exceeds the current
  schedule, but leaves two safe decimal places unused without reducing the
  accepted integer width or implementation complexity.
- **Retain M1 nine-decimal PSU units:** the maximum overflows `u64`; lowering
  the maximum would violate founder direction and saturating or wrapped
  arithmetic would violate conservation.
- **Adopt `u128` or arbitrary-width integers:** either could retain nine or
  more decimals, but would add a new primitive, encoding, cross-language, and
  storage migration before the existing `u64` option is exhausted. It can be
  reconsidered only through a separate protocol version.
- **Store monetary values as JSON numbers:** values above the interoperable
  exact-integer range can be rounded by common parsers before validation or
  hashing. Canonical decimal strings preserve the intended `u64` value.
- **Make the pretty file bytes canonical:** insignificant formatting changes
  would change the digest. JCS preserves semantic JSON while producing one
  deterministic hash input.
- **Issue each permission immediately:** accumulated permissions would become
  circulating supply before exercise and could not satisfy the founder rule
  that unexercised units do not exist.
- **Reserve only at exercise:** multiple accumulated permissions could promise
  more than a channel cap. Reservation makes the liability and remaining
  capacity explicit at creation.

## Consequences

- The fixed maximum and all constitutional amounts fit `u64`, and precision
  nine has an explicit overflow vector.
- The complete Founder base schedule derives five base-channel caps exactly;
  the full referred-seat schedule derives the referral cap exactly.
- The manifest can be hashed and exchanged without losing atomic values in
  generic JSON stacks.
- Outstanding permissions are visible liabilities but are excluded from
  issued and circulating supply until atomic exercise.
- Eligibility evidence remains an explicit unresolved boundary instead of an
  invented founder policy.
- The manifest selects future economic parameters but activates nothing. M1
  genesis, transaction bytes, supply, state roots, fee behavior, C++ code, and
  accepted research simulator schemas remain unchanged.

## Compatibility and independent review

The Founder Economy denomination is incompatible with the current M1
nine-decimal genesis constants. Any M3 implementation requires a new state and
transition version, explicit chain activation or new-genesis decision,
canonical C++ encodings, migration and cross-language vectors, and rollback
behavior. Existing version-one identifiers and bytes must never be
reinterpreted.

This ADR and its fixed vectors establish exact accounting inputs, not economic
or production safety. Activity, performance, referral, and direct-channel
policies still require founder decisions where reserved, adversarial
simulation, and independent economic and protocol review before activation.

[cosmos-denomination]: https://docs.cosmos.network/sdk/v0.53/build/architecture/adr-024-coin-metadata
[ethereum-phase0]: https://ethereum.github.io/consensus-specs/phase0/beacon-chain/
[rfc8785]: https://www.rfc-editor.org/rfc/rfc8785.html
