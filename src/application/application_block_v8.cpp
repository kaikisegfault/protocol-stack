// `finalize_block` and `commit`, which is where the version-eight application's
// one real safety argument lives.
//
// **`finalize_block` writes nothing.** It copies the durable head, executes the
// block against the copy, and stages the root, the block identifier, and the
// per-transaction results it produced. An identical repeat returns the same
// staged response, because CometBFT may ask twice and a second execution that
// disagreed with the first would be a bug this layer must not hide.
//
// **`commit` replays the same block through the store and requires the store to
// reproduce exactly what was staged** — the same commit record and the same
// root at the same height. Anything else is terminal: the node has told the
// network one root and persisted another, and there is no honest way to
// continue.

#include "protocol/application/application_v8.hpp"

#include "application_v8_internal.hpp"

#include <algorithm>
#include <utility>

namespace protocol::application {
namespace {

namespace v8 = protocol::v8;
using protocol::storage::BlockCommitV8;
using protocol::storage::BlockRejectedV8;
using protocol::storage::LedgerHeadV8;
using protocol::storage::SQLiteLedgerV8Error;

}  // namespace

namespace internal_v8 {

// One result per raw input, in the order the inputs arrived. A rejected
// admission carries its own small code and no receipt, because it performed no
// state read or write and never entered the transaction root.
std::variant<FinalizedBlockV8, ApplicationError> finalize_result(
    const v8::BlockOutcome& outcome) {
  FinalizedBlockV8 result{outcome.resulting_state_root, outcome.block_id, {}};
  result.transaction_results.reserve(outcome.admissions.size());
  std::size_t executed_index = 0;
  for (const auto& admission : outcome.admissions) {
    if (!admission.admitted()) {
      result.transaction_results.push_back(
          TransactionResult{application_code(*admission.error), {}});
      continue;
    }
    if (executed_index >= outcome.executed.size()) {
      return ApplicationError::internal_failure;
    }
    const auto& executed = outcome.executed[executed_index];
    auto encoded = v8::encode_receipt(executed.receipt);
    if (!encoded) return ApplicationError::internal_failure;
    result.transaction_results.push_back(TransactionResult{
        application_code(executed.outcome.result), std::move(*encoded)});
    ++executed_index;
  }
  // Every admitted input must have produced exactly one executed transaction.
  // The kernel pushes the two in lockstep; requiring it here is what makes the
  // response's order the block's order rather than a hope.
  if (executed_index != outcome.executed.size()) {
    return ApplicationError::internal_failure;
  }
  return result;
}

}  // namespace internal_v8

FinalizeBlockResultV8 ApplicationV8::finalize_block(
    std::uint64_t height, std::span<const v8::Bytes> transactions) {
  const std::lock_guard<std::mutex> lock(implementation_->mutex);
  if (implementation_->terminal || !implementation_->ready) {
    return ApplicationError::sequence_failure;
  }
  if (implementation_->stage) {
    const auto& stage = *implementation_->stage;
    if (stage.height == height &&
        std::equal(stage.transactions.begin(), stage.transactions.end(),
                   transactions.begin(), transactions.end())) {
      return stage.response;
    }
    return implementation_->fail(ApplicationError::sequence_failure);
  }
  if (height > kMaximumAdapterHeight ||
      !internal_v8::within_block_bounds(transactions)) {
    return implementation_->fail(ApplicationError::invalid_request);
  }

  auto head = implementation_->ledger.read_head();
  if (!std::holds_alternative<LedgerHeadV8>(head)) {
    return implementation_->fail(internal_v8::head_error(head));
  }
  auto durable = std::get<LedgerHeadV8>(std::move(head));
  if (height != durable.ledger.height + 1) {
    return implementation_->fail(ApplicationError::sequence_failure);
  }

  auto candidate = std::move(durable.ledger);
  auto outcome =
      v8::execute_block(candidate, transactions, implementation_->verify);
  if (!outcome) return implementation_->fail(ApplicationError::kernel_failure);

  auto response = internal_v8::finalize_result(*outcome);
  if (!std::holds_alternative<FinalizedBlockV8>(response)) {
    return implementation_->fail(std::get<ApplicationError>(response));
  }
  auto finalized = std::get<FinalizedBlockV8>(std::move(response));

  BlockCommitV8 expected;
  expected.height = outcome->height;
  expected.previous_state_root = outcome->previous_state_root;
  expected.resulting_state_root = outcome->resulting_state_root;
  expected.transaction_root = outcome->transaction_root;
  expected.block_id = outcome->block_id;
  expected.transaction_count =
      static_cast<std::uint32_t>(outcome->executed.size());

  implementation_->stage.emplace(Impl::Stage{
      height,
      std::vector<v8::Bytes>(transactions.begin(), transactions.end()),
      expected,
      finalized.state_root,
      finalized,
  });
  return implementation_->stage->response;
}

CommitResultV8 ApplicationV8::commit() {
  const std::lock_guard<std::mutex> lock(implementation_->mutex);
  if (implementation_->terminal || !implementation_->ready ||
      !implementation_->stage) {
    return implementation_->fail(ApplicationError::sequence_failure);
  }
  const auto& stage = *implementation_->stage;
  auto applied =
      implementation_->ledger.apply_block(stage.height, stage.transactions);
  if (std::holds_alternative<SQLiteLedgerV8Error>(applied)) {
    return implementation_->fail(ApplicationError::storage_failure);
  }
  if (std::holds_alternative<BlockRejectedV8>(applied)) {
    // The kernel accepted this block a moment ago against the same head. If it
    // refuses it now the two disagree, which is not a condition to recover from.
    return implementation_->fail(ApplicationError::internal_failure);
  }
  if (std::get<BlockCommitV8>(applied) != stage.commit) {
    return implementation_->fail(ApplicationError::internal_failure);
  }
  // And the durable head is at the root the network was told. Comparing roots is
  // comparing states, because the root commits to every entry.
  auto head = implementation_->ledger.read_head();
  if (!std::holds_alternative<LedgerHeadV8>(head)) {
    return implementation_->fail(internal_v8::head_error(head));
  }
  const auto& durable = std::get<LedgerHeadV8>(head);
  if (durable.state_root != stage.candidate_root ||
      durable.ledger.height != stage.height) {
    return implementation_->fail(ApplicationError::internal_failure);
  }

  const CommittedHeadV8 committed{stage.height, stage.response.state_root};
  implementation_->stage.reset();
  return committed;
}

}  // namespace protocol::application
