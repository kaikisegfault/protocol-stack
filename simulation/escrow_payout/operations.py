"""Outcomes, journals, and the write sets shared by the escrow handlers.

A handler is a pure function of the state and the event. It returns either a
rejection or a complete description of the writes, and never holds a mutable
reference it can partially write, so a rejected event cannot change state by
construction rather than by a compensating copy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..common.canonical import format_atomic
from .domain import Capability, State

JournalEntry = dict[str, Any]

INCREASE = "increase"
DECREASE = "decrease"


@dataclass(frozen=True)
class BindEffect:
    """The complete write set of one accepted opening-custody binding."""

    state_digest: str
    opening: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class GrantEffect:
    """The complete write set of one accepted capability grant."""

    capability_id: str
    capability: Capability


@dataclass(frozen=True)
class PayoutEffect:
    """The complete write set of one accepted payout."""

    payout_id: str
    capability_id: str
    escrow_id: str
    recipient_id: str
    available_custody: int
    paid_out_total: int
    recipient_balance: int
    spent: int


@dataclass(frozen=True)
class RevokeEffect:
    """The complete write set of one accepted revocation."""

    capability_id: str


@dataclass(frozen=True)
class CycleEffect:
    """The complete write set of one accepted cycle advance."""

    current_cycle: int


Effect = BindEffect | GrantEffect | PayoutEffect | RevokeEffect | CycleEffect


@dataclass
class Outcome:
    code: str
    effect: Effect | None = None
    journal: list[JournalEntry] = field(default_factory=list)

    @property
    def accepted(self) -> bool:
        return self.code == "OK"


def failure(code: str) -> Outcome:
    return Outcome(code=code)


def entry(bucket: str, direction: str, amount: int) -> JournalEntry:
    """Build one journal entry; amounts stay unsigned canonical decimal strings."""
    return {
        "bucket": bucket,
        "direction": direction,
        "amount_atomic": format_atomic(amount),
    }


def journal_delta(item: JournalEntry) -> int:
    amount = int(item["amount_atomic"])
    return amount if item["direction"] == INCREASE else -amount


def apply_effect(state: State, effect: object) -> None:
    """Commit a validated write set. Every check already passed."""
    if type(effect) is BindEffect:
        state.bound_state_digest = effect.state_digest
        for escrow_id, amount in effect.opening:
            state.opening_custody[escrow_id] = amount
            state.available_custody[escrow_id] = amount
    elif type(effect) is GrantEffect:
        state.capabilities[effect.capability_id] = effect.capability
    elif type(effect) is PayoutEffect:
        state.available_custody[effect.escrow_id] = effect.available_custody
        state.paid_out_total[effect.escrow_id] = effect.paid_out_total
        state.recipient_balances[effect.escrow_id][effect.recipient_id] = (
            effect.recipient_balance
        )
        state.capabilities[effect.capability_id].spent = effect.spent
        state.accepted_payout_ids.add(effect.payout_id)
    elif type(effect) is RevokeEffect:
        state.capabilities[effect.capability_id].revoked = True
    elif type(effect) is CycleEffect:
        state.current_cycle = effect.current_cycle
    else:  # pragma: no cover - the engine only commits accepted outcomes
        raise TypeError(f"unknown escrow effect: {type(effect).__name__}")
