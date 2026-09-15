"""Version-nine genesis bytes and chain identity.

The field table is version eight's with a different schema version, a different
chain-ID label, and **one field added**: a `u64` `genesis_timestamp` immediately
after the network identifier. The prefix is 150 octets rather than 142 and the
canonical object bound still admits 21,842 account entries that no conforming
genesis can reach, because 48-octet account entries absorb eight more prefix
octets without crossing an entry boundary.

**The timestamp sits with the network identifier rather than among the monetary
fields**, because it is part of what identifies this chain rather than part of
what it is worth, and `account_count` stays last, which it must: the account
entries follow it.

**Genesis validation applies `calendar-v1`'s range rule and reads no clock.**
That is forced rather than chosen: the chain identity is a hash of the genesis
bytes, so a validity rule that read a clock would make two machines disagree
about a chain's own identifier. A genesis timestamp in the future is therefore
well-formed, and the chain simply cannot produce its first block until civil time
reaches it — the refusal a machine reports there is `TIMESTAMP_NOT_MONOTONIC`,
because `calendar-v1`'s ordered conditions reach monotonicity before tolerance.
This is the open item that specification left to its binding version.

**The economy is sixteen entries rather than version eight's fourteen.** The
settlement cursor and window zero's month both carry `month_index(g)`. Window
zero's opening height is height zero, which no chain ever has — a chain starts at
height one — so genesis is its opening height and writing its month here is the
general rule reaching the one height that is a genesis rather than a block. The
unreferred pool is written with its three quantities at zero.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from simulation.calendar import months as calendar_months
from simulation.economy_transition.merkle import digest
from simulation.economy_transition_v6.envelope import MalformedTransaction, u16, u32, u64
from simulation.economy_transition_v6.genesis import InvalidGenesis
from simulation.economy_transition_v8.genesis import (
    Genesis as GenesisV8,
    require_valid as _v8_require_valid,
)

from . import contract as c
from .state import (
    settlement_cursor_key,
    settlement_cursor_value,
    unreferred_pool_key,
    unreferred_pool_value,
    window_month_key,
    window_month_value,
)

__all__ = [
    "GENESIS_WINDOW",
    "Genesis",
    "InvalidGenesis",
    "chain_id",
    "encode",
    "genesis_month",
    "initial_economy_entries",
    "maximum_accounts_bound",
    "predecessor_chain_id",
    "require_valid",
]

# The window whose opening height is genesis. No seat is ever in scope for it,
# because `first_cycle_window` is at least one, so it accrues nothing and its
# assignment is a complete no-op for the monthly settlement.
GENESIS_WINDOW = 0


@dataclass(frozen=True)
class Genesis:
    """Version eight's fields with the genesis timestamp added.

    It is a distinct type rather than version eight's with an attribute bolted
    on, because a version-eight genesis and a version-nine genesis are different
    lengths and neither decodes as the other.
    """

    network_id: int
    genesis_timestamp: int
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

    `total_supply` is written before `fixed_transfer_fee`, inherited three
    versions back. A decoder that read them in declaration order would produce a
    genesis whose re-encoding differs, which is exactly what the round-trip rule
    refuses.
    """
    require_valid(genesis)
    raw = (
        c.GENESIS_MAGIC
        + u16(schema_version)
        + u32(genesis.network_id)
        + u64(genesis.genesis_timestamp)
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
        raise InvalidGenesis("genesis prefix is not 150 octets")
    if len(raw) > c.MAX_OBJECT_BYTES:
        raise InvalidGenesis("genesis exceeds the canonical object bound")
    return raw


def require_valid(genesis: Genesis) -> None:
    """Version eight's six refusals, plus the one the added field brings."""
    _v8_require_valid(
        GenesisV8(
            network_id=genesis.network_id,
            supply_limit=genesis.supply_limit,
            fixed_transfer_fee=genesis.fixed_transfer_fee,
            manifest_digest=genesis.manifest_digest,
            verifier_key=genesis.verifier_key,
            dispute_authority_key=genesis.dispute_authority_key,
            total_supply=genesis.total_supply,
            initial_fee_pool=genesis.initial_fee_pool,
            accounts=genesis.accounts,
        )
    )
    if type(genesis.genesis_timestamp) is not int or not (
        c.MIN_TIMESTAMP_MILLIS <= genesis.genesis_timestamp <= c.MAX_TIMESTAMP_MILLIS
    ):
        raise MalformedTransaction(
            "genesis timestamp is outside calendar-v1's accepted range"
        )


def genesis_month(genesis: Genesis) -> int:
    """`calendar-v1`'s month index of the genesis timestamp.

    Read through the accepted calendar model rather than recomputed, which is
    the same binding `simulation.unreferred_pool` makes: this version owns no
    opinion about a date.
    """
    return calendar_months.month_index(genesis.genesis_timestamp)


def chain_id(genesis: Genesis) -> bytes:
    return digest(c.CHAIN_ID_LABEL, encode(genesis))


def predecessor_chain_id(genesis: Genesis, version: int) -> bytes:
    """The same fields under an earlier schema and label, for comparison.

    Version eight and earlier carry no timestamp, so the predecessor bytes are
    the 142- or 110-octet prefix without it. That is the point of the comparison:
    the objects are different lengths, so no version-nine genesis can be read as
    an earlier one whatever the label does.
    """
    if version not in (2, 3, 4, 5, 6, 7, 8):
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
    )
    if version == 8:
        raw += genesis.dispute_authority_key
    raw += u32(len(genesis.accounts))
    return digest(f"protocol-stack:v{version}:chain-id", raw)


def maximum_accounts_bound() -> tuple[int, int, int]:
    """The object bound under the wider prefix, recorded rather than exercised."""
    return (c.MAX_OBJECT_BYTES, c.GENESIS_PREFIX_BYTES, c.MAX_GENESIS_ACCOUNTS)


def initial_economy_entries(genesis: Genesis) -> dict[bytes, bytes]:
    """Version eight's fourteen entries, with kind 12 rewidened and two added.

    The fourteen are imported rather than restated, so a vector can require the
    twelve this version does not touch to be byte-identical to the accepted ones
    rather than merely to look alike. Two of the fourteen are replaced here: the
    unreferred pool, whose value gains `payable`, and nothing else.
    """
    from simulation.economy_transition_v8.genesis import (
        initial_economy_entries as _v8_initial,
    )

    entries = dict(_v8_initial(genesis.verifier_key))
    entries[unreferred_pool_key()] = unreferred_pool_value(0, 0, 0)
    month = genesis_month(genesis)
    entries[settlement_cursor_key()] = settlement_cursor_value(month)
    entries[window_month_key(GENESIS_WINDOW)] = window_month_value(month)
    if len(entries) != c.GENESIS_ECONOMY_ENTRY_COUNT:
        raise InvalidGenesis(
            f"genesis writes {len(entries)} economy entries, not "
            f"{c.GENESIS_ECONOMY_ENTRY_COUNT}"
        )
    return entries
