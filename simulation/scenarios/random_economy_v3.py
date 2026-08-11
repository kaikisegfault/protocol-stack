"""Seeded random event sequences for `founder-economy-simulator-v3`.

This generator produces varied, hostile, mostly-legal traffic; it does not
predict outcomes. Nothing here asserts anything: the properties are the model's
conservation equations, and the caller checks them against the recorded final
state. Every sequence is a pure function of its seed, so a failing property
names a reproducible input.

Version three rejects a window that is not the one its seat's schedule assigns,
and a record whose seat set is not exactly its window's in-scope set. A purely
random window and a purely random seat set would therefore be rejected almost
always, and the run would exercise two conditions instead of twenty. So the
activations come first, in non-decreasing height order, and are all accepted;
the generator then knows the activation table exactly and can aim an event at a
specific condition — the correct window and complete set, or one deliberate
defect at a time. Aiming is not predicting: the generator never records what it
expects the model to answer.

Two boundaries need care. An out-of-range count is an input-shape error that
aborts the whole run, while an over-target `uptime_seconds` is a modelled
rejection that must produce a trace record, so hostile uptimes are drawn above
the cycle target but well inside the parser's bounds. A height above `u64` is
likewise an input-shape error, so the unrepresentable-span draw uses a height
that parses and whose 731-window span does not fit.
"""

from __future__ import annotations

import random
from typing import Any

from ..cycle_boundary.grid import MAX_WINDOW, first_cycle_window, last_cycle_window
from ..founder_economy_v3 import contract as economy_contract

ECONOMY_SEATS = 4
ECONOMY_CYCLES = 8
# Activation windows are drawn from a span comparable to the cycle range, so
# in-scope sets differ between windows and grow as the run's windows advance.
ACTIVATION_WINDOW_SPAN = 6
WELL_FORMED_RECORD_PROBABILITY = 0.55
RECORD_SUPPLIED_PROBABILITY = 0.9
ELIGIBILITY_SUPPLIED_PROBABILITY = 0.85
MET_CYCLE_PROBABILITY = 0.75

# Above the 86,400-second cycle target, so the record is rejected by the model,
# and far below the parser's count bound, so the run continues.
OVER_TARGET_UPTIME = economy_contract.CYCLE_TARGET_SECONDS + 1

# A representable u64 height whose complete 731-window span is not, so an
# activation carrying it reaches `HEIGHT_RANGE` rather than an input error.
UNREPRESENTABLE_SPAN_HEIGHT = MAX_WINDOW * economy_contract.CYCLE_BLOCKS


class Schedule:
    """The activation table the accepted activations install."""

    def __init__(self, source: random.Random) -> None:
        span = ACTIVATION_WINDOW_SPAN * economy_contract.CYCLE_BLOCKS
        self.heights = sorted(source.randrange(span) for _ in range(ECONOMY_SEATS))

    def first(self, seat_id: int) -> int:
        return first_cycle_window(self.heights[seat_id])

    def last(self, seat_id: int) -> int:
        return last_cycle_window(self.heights[seat_id])

    def window_for(self, seat_id: int, cycle_index: int) -> int:
        return self.first(seat_id) + cycle_index

    def in_scope(self, window: int) -> list[int]:
        return [seat for seat in range(ECONOMY_SEATS) if self.first(seat) <= window]

    def out_of_scope(self, window: int) -> list[int]:
        return [seat for seat in range(ECONOMY_SEATS) if self.first(seat) > window]


def economy_events(seed: int, count: int) -> list[dict[str, Any]]:
    """Accepted activations, then hostile traffic against every transition."""
    source = random.Random(seed)
    schedule = Schedule(source)
    channels = sorted(economy_contract.DIRECT_CHANNEL_IDS)

    events: list[dict[str, Any]] = [
        {
            "id": f"a{seat_id:05d}",
            "kind": "activate_seat",
            "seat_id": seat_id,
            "referrer_seat_id": None if seat_id == 0 else source.randrange(seat_id),
            "activation_height": str(schedule.heights[seat_id]),
        }
        for seat_id in range(ECONOMY_SEATS)
    ]

    for index in range(count):
        seat_id = source.randrange(ECONOMY_SEATS)
        cycle_index = source.randrange(ECONOMY_CYCLES)
        choice = source.randrange(5)
        if choice == 0:
            events.append(_hostile_activation(source, index, seat_id, schedule))
        elif choice == 1:
            events.append(_random_base(source, index, seat_id, cycle_index, schedule))
        elif choice == 2:
            events.append(_random_accrual(index, seat_id, cycle_index))
        elif choice == 3:
            events.append(_random_exercise(index, seat_id, cycle_index))
        else:
            events.append(_random_direct(source, index, channels))
    return events


def _activation(
    index: int,
    seat_id: int,
    height: int,
    referrer: int | None = None,
) -> dict[str, Any]:
    return {
        "id": f"e{index:05d}",
        "kind": "activate_seat",
        "seat_id": seat_id,
        "referrer_seat_id": referrer,
        "activation_height": str(height),
    }


def _hostile_activation(
    source: random.Random,
    index: int,
    seat_id: int,
    schedule: Schedule,
) -> dict[str, Any]:
    """Always refused, so the installed schedule is never disturbed.

    Every variant is refused by construction rather than by chance, because an
    accepted extra activation would enlarge a later window's in-scope set and
    the generator would then aim at sets the model no longer expects. A replay
    names an already activated seat and carries a monotonic-valid height; the
    rest name a seat that never exists, so none can be mistaken for one.

    The five reach a replay, a height whose 731-window span would wrap, a height
    below the highest recorded, a self-referral, and a referrer that is a
    representable seat identifier which was never activated.
    """
    highest = schedule.heights[-1]
    flaw = source.randrange(5)
    if flaw == 0:
        return _activation(index, seat_id, highest)
    if flaw == 1:
        return _activation(index, ECONOMY_SEATS, UNREPRESENTABLE_SPAN_HEIGHT)
    if flaw == 2 and highest > 0:
        return _activation(index, ECONOMY_SEATS, highest - 1)
    if flaw == 3:
        return _activation(index, ECONOMY_SEATS, highest, referrer=ECONOMY_SEATS)
    return _activation(index, ECONOMY_SEATS, highest, referrer=ECONOMY_SEATS + 1)


def _entries(
    listed: list[int],
    source: random.Random,
    uptime: int | None = None,
) -> list[dict[str, Any]]:
    return [
        {
            "seat_id": seat,
            "uptime_seconds": uptime
            if uptime is not None
            else (
                economy_contract.CYCLE_TARGET_SECONDS
                if source.random() < MET_CYCLE_PROBABILITY
                else source.randrange(economy_contract.ACTIVITY_THRESHOLD_SECONDS)
            ),
        }
        for seat in listed
    ]


def _random_record(
    source: random.Random,
    seat_id: int,
    cycle_index: int,
    schedule: Schedule,
) -> dict[str, Any] | None:
    """A cycle uptime record aimed at one condition, correct or defective.

    The seven variants below reach, in order: the intended acceptance, a window
    before the seat's issuance, one after it, one inside the span but attached
    to another cycle, an out-of-scope seat, an omitted in-scope seat, and a
    record that omits the evaluated seat or over-reports its uptime.
    """
    if source.random() >= RECORD_SUPPLIED_PROBABILITY:
        return None

    window = schedule.window_for(seat_id, cycle_index)
    listed = schedule.in_scope(window)
    if source.random() < WELL_FORMED_RECORD_PROBABILITY:
        return {"cycle_window": window, "entries": _entries(listed, source)}

    flaw = source.randrange(6)
    outside = schedule.out_of_scope(window)
    others = [seat for seat in listed if seat != seat_id]

    if flaw == 0:
        return {
            "cycle_window": schedule.first(seat_id) - 1,
            "entries": _entries([seat_id], source),
        }
    if flaw == 1:
        return {
            "cycle_window": schedule.last(seat_id) + 1,
            "entries": _entries([seat_id], source),
        }
    if flaw == 2:
        return {"cycle_window": window + 1, "entries": _entries([seat_id], source)}
    if flaw == 3 and outside:
        return {
            "cycle_window": window,
            "entries": _entries(listed + [source.choice(outside)], source),
        }
    if flaw == 4 and others:
        dropped = source.choice(others)
        return {
            "cycle_window": window,
            "entries": _entries([seat for seat in listed if seat != dropped], source),
        }
    if source.random() < 0.5:
        return {"cycle_window": window, "entries": _entries(others, source)}
    return {
        "cycle_window": window,
        "entries": _entries(listed, source, uptime=OVER_TARGET_UPTIME),
    }


def _random_base(
    source: random.Random,
    index: int,
    seat_id: int,
    cycle_index: int,
    schedule: Schedule,
) -> dict[str, Any]:
    return {
        "id": f"e{index:05d}",
        "kind": "evaluate_base_permission",
        "seat_id": seat_id,
        "cycle_index": cycle_index,
        "cycle_uptime_record": _random_record(source, seat_id, cycle_index, schedule),
    }


def _random_accrual(index: int, seat_id: int, cycle_index: int) -> dict[str, Any]:
    """The accrual is unconditional, so it carries no research input at all."""
    return {
        "id": f"e{index:05d}",
        "kind": "accrue_referral",
        "seat_id": seat_id,
        "cycle_index": cycle_index,
    }


def _random_exercise(index: int, seat_id: int, cycle_index: int) -> dict[str, Any]:
    return {
        "id": f"e{index:05d}",
        "kind": "exercise_permission",
        "seat_id": seat_id,
        "cycle_index": cycle_index,
    }


def _random_direct(
    source: random.Random,
    index: int,
    channels: list[str],
) -> dict[str, Any]:
    """`channels` includes `founder_referral`, which the model must refuse.

    Leaving it in the draw is deliberate hostile traffic: the containment that
    keeps referral units inside the per-seat-cycle accounting is exercised by
    the property runs rather than only by a named probe.
    """
    channel = source.choice(channels)
    decision_id = f"decision-{source.randrange(16):02d}"
    beneficiary_id = f"beneficiary-{source.randrange(4)}"
    amount = str(source.randrange(1, 10**12))
    eligibility = None
    if source.random() < ELIGIBILITY_SUPPLIED_PROBABILITY:
        eligibility = {
            "channel": channel,
            "decision_id": decision_id,
            "beneficiary_id": beneficiary_id,
            "amount_atomic": amount,
            "eligible": source.random() < 0.8,
        }
    return {
        "id": f"e{index:05d}",
        "kind": "direct_issue",
        "channel": channel,
        "decision_id": decision_id,
        "beneficiary_id": beneficiary_id,
        "amount_atomic": amount,
        "eligibility_result": eligibility,
    }
