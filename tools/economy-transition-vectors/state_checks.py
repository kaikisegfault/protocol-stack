"""State key, tree, root, genesis, winner-commitment, and storage derivations."""

from __future__ import annotations

from pathlib import Path

import expected as e
from checker import Checker, read_vectors

from simulation.economy_transition import contract as c
from simulation.economy_transition import genesis, scenario, state, winners


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
    # The per-seat-cycle population is absent from the state entirely: a mint
    # takes everything, so one high-water mark per seat replaces what would
    # otherwise be 73,100,000 entries.
    check.equal(
        "state.no_entry_is_keyed_by_seat_cycle",
        all(width < 7 or kind in (4, 5, 6) for kind, (width, _) in e.ENTRY_WIDTHS.items()),
    )
    # No key is a prefix of another with a different meaning, which is what
    # makes unsigned lexicographic order total over a mixed-width key space.
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
    check.equal("state.economy_root_differs_from_genesis", empty != state.economy_root(populated))


def _independent_root(entries: dict[bytes, bytes]) -> str:
    """Rebuild the tree from `expected.py`'s Merkle and length-prefix rules."""
    leaves = [
        e.be(len(key), 4) + key + e.be(len(value), 4) + value
        for key, value in sorted(entries.items())
    ]
    return e.merkle(leaves, c.ECONOMY_TREE_PREFIX).hex()


def check_version_one_restatement(check: Checker, vector_root: Path) -> None:
    """The version-one root restatement must be the accepted one, not a lookalike.

    The non-collision claim below compares a version-two root against this
    module's version-one construction. If that construction were merely
    plausible rather than correct, "the roots differ" would be trivially true
    and would prove nothing, so it is first required to reproduce the accepted
    `protocol-primitives-v1` vectors exactly.
    """
    accepted = read_vectors(vector_root / "protocol-primitives-v1.txt")
    entries = [accepted[f"state.account{index}"] for index in range(3)]
    accounts = [
        (
            bytes.fromhex(entry[0:64]),
            int(entry[64:80], 16),
            int(entry[80:96], 16),
        )
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
    # The same tree shape under the transaction labels, so the Merkle
    # construction itself is checked against the accepted file rather than only
    # its accounts instance.
    items = [bytes.fromhex(accepted[f"tx.item{index}"]) for index in range(3)]
    from simulation.economy_transition.merkle import root as merkle_root

    check.equal(
        "state.version_one_transaction_tree_matches_accepted",
        merkle_root(items, "protocol-stack:v1:tx").hex() == accepted["tx.root"],
    )


def check_state_root(check: Checker) -> None:
    """The version-one and version-two roots must differ on identical accounts.

    A construction that collided on the empty-economy case would be a
    version-one root reinterpreted as a version-two root, which
    `protocol-primitives-v1` forbids outright.
    """
    accounts = [
        (bytes([index]) * 32, 1_000 * (index + 1), 0) for index in range(3)
    ]
    common = dict(
        chain_id=scenario.CHAIN_ID,
        height=7,
        supply_limit=e.MAXIMUM_SUPPLY_ATOMIC,
        total_supply=6_000,
        fee_pool_balance=0,
        accounts=accounts,
    )
    version_two = state.state_root(**common, economy={})
    version_one = state.version_one_state_root(**common)
    check.equal("state.root_empty_economy", version_two)
    check.equal("state.version_one_root_same_accounts", version_one)
    check.equal("state.roots_differ_on_identical_accounts", version_one != version_two)
    check.equal("state.root_schema_version", c.STATE_ROOT_SCHEMA_VERSION)
    check.equal("state.root_label", c.STATE_ROOT_LABEL)

    populated = state.state_root(**common, economy=scenario.populated_economy())
    check.equal("state.root_populated_economy", populated)
    check.equal("state.root_tracks_the_economy", populated != version_two)


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
    check.equal(
        "genesis.one_more_account_bytes", accepted_bytes + c.ACCOUNT_ENTRY_BYTES
    )
    check.equal("genesis.max_accounts_fits_object_bound", accepted_bytes <= e.MAX_OBJECT_BYTES)
    check.equal(
        "genesis.one_more_account_exceeds_object_bound",
        accepted_bytes + c.ACCOUNT_ENTRY_BYTES > e.MAX_OBJECT_BYTES,
    )
    # Version one's 46-byte prefix admits one more entry. Version two adds 64
    # bytes — the manifest digest and the verifier key — and loses exactly one
    # entry, so the accepting case clears the bound by two bytes.
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

    # The three relaxations the constitution forces, exercised together.
    check.equal("genesis.zero_total_supply_accepted", founder.total_supply == 0)
    check.equal("genesis.zero_accounts_accepted", len(founder.accounts) == 0)
    check.equal("genesis.zero_fee_accepted", founder.fixed_transfer_fee == 0)
    check.equal("genesis.verifier_key_is_a_field", founder.verifier_key.hex())
    # The verifier key sits inside the chain ID, so a chain trusting a different
    # verifier is a different chain rather than the same one.
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


def check_winners(check: Checker) -> None:
    """The cycle assignment: the winner rule, the split, and the two bitmaps."""
    derived = scenario.cycle_winners()
    check.equal("cycle.winners", ",".join(str(seat) for seat in derived))
    check.equal("cycle.winner_count", len(derived))
    check.equal("cycle.excludes_the_failed_seat", 7 not in derived)
    check.equal("cycle.excludes_below_maximum_uptime", c.MAX_SEAT_ID not in derived)

    # The encoding must not hold a second opinion about who wins. The accepted
    # economy model reaches the set from a supplied record and this one from a
    # cycle's measurements, so a set both produce has been derived twice.
    from simulation.founder_economy_v3 import uptime as economy_uptime

    record = {
        "entries": [
            {"seat_id": seat, "uptime_seconds": scenario.CYCLE_UPTIME[seat]}
            for seat in sorted(scenario.CYCLE_UPTIME)
        ]
    }
    check.equal(
        "cycle.agrees_with_the_accepted_economy_model",
        economy_uptime.winner_seats(record) == derived,
    )
    check.equal(
        "cycle.met_flags_are_the_accepted_threshold",
        all(
            scenario.CYCLE_MET[seat] == economy_uptime.met_cycle(seconds)
            for seat, seconds in scenario.CYCLE_UPTIME.items()
        ),
    )

    # Every leg is divided, not only the operator leg: a failed cycle's whole
    # permission moves to the winners, so the escrows and the System Creator are
    # paid at the winner's mint and each of their legs can leave a remainder.
    shares, carries = winners.split_permission(len(derived))
    expected_shares, expected_carries = e.split_permission(len(derived))
    for channel in sorted(shares):
        check.agree(f"cycle.share_atomic.{channel}", expected_shares[channel], shares[channel])
        check.agree(f"cycle.carry_atomic.{channel}", expected_carries[channel], carries[channel])
    check.agree(
        "cycle.base_permission_total_atomic",
        sum(e.base_permission_legs().values()),
        c.BASE_PERMISSION_TOTAL,
    )
    check.equal(
        "cycle.split_conserves_every_leg",
        all(
            shares[channel] * len(derived) + carries[channel] == amount
            for channel, amount in c.BASE_PERMISSION_LEGS
        ),
    )

    # A count that does not divide the legs, so a carried remainder is exercised
    # rather than only the exact-split case.
    odd_shares, odd_carries = winners.split_permission(7)
    check.agree(
        "cycle.share_atomic_over_seven.0", e.split_permission(7)[0][0], odd_shares[0]
    )
    check.agree(
        "cycle.carry_atomic_over_seven.0", e.split_permission(7)[1][0], odd_carries[0]
    )
    check.equal(
        "cycle.split_over_seven_conserves",
        all(
            odd_shares[channel] * 7 + odd_carries[channel] == amount
            for channel, amount in c.BASE_PERMISSION_LEGS
        ),
    )

    # An empty winner set carries the whole permission forward, which is the
    # founder-directed rule for a cycle no node met.
    empty_shares, empty_carries = winners.split_permission(0)
    check.equal("cycle.empty_set_shares_are_zero", all(v == 0 for v in empty_shares.values()))
    check.equal(
        "cycle.empty_set_carries_the_whole_permission",
        sum(empty_carries.values()) == c.BASE_PERMISSION_TOTAL,
    )

    _check_bitmaps(check, derived)


def _check_bitmaps(check: Checker, derived: tuple[int, ...]) -> None:
    """Two bitmaps over one in-scope order: met and won are separate facts."""
    met_flags = [scenario.CYCLE_MET[seat] for seat in scenario.IN_SCOPE_SEATS]
    winner_flags = [seat in derived for seat in scenario.IN_SCOPE_SEATS]
    met = state.bitmap(met_flags)
    won = state.bitmap(winner_flags)
    check.agree("cycle.met_bitmap", e.bitmap(met_flags).hex(), met.hex())
    check.agree("cycle.winner_bitmap", e.bitmap(winner_flags).hex(), won.hex())
    check.equal("cycle.bitmaps_differ", met != won)
    check.equal(
        "cycle.a_seat_may_meet_without_winning",
        any(
            state.bit_is_set(met, index) and not state.bit_is_set(won, index)
            for index in range(len(scenario.IN_SCOPE_SEATS))
        ),
    )
    check.equal(
        "cycle.every_winner_also_met",
        all(
            state.bit_is_set(met, index)
            for index in range(len(scenario.IN_SCOPE_SEATS))
            if state.bit_is_set(won, index)
        ),
    )
    key, value = scenario.cycle_assignment_entry()
    check.equal("cycle.assignment_key", key.hex())
    check.equal("cycle.assignment_value_bytes", len(value))
    check.agree(
        "cycle.assignment_entry_bytes",
        e.entry_bytes(c.CYCLE_ASSIGNMENT_ENTRY, len(scenario.IN_SCOPE_SEATS)),
        len(key) + len(value),
    )


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
        "channels": 10 * e.entry_bytes(c.CHANNEL_ENTRY),
        "referral_balance_per_referrer": e.entry_bytes(c.REFERRAL_BALANCE_ENTRY),
        "typed_custody": c.FOUNDER_SEAT_CAPACITY * e.entry_bytes(c.TYPED_CUSTODY_ENTRY),
        "carries": 10 * e.entry_bytes(c.CARRY_ENTRY),
        "verifier_key": e.entry_bytes(c.VERIFIER_KEY_ENTRY),
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

    # What the founder rule removed. A mint that could take a chosen amount
    # would need one entry per seat-cycle to record which cycles were taken;
    # a mint that takes everything needs one high-water mark per seat.
    check.equal(
        "storage.seat_cycle_entries_the_take_everything_rule_removes", population
    )
    check.equal(
        "storage.high_water_mark_bytes_at_capacity", c.FOUNDER_SEAT_CAPACITY * 8
    )
