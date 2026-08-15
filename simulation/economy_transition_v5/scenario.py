"""The checked-in fixture the version-five vectors are taken over.

Everything version five does not revise uses version four's fixture values
unchanged, and that is deliberate rather than lazy: the vectors require every
carried value to equal the one `test-vectors/economy-transition-v4.txt`
records, and a fixture that moved would make that comparison impossible to
read. The registry, the seats, the managers, the custody entry, the settlement
population, and the genesis fields are therefore version four's, imported.

Three fixtures are new, and each exists for one claim version five makes.

**The recovery transaction** is Carol's. She is the identity version four's
fixture already leaves holding zero addresses, so the kind-11 transaction in
this fixture *is* the path the whole version exists for: a person with an
identity, no linked addresses, and a fresh account they control.

**The squatting pair** is an attacker and a victim, each with a key whose
account is derived rather than declared, so the two readings of kind 11 can be
run against the same registry and compared.

Account identifiers here are derived with the accepted version-one
construction, `H(D("protocol-stack:v1:account") || 0x01 || public_key)`, because
version five's address-add message is built from the sender rather than from an
argument. Version four's fixture declared its account identifiers as constants,
which it could afford to do precisely because nothing derived them.
"""

from __future__ import annotations

from simulation.economy_transition_v4 import scenario as v4
from simulation.economy_transition_v3.settlement import SeatCycle

from . import contract as c
from .envelope import Transaction, account_id
from .genesis import Genesis
from .identity import Registry

# Version four's fixture, carried whole.
CHAIN_ID = v4.CHAIN_ID
SENDER_PUBLIC_KEY = v4.SENDER_PUBLIC_KEY
RECIPIENT_ACCOUNT_ID = v4.RECIPIENT_ACCOUNT_ID
TRANSFER_SIGNATURE = v4.TRANSFER_SIGNATURE

HUB_SIGNATURE = v4.HUB_SIGNATURE
VERIFIER_SIGNATURE = v4.VERIFIER_SIGNATURE
VERIFIER_KEY = v4.VERIFIER_KEY

ALICE_IDENTITY = v4.ALICE_IDENTITY
ALICE_KEY = v4.ALICE_KEY
ALICE_FIRST_ADDRESS = v4.ALICE_FIRST_ADDRESS
ALICE_SECOND_ADDRESS = v4.ALICE_SECOND_ADDRESS

BOB_IDENTITY = v4.BOB_IDENTITY
BOB_KEY = v4.BOB_KEY
BOB_ADDRESS = v4.BOB_ADDRESS

CAROL_IDENTITY = v4.CAROL_IDENTITY
CAROL_KEY = v4.CAROL_KEY
CAROL_ADDRESS = v4.CAROL_ADDRESS

MANAGER_ACCOUNT_ID = v4.MANAGER_ACCOUNT_ID
DECISION_ID = v4.DECISION_ID
BENEFICIARY_ACCOUNT_ID = v4.BENEFICIARY_ACCOUNT_ID
AUTHORIZATION = v4.AUTHORIZATION

FEE_LIMIT = v4.FEE_LIMIT
VALID_UNTIL_HEIGHT = v4.VALID_UNTIL_HEIGHT
REGISTRATION_HEIGHT = v4.REGISTRATION_HEIGHT

# The fresh account Carol reaches her identity from. She holds none of her
# linked addresses, so nothing about her old key is usable and nothing about it
# needs to be.
RECOVERY_PUBLIC_KEY = bytes.fromhex("c5" * 32)

# The squatting pair. Both accounts are derived from their keys, because the
# attack turns entirely on which account a transaction can name.
ATTACKER_IDENTITY = bytes.fromhex("e1" * 32)
ATTACKER_HUB_KEY = bytes.fromhex("e2" * 32)
ATTACKER_PUBLIC_KEY = bytes.fromhex("e3" * 32)
ATTACKER_FIRST_ADDRESS = bytes.fromhex("e9" * 32)

VICTIM_IDENTITY = bytes.fromhex("f1" * 32)
VICTIM_HUB_KEY = bytes.fromhex("f2" * 32)
VICTIM_PUBLIC_KEY = bytes.fromhex("f3" * 32)


def _envelope(kind: int, nonce: int, body: dict, public_key: bytes | None = None):
    return Transaction(
        kind=kind,
        chain_id=CHAIN_ID,
        sender_public_key=SENDER_PUBLIC_KEY if public_key is None else public_key,
        nonce=nonce,
        body=body,
        fee_limit=FEE_LIMIT,
        valid_until_height=VALID_UNTIL_HEIGHT,
    )


def accepted_transfer() -> Transaction:
    """The accepted version-one transfer, expressed as a kind-1 version-five one."""
    return v4.accepted_transfer()


def add_address_transaction(
    hub_identity_hash: bytes, public_key: bytes, nonce: int = 13
) -> Transaction:
    """Kind 11: an identity in the body, and the sender is the account added."""
    return _envelope(
        c.HUB_ADD_ADDRESS,
        nonce,
        {"hub_identity_hash": hub_identity_hash, "hub_signature": HUB_SIGNATURE},
        public_key=public_key,
    )


def recovery_transaction() -> Transaction:
    """Carol, holding no addresses, linking a fresh account she controls."""
    return add_address_transaction(CAROL_IDENTITY, RECOVERY_PUBLIC_KEY)


def recovery_account_id() -> bytes:
    return account_id(RECOVERY_PUBLIC_KEY)


def attacker_transaction() -> Transaction:
    """The attacker's own kind 11, which can only ever link the attacker."""
    return add_address_transaction(ATTACKER_IDENTITY, ATTACKER_PUBLIC_KEY, nonce=1)


def attacker_account_id() -> bytes:
    return account_id(ATTACKER_PUBLIC_KEY)


def victim_account_id() -> bytes:
    """The victim never sends a kind 11 at all; the attack is about their account."""
    return account_id(VICTIM_PUBLIC_KEY)


def transactions() -> dict[str, Transaction]:
    """Version four's set, with kind 11 rebuilt under the corrected reading."""
    built = dict(v4.transactions())
    built["hub_add_address"] = recovery_transaction()
    return built


def registry() -> Registry:
    """Version four's registry fixture, unchanged."""
    return v4.registry()


def squatting_registry() -> Registry:
    """The attacker registered; the victim not yet, which is the whole attack.

    Squatting is worth something only before its target registers: once the
    victim's account is their own, condition 2 refuses the attacker. So the
    fixture is the moment the attacker has to act in.
    """
    built = Registry()
    built.register(
        ATTACKER_IDENTITY, ATTACKER_HUB_KEY, ATTACKER_FIRST_ADDRESS, REGISTRATION_HEIGHT
    )
    return built


# The settlement fixture is version four's, which is version three's, so the
# assignment record must still come out byte-identical to the one version three
# recorded. Nothing about the settlement moves in version five.
CYCLE_WINDOW = v4.CYCLE_WINDOW
OUTAGE_WINDOW = v4.OUTAGE_WINDOW
ASSIGNMENT_HEIGHT = v4.ASSIGNMENT_HEIGHT
CURRENT_MARK = v4.CURRENT_MARK
CAPPED_MARK = v4.CAPPED_MARK

REFERRER_IDENTITY = v4.REFERRER_IDENTITY
CAPPED_REFERRER_IDENTITY = v4.CAPPED_REFERRER_IDENTITY
REFERRER_MARKS = v4.REFERRER_MARKS


def cycle_seats() -> list[SeatCycle]:
    return v4.cycle_seats()


def outage_seats() -> list[SeatCycle]:
    return v4.outage_seats()


def assignments() -> dict[int, object]:
    return v4.assignments()


def assignment_records() -> dict[int, bytes]:
    return v4.assignment_records()


def genesis() -> Genesis:
    """Version four's genesis fields, held fixed on purpose.

    Every field is identical to version four's fixture, so the only thing
    separating the two chains is the version identity itself. That makes the
    separation claim demonstrable rather than asserted: the encoded genesis
    differs from version four's in the schema-version field alone, and the
    chain identifier differs entirely.
    """
    return v4.genesis()


def populated_economy() -> dict[bytes, bytes]:
    """Version four's populated economy, entry for entry.

    No key, value, width, or ordering rule moves in version five, so the entry
    set is identical and only the tree prefix that commits to it differs. That
    is exactly the comparison the separation vectors need: the same entries,
    two different roots.
    """
    return v4.populated_economy()
