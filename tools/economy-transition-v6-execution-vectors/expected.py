"""The independent derivation of the version-six execution trace's values.

Like every `expected.py` before it, this module **imports nothing from
`simulation/`**: every value it produces comes from the accepted documents or
from arithmetic over founder-directed figures, never from the model it checks.

**It reaches the unchanged constructions through version six's accepted
derivation rather than through a third transcription of them.** The digest, the
RFC 9162 tree, the state-root preimage, the receipt layout, the genesis layout,
the channel table, the base-permission legs, and the verified-user arithmetic
were all verified by the hosted matrix over 462 vectors. Copying them again to
add a block header would put a transcription risk into the one artifact whose
whole job is to be a second opinion.

**What is written here by hand is what execution defines for itself**: the
146-byte application block header and the block-ID construction, the ordered
transaction tree, the closed-form monetary outcome of each scenario, and the
table of which rejection condition fires for each labelled step. The last is a
reading of `docs/specifications/economy-transition-v6.md`'s rejection orders,
written against the fixture and never against the executor — so a model that
resolved conditions in a different order disagrees here rather than agreeing
with itself.

Two of the constructions are checked against a third source before anything
rests on them: the transaction tree against `protocol-primitives-v1.txt`'s
recorded `tx.root`, and the header and block ID against
`ledger-transition-v1.txt`'s recorded `block_header` and `block_id`.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_TOOLS = Path(__file__).resolve().parents[1]


def _load(name: str, directory: str):
    """Load a sibling derivation by path, because every one is named `expected`."""
    path = _TOOLS / directory / "expected.py"
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        raise ImportError(f"cannot load the accepted derivation from {path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


_v6 = _load("expected_v6_for_execution", "economy-transition-v6-vectors")
_v4 = _load("expected_v4_for_execution", "economy-transition-v4-vectors")

be = _v6.be
digest = _v6.digest
domain = _v6.domain
merkle = _v6.merkle
receipt_hex = _v6.receipt_hex
genesis_bytes = _v6.genesis_bytes
state_root_hex = _v6.state_root_hex
escrow_id = _v6.escrow_id
signer_id = _v6.signer_id
walk_range = _v6.walk_range
verified_user_daily_atomic = _v6.verified_user_daily_atomic
verified_user_collection = _v6.verified_user_collection
base_permission_legs = _v4.base_permission_legs
flat_unsigned_transfer = _v6.flat_unsigned_transfer
requires_confirmation = _v6.requires_confirmation
relaxes = _v6.relaxes
RESULT_CODES = _v6.RESULT_CODES
REFERRAL_LEG_ATOMIC = _v6.REFERRAL_LEG_ATOMIC
ADMISSION_CODES = _v6.ADMISSION_CODES
CYCLE_BLOCKS = _v6.CYCLE_BLOCKS
MINT_ACCUMULATION_CAP = _v6.MINT_ACCUMULATION_CAP
ASSIGNMENT_LAG_WINDOWS = _v6.ASSIGNMENT_LAG_WINDOWS
CHANNEL_ORDER = _v6.CHANNEL_ORDER
VERIFIED_USER_CHANNEL = _v6.VERIFIED_USER_CHANNEL
CHAIN_ID_LABEL = _v6.CHAIN_ID_LABEL
STATE_ROOT_LABEL = _v6.STATE_ROOT_LABEL
ECONOMY_TREE_PREFIX = _v6.ECONOMY_TREE_PREFIX
STATE_ROOT_SCHEMA_VERSION = _v6.STATE_ROOT_SCHEMA_VERSION

CODE_NUMBER = {name: number for number, name in RESULT_CODES.items()}

# --- what execution defines for itself -----------------------------------

# `protocol-primitives-v1` fixes the application block header and the ordered
# transaction tree, and version six imposes no narrower rule on either, so both
# are inherited unchanged — including the header's schema version of 1.
BLOCK_MAGIC = b"PSBL"
BLOCK_HEADER_SCHEMA_VERSION = 1
BLOCK_HEADER_FIELD_WIDTHS: tuple[int, ...] = (4, 2, 32, 8, 32, 32, 32, 4)
BLOCK_HEADER_BYTES = sum(BLOCK_HEADER_FIELD_WIDTHS)
BLOCK_ID_LABEL = "protocol-stack:v1:block-id"
TRANSACTION_TREE_PREFIX = "protocol-stack:v1:tx"

MAX_RAW_INPUTS = 65_535
MAX_ADMITTED = 65_535

# The frozen version-one devnet fee, usable from a version-six genesis for the
# first time: registration is fee-exempt and pays the entry airdrop, so the
# bootstrap gap version two had to leave open is closed for a participant.
FIXED_FEE = 1_000
REFERRAL_CHANNEL = CHANNEL_ORDER.index("founder_referral")
FOUNDER_OPERATOR_CHANNEL = CHANNEL_ORDER.index("founder_operator")


def block_header_bytes(
    chain_id: bytes,
    height: int,
    previous_state_root: bytes,
    transaction_root: bytes,
    resulting_state_root: bytes,
    transaction_count: int,
) -> bytes:
    """The 146-byte header, assembled from its own field-width table."""
    parts = [
        BLOCK_MAGIC,
        be(BLOCK_HEADER_SCHEMA_VERSION, 2),
        chain_id,
        be(height, 8),
        previous_state_root,
        transaction_root,
        resulting_state_root,
        be(transaction_count, 4),
    ]
    raw = b""
    for part, width in zip(parts, BLOCK_HEADER_FIELD_WIDTHS):
        if len(part) != width:
            raise ValueError("block header field is not its recorded width")
        raw += part
    if len(raw) != BLOCK_HEADER_BYTES:
        raise ValueError("block header is not 146 octets")
    return raw


def block_id_hex(header: bytes) -> str:
    return digest(BLOCK_ID_LABEL, header).hex()


def transaction_root_hex(admitted_ids: list[bytes]) -> str:
    """The ordered transaction tree, duplicates included."""
    return merkle(list(admitted_ids), TRANSACTION_TREE_PREFIX).hex()


def transaction_id_hex(signed: bytes) -> str:
    return digest("protocol-stack:v1:tx-id", signed).hex()


def signing_message(unsigned: bytes) -> bytes:
    return domain("protocol-stack:v1:tx-sign") + unsigned


def last_assigned_window(height: int) -> int | None:
    window = height // CYCLE_BLOCKS
    if window < ASSIGNMENT_LAG_WINDOWS:
        return None
    return window - ASSIGNMENT_LAG_WINDOWS


def entry_airdrop() -> int:
    return verified_user_daily_atomic()


def base_permission_total() -> int:
    return sum(base_permission_legs().values())


# --- the one-cycle settlement, derived from the winner rule ---------------


def one_cycle_shares(in_span: int, met: int) -> dict[str, int]:
    """What one cycle assigns when `met` of `in_span` seats meet it and one wins.

    Derived from the winner rule rather than from a walk: the seats that met the
    cycle accrue their own permission, and the permissions of the seats that did
    not are divided among the winners, so a single winner among `in_span` seats
    collects every permission the cycle assigned. The remainder each leg leaves
    is the carry, and with one winner every leg divides exactly.
    """
    if met < 1 or in_span < met:
        raise ValueError("the fixture assigns at least one met seat")
    winners = 1
    reallocated = in_span - met
    carry = sum(leg % winners for leg in base_permission_legs().values()) * reallocated
    return {
        "in_span": in_span,
        "met": met,
        "winners": winners,
        "reallocated": reallocated,
        "carry": carry,
        "collected_by_the_winner": in_span * base_permission_total(),
        "operator_leg": in_span * base_permission_legs()[FOUNDER_OPERATOR_CHANNEL],
    }


def custody_after_one_cycle(in_span: int) -> dict[int, int]:
    """The four institutional legs a single winner's mint moves into custody."""
    legs = base_permission_legs()
    return {channel: in_span * legs[channel] for channel in (1, 2, 3, 4)}


# --- the closed-form outcome of each scenario ----------------------------


def registration_totals(transfer: int, collected_windows: int) -> dict[str, int]:
    airdrop = entry_airdrop()
    collection = collected_windows * airdrop
    return {
        "registrations": 2,
        "total_supply": 2 * airdrop + collection,
        "fee_pool": 2 * FIXED_FEE,
        "alice_balance": airdrop - transfer - FIXED_FEE + collection - FIXED_FEE,
        "bob_balance": airdrop + transfer,
        "collection_atomic": collection,
    }


def millionth_totals(transfer: int) -> dict[str, int]:
    airdrop = entry_airdrop()
    return {
        "total_supply": airdrop,
        "fee_pool": FIXED_FEE,
        "alice_balance": airdrop - transfer - FIXED_FEE,
        "dave_balance": transfer,
    }


def recovery_totals(transfer: int) -> dict[str, int]:
    airdrop = entry_airdrop()
    return {
        "total_supply": 2 * airdrop,
        "fee_pool": 3 * FIXED_FEE,
        "maria_balance": airdrop - 3 * FIXED_FEE - transfer,
        "bob_balance": airdrop + transfer,
    }


def compatibility_totals(transfer: int) -> dict[str, int]:
    airdrop = entry_airdrop()
    return {
        "total_supply": 2 * airdrop,
        "fee_pool": 2 * FIXED_FEE,
        "sender_balance": airdrop - 2 * FIXED_FEE - transfer,
        "bob_balance": airdrop + transfer,
    }


def posture_totals(transfer: int) -> dict[str, int]:
    airdrop = entry_airdrop()
    return {
        "total_supply": 2 * airdrop,
        "fee_pool": 4 * FIXED_FEE,
        "alice_balance": airdrop - 4 * FIXED_FEE - transfer,
        "bob_balance": airdrop + transfer,
    }


def block_totals(in_span: int, referred: int) -> dict[str, int]:
    airdrop = entry_airdrop()
    cycle = one_cycle_shares(in_span, met=1)
    referral = referred * REFERRAL_LEG_ATOMIC
    return {
        "total_supply": 3 * airdrop + cycle["collected_by_the_winner"] + referral,
        "fee_pool": 6 * FIXED_FEE,
        "alice_balance": airdrop - 3 * FIXED_FEE + cycle["operator_leg"],
        "bob_balance": airdrop - FIXED_FEE + referral,
        "carol_balance": airdrop - 2 * FIXED_FEE,
        "node_mint_atomic": cycle["collected_by_the_winner"],
        "referral_mint_atomic": referral,
        "unreferred_pool_atomic": (in_span - referred) * REFERRAL_LEG_ATOMIC,
    }


# Genesis writes the ten channels, the ten carries, the verifier key, the empty
# unreferred pool, and the verified-user counter, and nothing else.
GENESIS_ECONOMY_ENTRIES = len(CHANNEL_ORDER) * 2 + 3


def economy_entry_count(
    identities: int = 0,
    escrows: int = 0,
    signers: int = 0,
    enrollments: int = 0,
    seats: int = 0,
    assignments: int = 0,
    referral_balances: int = 0,
    custody: int = 0,
    decisions: int = 0,
) -> int:
    """The size of the economy map, derived from what each transition writes."""
    return (
        GENESIS_ECONOMY_ENTRIES
        + identities
        + escrows
        + signers
        + enrollments
        + seats
        + assignments
        + referral_balances
        + custody
        + decisions
    )


# Admission classifies bytes before any state is read, so its refusals are
# numbered in their own space: admission `1` is `MALFORMED_TRANSACTION` while
# result `1` is `ZERO_AMOUNT`.
EXPECTED_ADMISSIONS: dict[str, tuple[int, str]] = {
    "a_retired_kind_byte": (1, "step 1: kind 9 is retired and permanently unassigned"),
    "a_foreign_chain_id": (2, "step 2: the chain ID is not the configured one"),
}


# --- which rejection condition fires, read from the specification ---------

# Each entry is `label -> (result, the condition the specification names)`.
# Written against the fixture and never against the executor, so a model that
# resolved conditions in a different order disagrees here.
EXPECTED_RESULTS: dict[str, tuple[str, str]] = {
    # registration
    "alice_registers": ("SUCCESS", "a fresh identity, a fresh signer key, a signed attestation"),
    "alice_registers_again": ("REPLAY", "kind 10 condition 1: the identity hash is already registered"),
    "bob_registers": ("SUCCESS", "a fresh identity, a fresh signer key, a signed attestation"),
    "carol_reuses_alices_signer_key": ("REPLAY", "kind 10 condition 2: the first signer key is already assigned"),
    "alice_transfers_unconfirmed": ("BIOMETRIC_REQUIRED", "kind 1 condition 3: the default posture confirms every amount"),
    "alice_transfers_confirmed": ("SUCCESS", "kind 19 carries the confirmation the posture requires"),
    "alice_transfers_to_an_unregistered_recipient": ("RECIPIENT_NOT_REGISTERED", "kind 1 condition 2: the recipient has no escrow entry"),
    "alice_collects_before_any_window_completes": ("NOTHING_TO_MINT", "kind 18 condition 4: no window has completed"),
    "alice_collects_thirty_windows": ("SUCCESS", "the accumulation cap bounds the collection at thirty windows"),
    "alice_collects_again_immediately": ("NOTHING_TO_MINT", "kind 18 condition 4: the mark is already the collectable end"),
    # the millionth user
    "alice_registers_inside_the_population": ("SUCCESS", "the enrollment population is not exhausted"),
    "dave_registers_past_the_population": ("SUCCESS", "registration is fee-exempt and succeeds with no airdrop"),
    "dave_collects_holding_nothing": ("INSUFFICIENT_BALANCE", "envelope check 8 precedes every kind condition"),
    "dave_transfers_holding_nothing": ("INSUFFICIENT_BALANCE", "envelope check 8: the escrow cannot cover amount plus fee"),
    "dave_sends_a_zero_amount_holding_nothing": ("INSUFFICIENT_BALANCE", "version one answers ZERO_AMOUNT; version six checks the envelope first"),
    "alice_funds_dave": ("SUCCESS", "kind 19 to a registered escrow"),
    "dave_collects_with_no_enrollment": ("NOT_ENROLLED", "kind 18 condition 3: no enrollment entry exists"),
    # recovery
    "maria_registers": ("SUCCESS", "a fresh identity, a fresh signer key, a signed attestation"),
    "maria_revokes_her_only_signer": ("SUCCESS", "kind 16 is authorized by the identity, not by the signer"),
    "the_revoked_key_still_tries_to_spend": ("SIGNER_NOT_FOUND", "resolution under scheme 1: the key has no signer entry"),
    "maria_assigns_a_new_signer": ("SUCCESS", "kind 15 is authorized by the HUB key and the named escrow pays"),
    "maria_spends_with_the_new_key": ("SUCCESS", "the new signer resolves the escrow that already held the value"),
    # compatibility
    "the_sender_registers": ("SUCCESS", "the accepted transfer's public key becomes a first signer"),
    "the_accepted_transfer": ("RECIPIENT_NOT_REGISTERED", "kind 1 condition 2, reached by the accepted 200 octets"),
    "the_sender_relaxes_its_posture": ("SUCCESS", "kind 17 relaxes and carries the HUB signature"),
    "the_same_transfer_to_a_registered_recipient": ("SUCCESS", "only the recipient field differs from the accepted bytes"),
    # posture
    "relax_the_slot_mask_unsigned": ("UNAUTHORIZED", "kind 17 condition 2: setting a clear mask bit relaxes"),
    "relax_the_slot_mask_signed": ("SUCCESS", "the relaxation carries the posture-relax signature"),
    "mixed_change_unsigned": ("UNAUTHORIZED", "raising the minimum relaxes even while the mask tightens"),
    "mixed_change_signed": ("SUCCESS", "the mixed change carries the posture-relax signature"),
    "transfer_below_the_minimum": ("SUCCESS", "the amount is below the posture's minimum"),
    "transfer_at_the_minimum": ("BIOMETRIC_REQUIRED", "the predicate is `amount >= minimum`, so the boundary confirms"),
    "tighten_signed": ("UNAUTHORIZED", "a tightening must carry 64 zero octets"),
    "tighten_unsigned": ("SUCCESS", "a tightening needs only the signer signature"),
    "tighten_to_the_same_posture": ("REPLAY", "kind 17 condition 1: the proposal equals the stored posture"),
    # the boundary block
    "carol_registers": ("SUCCESS", "a fresh identity, a fresh signer key, a signed attestation"),
    "alice_buys_seat_zero": ("SUCCESS", "a free seat, a referrer who is another identity, a signed purchase"),
    "carol_buys_seat_one": ("SUCCESS", "a free seat with no referrer"),
    "alice_activates_seat_zero": ("SUCCESS", "kind 3 is one-time and permanent"),
    "carol_activates_seat_one": ("SUCCESS", "kind 3 is one-time and permanent"),
    "alice_mints_immediately_after_activating": ("NOTHING_TO_MINT", "kind 4 condition 7: the fresh mark is above the last assigned window"),
    "alice_mints_unconfirmed": ("BIOMETRIC_REQUIRED", "kind 4 condition 8: the destination's posture confirms the total"),
    "alice_mints_confirmed": ("SUCCESS", "the walk covers the window the prologue just assigned"),
    "bob_mints_his_referral": ("SUCCESS", "the prologue accrued the referral before the transaction ran"),
    "alice_mints_again": ("NOTHING_TO_MINT", "kind 4 condition 7: the mark is now the last assigned window"),
}
