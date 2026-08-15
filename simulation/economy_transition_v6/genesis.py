"""Version-six genesis bytes and chain identity.

The field table is version four's with a different schema version and a different
chain-ID label, so the prefix is still 110 bytes and the canonical object bound
still admits 21,843 account entries. What changes is that a version-six chain has
a different chain ID from any earlier chain with identical fields, which is what
makes the six contracts alternative chains rather than one chain read six ways.

**Version six is the first to require zero genesis accounts rather than merely to
expect it.** Versions two through five permitted `0` through `21,843` while
recording that the no-genesis-allocation rule forces zero. A genesis account
would now be an account with no escrow entry and no identity behind it, which
violates a structural invariant, so the field is retained at zero for layout
compatibility and the 21,843 bound is inherited and unreachable.
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
    fixed_transfer_fee: int
    manifest_digest: bytes
    verifier_key: bytes
    total_supply: int = 0
    initial_fee_pool: int = 0
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
    if genesis.accounts:
        # An account with no escrow entry has no identity behind it, which the
        # structural invariant forbids. Version six does not merely expect the
        # constitution's zero allocation; it refuses anything else.
        raise InvalidGenesis("version-six genesis writes no accounts")
    if genesis.total_supply != 0:
        raise InvalidGenesis("version-six genesis opens with zero supply")
    if genesis.initial_fee_pool != 0:
        raise InvalidGenesis("a nonzero fee pool is a genesis allocation")


def chain_id(genesis: Genesis) -> bytes:
    return digest(c.CHAIN_ID_LABEL, encode(genesis))


def predecessor_chain_id(genesis: Genesis, version: int) -> bytes:
    """The same fields under an earlier schema and label, for comparison."""
    if version not in (2, 3, 4, 5):
        raise InvalidGenesis(f"no predecessor chain ID for version {version}")
    return digest(
        f"protocol-stack:v{version}:chain-id", encode(genesis, schema_version=version)
    )


def maximum_accounts_bound() -> tuple[int, int, int]:
    """The inherited object bound, recorded rather than exercised.

    Returns the entry count the prefix admits and the two byte figures that
    bracket it. No version-six genesis can reach it, because the account count
    is required to be zero; the derivation is recorded so its unreachability is
    a stated consequence rather than a silence.
    """
    admitted = c.MAX_GENESIS_ACCOUNTS
    within = c.GENESIS_PREFIX_BYTES + c.ACCOUNT_ENTRY_BYTES * admitted
    beyond = c.GENESIS_PREFIX_BYTES + c.ACCOUNT_ENTRY_BYTES * (admitted + 1)
    return admitted, within, beyond


def initial_economy_entries(verifier_key: bytes) -> dict[bytes, bytes]:
    """The ten channels, the ten carries, the verifier key, the empty pool, and
    the verified-user counter at zero.

    Genesis writes nothing else: no seat, no identity, no escrow, no signer, no
    enrollment, no referral balance, no custody entry, and no cycle assignment.
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
        verified_user_counter_key,
        verified_user_counter_value,
        verifier_key_key,
        verifier_key_value,
    )

    entries = {channel_key(index): channel_value(0, 0) for index in range(10)}
    entries.update({carry_key(index): carry_value(0) for index in range(10)})
    entries[verifier_key_key()] = verifier_key_value(verifier_key)
    entries[unreferred_pool_key()] = unreferred_pool_value(0, 0)
    entries[verified_user_counter_key()] = verified_user_counter_value(0)
    return entries
