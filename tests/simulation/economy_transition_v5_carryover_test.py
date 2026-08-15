#!/usr/bin/env python3
"""Version five must differ from version four exactly where it says it does.

The vector file's carryover section reads that claim off two recorded files.
This module reads it off the two packages, which catches a different class of
defect: a constant that moved without any vector reaching it.

Both directions matter. A name version four defines and version five drops
would silently narrow the contract, and a name whose value moved without being
declared would widen it.
"""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.economy_transition_v4 import contract as v4
from simulation.economy_transition_v4 import envelope as v4_envelope
from simulation.economy_transition_v4 import scenario as v4_scenario
from simulation.economy_transition_v5 import contract as c
from simulation.economy_transition_v5 import envelope, receipt, scenario, state

# The six constructions the specification's version-identity table lists, plus
# the eight message labels and the two tuples built from them.
DECLARED_DIFFERENCES = frozenset(
    {
        "CHAIN_ID_LABEL",
        "STATE_ROOT_LABEL",
        "STATE_ROOT_SCHEMA_VERSION",
        "ECONOMY_TREE_PREFIX",
        "GENESIS_SCHEMA_VERSION",
        "RECEIPT_VERSION",
        "REGISTRATION_LABEL",
        "ADDRESS_ADD_LABEL",
        "ADDRESS_REMOVE_LABEL",
        "PURCHASE_LABEL",
        "ACTIVATION_LABEL",
        "MINT_LABEL",
        "MINT_BIOMETRIC_DISABLE_LABEL",
        "MANAGER_LABEL",
        "HUB_MESSAGE_LABELS",
        "VERIFIER_SIGNED_LABELS",
    }
)

# What version five adds: the accepted account derivation it is the first to
# need, the identity-source table, and kind 11's rejection order.
DECLARED_ADDITIONS = frozenset(
    {
        "ACCOUNT_ID_LABEL",
        "ACCOUNT_ID_DOMAIN",
        "MESSAGE_IDENTITY_SOURCE",
        "BODY_SOURCE",
        "SENDER_ADDRESS_ENTRY_SOURCE",
        "NAMED_ADDRESS_ENTRY_SOURCE",
        "SEAT_ENTRY_SOURCE",
        "NO_SOURCE",
        "VERSION_FOUR_ADDRESS_ADD_IDENTITY_SOURCE",
        "ADD_ADDRESS_REJECTION_ORDER",
    }
)


def public(module) -> dict[str, object]:
    """Every constant a module exports, excluding modules it imported."""
    return {
        name: getattr(module, name)
        for name in dir(module)
        if not name.startswith("_")
        and not isinstance(getattr(module, name), types.ModuleType)
    }


class ContractNamespaceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.four = public(v4)
        self.five = public(c)

    def test_version_five_defines_everything_version_four_did(self) -> None:
        self.assertEqual(sorted(set(self.four) - set(self.five)), [])

    def test_the_additions_are_the_declared_ones(self) -> None:
        self.assertEqual(set(self.five) - set(self.four), DECLARED_ADDITIONS)

    def test_the_differences_are_the_declared_ones(self) -> None:
        shared = set(self.four) & set(self.five)
        moved = {name for name in shared if self.four[name] != self.five[name]}
        self.assertEqual(moved, DECLARED_DIFFERENCES)

    def test_every_declared_difference_is_a_version_string_or_number(self) -> None:
        """Nothing structural is allowed into the difference set."""
        for name in sorted(DECLARED_DIFFERENCES):
            with self.subTest(name):
                value = self.five[name]
                if isinstance(value, str):
                    self.assertIn("v5", value)
                elif isinstance(value, tuple):
                    self.assertTrue(all("v5" in label for label in value))
                else:
                    self.assertEqual(value, 5)

    def test_the_transaction_signing_labels_stay_at_version_one(self) -> None:
        self.assertEqual(c.SIGN_LABEL, v4.SIGN_LABEL)
        self.assertEqual(c.TX_ID_LABEL, v4.TX_ID_LABEL)
        self.assertTrue(c.SIGN_LABEL.startswith("protocol-stack:v1:"))

    def test_no_width_code_or_bound_moves(self) -> None:
        for name in (
            "HEADER_BYTES",
            "TRAILER_BYTES",
            "SIGNATURE_BYTES",
            "BODY_BYTES",
            "RESULT_CODES",
            "ENTRY_KINDS",
            "ENTRY_KEY_BYTES",
            "ENTRY_VALUE_BYTES",
            "MAX_IDENTITY_ADDRESSES",
            "MAX_SEAT_MANAGERS",
            "MAX_SEATS_PER_IDENTITY",
            "MINT_ACCUMULATION_CAP",
        ):
            with self.subTest(name):
                self.assertEqual(self.five[name], self.four[name])


class SharedImplementationTest(unittest.TestCase):
    """The parts version five imports rather than restates are the same objects."""

    def test_the_key_space_is_version_fours(self) -> None:
        from simulation.economy_transition_v4 import state as v4_state

        for name in ("seat_key", "hub_identity_key", "hub_address_key", "seat_value"):
            with self.subTest(name):
                self.assertIs(getattr(state, name), getattr(v4_state, name))

    def test_the_registry_is_version_fours(self) -> None:
        from simulation.economy_transition_v4 import identity as v4_identity
        from simulation.economy_transition_v5 import identity as v5_identity

        self.assertIs(v5_identity.Registry, v4_identity.Registry)

    def test_the_receipt_layout_is_version_fours(self) -> None:
        from simulation.economy_transition_v4 import receipt as v4_receipt

        self.assertIs(receipt.Receipt, v4_receipt.Receipt)
        self.assertIs(receipt.NON_ISSUING_KINDS, v4_receipt.NON_ISSUING_KINDS)
        self.assertEqual(receipt.RECEIPT_BYTES, v4_receipt.RECEIPT_BYTES)

    def test_the_populated_economy_is_entry_for_entry_version_fours(self) -> None:
        self.assertEqual(scenario.populated_economy(), v4_scenario.populated_economy())

    def test_only_the_tree_prefix_separates_the_two_roots(self) -> None:
        from simulation.economy_transition_v4 import state as v4_state

        entries = scenario.populated_economy()
        self.assertNotEqual(state.economy_root(entries), v4_state.economy_root(entries))


class EnvelopeCarryoverTest(unittest.TestCase):
    """Every kind but 11 encodes identically under both packages."""

    def test_every_other_kind_is_byte_identical(self) -> None:
        for name, transaction in sorted(v4_scenario.transactions().items()):
            if transaction.kind == c.HUB_ADD_ADDRESS:
                continue
            with self.subTest(name):
                self.assertEqual(
                    envelope.signed_bytes(transaction, scenario.TRANSFER_SIGNATURE),
                    v4_envelope.signed_bytes(
                        transaction, scenario.TRANSFER_SIGNATURE
                    ),
                )

    def test_kind_eleven_encodes_the_same_octets_under_a_different_name(self) -> None:
        """The body stays 96 octets; only the name of its 32-byte field moves."""
        four = v4_scenario.transactions()["hub_add_address"]
        five = scenario.add_address_transaction(
            four.body["account_id"], four.sender_public_key, nonce=four.nonce
        )
        self.assertEqual(
            envelope.signed_bytes(five, scenario.TRANSFER_SIGNATURE),
            v4_envelope.signed_bytes(four, scenario.TRANSFER_SIGNATURE),
        )

    def test_the_two_packages_read_those_octets_differently(self) -> None:
        four = v4_scenario.transactions()["hub_add_address"]
        raw = v4_envelope.signed_bytes(four, scenario.TRANSFER_SIGNATURE)
        five_decoded, _ = envelope.decode_signed(raw)
        four_decoded, _ = v4_envelope.decode_signed(raw)
        self.assertEqual(sorted(four_decoded.body), ["account_id", "hub_signature"])
        self.assertEqual(
            sorted(five_decoded.body), ["hub_identity_hash", "hub_signature"]
        )
        self.assertEqual(
            five_decoded.body["hub_identity_hash"], four_decoded.body["account_id"]
        )


if __name__ == "__main__":
    unittest.main()
