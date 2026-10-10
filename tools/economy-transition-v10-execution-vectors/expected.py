"""Independent derivations for the version-ten execution vectors.

**This module imports nothing from `simulation/`.** Every value is computed from
the specification's own statements: the field tables, the label strings, the
ordered rejection conditions, the registry step, and `hashlib`.

Two kinds of derivation live here:

- **encodings**, built field by field from the tables: genesis, receipts, the
  block header, the approval message, and the machine-key value;
- **outcomes**, read off the specification's ordered conditions by a small
  evaluator that is handed the facts a case was built to have. The model reaches
  the same outcome by executing the transaction against a ledger. A condition
  placed in the wrong order in either one fails the agreement.
"""

from __future__ import annotations

import hashlib

# --- the accepted framing ------------------------------------------------------

GENESIS_MAGIC = b"PSGN"
BLOCK_MAGIC = b"PSBL"
RECEIPT_MAGIC = b"PSRC"
TX_ID_LABEL = "protocol-stack:v1:tx-id"
TRANSACTION_TREE_PREFIX = "protocol-stack:v1:tx"
CHAIN_ID_LABEL = "protocol-stack:v10:chain-id"
BLOCK_ID_LABEL = "protocol-stack:v9:block-id"
APPROVAL_LABEL = "protocol-stack:v10:hub-approval"
MANIFEST_DIGEST_HEX = (
    "af153c99adf7c49e5a92563946cf0e60dfd7a58785462530988f661aa68faaa7"
)

SCHEMA_VERSION = 10
BLOCK_HEADER_SCHEMA_VERSION = 9
RECEIPT_VERSION = 10
GENESIS_PREFIX_BYTES = 182
BLOCK_HEADER_BYTES = 154
SIGNATURE_BYTES = 64
TRAILER_BYTES = 16
HUB_SIGNATURE_BYTES = 64

# --- the specification's constants ----------------------------------------------

CYCLE_BLOCKS = 28_800
SLOT_SECONDS = 3_600
SLOTS_PER_WINDOW = 24
ASSIGNMENT_LAG_WINDOWS = 2
ACTIVITY_THRESHOLD_SECONDS = 64_800
APPROVAL_LIFETIME_BLOCKS = 1_200
MACHINE_REGISTRATIONS_PER_WINDOW = 1_000
LAUNCH_RETIREMENT_ACTIVE_MACHINES = 100
MAX_SEAT_ID = 99_999
MINT_ACCUMULATION_CAP = 30
ISSUANCE_CYCLES_PER_SEAT = 731
VERIFIED_USER_DAILY_ATOMIC = 171_000_000

RESULT_CODE = {
    "SUCCESS": 0,
    "EXPIRED": 3,
    "NONCE_MISMATCH": 6,
    "UNAUTHORIZED": 9,
    "CYCLE_RANGE": 10,
    "REPLAY": 12,
    "SEAT_NOT_ACTIVATED": 13,
    "SEAT_NOT_PURCHASED": 14,
    "BIOMETRIC_REQUIRED": 22,
    "LAUNCH_KEY_RETIRED": 45,
    "MACHINE_KEY_NOT_FOUND": 46,
    "MACHINE_NOT_ACTIVE": 47,
    "REGISTRATION_LIMIT": 48,
    "APPROVAL_LIFETIME_EXCEEDED": 49,
}


# --- primitives -------------------------------------------------------------------


def be(value: int, width: int) -> bytes:
    return value.to_bytes(width, "big")


def label_prefix(label: str) -> bytes:
    encoded = label.encode("ascii")
    return bytes([len(encoded)]) + encoded


def digest(label: str, payload: bytes) -> bytes:
    return hashlib.sha256(label_prefix(label) + payload).digest()


# --- encodings --------------------------------------------------------------------


def genesis_bytes(
    network_id: int,
    genesis_timestamp: int,
    supply_limit: int,
    fixed_transfer_fee: int,
    launch_key: bytes,
    dispute_authority_key: bytes,
    build_authority_key: bytes,
) -> bytes:
    raw = bytearray(GENESIS_PREFIX_BYTES)
    raw[0:4] = GENESIS_MAGIC
    raw[4:6] = be(SCHEMA_VERSION, 2)
    raw[6:10] = be(network_id, 4)
    raw[10:18] = be(genesis_timestamp, 8)
    raw[18:26] = be(supply_limit, 8)
    raw[34:42] = be(fixed_transfer_fee, 8)
    raw[50:82] = bytes.fromhex(MANIFEST_DIGEST_HEX)
    raw[82:114] = launch_key
    raw[114:146] = dispute_authority_key
    raw[146:178] = build_authority_key
    return bytes(raw)


def transaction_id(raw: bytes) -> bytes:
    return digest(TX_ID_LABEL, raw)


def receipt_bytes(raw: bytes, kind: int, result: str, fee: int, issued: int) -> bytes:
    return (
        RECEIPT_MAGIC
        + be(RECEIPT_VERSION, 2)
        + transaction_id(raw)
        + be(kind, 1)
        + be(RESULT_CODE[result], 1)
        + be(fee, 8)
        + be(issued, 8)
    )


def approved_bytes(raw: bytes) -> bytes:
    """The unsigned transaction with its HUB field zero.

    In every body-carried kind the HUB field is the body's last 64 octets, so it
    sits immediately before the 16-octet trailer of the unsigned bytes.
    """
    unsigned = bytearray(raw[:-SIGNATURE_BYTES])
    end = len(unsigned) - TRAILER_BYTES
    unsigned[end - HUB_SIGNATURE_BYTES : end] = bytes(HUB_SIGNATURE_BYTES)
    return bytes(unsigned)


def hub_field(raw: bytes) -> bytes:
    end = len(raw) - SIGNATURE_BYTES - TRAILER_BYTES
    return raw[end - HUB_SIGNATURE_BYTES : end]


def approval_message(raw: bytes) -> bytes:
    return label_prefix(APPROVAL_LABEL) + approved_bytes(raw)


def machine_key_value(
    key: bytes,
    build_digest: bytes,
    registered_at_height: int,
    last_met_window: int,
    registration_window: int,
    registrations_in_window: int,
) -> bytes:
    return (
        key
        + build_digest
        + be(registered_at_height, 8)
        + be(last_met_window, 8)
        + be(registration_window, 8)
        + be(registrations_in_window, 4)
    )


def block_header(
    chain_id: bytes,
    height: int,
    timestamp: int,
    previous_state_root: bytes,
    transaction_root: bytes,
    resulting_state_root: bytes,
    transaction_count: int,
) -> bytes:
    return (
        BLOCK_MAGIC
        + be(BLOCK_HEADER_SCHEMA_VERSION, 2)
        + chain_id
        + be(height, 8)
        + be(timestamp, 8)
        + previous_state_root
        + transaction_root
        + resulting_state_root
        + be(transaction_count, 4)
    )


def tx_tree(ids: list[bytes]) -> bytes:
    if not ids:
        return digest(f"{TRANSACTION_TREE_PREFIX}-empty", b"")
    if len(ids) == 1:
        return digest(f"{TRANSACTION_TREE_PREFIX}-leaf", ids[0])
    split = 1
    while split * 2 < len(ids):
        split *= 2
    return digest(
        f"{TRANSACTION_TREE_PREFIX}-node", tx_tree(ids[:split]) + tx_tree(ids[split:])
    )


# --- windows ----------------------------------------------------------------------


def window_of_height(height: int) -> int:
    return height // CYCLE_BLOCKS


def first_cycle_window(activation_height: int) -> int:
    return activation_height // CYCLE_BLOCKS + 1


def assignment_height(window: int) -> int:
    """Window `w` is assigned in the prologue of the first height of `w + 2`."""
    return (window + ASSIGNMENT_LAG_WINDOWS) * CYCLE_BLOCKS


def met(credited_slots: int) -> bool:
    return credited_slots * SLOT_SECONDS >= ACTIVITY_THRESHOLD_SECONDS


def lifetime_exceeded(valid_until: int, height: int) -> bool:
    return valid_until > height + APPROVAL_LIFETIME_BLOCKS


# --- the registry step --------------------------------------------------------------


def active_count(
    due: int,
    machines: int,
    first_window: int,
    plan: dict[int, dict[int, int]],
) -> int:
    """How many machines the registry step counts at `due`'s assignment.

    A machine counts when its seat is in scope for `due` and its credited slots
    meet the threshold. No seat is in scope before `first_window`, so nothing
    is counted there, whatever marks the entries hold.
    """
    if due < first_window:
        return 0
    credited = plan.get(due, {})
    return sum(
        1 for seat in range(machines) if met(credited.get(seat, SLOTS_PER_WINDOW))
    )


def retirement_height(
    machines: int, first_window: int, plan: dict[int, dict[int, int]], last_due: int
) -> int | None:
    for due in range(0, last_due + 1):
        if active_count(due, machines, first_window, plan) >= (
            LAUNCH_RETIREMENT_ACTIVE_MACHINES
        ):
            return assignment_height(due)
    return None


# --- the ordered conditions ---------------------------------------------------------


def kind_23_outcome(
    *,
    seat_id: int,
    purchased: bool = True,
    activated: bool = True,
    owned: bool = True,
    key_held: bool = False,
    attested: bool = True,
    approval: bool | None = True,
) -> str:
    """The seven conditions in the specification's order. `approval` is None
    for 64 zero octets, and False for a signature that does not verify."""
    if seat_id > MAX_SEAT_ID:
        return "CYCLE_RANGE"
    if not purchased:
        return "SEAT_NOT_PURCHASED"
    if not activated:
        return "SEAT_NOT_ACTIVATED"
    if not owned:
        return "UNAUTHORIZED"
    if key_held:
        return "REPLAY"
    if not attested:
        return "UNAUTHORIZED"
    if approval is None:
        return "BIOMETRIC_REQUIRED"
    if not approval:
        return "UNAUTHORIZED"
    return "SUCCESS"


def kind_10_outcome(
    *,
    attester: int | str,
    beyond_lifetime: bool = False,
    identity_known: bool = False,
    signer_known: bool = False,
    retired: bool = False,
    signed: bool = True,
    has_key: bool = True,
    active: bool = True,
    count: int = 0,
) -> str:
    """`EXPIRED`, the lifetime, the two replays, then the attester's branch."""
    if beyond_lifetime:
        return "APPROVAL_LIFETIME_EXCEEDED"
    if identity_known or signer_known:
        return "REPLAY"
    if attester == "launch":
        if retired:
            return "LAUNCH_KEY_RETIRED"
        return "SUCCESS" if signed else "UNAUTHORIZED"
    assert isinstance(attester, int)
    if attester > MAX_SEAT_ID:
        return "CYCLE_RANGE"
    if not has_key:
        return "MACHINE_KEY_NOT_FOUND"
    if not active:
        return "MACHINE_NOT_ACTIVE"
    if not signed:
        return "UNAUTHORIZED"
    if count >= MACHINE_REGISTRATIONS_PER_WINDOW:
        return "REGISTRATION_LIMIT"
    return "SUCCESS"


def resubmission_outcome(*, nonce: int, stored: int, approval_matches: bool) -> str:
    """A re-presented approval: the nonce first, then whether it signed this
    transaction. A refused transaction never moves the nonce."""
    if nonce != stored + 1:
        return "NONCE_MISMATCH"
    return "SUCCESS" if approval_matches else "UNAUTHORIZED"
