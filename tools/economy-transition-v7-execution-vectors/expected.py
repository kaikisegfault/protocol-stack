"""The independent derivation of the version-seven execution trace's values.

Like every `expected.py` before it, this module **imports nothing from
`simulation/`**: every value it produces comes from the accepted documents or
from arithmetic over founder-directed figures, never from the model it checks.

**It reaches unchanged constructions through the accepted derivations that
already verified them.** The digest, the RFC 9162 tree, the state-root preimage,
the channel table, the base-permission legs, the escrow and signer derivations,
the settlement's steps 5 through 7, and the mint walk with version seven's added
term come from `economy-transition-v7-vectors/expected.py`, which the hosted
matrix verified over 395 vectors. The 146-byte application block header, the
block ID, and the ordered transaction tree come from
`economy-transition-v6-execution-vectors/expected.py`, which it verified over
512. Transcribing either again to change a schema version would put a
transcription risk into the one artifact whose whole job is to be a second
opinion.

**What is written here by hand is what version seven's execution defines for
itself**: genesis under schema version 7, the receipt under version 7, and the
closed-form monetary outcome of each recorded scenario. The last is arithmetic
over the manifest's legs, written against the fixture and never against the
executor, so a model that settled a cycle differently disagrees here rather than
agreeing with itself.
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


_v7 = _load("economy-transition-v7-vectors", "expected_v7_for_execution")
_v6x = _load("economy-transition-v6-execution-vectors", "expected_v6x_for_v7")

# --- the settlement and the commitments, from the accepted derivations -------

be = _v6x.be
digest = _v6x.digest
merkle = _v6x.merkle
escrow_id = _v6x.escrow_id
signer_id = _v6x.signer_id
state_root_hex = _v6x.state_root_hex
base_permission_legs = _v7.base_permission_legs
assign = _v7.assign
collect = _v7.collect
bitmap_bytes = _v7.bitmap_bytes

CHANNEL_ORDER = _v6x.CHANNEL_ORDER
REFERRAL_CHANNEL = _v6x.REFERRAL_CHANNEL
FOUNDER_OPERATOR_CHANNEL = _v6x.FOUNDER_OPERATOR_CHANNEL
VERIFIED_USER_CHANNEL = _v6x.VERIFIED_USER_CHANNEL
REFERRAL_LEG_ATOMIC = _v6x.REFERRAL_LEG_ATOMIC
CYCLE_BLOCKS = _v6x.CYCLE_BLOCKS
ASSIGNMENT_LAG_WINDOWS = _v6x.ASSIGNMENT_LAG_WINDOWS
MINT_ACCUMULATION_CAP = _v6x.MINT_ACCUMULATION_CAP
RESULT_CODES = _v6x.RESULT_CODES
CODE_NUMBER = _v6x.CODE_NUMBER
FIXED_FEE = _v6x.FIXED_FEE

# --- the block layer, inherited from version one -----------------------------

BLOCK_HEADER_SCHEMA_VERSION = _v6x.BLOCK_HEADER_SCHEMA_VERSION
BLOCK_HEADER_BYTES = _v6x.BLOCK_HEADER_BYTES
BLOCK_ID_LABEL = _v6x.BLOCK_ID_LABEL
TRANSACTION_TREE_PREFIX = _v6x.TRANSACTION_TREE_PREFIX
block_header_bytes = _v6x.block_header_bytes
block_id_hex = _v6x.block_id_hex
transaction_root_hex = _v6x.transaction_root_hex

# --- what version seven re-versions ------------------------------------------

CHAIN_ID_LABEL = _v7.CHAIN_ID_LABEL
STATE_ROOT_LABEL = _v7.STATE_ROOT_LABEL
ECONOMY_TREE_PREFIX = _v7.ECONOMY_TREE_PREFIX
STATE_ROOT_SCHEMA_VERSION = _v7.STATE_ROOT_SCHEMA_VERSION
GENESIS_SCHEMA_VERSION = _v7.GENESIS_SCHEMA_VERSION
RECEIPT_VERSION = _v7.RECEIPT_VERSION
MANIFEST_DIGEST = _v7.MANIFEST_DIGEST
RECOVERY_POOL_ENTRY = _v7.RECOVERY_POOL_ENTRY
RECOVERY_POOL_LEGS = _v7.RECOVERY_POOL_LEGS
CYCLE_ASSIGNMENT_ENTRY = 3
CHANNEL_ENTRY = 2
GENESIS_FIELD_WIDTHS = _v7.GENESIS_FIELD_WIDTHS
GENESIS_PREFIX_BYTES = _v7.GENESIS_PREFIX_BYTES

# The receipt's own field widths, written here because the version field is what
# version seven changes and a re-export would carry version six's along with it.
RECEIPT_FIELD_WIDTHS: tuple[int, ...] = (4, 2, 32, 1, 1, 8, 8)
RECEIPT_BYTES = sum(RECEIPT_FIELD_WIDTHS)

# The trace's own fixture figures, restated so the arithmetic below never reads
# them from the model.
NETWORK_ID = 7
SUPPLY_LIMIT = 5_699_395_010_000_000_000
VERIFIED_USER_DAILY_ATOMIC = _v6x.verified_user_daily_atomic()
GENESIS_ECONOMY_ENTRIES = 14


def genesis_bytes(
    network_id: int,
    supply_limit: int,
    fixed_fee: int,
    manifest_digest: bytes,
    verifier_key: bytes,
) -> bytes:
    """Version-seven genesis built from its own field-width table.

    The field order is version six's and the schema version is not. Total supply,
    the initial fee pool, and the account count are all zero, which version seven
    requires rather than merely expects.
    """
    parts = [b"PSGN", be(GENESIS_SCHEMA_VERSION, 2), be(network_id, 4),
             be(supply_limit, 8), be(0, 8), be(fixed_fee, 8), be(0, 8),
             manifest_digest, verifier_key, be(0, 4)]
    raw = b""
    for part, width in zip(parts, GENESIS_FIELD_WIDTHS):
        if len(part) != width:
            raise ValueError("genesis field is not its recorded width")
        raw += part
    return raw


def chain_id(genesis: bytes) -> bytes:
    return digest(CHAIN_ID_LABEL, genesis)


def receipt_hex(
    transaction_id: bytes, kind: int, code: int, fee: int, issued: int
) -> str:
    """The 56-byte version-seven receipt, built from its own field-width table."""
    parts = [b"PSRC", be(RECEIPT_VERSION, 2), transaction_id, be(kind, 1),
             be(code, 1), be(fee, 8), be(issued, 8)]
    raw = b""
    for part, width in zip(parts, RECEIPT_FIELD_WIDTHS):
        if len(part) != width:
            raise ValueError("receipt field is not its recorded width")
        raw += part
    return raw.hex()


def recovery_pool_value_hex(legs: dict[int, int]) -> str:
    """Five `u64` amounts in channel order 0 through 4."""
    return b"".join(be(legs[channel], 8) for channel in RECOVERY_POOL_LEGS).hex()


def cycle_assignment_value_hex(
    share_per_winner: int,
    reallocated: int,
    winner_count: int,
    in_scope: int,
    bitmap_bits: int,
    absorbed: dict[int, int],
    accrued_seats: tuple[int, ...],
    winner_seats: tuple[int, ...],
) -> str:
    """The 64-octet fixed part and the two bitmaps, in the specified order."""
    fixed = (
        be(share_per_winner, 8)
        + be(reallocated, 4)
        + be(winner_count, 4)
        + be(in_scope, 4)
        + be(bitmap_bits, 4)
        + b"".join(be(absorbed[channel], 8) for channel in RECOVERY_POOL_LEGS)
    )
    return (fixed + _bitmap(accrued_seats, bitmap_bits)
            + _bitmap(winner_seats, bitmap_bits)).hex()


def _bitmap(seats: tuple[int, ...], bits: int) -> bytes:
    raw = bytearray(bitmap_bytes(bits))
    for seat in seats:
        raw[seat // 8] |= 1 << (7 - seat % 8)
    return bytes(raw)


# --- the closed-form outcome of each recorded scenario ------------------------


def leg_total(multiple: int) -> dict[int, int]:
    """`multiple` whole base permissions, leg by leg."""
    legs = base_permission_legs()
    return {channel: multiple * legs[channel] for channel in RECOVERY_POOL_LEGS}


def base_permission_total() -> int:
    return sum(base_permission_legs().values())


def pool_scenario_totals() -> dict[str, object]:
    """Two cycles, two seats each contributing, one winner in the second.

    Cycle one is met by nobody: both permissions are reallocated, nothing is
    divided, and the whole of both enters the pool. Cycle two is met by one seat
    alone: it accrues its own permission, takes the other's reallocated one, and
    absorbs everything cycle one left. Four permissions were assigned and one
    seat can claim all four.
    """
    return {
        "assigned_permissions": 4,
        "pool_after_dead_cycle": leg_total(2),
        "outstanding_after_dead_cycle": leg_total(2),
        "claimable_after_dead_cycle": leg_total(0),
        "pool_after_won_cycle": leg_total(0),
        "claimable_after_won_cycle": leg_total(4),
        "minted": leg_total(4),
        "minted_total_atomic": 4 * base_permission_total(),
        "outstanding_after_mint": leg_total(0),
        "unreferred_pool_atomic": 4 * REFERRAL_LEG_ATOMIC,
        "verified_user_issued_atomic": 2 * VERIFIED_USER_DAILY_ATOMIC,
    }


def permanence_scenario_totals() -> dict[str, object]:
    """One contributing cycle nobody met, then a cycle with no contributor at all.

    The out-of-span machine contributes nothing in either cycle and wins the
    second, so it collects the whole of the one permission the chain assigned —
    from a cycle in which the contributing set was empty. That is the case the
    pool would strand forever if the winner set were narrowed to the contributing
    set.
    """
    return {
        "assigned_permissions": 1,
        "pool_after_stranded_cycle": leg_total(1),
        "pool_after_drained_cycle": leg_total(0),
        "minted": leg_total(1),
        "minted_total_atomic": base_permission_total(),
        "outstanding_after_mint": leg_total(0),
        "unreferred_pool_atomic": REFERRAL_LEG_ATOMIC,
        "verified_user_issued_atomic": 2 * VERIFIED_USER_DAILY_ATOMIC,
    }


# --- the table of which condition fires, read from the specifications ---------

# Written against the fixture and never against the executor: every entry is a
# reading of `economy-transition-v6`'s rejection orders, which version seven
# carries unchanged, plus ADR 0045's derivation of `NOTHING_TO_MINT` as the empty
# walk range. A model that resolved a condition differently disagrees here rather
# than agreeing with itself.
EXPECTED_RESULTS: dict[str, tuple[str, str]] = {
    "alice_registers": ("SUCCESS", "the verifier signed it and no identity exists yet"),
    "bob_registers": ("SUCCESS", "the same, for a second person"),
    "carol_registers": ("SUCCESS", "the same, for a third"),
    "alice_purchases": ("SUCCESS", "a free seat, signed by the owning identity"),
    "bob_purchases": ("SUCCESS", "the same, for a second seat"),
    "carol_purchases": ("SUCCESS", "the same, for a third"),
    "alice_activates": ("SUCCESS", "a purchased seat, activated once"),
    "bob_activates": ("SUCCESS", "the same"),
    "carol_activates": ("SUCCESS", "the same"),
    "alice_mints": ("SUCCESS", "two assigned windows the mark has not reached"),
    "bob_mints_nothing": (
        "SUCCESS",
        "the walk range is non-empty, so the mint succeeds; the seat holds no bit "
        "in either window, so it collects nothing and still pays the fee",
    ),
    "alice_mints_again": (
        "NOTHING_TO_MINT",
        "the mark now equals the last assigned window, so the walk range is empty",
    ),
    "carol_mints_again": (
        "NOTHING_TO_MINT",
        "the same empty walk range, one block after the mark advanced",
    ),
    "carol_mints": (
        "SUCCESS",
        "a seat past its own 731 cycles holding a winner bit, which kind 4 has "
        "never been gated on span against",
    ),
}

EXPECTED_ADMISSIONS: dict[str, tuple[int, str]] = {
    "carol_registers_on_the_version_six_chain": (
        2,
        "admission step 2 compares the envelope's chain ID with the chain's own, "
        "and the two chains derive theirs under different labels",
    ),
}

# Registration is the one success in any version that charges no fee.
FEE_EXEMPT_LABELS = frozenset({"alice_registers", "bob_registers", "carol_registers"})


def issued_by_label(scenario: str) -> dict[str, int]:
    """What each successful step issues, derived rather than read back."""
    airdrop = VERIFIED_USER_DAILY_ATOMIC
    issued = {
        "alice_registers": airdrop,
        "bob_registers": airdrop,
        "carol_registers": airdrop,
    }
    if scenario in ("pool", "boundary"):
        issued["alice_mints"] = 4 * base_permission_total()
        issued["bob_mints_nothing"] = 0
    if scenario == "permanence":
        issued["carol_mints"] = base_permission_total()
    return issued


def fee_pool_atomic(fee_charging_successes: int) -> int:
    return fee_charging_successes * FIXED_FEE


def economy_entry_count(
    identities: int = 0,
    escrows: int = 0,
    signers: int = 0,
    enrollments: int = 0,
    seats: int = 0,
    assignments: int = 0,
    referral_balances: int = 0,
    custody: int = 0,
) -> int:
    """The size of the economy map, derived from what each transition writes.

    Version seven's genesis floor is fourteen rather than twenty-three: the ten
    carry entries are gone and one recovery pool entry replaces them.
    """
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
    )
