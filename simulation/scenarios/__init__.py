"""Deterministic multi-year and adversarial scenarios over the accepted models.

This package adds no model, transition, or schema. Every event it generates
conforms to an event schema already accepted by `founder-economy-simulator-v1`,
`founder-seat-schedule-v1`, `revenue-routing-v1`, or `escrow-payout-v1`, so a
scenario that cannot be expressed here is evidence about those schemas rather
than a reason to widen one.

Each generator is a pure function of its fixed parameters. No wall clock,
environment value, or unseeded random source reaches an event.
"""
