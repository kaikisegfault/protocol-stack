"""The version-nine economy key space, its tree, and the version-nine root.

Version nine's key space is version eight's with four entry kinds added and one
value widened, and **the widened one is the reason this is a version rather than
an edit**: kind 12 gains `payable` between `accrued` and `minted`, so a
version-eight decoder cannot read a version-nine pool entry and a version-nine
decoder cannot read a version-eight one.

**Everything else is imported rather than restated.** Every key builder and
value encoder version eight accepted is re-exported unchanged, so a width that
moved would have to move in an accepted module and would fail that version's own
vectors first.

**The root commits to the timestamp**, which is forced rather than chosen: C2
compares a block's stamp with its predecessor's, so a machine that restarted or
restored from a snapshot must know the predecessor's, and a value two machines
could hold differently without their roots differing is a fork no gate catches.
It is version one's argument for committing to the height, applied to the second
field that orders blocks.

**A zero is absence in two of the four new values and the decoders say so.** A
monthly figure of zero and a claim whose `accrued` is zero are both the
non-minimal representation `protocol-primitives-v1` forbids: a candidate with no
figure has a figure of zero by absence, and a seat that has won nothing has no
claim. Writing either would mean the same fact had two encodings, and in the
zero-best month it would mean 100,000 entries recording that nobody was paid.
"""

from __future__ import annotations

from simulation.economy_transition.merkle import digest, root
from simulation.economy_transition_v6.envelope import u16, u32, u64
from simulation.economy_transition_v6.state import u8
from simulation.economy_transition_v8.state import (
    CHALLENGE_ANSWERED,
    CHALLENGE_OUTSTANDING,
    InvalidStateEntry,
    accounts_root,
    all_slots_credited,
    channel_key,
    channel_value,
    credited_slots,
    cycle_assignment_key,
    cycle_assignment_value,
    decode_cycle_assignment_value,
    decode_open_challenge_value,
    decode_recovery_pool_value,
    decode_seat_window_value,
    direct_decision_key,
    entry_leaf,
    escrow_key,
    escrow_value,
    hub_identity_key,
    hub_identity_value,
    open_challenge_key,
    open_challenge_parts,
    open_challenge_value,
    recovery_pool_key,
    recovery_pool_value,
    referral_balance_key,
    referral_balance_value,
    seat_key,
    seat_value,
    seat_window_key,
    seat_window_parts,
    seat_window_value,
    signer_key,
    signer_value,
    typed_custody_key,
    typed_custody_value,
    unreferred_pool_key,
    verified_user_counter_key,
    verified_user_counter_value,
    verified_user_key,
    verified_user_value,
    verifier_key_key,
    verifier_key_value,
)

from . import contract as c

__all__ = [
    "CHALLENGE_ANSWERED",
    "CHALLENGE_OUTSTANDING",
    "InvalidStateEntry",
    "accounts_root",
    "all_slots_credited",
    "channel_key",
    "channel_value",
    "credited_slots",
    "cycle_assignment_key",
    "cycle_assignment_value",
    "decode_cycle_assignment_value",
    "decode_monthly_claim_value",
    "decode_monthly_figure_value",
    "decode_open_challenge_value",
    "decode_recovery_pool_value",
    "decode_seat_window_value",
    "decode_settlement_cursor_value",
    "decode_unreferred_pool_value",
    "decode_window_month_value",
    "direct_decision_key",
    "economy_root",
    "entry_leaf",
    "escrow_key",
    "escrow_value",
    "hub_identity_key",
    "hub_identity_value",
    "monthly_claim_key",
    "monthly_claim_parts",
    "monthly_claim_value",
    "monthly_figure_key",
    "monthly_figure_parts",
    "monthly_figure_value",
    "open_challenge_key",
    "open_challenge_parts",
    "open_challenge_value",
    "ordered_entries",
    "predecessor_state_root",
    "recovery_pool_key",
    "recovery_pool_value",
    "referral_balance_key",
    "referral_balance_value",
    "require_entry_shape",
    "seat_key",
    "seat_value",
    "seat_window_key",
    "seat_window_parts",
    "seat_window_value",
    "settlement_cursor_key",
    "settlement_cursor_value",
    "signer_key",
    "signer_value",
    "state_root",
    "state_root_frame",
    "state_root_from_frame",
    "typed_custody_key",
    "typed_custody_value",
    "unreferred_pool_key",
    "unreferred_pool_value",
    "verified_user_counter_key",
    "verified_user_counter_value",
    "verified_user_key",
    "verified_user_value",
    "verifier_key_key",
    "verifier_key_value",
    "window_month_key",
    "window_month_parts",
    "window_month_value",
]


def _require_u64(value: int, name: str) -> int:
    if type(value) is not int or value < 0 or value > c.MAX_U64:
        raise InvalidStateEntry(f"{name} is not a u64")
    return value


def _require_month(index: int, name: str = "month index") -> int:
    """Every recorded month is inside `calendar-v1`'s accepted range.

    The bound is what makes every derivation that reads one total: a month index
    above `MAX_MONTH_INDEX` has no first millisecond and no last, so a decoder
    that admitted one would hand an undefined case to arithmetic downstream.
    """
    if type(index) is not int or index < 0 or index > c.MAX_MONTH_INDEX:
        raise InvalidStateEntry(
            f"{name} {index} is outside 0..{c.MAX_MONTH_INDEX}"
        )
    return index


# --- kind 12, widened -------------------------------------------------------


def unreferred_pool_value(accrued: int, payable: int, minted: int) -> bytes:
    """`accrued || payable || minted`, in the order the units travel.

    A unit arrives and raises `accrued` and `payable` together; it is assigned to
    a winner and leaves `payable` for a claim; the winner mints it and it raises
    `minted`. The two bounds are the identities stated over one entry: nothing
    can be payable that was never accrued, and nothing can be minted that was
    never assigned.
    """
    _require_u64(accrued, "pool accrued")
    _require_u64(payable, "pool payable")
    _require_u64(minted, "pool minted")
    if payable > accrued:
        raise InvalidStateEntry("the pool's payable exceeds what it has accrued")
    if minted > accrued - payable:
        raise InvalidStateEntry("the pool minted more than it has assigned")
    return u64(accrued) + u64(payable) + u64(minted)


def decode_unreferred_pool_value(raw: bytes) -> tuple[int, int, int]:
    if len(raw) != c.ENTRY_VALUE_BYTES[c.UNREFERRED_POOL_ENTRY]:
        raise InvalidStateEntry("unreferred pool value is not twenty-four octets")
    accrued = int.from_bytes(raw[0:8], "big")
    payable = int.from_bytes(raw[8:16], "big")
    minted = int.from_bytes(raw[16:24], "big")
    if payable > accrued:
        raise InvalidStateEntry("the pool's payable exceeds what it has accrued")
    if minted > accrued - payable:
        raise InvalidStateEntry("the pool minted more than it has assigned")
    return accrued, payable, minted


# --- kind 20, the window month ----------------------------------------------


def window_month_key(cycle_window: int) -> bytes:
    return u8(c.WINDOW_MONTH_ENTRY) + u64(_require_u64(cycle_window, "cycle window"))


def window_month_parts(key: bytes) -> int:
    if len(key) != c.ENTRY_KEY_BYTES[c.WINDOW_MONTH_ENTRY] or key[0] != (
        c.WINDOW_MONTH_ENTRY
    ):
        raise InvalidStateEntry("not a window month key")
    return int.from_bytes(key[1:9], "big")


def window_month_value(month_index: int) -> bytes:
    """The month the window's first height fell in, written once and read once.

    It is written at the opening height because the timestamp it derives from is
    not reachable from the block that assigns the window two windows and 57,600
    heights later. A month of zero is a real month — January 1970 — so there is
    no absence rule here, unlike the figure and the claim.
    """
    return u32(_require_month(month_index))


def decode_window_month_value(raw: bytes) -> int:
    if len(raw) != c.ENTRY_VALUE_BYTES[c.WINDOW_MONTH_ENTRY]:
        raise InvalidStateEntry("window month value is not four octets")
    return _require_month(int.from_bytes(raw, "big"))


# --- kind 21, the monthly uptime figure -------------------------------------


def monthly_figure_key(month_index: int, seat_id: int) -> bytes:
    """`u8(21) || month_index:u32 || seat_id:u32`.

    The month is in the key even though exactly one month ever accumulates, so a
    stale entry from another month is visibly wrong rather than silently counted
    and the invariant that catches it can be stated over the state instead of
    over the history that produced it. It is version eight's choice for the seat
    window record, restated.
    """
    return (
        u8(c.MONTHLY_FIGURE_ENTRY)
        + u32(_require_month(month_index))
        + u32(_require_u64(seat_id, "seat id"))
    )


def monthly_figure_parts(key: bytes) -> tuple[int, int]:
    if len(key) != c.ENTRY_KEY_BYTES[c.MONTHLY_FIGURE_ENTRY] or key[0] != (
        c.MONTHLY_FIGURE_ENTRY
    ):
        raise InvalidStateEntry("not a monthly figure key")
    return (
        _require_month(int.from_bytes(key[1:5], "big")),
        int.from_bytes(key[5:9], "big"),
    )


def monthly_figure_value(uptime_seconds: int) -> bytes:
    """Accumulated seconds, nonzero. A zero figure is absence."""
    _require_u64(uptime_seconds, "monthly uptime figure")
    if uptime_seconds == 0:
        raise InvalidStateEntry("a monthly figure of zero is absence, not a value")
    return u64(uptime_seconds)


def decode_monthly_figure_value(raw: bytes) -> int:
    if len(raw) != c.ENTRY_VALUE_BYTES[c.MONTHLY_FIGURE_ENTRY]:
        raise InvalidStateEntry("monthly figure value is not eight octets")
    seconds = int.from_bytes(raw, "big")
    if seconds == 0:
        raise InvalidStateEntry("a monthly figure of zero is absence, not a value")
    return seconds


# --- kind 22, the monthly pool claim ----------------------------------------


def monthly_claim_key(seat_id: int) -> bytes:
    return u8(c.MONTHLY_CLAIM_ENTRY) + u32(_require_u64(seat_id, "seat id"))


def monthly_claim_parts(key: bytes) -> int:
    if len(key) != c.ENTRY_KEY_BYTES[c.MONTHLY_CLAIM_ENTRY] or key[0] != (
        c.MONTHLY_CLAIM_ENTRY
    ):
        raise InvalidStateEntry("not a monthly claim key")
    return int.from_bytes(key[1:5], "big")


def monthly_claim_value(accrued: int, minted: int) -> bytes:
    """The referral balance's shape, keyed by the seat rather than the identity.

    `accrued` is nonzero in every claim that exists: a settlement whose share
    rounds to zero writes no entry, because a claim is a balance and a balance of
    zero is absence. The entry survives being emptied, exactly as a referral
    balance does, because the pair is the audit trail of what a machine earned
    and what it took.
    """
    _require_u64(accrued, "claim accrued")
    _require_u64(minted, "claim minted")
    if accrued == 0:
        raise InvalidStateEntry("a claim of zero is absence, not a value")
    if minted > accrued:
        raise InvalidStateEntry("a claim minted more than it accrued")
    return u64(accrued) + u64(minted)


def decode_monthly_claim_value(raw: bytes) -> tuple[int, int]:
    if len(raw) != c.ENTRY_VALUE_BYTES[c.MONTHLY_CLAIM_ENTRY]:
        raise InvalidStateEntry("monthly claim value is not sixteen octets")
    accrued = int.from_bytes(raw[0:8], "big")
    minted = int.from_bytes(raw[8:16], "big")
    if accrued == 0:
        raise InvalidStateEntry("a claim of zero is absence, not a value")
    if minted > accrued:
        raise InvalidStateEntry("a claim minted more than it accrued")
    return accrued, minted


# --- kind 23, the settlement cursor -----------------------------------------


def settlement_cursor_key() -> bytes:
    return u8(c.SETTLEMENT_CURSOR_ENTRY)


def settlement_cursor_value(accumulating_month: int) -> bytes:
    """The month whose figures are currently accumulating.

    A singleton rather than a fourth field on the pool, because it describes
    where the window grid has reached on the calendar rather than what the pool
    holds, and would still be needed on a chain whose pool was permanently empty.
    """
    return u32(_require_month(accumulating_month, "accumulating month"))


def decode_settlement_cursor_value(raw: bytes) -> int:
    if len(raw) != c.ENTRY_VALUE_BYTES[c.SETTLEMENT_CURSOR_ENTRY]:
        raise InvalidStateEntry("settlement cursor value is not four octets")
    return _require_month(int.from_bytes(raw, "big"), "accumulating month")


# --- the tree ---------------------------------------------------------------


def economy_root(entries: dict[bytes, bytes]) -> bytes:
    ordered = ordered_entries(entries)
    return root(
        [entry_leaf(key, value) for key, value in ordered], c.ECONOMY_TREE_PREFIX
    )


def ordered_entries(entries: dict[bytes, bytes]) -> list[tuple[bytes, bytes]]:
    for key, value in entries.items():
        require_entry_shape(key, value)
    return sorted(entries.items(), key=lambda item: item[0])


_VALUE_DECODERS = {
    c.RECOVERY_POOL_ENTRY: decode_recovery_pool_value,
    c.OPEN_CHALLENGE_ENTRY: decode_open_challenge_value,
    c.SEAT_WINDOW_ENTRY: decode_seat_window_value,
    c.UNREFERRED_POOL_ENTRY: decode_unreferred_pool_value,
    c.WINDOW_MONTH_ENTRY: decode_window_month_value,
    c.MONTHLY_FIGURE_ENTRY: decode_monthly_figure_value,
    c.MONTHLY_CLAIM_ENTRY: decode_monthly_claim_value,
    c.SETTLEMENT_CURSOR_ENTRY: decode_settlement_cursor_value,
}


def require_entry_shape(key: bytes, value: bytes) -> None:
    if not key:
        raise InvalidStateEntry("empty economy key")
    kind = key[0]
    if kind in c.RETIRED_ENTRY_KINDS:
        raise InvalidStateEntry(
            f"entry kind {kind} is retired and permanently unassigned in version nine"
        )
    if kind not in c.ENTRY_KINDS:
        raise InvalidStateEntry(f"unknown economy entry kind {kind}")
    if len(key) != c.ENTRY_KEY_BYTES[kind]:
        raise InvalidStateEntry(f"entry kind {kind} key is not its fixed width")
    if kind == c.MONTHLY_FIGURE_ENTRY:
        monthly_figure_parts(key)
    elif kind == c.MONTHLY_CLAIM_ENTRY:
        monthly_claim_parts(key)
    expected = c.ENTRY_VALUE_BYTES[kind]
    if expected is None:
        decode_cycle_assignment_value(value)
        return
    if len(value) != expected:
        raise InvalidStateEntry(f"entry kind {kind} value is not its fixed width")
    decoder = _VALUE_DECODERS.get(kind)
    if decoder is not None:
        decoder(value)


# --- the root ---------------------------------------------------------------


def state_root(
    chain_id: bytes,
    height: int,
    timestamp: int,
    supply_limit: int,
    total_supply: int,
    fee_pool_balance: int,
    accounts: list[tuple[bytes, int, int]],
    economy: dict[bytes, bytes],
) -> str:
    """The version-nine root. Its label and version differ from all eight
    predecessors, and each non-collision is required separately."""
    return state_root_from_frame(
        state_root_frame(
            chain_id, supply_limit, total_supply, fee_pool_balance, accounts, economy
        ),
        height,
        timestamp,
    )


def state_root_frame(
    chain_id: bytes,
    supply_limit: int,
    total_supply: int,
    fee_pool_balance: int,
    accounts: list[tuple[bytes, int, int]],
    economy: dict[bytes, bytes],
) -> tuple[bytes, bytes]:
    """The root preimage split around the two fields a quiet height changes.

    Version eight split it around the height alone. Version nine's timestamp
    moves at every height too, so the split carries both: `state_root` is
    *defined* through this function, so there is one preimage in this module and
    a run of quiet heights cannot drift from it.
    """
    head = u16(c.STATE_ROOT_SCHEMA_VERSION) + _octets(chain_id, 32, "chain ID")
    leaves = [entry_leaf(key, value) for key, value in sorted(economy.items())]
    tail = (
        u64(supply_limit)
        + u64(total_supply)
        + u64(fee_pool_balance)
        + u64(len(accounts))
        + accounts_root(accounts)
        + u64(len(economy))
        + root(leaves, c.ECONOMY_TREE_PREFIX)
    )
    return head, tail


def state_root_from_frame(
    frame: tuple[bytes, bytes], height: int, timestamp: int
) -> str:
    head, tail = frame
    if not c.MIN_TIMESTAMP_MILLIS <= timestamp <= c.MAX_TIMESTAMP_MILLIS:
        raise InvalidStateEntry(
            f"timestamp {timestamp} is outside calendar-v1's accepted range"
        )
    return digest(c.STATE_ROOT_LABEL, head + u64(height) + u64(timestamp) + tail).hex()


def predecessor_state_root(
    version: int,
    chain_id: bytes,
    height: int,
    supply_limit: int,
    total_supply: int,
    fee_pool_balance: int,
    accounts: list[tuple[bytes, int, int]],
    economy: dict[bytes, bytes],
) -> str:
    """The same state under an earlier label, version field, and preimage.

    Every predecessor's preimage carries no timestamp, so a version-nine root
    cannot equal one even where the label collided, and the eight non-collisions
    are still required separately because distinct labels are strings rather than
    a chain.
    """
    if version not in (1, 2, 3, 4, 5, 6, 7, 8):
        raise InvalidStateEntry(f"no predecessor state root for version {version}")
    head = u16(version) + _octets(chain_id, 32, "chain ID")
    leaves = [entry_leaf(key, value) for key, value in sorted(economy.items())]
    tail = (
        u64(supply_limit)
        + u64(total_supply)
        + u64(fee_pool_balance)
        + u64(len(accounts))
        + accounts_root(accounts)
    )
    if version > 1:
        tail += u64(len(economy)) + root(
            leaves, f"protocol-stack:v{version}:economy"
        )
    return digest(
        f"protocol-stack:v{version}:state-root", head + u64(height) + tail
    ).hex()


def _octets(value: bytes, width: int, name: str) -> bytes:
    if type(value) is not bytes or len(value) != width:
        raise InvalidStateEntry(f"{name} is not {width} octets")
    return value
