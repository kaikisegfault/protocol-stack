"""Outcomes, journals, and the checked channel movements shared by handlers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import contract as c
from .canonical import checked_add, checked_sub, format_atomic
from .domain import Leg, State, credit_custody

JournalEntry = dict[str, Any]

INCREASE = "increase"
DECREASE = "decrease"


@dataclass
class Outcome:
    code: str
    journal: list[JournalEntry] = field(default_factory=list)

    @property
    def accepted(self) -> bool:
        return self.code == "OK"


def failure(code: str) -> Outcome:
    return Outcome(code=code)


def accepted(journal: list[JournalEntry] | None = None) -> Outcome:
    return Outcome(code="OK", journal=list(journal or []))


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


def check_reservable(state: State, legs: tuple[Leg, ...]) -> str | None:
    """Prove every leg fits its channel cap without writing any state."""
    requested: dict[str, int] = {}
    for leg in legs:
        total = checked_add(requested.get(leg.channel, 0), leg.amount_atomic)
        if total is None:
            return "ARITHMETIC_OVERFLOW"
        requested[leg.channel] = total
    for channel_id, amount in requested.items():
        channel = state.channels[channel_id]
        reserved = checked_add(channel.issued_atomic, channel.outstanding_atomic)
        if reserved is None or checked_add(reserved, amount) is None:
            return "ARITHMETIC_OVERFLOW"
        if reserved + amount > c.CHANNEL_CAPS[channel_id]:
            return "CHANNEL_CAP"
    return None


def reserve(state: State, legs: tuple[Leg, ...]) -> list[JournalEntry]:
    """Move value from channel capacity into outstanding permission liability."""
    journal: list[JournalEntry] = []
    for leg in legs:
        state.channels[leg.channel].outstanding_atomic += leg.amount_atomic
        journal.append(entry(f"capacity:{leg.channel}", DECREASE, leg.amount_atomic))
        journal.append(entry(f"outstanding:{leg.channel}", INCREASE, leg.amount_atomic))
    return journal


def check_issuable(state: State, legs: tuple[Leg, ...]) -> str | None:
    """Prove an exercise can move every leg from outstanding into custody."""
    released: dict[str, int] = {}
    credited: dict[str, int] = {}
    for leg in legs:
        released[leg.channel] = released.get(leg.channel, 0) + leg.amount_atomic
        credited[leg.custody_key] = credited.get(leg.custody_key, 0) + leg.amount_atomic
    for channel_id, amount in released.items():
        channel = state.channels[channel_id]
        outstanding = checked_sub(channel.outstanding_atomic, amount)
        if outstanding is None:
            return "INVARIANT"
        issued = checked_add(channel.issued_atomic, amount)
        if issued is None:
            return "ARITHMETIC_OVERFLOW"
        if issued + outstanding > c.CHANNEL_CAPS[channel_id]:
            return "CHANNEL_CAP"
    for custody_key, amount in credited.items():
        if checked_add(state.typed_custody.get(custody_key, 0), amount) is None:
            return "ARITHMETIC_OVERFLOW"
    return None


def issue(state: State, legs: tuple[Leg, ...]) -> list[JournalEntry]:
    """Move value from outstanding liability into issued supply and custody."""
    journal: list[JournalEntry] = []
    for leg in legs:
        channel = state.channels[leg.channel]
        channel.outstanding_atomic -= leg.amount_atomic
        channel.issued_atomic += leg.amount_atomic
        if not credit_custody(state, leg.custody_key, leg.amount_atomic):
            raise AssertionError("prechecked custody credit overflowed")
        journal.append(entry(f"outstanding:{leg.channel}", DECREASE, leg.amount_atomic))
        journal.append(entry(f"issued:{leg.channel}", INCREASE, leg.amount_atomic))
        journal.append(entry(f"custody:{leg.custody_key}", INCREASE, leg.amount_atomic))
    return journal


def issue_direct(
    state: State,
    channel_id: str,
    custody_key: str,
    amount: int,
) -> list[JournalEntry]:
    """Move value from channel capacity straight into issued supply and custody."""
    state.channels[channel_id].issued_atomic += amount
    if not credit_custody(state, custody_key, amount):
        raise AssertionError("prechecked custody credit overflowed")
    return [
        entry(f"capacity:{channel_id}", DECREASE, amount),
        entry(f"issued:{channel_id}", INCREASE, amount),
        entry(f"custody:{custody_key}", INCREASE, amount),
    ]
