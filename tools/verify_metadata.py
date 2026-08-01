#!/usr/bin/env python3
"""Validate repository documentation and Codex skill metadata."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import tomllib
from urllib.parse import unquote, urlsplit


SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
INTERFACE_VALUE = re.compile(r'^  ([a-z_]+): "([^"]*)"$')
MARKDOWN_LINK = re.compile(r"!?\[[^]]*\]\(([^)]+)\)")
REQUIRED_PATHS = (
    "AGENTS.md",
    ".codex/config.toml",
    "docs/project/current-state.md",
    "docs/project/charter.md",
    "docs/project/first-goal.md",
    "tools/clean-local.sh",
    ".agents/skills/change-protocol/SKILL.md",
    ".agents/skills/proceed-project/SKILL.md",
    ".agents/skills/verify-project/SKILL.md",
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


def interface_metadata(path: Path, errors: list[str]) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "interface:":
        errors.append(f"{path}: missing interface mapping")
        return {}
    values: dict[str, str] = {}
    for line in lines[1:]:
        if not line or not line.startswith(" "):
            break
        match = INTERFACE_VALUE.fullmatch(line)
        if not match:
            errors.append(f"{path}: interface strings must be two-space indented and quoted")
            continue
        key, value = match.groups()
        if key in values:
            errors.append(f"{path}: duplicate interface field {key}")
        values[key] = value
    required = {"display_name", "short_description", "default_prompt"}
    if not required.issubset(values):
        errors.append(f"{path}: missing required interface fields")
    return values


def validate_skill(skill_dir: Path, errors: list[str]) -> None:
    skill_file = skill_dir / "SKILL.md"
    metadata_file = skill_dir / "agents" / "openai.yaml"
    if not skill_file.is_file() or not metadata_file.is_file():
        errors.append(f"{skill_dir}: missing SKILL.md or agents/openai.yaml")
        return
    values = front_matter(skill_file, errors)
    name = values.get("name", "")
    if name != skill_dir.name or not SKILL_NAME.fullmatch(name):
        errors.append(f"{skill_file}: name must match its lowercase hyphenated directory")
    if not values.get("description", "").strip():
        errors.append(f"{skill_file}: description must not be empty")

    interface = interface_metadata(metadata_file, errors)
    short_description = interface.get("short_description", "")
    if short_description and not 25 <= len(short_description) <= 64:
        errors.append(f"{metadata_file}: short_description must contain 25-64 characters")
    if name and f"${name}" not in interface.get("default_prompt", ""):
        errors.append(f"{metadata_file}: default_prompt must mention ${name}")

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


def validate_markdown_links(root: Path, errors: list[str]) -> int:
    checked = 0
    resolved_root = root.resolve()
    for markdown in sorted(root.rglob("*.md")):
        if any(part in {".git", ".cache", "out"} for part in markdown.parts):
            continue
        text = markdown.read_text(encoding="utf-8")
        for match in MARKDOWN_LINK.finditer(text):
            target = link_target(match.group(1))
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or target.startswith("#"):
                continue
            relative = unquote(parsed.path)
            if not relative:
                continue
            candidate = root / relative.lstrip("/") if relative.startswith("/") else markdown.parent / relative
            resolved = candidate.resolve()
            checked += 1
            if not resolved.is_relative_to(resolved_root) or not resolved.exists():
                errors.append(f"{markdown}: missing or out-of-tree link target {target!r}")
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
    config_path = root / ".codex" / "config.toml"
    if config_path.is_file():
        try:
            with config_path.open("rb") as config_file:
                tomllib.load(config_file)
        except tomllib.TOMLDecodeError as error:
            errors.append(f"{config_path}: invalid TOML: {error}")
    skill_dirs = sorted(path for path in (root / ".agents" / "skills").iterdir() if path.is_dir())
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
