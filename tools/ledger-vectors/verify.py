#!/usr/bin/env python3

from __future__ import annotations

import ctypes
import ctypes.util
import hashlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path

MAX_U64 = (1 << 64) - 1
SUPPLY_LIMIT = 1_000_000_000_000_000_000
FIXED_FEE = 1_000
BLOCK_HEIGHT = 1


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


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


class Sodium:
    def __init__(self) -> None:
        library_name = os.environ.get(
            "PROTOCOL_STACK_LIBSODIUM"
        ) or ctypes.util.find_library("sodium")
        require(library_name is not None, "libsodium runtime not found")
        self.library = ctypes.CDLL(library_name)
        self.library.sodium_init.restype = ctypes.c_int
        require(self.library.sodium_init() >= 0, "libsodium init failed")
        self.library.crypto_sign_seed_keypair.argtypes = (
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
        )
        self.library.crypto_sign_seed_keypair.restype = ctypes.c_int
        self.library.crypto_sign_detached.argtypes = (
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_ulonglong),
            ctypes.c_void_p,
            ctypes.c_ulonglong,
            ctypes.c_void_p,
        )
        self.library.crypto_sign_detached.restype = ctypes.c_int
        self.library.crypto_sign_verify_detached.argtypes = (
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_ulonglong,
            ctypes.c_void_p,
        )
        self.library.crypto_sign_verify_detached.restype = ctypes.c_int

    def keypair(self, seed: bytes) -> tuple[bytes, bytes]:
        require(len(seed) == 32, "seed size")
        public_key = ctypes.create_string_buffer(32)
        secret_key = ctypes.create_string_buffer(64)
        require(
            self.library.crypto_sign_seed_keypair(
                public_key, secret_key, seed
            )
            == 0,
            "key derivation",
        )
        return public_key.raw, secret_key.raw

    def sign(self, seed: bytes, message: bytes) -> tuple[bytes, bytes]:
        public_key, secret_key = self.keypair(seed)
        signature = ctypes.create_string_buffer(64)
        size = ctypes.c_ulonglong()
        require(
            self.library.crypto_sign_detached(
                signature, ctypes.byref(size), message, len(message), secret_key
            )
            == 0
            and size.value == 64,
            "signing",
        )
        return public_key, signature.raw

    def verify(
        self, public_key: bytes, message: bytes, signature: bytes
    ) -> bool:
        if len(public_key) != 32 or len(signature) != 64:
            return False
        return (
            self.library.crypto_sign_verify_detached(
                signature, message, len(message), public_key
            )
            == 0
        )


@dataclass
class Account:
    balance: int
    nonce: int


@dataclass(frozen=True)
class Transaction:
    sender_id: bytes
    transaction_id: bytes
    nonce: int
    recipient: bytes
    amount: int
    fee_limit: int
    valid_until: int


def account_id(public_key: bytes) -> bytes:
    return digest("protocol-stack:v1:account", b"\x01" + public_key)


def account_entries(accounts: dict[bytes, Account]) -> list[bytes]:
    return [
        identifier
        + account.balance.to_bytes(8, "big")
        + account.nonce.to_bytes(8, "big")
        for identifier, account in sorted(accounts.items())
    ]


def state_root(
    chain_id: bytes,
    accounts: dict[bytes, Account],
    height: int,
    fee_pool: int,
    total_supply: int,
) -> bytes:
    entries = account_entries(accounts)
    require(sum(account.balance for account in accounts.values()) + fee_pool
            == total_supply, "supply conservation")
    payload = (
        (1).to_bytes(2, "big")
        + chain_id
        + height.to_bytes(8, "big")
        + SUPPLY_LIMIT.to_bytes(8, "big")
        + total_supply.to_bytes(8, "big")
        + fee_pool.to_bytes(8, "big")
        + len(entries).to_bytes(8, "big")
        + merkle(entries, "state")
    )
    return digest("protocol-stack:v1:state-root", payload)


def genesis_bytes(accounts: dict[bytes, Account], total_supply: int) -> bytes:
    entries = account_entries(accounts)
    result = (
        b"PSGN"
        + (1).to_bytes(2, "big")
        + (1).to_bytes(4, "big")
        + SUPPLY_LIMIT.to_bytes(8, "big")
        + total_supply.to_bytes(8, "big")
        + FIXED_FEE.to_bytes(8, "big")
        + (0).to_bytes(8, "big")
        + len(entries).to_bytes(4, "big")
        + b"".join(entries)
    )
    require(all(account.balance > 0 and account.nonce == 0
                for account in accounts.values()), "genesis account")
    return result


def signed_transfer(
    sodium: Sodium,
    seed: bytes,
    chain_id: bytes,
    nonce: int,
    recipient: bytes,
    amount: int,
    fee_limit: int,
    valid_until: int,
) -> bytes:
    public_key, _ = sodium.keypair(seed)
    unsigned = (
        b"PSTX"
        + (1).to_bytes(2, "big")
        + b"\x01"
        + chain_id
        + b"\x01"
        + public_key
        + nonce.to_bytes(8, "big")
        + recipient
        + amount.to_bytes(8, "big")
        + fee_limit.to_bytes(8, "big")
        + valid_until.to_bytes(8, "big")
    )
    _, signature = sodium.sign(
        seed, domain("protocol-stack:v1:tx-sign") + unsigned
    )
    return unsigned + signature


def admit(
    sodium: Sodium, raw: bytes, chain_id: bytes
) -> tuple[int, Transaction | None]:
    if (
        len(raw) != 200
        or raw[:4] != b"PSTX"
        or raw[4:7] != b"\x00\x01\x01"
        or raw[39] != 1
    ):
        return 1, None
    if raw[7:39] != chain_id:
        return 2, None
    public_key = raw[40:72]
    message = domain("protocol-stack:v1:tx-sign") + raw[:136]
    if not sodium.verify(public_key, message, raw[136:]):
        return 3, None
    return 0, Transaction(
        sender_id=account_id(public_key),
        transaction_id=digest("protocol-stack:v1:tx-id", raw),
        nonce=int.from_bytes(raw[72:80], "big"),
        recipient=raw[80:112],
        amount=int.from_bytes(raw[112:120], "big"),
        fee_limit=int.from_bytes(raw[120:128], "big"),
        valid_until=int.from_bytes(raw[128:136], "big"),
    )


def execute(
    transaction: Transaction, accounts: dict[bytes, Account], fee_pool: int
) -> tuple[int, int]:
    if transaction.amount == 0:
        return 1, fee_pool
    if transaction.fee_limit < FIXED_FEE:
        return 2, fee_pool
    if transaction.valid_until < BLOCK_HEIGHT:
        return 3, fee_pool
    sender = accounts.get(transaction.sender_id)
    if sender is None:
        return 4, fee_pool
    if sender.nonce == MAX_U64:
        return 5, fee_pool
    if transaction.nonce != sender.nonce + 1:
        return 6, fee_pool
    if transaction.amount > MAX_U64 - FIXED_FEE:
        return 7, fee_pool
    debit = transaction.amount + FIXED_FEE
    if sender.balance < debit:
        return 8, fee_pool

    if transaction.sender_id == transaction.recipient:
        sender.balance -= FIXED_FEE
    else:
        recipient = accounts.get(transaction.recipient)
        recipient_balance = 0 if recipient is None else recipient.balance
        require(
            recipient_balance <= MAX_U64 - transaction.amount,
            "recipient invariant",
        )
        sender.balance -= debit
        if recipient is None:
            accounts[transaction.recipient] = Account(transaction.amount, 0)
        else:
            recipient.balance += transaction.amount
    sender.nonce = transaction.nonce
    require(fee_pool <= MAX_U64 - FIXED_FEE, "fee-pool invariant")
    return 0, fee_pool + FIXED_FEE


def receipt(transaction_id: bytes, result: int) -> bytes:
    fee = FIXED_FEE if result == 0 else 0
    return (
        b"PSRC"
        + (1).to_bytes(2, "big")
        + transaction_id
        + bytes([result])
        + fee.to_bytes(8, "big")
    )


def scenario(sodium: Sodium) -> dict[str, str]:
    seed_a = bytes.fromhex(
        "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60"
    )
    seed_b = bytes.fromhex(
        "4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb"
    )
    seed_c = bytes.fromhex(
        "c5aa8df43f9f837bedb7442f31dcb7b166d38535076f094b85ce3a2e0b4458f7"
    )
    public_a, _ = sodium.keypair(seed_a)
    public_b, _ = sodium.keypair(seed_b)
    public_c, _ = sodium.keypair(seed_c)
    id_a = account_id(public_a)
    id_b = account_id(public_b)
    id_c = account_id(public_c)
    recipient_new = bytes(31) + b"\x01"
    accounts = {
        id_a: Account(5_000_000, 0),
        id_b: Account(2_000_000, 0),
    }
    total_supply = 7_000_000
    canonical_genesis = genesis_bytes(accounts, total_supply)
    chain_id = digest("protocol-stack:v1:chain-id", canonical_genesis)
    previous_root = state_root(chain_id, accounts, 0, 0, total_supply)

    transactions = [
        signed_transfer(sodium, seed_a, chain_id, 1, id_b, 1_000_000,
                        FIXED_FEE, 1),
        signed_transfer(sodium, seed_a, chain_id, 1, id_b, 1_000_000,
                        FIXED_FEE, 1),
        signed_transfer(sodium, seed_a, chain_id, 2, id_a, 1,
                        FIXED_FEE, 1),
        signed_transfer(sodium, seed_a, chain_id, 3, id_b, 0,
                        FIXED_FEE, 1),
        signed_transfer(sodium, seed_a, chain_id, 3, id_b, 1, 999, 1),
        signed_transfer(sodium, seed_a, chain_id, 3, id_b, 1,
                        FIXED_FEE, 0),
        signed_transfer(sodium, seed_c, chain_id, 1, id_a, 1,
                        FIXED_FEE, 1),
        signed_transfer(sodium, seed_b, chain_id, 5, id_a, 1,
                        FIXED_FEE, 1),
        signed_transfer(sodium, seed_b, chain_id, 1, id_a, MAX_U64,
                        FIXED_FEE, 1),
        signed_transfer(sodium, seed_b, chain_id, 1, id_a, 3_000_000,
                        FIXED_FEE, 1),
        signed_transfer(sodium, seed_b, chain_id, 1, recipient_new, 1_000_000,
                        FIXED_FEE, 1),
    ]
    invalid_signature = bytearray(
        signed_transfer(sodium, seed_c, chain_id, 1, id_a, 1, FIXED_FEE, 1)
    )
    invalid_signature[-1] ^= 1
    transactions.append(bytes(invalid_signature))
    transactions.append(transactions[0][:-1])
    wrong_chain = bytes([0xFF]) * 32
    transactions.append(
        signed_transfer(sodium, seed_c, wrong_chain, 1, id_a, 1, FIXED_FEE, 1)
    )
    unknown_transaction_kind = bytearray(transactions[0])
    unknown_transaction_kind[6] = 2
    transactions.append(bytes(unknown_transaction_kind))

    values: dict[str, str] = {
        "supply_limit": str(SUPPLY_LIMIT),
        "fixed_fee": str(FIXED_FEE),
        "total_supply": str(total_supply),
        "genesis": canonical_genesis.hex(),
        "chain_id": chain_id.hex(),
        "previous_state_root": previous_root.hex(),
        "raw_count": str(len(transactions)),
    }
    for index, entry in enumerate(account_entries(accounts)):
        values[f"genesis.account{index}"] = entry.hex()

    admitted_ids: list[bytes] = []
    fee_pool = 0
    receipt_index = 0
    for raw_index, raw in enumerate(transactions):
        values[f"raw{raw_index}"] = raw.hex()
        admission, transaction = admit(sodium, raw, chain_id)
        values[f"raw{raw_index}.admission"] = str(admission)
        if transaction is None:
            continue
        result, fee_pool = execute(transaction, accounts, fee_pool)
        admitted_ids.append(transaction.transaction_id)
        encoded_receipt = receipt(transaction.transaction_id, result)
        values[f"receipt{receipt_index}.result"] = str(result)
        values[f"receipt{receipt_index}"] = encoded_receipt.hex()
        receipt_index += 1

    resulting_root = state_root(
        chain_id, accounts, BLOCK_HEIGHT, fee_pool, total_supply
    )
    transaction_root = merkle(admitted_ids, "tx")
    header = (
        b"PSBL"
        + (1).to_bytes(2, "big")
        + chain_id
        + BLOCK_HEIGHT.to_bytes(8, "big")
        + previous_root
        + transaction_root
        + resulting_root
        + len(admitted_ids).to_bytes(4, "big")
    )
    values.update(
        {
            "admitted_count": str(len(admitted_ids)),
            "fee_pool": str(fee_pool),
            "transaction_root": transaction_root.hex(),
            "resulting_state_root": resulting_root.hex(),
            "block_header": header.hex(),
            "block_id": digest("protocol-stack:v1:block-id", header).hex(),
            "final_account_count": str(len(accounts)),
        }
    )
    for index, entry in enumerate(account_entries(accounts)):
        values[f"final.account{index}"] = entry.hex()
    boundary_accounts = {id_a: Account(5_000, MAX_U64)}
    boundary_transaction = Transaction(
        sender_id=id_a,
        transaction_id=bytes(32),
        nonce=MAX_U64,
        recipient=id_b,
        amount=1,
        fee_limit=FIXED_FEE,
        valid_until=1,
    )
    boundary_result, boundary_pool = execute(
        boundary_transaction, boundary_accounts, 0
    )
    require(
        boundary_result == 5
        and boundary_pool == 0
        and boundary_accounts[id_a] == Account(5_000, MAX_U64),
        "nonce exhaustion atomicity",
    )
    values["boundary.nonce_exhausted.result"] = str(boundary_result)
    return values


def load_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="ascii").splitlines():
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        require(bool(separator) and key not in values, "vector syntax")
        values[key] = value
    return values


def main() -> int:
    sodium = Sodium()
    expected = scenario(sodium)
    if len(sys.argv) == 2 and sys.argv[1] == "--emit":
        for key, value in expected.items():
            print(f"{key}={value}")
        return 0
    require(len(sys.argv) == 2, "usage: verify.py VECTOR_FILE")
    actual = load_values(Path(sys.argv[1]))
    require(actual == expected, "ledger vector mismatch")
    print("Python ledger transition vectors: passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, OSError, ValueError) as error:
        print(f"Python ledger transition vectors: failed: {error}",
              file=sys.stderr)
        raise SystemExit(1) from error
