"""Independent integer-only Founder Economy simulator.

Implements `docs/specifications/founder-economy-simulator-v1.md` against the
accepted `test-vectors/founder-economy-manifest-v1.json` contract. It is
research software: it proves accounting, not economic or production safety.
"""

from .engine import simulate
from .manifest import Manifest, ManifestError, load_manifest_file
from .validation import InputError, load_events_file, parse_events

__all__ = [
    "InputError",
    "Manifest",
    "ManifestError",
    "load_events_file",
    "load_manifest_file",
    "parse_events",
    "simulate",
]
