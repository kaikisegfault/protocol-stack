"""Internal authority state invariants."""

from __future__ import annotations

from .domain import (
    MAX_U64,
    InvariantError,
    Manifest,
    State,
    active_version,
)


def assert_invariants(state: State, manifest: Manifest) -> None:
    _u64(state.height, "height")
    if set(state.capabilities) != set(manifest.capabilities):
        raise InvariantError("capability keys differ from manifest")
    if len(state.capabilities) > manifest.parameters.max_capabilities:
        raise InvariantError("capability limit exceeded")
    for key, capability in state.capabilities.items():
        if key != (capability.module, capability.capability):
            raise InvariantError("capability key mismatch")
        expected = manifest.capabilities[key]
        if capability.set_id != expected.set_id:
            raise InvariantError("capability set family changed")
        _assert_capability(capability, manifest)
    _assert_identifiers(state)
    _assert_results(state, manifest)


def _assert_capability(capability, manifest: Manifest) -> None:
    versions = capability.versions
    if not versions or len(versions) > manifest.parameters.max_versions_per_capability:
        raise InvariantError("retained version count invalid")
    if [item.version for item in versions] != list(range(1, len(versions) + 1)):
        raise InvariantError("versions are not consecutive")
    if capability.active_version != versions[-1].version:
        raise InvariantError("active version mismatch")
    for index, version in enumerate(versions):
        _u64(version.version, "version", nonzero=True)
        _u64(version.threshold, "threshold", nonzero=True)
        _u64(version.activated_epoch, "activated_epoch")
        if version.retired_epoch is not None:
            _u64(version.retired_epoch, "retired_epoch")
        if (
            not version.members
            or version.members != sorted(set(version.members))
            or len(version.members) > manifest.parameters.max_members_per_set
            or version.threshold > len(version.members)
        ):
            raise InvariantError("version member or threshold shape invalid")
        if version.source not in {"genesis", "rotation", "recovery"}:
            raise InvariantError("unknown version source")
        if version.revoked_members != sorted(set(version.revoked_members)):
            raise InvariantError("revoked members are not a sorted set")
        if not set(version.revoked_members) <= set(version.members):
            raise InvariantError("revocation references an unknown member")
        if index + 1 == len(versions):
            if version.retired_epoch is not None:
                raise InvariantError("active version is retired")
        elif (
            version.retired_epoch is None
            or version.retired_epoch < version.activated_epoch
        ):
            raise InvariantError("retired version epoch invalid")
    active_version(capability)
    if capability.paused:
        if (
            capability.paused_epoch is None
            or capability.pause_reason_digest is None
            or capability.pending_rotation is not None
        ):
            raise InvariantError("paused capability shape invalid")
        _u64(capability.paused_epoch, "paused_epoch")
    elif (
        capability.paused_epoch is not None
        or capability.pause_reason_digest is not None
    ):
        raise InvariantError("unpaused capability retains pause state")
    pending = capability.pending_rotation
    if pending is not None:
        if pending.version != capability.active_version + 1:
            raise InvariantError("pending version is not consecutive")
        if (
            not pending.members
            or pending.members != sorted(set(pending.members))
            or len(pending.members) > manifest.parameters.max_members_per_set
            or not 1 <= pending.threshold <= len(pending.members)
        ):
            raise InvariantError("pending set shape invalid")
        _u64(pending.activation_epoch, "pending activation")


def _assert_identifiers(state: State) -> None:
    sets = [
        state.accepted_event_ids,
        state.accepted_result_ids,
        state.accepted_action_ids,
        state.accepted_proof_ids,
    ]
    if any(type(item) is not str for values in sets for item in values):
        raise InvariantError("accepted identifier is not a string")
    if set(state.authorization_results) - state.accepted_result_ids:
        raise InvariantError("authorization result was not accepted")


def _assert_results(state: State, manifest: Manifest) -> None:
    for key, result in state.authorization_results.items():
        if key != result.result_id:
            raise InvariantError("result key mismatch")
        if result.chain_id != manifest.chain_id:
            raise InvariantError("result chain mismatch")
        binding = state.capabilities.get((result.module, result.capability))
        if binding is None or result.set_id != binding.set_id:
            raise InvariantError("result capability mismatch")
        if result.set_version not in {item.version for item in binding.versions}:
            raise InvariantError("result version missing")
        if result.action_id not in state.accepted_action_ids:
            raise InvariantError("result action was not accepted")
        if not result.valid_from_epoch <= result.authorized_epoch <= result.deadline_epoch:
            raise InvariantError("result epoch outside validity window")
        _u64(result.authorized_height, "authorized height")
        _u64(result.authorized_epoch, "authorized epoch")
        members: set[str] = set()
        proofs: set[str] = set()
        for approval in result.approvals:
            if approval["member"] in members or approval["proof_id"] in proofs:
                raise InvariantError("result approval is duplicated")
            members.add(approval["member"])
            proofs.add(approval["proof_id"])
        if not proofs <= state.accepted_proof_ids:
            raise InvariantError("result proof was not accepted")


def _u64(value: int, name: str, *, nonzero: bool = False) -> None:
    if type(value) is not int or not 0 <= value <= MAX_U64:
        raise InvariantError(f"{name} is outside u64")
    if nonzero and value == 0:
        raise InvariantError(f"{name} is zero")
