// The version-eight application layer: construction, the read-only operations,
// and the two proposal operations.
//
// `application_block_v8.cpp` holds `finalize_block` and `commit`, which is where
// the staged-then-replayed equality lives.

#include "protocol/application/application_v8.hpp"

#include "application_v8_internal.hpp"

#include <algorithm>
#include <type_traits>
#include <utility>

namespace protocol::application {
namespace {

namespace v8 = protocol::v8;
using protocol::storage::LedgerHeadV8;
using protocol::storage::SQLiteLedgerV8Error;

// The chain identity a genesis produces is not the string an operator types
// into CometBFT, so the app state is what pins the two together: a node started
// against a version-one or version-seven genesis and a version-eight engine
// refuses at `init_chain` rather than at the first block.
//
// **The neighbour that matters here is version seven's, not version one's.** A
// version-one genesis and a version-eight one are unlikely to be confused by an
// operator; a version-seven one is what every node on this chain was running
// yesterday, and it is the string a stale deployment would still be sending.
constexpr std::uint8_t kExpectedAppStateV8[] = {
    '"', 'p', 'r', 'o', 't', 'o', 'c', 'o', 'l', '-',
    's', 't', 'a', 'c', 'k', '-', 'v', '8', '"',
};

}  // namespace

namespace internal_v8 {

bool within_block_bounds(std::span<const v8::Bytes> transactions) noexcept {
  if (transactions.size() > kMaximumBlockInputsV8) return false;
  std::size_t total = 0;
  for (const auto& transaction : transactions) {
    if (transaction.size() > kMaximumTransactionBytes ||
        transaction.size() > kMaximumBlockBytes - total) {
      return false;
    }
    total += transaction.size();
  }
  return true;
}

ApplicationError head_error(
    const protocol::storage::SQLiteV8HeadResult& result) noexcept {
  return std::holds_alternative<SQLiteLedgerV8Error>(result)
             ? ApplicationError::storage_failure
             : ApplicationError::internal_failure;
}

}  // namespace internal_v8

static_assert(std::is_nothrow_move_constructible_v<ApplicationV8>);
static_assert(std::is_nothrow_destructible_v<ApplicationV8>);

ApplicationV8::ApplicationV8(std::unique_ptr<Impl> implementation) noexcept
    : implementation_(std::move(implementation)) {}

ApplicationV8::~ApplicationV8() noexcept = default;
ApplicationV8::ApplicationV8(ApplicationV8&&) noexcept = default;

ApplicationV8Result make_application_v8(
    protocol::storage::SQLiteLedgerV8 ledger) {
  auto head = ledger.read_head();
  if (!std::holds_alternative<LedgerHeadV8>(head)) {
    return ApplicationV8Result{
        std::variant<ApplicationV8, ApplicationError>(
            std::in_place_type<ApplicationError>,
            internal_v8::head_error(head)),
    };
  }
  const auto& initial = std::get<LedgerHeadV8>(head);
  const auto chain_id = initial.ledger.chain_id;
  // A store already past genesis was initialised by a previous process, and
  // `init_chain` is called once in a chain's life rather than once per process.
  const bool ready = initial.ledger.height != 0;
  auto verify = ledger.verifier();
  return ApplicationV8Result{
      std::variant<ApplicationV8, ApplicationError>(
          std::in_place_type<ApplicationV8>,
          ApplicationV8(std::make_unique<ApplicationV8::Impl>(
              std::move(ledger), chain_id, std::move(verify), ready))),
  };
}

InfoResultV8 ApplicationV8::info() const {
  const std::lock_guard<std::mutex> lock(implementation_->mutex);
  if (implementation_->terminal) return ApplicationError::sequence_failure;
  auto head = implementation_->ledger.read_head();
  if (!std::holds_alternative<LedgerHeadV8>(head)) {
    return internal_v8::head_error(head);
  }
  const auto& durable = std::get<LedgerHeadV8>(head);
  return ApplicationInfoV8{
      kApplicationProtocolVersionV8,
      durable.ledger.height,
      durable.state_root,
  };
}

InitChainResultV8 ApplicationV8::init_chain(
    const v8::Octets32& chain_id, std::uint64_t initial_height,
    std::span<const std::uint8_t> app_state) {
  const std::lock_guard<std::mutex> lock(implementation_->mutex);
  if (implementation_->terminal) return ApplicationError::sequence_failure;
  auto head = implementation_->ledger.read_head();
  if (!std::holds_alternative<LedgerHeadV8>(head)) {
    return implementation_->fail(internal_v8::head_error(head));
  }
  const auto& durable = std::get<LedgerHeadV8>(head);
  if (durable.ledger.height != 0) {
    return implementation_->fail(ApplicationError::sequence_failure);
  }
  if (chain_id != implementation_->chain_id || initial_height != 1 ||
      !std::ranges::equal(app_state, kExpectedAppStateV8)) {
    return implementation_->fail(ApplicationError::invalid_request);
  }
  implementation_->ready = true;
  return durable.state_root;
}

TransactionCheckResultV8 ApplicationV8::check_transaction(
    std::span<const std::uint8_t> raw_transaction) const {
  const std::lock_guard<std::mutex> lock(implementation_->mutex);
  if (implementation_->terminal || !implementation_->ready) {
    return ApplicationError::sequence_failure;
  }
  if (raw_transaction.size() > kMaximumTransactionBytes) {
    return ApplicationError::invalid_request;
  }
  // Admission only. Whether a transaction *succeeds* depends on the state it
  // meets, and a mempool check that executed would be answering a question
  // about a height nobody has proposed yet.
  const auto admitted = v8::admit(raw_transaction, implementation_->chain_id,
                                  implementation_->verify);
  if (!admitted.admitted()) {
    return TransactionResult{application_code(*admitted.error), {}};
  }
  return TransactionResult{0, {}};
}

PrepareProposalResultV8 ApplicationV8::prepare_proposal(
    std::int64_t maximum_transaction_bytes,
    std::span<const v8::Bytes> transactions) const {
  const std::lock_guard<std::mutex> lock(implementation_->mutex);
  if (implementation_->terminal || !implementation_->ready ||
      implementation_->stage) {
    return ApplicationError::sequence_failure;
  }
  if (maximum_transaction_bytes < 0) return ApplicationError::invalid_request;
  const auto maximum = std::min<std::uint64_t>(
      static_cast<std::uint64_t>(maximum_transaction_bytes), kMaximumBlockBytes);

  // The order CometBFT handed us is the order we keep. Reordering is a policy
  // with economic consequences and nothing in the accepted contracts asks for
  // one, so the proposal is a prefix of what arrived.
  PreparedProposal result;
  result.transactions.reserve(
      std::min(transactions.size(), kMaximumBlockInputsV8));
  std::uint64_t total = 0;
  for (const auto& transaction : transactions) {
    if (result.transactions.size() == kMaximumBlockInputsV8 ||
        transaction.size() > kMaximumTransactionBytes ||
        transaction.size() > maximum - total) {
      break;
    }
    total += transaction.size();
    result.transactions.push_back(transaction);
  }
  return result;
}

ProcessProposalResultV8 ApplicationV8::process_proposal(
    std::uint64_t height, std::span<const v8::Bytes> transactions) const {
  const std::lock_guard<std::mutex> lock(implementation_->mutex);
  if (implementation_->terminal || !implementation_->ready ||
      implementation_->stage) {
    return ApplicationError::sequence_failure;
  }
  auto head = implementation_->ledger.read_head();
  if (!std::holds_alternative<LedgerHeadV8>(head)) {
    return internal_v8::head_error(head);
  }
  auto durable = std::get<LedgerHeadV8>(std::move(head));
  if (durable.ledger.height >= kMaximumAdapterHeight ||
      height != durable.ledger.height + 1 ||
      !internal_v8::within_block_bounds(transactions)) {
    return false;
  }
  // Execute it. `execute_block` rejects some blocks whole — an invariant
  // failure, a conservation failure, an admitted count past its bound — and a
  // block this node cannot execute must be voted against here rather than
  // accepted and then fatal at `finalize_block`. The candidate is a copy and
  // nothing is written.
  // **No uptime schedule and no `BlockOrder`.** Version eight's prologue
  // derives the schedule, so this layer has nothing left to supply — which is
  // what closes ADR 0058's owed item rather than satisfying it.
  auto candidate = std::move(durable.ledger);
  return v8::execute_block(candidate, transactions, implementation_->verify)
      .has_value();
}

}  // namespace protocol::application
