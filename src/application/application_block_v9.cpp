// `finalize_block` and `commit`, which is where the version-nine application's
// two safety arguments live.
//
// **The first is version eight's and is unchanged.** `finalize_block` writes
// nothing: it copies the durable head, executes the block against the copy, and
// stages the root, the block identifier, and the per-transaction results.
// `commit` replays the same block through the store and requires the store to
// reproduce exactly what was staged. That equality is what makes "the root this
// node told the network" and "the root this node persisted" one fact.
//
// **The second is version nine's and is about a value that must not be
// regenerated.** `commit` replays the block with the **staged** timestamp. A
// commit that replayed the height and supplied a fresh stamp would commit a root
// naming a height the stamp does not belong to, and every later block would still
// satisfy C2 because the stale stamp is smaller — a wrong root rather than a
// refusal, which is the direction that hides.
//
// **There is no clock in this file.** `replay_timestamp` takes none, the bound
// source is not reached, and C5 is therefore unreachable on the decided-block
// path by construction rather than by discipline.

#include "protocol/application/application_v9.hpp"

#include "application_v9_internal.hpp"

#include <algorithm>
#include <utility>

namespace protocol::application {
namespace {

namespace v9 = protocol::v9;
using protocol::storage::BlockCommitV9;
using protocol::storage::BlockRejectedV9;
using protocol::storage::LedgerHeadV9;
using protocol::storage::SQLiteLedgerV9Error;

}  // namespace

namespace internal_v9 {

// One result per raw input, in the order the inputs arrived. A rejected
// admission carries its own small code and no receipt, because it performed no
// state read or write and never entered the transaction root.
std::variant<FinalizedBlockV9, ApplicationError> finalize_result(
    const v9::BlockOutcome& outcome) {
  FinalizedBlockV9 result{outcome.resulting_state_root, outcome.block_id, {}};
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
    auto encoded = v9::encode_receipt(executed.receipt);
    if (!encoded) return ApplicationError::internal_failure;
    result.transaction_results.push_back(TransactionResult{
        application_code(executed.outcome.result), std::move(*encoded)});
    ++executed_index;
  }
  // Every admitted input must have produced exactly one executed transaction.
  if (executed_index != outcome.executed.size()) {
    return ApplicationError::internal_failure;
  }
  return result;
}

}  // namespace internal_v9

FinalizeBlockResultV9 ApplicationV9::finalize_block(
    std::uint64_t height, std::uint64_t timestamp,
    std::span<const v9::Bytes> transactions) {
  const std::lock_guard<std::mutex> lock(implementation_->mutex);
  if (implementation_->terminal || !implementation_->ready) {
    return FinalizeFailureV9{ApplicationError::sequence_failure};
  }
  if (implementation_->stage) {
    const auto& stage = *implementation_->stage;
    // **The stamp is part of what makes a repeat a repeat.** CometBFT may ask
    // twice, and the byte-identical response is owed only to a byte-identical
    // request — which under version nine includes the timestamp.
    if (stage.height == height && stage.timestamp == timestamp &&
        std::equal(stage.transactions.begin(), stage.transactions.end(),
                   transactions.begin(), transactions.end())) {
      return stage.response;
    }
    return FinalizeFailureV9{
        implementation_->fail(ApplicationError::sequence_failure)};
  }
  if (height > kMaximumAdapterHeight ||
      !internal_v9::within_block_bounds(transactions)) {
    return FinalizeFailureV9{
        implementation_->fail(ApplicationError::invalid_request)};
  }

  auto head = implementation_->ledger.read_head();
  if (!std::holds_alternative<LedgerHeadV9>(head)) {
    return FinalizeFailureV9{
        implementation_->fail(internal_v9::head_error(head))};
  }
  auto durable = std::get<LedgerHeadV9>(std::move(head));
  if (height != durable.ledger.height + 1) {
    return FinalizeFailureV9{
        implementation_->fail(ApplicationError::sequence_failure)};
  }

  // **C1 and C2, through the entry point that has no clock argument.** A failure
  // here is fatal and names which rule failed: this operation only ever runs on
  // a block the network already decided, so a refusal means this machine's rules
  // and the network's decision disagree about history, and a deterministic
  // application that has found such a disagreement cannot continue and be
  // trusted. It stops rather than guess which was right.
  const v9::Head current{durable.ledger.height, durable.ledger.timestamp};
  switch (v9::replay_timestamp(current, height, timestamp)) {
    case v9::TimestampCondition::accepted:
      break;
    case v9::TimestampCondition::timestamp_range:
      return implementation_->fail_timestamp(
          TimestampFailureV9::decided_block_failed_range);
    case v9::TimestampCondition::timestamp_not_monotonic:
      return implementation_->fail_timestamp(
          TimestampFailureV9::decided_block_failed_monotonicity);
    // `replay_timestamp` applies neither tolerance, so neither is reachable;
    // the height case is already refused above with its own sequence failure.
    case v9::TimestampCondition::height_not_next:
    case v9::TimestampCondition::timestamp_ahead_of_tolerance:
    case v9::TimestampCondition::timestamp_behind_tolerance:
      return FinalizeFailureV9{
          implementation_->fail(ApplicationError::internal_failure)};
  }

  auto candidate = std::move(durable.ledger);
  auto outcome = v9::execute_block(candidate, timestamp, transactions,
                                   implementation_->verify);
  if (!outcome) {
    return FinalizeFailureV9{
        implementation_->fail(ApplicationError::kernel_failure)};
  }

  auto response = internal_v9::finalize_result(*outcome);
  if (!std::holds_alternative<FinalizedBlockV9>(response)) {
    return FinalizeFailureV9{
        implementation_->fail(std::get<ApplicationError>(response))};
  }
  auto finalized = std::get<FinalizedBlockV9>(std::move(response));

  BlockCommitV9 expected;
  expected.height = outcome->height;
  expected.timestamp = outcome->timestamp;
  expected.previous_state_root = outcome->previous_state_root;
  expected.resulting_state_root = outcome->resulting_state_root;
  expected.transaction_root = outcome->transaction_root;
  expected.block_id = outcome->block_id;
  expected.transaction_count =
      static_cast<std::uint32_t>(outcome->executed.size());

  implementation_->stage.emplace(Impl::Stage{
      height,
      timestamp,
      std::vector<v9::Bytes>(transactions.begin(), transactions.end()),
      expected,
      finalized.state_root,
      finalized,
  });
  return implementation_->stage->response;
}

CommitResultV9 ApplicationV9::commit() {
  const std::lock_guard<std::mutex> lock(implementation_->mutex);
  if (implementation_->terminal || !implementation_->ready ||
      !implementation_->stage) {
    return implementation_->fail(ApplicationError::sequence_failure);
  }
  const auto& stage = *implementation_->stage;
  // The exact staged height, timestamp, and raw byte sequence.
  auto applied = implementation_->ledger.apply_block(stage.height,
                                                     stage.timestamp,
                                                     stage.transactions);
  if (std::holds_alternative<SQLiteLedgerV9Error>(applied)) {
    return implementation_->fail(ApplicationError::storage_failure);
  }
  if (std::holds_alternative<BlockRejectedV9>(applied)) {
    // The kernel accepted this block a moment ago against the same head. If it
    // refuses it now the two disagree, which is not a condition to recover from.
    return implementation_->fail(ApplicationError::internal_failure);
  }
  if (std::get<BlockCommitV9>(applied) != stage.commit) {
    return implementation_->fail(ApplicationError::internal_failure);
  }
  // And the durable head is at the root the network was told, at the height and
  // the stamp it was told. **The stamp is compared although the root commits to
  // it**, for the reason Info reports it: a root proves agreement without showing
  // the value, and the question version nine raises is precisely which stamp
  // landed.
  auto head = implementation_->ledger.read_head();
  if (!std::holds_alternative<LedgerHeadV9>(head)) {
    return implementation_->fail(internal_v9::head_error(head));
  }
  const auto& durable = std::get<LedgerHeadV9>(head);
  if (durable.state_root != stage.candidate_root ||
      durable.ledger.height != stage.height ||
      durable.ledger.timestamp != stage.timestamp) {
    return implementation_->fail(ApplicationError::internal_failure);
  }

  const CommittedHeadV9 committed{stage.height, stage.timestamp,
                                  stage.response.state_root};
  implementation_->stage.reset();
  return committed;
}

}  // namespace protocol::application
