"""An independent replay of escrow-payout-v1, sharing no model code.

The vector file was produced from the model, so restating the model's own
arithmetic would prove nothing. This module re-implements the specification
directly: it parses the events with the standard JSON decoder, keeps plain
dictionaries and a plain capability record, and re-derives every rejection from
the specification's ordered conditions rather than from the model's handlers.

The escrow identifiers and caps are written out as literals taken from the
Founder Constitution's maximum-supply allocation table, so a change in the
model's contract module cannot silently move them here too.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

MAX_U64 = (1 << 64) - 1

# Schema strings and digest labels as written in escrow-payout-v1 and
# escrow-payout-v2, so the model and the specification are compared rather than
# one restating the other. The two versions differ in exactly these six strings
# and in the fixture; every transition below is shared, which is the claim the
# two vector files exist to check.
@dataclass(frozen=True)
class Spec:
    version: str
    schema: str
    events_label: str
    state_label: str
    trace_label: str
    result_label: str
    economy_state_label: str
    events_file: str


V1 = Spec(
    version="v1",
    schema="protocol-stack/escrow-payout-result/v1",
    events_label="protocol-stack:escrow-payout:events-v1",
    state_label="protocol-stack:escrow-payout:state-v1",
    trace_label="protocol-stack:escrow-payout:trace-v1",
    result_label="protocol-stack:escrow-payout:result-v1",
    economy_state_label="protocol-stack:founder-economy:state-v1",
    events_file="simulation/escrow_payout/fixtures/research-events-v1.json",
)

V2 = Spec(
    version="v2",
    schema="protocol-stack/escrow-payout-result/v2",
    events_label="protocol-stack:escrow-payout:events-v2",
    state_label="protocol-stack:escrow-payout:state-v2",
    trace_label="protocol-stack:escrow-payout:trace-v2",
    result_label="protocol-stack:escrow-payout:result-v2",
    economy_state_label="protocol-stack:founder-economy:state-v2",
    events_file="simulation/escrow_payout/fixtures/research-events-v2.json",
)

SPECS: dict[str, Spec] = {V1.version: V1, V2.version: V2}


def state_digest(value: Any, economy_state_label: str) -> str:
    """Recompute a founder-economy state digest without the model's helpers.

    This is a second implementation of the accepted `D(L) || JCS(value)` rule
    from protocol-primitives-v1, so agreement with the model on the binding is
    evidence rather than a shared function call.
    """
    label = economy_state_label.encode("ascii")
    body = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(bytes([len(label)]) + label + body).hexdigest()


VENTURE = "venture_escrow"
COMMUNITY = "community_grants_escrow"
DEVELOPER = "developer_incentives_escrow"

# 12,500,100,000 / 2,500,020,000 / 1,250,010,000 display units, 8 decimals.
CAPS: dict[str, int] = {
    VENTURE: 1_250_010_000_000_000_000,
    COMMUNITY: 250_002_000_000_000_000,
    DEVELOPER: 125_001_000_000_000_000,
}
ESCROWS: tuple[str, ...] = (VENTURE, COMMUNITY, DEVELOPER)


@dataclass
class Capability:
    escrow_id: str
    per_payout_maximum: int
    envelope_total: int
    expiry_cycle: int
    spent: int = 0
    revoked: bool = False


@dataclass
class Walk:
    """Plain-dictionary replay of the specification's transitions."""

    bound_state_digest: str | None = None
    current_cycle: int = 0
    opening: dict[str, int] = field(
        default_factory=lambda: {escrow: 0 for escrow in ESCROWS}
    )
    available: dict[str, int] = field(
        default_factory=lambda: {escrow: 0 for escrow in ESCROWS}
    )
    paid_out: dict[str, int] = field(
        default_factory=lambda: {escrow: 0 for escrow in ESCROWS}
    )
    spec: Spec = V1
    capabilities: dict[str, Capability] = field(default_factory=dict)
    recipients: dict[str, dict[str, int]] = field(
        default_factory=lambda: {escrow: {} for escrow in ESCROWS}
    )
    accepted_payouts: list[str] = field(default_factory=list)
    results: list[str] = field(default_factory=list)
    # The strongest containment claim: custody never rises after the bind.
    custody_increases_after_bind: int = 0
    multi_escrow_payouts: int = 0

    def run(self, events: list[dict[str, Any]]) -> None:
        for event in events:
            before = dict(self.available)
            was_bound = self.bound_state_digest is not None
            self.results.append(self.apply(event))
            if was_bound:
                self._observe(before)

    def _observe(self, before: dict[str, int]) -> None:
        """Watch every event after the bind, which is the only custody source."""
        changed = [
            escrow for escrow in ESCROWS if self.available[escrow] != before[escrow]
        ]
        if len(changed) > 1:
            self.multi_escrow_payouts += 1
        for escrow in changed:
            if self.available[escrow] > before[escrow]:
                self.custody_increases_after_bind += 1

    def apply(self, event: dict[str, Any]) -> str:
        kind = event["kind"]
        if kind == "bind_opening_custody":
            return self.bind(event)
        if kind == "grant_capability":
            return self.grant(event)
        if kind == "execute_payout":
            return self.payout(event)
        if kind == "revoke_capability":
            return self.revoke(event)
        return self.advance(event)

    def bind(self, event: dict[str, Any]) -> str:
        if self.bound_state_digest is not None:
            return "ALREADY_BOUND"
        supplied = event["economy_state_result"]
        if supplied is None:
            return "MISSING_RESEARCH_INPUT"
        recomputed = state_digest(supplied["state_value"], self.spec.economy_state_label)
        if recomputed != supplied["state_digest"]:
            return "INVALID_RESEARCH_INPUT"

        custody = supplied["state_value"]["typed_custody"]
        opening = {
            escrow: int(custody.get(f"{escrow}:global", "0")) for escrow in ESCROWS
        }
        for escrow, amount in opening.items():
            if amount > CAPS[escrow]:
                return "CUSTODY_ABOVE_CAP"

        self.bound_state_digest = supplied["state_digest"]
        for escrow, amount in opening.items():
            self.opening[escrow] = amount
            self.available[escrow] = amount
        return "OK"

    def grant(self, event: dict[str, Any]) -> str:
        if self.bound_state_digest is None:
            return "NOT_BOUND"
        if event["capability_id"] in self.capabilities:
            return "REPLAY"
        if event["escrow_id"] not in CAPS:
            return "UNKNOWN_ESCROW"

        per_payout = int(event["per_payout_maximum"])
        envelope = int(event["envelope_total"])
        if per_payout == 0 or envelope == 0:
            return "ZERO_AMOUNT"
        if per_payout > envelope:
            return "INVALID_CAPABILITY"
        if event["expiry_cycle"] < self.current_cycle:
            return "CAPABILITY_EXPIRED"

        self.capabilities[event["capability_id"]] = Capability(
            escrow_id=event["escrow_id"],
            per_payout_maximum=per_payout,
            envelope_total=envelope,
            expiry_cycle=event["expiry_cycle"],
        )
        return "OK"

    def payout(self, event: dict[str, Any]) -> str:
        if event["payout_id"] in self.accepted_payouts:
            return "REPLAY"
        capability = self.capabilities.get(event["capability_id"])
        if capability is None:
            return "UNKNOWN_CAPABILITY"
        if capability.escrow_id != event["escrow_id"]:
            return "ESCROW_MISMATCH"
        if capability.revoked:
            return "CAPABILITY_REVOKED"
        if self.current_cycle > capability.expiry_cycle:
            return "CAPABILITY_EXPIRED"

        amount = int(event["amount_atomic"])
        if amount == 0:
            return "ZERO_AMOUNT"

        approval = event["approval_result"]
        if approval is None:
            return "MISSING_RESEARCH_INPUT"
        if approval["payout_id"] != event["payout_id"]:
            return "INVALID_RESEARCH_INPUT"
        if approval["decision"] != "approved":
            return "APPROVAL_WITHHELD"

        if amount > capability.per_payout_maximum:
            return "PAYOUT_LIMIT_EXCEEDED"
        if capability.spent + amount > capability.envelope_total:
            return "ENVELOPE_EXCEEDED"

        escrow = capability.escrow_id
        if amount > self.available[escrow]:
            return "INSUFFICIENT_CUSTODY"
        if self.paid_out[escrow] + amount > MAX_U64:
            return "ARITHMETIC_OVERFLOW"

        recipient = event["recipient_id"]
        self.available[escrow] -= amount
        self.paid_out[escrow] += amount
        self.recipients[escrow][recipient] = (
            self.recipients[escrow].get(recipient, 0) + amount
        )
        capability.spent += amount
        self.accepted_payouts.append(event["payout_id"])
        return "OK"

    def revoke(self, event: dict[str, Any]) -> str:
        capability = self.capabilities.get(event["capability_id"])
        if capability is None:
            return "UNKNOWN_CAPABILITY"
        if capability.revoked:
            return "ALREADY_REVOKED"
        capability.revoked = True
        return "OK"

    def advance(self, event: dict[str, Any]) -> str:
        if event["cycle_index"] != self.current_cycle:
            return "CYCLE_MISMATCH"
        if self.current_cycle + 1 > MAX_U64:
            return "ARITHMETIC_OVERFLOW"
        self.current_cycle += 1
        return "OK"

    def charged(self, escrow: str) -> int:
        return sum(
            capability.spent
            for capability in self.capabilities.values()
            if capability.escrow_id == escrow
        )

    def credited(self, escrow: str) -> int:
        return sum(self.recipients[escrow].values())


def load_events(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))
