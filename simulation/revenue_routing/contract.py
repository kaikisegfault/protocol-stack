"""Fixed routing contract from revenue-routing-v1.

Every value here is founder-directed or derived in the accepted specification.
Amounts are native atomic units under the denomination already accepted in
founder-economy-manifest-v1; seat sale USD cents never appear.
"""

from __future__ import annotations

from ..common.canonical import checked_add, checked_mul, checked_sub

SCHEMA = "protocol-stack/revenue-routing-result/v1"
EVENTS_LABEL = "protocol-stack:revenue-routing:events-v1"
STATE_LABEL = "protocol-stack:revenue-routing:state-v1"
TRACE_LABEL = "protocol-stack:revenue-routing:trace-v1"
RESULT_LABEL = "protocol-stack:revenue-routing:result-v1"

DECIMAL_PLACES = 8
ATOMIC_UNITS_PER_DISPLAY_UNIT = 100_000_000

SHARE_DENOMINATOR = 100
FOUNDER_SHARE_NUMERATOR = 45
CREATOR_SHARE_NUMERATOR = 45
SYSTEM_CREATOR_SHARE_NUMERATOR = 10
CREATOR_SPLIT_PARTS = 2

FOUNDER_SEAT_CAPACITY = 100_000

# The remainder repeats with this period, so scanning it proves the bound.
REMAINDER_PERIOD = 200
MAXIMUM_REMAINDER_SINGLE_CREATOR = 2
MAXIMUM_REMAINDER_TWO_CREATORS = 3


def share(amount: int, numerator: int) -> int | None:
    """Return floor(numerator * amount / 100) without ever overflowing u64.

    Computing `numerator * amount` first would leave u64 for a large but
    entirely representable payment, so the amount is split into its quotient
    and remainder modulo the denominator first. The identity is exact because
    `numerator * quotient` is an integer, so the floor distributes over the sum.
    """
    quotient, modulus = divmod(amount, SHARE_DENOMINATOR)
    whole = checked_mul(numerator, quotient)
    partial = checked_mul(numerator, modulus)
    if whole is None or partial is None:
        return None
    return checked_add(whole, partial // SHARE_DENOMINATOR)


def creator_legs(creator_share: int, *, product_creator: bool) -> tuple[int, int]:
    """Divide the already-floored creator share between the creator layers.

    Halving the 45% share is what makes two creators receive 22.5% each while
    keeping `project + product <= creator_share` by construction.
    """
    if not product_creator:
        return creator_share, 0
    half = creator_share // CREATOR_SPLIT_PARTS
    return half, half


def split(amount: int, *, product_creator: bool) -> tuple[int, int, int, int] | None:
    """Return (founder credit, project, product, system creator) for a payment.

    The founder credit already includes the routing remainder, which is the
    shortfall between the payment and the four floored credits.
    """
    founder = share(amount, FOUNDER_SHARE_NUMERATOR)
    creator = share(amount, CREATOR_SHARE_NUMERATOR)
    system = share(amount, SYSTEM_CREATOR_SHARE_NUMERATOR)
    if founder is None or creator is None or system is None:
        return None

    project, product = creator_legs(creator, product_creator=product_creator)
    credited = checked_add(founder, system)
    for leg in (project, product):
        credited = None if credited is None else checked_add(credited, leg)
    if credited is None:
        return None

    remainder = checked_sub(amount, credited)
    if remainder is None:
        return None
    founder_credit = checked_add(founder, remainder)
    if founder_credit is None:
        return None
    return founder_credit, project, product, system


def routing_remainder(amount: int, *, product_creator: bool) -> int | None:
    """The shortfall the founder credit absorbs, exposed for evidence."""
    parts = split(amount, product_creator=product_creator)
    founder = share(amount, FOUNDER_SHARE_NUMERATOR)
    if parts is None or founder is None:
        return None
    return parts[0] - founder


def maximum_remainder(*, product_creator: bool) -> int:
    return (
        MAXIMUM_REMAINDER_TWO_CREATORS
        if product_creator
        else MAXIMUM_REMAINDER_SINGLE_CREATOR
    )
