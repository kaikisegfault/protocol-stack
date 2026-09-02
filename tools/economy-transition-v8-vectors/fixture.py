"""The one recorded fixture every check runs against.

Fixed, small, and stated here rather than in each check, so a value that moves
moves in one place. Nothing in it is founder-directed: the keys and the network
identifier are arbitrary octets chosen to be distinguishable in a hex dump, and
every founder figure the checks touch is read from an accepted vector file.
"""

from __future__ import annotations

from simulation.economy_transition_v8 import contract as c
from simulation.economy_transition_v8.genesis import Genesis

NETWORK_ID = 8
SUPPLY_LIMIT = 5_699_395_010_000_000_000
FIXED_TRANSFER_FEE = 1_000

VERIFIER_KEY = bytes([0xA1]) * 32
DISPUTE_AUTHORITY_KEY = bytes([0xD8]) * 32
OTHER_KEY = bytes([0xEE]) * 32

HOLDER_IDENTITY = bytes([0x11]) * 32
STRANGER_IDENTITY = bytes([0x22]) * 32
HOLDER_ESCROW = bytes([0x31]) * 32
STRANGER_ESCROW = bytes([0x32]) * 32

BEACON = bytes(range(32))

# Seat 1 activates in window 0 and is in scope from window 1. Seat 2 activates
# in window 1, so window 1 is not its. Seat 3 is purchased and never activated.
ACTIVE_SEAT = 1
LATE_SEAT = 2
UNACTIVATED_SEAT = 3
ACTIVE_SEAT_ACTIVATION_HEIGHT = 100
LATE_SEAT_ACTIVATION_HEIGHT = c.CYCLE_BLOCKS + 100

MEASURED_WINDOW = 1
# One height inside window 1, slot 0, comfortably before the excluded tail.
CHALLENGE_HEIGHT = c.CYCLE_BLOCKS + 40
RESPONSE_HEIGHT = CHALLENGE_HEIGHT + 1
VALID_UNTIL_HEIGHT = 10_000_000


def genesis(manifest_digest: bytes) -> Genesis:
    return Genesis(
        network_id=NETWORK_ID,
        supply_limit=SUPPLY_LIMIT,
        fixed_transfer_fee=FIXED_TRANSFER_FEE,
        manifest_digest=manifest_digest,
        verifier_key=VERIFIER_KEY,
        dispute_authority_key=DISPUTE_AUTHORITY_KEY,
    )
