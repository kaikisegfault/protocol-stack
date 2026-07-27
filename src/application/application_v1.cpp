#include "protocol/application/application_v1.hpp"

#include "application_v1_internal.hpp"

#include "protocol/v1/admission.hpp"

#include <algorithm>
#include <type_traits>
#include <utility>

namespace protocol::application {
namespace {

using protocol::storage::LedgerHead;
using protocol::storage::SQLiteLedgerError;
using protocol::v1::AdmissionError;
using protocol::v1::Bytes;

constexpr std::uint8_t kExpectedAppState[] = {
    '"', 'p', 'r', 'o', 't', 'o', 'c', 'o', 'l', '-',
    's', 't', 'a', 'c', 'k', '-', 'v', '1', '"',
};

}  // namespace

namespace internal {

bool within_block_bounds(
    std::span<const Bytes> transactions) noexcept {
  if (transactions.size() > kMaximumBlockInputs) return false;
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
    const protocol::storage::SQLiteHeadResult& result) noexcept {
  return std::holds_alternative<SQLiteLedgerError>(result)
             ? ApplicationError::storage_failure
             : ApplicationError::internal_failure;
}

}  // namespace internal

static_assert(std::is_nothrow_move_constructible_v<ApplicationV1>);
static_assert(std::is_nothrow_destructible_v<ApplicationV1>);

ApplicationV1::ApplicationV1(
    std::unique_ptr<Impl> implementation) noexcept
    : implementation_(std::move(implementation)) {}

ApplicationV1::~ApplicationV1() noexcept = default;
ApplicationV1::ApplicationV1(ApplicationV1&&) noexcept = default;

ApplicationV1Result make_application_v1(
    protocol::storage::SQLiteLedger ledger) {
  auto head = ledger.read_head();
  if (!std::holds_alternative<LedgerHead>(head)) {
    return ApplicationV1Result{
        std::variant<ApplicationV1, ApplicationError>(
            std::in_place_type<ApplicationError>,
            internal::head_error(head)),
    };
  }
  auto initial = std::get<LedgerHead>(std::move(head));
  return ApplicationV1Result{
      std::variant<ApplicationV1, ApplicationError>(
          std::in_place_type<ApplicationV1>,
          ApplicationV1(std::make_unique<ApplicationV1::Impl>(
              std::move(ledger), initial.state.parameters,
              initial.state.height != 0))),
  };
}

InfoResult ApplicationV1::info() const {
  const std::lock_guard<std::mutex> lock(implementation_->mutex);
  if (implementation_->terminal) {
    return ApplicationError::sequence_failure;
  }
  auto head = implementation_->ledger.read_head();
  if (!std::holds_alternative<LedgerHead>(head)) {
    return internal::head_error(head);
  }
  const auto& durable = std::get<LedgerHead>(head);
  return ApplicationInfo{
      kApplicationProtocolVersion,
      durable.state.height,
      durable.state_root,
  };
}

EmptyResult ApplicationV1::init_chain(
    const protocol::v1::ChainId& chain_id,
    std::uint64_t initial_height,
    std::span<const std::uint8_t> app_state) {
  const std::lock_guard<std::mutex> lock(implementation_->mutex);
  if (implementation_->terminal) {
    return ApplicationError::sequence_failure;
  }
  auto head = implementation_->ledger.read_head();
  if (!std::holds_alternative<LedgerHead>(head)) {
    return implementation_->fail(internal::head_error(head));
  }
  if (std::get<LedgerHead>(head).state.height != 0) {
    return implementation_->fail(ApplicationError::sequence_failure);
  }
  if (chain_id != implementation_->parameters.chain_id ||
      initial_height != 1 ||
      !std::ranges::equal(app_state, kExpectedAppState)) {
    return implementation_->fail(ApplicationError::invalid_request);
  }
  implementation_->ready = true;
  return std::monostate{};
}

TransactionCheckResult ApplicationV1::check_transaction(
    std::span<const std::uint8_t> raw_transaction) const {
  const std::lock_guard<std::mutex> lock(implementation_->mutex);
  if (implementation_->terminal || !implementation_->ready) {
    return ApplicationError::sequence_failure;
  }
  if (raw_transaction.size() > kMaximumTransactionBytes) {
    return ApplicationError::invalid_request;
  }
  const auto admitted = protocol::v1::admit_transfer(
      raw_transaction, implementation_->parameters.chain_id);
  if (std::holds_alternative<AdmissionError>(admitted)) {
    return TransactionResult{
        application_code(std::get<AdmissionError>(admitted)), {}};
  }
  return TransactionResult{0, {}};
}

PrepareProposalResult ApplicationV1::prepare_proposal(
    std::int64_t maximum_transaction_bytes,
    std::span<const Bytes> transactions) const {
  const std::lock_guard<std::mutex> lock(implementation_->mutex);
  if (implementation_->terminal || !implementation_->ready ||
      implementation_->stage) {
    return ApplicationError::sequence_failure;
  }
  if (maximum_transaction_bytes < 0) {
    return ApplicationError::invalid_request;
  }
  const auto maximum = std::min<std::uint64_t>(
      static_cast<std::uint64_t>(maximum_transaction_bytes),
      kMaximumBlockBytes);

  PreparedProposal result;
  result.transactions.reserve(
      std::min(transactions.size(), kMaximumBlockInputs));
  std::uint64_t total = 0;
  for (const auto& transaction : transactions) {
    if (result.transactions.size() == kMaximumBlockInputs ||
        transaction.size() > kMaximumTransactionBytes ||
        transaction.size() > maximum - total) {
      break;
    }
    total += transaction.size();
    result.transactions.push_back(transaction);
  }
  return result;
}

ProcessProposalResult ApplicationV1::process_proposal(
    std::uint64_t height,
    std::span<const Bytes> transactions) const {
  const std::lock_guard<std::mutex> lock(implementation_->mutex);
  if (implementation_->terminal || !implementation_->ready ||
      implementation_->stage) {
    return ApplicationError::sequence_failure;
  }
  auto head = implementation_->ledger.read_head();
  if (!std::holds_alternative<LedgerHead>(head)) {
    return internal::head_error(head);
  }
  const auto durable_height = std::get<LedgerHead>(head).state.height;
  const auto valid_height =
      durable_height < kMaximumAdapterHeight &&
      height == durable_height + 1 &&
      height <= kMaximumAdapterHeight;
  return valid_height && internal::within_block_bounds(transactions);
}

}  // namespace protocol::application
