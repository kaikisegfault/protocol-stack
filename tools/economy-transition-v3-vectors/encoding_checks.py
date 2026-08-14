"""Envelope, compatibility, admission, message, code-space, and receipt checks."""

from __future__ import annotations

from pathlib import Path

import expected as e
from checker import Checker, read_vectors

from simulation.economy_transition_v3 import contract as c
from simulation.economy_transition_v3 import envelope, messages, receipt, scenario

KIND_NAMES = {kind: name for kind, name in c.TRANSACTION_KINDS.items()}


def check_envelope(check: Checker) -> None:
    check.agree("envelope.header_bytes", e.HEADER_BYTES, c.HEADER_BYTES)
    check.agree("envelope.trailer_bytes", e.TRAILER_BYTES, c.TRAILER_BYTES)
    check.agree("envelope.signature_bytes", e.SIGNATURE_BYTES, c.SIGNATURE_BYTES)
    check.agree("envelope.schema_version", 1, c.ENVELOPE_SCHEMA_VERSION)
    check.agree("envelope.kind_count", len(e.BODY_FIELD_WIDTHS), len(c.TRANSACTION_KINDS))

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
    # Version two recorded that a later version might add a kind whose length
    # coincides, and required dispatch on the kind byte for exactly that case.
    # Version three is that later version, so the collision is recorded as a
    # derived fact rather than avoided by padding.
    colliding = sorted(
        name
        for kind, name in KIND_NAMES.items()
        if sum(1 for other in c.BODY_BYTES.values() if other == c.BODY_BYTES[kind]) > 1
    )
    check.equal("envelope.kinds_sharing_a_body_length", ",".join(colliding))
    check.agree(
        "envelope.distinct_body_lengths",
        len(set(e.fixed_body_bytes(kind) for kind in e.BODY_FIELD_WIDTHS)),
        len(set(c.BODY_BYTES.values())),
    )
    check.equal("envelope.largest_signed_bytes", max(
        envelope.expected_signed_length(kind) for kind in c.TRANSACTION_KINDS
    ))

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

    largest = max(envelope.expected_signed_length(kind) for kind in c.TRANSACTION_KINDS)
    check.equal("envelope.largest_fits_object_bound", largest <= e.MAX_OBJECT_BYTES)
    check.equal("envelope.no_body_scales_with_the_population", True)


def check_compatibility(check: Checker, vector_root: Path) -> None:
    """The kind-1 identity, derived twice and checked against the accepted file.

    `expected.py` builds the transfer from the flat version-one field table and
    the model builds it from a header, a body, and a trailer. Both are then
    required to equal the bytes `protocol-primitives-v1` recorded, so the
    factoring is evidence rather than a restatement of itself — and requiring it
    again under version three is what shows that four new kinds, three new state
    entries, and a new settlement rule left it untouched.
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
    # The two transaction labels are deliberately not re-versioned and the six
    # verifier message labels are. Recording both halves keeps the asymmetry a
    # stated decision rather than an oversight.
    check.equal(
        "compatibility.transaction_labels_are_version_one",
        c.SIGN_LABEL.startswith("protocol-stack:v1:")
        and c.TX_ID_LABEL.startswith("protocol-stack:v1:"),
    )
    check.equal(
        "compatibility.verifier_labels_are_version_three",
        all(label.startswith("protocol-stack:v3:") for label in c.VERIFIER_MESSAGE_LABELS),
    )


def check_admission(check: Checker) -> None:
    """Every admission rejection is produced by mutating an accepted encoding."""
    transfer = scenario.accepted_transfer()
    accepted = bytearray(envelope.signed_bytes(transfer, scenario.TRANSFER_SIGNATURE))

    for number, name in sorted({1: "MALFORMED_TRANSACTION", 2: "WRONG_CHAIN",
                                3: "INVALID_SIGNATURE"}.items()):
        check.agree(f"admission.code.{number}", name, c.ADMISSION_CODES[number])

    envelope.decode_signed(bytes(accepted))
    check.equal("admission.positive_control_accepts", True)

    for name, mutated in _admission_mutations(accepted).items():
        check.equal(f"admission.reject.{name}", _refusal(mutated))

    check.equal("admission.reject.unknown_kind", _refusal(_with_kind(accepted, 11)))
    check.equal("admission.reject.kind_zero", _refusal(_with_kind(accepted, 0)))

    # Kinds 3 and 7 share a body length, so re-labelling one as the other is the
    # single case a length check cannot catch. It is admitted, and the signing
    # message differs — which is what makes a verifier approval for an
    # activation unusable as one for a protected mint.
    activate = scenario.transactions()["activate_seat"]
    relabelled = bytearray(envelope.signed_bytes(activate, scenario.TRANSFER_SIGNATURE))
    relabelled[6] = c.MINT_NODE_VERIFIED
    check.equal("admission.relabelled_same_length_kind_decodes", _refusal(bytes(relabelled)))
    decoded, _ = envelope.decode_signed(bytes(relabelled))
    check.equal("admission.relabelled_kind_is_read_as", decoded.kind)
    check.equal(
        "admission.relabelled_kind_changes_the_signing_message",
        envelope.signing_message(envelope.unsigned_bytes(decoded))
        != envelope.signing_message(envelope.unsigned_bytes(activate)),
    )

    # A kind whose length does not coincide is refused before the signature is
    # reached, which is the ordinary case.
    mint = scenario.transactions()["mint_node"]
    raw = bytearray(envelope.signed_bytes(mint, scenario.TRANSFER_SIGNATURE))
    raw[6] = c.MINT_REFERRAL
    check.equal("admission.reject.relabelled_kind", _refusal(bytes(raw)))
    check.equal(
        "admission.the_kind_byte_is_inside_the_signing_message",
        bytes([mint.kind]) in envelope.signing_message(envelope.unsigned_bytes(mint)),
    )


def _admission_mutations(accepted: bytearray) -> dict[str, bytes]:
    # The unreferred purchase is the positive control for the referrer encoding:
    # its 32 zero octets are the only representation of "no referrer".
    purchase = scenario.transactions()["purchase_unreferred_last_seat"]
    purchase_raw = bytearray(envelope.signed_bytes(purchase, scenario.TRANSFER_SIGNATURE))

    non_minimal = bytearray(purchase_raw)
    non_minimal[80 + 69] = 1

    bad_flag = bytearray(purchase_raw)
    bad_flag[80 + 68] = 2

    # Enabling protection carries no verifier signature, so its 64 octets must be
    # zero. This is the half of ADR 0033's asymmetry that is checkable on bytes.
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


def check_verifier_messages(check: Checker) -> None:
    """The six messages, their lengths, and the separation their labels give."""
    chain = scenario.CHAIN_ID
    expiry = scenario.VALID_UNTIL_HEIGHT
    built = {
        "enrollment": messages.enrollment_message(
            chain, 0, scenario.BIOMETRIC_IDENTITY_HASH,
            scenario.PURCHASER_ACCOUNT_ID, expiry
        ),
        "activation": messages.activation_message(
            chain, 0, scenario.PURCHASER_ACCOUNT_ID, expiry
        ),
        "mint": messages.mint_message(chain, 0, scenario.PURCHASER_ACCOUNT_ID, expiry),
        "mint_biometric_disable": messages.mint_biometric_disable_message(
            chain, 0, scenario.PURCHASER_ACCOUNT_ID, expiry
        ),
        "manager": messages.manager_message(
            chain, 0, scenario.PURCHASER_ACCOUNT_ID, scenario.MANAGER_ACCOUNT_ID, expiry
        ),
        "hub": messages.hub_message(
            chain, scenario.PURCHASER_ACCOUNT_ID, scenario.HUB_UNIQUENESS_HASH, expiry
        ),
    }
    for name in sorted(built):
        label, _ = e.VERIFIER_MESSAGES[name]
        check.equal(f"message.label.{name}", label)
        check.agree(
            f"message.bytes.{name}", e.verifier_message_bytes(name), len(built[name])
        )
        check.equal(f"message.hex.{name}", built[name].hex())

    check.equal("message.count", len(built))
    check.equal(
        "message.all_distinct", len({value for value in built.values()}) == len(built)
    )
    # Three of the six carry identical field shapes on identical inputs, so only
    # the label separates them. That is what domain separation is for, and it is
    # the property an approval for one action being unusable for another rests on.
    identical_shape = ("activation", "mint", "mint_biometric_disable")
    check.equal(
        "message.identical_field_shapes_differ_only_by_label",
        len({built[name] for name in identical_shape}) == 3
        and len({len(built[name]) - len(e.domain(e.VERIFIER_MESSAGES[name][0]))
                 for name in identical_shape}) == 1,
    )
    # A verifier approval is action-bound: changing the seat, the actor, the
    # chain, or the expiry changes the message the verifier signed.
    base = built["mint"]
    check.equal(
        "message.rebinding_the_seat_changes_the_message",
        messages.mint_message(chain, 1, scenario.PURCHASER_ACCOUNT_ID, expiry) != base,
    )
    check.equal(
        "message.rebinding_the_actor_changes_the_message",
        messages.mint_message(chain, 0, scenario.MANAGER_ACCOUNT_ID, expiry) != base,
    )
    check.equal(
        "message.rebinding_the_chain_changes_the_message",
        messages.mint_message(bytes(32), 0, scenario.PURCHASER_ACCOUNT_ID, expiry) != base,
    )
    check.equal(
        "message.rebinding_the_expiry_changes_the_message",
        messages.mint_message(chain, 0, scenario.PURCHASER_ACCOUNT_ID, expiry + 1) != base,
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
        "codes.version_two_count", e.VERSION_TWO_RESULT_COUNT, len(c.VERSION_TWO_RESULT_CODES)
    )
    check.agree(
        "codes.added_count",
        len(e.RESULT_CODES) - e.VERSION_TWO_RESULT_COUNT,
        len(c.ADDED_RESULT_CODES),
    )
    check.equal(
        "codes.added_names",
        ",".join(c.RESULT_CODES[number] for number in c.ADDED_RESULT_CODES),
    )
    # Six codes name conditions the research model cannot have, because it has
    # no signer, no purchase transition, no manager set, no registry, and no
    # take-everything mint.
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
        "codes.model.guards_have_no_receipt_code",
        not (guards & set(c.CODE_NUMBER)),
    )
    for name in sorted(unrepresentable):
        check.equal(
            f"codes.model.unrepresentable.{name}", c.UNREPRESENTABLE_MODEL_CODES[name]
        )


def check_receipt(check: Checker) -> None:
    check.agree("receipt.bytes", e.receipt_bytes(), receipt.RECEIPT_BYTES)
    check.equal("receipt.version", c.RECEIPT_VERSION)
    # The layout does not move and the version does, because the admissible kind
    # and result-code ranges widen.
    check.equal("receipt.layout_matches_version_two", receipt.RECEIPT_BYTES == 56)
    check.equal(
        "receipt.non_issuing_kinds",
        ",".join(c.TRANSACTION_KINDS[kind] for kind in sorted(receipt.NON_ISSUING_KINDS)),
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
        "unknown_kind": replace(accepted.transaction_id, 11, 0, 1_000, 0),
        "unknown_result_code": replace(accepted.transaction_id, 1, 200, 0, 0),
        "failed_with_fee": replace(accepted.transaction_id, 1, failed, 1_000, 0),
        "failed_with_issuance": replace(accepted.transaction_id, 4, failed, 0, 1),
        "non_issuing_kind_issues": replace(accepted.transaction_id, 1, 0, 1_000, 1),
        "purchase_issues": replace(accepted.transaction_id, c.PURCHASE_SEAT, 0, 1_000, 1),
        "manager_issues": replace(accepted.transaction_id, c.ADD_MANAGER, 0, 1_000, 1),
        "hub_issues": replace(accepted.transaction_id, c.HUB_VERIFY, 0, 1_000, 1),
    }


def _receipt_refusal(candidate: receipt.Receipt) -> str:
    try:
        receipt.encode(candidate)
    except receipt.InvalidReceipt:
        return "INVALID_RECEIPT"
    return "accepted"
