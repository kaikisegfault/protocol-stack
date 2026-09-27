#!/usr/bin/env python3
"""Validate repository documentation and Claude skill metadata."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MARKDOWN_LINK = re.compile(r"!?\[[^]]*\]\(([^)]+)\)")
ATX_HEADING = re.compile(r"^ {0,3}#{1,6}[ \t]+(.*?)(?:[ \t]+#+)?[ \t]*$")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
INLINE_LINK = re.compile(r"!?\[([^]]*)\]\([^)]*\)")
SLUG_REMOVED = re.compile(r"[^\w\- ]")
REQUIRED_PATHS = (
    "CLAUDE.md",
    ".claude/settings.json",
    "docs/project/current-state.md",
    "docs/project/charter.md",
    "docs/project/first-goal.md",
    "tools/clean-local.sh",
    ".claude/skills/change-protocol/SKILL.md",
    ".claude/skills/proceed-project/SKILL.md",
    ".claude/skills/verify-project/SKILL.md",
)


def front_matter(path: Path, errors: list[str]) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        errors.append(f"{path}: missing opening frontmatter delimiter")
        return {}
    try:
        end = lines.index("---", 1)
    except ValueError:
        errors.append(f"{path}: missing closing frontmatter delimiter")
        return {}
    values: dict[str, str] = {}
    for line in lines[1:end]:
        key, separator, value = line.partition(":")
        if not separator or not key or not value.strip() or key in values:
            errors.append(f"{path}: invalid frontmatter line {line!r}")
            continue
        values[key] = value.strip().strip('"')
    if set(values) != {"name", "description"}:
        errors.append(f"{path}: frontmatter must contain only name and description")
    return values


def validate_skill(skill_dir: Path, errors: list[str]) -> None:
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        errors.append(f"{skill_dir}: missing SKILL.md")
        return
    values = front_matter(skill_file, errors)
    name = values.get("name", "")
    if name != skill_dir.name or not SKILL_NAME.fullmatch(name):
        errors.append(f"{skill_file}: name must match its lowercase hyphenated directory")
    if not values.get("description", "").strip():
        errors.append(f"{skill_file}: description must not be empty")

    for path in skill_dir.rglob("*"):
        if path.is_file() and path.suffix in {".md", ".yaml", ".yml"}:
            text = path.read_text(encoding="utf-8")
            if "[TODO" in text or "TODO:" in text:
                errors.append(f"{path}: unresolved template TODO marker")


def link_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    elif " " in target:
        target = target.split(" ", 1)[0]
    return target


def heading_slug(heading: str) -> str:
    """GitHub's anchor for one heading's text, before duplicate numbering.

    **Each space becomes a hyphen, and runs are not collapsed.** So a heading
    reading "Kind 10 — hub_register" anchors as `kind-10--hub_register`:
    removing the em-dash leaves two spaces. A checker that collapsed them would
    report a false failure against nearly every heading here that carries a
    dash.
    """
    text = INLINE_LINK.sub(r"\1", heading).strip().lower()
    return SLUG_REMOVED.sub("", text).replace(" ", "-")


def markdown_anchors(path: Path) -> set[str]:
    """Every anchor GitHub renders for a file's ATX headings.

    Headings inside fenced code blocks are text, not headings. A repeated slug
    takes `-1`, `-2`, and so on, in document order.
    """
    anchors: set[str] = set()
    seen: dict[str, int] = {}
    fence = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        opened = FENCE.match(line)
        if opened:
            marker = opened.group(1)
            if not fence:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = ""
            continue
        if fence:
            continue
        heading = ATX_HEADING.match(line)
        if not heading:
            continue
        slug = heading_slug(heading.group(1))
        count = seen.get(slug, 0)
        seen[slug] = count + 1
        anchors.add(slug if count == 0 else f"{slug}-{count}")
    return anchors


def validate_markdown_links(root: Path, errors: list[str]) -> int:
    """Check every internal link's file, and its fragment when it names one.

    A fragment is checked only against a Markdown target, the linking file
    itself included, because that is the only kind whose anchors are known here.
    """
    checked = 0
    resolved_root = root.resolve()
    anchors: dict[Path, set[str]] = {}
    for markdown in sorted(root.rglob("*.md")):
        if any(part in {".git", ".cache", "out"} for part in markdown.parts):
            continue
        text = markdown.read_text(encoding="utf-8")
        for match in MARKDOWN_LINK.finditer(text):
            target = link_target(match.group(1))
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc:
                continue
            relative = unquote(parsed.path)
            if not relative:
                resolved = markdown.resolve()
            else:
                candidate = root / relative.lstrip("/") if relative.startswith("/") else markdown.parent / relative
                resolved = candidate.resolve()
            checked += 1
            if not resolved.is_relative_to(resolved_root) or not resolved.exists():
                errors.append(f"{markdown}: missing or out-of-tree link target {target!r}")
                continue
            if not parsed.fragment or resolved.suffix != ".md" or not resolved.is_file():
                continue
            if resolved not in anchors:
                anchors[resolved] = markdown_anchors(resolved)
            if unquote(parsed.fragment) not in anchors[resolved]:
                errors.append(f"{markdown}: link target {target!r} names no heading")
    return checked


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    return parser.parse_args()


def main() -> int:
    root = parse_args().root.resolve()
    errors: list[str] = []
    for relative in REQUIRED_PATHS:
        if not (root / relative).exists():
            errors.append(f"missing required repository path: {relative}")
    config_path = root / ".claude" / "settings.json"
    if config_path.is_file():
        try:
            json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            errors.append(f"{config_path}: invalid JSON: {error}")
    skill_dirs = sorted(path for path in (root / ".claude" / "skills").iterdir() if path.is_dir())
    for skill_dir in skill_dirs:
        validate_skill(skill_dir, errors)
    link_count = validate_markdown_links(root, errors)
    if errors:
        for error in errors:
            print(error)
        return 1
    print(f"Validated {len(skill_dirs)} repository skills and {link_count} internal Markdown links.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
