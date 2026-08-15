"""Derivations, registry transitions, postures, the settlement, and channel 8."""

from __future__ import annotations

from pathlib import Path

import expected as e
from checker import Checker

from simulation.economy_transition_v6 import contract as c
from simulation.economy_transition_v6 import scenario, verified_user
from simulation.economy_transition_v6.identity import (
    Posture,
    Registry,
    RegistryError,
    escrow_id,
    relaxes,
    requires_confirmation,
    signer_id,
    slot_of,
    unchanged,
)


def check_derivations(check: Checker, accepted: Path) -> None:
    """The escrow derivation, and the signer derivation against a third source."""
    check.agree("escrow.label", e.ESCROW_LABEL, c.ESCROW_LABEL)
    identity = scenario.ALICE_IDENTITY
    other = scenario.BOB_IDENTITY

    for index in (0, 1, 2):
        check.agree(
            f"escrow.identity_a_index{index}_hex",
            e.escrow_id(identity, index).hex(),
            escrow_id(identity, index).hex(),
        )
    check.agree(
        "escrow.identity_b_index0_hex",
        e.escrow_id(other, 0).hex(),
        escrow_id(other, 0).hex(),
    )

    # Two indexes of one identity and one index of two identities all differ,
    # which is what makes the identifier a function of both terms.
    derived = {
        escrow_id(identity, 0),
        escrow_id(identity, 1),
        escrow_id(identity, 2),
        escrow_id(other, 0),
    }
    check.equal("escrow.four_derivations_are_distinct", len(derived) == 4)
    check.agree("escrow.identifier_bytes", 32, len(escrow_id(identity, 0)))

    # The signer derivation is the accepted version-one account derivation, so
    # it is checked against the identifier the accepted file already records
    # rather than against a second restatement of the same formula.
    primitives = _read(accepted / "protocol-primitives-v1.txt")
    check.equal(
        "signer.derivation_reproduces_the_accepted_account_identifier",
        signer_id(scenario.SENDER_PUBLIC_KEY).hex() == primitives["account_id"],
    )
    check.agree(
        "signer.derivation_label_is_the_version_one_account_label",
        e.ACCOUNT_LABEL,
        c.ACCOUNT_LABEL,
    )
    check.agree(
        "signer.identity_a_signer_hex",
        e.signer_id(scenario.ALICE_SIGNER_KEY).hex(),
        signer_id(scenario.ALICE_SIGNER_KEY).hex(),
    )


def check_registry(check: Checker) -> None:
    """The fixture's registry, and the transitions that produced it."""
    built = scenario.registry()
    check.agree("registry.identity_count", 3, len(built.identities))
    check.agree("registry.escrow_count", 4, len(built.escrows))
    check.agree("registry.signer_count", 4, len(built.signers))
    check.agree("registry.enrollment_count", 3, len(built.enrollments))
    check.agree("registry.enrolled_count", 3, built.enrolled_count)

    alice = built.identities[scenario.ALICE_IDENTITY]
    check.agree("registry.alice_next_escrow_index", 3, alice.next_escrow_index)
    check.agree("registry.alice_live_escrow_count", 2, alice.escrow_count)
    check.agree("registry.alice_seat_count", 1, alice.seat_count)

    # A deleted escrow's index is never reissued: the next index stays past it
    # while the live count falls, which is why the two fields are separate.
    check.equal(
        "registry.a_deleted_index_is_never_reissued",
        alice.next_escrow_index > alice.escrow_count
        and scenario.ALICE_THIRD_ESCROW not in built.escrows,
    )
    check.equal(
        "registry.an_escrow_may_hold_no_signer",
        built.escrows[scenario.ALICE_SECOND_ESCROW].signer_count == 0,
    )

    # Recovery: Maria holds no original signer and her escrow still resolves
    # through the one her identity assigned.
    maria = built.escrows[scenario.MARIA_ESCROW]
    check.agree("registry.maria_signer_count", 1, maria.signer_count)
    check.equal(
        "registry.the_lost_signer_no_longer_resolves",
        signer_id(scenario.MARIA_LOST_SIGNER_KEY) not in built.signers,
    )
    check.equal(
        "registry.the_new_signer_resolves_to_marias_escrow",
        built.escrow_of_signer(scenario.MARIA_NEW_SIGNER_KEY) == scenario.MARIA_ESCROW,
    )

    check.agree("registry.structural_failure_count", 0, len(built.structural_failures()))
    check.equal(
        "registry.every_account_is_an_escrow",
        set(built.accounts) == set(built.escrows),
    )

    # Fail-closed, in the directions that matter.
    check.equal(
        "registry.refuses_a_second_registration_of_one_identity",
        _refused(
            built.register,
            scenario.ALICE_IDENTITY,
            scenario.ALICE_KEY,
            bytes.fromhex("ee" * 32),
            1,
        ),
    )
    check.equal(
        "registry.refuses_a_signer_key_already_assigned",
        _refused(built.add_signer, scenario.BOB_ESCROW, scenario.ALICE_SIGNER_KEY),
    )
    check.equal(
        "registry.refuses_an_unknown_signer_key",
        _refused(built.escrow_of_signer, bytes.fromhex("fe" * 32)),
    )
    check.equal(
        "registry.refuses_an_escrow_owned_by_another_identity",
        _refused(built.require_owned, scenario.BOB_ESCROW, scenario.ALICE_IDENTITY),
    )
    check.equal(
        "registry.refuses_a_header_key_that_is_not_the_recorded_key",
        _refused(
            built.require_identity, scenario.ALICE_IDENTITY, bytes.fromhex("00" * 32)
        ),
    )
    check.equal(
        "registry.refuses_deleting_an_escrow_that_holds_value",
        _refused_delete(built),
    )

    limit = Registry()
    limit.register(
        scenario.ALICE_IDENTITY, scenario.ALICE_KEY, scenario.ALICE_SIGNER_KEY, 1
    )
    target = escrow_id(scenario.ALICE_IDENTITY, 0)
    for index in range(c.MAX_SIGNERS_PER_ESCROW - 1):
        limit.add_signer(target, bytes([index + 1]) * 32)
    check.agree(
        "registry.signer_bound", e.MAX_SIGNERS_PER_ESCROW, c.MAX_SIGNERS_PER_ESCROW
    )
    check.equal(
        "registry.refuses_a_seventeenth_signer",
        _refused(limit.add_signer, target, bytes([0xF1]) * 32),
    )


def _refused(operation, *arguments) -> bool:
    try:
        operation(*arguments)
    except (RegistryError, KeyError):
        return True
    return False


def _refused_delete(built: Registry) -> bool:
    funded = Registry()
    funded.register(
        scenario.BOB_IDENTITY, scenario.BOB_KEY, scenario.BOB_SIGNER_KEY, 1
    )
    escrow = escrow_id(scenario.BOB_IDENTITY, 0)
    funded.accounts[escrow] = (1, 0)
    return _refused(funded.delete_escrow, scenario.BOB_IDENTITY, escrow)


def check_posture(check: Checker) -> None:
    """Both predicates, each disjunct alone and in combination."""
    strict = Posture()
    check.agree("posture.default_requires_confirmation", True, strict.requires_confirmation)
    check.agree("posture.default_min_amount_atomic", 0, strict.min_amount_atomic)
    check.agree("posture.default_exempt_slot_mask", 0, strict.exempt_slot_mask)
    check.agree("posture.slots_per_window", e.SLOTS_PER_WINDOW, c.SLOTS_PER_WINDOW)
    check.agree("posture.slot_blocks", e.SLOT_BLOCKS, c.SLOT_BLOCKS)
    check.agree("posture.max_exempt_slot_mask", (1 << 24) - 1, c.MAX_EXEMPT_SLOT_MASK)

    # A slot is derived from a height and the accepted grid, never from a clock.
    for height in (0, c.SLOT_BLOCKS, c.SLOT_BLOCKS * 23, c.CYCLE_BLOCKS - 1):
        check.agree(f"posture.slot_of_height_{height}", e.slot_of(height), slot_of(height))
    check.agree("posture.slot_of_a_window_boundary", 0, slot_of(c.CYCLE_BLOCKS))

    # Each case is phrased so its name asserts what its value establishes, and
    # a case whose answer is "no confirmation" records the negation positively.
    # A boolean vector may only be true, so `requires` and `does_not_require`
    # are separate names rather than one name with two values.
    requiring = {
        "strict_requires_at_zero": (strict, 0, 0),
        "strict_requires_at_a_large_amount": (strict, 10**12, 0),
        "at_the_minimum_requires": (Posture(min_amount_atomic=100_000_000), 100_000_000, 0),
        "a_non_exempt_slot_requires": (Posture(exempt_slot_mask=0b1), 1, c.SLOT_BLOCKS),
    }
    exempting = {
        "off_never_requires": (Posture(requires_confirmation=False), 10**12, 0),
        "below_the_minimum_does_not_require": (
            Posture(min_amount_atomic=100_000_000),
            99_999_999,
            0,
        ),
        "an_exempt_slot_does_not_require": (Posture(exempt_slot_mask=0b1), 1, 0),
    }
    for name, (posture, amount, height) in requiring.items():
        check.agree(
            f"posture.confirmation.{name}",
            e.requires_confirmation(*_tuple(posture), amount, height),
            requires_confirmation(posture, amount, height),
        )
    for name, (posture, amount, height) in exempting.items():
        check.agree(
            f"posture.confirmation.{name}",
            not e.requires_confirmation(*_tuple(posture), amount, height),
            not requires_confirmation(posture, amount, height),
        )

    relaxations = {
        "turning_confirmation_off": Posture(requires_confirmation=False),
        "raising_the_minimum": Posture(min_amount_atomic=1),
        "setting_an_exempt_slot": Posture(exempt_slot_mask=0b1),
        "a_mixed_change_that_weakens_anything": Posture(
            requires_confirmation=True, min_amount_atomic=1, exempt_slot_mask=0
        ),
    }
    for name, proposed in relaxations.items():
        check.agree(
            f"posture.relaxes.{name}",
            e.relaxes(_tuple(strict), _tuple(proposed)),
            relaxes(strict, proposed),
        )
        check.equal(f"posture.{name}_relaxes", relaxes(strict, proposed))

    loose = Posture(
        requires_confirmation=False, min_amount_atomic=10, exempt_slot_mask=0b11
    )
    tightenings = {
        "turning_confirmation_on": Posture(
            requires_confirmation=True, min_amount_atomic=10, exempt_slot_mask=0b11
        ),
        "lowering_the_minimum": Posture(
            requires_confirmation=False, min_amount_atomic=9, exempt_slot_mask=0b11
        ),
        "clearing_an_exempt_slot": Posture(
            requires_confirmation=False, min_amount_atomic=10, exempt_slot_mask=0b1
        ),
    }
    for name, proposed in tightenings.items():
        check.agree(
            f"posture.tightens.{name}",
            not e.relaxes(_tuple(loose), _tuple(proposed)),
            not relaxes(loose, proposed),
        )
        check.equal(f"posture.{name}_tightens", not relaxes(loose, proposed))

    check.equal("posture.an_equal_posture_is_unchanged", unchanged(strict, Posture()))
    check.equal(
        "posture.an_unchanged_posture_is_refused",
        _refused(scenario.registry().set_posture, scenario.ALICE_FIRST_ESCROW, Posture()),
    )


def _tuple(posture: Posture) -> tuple[bool, int, int]:
    return (
        posture.requires_confirmation,
        posture.min_amount_atomic,
        posture.exempt_slot_mask,
    )


def check_verified_user(check: Checker) -> None:
    """The derived rate, the entry airdrop, a full period, and forfeiture."""
    check.agree(
        "verified_user.channel_id", e.VERIFIED_USER_CHANNEL, c.VERIFIED_USER_CHANNEL
    )
    check.agree(
        "verified_user.population", e.VERIFIED_USER_POPULATION, c.VERIFIED_USER_POPULATION
    )
    check.agree("verified_user.cycles", e.VERIFIED_USER_CYCLES, c.VERIFIED_USER_CYCLES)
    check.agree(
        "verified_user.channel_cap_atomic",
        e.VERIFIED_USER_CHANNEL_CAP_ATOMIC,
        c.VERIFIED_USER_CHANNEL_CAP,
    )
    check.agree(
        "verified_user.daily_atomic",
        e.verified_user_daily_atomic(),
        verified_user.derived_daily_atomic(),
    )
    check.agree(
        "verified_user.daily_display",
        e.verified_user_daily_atomic() / e.ATOMIC_PER_DISPLAY,
        c.VERIFIED_USER_DAILY_ATOMIC / e.ATOMIC_PER_DISPLAY,
    )
    check.equal(
        "verified_user.the_rate_reproduces_the_accepted_cap",
        e.VERIFIED_USER_POPULATION
        * e.VERIFIED_USER_CYCLES
        * e.verified_user_daily_atomic()
        == c.VERIFIED_USER_CHANNEL_CAP,
    )
    # 730 cycles leaves a remainder and 731 leaves none, which is what fixes the
    # period rather than making it a choice.
    check.agree(
        "verified_user.channel_cap_remainder_at_730_cycles",
        e.verified_user_remainder_at(730),
        c.VERIFIED_USER_CHANNEL_CAP % (c.VERIFIED_USER_POPULATION * 730),
    )
    check.equal(
        "verified_user.a_730_cycle_period_leaves_a_remainder",
        e.verified_user_remainder_at(730) > 0,
    )
    check.equal(
        "verified_user.a_731_cycle_period_leaves_none",
        e.verified_user_remainder_at(731) == 0,
    )
    check.agree(
        "verified_user.maximum_per_identity_atomic",
        e.VERIFIED_USER_CYCLES * e.verified_user_daily_atomic(),
        verified_user.maximum_issuance_per_identity(),
    )

    height = 5 * c.CYCLE_BLOCKS
    enrollment = verified_user.enroll(height)
    check.agree("verified_user.airdrop_atomic", 171_000_000, enrollment.issued_atomic)
    check.agree("verified_user.enrolled_window", 5, enrollment.minted_through_window)
    check.agree("verified_user.last_window", 5 + 730, verified_user.last_window(enrollment))

    cases = {
        "the_day_after_enrollment": 6,
        "at_the_cap": 5 + 31,
        "one_window_past_the_cap": 5 + 32,
        "ten_windows_past_the_cap": 5 + 41,
        "long_past_the_period": 5 + 800,
    }
    for name, window in cases.items():
        at = window * c.CYCLE_BLOCKS
        collection = verified_user.collect(enrollment, at)
        start, end, count = e.verified_user_collection(
            enrollment.minted_through_window, 5, at
        )
        check.agree(f"verified_user.{name}.window_start", start, collection.window_start)
        check.agree(f"verified_user.{name}.collectable_end", end, collection.collectable_end)
        check.agree(f"verified_user.{name}.count", count, collection.count)
        check.agree(
            f"verified_user.{name}.amount_atomic",
            count * e.verified_user_daily_atomic(),
            collection.amount_atomic,
        )

    # Forfeiture is what the cap does here, and the mark advancing past the
    # forfeited windows is what makes it permanent rather than deferred.
    neglected = verified_user.collect(enrollment, (5 + 41) * c.CYCLE_BLOCKS)
    check.agree("verified_user.forfeited_windows_after_forty", 10, neglected.forfeited_windows)
    check.equal(
        "verified_user.a_forfeiting_mint_collects_exactly_the_cap",
        neglected.count == c.MINT_ACCUMULATION_CAP,
    )
    applied = verified_user.applied(enrollment, neglected)
    check.equal(
        "verified_user.the_mark_advances_past_the_forfeited_windows",
        applied.minted_through_window == neglected.collectable_end,
    )
    second = verified_user.collect(applied, (5 + 41) * c.CYCLE_BLOCKS)
    check.equal(
        "verified_user.the_forfeited_windows_are_not_collectable_later",
        second.count == 0,
    )

    # A person who never neglects collects the whole period and no more.
    walking = verified_user.enroll(height)
    for window in range(6, 5 + 731 + 1):
        collection = verified_user.collect(walking, window * c.CYCLE_BLOCKS)
        walking = verified_user.applied(walking, collection)
    check.agree(
        "verified_user.a_complete_period_issues_the_full_allocation",
        e.VERIFIED_USER_CYCLES * e.verified_user_daily_atomic(),
        walking.issued_atomic,
    )
    beyond = verified_user.collect(walking, (5 + 900) * c.CYCLE_BLOCKS)
    check.agree("verified_user.nothing_is_collectable_after_the_period", 0, beyond.count)

    # The channel has no accrual step, so it has no outstanding term at all:
    # value is issued when collected and is otherwise never represented. The
    # claim is checked against the entry set rather than against a constant.
    entries = scenario.registry().entries()
    accrual_entries = [key for key in entries if key[0] == c.REFERRAL_BALANCE_ENTRY]
    check.agree(
        "verified_user.the_channel_writes_no_accrual_entry", 0, len(accrual_entries)
    )
    check.equal(
        "verified_user.an_enrollment_records_only_what_was_issued",
        all(
            enrollment.issued_atomic
            <= verified_user.maximum_issuance_per_identity()
            for enrollment in scenario.registry().enrollments.values()
        ),
    )
    check.equal(
        "verified_user.issuance_stays_within_the_cap",
        e.VERIFIED_USER_POPULATION * walking.issued_atomic
        <= c.VERIFIED_USER_CHANNEL_CAP,
    )
    check.equal(
        "verified_user.channel_eight_left_the_reserved_direct_issue_set",
        e.VERIFIED_USER_CHANNEL not in c.DIRECT_ISSUE_CHANNELS,
    )
    check.agree(
        "verified_user.reserved_direct_issue_channels",
        ",".join(str(channel) for channel in e.DIRECT_ISSUE_CHANNELS),
        ",".join(str(channel) for channel in c.DIRECT_ISSUE_CHANNELS),
    )


def check_settlement_is_version_three(check: Checker, accepted: Path) -> None:
    """The imported settlement must reproduce version three's recorded record.

    The settlement did not move, so a copy would be a second implementation of
    one accepted contract with nothing keeping the two equal. The equality
    against the accepted file is what keeps the import honest.
    """
    recorded = _read(accepted / "economy-transition-v3.txt")
    records = scenario.assignment_records()
    check.agree("settlement.assignment_cap_windows", e.MINT_ACCUMULATION_CAP, c.MINT_ACCUMULATION_CAP)
    check.agree("settlement.assignment_lag_windows", e.ASSIGNMENT_LAG_WINDOWS, c.ASSIGNMENT_LAG_WINDOWS)

    # The lookup is total. A missing key is a failure rather than a fallback,
    # because a check that can quietly not run establishes nothing.
    for label, window in (
        ("cycle", scenario.CYCLE_WINDOW),
        ("outage", scenario.OUTAGE_WINDOW),
    ):
        key = f"{label}.assignment_value_hex"
        if key not in recorded:
            check.failures.append(
                f"settlement.{label}: economy-transition-v3.txt records no {key}"
            )
            continue
        check.equal(
            f"settlement.the_{label}_record_is_byte_identical_to_version_three",
            records[window].hex() == recorded[key],
        )

    # The walk is half-open on the mark and closed at the cap, unchanged from
    # version three: `(mark, min(last_assigned, mark + 30)]`.
    mark = scenario.CURRENT_MARK
    check.equal(
        "settlement.a_window_within_the_cap_accrues",
        e.accrues(mark + c.MINT_ACCUMULATION_CAP, mark),
    )
    check.equal(
        "settlement.a_window_beyond_the_cap_does_not_accrue",
        not e.accrues(mark + c.MINT_ACCUMULATION_CAP + 1, mark),
    )
    low, high = e.walk_range(mark, mark + 100)
    check.agree("settlement.walk_first_window", low, mark + 1)
    check.agree("settlement.walk_last_window", high, mark + c.MINT_ACCUMULATION_CAP)
    check.equal(
        "settlement.a_mark_at_the_last_assigned_window_walks_nothing",
        e.walk_range(mark, mark) is None,
    )


def _read(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        values[key] = value
    return values
