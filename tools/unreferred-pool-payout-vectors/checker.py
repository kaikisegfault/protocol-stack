"""Vector file reading, the fail-closed checker, and the reproducible emitter.

The checker fails in both directions: a derived key the file does not carry is a
failure, and a recorded key no derivation reaches is also a failure, so partial
coverage cannot report success and the file cannot hold a claim nothing
reproduces.

`docs/engineering/verification.md`'s three rules apply. **A boolean vector may
only be true**, because its name is the claim and recording `false` records the
negation. **A name asserts no more than its value establishes.** **A claim is
checked against something other than itself**, which here means every value is
produced twice — once by `expected.py`, which imports nothing from `simulation/`
and settles the whole sequence in closed form, and once by a live run of the
model, which is a machine consuming one window at a time. Two different
constructions agreeing is the evidence.

**`--emit` writes the file rather than checking it, and it is not a repair
tool.** It runs the identical derivations through the identical `agree` gate, so
it can only ever write a value the independent derivation and the model already
produce alike. A disagreement fails in emit mode exactly as it fails in check
mode; what emit removes is the transcription step, not the evidence. The hosted
matrix runs the checking mode over the committed file.
"""

from __future__ import annotations

from pathlib import Path

HEADER = """\
# Unreferred pool payout v1 normative vectors.
# Amounts are unsigned decimal atomic units at the eight-decimal denomination.
# Uptime figures are unsigned decimal seconds. Month indices are calendar-v1's,
# counted from January 1970.
#
# Every value here is derived twice: once by
# tools/unreferred-pool-payout-vectors/expected.py, which imports nothing from
# simulation/ and settles the whole sequence in closed form, and once by a live
# run of simulation/unreferred_pool, which is a machine consuming one window at
# a time. A boolean vector may only be true, because its name is the claim.
#
# The scenario is simulation/unreferred_pool/scenario.py. Its genesis sits off a
# day boundary so a window straddles a month boundary, and its months reach a
# single winner, a two-way tie over an odd balance, a three-way tie, a month
# every candidate ran zero seconds in, and two months a halt left with no window
# at all.
"""


def render(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, bytes):
        return value.hex()
    return str(value)


def falsified(key: str, derived: object) -> str | None:
    if isinstance(derived, bool) and not derived:
        return f"{key}: a boolean vector asserts its own name, and this one is false"
    return None


class Checker:
    def __init__(self, recorded: dict[str, str], emit: bool = False) -> None:
        self.recorded = recorded
        self.emit = emit
        self.failures: list[str] = []
        self.seen: set[str] = set()
        self.emitted: list[tuple[str, str]] = []
        self._sections: dict[str, str] = {}
        self._pending_section: str | None = None

    @property
    def checked(self) -> int:
        return len(self.seen)

    def section(self, comment: str) -> None:
        """Mark the next emitted key as opening a commented section."""
        self._pending_section = comment

    def equal(self, key: str, derived: object) -> None:
        negated = falsified(key, derived)
        if negated is not None:
            self.failures.append(negated)
            return
        rendered = render(derived)
        if self.emit:
            if key in self.seen:
                self.failures.append(f"{key}: derived twice")
                return
            self.seen.add(key)
            self.emitted.append((key, rendered))
            comment = self._pending_section
            if comment:
                self._sections[key] = comment
                self._pending_section = None
            return
        if key not in self.recorded:
            self.failures.append(f"{key}: not recorded in the vector file")
            return
        self.seen.add(key)
        if rendered != self.recorded[key]:
            self.failures.append(
                f"{key}: derived {rendered!r}, recorded {self.recorded[key]!r}"
            )

    def agree(self, key: str, closed_form: object, live: object) -> None:
        """Record a value only when the independent derivation and the model agree.

        A vector only the model reproduces would be a restatement of the model
        rather than evidence about it.
        """
        if render(closed_form) != render(live):
            self.failures.append(
                f"{key}: the independent derivation gives {closed_form!r} but the "
                f"model gives {live!r}"
            )
            return
        self.equal(key, closed_form)

    def require_full_coverage(self) -> None:
        if self.emit:
            return
        for key in sorted(set(self.recorded) - self.seen):
            self.failures.append(f"{key}: recorded but never derived")

    def write(self, path: Path) -> int:
        lines = [HEADER]
        for key, value in self.emitted:
            comment = self._sections.get(key)
            if comment:
                lines.append(f"\n# {comment}")
            lines.append(f"{key}={value}")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return len(self.emitted)


def read_vectors(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, separator, value = stripped.partition("=")
        if not separator or key in values:
            raise ValueError(f"{path}:{number}: malformed or duplicate vector line")
        values[key] = value
    return values
