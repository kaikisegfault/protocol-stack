"""The ordered acceptance rules and the month over a chain of heights.

Two entry points, and the difference between them is the whole of ADR 0050's
first decision:

`accept` is the consensus admission check. It applies every rule including the
tolerance, and the observing machine's clock reading is an explicit parameter
rather than something this module reads. A model that read a clock would not be
a model of a deterministic protocol.

`replay` is what a machine re-applies to history. It applies the deterministic
rules only and takes no clock at all, because the clock that would answer on
replay is not the clock that agreed the block. A machine that re-applied the
tolerance on replay would reject its own past one tolerance-width after
producing it.
"""

from __future__ import annotations

from dataclasses import dataclass

from simulation.calendar import contract as c
from simulation.calendar import months
from simulation.common.canonical import CodedError, InvariantError, digest


@dataclass(frozen=True)
class Block:
    height: int
    timestamp: int


class Calendar:
    """A chain of accepted block timestamps and the months they fall in."""

    def __init__(self, genesis_timestamp: int) -> None:
        if not months.in_range(genesis_timestamp):
            raise InvariantError(
                f"genesis timestamp {genesis_timestamp} is outside the accepted range"
            )
        self.genesis_timestamp = genesis_timestamp
        self.blocks: list[Block] = []

    # -- state ------------------------------------------------------------

    @property
    def head_height(self) -> int:
        return self.blocks[-1].height if self.blocks else c.GENESIS_HEIGHT

    @property
    def head_timestamp(self) -> int:
        """The predecessor a new block's monotonicity is judged against.

        Genesis supplies it for the chain's first block, which is why a genesis
        timestamp is a field rather than an optional one.
        """
        return self.blocks[-1].timestamp if self.blocks else self.genesis_timestamp

    @property
    def next_height(self) -> int:
        return self.head_height + 1

    def timestamp_of(self, height: int) -> int:
        if not c.FIRST_BLOCK_HEIGHT <= height <= self.head_height:
            raise InvariantError(f"height {height} is not in the chain")
        return self.blocks[height - c.FIRST_BLOCK_HEIGHT].timestamp

    # -- the ordered rules ------------------------------------------------

    def _check_deterministic(self, height: int, timestamp: int) -> None:
        """Conditions 1 to 3, the rules every replay re-applies."""
        if height != self.next_height:
            raise CodedError(
                "HEIGHT_NOT_NEXT",
                f"height {height} is not the chain's next height {self.next_height}",
            )
        if not months.in_range(timestamp):
            raise CodedError(
                "TIMESTAMP_RANGE",
                f"timestamp {timestamp} is outside "
                f"[{c.MIN_TIMESTAMP_MILLIS}, {c.MAX_TIMESTAMP_MILLIS}]",
            )
        if timestamp < self.head_timestamp:
            raise CodedError(
                "TIMESTAMP_NOT_MONOTONIC",
                f"timestamp {timestamp} is below the predecessor's "
                f"{self.head_timestamp}",
            )

    def _check_tolerance(self, timestamp: int, observed_clock: int) -> None:
        """Conditions 4 and 5, applied once at admission and never again.

        Both comparisons are written as guarded subtractions rather than as
        `timestamp > observed_clock + TOLERANCE`. The sum is the shape that
        wraps when a clock sits near the u64 bound, and a wrapped comparison
        accepts exactly the values it exists to refuse.
        """
        if observed_clock < 0:
            raise InvariantError("an observed clock reading is not negative")
        if timestamp > observed_clock:
            if timestamp - observed_clock > c.TIMESTAMP_TOLERANCE_MILLIS:
                raise CodedError(
                    "TIMESTAMP_AHEAD_OF_TOLERANCE",
                    f"timestamp {timestamp} is "
                    f"{timestamp - observed_clock}ms ahead of the observed clock",
                )
        elif observed_clock - timestamp > c.TIMESTAMP_TOLERANCE_MILLIS:
            raise CodedError(
                "TIMESTAMP_BEHIND_TOLERANCE",
                f"timestamp {timestamp} is "
                f"{observed_clock - timestamp}ms behind the observed clock",
            )

    def accept(self, height: int, timestamp: int, observed_clock: int) -> int:
        """Admit a proposed block, or refuse it and write nothing.

        Returns the month index the block falls in.
        """
        self._check_deterministic(height, timestamp)
        self._check_tolerance(timestamp, observed_clock)
        self.blocks.append(Block(height, timestamp))
        return months.month_index(timestamp)

    def replay(self, height: int, timestamp: int) -> int:
        """Re-apply an accepted block with no clock available."""
        self._check_deterministic(height, timestamp)
        self.blocks.append(Block(height, timestamp))
        return months.month_index(timestamp)

    # -- the month over the chain -----------------------------------------

    def month_of_height(self, height: int) -> int:
        return months.month_index(self.timestamp_of(height))

    def opens_a_month(self, height: int) -> bool:
        """Whether this block is the first of the chain's view of a month.

        The chain's first block always opens one: there is no earlier height,
        so whatever month it lands in, it is the first height the chain has in
        it. Genesis is not a block and holds no heights.
        """
        if height == c.FIRST_BLOCK_HEIGHT:
            return True
        return self.month_of_height(height) > self.month_of_height(height - 1)

    def months_closed_by(self, height: int) -> tuple[int, ...]:
        """Every month index this block makes final.

        A month's last height is not recognisable when it executes, because
        whether a later block falls in the same month is not yet known. The
        opening block is the only recognisable point, so it is where a
        transition acting on a completed month belongs.

        The range is closed at the bottom and open at the top: the predecessor's
        own month is closed, and so is every empty month between it and this
        one. A chain halted across a month boundary would otherwise skip a whole
        month silently.
        """
        if height == c.FIRST_BLOCK_HEIGHT:
            return ()
        previous = self.month_of_height(height - 1)
        current = self.month_of_height(height)
        return tuple(range(previous, current))

    def empty_months(self) -> tuple[int, ...]:
        """Month indices the chain passed over without holding a single height."""
        if not self.blocks:
            return ()
        occupied = {months.month_index(block.timestamp) for block in self.blocks}
        first = months.month_index(self.blocks[0].timestamp)
        last = months.month_index(self.blocks[-1].timestamp)
        return tuple(index for index in range(first, last + 1) if index not in occupied)

    def month_height_span(self, index: int) -> tuple[int, int] | None:
        """The first and last height the chain holds in a month, if any."""
        heights = [
            block.height
            for block in self.blocks
            if months.month_index(block.timestamp) == index
        ]
        if not heights:
            return None
        return (heights[0], heights[-1])

    def month_indices(self) -> tuple[int, ...]:
        return tuple(months.month_index(block.timestamp) for block in self.blocks)

    # -- evidence ---------------------------------------------------------

    def canonical_state(self) -> dict[str, object]:
        """Heights and timestamps as canonical decimal strings.

        Both are u64 quantities and a millisecond timestamp already exceeds the
        largest integer a conforming JSON stack represents exactly, so both are
        strings for the same reason a monetary value is.
        """
        return {
            "schema": c.STATE_SCHEMA,
            "genesis_timestamp": str(self.genesis_timestamp),
            "blocks": [
                {
                    "height": str(block.height),
                    "timestamp": str(block.timestamp),
                    "month_index": months.month_index(block.timestamp),
                }
                for block in self.blocks
            ],
        }

    def state_digest(self) -> str:
        return digest(c.STATE_LABEL, self.canonical_state())
