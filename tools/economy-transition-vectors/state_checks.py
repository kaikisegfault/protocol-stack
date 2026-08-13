"""State key, tree, root, genesis, winner-commitment, and storage derivations."""

from __future__ import annotations

import expected as e
from checker import Checker

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
        "state.window_result_fixed_value_bytes",
        e.WINDOW_RESULT_FIXED_VALUE_BYTES,
        c.WINDOW_RESULT_FIXED_VALUE_BYTES,
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

    at_genesis = genesis.initial_economy_entries()
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
    # Version one's 46-byte prefix admits one more entry; the difference is
    # exactly the 32-byte manifest digest this version binds into chain identity.
    check.equal("genesis.version_one_max_accounts", (e.MAX_OBJECT_BYTES - 46) // 48)

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

    for name, candidate in _invalid_genesis(founder).items():
        check.equal(f"genesis.reject.{name}", _genesis_refusal(candidate))


def _invalid_genesis(founder: genesis.Genesis) -> dict[str, genesis.Genesis]:
    def variant(**changes: object) -> genesis.Genesis:
        fields = dict(
            network_id=founder.network_id,
            supply_limit=founder.supply_limit,
            total_supply=founder.total_supply,
            fixed_transfer_fee=founder.fixed_transfer_fee,
            initial_fee_pool=founder.initial_fee_pool,
            manifest_digest=founder.manifest_digest,
            accounts=list(founder.accounts),
        )
        fields.update(changes)
        return genesis.Genesis(**fields)  # type: ignore[arg-type]

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
    derived = scenario.window_winners()
    check.equal("winners.derived", ",".join(str(seat) for seat in derived))
    check.equal("winners.count", len(derived))
    check.equal("winners.excludes_the_failed_seat", 7 not in derived)
    check.equal("winners.excludes_below_maximum_uptime", c.MAX_SEAT_ID not in derived)

    root = winners.winner_root(derived)
    check.agree(
        "winners.root",
        e.merkle([e.be(seat, 4) for seat in derived], c.WINNER_TREE_PREFIX).hex(),
        root.hex(),
    )
    check.equal("winners.empty_root", winners.winner_root(()).hex())

    share, remainder = winners.equal_split(e.FOUNDER_OPERATOR_LEG_ATOMIC, len(derived))
    expected_split = e.equal_split(e.FOUNDER_OPERATOR_LEG_ATOMIC, len(derived))
    check.agree("winners.share_atomic", expected_split[0], share)
    check.agree("winners.remainder_atomic", expected_split[1], remainder)

    # A count that does not divide the portion, so the carried remainder is
    # exercised rather than only the exact-split case.
    odd_share, odd_remainder = winners.equal_split(e.FOUNDER_OPERATOR_LEG_ATOMIC, 7)
    check.agree("winners.share_atomic_over_seven", e.equal_split(e.FOUNDER_OPERATOR_LEG_ATOMIC, 7)[0], odd_share)
    check.agree("winners.remainder_atomic_over_seven", e.equal_split(e.FOUNDER_OPERATOR_LEG_ATOMIC, 7)[1], odd_remainder)

    # An empty winner set carries the whole portion forward, which is the
    # founder-directed rule for a window no node met.
    empty_share, empty_remainder = winners.equal_split(e.FOUNDER_OPERATOR_LEG_ATOMIC, 0)
    check.equal("winners.empty_set_share", empty_share)
    check.equal("winners.empty_set_carry", empty_remainder)

    # The encoding must not hold a second opinion about who wins. The accepted
    # economy model reaches the set from a supplied record and this one from a
    # window's measurements, so a set both produce has been derived twice.
    from simulation.founder_economy_v3 import uptime as economy_uptime

    record = {
        "entries": [
            {"seat_id": seat, "uptime_seconds": scenario.WINDOW_UPTIME[seat]}
            for seat in sorted(scenario.WINDOW_UPTIME)
        ]
    }
    check.equal(
        "winners.agrees_with_the_accepted_economy_model",
        economy_uptime.winner_seats(record) == derived,
    )
    check.equal(
        "winners.met_flags_are_the_accepted_threshold",
        all(
            scenario.WINDOW_MET[seat] == economy_uptime.met_cycle(seconds)
            for seat, seconds in scenario.WINDOW_UPTIME.items()
        ),
    )

    check.equal(
        "winners.commitment_accepts_the_derived_set",
        winners.matches_commitment(derived, root, len(derived)),
    )
    for name, candidate in _winner_mutations(derived).items():
        check.equal(
            f"winners.reject.{name}",
            not winners.matches_commitment(candidate, root, len(derived)),
        )


def _winner_mutations(derived: tuple[int, ...]) -> dict[str, tuple[int, ...]]:
    return {
        "reordered": tuple(reversed(derived)),
        "short_by_one": derived[:-1],
        "long_by_one": tuple(sorted(derived + (c.MAX_SEAT_ID,))),
        "substituted": tuple(sorted(derived[:-1] + (derived[-1] + 1,))),
        "empty": (),
    }


def check_storage_bounds(check: Checker) -> None:
    """Requirement 12's per-seat-balance and recipient-balance parts."""
    population = c.FOUNDER_SEAT_CAPACITY * c.ISSUANCE_CYCLES_PER_SEAT
    check.agree("storage.seat_cycle_population", e.FOUNDER_SEAT_CAPACITY * e.ISSUANCE_CYCLES_PER_SEAT, population)

    bounds = {
        "seats": c.FOUNDER_SEAT_CAPACITY * e.entry_bytes(c.SEAT_ENTRY),
        "channels": 10 * e.entry_bytes(c.CHANNEL_ENTRY),
        "pending_permissions": population * e.entry_bytes(c.PENDING_PERMISSION_ENTRY),
        "referral_accruals": population * e.entry_bytes(c.REFERRAL_ACCRUAL_ENTRY),
        "typed_custody": c.FOUNDER_SEAT_CAPACITY * e.entry_bytes(c.TYPED_CUSTODY_ENTRY),
        "performance_carry": e.entry_bytes(c.PERFORMANCE_CARRY_ENTRY),
    }
    for name, value in sorted(bounds.items()):
        check.equal(f"storage.{name}_bytes_at_capacity", value)

    per_window = e.entry_bytes(c.WINDOW_RESULT_ENTRY, c.FOUNDER_SEAT_CAPACITY)
    check.equal("storage.window_result_bytes_at_capacity", per_window)
    check.equal(
        "storage.window_results_bytes_concentrated_activation",
        per_window * c.ISSUANCE_CYCLES_PER_SEAT,
    )
    # One window per 28,800 blocks at the pinned three-second commit interval.
    windows_per_year = (365 * 24 * 3_600) // (c.CYCLE_BLOCKS * 3)
    check.agree("storage.windows_per_year", (365 * 24 * 3_600) // (e.CYCLE_BLOCKS * 3), windows_per_year)
    check.equal("storage.window_results_bytes_per_year", per_window * windows_per_year)
