from __future__ import annotations

import hashlib
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="ascii").splitlines():
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        require(bool(separator) and key not in values, "malformed vector file")
        values[key] = value
    return values


def domain(label: str) -> bytes:
    encoded = label.encode("ascii")
    require(len(encoded) < 256, "domain label too long")
    return bytes([len(encoded)]) + encoded


def digest(label: str, payload: bytes = b"") -> bytes:
    return hashlib.sha256(domain(label) + payload).digest()


def merkle(items: list[bytes], prefix: str) -> bytes:
    base = f"protocol-stack:v1:{prefix}"
    if not items:
        return digest(f"{base}-empty")
    if len(items) == 1:
        return digest(f"{base}-leaf", items[0])
    split = 1 << ((len(items) - 1).bit_length() - 1)
    if split == len(items):
        split //= 2
    return digest(
        f"{base}-node",
        merkle(items[:split], prefix) + merkle(items[split:], prefix),
    )


def convert_bits(data: bytes) -> list[int]:
    accumulator = 0
    bit_count = 0
    result: list[int] = []
    for value in data:
        accumulator = (accumulator << 8) | value
        bit_count += 8
        while bit_count >= 5:
            bit_count -= 5
            result.append((accumulator >> bit_count) & 31)
    if bit_count:
        result.append((accumulator << (5 - bit_count)) & 31)
    return result


def polymod(values: list[int]) -> int:
    generators = (0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3)
    checksum = 1
    for value in values:
        top = checksum >> 25
        checksum = ((checksum & 0x1FFFFFF) << 5) ^ value
        for index, generator in enumerate(generators):
            if (top >> index) & 1:
                checksum ^= generator
    return checksum


def hrp_expand(hrp: str) -> list[int]:
    return [ord(value) >> 5 for value in hrp] + [0] + [
        ord(value) & 31 for value in hrp
    ]


def bech32m(hrp: str, payload: bytes) -> str:
    charset = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
    data = convert_bits(payload)
    checksum = polymod(hrp_expand(hrp) + data + [0] * 6) ^ 0x2BC830A3
    check_values = [(checksum >> (5 * (5 - index))) & 31 for index in range(6)]
    return hrp + "1" + "".join(charset[value] for value in data + check_values)


def decode_address(address: str, expected_hrp: str) -> bytes:
    charset = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
    require(address == address.lower() and len(address) <= 90, "address case")
    separator = address.rfind("1")
    require(separator == len(expected_hrp), "address HRP")
    require(address[:separator] == expected_hrp, "address network")
    try:
        data = [charset.index(value) for value in address[separator + 1 :]]
    except ValueError as error:
        raise ValueError("address alphabet") from error
    require(len(data) >= 6, "short address")
    require(
        polymod(hrp_expand(expected_hrp) + data) == 0x2BC830A3,
        "address checksum",
    )
    accumulator = 0
    bit_count = 0
    payload = bytearray()
    for value in data[:-6]:
        accumulator = (accumulator << 5) | value
        bit_count += 5
        if bit_count >= 8:
            bit_count -= 8
            payload.append((accumulator >> bit_count) & 255)
    require(
        bit_count < 5 and ((accumulator << (8 - bit_count)) & 255) == 0,
        "address padding",
    )
    require(len(payload) == 33 and payload[0] == 1, "address payload")
    return bytes(payload)


def transfer(values: dict[str, str]) -> bytes:
    result = (
        b"PSTX"
        + (1).to_bytes(2, "big")
        + b"\x01"
        + bytes.fromhex(values["chain_id"])
        + b"\x01"
        + bytes.fromhex(values["rfc8032.public_key"])
        + int(values["tx.nonce"]).to_bytes(8, "big")
        + bytes.fromhex(values["tx.recipient"])
        + int(values["tx.amount"]).to_bytes(8, "big")
        + int(values["tx.fee_limit"]).to_bytes(8, "big")
        + int(values["tx.valid_until"]).to_bytes(8, "big")
    )
    require(len(result) == 136, "wrong unsigned transaction size")
    return result


def valid_signed_transaction_shape(transaction: bytes) -> bool:
    return (
        len(transaction) == 200
        and transaction[:4] == b"PSTX"
        and transaction[4:7] == b"\x00\x01\x01"
        and transaction[39] == 1
    )


def state_root(
    chain_id: bytes,
    entries: list[bytes],
    height: int,
    supply_limit: int,
    total_supply: int,
    fee_pool: int,
) -> bytes:
    require(total_supply <= supply_limit, "supply exceeds limit")
    require(all(len(entry) == 48 for entry in entries), "account entry size")
    identifiers = [entry[:32] for entry in entries]
    require(identifiers == sorted(set(identifiers)), "account order")
    require(
        sum(int.from_bytes(entry[32:40], "big") for entry in entries)
        + fee_pool
        == total_supply,
        "supply conservation",
    )
    payload = (
        (1).to_bytes(2, "big")
        + chain_id
        + height.to_bytes(8, "big")
        + supply_limit.to_bytes(8, "big")
        + total_supply.to_bytes(8, "big")
        + fee_pool.to_bytes(8, "big")
        + len(entries).to_bytes(8, "big")
        + merkle(entries, "state")
    )
    return digest("protocol-stack:v1:state-root", payload)
