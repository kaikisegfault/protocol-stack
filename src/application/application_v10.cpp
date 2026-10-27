// The version-ten application layer: construction, the read-only operations,
// and the two proposal operations.
//
// `application_block_v10.cpp` holds `finalize_block` and `commit`, which is where
// the staged-then-replayed equality lives.
//
// **The clock appears exactly once in this file**, in `process_proposal`, and it
// appears nowhere in the other one.

#include "protocol/application/application_v10.hpp"

#include "application_v10_internal.hpp"

#include <algorithm>
#include <type_traits>
#include <utility>

namespace protocol::application {
namespace {

namespace v10 = protocol::v10;
using protocol::storage::LedgerHeadV10;
using protocol::storage::SQLiteLedgerV10Error;

// The chain identity a genesis produces is not the string an operator types into
// CometBFT, so the app state is what pins the two together.
//
// **The neighbour that matters is version nine's**, which is what every node on
// a network runs until ADR 0104's step 6 and the string a stale deployment would
// still be sending. Version ten's is one octet longer, so the comparison refuses
// it on length before it reads a byte.
constexpr std::uint8_t kExpectedAppStateV10[] = {
    '"', 'p', 'r', 'o', 't', 'o', 'c', 'o', 'l', '-',
    's', 't', 'a', 'c', 'k', '-', 'v', '1', '0', '"',
};

}  // namespace

namespace internal_v10 {

bool within_block_bounds(std::span<const v10::Bytes> transactions) noexcept {
  if (transactions.size() > kMaximumBlockInputsV10) return false;
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
    const protocol::storage::SQLiteV10HeadResult& result) noexcept {
  return std::holds_alternative<SQLiteLedgerV10Error>(result)
             ? ApplicationError::storage_failure
             : ApplicationError::internal_failure;
}

}  // namespace internal_v10

static_assert(std::is_nothrow_move_constructible_v<ApplicationV10>);
static_assert(std::is_nothrow_destructible_v<ApplicationV10>);

ApplicationV10::ApplicationV10(std::unique_ptr<Impl> implementation) noexcept
    : implementation_(std::move(implementation)) {}

ApplicationV10::~ApplicationV10() noexcept = default;
ApplicationV10::ApplicationV10(ApplicationV10&&) noexcept = default;

ApplicationV10Result make_application_v10(
    protocol::storage::SQLiteLedgerV10 ledger, ClockSourceV10 clock) {
  // **A deployment that cannot read a clock fails to start.** The alternative is
  // a machine that votes on an assumed value, which is worse than one that does
  // not vote: an assumed clock makes C5 pass on every proposal, silently.
  if (!clock) {
    return ApplicationV10Result{
        std::variant<ApplicationV10, ApplicationError>(
            std::in_place_type<ApplicationError>,
            ApplicationError::invalid_request),
    };
  }
  auto head = ledger.read_head();
  if (!std::holds_alternative<LedgerHeadV10>(head)) {
    return ApplicationV10Result{
        std::variant<ApplicationV10, ApplicationError>(
            std::in_place_type<ApplicationError>,
            internal_v10::head_error(head)),
    };
  }
  const auto& initial = std::get<LedgerHeadV10>(head);
  const auto chain_id = initial.ledger.chain_id;
  // A store already past genesis was initialised by a previous process, and
  // `init_chain` is called once in a chain's life rather than once per process.
  const bool ready = initial.ledger.height != 0;
  auto verify = ledger.verifier();
  return ApplicationV10Result{
      std::variant<ApplicationV10, ApplicationError>(
          std::in_place_type<ApplicationV10>,
          ApplicationV10(std::make_unique<ApplicationV10::Impl>(
              std::move(ledger), chain_id, std::move(verify), std::move(clock),
              ready))),
  };
}

InfoResultV10 ApplicationV10::info() const {
  const std::lock_guard<std::mutex> lock(implementation_->mutex);
  if (implementation_->terminal) return ApplicationError::sequence_failure;
  auto head = implementation_->ledger.read_head();
  if (!std::holds_alternative<LedgerHeadV10>(head)) {
    return internal_v10::head_error(head);
  }
  const auto& durable = std::get<LedgerHeadV10>(head);
  return ApplicationInfoV10{
      kApplicationProtocolVersionV10,
      durable.ledger.height,
      durable.ledger.timestamp,
      durable.state_root,
  };
}

InitChainResultV10 ApplicationV10::init_chain(
    const v10::Octets32& chain_id, std::uint64_t initial_height,
    std::uint64_t genesis_timestamp, std::span<const std::uint8_t> app_state) {
  const std::lock_guard<std::mutex> lock(implementation_->mutex);
  if (implementation_->terminal) return ApplicationError::sequence_failure;
  auto head = implementation_->ledger.read_head();
  if (!std::holds_alternative<LedgerHeadV10>(head)) {
    return implementation_->fail(internal_v10::head_error(head));
  }
  const auto& durable = std::get<LedgerHeadV10>(head);
  if (durable.ledger.height != 0) {
    return implementation_->fail(ApplicationError::sequence_failure);
  }
  // **Four values, and the fourth is read from the head rather than from a
  // stored copy.** At height zero the head's stamp is the genesis stamp by
  // construction, so this compares the operator's claim against the validated
  // canonical genesis the store restored — with no second copy to drift.
  //
  // C1 is already satisfied by that genesis having been loaded at all, and no
  // clock is read: a tolerance here would make a chain un-initialisable one
  // tolerance-width after its genesis was written.
  if (chain_id != implementation_->chain_id || initial_height != 1 ||
      genesis_timestamp != durable.ledger.timestamp ||
      !std::ranges::equal(app_state, kExpectedAppStateV10)) {
    return implementation_->fail(ApplicationError::invalid_request);
  }
  implementation_->ready = true;
  return durable.state_root;
}

TransactionCheckResultV10 ApplicationV10::check_transaction(
    std::span<const std::uint8_t> raw_transaction) const {
  const std::lock_guard<std::mutex> lock(implementation_->mutex);
  if (implementation_->terminal || !implementation_->ready) {
    return ApplicationError::sequence_failure;
  }
  if (raw_transaction.size() > kMaximumTransactionBytes) {
    return ApplicationError::invalid_request;
  }
  // **Admission has no timestamp input and reads no clock.** It is exact
  // decoding, chain comparison, sender derivation, and strict signature
  // verification, none of which reads a height, a state, or a clock. A kind-22
  // monthly pool mint is admitted here like any other: whether it succeeds
  // depends on the state it meets, which is `finalize_block`'s question.
  const auto admitted = v10::admit(raw_transaction, implementation_->chain_id,
                                  implementation_->verify);
  if (!admitted.admitted()) {
    return TransactionResult{application_code(*admitted.error), {}};
  }
  return TransactionResult{0, {}};
}

PrepareProposalResultV10 ApplicationV10::prepare_proposal(
    std::int64_t maximum_transaction_bytes,
    std::span<const v10::Bytes> transactions) const {
  const std::lock_guard<std::mutex> lock(implementation_->mutex);
  if (implementation_->terminal || !implementation_->ready ||
      implementation_->stage) {
    return ApplicationError::sequence_failure;
  }
  if (maximum_transaction_bytes < 0) return ApplicationError::invalid_request;
  const auto maximum = std::min<std::uint64_t>(
      static_cast<std::uint64_t>(maximum_transaction_bytes), kMaximumBlockBytes);

  // **This does not choose or report a timestamp, and the omission is a rule.**
  // Under CometBFT the block time is the engine's, produced by BFT time from vote
  // timestamps, and `economy-transition-v9` requires, as version ten carries, the
  // proposer's algorithm for choosing a value to stay unconstrained. An
  // application that selected the stamp would constrain exactly that and would
  // foreclose the deployment in which BFT time supplies it.
  PreparedProposal result;
  result.transactions.reserve(
      std::min(transactions.size(), kMaximumBlockInputsV10));
  std::uint64_t total = 0;
  for (const auto& transaction : transactions) {
    if (result.transactions.size() == kMaximumBlockInputsV10 ||
        transaction.size() > kMaximumTransactionBytes ||
        transaction.size() > maximum - total) {
      break;
    }
    total += transaction.size();
    result.transactions.push_back(transaction);
  }
  return result;
}

ProcessProposalResultV10 ApplicationV10::process_proposal(
    std::uint64_t height, std::uint64_t timestamp,
    std::span<const v10::Bytes> transactions) const {
  const std::lock_guard<std::mutex> lock(implementation_->mutex);
  // A staged block, a terminal application, or one not yet initialised describes
  // *this machine* rather than the proposal, so it is a sequence failure and not
  // a decision. That is version one's rule unchanged.
  if (implementation_->terminal || !implementation_->ready ||
      implementation_->stage) {
    return ApplicationError::sequence_failure;
  }
  auto head = implementation_->ledger.read_head();
  if (!std::holds_alternative<LedgerHeadV10>(head)) {
    return internal_v10::head_error(head);
  }
  auto durable = std::get<LedgerHeadV10>(std::move(head));

  // **The clock is read here and exactly here, once.** Reading it twice would
  // let two conditions of one evaluation disagree about the time.
  const auto observed = implementation_->clock();

  // **`calendar-v1`'s ordered conditions run before the resource bounds.** The
  // vote is identical under either order, so this decides only what is
  // *reported* — and therefore what is testable. The order is normative and
  // total, so a proposal failing both a bound and a timestamp rule reports what
  // `calendar-v1` says fires first.
  const v10::Head current{durable.ledger.height, durable.ledger.timestamp};
  if (durable.ledger.height >= kMaximumAdapterHeight) {
    return ProposalDecisionV10::height_not_next;
  }
  const auto condition =
      v10::accept_timestamp(current, height, timestamp, observed);
  if (condition != v10::TimestampCondition::accepted) {
    return decision_of(condition);
  }
  if (!internal_v10::within_block_bounds(transactions)) {
    return ProposalDecisionV10::resource_bound;
  }
  // Execute it against a candidate copy. `execute_block` rejects some blocks
  // whole, and a block this node cannot execute must be voted against here
  // rather than accepted and then fatal at `finalize_block`. Nothing is written.
  //
  // **The candidate carries the head's stamp**, so its C1 and C2 are already
  // satisfied by the time it runs and this decision can only mean an invariant,
  // conservation, or bound failure inside the block.
  auto candidate = std::move(durable.ledger);
  const auto executed = v10::execute_block(candidate, timestamp, transactions,
                                          implementation_->verify);
  return executed.has_value() ? ProposalDecisionV10::accepted
                              : ProposalDecisionV10::not_executable;
}

}  // namespace protocol::application
