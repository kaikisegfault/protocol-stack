"""The `founder-economy-manifest-v3` contract table and its strict loader.

This package implements `docs/specifications/founder-economy-manifest-v3.md`
against `test-vectors/founder-economy-manifest-v3.json`. Version three exists
because the 2026-08-19 pivot renames issuance channel 9, and a channel
identifier is inside the manifest JSON, which the manifest digest commits to,
which genesis carries, which the chain ID commits to. Version two fixes its
schema string, label, and digest as immutable, so the rename is a version
rather than an edit.

Nothing else moves. The founder-directed table is derived from version two's by
applying the rename, so a changed cap, leg, denomination, or bound cannot be
expressed here.

It is research software: it states an economic input contract and proves the
supply arithmetic of that contract, not measurement integrity, economic safety,
or production readiness. No settlement, transition, or state model lives here;
`economy-transition-v7` and the revised simulator are separate slices.
"""

from .manifest import (
    Manifest,
    ManifestError,
    accept_manifest,
    load_manifest_file,
    load_manifest_text,
)

__all__ = [
    "Manifest",
    "ManifestError",
    "accept_manifest",
    "load_manifest_file",
    "load_manifest_text",
]
