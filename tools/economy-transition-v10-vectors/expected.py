"""Independent derivations for the version-ten contract vectors.

**This module imports nothing from `simulation/`.** Every value is computed from
the specification's own statements: the field tables, the label strings, the
offsets, and `hashlib`. A vector it agrees with the model about is evidence,
not one implementation restating itself.

**Byte strings are built field by field from the tables**, where the model
builds them by composing version nine's encoders. A field placed at the wrong
offset in either one fails the agreement.
"""

from __future__ import annotations

import hashlib

# --- the accepted framing, from `protocol-primitives-v1` and version six -----

TRANSACTION_MAGIC = b"PSTX"
GENESIS_MAGIC = b"PSGN"
ENVELOPE_SCHEMA_VERSION = 1
SIGN_LABEL = "protocol-stack:v1:tx-sign"
HEADER_BYTES = 80
TRAILER_BYTES = 16
SIGNATURE_BYTES = 64
HUB_SIGNATURE_BYTES = 64
SCHEME_SIGNER = 1
SCHEME_IDENTITY = 2
MAX_OBJECT_BYTES = 1_048_576
ACCOUNT_ENTRY_BYTES = 48
VERIFIER_KEY_ENTRY = 8
MANIFEST_DIGEST_HEX = (
    "af153c99adf7c49e5a92563946cf0e60dfd7a58785462530988f661aa68faaa7"
)

# --- version ten's identity ----------------------------------------------------

CHAIN_ID_LABEL = "protocol-stack:v10:chain-id"
STATE_ROOT_LABEL = "protocol-stack:v10:state-root"
ECONOMY_TREE_PREFIX = "protocol-stack:v10:economy"
BLOCK_ID_LABEL = "protocol-stack:v9:block-id"
REGISTRATION_LABEL = "protocol-stack:v10:hub-registration"
APPROVAL_LABEL = "protocol-stack:v10:hub-approval"
ATTESTATION_LABEL = "protocol-stack:v10:machine-attestation"

SCHEMA_VERSION = 10
BLOCK_HEADER_SCHEMA_VERSION = 9
RECEIPT_VERSION = 10

# --- the specification's constants table ---------------------------------------

LAUNCH_RETIREMENT_ACTIVE_MACHINES = 100
MACHINE_REGISTRATIONS_PER_WINDOW = 1_000
APPROVAL_LIFETIME_BLOCKS = 1_200
LAUNCH_ATTESTER = 4_294_967_295
ACTIVITY_THRESHOLD_SECONDS = 64_800
GENESIS_PREFIX_BYTES = 182

ADDED_RESULT_CODES = {
    45: "LAUNCH_KEY_RETIRED",
    46: "MACHINE_KEY_NOT_FOUND",
    47: "MACHINE_NOT_ACTIVE",
    48: "REGISTRATION_LIMIT",
    49: "APPROVAL_LIFETIME_EXCEEDED",
}
RESULT_CODE_COUNT = 50

# Kind, entry, key bytes, and value bytes, from the specification's tables.
ADDED_ENTRIES = {
    24: ("machine_key", 5, 92),
    25: ("launch_retirement", 1, 8),
    26: ("machine_key_owner", 33, 4),
}

KIND_10_BODY_BYTES = 32 + 32 + 4 + 64
KIND_23_BODY_BYTES = 4 + 32 + 32 + 64 + 64

APPROVAL_KINDS = (2, 3, 4, 5, 17, 18, 19, 22, 23)
ALWAYS_PROVEN_KINDS = (10, 13, 14, 15, 16, 23)


# --- primitives ------------------------------------------------------------------


def be(value: int, width: int) -> bytes:
    return value.to_bytes(width, "big")


def label_prefix(label: str) -> bytes:
    """`D(L) = u8(byte_length(L)) || ascii(L)`, the accepted separator."""
    encoded = label.encode("ascii")
    return bytes([len(encoded)]) + encoded


def digest(label: str, payload: bytes) -> bytes:
    return hashlib.sha256(label_prefix(label) + payload).digest()


def account_bound() -> int:
    return (MAX_OBJECT_BYTES - GENESIS_PREFIX_BYTES) // ACCOUNT_ENTRY_BYTES


# --- genesis ---------------------------------------------------------------------


def genesis_bytes(
    network_id: int,
    genesis_timestamp: int,
    supply_limit: int,
    fixed_transfer_fee: int,
    launch_key: bytes,
    dispute_authority_key: bytes,
    build_authority_key: bytes,
) -> bytes:
    """The version-ten field table, offset by offset."""
    raw = bytearray(GENESIS_PREFIX_BYTES)
    raw[0:4] = GENESIS_MAGIC
    raw[4:6] = be(SCHEMA_VERSION, 2)
    raw[6:10] = be(network_id, 4)
    raw[10:18] = be(genesis_timestamp, 8)
    raw[18:26] = be(supply_limit, 8)
    raw[26:34] = be(0, 8)
    raw[34:42] = be(fixed_transfer_fee, 8)
    raw[42:50] = be(0, 8)
    raw[50:82] = bytes.fromhex(MANIFEST_DIGEST_HEX)
    raw[82:114] = launch_key
    raw[114:146] = dispute_authority_key
    raw[146:178] = build_authority_key
    raw[178:182] = be(0, 4)
    return bytes(raw)


def chain_id(genesis: bytes) -> bytes:
    return digest(CHAIN_ID_LABEL, genesis)


# --- the three new entries ---------------------------------------------------------


def machine_key_key(seat_id: int) -> bytes:
    return bytes([24]) + be(seat_id, 4)


def machine_key_value(
    machine_public_key: bytes,
    build_digest: bytes,
    registered_at_height: int,
    last_met_window: int,
    registration_window: int,
    registrations_in_window: int,
) -> bytes:
    raw = bytearray(92)
    raw[0:32] = machine_public_key
    raw[32:64] = build_digest
    raw[64:72] = be(registered_at_height, 8)
    raw[72:80] = be(last_met_window, 8)
    raw[80:88] = be(registration_window, 8)
    raw[88:92] = be(registrations_in_window, 4)
    return bytes(raw)


def launch_retirement_key() -> bytes:
    return bytes([25])


def launch_retirement_value(height: int) -> bytes:
    return be(height, 8)


def machine_key_owner_key(machine_public_key: bytes) -> bytes:
    return bytes([26]) + machine_public_key


def machine_key_owner_value(seat_id: int) -> bytes:
    return be(seat_id, 4)


# --- the three signed constructions ----------------------------------------------


def registration_message(
    chain: bytes,
    attesting_seat_id: int,
    identity: bytes,
    hub_key: bytes,
    first_signer: bytes,
    valid_until: int,
) -> bytes:
    return (
        label_prefix(REGISTRATION_LABEL)
        + chain
        + be(attesting_seat_id, 4)
        + identity
        + hub_key
        + first_signer
        + be(valid_until, 8)
    )


def attestation_message(
    chain: bytes, seat_id: int, key: bytes, build: bytes, valid_until: int
) -> bytes:
    return (
        label_prefix(ATTESTATION_LABEL)
        + chain
        + be(seat_id, 4)
        + key
        + build
        + be(valid_until, 8)
    )


# --- transactions, built from the header and body tables --------------------------


def unsigned(
    kind: int,
    chain: bytes,
    scheme: int,
    authority: bytes,
    nonce: int,
    body: bytes,
    fee_limit: int,
    valid_until: int,
) -> bytes:
    header = bytearray(HEADER_BYTES)
    header[0:4] = TRANSACTION_MAGIC
    header[4:6] = be(ENVELOPE_SCHEMA_VERSION, 2)
    header[6] = kind
    header[7:39] = chain
    header[39] = scheme
    header[40:72] = authority
    header[72:80] = be(nonce, 8)
    return bytes(header) + body + be(fee_limit, 8) + be(valid_until, 8)


def kind_10_body(
    identity: bytes, first_signer: bytes, attesting_seat_id: int, attestation: bytes
) -> bytes:
    return identity + first_signer + be(attesting_seat_id, 4) + attestation


def kind_23_body(
    seat_id: int, key: bytes, build: bytes, attestation: bytes, hub: bytes
) -> bytes:
    return be(seat_id, 4) + key + build + attestation + hub


def kind_19_body(recipient: bytes, amount: int, hub: bytes) -> bytes:
    return recipient + be(amount, 8) + hub


def approval_message(unsigned_with_zero_hub: bytes) -> bytes:
    """`D(approval label) || approved_bytes`. The caller supplies the unsigned
    transaction already built with its HUB field zero, from the body table."""
    return label_prefix(APPROVAL_LABEL) + unsigned_with_zero_hub


def lifetime_exceeded(valid_until: int, height: int) -> bool:
    return valid_until > height + APPROVAL_LIFETIME_BLOCKS
