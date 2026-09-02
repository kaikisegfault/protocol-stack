"""Kind 20 and kind 21: the two transitions version eight adds.

Each is stated as its ordered rejection conditions and its writes, over exactly
the state it reads. **Version seven's shared envelope checks are not restated
here** — the nonce, the fee limit, the expiry, and the resolution of the acting
escrow are version seven's and run before any condition below.

The conditions are in the specification's order, and one departs from the
accepted measurement model with its reason recorded in place: kind 20 checks
`RESPONSE_TOO_LATE` *before* `CHALLENGE_NOT_ISSUED`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from . import contract as c
from .envelope import dispute_message
from .slots import in_scope, slot_of_height, window_of_height
from .state import (
    CHALLENGE_ANSWERED,
    CHALLENGE_OUTSTANDING,
    all_slots_credited,
    decode_open_challenge_value,
    decode_seat_window_value,
    open_challenge_key,
    open_challenge_value,
    seat_window_key,
    seat_window_value,
)

__all__ = [
    "Context",
    "Outcome",
    "Seat",
    "expire_challenge",
    "file_dispute",
    "issue_challenge",
    "submit_response",
]

Verifier = Callable[[bytes, bytes, bytes], bool]


@dataclass(frozen=True)
class Seat:
    hub_identity_hash: bytes
    activation_height: int
    is_activated: bool


@dataclass
class Context:
    """Exactly what the two transitions read, and nothing else.

    The economy dictionary is the same key space the state root commits to, so
    a transition's writes are state writes rather than a model-side shadow.
    """

    chain_id: bytes
    height: int
    dispute_authority_key: bytes
    seats: dict[int, Seat] = field(default_factory=dict)
    # escrow identifier to the HUB identity that owns it.
    escrow_owner: dict[bytes, bytes] = field(default_factory=dict)
    economy: dict[bytes, bytes] = field(default_factory=dict)


@dataclass(frozen=True)
class Outcome:
    code: str

    @property
    def succeeded(self) -> bool:
        return self.code == "SUCCESS"


def _refused(code: str) -> Outcome:
    return Outcome(code=code)


_SUCCESS = Outcome(code="SUCCESS")


def submit_response(
    context: Context, acting_escrow: bytes, body: dict[str, object]
) -> Outcome:
    """Kind 20. Nine ordered conditions, then one state write.

    On acceptance the open challenge entry's state becomes `1`. **No credited
    slot is added**, because a slot bit is already set and only expiry or a
    dispute ever clears one.
    """
    seat_id = int(body["seat_id"])
    challenge_height = int(body["challenge_height"])
    height = context.height
    window = window_of_height(height)

    if seat_id > c.MAX_SEAT_ID:
        return _refused("CYCLE_RANGE")
    seat = context.seats.get(seat_id)
    if seat is None:
        return _refused("SEAT_NOT_PURCHASED")
    if not seat.is_activated:
        return _refused("SEAT_NOT_ACTIVATED")
    if context.escrow_owner.get(acting_escrow) != seat.hub_identity_hash:
        return _refused("UNAUTHORIZED")
    if not in_scope(seat.activation_height, window):
        return _refused("SEAT_NOT_IN_SCOPE")
    if challenge_height >= height or not _same_slot(challenge_height, height):
        return _refused("CHALLENGE_NOT_OPEN")
    if height > challenge_height + c.RESPONSE_DEADLINE_BLOCKS:
        # Ahead of the issuance check, and the accepted model orders them the
        # other way. The model recomputes selection from retained beacons and
        # can say "issued, and you are late"; version eight deletes the entry at
        # expiry, so checking issuance first would report that a challenge which
        # *was* issued never was. Both are refusals that write nothing, so the
        # reordering changes no accepted outcome and makes the report true.
        return _refused("RESPONSE_TOO_LATE")

    key = open_challenge_key(challenge_height, seat_id)
    recorded = context.economy.get(key)
    if recorded is None:
        return _refused("CHALLENGE_NOT_ISSUED")
    if decode_open_challenge_value(recorded) == CHALLENGE_ANSWERED:
        return _refused("RESPONSE_REPLAY")

    context.economy[key] = open_challenge_value(CHALLENGE_ANSWERED)
    return _SUCCESS


def file_dispute(
    context: Context, body: dict[str, object], verify: Verifier
) -> Outcome:
    """Kind 21. Ten ordered conditions, then one bit set.

    On acceptance the slot's bit is set in `disputed` and **`credited` is not
    changed**, so the record keeps what the seat's own evidence said and the
    containment invariant stays checkable against that evidence.
    """
    seat_id = int(body["seat_id"])
    cycle_window = int(body["cycle_window"])
    slot_index = int(body["slot_index"])
    reason_code = int(body["reason_code"])
    signature = body["authority_signature"]
    valid_until_height = int(body["valid_until_height"])
    window = window_of_height(context.height)

    message = dispute_message(
        context.chain_id,
        seat_id,
        cycle_window,
        slot_index,
        reason_code,
        valid_until_height,
    )
    if not verify(context.dispute_authority_key, message, signature):
        return _refused("UNAUTHORIZED_DISPUTE")
    if seat_id > c.MAX_SEAT_ID:
        return _refused("CYCLE_RANGE")
    seat = context.seats.get(seat_id)
    if seat is None:
        return _refused("SEAT_NOT_PURCHASED")
    if slot_index > c.MAX_SLOT_INDEX:
        return _refused("SLOT_RANGE")
    if cycle_window >= window:
        return _refused("WINDOW_NOT_CLOSED")
    if cycle_window + c.ASSIGNMENT_LAG_WINDOWS <= window:
        return _refused("DISPUTE_WINDOW_CLOSED")
    if not in_scope(seat.activation_height, cycle_window):
        return _refused("SEAT_NOT_IN_SCOPE")

    key = seat_window_key(cycle_window, seat_id)
    recorded = context.economy.get(key)
    credited, disputed = (
        (all_slots_credited(), 0) if recorded is None else decode_seat_window_value(recorded)
    )
    bit = 1 << slot_index
    if disputed & bit:
        return _refused("DISPUTE_REPLAY")
    if not credited & bit:
        return _refused("DISPUTE_SLOT_NOT_CREDITED")
    if bin(disputed).count("1") >= c.DISPUTE_CAP_SLOTS_PER_SEAT:
        return _refused("DISPUTE_CAP_EXCEEDED")

    context.economy[key] = seat_window_value(credited, disputed | bit)
    return _SUCCESS


def expire_challenge(context: Context, challenge_height: int, seat_id: int) -> None:
    """The expiry step's per-entry effect, which no transaction can request.

    An answered challenge is deleted and nothing else is written. An outstanding
    one clears the seat's bit for the slot of its *challenge* height, creating
    the window record if it is absent — which is the model's slot-close sweep
    made incremental and exact.
    """
    key = open_challenge_key(challenge_height, seat_id)
    recorded = context.economy.pop(key, None)
    if recorded is None:
        return
    if decode_open_challenge_value(recorded) == CHALLENGE_ANSWERED:
        return

    window = window_of_height(challenge_height)
    record_key = seat_window_key(window, seat_id)
    existing = context.economy.get(record_key)
    credited, disputed = (
        (all_slots_credited(), 0)
        if existing is None
        else decode_seat_window_value(existing)
    )
    credited &= ~(1 << slot_of_height(challenge_height))
    context.economy[record_key] = seat_window_value(credited, disputed)


def issue_challenge(context: Context, challenge_height: int, seat_id: int) -> None:
    """The issue step's per-seat effect. A height is written once."""
    key = open_challenge_key(challenge_height, seat_id)
    if key in context.economy:
        raise ValueError("a challenge for this height and seat already exists")
    context.economy[key] = open_challenge_value(CHALLENGE_OUTSTANDING)


def _same_slot(left: int, right: int) -> bool:
    return (window_of_height(left), slot_of_height(left)) == (
        window_of_height(right),
        slot_of_height(right),
    )
