"""Version identity, the retained labels, genesis, and the seven non-collisions."""

from __future__ import annotations

from pathlib import Path

import expected as x
import fixture as f
from checker import Checker, read_vectors

from simulation.economy_transition_v7 import contract as v7
from simulation.economy_transition_v8 import contract as c
from simulation.economy_transition_v8 import genesis as g
from simulation.economy_transition_v8.state import predecessor_state_root, state_root

PREDECESSORS = (1, 2, 3, 4, 5, 6, 7)


def check_identity(check: Checker) -> None:
    check.section("The re-versioned constructions and the two new labels.")
    check.agree("version.chain_id_label", x.CHAIN_ID_LABEL, c.CHAIN_ID_LABEL)
    check.agree("version.state_root_label", x.STATE_ROOT_LABEL, c.STATE_ROOT_LABEL)
    check.agree(
        "version.economy_tree_prefix", x.ECONOMY_TREE_PREFIX, c.ECONOMY_TREE_PREFIX
    )
    check.agree("version.challenge_label", x.CHALLENGE_LABEL, c.CHALLENGE_LABEL)
    check.agree("version.dispute_label", x.DISPUTE_LABEL, c.DISPUTE_LABEL)
    check.agree(
        "version.state_root_schema_version",
        x.SCHEMA_VERSION,
        c.STATE_ROOT_SCHEMA_VERSION,
    )
    check.agree(
        "version.genesis_schema_version", x.SCHEMA_VERSION, c.GENESIS_SCHEMA_VERSION
    )
    check.agree("version.receipt_version", x.SCHEMA_VERSION, c.RECEIPT_VERSION)

    check.section("Labels version eight keeps at the version that accepted them.")
    for name in ("ACCOUNT_LABEL", "ESCROW_LABEL", "SIGN_LABEL", "TX_ID_LABEL"):
        check.agree(
            f"version.retained.{name.lower()}",
            getattr(v7, name),
            getattr(c, name),
        )
    check.equal(
        "version.retained.hub_message_labels_are_version_six_s",
        all(label.startswith("protocol-stack:v6:") for label in c.HUB_MESSAGE_LABELS),
    )


def check_manifest_binding(check: Checker, accepted: Path) -> None:
    """The manifest does not move, and it is checked against its own file."""
    recorded = read_vectors(accepted / "founder-economy-manifest-v3.txt")
    digest = recorded["manifest_digest"]
    check.section("Version eight changes no founder-directed figure.")
    check.agree("manifest.digest", digest, c.MANIFEST_DIGEST_HEX)
    check.equal(
        "manifest.binding_is_version_seven_s",
        c.MANIFEST_DIGEST_HEX == v7.MANIFEST_DIGEST_HEX,
    )
    check.agree(
        "manifest.referral_leg_atomic", v7.REFERRAL_LEG_ATOMIC, c.REFERRAL_LEG_ATOMIC
    )
    check.agree(
        "manifest.issuance_cycles_per_seat",
        x.ISSUANCE_CYCLES_PER_SEAT,
        c.ISSUANCE_CYCLES_PER_SEAT,
    )


def check_genesis(check: Checker) -> None:
    genesis = f.genesis(bytes.fromhex(c.MANIFEST_DIGEST_HEX))
    raw = g.encode(genesis)
    independent = x.genesis_bytes(
        c.GENESIS_MAGIC,
        x.SCHEMA_VERSION,
        f.NETWORK_ID,
        f.SUPPLY_LIMIT,
        0,
        f.FIXED_TRANSFER_FEE,
        0,
        bytes.fromhex(c.MANIFEST_DIGEST_HEX),
        f.VERIFIER_KEY,
        f.DISPUTE_AUTHORITY_KEY,
        0,
    )
    check.section("Genesis gains one 32-octet key after the verifier key.")
    check.agree("genesis.prefix_bytes", x.GENESIS_PREFIX_BYTES, len(raw))
    check.agree("genesis.bytes", independent, raw)
    check.agree(
        "genesis.chain_id",
        x.digest(x.CHAIN_ID_LABEL, independent),
        g.chain_id(genesis),
    )
    check.agree(
        "genesis.dispute_authority_key_offset",
        110 - 4,
        raw.index(f.DISPUTE_AUTHORITY_KEY),
    )
    check.agree(
        "genesis.max_accounts", x.MAX_GENESIS_ACCOUNTS, c.MAX_GENESIS_ACCOUNTS
    )
    check.equal(
        "genesis.max_accounts_falls_from_version_seven",
        c.MAX_GENESIS_ACCOUNTS < v7.MAX_GENESIS_ACCOUNTS,
    )
    check.equal(
        "genesis.writes_fourteen_economy_entries",
        len(g.initial_economy_entries(f.VERIFIER_KEY)) == 14,
    )
    check.equal(
        "genesis.writes_no_uptime_entry",
        not any(
            key[0] in (c.OPEN_CHALLENGE_ENTRY, c.SEAT_WINDOW_ENTRY)
            for key in g.initial_economy_entries(f.VERIFIER_KEY)
        ),
    )

    check.section("No predecessor genesis is the same object.")
    for version in PREDECESSORS[1:]:
        earlier = g.predecessor_chain_id(genesis, version)
        check.equal(
            f"genesis.chain_id_differs_from_v{version}",
            earlier != g.chain_id(genesis),
        )
    check.equal(
        "genesis.is_thirty_two_octets_longer_than_version_seven",
        len(raw) == v7.GENESIS_PREFIX_BYTES + c.DISPUTE_AUTHORITY_KEY_BYTES,
    )


def check_non_collision(check: Checker) -> None:
    """Seven separate claims, because distinct labels are strings not a chain."""
    genesis = f.genesis(bytes.fromhex(c.MANIFEST_DIGEST_HEX))
    chain_id = g.chain_id(genesis)
    arguments = (chain_id, 12, f.SUPPLY_LIMIT, 0, 0, [], {})
    mine = state_root(*arguments)

    check.section("The version-eight root collides with none of its seven predecessors.")
    check.equal("root.version_eight", mine)
    for version in PREDECESSORS:
        earlier = predecessor_state_root(version, *arguments[:6], {} if version > 1 else None)
        check.equal(f"root.differs_from_v{version}", earlier != mine)
