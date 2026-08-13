"""Version-two genesis bytes and chain identity.

Three of version one's genesis requirements relax, and each is forced by founder
direction rather than chosen. The Founder Constitution states that native units
enter circulation only through issuance permissions and capped direct-mint
channels, so a conforming chain must open with zero total supply and zero
accounts, which version one forbids. The fixed fee relaxes to permit zero as the
consequence: with a zero allocation and a nonzero fee, no account can pay for the
first transaction, so the chain can never reach a state in which any fee is
payable.

The accepted manifest digest is a genesis field, so a chain whose channel table
differs is a different chain rather than the same chain with a different table.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import contract as c
from .envelope import MalformedTransaction, u16, u32, u64
from .merkle import digest


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
    accounts: list[tuple[bytes, int, int]] = field(default_factory=list)


def encode(genesis: Genesis) -> bytes:
    require_valid(genesis)
    raw = (
        c.GENESIS_MAGIC
        + u16(c.GENESIS_SCHEMA_VERSION)
        + u32(genesis.network_id)
        + u64(genesis.supply_limit)
        + u64(genesis.total_supply)
        + u64(genesis.fixed_transfer_fee)
        + u64(genesis.initial_fee_pool)
        + genesis.manifest_digest
        + u32(len(genesis.accounts))
    )
    if len(raw) != c.GENESIS_PREFIX_BYTES:
        raise InvalidGenesis("genesis prefix is not 78 octets")
    for account_id, balance, nonce in genesis.accounts:
        raw += account_id + u64(balance) + u64(nonce)
    if len(raw) > c.MAX_OBJECT_BYTES:
        raise InvalidGenesis("genesis exceeds the canonical object bound")
    return raw


def require_valid(genesis: Genesis) -> None:
    if type(genesis.manifest_digest) is not bytes or len(genesis.manifest_digest) != 32:
        raise MalformedTransaction("manifest digest is not 32 octets")
    if genesis.supply_limit == 0:
        raise InvalidGenesis("supply limit must be nonzero")
    if genesis.total_supply > genesis.supply_limit:
        raise InvalidGenesis("total supply exceeds the supply limit")
    if len(genesis.accounts) > c.MAX_GENESIS_ACCOUNTS:
        # Rejected before allocating account storage, as version one requires.
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


def initial_economy_entries() -> dict[bytes, bytes]:
    """The ten channel entries at zero and the performance carry at zero.

    Genesis writes nothing else: no seat, no permission, no custody entry, and
    no window result. Writing the fixed table explicitly is what keeps an absent
    entry unambiguous, rather than making absence an implicit zero default.
    """
    from .state import channel_key, channel_value, performance_carry_key
    from .state import performance_carry_value

    entries = {channel_key(index): channel_value(0, 0) for index in range(10)}
    entries[performance_carry_key()] = performance_carry_value(0)
    return entries
