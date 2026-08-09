"""Vector file reading and the fail-closed derive-and-compare checker.

The checker fails in both directions. A derived key the file does not carry is a
failure, and a recorded key no derivation reaches is also a failure, so partial
coverage cannot report success and the file cannot hold a claim nothing
reproduces.
"""

from __future__ import annotations

from pathlib import Path


def render(value: object) -> str:
    """Render a derived value the way the vector files spell it.

    Booleans are lowercase so a recorded claim reads as `true` rather than as
    Python's `True`, matching every accepted vector file in `test-vectors/`.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


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
        recorded_value = self.recorded[key]
        if render(derived) != recorded_value:
            self.failures.append(
                f"{key}: derived {derived!r}, recorded {recorded_value!r}"
            )

    def agree(self, key: str, closed_form: object, live: object) -> None:
        """Record a value only when the founder derivation and the model agree.

        `closed_form` is always `expected.py`, which imports nothing from
        `simulation/`. A vector only the model reproduces would be a restatement
        of the model rather than evidence about it.
        """
        if render(closed_form) != render(live):
            self.failures.append(
                f"{key}: the founder derivation gives {closed_form!r} but the "
                f"model gives {live!r}"
            )
            return
        self.equal(key, closed_form)

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
