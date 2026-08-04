"""Vector file reading and the derive-and-compare checker.

The checker fails closed in both directions: a derived key missing from the file
is a failure, and a recorded key that is never derived is also a failure, so the
file cannot carry a value no implementation reproduces.
"""

from __future__ import annotations

from pathlib import Path


class Checker:
    def __init__(self, recorded: dict[str, str]) -> None:
        self.recorded = recorded
        self.failures: list[str] = []
        self.seen: set[str] = set()

    @property
    def checked(self) -> int:
        return len(self.seen)

    def equal(self, key: str, derived: object) -> None:
        if key not in self.recorded:
            self.failures.append(f"{key}: not recorded in the vector file")
            return
        self.seen.add(key)
        if str(derived) != self.recorded[key]:
            self.failures.append(
                f"{key}: derived {derived!r}, recorded {self.recorded[key]!r}"
            )

    def require_full_coverage(self) -> None:
        for key in sorted(set(self.recorded) - self.seen):
            self.failures.append(f"{key}: recorded but never derived")


def read_vectors(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, separator, value = stripped.partition("=")
        if not separator or key in values:
            raise ValueError(f"{path}:{number}: malformed or duplicate vector line")
        values[key] = value
    return values
