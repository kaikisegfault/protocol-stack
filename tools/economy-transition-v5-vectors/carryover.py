"""Prove that version five moved exactly what it said it moved, and nothing else.

Version five's central claim is negative: "everything else in version four
carries over unchanged and is incorporated by reference". A negative claim is
the hard kind to evidence, because no derivation demonstrates the absence of a
change — a body width that quietly moved would simply be recorded at its new
value and pass every check that derives it.

So this module compares the two recorded files directly. Every key
`test-vectors/economy-transition-v4.txt` carries is classified in advance as
carried, renamed, or revised, and the classification must be total. A carried
key must hold version four's exact value; a revised key must hold a different
one; a renamed key must be gone under its old name and present under its new
one with version four's value. Getting the classification wrong fails in both
directions: an unlisted change lands in the carried set and its values
disagree, and an over-listed one lands in the revised set and its values agree.

The comparison does not mark any key as derived. Every value in version five's
file is still produced by a live run of the model and by the independent
derivation; this is a second, orthogonal reading of the same file.
"""

from __future__ import annotations

from pathlib import Path

from checker import Checker, read_vectors

# Keys whose value legitimately differs, each because version five relabels or
# re-versions the construction behind it.
REVISED: frozenset[str] = frozenset(
    {
        # The eight HUB message labels, and therefore the eight messages.
        "message.label.registration",
        "message.label.address_add",
        "message.label.address_remove",
        "message.label.purchase",
        "message.label.activation",
        "message.label.mint",
        "message.label.mint_biometric_disable",
        "message.label.manager",
        "message.hex.registration",
        "message.hex.address_add",
        "message.hex.address_remove",
        "message.hex.purchase",
        "message.hex.activation",
        "message.hex.mint",
        "message.hex.mint_biometric_disable",
        "message.hex.manager",
        # The receipt version field, and the one encoded receipt that carries it.
        "receipt.version",
        "receipt.encoded_hex",
        # The economy tree prefix, and every root taken under it.
        "state.economy_tree_prefix",
        "state.economy_root_empty",
        "state.economy_root_genesis",
        "state.economy_root_populated",
        # The state-root label and version field, and both roots.
        "state.root_label",
        "state.root_schema_version",
        "state.root_empty_economy",
        "state.root_populated_economy",
        # The genesis schema version, the object it encodes, and its identifier.
        "genesis.schema_version",
        "genesis.chain_id_label",
        "genesis.bytes_hex",
        "genesis.chain_id",
    }
)

# Keys whose claim survives under a new name because the name counts versions.
RENAMED: dict[str, str] = {
    "compatibility.hub_labels_are_version_four": (
        "compatibility.hub_labels_are_version_five"
    ),
    "state.all_four_roots_are_distinct": "state.all_five_roots_are_distinct",
}


def check_carryover(check: Checker, vector_root: Path, recorded: Path) -> None:
    four = read_vectors(vector_root / "economy-transition-v4.txt")
    five = read_vectors(recorded)

    unknown = sorted((REVISED | set(RENAMED)) - set(four))
    for key in unknown:
        check.failures.append(
            f"carryover: {key} is classified but version four does not record it"
        )

    carried = sorted(set(four) - REVISED - set(RENAMED))
    for key in carried:
        if key not in five:
            check.failures.append(f"carryover: {key} is carried but version five drops it")
        elif five[key] != four[key]:
            check.failures.append(
                f"carryover: {key} is classified as carried but moved from "
                f"{four[key]!r} to {five[key]!r}"
            )

    for key in sorted(REVISED):
        if key not in five:
            check.failures.append(f"carryover: {key} is revised but version five drops it")
        elif five[key] == four.get(key):
            check.failures.append(
                f"carryover: {key} is classified as revised and did not move"
            )

    for old, new in sorted(RENAMED.items()):
        if old in five:
            check.failures.append(f"carryover: {old} was renamed but is still recorded")
        if new not in five:
            check.failures.append(f"carryover: {new} is missing")
        elif five[new] != four[old]:
            check.failures.append(
                f"carryover: {new} should carry {four[old]!r}, records {five[new]!r}"
            )

    check.equal("carryover.version_four_keys", len(four))
    check.equal("carryover.carried", len(carried))
    check.equal("carryover.revised", len(REVISED))
    check.equal("carryover.renamed", len(RENAMED))
    check.equal("carryover.added", len(set(five) - set(four) - set(RENAMED.values())))
    check.equal(
        "carryover.classification_is_total",
        len(carried) + len(REVISED) + len(RENAMED) == len(four),
    )
    check.equal("carryover.revised_keys", ",".join(sorted(REVISED)))
    check.equal(
        "carryover.renamed_keys",
        ",".join(f"{old}->{new}" for old, new in sorted(RENAMED.items())),
    )
    # Every revision traces to one of the six constructions the specification's
    # version-identity table lists, or to a message label. Nothing else in
    # version four had a version in it.
    check.equal(
        "carryover.every_revision_is_a_relabelling",
        all(
            key.startswith(("message.label.", "message.hex."))
            or key
            in {
                "receipt.version",
                "receipt.encoded_hex",
                "state.economy_tree_prefix",
                "state.economy_root_empty",
                "state.economy_root_genesis",
                "state.economy_root_populated",
                "state.root_label",
                "state.root_schema_version",
                "state.root_empty_economy",
                "state.root_populated_economy",
                "genesis.schema_version",
                "genesis.chain_id_label",
                "genesis.bytes_hex",
                "genesis.chain_id",
            }
            for key in REVISED
        ),
    )
    # No transaction encoding is revised at all, which is the sharpest form of
    # "the bytes did not move": kind 11's correction changes what a field means
    # and leaves every recorded width, length, and refusal alone.
    check.equal(
        "carryover.no_envelope_vector_is_revised",
        not any(key.startswith(("envelope.", "admission.", "codes.")) for key in REVISED),
    )
    check.equal(
        "carryover.no_state_key_vector_is_revised",
        not any(
            key.startswith(("state.key_", "state.value_", "storage.")) for key in REVISED
        ),
    )
    check.equal(
        "carryover.no_settlement_vector_is_revised",
        not any(
            key.startswith(("cap.", "cycle.", "outage.", "mint.", "referral."))
            for key in REVISED
        ),
    )
