"""Shared event-operation helpers."""

from __future__ import annotations

from dataclasses import dataclass, field

from .domain import State, checked_add


@dataclass
class Outcome:
    code: str
    journal: list[dict[str, int | str]] = field(default_factory=list)

    @property
    def accepted(self) -> bool:
        return self.code == "OK"


def failure(code: str) -> Outcome:
    return Outcome(code=code)


def success(*entries: tuple[str, int]) -> Outcome:
    journal = [
        {"bucket": bucket, "delta": delta}
        for bucket, delta in entries
        if delta != 0
    ]
    return Outcome(code="OK", journal=journal)


def credit_account(state: State, account: str, amount: int) -> bool:
    current = state.accounts.get(account, 0)
    result = checked_add(current, amount)
    if result is None:
        return False
    state.accounts[account] = result
    return True
