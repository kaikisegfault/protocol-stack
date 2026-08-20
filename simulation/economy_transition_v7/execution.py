"""Admission, escrow resolution, the shared envelope checks, and dispatch.

**Every one of them is version six's and none is restated.** Version seven
changes no transaction: the envelope, its two authorization schemes, the fourteen
kinds, admission's four steps, the shared envelope checks in version one's order,
and the three execution rules ADR 0045 derived are all carried, and the only
reason this module exists at all is that version six's `execute` names version
six's dispatch table by module.

So `execute` here is version six's function with one name rebound, and
everything it calls is imported — including two module-private helpers.
`_resolve` and `_envelope_checks` are private to version six because nothing
outside its package should re-derive which escrow acts or in what order the five
shared checks fire. Version seven is not re-deriving them; it is running the same
two functions. The alternative is an eighty-line second copy of an accepted
rejection order with nothing keeping the two equal, which is the defect ADR 0026,
ADR 0029, and ADR 0046 each exist to avoid.

`tests/simulation/economy_transition_v7_execution_test.py` requires the imported
objects to be version six's own objects rather than equal ones, so a copy that
appeared here later would fail a test rather than pass silently.
"""

from __future__ import annotations

from simulation.economy_transition_v6.execution import (
    ADMISSION_NUMBER,
    SCHEME_TWO_FEE_FIELD,
    Admission,
    Outcome,
    Refused,
    SignatureOracle,
    admit,
    require_zero_confirmation,
)
from simulation.economy_transition_v6.execution import (
    _envelope_checks,
    _resolve,
)
from simulation.economy_transition_v6.envelope import Transaction
from simulation.economy_transition_v6.identity import RegistryError

from . import contract as c
from .ledger import Ledger
from .receipt import Receipt

__all__ = [
    "ADMISSION_NUMBER",
    "SCHEME_TWO_FEE_FIELD",
    "Admission",
    "Outcome",
    "Refused",
    "SignatureOracle",
    "admit",
    "execute",
    "receipt_for",
    "require_zero_confirmation",
]


def execute(ledger: Ledger, transaction: Transaction, oracle: SignatureOracle) -> Outcome:
    """Resolve the acting escrow, apply the shared checks, then the kind's own.

    Every non-success result performs no state write and charges no fee, and the
    transitions validate completely before writing anything, so atomicity is
    structural here exactly as in version six — and the trace checks it by
    requiring the state root to be unchanged across every failure.
    """
    from . import transitions

    try:
        escrow = _resolve(ledger, transaction)
        if transaction.kind != c.HUB_REGISTER:
            _envelope_checks(ledger, transaction, escrow)
        outcome = transitions.dispatch(ledger, transaction, escrow, oracle)
    except Refused as refusal:
        return Outcome(result=refusal.result)
    except RegistryError as refusal:
        return Outcome(result=refusal.code)
    return outcome


def receipt_for(
    transaction_id: bytes, transaction: Transaction, outcome: Outcome
) -> Receipt:
    """The version-seven receipt. The dataclass is version six's; `encode` is not."""
    return Receipt(
        transaction_id=transaction_id,
        kind=transaction.kind,
        result_code=outcome.code,
        fee_charged=outcome.fee_charged,
        issued_atomic=outcome.issued_atomic,
    )
