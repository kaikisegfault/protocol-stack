"""Rederive every manifest product and subtotal instead of trusting it.

The ordered loader reaches this stage only for a manifest that already matches
the fixed contract table, so it is a separate module to prove that a
self-consistent but arithmetically wrong manifest is still rejected.
"""

from __future__ import annotations

from typing import Any

from . import contract as c
from ..common.canonical import CodedError, checked_mul, checked_sum


class DerivationError(CodedError):
    """A manifest failed a checked arithmetic derivation."""


def _fail(code: str, detail: str) -> None:
    raise DerivationError(code, detail)


def check_derivations(root: dict[str, Any]) -> None:
    seats = root["seat_schedule"]["founder_seat_capacity"]
    cycles = root["seat_schedule"]["issuance_cycles_per_seat"]
    legs = [int(leg["amount_atomic"]) for leg in root["base_permission"]["legs"]]
    caps = {entry["id"]: int(entry["cap_atomic"]) for entry in root["channels"]}
    referral = int(root["referral_permission"]["amount_atomic"])

    population = checked_mul(seats, cycles)
    if population is None:
        _fail("ARITHMETIC_OVERFLOW", "seat capacity times cycles exceeds u64")
    schedules = [checked_mul(amount, population) for amount in legs + [referral]]
    display = checked_mul(
        int(root["denomination"]["maximum_supply_display"]),
        int(root["denomination"]["atomic_units_per_display_unit"]),
    )
    if any(value is None for value in schedules) or display is None:
        _fail("ARITHMETIC_OVERFLOW", "a required schedule product exceeds u64")

    if checked_sum(legs) != int(root["base_permission"]["total_atomic"]):
        _fail("SUPPLY_MISMATCH", "base legs do not sum to the base total")
    if display != int(root["denomination"]["maximum_supply_atomic"]):
        _fail("SUPPLY_MISMATCH", "display maximum does not derive the atomic maximum")

    for leg, schedule in zip(root["base_permission"]["legs"], schedules):
        if caps[leg["channel"]] != schedule:
            _fail("SUPPLY_MISMATCH", f"{leg['channel']} cap is not its full schedule")
    if caps[c.REFERRAL_CHANNEL] != schedules[-1]:
        _fail("SUPPLY_MISMATCH", "referral cap is not its full schedule")

    founder = checked_sum(
        [
            caps[entry["id"]]
            for entry in root["channels"]
            if entry["issuance_kind"] != c.DIRECT_MINT
        ]
    )
    direct = checked_sum(
        [
            caps[entry["id"]]
            for entry in root["channels"]
            if entry["issuance_kind"] == c.DIRECT_MINT
        ]
    )
    if founder != c.FOUNDER_CHANNEL_SUBTOTAL:
        _fail("SUPPLY_MISMATCH", "Founder Node channel subtotal differs")
    if direct != c.DIRECT_CHANNEL_SUBTOTAL:
        _fail("SUPPLY_MISMATCH", "direct-mint channel subtotal differs")
    if checked_sum([founder, direct]) != display:
        _fail("SUPPLY_MISMATCH", "channel subtotals do not sum to the maximum")
