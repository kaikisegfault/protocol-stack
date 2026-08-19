"""Vector file reading and the fail-closed comparison used by both verifiers.

A verifier that only compared the values it happened to derive would pass on a
file full of unreached claims, and one that only checked recorded keys would
pass when a derivation produced a value the file never fixed. Both directions
are failures here.
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
        expected_value = self.recorded[key]
        if str(derived) != expected_value:
            self.failures.append(
                f"{key}: derived {derived!r}, recorded {expected_value!r}"
            )

    def agree(
        self,
        key: str,
        closed_form: object,
        cross_check: object,
        source: str = "the manifest",
    ) -> None:
        """Record a value only when two independent sources agree.

        `closed_form` is always the constitutional derivation in `expected.py`.
        `source` names where `cross_check` came from, so a mismatch says which
        two things disagree rather than naming a source that was not consulted.
        """
        if str(closed_form) != str(cross_check):
            self.failures.append(
                f"{key}: the constitution derives {closed_form!r} but {source} "
                f"carries {cross_check!r}"
            )
            return
        self.equal(key, closed_form)

    def require_full_coverage(self) -> None:
        """Fail closed when a recorded vector was never derived."""
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
