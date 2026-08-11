#!/usr/bin/env python3
"""Require every simulation test and vector verifier to be gated by ctest.

`CMakeLists.txt` registers each test and each verifier with an explicit
`add_test`, so adding a file does not add a gate. An unregistered test still
passes locally and still appears in a slice's evidence, while the hosted matrix
never runs it — the failure is silent in exactly the direction that matters.

This module runs under `tests/tools`, which the focused metadata path executes
on every pull request regardless of scope classification, so the omission is
caught even by a change that does not build anything.

M3.6a and M3.6b were merged with five unregistered test files and two
unregistered verifiers. M3.6c registered them and added this guard.
"""

from pathlib import Path
import re
import unittest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CMAKE_LISTS = REPOSITORY_ROOT / "CMakeLists.txt"
SIMULATION_TESTS = REPOSITORY_ROOT / "tests" / "simulation"
TOOLS = REPOSITORY_ROOT / "tools"

# A verifier a slice added but never registered would go unrun in the same way.
# Only an executable entry point needs its own registration: a `verify_*.py`
# that another verifier imports is already covered by the one that imports it,
# so the executable guard rather than the file name is what distinguishes them.
VERIFIER_PATTERN = re.compile(r"^verify.*\.py$")
ENTRY_POINT = 'if __name__ == "__main__":'


def cmake_text() -> str:
    return CMAKE_LISTS.read_text(encoding="utf-8")


class SimulationTestRegistrationTest(unittest.TestCase):
    def test_every_simulation_test_is_registered(self) -> None:
        text = cmake_text()
        missing = sorted(
            path.name
            for path in SIMULATION_TESTS.glob("*_test.py")
            if f"tests/simulation/{path.name}" not in text
        )
        self.assertEqual(
            missing,
            [],
            "these simulation tests have no add_test in CMakeLists.txt, so the "
            "hosted matrix never runs them",
        )

    def test_every_simulation_test_runs_as_a_script(self) -> None:
        """`ctest` invokes each test as `python3 <path>`, not through discovery.

        A module written for `unittest discover` passes locally and fails the
        moment it is registered: a package-relative import has no package, and a
        module with no entry point runs nothing and exits 0. Four modules were
        in the first state when M3.6c registered them.
        """
        broken = []
        for path in sorted(SIMULATION_TESTS.glob("*_test.py")):
            source = path.read_text(encoding="utf-8")
            if 'if __name__ == "__main__":' not in source:
                broken.append(f"{path.name}: no entry point, so it would run nothing")
            if re.search(r"^from \.", source, re.MULTILINE):
                broken.append(f"{path.name}: package-relative import")
        self.assertEqual(broken, [])

    def test_every_vector_verifier_is_registered(self) -> None:
        text = cmake_text()
        missing = []
        for directory in sorted(TOOLS.glob("*-vectors")):
            for path in sorted(directory.iterdir()):
                if not path.is_file() or not VERIFIER_PATTERN.fullmatch(path.name):
                    continue
                if ENTRY_POINT not in path.read_text(encoding="utf-8"):
                    continue
                reference = f"tools/{directory.name}/{path.name}"
                if reference not in text:
                    missing.append(reference)
        self.assertEqual(
            missing,
            [],
            "these vector verifiers have no add_test in CMakeLists.txt, so the "
            "hosted matrix never runs them",
        )

    def test_every_accepted_vector_file_is_verified(self) -> None:
        """A recorded vector file no registered verifier reads is not evidence."""
        text = cmake_text()
        missing = sorted(
            path.name
            for path in (REPOSITORY_ROOT / "test-vectors").glob("*.txt")
            if f"test-vectors/{path.name}" not in text
        )
        self.assertEqual(
            missing,
            [],
            "these vector files are referenced by no registered ctest entry",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
