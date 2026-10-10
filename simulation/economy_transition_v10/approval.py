"""One approval for every body-carried kind, over version nine's rejection orders.

Version ten replaces version nine's five per-action HUB messages with one that
signs the whole transaction. **It changes which message a body approval
verifies over, and nothing else about kinds 2, 3, 4, 5, 17, 18, 19, and 22**:
every rejection condition, its order, the posture rule that decides whether an
approval is required, and the key it verifies against stay version nine's.

So those eight kinds run on version nine's own handlers, and the one change is
made where it belongs. `ApprovalOracle` is the signature oracle a carried
handler is given. When the handler asks whether a HUB key signed one of the five
withdrawn messages, the oracle answers whether that key signed the version-ten
approval of the transaction being executed instead. Every other question — the
dispute authority's, for one — passes through unchanged.

**The key is unchanged as well as the order.** Version nine verifies every body
approval against the recorded HUB key of the identity that owns the acting
escrow: kinds 2, 5, 18, and 19 name that identity directly, kind 17 reads the
acting escrow's owner, and kinds 3, 4, and 22 refuse a seat whose identity is
not that owner before they verify anything. Version ten verifies against the
same key, so nothing about whose approval counts moves with the message.

**A version-nine approval never verifies here.** The oracle never asks about a
withdrawn message itself, so a signature over one is refused for the reason the
specification gives: it signed a different message.
"""

from __future__ import annotations

from simulation.common.canonical import label_prefix
from simulation.economy_transition_v6.execution import SignatureOracle
from simulation.economy_transition_v9 import contract as v9c

from . import contract as c
from .envelope import Transaction
from .messages import approval_message

__all__ = ["ApprovalOracle", "WITHDRAWN_PREFIXES"]

# The five labels version nine's body approvals were signed under, as the
# length-prefixed separators that open each message. A label prefix cannot open
# a message under any other label, so matching on it is exact.
WITHDRAWN_PREFIXES: tuple[bytes, ...] = tuple(
    label_prefix(getattr(v9c, name)) for name in c.WITHDRAWN_IN_V10
)


class ApprovalOracle:
    """A signature oracle bound to the one transaction being executed."""

    def __init__(self, oracle: SignatureOracle, transaction: Transaction) -> None:
        self._oracle = oracle
        self._approval: bytes | None = None
        if transaction.kind in c.APPROVAL_KINDS:
            self._approval = approval_message(transaction)

    def verify(self, public_key: bytes, message: bytes, signature: bytes) -> bool:
        if message.startswith(WITHDRAWN_PREFIXES):
            if self._approval is None:
                # A kind that carries no body approval asked about one. No
                # carried handler does; refusing keeps the answer false rather
                # than letting a withdrawn message verify.
                return False
            return self._oracle.verify(public_key, self._approval, signature)
        return self._oracle.verify(public_key, message, signature)
