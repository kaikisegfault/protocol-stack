"""State keys, trees, roots, predecessor restatements, genesis, and storage."""

from __future__ import annotations

from pathlib import Path

import expected as e
from checker import Checker

from simulation.economy_transition_v6 import contract as c
from simulation.economy_transition_v6 import genesis as genesis_module
from simulation.economy_transition_v6 import scenario, state
from simulation.economy_transition_v6.state import InvalidStateEntry

ACCOUNT_SET: list[tuple[bytes, int, int]] = [
    (bytes(range(32)), 100, 0),
    (bytes(range(0x20, 0x40)), 200, 1),
    (bytes(range(0x40, 0x60)), 300, 2),
]


def check_state_keys(check: Checker) -> None:
    """Every assigned entry kind, its key width derived from its named fields."""
    check.agree("state.entry_kind_count", len(e.ENTRY_NAMES), len(c.ENTRY_KINDS))
    check.agree(
        "state.retired_entry_kind_count",
        len(e.RETIRED_ENTRY_KINDS),
        len(c.RETIRED_ENTRY_KINDS),
    )
    for kind in sorted(e.ENTRY_NAMES):
        check.agree(f"state.entry{kind}.name", e.ENTRY_NAMES[kind], c.ENTRY_KINDS[kind])
        check.agree(
            f"state.entry{kind}.key_bytes",
            e.key_bytes_from_fields(kind),
            c.ENTRY_KEY_BYTES[kind],
        )
        if c.ENTRY_VALUE_BYTES[kind] is None:
            # The one variable-width value. Its fixed part and its two bitmaps
            # are recorded separately, because a single total would have to
            # invent a population.
            check.agree(
                f"state.entry{kind}.fixed_value_bytes",
                e.CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES,
                c.CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES,
            )
            check.agree(
                f"state.entry{kind}.total_bytes_at_capacity",
                e.entry_bytes(kind, e.FOUNDER_SEAT_CAPACITY),
                c.ENTRY_KEY_BYTES[kind]
                + c.CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES
                + 2 * (c.FOUNDER_SEAT_CAPACITY // 8),
            )
            continue
        check.agree(
            f"state.entry{kind}.value_bytes",
            e.value_bytes_from_fields(kind),
            c.ENTRY_VALUE_BYTES[kind],
        )
        check.agree(
            f"state.entry{kind}.total_bytes",
            e.entry_bytes(kind),
            c.ENTRY_KEY_BYTES[kind] + c.ENTRY_VALUE_BYTES[kind],
        )
    for kind, name in sorted(e.RETIRED_ENTRY_KINDS.items()):
        check.agree(f"state.retired_entry{kind}.was", name, c.RETIRED_ENTRY_KINDS[kind])
        check.equal(
            f"state.retired_entry{kind}_is_refused",
            not _entry_accepted(bytes([kind]) + bytes(32), b""),
        )

    # No key names both a seat and a cycle, which is the property version three
    # replaced a false boolean with a derivation to establish.
    keyed_by_both = [
        kind
        for kind, fields in e.ENTRY_KEY_FIELDS.items()
        if "seat_id" in fields and "cycle_window" in fields
    ]
    check.agree("state.entries_keyed_by_both_a_seat_and_a_cycle", 0, len(keyed_by_both))

    check.equal(
        "state.every_key_is_shape_checked",
        not _entry_accepted(bytes([c.SEAT_ENTRY]), b"x" * 82),
    )
    check.equal(
        "state.unknown_entry_kind_is_refused",
        not _entry_accepted(bytes([200]) + bytes(32), b""),
    )


def _entry_accepted(key: bytes, value: bytes) -> bool:
    try:
        state.ordered_entries({key: value})
    except (InvalidStateEntry, ValueError):
        return False
    return True


def check_trees(check: Checker) -> None:
    """The economy tree over the empty, genesis, and populated entry sets."""
    empty = state.economy_root({})
    check.agree(
        "tree.empty_root_hex",
        e.digest(f"{e.ECONOMY_TREE_PREFIX}-empty").hex(),
        empty.hex(),
    )

    initial = genesis_module.initial_economy_entries(scenario.VERIFIER_KEY)
    # Ten channels, ten carries, and the three singletons genesis writes: the
    # verifier key, the empty unreferred pool, and the verified-user counter.
    singleton_kinds = (c.VERIFIER_KEY_ENTRY, c.UNREFERRED_POOL_ENTRY,
                       c.VERIFIED_USER_COUNTER_ENTRY)
    check.agree(
        "tree.genesis_entry_count", 10 + 10 + len(singleton_kinds), len(initial)
    )
    check.equal(
        "tree.genesis_writes_every_singleton_entry",
        all(bytes([kind]) in initial for kind in singleton_kinds),
    )
    check.equal(
        "tree.genesis_writes_no_seat_identity_escrow_or_signer",
        not any(
            key[0]
            in (c.SEAT_ENTRY, c.HUB_IDENTITY_ENTRY, c.ESCROW_ENTRY, c.SIGNER_ENTRY)
            for key in initial
        ),
    )
    check.agree(
        "tree.genesis_root_hex",
        _independent_root(initial).hex(),
        state.economy_root(initial).hex(),
    )

    populated = scenario.populated_economy()
    check.agree(
        "tree.populated_root_hex",
        _independent_root(populated).hex(),
        state.economy_root(populated).hex(),
    )
    check.agree(
        "tree.populated_entry_count", len(populated), len(state.ordered_entries(populated))
    )
    covered = {key[0] for key in populated}
    check.equal(
        "tree.populated_set_covers_every_assigned_entry_kind",
        covered == set(c.ENTRY_KINDS),
    )


def _independent_root(entries: dict[bytes, bytes]) -> bytes:
    leaves = [
        e.be(len(key), 4) + key + e.be(len(value), 4) + value
        for key, value in sorted(entries.items())
    ]
    return e.merkle(leaves, e.ECONOMY_TREE_PREFIX)


PREDECESSOR_FILES: dict[int, str] = {
    2: "economy-transition-v2.txt",
    3: "economy-transition-v3.txt",
    4: "economy-transition-v4.txt",
    5: "economy-transition-v5.txt",
}


def check_predecessor_restatements(check: Checker, accepted: Path) -> None:
    """Each predecessor construction must reproduce its own accepted vectors.

    A lookalike would make the six-way non-collision trivially true, so every
    restatement is required to hit a value that file already records before any
    comparison rests on it. The lookup is total: a missing key is a failure
    rather than a skip, because a check that can quietly not run is the vacuous
    kind `docs/engineering/verification.md` forbids.
    """
    for version, filename in sorted(PREDECESSOR_FILES.items()):
        recorded = _read(accepted / filename)
        key = "state.economy_root_empty"
        if key not in recorded:
            check.failures.append(
                f"root.v{version}_restatement: {filename} records no {key}"
            )
            continue
        check.equal(
            f"root.v{version}_restatement_reproduces_its_accepted_empty_economy_root",
            e.digest(f"protocol-stack:v{version}:economy-empty").hex() == recorded[key],
        )

    # Version one has no economy tree, so its restatement is checked against the
    # accepted accounts tree instead — the construction version six reuses.
    primitives = _read(accepted / "protocol-primitives-v1.txt")
    accounts = [
        (bytes.fromhex(primitives[f"state.account{index}"][:64]),
         int(primitives[f"state.account{index}"][64:80], 16),
         int(primitives[f"state.account{index}"][80:96], 16))
        for index in range(3)
    ]
    check.equal(
        "root.v1_accounts_tree_restatement_reproduces_its_accepted_root",
        state.accounts_root(accounts).hex() == primitives["state.accounts_tree_root"],
    )


def check_state_root(check: Checker) -> None:
    """The version-six root, and the six-way non-collision it must satisfy."""
    chain_id = scenario.CHAIN_ID
    arguments = dict(
        chain_id=chain_id,
        height=9,
        supply_limit=e.MAXIMUM_SUPPLY_ATOMIC,
        total_supply=1_000,
        fee_pool_balance=7,
        accounts=ACCOUNT_SET,
    )
    six = state.state_root(economy={}, **arguments)
    check.agree(
        "root.version_six_over_an_empty_economy",
        e.state_root_hex(
            e.STATE_ROOT_LABEL, 6, chain_id, 9, e.MAXIMUM_SUPPLY_ATOMIC, 1_000, 7,
            ACCOUNT_SET, {}, e.ECONOMY_TREE_PREFIX,
        ),
        six,
    )
    check.agree("root.schema_version", e.STATE_ROOT_SCHEMA_VERSION, 6)
    check.agree("root.label", e.STATE_ROOT_LABEL, c.STATE_ROOT_LABEL)

    roots = {6: six}
    for version in (1, 2, 3, 4, 5):
        roots[version] = state.predecessor_state_root(version=version, **arguments)
    check.equal("root.all_six_differ_over_identical_inputs", len(set(roots.values())) == 6)
    for version in (1, 2, 3, 4, 5):
        check.equal(
            f"root.version_six_differs_from_version_{version}", roots[version] != six
        )

    economy = scenario.populated_economy()
    populated = state.state_root(economy=economy, **arguments)
    check.agree(
        "root.version_six_over_the_populated_economy",
        e.state_root_hex(
            e.STATE_ROOT_LABEL, 6, chain_id, 9, e.MAXIMUM_SUPPLY_ATOMIC, 1_000, 7,
            ACCOUNT_SET, economy, e.ECONOMY_TREE_PREFIX,
        ),
        populated,
    )
    check.equal("root.the_economy_changes_the_root", populated != six)

    check.agree(
        "root.accounts_tree_hex",
        e.merkle(
            [
                account + e.be(balance, 8) + e.be(nonce, 8)
                for account, balance, nonce in ACCOUNT_SET
            ],
            "protocol-stack:v1:state",
        ).hex(),
        state.accounts_root(ACCOUNT_SET).hex(),
    )


def check_genesis(check: Checker) -> None:
    """Version-six genesis, its chain ID, and its required zero account count."""
    fixture = scenario.genesis()
    raw = genesis_module.encode(fixture)
    check.agree("genesis.prefix_bytes", e.genesis_prefix_bytes(), len(raw))
    check.agree("genesis.schema_version", e.GENESIS_SCHEMA_VERSION, c.GENESIS_SCHEMA_VERSION)
    check.agree(
        "genesis.bytes_hex",
        e.genesis_bytes(
            fixture.network_id,
            fixture.supply_limit,
            fixture.fixed_transfer_fee,
            fixture.manifest_digest,
            fixture.verifier_key,
        ).hex(),
        raw.hex(),
    )
    check.agree("genesis.chain_id_label", e.CHAIN_ID_LABEL, c.CHAIN_ID_LABEL)
    check.agree(
        "genesis.chain_id_hex",
        e.digest(e.CHAIN_ID_LABEL, raw).hex(),
        genesis_module.chain_id(fixture).hex(),
    )

    for version in (2, 3, 4, 5):
        other = genesis_module.predecessor_chain_id(fixture, version)
        check.equal(
            f"genesis.differs_from_a_version_{version}_genesis_with_identical_fields",
            other != genesis_module.chain_id(fixture),
        )

    admitted, within, beyond = genesis_module.maximum_accounts_bound()
    check.agree("genesis.object_bound_admits_entries", e.max_genesis_accounts(), admitted)
    check.agree(
        "genesis.object_bound_within_bytes",
        e.genesis_prefix_bytes() + e.ACCOUNT_ENTRY_BYTES * admitted,
        within,
    )
    check.equal("genesis.object_bound_within_the_limit", within <= e.MAX_OBJECT_BYTES)
    check.equal("genesis.object_bound_beyond_the_limit", beyond > e.MAX_OBJECT_BYTES)

    # Version six is the first to require zero accounts rather than expect it.
    check.equal(
        "genesis.refuses_any_account_entry",
        not _genesis_accepted(fixture, accounts=[(bytes(32), 1, 0)]),
    )
    check.equal(
        "genesis.refuses_a_nonzero_total_supply",
        not _genesis_accepted(fixture, total_supply=1),
    )
    check.equal(
        "genesis.refuses_a_nonzero_initial_fee_pool",
        not _genesis_accepted(fixture, initial_fee_pool=1),
    )
    check.equal("genesis.opens_with_zero_supply", fixture.total_supply == 0)
    check.equal("genesis.permits_a_zero_fee", fixture.fixed_transfer_fee == 0)


def _genesis_accepted(fixture, **overrides) -> bool:
    from dataclasses import replace

    try:
        genesis_module.encode(replace(fixture, **overrides))
    except (genesis_module.InvalidGenesis, ValueError):
        return False
    return True


def check_storage_bounds(check: Checker) -> None:
    """Requirement 12's figures, per seat and per person."""
    check.agree(
        "storage.seats_at_capacity_bytes",
        e.FOUNDER_SEAT_CAPACITY * e.entry_bytes(1),
        c.FOUNDER_SEAT_CAPACITY * (c.ENTRY_KEY_BYTES[1] + c.ENTRY_VALUE_BYTES[1]),
    )
    check.agree("storage.identity_bytes", e.entry_bytes(10), 33 + 52)
    check.agree(
        "storage.escrow_bytes",
        e.entry_bytes(13) + e.ACCOUNT_ENTRY_BYTES,
        33 + 49 + 48,
    )
    check.agree("storage.signer_bytes", e.entry_bytes(14), 33 + 32)
    check.agree(
        "storage.signers_at_the_bound_bytes",
        e.MAX_SIGNERS_PER_ESCROW * e.entry_bytes(14),
        c.MAX_SIGNERS_PER_ESCROW * (33 + 32),
    )
    check.agree(
        "storage.verified_user_enrollments_at_the_population_bytes",
        e.VERIFIED_USER_POPULATION * e.entry_bytes(15),
        c.VERIFIED_USER_POPULATION * (33 + 24),
    )
    check.agree("storage.channels_bytes", 10 * e.entry_bytes(2), 10 * (2 + 16))
    check.agree("storage.carries_bytes", 10 * e.entry_bytes(7), 10 * (2 + 8))
    check.agree("storage.typed_custody_bytes", 4 * e.entry_bytes(6), 4 * (34 + 8))
    check.agree("storage.referral_balance_bytes", e.entry_bytes(4), 33 + 24)
    check.agree("storage.verifier_key_bytes", e.entry_bytes(8), 1 + 32)
    check.agree("storage.unreferred_pool_bytes", e.entry_bytes(12), 1 + 16)
    check.agree("storage.verified_user_counter_bytes", e.entry_bytes(16), 1 + 8)
    check.agree(
        "storage.cycle_assignment_bytes_per_cycle",
        e.entry_bytes(3, e.FOUNDER_SEAT_CAPACITY),
        9 + 24 + 2 * 12_500,
    )
    check.agree(
        "storage.one_person_with_three_escrows_and_five_signers_bytes",
        e.per_person_storage_bytes(3, 5),
        85 + 130 * 3 + 65 * 5,
    )

    # The seat family fell by an order of magnitude, and the figure is derived
    # from the two versions' own entry widths rather than quoted.
    version_four_seats = e.FOUNDER_SEAT_CAPACITY * (5 + 119)
    version_four_managers = e.FOUNDER_SEAT_CAPACITY * 16 * 37
    check.agree(
        "storage.version_four_seat_family_bytes",
        version_four_seats + version_four_managers,
        71_600_000,
    )
    check.equal(
        "storage.the_seat_family_shrank",
        e.FOUNDER_SEAT_CAPACITY * e.entry_bytes(1)
        < version_four_seats + version_four_managers,
    )


def _read(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        values[key] = value
    return values
