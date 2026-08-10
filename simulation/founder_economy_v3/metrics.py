"""Derived reporting views. No invariant depends on a metric."""

from __future__ import annotations

from typing import Any

from . import contract as c
from ..common.canonical import format_atomic, required_sum
from .domain import State, founder_accounted, issued_supply, outstanding_permissions


def build_metrics(state: State) -> dict[str, Any]:
    issued = issued_supply(state)
    outstanding = outstanding_permissions(state)
    remaining = required_sum(
        [state.capacity(channel_id) for channel_id in c.CHANNEL_IDS],
        "remaining capacity",
    )
    return {
        "maximum_supply_atomic": format_atomic(c.MAXIMUM_SUPPLY_ATOMIC),
        "issued_supply_atomic": format_atomic(issued),
        "outstanding_permissions_atomic": format_atomic(outstanding),
        "remaining_capacity_atomic": format_atomic(remaining),
        "performance_carry_atomic": format_atomic(state.performance_carry_atomic),
        # The carry conservation identity, reported so a reader can check it
        # against the evaluated key count without replaying the run.
        "founder_accounted_atomic": format_atomic(founder_accounted(state)),
        "unreferred_pool_atomic": format_atomic(
            state.typed_custody.get(
                f"{c.UNREFERRED_POOL_KIND}:{c.SINGLETON_BENEFICIARY_ID}", 0
            )
        ),
        "channels": {
            channel_id: {
                "cap_atomic": format_atomic(c.CHANNEL_CAPS[channel_id]),
                "issued_atomic": format_atomic(state.channels[channel_id].issued_atomic),
                "outstanding_atomic": format_atomic(
                    state.channels[channel_id].outstanding_atomic
                ),
                "remaining_atomic": format_atomic(state.capacity(channel_id)),
            }
            for channel_id in c.CHANNEL_IDS
        },
        "activated_seat_count": len(state.seats),
        "pending_permission_count": len(state.pending_permissions),
        "evaluated_permission_key_count": len(state.evaluated_permission_keys),
        "referral_accrual_key_count": len(state.referral_accrual_keys),
        "bound_uptime_record_count": len(state.bound_uptime_records),
        "accepted_direct_decision_count": len(state.accepted_direct_decision_ids),
    }
