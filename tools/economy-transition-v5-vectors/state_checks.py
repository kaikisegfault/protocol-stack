"""State key, tree, root, genesis, and storage-bound derivations.

The key space is version four's and none of it moves, so these checks run
version four's builders under version five's package and require the same
widths, orders, and refusals. What version five adds is a fourth predecessor to
separate itself from, in each of the three places a chain is separated from
another: the chain identifier, the state root, and the economy tree.
"""

from __future__ import annotations

from pathlib import Path

import expected as e
from checker import Checker, read_vectors

from simulation.economy_transition_v5 import contract as c
from simulation.economy_transition_v5 import genesis, scenario, state

ACCOUNTS = [(bytes([index]) * 32, 1_000 * (index + 1), 0) for index in range(3)]
COMMON = dict(
    chain_id=scenario.CHAIN_ID,
    height=7,
    supply_limit=5_699_395_010_000_000_000,
    total_supply=6_000,
    fee_pool_balance=0,
    accounts=ACCOUNTS,
)
PREDECESSORS = (1, 2, 3, 4)


def check_state_keys(check: Checker) -> None:
    check.agree("state.entry_kind_count", len(e.ENTRY_WIDTHS), len(c.ENTRY_KINDS))
    for kind, name in sorted(c.ENTRY_KINDS.items()):
        key_width, value_width = e.ENTRY_WIDTHS[kind]
        check.agree(f"state.key_bytes.{name}", key_width, c.ENTRY_KEY_BYTES[kind])
        model_value = c.ENTRY_VALUE_BYTES[kind]
        check.agree(
            f"state.value_bytes.{name}",
            "variable" if value_width is None else value_width,
            "variable" if model_value is None else model_value,
        )
        check.equal(f"state.key_fields.{name}", ",".join(e.ENTRY_KEY_FIELDS[kind]))
        check.agree(
            f"state.key_bytes_from_fields.{name}",
            e.key_bytes_from_fields(kind),
            c.ENTRY_KEY_BYTES[kind],
        )
    check.agree(
        "state.cycle_assignment_fixed_value_bytes",
        e.CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES,
        c.CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES,
    )
    check.equal(
        "state.no_key_names_a_seat_and_a_cycle",
        not any(e.keys_a_seat_and_a_cycle(kind) for kind in e.ENTRY_KEY_FIELDS),
    )
    check.equal(
        "state.referral_balance_is_keyed_by_identity",
        e.ENTRY_KEY_FIELDS[c.REFERRAL_BALANCE_ENTRY] == ("hub_identity_hash",),
    )
    check.equal(
        "state.hub_address_is_keyed_by_account",
        e.ENTRY_KEY_FIELDS[c.HUB_ADDRESS_ENTRY] == ("account_id",),
    )

    populated = scenario.populated_economy()
    keys = sorted(populated)
    check.equal(
        "state.no_key_is_a_prefix_of_another",
        all(
            not later.startswith(earlier)
            for index, earlier in enumerate(keys)
            for later in keys[index + 1 :]
        ),
    )
    check.equal("state.keys_are_unique", len(set(populated)) == len(populated))
    check.equal(
        "state.populated_covers_every_entry_kind",
        {key[0] for key in populated} == set(c.ENTRY_KINDS),
    )

    check.agree(
        "state.beneficiary_kind_count",
        len(e.BENEFICIARY_KINDS),
        len(c.BENEFICIARY_KINDS),
    )
    for kind, name in sorted(c.BENEFICIARY_KINDS.items()):
        check.agree(f"state.beneficiary_kind.{kind}", e.BENEFICIARY_KINDS[kind], name)
    check.equal(
        "state.reject.singleton_with_a_named_beneficiary",
        _refusal(
            lambda: state.typed_custody_key(
                c.VENTURE_ESCROW_BENEFICIARY, scenario.BENEFICIARY_ACCOUNT_ID
            )
        ),
    )
    check.equal(
        "state.reject.unknown_beneficiary_kind",
        _refusal(lambda: state.typed_custody_key(6, bytes(32))),
    )
    check.equal("state.max_seat_managers", c.MAX_SEAT_MANAGERS)
    check.agree(
        "state.max_seat_managers_agrees", e.MAX_SEAT_MANAGERS, c.MAX_SEAT_MANAGERS
    )
    check.equal(
        "state.reject.manager_count_above_the_bound",
        _refusal(
            lambda: state.seat_value(
                scenario.ALICE_IDENTITY,
                scenario.ALICE_FIRST_ADDRESS,
                None,
                manager_count=c.MAX_SEAT_MANAGERS + 1,
            )
        ),
    )
    check.equal(
        "state.reject.referral_minted_above_accrued",
        _refusal(lambda: state.referral_balance_value(1, 2, 0)),
    )
    check.equal(
        "state.reject.pool_minted_above_accrued",
        _refusal(lambda: state.unreferred_pool_value(1, 2)),
    )


def _refusal(build) -> str:
    try:
        build()
    except state.InvalidStateEntry:
        return "INVALID_STATE_ENTRY"
    except Exception as error:  # noqa: BLE001 - shape errors are a distinct class
        return type(error).__name__
    return "accepted"


def check_trees(check: Checker) -> None:
    empty = state.economy_root({})
    check.agree(
        "state.economy_root_empty",
        e.merkle([], c.ECONOMY_TREE_PREFIX).hex(),
        empty.hex(),
    )

    at_genesis = genesis.initial_economy_entries(scenario.VERIFIER_KEY)
    check.equal("state.economy_entry_count_genesis", len(at_genesis))
    check.agree(
        "state.economy_root_genesis",
        _independent_root(at_genesis),
        state.economy_root(at_genesis).hex(),
    )

    populated = scenario.populated_economy()
    check.equal("state.economy_entry_count_populated", len(populated))
    check.agree(
        "state.economy_root_populated",
        _independent_root(populated),
        state.economy_root(populated).hex(),
    )
    check.equal(
        "state.economy_root_differs_from_genesis",
        empty != state.economy_root(populated),
    )
    check.equal("state.economy_tree_prefix", c.ECONOMY_TREE_PREFIX)
    prefixes = (c.ECONOMY_TREE_PREFIX, *e.PREDECESSOR_ECONOMY_TREES.values())
    check.equal(
        "state.economy_tree_prefix_separates_versions",
        len({e.merkle([], prefix).hex() for prefix in prefixes}) == len(prefixes),
    )


def _independent_root(entries: dict[bytes, bytes]) -> str:
    leaves = [
        e.be(len(key), 4) + key + e.be(len(value), 4) + value
        for key, value in sorted(entries.items())
    ]
    return e.merkle(leaves, c.ECONOMY_TREE_PREFIX).hex()


def check_predecessor_restatements(check: Checker, vector_root: Path) -> None:
    """Each predecessor construction must reproduce its own accepted vectors.

    A five-way non-collision claim is worthless if any of the four
    constructions it compares against is a lookalike rather than the accepted
    one, so each is first required to reproduce a value that version recorded.
    """
    primitives = read_vectors(vector_root / "protocol-primitives-v1.txt")
    entries = [primitives[f"state.account{index}"] for index in range(3)]
    accounts = [
        (bytes.fromhex(v[0:64]), int(v[64:80], 16), int(v[80:96], 16)) for v in entries
    ]
    check.equal(
        "state.version_one_accounts_tree_matches_accepted",
        state.accounts_root(accounts).hex() == primitives["state.accounts_tree_root"],
    )
    check.equal(
        "state.version_one_root_matches_accepted",
        state.predecessor_state_root(
            1,
            chain_id=bytes.fromhex(primitives["chain_id"]),
            height=int(primitives["state.height"]),
            supply_limit=int(primitives["state.supply_limit"]),
            total_supply=int(primitives["state.total_supply"]),
            fee_pool_balance=int(primitives["state.fee_pool_balance"]),
            accounts=accounts,
        )
        == primitives["state.root"],
    )

    for version, path in (
        (2, "economy-transition-v2.txt"),
        (3, "economy-transition-v3.txt"),
        (4, "economy-transition-v4.txt"),
    ):
        accepted = read_vectors(vector_root / path)
        check.equal(
            f"state.version_{version}_root_matches_accepted",
            state.predecessor_state_root(version, **COMMON)
            == accepted["state.root_empty_economy"],
        )
        check.agree(
            f"state.version_{version}_root_label",
            e.PREDECESSOR_STATE_ROOTS[version],
            state.PREDECESSOR_ROOTS[version][0],
        )


def check_state_root(check: Checker) -> None:
    """All five roots must differ on identical accounts and an empty economy."""
    five = state.state_root(**COMMON, economy={})
    predecessors = {
        version: state.predecessor_state_root(version, **COMMON)
        for version in PREDECESSORS
    }
    check.equal("state.root_empty_economy", five)
    for version, name in ((1, "one"), (2, "two"), (3, "three"), (4, "four")):
        check.equal(f"state.version_{name}_root_same_accounts", predecessors[version])
        check.equal(
            f"state.roots_differ_from_version_{name}", predecessors[version] != five
        )
    check.equal(
        "state.all_five_roots_are_distinct",
        len({five, *predecessors.values()}) == len(PREDECESSORS) + 1,
    )
    check.equal("state.root_schema_version", c.STATE_ROOT_SCHEMA_VERSION)
    check.equal("state.root_label", c.STATE_ROOT_LABEL)

    populated = state.state_root(**COMMON, economy=scenario.populated_economy())
    check.equal("state.root_populated_economy", populated)
    check.equal("state.root_tracks_the_economy", populated != five)


def check_genesis(check: Checker) -> None:
    check.agree(
        "genesis.prefix_bytes", e.genesis_prefix_bytes(), c.GENESIS_PREFIX_BYTES
    )
    check.agree(
        "genesis.max_accounts", e.max_genesis_accounts(), c.MAX_GENESIS_ACCOUNTS
    )
    accepted_bytes = (
        c.GENESIS_PREFIX_BYTES + c.ACCOUNT_ENTRY_BYTES * c.MAX_GENESIS_ACCOUNTS
    )
    check.equal("genesis.max_accounts_bytes", accepted_bytes)
    check.equal(
        "genesis.one_more_account_bytes", accepted_bytes + c.ACCOUNT_ENTRY_BYTES
    )
    check.equal(
        "genesis.max_accounts_fits_object_bound", accepted_bytes <= e.MAX_OBJECT_BYTES
    )
    check.equal(
        "genesis.one_more_account_exceeds_object_bound",
        accepted_bytes + c.ACCOUNT_ENTRY_BYTES > e.MAX_OBJECT_BYTES,
    )
    check.equal("genesis.accepting_margin_bytes", e.MAX_OBJECT_BYTES - accepted_bytes)

    founder = scenario.genesis()
    encoded = genesis.encode(founder)
    check.equal("genesis.bytes", len(encoded))
    check.equal("genesis.bytes_hex", encoded.hex())
    check.equal("genesis.chain_id", genesis.chain_id(founder).hex())
    check.equal("genesis.chain_id_label", c.CHAIN_ID_LABEL)
    check.equal("genesis.schema_version", c.GENESIS_SCHEMA_VERSION)
    check.equal("genesis.manifest_digest", c.MANIFEST_DIGEST_HEX)

    identifiers = {genesis.chain_id(founder).hex()}
    for version in (2, 3, 4):
        other = genesis.predecessor_chain_id(founder, version).hex()
        check.equal(f"genesis.version_{version}_chain_id", other)
        check.agree(
            f"genesis.version_{version}_chain_id_label",
            e.PREDECESSOR_CHAIN_IDS[version],
            genesis.PREDECESSOR_CHAIN_IDS[version],
        )
        identifiers.add(other)
    check.equal("genesis.chain_ids_are_distinct", len(identifiers) == 4)

    check.equal("genesis.zero_total_supply_accepted", founder.total_supply == 0)
    check.equal("genesis.zero_accounts_accepted", len(founder.accounts) == 0)
    check.equal("genesis.zero_fee_accepted", founder.fixed_transfer_fee == 0)
    check.equal("genesis.verifier_key_is_a_field", founder.verifier_key.hex())
    check.equal(
        "genesis.verifier_key_changes_chain_identity",
        genesis.chain_id(_variant(founder, verifier_key=bytes(32)))
        != genesis.chain_id(founder),
    )
    check.equal(
        "genesis.manifest_digest_changes_chain_identity",
        genesis.chain_id(_variant(founder, manifest_digest=bytes(32)))
        != genesis.chain_id(founder),
    )

    entries = genesis.initial_economy_entries(scenario.VERIFIER_KEY)
    check.equal(
        "genesis.writes_only_the_fixed_tables",
        {key[0] for key in entries}
        == {
            c.CHANNEL_ENTRY,
            c.CARRY_ENTRY,
            c.VERIFIER_KEY_ENTRY,
            c.UNREFERRED_POOL_ENTRY,
        },
    )
    check.equal(
        "genesis.writes_no_hub_identity",
        not any(
            key[0] in (c.HUB_IDENTITY_ENTRY, c.HUB_ADDRESS_ENTRY) for key in entries
        ),
    )

    for name, candidate in _invalid_genesis(founder).items():
        check.equal(f"genesis.reject.{name}", _genesis_refusal(candidate))


def _variant(founder: genesis.Genesis, **changes: object) -> genesis.Genesis:
    fields = dict(
        network_id=founder.network_id,
        supply_limit=founder.supply_limit,
        total_supply=founder.total_supply,
        fixed_transfer_fee=founder.fixed_transfer_fee,
        initial_fee_pool=founder.initial_fee_pool,
        manifest_digest=founder.manifest_digest,
        verifier_key=founder.verifier_key,
        accounts=list(founder.accounts),
    )
    fields.update(changes)
    return genesis.Genesis(**fields)  # type: ignore[arg-type]


def _invalid_genesis(founder: genesis.Genesis) -> dict[str, genesis.Genesis]:
    def variant(**changes: object) -> genesis.Genesis:
        return _variant(founder, **changes)

    return {
        "zero_supply_limit": variant(supply_limit=0),
        "supply_above_limit": variant(supply_limit=10, total_supply=11),
        "unconserved_supply": variant(total_supply=1),
        "zero_balance_account": variant(total_supply=0, accounts=[(bytes(32), 0, 0)]),
        "nonzero_nonce": variant(total_supply=1_000, accounts=[(bytes(32), 1_000, 1)]),
        "account_count_above_bound": variant(
            total_supply=1_000 * (c.MAX_GENESIS_ACCOUNTS + 1),
            accounts=[
                (index.to_bytes(32, "big"), 1_000, 0)
                for index in range(c.MAX_GENESIS_ACCOUNTS + 1)
            ],
        ),
    }


def _genesis_refusal(candidate: genesis.Genesis) -> str:
    try:
        genesis.encode(candidate)
    except genesis.InvalidGenesis:
        return "INVALID_GENESIS"
    except Exception as error:  # noqa: BLE001 - shape errors are a distinct class
        return type(error).__name__
    return "accepted"


def check_storage_bounds(check: Checker) -> None:
    """Requirement 12's per-seat-balance and recipient-balance parts."""
    bounds = {
        "seats": c.FOUNDER_SEAT_CAPACITY * e.entry_bytes(c.SEAT_ENTRY),
        "seat_managers": (
            c.FOUNDER_SEAT_CAPACITY
            * c.MAX_SEAT_MANAGERS
            * e.entry_bytes(c.SEAT_MANAGER_ENTRY)
        ),
        "channels": 10 * e.entry_bytes(c.CHANNEL_ENTRY),
        "carries": 10 * e.entry_bytes(c.CARRY_ENTRY),
        "typed_custody": len(c.SINGLETON_BENEFICIARY_KINDS)
        * e.entry_bytes(c.TYPED_CUSTODY_ENTRY),
        "referral_balance_per_identity": e.entry_bytes(c.REFERRAL_BALANCE_ENTRY),
        "hub_identity_per_person": e.entry_bytes(c.HUB_IDENTITY_ENTRY),
        "hub_address_per_account": e.entry_bytes(c.HUB_ADDRESS_ENTRY),
        "verifier_key": e.entry_bytes(c.VERIFIER_KEY_ENTRY),
        "unreferred_pool": e.entry_bytes(c.UNREFERRED_POOL_ENTRY),
    }
    for name, value in sorted(bounds.items()):
        check.equal(f"storage.{name}_bytes_at_capacity", value)

    check.equal(
        "storage.hub_registry_bytes_at_the_minimum_principal_count",
        100 * e.entry_bytes(c.HUB_IDENTITY_ENTRY),
    )
    check.equal(
        "storage.hub_addresses_bytes_per_full_identity",
        c.MAX_IDENTITY_ADDRESSES * e.entry_bytes(c.HUB_ADDRESS_ENTRY),
    )

    per_cycle = e.entry_bytes(c.CYCLE_ASSIGNMENT_ENTRY, c.FOUNDER_SEAT_CAPACITY)
    check.equal("storage.cycle_assignment_bytes_at_capacity", per_cycle)
    cycles_per_year = (365 * 24 * 3_600) // (c.CYCLE_BLOCKS * 3)
    check.agree(
        "storage.cycles_per_year",
        (365 * 24 * 3_600) // (e.CYCLE_BLOCKS * 3),
        cycles_per_year,
    )
    check.equal("storage.cycle_assignment_bytes_per_year", per_cycle * cycles_per_year)
    check.equal(
        "storage.cycle_assignment_matches_version_three_width", per_cycle == 25_033
    )
