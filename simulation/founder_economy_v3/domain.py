"""Founder Economy v3 simulator state, canonical values, and invariants.

The state differs from version two's in exactly two places: a seat record
carries the activation height its 731-window schedule is derived from, and the
state carries the highest height recorded so far. Everything below the seat
table is version two's state unchanged.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from . import contract as c
from ..common.canonical import (
    MAX_U64,
    InvariantError,
    checked_add,
    checked_mul,
    digest,
    format_atomic,
    required_sum,
)
from ..cycle_boundary.grid import (
    first_cycle_window,
    last_cycle_window,
    span_is_representable,
    window_for_cycle,
)

STATE_LABEL = "protocol-stack:founder-economy:state-v3"


def permission_key(seat_id: int, cycle_index: int) -> str:
    """Return the zero-padded replay key, which sorts numerically and lexically."""
    return f"{seat_id:05d}:{cycle_index:03d}"


def founder_custody_key(seat_id: int) -> str:
    return f"{c.FOUNDER_SEAT_KIND}:{seat_id:05d}"


def singleton_custody_key(beneficiary_kind: str) -> str:
    return f"{beneficiary_kind}:{c.SINGLETON_BENEFICIARY_ID}"


def direct_custody_key(beneficiary_id: str) -> str:
    return f"{c.DIRECT_BENEFICIARY_KIND}:{beneficiary_id}"


def format_height(value: int) -> str:
    """Render a u64 height as a canonical decimal string.

    A height can exceed the largest integer a conforming JSON stack represents
    exactly, so it is never a JSON number. A window can not, which
    `assert_window_rendering_is_safe` derives, so windows stay numbers and the
    uptime record's shape is unchanged.
    """
    if type(value) is not int or not 0 <= value <= MAX_U64:
        raise InvariantError(f"cannot format non-u64 height: {value!r}")
    return str(value)


@dataclass(frozen=True)
class Seat:
    """One activated seat: who referred it, and the schedule it holds."""

    referrer_seat_id: int | None
    activation_height: int


@dataclass
class Channel:
    issued_atomic: int = 0
    outstanding_atomic: int = 0


@dataclass(frozen=True)
class Leg:
    channel: str
    custody_key: str
    amount_atomic: int


@dataclass(frozen=True)
class PendingPermission:
    seat_id: int
    cycle_index: int
    cycle_window: int
    met_cycle: bool
    total_atomic: int
    legs: tuple[Leg, ...]


@dataclass
class State:
    seats: dict[int, Seat] = field(default_factory=dict)
    last_activation_height: int | None = None
    channels: dict[str, Channel] = field(default_factory=dict)
    pending_permissions: dict[str, PendingPermission] = field(default_factory=dict)
    evaluated_permission_keys: set[str] = field(default_factory=set)
    referral_accrual_keys: set[str] = field(default_factory=set)
    accepted_direct_decision_ids: set[str] = field(default_factory=set)
    bound_uptime_records: dict[int, str] = field(default_factory=dict)
    typed_custody: dict[str, int] = field(default_factory=dict)
    performance_carry_atomic: int = 0

    def clone(self) -> State:
        return copy.deepcopy(self)

    def capacity(self, channel_id: str) -> int:
        channel = self.channels[channel_id]
        return c.CHANNEL_CAPS[channel_id] - channel.issued_atomic - channel.outstanding_atomic


def initial_state() -> State:
    """Every channel and the carry start empty; there is no genesis allocation."""
    return State(channels={channel_id: Channel() for channel_id in c.CHANNEL_IDS})


def issued_supply(state: State) -> int:
    return required_sum(
        [channel.issued_atomic for channel in state.channels.values()],
        "issued supply",
    )


def outstanding_permissions(state: State) -> int:
    return required_sum(
        [channel.outstanding_atomic for channel in state.channels.values()],
        "outstanding permissions",
    )


def founder_accounted(state: State) -> int:
    """Return issued plus outstanding plus carried Founder-portion value."""
    channel = state.channels[c.FOUNDER_CHANNEL]
    return required_sum(
        [channel.issued_atomic, channel.outstanding_atomic, state.performance_carry_atomic],
        "founder accounted total",
    )


def credit_custody(state: State, custody_key: str, amount: int) -> bool:
    result = checked_add(state.typed_custody.get(custody_key, 0), amount)
    if result is None:
        return False
    state.typed_custody[custody_key] = result
    return True


def state_value(state: State) -> dict[str, Any]:
    """Return the canonical state value.

    A seat's span endpoints are derived from its activation height and recorded
    anyway. That puts the grid inside the state digest, so a change to
    `CYCLE_BLOCKS` moves every digest rather than silently renumbering windows
    behind one that did not move, and it lets a reader check a pending
    permission's window against its seat's span without replaying the run.
    """
    return {
        "seats": {
            f"{seat_id:05d}": {
                "referrer_seat_id": (
                    None if seat.referrer_seat_id is None else f"{seat.referrer_seat_id:05d}"
                ),
                "activation_height": format_height(seat.activation_height),
                "first_cycle_window": first_cycle_window(seat.activation_height),
                "last_cycle_window": last_cycle_window(seat.activation_height),
            }
            for seat_id, seat in sorted(state.seats.items())
        },
        "last_activation_height": (
            None
            if state.last_activation_height is None
            else format_height(state.last_activation_height)
        ),
        "channels": {
            channel_id: {
                "issued_atomic": format_atomic(state.channels[channel_id].issued_atomic),
                "outstanding_atomic": format_atomic(
                    state.channels[channel_id].outstanding_atomic
                ),
            }
            for channel_id in c.CHANNEL_IDS
        },
        "pending_permissions": {
            key: {
                "seat_id": permission.seat_id,
                "cycle_index": permission.cycle_index,
                "cycle_window": permission.cycle_window,
                "met_cycle": permission.met_cycle,
                "total_atomic": format_atomic(permission.total_atomic),
                "legs": [
                    {
                        "channel": leg.channel,
                        "custody_key": leg.custody_key,
                        "amount_atomic": format_atomic(leg.amount_atomic),
                    }
                    for leg in permission.legs
                ],
            }
            for key, permission in sorted(state.pending_permissions.items())
        },
        "evaluated_permission_keys": sorted(state.evaluated_permission_keys),
        "referral_accrual_keys": sorted(state.referral_accrual_keys),
        "accepted_direct_decision_ids": sorted(state.accepted_direct_decision_ids),
        "bound_uptime_records": {
            str(window): state.bound_uptime_records[window]
            for window in sorted(state.bound_uptime_records)
        },
        "typed_custody": {
            key: format_atomic(value) for key, value in sorted(state.typed_custody.items())
        },
        "performance_carry_atomic": format_atomic(state.performance_carry_atomic),
    }


def state_digest(state: State) -> str:
    return digest(STATE_LABEL, state_value(state))


def assert_invariants(state: State) -> None:
    _assert_scalars(state)
    _assert_schedules(state)
    _assert_channels(state)
    _assert_permissions(state)

    issued = issued_supply(state)
    outstanding = outstanding_permissions(state)
    if issued > c.MAXIMUM_SUPPLY_ATOMIC:
        raise InvariantError("issued supply exceeds the maximum supply")
    if checked_add(issued, outstanding) is None:
        raise InvariantError("issued plus outstanding exceeds u64")
    if issued + outstanding > c.MAXIMUM_SUPPLY_ATOMIC:
        raise InvariantError("issued plus outstanding exceeds the maximum supply")

    custodied = required_sum(list(state.typed_custody.values()), "typed custody")
    if custodied != issued:
        raise InvariantError("typed custody does not equal issued supply")


def _assert_scalars(state: State) -> None:
    values = [channel.issued_atomic for channel in state.channels.values()]
    values += [channel.outstanding_atomic for channel in state.channels.values()]
    values += list(state.typed_custody.values())
    values += [permission.total_atomic for permission in state.pending_permissions.values()]
    values.append(state.performance_carry_atomic)
    if any(type(value) is not int or not 0 <= value <= MAX_U64 for value in values):
        raise InvariantError("a stored monetary value is outside u64")
    if any(value == 0 for value in state.typed_custody.values()):
        raise InvariantError("a zero custody entry exists")
    if any(
        seat.referrer_seat_id not in state.seats or seat.referrer_seat_id == seat_id
        for seat_id, seat in state.seats.items()
        if seat.referrer_seat_id is not None
    ):
        raise InvariantError("a seat references an unknown or self referrer")


def _assert_schedules(state: State) -> None:
    """Require every recorded schedule to be representable and monotonic.

    A wrapped window would silently alias another seat's span, and a height
    below the recorded maximum would be a schedule installed in the past.
    """
    heights = [seat.activation_height for seat in state.seats.values()]
    for height in heights:
        if type(height) is not int or not 0 <= height <= c.MAX_HEIGHT:
            raise InvariantError("a recorded activation height is outside u64")
        if not span_is_representable(height):
            raise InvariantError(f"activation height {height} has no representable span")
    if not heights:
        if state.last_activation_height is not None:
            raise InvariantError("a last activation height exists with no activated seat")
        return
    if state.last_activation_height != max(heights):
        raise InvariantError("the last activation height is not the highest recorded one")


def _assert_channels(state: State) -> None:
    if set(state.channels) != set(c.CHANNEL_IDS):
        raise InvariantError("the channel set does not match the manifest")
    for channel_id, channel in state.channels.items():
        reserved = checked_add(channel.issued_atomic, channel.outstanding_atomic)
        if reserved is None or reserved > c.CHANNEL_CAPS[channel_id]:
            raise InvariantError(f"{channel_id} exceeds its manifest cap")
    _assert_founder_accounting(state)


def _assert_founder_accounting(state: State) -> None:
    """Require the carry conservation identity exactly, not merely as a bound."""
    accounted = founder_accounted(state)
    expected = checked_mul(len(state.evaluated_permission_keys), c.FOUNDER_OPERATOR_LEG)
    if expected is None:
        raise InvariantError("the Founder accounting product exceeds u64")
    if accounted != expected:
        raise InvariantError("issued, outstanding, and carried value do not equal the "
                             "evaluated Founder portions")
    if accounted > c.CHANNEL_CAPS[c.FOUNDER_CHANNEL]:
        raise InvariantError("issued, outstanding, and carried value exceed the Founder cap")


def _assert_permissions(state: State) -> None:
    for key, permission in state.pending_permissions.items():
        if key != permission_key(permission.seat_id, permission.cycle_index):
            raise InvariantError("a pending permission key does not match its record")
        if key not in state.evaluated_permission_keys:
            raise InvariantError("a pending permission is not recorded as evaluated")
        if not permission.legs:
            raise InvariantError("a pending permission has no legs")
        if any(leg.amount_atomic == 0 for leg in permission.legs):
            raise InvariantError("a pending permission has a zero leg")
        total = required_sum([leg.amount_atomic for leg in permission.legs], key)
        if total != permission.total_atomic:
            raise InvariantError("a pending permission's legs do not sum to its total")
        _assert_permission_window(state, permission)


def _assert_permission_window(state: State, permission: PendingPermission) -> None:
    """Require a pending permission's window to be the window for its cycle.

    This is the enforced form of the gap version two records. It is asserted
    over the whole pending set at every accepted state rather than only at the
    event that created the permission, so a defect that wrote a permission under
    one schedule and then altered the schedule fails rather than being reported.
    """
    seat = state.seats.get(permission.seat_id)
    if seat is None:
        raise InvariantError("a pending permission belongs to an unactivated seat")
    expected = window_for_cycle(seat.activation_height, permission.cycle_index)
    if permission.cycle_window != expected:
        raise InvariantError(
            f"pending permission window {permission.cycle_window} is not the "
            f"window {expected} for cycle {permission.cycle_index}"
        )
