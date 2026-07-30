"""Internal participation state invariant checks."""

from __future__ import annotations

from .domain import (
    MAX_U64,
    Manifest,
    Participant,
    ParticipantTotal,
    RoleTotal,
    State,
    checked_add,
    checked_mul,
)


class InvariantError(RuntimeError):
    """The simulator constructed an invalid participation state."""


def assert_invariants(state: State, manifest: Manifest) -> None:
    _assert_u64(state.height, "height")
    if len(state.participants) > manifest.parameters.max_participants:
        raise InvariantError("participant limit exceeded")
    for key, participant in state.participants.items():
        _assert_participant(key, participant, manifest)
    _assert_contributions(state, manifest)
    _assert_budgets(state)


def _assert_participant(
    key: str,
    value: Participant,
    manifest: Manifest,
) -> None:
    if key != value.participant:
        raise InvariantError("participant key mismatch")
    if value.role not in {"validator", "node"}:
        raise InvariantError("invalid participant role")
    if value.phase not in {"pending", "active", "exit_pending", "exited", "removed"}:
        raise InvariantError("invalid participant phase")
    numeric = [
        value.registered_epoch,
        value.activation_epoch,
        value.activated_epoch,
        value.exit_epoch,
        value.unbond_ready_epoch,
        value.jailed_until_epoch,
        value.confirmed_bond,
        value.removed_epoch,
    ]
    for item in numeric:
        if item is not None:
            _assert_u64(item, "participant scalar")
    expected_activation = checked_add(
        value.registered_epoch,
        manifest.parameters.activation_delay_epochs,
    )
    if expected_activation != value.activation_epoch:
        raise InvariantError("invalid activation epoch")
    _assert_participant_role(value, manifest)
    _assert_participant_phase(value, manifest)
    if value.jailed_until_epoch is not None and value.phase not in {
        "active",
        "exit_pending",
    }:
        raise InvariantError("invalid jailed phase")
    if value.recovery_requested and value.jailed_until_epoch is None:
        raise InvariantError("recovery requested without jail")


def _assert_participant_role(value: Participant, manifest: Manifest) -> None:
    if value.role == "validator":
        if value.bond_id is None:
            raise InvariantError("validator lacks bond identifier")
        if value.confirmed_bond == 0:
            raise InvariantError("validator has zero bond confirmation")
        if (
            value.confirmed_bond is not None
            and value.confirmed_bond < manifest.parameters.validator_minimum_bond
        ):
            raise InvariantError("validator bond is below research minimum")
    elif value.bond_id is not None or value.confirmed_bond is not None:
        raise InvariantError("node has validator bond state")


def _assert_participant_phase(value: Participant, manifest: Manifest) -> None:
    if value.phase == "pending" and value.activated_epoch is not None:
        raise InvariantError("pending participant was activated")
    if value.phase in {"active", "exit_pending", "exited"}:
        if value.activated_epoch is None:
            raise InvariantError("nonpending participant lacks activation epoch")
    if (
        value.activated_epoch is not None
        and value.activated_epoch < value.activation_epoch
    ):
        raise InvariantError("participant activated too early")
    if value.phase in {"exit_pending", "exited"} and value.exit_epoch is None:
        raise InvariantError("exiting participant lacks exit epoch")
    if value.phase in {"pending", "active"} and value.exit_epoch is not None:
        raise InvariantError("nonexiting participant has exit epoch")
    if value.phase == "exited":
        expected = value.exit_epoch if value.role == "validator" else None
        if value.unbond_ready_epoch != expected:
            raise InvariantError("invalid exited unbond readiness")
    if value.phase in {"pending", "active", "exit_pending"}:
        if value.unbond_ready_epoch is not None:
            raise InvariantError("live participant has unbond readiness")
    _assert_removed(value, manifest)


def _assert_removed(value: Participant, manifest: Manifest) -> None:
    if value.phase != "removed":
        if value.removed_epoch is not None or value.terminal_reason is not None:
            raise InvariantError("nonremoved participant has terminal record")
        return
    if value.removed_epoch is None or value.terminal_reason is None:
        raise InvariantError("removed participant lacks terminal record")
    if value.role == "node":
        if value.unbond_ready_epoch is not None:
            raise InvariantError("removed node has unbond readiness")
        return
    if value.unbond_ready_epoch is None:
        raise InvariantError("removed validator lacks unbond readiness")
    minimum = checked_add(
        value.removed_epoch,
        manifest.parameters.removal_hold_epochs,
    )
    if minimum is None or value.unbond_ready_epoch < minimum:
        raise InvariantError("removed validator hold is too short")
    if value.exit_epoch is not None and value.unbond_ready_epoch < value.exit_epoch:
        raise InvariantError("removed validator precedes exit epoch")


def _assert_contributions(state: State, manifest: Manifest) -> None:
    expected_participant: dict[tuple[int, str, str], ParticipantTotal] = {}
    for key, value in state.contributions.items():
        epoch, role, participant, kind = key
        _assert_u64(epoch, "contribution epoch")
        if participant not in state.participants:
            raise InvariantError("contribution participant is absent")
        policy = manifest.contributions.get(role, {}).get(kind)
        if policy is None:
            raise InvariantError("unknown contribution policy")
        _assert_positive(value.units, "contribution units")
        weighted = checked_mul(value.units, policy.weight)
        if weighted is None or weighted != value.weighted_units:
            raise InvariantError("invalid weighted contribution")
        total = expected_participant.setdefault(key[:3], ParticipantTotal(0, 0))
        total.raw_units = _must_add(total.raw_units, value.units)
        total.weighted_units = _must_add(total.weighted_units, value.weighted_units)
    if expected_participant != state.participant_totals:
        raise InvariantError("participant contribution aggregates differ")
    _assert_role_totals(state, manifest)


def _assert_role_totals(state: State, manifest: Manifest) -> None:
    expected_roles: dict[tuple[int, str], RoleTotal] = {}
    for key, value in state.participant_totals.items():
        _assert_positive(value.raw_units, "participant raw units")
        _assert_positive(value.weighted_units, "participant weighted units")
        if value.raw_units > manifest.parameters.max_units_per_participant_epoch:
            raise InvariantError("participant unit cap exceeded")
        role = expected_roles.setdefault(key[:2], RoleTotal(0, 0))
        role.weighted_units = _must_add(role.weighted_units, value.weighted_units)
        role.participant_count = _must_add(role.participant_count, 1)
    if expected_roles != state.role_totals:
        raise InvariantError("role contribution aggregates differ")


def _assert_budgets(state: State) -> None:
    for key, budget in state.budgets.items():
        _assert_positive(budget.amount, "budget amount")
        _assert_positive(budget.total_weight, "budget total weight")
        _assert_positive(budget.participant_count, "budget participant count")
        _assert_u64(budget.settled_count, "budget settled count")
        _assert_u64(budget.allocated, "budget allocation")
        role_total = state.role_totals.get(key)
        if (
            role_total is None
            or role_total.weighted_units != budget.total_weight
            or role_total.participant_count != budget.participant_count
        ):
            raise InvariantError("budget snapshot differs from role total")
        matching = {
            ent_key: value
            for ent_key, value in state.entitlements.items()
            if ent_key[:2] == key
        }
        _assert_budget_entitlements(state, budget, matching)
    for key in state.entitlements:
        if key[:2] not in state.budgets:
            raise InvariantError("entitlement lacks budget")


def _assert_budget_entitlements(state: State, budget, matching: dict) -> None:
    if budget.settled_count != len(matching):
        raise InvariantError("budget settled count differs")
    allocated = 0
    for key, entitlement in matching.items():
        _assert_positive(entitlement.participant_weight, "entitlement weight")
        _assert_u64(entitlement.amount, "entitlement amount")
        participant_total = state.participant_totals.get(key)
        if (
            participant_total is None
            or participant_total.weighted_units != entitlement.participant_weight
        ):
            raise InvariantError("entitlement weight differs")
        allocated = _must_add(allocated, entitlement.amount)
    if allocated != budget.allocated or allocated > budget.amount:
        raise InvariantError("budget allocation differs")
    if budget.finalized:
        if budget.settled_count != budget.participant_count:
            raise InvariantError("finalized budget is incomplete")
        if budget.remainder != budget.amount - budget.allocated:
            raise InvariantError("budget remainder differs")
    elif budget.remainder is not None:
        raise InvariantError("open budget has remainder")


def _assert_u64(value: int, name: str) -> None:
    if type(value) is not int or not 0 <= value <= MAX_U64:
        raise InvariantError(f"{name} is outside u64")


def _assert_positive(value: int, name: str) -> None:
    _assert_u64(value, name)
    if value == 0:
        raise InvariantError(f"{name} is zero")


def _must_add(left: int, right: int) -> int:
    result = checked_add(left, right)
    if result is None:
        raise InvariantError("aggregate exceeds u64")
    return result
