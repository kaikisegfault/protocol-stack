#!/usr/bin/env python3
"""Seeded research populations: the contract against its closed form, differentially.

The recorded run is one population. These draw others from the same shape:
the number of people and seats, who refers whom, the stagger, the uptime table,
outages, collection periods on both sides of the thirty-window cap, lapses,
genesis dates, and block rates from one window a day to one window a month.
Each population runs through the version-nine contract with every per-window
check, and then every figure the closed form derives must agree with it.

**Nothing here predicts a value.** The properties are the four claims the run
checks at every window and agreement with an independent walk, so a defect
either model has alone is a failure on some seed.
"""

from __future__ import annotations

import random
import sys
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "tools" / "scenario-suite-vectors")
)

import expected_v4 as x
from checker import Checker
from population_checks_v4 import check_differential

from simulation.calendar.civil import days_from_civil
from simulation.economy_transition_v9 import contract as c
from simulation.scenarios.economy_population_v4 import PopulationRun
from simulation.scenarios.economy_schedule_v4 import Fixture

SEEDS = range(32)
# Three seconds is the commit target, ninety seconds puts a window in each
# month, and ten minutes skips months between windows.
BLOCK_RATES = (3_000, 30_000, 90_000, 600_000)


class Agreement(Checker):
    """Records only disagreements: there is no file to compare against."""

    def __init__(self) -> None:
        super().__init__({})

    def equal(self, key: str, derived: object) -> None:
        self.seen.add(key)


def pattern(rng: random.Random) -> tuple[tuple[int, int, int], ...]:
    rows = []
    bound = -1
    for _ in range(rng.randint(1, 6)):
        bound += rng.randint(1, 6)
        credited = rng.choice((0, 12, 17, 18, 19, 20, 22, 24, 24))
        disputed = rng.randint(0, min(c.DISPUTE_CAP_SLOTS_PER_SEAT, credited))
        rows.append((bound, credited, disputed))
    return tuple(rows)


def draw(seed: int) -> dict:
    rng = random.Random(seed)
    people = rng.randint(2, 7)
    seat_count = rng.randint(1, 7)
    seats = {}
    for seat in range(seat_count):
        owner = rng.randrange(people)
        referrer = rng.choice([None] + [p for p in range(people) if p != owner])
        seats[seat] = (owner, referrer)
    stagger = rng.randint(0, 70)
    last_activation = (seat_count - 1) * stagger
    period = rng.randint(3, 45)
    year = rng.randint(2026, 2031)
    return {
        "genesis_millis": days_from_civil(year, rng.randint(1, 12), rng.randint(1, 28))
        * 86_400_000 + rng.randrange(86_400_000),
        "millis_per_block": rng.choice(BLOCK_RATES),
        "people": people,
        "seats": seats,
        "stagger": stagger,
        "keeper": rng.randrange(seat_count),
        "pattern": pattern(rng),
        "window_factor": rng.randint(1, 13),
        "seat_factor": rng.randint(1, 13),
        "outage_period": rng.randint(5, 80),
        "outage_phase": rng.randint(0, 4),
        "mint_period": period,
        "node_mint_phase": rng.randrange(period),
        "referral_mint_phase": rng.randrange(period),
        "seat_lapse": (rng.randrange(seat_count), rng.randint(0, 200), rng.randint(0, 260)),
        "referrer_lapse": (rng.randrange(people), rng.randint(0, 200), rng.randint(0, 260)),
        "pool_hoarder": rng.choice([-1, rng.randrange(seat_count)]),
        # Every seat activates before the run's last window.
        "horizon": last_activation + rng.randint(4, 260),
    }


class DifferentialTest(unittest.TestCase):
    reached: Counter = Counter()

    @classmethod
    def setUpClass(cls) -> None:
        cls.runs = []
        for seed in SEEDS:
            drawn = draw(seed)
            run = PopulationRun(Fixture(**drawn)).run()
            cls.runs.append((seed, drawn, run))
            for (label, result), count in run.observed.results.items():
                cls.reached[f"{label}.{result}"] += count
            cls.reached["settled_months"] += len(run.observed.settlements)
            cls.reached["skipped_months"] += sum(
                1 for window, settled in run.observed.settlements
                if run.fixture.window_month(window - c.ASSIGNMENT_LAG_WINDOWS)
                > settled.month + 1
            )
            cls.reached["pooled"] += run.observed.peak_recovery_pool > 0
            cls.reached["monthly_remainder"] += sum(
                1 for _window, settled in run.observed.settlements if settled.remainder
            )
            walk = x.derive(x.Params(**drawn))
            for name in ("empty_winner_windows", "multi_winner_windows",
                         "over_cap_seat_windows", "forfeited_referral_legs"):
                cls.reached[name] += walk.counts.get(name, 0)

    def test_every_population_agrees_with_the_closed_form(self) -> None:
        for seed, drawn, run in self.runs:
            with self.subTest(seed=seed):
                check = Agreement()
                check_differential(check, x, run, x.Params(**drawn))
                self.assertEqual(check.failures, [])
                self.assertGreater(check.checked, 30)

    def test_every_run_checked_every_window(self) -> None:
        for seed, drawn, run in self.runs:
            with self.subTest(seed=seed):
                self.assertEqual(run.observed.windows_checked, drawn["horizon"] + 1)

    def test_what_is_outstanding_after_the_last_round_is_the_recovery_pool(self) -> None:
        """Every seat collected to the last assigned window, so only the pool is owed."""
        for seed, _drawn, run in self.runs:
            with self.subTest(seed=seed):
                ledger = run.ledger
                for channel, _leg in c.BASE_PERMISSION_LEGS:
                    self.assertEqual(ledger.channel_outstanding[channel],
                                     ledger.pool[channel])

    def test_the_draws_reach_the_paths_they_exist_for(self) -> None:
        """A generator that never reached a path would pass vacuously."""
        for path in ("mint_node.SUCCESS", "mint_node.NOTHING_TO_MINT",
                     "mint_pool.SUCCESS", "mint_pool.NOTHING_TO_MINT",
                     "mint_referral.SUCCESS", "settled_months",
                     "skipped_months", "pooled", "monthly_remainder",
                     "empty_winner_windows",
                     "multi_winner_windows", "over_cap_seat_windows",
                     "forfeited_referral_legs"):
            with self.subTest(path=path):
                self.assertGreater(self.reached[path], 0)


if __name__ == "__main__":
    unittest.main()
