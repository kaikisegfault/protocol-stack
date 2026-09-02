"""The two new entries, their widths, their refusals, and the kind spaces."""

from __future__ import annotations

import expected as x
from checker import Checker

from simulation.economy_transition_v7 import contract as v7
from simulation.economy_transition_v8 import contract as c
from simulation.economy_transition_v8 import envelope as e
from simulation.economy_transition_v8 import state as st


def _refusal(call, *arguments) -> str:
    try:
        call(*arguments)
    except Exception as error:  # noqa: BLE001 - the refusal is the subject
        return type(error).__name__
    return "ACCEPTED"


def check_entry_space(check: Checker) -> None:
    check.section("The two entry kinds version eight adds.")
    check.agree("state.open_challenge.kind", x.OPEN_CHALLENGE_ENTRY, c.OPEN_CHALLENGE_ENTRY)
    check.agree("state.seat_window.kind", x.SEAT_WINDOW_ENTRY, c.SEAT_WINDOW_ENTRY)
    check.agree(
        "state.open_challenge.key_bytes",
        x.OPEN_CHALLENGE_KEY_BYTES,
        c.ENTRY_KEY_BYTES[c.OPEN_CHALLENGE_ENTRY],
    )
    check.agree(
        "state.open_challenge.value_bytes",
        x.OPEN_CHALLENGE_VALUE_BYTES,
        c.ENTRY_VALUE_BYTES[c.OPEN_CHALLENGE_ENTRY],
    )
    check.agree(
        "state.seat_window.key_bytes",
        x.SEAT_WINDOW_KEY_BYTES,
        c.ENTRY_KEY_BYTES[c.SEAT_WINDOW_ENTRY],
    )
    check.agree(
        "state.seat_window.value_bytes",
        x.SEAT_WINDOW_VALUE_BYTES,
        c.ENTRY_VALUE_BYTES[c.SEAT_WINDOW_ENTRY],
    )
    check.agree(
        "state.open_challenge.key",
        x.open_challenge_key(29_000, 7),
        st.open_challenge_key(29_000, 7),
    )
    check.agree(
        "state.seat_window.key", x.seat_window_key(1, 7), st.seat_window_key(1, 7)
    )
    check.equal(
        "state.neither_kind_was_ever_assigned",
        all(
            kind not in v7.ENTRY_KINDS and kind not in v7.RETIRED_ENTRY_KINDS
            for kind in (c.OPEN_CHALLENGE_ENTRY, c.SEAT_WINDOW_ENTRY)
        ),
    )
    check.equal(
        "state.no_retired_entry_kind_is_reused",
        not set(c.RETIRED_ENTRY_KINDS) & set(c.ENTRY_KINDS),
    )


def check_entry_refusals(check: Checker) -> None:
    check.section("What a decoder refuses, each produced by a live refusal.")
    check.equal(
        "state.open_challenge.refuses_state_two",
        _refusal(st.decode_open_challenge_value, bytes([2])) == "InvalidStateEntry",
    )
    check.equal(
        "state.open_challenge.accepts_zero_and_one",
        [st.decode_open_challenge_value(bytes([n])) for n in (0, 1)] == [0, 1],
    )
    check.equal(
        "state.seat_window.refuses_a_credited_pad_bit",
        _refusal(st.seat_window_value, 1 << c.SLOTS_PER_WINDOW, 0)
        == "InvalidStateEntry",
    )
    check.equal(
        "state.seat_window.refuses_a_disputed_pad_bit",
        _refusal(st.seat_window_value, x.all_slots_credited(), 1 << c.SLOTS_PER_WINDOW)
        == "InvalidStateEntry",
    )
    check.equal(
        "state.seat_window.refuses_a_dispute_of_an_uncredited_slot",
        _refusal(st.seat_window_value, 0b1110, 0b0001) == "InvalidStateEntry",
    )
    check.equal(
        "state.seat_window.refuses_a_short_value",
        _refusal(st.decode_seat_window_value, bytes(7)) == "InvalidStateEntry",
    )
    check.equal(
        "state.entry_shape.refuses_a_wrong_width_key",
        _refusal(
            st.require_entry_shape,
            bytes([c.OPEN_CHALLENGE_ENTRY]) + bytes(11),
            bytes([0]),
        )
        == "InvalidStateEntry",
    )
    check.equal(
        "state.entry_shape.refuses_a_retired_kind",
        _refusal(st.require_entry_shape, bytes([7]) + bytes(8), bytes(8))
        == "InvalidStateEntry",
    )
    check.equal(
        "state.entry_shape.checks_the_open_challenge_value",
        _refusal(
            st.require_entry_shape, st.open_challenge_key(1, 1), bytes([2])
        )
        == "InvalidStateEntry",
    )


def check_absent_record(check: Checker) -> None:
    check.section("An absent record reads as a fully credited seat.")
    credited = st.all_slots_credited()
    check.agree("state.seat_window.absent_reads_credited", x.all_slots_credited(), credited)
    check.agree(
        "state.seat_window.absent_uptime_seconds",
        x.uptime_seconds(x.all_slots_credited(), 0),
        st.credited_slots(credited, 0) * c.SLOT_SECONDS,
    )
    check.equal(
        "state.seat_window.absent_is_a_full_window",
        st.credited_slots(credited, 0) == c.SLOTS_PER_WINDOW,
    )
    check.agree(
        "state.seat_window.value_of_a_full_record",
        x.seat_window_value(x.all_slots_credited(), 0),
        st.seat_window_value(credited, 0),
    )


def check_kind_space(check: Checker) -> None:
    check.section("The two transaction kinds, their bodies, and their scheme.")
    check.agree("kind.challenge_response", x.CHALLENGE_RESPONSE, c.CHALLENGE_RESPONSE)
    check.agree("kind.file_dispute", x.FILE_DISPUTE, c.FILE_DISPUTE)
    check.agree(
        "kind.challenge_response.body_bytes",
        x.CHALLENGE_RESPONSE_BODY_BYTES,
        c.BODY_BYTES[c.CHALLENGE_RESPONSE],
    )
    check.agree(
        "kind.file_dispute.body_bytes",
        x.FILE_DISPUTE_BODY_BYTES,
        c.BODY_BYTES[c.FILE_DISPUTE],
    )
    check.agree(
        "kind.challenge_response.signed_bytes",
        x.HEADER_BYTES + x.CHALLENGE_RESPONSE_BODY_BYTES + x.TRAILER_BYTES + x.SIGNATURE_BYTES,
        e.expected_signed_length(c.CHALLENGE_RESPONSE),
    )
    check.agree(
        "kind.file_dispute.signed_bytes",
        x.HEADER_BYTES + x.FILE_DISPUTE_BODY_BYTES + x.TRAILER_BYTES + x.SIGNATURE_BYTES,
        e.expected_signed_length(c.FILE_DISPUTE),
    )
    check.equal(
        "kind.both_are_scheme_one",
        {c.KIND_SCHEME[c.CHALLENGE_RESPONSE], c.KIND_SCHEME[c.FILE_DISPUTE]}
        == {c.SCHEME_SIGNER},
    )
    check.equal(
        "kind.neither_number_was_ever_assigned",
        all(
            kind not in v7.TRANSACTION_KINDS and kind not in v7.RETIRED_KINDS
            for kind in (c.CHALLENGE_RESPONSE, c.FILE_DISPUTE)
        ),
    )
    check.equal(
        "kind.version_seven_kinds_keep_their_bodies",
        all(c.BODY_BYTES[kind] == v7.BODY_BYTES[kind] for kind in v7.TRANSACTION_KINDS),
    )


def check_result_codes(check: Checker) -> None:
    check.section("Twelve codes added; the space stays contiguous from zero.")
    check.agree("result.code_count", x.RESULT_CODE_COUNT, len(c.RESULT_CODES))
    check.equal(
        "result.space_is_contiguous",
        sorted(c.RESULT_CODES) == list(range(len(c.RESULT_CODES))),
    )
    for number in sorted(x.ADDED_RESULT_CODES):
        check.agree(
            f"result.added.{number}", x.ADDED_RESULT_CODES[number], c.RESULT_CODES[number]
        )
    check.equal(
        "result.version_seven_codes_keep_their_numbers",
        all(c.RESULT_CODES[number] == name for number, name in v7.RESULT_CODES.items()),
    )
    check.equal("result.no_name_is_reused", len(c.CODE_NUMBER) == len(c.RESULT_CODES))
    check.equal(
        "result.frozen_unreachable_codes_are_inherited",
        c.UNREACHABLE_RESULT_CODES == v7.UNREACHABLE_RESULT_CODES,
    )
    check.section("Model codes version eight deliberately does not encode.")
    for name in sorted(c.ABSENT_MODEL_CODES):
        check.equal(f"result.absent.{name.lower()}_is_not_encoded", name not in c.CODE_NUMBER)
