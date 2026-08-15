"""Version-five genesis bytes and chain identity.

The field table is version four's, so the prefix is still 110 octets and the
canonical object bound still admits 21,843 account entries. Version four's
encoder already takes the schema version as an argument, so version five sets
it rather than restating a table it does not change.

What differs is that the same fields under a version-five schema and label give
a different chain ID from any earlier chain. That is what makes the five
contracts alternative chains rather than one chain read five ways, and it is
why a version-four kind-11 transaction — which is a valid version-five kind-11
transaction by shape and a different one by meaning — can never execute under
version-five rules: the chain ID inside its signature preimage binds it to one
chain.
"""

from __future__ import annotations

from simulation.economy_transition.merkle import digest
from simulation.economy_transition_v4 import genesis as v4
from simulation.economy_transition_v4.genesis import (
    Genesis,
    InvalidGenesis,
    initial_economy_entries,
    require_valid,
)

from . import contract as c

__all__ = [
    "Genesis",
    "InvalidGenesis",
    "chain_id",
    "encode",
    "initial_economy_entries",
    "predecessor_chain_id",
    "require_valid",
]

PREDECESSOR_CHAIN_IDS: dict[int, str] = {
    2: "protocol-stack:v2:chain-id",
    3: "protocol-stack:v3:chain-id",
    4: "protocol-stack:v4:chain-id",
}


def encode(genesis: Genesis, schema_version: int = c.GENESIS_SCHEMA_VERSION) -> bytes:
    return v4.encode(genesis, schema_version=schema_version)


def chain_id(genesis: Genesis) -> bytes:
    return digest(c.CHAIN_ID_LABEL, encode(genesis))


def predecessor_chain_id(genesis: Genesis, version: int) -> bytes:
    """The same fields under an earlier schema and label, for comparison."""
    if version not in PREDECESSOR_CHAIN_IDS:
        raise InvalidGenesis(f"no predecessor chain ID for version {version}")
    return digest(
        PREDECESSOR_CHAIN_IDS[version], encode(genesis, schema_version=version)
    )
