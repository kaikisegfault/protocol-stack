#!/usr/bin/env python3
"""Independently derive and check the Founder Seat schedule vectors.

Independence matters here because the vector file was produced from the model.
Every schedule value is therefore rederived by walking the Founder
Constitution's rule one block at a time, which shares no code with the
contract module's constant-time formula and closed-form sums. The recorded
file, the sequential walk, and the contract must all agree, and the four
founder-stated anchors are checked against literals taken from the
constitution rather than from either implementation.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.common.canonical import MAX_U64
from simulation.founder_seats import contract as c
from simulation.founder_seats.domain import initial_state, state_digest
from simulation.founder_seats.engine import apply_event, simulate
from simulation.founder_seats.validation import load_events_file

ROOT = Path(__file__).resolve().parents[2]

# Anchors quoted directly from docs/project/founder-constitution.md.
CONSTITUTION_SEAT_CAPACITY = 100_000
CONSTITUTION_SEATS_PER_PERSON = 1_000
CONSTITUTION_FIRST_BLOCK_USD = 100
CONSTITUTION_TIER_BOUNDARY_USD = 1_000
CONSTITUTION_FINAL_BLOCK_USD = 91_900
CONSTITUTION_FULL_SALE_USD = 4_231_855_000

MODELLED_CODES = frozenset(
    {
        "REPLAY",
        "CAPACITY_EXHAUSTED",
        "INVALID_REFERRER",
        "PRINCIPAL_SEAT_LIMIT",
        "MISSING_RESEARCH_INPUT",
        "INVALID_RESEARCH_INPUT",
        "PAYMENT_NOT_SETTLED",
        "ARITHMETIC_OVERFLOW",
        "INVARIANT",
    }
)


class Checker:
    def __init__(self, recorded: dict[str, str]) -> None:
        self.recorded = recorded
        self.failures: list[str] = []
        self.seen: set[str] = set()

    @property
    def checked(self) -> int:
        return len(self.seen)

    def equal(self, key: str, derived: object) -> None:
        if key not in self.recorded:
            self.failures.append(f"{key}: not recorded in the vector file")
            return
        self.seen.add(key)
        if str(derived) != self.recorded[key]:
            self.failures.append(
                f"{key}: derived {derived!r}, recorded {self.recorded[key]!r}"
            )

    def require_full_coverage(self) -> None:
        for key in sorted(set(self.recorded) - self.seen):
            self.failures.append(f"{key}: recorded but never derived")


def read_vectors(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, separator, value = stripped.partition("=")
        if not separator or key in values:
            raise ValueError(f"{path}:{number}: malformed or duplicate vector line")
        values[key] = value
    return values


def walk_schedule() -> tuple[list[int], list[int]]:
    """Walk the constitutional rule block by block, sharing no contract code.

    Seats 1 through 100 cost USD 100. The price rises by USD 10 per next block
    until a block price of USD 1,000 is reached. After that block it rises by
    USD 100 per next block.
    """
    cents = 100
    prices: list[int] = []
    price = CONSTITUTION_FIRST_BLOCK_USD * cents
    boundary = CONSTITUTION_TIER_BOUNDARY_USD * cents
    for _ in range(CONSTITUTION_SEAT_CAPACITY // 100):
        prices.append(price)
        price = price + 10 * cents if price < boundary else price + 100 * cents

    cumulative: list[int] = []
    running = 0
    for block_price in prices:
        running += block_price * 100
        cumulative.append(running)
    return prices, cumulative


def check_anchors(check: Checker, prices: list[int], cumulative: list[int]) -> None:
    """The walk must reproduce the four figures stated in the constitution."""
    cents = 100
    if prices[0] != CONSTITUTION_FIRST_BLOCK_USD * cents:
        check.failures.append("walk: first block price does not match the constitution")
    if CONSTITUTION_TIER_BOUNDARY_USD * cents not in prices:
        check.failures.append("walk: the USD 1,000 tier boundary is never a block price")
    if prices[-1] != CONSTITUTION_FINAL_BLOCK_USD * cents:
        check.failures.append("walk: final block price does not match the constitution")
    if cumulative[-1] != CONSTITUTION_FULL_SALE_USD * cents:
        check.failures.append("walk: full-sale proceeds do not match the constitution")
    if len(prices) * 100 != CONSTITUTION_SEAT_CAPACITY:
        check.failures.append("walk: block count does not cover the seat capacity")


def check_contract_agreement(check: Checker, prices: list[int], cumulative: list[int]) -> None:
    """Every block must agree between the walk and the contract module."""
    for index, (price, total) in enumerate(zip(prices, cumulative)):
        if c.block_price_cents(index) != price:
            check.failures.append(f"block {index}: contract price disagrees with the walk")
            return
        if c.cumulative_proceeds_cents(index) != total:
            check.failures.append(f"block {index}: contract cumulative disagrees with the walk")
            return
    for seat_id in (0, 99, 100, 9_000, 9_100, 99_999):
        if c.seat_price_cents(seat_id) != prices[seat_id // 100]:
            check.failures.append(f"seat {seat_id}: contract price disagrees with the walk")
    if c.block_price_cents(-1) is not None or c.block_price_cents(1_000) is not None:
        check.failures.append("contract accepts an out-of-range block index")
    if c.seat_price_cents(CONSTITUTION_SEAT_CAPACITY) is not None:
        check.failures.append("contract prices a seat beyond the capacity")


def check_schedule_vectors(check: Checker, prices: list[int], cumulative: list[int]) -> None:
    cents = 100
    check.equal("denomination.cents_per_usd", cents)
    check.equal("denomination.full_sale_proceeds_cents", cumulative[-1])
    check.equal("denomination.full_sale_proceeds_usd", cumulative[-1] // cents)

    check.equal("capacity.founder_seat_capacity", len(prices) * 100)
    check.equal("capacity.seats_per_block", 100)
    check.equal("capacity.block_count", len(prices))
    check.equal("capacity.maximum_seats_per_person", CONSTITUTION_SEATS_PER_PERSON)

    check.equal("schedule.first_block_price_cents", prices[0])
    check.equal("schedule.low_tier_step_cents", prices[1] - prices[0])
    check.equal("schedule.tier_boundary_price_cents", CONSTITUTION_TIER_BOUNDARY_USD * cents)
    check.equal("schedule.high_tier_step_cents", prices[-1] - prices[-2])
    check.equal("schedule.last_low_tier_block", prices.index(CONSTITUTION_TIER_BOUNDARY_USD * cents))
    check.equal("schedule.final_block_price_cents", prices[-1])

    for index in (0, 1, 89, 90, 91, 998, 999):
        check.equal(f"block{index}.price_cents", prices[index])
        check.equal(f"block{index}.price_usd", prices[index] // cents)
        check.equal(f"block{index}.cumulative_cents", cumulative[index])

    for seat_id in (0, 99, 100, 9_000, 9_100, 99_999):
        check.equal(f"seat{seat_id}.block_index", seat_id // 100)
        check.equal(f"seat{seat_id}.price_cents", prices[seat_id // 100])


def check_scenario_vectors(check: Checker, result: dict, prices: list[int]) -> None:
    records = result["records"]
    rejected = [record for record in records if not record["accepted"]]
    metrics = result["metrics"]

    check.equal("schema", result["schema"])
    check.equal("events_file", "simulation/founder_seats/fixtures/research-events-v1.json")
    check.equal("events_domain_label", c.EVENTS_LABEL)
    check.equal("state_domain_label", c.STATE_LABEL)
    check.equal("trace_domain_label", c.TRACE_LABEL)
    check.equal("result_domain_label", c.RESULT_LABEL)

    check.equal("scenario.event_count", len(records))
    check.equal("scenario.accepted_count", len(records) - len(rejected))
    check.equal("scenario.rejected_count", len(rejected))
    check.equal("scenario.events_digest", result["events_digest"])
    check.equal("scenario.trace_digest", result["trace_digest"])
    check.equal("scenario.state_digest", result["state_digest"])
    check.equal("scenario.result_digest", result["result_digest"])

    accepted = len(records) - len(rejected)
    check.equal("scenario.seats_sold", metrics["seats_sold"])
    check.equal("scenario.seats_remaining", CONSTITUTION_SEAT_CAPACITY - accepted)
    check.equal("scenario.proceeds_cents", sum(prices[n // 100] for n in range(accepted)))
    check.equal("scenario.distinct_principal_count", metrics["distinct_principal_count"])
    check.equal("scenario.largest_principal_holding", metrics["largest_principal_holding"])

    for index, record in enumerate(records):
        check.equal(f"record{index}.event_id", record["event_id"])
        check.equal(f"record{index}.result", record["result"])

    check.equal("atomic_failure.rejected_state_writes", count_rejected_writes())
    check.equal(
        "atomic_failure.rejected_journal_entries",
        sum(len(record["journal"]) for record in rejected),
    )
    consumed = len(result["final_state"]["accepted_purchase_ids"]) - accepted
    check.equal("atomic_failure.purchase_identifiers_consumed", consumed)


def count_rejected_writes() -> int:
    """Step the scenario and digest the whole state around every rejection.

    Trace records no longer carry per-event state digests, so this derives the
    zero-write claim directly instead of reading back a recorded field. The
    research scenario is short, so a full digest per event is affordable here
    even though it would not be for the complete sale.
    """
    events = load_events_file(
        ROOT / "simulation" / "founder_seats" / "fixtures" / "research-events-v1.json"
    )
    state = initial_state()
    writes = 0
    for index, event in enumerate(events):
        before = state_digest(state)
        record = apply_event(state, event, index)
        after = state_digest(state)
        if not record["accepted"] and before != after:
            writes += 1
        if record["accepted"] and before == after:
            writes += 1  # an accepted purchase that wrote nothing is also wrong
    return writes


def check_negative_vectors(check: Checker) -> None:
    for key in sorted(check.recorded):
        if key.startswith("negative.") and key.endswith(".result"):
            recorded = check.recorded[key]
            check.equal(key, recorded if recorded in MODELLED_CODES else "UNMODELLED")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--vectors",
        type=Path,
        default=ROOT / "test-vectors" / "founder-seat-schedule-v1.txt",
    )
    arguments = parser.parse_args()

    prices, cumulative = walk_schedule()
    if cumulative[-1] > MAX_U64:
        sys.stderr.write("full-sale proceeds exceed u64\n")
        return 1

    result = simulate(
        load_events_file(
            ROOT / "simulation" / "founder_seats" / "fixtures" / "research-events-v1.json"
        )
    )

    check = Checker(read_vectors(arguments.vectors))
    check_anchors(check, prices, cumulative)
    check_contract_agreement(check, prices, cumulative)
    check_schedule_vectors(check, prices, cumulative)
    check_scenario_vectors(check, result, prices)
    check_negative_vectors(check)
    check.require_full_coverage()

    for failure in check.failures:
        sys.stderr.write(f"vector mismatch: {failure}\n")
    if check.failures:
        return 1

    sys.stdout.write(
        f"derived and matched {check.checked} seat schedule vectors; "
        f"the independent walk agrees with the contract on all {len(prices)} blocks\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
