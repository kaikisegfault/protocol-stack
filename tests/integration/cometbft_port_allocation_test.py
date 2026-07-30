#!/usr/bin/env python3
"""Focused Linux listener-port allocation tests."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cometbft_process import (  # noqa: E402
    MAXIMUM_PORT,
    non_ephemeral_block_bases,
    read_linux_ephemeral_port_range,
    reserve_non_ephemeral_port_block,
)

OFFSETS = (0, 1, 2, 10, 11, 12, 20, 21, 22, 30, 31, 32)


class CometBftPortAllocationTest(unittest.TestCase):
    def test_parses_and_rejects_linux_ephemeral_ranges(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "range"
            path.write_text("32768\t60999\n", encoding="ascii")
            self.assertEqual(
                read_linux_ephemeral_port_range(path),
                (32768, 60999),
            )
            for value in (
                "",
                "32768",
                "high low",
                "60000 32768",
                "0 1",
                f"1 {MAXIMUM_PORT + 1}",
            ):
                with self.subTest(value=value):
                    path.write_text(value, encoding="ascii")
                    with self.assertRaises(RuntimeError):
                        read_linux_ephemeral_port_range(path)

    def test_candidate_blocks_never_overlap_ephemeral_ports(self) -> None:
        ephemeral = (32768, 60999)
        bases = non_ephemeral_block_bases(ephemeral, OFFSETS)
        self.assertGreater(len(bases), 1)
        self.assertEqual(len(bases), len(set(bases)))
        for base in bases:
            self.assertGreaterEqual(base, 1024)
            self.assertLessEqual(base + max(OFFSETS), MAXIMUM_PORT)
            for offset in OFFSETS:
                port = base + offset
                self.assertFalse(ephemeral[0] <= port <= ephemeral[1])

    def test_offset_contract_and_live_selection(self) -> None:
        invalid = ((), (1,), (0, 0), (0, MAXIMUM_PORT + 1))
        for offsets in invalid:
            with self.subTest(offsets=offsets):
                with self.assertRaises(ValueError):
                    non_ephemeral_block_bases((32768, 60999), offsets)
        for ephemeral in ((0, 1), (2, 1), (1, MAXIMUM_PORT + 1)):
            with self.subTest(ephemeral=ephemeral):
                with self.assertRaises(ValueError):
                    non_ephemeral_block_bases(ephemeral, OFFSETS)
        self.assertTrue(
            all(
                base >= 1024
                for base in non_ephemeral_block_bases((1, 1000), OFFSETS)
            )
        )

        ephemeral = read_linux_ephemeral_port_range()
        base = reserve_non_ephemeral_port_block(OFFSETS)
        self.assertTrue(
            base + max(OFFSETS) < ephemeral[0] or base > ephemeral[1]
        )


if __name__ == "__main__":
    unittest.main()
