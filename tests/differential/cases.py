"""Stable fixtures and directed cases for differential ledger testing."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from model import (
    MAX_U64,
    Account,
    Sodium,
    account_id,
    encode_genesis,
    signed_transfer,
)
from protocol_bytes import require

DEFAULT_RANDOM_SCENARIOS = 10_000
DEFAULT_SEED = 0x5053444946465631
SUPPLY_LIMIT = 1_000_000_000_000_000_000
TOTAL_SUPPLY = 100_000_000_000_000_000
FIXED_FEE = 1_000
DIRECTED_SCENARIOS = 11
MASK_U64 = (1 << 64) - 1


class SplitMix64:
    """Repository-specified deterministic generator for corpus stability."""

    def __init__(self, seed: int) -> None:
        self.state = seed & MASK_U64

    def next_u64(self) -> int:
        self.state = (self.state + 0x9E3779B97F4A7C15) & MASK_U64
        value = self.state
        value = (
            (value ^ (value >> 30)) * 0xBF58476D1CE4E5B9
        ) & MASK_U64
        value = (
            (value ^ (value >> 27)) * 0x94D049BB133111EB
        ) & MASK_U64
        return (value ^ (value >> 31)) & MASK_U64

    def below(self, upper: int) -> int:
        require(0 < upper <= 1 << 64, "invalid random bound")
        limit = (1 << 64) - ((1 << 64) % upper)
        while True:
            value = self.next_u64()
            if value < limit:
                return value % upper

    def bytes(self, size: int) -> bytes:
        require(size >= 0, "negative random byte count")
        encoded = bytearray()
        while len(encoded) < size:
            encoded.extend(self.next_u64().to_bytes(8, "big"))
        return bytes(encoded[:size])


def verify_prng() -> None:
    generator = SplitMix64(0)
    observed = tuple(generator.next_u64() for _ in range(3))
    expected = (
        0xE220A8397B1DCDAF,
        0x6E789E6AA1B965F4,
        0x06C45D188009454F,
    )
    require(observed == expected, "SplitMix64-v1 compatibility vector")


@dataclass(frozen=True)
class Fixture:
    genesis: bytes
    chain_id: bytes
    seeds: tuple[bytes, ...]
    identifiers: tuple[bytes, ...]
    seed_by_identifier: dict[bytes, bytes]


def make_fixture(sodium: Sodium) -> Fixture:
    seeds = tuple(
        hashlib.sha256(
            b"protocol-stack:v1:differential-key"
            + index.to_bytes(4, "big")
        ).digest()
        for index in range(12)
    )
    identifiers = tuple(
        account_id(sodium.keypair(seed)[0]) for seed in seeds
    )
    accounts = {
        identifier: Account(TOTAL_SUPPLY // 4, 0)
        for identifier in identifiers[:4]
    }
    genesis = encode_genesis(
        accounts, SUPPLY_LIMIT, TOTAL_SUPPLY, FIXED_FEE
    )
    chain_id = hashlib.sha256(
        bytes([len("protocol-stack:v1:chain-id")])
        + b"protocol-stack:v1:chain-id"
        + genesis
    ).digest()
    return Fixture(
        genesis,
        chain_id,
        seeds,
        identifiers,
        dict(zip(identifiers, seeds, strict=True)),
    )


def transfer(
    sodium: Sodium,
    fixture: Fixture,
    seed_index: int,
    nonce: int,
    recipient_index: int,
    amount: int,
    fee_limit: int = FIXED_FEE,
    valid_until: int = 100,
    chain_id: bytes | None = None,
) -> bytes:
    return signed_transfer(
        sodium,
        fixture.seeds[seed_index],
        fixture.chain_id if chain_id is None else chain_id,
        nonce,
        fixture.identifiers[recipient_index],
        amount,
        fee_limit,
        valid_until,
    )


def corrupt_signature(raw: bytes) -> bytes:
    changed = bytearray(raw)
    changed[-1] ^= 1
    return bytes(changed)


def directed_blocks(
    scenario: int, sodium: Sodium, fixture: Fixture
) -> list[list[bytes]]:
    valid = transfer(sodium, fixture, 0, 1, 1, 10_000)
    wrong_chain = hashlib.sha256(b"protocol-stack:wrong-chain").digest()
    wrong = transfer(
        sodium, fixture, 0, 1, 1, 10_000, chain_id=wrong_chain
    )
    invalid = corrupt_signature(valid)
    malformed = valid[:-1]

    if scenario == 0:
        return [[]]
    if scenario == 1:
        return [[malformed, wrong, invalid]]
    if scenario == 2:
        return [[
            transfer(sodium, fixture, 0, 99, 1, 0, valid_until=0),
            transfer(sodium, fixture, 0, 99, 1, 1, fee_limit=999),
            transfer(sodium, fixture, 0, 99, 1, 1, valid_until=0),
            transfer(sodium, fixture, 4, 1, 0, 1),
            transfer(sodium, fixture, 0, 2, 1, 1),
            transfer(sodium, fixture, 0, 1, 1, MAX_U64),
            transfer(
                sodium,
                fixture,
                0,
                1,
                1,
                TOTAL_SUPPLY // 4,
            ),
        ]]
    if scenario == 3:
        return [[transfer(sodium, fixture, 0, 1, 4, 50_000)]]
    if scenario == 4:
        return [[transfer(sodium, fixture, 0, 1, 0, 1)]]
    if scenario == 5:
        return [[valid, valid]]
    if scenario == 6:
        return [[
            valid,
            transfer(sodium, fixture, 0, 2, 0, 1),
        ]]
    if scenario == 7:
        return [[
            transfer(sodium, fixture, 0, 2, 0, 1),
            valid,
        ]]
    if scenario == 8:
        return [[
            malformed,
            valid,
            wrong,
            transfer(sodium, fixture, 1, 1, 0, 0),
            invalid,
        ]]
    if scenario == 9:
        return [[valid], [valid]]
    require(scenario == 10, "unknown directed scenario")
    return [[], [valid], []]
