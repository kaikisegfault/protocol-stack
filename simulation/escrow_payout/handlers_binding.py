"""The opening-custody binding transition.

Escrow custody is not a free parameter. The supplied value must be a complete
recorded founder-economy canonical state whose digest this model recomputes
before reading a single amount, so custody that no accepted economy run
produced cannot enter here.

Which economy version that state must come from is the binding's one
version-specific decision, and it is the only place a version reads outside its
own model. A v1 state cannot satisfy a v2 bind, because the digest is computed
over the version's own domain label.
"""

from __future__ import annotations

from typing import Any

from . import contract as c
from ..common.canonical import InvariantError, digest, parse_atomic, required_sum
from .domain import State
from .operations import (
    DECREASE,
    INCREASE,
    BindEffect,
    JournalEntry,
    Outcome,
    entry,
    failure,
)


def bind_opening_custody(
    state: State,
    event: dict[str, Any],
    binding: c.Binding = c.V1,
) -> Outcome:
    if state.bound:
        return failure("ALREADY_BOUND")

    supplied = event["economy_state_result"]
    if supplied is None:
        return failure("MISSING_RESEARCH_INPUT")

    recomputed = _economy_digest(supplied["state_value"], binding)
    if recomputed is None or recomputed != supplied["state_digest"]:
        return failure("INVALID_RESEARCH_INPUT")

    opening = _opening_custody(supplied["state_value"])
    if opening is None:
        return failure("INVALID_RESEARCH_INPUT")

    # The cap comes from the bound economy contract rather than the module
    # default, because this is the one transition whose meaning is version
    # specific. Both accepted versions happen to agree; a future one need not.
    caps = binding.escrow_caps
    for escrow_id, amount in opening:
        if amount > caps[escrow_id]:
            return failure("CUSTODY_ABOVE_CAP")

    return Outcome(
        code="OK",
        effect=BindEffect(state_digest=recomputed, opening=opening),
        journal=_journal(opening),
    )


def _economy_digest(state_value: Any, binding: c.Binding) -> str | None:
    """Recompute the accepted economy state digest over the supplied value."""
    if type(state_value) is not dict:
        return None
    try:
        return digest(binding.economy_state_label, state_value)
    except InvariantError:
        return None


def _opening_custody(state_value: dict[str, Any]) -> tuple[tuple[str, int], ...] | None:
    """Read the three singleton escrow custody keys; a missing key is zero."""
    custody = state_value.get("typed_custody")
    if type(custody) is not dict:
        return None

    opening: list[tuple[str, int]] = []
    for escrow_id in c.ESCROW_IDS:
        raw = custody.get(c.custody_key(escrow_id))
        if raw is None:
            opening.append((escrow_id, 0))
            continue
        amount = parse_atomic(raw)
        if amount is None:
            return None
        opening.append((escrow_id, amount))
    return tuple(opening)


def _journal(opening: tuple[tuple[str, int], ...]) -> list[JournalEntry]:
    """An economy state with three empty escrows binds with an empty journal."""
    total = required_sum([amount for _, amount in opening], "opening custody")
    if total == 0:
        return []
    journal = [entry("economy_custody", DECREASE, total)]
    journal.extend(
        entry(f"custody:{escrow_id}", INCREASE, amount)
        for escrow_id, amount in opening
        if amount != 0
    )
    return journal
