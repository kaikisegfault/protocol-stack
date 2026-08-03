"""Independent integer-only Founder Seat sale model.

Implements `docs/specifications/founder-seat-schedule-v1.md`. It models seat
capacity, the USD price schedule, ownership bounds, and proceeds. It is
research software: it proves schedule arithmetic, not payment or custody
safety, and it does not make a seat operable.
"""

from .engine import simulate
from .validation import InputError, load_events_file, parse_events

__all__ = ["InputError", "load_events_file", "parse_events", "simulate"]
