"""A second implementation of the version-three transitions.

This module replays an event array using only `expected.py`, which imports
nothing from `simulation/`. It is not a wrapper around the model: it keeps its
own channel, custody, permission, and carry state and reaches every result code
through its own ordered conditions.

A recorded trace both this walk and the model reproduce has been derived twice.
A walk that called the model would only prove the model equals itself.
"""

from __future__ import annotations

from typing import Any

import expected as e


def record_identity(record: dict[str, Any]) -> tuple[Any, ...]:
    """An injective rendering of a record, standing in for its digest.

    The walk only needs to know whether two records for one window are the same
    record. Recomputing the model's digest would import its labelling and make
    the binding check a restatement rather than a second derivation.
    """
    entries = sorted(record["entries"], key=lambda item: item["seat_id"])
    return (
        record["cycle_window"],
        tuple((entry["seat_id"], entry["uptime_seconds"]) for entry in entries),
    )


class Walk:
    """Independent version-three state and transitions."""

    def __init__(self) -> None:
        self.heights: dict[int, int] = {}
        self.referrers: dict[int, int | None] = {}
        self.last_height: int | None = None
        self.issued: dict[str, int] = {channel: 0 for channel in e.CHANNEL_ORDER}
        self.outstanding: dict[str, int] = {channel: 0 for channel in e.CHANNEL_ORDER}
        self.pending: dict[tuple[int, int], list[tuple[str, str, int]]] = {}
        self.evaluated: set[tuple[int, int]] = set()
        self.accruals: set[tuple[int, int]] = set()
        self.decisions: set[str] = set()
        self.bound: dict[int, tuple[Any, ...]] = {}
        self.custody: dict[str, int] = {}
        self.carry = 0

    # --- helpers ------------------------------------------------------------

    def _reservable(self, legs: list[tuple[str, str, int]]) -> bool:
        requested: dict[str, int] = {}
        for channel, _key, amount in legs:
            requested[channel] = requested.get(channel, 0) + amount
        return all(
            self.issued[channel] + self.outstanding[channel] + amount
            <= e.CHANNEL_CAPS[channel]
            for channel, amount in requested.items()
        )

    def _credit(self, custody_key: str, amount: int) -> None:
        self.custody[custody_key] = self.custody.get(custody_key, 0) + amount

    def _base_legs(self, seat_id: int, record: dict[str, Any], met: bool):
        """The four fixed legs plus the resolved Founder legs, in order."""
        legs = [
            (channel, f"{kind}:global", amount)
            for channel, kind, amount in (
                ("venture_escrow", "venture_escrow", e.BASE_LEGS["venture_escrow"]),
                (
                    "community_grants_escrow",
                    "community_grants_escrow",
                    e.BASE_LEGS["community_grants_escrow"],
                ),
                (
                    "developer_incentives_escrow",
                    "developer_incentives_escrow",
                    e.BASE_LEGS["developer_incentives_escrow"],
                ),
                (
                    "system_creator_issuance_royalty",
                    "system_creator_company",
                    e.BASE_LEGS["system_creator_issuance_royalty"],
                ),
            )
        ]
        if met:
            return legs + [
                ("founder_operator", f"founder_seat:{seat_id:05d}", e.FOUNDER_OPERATOR_LEG)
            ], self.carry

        winners = e.winner_seats(record)
        pot = e.FOUNDER_OPERATOR_LEG + self.carry
        if not winners:
            return legs, pot
        share, remainder = e.equal_split(pot, len(winners))
        legs += [
            ("founder_operator", f"founder_seat:{winner:05d}", share) for winner in winners
        ]
        return legs, remainder

    # --- transitions --------------------------------------------------------

    def activate_seat(self, event: dict[str, Any]) -> str:
        height = int(event["activation_height"])
        code = e.activate_seat(
            self.heights,
            self.last_height,
            event["seat_id"],
            event["referrer_seat_id"],
            height,
        )
        if code != "OK":
            return code
        self.heights[event["seat_id"]] = height
        self.referrers[event["seat_id"]] = event["referrer_seat_id"]
        self.last_height = height
        return "OK"

    def evaluate_base_permission(self, event: dict[str, Any]) -> str:
        record = event["cycle_uptime_record"]
        code = e.evaluate_base_permission(
            self.heights,
            self.evaluated,
            self.bound,
            record_identity,
            event["seat_id"],
            event["cycle_index"],
            record,
        )
        if code != "OK":
            return code

        seat_id = event["seat_id"]
        uptime = next(
            entry["uptime_seconds"]
            for entry in record["entries"]
            if entry["seat_id"] == seat_id
        )
        met = e.met_cycle(uptime)
        legs, carry_after = self._base_legs(seat_id, record, met)
        if not self._reservable(legs):
            return "CHANNEL_CAP"

        for channel, _key, amount in legs:
            self.outstanding[channel] += amount
        self.carry = carry_after
        self.pending[(seat_id, event["cycle_index"])] = legs
        self.evaluated.add((seat_id, event["cycle_index"]))
        self.bound[record["cycle_window"]] = record_identity(record)
        return "OK"

    def accrue_referral(self, event: dict[str, Any]) -> str:
        seat_id = event["seat_id"]
        cycle_index = event["cycle_index"]
        if not 0 <= seat_id <= e.MAX_SEAT_ID or not 0 <= cycle_index <= e.MAX_CYCLE_INDEX:
            return "CYCLE_RANGE"
        if seat_id not in self.heights:
            return "SEAT_NOT_ACTIVATED"
        if (seat_id, cycle_index) in self.accruals:
            return "REPLAY"

        referrer = self.referrers[seat_id]
        custody_key = (
            "unreferred_performance_pool:global"
            if referrer is None
            else f"founder_seat:{referrer:05d}"
        )
        channel = e.REFERRAL_CHANNEL
        if (
            self.issued[channel] + self.outstanding[channel] + e.REFERRAL_AMOUNT
            > e.CHANNEL_CAPS[channel]
        ):
            return "CHANNEL_CAP"
        self.issued[channel] += e.REFERRAL_AMOUNT
        self._credit(custody_key, e.REFERRAL_AMOUNT)
        self.accruals.add((seat_id, cycle_index))
        return "OK"

    def exercise_permission(self, event: dict[str, Any]) -> str:
        seat_id = event["seat_id"]
        cycle_index = event["cycle_index"]
        if not 0 <= seat_id <= e.MAX_SEAT_ID or not 0 <= cycle_index <= e.MAX_CYCLE_INDEX:
            return "CYCLE_RANGE"
        legs = self.pending.get((seat_id, cycle_index))
        if legs is None:
            return "PERMISSION_NOT_FOUND"
        for channel, custody_key, amount in legs:
            self.outstanding[channel] -= amount
            self.issued[channel] += amount
            self._credit(custody_key, amount)
        del self.pending[(seat_id, cycle_index)]
        return "OK"

    def direct_issue(self, event: dict[str, Any]) -> str:
        channel = event["channel"]
        if channel not in e.PLACEHOLDER_DIRECT_CHANNELS:
            return "INVALID_CHANNEL"
        amount = int(event["amount_atomic"])
        if amount == 0:
            return "ZERO_AMOUNT"
        if event["decision_id"] in self.decisions:
            return "REPLAY"
        eligibility = event["eligibility_result"]
        if eligibility is None:
            return "MISSING_RESEARCH_INPUT"
        if any(
            eligibility[name] != event[name]
            for name in ("channel", "decision_id", "beneficiary_id", "amount_atomic")
        ):
            return "INVALID_RESEARCH_INPUT"
        if not eligibility["eligible"]:
            return "NOT_ELIGIBLE"
        if (
            self.issued[channel] + self.outstanding[channel] + amount
            > e.CHANNEL_CAPS[channel]
        ):
            return "CHANNEL_CAP"
        self.issued[channel] += amount
        self._credit(f"direct_beneficiary:{event['beneficiary_id']}", amount)
        self.decisions.add(event["decision_id"])
        return "OK"

    def apply(self, event: dict[str, Any]) -> str:
        return getattr(self, event["kind"])(event)


def replay(events: list[dict[str, Any]]) -> tuple[Walk, list[str]]:
    """Run the whole event array and return the final state and its codes."""
    walk = Walk()
    return walk, [walk.apply(event) for event in events]
