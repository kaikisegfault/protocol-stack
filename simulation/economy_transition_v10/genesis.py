"""Version-ten genesis bytes and chain identity.

Version nine's field table with the schema version at 10, `verifier_key` renamed
`launch_key` at the same offset, and **one field added**: `build_authority_key`
after `dispute_authority_key`. The prefix is 182 octets. `account_count` stays
last, because the account entries follow it.

**The launch key keeps the verifier key's offset and its state entry**, because
it is the same key in a narrower role. Entry kind 8, which version six named the
verifier key, holds it. Version nine's key signed every registration for the
chain's life. Version ten's signs only until the registry step retires it.

**The build authority is a third key and is not written to state.** It is a
genesis field bound into the chain identity, exactly as the dispute authority
key is. Retiring the key that admits people then changes nothing about who
admits machines.

**Genesis writes version nine's sixteen economy entries and no others.** It
writes no machine key, no owner entry, and no retirement.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from simulation.economy_transition.merkle import digest
from simulation.economy_transition_v6.envelope import MalformedTransaction, u16, u32, u64
from simulation.economy_transition_v6.genesis import InvalidGenesis
from simulation.economy_transition_v9 import genesis as v9genesis

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
    """Version nine's fields with the launch key renamed and a build key added.

    A distinct type rather than version nine's with an attribute bolted on,
    because the two are different lengths and neither decodes as the other.
    """

    network_id: int
    genesis_timestamp: int
    supply_limit: int
    fixed_transfer_fee: int
    manifest_digest: bytes
    launch_key: bytes
    dispute_authority_key: bytes
    build_authority_key: bytes
    total_supply: int = 0
    initial_fee_pool: int = 0
    accounts: list[tuple[bytes, int, int]] = field(default_factory=list)


def _as_v9(genesis: Genesis) -> v9genesis.Genesis:
    return v9genesis.Genesis(
        network_id=genesis.network_id,
        genesis_timestamp=genesis.genesis_timestamp,
        supply_limit=genesis.supply_limit,
        fixed_transfer_fee=genesis.fixed_transfer_fee,
        manifest_digest=genesis.manifest_digest,
        verifier_key=genesis.launch_key,
        dispute_authority_key=genesis.dispute_authority_key,
        total_supply=genesis.total_supply,
        initial_fee_pool=genesis.initial_fee_pool,
        accounts=genesis.accounts,
    )


def require_valid(genesis: Genesis) -> None:
    """Version nine's refusals, plus the one the added field brings."""
    v9genesis.require_valid(_as_v9(genesis))
    if (
        type(genesis.build_authority_key) is not bytes
        or len(genesis.build_authority_key) != c.BUILD_AUTHORITY_KEY_BYTES
    ):
        raise MalformedTransaction("build authority key is not 32 octets")


def encode(genesis: Genesis) -> bytes:
    """The encoder's field order, which is version nine's with one field added.

    `total_supply` is still written before `fixed_transfer_fee`, inherited four
    versions back, so a decoder reading declaration order would fail the
    round trip.
    """
    require_valid(genesis)
    raw = (
        c.GENESIS_MAGIC
        + u16(c.GENESIS_SCHEMA_VERSION)
        + u32(genesis.network_id)
        + u64(genesis.genesis_timestamp)
        + u64(genesis.supply_limit)
        + u64(genesis.total_supply)
        + u64(genesis.fixed_transfer_fee)
        + u64(genesis.initial_fee_pool)
        + genesis.manifest_digest
        + genesis.launch_key
        + genesis.dispute_authority_key
        + genesis.build_authority_key
        + u32(len(genesis.accounts))
    )
    if len(raw) != c.GENESIS_PREFIX_BYTES:
        raise InvalidGenesis("genesis prefix is not 182 octets")
    if len(raw) > c.MAX_OBJECT_BYTES:
        raise InvalidGenesis("genesis exceeds the canonical object bound")
    return raw


def chain_id(genesis: Genesis) -> bytes:
    return digest(c.CHAIN_ID_LABEL, encode(genesis))


def predecessor_chain_id(genesis: Genesis, version: int) -> bytes:
    """The same fields under every earlier schema and label.

    Version nine's is its own chain ID over its 150-octet prefix. Every earlier
    one is version nine's `predecessor_chain_id`. None carries the build
    authority key, so no version-ten genesis can be read as an earlier one,
    whatever the label does.
    """
    require_valid(genesis)
    if version == 9:
        return v9genesis.chain_id(_as_v9(genesis))
    return v9genesis.predecessor_chain_id(_as_v9(genesis), version)


def maximum_accounts_bound() -> tuple[int, int, int]:
    """The object bound under the wider prefix, recorded, never exercised."""
    return (c.MAX_OBJECT_BYTES, c.GENESIS_PREFIX_BYTES, c.MAX_GENESIS_ACCOUNTS)


def initial_economy_entries(genesis: Genesis) -> dict[bytes, bytes]:
    """Version nine's sixteen, with the launch key where the verifier key was."""
    entries = v9genesis.initial_economy_entries(_as_v9(genesis))
    if len(entries) != c.GENESIS_ECONOMY_ENTRY_COUNT:
        raise InvalidGenesis(
            f"genesis writes {len(entries)} economy entries, not "
            f"{c.GENESIS_ECONOMY_ENTRY_COUNT}"
        )
    return entries
