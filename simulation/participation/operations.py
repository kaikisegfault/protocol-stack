"""Typed ordinary event outcomes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Outcome:
    accepted: bool
    code: str


def success() -> Outcome:
    return Outcome(accepted=True, code="OK")


def failure(code: str) -> Outcome:
    return Outcome(accepted=False, code=code)
