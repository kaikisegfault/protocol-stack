"""State key, tree, root, genesis, and storage-bound derivations."""

from __future__ import annotations

from pathlib import Path

import expected as e
from checker import Checker, read_vectors

from simulation.economy_transition_v3 import contract as c
from simulation.economy_transition_v3 import genesis, scenario, state


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
    check.agree(
        "state.cycle_assignment_fixed_value_bytes",
        e.CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES,
        c.CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES,
    )
    # Each key width is derived a second time from its named fields, so the
    # statement below is about the key space rather than about a byte count.
    for kind, name in sorted(c.ENTRY_KINDS.items()):
        check.equal(f"state.key_fields.{name}", ",".join(e.ENTRY_KEY_FIELDS[kind]))
        check.agree(
            f"state.key_bytes_from_fields.{name}",
            e.key_bytes_from_fields(kind),
            c.ENTRY_KEY_BYTES[kind],
        )
    # The per-seat-cycle population is absent from the state entirely: a mint
    # takes everything, so one high-water mark per seat replaces what would
    # otherwise be 73,100,000 entries. No key names a seat and a cycle at once,
    # which is what such an entry would have to do.
    check.equal(
        "state.no_key_names_a_seat_and_a_cycle",
        not any(e.keys_a_seat_and_a_cycle(kind) for kind in e.ENTRY_KEY_FIELDS),
    )
    check.equal(
        "state.entry_kinds_keyed_by_a_seat",
        ",".join(
            c.ENTRY_KINDS[kind]
            for kind in sorted(e.ENTRY_KEY_FIELDS)
            if "seat_id" in e.ENTRY_KEY_FIELDS[kind]
        ),
    )
    check.equal(
        "state.entry_kinds_keyed_by_a_cycle",
        ",".join(
            c.ENTRY_KINDS[kind]
            for kind in sorted(e.ENTRY_KEY_FIELDS)
            if "cycle_window" in e.ENTRY_KEY_FIELDS[kind]
        ),
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

    # The beneficiary space version two used and never enumerated.
    check.agree(
        "state.beneficiary_kind_count", len(e.BENEFICIARY_KINDS), len(c.BENEFICIARY_KINDS)
    )
    for kind, name in sorted(c.BENEFICIARY_KINDS.items()):
        check.agree(f"state.beneficiary_kind.{kind}", e.BENEFICIARY_KINDS[kind], name)
    check.equal(
        "state.singleton_beneficiary_kinds",
        ",".join(c.BENEFICIARY_KINDS[kind] for kind in c.SINGLETON_BENEFICIARY_KINDS),
    )
    check.equal(
        "state.singleton_beneficiary_id_is_zero",
        c.SINGLETON_BENEFICIARY_ID == bytes(32),
    )
    check.equal(
        "state.reject.singleton_with_a_named_beneficiary",
        _entry_refusal(
            lambda: state.typed_custody_key(
                c.VENTURE_ESCROW_BENEFICIARY, scenario.BENEFICIARY_ACCOUNT_ID
            )
        ),
    )
    check.equal(
        "state.reject.unknown_beneficiary_kind",
        _entry_refusal(lambda: state.typed_custody_key(6, bytes(32))),
    )
    # A Founder Seat and a referrer are not beneficiary kinds: minted value
    # lands in an ordinary account balance under ADR 0033.
    check.equal(
        "state.no_founder_seat_beneficiary_kind",
        "founder_seat" not in c.BENEFICIARY_KINDS.values()
        and "recorded_referrer" not in c.BENEFICIARY_KINDS.values(),
    )

    # The seat record's two new fields, and the manager bound they enforce.
    check.equal("state.max_seat_managers", c.MAX_SEAT_MANAGERS)
    check.agree("state.max_seat_managers_agrees", e.MAX_SEAT_MANAGERS, c.MAX_SEAT_MANAGERS)
    check.equal(
        "state.reject.manager_count_above_the_bound",
        _entry_refusal(
            lambda: state.seat_value(
                scenario.BIOMETRIC_IDENTITY_HASH,
                scenario.PURCHASER_ACCOUNT_ID,
                None,
                manager_count=c.MAX_SEAT_MANAGERS + 1,
            )
        ),
    )
    check.equal(
        "state.reject.manager_count_below_one",
        _entry_refusal(
            lambda: state.seat_value(
                scenario.BIOMETRIC_IDENTITY_HASH,
                scenario.PURCHASER_ACCOUNT_ID,
                None,
                manager_count=0,
            )
        ),
    )
    check.equal(
        "state.reject.referral_minted_above_accrued",
        _entry_refusal(lambda: state.referral_balance_value(1, 2, 0)),
    )
    check.equal(
        "state.reject.pool_minted_above_accrued",
        _entry_refusal(lambda: state.unreferred_pool_value(1, 2)),
    )


def _entry_refusal(build) -> str:
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
        "state.economy_root_differs_from_genesis", empty != state.economy_root(populated)
    )
    check.equal("state.economy_tree_prefix", c.ECONOMY_TREE_PREFIX)
    # A version-two tree over the same entries is a different tree, because the
    # prefix is part of every leaf and node preimage.
    check.equal(
        "state.economy_tree_prefix_separates_versions",
        e.merkle([], c.ECONOMY_TREE_PREFIX) != e.merkle([], "protocol-stack:v2:economy"),
    )


def _independent_root(entries: dict[bytes, bytes]) -> str:
    """Rebuild the tree from `expected.py`'s Merkle and length-prefix rules."""
    leaves = [
        e.be(len(key), 4) + key + e.be(len(value), 4) + value
        for key, value in sorted(entries.items())
    ]
    return e.merkle(leaves, c.ECONOMY_TREE_PREFIX).hex()


def check_version_one_restatement(check: Checker, vector_root: Path) -> None:
    """The version-one restatement must be the accepted one, not a lookalike.

    The non-collision claims below compare a version-three root against this
    module's version-one and version-two constructions. If those were merely
    plausible rather than correct, "the roots differ" would be trivially true.
    """
    accepted = read_vectors(vector_root / "protocol-primitives-v1.txt")
    entries = [accepted[f"state.account{index}"] for index in range(3)]
    accounts = [
        (bytes.fromhex(entry[0:64]), int(entry[64:80], 16), int(entry[80:96], 16))
        for entry in entries
    ]

    check.equal(
        "state.version_one_empty_tree_matches_accepted",
        state.accounts_root([]).hex() == accepted["state.empty_tree_root"],
    )
    check.equal(
        "state.version_one_accounts_tree_matches_accepted",
        state.accounts_root(accounts).hex() == accepted["state.accounts_tree_root"],
    )
    derived = state.version_one_state_root(
        chain_id=bytes.fromhex(accepted["chain_id"]),
        height=int(accepted["state.height"]),
        supply_limit=int(accepted["state.supply_limit"]),
        total_supply=int(accepted["state.total_supply"]),
        fee_pool_balance=int(accepted["state.fee_pool_balance"]),
        accounts=accounts,
    )
    check.equal(
        "state.version_one_root_matches_accepted", derived == accepted["state.root"]
    )
    items = [bytes.fromhex(accepted[f"tx.item{index}"]) for index in range(3)]
    from simulation.economy_transition.merkle import root as merkle_root

    check.equal(
        "state.version_one_transaction_tree_matches_accepted",
        merkle_root(items, "protocol-stack:v1:tx").hex() == accepted["tx.root"],
    )


def check_version_two_restatement(check: Checker, vector_root: Path) -> None:
    """The version-two restatement must reproduce that version's own vectors."""
    accepted = read_vectors(vector_root / "economy-transition-v2.txt")
    accounts = [(bytes([index]) * 32, 1_000 * (index + 1), 0) for index in range(3)]
    derived = state.version_two_state_root(
        chain_id=scenario.CHAIN_ID,
        height=7,
        supply_limit=e.MAXIMUM_SUPPLY_ATOMIC,
        total_supply=6_000,
        fee_pool_balance=0,
        accounts=accounts,
    )
    check.equal(
        "state.version_two_root_matches_accepted",
        derived == accepted["state.root_empty_economy"],
    )
    check.equal(
        "state.version_two_empty_economy_root_matches_accepted",
        e.merkle([], "protocol-stack:v2:economy").hex()
        == accepted["state.economy_root_empty"],
    )


def check_state_root(check: Checker) -> None:
    """All three roots must differ on identical accounts and an empty economy.

    Version two proved this against version one. Distinct labels are strings
    rather than a chain, so refusing a version-one collision implies nothing
    about a version-two one, and version three must prove both.
    """
    accounts = [(bytes([index]) * 32, 1_000 * (index + 1), 0) for index in range(3)]
    common = dict(
        chain_id=scenario.CHAIN_ID,
        height=7,
        supply_limit=e.MAXIMUM_SUPPLY_ATOMIC,
        total_supply=6_000,
        fee_pool_balance=0,
        accounts=accounts,
    )
    version_three = state.state_root(**common, economy={})
    version_two = state.version_two_state_root(**common)
    version_one = state.version_one_state_root(**common)
    check.equal("state.root_empty_economy", version_three)
    check.equal("state.version_two_root_same_accounts", version_two)
    check.equal("state.version_one_root_same_accounts", version_one)
    check.equal(
        "state.roots_differ_from_version_one", version_one != version_three
    )
    check.equal(
        "state.roots_differ_from_version_two", version_two != version_three
    )
    check.equal(
        "state.all_three_roots_are_distinct",
        len({version_one, version_two, version_three}) == 3,
    )
    check.equal("state.root_schema_version", c.STATE_ROOT_SCHEMA_VERSION)
    check.equal("state.root_label", c.STATE_ROOT_LABEL)

    populated = state.state_root(**common, economy=scenario.populated_economy())
    check.equal("state.root_populated_economy", populated)
    check.equal("state.root_tracks_the_economy", populated != version_three)


def check_genesis(check: Checker) -> None:
    check.agree("genesis.prefix_bytes", e.genesis_prefix_bytes(), c.GENESIS_PREFIX_BYTES)
    check.agree(
        "genesis.version_one_prefix_bytes",
        e.VERSION_ONE_GENESIS_PREFIX_BYTES,
        c.GENESIS_PREFIX_BYTES - 64,
    )
    check.agree("genesis.max_accounts", e.max_genesis_accounts(), c.MAX_GENESIS_ACCOUNTS)
    accepted_bytes = c.GENESIS_PREFIX_BYTES + c.ACCOUNT_ENTRY_BYTES * c.MAX_GENESIS_ACCOUNTS
    check.equal("genesis.max_accounts_bytes", accepted_bytes)
    check.equal("genesis.one_more_account_bytes", accepted_bytes + c.ACCOUNT_ENTRY_BYTES)
    check.equal("genesis.max_accounts_fits_object_bound", accepted_bytes <= e.MAX_OBJECT_BYTES)
    check.equal(
        "genesis.one_more_account_exceeds_object_bound",
        accepted_bytes + c.ACCOUNT_ENTRY_BYTES > e.MAX_OBJECT_BYTES,
    )
    check.equal("genesis.version_one_max_accounts", (e.MAX_OBJECT_BYTES - 46) // 48)
    check.equal("genesis.accepting_margin_bytes", e.MAX_OBJECT_BYTES - accepted_bytes)

    founder = scenario.genesis()
    encoded = genesis.encode(founder)
    check.equal("genesis.bytes", len(encoded))
    check.equal("genesis.bytes_hex", encoded.hex())
    check.equal("genesis.chain_id", genesis.chain_id(founder).hex())
    check.equal("genesis.chain_id_label", c.CHAIN_ID_LABEL)
    check.equal("genesis.schema_version", c.GENESIS_SCHEMA_VERSION)
    check.equal("genesis.manifest_digest", c.MANIFEST_DIGEST_HEX)

    # The same fields under version two's schema and label are a different
    # chain, which is what makes the two alternative chains rather than one
    # chain read two ways.
    check.equal("genesis.version_two_chain_id", genesis.version_two_chain_id(founder).hex())
    check.equal(
        "genesis.chain_id_differs_from_version_two",
        genesis.chain_id(founder) != genesis.version_two_chain_id(founder),
    )

    # The three relaxations the constitution forces, exercised together.
    check.equal("genesis.zero_total_supply_accepted", founder.total_supply == 0)
    check.equal("genesis.zero_accounts_accepted", len(founder.accounts) == 0)
    check.equal("genesis.zero_fee_accepted", founder.fixed_transfer_fee == 0)
    check.equal("genesis.verifier_key_is_a_field", founder.verifier_key.hex())
    drifted = _variant(founder, verifier_key=bytes(32))
    check.equal(
        "genesis.verifier_key_changes_chain_identity",
        genesis.chain_id(drifted) != genesis.chain_id(founder),
    )
    check.equal(
        "genesis.manifest_digest_changes_chain_identity",
        genesis.chain_id(_variant(founder, manifest_digest=bytes(32)))
        != genesis.chain_id(founder),
    )

    entries = genesis.initial_economy_entries(scenario.VERIFIER_KEY)
    check.equal("genesis.writes_the_unreferred_pool", state.unreferred_pool_key() in entries)
    check.equal(
        "genesis.writes_no_seat_manager_or_registration",
        not any(
            key[0] in (c.SEAT_ENTRY, c.SEAT_MANAGER_ENTRY, c.HUB_REGISTRATION_ENTRY,
                       c.REFERRAL_BALANCE_ENTRY, c.TYPED_CUSTODY_ENTRY,
                       c.CYCLE_ASSIGNMENT_ENTRY, c.DIRECT_DECISION_ENTRY)
            for key in entries
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

    account = (bytes(32), 1_000, 0)
    return {
        "zero_supply_limit": variant(supply_limit=0),
        "supply_above_limit": variant(supply_limit=10, total_supply=11),
        "unconserved_supply": variant(total_supply=1),
        "zero_balance_account": variant(total_supply=0, accounts=[(bytes(32), 0, 0)]),
        "nonzero_nonce": variant(total_supply=1_000, accounts=[(bytes(32), 1_000, 1)]),
        "unordered_accounts": variant(
            total_supply=2_000, accounts=[(b"\xff" * 32, 1_000, 0), account]
        ),
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
    population = c.FOUNDER_SEAT_CAPACITY * c.ISSUANCE_CYCLES_PER_SEAT
    check.agree(
        "storage.seat_cycle_population",
        e.FOUNDER_SEAT_CAPACITY * e.ISSUANCE_CYCLES_PER_SEAT,
        population,
    )

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
        "referral_balance_per_referrer": e.entry_bytes(c.REFERRAL_BALANCE_ENTRY),
        "hub_registration_per_account": e.entry_bytes(c.HUB_REGISTRATION_ENTRY),
        "verifier_key": e.entry_bytes(c.VERIFIER_KEY_ENTRY),
        "unreferred_pool": e.entry_bytes(c.UNREFERRED_POOL_ENTRY),
    }
    for name, value in sorted(bounds.items()):
        check.equal(f"storage.{name}_bytes_at_capacity", value)

    per_cycle = e.entry_bytes(c.CYCLE_ASSIGNMENT_ENTRY, c.FOUNDER_SEAT_CAPACITY)
    check.equal("storage.cycle_assignment_bytes_at_capacity", per_cycle)
    cycles_per_year = (365 * 24 * 3_600) // (c.CYCLE_BLOCKS * 3)
    check.agree(
        "storage.cycles_per_year",
        (365 * 24 * 3_600) // (e.CYCLE_BLOCKS * 3),
        cycles_per_year,
    )
    check.equal("storage.cycle_assignment_bytes_per_year", per_cycle * cycles_per_year)
    # The record is the same width as version two's while carrying one more
    # field, because the two bitmap length prefixes are gone: their width is
    # derivable from the recorded bit count.
    check.equal("storage.cycle_assignment_matches_version_two_width", per_cycle == 25_033)

    check.equal(
        "storage.seat_cycle_entries_the_take_everything_rule_removes", population
    )
    check.equal("storage.high_water_mark_bytes_at_capacity", c.FOUNDER_SEAT_CAPACITY * 8)
    # Version two held one typed-custody entry per Founder Seat. Minted value
    # now lands in an account those founders already hold in order to pay a fee.
    check.equal(
        "storage.typed_custody_entries_the_account_credit_removes",
        c.FOUNDER_SEAT_CAPACITY,
    )
    check.equal(
        "storage.version_two_typed_custody_bytes_at_capacity",
        c.FOUNDER_SEAT_CAPACITY * (34 + 8),
    )
