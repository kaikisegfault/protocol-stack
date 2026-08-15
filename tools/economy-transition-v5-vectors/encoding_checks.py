"""Envelope, compatibility, admission, message, code-space, and receipt checks."""

from __future__ import annotations

from pathlib import Path

import expected as e
from checker import Checker, read_vectors

from simulation.economy_transition_v5 import contract as c
from simulation.economy_transition_v5 import envelope, messages, receipt, scenario

KIND_NAMES = {kind: name for kind, name in c.TRANSACTION_KINDS.items()}


def check_envelope(check: Checker) -> None:
    check.agree("envelope.header_bytes", e.HEADER_BYTES, c.HEADER_BYTES)
    check.agree("envelope.trailer_bytes", e.TRAILER_BYTES, c.TRAILER_BYTES)
    check.agree("envelope.signature_bytes", e.SIGNATURE_BYTES, c.SIGNATURE_BYTES)
    check.agree("envelope.schema_version", 1, c.ENVELOPE_SCHEMA_VERSION)
    check.agree(
        "envelope.kind_count", len(e.BODY_FIELD_WIDTHS), len(c.TRANSACTION_KINDS)
    )

    for kind, name in sorted(KIND_NAMES.items()):
        check.agree(f"envelope.kind_name.{kind}", e.KIND_NAMES[kind], name)
        check.agree(
            f"envelope.body_bytes.{name}", e.fixed_body_bytes(kind), c.BODY_BYTES[kind]
        )
        check.agree(
            f"envelope.signed_bytes.{name}",
            e.signed_length(kind),
            envelope.expected_signed_length(kind),
        )
    check.equal(
        "envelope.every_kind_is_fixed_length",
        all(
            envelope.expected_signed_length(kind)
            == c.HEADER_BYTES + c.BODY_BYTES[kind] + c.TRAILER_BYTES + c.SIGNATURE_BYTES
            for kind in c.TRANSACTION_KINDS
        ),
    )
    colliding = sorted(
        name
        for kind, name in KIND_NAMES.items()
        if sum(1 for other in c.BODY_BYTES.values() if other == c.BODY_BYTES[kind]) > 1
    )
    check.equal("envelope.kinds_sharing_a_body_length", ",".join(colliding))
    check.agree(
        "envelope.distinct_body_lengths",
        len({e.fixed_body_bytes(kind) for kind in e.BODY_FIELD_WIDTHS}),
        len(set(c.BODY_BYTES.values())),
    )
    largest = max(envelope.expected_signed_length(kind) for kind in c.TRANSACTION_KINDS)
    check.equal("envelope.largest_signed_bytes", largest)
    check.equal("envelope.version_three_largest_signed_bytes", 325)
    check.equal("envelope.largest_is_smaller_than_version_three", largest < 325)

    for name, transaction in sorted(scenario.transactions().items()):
        raw = envelope.signed_bytes(transaction, scenario.TRANSFER_SIGNATURE)
        check.agree(
            f"envelope.encoded_signed_bytes.{name}",
            e.signed_length(transaction.kind),
            len(raw),
        )
        decoded, signature = envelope.decode_signed(raw)
        check.equal(f"envelope.roundtrip.{name}", decoded == transaction)
        check.equal(
            f"envelope.roundtrip_signature.{name}",
            signature == scenario.TRANSFER_SIGNATURE,
        )

    check.equal("envelope.largest_fits_object_bound", largest <= e.MAX_OBJECT_BYTES)
    check.equal("envelope.no_body_scales_with_the_population", True)


def check_compatibility(check: Checker, vector_root: Path) -> None:
    """The kind-1 identity, derived twice and checked against the accepted file.

    Four contract revisions have now left it untouched, which is what an
    extension is supposed to be able to do — and it is only evidence if it is
    checked against the accepted bytes each time rather than against the
    previous version's model.
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
        "compatibility.transaction_labels_are_version_one",
        c.SIGN_LABEL.startswith("protocol-stack:v1:")
        and c.TX_ID_LABEL.startswith("protocol-stack:v1:"),
    )
    check.equal(
        "compatibility.hub_labels_are_version_five",
        all(label.startswith("protocol-stack:v5:") for label in c.HUB_MESSAGE_LABELS),
    )

    # The account derivation is version one's too, and version five is the first
    # transition contract that has to perform it: its address-add message is
    # built from the sender rather than from a supplied argument.
    check.equal("compatibility.account_id_label", c.ACCOUNT_ID_LABEL)
    check.agree(
        "compatibility.account_id_of_the_accepted_sender",
        e.account_id(scenario.SENDER_PUBLIC_KEY).hex(),
        envelope.sender_account_id(transfer).hex(),
    )


def check_admission(check: Checker) -> None:
    """Every admission rejection is produced by mutating an accepted encoding."""
    transfer = scenario.accepted_transfer()
    accepted = bytearray(envelope.signed_bytes(transfer, scenario.TRANSFER_SIGNATURE))

    for number, name in sorted(
        {1: "MALFORMED_TRANSACTION", 2: "WRONG_CHAIN", 3: "INVALID_SIGNATURE"}.items()
    ):
        check.agree(f"admission.code.{number}", name, c.ADMISSION_CODES[number])

    envelope.decode_signed(bytes(accepted))
    check.equal("admission.positive_control_accepts", True)

    for name, mutated in _admission_mutations(accepted).items():
        check.equal(f"admission.reject.{name}", _refusal(mutated))

    check.equal("admission.reject.unknown_kind", _refusal(_with_kind(accepted, 13)))
    check.equal("admission.reject.kind_zero", _refusal(_with_kind(accepted, 0)))

    # The two relabellings a length check cannot catch. Both are admitted and
    # both change the signing message, which is what makes a signature unusable
    # across kinds that happen to coincide in width.
    for source, target, key in (
        ("activate_seat", c.MINT_NODE_VERIFIED, "seat"),
        ("hub_add_address", c.HUB_REMOVE_ADDRESS, "address"),
    ):
        original = scenario.transactions()[source]
        raw = bytearray(envelope.signed_bytes(original, scenario.TRANSFER_SIGNATURE))
        raw[6] = target
        check.equal(f"admission.relabelled_{key}_kind_decodes", _refusal(bytes(raw)))
        decoded, _ = envelope.decode_signed(bytes(raw))
        check.equal(f"admission.relabelled_{key}_kind_is_read_as", decoded.kind)
        check.equal(
            f"admission.relabelled_{key}_kind_changes_the_signing_message",
            envelope.signing_message(envelope.unsigned_bytes(decoded))
            != envelope.signing_message(envelope.unsigned_bytes(original)),
        )

    mint = scenario.transactions()["mint_node"]
    raw = bytearray(envelope.signed_bytes(mint, scenario.TRANSFER_SIGNATURE))
    raw[6] = c.MINT_REFERRAL
    check.equal("admission.reject.relabelled_kind", _refusal(bytes(raw)))
    check.equal(
        "admission.the_kind_byte_is_inside_the_signing_message",
        bytes([mint.kind]) in envelope.signing_message(envelope.unsigned_bytes(mint)),
    )


def _admission_mutations(accepted: bytearray) -> dict[str, bytes]:
    purchase = scenario.transactions()["purchase_unreferred_last_seat"]
    purchase_raw = bytearray(
        envelope.signed_bytes(purchase, scenario.TRANSFER_SIGNATURE)
    )

    non_minimal = bytearray(purchase_raw)
    non_minimal[80 + 37] = 1

    bad_flag = bytearray(purchase_raw)
    bad_flag[80 + 36] = 2

    enable = scenario.transactions()["enable_mint_biometric"]
    enable_raw = bytearray(envelope.signed_bytes(enable, scenario.TRANSFER_SIGNATURE))

    signed_enable = bytearray(enable_raw)
    signed_enable[80 + 5] = 1

    bad_enable = bytearray(enable_raw)
    bad_enable[80 + 4] = 2

    return {
        "wrong_magic": bytes(b"XSTX" + accepted[4:]),
        "wrong_schema_version": bytes(accepted[:4] + b"\x00\x02" + accepted[6:]),
        "unknown_signature_scheme": bytes(accepted[:39] + b"\x02" + accepted[40:]),
        "trailing_byte": bytes(accepted) + b"\x00",
        "truncated": bytes(accepted[:-1]),
        "non_minimal_absent_referrer": bytes(non_minimal),
        "non_canonical_bool": bytes(bad_flag),
        "non_minimal_enabling_signature": bytes(signed_enable),
        "non_canonical_enable_bool": bytes(bad_enable),
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


def check_hub_messages(check: Checker) -> None:
    """Eight messages, and the separation their labels and identity field give."""
    chain = scenario.CHAIN_ID
    expiry = scenario.VALID_UNTIL_HEIGHT
    who = scenario.ALICE_IDENTITY
    built = {
        "registration": messages.registration_message(
            chain, who, scenario.ALICE_KEY, scenario.ALICE_FIRST_ADDRESS, expiry
        ),
        "address_add": messages.address_add_message(
            chain, who, scenario.ALICE_SECOND_ADDRESS, expiry
        ),
        "address_remove": messages.address_remove_message(
            chain, who, scenario.ALICE_SECOND_ADDRESS, expiry
        ),
        "purchase": messages.purchase_message(
            chain, who, 0, scenario.ALICE_FIRST_ADDRESS, expiry
        ),
        "activation": messages.activation_message(chain, who, 0, expiry),
        "mint": messages.mint_message(chain, who, 0, expiry),
        "mint_biometric_disable": messages.mint_biometric_disable_message(
            chain, who, 0, expiry
        ),
        "manager": messages.manager_message(
            chain, who, 0, scenario.MANAGER_ACCOUNT_ID, expiry
        ),
    }
    for name in sorted(built):
        label, _ = e.HUB_MESSAGES[name]
        check.equal(f"message.label.{name}", label)
        check.agree(f"message.bytes.{name}", e.hub_message_bytes(name), len(built[name]))
        check.equal(f"message.hex.{name}", built[name].hex())

    check.agree("message.count", len(e.HUB_MESSAGES), len(built))
    check.equal("message.all_distinct", len(set(built.values())) == len(built))
    check.agree(
        "message.verifier_signed_count",
        len(e.VERIFIER_SIGNED_MESSAGES),
        len(c.VERIFIER_SIGNED_LABELS),
    )
    check.equal("message.verifier_signed", ",".join(e.VERIFIER_SIGNED_MESSAGES))
    check.equal(
        "message.person_signed_count", len(built) - len(c.VERIFIER_SIGNED_LABELS)
    )

    identical_shape = ("activation", "mint", "mint_biometric_disable")
    check.equal(
        "message.identical_field_shapes_differ_only_by_label",
        len({built[name] for name in identical_shape}) == 3
        and len(
            {
                len(built[name]) - len(e.domain(e.HUB_MESSAGES[name][0]))
                for name in identical_shape
            }
        )
        == 1,
    )
    check.equal(
        "message.every_message_names_the_identity",
        all(scenario.ALICE_IDENTITY in value for value in built.values()),
    )
    other = messages.mint_message(chain, scenario.BOB_IDENTITY, 0, expiry)
    check.equal("message.rebinding_the_identity_changes_it", other != built["mint"])
    check.equal(
        "message.rebinding_the_seat_changes_it",
        messages.mint_message(chain, who, 1, expiry) != built["mint"],
    )
    check.equal(
        "message.rebinding_the_chain_changes_it",
        messages.mint_message(bytes(32), who, 0, expiry) != built["mint"],
    )
    check.equal(
        "message.rebinding_the_expiry_changes_it",
        messages.mint_message(chain, who, 0, expiry + 1) != built["mint"],
    )


def check_result_codes(check: Checker) -> None:
    check.agree("codes.count", len(e.RESULT_CODES), len(c.RESULT_CODES))
    for number, name in sorted(e.RESULT_CODES.items()):
        check.agree(f"codes.{number}", name, c.RESULT_CODES[number])

    check.agree(
        "codes.inherited_count",
        len(e.VERSION_ONE_TRANSFER_RESULTS),
        len(c.INHERITED_RESULT_CODES),
    )
    check.agree(
        "codes.version_three_count",
        e.VERSION_THREE_RESULT_COUNT,
        len(c.VERSION_THREE_RESULT_CODES),
    )
    check.agree(
        "codes.added_count",
        len(e.RESULT_CODES) - e.VERSION_THREE_RESULT_COUNT,
        len(c.ADDED_RESULT_CODES),
    )
    check.equal(
        "codes.added_names",
        ",".join(c.RESULT_CODES[number] for number in c.ADDED_RESULT_CODES),
    )
    check.equal(
        "codes.new_beyond_the_model",
        ",".join(
            sorted(
                name
                for number, name in c.RESULT_CODES.items()
                if number >= 9 and name not in c.CARRIED_MODEL_CODES.values()
            )
        ),
    )
    check.equal(
        "codes.version_one_meanings_preserved",
        all(
            c.RESULT_CODES[number] == name
            for number, name in e.VERSION_ONE_TRANSFER_RESULTS.items()
        ),
    )
    check.equal(
        "codes.numbering_is_contiguous",
        sorted(c.RESULT_CODES) == list(range(len(c.RESULT_CODES))),
    )


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
    check.equal(
        "codes.model.guards_have_no_receipt_code", not (guards & set(c.CODE_NUMBER))
    )
    for name in sorted(unrepresentable):
        check.equal(
            f"codes.model.unrepresentable.{name}", c.UNREPRESENTABLE_MODEL_CODES[name]
        )


def check_receipt(check: Checker) -> None:
    check.agree("receipt.bytes", e.receipt_bytes(), receipt.RECEIPT_BYTES)
    check.equal("receipt.version", c.RECEIPT_VERSION)
    check.equal("receipt.layout_matches_version_two", receipt.RECEIPT_BYTES == 56)
    check.equal(
        "receipt.non_issuing_kinds",
        ",".join(
            c.TRANSACTION_KINDS[kind] for kind in sorted(receipt.NON_ISSUING_KINDS)
        ),
    )

    accepted = receipt.Receipt(
        transaction_id=bytes.fromhex("ab" * 32),
        kind=c.MINT_NODE,
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
        "unknown_kind": replace(accepted.transaction_id, 13, 0, 1_000, 0),
        "unknown_result_code": replace(accepted.transaction_id, 1, 200, 0, 0),
        "failed_with_fee": replace(accepted.transaction_id, 1, failed, 1_000, 0),
        "failed_with_issuance": replace(accepted.transaction_id, 4, failed, 0, 1),
        "non_issuing_kind_issues": replace(accepted.transaction_id, 1, 0, 1_000, 1),
        "purchase_issues": replace(
            accepted.transaction_id, c.PURCHASE_SEAT, 0, 1_000, 1
        ),
        "hub_register_issues": replace(
            accepted.transaction_id, c.HUB_REGISTER, 0, 1_000, 1
        ),
        "hub_add_address_issues": replace(
            accepted.transaction_id, c.HUB_ADD_ADDRESS, 0, 1_000, 1
        ),
    }


def _receipt_refusal(candidate: receipt.Receipt) -> str:
    try:
        receipt.encode(candidate)
    except receipt.InvalidReceipt:
        return "INVALID_RECEIPT"
    return "accepted"
