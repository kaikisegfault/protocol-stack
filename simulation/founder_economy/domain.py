"""Founder Economy simulator state, canonical values, and invariants."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from . import contract as c
from .canonical import (
    MAX_U64,
    InvariantError,
    checked_add,
    digest,
    format_atomic,
    required_sum,
)

STATE_LABEL = "protocol-stack:founder-economy:state-v1"
PERMISSION_KINDS = ("base", "referral")


def permission_key(seat_id: int, cycle_index: int, kind: str) -> str:
    """Return the zero-padded replay key, which sorts numerically and lexically."""
    return f"{seat_id:05d}:{cycle_index:03d}:{kind}"


def founder_custody_key(seat_id: int) -> str:
    return f"{c.FOUNDER_SEAT_KIND}:{seat_id:05d}"


def singleton_custody_key(beneficiary_kind: str) -> str:
    return f"{beneficiary_kind}:{c.SINGLETON_BENEFICIARY_ID}"


def direct_custody_key(beneficiary_id: str) -> str:
    return f"{c.DIRECT_BENEFICIARY_KIND}:{beneficiary_id}"


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
    kind: str
    total_atomic: int
    legs: tuple[Leg, ...]


@dataclass
class State:
    seats: dict[int, int | None] = field(default_factory=dict)
    channels: dict[str, Channel] = field(default_factory=dict)
    pending_permissions: dict[str, PendingPermission] = field(default_factory=dict)
    evaluated_permission_keys: set[str] = field(default_factory=set)
    accepted_direct_decision_ids: set[str] = field(default_factory=set)
    typed_custody: dict[str, int] = field(default_factory=dict)

    def clone(self) -> State:
        return copy.deepcopy(self)

    def capacity(self, channel_id: str) -> int:
        channel = self.channels[channel_id]
        return c.CHANNEL_CAPS[channel_id] - channel.issued_atomic - channel.outstanding_atomic


def initial_state() -> State:
    """Every channel starts empty; there is no genesis allocation."""
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


def credit_custody(state: State, custody_key: str, amount: int) -> bool:
    result = checked_add(state.typed_custody.get(custody_key, 0), amount)
    if result is None:
        return False
    state.typed_custody[custody_key] = result
    return True


def state_value(state: State) -> dict[str, Any]:
    """Return the canonical state value; monetary fields are decimal strings."""
    return {
        "seats": {
            f"{seat_id:05d}": (
                None if referrer is None else f"{referrer:05d}"
            )
            for seat_id, referrer in sorted(state.seats.items())
        },
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
                "kind": permission.kind,
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
        "accepted_direct_decision_ids": sorted(state.accepted_direct_decision_ids),
        "typed_custody": {
            key: format_atomic(value)
            for key, value in sorted(state.typed_custody.items())
        },
    }


def state_digest(state: State) -> str:
    return digest(STATE_LABEL, state_value(state))


def assert_invariants(state: State) -> None:
    _assert_scalars(state)
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
    if any(type(value) is not int or not 0 <= value <= MAX_U64 for value in values):
        raise InvariantError("a stored monetary value is outside u64")
    if any(value == 0 for value in state.typed_custody.values()):
        raise InvariantError("a zero custody entry exists")
    if any(
        referrer not in state.seats or referrer == seat_id
        for seat_id, referrer in state.seats.items()
        if referrer is not None
    ):
        raise InvariantError("a seat references an unknown or self referrer")


def _assert_channels(state: State) -> None:
    if set(state.channels) != set(c.CHANNEL_IDS):
        raise InvariantError("the channel set does not match the manifest")
    for channel_id, channel in state.channels.items():
        reserved = checked_add(channel.issued_atomic, channel.outstanding_atomic)
        if reserved is None or reserved > c.CHANNEL_CAPS[channel_id]:
            raise InvariantError(f"{channel_id} exceeds its manifest cap")


def _assert_permissions(state: State) -> None:
    for key, permission in state.pending_permissions.items():
        if key != permission_key(permission.seat_id, permission.cycle_index,
                                 permission.kind):
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
