#!/usr/bin/env python3
"""Independently derive and check the economy-transition-v10 contract vectors.

Every recorded value is derived twice: once from the specification in
`expected.py`, which imports nothing from `simulation/`, and once from a live
run of `simulation/economy_transition_v10`. A value only the model reaches
would be a restatement of the model, not evidence about it. The carryover
section is the exception, and says so: it compares version ten's tables with
version nine's own objects.

`--emit` rewrites the vector file from the same derivations through the same
agreement gate, so a recorded value is never transcribed by hand.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import expected as e
from checker import Checker, read_vectors

from simulation.economy_transition_v9 import contract as v9c
from simulation.economy_transition_v9 import envelope as v9envelope
from simulation.economy_transition_v10 import contract as c
from simulation.economy_transition_v10 import envelope, genesis, messages, state

CHAIN_FIXTURE = bytes([0x0C]) * 32
IDENTITY = bytes([0xA1]) * 32
HUB_KEY = bytes([0x01]) * 32
FIRST_SIGNER = bytes([0x11]) * 32
SIGNER = bytes([0x12]) * 32
MACHINE_KEY = bytes([0x22]) * 32
BUILD_DIGEST = bytes([0x33]) * 32
RECIPIENT = bytes([0xB1]) * 32
SIGNATURE = bytes([0x5A]) * 64
NO_SIGNATURE = bytes(64)
SEAT = 7
VALID_UNTIL = 1_200


def fixture_genesis() -> genesis.Genesis:
    return genesis.Genesis(
        network_id=10,
        genesis_timestamp=1_768_435_200_000,
        supply_limit=5_699_395_010_000_000_000,
        fixed_transfer_fee=1_000,
        manifest_digest=bytes.fromhex(c.MANIFEST_DIGEST_HEX),
        launch_key=bytes([0x55]) * 32,
        dispute_authority_key=bytes([0xD8]) * 32,
        build_authority_key=bytes([0xB4]) * 32,
    )


def check_version_identity(check: Checker) -> None:
    check.section(
        "Three constructions are re-versioned: the chain ID, the state root, and "
        "the economy tree. The block header's bytes do not change, so its schema "
        "version and the block identifier keep version nine's."
    )
    check.agree("identity.chain_id_label", e.CHAIN_ID_LABEL, c.CHAIN_ID_LABEL)
    check.agree("identity.state_root_label", e.STATE_ROOT_LABEL, c.STATE_ROOT_LABEL)
    check.agree(
        "identity.economy_tree_prefix", e.ECONOMY_TREE_PREFIX, c.ECONOMY_TREE_PREFIX
    )
    check.agree(
        "identity.genesis_schema_version", e.SCHEMA_VERSION, c.GENESIS_SCHEMA_VERSION
    )
    check.agree(
        "identity.state_root_schema_version",
        e.SCHEMA_VERSION,
        c.STATE_ROOT_SCHEMA_VERSION,
    )
    check.agree("identity.receipt_version", e.RECEIPT_VERSION, c.RECEIPT_VERSION)
    check.agree("identity.block_id_label", e.BLOCK_ID_LABEL, c.BLOCK_ID_LABEL)
    check.agree(
        "identity.block_header_schema_version",
        e.BLOCK_HEADER_SCHEMA_VERSION,
        c.BLOCK_HEADER_SCHEMA_VERSION,
    )
    check.section(
        "Two HUB labels replace version nine's six. The registration is the only "
        "message an attester signs, and the approval is the only one a HUB key "
        "signs in a body."
    )
    check.agree(
        "identity.registration_label", e.REGISTRATION_LABEL, c.REGISTRATION_LABEL
    )
    check.agree("identity.approval_label", e.APPROVAL_LABEL, c.APPROVAL_LABEL)
    check.agree(
        "identity.attestation_label", e.ATTESTATION_LABEL, c.ATTESTATION_LABEL
    )
    check.equal(
        "identity.hub_message_labels", ",".join(c.HUB_MESSAGE_LABELS)
    )


def check_widths(check: Checker) -> None:
    check.section(
        "Kind 10 gains four octets for the attesting seat. Kind 23 is new. Every "
        "length is header plus body plus trailer plus signature."
    )
    check.agree("widths.kind_10_body", e.KIND_10_BODY_BYTES, c.BODY_BYTES[10])
    check.agree(
        "widths.kind_10_signed",
        e.HEADER_BYTES + e.KIND_10_BODY_BYTES + e.TRAILER_BYTES + e.SIGNATURE_BYTES,
        envelope.expected_signed_length(10),
    )
    check.agree("widths.kind_23_body", e.KIND_23_BODY_BYTES, c.BODY_BYTES[23])
    check.agree(
        "widths.kind_23_signed",
        e.HEADER_BYTES + e.KIND_23_BODY_BYTES + e.TRAILER_BYTES + e.SIGNATURE_BYTES,
        envelope.expected_signed_length(23),
    )
    check.agree("widths.genesis_prefix", e.GENESIS_PREFIX_BYTES, c.GENESIS_PREFIX_BYTES)
    check.agree("widths.max_genesis_accounts", e.account_bound(), c.MAX_GENESIS_ACCOUNTS)
    for kind, (name, key_bytes, value_bytes) in sorted(e.ADDED_ENTRIES.items()):
        check.agree(f"widths.entry_{kind}_name", name, c.ENTRY_KINDS[kind])
        check.agree(f"widths.entry_{kind}_key", key_bytes, c.ENTRY_KEY_BYTES[kind])
        check.agree(
            f"widths.entry_{kind}_value", value_bytes, c.ENTRY_VALUE_BYTES[kind]
        )


def check_constants(check: Checker) -> None:
    check.section(
        "ADR 0101's three answers, and engineering's two figures. Each is a "
        "consensus parameter of this version, not a deployment option."
    )
    check.agree(
        "constants.launch_retirement_active_machines",
        e.LAUNCH_RETIREMENT_ACTIVE_MACHINES,
        c.LAUNCH_RETIREMENT_ACTIVE_MACHINES,
    )
    check.agree(
        "constants.machine_registrations_per_window",
        e.MACHINE_REGISTRATIONS_PER_WINDOW,
        c.MACHINE_REGISTRATIONS_PER_WINDOW,
    )
    check.agree(
        "constants.activity_threshold_seconds",
        e.ACTIVITY_THRESHOLD_SECONDS,
        c.ACTIVITY_THRESHOLD_SECONDS,
    )
    check.agree(
        "constants.approval_lifetime_blocks",
        e.APPROVAL_LIFETIME_BLOCKS,
        c.APPROVAL_LIFETIME_BLOCKS,
    )
    check.agree("constants.launch_attester", e.LAUNCH_ATTESTER, c.LAUNCH_ATTESTER)
    check.equal(
        "constants.launch_attester_is_above_every_seat",
        c.LAUNCH_ATTESTER > c.MAX_SEAT_ID,
    )
    check.section(
        "Five result codes are added, and codes 0 through 44 keep version nine's "
        "meanings."
    )
    for number, name in sorted(e.ADDED_RESULT_CODES.items()):
        check.agree(f"codes.{number}", name, c.RESULT_CODES[number])
    check.agree("codes.count", e.RESULT_CODE_COUNT, len(c.RESULT_CODES))
    check.equal(
        "codes.zero_through_forty_four_unchanged",
        all(c.RESULT_CODES[n] == v9c.RESULT_CODES[n] for n in range(45)),
    )
    check.section(
        "The kinds that carry a body approval, and the kinds that always carry a "
        "HUB proof."
    )
    check.agree(
        "kinds.approval",
        ",".join(str(k) for k in e.APPROVAL_KINDS),
        ",".join(str(k) for k in sorted(c.APPROVAL_KINDS)),
    )
    check.agree(
        "kinds.always_proven",
        ",".join(str(k) for k in e.ALWAYS_PROVEN_KINDS),
        ",".join(str(k) for k in sorted(c.ALWAYS_PROVEN_KINDS)),
    )


def check_genesis(check: Checker) -> None:
    check.section(
        "A fixture genesis: version nine's trace figures with three distinct "
        "keys. The launch key keeps the verifier key's offset and its state "
        "entry, and the build authority key follows the dispute authority key."
    )
    fixture = fixture_genesis()
    independent = e.genesis_bytes(
        fixture.network_id,
        fixture.genesis_timestamp,
        fixture.supply_limit,
        fixture.fixed_transfer_fee,
        fixture.launch_key,
        fixture.dispute_authority_key,
        fixture.build_authority_key,
    )
    check.agree("genesis.bytes", independent, genesis.encode(fixture))
    check.agree("genesis.chain_id", e.chain_id(independent), genesis.chain_id(fixture))
    entries = genesis.initial_economy_entries(fixture)
    check.equal("genesis.economy_entry_count", len(entries))
    check.agree(
        "genesis.launch_key_entry",
        fixture.launch_key,
        entries[bytes([e.VERIFIER_KEY_ENTRY])],
    )
    check.equal(
        "genesis.writes_no_registry_entry",
        not any(key[0] in c.ADDED_IN_V10_ENTRY_KINDS for key in entries),
    )


def check_non_collision(check: Checker) -> None:
    check.section(
        "The version-ten chain ID differs from the same fields under every "
        "earlier schema and label, each required separately."
    )
    fixture = fixture_genesis()
    here = genesis.chain_id(fixture)
    for version in range(2, 10):
        check.equal(
            f"non_collision.chain_id_v{version}_differs",
            genesis.predecessor_chain_id(fixture, version) != here,
        )
    check.section(
        "The genesis state under version ten's root differs from the same state "
        "under every earlier root."
    )
    entries = genesis.initial_economy_entries(fixture)
    args = (
        here,
        0,
        fixture.genesis_timestamp,
        fixture.supply_limit,
        0,
        0,
        [],
        entries,
    )
    root = state.state_root(*args)
    for version in range(1, 10):
        check.equal(
            f"non_collision.state_root_v{version}_differs",
            state.predecessor_state_root(version, *args) != root,
        )


def check_state_surface(check: Checker) -> None:
    check.section(
        "The three new entries, encoded from the specification's tables, and "
        "the values no transition writes, refused by the decoders."
    )
    fixture = state.MachineKey(MACHINE_KEY, BUILD_DIGEST, 3, 5, 6, 999)
    check.agree("state.machine_key_key", e.machine_key_key(SEAT), state.machine_key_key(SEAT))
    check.agree(
        "state.machine_key_value",
        e.machine_key_value(MACHINE_KEY, BUILD_DIGEST, 3, 5, 6, 999),
        state.machine_key_value(fixture),
    )
    check.agree(
        "state.launch_retirement_key",
        e.launch_retirement_key(),
        state.launch_retirement_key(),
    )
    check.agree(
        "state.launch_retirement_value",
        e.launch_retirement_value(86_401),
        state.launch_retirement_value(86_401),
    )
    check.agree(
        "state.machine_key_owner_key",
        e.machine_key_owner_key(MACHINE_KEY),
        state.machine_key_owner_key(MACHINE_KEY),
    )
    check.agree(
        "state.machine_key_owner_value",
        e.machine_key_owner_value(SEAT),
        state.machine_key_owner_value(SEAT),
    )
    check.equal(
        "state.machine_key_round_trips",
        state.decode_machine_key_value(state.machine_key_value(fixture)) == fixture,
    )
    limit = e.machine_key_value(MACHINE_KEY, BUILD_DIGEST, 3, 5, 6, 1_000)
    over = e.machine_key_value(MACHINE_KEY, BUILD_DIGEST, 3, 5, 6, 1_001)
    unwritten = e.machine_key_value(MACHINE_KEY, BUILD_DIGEST, 0, 5, 6, 0)
    check.equal(
        "state.machine_key_admits_the_limit",
        state.decode_machine_key_value(limit).registrations_in_window == 1_000,
    )
    check.equal("state.machine_key_refuses_a_count_above_the_limit", _refused(state.decode_machine_key_value, over))
    check.equal("state.machine_key_refuses_a_zero_height", _refused(state.decode_machine_key_value, unwritten))
    check.equal(
        "state.launch_retirement_refuses_zero",
        _refused(state.decode_launch_retirement_value, bytes(8)),
    )
    check.equal(
        "state.entry_shape_refuses_a_short_owner_value",
        _refused(lambda raw: state.require_entry_shape(e.machine_key_owner_key(MACHINE_KEY), raw), bytes(3)),
    )


def _refused(function, raw) -> bool:
    try:
        function(raw)
    except state.InvalidStateEntry:
        return True
    return False


def _kind_10(seat: int) -> envelope.Transaction:
    return envelope.Transaction(
        kind=10,
        scheme=c.SCHEME_IDENTITY,
        chain_id=CHAIN_FIXTURE,
        authority_public_key=HUB_KEY,
        nonce=0,
        body={
            "hub_identity_hash": IDENTITY,
            "first_signer_public_key": FIRST_SIGNER,
            "attesting_seat_id": seat,
            "attestation_signature": SIGNATURE,
        },
        fee_limit=0,
        valid_until_height=VALID_UNTIL,
    )


def _kind_23(hub: bytes, nonce: int = 4) -> envelope.Transaction:
    return envelope.Transaction(
        kind=23,
        scheme=c.SCHEME_SIGNER,
        chain_id=CHAIN_FIXTURE,
        authority_public_key=SIGNER,
        nonce=nonce,
        body={
            "seat_id": SEAT,
            "machine_public_key": MACHINE_KEY,
            "build_digest": BUILD_DIGEST,
            "attestation_signature": SIGNATURE,
            "hub_signature": hub,
        },
        fee_limit=1_000,
        valid_until_height=VALID_UNTIL,
    )


def _kind_19(hub: bytes, nonce: int = 4) -> envelope.Transaction:
    return envelope.Transaction(
        kind=19,
        scheme=c.SCHEME_SIGNER,
        chain_id=CHAIN_FIXTURE,
        authority_public_key=SIGNER,
        nonce=nonce,
        body={"recipient_escrow_id": RECIPIENT, "amount_atomic": 9, "hub_signature": hub},
        fee_limit=1_000,
        valid_until_height=VALID_UNTIL,
    )


def check_bodies(check: Checker) -> None:
    check.section(
        "The two changed bodies, built from the header and body tables, and "
        "decoded back. A registration names the launch key by the attester u32 "
        "maximum."
    )
    for name, seat in (("launch", c.LAUNCH_ATTESTER), ("machine", SEAT)):
        transaction = _kind_10(seat)
        check.agree(
            f"bodies.kind_10_{name}_unsigned",
            e.unsigned(
                10,
                CHAIN_FIXTURE,
                e.SCHEME_IDENTITY,
                HUB_KEY,
                0,
                e.kind_10_body(IDENTITY, FIRST_SIGNER, seat, SIGNATURE),
                0,
                VALID_UNTIL,
            ),
            envelope.unsigned_bytes(transaction),
        )
        signed = envelope.signed_bytes(transaction, SIGNATURE)
        check.equal(
            f"bodies.kind_10_{name}_round_trips",
            envelope.decode_signed(signed)[0] == transaction,
        )
    transaction = _kind_23(SIGNATURE)
    check.agree(
        "bodies.kind_23_unsigned",
        e.unsigned(
            23,
            CHAIN_FIXTURE,
            e.SCHEME_SIGNER,
            SIGNER,
            4,
            e.kind_23_body(SEAT, MACHINE_KEY, BUILD_DIGEST, SIGNATURE, SIGNATURE),
            1_000,
            VALID_UNTIL,
        ),
        envelope.unsigned_bytes(transaction),
    )
    check.equal(
        "bodies.kind_23_round_trips",
        envelope.decode_signed(envelope.signed_bytes(transaction, SIGNATURE))[0]
        == transaction,
    )
    check.section(
        "Every other kind keeps version nine's shape, and kind 1 keeps the bytes "
        "version one accepted."
    )
    transfer = envelope.Transaction(
        kind=1,
        scheme=c.SCHEME_SIGNER,
        chain_id=CHAIN_FIXTURE,
        authority_public_key=SIGNER,
        nonce=4,
        body={"recipient_escrow_id": RECIPIENT, "amount_atomic": 9},
        fee_limit=1_000,
        valid_until_height=VALID_UNTIL,
    )
    check.equal(
        "bodies.kind_1_bytes_are_version_nines",
        envelope.unsigned_bytes(transfer) == v9envelope.unsigned_bytes(transfer),
    )
    check.equal(
        "bodies.version_nine_registration_is_malformed",
        _malformed(v9envelope.signed_bytes(_v9_registration(), SIGNATURE)),
    )


def _v9_registration() -> envelope.Transaction:
    return envelope.Transaction(
        kind=10,
        scheme=c.SCHEME_IDENTITY,
        chain_id=CHAIN_FIXTURE,
        authority_public_key=HUB_KEY,
        nonce=0,
        body={
            "hub_identity_hash": IDENTITY,
            "first_signer_public_key": FIRST_SIGNER,
            "verifier_signature": SIGNATURE,
        },
        fee_limit=0,
        valid_until_height=VALID_UNTIL,
    )


def _malformed(raw: bytes) -> bool:
    try:
        envelope.decode_signed(raw)
    except envelope.MalformedTransaction:
        return True
    return False


def check_messages(check: Checker) -> None:
    check.section(
        "The registration binds its attesting seat, so one machine's signature "
        "cannot be presented as another's."
    )
    for name, seat in (("launch", c.LAUNCH_ATTESTER), ("machine", SEAT)):
        check.agree(
            f"messages.registration_{name}",
            e.registration_message(
                CHAIN_FIXTURE, seat, IDENTITY, HUB_KEY, FIRST_SIGNER, VALID_UNTIL
            ),
            messages.registration_message(
                CHAIN_FIXTURE, seat, IDENTITY, HUB_KEY, FIRST_SIGNER, VALID_UNTIL
            ),
        )
    check.agree(
        "messages.attestation",
        e.attestation_message(CHAIN_FIXTURE, SEAT, MACHINE_KEY, BUILD_DIGEST, VALID_UNTIL),
        messages.attestation_message(
            CHAIN_FIXTURE, SEAT, MACHINE_KEY, BUILD_DIGEST, VALID_UNTIL
        ),
    )
    check.section(
        "The approval signs the whole unsigned transaction with its HUB field "
        "zero. So it is the same whatever the field holds, and different for "
        "every other change, the nonce included."
    )
    approved = _kind_19(SIGNATURE)
    check.agree(
        "messages.approval_kind_19",
        e.approval_message(
            e.unsigned(
                19,
                CHAIN_FIXTURE,
                e.SCHEME_SIGNER,
                SIGNER,
                4,
                e.kind_19_body(RECIPIENT, 9, NO_SIGNATURE),
                1_000,
                VALID_UNTIL,
            )
        ),
        messages.approval_message(approved),
    )
    check.agree(
        "messages.approval_kind_23",
        e.approval_message(
            e.unsigned(
                23,
                CHAIN_FIXTURE,
                e.SCHEME_SIGNER,
                SIGNER,
                4,
                e.kind_23_body(SEAT, MACHINE_KEY, BUILD_DIGEST, SIGNATURE, NO_SIGNATURE),
                1_000,
                VALID_UNTIL,
            )
        ),
        messages.approval_message(_kind_23(SIGNATURE)),
    )
    check.equal(
        "messages.approval_ignores_the_hub_field",
        messages.approval_message(approved)
        == messages.approval_message(_kind_19(NO_SIGNATURE)),
    )
    check.equal(
        "messages.approval_binds_the_nonce",
        messages.approval_message(approved)
        != messages.approval_message(_kind_19(SIGNATURE, nonce=5)),
    )
    check.equal(
        "messages.approval_binds_the_amount",
        messages.approval_message(approved)
        != messages.approval_message(
            replace(approved, body=approved.body | {"amount_atomic": 10})
        ),
    )
    check.equal(
        "messages.approval_is_not_the_envelope_message",
        messages.approval_message(approved)
        != envelope.signing_message(messages.approved_bytes(approved)),
    )


def check_lifetime(check: Checker) -> None:
    check.section(
        "An approval lives at most one slot above the executing height. A "
        "transaction with no HUB proof is not governed."
    )
    height = 50
    for name, transaction in (
        ("kind_19", _kind_19(SIGNATURE)),
        ("kind_23", _kind_23(SIGNATURE)),
        ("kind_10", _kind_10(SEAT)),
    ):
        at_bound = replace(transaction, valid_until_height=height + 1_200)
        past = replace(transaction, valid_until_height=height + 1_201)
        check.agree(
            f"lifetime.{name}_at_the_bound_is_accepted",
            not e.lifetime_exceeded(height + 1_200, height),
            not messages.approval_lifetime_exceeded(at_bound, height),
        )
        check.agree(
            f"lifetime.{name}_past_the_bound_is_refused",
            e.lifetime_exceeded(height + 1_201, height),
            messages.approval_lifetime_exceeded(past, height),
        )
    far = replace(_kind_19(NO_SIGNATURE), valid_until_height=10_000_000_000)
    check.equal(
        "lifetime.an_absent_field_is_not_governed",
        not messages.approval_lifetime_exceeded(far, height),
    )


def check_carryover(check: Checker) -> None:
    check.section(
        "Version nine's public surface is partitioned exactly into carried, "
        "revised, withdrawn, and replaced, and every carried constant is "
        "version nine's own object."
    )
    surface = {n for n in dir(v9c) if n.isupper() and not n.startswith("_")}
    declared = (
        set(c.CARRIED_FROM_V9)
        | set(c.REVISED_IN_V10)
        | set(c.WITHDRAWN_IN_V10)
        | set(c.REPLACED_DECLARATIONS)
    )
    check.equal("carryover.partition_is_exact", declared == surface)
    check.equal("carryover.carried", len(c.CARRIED_FROM_V9))
    check.equal("carryover.revised", len(c.REVISED_IN_V10))
    check.equal("carryover.withdrawn", ",".join(c.WITHDRAWN_IN_V10))
    check.equal(
        "carryover.carried_are_version_nines_objects",
        all(getattr(c, n) is getattr(v9c, n) for n in c.CARRIED_FROM_V9),
    )
    check.equal(
        "carryover.withdrawn_are_undefined",
        not any(hasattr(c, n) for n in c.WITHDRAWN_IN_V10),
    )
    check.equal(
        "carryover.unchanged_bodies_are_version_nines",
        all(
            c.BODY_BYTES[k] == v9c.BODY_BYTES[k]
            for k in v9c.BODY_BYTES
            if k != c.HUB_REGISTER
        ),
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
    check_non_collision(check)
    check_state_surface(check)
    check_bodies(check)
    check_messages(check)
    check_lifetime(check)
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
    print(f"economy-transition-v10: {check.checked} vectors checked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
