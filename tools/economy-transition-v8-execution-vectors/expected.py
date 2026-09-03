"""The independent derivation of the version-eight execution trace's values.

Like every `expected.py` before it, this module **imports nothing from
`simulation/`**: every value it produces comes from the accepted documents or
from arithmetic over founder-directed figures, never from the model it checks.

**It reaches unchanged constructions through the accepted derivations that
already verified them.** The digest, the RFC 9162 tree, the state-root preimage,
the base-permission legs, the settlement's steps 5 through 7, the mint walk, the
146-octet application block header, the block ID, and the ordered transaction
tree come from `economy-transition-v7-execution-vectors/expected.py`, which the
hosted matrix verified over 590 vectors. Selection, the two new state entries,
the dispute message, and the version-eight genesis field order come from
`economy-transition-v8-vectors/expected.py`, verified over 183. Transcribing
either again to change a schema version would put a transcription risk into the
one artifact whose whole job is to be a second opinion.

**What is written here by hand is what version eight's execution defines for
itself**: genesis under schema version 8, the receipt under version 8, and the
closed-form outcome of each recorded scenario — including the one claim the whole
version exists to support, that a cycle settled from measured evidence settles
exactly as version seven settles the same seats and uptimes.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_TOOLS = Path(__file__).resolve().parents[1]


def _load(directory: str, name: str):
    """Load a sibling derivation by path, because every one is named `expected`."""
    path = _TOOLS / directory / "expected.py"
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        raise ImportError(f"cannot load the accepted derivation at {path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


_v7x = _load("economy-transition-v7-execution-vectors", "expected_v7x_for_v8x")
_v8 = _load("economy-transition-v8-vectors", "expected_v8_for_execution")

# --- the constructions version eight inherits unchanged ----------------------

be = _v7x.be
digest = _v7x.digest
state_root_hex = _v7x.state_root_hex
block_header_bytes = _v7x.block_header_bytes
block_id_hex = _v7x.block_id_hex
transaction_root_hex = _v7x.transaction_root_hex
assign = _v7x.assign
collect = _v7x.collect
base_permission_legs = _v7x.base_permission_legs
base_permission_total = _v7x.base_permission_total
bitmap_bytes = _v7x.bitmap_bytes
cycle_assignment_value_hex = _v7x.cycle_assignment_value_hex
_economy_entry_count_v7 = _v7x.economy_entry_count
fee_pool_atomic = _v7x.fee_pool_atomic
leg_total = _v7x.leg_total

BLOCK_HEADER_SCHEMA_VERSION = _v7x.BLOCK_HEADER_SCHEMA_VERSION
BLOCK_HEADER_BYTES = _v7x.BLOCK_HEADER_BYTES
BLOCK_ID_LABEL = _v7x.BLOCK_ID_LABEL
TRANSACTION_TREE_PREFIX = _v7x.TRANSACTION_TREE_PREFIX
CHANNEL_ORDER = _v7x.CHANNEL_ORDER
REFERRAL_CHANNEL = _v7x.REFERRAL_CHANNEL
REFERRAL_LEG_ATOMIC = _v7x.REFERRAL_LEG_ATOMIC
FOUNDER_OPERATOR_CHANNEL = _v7x.FOUNDER_OPERATOR_CHANNEL
RECOVERY_POOL_LEGS = _v7x.RECOVERY_POOL_LEGS
MINT_ACCUMULATION_CAP = _v7x.MINT_ACCUMULATION_CAP
VERIFIED_USER_DAILY_ATOMIC = _v7x.VERIFIED_USER_DAILY_ATOMIC
FIXED_FEE = _v7x.FIXED_FEE
GENESIS_ECONOMY_ENTRIES = _v7x.GENESIS_ECONOMY_ENTRIES
TRANSFER_AMOUNT = _v7x.TRANSFER_AMOUNT
SUPPLY_LIMIT = _v7x.SUPPLY_LIMIT
CODE_NUMBER = dict(_v7x.CODE_NUMBER) | {
    name: number for number, name in _v8.ADDED_RESULT_CODES.items()
}

# --- what version eight is ---------------------------------------------------

CHAIN_ID_LABEL = _v8.CHAIN_ID_LABEL
STATE_ROOT_LABEL = _v8.STATE_ROOT_LABEL
ECONOMY_TREE_PREFIX = _v8.ECONOMY_TREE_PREFIX
STATE_ROOT_SCHEMA_VERSION = _v8.SCHEMA_VERSION
GENESIS_SCHEMA_VERSION = _v8.SCHEMA_VERSION
RECEIPT_VERSION = _v8.SCHEMA_VERSION
GENESIS_PREFIX_BYTES = _v8.GENESIS_PREFIX_BYTES
MANIFEST_DIGEST = _v7x.MANIFEST_DIGEST

CHALLENGE_RESPONSE = _v8.CHALLENGE_RESPONSE
FILE_DISPUTE = _v8.FILE_DISPUTE
OPEN_CHALLENGE_ENTRY = _v8.OPEN_CHALLENGE_ENTRY
SEAT_WINDOW_ENTRY = _v8.SEAT_WINDOW_ENTRY
CYCLE_BLOCKS = _v8.CYCLE_BLOCKS
SLOT_BLOCKS = _v8.SLOT_BLOCKS
SLOTS_PER_WINDOW = _v8.SLOTS_PER_WINDOW
SLOT_SECONDS = _v8.SLOT_SECONDS
RESPONSE_DEADLINE_BLOCKS = _v8.RESPONSE_DEADLINE_BLOCKS
CHALLENGE_PERIOD_BLOCKS = _v8.CHALLENGE_PERIOD_BLOCKS
DISPUTE_CAP_SLOTS_PER_SEAT = _v8.DISPUTE_CAP_SLOTS_PER_SEAT
ACTIVITY_THRESHOLD_SECONDS = _v8.ACTIVITY_THRESHOLD_SECONDS
ASSIGNMENT_LAG_WINDOWS = _v8.ASSIGNMENT_LAG_WINDOWS

all_slots_credited = _v8.all_slots_credited
credited_slots = _v8.credited_slots
uptime_seconds = _v8.uptime_seconds
first_cycle_window = _v8.first_cycle_window
is_selected = _v8.is_selected
is_challengeable_height = _v8.is_challengeable_height
slot_of_height = _v8.slot_of_height
open_challenge_key = _v8.open_challenge_key
seat_window_key = _v8.seat_window_key
seat_window_value = _v8.seat_window_value
dispute_message = _v8.dispute_message
genesis_bytes_v8 = _v8.genesis_bytes

# The sixteen kind numbers version eight admits: version seven's fourteen and
# the two this version adds.
KIND_NUMBERS = frozenset(_v7x.KIND_NUMBERS | {CHALLENGE_RESPONSE, FILE_DISPUTE})

# The receipt's own field widths, written here because the version field is what
# version eight changes and a re-export would carry version seven's along.
RECEIPT_FIELD_WIDTHS: tuple[int, ...] = (4, 2, 32, 1, 1, 8, 8)
RECEIPT_BYTES = sum(RECEIPT_FIELD_WIDTHS)

# --- the trace's own fixture, restated so nothing is read from the model -----

NETWORK_ID = 8
ALICE_SEAT = 0
BOB_SEAT = 1
MEASURED_WINDOW = 1
ACTIVATION_HEIGHT = CYCLE_BLOCKS - 10
ASSIGNMENT_HEIGHT = (MEASURED_WINDOW + ASSIGNMENT_LAG_WINDOWS) * CYCLE_BLOCKS
DISPUTE_HEIGHT = (MEASURED_WINDOW + 1) * CYCLE_BLOCKS + 100


def economy_entry_count(
    open_challenges: int = 0, window_records: int = 0, **carried: int
) -> int:
    """Version seven's shape with the two entry kinds version eight can write.

    Neither is written at genesis and neither is written by any carried
    transition, so the floor is unchanged and the two terms are additive: a
    chain that never audits anybody has exactly version seven's economy map.
    """
    return _economy_entry_count_v7(**carried) + open_challenges + window_records


def genesis_bytes(
    network_id: int,
    supply_limit: int,
    fixed_fee: int,
    manifest_digest: bytes,
    verifier_key: bytes,
    dispute_authority_key: bytes,
) -> bytes:
    """Version-eight genesis: version seven's fields with one 32-octet key added.

    Total supply, the initial fee pool, and the account count are all zero, which
    version eight requires rather than merely expects.
    """
    raw = genesis_bytes_v8(
        b"PSGN", GENESIS_SCHEMA_VERSION, network_id, supply_limit, 0,
        fixed_fee, 0, manifest_digest, verifier_key, dispute_authority_key, 0,
    )
    if len(raw) != GENESIS_PREFIX_BYTES:
        raise ValueError("genesis prefix is not 142 octets")
    return raw


def chain_id(raw: bytes) -> bytes:
    return digest(CHAIN_ID_LABEL, raw)


def receipt_hex(
    transaction_id: bytes, kind: int, code: int, fee: int, issued: int
) -> str:
    """The 56-octet version-eight receipt, built from its own field-width table."""
    parts = [b"PSRC", be(RECEIPT_VERSION, 2), transaction_id, be(kind, 1),
             be(code, 1), be(fee, 8), be(issued, 8)]
    raw = b""
    for part, width in zip(parts, RECEIPT_FIELD_WIDTHS):
        if len(part) != width:
            raise ValueError("receipt field is not its recorded width")
        raw += part
    return raw.hex()


# --- the closed-form outcome of the measured window --------------------------


def measured_seats(bob_credited_slots: int) -> list[dict]:
    """The window-1 schedule the chain should have derived, stated by hand.

    Alice answered every challenge, so her record is absent and she reads as
    fully credited. Bob answered none, so his credit is whatever survived his
    expiries — **the one number this derivation takes from the run**, because it
    is the outcome of a selection sequence no closed form reproduces. Everything
    the assignment does with it is derived here.
    """
    return [
        {
            "seat_id": ALICE_SEAT,
            "uptime": SLOTS_PER_WINDOW * SLOT_SECONDS,
            "in_span": True,
            "window": MEASURED_WINDOW,
            "mark": 0,
        },
        {
            "seat_id": BOB_SEAT,
            "uptime": bob_credited_slots * SLOT_SECONDS,
            "in_span": True,
            "window": MEASURED_WINDOW,
            "mark": 0,
        },
    ]


def measured_assignment(bob_credited_slots: int) -> dict:
    """Version *seven's* settlement over the derived seats.

    This is the whole carryover claim and it is checked against the accepted
    version-seven derivation rather than against version eight's own model: if
    the carrier had changed a settlement, this arithmetic and the run would
    disagree.
    """
    empty = {channel: 0 for channel in RECOVERY_POOL_LEGS}
    return assign(measured_seats(bob_credited_slots), empty)


def measured_totals(bob_credited_slots: int) -> dict[str, object]:
    """What the measured chain holds once Alice has minted her measured cycle.

    Two registrations airdrop; Alice collects her own permission and the one Bob
    failed to earn, and the referral leg Bob's purchase accrued to her. Bob is in
    span, so his permission is generated and reallocated rather than never
    created — which is the difference between a failed cycle and an absent seat.
    """
    outcome = measured_assignment(bob_credited_slots)
    minted = (len(outcome["accrued"]) + outcome["reallocated"]) * base_permission_total()
    return {
        "winners": outcome["winners"],
        "accrued": outcome["accrued"],
        "reallocated": outcome["reallocated"],
        "assigned_permissions": len(outcome["contributing"]),
        "alice_minted_atomic": minted,
        "alice_referral_atomic": REFERRAL_LEG_ATOMIC,
        "unreferred_pool_atomic": REFERRAL_LEG_ATOMIC,
        "pool_after": outcome["pool_after"],
        "total_supply": 2 * VERIFIED_USER_DAILY_ATOMIC + minted + REFERRAL_LEG_ATOMIC,
    }


# --- the closed-form outcome of the disputed window --------------------------


def disputed_seats(disputed_bits: int) -> list[dict]:
    """Two perfect machines, one of which has had `disputed_bits` slots voided."""
    credit = credited_slots(all_slots_credited(), (1 << disputed_bits) - 1)
    return [
        {
            "seat_id": ALICE_SEAT,
            "uptime": credit * SLOT_SECONDS,
            "in_span": True,
            "window": MEASURED_WINDOW,
            "mark": 0,
        },
        {
            "seat_id": BOB_SEAT,
            "uptime": SLOTS_PER_WINDOW * SLOT_SECONDS,
            "in_span": True,
            "window": MEASURED_WINDOW,
            "mark": 0,
        },
    ]


def disputed_winners(disputed_bits: int) -> tuple[int, ...]:
    empty = {channel: 0 for channel in RECOVERY_POOL_LEGS}
    return assign(disputed_seats(disputed_bits), empty)["winners"]


def containment_uptime_seconds() -> int:
    """What a fully credited seat keeps after a maximal dispute, in seconds.

    `uptime-measurement-v1`'s containment theorem, restated over the encoded
    bitmaps: twenty-four slots less the six-slot cap is eighteen slots, which at
    one hour per slot is exactly the founder-directed activity threshold. The
    equality is the theorem's margin, and it is zero.
    """
    return (SLOTS_PER_WINDOW - DISPUTE_CAP_SLOTS_PER_SEAT) * SLOT_SECONDS


# --- what each labelled step should do, and why ------------------------------

EXPECTED_RESULTS: dict[str, tuple[str, str]] = {
    "alice_registers": ("SUCCESS", "the verifier signed it and no identity exists yet"),
    "bob_registers": ("SUCCESS", "the same, for a second person"),
    "alice_purchases": ("SUCCESS", "a free seat, signed by the owning identity"),
    "bob_purchases": ("SUCCESS", "the same, naming Alice's escrow as the referrer"),
    "bob_purchases_a_seat_he_never_runs": (
        "SUCCESS",
        "a seat may be bought and never activated; it is then in no window's "
        "scope and the issue step must never audit it",
    ),
    "alice_activates": ("SUCCESS", "a purchased seat, activated once"),
    "bob_activates": ("SUCCESS", "the same"),
    # Scenario measured.
    "alice_mints_her_measured_cycle": (
        "SUCCESS",
        "window one was assigned from evidence the chain recorded, and Alice holds "
        "the only accrued bit in it",
    ),
    "bob_mints_and_receives_nothing": (
        "SUCCESS",
        "the walk range is non-empty so the mint succeeds; Bob failed the measured "
        "cycle, holds no accrued bit, collects nothing, and still pays the fee",
    ),
    "bob_mints_again": (
        "NOTHING_TO_MINT",
        "the first attempt advanced the mark to the last assigned window, so the "
        "walk range is now empty",
    ),
    "alice_mints_her_referral_leg": (
        "SUCCESS",
        "Bob's seat is in span and names Alice, so one referral leg accrued to her",
    ),
    # Scenario disputed. Six accepted voids and four refusals, one for each of
    # the conditions a relayed dispute can fail on this chain.
    **{
        f"dispute_voids_alice_slot_{slot}": (
            "SUCCESS",
            "a closed window, a credited slot, an authority signature over this "
            "exact message, and a disputed bitmap still under the cap",
        )
        for slot in range(DISPUTE_CAP_SLOTS_PER_SEAT)
    },
    "dispute_past_the_cap": (
        "DISPUTE_CAP_EXCEEDED",
        "the disputed bitmap already holds the founder-directed grace allowance, "
        "which is what stops an authority failing a machine that was operational",
    ),
    "dispute_replayed_on_a_voided_slot": (
        "DISPUTE_REPLAY",
        "the slot's bit is already set in the disputed bitmap, which is the code "
        "that folding the two bitmaps into one would make unreachable",
    ),
    "dispute_from_an_unrecognised_authority": (
        "UNAUTHORIZED_DISPUTE",
        "the signature does not verify against the recorded dispute authority key, "
        "and it is checked before anything else is read",
    ),
    "dispute_of_a_window_still_open": (
        "WINDOW_NOT_CLOSED",
        "a window is disputable only once the executing height has left it",
    ),
    # Scenario deadline.
    "response_in_the_issuing_block": (
        "CHALLENGE_NOT_OPEN",
        "the challenge height is the executing height, and condition 6 precedes "
        "the issuance check, so the report is that it is not open rather than "
        "that it was never issued",
    ),
    # Scenario carried. Version six's rejection orders, unchanged, over a
    # version-eight state.
    "alice_transfers_unconfirmed": (
        "BIOMETRIC_REQUIRED",
        "the opening posture requires a confirmation at every amount",
    ),
    "alice_transfers_confirmed": ("SUCCESS", "the same transfer, with the proof"),
    "alice_transfers_to_an_unregistered_recipient": (
        "RECIPIENT_NOT_REGISTERED",
        "a transfer's destination must be an escrow the chain knows",
    ),
    "alice_attempts_a_direct_issue": (
        "UNAUTHORIZED",
        "no direct decision entry authorizes it",
    ),
    "alice_creates_a_second_escrow": ("SUCCESS", "the identity is its own admin"),
    "alice_deletes_the_second_escrow": ("SUCCESS", "an empty escrow, paid for by another"),
    "alice_assigns_a_fresh_signer": ("SUCCESS", "an unused key on an owned escrow"),
    "alice_revokes_the_fresh_signer": ("SUCCESS", "the signer it just assigned"),
    "alice_relaxes_without_a_signature": (
        "UNAUTHORIZED",
        "a relaxation needs the identity's own proof",
    ),
    "alice_relaxes_her_posture": ("SUCCESS", "the same change, with the proof"),
    "alice_tightens_her_posture": ("SUCCESS", "a tightening needs no proof"),
    "alice_repeats_the_posture_she_holds": (
        "REPLAY",
        "a posture change that changes nothing is refused",
    ),
    "alice_collects_thirty_windows": (
        "SUCCESS",
        "forty windows since enrolment, capped at thirty",
    ),
    "alice_collects_again_immediately": (
        "NOTHING_TO_MINT",
        "the mark has reached the executing window",
    ),
}

EXPECTED_ADMISSIONS: dict[str, tuple[int, str]] = {}

# The two kinds that charge no fee on success. A challenge response joins the
# registration on the founder answer of 2026-09-02.
FEE_EXEMPT_LABELS = frozenset({"alice_registers", "bob_registers"})
FEE_EXEMPT_KINDS = frozenset({10, CHALLENGE_RESPONSE})


def issued_by_label(scenario: str, bob_credited_slots: int = 0) -> dict[str, int]:
    """What each successful step issues, derived rather than read back."""
    airdrop = VERIFIED_USER_DAILY_ATOMIC
    issued = {"alice_registers": airdrop, "bob_registers": airdrop}
    if scenario == "measured":
        totals = measured_totals(bob_credited_slots)
        issued["alice_mints_her_measured_cycle"] = totals["alice_minted_atomic"]
        issued["bob_mints_and_receives_nothing"] = 0
        issued["alice_mints_her_referral_leg"] = totals["alice_referral_atomic"]
    if scenario == "carried":
        issued["alice_collects_thirty_windows"] = (
            MINT_ACCUMULATION_CAP * VERIFIED_USER_DAILY_ATOMIC
        )
    return issued
