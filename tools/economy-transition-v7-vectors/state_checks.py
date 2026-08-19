"""The state surface: one entry kind retired, one added, one record extended.

Every width here is derived from the specification's field tables on one side
and from the model's encoders on the other, so a width that moved in either
would have to move in both to pass.
"""

from __future__ import annotations

import expected as e
from simulation.economy_transition_v7 import contract as c
from simulation.economy_transition_v7 import genesis as g
from simulation.economy_transition_v7 import settlement as t
from simulation.economy_transition_v7 import state as s


def check_entry_kinds(check) -> None:
    check.agree("state.entry_kind_count", len(e.ENTRY_NAMES), len(c.ENTRY_KINDS))
    check.agree(
        "state.retired_entry_kinds",
        ",".join(str(kind) for kind in sorted(e.RETIRED_ENTRY_KINDS)),
        ",".join(str(kind) for kind in sorted(c.RETIRED_ENTRY_KINDS)),
    )
    check.equal("state.carry_entry_is_retired", 7 in c.RETIRED_ENTRY_KINDS)
    check.equal("state.carry_entry_is_not_assigned", 7 not in c.ENTRY_KINDS)
    check.equal(
        "state.retired_kinds_are_never_reused",
        set(c.RETIRED_ENTRY_KINDS).isdisjoint(c.ENTRY_KINDS),
    )
    for kind in sorted(e.ENTRY_NAMES):
        check.agree(
            f"state.kind{kind}.name", e.ENTRY_NAMES[kind], c.ENTRY_KINDS[kind]
        )
        check.agree(
            f"state.kind{kind}.key_bytes",
            e.key_bytes_from_fields(kind),
            c.ENTRY_KEY_BYTES[kind],
        )
        if e.ENTRY_VALUE_FIELDS[kind] is not None:
            check.agree(
                f"state.kind{kind}.value_bytes",
                e.value_bytes_from_fields(kind),
                c.ENTRY_VALUE_BYTES[kind],
            )


def check_recovery_pool(check) -> None:
    check.agree("state.recovery_pool.kind", e.RECOVERY_POOL_ENTRY, c.RECOVERY_POOL_ENTRY)
    check.agree(
        "state.recovery_pool.legs",
        ",".join(str(leg) for leg in e.RECOVERY_POOL_LEGS),
        ",".join(str(leg) for leg in c.RECOVERY_POOL_LEGS),
    )
    check.agree(
        "state.recovery_pool.key_bytes",
        e.key_bytes_from_fields(e.RECOVERY_POOL_ENTRY),
        len(s.recovery_pool_key()),
    )
    pool = {channel: 0 for channel in c.RECOVERY_POOL_LEGS}
    check.agree(
        "state.recovery_pool.value_bytes",
        e.value_bytes_from_fields(e.RECOVERY_POOL_ENTRY),
        len(s.recovery_pool_value(pool)),
    )
    check.agree(
        "state.recovery_pool.entry_bytes",
        e.entry_bytes(e.RECOVERY_POOL_ENTRY),
        len(s.recovery_pool_key()) + len(s.recovery_pool_value(pool)),
    )
    check.equal("state.recovery_pool.key_hex", s.recovery_pool_key().hex())

    # The five legs are distinguishable in the bytes, so a transposition is not
    # a value that happens to encode the same.
    distinct = {channel: 1 << (8 * index) for index, channel in enumerate(c.RECOVERY_POOL_LEGS)}
    encoded = s.recovery_pool_value(distinct)
    check.equal("state.recovery_pool.ordered_value_hex", encoded.hex())
    check.equal(
        "state.recovery_pool.value_round_trips",
        s.decode_recovery_pool_value(encoded) == distinct,
    )
    swapped = dict(distinct)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    check.equal(
        "state.recovery_pool.transposed_legs_encode_differently",
        s.recovery_pool_value(swapped) != encoded,
    )
    check.equal(
        "state.recovery_pool.a_missing_leg_is_refused",
        _refuses(lambda: s.recovery_pool_value({0: 0})),
    )
    check.equal(
        "state.recovery_pool.a_short_value_is_refused",
        _refuses(lambda: s.decode_recovery_pool_value(encoded[:-1])),
    )


def check_cycle_assignment(check) -> None:
    check.agree(
        "state.cycle_assignment.fixed_value_bytes",
        e.CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES,
        c.CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES,
    )
    check.equal(
        "state.cycle_assignment.fixed_value_bytes_grew_by_five_legs",
        c.CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES
        == 24 + 8 * len(c.RECOVERY_POOL_LEGS),
    )
    for name, _width in e.CYCLE_ASSIGNMENT_FIXED_FIELDS:
        check.equal(f"state.cycle_assignment.offset.{name}", e.field_offset(name))

    absorbed = {channel: 100 + channel for channel in c.RECOVERY_POOL_LEGS}
    value = s.cycle_assignment_value(11, 2, 3, 4, 8, absorbed, b"\x81", b"\x41")
    check.agree(
        "state.cycle_assignment.value_bytes_at_eight_bits",
        e.value_bytes_from_fields(3, 8),
        len(value),
    )
    check.equal("state.cycle_assignment.value_hex", value.hex())
    decoded = s.decode_cycle_assignment_value(value)
    check.equal("state.cycle_assignment.round_trips", decoded["pool_absorbed"] == absorbed)
    check.equal(
        "state.cycle_assignment.absorbed_without_a_winner_is_refused",
        _refuses(
            lambda: s.cycle_assignment_value(0, 2, 0, 4, 8, absorbed, b"\x00", b"\x00")
        ),
    )
    zero = {channel: 0 for channel in c.RECOVERY_POOL_LEGS}
    check.equal(
        "state.cycle_assignment.no_winner_and_no_absorption_is_accepted",
        len(s.cycle_assignment_value(0, 2, 0, 4, 8, zero, b"\x00", b"\x00"))
        == c.CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES + 2,
    )
    check.equal(
        "state.cycle_assignment.a_decoded_absorption_without_a_winner_is_refused",
        _refuses(
            lambda: s.decode_cycle_assignment_value(
                value[:12] + (0).to_bytes(4, "big") + value[16:]
            )
        ),
    )


def check_entry_shape(check) -> None:
    check.equal(
        "state.a_retired_kind_in_the_map_is_refused",
        _refuses(lambda: s.ordered_entries({bytes([7, 0]): bytes(8)})),
    )
    check.equal(
        "state.an_unassigned_kind_in_the_map_is_refused",
        _refuses(lambda: s.ordered_entries({bytes([200]): b""})),
    )
    check.equal(
        "state.a_pool_value_of_the_wrong_width_is_refused",
        _refuses(lambda: s.ordered_entries({s.recovery_pool_key(): bytes(39)})),
    )


def check_genesis(check) -> None:
    genesis = g.Genesis(
        network_id=7,
        supply_limit=e.MAXIMUM_SUPPLY_ATOMIC,
        fixed_transfer_fee=100_000,
        manifest_digest=bytes.fromhex(e.MANIFEST_DIGEST),
        verifier_key=bytes(range(32)),
    )
    entries = g.initial_economy_entries(genesis.verifier_key)
    check.agree(
        "genesis.economy_entry_count", len(e.GENESIS_ECONOMY_ENTRIES), len(entries)
    )
    check.equal(
        "genesis.writes_one_recovery_pool_entry",
        s.recovery_pool_key() in entries,
    )
    check.equal(
        "genesis.the_recovery_pool_opens_empty",
        s.decode_recovery_pool_value(entries[s.recovery_pool_key()])
        == t.empty_pool(),
    )
    check.equal(
        "genesis.writes_no_carry_entry",
        not any(key[0] == 7 for key in entries),
    )
    check.equal(
        "genesis.replaces_ten_carry_entries_with_one",
        len(entries) == 23 - 10 + 1,
    )
    check.agree("genesis.prefix_bytes", e.GENESIS_PREFIX_BYTES, len(g.encode(genesis)))
    check.agree(
        "genesis.schema_version", e.GENESIS_SCHEMA_VERSION, c.GENESIS_SCHEMA_VERSION
    )
    admitted, within, beyond = g.maximum_accounts_bound()
    check.agree("genesis.max_accounts_admitted", e.MAX_GENESIS_ACCOUNTS, admitted)
    check.equal("genesis.max_accounts_within_bytes", within)
    check.equal("genesis.max_accounts_beyond_bytes", beyond)
    check.equal("genesis.accounts_are_required_to_be_zero", _refuses_accounts(g, genesis))


def check_storage_bounds(check) -> None:
    """Requirement 12: ten entries out, one in, and every record 40 octets up."""
    seats = e.FOUNDER_SEAT_CAPACITY
    carry_bytes_removed = 10 * (2 + 8)
    pool_bytes_added = e.entry_bytes(e.RECOVERY_POOL_ENTRY)
    check.equal("storage.carry_bytes_removed", carry_bytes_removed)
    check.equal("storage.recovery_pool_bytes_added", pool_bytes_added)
    check.equal(
        "storage.fixed_entry_bytes_saved", carry_bytes_removed - pool_bytes_added
    )
    record = e.entry_bytes(3, seats)
    six_record = record - 8 * len(e.RECOVERY_POOL_LEGS)
    check.equal("storage.cycle_assignment_bytes_at_capacity", record)
    check.equal("storage.cycle_assignment_growth_at_capacity", record - six_record)
    check.equal(
        "storage.cycle_assignment_growth_is_under_one_part_in_five_hundred",
        (record - six_record) * 500 < six_record,
    )


def _refuses(call) -> bool:
    try:
        call()
    except Exception:
        return True
    return False


def _refuses_accounts(module, genesis) -> bool:
    from dataclasses import replace

    return _refuses(
        lambda: module.encode(replace(genesis, accounts=[(bytes(32), 0, 0)]))
    )
