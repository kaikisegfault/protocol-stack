"""Binding check for the single remaining research placeholder.

Version one carried four placeholders. Three closed on 2026-08-07: activity and
performance reallocation became derived rules in `uptime.py`, and the referral
became unconditional. Only direct-channel eligibility remains founder-reserved,
and it applies to the four direct-mint channels other than `founder_referral`.

The object must be bound to the exact action it authorizes. A stand-in that
could authorize a different channel, decision, beneficiary, or amount would let
a fixture silently become policy, so binding is total rather than partial.
"""

from __future__ import annotations

from typing import Any

BOUND_FIELDS = ("channel", "decision_id", "beneficiary_id", "amount_atomic")


def bound_to_direct(result: dict[str, Any], event: dict[str, Any]) -> bool:
    return all(result[name] == event[name] for name in BOUND_FIELDS)
