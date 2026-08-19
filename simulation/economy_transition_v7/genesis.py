"""Version-seven genesis bytes and chain identity.

The field table is version six's with a different schema version, a different
chain-ID label, and the version-three manifest digest, so the prefix is still
110 octets and the canonical object bound still admits 21,843 account entries
that no conforming genesis can reach.

**What changes in the economy is nine entries.** The ten `carry` entries are
gone and one `recovery_pool` entry with five zero legs replaces them, so genesis
writes fourteen where version six wrote twenty-three.

Zero genesis accounts is still required rather than expected, for version six's
reason: an account with no escrow entry has no identity behind it, which the
structural invariant forbids.
"""

from __future__ import annotations

from simulation.economy_transition.merkle import digest
from simulation.economy_transition_v6.genesis import (
    Genesis,
    InvalidGenesis,
    maximum_accounts_bound as _v6_maximum_accounts_bound,
    require_valid as _v6_require_valid,
)
from simulation.economy_transition_v6.envelope import u16, u32, u64

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


def encode(genesis: Genesis, schema_version: int = c.GENESIS_SCHEMA_VERSION) -> bytes:
    """Version six's field order under version seven's schema version.

    Re-encoded here rather than imported because version six's `encode` defaults
    to its own schema version and reads its own constants; the field order is the
    subject of the compatibility claim, so it is written where the claim is made
    and checked against version six's bytes by a vector.
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
        + u32(len(genesis.accounts))
    )
    if len(raw) != c.GENESIS_PREFIX_BYTES:
        raise InvalidGenesis("genesis prefix is not 110 octets")
    if len(raw) > c.MAX_OBJECT_BYTES:
        raise InvalidGenesis("genesis exceeds the canonical object bound")
    return raw


def require_valid(genesis: Genesis) -> None:
    """Version six's five refusals, unchanged and imported."""
    _v6_require_valid(genesis)


def chain_id(genesis: Genesis) -> bytes:
    return digest(c.CHAIN_ID_LABEL, encode(genesis))


def predecessor_chain_id(genesis: Genesis, version: int) -> bytes:
    """The same fields under an earlier schema and label, for comparison."""
    if version not in (2, 3, 4, 5, 6):
        raise InvalidGenesis(f"no predecessor chain ID for version {version}")
    return digest(
        f"protocol-stack:v{version}:chain-id", encode(genesis, schema_version=version)
    )


def maximum_accounts_bound() -> tuple[int, int, int]:
    """The inherited object bound, recorded rather than exercised."""
    return _v6_maximum_accounts_bound()


def initial_economy_entries(verifier_key: bytes) -> dict[bytes, bytes]:
    """The ten channels, the empty recovery pool, the verifier key, the empty
    unreferred pool, and the verified-user counter at zero: fourteen entries.

    Genesis writes nothing else: no seat, no identity, no escrow, no signer, no
    enrollment, no referral balance, no custody entry, and no cycle assignment.
    Writing the fixed tables explicitly is what keeps an absent entry
    unambiguous rather than making absence an implicit zero default.
    """
    from .settlement import empty_pool
    from .state import (
        channel_key,
        channel_value,
        recovery_pool_key,
        recovery_pool_value,
        unreferred_pool_key,
        unreferred_pool_value,
        verified_user_counter_key,
        verified_user_counter_value,
        verifier_key_key,
        verifier_key_value,
    )

    entries = {channel_key(index): channel_value(0, 0) for index in range(10)}
    entries[recovery_pool_key()] = recovery_pool_value(empty_pool())
    entries[verifier_key_key()] = verifier_key_value(verifier_key)
    entries[unreferred_pool_key()] = unreferred_pool_value(0, 0)
    entries[verified_user_counter_key()] = verified_user_counter_value(0)
    return entries
