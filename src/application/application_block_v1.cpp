#include "protocol/application/application_v1.hpp"

#include "application_v1_internal.hpp"

#include "protocol/v1/ledger.hpp"

#include <algorithm>
#include <utility>

namespace protocol::application {
namespace {

using protocol::storage::LedgerHead;
using protocol::storage::SQLiteLedgerError;
using protocol::v1::BlockCommit;
using protocol::v1::Bytes;
using protocol::v1::Ledger;

std::variant<FinalizedBlock, ApplicationError> finalize_result(
    const BlockCommit& commit) {
  const auto admitted_count = static_cast<std::size_t>(
      std::count_if(
          commit.admissions.begin(), commit.admissions.end(),
          [](const auto& admission) { return !admission; }));
  if (admitted_count != commit.transaction_ids.size() ||
      commit.transaction_ids.size() != commit.receipts.size() ||
      commit.receipts.size() != commit.encoded_receipts.size()) {
    return ApplicationError::internal_failure;
  }

  FinalizedBlock result{commit.resulting_state_root, {}};
  result.transaction_results.reserve(commit.admissions.size());
  std::size_t admitted_index = 0;
  for (const auto& admission : commit.admissions) {
    if (admission) {
      result.transaction_results.push_back(
          TransactionResult{application_code(*admission), {}});
      continue;
    }
    if (admitted_index >= commit.receipts.size()) {
      return ApplicationError::internal_failure;
    }
    result.transaction_results.push_back(TransactionResult{
        application_code(commit.receipts[admitted_index].result),
        commit.encoded_receipts[admitted_index],
    });
    ++admitted_index;
  }
  if (admitted_index != commit.receipts.size()) {
    return ApplicationError::internal_failure;
  }
  return result;
}

}  // namespace

FinalizeBlockResult ApplicationV1::finalize_block(
    std::uint64_t height,
    std::span<const Bytes> transactions) {
  const std::lock_guard<std::mutex> lock(implementation_->mutex);
  if (implementation_->terminal || !implementation_->ready) {
    return ApplicationError::sequence_failure;
  }
  if (implementation_->stage) {
    const auto& stage = *implementation_->stage;
    if (stage.height == height &&
        std::ranges::equal(stage.transactions, transactions)) {
      return stage.response;
    }
    return implementation_->fail(ApplicationError::sequence_failure);
  }
  if (height > kMaximumAdapterHeight ||
      !internal::within_block_bounds(transactions)) {
    return implementation_->fail(ApplicationError::invalid_request);
  }

  auto head = implementation_->ledger.read_head();
  if (!std::holds_alternative<LedgerHead>(head)) {
    return implementation_->fail(internal::head_error(head));
  }
  auto durable = std::get<LedgerHead>(std::move(head));
  auto restored = protocol::v1::restore_ledger(
      durable.state, implementation_->parameters, durable.state_root);
  if (!std::holds_alternative<Ledger>(restored.result)) {
    return implementation_->fail(ApplicationError::internal_failure);
  }
  auto candidate = std::get<Ledger>(std::move(restored.result));
  auto applied = candidate.apply_block(height, transactions);
  if (!std::holds_alternative<BlockCommit>(applied)) {
    return implementation_->fail(ApplicationError::kernel_failure);
  }
  auto commit = std::get<BlockCommit>(std::move(applied));
  auto response = finalize_result(commit);
  if (!std::holds_alternative<FinalizedBlock>(response)) {
    return implementation_->fail(
        std::get<ApplicationError>(response));
  }

  auto finalized = std::get<FinalizedBlock>(std::move(response));
  implementation_->stage.emplace(Impl::Stage{
      height,
      std::vector<Bytes>(transactions.begin(), transactions.end()),
      std::move(commit),
      LedgerHead{candidate.state(), finalized.state_root},
      finalized,
  });
  return implementation_->stage->response;
}

CommitResult ApplicationV1::commit() {
  const std::lock_guard<std::mutex> lock(implementation_->mutex);
  if (implementation_->terminal || !implementation_->ready ||
      !implementation_->stage) {
    return implementation_->fail(ApplicationError::sequence_failure);
  }
  const auto& stage = *implementation_->stage;
  auto applied = implementation_->ledger.apply_block(
      stage.height, stage.transactions);
  if (std::holds_alternative<SQLiteLedgerError>(applied)) {
    return implementation_->fail(ApplicationError::storage_failure);
  }
  if (!std::holds_alternative<BlockCommit>(applied) ||
      std::get<BlockCommit>(applied) != stage.commit) {
    return implementation_->fail(ApplicationError::internal_failure);
  }
  auto head = implementation_->ledger.read_head();
  if (!std::holds_alternative<LedgerHead>(head) ||
      std::get<LedgerHead>(head) != stage.candidate_head) {
    return implementation_->fail(
        std::holds_alternative<LedgerHead>(head)
            ? ApplicationError::internal_failure
            : ApplicationError::storage_failure);
  }

  const auto committed = CommittedHead{
      stage.height,
      stage.response.state_root,
  };
  implementation_->stage.reset();
  return committed;
}

}  // namespace protocol::application
