"""Seeded random sequence generation for differential ledger testing."""

from __future__ import annotations

import hashlib

from cases import Fixture, SplitMix64, corrupt_signature
from model import (
    MAX_U64,
    Account,
    ReferenceLedger,
    Sodium,
    State,
    account_id,
    admit,
    execute,
    signed_transfer,
)
from protocol_bytes import require


def choose_sender(
    rng: SplitMix64, state: State, fixture: Fixture, funded: bool
) -> tuple[bytes, bytes, Account]:
    candidates = [
        (identifier, fixture.seed_by_identifier[identifier], account)
        for identifier, account in state.accounts.items()
        if identifier in fixture.seed_by_identifier
        and (not funded or account.balance > state.fixed_fee)
    ]
    require(bool(candidates), "no generated sender candidate")
    return candidates[rng.below(len(candidates))]


def absent_seed(
    rng: SplitMix64,
    state: State,
    fixture: Fixture,
    sodium: Sodium,
) -> bytes:
    candidates = [
        fixture.seed_by_identifier[identifier]
        for identifier in fixture.identifiers
        if identifier not in state.accounts
    ]
    if candidates:
        return candidates[rng.below(len(candidates))]
    seed = hashlib.sha256(
        b"protocol-stack:v1:differential-absent"
        + rng.bytes(32)
    ).digest()
    require(
        account_id(sodium.keypair(seed)[0]) not in state.accounts,
        "derived absent sender collision",
    )
    return seed


def make_random_raw(
    rng: SplitMix64,
    scenario: int,
    input_index: int,
    height: int,
    planning: State,
    sodium: Sodium,
    fixture: Fixture,
    replay_pool: list[bytes],
) -> bytes:
    category = rng.below(15)
    sender_id, seed, sender = choose_sender(
        rng, planning, fixture, funded=category in {0, 1, 2, 13}
    )
    nonce = sender.nonce + 1
    recipient = fixture.identifiers[rng.below(len(fixture.identifiers))]
    maximum_amount = (
        sender.balance - planning.fixed_fee
        if category in {0, 1, 2, 13}
        else sender.balance
    )
    amount = max(1, min(1 + rng.below(1_000_000), maximum_amount))
    fee_limit = planning.fixed_fee
    valid_until = height + rng.below(6)
    chain_id = planning.chain_id

    if category == 1:
        recipient = sender_id
        amount = 1
    elif category == 2:
        missing = [
            identifier
            for identifier in fixture.identifiers
            if identifier not in planning.accounts
        ]
        if missing:
            recipient = missing[rng.below(len(missing))]
    elif category == 3:
        amount = 0
    elif category == 4:
        fee_limit = planning.fixed_fee - 1
    elif category == 5:
        valid_until = height - 1
    elif category == 6:
        seed = absent_seed(rng, planning, fixture, sodium)
        nonce = 1
    elif category == 7:
        nonce += 1
    elif category == 8:
        amount = MAX_U64
    elif category == 9:
        amount = sender.balance
    elif category == 11:
        chain_id = hashlib.sha256(
            scenario.to_bytes(8, "big")
            + input_index.to_bytes(8, "big")
            + b"wrong-chain"
        ).digest()
    elif category == 14 and replay_pool:
        return replay_pool[rng.below(len(replay_pool))]

    raw = signed_transfer(
        sodium,
        seed,
        chain_id,
        nonce,
        recipient,
        amount,
        fee_limit,
        valid_until,
    )
    if category == 10:
        mutation = rng.below(5)
        if mutation == 0:
            return raw[:-1]
        if mutation == 1:
            return raw + b"\x00"
        changed = bytearray(raw)
        if mutation == 2:
            changed[0] ^= 1
        elif mutation == 3:
            changed[6] = 2
        else:
            changed[39] = 2
        return bytes(changed)
    if category == 12:
        return corrupt_signature(raw)
    return raw


def random_blocks(
    rng: SplitMix64,
    scenario: int,
    count: int,
    ledger: ReferenceLedger,
    sodium: Sodium,
    fixture: Fixture,
) -> list[list[bytes]]:
    blocks: list[list[bytes]] = []
    replay_pool: list[bytes] = []
    has_raw_input = False
    for block_index in range(count):
        height = ledger.state.height + 1
        planning = ledger.state.clone()
        raws: list[bytes] = []
        raw_count = rng.below(7)
        if block_index + 1 == count and not has_raw_input and raw_count == 0:
            raw_count = 1
        for input_index in range(raw_count):
            raw = make_random_raw(
                rng,
                scenario,
                input_index,
                height,
                planning,
                sodium,
                fixture,
                replay_pool,
            )
            raws.append(raw)
            admission, transaction = admit(
                sodium, raw, planning.chain_id
            )
            if admission == 0 and transaction is not None:
                execution = execute(transaction, planning, height)
                if execution.result == 0:
                    replay_pool.append(raw)
        has_raw_input |= bool(raws)
        planning.height = height
        ledger.state = planning
        blocks.append(raws)
    require(has_raw_input, "randomized sequence has no raw input")
    return blocks


def scenario_rng(seed: int, scenario: int) -> SplitMix64:
    derived = hashlib.sha256(
        seed.to_bytes(32, "big", signed=False)
        + scenario.to_bytes(8, "big")
    ).digest()
    return SplitMix64(int.from_bytes(derived[:8], "big"))
