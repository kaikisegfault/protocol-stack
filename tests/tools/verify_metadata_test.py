#!/usr/bin/env python3

from pathlib import Path
import sys
import tempfile
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "tools"))

from verify_metadata import (  # noqa: E402
    HANDOFF,
    HANDOFF_LINE_LIMIT,
    heading_slug,
    validate_handoff_length,
    validate_markdown_links,
    validate_skill,
)


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

    def test_heading_slugs_follow_github(self) -> None:
        # Each space is a hyphen, so a dash between spaces leaves two.
        self.assertEqual(heading_slug("Kind 10 — `hub_register`"), "kind-10--hub_register")
        self.assertEqual(heading_slug("**Bold** and [a link](x.md)"), "bold-and-a-link")
        self.assertEqual(heading_slug("ADR 0070: What, and why?"), "adr-0070-what-and-why")

    def test_fragments_must_name_a_heading(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "target.md").write_text(
                "# Target\n\n## Kind 10 — `hub_register`\n\n## Twice\n\n## Twice\n\n"
                "```text\n## Fenced\n```\n",
                encoding="utf-8",
            )
            source = root / "source.md"
            source.write_text(
                "# Source\n\n[a](target.md#kind-10--hub_register) [b](target.md#twice-1) "
                "[c](#source) [d](target.md#target)\n",
                encoding="utf-8",
            )
            errors: list[str] = []
            self.assertEqual(validate_markdown_links(root, errors), 4)
            self.assertEqual(errors, [])
            for broken in (
                "target.md#kind-10-hub_register",
                "target.md#twice-2",
                "target.md#fenced",
                "#nowhere",
            ):
                source.write_text(f"# Source\n\n[x]({broken})\n", encoding="utf-8")
                errors = []
                validate_markdown_links(root, errors)
                self.assertEqual(len(errors), 1, broken)

    def test_handoff_is_refused_above_its_line_limit(self) -> None:
        # The limit is written out so that moving the constant fails here.
        self.assertEqual(HANDOFF_LINE_LIMIT, 600)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            errors: list[str] = []
            self.assertEqual(validate_handoff_length(root, errors), 0)
            self.assertEqual(errors, [])
            handoff = root / HANDOFF
            handoff.parent.mkdir(parents=True)
            handoff.write_text("line\n" * 600, encoding="utf-8")
            self.assertEqual(validate_handoff_length(root, errors), 600)
            self.assertEqual(errors, [])
            handoff.write_text("line\n" * 601, encoding="utf-8")
            self.assertEqual(validate_handoff_length(root, errors), 601)
            self.assertEqual(len(errors), 1)
            self.assertIn("601 lines", errors[0])


if __name__ == "__main__":
    unittest.main()
