"""Envelope, compatibility, admission, messages, codes, and receipt checks."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import expected as e
from checker import Checker

from simulation.economy_transition_v6 import contract as c
from simulation.economy_transition_v6 import envelope, messages, receipt, scenario
from simulation.economy_transition_v6.envelope import MalformedTransaction
from simulation.economy_transition_v6.identity import Posture


def check_envelope(check: Checker) -> None:
    """The two schemes, the fourteen kinds, and every fixed length."""
    check.agree("envelope.header_bytes", e.HEADER_BYTES, c.HEADER_BYTES)
    check.agree("envelope.trailer_bytes", e.TRAILER_BYTES, c.TRAILER_BYTES)
    check.agree("envelope.signature_bytes", e.SIGNATURE_BYTES, c.SIGNATURE_BYTES)
    check.agree("envelope.kind_count", len(e.KIND_NAMES), len(c.TRANSACTION_KINDS))
    check.agree("envelope.retired_kind_count", len(e.RETIRED_KINDS), len(c.RETIRED_KINDS))
    check.agree("envelope.scheme_count", len(e.SCHEMES), len(c.SIGNATURE_SCHEMES))

    for kind in sorted(e.KIND_NAMES):
        name = e.KIND_NAMES[kind]
        check.agree(f"envelope.kind{kind}.name", name, c.TRANSACTION_KINDS[kind])
        check.agree(
            f"envelope.kind{kind}.body_bytes", e.fixed_body_bytes(kind), c.BODY_BYTES[kind]
        )
        check.agree(
            f"envelope.kind{kind}.unsigned_bytes",
            e.unsigned_length(kind),
            c.HEADER_BYTES + c.BODY_BYTES[kind] + c.TRAILER_BYTES,
        )
        check.agree(
            f"envelope.kind{kind}.signed_bytes",
            e.signed_length(kind),
            envelope.expected_signed_length(kind),
        )
        check.agree(
            f"envelope.kind{kind}.scheme", e.KIND_SCHEME[kind], c.KIND_SCHEME[kind]
        )

    for kind, name in sorted(e.RETIRED_KINDS.items()):
        check.agree(f"envelope.retired{kind}.was", name, c.RETIRED_KINDS[kind])
        check.equal(f"envelope.retired{kind}.is_unassigned", kind not in c.TRANSACTION_KINDS)

    # The widest length collision any version has had. It is recorded as a
    # derived set rather than asserted, because a decoder that dispatched on
    # length would now be wrong five ways rather than two.
    by_length: dict[int, list[int]] = {}
    for kind in c.TRANSACTION_KINDS:
        by_length.setdefault(c.BODY_BYTES[kind], []).append(kind)
    collisions = sorted(
        (length, sorted(kinds)) for length, kinds in by_length.items() if len(kinds) > 1
    )
    derived = sorted(
        (length, sorted(kinds))
        for length, kinds in _group_lengths(e.BODY_FIELD_WIDTHS).items()
        if len(kinds) > 1
    )
    check.agree("envelope.length_collision_groups", len(derived), len(collisions))
    for length, kinds in collisions:
        check.agree(
            f"envelope.length_collision.{length}",
            ",".join(str(k) for k in dict(derived)[length]),
            ",".join(str(k) for k in kinds),
        )

    check.agree(
        "envelope.largest_signed_bytes",
        max(e.signed_length(kind) for kind in e.KIND_NAMES),
        max(envelope.expected_signed_length(kind) for kind in c.TRANSACTION_KINDS),
    )


def _group_lengths(field_widths: dict[int, tuple[int, ...]]) -> dict[int, list[int]]:
    grouped: dict[int, list[int]] = {}
    for kind, widths in field_widths.items():
        grouped.setdefault(sum(widths), []).append(kind)
    return grouped


def check_compatibility(check: Checker, accepted: Path) -> None:
    """The kind-1 byte identity, and the execution divergence beside it.

    The bytes are checked against `test-vectors/protocol-primitives-v1.txt`
    rather than against this model's second opinion, which is the third source
    every version since two has used for exactly this claim.
    """
    recorded = _read(accepted / "protocol-primitives-v1.txt")
    transfer = scenario.accepted_transfer()
    unsigned = envelope.unsigned_bytes(transfer)
    signed = envelope.signed_bytes(transfer, scenario.TRANSFER_SIGNATURE)

    flat = e.flat_unsigned_transfer(
        chain_id=bytes.fromhex(recorded["chain_id"]),
        public_key=scenario.SENDER_PUBLIC_KEY,
        nonce=transfer.nonce,
        recipient=transfer.body["recipient_escrow_id"],
        amount=transfer.body["amount_atomic"],
        fee_limit=transfer.fee_limit,
        valid_until=transfer.valid_until_height,
    )
    check.agree("compatibility.unsigned_transfer_hex", flat.hex(), unsigned.hex())
    check.equal(
        "compatibility.unsigned_transfer_equals_accepted_bytes",
        unsigned.hex() == recorded["unsigned_tx"],
    )
    check.equal(
        "compatibility.signed_transfer_equals_accepted_bytes",
        signed.hex() == recorded["signed_tx"],
    )
    check.equal(
        "compatibility.transaction_id_equals_accepted_id",
        envelope.transaction_id(signed) == recorded["tx.item2"],
    )
    check.agree(
        "compatibility.unsigned_transfer_bytes", e.UNSIGNED_TRANSFER_BYTES, len(unsigned)
    )
    check.agree(
        "compatibility.signed_transfer_bytes", e.SIGNED_TRANSFER_BYTES, len(signed)
    )

    # The half no earlier version had to record: the same bytes, a different
    # result. Version one creates the recipient; version six refuses it.
    registered = scenario.registry()
    check.equal(
        "compatibility.accepted_recipient_is_not_a_registered_escrow",
        transfer.body["recipient_escrow_id"] not in registered.escrows,
    )
    check.equal(
        "compatibility.transfer_to_a_registered_escrow_is_representable",
        scenario.BOB_ESCROW in registered.escrows,
    )
    check.agree(
        "compatibility.unregistered_recipient_code",
        e.RESULT_CODES[27],
        c.RESULT_CODES[27],
    )


def check_admission(check: Checker) -> None:
    """Every step-1 classification, over a minimally mutated accepted input."""
    check.agree("admission.code_count", len(e.ADMISSION_CODES), len(c.ADMISSION_CODES))
    for number, name in sorted(e.ADMISSION_CODES.items()):
        check.agree(f"admission.code{number}", name, c.ADMISSION_CODES[number])

    valid = envelope.signed_bytes(
        scenario.accepted_transfer(), scenario.TRANSFER_SIGNATURE
    )
    check.equal("admission.positive_control_decodes", _decodes(valid))

    mutations = {
        "wrong_magic": bytes([valid[0] ^ 0xFF]) + valid[1:],
        "wrong_schema_version": valid[:4] + b"\x00\x02" + valid[6:],
        "unknown_kind": valid[:6] + bytes([200]) + valid[7:],
        "retired_kind": valid[:6] + bytes([9]) + valid[7:],
        "unknown_scheme": valid[:39] + bytes([9]) + valid[40:],
        "scheme_this_kind_forbids": valid[:39] + bytes([2]) + valid[40:],
        "trailing_suffix": valid + b"\x00",
        "truncated": valid[:-1],
    }
    for name, raw in mutations.items():
        check.equal(f"admission.refuses_{name}", not _decodes(raw))

    # The non-minimal encodings this version adds to the ones version two named.
    purchase = scenario.transactions()["purchase_unreferred_last_seat"]
    body = bytearray(envelope.body_bytes(purchase.kind, purchase.body))
    body[5] = 0xFF
    check.equal(
        "admission.refuses_non_minimal_absent_referrer",
        not _body_decodes(purchase.kind, bytes(body)),
    )

    posture = scenario.transactions()["posture_relax"]
    raw = bytearray(envelope.body_bytes(posture.kind, posture.body))
    raw[9] = 0x01
    check.equal(
        "admission.refuses_slot_mask_above_slot_23",
        not _body_decodes(posture.kind, bytes(raw)),
    )
    raw = bytearray(envelope.body_bytes(posture.kind, posture.body))
    raw[0] = 0x02
    check.equal(
        "admission.refuses_non_canonical_confirmation_flag",
        not _body_decodes(posture.kind, bytes(raw)),
    )

    registration = scenario.transactions()["hub_register"]
    check.equal(
        "admission.refuses_registration_with_a_nonzero_nonce",
        not _encodes(replace(registration, nonce=1)),
    )
    check.equal(
        "admission.refuses_registration_with_a_nonzero_fee_limit",
        not _encodes(replace(registration, fee_limit=1)),
    )


def _decodes(raw: bytes) -> bool:
    try:
        envelope.decode_signed(raw)
    except MalformedTransaction:
        return False
    return True


def _body_decodes(kind: int, body: bytes) -> bool:
    template = scenario.transactions()["transfer"]
    header = (
        c.TRANSACTION_MAGIC
        + envelope.u16(c.ENVELOPE_SCHEMA_VERSION)
        + envelope.u8(kind)
        + template.chain_id
        + envelope.u8(c.KIND_SCHEME[kind])
        + template.authority_public_key
        + envelope.u64(1)
    )
    trailer = envelope.u64(0) + envelope.u64(1)
    return _decodes(header + body + trailer + bytes(64))


def _encodes(transaction) -> bool:
    try:
        raw = envelope.signed_bytes(transaction, bytes(64))
    except MalformedTransaction:
        return False
    return _decodes(raw)


def check_hub_messages(check: Checker) -> None:
    """The six constructions, their widths, and their pairwise distinctness."""
    check.agree("hub.message_count", len(e.HUB_MESSAGES), len(c.HUB_MESSAGE_LABELS))
    check.agree(
        "hub.verifier_signed_count",
        len(e.VERIFIER_SIGNED_MESSAGES),
        len(c.VERIFIER_SIGNED_LABELS),
    )

    chain = scenario.CHAIN_ID
    identity = scenario.ALICE_IDENTITY
    height = scenario.VALID_UNTIL_HEIGHT
    built = {
        "registration": messages.registration_message(
            chain, identity, scenario.ALICE_KEY, scenario.ALICE_SIGNER_KEY, height
        ),
        "purchase": messages.purchase_message(chain, identity, 0, height),
        "activation": messages.activation_message(chain, identity, 0, height),
        "mint": messages.mint_message(
            chain, identity, c.MINT_NODE, 0, scenario.ALICE_FIRST_ESCROW, height
        ),
        "posture_relax": messages.posture_relax_message(
            chain, identity, scenario.ALICE_FIRST_ESCROW, Posture(), height
        ),
        "transfer_confirm": messages.transfer_confirm_message(
            chain, identity, scenario.ALICE_FIRST_ESCROW, scenario.BOB_ESCROW, 1, height
        ),
    }
    seat = e.be(0, 4)
    kind_byte = e.be(c.MINT_NODE, 1)
    strict = (e.be(1, 1), e.be(0, 8), e.be(0, 4))
    terms = {
        "registration": [chain, identity, scenario.ALICE_KEY, scenario.ALICE_SIGNER_KEY,
                         e.be(height, 8)],
        "purchase": [chain, identity, seat, e.be(height, 8)],
        "activation": [chain, identity, seat, e.be(height, 8)],
        "mint": [chain, identity, kind_byte, seat, scenario.ALICE_FIRST_ESCROW,
                 e.be(height, 8)],
        "posture_relax": [chain, identity, scenario.ALICE_FIRST_ESCROW, *strict,
                          e.be(height, 8)],
        "transfer_confirm": [chain, identity, scenario.ALICE_FIRST_ESCROW,
                             scenario.BOB_ESCROW, e.be(1, 8), e.be(height, 8)],
    }
    for name in sorted(e.HUB_MESSAGES):
        label = e.HUB_MESSAGES[name][0]
        check.agree(f"hub.{name}.label", label, _label_of(name))
        check.agree(f"hub.{name}.bytes", e.hub_message_bytes(name), len(built[name]))
        check.agree(
            f"hub.{name}.hex", e.hub_message(name, terms[name]).hex(), built[name].hex()
        )

    check.equal("hub.messages_are_pairwise_distinct", len(set(built.values())) == 6)

    # The three mints share every field but the kind byte, which is what stops a
    # confirmation for one being replayed onto another.
    per_kind = {
        kind: messages.mint_message(
            chain, identity, kind, 0, scenario.ALICE_FIRST_ESCROW, height
        )
        for kind in e.CONFIRMABLE_MINTS
    }
    check.equal("hub.mint_messages_differ_by_kind", len(set(per_kind.values())) == 3)
    check.agree(
        "hub.confirmable_mint_count", len(e.CONFIRMABLE_MINTS), len(c.CONFIRMABLE_MINTS)
    )

    # A relax approval binds the exact posture, so an approval to raise a
    # minimum cannot be presented as an approval to turn confirmation off.
    off = messages.posture_relax_message(
        chain,
        identity,
        scenario.ALICE_FIRST_ESCROW,
        Posture(requires_confirmation=False),
        height,
    )
    check.equal(
        "hub.posture_message_binds_the_exact_posture", off != built["posture_relax"]
    )


def _label_of(name: str) -> str:
    return {
        "registration": c.REGISTRATION_LABEL,
        "purchase": c.PURCHASE_LABEL,
        "activation": c.ACTIVATION_LABEL,
        "mint": c.MINT_CONFIRM_LABEL,
        "posture_relax": c.POSTURE_RELAX_LABEL,
        "transfer_confirm": c.TRANSFER_CONFIRM_LABEL,
    }[name]


def check_result_codes(check: Checker) -> None:
    """The complete space, its contiguity, and the three frozen unreachables."""
    check.agree("codes.count", len(e.RESULT_CODES), len(c.RESULT_CODES))
    check.equal(
        "codes.space_is_contiguous_from_zero",
        sorted(c.RESULT_CODES) == list(range(len(c.RESULT_CODES))),
    )
    for number in sorted(e.RESULT_CODES):
        check.agree(f"codes.code{number}", e.RESULT_CODES[number], c.RESULT_CODES[number])
    check.agree(
        "codes.version_four_carried_count",
        e.VERSION_FOUR_RESULT_COUNT,
        len(c.VERSION_FOUR_RESULT_CODES),
    )
    check.agree("codes.added_count", 7, len(c.ADDED_RESULT_CODES))
    check.agree(
        "codes.unreachable_count",
        len(e.UNREACHABLE_RESULT_CODES),
        len(c.UNREACHABLE_RESULT_CODES),
    )
    for number in e.UNREACHABLE_RESULT_CODES:
        check.equal(
            f"codes.code{number}_is_frozen_and_unreachable",
            number in c.UNREACHABLE_RESULT_CODES and number in c.RESULT_CODES,
        )


def check_model_mapping(check: Checker) -> None:
    """The economy model's twenty-four codes partition exactly as in version four."""
    carried = set(c.CARRIED_MODEL_CODES)
    guards = set(c.GUARD_MODEL_CODES)
    unrepresentable = set(c.UNREPRESENTABLE_MODEL_CODES)
    declared = set(e.MODEL_RESULT_CODES)

    check.agree("model_mapping.carried_count", 11, len(carried))
    check.agree("model_mapping.guard_count", 2, len(guards))
    check.agree("model_mapping.unrepresentable_count", 11, len(unrepresentable))
    check.equal(
        "model_mapping.three_sets_partition_the_declared_set",
        carried | guards | unrepresentable == declared
        and not (carried & guards)
        and not (carried & unrepresentable)
        and not (guards & unrepresentable),
    )
    for name in sorted(carried):
        check.agree(
            f"model_mapping.carried.{name}",
            c.CARRIED_MODEL_CODES[name],
            c.CARRIED_MODEL_CODES[name],
        )


def check_receipt(check: Checker) -> None:
    """The layout, the new version, and the fee-exempt success."""
    check.agree("receipt.bytes", e.receipt_bytes(), receipt.RECEIPT_BYTES)
    check.agree("receipt.version", e.RECEIPT_VERSION, c.RECEIPT_VERSION)
    check.agree(
        "receipt.non_issuing_kind_count",
        len(e.NON_ISSUING_KINDS),
        len(receipt.NON_ISSUING_KINDS),
    )
    for kind in e.NON_ISSUING_KINDS:
        check.equal(
            f"receipt.kind{kind}_issues_nothing", kind in receipt.NON_ISSUING_KINDS
        )

    success = receipt.Receipt(bytes(32), c.TRANSFER, 0, 7, 0)
    check.agree(
        "receipt.success_hex",
        e.receipt_hex(bytes(32), c.TRANSFER, 0, 7, 0),
        receipt.encode(success).hex(),
    )
    check.equal(
        "receipt.round_trips", receipt.decode(receipt.encode(success)) == success
    )

    registration = receipt.Receipt(bytes(32), c.HUB_REGISTER, 0, 0, 171_000_000)
    check.equal(
        "receipt.a_registration_success_charges_no_fee",
        receipt.decode(receipt.encode(registration)).fee_charged == 0,
    )
    check.equal(
        "receipt.a_registration_issues_the_entry_airdrop",
        registration.issued_atomic == e.verified_user_daily_atomic(),
    )
    check.equal(
        "receipt.refuses_a_registration_that_charged_a_fee",
        not _receipt_valid(receipt.Receipt(bytes(32), c.HUB_REGISTER, 0, 7, 0)),
    )
    check.equal(
        "receipt.refuses_a_retired_kind",
        not _receipt_valid(receipt.Receipt(bytes(32), 9, 0, 0, 0)),
    )
    check.equal(
        "receipt.refuses_a_failure_that_charged_a_fee",
        not _receipt_valid(receipt.Receipt(bytes(32), c.TRANSFER, 12, 7, 0)),
    )
    check.equal(
        "receipt.refuses_a_failure_that_issued_units",
        not _receipt_valid(receipt.Receipt(bytes(32), c.MINT_NODE, 12, 0, 5)),
    )


def _receipt_valid(candidate: receipt.Receipt) -> bool:
    try:
        receipt.require_consistent(candidate)
    except (receipt.InvalidReceipt, MalformedTransaction):
        return False
    return True


def _read(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        values[key] = value
    return values
