"""Fixed escrow payout contract from escrow-payout-v1 and escrow-payout-v2.

Every value here is founder-directed or derived in the accepted manifest
specification. The escrow set and its caps are taken from the accepted
founder-economy contract rather than restated, so the two cannot drift apart.
Amounts are native atomic units under the denomination already accepted in
founder-economy-manifest-v1, which version two does not change.

The two accepted versions differ in exactly six strings: the five labels this
model writes and the one founder-economy state label it reads. The transitions,
the escrow set, the caps, the rejection order, and the journal buckets are
identical, so they are stated once and selected by a `Binding` rather than
copied into a second package. ADR 0026 records that decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from ..founder_economy import contract as economy_v1
from ..founder_economy_v2 import contract as economy_v2

# The closed escrow set. A fourth treasury category would require an explicit
# founder decision and a new manifest channel, which this model cannot express.
ESCROW_IDS: tuple[str, ...] = (
    "venture_escrow",
    "community_grants_escrow",
    "developer_incentives_escrow",
)

APPROVED = "approved"
REJECTED = "rejected"
DECISIONS = frozenset({APPROVED, REJECTED})

# Version two does not revise the denomination, so it is stated once. The
# loaders of both manifests enforce it independently.
DECIMAL_PLACES = economy_v2.DECIMAL_PLACES
ATOMIC_UNITS_PER_DISPLAY_UNIT = economy_v2.ATOMIC_UNITS_PER_DISPLAY_UNIT


@dataclass(frozen=True)
class Binding:
    """One accepted escrow-payout version and the economy contract it reads.

    `economy_state_label` is the whole compatibility boundary. A founder-economy
    state digest is computed over its own domain label, so a state recorded
    under one version can never satisfy a bind under the other, and the two
    vector files are evidence about disjoint provenance.
    """

    version: str
    schema: str
    events_label: str
    state_label: str
    trace_label: str
    result_label: str
    # Read, never written. This model produces no economy state.
    economy_state_label: str
    economy_channel_caps: Mapping[str, int]

    @property
    def escrow_caps(self) -> dict[str, int]:
        return {escrow_id: self.economy_channel_caps[escrow_id] for escrow_id in ESCROW_IDS}


V1 = Binding(
    version="v1",
    schema="protocol-stack/escrow-payout-result/v1",
    events_label="protocol-stack:escrow-payout:events-v1",
    state_label="protocol-stack:escrow-payout:state-v1",
    trace_label="protocol-stack:escrow-payout:trace-v1",
    result_label="protocol-stack:escrow-payout:result-v1",
    economy_state_label="protocol-stack:founder-economy:state-v1",
    economy_channel_caps=MappingProxyType(dict(economy_v1.CHANNEL_CAPS)),
)

V2 = Binding(
    version="v2",
    schema="protocol-stack/escrow-payout-result/v2",
    events_label="protocol-stack:escrow-payout:events-v2",
    state_label="protocol-stack:escrow-payout:state-v2",
    trace_label="protocol-stack:escrow-payout:trace-v2",
    result_label="protocol-stack:escrow-payout:result-v2",
    economy_state_label="protocol-stack:founder-economy:state-v2",
    economy_channel_caps=MappingProxyType(dict(economy_v2.CHANNEL_CAPS)),
)

BINDINGS: dict[str, Binding] = {V1.version: V1, V2.version: V2}

# The three escrow caps are identical in both accepted economy contracts. That
# is a fact about the revision, not an assumption: ADR 0023 raised the maximum
# supply through the referral channel alone. The verifier records the agreement
# as a derived vector rather than this module asserting it at import.
ESCROW_CAPS: dict[str, int] = V1.escrow_caps


def caps_agree() -> bool:
    """Whether both accepted economy contracts give the same three caps."""
    return V1.escrow_caps == V2.escrow_caps


def custody_key(escrow_id: str) -> str:
    """The economy model's singleton custody key for this escrow.

    Both economy versions use the same singleton beneficiary identifier, so one
    rendering serves both. A version that changed it would change this key and
    would therefore need its own binding entry.
    """
    if economy_v1.SINGLETON_BENEFICIARY_ID != economy_v2.SINGLETON_BENEFICIARY_ID:
        raise AssertionError("the two economy contracts disagree on the singleton id")
    return f"{escrow_id}:{economy_v2.SINGLETON_BENEFICIARY_ID}"
