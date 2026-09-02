"""The window and slot grid, and version eight's challenge selection.

The grid is `cycle-boundary-v1`'s and `uptime-measurement-v1`'s, bound rather
than restated. What belongs to version eight is the **canonical octet preimage**
selection is computed over.

**It is deliberately not the measurement model's.** That model digests an RFC
8785 JSON object, as every accepted model in this repository does. A consensus
kernel that canonicalised JSON to decide who is audited would put a parser on
the most adversarial path the pipeline has, and every version-seven construction
is octets for that reason. So the chain and the model select different heights
for the same beacon; what the two share is the rule, and every property the
accepted specification argues from is a property of the rule rather than of the
byte layout.
"""

from __future__ import annotations

from simulation.economy_transition.merkle import digest
from simulation.economy_transition_v6.envelope import MalformedTransaction, u32, u64

from . import contract as c

__all__ = [
    "challenge_preimage",
    "first_cycle_window",
    "in_scope",
    "in_span",
    "is_challengeable_height",
    "is_selected",
    "selection_value",
    "slot_first_height",
    "slot_last_height",
    "slot_of_height",
    "window_first_height",
    "window_of_height",
]


def window_of_height(height: int) -> int:
    return height // c.CYCLE_BLOCKS


def window_first_height(window: int) -> int:
    return window * c.CYCLE_BLOCKS


def slot_of_height(height: int) -> int:
    return (height - window_first_height(window_of_height(height))) // c.SLOT_BLOCKS


def slot_first_height(window: int, slot: int) -> int:
    return window_first_height(window) + slot * c.SLOT_BLOCKS


def slot_last_height(window: int, slot: int) -> int:
    return slot_first_height(window, slot) + c.SLOT_BLOCKS - 1


def is_challengeable_height(height: int) -> bool:
    """The final `RESPONSE_DEADLINE_BLOCKS` heights of a slot issue nothing.

    That exclusion is what puts a challenge and its deadline inside one slot,
    which is in turn what lets version eight clear a slot bit at expiry instead
    of sweeping the population at every slot boundary.
    """
    window = window_of_height(height)
    slot = slot_of_height(height)
    return height <= slot_last_height(window, slot) - c.RESPONSE_DEADLINE_BLOCKS


def challenge_preimage(beacon: bytes, seat_id: int, height: int) -> bytes:
    """`beacon:32 || u32_be(seat_id) || u64_be(height)`, 44 octets.

    The height is bound even though the beacon already varies with it, so a
    selection value is unique to one height and cannot be presented as belonging
    to another.
    """
    if type(beacon) is not bytes or len(beacon) != 32:
        raise MalformedTransaction("beacon is not 32 octets")
    return beacon + u32(seat_id) + u64(height)


def selection_value(beacon: bytes, seat_id: int, height: int) -> int:
    """The first eight octets of the labelled digest, big-endian.

    Truncating biases selection by less than one part in `2^54`: `2^64 mod
    1200` is 1,216, so 1,216 residues occur once more often than the rest over
    the full range. Reducing the whole 256-bit digest would need big-integer
    arithmetic on a consensus path to remove a bias no observer could measure.
    """
    raw = digest(c.CHALLENGE_LABEL, challenge_preimage(beacon, seat_id, height))
    return int.from_bytes(raw[0:8], "big")


def is_selected(beacon: bytes, seat_id: int, height: int) -> bool:
    if not is_challengeable_height(height):
        return False
    return selection_value(beacon, seat_id, height) % c.CHALLENGE_PERIOD_BLOCKS == 0


def first_cycle_window(activation_height: int) -> int:
    """`cycle-boundary-v1`'s rule: the first window that starts *after* it."""
    return window_of_height(activation_height) + 1


def in_scope(activation_height: int, window: int) -> bool:
    """A seat activated strictly before the window's first height.

    A seat activated inside a window cannot have evidence for the whole window,
    and `cycle-boundary-v1` already opens a seat's first cycle at the next full
    window for the same reason.
    """
    return first_cycle_window(activation_height) <= window


def in_span(activation_height: int, window: int) -> bool:
    """In scope and inside the seat's own 731 issuance cycles."""
    first = first_cycle_window(activation_height)
    return first <= window < first + c.ISSUANCE_CYCLES_PER_SEAT
