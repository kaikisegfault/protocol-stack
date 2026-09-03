"""Version eight's dispatch table: fourteen carried handlers and two new ones.

Version seven's table is fourteen kinds, thirteen of them version six's own
function objects. Version eight does not touch it: `dispatch` delegates every
carried kind to `simulation.economy_transition_v7.transitions.dispatch` and adds
exactly two rows, so the table a reader audits is one delegation and two
handlers rather than a sixteen-row copy.

Each of the two handlers is a thin envelope around the accepted contract model.
`uptime_transitions.submit_response` and `uptime_transitions.file_dispute` hold
every ordered rejection condition and every state write; what lives here is the
three things a *transition* owes that a condition list does not: which escrow
acts, what the success tail charges, and where the envelope's own fields enter
the transition.

**`valid_until_height` is an envelope field and not a body field**, and the
dispute message binds it. The body is 78 octets and has no room for it, which is
deliberate: the relayer chooses the expiry it submits under and the authority
signed one, so binding the envelope's own value is what makes a held signature
expire rather than letting a relayer restate the bound it was given.

`tests/simulation/economy_transition_v8_execution_test.py` requires the carried
delegation to be version seven's own function object, so a sixteen-row copy that
appeared here later would fail a test rather than pass silently.
"""

from __future__ import annotations

from simulation.economy_transition_v6.transitions import _charged
from simulation.economy_transition_v7 import transitions as v7

from . import contract as c
from .envelope import Transaction
from .execution import Outcome, SignatureOracle
from .ledger import Ledger
from .uptime_transitions import file_dispute, submit_response

__all__ = [
    "VERSION_SEVEN_DISPATCH",
    "challenge_response",
    "dispatch",
    "file_dispute_transition",
]

# Version seven's own dispatch, kept reachable so a test can require this
# module's carried path to be it rather than an equal-looking copy.
VERSION_SEVEN_DISPATCH = v7.dispatch


def dispatch(
    ledger: Ledger,
    transaction: Transaction,
    escrow: bytes | None,
    oracle: SignatureOracle,
) -> Outcome:
    if transaction.kind == c.CHALLENGE_RESPONSE:
        return challenge_response(ledger, transaction, escrow, oracle)
    if transaction.kind == c.FILE_DISPUTE:
        return file_dispute_transition(ledger, transaction, escrow, oracle)
    return VERSION_SEVEN_DISPATCH(ledger, transaction, escrow, oracle)


def challenge_response(
    ledger: Ledger,
    transaction: Transaction,
    escrow: bytes | None,
    oracle: SignatureOracle,
) -> Outcome:
    """Kind 20. Nine ordered conditions, one state write, and no fee.

    **The nonce advances and nothing is collected**, which is the asymmetry the
    founder answer produces: a registration drops its nonce because it has no
    escrow to sequence, and a response keeps its own because it has one. So the
    success tail is `_charged` with its second half removed rather than skipped
    whole, and the receipt records a zero fee against a success — the one
    combination `require_consistent` now permits for two kinds instead of one.
    """
    del oracle
    assert escrow is not None
    outcome = submit_response(ledger.uptime_context(), escrow, transaction.body)
    if not outcome.succeeded:
        return Outcome(result=outcome.code)
    ledger.set_nonce(escrow, ledger.nonce(escrow) + 1)
    return Outcome(result="SUCCESS", fee_charged=0)


def file_dispute_transition(
    ledger: Ledger,
    transaction: Transaction,
    escrow: bytes | None,
    oracle: SignatureOracle,
) -> Outcome:
    """Kind 21. Ten ordered conditions, one bit set, and the fixed fee.

    The envelope's signer relays and pays; the dispute authority signs the body.
    That is kind 10's pattern and the reason neither new kind needs a third
    signature scheme: giving the ecosystem AI the envelope would give it a chain
    account, a nonce sequence, a balance, and a fee obligation, none of which any
    accepted document gives it.
    """
    assert escrow is not None
    body = dict(transaction.body)
    body["valid_until_height"] = transaction.valid_until_height
    outcome = file_dispute(ledger.uptime_context(), body, oracle.verify)
    if not outcome.succeeded:
        return Outcome(result=outcome.code)
    charged = _charged(ledger, escrow)
    return Outcome(result=charged.result, fee_charged=charged.fee_charged)
