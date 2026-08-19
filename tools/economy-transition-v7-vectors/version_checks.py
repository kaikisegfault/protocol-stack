"""Version seven's identity: what re-versions, what does not, and what collides.

Distinct labels are strings rather than a chain, so refusing one collision
implies nothing about another. Version seven must refuse six, and each
predecessor construction is first required to reproduce its own accepted empty
economy root, so the comparison is against the real predecessor rather than
against a restatement that happens to differ.
"""

from __future__ import annotations

from pathlib import Path

import expected as e
from simulation.economy_transition_v7 import contract as c
from simulation.economy_transition_v7 import genesis as g
from simulation.economy_transition_v7 import state as s


def _read(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, separator, value = stripped.partition("=")
        if separator:
            values[key] = value
    return values


def check_identity(check) -> None:
    check.agree("version.chain_id_label", e.CHAIN_ID_LABEL, c.CHAIN_ID_LABEL)
    check.agree("version.state_root_label", e.STATE_ROOT_LABEL, c.STATE_ROOT_LABEL)
    check.agree(
        "version.economy_tree_prefix", e.ECONOMY_TREE_PREFIX, c.ECONOMY_TREE_PREFIX
    )
    check.agree(
        "version.state_root_schema_version",
        e.STATE_ROOT_SCHEMA_VERSION,
        c.STATE_ROOT_SCHEMA_VERSION,
    )
    check.agree(
        "version.genesis_schema_version",
        e.GENESIS_SCHEMA_VERSION,
        c.GENESIS_SCHEMA_VERSION,
    )
    check.agree("version.receipt_version", e.RECEIPT_VERSION, c.RECEIPT_VERSION)

    # Retained rather than re-versioned: a label names the artifact it derives,
    # and none of these artifacts changed.
    check.agree("version.retained.account_label", e.RETAINED_LABELS["account"], c.ACCOUNT_LABEL)
    check.agree("version.retained.escrow_label", e.RETAINED_LABELS["escrow"], c.ESCROW_LABEL)
    check.agree(
        "version.retained.transaction_sign_label",
        e.RETAINED_LABELS["transaction_sign"],
        c.SIGN_LABEL,
    )
    check.agree(
        "version.retained.transaction_id_label",
        e.RETAINED_LABELS["transaction_id"],
        c.TX_ID_LABEL,
    )
    check.agree(
        "version.retained.hub_registration_label",
        e.RETAINED_LABELS["hub_registration"],
        c.REGISTRATION_LABEL,
    )
    check.equal(
        "version.retained.every_hub_message_label_is_version_six",
        all(label.startswith("protocol-stack:v6:") for label in c.HUB_MESSAGE_LABELS),
    )
    check.equal("version.retained.hub_message_count", len(c.HUB_MESSAGE_LABELS))


def check_manifest_binding(check, accepted: Path) -> None:
    """The binding moved to version three and the economy did not."""
    check.agree("version.manifest_digest", e.MANIFEST_DIGEST, c.MANIFEST_DIGEST_HEX)
    check.agree(
        "version.superseded_manifest_digest",
        e.SUPERSEDED_MANIFEST_DIGEST,
        c.SUPERSEDED_MANIFEST_DIGEST_HEX,
    )
    check.equal(
        "version.manifest_digest_differs_from_the_superseded_one",
        c.MANIFEST_DIGEST_HEX != c.SUPERSEDED_MANIFEST_DIGEST_HEX,
    )

    # A third source: the accepted manifest file, not either derivation here.
    recorded = _read(accepted / "founder-economy-manifest-v3.txt")
    check.equal(
        "version.manifest_digest_matches_the_accepted_manifest_file",
        recorded.get("manifest_digest") == c.MANIFEST_DIGEST_HEX,
    )
    check.equal(
        "version.superseded_digest_matches_the_accepted_manifest_file",
        recorded.get("supersedes.digest") == c.SUPERSEDED_MANIFEST_DIGEST_HEX,
    )
    check.equal("version.channel9_identifier", e.CHANNEL_ORDER[9])
    check.equal(
        "version.channel9_identifier_matches_the_accepted_manifest_file",
        recorded.get("channel9.id") == e.CHANNEL_ORDER[9],
    )
    check.equal(
        "version.channel9_identifier_is_the_only_one_that_moved",
        [
            index
            for index, name in enumerate(e.CHANNEL_ORDER)
            if name != e.SUPERSEDED_CHANNEL_ORDER[index]
        ]
        == [9],
    )
    legs = e.base_permission_legs()
    for channel in e.RECOVERY_POOL_LEGS:
        check.equal(
            f"version.leg{channel}_matches_the_accepted_manifest_file",
            recorded.get(f"base_permission.{e.CHANNEL_ORDER[channel]}")
            == str(legs[channel]),
        )


def _fixture_genesis():
    return g.Genesis(
        network_id=7,
        supply_limit=e.MAXIMUM_SUPPLY_ATOMIC,
        fixed_transfer_fee=100_000,
        manifest_digest=bytes.fromhex(e.MANIFEST_DIGEST),
        verifier_key=bytes(range(32)),
    )


def check_non_collision(check) -> None:
    """Six chain identities and six state roots, over identical inputs."""
    genesis = _fixture_genesis()
    current = g.chain_id(genesis)
    check.equal("version.chain_id", current.hex())
    check.equal("version.genesis_prefix_bytes", len(g.encode(genesis)))

    for version in e.PREDECESSOR_VERSIONS:
        if version == 1:
            continue
        earlier = g.predecessor_chain_id(genesis, version)
        check.equal(
            f"version.chain_id_differs_from_v{version}", earlier.hex() != current.hex()
        )

    entries = g.initial_economy_entries(genesis.verifier_key)
    root = s.state_root(current, 0, genesis.supply_limit, 0, 0, [], entries)
    check.equal("version.state_root", root)
    for version in e.PREDECESSOR_VERSIONS:
        earlier = s.predecessor_state_root(
            version, current, 0, genesis.supply_limit, 0, 0, [], entries
        )
        check.equal(f"version.state_root_differs_from_v{version}", earlier != root)


def check_predecessor_restatements(check, accepted: Path) -> None:
    """Each predecessor tree construction reproduces its own accepted empty root.

    Without this the six non-collisions would rest on six restatements that had
    never been shown to be the real thing.
    """
    from simulation.economy_transition.merkle import root as merkle_root

    files = {
        2: ("economy-transition-v2.txt", "state.economy_root_empty"),
        3: ("economy-transition-v3.txt", "state.economy_root_empty"),
        4: ("economy-transition-v4.txt", "state.economy_root_empty"),
        5: ("economy-transition-v5.txt", "state.economy_root_empty"),
        6: ("economy-transition-v6.txt", "tree.empty_root_hex"),
    }
    for version, (name, key) in files.items():
        recorded = _read(accepted / name)
        derived = merkle_root([], f"protocol-stack:v{version}:economy").hex()
        check.equal(
            f"version.v{version}_empty_economy_root_reproduced",
            recorded.get(key) == derived,
        )
    check.agree(
        "version.economy_empty_root",
        e.merkle([], e.ECONOMY_TREE_PREFIX).hex(),
        s.economy_root({}).hex(),
    )
