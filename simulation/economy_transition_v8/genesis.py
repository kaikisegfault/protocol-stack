"""Version-eight genesis bytes and chain identity.

The field table is version seven's with a different schema version, a different
chain-ID label, and **one field added**: a 32-octet `dispute_authority_key`
immediately after the ecosystem verifier key. The prefix is 142 octets rather
than 110 and the canonical object bound admits 21,842 account entries that no
conforming genesis can reach.

**The two keys are separate on purpose.** Whoever attests HUB identities should
not thereby acquire the power to void a machine's uptime; least privilege costs
32 octets here. It is the pre-pivot single-key shape `uptime-measurement-v1`
names, and ADR 0048's registry of per-machine attestation keys replaces it in a
later transition version.

**The economy is version seven's fourteen entries, unchanged.** The dispute
authority key is a genesis field bound into the chain identity, not a state
entry, exactly as `network_id` and `supply_limit` are. Genesis writes no open
challenge and no seat window record: a challenge is issued by a block and a
window record exists only once a seat has lost or had a slot voided.

Zero genesis accounts is still required rather than expected, for version six's
reason: an account with no escrow entry has no identity behind it, which the
structural invariant forbids.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from simulation.economy_transition.merkle import digest
from simulation.economy_transition_v6.envelope import MalformedTransaction, u16, u32, u64
from simulation.economy_transition_v6.genesis import InvalidGenesis
from simulation.economy_transition_v7.genesis import (
    Genesis as GenesisV7,
    require_valid as _v7_require_valid,
)

from . import contract as c

__all__ = [
    "Genesis",
    "InvalidGenesis",
    "chain_id",
    "encode",
    "initial_economy_entries",
    "maximum_accounts_bound",
    "predecessor_chain_id",
    "require_valid",
]


@dataclass(frozen=True)
class Genesis:
    """Version seven's fields with the dispute authority key added.

    It is a distinct type rather than version seven's with an attribute bolted
    on, because a version-seven genesis and a version-eight genesis are
    different lengths and neither decodes as the other.
    """

    network_id: int
    supply_limit: int
    fixed_transfer_fee: int
    manifest_digest: bytes
    verifier_key: bytes
    dispute_authority_key: bytes
    total_supply: int = 0
    initial_fee_pool: int = 0
    accounts: list[tuple[bytes, int, int]] = field(default_factory=list)


def encode(genesis: Genesis, schema_version: int = c.GENESIS_SCHEMA_VERSION) -> bytes:
    """The encoder's field order, which is not the declaration's.

    `total_supply` is written before `fixed_transfer_fee`, inherited from
    version six. A decoder that read them in declaration order would produce a
    genesis whose re-encoding differs, which is exactly what the round-trip rule
    refuses.
    """
    require_valid(genesis)
    raw = (
        c.GENESIS_MAGIC
        + u16(schema_version)
        + u32(genesis.network_id)
        + u64(genesis.supply_limit)
        + u64(genesis.total_supply)
        + u64(genesis.fixed_transfer_fee)
        + u64(genesis.initial_fee_pool)
        + genesis.manifest_digest
        + genesis.verifier_key
        + genesis.dispute_authority_key
        + u32(len(genesis.accounts))
    )
    if len(raw) != c.GENESIS_PREFIX_BYTES:
        raise InvalidGenesis("genesis prefix is not 142 octets")
    if len(raw) > c.MAX_OBJECT_BYTES:
        raise InvalidGenesis("genesis exceeds the canonical object bound")
    return raw


def require_valid(genesis: Genesis) -> None:
    """Version seven's five refusals, plus the one the added field brings."""
    _v7_require_valid(
        GenesisV7(
            network_id=genesis.network_id,
            supply_limit=genesis.supply_limit,
            fixed_transfer_fee=genesis.fixed_transfer_fee,
            manifest_digest=genesis.manifest_digest,
            verifier_key=genesis.verifier_key,
            total_supply=genesis.total_supply,
            initial_fee_pool=genesis.initial_fee_pool,
            accounts=genesis.accounts,
        )
    )
    if (
        type(genesis.dispute_authority_key) is not bytes
        or len(genesis.dispute_authority_key) != c.DISPUTE_AUTHORITY_KEY_BYTES
    ):
        raise MalformedTransaction("dispute authority key is not 32 octets")


def chain_id(genesis: Genesis) -> bytes:
    return digest(c.CHAIN_ID_LABEL, encode(genesis))


def predecessor_chain_id(genesis: Genesis, version: int) -> bytes:
    """The same fields under an earlier schema and label, for comparison.

    Version seven and earlier have no dispute authority key, so the predecessor
    bytes are the 110-octet prefix without it. That is the point of the
    comparison: the two objects are different lengths, so no version-eight
    genesis can be read as an earlier one whatever the label does.
    """
    if version not in (2, 3, 4, 5, 6, 7):
        raise InvalidGenesis(f"no predecessor chain ID for version {version}")
    require_valid(genesis)
    raw = (
        c.GENESIS_MAGIC
        + u16(version)
        + u32(genesis.network_id)
        + u64(genesis.supply_limit)
        + u64(genesis.total_supply)
        + u64(genesis.fixed_transfer_fee)
        + u64(genesis.initial_fee_pool)
        + genesis.manifest_digest
        + genesis.verifier_key
        + u32(len(genesis.accounts))
    )
    return digest(f"protocol-stack:v{version}:chain-id", raw)


def maximum_accounts_bound() -> tuple[int, int, int]:
    """The object bound under the wider prefix, recorded rather than exercised."""
    return (
        c.MAX_OBJECT_BYTES,
        c.GENESIS_PREFIX_BYTES,
        c.MAX_GENESIS_ACCOUNTS,
    )


def initial_economy_entries(verifier_key: bytes) -> dict[bytes, bytes]:
    """Version seven's fourteen entries, imported rather than restated.

    Version eight adds two entry kinds and writes neither at genesis, so the
    initial economy is exactly the accepted one and a vector can require the two
    to be equal rather than merely to look alike.
    """
    from simulation.economy_transition_v7.genesis import (
        initial_economy_entries as _v7_initial,
    )

    return _v7_initial(verifier_key)
