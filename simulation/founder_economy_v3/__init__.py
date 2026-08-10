"""Independent integer-only Founder Economy simulator with the cycle boundary
and record completeness enforced.

This package implements `docs/specifications/founder-economy-simulator-v3.md`
against the accepted `test-vectors/founder-economy-manifest-v2.json`. The
manifest is not re-versioned, because no founder-directed figure moves, so this
package binds `simulation/founder_economy_v2/`'s manifest layer and
`simulation/cycle_boundary/`'s window grid rather than copying either.

It is research software: it proves accounting under an enforced schedule and a
complete record, not measurement integrity, economic safety, or production
readiness.

`simulation/founder_economy/` and `simulation/founder_economy_v2/` are the
retained v1 and v2 models and are not modified by this package. All three
contracts coexist deliberately: each records what a particular body of accepted
evidence proves.
"""

from .engine import simulate
from .validation import InputError, load_events_file, parse_events

__all__ = [
    "InputError",
    "load_events_file",
    "parse_events",
    "simulate",
]
