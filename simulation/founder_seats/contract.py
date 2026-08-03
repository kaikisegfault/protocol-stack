"""Fixed Founder Seat sale contract from founder-seat-schedule-v1.

Every value here is founder-directed or derived from the Founder Constitution's
price rule. Prices are unsigned integer USD cents, a separate unit from native
atomic units; a sale amount is never native supply.
"""

from __future__ import annotations

from ..common.canonical import checked_add, checked_mul

SCHEMA = "protocol-stack/founder-seat-schedule-result/v1"
EVENTS_LABEL = "protocol-stack:founder-seat-schedule:events-v1"
STATE_LABEL = "protocol-stack:founder-seat-schedule:state-v1"
TRACE_LABEL = "protocol-stack:founder-seat-schedule:trace-v1"
RESULT_LABEL = "protocol-stack:founder-seat-schedule:result-v1"

CENTS_PER_USD = 100
FOUNDER_SEAT_CAPACITY = 100_000
SEATS_PER_BLOCK = 100
BLOCK_COUNT = FOUNDER_SEAT_CAPACITY // SEATS_PER_BLOCK
MAXIMUM_SEATS_PER_PERSON = 1_000

FIRST_BLOCK_PRICE_CENTS = 100 * CENTS_PER_USD
LOW_TIER_STEP_CENTS = 10 * CENTS_PER_USD
TIER_BOUNDARY_PRICE_CENTS = 1_000 * CENTS_PER_USD
HIGH_TIER_STEP_CENTS = 100 * CENTS_PER_USD

# The last block index priced by the low-tier rule; block 90 is the boundary.
LAST_LOW_TIER_BLOCK = (
    TIER_BOUNDARY_PRICE_CENTS - FIRST_BLOCK_PRICE_CENTS
) // LOW_TIER_STEP_CENTS

FINAL_BLOCK_PRICE_CENTS = 91_900 * CENTS_PER_USD
FULL_SALE_PROCEEDS_CENTS = 4_231_855_000 * CENTS_PER_USD


def block_index(seat_id: int) -> int:
    return seat_id // SEATS_PER_BLOCK


def block_price_cents(index: int) -> int | None:
    """Return a block's price in cents, or None if a checked step overflows."""
    if not 0 <= index < BLOCK_COUNT:
        return None
    if index <= LAST_LOW_TIER_BLOCK:
        step = checked_mul(index, LOW_TIER_STEP_CENTS)
        return None if step is None else checked_add(FIRST_BLOCK_PRICE_CENTS, step)
    step = checked_mul(index - LAST_LOW_TIER_BLOCK, HIGH_TIER_STEP_CENTS)
    return None if step is None else checked_add(TIER_BOUNDARY_PRICE_CENTS, step)


def seat_price_cents(seat_id: int) -> int | None:
    if not 0 <= seat_id < FOUNDER_SEAT_CAPACITY:
        return None
    return block_price_cents(block_index(seat_id))


def cumulative_proceeds_cents(through_block: int) -> int | None:
    """Total proceeds once every seat in blocks 0..through_block is sold.

    Uses the two arithmetic series in closed form so the value does not depend
    on accumulating a thousand terms.
    """
    if not 0 <= through_block < BLOCK_COUNT:
        return None
    low_blocks = min(through_block, LAST_LOW_TIER_BLOCK) + 1
    low_last = block_price_cents(low_blocks - 1)
    if low_last is None:
        return None
    total = low_blocks * (FIRST_BLOCK_PRICE_CENTS + low_last) // 2

    if through_block > LAST_LOW_TIER_BLOCK:
        high_blocks = through_block - LAST_LOW_TIER_BLOCK
        high_first = block_price_cents(LAST_LOW_TIER_BLOCK + 1)
        high_last = block_price_cents(through_block)
        if high_first is None or high_last is None:
            return None
        total += high_blocks * (high_first + high_last) // 2
    return checked_mul(total, SEATS_PER_BLOCK)
