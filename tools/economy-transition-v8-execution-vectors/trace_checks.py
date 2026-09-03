"""Derive every recorded block-level vector and record only what agrees.

The independent side is `expected.py`, which imports nothing from `simulation/`.
The live side is a real run of the version-eight execution model. Every value two
sources can reach is recorded only when both produce it; a value only one source
can reach — a property of a state, a count of blocks in a fixture — is recorded
from the one source and is a claim the file pins rather than one it proves twice.

Three constructions are checked against a third source before anything rests on
them: the ordered transaction tree against `protocol-primitives-v1.txt`'s
recorded `tx.root`, and the application block header and block ID against
`ledger-transition-v1.txt`'s recorded pair. Each is inherited from version one,
so a restatement that had drifted would otherwise agree only with itself.
"""

from __future__ import annotations

from pathlib import Path

import expected as e
from checker import Checker, read_vectors

from simulation.economy_transition_v7.receipt import encode as encode_v7_receipt
from simulation.economy_transition_v6.receipt import Receipt
from simulation.economy_transition_v8 import trace
from simulation.economy_transition_v8.block import block_header, transaction_root
from simulation.economy_transition_v8.genesis import chain_id as derive_chain_id
from simulation.economy_transition_v8.genesis import encode as encode_genesis
from simulation.economy_transition_v8.genesis import predecessor_chain_id
from simulation.economy_transition_v8.receipt import decode as decode_receipt


def check_constructions(check: Checker, accepted: Path) -> None:
    """The version-one constructions version eight inherits, each against the
    accepted file that fixes it."""
    check.section(
        "The version-one constructions version eight inherits, checked against "
        "the accepted vectors that fix them."
    )
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
    derived = e.block_header_bytes(
        recorded[6:38],
        int.from_bytes(recorded[38:46], "big"),
        bytes.fromhex(ledger_vectors["previous_state_root"]),
        bytes.fromhex(ledger_vectors["transaction_root"]),
        bytes.fromhex(ledger_vectors["resulting_state_root"]),
        int.from_bytes(recorded[142:146], "big"),
    )
    live = block_header(
        recorded[6:38],
        int.from_bytes(recorded[38:46], "big"),
        ledger_vectors["previous_state_root"],
        ledger_vectors["transaction_root"],
        ledger_vectors["resulting_state_root"],
        int.from_bytes(recorded[142:146], "big"),
    )
    check.agree("construction.block_header", derived.hex(), live.hex())
    check.equal(
        "construction.block_header_reproduces_the_accepted_vector",
        derived.hex() == ledger_vectors["block_header"],
    )
    check.agree("construction.block_id", e.block_id_hex(derived), e.block_id_hex(live))
    check.equal(
        "construction.block_id_reproduces_the_accepted_vector",
        e.block_id_hex(derived) == ledger_vectors["block_id"],
    )
    check.equal("construction.block_header_schema_version", e.BLOCK_HEADER_SCHEMA_VERSION)
    check.equal("construction.block_header_bytes", e.BLOCK_HEADER_BYTES)


def check_genesis(check: Checker) -> None:
    """Fourteen entries, a 142-octet prefix, and no collision with any predecessor."""
    check.section(
        "The genesis every scenario runs on: version seven's fourteen economy "
        "entries under a nine-field genesis."
    )
    genesis = trace.genesis()
    derived = e.genesis_bytes(
        trace.NETWORK_ID,
        trace.SUPPLY_LIMIT,
        trace.FIXED_FEE,
        genesis.manifest_digest,
        genesis.verifier_key,
        genesis.dispute_authority_key,
    )
    check.agree("genesis.bytes", derived.hex(), encode_genesis(genesis).hex())
    check.equal("genesis.prefix_bytes", e.GENESIS_PREFIX_BYTES)
    check.equal("genesis.schema_version", e.GENESIS_SCHEMA_VERSION)
    check.agree(
        "genesis.manifest_digest", e.MANIFEST_DIGEST, genesis.manifest_digest.hex()
    )
    check.agree(
        "genesis.chain_id", e.chain_id(derived).hex(), derive_chain_id(genesis).hex()
    )
    check.equal("genesis.economy_entries", e.GENESIS_ECONOMY_ENTRIES)
    check.agree("genesis.fixed_fee", e.FIXED_FEE, trace.FIXED_FEE)
    check.equal(
        "genesis.the_dispute_authority_key_is_not_the_verifier_key",
        genesis.dispute_authority_key != genesis.verifier_key,
    )
    check.equal(
        "genesis.writes_no_open_challenge_and_no_window_record",
        not trace.Ledger.from_genesis(genesis).uptime,
    )

    for version in (2, 3, 4, 5, 6, 7):
        earlier = predecessor_chain_id(genesis, version)
        check.equal(
            f"genesis.chain_id_differs_from_v{version}",
            earlier.hex() != derive_chain_id(genesis).hex(),
        )


def check_receipt(check: Checker) -> None:
    """Two octets separate a version-eight receipt from a version-seven one."""
    check.section(
        "The receipt: version eight's version field, and the one consistency "
        "rule the founder answer moves."
    )
    receipt = Receipt(
        transaction_id=bytes(range(32)),
        kind=4,
        result_code=e.CODE_NUMBER["SUCCESS"],
        fee_charged=e.FIXED_FEE,
        issued_atomic=e.base_permission_total(),
    )
    mine = e.receipt_hex(
        receipt.transaction_id,
        receipt.kind,
        receipt.result_code,
        receipt.fee_charged,
        receipt.issued_atomic,
    )
    theirs = encode_v7_receipt(receipt).hex()
    check.equal("receipt.version", e.RECEIPT_VERSION)
    check.equal("receipt.bytes", e.RECEIPT_BYTES)
    check.equal("receipt.mint_receipt", mine)
    check.equal(
        "receipt.differs_from_the_version_seven_receipt_in_one_octet",
        sum(1 for left, right in zip(mine, theirs) if left != right) == 1,
    )
    check.equal(
        "receipt.a_version_seven_receipt_is_refused", _refuses(bytes.fromhex(theirs))
    )
    check.equal(
        "receipt.a_version_eight_receipt_round_trips",
        decode_receipt(bytes.fromhex(mine)) == receipt,
    )

    # The two kinds version eight adds issue nothing, and one of them charges
    # nothing. Each is required by refusing the receipt that would deny it.
    for kind in (e.CHALLENGE_RESPONSE, e.FILE_DISPUTE):
        check.equal(
            f"receipt.kind{kind}_issuing_a_nonzero_amount_is_refused",
            _refuses_receipt(kind, e.CODE_NUMBER["SUCCESS"], 0, 1),
        )
    check.equal(
        "receipt.a_challenge_response_charging_a_fee_is_refused",
        _refuses_receipt(e.CHALLENGE_RESPONSE, e.CODE_NUMBER["SUCCESS"], e.FIXED_FEE, 0),
    )
    check.equal(
        "receipt.a_successful_response_charging_nothing_is_accepted",
        not _refuses_receipt(e.CHALLENGE_RESPONSE, e.CODE_NUMBER["SUCCESS"], 0, 0),
    )
    check.equal(
        "receipt.a_successful_dispute_charging_the_fixed_fee_is_accepted",
        not _refuses_receipt(e.FILE_DISPUTE, e.CODE_NUMBER["SUCCESS"], e.FIXED_FEE, 0),
    )


def _refuses(raw: bytes) -> bool:
    try:
        decode_receipt(raw)
    except Exception:
        return True
    return False


def _refuses_receipt(kind: int, code: int, fee: int, issued: int) -> bool:
    from simulation.economy_transition_v8.receipt import encode as encode_v8

    try:
        encode_v8(
            Receipt(
                transaction_id=bytes(range(32)),
                kind=kind,
                result_code=code,
                fee_charged=fee,
                issued_atomic=issued,
            )
        )
    except Exception:
        return True
    return False


def check_scenario(
    check: Checker, scenario, totals: dict[str, object], shape: int, issued: dict
) -> None:
    """Every recorded block's commitments, and every step's result and receipt."""
    name = scenario.name
    ledger = scenario.ledger

    check.equal(f"{name}.block_count", len(scenario.blocks))
    check.equal(f"{name}.heights_run_between_recorded_blocks", scenario.skipped_blocks)
    for label, code in scenario.rejected.items():
        expected_code, _reason = e.EXPECTED_ADMISSIONS[label]
        check.agree(f"{name}.{label}.admission_code", expected_code, code)
    check.equal(
        f"{name}.admission_failures_produce_no_receipt",
        sum(scenario.raw_inputs)
        - sum(len(block.executed) for block in scenario.blocks)
        == len(scenario.rejected),
    )

    for index, (block, labels) in enumerate(zip(scenario.blocks, scenario.labels)):
        prefix = f"{name}.block{index}"
        check.equal(f"{prefix}.height", block.height)
        check.equal(f"{prefix}.raw_input_count", scenario.raw_inputs[index])
        check.equal(f"{prefix}.admitted_count", len(block.executed))
        if block.assigned_window is not None:
            check.equal(f"{prefix}.assigned_window", block.assigned_window)
            check.equal(
                f"{prefix}.the_record_is_written_at_the_first_height_of_w_plus_two",
                block.height
                == (block.assigned_window + e.ASSIGNMENT_LAG_WINDOWS) * e.CYCLE_BLOCKS,
            )
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
                    _expected_fee(label, entry.kind, result),
                    issued.get(label, 0) if result == "SUCCESS" else 0,
                ),
                block.receipts[position].hex(),
            )

    check.agree(f"{name}.total_supply", totals["total_supply"], ledger.total_supply)
    check.agree(f"{name}.fee_pool", totals["fee_pool"], ledger.fee_pool)
    check.agree(f"{name}.economy_entry_count", shape, len(ledger.economy_entries()))
    check.equal(f"{name}.state_is_conserved", not ledger.conservation_failures())
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


def _expected_fee(label: str, kind: int, result: str) -> int:
    if result != "SUCCESS":
        return 0
    if label in e.FEE_EXEMPT_LABELS or kind in e.FEE_EXEMPT_KINDS:
        return 0
    return e.FIXED_FEE
