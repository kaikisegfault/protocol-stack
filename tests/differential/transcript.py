"""Typed transcript formatting and comparison for the C++ runner protocol."""

from __future__ import annotations

from model import BlockCommit, State


def format_block(
    scenario: int,
    block_index: int,
    commit: BlockCommit,
    state: State,
) -> str:
    def joined(values: list[str]) -> str:
        return ",".join(values) if values else "-"

    accounts = joined(
        [
            f"{identifier.hex()}:{account.balance}:{account.nonce}"
            for identifier, account in sorted(state.accounts.items())
        ]
    )
    fields = [
        "D",
        str(scenario),
        str(block_index),
        str(commit.height),
        joined([str(value) for value in commit.admissions]),
        joined(
            [
                transaction.transaction_id.hex()
                for transaction in commit.transactions
            ]
        ),
        joined([receipt.hex() for receipt in commit.encoded_receipts]),
        joined(
            [
                f"{transaction.transaction_id.hex()}:"
                f"{execution.result}:"
                f"{state.fixed_fee if execution.result == 0 else 0}"
                for transaction, execution in zip(
                    commit.transactions, commit.executions, strict=True
                )
            ]
        ),
        commit.previous_state_root.hex(),
        commit.transaction_root.hex(),
        commit.resulting_state_root.hex(),
        commit.header.hex(),
        commit.block_id.hex(),
        state.chain_id.hex(),
        str(state.supply_limit),
        str(state.total_supply),
        str(state.fixed_fee),
        str(state.height),
        str(state.fee_pool),
        accounts,
    ]
    return "\t".join(fields)


def compare(expected: list[str], actual_text: str) -> None:
    actual = actual_text.splitlines()
    if expected == actual:
        return
    limit = max(len(expected), len(actual))
    mismatch = next(
        (
            index
            for index in range(limit)
            if index >= len(expected)
            or index >= len(actual)
            or expected[index] != actual[index]
        ),
        0,
    )
    expected_line = (
        expected[mismatch] if mismatch < len(expected) else "<EOF>"
    )
    actual_line = actual[mismatch] if mismatch < len(actual) else "<EOF>"
    raise ValueError(
        f"transcript mismatch at block record {mismatch}\n"
        f"expected: {expected_line}\nactual:   {actual_line}"
    )
