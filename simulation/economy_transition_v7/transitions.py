"""Version seven's dispatch table: thirteen carried handlers and one rebound.

Version seven changes no transaction. The six authority and identity transitions
— register, create an escrow, delete one, assign a signer, revoke a signer, and
change a posture — and seven of the eight value transitions are version six's
**functions**, not copies of them, and this module names them one by one so the
table a reader audits is a list of thirteen identities and one exception.

`mint_node` is the exception, and it is the only transition in the contract that
reads a surface version seven moved: it calls the settlement's `collect`, which
gained the pool share. Everything else it does — the seat check, the destination
check, the confirmation predicate, the channel caps, the credit, the custody, the
issue, and the mark advance — is unchanged and is imported.

`tests/simulation/economy_transition_v7_execution_test.py` requires this table to
cover the fourteen kinds and to hold version six's own function object for every
kind except 4, so a transition that quietly diverged fails a test.
"""

from __future__ import annotations

from simulation.economy_transition_v6 import transitions as v6
from simulation.economy_transition_v6.envelope import Transaction
from simulation.economy_transition_v6.transitions import (
    activation_mark,
    confirmation_required,
    escrow_create,
    escrow_delete,
    hub_register,
    set_security_posture,
    signer_add,
    signer_revoke,
    _charged,
)

from . import contract as c
from .execution import Outcome, SignatureOracle
from .ledger import Ledger

__all__ = [
    "AUTHORITY_HANDLERS",
    "VERSION_SIX_HANDLERS",
    "activation_mark",
    "confirmation_required",
    "dispatch",
    "escrow_create",
    "escrow_delete",
    "hub_register",
    "set_security_posture",
    "signer_add",
    "signer_revoke",
]

# The six kinds that write authority and identity rather than value. Each is
# version six's function object, so a divergence is impossible rather than
# merely unlikely.
AUTHORITY_HANDLERS = {
    c.HUB_REGISTER: hub_register,
    c.ESCROW_CREATE: escrow_create,
    c.ESCROW_DELETE: escrow_delete,
    c.SIGNER_ADD: signer_add,
    c.SIGNER_REVOKE: signer_revoke,
    c.SET_SECURITY_POSTURE: set_security_posture,
}


def dispatch(
    ledger: Ledger,
    transaction: Transaction,
    escrow: bytes | None,
    oracle: SignatureOracle,
) -> Outcome:
    from . import value_transitions

    handler = AUTHORITY_HANDLERS.get(transaction.kind)
    if handler is not None:
        return handler(ledger, transaction, escrow, oracle)
    return value_transitions.dispatch(ledger, transaction, escrow, oracle)


# Version six's own table, kept reachable so a test can require this module's to
# be it. Reading it here rather than in the test keeps the comparison in the
# module that makes the claim.
VERSION_SIX_HANDLERS = v6._HANDLERS
