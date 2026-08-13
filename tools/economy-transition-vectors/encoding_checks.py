"""Envelope, compatibility, admission, code-space, and receipt derivations."""

from __future__ import annotations

from pathlib import Path

import expected as e
from checker import Checker, read_vectors

from simulation.economy_transition import contract as c
from simulation.economy_transition import envelope, receipt, scenario

KIND_NAMES = {kind: name for kind, name in c.TRANSACTION_KINDS.items()}


def check_envelope(check: Checker) -> None:
    check.agree("envelope.header_bytes", e.HEADER_BYTES, c.HEADER_BYTES)
    check.agree("envelope.trailer_bytes", e.TRAILER_BYTES, c.TRAILER_BYTES)
    check.agree("envelope.signature_bytes", e.SIGNATURE_BYTES, c.SIGNATURE_BYTES)
    check.agree(
        "envelope.schema_version", 1, c.ENVELOPE_SCHEMA_VERSION
    )
    check.agree("envelope.kind_count", len(e.BODY_FIELD_WIDTHS), len(c.TRANSACTION_KINDS))

    for kind, name in sorted(KIND_NAMES.items()):
        check.agree(
            f"envelope.body_bytes.{name}", e.fixed_body_bytes(kind), c.FIXED_BODY_BYTES[kind]
        )
        check.agree(
            f"envelope.signed_bytes.{name}",
            e.signed_length(kind),
            envelope.expected_signed_length(kind),
        )

    for name, transaction in sorted(scenario.transactions().items()):
        winners = len(transaction.body.get("winners", ()))
        raw = envelope.signed_bytes(transaction, scenario.TRANSFER_SIGNATURE)
        check.agree(
            f"envelope.encoded_signed_bytes.{name}",
            e.signed_length(transaction.kind, winners),
            len(raw),
        )
        decoded, signature = envelope.decode_signed(raw)
        check.equal(f"envelope.roundtrip.{name}", decoded == transaction)
        check.equal(
            f"envelope.roundtrip_signature.{name}",
            signature == scenario.TRANSFER_SIGNATURE,
        )

    capacity = c.FOUNDER_SEAT_CAPACITY
    at_capacity = e.signed_length(c.EXERCISE_PERMISSION, capacity)
    check.agree(
        "envelope.exercise_signed_bytes_at_capacity",
        at_capacity,
        envelope.expected_signed_length(c.EXERCISE_PERMISSION, capacity),
    )
    check.equal("envelope.exercise_fits_object_bound", at_capacity <= e.MAX_OBJECT_BYTES)


def check_compatibility(check: Checker, vector_root: Path) -> None:
    """The kind-1 identity, derived twice and checked against the accepted file.

    `expected.py` builds the transfer from the flat version-one field table and
    the model builds it from a header, a body, and a trailer. Both are then
    required to equal the bytes `protocol-primitives-v1` recorded, so the
    factoring is evidence rather than a restatement of itself.
    """
    accepted = read_vectors(vector_root / "protocol-primitives-v1.txt")
    transfer = scenario.accepted_transfer()

    flat = e.flat_unsigned_transfer(
        scenario.CHAIN_ID,
        scenario.SENDER_PUBLIC_KEY,
        transfer.nonce,
        scenario.RECIPIENT_ACCOUNT_ID,
        transfer.body["amount_atomic"],
        transfer.fee_limit,
        transfer.valid_until_height,
    )
    factored = envelope.unsigned_bytes(transfer)
    check.agree("compatibility.kind_one_unsigned_hex", flat.hex(), factored.hex())
    check.equal(
        "compatibility.kind_one_matches_accepted_unsigned",
        flat.hex() == accepted["unsigned_tx"],
    )

    signed = envelope.signed_bytes(transfer, scenario.TRANSFER_SIGNATURE)
    check.agree(
        "compatibility.kind_one_signed_hex",
        (flat + scenario.TRANSFER_SIGNATURE).hex(),
        signed.hex(),
    )
    check.equal(
        "compatibility.kind_one_matches_accepted_signed",
        signed.hex() == accepted["signed_tx"],
    )

    derived_id = envelope.transaction_id(signed)
    check.agree(
        "compatibility.kind_one_transaction_id",
        e.digest("protocol-stack:v1:tx-id", flat + scenario.TRANSFER_SIGNATURE).hex(),
        derived_id,
    )
    check.equal(
        "compatibility.kind_one_matches_accepted_transaction_id",
        derived_id == accepted["tx_id"],
    )
    check.equal("compatibility.sign_label", c.SIGN_LABEL)
    check.equal("compatibility.tx_id_label", c.TX_ID_LABEL)
    check.equal(
        "compatibility.signing_message_prefix",
        envelope.signing_message(b"")[: len(c.SIGN_LABEL) + 1].hex(),
    )


def check_admission(check: Checker) -> None:
    """Every admission rejection is produced by mutating an accepted encoding."""
    transfer = scenario.accepted_transfer()
    accepted = bytearray(envelope.signed_bytes(transfer, scenario.TRANSFER_SIGNATURE))

    for number, name in sorted(e_admission().items()):
        check.agree(f"admission.code.{number}", name, c.ADMISSION_CODES[number])

    envelope.decode_signed(bytes(accepted))
    check.equal("admission.positive_control_accepts", True)

    for name, mutated in _admission_mutations(accepted).items():
        check.equal(f"admission.reject.{name}", _refusal(mutated))

    check.equal("admission.reject.unknown_kind", _refusal(_with_kind(accepted, 7)))
    check.equal("admission.reject.kind_zero", _refusal(_with_kind(accepted, 0)))

    # Two kinds share a body width, so the kind byte alone separates them. The
    # bytes still decode; what fails is the signature, which is checked at
    # admission step 4 over a preimage that includes the kind.
    evaluation = scenario.transactions()["evaluate_first_cycle"]
    raw = bytearray(envelope.signed_bytes(evaluation, scenario.TRANSFER_SIGNATURE))
    raw[6] = c.ACCRUE_REFERRAL
    reinterpreted, _ = envelope.decode_signed(bytes(raw))
    check.equal("admission.cross_kind_body_decodes", reinterpreted.kind == c.ACCRUE_REFERRAL)
    check.equal(
        "admission.cross_kind_changes_signing_message",
        envelope.signing_message(bytes(raw[:-64]))
        != envelope.signing_message(envelope.unsigned_bytes(evaluation)),
    )


def e_admission() -> dict[int, str]:
    return {1: "MALFORMED_TRANSACTION", 2: "WRONG_CHAIN", 3: "INVALID_SIGNATURE"}


def _admission_mutations(accepted: bytearray) -> dict[str, bytes]:
    activation = scenario.transactions()["activate_first_seat"]
    activation_raw = bytearray(
        envelope.signed_bytes(activation, scenario.TRANSFER_SIGNATURE)
    )
    non_minimal = bytearray(activation_raw)
    non_minimal[85:89] = (1).to_bytes(4, "big")

    exercise = scenario.transactions()["exercise_failed_cycle"]
    exercise_raw = bytearray(envelope.signed_bytes(exercise, scenario.TRANSFER_SIGNATURE))
    unordered = bytearray(exercise_raw)
    unordered[90:94], unordered[94:98] = unordered[94:98], unordered[90:94]

    over_capacity = bytearray(exercise_raw)
    over_capacity[86:90] = (c.FOUNDER_SEAT_CAPACITY + 1).to_bytes(4, "big")

    bad_flag = bytearray(activation_raw)
    bad_flag[84] = 2

    return {
        "wrong_magic": bytes(b"XSTX" + accepted[4:]),
        "wrong_schema_version": bytes(accepted[:4] + b"\x00\x02" + accepted[6:]),
        "unknown_signature_scheme": bytes(accepted[:39] + b"\x02" + accepted[40:]),
        "trailing_byte": bytes(accepted) + b"\x00",
        "truncated": bytes(accepted[:-1]),
        "non_minimal_absent_referrer": bytes(non_minimal),
        "non_canonical_bool": bytes(bad_flag),
        "winner_list_not_increasing": bytes(unordered),
        "winner_count_above_capacity": bytes(over_capacity),
    }


def _with_kind(accepted: bytearray, kind: int) -> bytes:
    mutated = bytearray(accepted)
    mutated[6] = kind
    return bytes(mutated)


def _refusal(raw: bytes) -> str:
    try:
        envelope.decode_signed(raw)
    except envelope.MalformedTransaction:
        return "MALFORMED_TRANSACTION"
    return "accepted"


def check_result_codes(check: Checker) -> None:
    check.agree("codes.count", len(e.RESULT_CODES), len(c.RESULT_CODES))
    for number, name in sorted(e.RESULT_CODES.items()):
        check.agree(f"codes.{number}", name, c.RESULT_CODES[number])

    check.agree(
        "codes.inherited_count", len(e.VERSION_ONE_TRANSFER_RESULTS), len(c.INHERITED_RESULT_CODES)
    )
    check.agree(
        "codes.added_count",
        len(e.RESULT_CODES) - len(e.VERSION_ONE_TRANSFER_RESULTS),
        len(c.ADDED_RESULT_CODES),
    )
    # The frozen half, checked against `ledger-transition-v1`'s own table rather
    # than against the model's copy of it.
    check.equal(
        "codes.version_one_meanings_preserved",
        all(c.RESULT_CODES[number] == name for number, name in e.VERSION_ONE_TRANSFER_RESULTS.items()),
    )
    check.equal("codes.numbering_is_contiguous", sorted(c.RESULT_CODES) == list(range(len(c.RESULT_CODES))))


def check_model_mapping(check: Checker) -> None:
    """The mapping from the economy model's codes onto this surface is total."""
    declared = set(e.MODEL_RESULT_CODES)
    carried = set(c.CARRIED_MODEL_CODES)
    guards = set(c.GUARD_MODEL_CODES)
    unrepresentable = set(c.UNREPRESENTABLE_MODEL_CODES)

    check.agree("codes.model.declared", len(e.MODEL_RESULT_CODES), len(declared))
    check.equal("codes.model.carried", len(carried))
    check.equal("codes.model.guard", len(guards))
    check.equal("codes.model.unrepresentable", len(unrepresentable))
    check.equal(
        "codes.model.partition_is_total",
        carried | guards | unrepresentable == declared
        and not (carried & guards)
        and not (carried & unrepresentable)
        and not (guards & unrepresentable),
    )
    check.equal(
        "codes.model.carried_targets_exist",
        all(target in c.CODE_NUMBER for target in c.CARRIED_MODEL_CODES.values()),
    )
    # A guard must not acquire a receipt code: `ledger-transition-v1` already
    # decides that a checked-arithmetic violation invalidates the block.
    check.equal(
        "codes.model.guards_have_no_receipt_code",
        not (guards & set(c.CODE_NUMBER)),
    )
    for name in sorted(unrepresentable):
        check.equal(f"codes.model.unrepresentable.{name}", c.UNREPRESENTABLE_MODEL_CODES[name])


def check_receipt(check: Checker) -> None:
    check.agree("receipt.bytes", e.receipt_bytes(), receipt.RECEIPT_BYTES)
    check.equal("receipt.version", c.RECEIPT_VERSION)

    accepted = receipt.Receipt(
        transaction_id=bytes.fromhex("ab" * 32),
        kind=c.EXERCISE_PERMISSION,
        result_code=c.CODE_NUMBER["SUCCESS"],
        fee_charged=1_000,
        issued_atomic=57_430_000_000,
    )
    encoded = receipt.encode(accepted)
    check.equal("receipt.encoded_bytes", len(encoded))
    check.equal("receipt.roundtrip", receipt.decode(encoded) == accepted)
    check.equal("receipt.encoded_hex", encoded.hex())

    for name, candidate in _invalid_receipts(accepted).items():
        check.equal(f"receipt.reject.{name}", _receipt_refusal(candidate))


def _invalid_receipts(accepted: receipt.Receipt) -> dict[str, receipt.Receipt]:
    replace = accepted.__class__
    failed = c.CODE_NUMBER["CHANNEL_CAP"]
    return {
        "unknown_kind": replace(accepted.transaction_id, 7, 0, 1_000, 0),
        "unknown_result_code": replace(accepted.transaction_id, 1, 200, 0, 0),
        "failed_with_fee": replace(accepted.transaction_id, 1, failed, 1_000, 0),
        "failed_with_issuance": replace(accepted.transaction_id, 4, failed, 0, 1),
        "non_issuing_kind_issues": replace(accepted.transaction_id, 1, 0, 1_000, 1),
    }


def _receipt_refusal(candidate: receipt.Receipt) -> str:
    try:
        receipt.encode(candidate)
    except receipt.InvalidReceipt:
        return "INVALID_RECEIPT"
    return "accepted"
