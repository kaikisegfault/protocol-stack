"""Escrow payout state, canonical values, and custody conservation.

Each escrow keeps its own custody, paid-out total, and recipient balances, so
no expression here reads two escrows' custody together. That separation is what
makes cross-escrow containment structural rather than asserted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import contract as c
from ..common.canonical import (
    MAX_U64,
    InvariantError,
    digest,
    format_atomic,
    required_sum,
)


@dataclass
class Capability:
    """Bounded, escrow-scoped, revocable spending authority."""

    escrow_id: str
    per_payout_maximum: int
    envelope_total: int
    spent: int = 0
    expiry_cycle: int = 0
    revoked: bool = False

    def usable_at(self, cycle: int) -> bool:
        return not self.revoked and cycle <= self.expiry_cycle


def _zero_amounts() -> dict[str, int]:
    return {escrow_id: 0 for escrow_id in c.ESCROW_IDS}


def _empty_balances() -> dict[str, dict[str, int]]:
    return {escrow_id: {} for escrow_id in c.ESCROW_IDS}


@dataclass
class State:
    bound_state_digest: str | None = None
    current_cycle: int = 0
    opening_custody: dict[str, int] = field(default_factory=_zero_amounts)
    available_custody: dict[str, int] = field(default_factory=_zero_amounts)
    paid_out_total: dict[str, int] = field(default_factory=_zero_amounts)
    capabilities: dict[str, Capability] = field(default_factory=dict)
    recipient_balances: dict[str, dict[str, int]] = field(
        default_factory=_empty_balances
    )
    accepted_payout_ids: set[str] = field(default_factory=set)

    @property
    def bound(self) -> bool:
        return self.bound_state_digest is not None

    def summary(self) -> tuple[Any, ...]:
        """A constant-time fingerprint used to cross-check no-write rejection.

        The primary guarantee is that handlers are pure and never receive a
        reference they partially write. This is a cheap defence in depth; the
        tests additionally compare full state digests across rejections.
        """
        return (
            self.bound_state_digest,
            self.current_cycle,
            tuple(self.available_custody[escrow] for escrow in c.ESCROW_IDS),
            tuple(self.paid_out_total[escrow] for escrow in c.ESCROW_IDS),
            tuple(
                len(self.recipient_balances[escrow]) for escrow in c.ESCROW_IDS
            ),
            len(self.capabilities),
            len(self.accepted_payout_ids),
        )


def initial_state() -> State:
    """Nothing is bound, no capability exists, and no custody is present."""
    return State()


def capability_value(capability: Capability) -> dict[str, Any]:
    return {
        "escrow_id": capability.escrow_id,
        "per_payout_maximum": format_atomic(capability.per_payout_maximum),
        "envelope_total": format_atomic(capability.envelope_total),
        "spent": format_atomic(capability.spent),
        "expiry_cycle": capability.expiry_cycle,
        "revoked": capability.revoked,
    }


def state_value(state: State) -> dict[str, Any]:
    return {
        "bound_state_digest": state.bound_state_digest,
        "current_cycle": state.current_cycle,
        "opening_custody": _amount_map(state.opening_custody),
        "available_custody": _amount_map(state.available_custody),
        "paid_out_total": _amount_map(state.paid_out_total),
        "capabilities": {
            capability_id: capability_value(capability)
            for capability_id, capability in sorted(state.capabilities.items())
        },
        "recipient_balances": {
            escrow_id: {
                recipient: format_atomic(amount)
                for recipient, amount in sorted(
                    state.recipient_balances[escrow_id].items()
                )
            }
            for escrow_id in sorted(c.ESCROW_IDS)
        },
        "accepted_payout_ids": sorted(state.accepted_payout_ids),
    }


def _amount_map(amounts: dict[str, int]) -> dict[str, str]:
    return {
        escrow_id: format_atomic(amounts[escrow_id])
        for escrow_id in sorted(c.ESCROW_IDS)
    }


def state_digest(state: State) -> str:
    return digest(c.STATE_LABEL, state_value(state))


def assert_invariants(state: State) -> None:
    _assert_shape(state)
    _assert_capabilities(state)
    _assert_unbound(state)
    for escrow_id in c.ESCROW_IDS:
        _assert_escrow_conservation(state, escrow_id)


def _assert_shape(state: State) -> None:
    for amounts in (
        state.opening_custody,
        state.available_custody,
        state.paid_out_total,
    ):
        if set(amounts) != set(c.ESCROW_IDS):
            raise InvariantError("the escrow set does not match the contract")
        for value in amounts.values():
            if type(value) is not int or not 0 <= value <= MAX_U64:
                raise InvariantError("a custody amount is outside u64")
    if set(state.recipient_balances) != set(c.ESCROW_IDS):
        raise InvariantError("the recipient balance map is missing an escrow")
    if type(state.current_cycle) is not int or not 0 <= state.current_cycle <= MAX_U64:
        raise InvariantError("the cycle counter is outside u64")
    for balances in state.recipient_balances.values():
        for amount in balances.values():
            if type(amount) is not int or not 0 < amount <= MAX_U64:
                raise InvariantError("a recipient balance is zero or outside u64")


def _assert_capabilities(state: State) -> None:
    for capability in state.capabilities.values():
        if capability.escrow_id not in c.ESCROW_CAPS:
            raise InvariantError("a capability names an unknown escrow")
        amounts = (
            capability.per_payout_maximum,
            capability.envelope_total,
            capability.spent,
        )
        if any(
            type(value) is not int or not 0 <= value <= MAX_U64
            for value in amounts
        ):
            raise InvariantError("a capability amount is outside u64")
        if not 0 < capability.per_payout_maximum <= capability.envelope_total:
            raise InvariantError("a capability bound is zero or above its envelope")
        if capability.spent > capability.envelope_total:
            raise InvariantError("a capability spent above its envelope")


def _assert_unbound(state: State) -> None:
    """Before binding, nothing may exist that only a bound state can produce."""
    if state.bound:
        return
    empty = (
        all(value == 0 for value in state.opening_custody.values())
        and all(value == 0 for value in state.available_custody.values())
        and all(value == 0 for value in state.paid_out_total.values())
        and not state.capabilities
        and not state.accepted_payout_ids
        and all(not balances for balances in state.recipient_balances.values())
    )
    if not empty:
        raise InvariantError("an unbound state holds custody, capability, or payout")


def _assert_escrow_conservation(state: State, escrow_id: str) -> None:
    opening = state.opening_custody[escrow_id]
    paid_out = state.paid_out_total[escrow_id]
    if opening > c.ESCROW_CAPS[escrow_id]:
        raise InvariantError(f"{escrow_id} opened above its manifest cap")

    held = required_sum([state.available_custody[escrow_id], paid_out], escrow_id)
    if held != opening:
        raise InvariantError(f"{escrow_id} custody is neither available nor paid out")

    credited = required_sum(
        list(state.recipient_balances[escrow_id].values()), f"{escrow_id} recipients"
    )
    if credited != paid_out:
        raise InvariantError(f"{escrow_id} payouts do not reach its recipients")

    charged = required_sum(
        [
            capability.spent
            for capability in state.capabilities.values()
            if capability.escrow_id == escrow_id
        ],
        f"{escrow_id} envelopes",
    )
    if charged != paid_out:
        raise InvariantError(f"{escrow_id} payouts do not match its charged envelopes")
