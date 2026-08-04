"""Fixed escrow payout contract from escrow-payout-v1.

Every value here is founder-directed or derived in the accepted manifest
specification. The escrow set and its caps are taken from the accepted
founder-economy contract rather than restated, so the two cannot drift apart.
Amounts are native atomic units under the denomination already accepted in
founder-economy-manifest-v1.
"""

from __future__ import annotations

from ..founder_economy import contract as economy

SCHEMA = "protocol-stack/escrow-payout-result/v1"
EVENTS_LABEL = "protocol-stack:escrow-payout:events-v1"
STATE_LABEL = "protocol-stack:escrow-payout:state-v1"
TRACE_LABEL = "protocol-stack:escrow-payout:trace-v1"
RESULT_LABEL = "protocol-stack:escrow-payout:result-v1"

# Read, never written. This model produces no economy state.
ECONOMY_STATE_LABEL = "protocol-stack:founder-economy:state-v1"

DECIMAL_PLACES = economy.DECIMAL_PLACES
ATOMIC_UNITS_PER_DISPLAY_UNIT = economy.ATOMIC_UNITS_PER_DISPLAY_UNIT

# The closed escrow set. A fourth treasury category would require an explicit
# founder decision and a new manifest channel, which this model cannot express.
ESCROW_IDS: tuple[str, ...] = (
    "venture_escrow",
    "community_grants_escrow",
    "developer_incentives_escrow",
)

ESCROW_CAPS: dict[str, int] = {
    escrow_id: economy.CHANNEL_CAPS[escrow_id] for escrow_id in ESCROW_IDS
}

APPROVED = "approved"
REJECTED = "rejected"
DECISIONS = frozenset({APPROVED, REJECTED})


def custody_key(escrow_id: str) -> str:
    """The economy model's singleton custody key for this escrow."""
    return f"{escrow_id}:{economy.SINGLETON_BENEFICIARY_ID}"
