"""Outcomes, journals, and the write sets shared by the routing handlers.

A handler is a pure function of the state and the event. It returns either a
rejection or a complete description of the writes, and never holds a mutable
reference it can partially write, so a rejected event cannot change state by
construction rather than by a compensating copy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..common.canonical import format_atomic
from .domain import State

JournalEntry = dict[str, Any]

INCREASE = "increase"
DECREASE = "decrease"


@dataclass(frozen=True)
class PaymentEffect:
    """The complete write set of one accepted commercial payment."""

    payment_id: str
    commercial_pool: int
    system_creator_balance: int
    commercial_routed_total: int
    creator_balances: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class FeeEffect:
    """The complete write set of one accepted transaction fee."""

    fee_id: str
    fee_pool: int
    fee_routed_total: int


@dataclass(frozen=True)
class CloseEffect:
    """The complete write set of one accepted cycle close."""

    commercial_carry: int
    fee_carry: int
    commercial_credits: tuple[tuple[int, int], ...]
    fee_credits: tuple[tuple[int, int], ...]


Effect = PaymentEffect | FeeEffect | CloseEffect


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
    if type(effect) is PaymentEffect:
        state.commercial_pool = effect.commercial_pool
        state.system_creator_balance = effect.system_creator_balance
        state.commercial_routed_total = effect.commercial_routed_total
        state.creator_balances.update(effect.creator_balances)
        state.accepted_payment_ids.add(effect.payment_id)
    elif type(effect) is FeeEffect:
        state.fee_pool = effect.fee_pool
        state.fee_routed_total = effect.fee_routed_total
        state.accepted_fee_ids.add(effect.fee_id)
    elif type(effect) is CloseEffect:
        state.founder_commercial_balances.update(effect.commercial_credits)
        state.founder_fee_balances.update(effect.fee_credits)
        state.commercial_pool = 0
        state.fee_pool = 0
        state.commercial_carry = effect.commercial_carry
        state.fee_carry = effect.fee_carry
        state.current_cycle += 1
    else:  # pragma: no cover - the engine only commits accepted outcomes
        raise TypeError(f"unknown routing effect: {type(effect).__name__}")
