#!/usr/bin/env python3

"""Independent version-one ledger model for randomized differential tests."""

from __future__ import annotations

from dataclasses import dataclass

from pinned_sodium import Sodium
from protocol_bytes import (
    MAX_BLOCK_INPUTS,
    MAX_CANONICAL_BYTES,
    MAX_GENESIS_ACCOUNTS,
    MAX_U64,
    account_id,
    digest,
    domain,
    encode_receipt,
    merkle,
    require,
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


@dataclass
class State:
    chain_id: bytes
    supply_limit: int
    total_supply: int
    fixed_fee: int
    height: int
    fee_pool: int
    accounts: dict[bytes, Account]

    def clone(self) -> State:
        return State(
            self.chain_id,
            self.supply_limit,
            self.total_supply,
            self.fixed_fee,
            self.height,
            self.fee_pool,
            {
                identifier: Account(account.balance, account.nonce)
                for identifier, account in self.accounts.items()
            },
        )


@dataclass(frozen=True)
class Execution:
    result: int
    self_transfer: bool
    created_recipient: bool


@dataclass
class BlockCommit:
    height: int
    admissions: list[int]
    transactions: list[Transaction]
    executions: list[Execution]
    encoded_receipts: list[bytes]
    previous_state_root: bytes
    transaction_root: bytes
    resulting_state_root: bytes
    header: bytes
    block_id: bytes


def account_entries(accounts: dict[bytes, Account]) -> list[bytes]:
    return [
        identifier
        + account.balance.to_bytes(8, "big")
        + account.nonce.to_bytes(8, "big")
        for identifier, account in sorted(accounts.items())
    ]


def state_root(state: State) -> bytes:
    require(state.total_supply <= state.supply_limit, "supply limit")
    conserved = state.fee_pool
    for account in state.accounts.values():
        require(conserved <= MAX_U64 - account.balance, "supply overflow")
        conserved += account.balance
    require(conserved == state.total_supply, "supply mismatch")
    entries = account_entries(state.accounts)
    payload = (
        (1).to_bytes(2, "big")
        + state.chain_id
        + state.height.to_bytes(8, "big")
        + state.supply_limit.to_bytes(8, "big")
        + state.total_supply.to_bytes(8, "big")
        + state.fee_pool.to_bytes(8, "big")
        + len(entries).to_bytes(8, "big")
        + merkle(entries, "state")
    )
    return digest("protocol-stack:v1:state-root", payload)


def encode_genesis(
    accounts: dict[bytes, Account],
    supply_limit: int,
    total_supply: int,
    fixed_fee: int,
    fee_pool: int = 0,
) -> bytes:
    entries = account_entries(accounts)
    require(0 < len(entries) <= MAX_GENESIS_ACCOUNTS, "genesis count")
    require(
        all(account.balance > 0 and account.nonce == 0
            for account in accounts.values()),
        "invalid genesis account",
    )
    encoded = (
        b"PSGN"
        + (1).to_bytes(2, "big")
        + (1).to_bytes(4, "big")
        + supply_limit.to_bytes(8, "big")
        + total_supply.to_bytes(8, "big")
        + fixed_fee.to_bytes(8, "big")
        + fee_pool.to_bytes(8, "big")
        + len(entries).to_bytes(4, "big")
        + b"".join(entries)
    )
    require(len(encoded) <= MAX_CANONICAL_BYTES, "genesis size")
    return encoded


def decode_genesis(encoded: bytes) -> State:
    require(len(encoded) >= 46, "truncated genesis")
    require(len(encoded) <= MAX_CANONICAL_BYTES, "oversized genesis")
    require(encoded[:6] == b"PSGN\x00\x01", "genesis shape")
    require(int.from_bytes(encoded[6:10], "big") == 1, "network")
    supply_limit = int.from_bytes(encoded[10:18], "big")
    total_supply = int.from_bytes(encoded[18:26], "big")
    fixed_fee = int.from_bytes(encoded[26:34], "big")
    fee_pool = int.from_bytes(encoded[34:42], "big")
    count = int.from_bytes(encoded[42:46], "big")
    require(0 < count <= MAX_GENESIS_ACCOUNTS, "genesis count")
    require(len(encoded) == 46 + count * 48, "genesis length")
    require(
        supply_limit > 0
        and 0 < total_supply <= supply_limit
        and fixed_fee > 0,
        "genesis parameters",
    )
    accounts: dict[bytes, Account] = {}
    previous: bytes | None = None
    for index in range(count):
        offset = 46 + index * 48
        identifier = encoded[offset : offset + 32]
        balance = int.from_bytes(encoded[offset + 32 : offset + 40], "big")
        nonce = int.from_bytes(encoded[offset + 40 : offset + 48], "big")
        require(
            balance > 0
            and nonce == 0
            and (previous is None or previous < identifier),
            "genesis accounts",
        )
        accounts[identifier] = Account(balance, nonce)
        previous = identifier
    state = State(
        digest("protocol-stack:v1:chain-id", encoded),
        supply_limit,
        total_supply,
        fixed_fee,
        0,
        fee_pool,
        accounts,
    )
    state_root(state)
    return state


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
    signature = sodium.sign(
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
    signing_message = domain("protocol-stack:v1:tx-sign") + raw[:136]
    if not sodium.verify(public_key, signing_message, raw[136:]):
        return 3, None
    return 0, Transaction(
        account_id(public_key),
        digest("protocol-stack:v1:tx-id", raw),
        int.from_bytes(raw[72:80], "big"),
        raw[80:112],
        int.from_bytes(raw[112:120], "big"),
        int.from_bytes(raw[120:128], "big"),
        int.from_bytes(raw[128:136], "big"),
    )


def execute(transaction: Transaction, state: State, height: int) -> Execution:
    if transaction.amount == 0:
        return Execution(1, False, False)
    if transaction.fee_limit < state.fixed_fee:
        return Execution(2, False, False)
    if transaction.valid_until < height:
        return Execution(3, False, False)
    sender = state.accounts.get(transaction.sender_id)
    if sender is None:
        return Execution(4, False, False)
    if sender.nonce == MAX_U64:
        return Execution(5, False, False)
    if transaction.nonce != sender.nonce + 1:
        return Execution(6, False, False)
    if transaction.amount > MAX_U64 - state.fixed_fee:
        return Execution(7, False, False)
    debit = transaction.amount + state.fixed_fee
    if sender.balance < debit:
        return Execution(8, False, False)

    self_transfer = transaction.sender_id == transaction.recipient
    created_recipient = (
        not self_transfer and transaction.recipient not in state.accounts
    )
    if not self_transfer:
        recipient = state.accounts.get(transaction.recipient)
        recipient_balance = 0 if recipient is None else recipient.balance
        require(
            recipient_balance <= MAX_U64 - transaction.amount,
            "recipient invariant",
        )
    require(
        state.fee_pool <= MAX_U64 - state.fixed_fee,
        "fee-pool invariant",
    )
    if self_transfer:
        sender.balance -= state.fixed_fee
    else:
        recipient = state.accounts.get(transaction.recipient)
        sender.balance -= debit
        if recipient is None:
            state.accounts[transaction.recipient] = Account(
                transaction.amount, 0
            )
        else:
            recipient.balance += transaction.amount
    sender.nonce = transaction.nonce
    state.fee_pool += state.fixed_fee
    return Execution(0, self_transfer, created_recipient)


class ReferenceLedger:
    def __init__(self, genesis: bytes, sodium: Sodium) -> None:
        self.state = decode_genesis(genesis)
        self.sodium = sodium

    def apply_block(self, height: int, raws: list[bytes]) -> BlockCommit:
        require(len(raws) <= MAX_BLOCK_INPUTS, "block input count")
        require(self.state.height < MAX_U64, "height exhausted")
        require(height == self.state.height + 1, "invalid height")
        previous_root = state_root(self.state)
        tentative = self.state.clone()
        admissions: list[int] = []
        transactions: list[Transaction] = []
        executions: list[Execution] = []
        receipts: list[bytes] = []
        for raw in raws:
            admission, transaction = admit(
                self.sodium, raw, tentative.chain_id
            )
            admissions.append(admission)
            if transaction is None:
                continue
            execution = execute(transaction, tentative, height)
            transactions.append(transaction)
            executions.append(execution)
            receipts.append(
                encode_receipt(
                    transaction.transaction_id,
                    execution.result,
                    tentative.fixed_fee,
                )
            )
        tentative.height = height
        resulting_root = state_root(tentative)
        transaction_root = merkle(
            [transaction.transaction_id for transaction in transactions],
            "tx",
        )
        header = (
            b"PSBL"
            + (1).to_bytes(2, "big")
            + tentative.chain_id
            + height.to_bytes(8, "big")
            + previous_root
            + transaction_root
            + resulting_root
            + len(transactions).to_bytes(4, "big")
        )
        commit = BlockCommit(
            height,
            admissions,
            transactions,
            executions,
            receipts,
            previous_root,
            transaction_root,
            resulting_root,
            header,
            digest("protocol-stack:v1:block-id", header),
        )
        self.state = tentative
        return commit
