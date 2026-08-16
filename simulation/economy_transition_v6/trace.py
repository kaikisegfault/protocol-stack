"""The recorded version-six transition trace: five scenarios, executed.

Each scenario is chosen for what would go undetected otherwise, and each runs
real blocks against a real state rather than asserting an outcome:

1. **registration** — a whole participant created in one atomic execution, the
   entry airdrop that makes the new escrow able to transact, and a forfeiting
   verified-user collection thirty windows later.
2. **recovery** — a person with an identity, no signer, and an escrow that holds
   value assigns a new signer under scheme 2, pays the fee from that escrow, and
   then transacts with the new key. That is the path version four disabled and
   version five could not fund.
3. **compatibility** — the accepted version-one signed transfer, byte for byte,
   admitted and then refused for its recipient; and the same transaction with
   only the recipient replaced, accepted. The byte identity and the execution
   divergence appear in one trace.
4. **posture** — both directions of a change, including a mixed one that tightens
   the slot mask and raises the minimum and therefore needs the HUB signature.
5. **block** — a block that writes a cycle assignment, executes a mint against
   the record it just wrote, and commits a root; and the same block under the
   rejected ordering, where the mint collects nothing and forfeits the day.

**A fixed fee is used throughout, and version six is the first contract under
which that is reachable.** Version two derived that a conforming chain must
permit a zero fee, because a zero genesis allocation and a nonzero fee leave no
account able to pay for the first transaction. Registration is fee-exempt and
pays the entry airdrop, so the first transaction now funds itself and the
accepted version-one devnet fee of 1,000 is usable from genesis.

**No signature is computed anywhere.** A stand-in is an eight-octet counter
padded to 64, recorded in the oracle against the exact key and message it
authorizes; the one real signature in the trace is the accepted version-one
transfer's, taken from `test-vectors/protocol-primitives-v1.txt`.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field

from simulation.economy_transition_v3.settlement import SeatCycle

from . import contract as c
from . import messages
from .block import BlockOutcome, execute_block
from .envelope import Transaction, signed_bytes, signing_message, unsigned_bytes
from .execution import SignatureOracle
from .genesis import Genesis
from .identity import Posture, escrow_id, signer_id
from .ledger import Ledger

SUPPLY_LIMIT = 5_699_395_010_000_000_000
FIXED_FEE = 1_000
NETWORK_ID = 6

VERIFIER_KEY = bytes.fromhex("55" * 32)

ALICE_IDENTITY = bytes.fromhex("a1" * 32)
ALICE_KEY = bytes.fromhex("a2" * 32)
ALICE_SIGNER_KEY = bytes.fromhex("a3" * 32)
BOB_IDENTITY = bytes.fromhex("b1" * 32)
BOB_KEY = bytes.fromhex("b2" * 32)
BOB_SIGNER_KEY = bytes.fromhex("b3" * 32)
CAROL_IDENTITY = bytes.fromhex("e1" * 32)
CAROL_KEY = bytes.fromhex("e2" * 32)
CAROL_SIGNER_KEY = bytes.fromhex("e3" * 32)
MARIA_IDENTITY = bytes.fromhex("c1" * 32)
MARIA_KEY = bytes.fromhex("c2" * 32)
MARIA_LOST_SIGNER_KEY = bytes.fromhex("c3" * 32)
MARIA_NEW_SIGNER_KEY = bytes.fromhex("c4" * 32)
DAVE_IDENTITY = bytes.fromhex("d1" * 32)
DAVE_KEY = bytes.fromhex("d2" * 32)
DAVE_SIGNER_KEY = bytes.fromhex("d3" * 32)

ALICE_ESCROW = escrow_id(ALICE_IDENTITY, 0)
BOB_ESCROW = escrow_id(BOB_IDENTITY, 0)
CAROL_ESCROW = escrow_id(CAROL_IDENTITY, 0)
MARIA_ESCROW = escrow_id(MARIA_IDENTITY, 0)
DAVE_ESCROW = escrow_id(DAVE_IDENTITY, 0)

# The accepted version-one transfer, from `test-vectors/protocol-primitives-v1.txt`.
ACCEPTED_CHAIN_ID = bytes(range(32))
ACCEPTED_SENDER_KEY = bytes.fromhex(
    "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
)
ACCEPTED_RECIPIENT = bytes(range(0x20, 0x40))
ACCEPTED_SIGNATURE = bytes.fromhex(
    "4678857e9c2da9acd3796819bd151958c6497122d962b0600ba51914d0b10d3a"
    "b922b9bba415e4fdc7d120227548a7c0ec87fc66315d01b8f64165944ee82b06"
)
ACCEPTED_NONCE = 1
ACCEPTED_AMOUNT = 1_000_000
ACCEPTED_FEE_LIMIT = 1_000
ACCEPTED_VALID_UNTIL = 42
ACCEPTED_IDENTITY = bytes.fromhex("f1" * 32)
ACCEPTED_HUB_KEY = bytes.fromhex("f2" * 32)
ACCEPTED_ESCROW = escrow_id(ACCEPTED_IDENTITY, 0)

VALID_UNTIL = 10_000_000
ZERO_CONFIRMATION = bytes(c.HUB_SIGNATURE_BYTES)

# Scenario five's window. A seat activated in window 199 has mark 199, so the
# walk at the first height of window 202 covers exactly window 200.
ASSIGNED_WINDOW = 200
BOUNDARY_HEIGHT = (ASSIGNED_WINDOW + 2) * c.CYCLE_BLOCKS
ACTIVATION_HEIGHT = (ASSIGNED_WINDOW - 1) * c.CYCLE_BLOCKS + 10
MET_UPTIME_SECONDS = 72_000
FAILED_UPTIME_SECONDS = 7_200
COLLECTION_HEIGHT = 40 * c.CYCLE_BLOCKS
# A minimum the fixture can straddle from both sides on one entry airdrop.
POSTURE_MINIMUM = 1_000_000


class Signatures:
    """Deterministic stand-ins, recorded against the exact key and message.

    A stand-in is an eight-octet counter padded to 64 octets — unmistakably not
    an Ed25519 signature, and unique per `(key, message)` pair, so a signature
    presented over any other message is simply absent from the table.
    """

    def __init__(self) -> None:
        self.oracle = SignatureOracle()
        self._issued: dict[tuple[bytes, bytes], bytes] = {}

    def sign(self, public_key: bytes, message: bytes) -> bytes:
        existing = self._issued.get((public_key, message))
        if existing is not None:
            return existing
        token = len(self._issued).to_bytes(8, "big") + bytes(56)
        self._issued[(public_key, message)] = token
        return self.oracle.record(public_key, message, token)

    def adopt(self, public_key: bytes, message: bytes, signature: bytes) -> bytes:
        """Record a signature this model did not choose — the accepted one."""
        self._issued[(public_key, message)] = signature
        return self.oracle.record(public_key, message, signature)


@dataclass
class Step:
    """One raw input and the label the vectors record its outcome under.

    `admits` is false for an input the trace offers in order to be refused at
    admission. Such an input performs no state read or write, produces no
    receipt, and never enters the transaction root, so it is tracked apart from
    the executed steps rather than zipped alongside them.
    """

    label: str
    raw: bytes
    admits: bool = True


@dataclass
class Scenario:
    name: str
    ledger: Ledger
    blocks: list[BlockOutcome] = field(default_factory=list)
    labels: list[list[str]] = field(default_factory=list)
    rejected: dict[str, int] = field(default_factory=dict)
    raw_inputs: list[int] = field(default_factory=list)
    notes: dict[str, object] = field(default_factory=dict)
    skipped_blocks: int = 0

    def results(self) -> dict[str, str]:
        recorded: dict[str, str] = {}
        for block, labels in zip(self.blocks, self.labels):
            for label, entry in zip(labels, block.executed):
                recorded[label] = entry.result
        return recorded

    def receipts(self) -> dict[str, bytes]:
        recorded: dict[str, bytes] = {}
        for block, labels in zip(self.blocks, self.labels):
            for label, raw in zip(labels, block.receipts):
                recorded[label] = raw
        return recorded


def build(
    signatures: Signatures,
    ledger: Ledger,
    kind: int,
    authority: bytes,
    nonce: int,
    body: dict,
    valid_until: int = VALID_UNTIL,
    fee_limit: int = FIXED_FEE,
) -> bytes:
    transaction = Transaction(
        kind=kind,
        scheme=c.KIND_SCHEME[kind],
        chain_id=ledger.chain_id,
        authority_public_key=authority,
        nonce=nonce,
        body=body,
        fee_limit=0 if kind == c.HUB_REGISTER else fee_limit,
        valid_until_height=valid_until,
    )
    unsigned = unsigned_bytes(transaction)
    signature = signatures.sign(authority, signing_message(unsigned))
    return signed_bytes(transaction, signature)


def genesis() -> Genesis:
    """A Founder Economy genesis: no allocation, no accounts, a nonzero fee."""
    return Genesis(
        network_id=NETWORK_ID,
        supply_limit=SUPPLY_LIMIT,
        fixed_transfer_fee=FIXED_FEE,
        manifest_digest=bytes.fromhex(c.MANIFEST_DIGEST_HEX),
        verifier_key=VERIFIER_KEY,
    )


def _open(chain_id: bytes | None = None) -> Ledger:
    ledger = Ledger.from_genesis(genesis())
    if chain_id is not None:
        ledger.chain_id = chain_id
    return ledger


def _register(
    signatures: Signatures,
    ledger: Ledger,
    identity: bytes,
    hub_key: bytes,
    signer_key: bytes,
    valid_until: int = VALID_UNTIL,
) -> bytes:
    message = messages.registration_message(
        ledger.chain_id, identity, hub_key, signer_key, valid_until
    )
    return build(
        signatures,
        ledger,
        c.HUB_REGISTER,
        hub_key,
        0,
        {
            "hub_identity_hash": identity,
            "first_signer_public_key": signer_key,
            "verifier_signature": signatures.sign(VERIFIER_KEY, message),
        },
        valid_until=valid_until,
    )


def _run(
    scenario: Scenario,
    signatures: Signatures,
    steps: list[Step],
    uptime: dict[int, list[SeatCycle]] | None = None,
    assignment_is_prologue: bool = True,
) -> BlockOutcome:
    block = execute_block(
        scenario.ledger,
        [step.raw for step in steps],
        signatures.oracle,
        uptime=uptime,
        assignment_is_prologue=assignment_is_prologue,
    )
    scenario.blocks.append(block)
    scenario.labels.append([step.label for step in steps if step.admits])
    scenario.raw_inputs.append(len(steps))
    for step, admission in zip(steps, block.admissions):
        if not step.admits:
            scenario.rejected[step.label] = admission.code
    return block


# --- scenario one: registration -----------------------------------------


def registration_scenario() -> tuple[Scenario, Signatures]:
    """A whole participant in one execution, and the airdrop that funds them."""
    signatures = Signatures()
    scenario = Scenario(name="registration", ledger=_open())
    ledger = scenario.ledger

    _run(
        scenario,
        signatures,
        [
            Step(
                "alice_registers",
                _register(signatures, ledger, ALICE_IDENTITY, ALICE_KEY, ALICE_SIGNER_KEY),
            ),
            Step(
                "alice_registers_again",
                _register(signatures, ledger, ALICE_IDENTITY, ALICE_KEY, ALICE_SIGNER_KEY),
            ),
        ],
    )
    _run(
        scenario,
        signatures,
        [
            Step(
                "bob_registers",
                _register(signatures, ledger, BOB_IDENTITY, BOB_KEY, BOB_SIGNER_KEY),
            ),
            Step(
                "carol_reuses_alices_signer_key",
                _register(
                    signatures, ledger, CAROL_IDENTITY, CAROL_KEY, ALICE_SIGNER_KEY
                ),
            ),
            # An admission failure reads no state, produces no receipt, and never
            # enters the transaction root, so this input leaves the block exactly
            # two transactions wide.
            Step("a_retired_kind_byte", _retired_kind_input(signatures, ledger), admits=False),
            Step("a_foreign_chain_id", _foreign_chain_input(signatures, ledger), admits=False),
        ],
    )
    _run(
        scenario,
        signatures,
        [
            Step(
                "alice_transfers_unconfirmed",
                build(
                    signatures,
                    ledger,
                    c.TRANSFER,
                    ALICE_SIGNER_KEY,
                    1,
                    {"recipient_escrow_id": BOB_ESCROW, "amount_atomic": 1_000_000},
                ),
            ),
            Step(
                "alice_transfers_confirmed",
                _confirmed_transfer(signatures, ledger, 1, BOB_ESCROW, 1_000_000),
            ),
            Step(
                "alice_transfers_to_an_unregistered_recipient",
                build(
                    signatures,
                    ledger,
                    c.TRANSFER,
                    ALICE_SIGNER_KEY,
                    2,
                    {
                        "recipient_escrow_id": ACCEPTED_RECIPIENT,
                        "amount_atomic": 1_000_000,
                    },
                ),
            ),
            Step(
                "alice_collects_before_any_window_completes",
                _verified_user_mint(signatures, ledger, ALICE_IDENTITY, 2, ALICE_ESCROW),
            ),
        ],
    )

    scenario.skipped_blocks = ledger.advance_to(COLLECTION_HEIGHT - 1)
    _run(
        scenario,
        signatures,
        [
            Step(
                "alice_collects_thirty_windows",
                _verified_user_mint(signatures, ledger, ALICE_IDENTITY, 2, ALICE_ESCROW),
            ),
            Step(
                "alice_collects_again_immediately",
                _verified_user_mint(signatures, ledger, ALICE_IDENTITY, 3, ALICE_ESCROW),
            ),
        ],
    )
    scenario.notes["collection_height"] = COLLECTION_HEIGHT
    return scenario, signatures


def _retired_kind_input(signatures: Signatures, ledger: Ledger) -> bytes:
    """A well-formed transfer with kind 9, which version six retired."""
    raw = bytearray(
        build(
            signatures,
            ledger,
            c.TRANSFER,
            ALICE_SIGNER_KEY,
            1,
            {"recipient_escrow_id": BOB_ESCROW, "amount_atomic": 1},
        )
    )
    raw[6] = next(iter(sorted(c.RETIRED_KINDS)))
    return bytes(raw)


def _foreign_chain_input(signatures: Signatures, ledger: Ledger) -> bytes:
    """A well-formed, correctly signed transfer carrying another chain's ID."""
    transaction = Transaction(
        kind=c.TRANSFER,
        scheme=c.SCHEME_SIGNER,
        chain_id=bytes(32),
        authority_public_key=ALICE_SIGNER_KEY,
        nonce=1,
        body={"recipient_escrow_id": BOB_ESCROW, "amount_atomic": 1},
        fee_limit=FIXED_FEE,
        valid_until_height=VALID_UNTIL,
    )
    unsigned = unsigned_bytes(transaction)
    return signed_bytes(
        transaction, signatures.sign(ALICE_SIGNER_KEY, signing_message(unsigned))
    )


def _confirmed_transfer(
    signatures: Signatures,
    ledger: Ledger,
    nonce: int,
    recipient: bytes,
    amount: int,
    identity: bytes = ALICE_IDENTITY,
    hub_key: bytes = ALICE_KEY,
    signer_key: bytes = ALICE_SIGNER_KEY,
    escrow: bytes = ALICE_ESCROW,
) -> bytes:
    message = messages.transfer_confirm_message(
        ledger.chain_id, identity, escrow, recipient, amount, VALID_UNTIL
    )
    return build(
        signatures,
        ledger,
        c.TRANSFER_VERIFIED,
        signer_key,
        nonce,
        {
            "recipient_escrow_id": recipient,
            "amount_atomic": amount,
            "hub_signature": signatures.sign(hub_key, message),
        },
    )


def _verified_user_mint(
    signatures: Signatures,
    ledger: Ledger,
    identity: bytes,
    nonce: int,
    destination: bytes,
    hub_key: bytes = ALICE_KEY,
    signer_key: bytes = ALICE_SIGNER_KEY,
) -> bytes:
    message = messages.mint_message(
        ledger.chain_id, identity, c.MINT_VERIFIED_USER, 0, destination, VALID_UNTIL
    )
    return build(
        signatures,
        ledger,
        c.MINT_VERIFIED_USER,
        signer_key,
        nonce,
        {
            "destination_escrow_id": destination,
            "hub_signature": signatures.sign(hub_key, message),
        },
    )


# --- scenario two: the millionth user -----------------------------------


def millionth_scenario() -> tuple[Scenario, Signatures]:
    """Registration past the enrollment population, which must still succeed.

    **The counter is stamped one short of the population before any block runs**,
    because reaching 999,999 needs 999,999 registrations. Everything after the
    stamp is executed: Alice's registration is the millionth and takes the last
    airdrop, and Dave's is the millionth and first and takes none. The
    consequence that exposes is the one ADR 0042's preferred credit-then-charge
    rule would have produced for every user after the millionth — a zero-balance
    escrow that cannot pay a fee. Fee exemption is what keeps the registration
    itself possible; nothing keeps the account usable until somebody funds it.
    """
    signatures = Signatures()
    scenario = Scenario(name="millionth", ledger=_open())
    ledger = scenario.ledger

    ledger.registry.enrolled_count = c.VERIFIED_USER_POPULATION - 1
    scenario.notes["stamped_enrolled_count"] = c.VERIFIED_USER_POPULATION - 1

    _run(
        scenario,
        signatures,
        [
            Step(
                "alice_registers_inside_the_population",
                _register(signatures, ledger, ALICE_IDENTITY, ALICE_KEY, ALICE_SIGNER_KEY),
            )
        ],
    )
    _run(
        scenario,
        signatures,
        [
            Step(
                "dave_registers_past_the_population",
                _register(signatures, ledger, DAVE_IDENTITY, DAVE_KEY, DAVE_SIGNER_KEY),
            )
        ],
    )
    _run(
        scenario,
        signatures,
        [
            Step(
                "dave_collects_holding_nothing",
                _verified_user_mint(
                    signatures,
                    ledger,
                    DAVE_IDENTITY,
                    1,
                    DAVE_ESCROW,
                    hub_key=DAVE_KEY,
                    signer_key=DAVE_SIGNER_KEY,
                ),
            ),
            Step(
                "dave_transfers_holding_nothing",
                build(
                    signatures,
                    ledger,
                    c.TRANSFER,
                    DAVE_SIGNER_KEY,
                    1,
                    {"recipient_escrow_id": ALICE_ESCROW, "amount_atomic": 1},
                ),
            ),
            # Version one answers this one `ZERO_AMOUNT`, because its order puts
            # that condition first. Version six puts the shared envelope checks
            # ahead of every kind's own conditions, so the same bytes against
            # the same balance answer `INSUFFICIENT_BALANCE`.
            Step(
                "dave_sends_a_zero_amount_holding_nothing",
                build(
                    signatures,
                    ledger,
                    c.TRANSFER,
                    DAVE_SIGNER_KEY,
                    1,
                    {"recipient_escrow_id": ALICE_ESCROW, "amount_atomic": 0},
                ),
            ),
        ],
    )
    # Nothing Dave can sign reaches its own kind's conditions while his escrow
    # cannot cover the fee, so the enrollment refusal is only observable after
    # somebody already inside the ecosystem sends him value.
    _run(
        scenario,
        signatures,
        [
            Step(
                "alice_funds_dave",
                _confirmed_transfer(signatures, ledger, 1, DAVE_ESCROW, 1_000_000),
            )
        ],
    )
    _run(
        scenario,
        signatures,
        [
            Step(
                "dave_collects_with_no_enrollment",
                _verified_user_mint(
                    signatures,
                    ledger,
                    DAVE_IDENTITY,
                    1,
                    DAVE_ESCROW,
                    hub_key=DAVE_KEY,
                    signer_key=DAVE_SIGNER_KEY,
                ),
            )
        ],
    )
    return scenario, signatures


# --- scenario three: recovery -------------------------------------------


def recovery_scenario() -> tuple[Scenario, Signatures]:
    """Maria holds her face and nothing else, and the chain is enough."""
    signatures = Signatures()
    scenario = Scenario(name="recovery", ledger=_open())
    ledger = scenario.ledger

    _run(
        scenario,
        signatures,
        [
            Step(
                "maria_registers",
                _register(
                    signatures, ledger, MARIA_IDENTITY, MARIA_KEY, MARIA_LOST_SIGNER_KEY
                ),
            ),
            Step(
                "bob_registers",
                _register(signatures, ledger, BOB_IDENTITY, BOB_KEY, BOB_SIGNER_KEY),
            ),
        ],
    )
    _run(
        scenario,
        signatures,
        [
            Step(
                "maria_revokes_her_only_signer",
                build(
                    signatures,
                    ledger,
                    c.SIGNER_REVOKE,
                    MARIA_KEY,
                    1,
                    {
                        "hub_identity_hash": MARIA_IDENTITY,
                        "escrow_id": MARIA_ESCROW,
                        "signer_id": signer_id(MARIA_LOST_SIGNER_KEY),
                    },
                ),
            )
        ],
    )
    _run(
        scenario,
        signatures,
        [
            Step(
                "the_revoked_key_still_tries_to_spend",
                build(
                    signatures,
                    ledger,
                    c.TRANSFER,
                    MARIA_LOST_SIGNER_KEY,
                    2,
                    {"recipient_escrow_id": BOB_ESCROW, "amount_atomic": 1_000_000},
                ),
            ),
            Step(
                "maria_assigns_a_new_signer",
                build(
                    signatures,
                    ledger,
                    c.SIGNER_ADD,
                    MARIA_KEY,
                    2,
                    {
                        "hub_identity_hash": MARIA_IDENTITY,
                        "escrow_id": MARIA_ESCROW,
                        "signer_public_key": MARIA_NEW_SIGNER_KEY,
                    },
                ),
            ),
        ],
    )
    _run(
        scenario,
        signatures,
        [
            Step(
                "maria_spends_with_the_new_key",
                _confirmed_transfer(
                    signatures,
                    ledger,
                    3,
                    BOB_ESCROW,
                    1_000_000,
                    identity=MARIA_IDENTITY,
                    hub_key=MARIA_KEY,
                    signer_key=MARIA_NEW_SIGNER_KEY,
                    escrow=MARIA_ESCROW,
                ),
            )
        ],
    )
    return scenario, signatures


# --- scenario four: compatibility ----------------------------------------


def compatibility_scenario() -> tuple[Scenario, Signatures]:
    """The accepted version-one transfer, executed under version six.

    **The chain ID is stamped to the accepted vectors' value** so the accepted
    bytes are admitted rather than refused with `WRONG_CHAIN`; every other field
    is a version-six genesis's. That is the only way the exact 200 octets can
    reach execution at all, and reaching execution is the whole point.
    """
    signatures = Signatures()
    scenario = Scenario(name="compatibility", ledger=_open(chain_id=ACCEPTED_CHAIN_ID))
    ledger = scenario.ledger

    _run(
        scenario,
        signatures,
        [
            Step(
                "the_sender_registers",
                _register(
                    signatures,
                    ledger,
                    ACCEPTED_IDENTITY,
                    ACCEPTED_HUB_KEY,
                    ACCEPTED_SENDER_KEY,
                    valid_until=ACCEPTED_VALID_UNTIL,
                ),
            ),
            Step(
                "bob_registers",
                _register(
                    signatures,
                    ledger,
                    BOB_IDENTITY,
                    BOB_KEY,
                    BOB_SIGNER_KEY,
                    valid_until=ACCEPTED_VALID_UNTIL,
                ),
            ),
        ],
    )
    _run(
        scenario,
        signatures,
        [Step("the_accepted_transfer", accepted_transfer_bytes(signatures))],
    )

    relaxed = Posture(requires_confirmation=False)
    relax_message = messages.posture_relax_message(
        ledger.chain_id, ACCEPTED_IDENTITY, ACCEPTED_ESCROW, relaxed, ACCEPTED_VALID_UNTIL
    )
    _run(
        scenario,
        signatures,
        [
            Step(
                "the_sender_relaxes_its_posture",
                build(
                    signatures,
                    ledger,
                    c.SET_SECURITY_POSTURE,
                    ACCEPTED_SENDER_KEY,
                    1,
                    {
                        "requires_confirmation": False,
                        "min_amount_atomic": 0,
                        "exempt_slot_mask": 0,
                        "hub_signature": signatures.sign(
                            ACCEPTED_HUB_KEY, relax_message
                        ),
                    },
                    valid_until=ACCEPTED_VALID_UNTIL,
                ),
            )
        ],
    )
    _run(
        scenario,
        signatures,
        [
            Step(
                "the_same_transfer_to_a_registered_recipient",
                build(
                    signatures,
                    ledger,
                    c.TRANSFER,
                    ACCEPTED_SENDER_KEY,
                    2,
                    {
                        "recipient_escrow_id": BOB_ESCROW,
                        "amount_atomic": ACCEPTED_AMOUNT,
                    },
                    valid_until=ACCEPTED_VALID_UNTIL,
                    fee_limit=ACCEPTED_FEE_LIMIT,
                ),
            )
        ],
    )
    return scenario, signatures


def accepted_transfer_bytes(signatures: Signatures) -> bytes:
    """The accepted 200 octets, with the accepted signature adopted as-is."""
    transaction = Transaction(
        kind=c.TRANSFER,
        scheme=c.SCHEME_SIGNER,
        chain_id=ACCEPTED_CHAIN_ID,
        authority_public_key=ACCEPTED_SENDER_KEY,
        nonce=ACCEPTED_NONCE,
        body={
            "recipient_escrow_id": ACCEPTED_RECIPIENT,
            "amount_atomic": ACCEPTED_AMOUNT,
        },
        fee_limit=ACCEPTED_FEE_LIMIT,
        valid_until_height=ACCEPTED_VALID_UNTIL,
    )
    unsigned = unsigned_bytes(transaction)
    signatures.adopt(
        ACCEPTED_SENDER_KEY, signing_message(unsigned), ACCEPTED_SIGNATURE
    )
    return signed_bytes(transaction, ACCEPTED_SIGNATURE)


# --- scenario five: the posture -----------------------------------------


def posture_scenario() -> tuple[Scenario, Signatures]:
    """Both directions, including a change that tightens and relaxes at once."""
    signatures = Signatures()
    scenario = Scenario(name="posture", ledger=_open())
    ledger = scenario.ledger

    _run(
        scenario,
        signatures,
        [
            Step(
                "alice_registers",
                _register(signatures, ledger, ALICE_IDENTITY, ALICE_KEY, ALICE_SIGNER_KEY),
            ),
            Step(
                "bob_registers",
                _register(signatures, ledger, BOB_IDENTITY, BOB_KEY, BOB_SIGNER_KEY),
            ),
        ],
    )
    exempt = Posture(exempt_slot_mask=0b1)
    mixed = Posture(min_amount_atomic=POSTURE_MINIMUM)
    strict = Posture()

    _run(
        scenario,
        signatures,
        [
            Step("relax_the_slot_mask_unsigned", _posture(signatures, ledger, 1, exempt, False)),
            Step("relax_the_slot_mask_signed", _posture(signatures, ledger, 1, exempt, True)),
        ],
    )
    _run(
        scenario,
        signatures,
        [
            Step("mixed_change_unsigned", _posture(signatures, ledger, 2, mixed, False)),
            Step("mixed_change_signed", _posture(signatures, ledger, 2, mixed, True)),
        ],
    )
    _run(
        scenario,
        signatures,
        [
            Step(
                "transfer_below_the_minimum",
                build(
                    signatures,
                    ledger,
                    c.TRANSFER,
                    ALICE_SIGNER_KEY,
                    3,
                    {"recipient_escrow_id": BOB_ESCROW, "amount_atomic": POSTURE_MINIMUM - 1},
                ),
            ),
            Step(
                "transfer_at_the_minimum",
                build(
                    signatures,
                    ledger,
                    c.TRANSFER,
                    ALICE_SIGNER_KEY,
                    4,
                    {"recipient_escrow_id": BOB_ESCROW, "amount_atomic": POSTURE_MINIMUM},
                ),
            ),
        ],
    )
    _run(
        scenario,
        signatures,
        [
            Step("tighten_signed", _posture(signatures, ledger, 4, strict, True)),
            Step("tighten_unsigned", _posture(signatures, ledger, 4, strict, False)),
            Step("tighten_to_the_same_posture", _posture(signatures, ledger, 5, strict, False)),
        ],
    )
    return scenario, signatures


def _posture(
    signatures: Signatures, ledger: Ledger, nonce: int, posture: Posture, signed: bool
) -> bytes:
    message = messages.posture_relax_message(
        ledger.chain_id, ALICE_IDENTITY, ALICE_ESCROW, posture, VALID_UNTIL
    )
    return build(
        signatures,
        ledger,
        c.SET_SECURITY_POSTURE,
        ALICE_SIGNER_KEY,
        nonce,
        {
            "requires_confirmation": posture.requires_confirmation,
            "min_amount_atomic": posture.min_amount_atomic,
            "exempt_slot_mask": posture.exempt_slot_mask,
            "hub_signature": (
                signatures.sign(ALICE_KEY, message) if signed else ZERO_CONFIRMATION
            ),
        },
    )


# --- scenario six: the boundary block ------------------------------------


def uptime_records() -> dict[int, list[SeatCycle]]:
    """Window 200's finalised measurement: one seat meets it, one fails."""
    return {
        ASSIGNED_WINDOW: [
            SeatCycle(0, MET_UPTIME_SECONDS, True, ASSIGNED_WINDOW - 1, BOB_IDENTITY),
            SeatCycle(1, FAILED_UPTIME_SECONDS, True, ASSIGNED_WINDOW - 1, None),
        ]
    }


def block_scenario() -> tuple[Scenario, Signatures]:
    """A block writes a cycle assignment and a mint in it collects that cycle."""
    signatures = Signatures()
    scenario = Scenario(name="block", ledger=_open())
    ledger = scenario.ledger
    uptime = uptime_records()

    _run(
        scenario,
        signatures,
        [
            Step(
                "alice_registers",
                _register(signatures, ledger, ALICE_IDENTITY, ALICE_KEY, ALICE_SIGNER_KEY),
            ),
            Step(
                "bob_registers",
                _register(signatures, ledger, BOB_IDENTITY, BOB_KEY, BOB_SIGNER_KEY),
            ),
            Step(
                "carol_registers",
                _register(signatures, ledger, CAROL_IDENTITY, CAROL_KEY, CAROL_SIGNER_KEY),
            ),
        ],
        uptime=uptime,
    )
    scenario.skipped_blocks = ledger.advance_to(ACTIVATION_HEIGHT - 1, uptime)
    _run(
        scenario,
        signatures,
        [
            Step("alice_buys_seat_zero", _purchase(signatures, ledger, 1, 0, BOB_ESCROW)),
            Step(
                "carol_buys_seat_one",
                _purchase(
                    signatures,
                    ledger,
                    1,
                    1,
                    None,
                    identity=CAROL_IDENTITY,
                    hub_key=CAROL_KEY,
                    signer_key=CAROL_SIGNER_KEY,
                ),
            ),
            Step("alice_activates_seat_zero", _activate(signatures, ledger, 2, 0)),
            Step(
                "carol_activates_seat_one",
                _activate(
                    signatures,
                    ledger,
                    2,
                    1,
                    identity=CAROL_IDENTITY,
                    hub_key=CAROL_KEY,
                    signer_key=CAROL_SIGNER_KEY,
                ),
            ),
            # A seat activated in window `w` holds mark `w` while the last
            # assigned window is `w - 2`. Under the literal reading of
            # `NOTHING_TO_MINT` this mint would succeed, collect nothing, and
            # lower the mark by two — which is why the condition is the empty
            # walk range rather than an equality.
            Step(
                "alice_mints_immediately_after_activating",
                _mint_node(signatures, ledger, 3, 0, True),
            ),
        ],
        uptime=uptime,
    )
    scenario.skipped_blocks += ledger.advance_to(BOUNDARY_HEIGHT - 1, uptime)

    rejected = copy.deepcopy(ledger)
    boundary_steps = [
        Step("alice_mints_unconfirmed", _mint_node(signatures, ledger, 3, 0, False)),
        Step("alice_mints_confirmed", _mint_node(signatures, ledger, 3, 0, True)),
        Step("bob_mints_his_referral", _mint_referral(signatures, ledger, 1)),
        Step("alice_mints_again", _mint_node(signatures, ledger, 4, 0, True)),
    ]
    _run(scenario, signatures, boundary_steps, uptime=uptime)
    scenario.notes["boundary_block_index"] = len(scenario.blocks) - 1

    # One more block at the very next height, so the boundary block's root is
    # chained forward by a real successor rather than by an empty claim — and so
    # the window it assigned is not assigned a second time.
    _run(
        scenario,
        signatures,
        [
            Step("bob_mints_his_referral_again", _mint_referral(signatures, ledger, 2)),
            Step("alice_mints_the_day_after", _mint_node(signatures, ledger, 4, 0, True)),
        ],
        uptime=uptime,
    )

    rejected_block = execute_block(
        rejected,
        [step.raw for step in boundary_steps],
        signatures.oracle,
        uptime=uptime,
        assignment_is_prologue=False,
    )
    scenario.notes["rejected_ordering"] = rejected_block
    scenario.notes["rejected_ledger"] = rejected
    scenario.notes["boundary_height"] = BOUNDARY_HEIGHT
    scenario.notes["assigned_window"] = ASSIGNED_WINDOW
    return scenario, signatures


def _purchase(
    signatures: Signatures,
    ledger: Ledger,
    nonce: int,
    seat_id: int,
    referrer: bytes | None,
    identity: bytes = ALICE_IDENTITY,
    hub_key: bytes = ALICE_KEY,
    signer_key: bytes = ALICE_SIGNER_KEY,
) -> bytes:
    message = messages.purchase_message(ledger.chain_id, identity, seat_id, VALID_UNTIL)
    return build(
        signatures,
        ledger,
        c.PURCHASE_SEAT,
        signer_key,
        nonce,
        {
            "seat_id": seat_id,
            "has_referrer": referrer is not None,
            "referrer_escrow_id": referrer if referrer is not None else bytes(32),
            "hub_signature": signatures.sign(hub_key, message),
        },
    )


def _activate(
    signatures: Signatures,
    ledger: Ledger,
    nonce: int,
    seat_id: int,
    identity: bytes = ALICE_IDENTITY,
    hub_key: bytes = ALICE_KEY,
    signer_key: bytes = ALICE_SIGNER_KEY,
) -> bytes:
    message = messages.activation_message(
        ledger.chain_id, identity, seat_id, VALID_UNTIL
    )
    return build(
        signatures,
        ledger,
        c.ACTIVATE_SEAT,
        signer_key,
        nonce,
        {"seat_id": seat_id, "hub_signature": signatures.sign(hub_key, message)},
    )


def _mint_node(
    signatures: Signatures, ledger: Ledger, nonce: int, seat_id: int, confirmed: bool
) -> bytes:
    message = messages.mint_message(
        ledger.chain_id, ALICE_IDENTITY, c.MINT_NODE, seat_id, ALICE_ESCROW, VALID_UNTIL
    )
    return build(
        signatures,
        ledger,
        c.MINT_NODE,
        ALICE_SIGNER_KEY,
        nonce,
        {
            "seat_id": seat_id,
            "destination_escrow_id": ALICE_ESCROW,
            "hub_signature": (
                signatures.sign(ALICE_KEY, message) if confirmed else ZERO_CONFIRMATION
            ),
        },
    )


def _mint_referral(signatures: Signatures, ledger: Ledger, nonce: int) -> bytes:
    message = messages.mint_message(
        ledger.chain_id, BOB_IDENTITY, c.MINT_REFERRAL, 0, BOB_ESCROW, VALID_UNTIL
    )
    return build(
        signatures,
        ledger,
        c.MINT_REFERRAL,
        BOB_SIGNER_KEY,
        nonce,
        {
            "destination_escrow_id": BOB_ESCROW,
            "hub_signature": signatures.sign(BOB_KEY, message),
        },
    )


SCENARIOS = (
    registration_scenario,
    millionth_scenario,
    recovery_scenario,
    compatibility_scenario,
    posture_scenario,
    block_scenario,
)
