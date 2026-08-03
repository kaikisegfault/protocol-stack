#!/usr/bin/env python3

from pathlib import Path
import sys
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "tools"))

from verification_scope import classify, is_lightweight_path  # noqa: E402


class VerificationScopeTest(unittest.TestCase):
    def test_documentation_and_skill_metadata_are_lightweight(self) -> None:
        paths = [
            "README.md",
            "docs/project/current-state.md",
            "docs/architecture/diagram.svg",
            ".claude/skills/conclude-project/SKILL.md",
        ]
        self.assertTrue(all(is_lightweight_path(path) for path in paths))
        self.assertEqual(classify(paths), "lightweight")

    def test_executable_and_control_files_force_full_verification(self) -> None:
        paths = [
            "src/v1/ledger.cpp",
            "tools/verify.sh",
            "tools/verification_scope.py",
            ".claude/skills/example/scripts/check.py",
            ".github/workflows/verify.yml",
            ".claude/settings.json",
            "CMakeLists.txt",
            "adapter/cometbft/go.mod",
        ]
        for path in paths:
            with self.subTest(path=path):
                self.assertFalse(is_lightweight_path(path))
                self.assertEqual(classify(["README.md", path]), "full")

    def test_empty_or_unsafe_path_sets_fail_closed(self) -> None:
        self.assertEqual(classify([]), "full")
        self.assertFalse(is_lightweight_path("../README.md"))
        self.assertFalse(is_lightweight_path("/README.md"))


if __name__ == "__main__":
    unittest.main()
