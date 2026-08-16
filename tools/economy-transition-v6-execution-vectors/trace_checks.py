"""Derive every recorded execution vector and record only what agrees.

The independent side is `expected.py`, which imports nothing from `simulation/`.
The live side is a real run of the execution model. Every value two sources can
reach is recorded only when both produce it; a value only one source can reach —
a property of a state, a count of blocks in a fixture — is recorded from the one
source and is a claim the file pins rather than a claim it proves twice.

Three constructions are checked against a third source before anything rests on
them: the ordered transaction tree against `protocol-primitives-v1.txt`'s
recorded `tx.root`, the block header and block ID against
`ledger-transition-v1.txt`'s recorded pair, and the accepted version-one signed
transfer and its transaction ID against `protocol-primitives-v1.txt` itself.
Without those, a restated construction that had drifted would agree only with
itself.
"""

from __future__ import annotations

from pathlib import Path

import expected as e
from checker import Checker, read_vectors

from simulation.economy_transition_v6 import trace
from simulation.economy_transition_v6.block import (
    BLOCK_HEADER_SCHEMA_VERSION,
    block_header,
    transaction_root,
)
from simulation.economy_transition_v6.genesis import chain_id as derive_chain_id
from simulation.economy_transition_v6.genesis import encode as encode_genesis

TRANSFER_AMOUNT = 1_000_000


def check_constructions(check: Checker, accepted: Path) -> None:
    """The two inherited constructions, each against the file that fixes it."""
    check.section("The inherited constructions, checked against accepted vectors.")
    primitives = read_vectors(accepted / "protocol-primitives-v1.txt")
    items = [bytes.fromhex(primitives[f"tx.item{index}"]) for index in range(3)]

    check.equal("construction.transaction_tree_prefix", e.TRANSACTION_TREE_PREFIX)
    check.agree(
        "construction.transaction_root_over_the_accepted_items",
        e.transaction_root_hex(items),
        transaction_root(items).hex(),
    )
    check.equal(
        "construction.transaction_root_reproduces_the_accepted_vector",
        e.transaction_root_hex(items) == primitives["tx.root"],
    )
    check.agree(
        "construction.empty_transaction_root",
        e.transaction_root_hex([]),
        transaction_root([]).hex(),
    )
    check.equal(
        "construction.empty_transaction_root_reproduces_the_accepted_vector",
        e.transaction_root_hex([]) == primitives["tx.empty_root"],
    )

    ledger_vectors = read_vectors(accepted / "ledger-transition-v1.txt")
    recorded = bytes.fromhex(ledger_vectors["block_header"])
    fields = (
        recorded[6:38],
        int.from_bytes(recorded[38:46], "big"),
        ledger_vectors["previous_state_root"],
        ledger_vectors["transaction_root"],
        ledger_vectors["resulting_state_root"],
        int.from_bytes(recorded[142:146], "big"),
    )
    derived = e.block_header_bytes(
        fields[0],
        fields[1],
        bytes.fromhex(fields[2]),
        bytes.fromhex(fields[3]),
        bytes.fromhex(fields[4]),
        fields[5],
    )
    check.agree(
        "construction.block_header_over_the_accepted_fields",
        derived.hex(),
        block_header(*fields).hex(),
    )
    check.equal(
        "construction.block_header_reproduces_the_accepted_version_one_header",
        derived == recorded,
    )
    check.equal(
        "construction.block_id_reproduces_the_accepted_version_one_block_id",
        e.block_id_hex(derived) == ledger_vectors["block_id"],
    )
    check.equal("construction.block_header_bytes", e.BLOCK_HEADER_BYTES)
    # Version six re-versions genesis, the receipt, and the state root, and says
    # nothing about the header, so `protocol-primitives-v1`'s value governs.
    check.agree(
        "construction.block_header_schema_version",
        e.BLOCK_HEADER_SCHEMA_VERSION,
        BLOCK_HEADER_SCHEMA_VERSION,
    )


def check_genesis(check: Checker) -> None:
    check.section("The genesis the whole trace runs on: a nonzero fee, no allocation.")
    genesis = trace.genesis()
    derived = e.genesis_bytes(
        trace.NETWORK_ID,
        trace.SUPPLY_LIMIT,
        trace.FIXED_FEE,
        genesis.manifest_digest,
        genesis.verifier_key,
    )
    check.agree("genesis.bytes", derived.hex(), encode_genesis(genesis).hex())
    check.agree(
        "genesis.chain_id",
        e.digest(e.CHAIN_ID_LABEL, derived).hex(),
        derive_chain_id(genesis).hex(),
    )
    check.agree("genesis.fixed_fee", e.FIXED_FEE, trace.FIXED_FEE)
    check.equal("genesis.entry_airdrop_atomic", e.entry_airdrop())
    check.equal("genesis.economy_entries", e.GENESIS_ECONOMY_ENTRIES)
    # Version two derived that a conforming chain must permit a zero fee,
    # because a zero allocation and a nonzero fee leave nobody able to pay for
    # the first transaction. Registration is fee-exempt and pays the airdrop.
    check.equal(
        "genesis.a_nonzero_fixed_fee_is_reachable_from_a_version_six_genesis",
        trace.FIXED_FEE > 0
        and genesis.total_supply == 0
        and not genesis.accounts
        and e.entry_airdrop() > trace.FIXED_FEE,
    )


def check_scenario(check: Checker, scenario, totals: dict[str, int], shape: int) -> None:
    """Every block's commitments, and every step's result and receipt."""
    name = scenario.name
    check.section(f"Scenario {name}.")
    issued = _issued_by_label(name, totals)
    ledger = scenario.ledger

    check.equal(f"{name}.block_count", len(scenario.blocks))
    for label, code in scenario.rejected.items():
        expected_code, _reason = e.EXPECTED_ADMISSIONS[label]
        check.agree(f"{name}.{label}.admission_code", expected_code, code)
    check.equal(
        f"{name}.admission_failures_produce_no_receipt",
        sum(scenario.raw_inputs) - sum(len(block.executed) for block in scenario.blocks)
        == len(scenario.rejected),
    )
    check.equal(f"{name}.blocks_skipped_between_segments", scenario.skipped_blocks)
    for index, (block, labels) in enumerate(zip(scenario.blocks, scenario.labels)):
        prefix = f"{name}.block{index}"
        check.equal(f"{prefix}.height", block.height)
        check.equal(f"{prefix}.raw_input_count", scenario.raw_inputs[index])
        check.equal(f"{prefix}.admitted_count", len(block.executed))
        check.agree(
            f"{prefix}.transaction_root",
            e.transaction_root_hex(block.admitted_ids),
            block.transaction_root,
        )
        header = e.block_header_bytes(
            ledger.chain_id,
            block.height,
            bytes.fromhex(block.previous_state_root),
            bytes.fromhex(block.transaction_root),
            bytes.fromhex(block.resulting_state_root),
            len(block.executed),
        )
        check.agree(f"{prefix}.header", header.hex(), block.header.hex())
        check.agree(f"{prefix}.block_id", e.block_id_hex(header), block.block_id)
        check.equal(f"{prefix}.resulting_state_root", block.resulting_state_root)
        for position, (label, entry) in enumerate(zip(labels, block.executed)):
            result, _reason = e.EXPECTED_RESULTS[label]
            check.agree(f"{name}.{label}.result", result, entry.result)
            check.equal(f"{name}.{label}.result_code", e.CODE_NUMBER[result])
            check.agree(
                f"{name}.{label}.receipt",
                e.receipt_hex(
                    entry.transaction_id,
                    entry.kind,
                    e.CODE_NUMBER[result],
                    _expected_fee(entry.kind, result),
                    issued.get(label, 0) if result == "SUCCESS" else 0,
                ),
                block.receipts[position].hex(),
            )

    # A block that follows its predecessor by one height must open on exactly
    # the root its predecessor committed. A segment boundary is a run of empty
    # blocks the trace does not execute, so those pairs are excluded by the
    # height test rather than by an exception.
    consecutive = [
        (earlier, later)
        for earlier, later in zip(scenario.blocks, scenario.blocks[1:])
        if later.height == earlier.height + 1
    ]
    check.equal(f"{name}.consecutive_block_pairs", len(consecutive))
    check.equal(
        f"{name}.every_consecutive_block_opens_on_its_predecessor_root",
        all(
            later.previous_state_root == earlier.resulting_state_root
            for earlier, later in consecutive
        ),
    )
    check.equal(
        f"{name}.heights_never_decrease",
        all(
            later.height > earlier.height
            for earlier, later in zip(scenario.blocks, scenario.blocks[1:])
        ),
    )
    check.agree(f"{name}.total_supply", totals["total_supply"], ledger.total_supply)
    check.agree(f"{name}.fee_pool", totals["fee_pool"], ledger.fee_pool)
    check.agree(f"{name}.economy_entry_count", shape, len(ledger.economy_entries()))
    check.equal(f"{name}.state_is_conserved", not ledger.conservation_failures())
    check.equal(
        f"{name}.every_account_is_an_escrow",
        set(ledger.registry.accounts) == set(ledger.registry.escrows),
    )
    failures = sum(block.atomic_failures for block in scenario.blocks)
    check.equal(f"{name}.refusals_checked_for_atomicity", failures)
    check.equal(f"{name}.every_refusal_left_the_state_root_unchanged", failures >= 1)
    check.agree(
        f"{name}.final_state_root",
        e.state_root_hex(
            e.STATE_ROOT_LABEL,
            e.STATE_ROOT_SCHEMA_VERSION,
            ledger.chain_id,
            ledger.height,
            ledger.supply_limit,
            ledger.total_supply,
            ledger.fee_pool,
            ledger.accounts(),
            ledger.economy_entries(),
            e.ECONOMY_TREE_PREFIX,
        ),
        ledger.state_root(),
    )


def check_balances(check: Checker, name: str, ledger, balances: dict[str, tuple]) -> None:
    for label, (escrow, amount) in balances.items():
        check.agree(f"{name}.{label}", amount, ledger.balance(escrow))


def _expected_fee(kind: int, result: str) -> int:
    """A successful registration is the one success in any version with no fee."""
    if result != "SUCCESS":
        return 0
    return 0 if kind == 10 else e.FIXED_FEE


def _issued_by_label(name: str, totals: dict[str, int]) -> dict[str, int]:
    """What each successful step issues, taken from the closed forms alone."""
    airdrop = e.entry_airdrop()
    tables = {
        "registration": {
            "alice_registers": airdrop,
            "bob_registers": airdrop,
            "alice_collects_thirty_windows": totals.get("collection_atomic", 0),
        },
        "millionth": {
            "alice_registers_inside_the_population": airdrop,
            "dave_registers_past_the_population": 0,
        },
        "recovery": {"maria_registers": airdrop, "bob_registers": airdrop},
        "compatibility": {"the_sender_registers": airdrop, "bob_registers": airdrop},
        "posture": {"alice_registers": airdrop, "bob_registers": airdrop},
        "block": {
            "alice_registers": airdrop,
            "bob_registers": airdrop,
            "carol_registers": airdrop,
            "alice_mints_confirmed": totals.get("node_mint_atomic", 0),
            "bob_mints_his_referral": totals.get("referral_mint_atomic", 0),
        },
    }
    return tables[name]
