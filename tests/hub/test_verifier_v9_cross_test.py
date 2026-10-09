#!/usr/bin/env python3

"""The test HUB verifier's command, checked by the independent model (ADR 0099).

The command builds every message it signs with the kernel's builders. This
check hands it transactions the Python model encodes, and verifies every
signature it prints against the model's own message constructions with the
pinned libsodium. So a decision passes only if the kernel's builders and the
model's agree byte for byte. The stand-in derivation is restated here from ADR
0099 rather than taken from the command, so it is checked too.
"""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

REPOSITORY = pathlib.Path(__file__).resolve().parents[2]
for _entry in (REPOSITORY, REPOSITORY / "tests" / "differential"):
    if str(_entry) not in sys.path:
        sys.path.insert(0, str(_entry))

from pinned_sodium import Sodium  # noqa: E402
from simulation.economy_transition.merkle import digest  # noqa: E402
from simulation.economy_transition_v6 import messages  # noqa: E402
from simulation.economy_transition_v6.identity import (  # noqa: E402
    Posture,
    escrow_id,
    signer_id,
)
from simulation.economy_transition_v9 import contract as c  # noqa: E402
from simulation.economy_transition_v9.envelope import (  # noqa: E402
    Transaction,
    decode_signed,
    mint_message,
    signing_message,
    unsigned_bytes,
)

VERIFIER_SEED = bytes([0x77]) * 32
CHAIN = bytes([0x0C]) * 32
ALICE = bytes([0xA1]) * 32
BOB = bytes([0xB1]) * 32
FIRST_SIGNER = bytes([0x11]) * 32
VALID_UNTIL = 1_000
NO_SIGNATURE = bytes(64)
REFUSED = 3
USAGE = 2


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


class Command:
    def __init__(self, path: str) -> None:
        self._path = path

    def run(self, *arguments: str) -> tuple[int, dict[str, str]]:
        completed = subprocess.run(
            [self._path, *arguments],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        fields = dict(
            line.split("=", 1) for line in completed.stdout.splitlines() if "=" in line
        )
        return completed.returncode, fields

    def approve(self, secret: bytes, unsigned: bytes, acting: bytes) -> tuple[int, dict[str, str]]:
        return self.run(
            "approve", VERIFIER_SEED.hex(), secret.hex(), unsigned.hex(), acting.hex()
        )


def identity(secret: bytes) -> bytes:
    """ADR 0099's stand-in, restated: one secret derives the identity."""
    return digest("protocol-stack:hub-test-verifier:identity", secret)


def hub_key(sodium: Sodium, secret: bytes) -> bytes:
    """ADR 0099's stand-in, restated: and the same secret derives the HUB key."""
    return sodium.keypair(digest("protocol-stack:hub-test-verifier:hub-key", secret))[0]


def unsigned(kind: int, authority: bytes, body: dict) -> bytes:
    return unsigned_bytes(
        Transaction(
            kind=kind,
            scheme=c.KIND_SCHEME[kind],
            chain_id=CHAIN,
            authority_public_key=authority,
            nonce=1,
            body=body,
            fee_limit=1_000,
            valid_until_height=VALID_UNTIL,
        )
    )


def check_key_and_registration(command: Command, sodium: Sodium) -> None:
    status, fields = command.run("key", VERIFIER_SEED.hex())
    verifier = sodium.keypair(VERIFIER_SEED)[0]
    require(status == 0 and bytes.fromhex(fields["verifier_public_key"]) == verifier,
            "the verifier key is its seed's")

    arguments = ("register", VERIFIER_SEED.hex(), CHAIN.hex(), ALICE.hex(),
                 FIRST_SIGNER.hex(), str(VALID_UNTIL))
    status, fields = command.run(*arguments)
    require(status == 0 and command.run(*arguments)[1] == fields,
            "a registration succeeds and prints the same bytes twice")
    alice, key = identity(ALICE), hub_key(sodium, ALICE)
    require(bytes.fromhex(fields["hub_identity_hash"]) == alice and
            bytes.fromhex(fields["hub_public_key"]) == key,
            "the identity and the HUB key are the stand-in's")

    transaction, signature = decode_signed(bytes.fromhex(fields["signed_transaction"]))
    require((transaction.kind, transaction.scheme, transaction.nonce,
             transaction.fee_limit) == (c.HUB_REGISTER, 2, 0, 0),
            "a registration is a fee-exempt kind 10 at nonce zero")
    require(transaction.authority_public_key == key and
            transaction.body["hub_identity_hash"] == alice and
            transaction.body["first_signer_public_key"] == FIRST_SIGNER,
            "the registration names the person and their first signer")
    require(sodium.verify(verifier, messages.registration_message(
                CHAIN, alice, key, FIRST_SIGNER, VALID_UNTIL),
            transaction.body["verifier_signature"]),
            "the verifier key signs the model's registration message")
    require(sodium.verify(key, signing_message(unsigned_bytes(transaction)), signature),
            "the HUB key signs the envelope")


def check_body_carried_approvals(command: Command, sodium: Sodium) -> None:
    """Each body-carried kind, against the model's message for it."""
    alice, key = identity(ALICE), hub_key(sodium, ALICE)
    escrow = escrow_id(alice, 0)
    recipient = escrow_id(identity(BOB), 0)
    posture = Posture(requires_confirmation=False, min_amount_atomic=5,
                      exempt_slot_mask=3)
    cases = [
        (c.PURCHASE_SEAT,
         {"seat_id": 7, "has_referrer": False, "referrer_escrow_id": bytes(32)},
         messages.purchase_message(CHAIN, alice, 7, VALID_UNTIL)),
        (c.ACTIVATE_SEAT, {"seat_id": 7},
         messages.activation_message(CHAIN, alice, 7, VALID_UNTIL)),
        (c.SET_SECURITY_POSTURE,
         {"requires_confirmation": False, "min_amount_atomic": 5, "exempt_slot_mask": 3},
         messages.posture_relax_message(CHAIN, alice, escrow, posture, VALID_UNTIL)),
        (c.TRANSFER_VERIFIED, {"recipient_escrow_id": recipient, "amount_atomic": 9},
         messages.transfer_confirm_message(CHAIN, alice, escrow, recipient, 9,
                                           VALID_UNTIL)),
    ]
    for kind in (c.MINT_NODE, c.MINT_POOL):
        cases.append((kind, {"seat_id": 7, "destination_escrow_id": escrow},
                      mint_message(CHAIN, alice, kind, 7, escrow, VALID_UNTIL)))
    for kind in (c.MINT_REFERRAL, c.MINT_VERIFIED_USER):
        cases.append((kind, {"destination_escrow_id": escrow},
                      mint_message(CHAIN, alice, kind, 0, escrow, VALID_UNTIL)))

    for kind, body, message in cases:
        raw = unsigned(kind, FIRST_SIGNER, body | {"hub_signature": NO_SIGNATURE})
        status, fields = command.approve(ALICE, raw, escrow)
        require(status == 0 and "signed_transaction" not in fields,
                f"kind {kind} is approved with a HUB signature alone")
        signature = bytes.fromhex(fields["hub_signature"])
        require(sodium.verify(key, message, signature),
                f"kind {kind}'s HUB signature covers the model's message")
        require(not sodium.verify(key, message + b"\x00", signature),
                f"kind {kind}'s HUB signature covers nothing else")


def check_identity_administration(command: Command, sodium: Sodium) -> None:
    """Kinds 13 to 16 come back whole, and are exactly what was sent, signed."""
    alice, key = identity(ALICE), hub_key(sodium, ALICE)
    escrow = escrow_id(alice, 0)
    cases = [
        (c.ESCROW_CREATE, {"hub_identity_hash": alice, "fee_escrow_id": escrow}),
        (c.ESCROW_DELETE, {"hub_identity_hash": alice,
                           "target_escrow_id": escrow_id(alice, 1),
                           "fee_escrow_id": escrow}),
        (c.SIGNER_ADD, {"hub_identity_hash": alice, "escrow_id": escrow,
                        "signer_public_key": bytes([0x13]) * 32}),
        (c.SIGNER_REVOKE, {"hub_identity_hash": alice, "escrow_id": escrow,
                           "signer_id": signer_id(bytes([0x13]) * 32)}),
    ]
    for kind, body in cases:
        raw = unsigned(kind, key, body)
        status, fields = command.approve(ALICE, raw, bytes(32))
        require(status == 0 and "hub_signature" not in fields,
                f"kind {kind} is approved as a whole transaction")
        signed = bytes.fromhex(fields["signed_transaction"])
        transaction, signature = decode_signed(signed)
        require(signed[:-64] == raw, f"kind {kind} comes back exactly as sent")
        require(sodium.verify(key, signing_message(unsigned_bytes(transaction)), signature),
                f"kind {kind}'s envelope is signed by the HUB key")


def check_refusals(command: Command, sodium: Sodium) -> None:
    alice = identity(ALICE)
    add = {"hub_identity_hash": alice, "escrow_id": escrow_id(alice, 0),
           "signer_public_key": bytes([0x13]) * 32}
    alices = unsigned(c.SIGNER_ADD, hub_key(sodium, ALICE), add)
    status, fields = command.approve(BOB, alices, bytes(32))
    require(status == REFUSED and fields.get("refusal") == "not_the_person" and
            bytes.fromhex(fields["hub_identity_hash"]) == identity(BOB),
            "Bob's capture cannot approve Alice's administration, and is named")
    transfer = unsigned(c.TRANSFER, FIRST_SIGNER,
                        {"recipient_escrow_id": bytes(32), "amount_atomic": 1})
    status, fields = command.approve(ALICE, transfer, bytes(32))
    require(status == REFUSED and fields.get("refusal") == "not_a_hub_decision",
            "an unconfirmed transfer takes no HUB proof")
    for broken in (alices[:-1].hex(), "zz", ""):
        status, _ = command.run("approve", VERIFIER_SEED.hex(), ALICE.hex(), broken,
                                bytes(32).hex())
        require(status == USAGE, "bytes that are not a transaction are a usage error")
    status, _ = command.run("register", VERIFIER_SEED.hex(), CHAIN.hex(), ALICE.hex(),
                            FIRST_SIGNER.hex(), "-1")
    require(status == USAGE, "a height that is not a u64 is a usage error")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command")
    parser.add_argument("--libsodium", required=True)
    arguments = parser.parse_args()
    command = Command(arguments.command)
    sodium = Sodium(arguments.libsodium)
    check_key_and_registration(command, sodium)
    check_body_carried_approvals(command, sodium)
    check_identity_administration(command, sodium)
    check_refusals(command, sodium)
    print("hub-test-verifier-v9-cross: four checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
