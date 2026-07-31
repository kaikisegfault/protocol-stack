"""Shared threshold checks and ordinary outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .domain import AuthoritySet, Manifest, State, Version, current_epoch


@dataclass(frozen=True)
class Outcome:
    accepted: bool
    code: str


def success() -> Outcome:
    return Outcome(accepted=True, code="OK")


def failure(code: str) -> Outcome:
    return Outcome(accepted=False, code=code)


def threshold_prefix(
    state: State,
    manifest: Manifest,
    event: dict,
) -> Outcome | None:
    if event["result_id"] in state.accepted_result_ids:
        return failure("RESULT_REPLAY")
    if event["action_id"] in state.accepted_action_ids:
        return failure("ACTION_REPLAY")
    if event["chain_id"] != manifest.chain_id:
        return failure("DOMAIN_MISMATCH")
    return None


def check_window(
    state: State,
    manifest: Manifest,
    event: dict,
) -> Outcome | None:
    start = event["valid_from_epoch"]
    deadline = event["deadline_epoch"]
    if start > deadline:
        return failure("INVALID_TARGET")
    if deadline - start > manifest.parameters.max_action_lifetime_epochs:
        return failure("INVALID_TARGET")
    epoch = current_epoch(state, manifest)
    if epoch < start:
        return failure("TOO_EARLY")
    if epoch > deadline:
        return failure("EXPIRED")
    return None


def check_approvals(
    state: State,
    manifest: Manifest,
    event: dict,
    required_sets: Iterable[AuthoritySet | Version],
) -> Outcome | None:
    approvals = event["approvals"]
    if not approvals or len(approvals) > manifest.parameters.max_approvals_per_result:
        return failure("LIMIT")
    sets = list(required_sets)
    allowed = set().union(*(set(item.members) for item in sets))
    event_proofs: set[str] = set()
    event_members: set[str] = set()
    for approval in approvals:
        proof_id = approval["proof_id"]
        member = approval["member"]
        if proof_id in state.accepted_proof_ids or proof_id in event_proofs:
            return failure("PROOF_REPLAY")
        if member in event_members:
            return failure("DUPLICATE_MEMBER")
        if member not in allowed:
            return failure("UNAUTHORIZED_MEMBER")
        event_proofs.add(proof_id)
        event_members.add(member)
    for authority_set in sets:
        count = len(event_members & set(authority_set.members))
        if count < authority_set.threshold:
            return failure("THRESHOLD")
    return None


def proposed_set(
    manifest: Manifest,
    event: dict,
    set_id: str,
) -> AuthoritySet | Outcome:
    members = event["next_members"]
    if len(members) > manifest.parameters.max_members_per_set:
        return failure("LIMIT")
    threshold = event["next_threshold"]
    if threshold == 0 or threshold > len(members):
        return failure("INVALID_TARGET")
    return AuthoritySet(
        set_id=set_id,
        version=event["next_version"],
        members=tuple(members),
        threshold=threshold,
    )
