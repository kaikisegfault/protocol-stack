"""What version five exists to record: kind 11, and the separation from version four.

Three things are checked here that no earlier version could check at all.

**That kind 11 is implementable.** Its 32-byte field is read as an identity, and
its message is built from one decoded transaction — the identity from the body,
the account from the sender — so a chain holding the transaction bytes and
nothing else can construct the message its signature covers. Version four could
not, which is the defect ADR 0037 records.

**That the correction closes squatting rather than merely moving it.** The same
attack is run under both readings against the same registry: version four's
permits an attacker to link a stranger's account to their own identity and lock
that person out of registration forever, and version five's cannot express the
attempt.

**That the two contracts are separate chains.** Chain identifier, state root,
and economy tree are compared over identical inputs, with version four's
construction first required to reproduce its own accepted vectors so the
comparison is against the real one rather than a lookalike.
"""

from __future__ import annotations

from pathlib import Path

import expected as e
from checker import Checker, read_vectors

from simulation.economy_transition_v4 import envelope as v4_envelope
from simulation.economy_transition_v4 import genesis as v4_genesis
from simulation.economy_transition_v4 import messages as v4_messages
from simulation.economy_transition_v4 import scenario as v4_scenario
from simulation.economy_transition_v4 import state as v4_state
from simulation.economy_transition_v5 import contract as c
from simulation.economy_transition_v5 import (
    envelope,
    genesis,
    identity,
    messages,
    scenario,
    state,
)
from state_checks import COMMON


def check_add_address_body(check: Checker, vector_root: Path) -> None:
    """Kind 11's corrected body: 96 octets, with its 32-byte field an identity."""
    accepted = read_vectors(vector_root / "economy-transition-v4.txt")
    check.agree(
        "add_address.body_bytes",
        e.add_address_body_bytes(),
        c.BODY_BYTES[c.HUB_ADD_ADDRESS],
    )
    check.equal(
        "add_address.body_bytes_unchanged_from_version_four",
        str(c.BODY_BYTES[c.HUB_ADD_ADDRESS])
        == accepted["envelope.body_bytes.hub_add_address"],
    )
    for name, offset, width in e.ADD_ADDRESS_BODY_FIELDS:
        check.equal(f"add_address.field.{name}.offset", offset)
        check.equal(f"add_address.field.{name}.bytes", width)
    check.equal(
        "add_address.shares_a_length_with_remove",
        c.BODY_BYTES[c.HUB_ADD_ADDRESS] == c.BODY_BYTES[c.HUB_REMOVE_ADDRESS],
    )
    check.agree(
        "add_address.rejection_order",
        ",".join(e.ADD_ADDRESS_REJECTION_ORDER),
        ",".join(c.ADD_ADDRESS_REJECTION_ORDER),
    )

    transaction = scenario.recovery_transaction()
    body = envelope.body_bytes(c.HUB_ADD_ADDRESS, transaction.body)
    check.equal("add_address.body_hex", body.hex())
    check.equal("add_address.body_identity_field_hex", body[0:32].hex())
    check.equal(
        "add_address.body_field_is_the_identity",
        body[0:32] == transaction.body["hub_identity_hash"],
    )

    raw = envelope.signed_bytes(transaction, scenario.TRANSFER_SIGNATURE)
    decoded, _ = envelope.decode_signed(raw)
    check.equal("add_address.decoded_field_names", ",".join(sorted(decoded.body)))
    check.equal(
        "add_address.decode_reads_an_identity",
        decoded.body["hub_identity_hash"] == transaction.body["hub_identity_hash"],
    )
    # The bytes are version four's; only the reading moves. Handing version
    # four's encoder the same 32 octets under the field name it knows produces
    # the identical body, which is what "the body stays 96 octets" means.
    check.equal(
        "add_address.bytes_are_version_four_bytes",
        body
        == v4_envelope.body_bytes(
            c.HUB_ADD_ADDRESS,
            {
                "account_id": transaction.body["hub_identity_hash"],
                "hub_signature": transaction.body["hub_signature"],
            },
        ),
    )
    check.equal("add_address.signed_bytes", len(raw))


def check_add_address_message(check: Checker) -> None:
    """The message a chain builds from the transaction and nothing else."""
    transaction = scenario.recovery_transaction()
    derived = messages.address_add_message_for(transaction)
    sender = envelope.sender_account_id(transaction)

    check.agree(
        "add_address.sender_account_id",
        e.account_id(scenario.RECOVERY_PUBLIC_KEY).hex(),
        sender.hex(),
    )
    check.equal("add_address.linked_account", identity.linked_account(transaction).hex())
    check.equal(
        "add_address.linked_account_is_the_sender",
        identity.linked_account(transaction) == sender,
    )
    check.equal("message.hex.address_add_from_transaction", derived.hex())
    check.agree(
        "message.bytes.address_add_from_transaction",
        e.hub_message_bytes("address_add"),
        len(derived),
    )
    # Built from the transaction, and equal to the message the generic builder
    # produces for the same identity and the same account. A chain has both
    # halves; version four had only the second.
    check.equal(
        "add_address.message_is_the_generic_one",
        derived
        == messages.address_add_message(
            transaction.chain_id,
            transaction.body["hub_identity_hash"],
            sender,
            transaction.valid_until_height,
        ),
    )
    check.equal(
        "add_address.a_different_sender_changes_the_message",
        messages.address_add_message_for(scenario.attacker_transaction()) != derived,
    )
    check.equal(
        "add_address.no_other_kind_carries_this_message",
        _message_refusal(scenario.transactions()["hub_remove_address"]),
    )

    for name in sorted(e.MESSAGE_IDENTITY_SOURCE):
        check.agree(
            f"message.identity_source.{name}",
            e.MESSAGE_IDENTITY_SOURCE[name],
            c.MESSAGE_IDENTITY_SOURCE[name],
        )
    check.equal(
        "message.every_identity_is_reachable",
        c.NO_SOURCE not in set(c.MESSAGE_IDENTITY_SOURCE.values()),
    )
    check.agree(
        "message.version_four_address_add_identity_source",
        e.VERSION_FOUR_ADDRESS_ADD_IDENTITY_SOURCE,
        c.VERSION_FOUR_ADDRESS_ADD_IDENTITY_SOURCE,
    )


def _message_refusal(transaction) -> str:
    try:
        messages.address_add_message_for(transaction)
    except envelope.MalformedTransaction:
        return "MALFORMED_TRANSACTION"
    return "accepted"


def check_message_layouts_are_version_four(check: Checker) -> None:
    """Every message's fields are version four's; only its label moves."""
    chain = scenario.CHAIN_ID
    expiry = scenario.VALID_UNTIL_HEIGHT
    who = scenario.ALICE_IDENTITY
    pairs = {
        "registration": (
            messages.registration_message(
                chain, who, scenario.ALICE_KEY, scenario.ALICE_FIRST_ADDRESS, expiry
            ),
            v4_messages.registration_message(
                chain, who, scenario.ALICE_KEY, scenario.ALICE_FIRST_ADDRESS, expiry
            ),
        ),
        "address_add": (
            messages.address_add_message(
                chain, who, scenario.ALICE_SECOND_ADDRESS, expiry
            ),
            v4_messages.address_add_message(
                chain, who, scenario.ALICE_SECOND_ADDRESS, expiry
            ),
        ),
        "address_remove": (
            messages.address_remove_message(
                chain, who, scenario.ALICE_SECOND_ADDRESS, expiry
            ),
            v4_messages.address_remove_message(
                chain, who, scenario.ALICE_SECOND_ADDRESS, expiry
            ),
        ),
        "purchase": (
            messages.purchase_message(
                chain, who, 0, scenario.ALICE_FIRST_ADDRESS, expiry
            ),
            v4_messages.purchase_message(
                chain, who, 0, scenario.ALICE_FIRST_ADDRESS, expiry
            ),
        ),
        "activation": (
            messages.activation_message(chain, who, 0, expiry),
            v4_messages.activation_message(chain, who, 0, expiry),
        ),
        "mint": (
            messages.mint_message(chain, who, 0, expiry),
            v4_messages.mint_message(chain, who, 0, expiry),
        ),
        "mint_biometric_disable": (
            messages.mint_biometric_disable_message(chain, who, 0, expiry),
            v4_messages.mint_biometric_disable_message(chain, who, 0, expiry),
        ),
        "manager": (
            messages.manager_message(
                chain, who, 0, scenario.MANAGER_ACCOUNT_ID, expiry
            ),
            v4_messages.manager_message(
                chain, who, 0, scenario.MANAGER_ACCOUNT_ID, expiry
            ),
        ),
    }
    for name in sorted(pairs):
        five, four = pairs[name]
        five_label, _ = e.HUB_MESSAGES[name]
        four_label = f"protocol-stack:v4:{five_label.split(':', 2)[2]}"
        check.equal(
            f"message.fields_match_version_four.{name}",
            five[len(e.domain(five_label)) :] == four[len(e.domain(four_label)) :],
        )
        check.equal(f"message.differs_from_version_four.{name}", five != four)


def check_squatting(check: Checker) -> None:
    """The second hole the chosen repair closes, run under both readings."""
    victim = scenario.victim_account_id()
    attacker_transaction = scenario.attacker_transaction()

    check.agree(
        "squatting.victim_account_id",
        e.account_id(scenario.VICTIM_PUBLIC_KEY).hex(),
        victim.hex(),
    )
    check.agree(
        "squatting.attacker_account_id",
        e.account_id(scenario.ATTACKER_PUBLIC_KEY).hex(),
        scenario.attacker_account_id().hex(),
    )

    # Version four's reading: the account came from the body, so the attacker
    # names the victim's. The victim can then never register that account, and
    # cannot call removal, because removal is authorized by the identity the
    # account is linked to — the attacker's.
    under_four = scenario.squatting_registry()
    check.equal(
        "squatting.version_four_links_a_strangers_account",
        identity.version_four_add_address(
            under_four, scenario.ATTACKER_IDENTITY, victim
        ),
    )
    check.equal(
        "squatting.version_four_leaves_the_victim_locked_out",
        under_four.register(
            scenario.VICTIM_IDENTITY,
            scenario.VICTIM_HUB_KEY,
            victim,
            scenario.REGISTRATION_HEIGHT,
        ),
    )
    check.equal(
        "squatting.version_four_binds_the_account_to_the_attacker",
        under_four.identity_of(victim) == scenario.ATTACKER_IDENTITY,
    )

    # Version five's reading: the account is the sender, so the attacker's own
    # transaction can only ever link the attacker's own account.
    under_five = scenario.squatting_registry()
    check.equal(
        "squatting.version_five_links_only_the_sender",
        identity.apply_add_address(under_five, attacker_transaction),
    )
    check.equal(
        "squatting.version_five_leaves_the_victim_free",
        under_five.register(
            scenario.VICTIM_IDENTITY,
            scenario.VICTIM_HUB_KEY,
            victim,
            scenario.REGISTRATION_HEIGHT,
        ),
    )
    check.equal(
        "squatting.version_five_never_touched_the_victim",
        under_five.identity_of(victim) == scenario.VICTIM_IDENTITY,
    )
    check.equal(
        "squatting.the_attempt_is_unrepresentable",
        identity.linked_account(attacker_transaction) != victim,
    )


def check_recovery(check: Checker) -> None:
    """A person with an identity, no linked addresses, and a fresh account."""
    registry = scenario.registry()
    transaction = scenario.recovery_transaction()
    account = scenario.recovery_account_id()

    check.equal(
        "recovery.identity_holds_no_addresses",
        registry.identities[scenario.CAROL_IDENTITY].address_count == 0,
    )
    check.equal(
        "recovery.the_sender_is_unlinked", registry.identity_of(account) is None
    )
    check.equal(
        "recovery.add_address", identity.apply_add_address(registry, transaction)
    )
    check.equal(
        "recovery.the_account_is_now_the_persons",
        registry.identity_of(account) == scenario.CAROL_IDENTITY,
    )
    check.equal(
        "recovery.address_count_after",
        registry.identities[scenario.CAROL_IDENTITY].address_count,
    )
    check.equal(
        "recovery.counts_agree_after", registry.counts_agree({scenario.ALICE_IDENTITY: 1})
    )
    check.equal(
        "recovery.replaying_it_is_refused",
        identity.apply_add_address(registry, transaction),
    )
    # The transaction is a fee payer like any other, so the recovering person
    # needs a funded account first. That is the bootstrap dependency version two
    # recorded and the bridge milestone owns; it is stated because recovery is
    # the path it now sits on.
    check.equal("recovery.sender_fee_limit", transaction.fee_limit)
    check.equal(
        "recovery.the_kind_is_not_fee_exempt",
        c.HUB_ADD_ADDRESS in c.TRANSACTION_KINDS and transaction.fee_limit > 0,
    )


def check_version_four_separation(check: Checker, vector_root: Path) -> None:
    """The same inputs under both contracts must give different commitments."""
    accepted = read_vectors(vector_root / "economy-transition-v4.txt")

    # Version four's own constructions, required to reproduce version four's
    # accepted vectors before any difference claim rests on them.
    four_root = v4_state.state_root(**COMMON, economy={})
    check.equal(
        "separation.version_four_root_is_the_accepted_one",
        four_root == accepted["state.root_empty_economy"],
    )
    check.equal(
        "separation.version_four_restatement_is_the_real_one",
        state.predecessor_state_root(4, **COMMON) == four_root,
    )
    five_root = state.state_root(**COMMON, economy={})
    check.equal("separation.state_roots_differ", five_root != four_root)

    four_genesis = v4_genesis.chain_id(scenario.genesis()).hex()
    check.equal(
        "separation.version_four_chain_id_is_the_accepted_one",
        four_genesis == accepted["genesis.chain_id"],
    )
    check.equal(
        "separation.version_four_chain_id_restatement_is_the_real_one",
        genesis.predecessor_chain_id(scenario.genesis(), 4).hex() == four_genesis,
    )
    five_genesis = genesis.chain_id(scenario.genesis()).hex()
    check.equal("separation.chain_ids_differ", five_genesis != four_genesis)

    populated = scenario.populated_economy()
    four_tree = v4_state.economy_root(populated).hex()
    check.equal(
        "separation.version_four_economy_root_is_the_accepted_one",
        four_tree == accepted["state.economy_root_populated"],
    )
    check.equal(
        "separation.economy_roots_differ",
        state.economy_root(populated).hex() != four_tree,
    )
    # The roots differ over an *identical* entry set, which is the claim. The
    # comparison is against version four's own fixture rather than against this
    # one, because comparing a fixture to itself establishes nothing.
    check.equal(
        "separation.the_entries_are_identical",
        populated == v4_scenario.populated_economy(),
    )

    # The genesis fields are held fixed, so the encoded object differs from
    # version four's in the schema-version field alone while the identifier
    # derived from it differs entirely.
    five_bytes = genesis.encode(scenario.genesis())
    four_bytes = v4_genesis.encode(scenario.genesis())
    check.equal(
        "separation.genesis_bytes_are_the_accepted_ones",
        four_bytes.hex() == accepted["genesis.bytes_hex"],
    )
    check.equal("separation.genesis_bytes_length", len(five_bytes))
    check.equal(
        "separation.genesis_bytes_length_is_unchanged",
        len(five_bytes) == len(four_bytes),
    )
    check.equal(
        "separation.genesis_differing_octets",
        sum(1 for a, b in zip(five_bytes, four_bytes) if a != b),
    )
    check.equal(
        "separation.genesis_differs_only_in_the_schema_version",
        five_bytes[:4] == four_bytes[:4] and five_bytes[6:] == four_bytes[6:],
    )

    # A version-four kind-11 transaction is a valid version-five kind-11
    # transaction by shape and a different one by meaning. The chain ID inside
    # the signature preimage is what keeps it from ever executing here.
    four_transaction = v4_scenario.transactions()["hub_add_address"]
    four_raw = v4_envelope.signed_bytes(four_transaction, scenario.TRANSFER_SIGNATURE)
    decoded, _ = envelope.decode_signed(four_raw)
    check.equal("separation.version_four_kind_eleven_decodes", decoded.kind)
    check.equal(
        "separation.version_four_kind_eleven_is_read_as_an_identity",
        decoded.body["hub_identity_hash"] == four_transaction.body["account_id"],
    )
    check.equal(
        "separation.version_four_kind_eleven_binds_a_different_message",
        messages.address_add_message_for(decoded)
        != v4_messages.address_add_message(
            four_transaction.chain_id,
            scenario.ALICE_IDENTITY,
            four_transaction.body["account_id"],
            four_transaction.valid_until_height,
        ),
    )
