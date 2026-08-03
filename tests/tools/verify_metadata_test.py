#!/usr/bin/env python3

from pathlib import Path
import sys
import tempfile
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "tools"))

from verify_metadata import validate_markdown_links, validate_skill  # noqa: E402


VALID_SKILL = """---
name: test-skill
description: Exercise the repository metadata validator.
---

# Test skill
"""


class VerifyMetadataTest(unittest.TestCase):
    def make_skill(self, root: Path) -> Path:
        skill_dir = root / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(VALID_SKILL, encoding="utf-8")
        return skill_dir

    def test_valid_skill_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            errors: list[str] = []
            validate_skill(self.make_skill(Path(directory)), errors)
            self.assertEqual(errors, [])

    def test_name_mismatch_and_todo_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill_dir = self.make_skill(Path(directory))
            content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
            (skill_dir / "SKILL.md").write_text(content.replace("test-skill", "other-skill") + "\nTODO: finish\n", encoding="utf-8")
            errors: list[str] = []
            validate_skill(skill_dir, errors)
            self.assertGreaterEqual(len(errors), 2)

    def test_internal_links_exist_and_external_links_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "target.md").write_text("# Target\n", encoding="utf-8")
            source = root / "source.md"
            source.write_text("[ok](target.md) [web](https://example.com)\n", encoding="utf-8")
            errors: list[str] = []
            self.assertEqual(validate_markdown_links(root, errors), 1)
            self.assertEqual(errors, [])
            source.write_text("[missing](missing.md)\n", encoding="utf-8")
            self.assertEqual(validate_markdown_links(root, errors), 1)
            self.assertEqual(len(errors), 1)


if __name__ == "__main__":
    unittest.main()
