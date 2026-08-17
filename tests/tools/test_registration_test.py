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

# A fuzz executable is registered in four separate places, and each omission
# fails differently. Missing from `PROTOCOL_STACK_TARGETS` it builds without
# `-Werror`, the sanitizer flags, or the libsodium link — the M3.9a defect, and
# the quiet one. Missing from the instrumentation loop it builds without
# coverage feedback and fuzzes nothing while reporting success. Missing from the
# link loop it has no libFuzzer `main` and fails to link, which is how M3.10c
# found this guard was needed.
FUZZ_SOURCE = REPOSITORY_ROOT / "tests" / "fuzz"
FUZZ_EXECUTABLE = re.compile(
    r"add_executable\(\s*(\S+)\s+(tests/fuzz/\S+\.cpp)\s*\)", re.DOTALL
)
# Each list is read as a list rather than searched for as a substring. The first
# draft of this guard split the file at the first `PROTOCOL_STACK_TARGETS` and
# looked for an indented name in everything after it — which matched the
# target's own `add_executable` block and passed with the target removed from
# the list entirely. That is the vacuous shape
# `docs/engineering/verification.md`'s third rule names, in the guard written to
# catch a silent omission.
# The `set(...)` block closes in column zero and the `list(APPEND ...)` block is
# nested inside `if(PROTOCOL_STACK_ENABLE_FUZZING)` and closes on an indented
# paren, so the close must tolerate leading space. Anchored to column zero the
# second block does not terminate and the match runs on into unrelated
# `add_executable` blocks, which is how the first draft found a name it had just
# been asked to notice was missing.
TARGET_LIST = re.compile(
    r"(?:set|list)\(\s*(?:APPEND\s+)?PROTOCOL_STACK_TARGETS\s+(.*?)\n\s*\)", re.DOTALL
)
FOREACH_ITEMS = re.compile(
    r"foreach\(\s*\S+\s+IN ITEMS\s+(.*?)\n\s*\)\n(.*?)endforeach\(\)", re.DOTALL
)


def cmake_word_set(body: str) -> set[str]:
    return {word for word in body.split() if re.fullmatch(r"[A-Za-z_][\w-]*", word)}


def project_build_targets() -> set[str]:
    names: set[str] = set()
    for body in TARGET_LIST.findall(cmake_text()):
        names |= cmake_word_set(body)
    return names


def foreach_items_containing(flag: str) -> set[str]:
    """The items of every `foreach` whose body applies exactly `flag`."""
    names: set[str] = set()
    for items, body in FOREACH_ITEMS.findall(cmake_text()):
        applied = re.findall(r"-fsanitize=fuzzer(?:-no-link)?", body)
        if flag in applied:
            names |= cmake_word_set(items)
    return names


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


class FuzzTargetRegistrationTest(unittest.TestCase):
    """A fuzz executable is registered four times and each omission fails apart.

    Two of the four fail loudly and two do not. Left out of the link loop the
    target has no libFuzzer `main` and does not link; left out of
    `PROTOCOL_STACK_TARGETS` it links and runs while held to weaker rules than
    everything around it, and left out of the instrumentation loop it runs with
    no coverage feedback and explores nothing while reporting success. The
    quiet two are why this is checked statically.
    """

    def test_the_fuzz_parse_reaches_every_target(self) -> None:
        """A pattern that matched nothing would pass every check below."""
        sources = sorted(path.name for path in FUZZ_SOURCE.glob("*.cpp"))
        found = FUZZ_EXECUTABLE.findall(cmake_text())
        self.assertEqual(
            sorted(Path(source).name for _, source in found),
            sources,
            "every file under tests/fuzz must have exactly one add_executable",
        )

    def test_the_target_and_foreach_lists_parse(self) -> None:
        """Three lists, each of which would pass every check below if empty.

        The build-target list is two blocks — the unconditional `set` and the
        `list(APPEND)` the fuzzing option adds — and a pattern that reached only
        the first would still find every fuzz target, in the `add_executable`
        blocks the runaway match swallowed.
        """
        self.assertEqual(len(TARGET_LIST.findall(cmake_text())), 2)
        targets = project_build_targets()
        self.assertIn("protocol_kernel", targets)
        self.assertIn("kernel_admission_fuzz", targets)
        self.assertNotIn("tests/fuzz/economy_v6_fuzz.cpp", targets)
        self.assertNotEqual(foreach_items_containing("-fsanitize=fuzzer-no-link"), set())
        self.assertNotEqual(foreach_items_containing("-fsanitize=fuzzer"), set())

    def test_every_fuzz_target_carries_the_project_build_rules(self) -> None:
        targets = {name for name, _ in FUZZ_EXECUTABLE.findall(cmake_text())}
        self.assertNotEqual(targets, set())
        self.assertEqual(
            sorted(targets - project_build_targets()),
            [],
            "these fuzz targets are absent from PROTOCOL_STACK_TARGETS, so they "
            "build without -Werror, the sanitizer flags, and the libsodium link",
        )

    def test_every_fuzz_target_is_instrumented_and_linked(self) -> None:
        targets = {name for name, _ in FUZZ_EXECUTABLE.findall(cmake_text())}
        self.assertEqual(
            sorted(targets - foreach_items_containing("-fsanitize=fuzzer-no-link")),
            [],
            "these fuzz targets are not compiled with -fsanitize=fuzzer-no-link, "
            "so they run with no coverage feedback and explore nothing",
        )
        self.assertEqual(
            sorted(targets - foreach_items_containing("-fsanitize=fuzzer")),
            [],
            "these fuzz targets are not linked with -fsanitize=fuzzer, so they "
            "have no libFuzzer entry point",
        )

    def test_every_fuzz_target_has_a_bounded_smoke_entry(self) -> None:
        targets = {name for name, _ in FUZZ_EXECUTABLE.findall(cmake_text())}
        registered = {
            body.split()[0] for name, body in registered_tests() if name.endswith("-fuzz-smoke")
        }
        self.assertEqual(
            sorted(targets - registered),
            [],
            "these fuzz targets have no registered smoke entry, so the hosted "
            "matrix never runs them",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
