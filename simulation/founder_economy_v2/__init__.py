"""Founder Economy contract under the 2026-08-07 founder direction.

This package implements `docs/specifications/founder-economy-manifest-v2.md`
against `test-vectors/founder-economy-manifest-v2.json`. It currently carries
the contract and its strict loader only; the revised transition model is the
next milestone slice.

`simulation/founder_economy/` is the retained v1 model and is not modified by
this package. The two contracts coexist deliberately: v1 records what the M2
evidence proves, and v2 records what the Founder Constitution now directs.
"""

from .manifest import Manifest, ManifestError, load_manifest_file, load_manifest_text

__all__ = [
    "Manifest",
    "ManifestError",
    "load_manifest_file",
    "load_manifest_text",
]
