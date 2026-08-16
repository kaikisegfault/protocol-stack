"""The compatibility boundary, the ordering derivation, determinism, and the
three execution rules this slice had to derive.

The ordering section is the load-bearing one. `ledger-transition-v1` does not
say whether the cycle assignment a window boundary is due is written before or
after that block's transactions, and version six inherits the silence. The two
readings are run against identical inputs, and the difference is not cosmetic: a
mint in the boundary block collects a whole cycle under one and forfeits it
permanently under the other, because the mark advances to the last assigned
window whatever the walk found. The specification's own sentence — "the last
assigned window at any height `h` is `window_of_height(h) - 2`" — is a statement
about every transaction executing at `h`, and only the prologue reading makes it
true.
"""

from __future__ import annotations

from pathlib import Path

import expected as e
from checker import Checker, read_vectors

from simulation.economy_transition_v6 import contract as c
from simulation.economy_transition_v6 import trace
from simulation.economy_transition_v6.envelope import (
    Transaction,
    signed_bytes,
    unsigned_bytes,
)
from simulation.economy_transition_v6.identity import escrow_id


def check_compatibility(check: Checker, accepted: Path, scenario) -> None:
    """The accepted 200 octets, admitted and refused, and the one field that moved."""
    check.section("The accepted version-one transfer, executed under version six.")
    primitives = read_vectors(accepted / "protocol-primitives-v1.txt")
    signatures = trace.Signatures()
    raw = trace.accepted_transfer_bytes(signatures)

    derived_unsigned = e.flat_unsigned_transfer(
        trace.ACCEPTED_CHAIN_ID,
        trace.ACCEPTED_SENDER_KEY,
        trace.ACCEPTED_NONCE,
        trace.ACCEPTED_RECIPIENT,
        trace.ACCEPTED_AMOUNT,
        trace.ACCEPTED_FEE_LIMIT,
        trace.ACCEPTED_VALID_UNTIL,
    )
    check.agree(
        "compatibility.unsigned_transaction",
        derived_unsigned.hex(),
        raw[: len(derived_unsigned)].hex(),
    )
    check.equal(
        "compatibility.unsigned_transaction_is_the_accepted_one",
        derived_unsigned.hex() == primitives["unsigned_tx"],
    )
    check.agree(
        "compatibility.signed_transaction",
        (derived_unsigned + trace.ACCEPTED_SIGNATURE).hex(),
        raw.hex(),
    )
    check.equal(
        "compatibility.signed_transaction_is_the_accepted_one",
        raw.hex() == primitives["signed_tx"],
    )
    check.agree(
        "compatibility.transaction_id",
        e.transaction_id_hex(raw),
        _model_transaction_id(raw),
    )
    check.equal(
        "compatibility.transaction_id_is_the_accepted_one",
        e.transaction_id_hex(raw) == primitives["tx_id"],
    )

    # The comparison the founder answer produced. Renumbering the nonce and
    # replacing the recipient are the only two edits, and they are separable.
    renonced = _transfer_bytes(
        signatures, trace.ACCEPTED_RECIPIENT, nonce=2, amount=trace.ACCEPTED_AMOUNT
    )
    rerouted = _transfer_bytes(
        signatures, trace.BOB_ESCROW, nonce=2, amount=trace.ACCEPTED_AMOUNT
    )
    check.equal(
        "compatibility.renonced_differs_from_the_accepted_bytes_in_octets",
        _differing_octets(raw[:136], renonced[:136]),
    )
    check.equal(
        "compatibility.rerouted_differs_from_the_renonced_bytes_in_octets",
        _differing_octets(renonced[:136], rerouted[:136]),
    )
    check.equal(
        "compatibility.the_only_field_that_moved_is_the_recipient",
        _differing_span(renonced[:136], rerouted[:136]) == (80, 112),
    )
    # The accepted recipient is an arbitrary 32-byte value, and a version-six
    # escrow identifier is a digest of an identity and an index. Reaching it
    # would be a SHA-256 preimage, so the accepted transfer is refused on every
    # conforming version-six chain rather than only on this fixture's.
    check.equal(
        "compatibility.the_accepted_recipient_is_no_escrow_of_any_fixture_identity",
        not _reachable(trace.ACCEPTED_RECIPIENT, 1_024),
    )
    check.equal(
        "compatibility.byte_identity_is_preserved_and_execution_identity_is_not",
        raw.hex() == primitives["signed_tx"]
        and scenario.results()["the_accepted_transfer"] == "RECIPIENT_NOT_REGISTERED"
        and scenario.results()["the_same_transfer_to_a_registered_recipient"] == "SUCCESS",
    )


def _model_transaction_id(raw: bytes) -> str:
    from simulation.economy_transition_v6.envelope import transaction_id

    return transaction_id(raw)


def _transfer_bytes(
    signatures: trace.Signatures, recipient: bytes, nonce: int, amount: int
) -> bytes:
    transaction = Transaction(
        kind=c.TRANSFER,
        scheme=c.SCHEME_SIGNER,
        chain_id=trace.ACCEPTED_CHAIN_ID,
        authority_public_key=trace.ACCEPTED_SENDER_KEY,
        nonce=nonce,
        body={"recipient_escrow_id": recipient, "amount_atomic": amount},
        fee_limit=trace.ACCEPTED_FEE_LIMIT,
        valid_until_height=trace.ACCEPTED_VALID_UNTIL,
    )
    unsigned = unsigned_bytes(transaction)
    from simulation.economy_transition_v6.envelope import signing_message

    return signed_bytes(
        transaction,
        signatures.sign(trace.ACCEPTED_SENDER_KEY, signing_message(unsigned)),
    )


def _differing_octets(left: bytes, right: bytes) -> int:
    return sum(1 for a, b in zip(left, right) if a != b)


def _differing_span(left: bytes, right: bytes) -> tuple[int, int]:
    positions = [index for index, (a, b) in enumerate(zip(left, right)) if a != b]
    return (positions[0], positions[-1] + 1) if positions else (0, 0)


def _reachable(candidate: bytes, indexes: int) -> bool:
    identities = (
        trace.ALICE_IDENTITY,
        trace.BOB_IDENTITY,
        trace.CAROL_IDENTITY,
        trace.MARIA_IDENTITY,
        trace.DAVE_IDENTITY,
        trace.ACCEPTED_IDENTITY,
    )
    return any(
        escrow_id(identity, index) == candidate
        for identity in identities
        for index in range(indexes)
    )


def check_ordering(check: Checker, scenario) -> None:
    """Both readings of the boundary block, run against identical inputs."""
    check.section("Where the cycle assignment lands inside a block, and what it costs.")
    accepted_block = scenario.blocks[-1]
    rejected_block = scenario.notes["rejected_ordering"]
    accepted_ledger = scenario.ledger
    rejected_ledger = scenario.notes["rejected_ledger"]
    window = scenario.notes["assigned_window"]
    height = scenario.notes["boundary_height"]

    check.agree("ordering.boundary_height", (window + 2) * e.CYCLE_BLOCKS, height)
    check.agree(
        "ordering.last_assigned_window", e.last_assigned_window(height), window
    )
    check.equal(
        "ordering.last_assigned_window_is_arithmetic_on_height_alone",
        e.last_assigned_window(height) == window,
    )
    check.equal("ordering.prologue.assigned_window", accepted_block.assigned_window)
    check.equal("ordering.epilogue.assigned_window", rejected_block.assigned_window)
    check.equal(
        "ordering.prologue.node_mint_result", accepted_block.results[1]
    )
    check.equal("ordering.epilogue.node_mint_result", rejected_block.results[1])
    check.agree(
        "ordering.prologue.node_mint_issued",
        e.block_totals(in_span=2, referred=1)["node_mint_atomic"],
        accepted_block.executed[1].receipt.issued_atomic,
    )
    check.equal(
        "ordering.epilogue.node_mint_issued",
        rejected_block.executed[1].receipt.issued_atomic,
    )
    check.equal(
        "ordering.the_epilogue_mint_succeeds_and_collects_nothing",
        rejected_block.results[1] == "SUCCESS"
        and rejected_block.executed[1].receipt.issued_atomic == 0,
    )
    check.equal(
        "ordering.prologue.referral_mint_result", accepted_block.results[2]
    )
    check.equal("ordering.epilogue.referral_mint_result", rejected_block.results[2])
    check.equal(
        "ordering.prologue.seat_zero_mark", accepted_ledger.seats[0].minted_through_window
    )
    check.equal(
        "ordering.epilogue.seat_zero_mark", rejected_ledger.seats[0].minted_through_window
    )
    check.equal("ordering.prologue.total_supply", accepted_ledger.total_supply)
    check.equal("ordering.epilogue.total_supply", rejected_ledger.total_supply)
    # The mark advances to the last assigned window whatever the walk found, so
    # a walk over records that are not yet written forfeits the cycle for good.
    check.equal(
        "ordering.the_epilogue_reading_forfeits_the_assigned_cycle_permanently",
        rejected_ledger.seats[0].minted_through_window == window
        and rejected_ledger.total_supply < accepted_ledger.total_supply,
    )
    # A referral is deferred rather than forfeited, because kind 5 advances its
    # own mark only on success and the accrual survives in the balance entry.
    check.equal(
        "ordering.the_epilogue_reading_only_defers_the_referral",
        rejected_block.results[2] == "NOTHING_TO_MINT"
        and rejected_ledger.channel_outstanding[e.REFERRAL_CHANNEL] > 0,
    )
    check.equal(
        "ordering.the_prologue_reading_makes_the_specification_sentence_true",
        accepted_block.assigned_window == e.last_assigned_window(height)
        and accepted_block.results[1] == "SUCCESS",
    )


def check_determinism(check: Checker, scenarios) -> None:
    """Replaying every scenario reproduces every commitment it recorded."""
    check.section("Determinism: the same inputs reproduce the same commitments.")
    replayed = [maker() for maker in trace.SCENARIOS]
    roots_match = True
    receipts_match = True
    for first, (second, _signatures) in zip(scenarios, replayed):
        for left, right in zip(first.blocks, second.blocks):
            roots_match &= left.resulting_state_root == right.resulting_state_root
            roots_match &= left.block_id == right.block_id
            receipts_match &= left.receipts == right.receipts
    check.equal("determinism.every_replayed_block_commits_the_same_root", roots_match)
    check.equal("determinism.every_replayed_block_emits_the_same_receipts", receipts_match)
    check.equal("determinism.scenarios_replayed", len(replayed))


def check_derived_rules(check: Checker) -> None:
    """The three execution rules the accepted contract left to be derived."""
    check.section("Three execution rules derived from the accepted contract.")

    # 1. `DEBIT_OVERFLOW` is returned at envelope check 8. Under the literal
    #    "envelope checks, then the kind's own conditions" order it would be
    #    unreachable, because no balance can reach the amount an overflowing
    #    debit needs — and the specification lists exactly three unreachable
    #    frozen codes and does not list this one.
    overflow_amount = (1 << 64) - e.FIXED_FEE
    check.equal("derived.overflow_amount_atomic", overflow_amount)
    check.equal(
        "derived.an_overflowing_debit_exceeds_any_reachable_balance",
        overflow_amount > trace.SUPPLY_LIMIT,
    )
    check.equal("derived.overflowing_debit_result", _debit_overflow_result())
    check.equal(
        "derived.debit_overflow_is_returned_at_envelope_check_eight",
        _debit_overflow_result() == "DEBIT_OVERFLOW",
    )

    # 2. The zero-confirmation-field rule cannot be an admission rule and cannot
    #    return the code the specification names.
    check.equal(
        "derived.the_result_code_space_has_no_malformed_transaction",
        "MALFORMED_TRANSACTION" not in e.CODE_NUMBER,
    )
    check.equal(
        "derived.admission_code_one_and_result_code_one_are_different_names",
        e.ADMISSION_CODES[1] != e.RESULT_CODES[1],
    )
    check.equal(
        "derived.an_unrequested_confirmation_is_refused_with_unauthorized",
        _unrequested_confirmation_result() == "UNAUTHORIZED",
    )

    # 3. `NOTHING_TO_MINT` is the empty walk range. A seat activated in window
    #    `w` holds mark `w` while the last assigned window is `w - 2`, so the
    #    literal "already equal" reading would let the mint lower the mark.
    activation = trace.ACTIVATION_HEIGHT
    mark = activation // e.CYCLE_BLOCKS
    last = e.last_assigned_window(activation)
    check.equal("derived.mark_at_activation", mark)
    check.equal("derived.last_assigned_window_at_activation", last)
    check.equal("derived.a_fresh_mark_exceeds_the_last_assigned_window", mark > last)
    check.equal(
        "derived.nothing_to_mint_is_the_empty_walk_range",
        e.walk_range(mark, last) is None and e.walk_range(last - 1, last) is not None,
    )


def _debit_overflow_result() -> str:
    """Offer an overflowing transfer from an escrow that could otherwise pay.

    The escrow's balance is stamped to the `u64` maximum, which no conserved
    chain reaches; that is the point. Even given a balance nothing can exceed,
    the sum `amount + fee` still does not fit, so the code that reports it must
    be returned before the balance comparison or it is returned never.
    """
    from simulation.economy_transition_v6.execution import SignatureOracle, execute
    from simulation.economy_transition_v6.ledger import Ledger

    ledger = Ledger(
        chain_id=bytes(32),
        supply_limit=trace.SUPPLY_LIMIT,
        fixed_fee=e.FIXED_FEE,
        verifier_key=bytes(32),
    )
    escrow = ledger.registry.register(
        trace.ALICE_IDENTITY, trace.ALICE_KEY, trace.ALICE_SIGNER_KEY, 0
    )
    ledger.registry.accounts[escrow] = ((1 << 64) - 1, 0)
    transaction = Transaction(
        kind=c.TRANSFER,
        scheme=c.SCHEME_SIGNER,
        chain_id=bytes(32),
        authority_public_key=trace.ALICE_SIGNER_KEY,
        nonce=1,
        body={"recipient_escrow_id": escrow, "amount_atomic": (1 << 64) - 1},
        fee_limit=e.FIXED_FEE,
        valid_until_height=1,
    )
    return execute(ledger, transaction, SignatureOracle()).result


def _unrequested_confirmation_result() -> str:
    from simulation.economy_transition_v6.execution import Refused, require_zero_confirmation

    try:
        require_zero_confirmation(bytes([1]) + bytes(63))
    except Refused as refusal:
        return refusal.result
    return "SUCCESS"
