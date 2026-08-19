"""Strict Founder Economy v2 manifest loading with the accepted failure order.

Version two binds the shared ordered loader to its own contract table. The
stages, their order, and every result code are unchanged from when this module
carried them itself; `founder-economy-manifest-v2.txt` executes each one and
pins the canonical length and digest, so the binding is checked rather than
asserted.
"""

from __future__ import annotations

from . import contract as c
from ..founder_economy_manifest.loader import (
    Manifest,
    ManifestError,
    ManifestLoader,
    parse_json,
)

_LOADER = ManifestLoader(c)

load_manifest_file = _LOADER.load_file
load_manifest_text = _LOADER.load_text
accept_manifest = _LOADER.accept

__all__ = [
    "Manifest",
    "ManifestError",
    "accept_manifest",
    "load_manifest_file",
    "load_manifest_text",
    "parse_json",
]
