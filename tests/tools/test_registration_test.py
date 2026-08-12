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
TOOLS_TESTS = REPOSITORY_ROOT / "tests" / "tools"
TOOLS = REPOSITORY_ROOT / "tools"

# A verifier a slice added but never registered would go unrun in the same way.
# Only an executable entry point needs its own registration: a `verify_*.py`
# that another verifier imports is already covered by the one that imports it,
# so the executable guard rather than the file name is what distinguishes them.
VERIFIER_PATTERN = re.compile(r"^verify.*\.py$")
ENTRY_POINT = 'if __name__ == "__main__":'

# The fuzz entries are nested inside an `if()` block and close on an indented
# `)`, so a pattern anchored to a closing paren in column zero silently swallows
# all six into the preceding match instead of failing.
ADD_TEST = re.compile(r"add_test\(\s*NAME\s+(\S+)\s+COMMAND\s+(.*?)\n\s*\)", re.DOTALL)
BINARY_DIR_ARGUMENT = re.compile(r"\$\{CMAKE_CURRENT_BINARY_DIR\}/([^\"\s]+)")


def cmake_text() -> str:
    return CMAKE_LISTS.read_text(encoding="utf-8")


def registered_tests() -> list[tuple[str, str]]:
    return ADD_TEST.findall(cmake_text())


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

    def test_every_tools_test_is_registered(self) -> None:
        """These guard the gate itself, so the gate must not be their only caller.

        `tests/tools` is executed two ways, and they do not overlap: the focused
        metadata path runs `unittest discover` when the scope classifies
        `lightweight`, and `ctest` runs the registered entries when it
        classifies `full`. A module registered in neither runs on documentation
        changes only; a module registered here runs on both. This guard itself
        was in the first state, so the check that catches an unregistered test
        was skipped by every pull request able to add one.
        """
        text = cmake_text()
        missing = sorted(
            path.name
            for path in TOOLS_TESTS.glob("*_test.py")
            if f"tests/tools/{path.name}" not in text
        )
        self.assertEqual(
            missing,
            [],
            "these tests/tools modules have no add_test in CMakeLists.txt, so a "
            "full-scope pull request never runs them",
        )

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


class ParallelSafetyTest(unittest.TestCase):
    """`ctest` now runs entries concurrently, so two entries may not share a path.

    Every entry that writes runs in the one build directory, and each is given
    its own name under it. Two entries handed the same name passed while the
    run was serial and would race the moment it was not — the failure would be
    intermittent and would appear in an unrelated slice. The registration is
    where that collision is introduced, so it is checked statically rather than
    hunted in a flaky log.
    """

    def test_the_registration_parse_reaches_every_entry(self) -> None:
        """A pattern that matches nothing would pass the check below vacuously."""
        self.assertEqual(len(registered_tests()), cmake_text().count("add_test("))

    def test_no_two_entries_are_handed_the_same_build_directory_path(self) -> None:
        owners: dict[str, list[str]] = {}
        for name, body in registered_tests():
            for path in BINARY_DIR_ARGUMENT.findall(body):
                owners.setdefault(path, []).append(name)
        shared = {path: names for path, names in owners.items() if len(names) > 1}
        self.assertEqual(
            shared,
            {},
            "these build-directory paths are used by more than one registered "
            "test, so the entries would race under ctest --parallel",
        )

    def test_every_registered_entry_has_a_unique_name(self) -> None:
        names = [name for name, _ in registered_tests()]
        duplicated = sorted({name for name in names if names.count(name) > 1})
        self.assertEqual(duplicated, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
