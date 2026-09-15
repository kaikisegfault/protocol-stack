#!/usr/bin/env python3
"""Independently derive and check the economy-transition-v9 vectors.

Every recorded value is rederived twice: once from the accepted documents in
`expected.py`, which imports nothing from `simulation/`, and once from a live run
of `simulation/economy_transition_v9`. A value both reach has been derived by two
constructions; a value only the model reproduces would be a restatement of the
model rather than evidence about it.

`--emit` rewrites the vector file from the same derivations through the same
agreement gate, so a recorded value is never transcribed by hand.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import expected as e
from checker import Checker, read_vectors

from simulation.common.canonical import CodedError
from simulation.economy_transition_v6.envelope import Transaction
from simulation.economy_transition_v8 import contract as v8c
from simulation.economy_transition_v8 import state as v8state
from simulation.economy_transition_v9 import contract as c
from simulation.economy_transition_v9 import (
    envelope,
    genesis,
    header,
    scenario,
    settlement,
)
from simulation.economy_transition_v9 import state, timeline
from simulation.unreferred_pool import scenario as pool_scenario


def check_version_identity(check: Checker) -> None:
    check.section(
        "Four constructions are re-versioned and every other label keeps the "
        "version that accepted it. The block identifier and the header schema "
        "version move for the first time since version one, because version "
        "nine is the first version to change the header's bytes."
    )
    check.agree("identity.chain_id_label", e.CHAIN_ID_LABEL, c.CHAIN_ID_LABEL)
    check.agree("identity.state_root_label", e.STATE_ROOT_LABEL, c.STATE_ROOT_LABEL)
    check.agree(
        "identity.economy_tree_prefix", e.ECONOMY_TREE_PREFIX, c.ECONOMY_TREE_PREFIX
    )
    check.agree("identity.block_id_label", e.BLOCK_ID_LABEL, c.BLOCK_ID_LABEL)
    check.agree(
        "identity.genesis_schema_version", e.SCHEMA_VERSION, c.GENESIS_SCHEMA_VERSION
    )
    check.agree(
        "identity.state_root_schema_version",
        e.SCHEMA_VERSION,
        c.STATE_ROOT_SCHEMA_VERSION,
    )
    check.agree(
        "identity.block_header_schema_version",
        e.BLOCK_HEADER_SCHEMA_VERSION,
        c.BLOCK_HEADER_SCHEMA_VERSION,
    )
    check.agree("identity.receipt_version", e.RECEIPT_VERSION, c.RECEIPT_VERSION)

    check.section(
        "Every inherited label keeps the version that accepted it, because a "
        "label names the artifact it derives and none of those artifacts "
        "changed. The mint message kind 22 reuses is version six's."
    )
    for name, label in (
        ("sign", c.SIGN_LABEL),
        ("transaction_id", c.TX_ID_LABEL),
        ("mint_confirm", c.MINT_CONFIRM_LABEL),
        ("challenge", c.CHALLENGE_LABEL),
        ("dispute", c.DISPUTE_LABEL),
    ):
        check.equal(f"identity.carried_label.{name}", label)
    check.equal(
        "identity.carried_label.mint_confirm_is_version_six",
        c.MINT_CONFIRM_LABEL == e.MINT_CONFIRM_LABEL,
    )


def check_widths(check: Checker) -> None:
    check.section(
        "The block header is version one's with the timestamp inserted after "
        "the height, which moves every later offset. Appending would have "
        "preserved them, and that is a hazard rather than a benefit: a loose "
        "decoder would read a version-nine header as a version-one header with "
        "eight trailing octets and agree with itself about every field."
    )
    check.agree(
        "header.bytes", e.BLOCK_HEADER_BYTES, c.BLOCK_HEADER_BYTES
    )
    check.equal("header.timestamp_offset", e.BLOCK_TIMESTAMP_OFFSET)
    check.equal("header.grew_by", c.BLOCK_HEADER_BYTES - 146)
    check.equal("header.version_eight_bytes", 146)

    chain_id = bytes(range(32))
    previous = bytes([0xA0]) * 32
    transactions = bytes([0xB0]) * 32
    resulting = bytes([0xC0]) * 32
    derived = e.block_header(
        c.GENESIS_MAGIC.replace(b"PSGN", b"PSBL"),
        chain_id,
        4,
        scenario.GENESIS_MILLIS,
        previous,
        transactions,
        resulting,
        2,
    )
    live = header.block_header(
        chain_id,
        4,
        scenario.GENESIS_MILLIS,
        previous.hex(),
        transactions.hex(),
        resulting.hex(),
        2,
    )
    check.agree("header.bytes_encoded", derived.hex(), live.hex())
    check.agree("header.encoded_length", len(derived), len(live))
    check.equal(
        "header.timestamp_field",
        int.from_bytes(live[46:54], "big") == scenario.GENESIS_MILLIS,
    )
    check.agree(
        "header.block_id",
        e.digest(e.BLOCK_ID_LABEL, derived).hex(),
        header.block_id(live),
    )
    check.equal(
        "header.block_id_differs_from_version_ones",
        header.block_id(live) != header.predecessor_block_id(live),
    )
    try:
        header.block_header(
            chain_id, 4, c.MAX_TIMESTAMP_MILLIS + 1, previous.hex(),
            transactions.hex(), resulting.hex(), 2,
        )
        refused = False
    except Exception:
        refused = True
    check.equal("header.refuses_a_timestamp_outside_the_range", refused)

    check.section(
        "Genesis gains a u64 after the network identifier. account_count stays "
        "last, which it must: the account entries follow it. The account bound "
        "is unchanged, because 48-octet entries absorb eight more prefix octets "
        "without crossing an entry boundary."
    )
    check.agree(
        "genesis.prefix_bytes", e.GENESIS_PREFIX_BYTES, c.GENESIS_PREFIX_BYTES
    )
    check.equal("genesis.timestamp_offset", e.GENESIS_TIMESTAMP_OFFSET)
    check.equal("genesis.version_eight_prefix_bytes", v8c.GENESIS_PREFIX_BYTES)
    check.agree(
        "genesis.max_accounts", e.MAX_GENESIS_ACCOUNTS, c.MAX_GENESIS_ACCOUNTS
    )
    check.equal(
        "genesis.max_accounts_unchanged_from_version_eight",
        c.MAX_GENESIS_ACCOUNTS == v8c.MAX_GENESIS_ACCOUNTS,
    )
    check.agree(
        "genesis.economy_entry_count",
        e.GENESIS_ECONOMY_ENTRY_COUNT,
        c.GENESIS_ECONOMY_ENTRY_COUNT,
    )

    check.section(
        "Kind 22's body is kind 4's exactly, and that is the point rather than "
        "a coincidence: a mint of a seat's award is authorized the way a mint "
        "of a seat's permissions is."
    )
    check.agree("kind22.body_bytes", e.MINT_POOL_BODY_BYTES, c.BODY_BYTES[c.MINT_POOL])
    check.equal(
        "kind22.body_equals_mint_node",
        c.BODY_BYTES[c.MINT_POOL] == c.BODY_BYTES[c.MINT_NODE],
    )
    check.equal("kind22.scheme", c.KIND_SCHEME[c.MINT_POOL])
    check.equal("kind22.transaction_kind", c.MINT_POOL)
    check.equal("kind22.is_confirmable_mint", c.MINT_POOL in c.CONFIRMABLE_MINTS)
    check.equal("kind22.is_issuing_kind", c.MINT_POOL in c.ISSUING_KINDS)
    check.equal("kind22.transaction_kind_count", len(c.TRANSACTION_KINDS))

    check.section(
        "Version nine adds no result code. Kind 22 reuses kind 4's ladder "
        "exactly, so every refusal it can produce already has a number. The "
        "opposite would be worth noticing: a new mint needing a new refusal "
        "would be a mint whose authority rules differ from every other mint's."
    )
    check.agree("codes.count", e.RESULT_CODE_COUNT, len(c.RESULT_CODES))
    check.equal("codes.unchanged_from_version_eight", c.RESULT_CODES == v8c.RESULT_CODES)
    for name in (
        "CYCLE_RANGE",
        "SEAT_NOT_PURCHASED",
        "SEAT_NOT_ACTIVATED",
        "UNAUTHORIZED",
        "ESCROW_NOT_FOUND",
        "ESCROW_NOT_OWNED",
        "NOTHING_TO_MINT",
        "BIOMETRIC_REQUIRED",
        "CHANNEL_CAP",
    ):
        check.equal(f"codes.kind22.{name.lower()}", c.CODE_NUMBER[name])

    check.section(
        "calendar-v1's four timestamp conditions produce no result code. They "
        "are block-level and belong to the application contract's status space, "
        "exactly as ledger-transition-v1's height rule does."
    )
    check.agree(
        "codes.timestamp_conditions", e.TIMESTAMP_CONDITIONS, c.TIMESTAMP_CONDITIONS
    )
    check.equal(
        "codes.no_timestamp_condition_is_a_result_code",
        not (set(c.TIMESTAMP_CONDITIONS) & set(c.CODE_NUMBER)),
    )


def check_constants(check: Checker) -> None:
    check.section(
        "The clock is calendar-v1's, bound rather than restated: a second copy "
        "of a tolerance is a second opinion, and two machines holding different "
        "tolerances is a fork."
    )
    check.agree("clock.millis_per_day", e.MILLIS_PER_DAY, c.MILLIS_PER_DAY)
    check.agree(
        "clock.min_timestamp_millis", e.MIN_TIMESTAMP_MILLIS, c.MIN_TIMESTAMP_MILLIS
    )
    check.agree(
        "clock.max_timestamp_millis", e.MAX_TIMESTAMP_MILLIS, c.MAX_TIMESTAMP_MILLIS
    )
    check.agree("clock.max_month_index", e.MAX_MONTH_INDEX, c.MAX_MONTH_INDEX)
    check.agree(
        "clock.tolerance_millis",
        e.TIMESTAMP_TOLERANCE_MILLIS,
        c.TIMESTAMP_TOLERANCE_MILLIS,
    )
    check.equal(
        "clock.tolerance_is_not_a_genesis_field",
        "timestamp_tolerance" not in genesis.Genesis.__dataclass_fields__,
    )


def check_genesis(check: Checker) -> None:
    fixture = scenario.genesis()
    derived = e.genesis_bytes(
        c.GENESIS_MAGIC,
        e.SCHEMA_VERSION,
        scenario.NETWORK_ID,
        scenario.GENESIS_MILLIS,
        scenario.SUPPLY_LIMIT,
        0,
        scenario.FIXED_TRANSFER_FEE,
        0,
        scenario.MANIFEST_DIGEST,
        scenario.VERIFIER_KEY,
        scenario.DISPUTE_AUTHORITY_KEY,
        0,
    )
    live = genesis.encode(fixture)

    check.section(
        "The genesis bytes and the chain identity, derived twice. The encoder's "
        "field order is not the declaration's: total_supply is written before "
        "fixed_transfer_fee, inherited three versions back."
    )
    check.agree("genesis.bytes", derived.hex(), live.hex())
    check.agree("genesis.encoded_bytes", len(derived), len(live))
    check.agree(
        "genesis.chain_id",
        e.digest(e.CHAIN_ID_LABEL, derived).hex(),
        genesis.chain_id(fixture).hex(),
    )
    check.agree(
        "genesis.timestamp_field",
        int.from_bytes(derived[10:18], "big"),
        int.from_bytes(live[10:18], "big"),
    )
    check.agree(
        "genesis.month", e.month_index(scenario.GENESIS_MILLIS),
        genesis.genesis_month(fixture),
    )

    check.section(
        "No version-nine chain identity equals a predecessor's. Each "
        "non-collision is required separately, because distinct labels are "
        "strings rather than a chain, and the objects are different lengths so "
        "no version-nine genesis can be read as an earlier one either."
    )
    for version in (2, 3, 4, 5, 6, 7, 8):
        check.equal(
            f"genesis.chain_id_differs_from_v{version}",
            genesis.predecessor_chain_id(fixture, version)
            != genesis.chain_id(fixture),
        )

    check.section(
        "Genesis validation applies calendar-v1's range rule and reads no "
        "clock. That is forced: the chain identity is a hash of the genesis "
        "bytes, so a validity rule that read a clock would make two machines "
        "disagree about a chain's own identifier."
    )
    for label, value in (
        ("above_the_range", e.MAX_TIMESTAMP_MILLIS + 1),
        ("below_the_range", -1),
    ):
        try:
            genesis.encode(
                genesis.Genesis(
                    network_id=scenario.NETWORK_ID,
                    genesis_timestamp=value,
                    supply_limit=scenario.SUPPLY_LIMIT,
                    fixed_transfer_fee=scenario.FIXED_TRANSFER_FEE,
                    manifest_digest=scenario.MANIFEST_DIGEST,
                    verifier_key=scenario.VERIFIER_KEY,
                    dispute_authority_key=scenario.DISPUTE_AUTHORITY_KEY,
                )
            )
            refused = False
        except Exception:
            refused = True
        check.equal(f"genesis.refuses_a_timestamp_{label}", refused)

    check.section(
        "Genesis writes sixteen economy entries: version eight's fourteen with "
        "the pool rewidened, plus the settlement cursor and window zero's "
        "month, both at the genesis month. Height zero is never a block, so "
        "genesis is window zero's opening height and writing its month here is "
        "the general rule reaching the one height that is a genesis."
    )
    entries = genesis.initial_economy_entries(fixture)
    check.equal("genesis.entry_count", len(entries))
    check.agree(
        "genesis.cursor_value",
        e.settlement_cursor_value(e.month_index(scenario.GENESIS_MILLIS)).hex(),
        entries[state.settlement_cursor_key()].hex(),
    )
    check.agree(
        "genesis.window_zero_month_value",
        e.window_month_value(e.month_index(scenario.GENESIS_MILLIS)).hex(),
        entries[state.window_month_key(genesis.GENESIS_WINDOW)].hex(),
    )
    check.agree(
        "genesis.pool_value",
        e.unreferred_pool_value(0, 0, 0).hex(),
        entries[state.unreferred_pool_key()].hex(),
    )
    check.equal(
        "genesis.twelve_entries_are_version_eights_unchanged",
        {
            key: value
            for key, value in entries.items()
            if key[0] not in (c.UNREFERRED_POOL_ENTRY, c.WINDOW_MONTH_ENTRY,
                              c.SETTLEMENT_CURSOR_ENTRY)
        }
        == {
            key: value
            for key, value in __import__(
                "simulation.economy_transition_v8.genesis", fromlist=["x"]
            ).initial_economy_entries(scenario.VERIFIER_KEY).items()
            if key[0] != c.UNREFERRED_POOL_ENTRY
        },
    )


def check_state_surface(check: Checker) -> None:
    check.section(
        "The four new entry kinds, their key and value widths derived twice, "
        "and the widened pool value that makes this a version rather than an "
        "edit: no version-eight decoder can read a version-nine kind-12 entry "
        "and no version-nine decoder can read a version-eight one."
    )
    for name, kind, key_bytes, value_bytes in (
        ("window_month", c.WINDOW_MONTH_ENTRY, e.WINDOW_MONTH_KEY_BYTES,
         e.WINDOW_MONTH_VALUE_BYTES),
        ("monthly_figure", c.MONTHLY_FIGURE_ENTRY, e.MONTHLY_FIGURE_KEY_BYTES,
         e.MONTHLY_FIGURE_VALUE_BYTES),
        ("monthly_claim", c.MONTHLY_CLAIM_ENTRY, e.MONTHLY_CLAIM_KEY_BYTES,
         e.MONTHLY_CLAIM_VALUE_BYTES),
        ("settlement_cursor", c.SETTLEMENT_CURSOR_ENTRY,
         e.SETTLEMENT_CURSOR_KEY_BYTES, e.SETTLEMENT_CURSOR_VALUE_BYTES),
    ):
        check.equal(f"state.{name}.kind", kind)
        check.agree(f"state.{name}.key_bytes", key_bytes, c.ENTRY_KEY_BYTES[kind])
        check.agree(f"state.{name}.value_bytes", value_bytes, c.ENTRY_VALUE_BYTES[kind])
    check.agree(
        "state.unreferred_pool.value_bytes",
        e.UNREFERRED_POOL_VALUE_BYTES,
        c.ENTRY_VALUE_BYTES[c.UNREFERRED_POOL_ENTRY],
    )
    check.equal(
        "state.unreferred_pool.value_bytes_in_version_eight",
        v8c.ENTRY_VALUE_BYTES[c.UNREFERRED_POOL_ENTRY],
    )
    check.equal("state.entry_kind_count", len(c.ENTRY_KINDS))

    check.section("The encodings themselves, derived twice.")
    check.agree(
        "state.window_month.key", e.window_month_key(4).hex(),
        state.window_month_key(4).hex(),
    )
    check.agree(
        "state.window_month.value", e.window_month_value(674).hex(),
        state.window_month_value(674).hex(),
    )
    check.agree(
        "state.monthly_figure.key", e.monthly_figure_key(674, 2).hex(),
        state.monthly_figure_key(674, 2).hex(),
    )
    check.agree(
        "state.monthly_figure.value", e.monthly_figure_value(216_000).hex(),
        state.monthly_figure_value(216_000).hex(),
    )
    check.agree(
        "state.monthly_claim.key", e.monthly_claim_key(2).hex(),
        state.monthly_claim_key(2).hex(),
    )
    check.agree(
        "state.monthly_claim.value", e.monthly_claim_value(9_120_000_000, 0).hex(),
        state.monthly_claim_value(9_120_000_000, 0).hex(),
    )
    check.agree(
        "state.settlement_cursor.key", e.settlement_cursor_key().hex(),
        state.settlement_cursor_key().hex(),
    )
    check.agree(
        "state.settlement_cursor.value", e.settlement_cursor_value(679).hex(),
        state.settlement_cursor_value(679).hex(),
    )
    check.agree(
        "state.unreferred_pool.value",
        e.unreferred_pool_value(23_940_000_001, 3_420_000_001, 0).hex(),
        state.unreferred_pool_value(23_940_000_001, 3_420_000_001, 0).hex(),
    )

    check.section(
        "A zero is absence in two of the four new values, and the decoders say "
        "so. A candidate with no figure has a figure of zero by absence and a "
        "seat that has won nothing has no claim, so writing either would give "
        "one fact two encodings. In the zero-best month that is up to 100,000 "
        "entries recording that nobody was paid."
    )
    for label, call in (
        ("figure_of_zero", lambda: state.monthly_figure_value(0)),
        ("claim_of_zero", lambda: state.monthly_claim_value(0, 0)),
        ("claim_minting_more_than_it_accrued",
         lambda: state.monthly_claim_value(10, 11)),
        ("month_above_the_calendar_bound",
         lambda: state.window_month_value(c.MAX_MONTH_INDEX + 1)),
        ("cursor_above_the_calendar_bound",
         lambda: state.settlement_cursor_value(c.MAX_MONTH_INDEX + 1)),
        ("figure_key_above_the_calendar_bound",
         lambda: state.monthly_figure_key(c.MAX_MONTH_INDEX + 1, 1)),
        ("pool_payable_above_accrued",
         lambda: state.unreferred_pool_value(1, 2, 0)),
        ("pool_minting_more_than_it_assigned",
         lambda: state.unreferred_pool_value(10, 5, 6)),
    ):
        try:
            call()
            refused = False
        except state.InvalidStateEntry:
            refused = True
        check.equal(f"state.refuses_a_{label}", refused)

    check.section(
        "A version-eight decoder refuses every version-nine entry, by kind or "
        "by width. This is the compatibility boundary stated as behaviour "
        "rather than as a sentence about lengths."
    )
    for name, key, value in (
        ("window_month", state.window_month_key(4), state.window_month_value(674)),
        ("monthly_figure", state.monthly_figure_key(674, 2),
         state.monthly_figure_value(216_000)),
        ("monthly_claim", state.monthly_claim_key(2),
         state.monthly_claim_value(1, 0)),
        ("settlement_cursor", state.settlement_cursor_key(),
         state.settlement_cursor_value(679)),
        ("widened_pool", state.unreferred_pool_key(),
         state.unreferred_pool_value(1, 1, 0)),
    ):
        try:
            v8state.require_entry_shape(key, value)
            refused = False
        except v8state.InvalidStateEntry:
            refused = True
        check.equal(f"state.version_eight_refuses_the_{name}", refused)

    check.section(
        "Two window-month entries are live and not the three "
        "unreferred-pool-payout-v1 sized for. That document counts the open "
        "window and the two inside the assignment lag; version nine deletes the "
        "oldest of the three in the same prologue that assigns it, so at every "
        "point inside a block the entries are the open window's and its "
        "predecessor's."
    )
    check.agree(
        "state.live_window_months", e.LIVE_WINDOW_MONTHS, c.LIVE_WINDOW_MONTHS
    )
    check.equal("state.live_window_months_sized_by_the_payout_spec", 3)


def check_timestamp_rules(check: Checker) -> None:
    check.section(
        "calendar-v1's five rules, each reached on its own and in its normative "
        "order. The two tolerance conditions are the two sides of C5 and are "
        "separately named so each can be tested alone: a one-sided rule would "
        "let a colluding proposer set hold the chain's clock back indefinitely "
        "and pay nobody while satisfying every other rule."
    )
    head = scenario.genesis_head()
    accepted: list[tuple[int, int]] = []
    for height, timestamp, clock, label in scenario.proposals():
        derived = e.timestamp_condition(
            head.height + 1, head.timestamp, height, timestamp, clock
        )
        try:
            advanced = timeline.accept(head, height, timestamp, clock)
            live = "ACCEPTED"
        except CodedError as refusal:
            live = refusal.code
            advanced = head
        check.agree(f"timestamp.{label}", derived, live)
        if live == "ACCEPTED":
            accepted.append((height, timestamp))
        head = advanced

    check.section(
        "Every one of the five conditions is reached by the recorded "
        "proposals, counted rather than assumed, so a later scenario cannot "
        "lose coverage while still passing."
    )
    conditions = set()
    replay_head = scenario.genesis_head()
    for height, timestamp, clock, _label in scenario.proposals():
        outcome = e.timestamp_condition(
            replay_head.height + 1, replay_head.timestamp, height, timestamp, clock
        )
        conditions.add(outcome)
        if outcome == "ACCEPTED":
            replay_head = timeline.Head(height, timestamp)
    check.equal(
        "timestamp.every_condition_is_reached",
        set(c.TIMESTAMP_CONDITIONS) <= conditions,
    )
    check.equal("timestamp.conditions_reached", len(conditions))

    check.section(
        "The clockless replay of an accepted chain agrees height for height. "
        "This is the evidence that C5 is not on the replay path: a machine that "
        "re-applied the tolerance while replaying history would reject the "
        "chain's own past one tolerance-width after it was produced."
    )
    replayed = scenario.genesis_head()
    for height, timestamp in accepted:
        replayed = timeline.replay(replayed, height, timestamp)
    check.agree("replay.head_height", accepted[-1][0], replayed.height)
    check.agree("replay.head_timestamp", accepted[-1][1], replayed.timestamp)
    check.equal("replay.accepted_height_count", len(accepted))

    stale_clock = scenario.GENESIS_MILLIS - 10 * c.TIMESTAMP_TOLERANCE_MILLIS
    survivors = 0
    head = scenario.genesis_head()
    for height, timestamp in accepted:
        try:
            timeline.accept(head, height, timestamp, stale_clock)
            survivors += 1
        except CodedError:
            pass
        head = timeline.Head(height, timestamp)
    check.equal(
        "replay.a_stale_clock_would_reject_the_chains_own_past", survivors == 0
    )

    check.section(
        "The version-nine restatement of the rules is the accepted model's, "
        "outcome for outcome and condition for condition, over the same "
        "proposals. A restatement that merely accepted the same blocks would "
        "not be checked: the ordered conditions are the part a second "
        "implementation gets wrong."
    )
    timeline.assert_agrees_with_calendar_v1(
        scenario.GENESIS_MILLIS,
        [(h, t, cl) for h, t, cl, _ in scenario.proposals()],
    )
    check.equal("timestamp.agrees_with_calendar_v1", True)


def check_calendar_over_the_chain(check: Checker) -> None:
    months = scenario.window_months()
    check.section(
        "A window is attributed to the month containing its first height. The "
        "fixture's genesis sits six hours off a day boundary, so one window "
        "straddles a month boundary, and the month a last-height attribution "
        "would have chosen is recorded beside the real one so the accepted rule "
        "and the rejected one are distinguishable rather than merely described."
    )
    for index in sorted(months):
        first = scenario.timestamp_of_height(index * c.CYCLE_BLOCKS)
        check.agree(f"attribution.window_{index}.month", e.month_index(first), months[index])
    from simulation.calendar import months as calendar_months

    for index in pool_scenario.straddling_windows():
        last = scenario.timestamp_of_height((index + 1) * c.CYCLE_BLOCKS - 1)
        check.equal(f"attribution.window_{index}.straddles", True)
        check.agree(
            f"attribution.window_{index}.month_under_the_rejected_rule",
            e.month_index(last),
            calendar_months.month_index(last),
        )
        check.equal(
            f"attribution.window_{index}.the_two_rules_disagree",
            calendar_months.month_index(last) != months[index],
        )
    check.equal(
        "attribution.straddling_windows", len(pool_scenario.straddling_windows())
    )
    check.section(
        "Window zero's month is genesis's, because height zero is never a "
        "block: a chain starts at height one, so genesis is window zero's "
        "opening height."
    )
    check.agree(
        "attribution.window_zero_month",
        e.month_index(scenario.GENESIS_MILLIS),
        months[0],
    )
    check.equal(
        "attribution.no_seat_is_in_scope_at_window_zero",
        settlement.candidates(scenario.ACTIVATIONS, 0) == (),
    )


def check_settlement(check: Checker) -> None:
    live = scenario.run()
    closed = e.settle(
        pool_scenario.SEQUENCE, scenario.ACTIVATIONS, lambda w: scenario.window_months()[w]
    )

    check.section(
        "The recorded settlement, derived twice: once by a machine consuming "
        "one window at a time and carrying a balance, and once by a closed-form "
        "fold that groups the whole sequence by month first. Two different "
        "shapes reaching the same claims is what makes a recorded value "
        "evidence."
    )
    check.agree("settlement.pool_accrued", closed["accrued"], live["pool"].accrued)
    check.agree("settlement.pool_payable", closed["payable"], live["pool"].payable)
    check.agree("settlement.cursor", closed["cursor"], live["cursor"])
    check.agree(
        "settlement.claims",
        ";".join(f"{seat}:{amount}" for seat, amount in sorted(closed["claims"].items())),
        ";".join(
            f"{seat}:{accrued}"
            for seat, (accrued, _minted) in sorted(live["claims"].items())
        ),
    )
    check.agree(
        "settlement.open_figures",
        ";".join(
            f"{seat}:{seconds}" for seat, seconds in sorted(closed["open_figures"].items())
        ),
        ";".join(
            f"{seat}:{seconds}"
            for (_month, seat), seconds in sorted(live["figures"].items())
        ),
    )

    for derived, actual in zip(closed["settlements"], live["settlements"]):
        prefix = f"settlement.month_{actual.month}"
        check.agree(f"{prefix}.candidate_count", derived["candidate_count"],
                    actual.candidate_count)
        check.agree(f"{prefix}.best_figure", derived["best_figure"], actual.best_figure)
        check.agree(
            f"{prefix}.winners",
            ",".join(str(seat) for seat in derived["winners"]),
            ",".join(str(seat) for seat in actual.winners),
        )
        check.agree(f"{prefix}.payable_before", derived["payable_before"],
                    actual.payable_before)
        check.agree(f"{prefix}.share", derived["share"], actual.share)
        check.agree(f"{prefix}.remainder", derived["remainder"], actual.remainder)
        check.agree(f"{prefix}.assigned", derived["assigned"], actual.assigned)

    check.section(
        "A month that accrued nothing pays nothing and that is not an error; a "
        "share that rounds to zero writes no claim entry, because a claim is a "
        "balance and a balance of zero is absence; and a remainder stays in the "
        "pool and is distributed with the next month that pays."
    )
    february = live["settlements"][0]
    check.equal("settlement.february_pays_nothing", february.assigned == 0)
    check.equal("settlement.february_writes_no_claim", february.share == 0)
    check.equal(
        "settlement.remainders_carry",
        all(s.remainder == 0 or s.remainder < len(s.winners) for s in live["settlements"]
            if s.winners),
    )

    zero_share = settlement.settle_month(700, (1, 2, 3), {}, 2)
    pool = settlement.Pool(accrued=2, payable=2)
    claims: dict[int, tuple[int, int]] = {}
    figures: dict[tuple[int, int], int] = {}
    settlement.apply_settlement(zero_share, pool, claims, figures)
    check.equal("settlement.zero_share_writes_no_claim", claims == {})
    check.equal("settlement.zero_share_carries_the_whole_balance", pool.payable == 2)
    check.equal("settlement.zero_share_winner_count", len(zero_share.winners))

    check.section(
        "A month in which no candidate was credited for a single slot is a "
        "zero-best month: every candidate ties and shares. ADR 0075 declined a "
        "duty gate and ADR 0076 declined an accumulation-cap filter, so it is "
        "not an error and it is not to be filtered."
    )
    may = [s for s in live["settlements"] if s.best_figure == 0 and s.winners]
    check.equal("settlement.zero_best_months", len(may))
    check.equal(
        "settlement.zero_best_month_pays_every_candidate",
        all(len(s.winners) == s.candidate_count for s in may),
    )

    check.section(
        "Exactly one month closes per assignment and the empty indices are "
        "skipped, because window attribution is non-decreasing and consecutive "
        "assigned windows carry the cursor's month and the new one with nothing "
        "between them. Iterating them would make one block's work proportional "
        "to how long the network was down."
    )
    check.agree(
        "settlement.skipped_months",
        ",".join(str(month) for month in closed["skipped"]),
        ",".join(str(month) for month in live["skipped"]),
    )
    check.equal("settlement.settled_month_count", len(live["settlements"]))

    check.section(
        "The single pass and an explicit per-index loop agree state for state "
        "over a multi-month halt. This is the evidence the equivalence needs, "
        "because no invariant over a single accepted state separates the two: "
        "they agree on every state both produce, so what distinguishes them is "
        "a scenario."
    )
    settlement.assert_single_pass_equals_loop(
        676,
        679,
        scenario.ACTIVATIONS,
        63,
        settlement.Pool(accrued=10_000, payable=10_000),
        {},
        {(676, 1): 86_400},
    )
    check.equal("settlement.single_pass_equals_the_loop", True)
    check.equal("settlement.halt_months_closed_in_one_pass", 679 - 676)

    check.section(
        "The version-nine arithmetic is unreferred-pool-payout-v1's model's, "
        "month for month over the recorded run. A restatement that reached a "
        "different winner would fail here rather than survive as a second "
        "opinion about who is paid."
    )
    reference = pool_scenario.build()
    folded: dict[int, int] = {}
    for (_month, seat), amount in reference.claims.items():
        folded[seat] = folded.get(seat, 0) + amount
    check.equal(
        "settlement.agrees_with_the_payout_model",
        folded == {seat: accrued for seat, (accrued, _m) in live["claims"].items()},
    )
    check.equal(
        "settlement.payout_model_carries_the_same_months",
        tuple(p.month for p in reference.payouts if not p.winners) == live["skipped"],
    )

    check.section(
        "The two pool identities, checked over the encoded state after the "
        "recorded run rather than argued. The second is the one "
        "unreferred-pool-payout-v1 names for completeness and leaves to the "
        "version that implements a mint, and version nine states it as an "
        "equality because an equality catches a unit minted twice."
    )
    live["pool"].assert_conserved(live["claims"])
    check.equal("settlement.conserved", True)
    check.equal(
        "settlement.assigned_total",
        sum(accrued for accrued, _m in live["claims"].values()),
    )


def check_kind_twenty_two(check: Checker) -> None:
    check.section(
        "Kind 22's body and its signed length, derived twice, and the mint "
        "message it reuses. No new domain-separated label is added: version "
        "six's message already binds the transaction kind, precisely so a "
        "confirmation obtained for one mint cannot be replayed onto another."
    )
    seat, destination, signature = 3, bytes([0x31]) * 32, bytes([0x9C]) * 64
    derived_body = e.mint_pool_body(seat, destination, signature)
    live_body = envelope.body_bytes(
        c.MINT_POOL,
        {
            "seat_id": seat,
            "destination_escrow_id": destination,
            "hub_signature": signature,
        },
    )
    check.agree("kind22.body", derived_body.hex(), live_body.hex())
    check.agree(
        "kind22.signed_length",
        e.HEADER_BYTES + e.MINT_POOL_BODY_BYTES + e.TRAILER_BYTES + e.SIGNATURE_BYTES,
        envelope.expected_signed_length(c.MINT_POOL),
    )

    chain_id = bytes(range(32))
    identity = bytes(range(32, 64))
    messages = {
        kind: envelope.mint_message(chain_id, identity, kind, 7, destination, 4_321)
        for kind in sorted(c.CONFIRMABLE_MINTS)
    }
    check.section(
        "The four confirmable mints differ on identical remaining fields, and "
        "the byte that differs is the kind. Kind 22's message is derived twice."
    )
    check.agree(
        "kind22.mint_message",
        e.mint_message(chain_id, identity, c.MINT_POOL, 7, destination, 4_321).hex(),
        messages[c.MINT_POOL].hex(),
    )
    check.equal(
        "kind22.four_mint_messages_are_distinct", len(set(messages.values())) == 4
    )
    envelope.assert_agrees_with_version_six()
    check.equal("kind22.mint_message_agrees_with_version_six", True)

    check.section(
        "A version-nine kind-22 transaction round-trips, and version eight "
        "refuses it as an unknown kind rather than decoding it as something "
        "else."
    )
    transaction = Transaction(
        kind=c.MINT_POOL,
        scheme=c.SCHEME_SIGNER,
        chain_id=chain_id,
        authority_public_key=bytes([0x5A]) * 32,
        nonce=4,
        body={
            "seat_id": seat,
            "destination_escrow_id": destination,
            "hub_signature": signature,
        },
        fee_limit=scenario.FIXED_TRANSFER_FEE,
        valid_until_height=4_321,
    )
    raw = envelope.signed_bytes(transaction, bytes([0x77]) * 64)
    decoded, _signature = envelope.decode_signed(raw)
    check.equal("kind22.round_trips", envelope.signed_bytes(decoded, bytes([0x77]) * 64) == raw)
    check.equal("kind22.signed_bytes", len(raw))

    from simulation.economy_transition_v8 import envelope as v8envelope

    try:
        v8envelope.decode_signed(raw)
        refused = False
    except v8envelope.MalformedTransaction:
        refused = True
    check.equal("kind22.version_eight_refuses_it", refused)


def check_carryover(check: Checker) -> None:
    check.section(
        "The carryover declaration partitions version eight's public surface "
        "exactly, so a constant that moved without a vector reaching it fails a "
        "test rather than surviving as a copy nobody compared."
    )
    surface = {
        name
        for name in dir(v8c)
        if name.isupper() and not name.startswith("_")
    }
    classified = (
        set(c.CARRIED_FROM_V8)
        | set(c.REVISED_IN_V9)
        | set(c.REPLACED_DECLARATIONS)
    )
    check.equal("carryover.version_eight_surface", len(surface))
    check.equal("carryover.classification_is_total", classified == surface)
    check.equal("carryover.carried", len(c.CARRIED_FROM_V8))
    check.equal("carryover.revised", len(c.REVISED_IN_V9))
    check.equal("carryover.added", len(c.ADDED_IN_V9))
    check.equal("carryover.replaced_declarations", len(c.REPLACED_DECLARATIONS))
    check.equal(
        "carryover.every_carried_constant_is_version_eights_own_object",
        all(getattr(c, name) is getattr(v8c, name) for name in c.CARRIED_FROM_V8),
    )
    check.equal(
        "carryover.every_revised_constant_moved",
        all(getattr(c, name) != getattr(v8c, name) for name in c.REVISED_IN_V9),
    )
    check.equal(
        "carryover.every_added_constant_is_new",
        all(not hasattr(v8c, name) for name in c.ADDED_IN_V9),
    )
    c.assert_account_bound_unchanged()
    check.equal(
        "carryover.the_account_bound_survives_the_wider_prefix",
        c.ACCOUNT_BOUND_UNDER_THE_WIDER_PREFIX == c.MAX_GENESIS_ACCOUNTS,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vectors", type=Path, required=True)
    parser.add_argument("--emit", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    check = Checker(read_vectors(args.vectors), emit=args.emit)

    check_version_identity(check)
    check_widths(check)
    check_constants(check)
    check_genesis(check)
    check_state_surface(check)
    check_timestamp_rules(check)
    check_calendar_over_the_chain(check)
    check_settlement(check)
    check_kind_twenty_two(check)
    check_carryover(check)
    check.require_full_coverage()

    if check.failures:
        for failure in check.failures:
            print(f"FAIL {failure}", file=sys.stderr)
        return 1
    if args.emit:
        written = check.write(args.vectors)
        print(f"wrote {written} vectors to {args.vectors}")
        return 0
    print(f"economy-transition-v9: {check.checked} vectors checked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
