"""Independent integer-only Founder Economy simulator under the 2026-08-07
founder direction.

This package implements `docs/specifications/founder-economy-manifest-v2.md`
and `docs/specifications/founder-economy-simulator-v2.md` against
`test-vectors/founder-economy-manifest-v2.json`. It is research software: it
proves accounting under a supplied measurement, not measurement integrity,
economic safety, or production readiness.

`simulation/founder_economy/` is the retained v1 model and is not modified by
this package. The two contracts coexist deliberately: v1 records what the M2
evidence proves, and v2 records what the Founder Constitution now directs.
"""

from .engine import simulate
from .manifest import Manifest, ManifestError, load_manifest_file, load_manifest_text
from .validation import InputError, load_events_file, parse_events

__all__ = [
    "InputError",
    "Manifest",
    "ManifestError",
    "load_events_file",
    "load_manifest_file",
    "load_manifest_text",
    "parse_events",
    "simulate",
]
