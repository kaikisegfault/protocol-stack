"""The uptime-measurement model: evidence in, a finalised record out.

Implements `docs/specifications/uptime-measurement-v1.md`. It holds no value,
issues nothing, and credits no unit. It consumes duty reports and challenge
responses, applies bounded disputes, and emits the `cycle_uptime_record` shape
`founder-economy-simulator-v2` already accepts.

Evidence only ever removes credit. A slot's bit begins set when a window opens
and every transition here can clear it; none can set it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from simulation.common.canonical import MAX_U64, CodedError, InvariantError, digest
from simulation.cycle_boundary.grid import window_first_height, window_of_height
from simulation.cycle_boundary.model import CycleBoundary

from . import contract as c
from .slots import is_selected, slot_last_height, slot_of_height


@dataclass(frozen=True)
class DutyReport:
    """One assigned duty and whether the seat performed it.

    A report exists only for a duty the seat was *assigned*. A seat outside the
    bounded live signing set produces none, and an empty assignment is satisfied
    vacuously rather than failed.
    """

    seat_id: int
    kind: str
    performed: bool


@dataclass(frozen=True)
class UptimeRecord:
    """A finalised window's measurements, in economy-v2's accepted shape."""

    cycle_window: int
    entries: tuple[tuple[int, int], ...]

    def as_economy_input(self) -> dict[str, object]:
        return {
            "cycle_window": self.cycle_window,
            "entries": [
                {"seat_id": seat_id, "uptime_seconds": seconds}
                for seat_id, seconds in self.entries
            ],
        }


@dataclass
class UptimeMeasurement:
    ai_key: str
    bound_schedule_digest: str | None = None
    schedule: CycleBoundary | None = None
    height: int | None = None
    window_bitmaps: dict[int, dict[int, set[int]]] = field(default_factory=dict)
    slot_issued: dict[int, int] = field(default_factory=dict)
    slot_answered: dict[int, int] = field(default_factory=dict)
    answered: set[tuple[int, int]] = field(default_factory=set)
    duties_seen: set[tuple[int, str]] = field(default_factory=set)
    disputed: dict[int, dict[int, set[int]]] = field(default_factory=dict)
    beacons: dict[int, str] = field(default_factory=dict)
    closed_windows: set[int] = field(default_factory=set)

    # --- bindings -------------------------------------------------------

    def bind_schedule(self, schedule: CycleBoundary, recorded_digest: str) -> None:
        """Bind the activation table the in-scope seat set is derived from.

        Recomputing the digest proves consistency and not provenance: a
        self-consistent invented schedule would also bind. The verifier closes
        that gap by requiring this model's fixture to bind a live
        cycle-boundary run.
        """
        if self.bound_schedule_digest is not None:
            raise CodedError("REPLAY", "the schedule is already bound")
        if schedule.state_digest() != recorded_digest:
            raise CodedError(
                "INVALID_BOUND_SCHEDULE",
                f"schedule digest {schedule.state_digest()} is not {recorded_digest}",
            )
        self.bound_schedule_digest = recorded_digest
        self.schedule = schedule

    # --- scope ----------------------------------------------------------

    def in_scope(self, window: int) -> list[int]:
        """Seats activated strictly before the window's first height.

        A seat activated inside a window cannot have evidence for the whole
        window, and `cycle-boundary-v1` already opens a seat's first cycle at
        the next full window for the same reason.
        """
        self._require_bound()
        assert self.schedule is not None
        first_height = window_first_height(window)
        return sorted(
            seat_id
            for seat_id, activation in self.schedule.activation_heights.items()
            if activation < first_height
        )

    # --- transitions ----------------------------------------------------

    def execute_block(
        self,
        height: int,
        beacon: str,
        duty_reports: tuple[DutyReport, ...] = (),
    ) -> None:
        """Advance one height, apply its duty reports, close a slot or window.

        Closing is driven by height rather than by a caller, so a window
        finalises at a chain-defined point that every node reaches identically.

        A slot closes when the first height of the next slot executes rather
        than at the end of its own last height. A response is carried by a block
        like any transaction, so a response to a challenge at the slot's last
        challengeable height is submitted while that slot's final height is the
        executed one; closing eagerly would discard it.
        """
        self._require_bound()
        _require_count(height, "height")

        if height > c.MAX_HEIGHT:
            raise CodedError("HEIGHT_RANGE", f"height {height} above {c.MAX_HEIGHT}")
        expected = 0 if self.height is None else self.height + 1
        if height != expected:
            raise CodedError(
                "HEIGHT_NOT_MONOTONIC", f"height {height} is not the successor {expected}"
            )

        window = window_of_height(height)
        scope = set(self.in_scope(window))
        if self.height is not None:
            previous_window = window_of_height(self.height)
            previous_slot = slot_of_height(self.height)
            if (previous_window, previous_slot) != (window, slot_of_height(height)):
                self._close_slot(previous_window, previous_slot, set(self.in_scope(previous_window)))
        self._open_window(window, scope)

        seen: set[tuple[int, str]] = set()
        for report in duty_reports:
            _require_count(report.seat_id, "seat_id")
            if report.seat_id > c.MAX_SEAT_ID:
                raise CodedError("SEAT_RANGE", f"seat {report.seat_id} above {c.MAX_SEAT_ID}")
            if report.seat_id not in scope:
                raise CodedError(
                    "SEAT_NOT_IN_SCOPE", f"seat {report.seat_id} is not in window {window}"
                )
            if report.kind not in c.DUTY_KINDS:
                raise CodedError("INVALID_DUTY_KIND", f"duty kind {report.kind!r} is unknown")
            key = (report.seat_id, report.kind)
            if key in seen:
                raise CodedError(
                    "DUTY_REPLAY", f"seat {report.seat_id} reports {report.kind} twice"
                )
            seen.add(key)

        self.height = height
        self.beacons[height] = beacon

        slot = slot_of_height(height)
        for report in duty_reports:
            if not report.performed:
                self.window_bitmaps[window][report.seat_id].discard(slot)

        for seat_id in sorted(scope):
            if is_selected(seat_id, height, beacon):
                self.slot_issued[seat_id] = self.slot_issued.get(seat_id, 0) + 1

    def submit_response(self, seat_id: int, challenge_height: int, answer_ok: bool) -> None:
        """Record a seat's answer to a challenge issued at `challenge_height`.

        Conditions 4 and 7 are the containment conditions: a seat cannot
        manufacture credit by answering a challenge it was never issued, and
        cannot cover a missed challenge by answering an issued one twice.
        """
        self._require_bound()
        _require_count(seat_id, "seat_id")
        _require_count(challenge_height, "challenge_height")
        if self.height is None:
            raise CodedError("CHALLENGE_NOT_OPEN", "no block has executed")

        window = window_of_height(self.height)
        if seat_id > c.MAX_SEAT_ID:
            raise CodedError("SEAT_RANGE", f"seat {seat_id} above {c.MAX_SEAT_ID}")
        if seat_id not in set(self.in_scope(window)):
            raise CodedError("SEAT_NOT_IN_SCOPE", f"seat {seat_id} is not in window {window}")

        slot = slot_of_height(self.height)
        if window_of_height(challenge_height) != window or slot_of_height(challenge_height) != slot:
            raise CodedError(
                "CHALLENGE_NOT_OPEN",
                f"height {challenge_height} is outside the open slot {slot}",
            )
        beacon = self.beacons.get(challenge_height)
        if beacon is None or not is_selected(seat_id, challenge_height, beacon):
            raise CodedError(
                "CHALLENGE_NOT_ISSUED",
                f"seat {seat_id} was not challenged at height {challenge_height}",
            )
        if self.height > challenge_height + c.RESPONSE_DEADLINE_BLOCKS:
            raise CodedError(
                "RESPONSE_TOO_LATE",
                f"height {self.height} is past the deadline "
                f"{challenge_height + c.RESPONSE_DEADLINE_BLOCKS}",
            )
        if (seat_id, challenge_height) in self.answered:
            raise CodedError(
                "RESPONSE_REPLAY", f"seat {seat_id} already answered height {challenge_height}"
            )
        if not answer_ok:
            raise CodedError("RESPONSE_INVALID", f"seat {seat_id} answered incorrectly")

        self.answered.add((seat_id, challenge_height))
        self.slot_answered[seat_id] = self.slot_answered.get(seat_id, 0) + 1

    def file_dispute(self, window: int, seat_id: int, slot: int, reason: str, signer: str) -> None:
        """Void one slot of one seat in a closed, not yet finalised window.

        The AI can only subtract. There is no transition that adds credit, so a
        captured key can reduce a result and never manufacture one.
        """
        self._require_bound()
        _require_count(window, "window")
        _require_count(seat_id, "seat_id")
        _require_count(slot, "slot")

        if signer != self.ai_key:
            raise CodedError("UNAUTHORIZED_DISPUTE", f"signer {signer!r} is not the AI key")
        if seat_id > c.MAX_SEAT_ID:
            raise CodedError("SEAT_RANGE", f"seat {seat_id} above {c.MAX_SEAT_ID}")
        if slot > c.MAX_SLOT_INDEX:
            raise CodedError("SLOT_RANGE", f"slot {slot} above {c.MAX_SLOT_INDEX}")
        if window not in self.closed_windows:
            raise CodedError("WINDOW_NOT_CLOSED", f"window {window} has not closed")
        if self.is_final(window):
            raise CodedError("DISPUTE_WINDOW_CLOSED", f"window {window} is already final")
        if seat_id not in set(self.in_scope(window)):
            raise CodedError("SEAT_NOT_IN_SCOPE", f"seat {seat_id} is not in window {window}")

        voided = self.disputed.setdefault(window, {}).setdefault(seat_id, set())
        if slot in voided:
            raise CodedError("DISPUTE_REPLAY", f"slot {slot} is already voided")
        if slot not in self.window_bitmaps[window][seat_id]:
            raise CodedError(
                "DISPUTE_SLOT_NOT_CREDITED", f"seat {seat_id} holds no credit for slot {slot}"
            )
        if len(voided) >= c.DISPUTE_CAP_SLOTS_PER_SEAT:
            raise CodedError(
                "DISPUTE_CAP_EXCEEDED",
                f"seat {seat_id} is at the {c.DISPUTE_CAP_SLOTS_PER_SEAT}-slot cap",
            )

        voided.add(slot)
        self._assert_dispute_containment(window, seat_id)

    # --- queries --------------------------------------------------------

    def is_final(self, window: int) -> bool:
        """Whether a window's result is final. Silence finalises it.

        No signature, liveness, quorum, or acknowledgement is required, so an
        outage of any length delays nothing and withholds nothing.
        """
        if self.height is None or window not in self.closed_windows:
            return False
        return window_of_height(self.height) >= window + c.DISPUTE_WINDOW_WINDOWS + 1

    def credited_slots(self, window: int, seat_id: int) -> int:
        bits = self.window_bitmaps.get(window, {}).get(seat_id, set())
        voided = self.disputed.get(window, {}).get(seat_id, set())
        return len(bits - voided)

    def uptime_seconds(self, window: int, seat_id: int) -> int:
        seconds = self.credited_slots(window, seat_id) * c.SLOT_SECONDS
        if seconds > c.CYCLE_BLOCKS * c.TARGET_COMMIT_SECONDS:
            raise InvariantError(f"seat {seat_id} exceeds a window's nominal duration")
        return seconds

    def emit_record(self, window: int) -> UptimeRecord:
        """The finalised record for a window. A pure query; it writes nothing.

        The seat set is derived from the bound schedule rather than supplied, so
        an omission is unrepresentable rather than detected.
        """
        if not self.is_final(window):
            raise CodedError("RECORD_NOT_FINAL", f"window {window} is not final")
        scope = self.in_scope(window)
        if not scope:
            raise CodedError("WINDOW_HAS_NO_SEATS", f"window {window} has no in-scope seats")

        entries = tuple((seat_id, self.uptime_seconds(window, seat_id)) for seat_id in scope)
        if [seat_id for seat_id, _ in entries] != scope:
            raise InvariantError("the emitted seat set is not the in-scope set")
        return UptimeRecord(window, entries)

    # --- canonical state ------------------------------------------------

    def canonical_state(self) -> dict[str, object]:
        return {
            "schema": c.STATE_SCHEMA,
            "slots_per_window": c.SLOTS_PER_WINDOW,
            "bound_schedule_digest": self.bound_schedule_digest,
            "height": None if self.height is None else _height_string(self.height),
            "windows": [
                {
                    "window": _height_string(window),
                    "closed": window in self.closed_windows,
                    "final": self.is_final(window),
                    "seats": [
                        {
                            "seat_id": seat_id,
                            "credited_slots": self.credited_slots(window, seat_id),
                            "voided_slots": sorted(
                                self.disputed.get(window, {}).get(seat_id, set())
                            ),
                        }
                        for seat_id in sorted(self.window_bitmaps[window])
                    ],
                }
                for window in sorted(self.window_bitmaps)
            ],
        }

    def state_digest(self) -> str:
        return digest(c.STATE_LABEL, self.canonical_state())

    # --- internals ------------------------------------------------------

    def _open_window(self, window: int, scope: set[int]) -> None:
        if window in self.window_bitmaps:
            return
        self.window_bitmaps[window] = {
            seat_id: set(range(c.SLOTS_PER_WINDOW)) for seat_id in scope
        }

    def _close_slot(self, window: int, slot: int, scope: set[int]) -> None:
        """Clear the bit of every seat that left a challenge unanswered.

        Then discard the counters. They are never carried across a slot
        boundary, which is what bounds the live state.
        """
        for seat_id in scope:
            if self.slot_issued.get(seat_id, 0) != self.slot_answered.get(seat_id, 0):
                self.window_bitmaps[window][seat_id].discard(slot)
        self.slot_issued = {}
        self.slot_answered = {}
        self.answered = set()
        self.beacons = {}
        if slot == c.MAX_SLOT_INDEX:
            self.closed_windows.add(window)

    def _require_bound(self) -> None:
        if self.bound_schedule_digest is None:
            raise CodedError("SCHEDULE_NOT_BOUND", "no activation schedule is bound")

    def _assert_dispute_containment(self, window: int, seat_id: int) -> None:
        """Invariant 5, asserted rather than left to the cap arithmetic.

        A seat credited for every slot must still meet its cycle after any
        admissible set of disputes, or the AI alone can fail a fully operational
        node.
        """
        voided = self.disputed[window][seat_id]
        if len(voided) > c.DISPUTE_CAP_SLOTS_PER_SEAT:
            raise InvariantError(f"seat {seat_id} exceeds the dispute cap in window {window}")
        perfect = c.SLOTS_PER_WINDOW - len(voided)
        if perfect < c.ACTIVITY_THRESHOLD_SLOTS:
            raise InvariantError(
                f"a maximal dispute leaves a perfect seat {perfect} slots, "
                f"below the {c.ACTIVITY_THRESHOLD_SLOTS}-slot threshold"
            )


def _height_string(value: int) -> str:
    if type(value) is not int or not 0 <= value <= MAX_U64:
        raise InvariantError(f"cannot format non-u64 height: {value!r}")
    return str(value)


def _require_count(value: object, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise InvariantError(f"{name} {value!r} is not an integer")
    if value < 0:
        raise InvariantError(f"{name} {value} is negative")
