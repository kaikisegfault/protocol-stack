"""Coverage accounting for directed and randomized differential cases."""

from __future__ import annotations

from dataclasses import dataclass, field

from model import BlockCommit
from protocol_bytes import require


@dataclass
class Coverage:
    admission_errors: set[int] = field(default_factory=set)
    execution_results: set[int] = field(default_factory=set)
    features: set[str] = field(default_factory=set)
    blocks: int = 0
    raw_inputs: int = 0
    admitted: int = 0

    def observe(
        self,
        raws: list[bytes],
        commit: BlockCommit,
        seen: dict[bytes, int],
    ) -> None:
        self.blocks += 1
        self.raw_inputs += len(raws)
        self.admitted += len(commit.transactions)
        self.admission_errors.update(
            value for value in commit.admissions if value != 0
        )
        self.execution_results.update(
            execution.result for execution in commit.executions
        )
        if not raws:
            self.features.add("empty_block")
        if raws and all(value != 0 for value in commit.admissions):
            self.features.add("all_unadmitted")

        for transaction, execution in zip(
            commit.transactions, commit.executions, strict=True
        ):
            previous_result = seen.get(transaction.transaction_id)
            if previous_result == 0 and execution.result == 6:
                self.features.add("replay")
            seen[transaction.transaction_id] = execution.result
            if execution.result == 0 and execution.self_transfer:
                self.features.add("self_transfer")
            if execution.result == 0 and execution.created_recipient:
                self.features.add("recipient_creation")

        for earlier_index, earlier in enumerate(commit.transactions):
            later_indexes = range(
                earlier_index + 1, len(commit.transactions)
            )
            for later_index in later_indexes:
                later = commit.transactions[later_index]
                if (
                    earlier.sender_id == later.sender_id
                    and earlier.nonce == later.nonce + 1
                    and commit.executions[earlier_index].result == 6
                    and commit.executions[later_index].result == 0
                ):
                    self.features.add("ordered_effect")

    def verify(self) -> None:
        require(
            self.admission_errors == {1, 2, 3},
            f"admission coverage: {sorted(self.admission_errors)}",
        )
        require(
            self.execution_results == {0, 1, 2, 3, 4, 6, 7, 8},
            f"execution coverage: {sorted(self.execution_results)}",
        )
        required_features = {
            "all_unadmitted",
            "empty_block",
            "ordered_effect",
            "recipient_creation",
            "replay",
            "self_transfer",
        }
        require(
            self.features == required_features,
            f"feature coverage: {sorted(self.features)}",
        )
