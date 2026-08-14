"""Version-four genesis bytes and chain identity.

The field table is version three's with a different schema version and a
different chain-ID label, so the prefix is still 110 bytes and the canonical
object bound still admits 21,843 account entries. What changes is that a
version-four chain has a different chain ID from any earlier chain with
identical fields, which is what makes the four contracts alternative chains
rather than one chain read four ways.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from simulation.economy_transition.merkle import digest

from . import contract as c
from .envelope import MalformedTransaction, u16, u32, u64


class InvalidGenesis(ValueError):
    """Genesis bytes no conforming deployment could produce."""


@dataclass(frozen=True)
class Genesis:
    network_id: int
    supply_limit: int
    total_supply: int
    fixed_transfer_fee: int
    initial_fee_pool: int
    manifest_digest: bytes
    verifier_key: bytes
    accounts: list[tuple[bytes, int, int]] = field(default_factory=list)


def encode(genesis: Genesis, schema_version: int = c.GENESIS_SCHEMA_VERSION) -> bytes:
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
        + u32(len(genesis.accounts))
    )
    if len(raw) != c.GENESIS_PREFIX_BYTES:
        raise InvalidGenesis("genesis prefix is not 110 octets")
    for account_id, balance, nonce in genesis.accounts:
        raw += account_id + u64(balance) + u64(nonce)
    if len(raw) > c.MAX_OBJECT_BYTES:
        raise InvalidGenesis("genesis exceeds the canonical object bound")
    return raw


def require_valid(genesis: Genesis) -> None:
    if type(genesis.manifest_digest) is not bytes or len(genesis.manifest_digest) != 32:
        raise MalformedTransaction("manifest digest is not 32 octets")
    if type(genesis.verifier_key) is not bytes or len(genesis.verifier_key) != 32:
        raise MalformedTransaction("ecosystem verifier key is not 32 octets")
    if genesis.supply_limit == 0:
        raise InvalidGenesis("supply limit must be nonzero")
    if genesis.total_supply > genesis.supply_limit:
        raise InvalidGenesis("total supply exceeds the supply limit")
    if len(genesis.accounts) > c.MAX_GENESIS_ACCOUNTS:
        raise InvalidGenesis(
            f"account count above the {c.MAX_GENESIS_ACCOUNTS}-entry object bound"
        )
    previous: bytes | None = None
    accumulated = genesis.initial_fee_pool
    for account_id, balance, nonce in genesis.accounts:
        if type(account_id) is not bytes or len(account_id) != 32:
            raise MalformedTransaction("account ID is not 32 octets")
        if previous is not None and account_id <= previous:
            raise InvalidGenesis("genesis account IDs are not strictly increasing")
        previous = account_id
        if balance == 0:
            raise InvalidGenesis("genesis balances must be nonzero")
        if nonce != 0:
            raise InvalidGenesis("genesis nonces must be zero")
        accumulated += balance
    if accumulated != genesis.total_supply:
        raise InvalidGenesis("balances plus the fee pool do not equal total supply")


def chain_id(genesis: Genesis) -> bytes:
    return digest(c.CHAIN_ID_LABEL, encode(genesis))


def predecessor_chain_id(genesis: Genesis, version: int) -> bytes:
    """The same fields under an earlier schema and label, for comparison."""
    if version not in (2, 3):
        raise InvalidGenesis(f"no predecessor chain ID for version {version}")
    return digest(
        f"protocol-stack:v{version}:chain-id", encode(genesis, schema_version=version)
    )


def initial_economy_entries(verifier_key: bytes) -> dict[bytes, bytes]:
    """The ten channels, the ten carries, the verifier key, and the empty pool.

    Genesis writes nothing else: no seat, no manager, no HUB identity, no HUB
    address, no referral balance, no custody entry, and no cycle assignment.
    Writing the fixed tables explicitly is what keeps an absent entry
    unambiguous rather than making absence an implicit zero default.
    """
    from .state import (
        carry_key,
        carry_value,
        channel_key,
        channel_value,
        unreferred_pool_key,
        unreferred_pool_value,
        verifier_key_key,
        verifier_key_value,
    )

    entries = {channel_key(index): channel_value(0, 0) for index in range(10)}
    entries.update({carry_key(index): carry_value(0) for index in range(10)})
    entries[verifier_key_key()] = verifier_key_value(verifier_key)
    entries[unreferred_pool_key()] = unreferred_pool_value(0, 0)
    return entries
