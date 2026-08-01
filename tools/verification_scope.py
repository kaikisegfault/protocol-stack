#!/usr/bin/env python3
"""Classify a changed-path set for risk-proportionate verification."""

from __future__ import annotations

import argparse
from pathlib import PurePosixPath
import sys


STATIC_DOCUMENT_SUFFIXES = {
    ".avif",
    ".gif",
    ".jpeg",
    ".jpg",
    ".png",
    ".svg",
    ".webp",
}
ROOT_DOCUMENTS = {"LICENSE", "NOTICE"}


def is_lightweight_path(raw_path: str) -> bool:
    path = PurePosixPath(raw_path)
    parts = path.parts
    if not parts or path.is_absolute() or ".." in parts:
        return False
    if path.suffix.lower() == ".md" or raw_path in ROOT_DOCUMENTS:
        return True
    if parts[0] == "docs" and path.suffix.lower() in STATIC_DOCUMENT_SUFFIXES:
        return True
    return (
        len(parts) == 5
        and parts[:2] == (".agents", "skills")
        and parts[-2:] == ("agents", "openai.yaml")
    )


def classify(paths: list[str]) -> str:
    if not paths:
        return "full"
    return "lightweight" if all(is_lightweight_path(path) for path in paths) else "full"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--null",
        action="store_true",
        help="read NUL-delimited paths from standard input",
    )
    parser.add_argument("paths", nargs="*")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = list(args.paths)
    if args.null:
        raw_paths = sys.stdin.buffer.read().split(b"\0")
        paths.extend(raw.decode("utf-8", "surrogateescape") for raw in raw_paths if raw)
    print(classify(paths))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
