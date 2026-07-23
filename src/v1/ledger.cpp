#include "protocol/v1/ledger.hpp"

#include "commitments.hpp"
#include "execution.hpp"
#include "genesis.hpp"
#include "protocol/v1/admission.hpp"

#include <limits>
#include <optional>
#include <type_traits>
#include <utility>
#include <variant>

namespace protocol::v1 {
namespace {

constexpr std::size_t kMaximumBlockInputs = 65'535;

}  // namespace

static_assert(std::is_nothrow_move_constructible_v<State>);
static_assert(std::is_nothrow_move_assignable_v<State>);
static_assert(std::is_nothrow_move_constructible_v<BlockCommit>);

Ledger::Ledger(State state) noexcept : state_(std::move(state)) {}

LedgerLoad load_genesis(
    std::span<const std::uint8_t> canonical_genesis) {
  auto decoded = internal::decode_genesis(canonical_genesis);
  if (std::holds_alternative<GenesisError>(decoded)) {
    return LedgerLoad{
        std::variant<Ledger, GenesisError>(
            std::in_place_type<GenesisError>,
            std::get<GenesisError>(decoded)),
    };
  }
  return LedgerLoad{
      std::variant<Ledger, GenesisError>(
          std::in_place_type<Ledger>,
          Ledger(std::get<State>(std::move(decoded)))),
  };
}

LedgerRestore restore_ledger(
    State state,
    const Parameters& expected_parameters,
    const StateRoot& expected_state_root) {
  const auto commitment = internal::state_root(state);
  if (std::holds_alternative<internal::StateError>(commitment)) {
    return LedgerRestore{
        std::variant<Ledger, LedgerRestoreError>(
            std::in_place_type<LedgerRestoreError>,
            LedgerRestoreError::invalid_state),
    };
  }
  if (state.parameters != expected_parameters) {
    return LedgerRestore{
        std::variant<Ledger, LedgerRestoreError>(
            std::in_place_type<LedgerRestoreError>,
            LedgerRestoreError::immutable_parameters_mismatch),
    };
  }
  if (std::get<StateRoot>(commitment) != expected_state_root) {
    return LedgerRestore{
        std::variant<Ledger, LedgerRestoreError>(
            std::in_place_type<LedgerRestoreError>,
            LedgerRestoreError::state_root_mismatch),
    };
  }
  return LedgerRestore{
      std::variant<Ledger, LedgerRestoreError>(
          std::in_place_type<Ledger>, Ledger(std::move(state))),
  };
}

std::variant<StateRoot, BlockError> Ledger::current_state_root() const {
  auto commitment = internal::state_root(state_);
  if (std::holds_alternative<internal::StateError>(commitment)) {
    return BlockError::invalid_state;
  }
  return std::get<StateRoot>(std::move(commitment));
}

std::variant<BlockCommit, BlockError> Ledger::apply_block(
    std::uint64_t height,
    std::span<const Bytes> raw_transactions) {
  if (raw_transactions.size() > kMaximumBlockInputs) {
    return BlockError::too_many_inputs;
  }

  auto previous_commitment = internal::state_root(state_);
  if (std::holds_alternative<internal::StateError>(previous_commitment)) {
    return BlockError::invalid_state;
  }
  if (state_.height == std::numeric_limits<std::uint64_t>::max()) {
    return BlockError::height_exhausted;
  }
  if (height != state_.height + 1) {
    return BlockError::invalid_height;
  }

  State tentative = state_;
  std::vector<std::optional<AdmissionError>> admissions;
  std::vector<TransactionId> transaction_ids;
  std::vector<Receipt> receipts;
  std::vector<Bytes> encoded_receipts;
  admissions.reserve(raw_transactions.size());
  transaction_ids.reserve(raw_transactions.size());
  receipts.reserve(raw_transactions.size());
  encoded_receipts.reserve(raw_transactions.size());

  for (const auto& raw_transaction : raw_transactions) {
    auto admission =
        admit_transfer(raw_transaction, tentative.parameters.chain_id);
    if (std::holds_alternative<AdmissionError>(admission)) {
      admissions.emplace_back(std::get<AdmissionError>(admission));
      continue;
    }
    admissions.emplace_back(std::nullopt);

    const auto& transfer = std::get<Transfer>(admission);
    transaction_ids.push_back(transfer.transaction_id);
    auto execution = internal::execute_transfer(transfer, tentative, height);
    if (std::holds_alternative<internal::ExecutionError>(execution)) {
      return BlockError::invariant_failure;
    }

    auto receipt = std::get<Receipt>(std::move(execution));
    auto encoded =
        internal::encode_receipt(receipt, tentative.parameters.fixed_fee);
    if (!encoded) {
      return BlockError::invariant_failure;
    }
    receipts.push_back(std::move(receipt));
    encoded_receipts.push_back(std::move(*encoded));
  }

  tentative.height = height;
  auto resulting_commitment = internal::state_root(tentative);
  if (std::holds_alternative<internal::StateError>(resulting_commitment)) {
    return BlockError::invariant_failure;
  }

  const auto previous_state_root =
      std::get<StateRoot>(std::move(previous_commitment));
  const auto resulting_state_root =
      std::get<StateRoot>(std::move(resulting_commitment));
  const auto committed_transaction_root =
      internal::transaction_root(transaction_ids);
  auto header = internal::encode_block_header(
      tentative.parameters.chain_id, height, previous_state_root,
      committed_transaction_root, resulting_state_root,
      static_cast<std::uint32_t>(transaction_ids.size()));
  auto committed_block_id = internal::block_id(header);
  if (!committed_block_id) {
    return BlockError::invariant_failure;
  }

  std::variant<BlockCommit, BlockError> result(
      std::in_place_type<BlockCommit>,
      BlockCommit{
          height,
          std::move(admissions),
          std::move(transaction_ids),
          std::move(receipts),
          std::move(encoded_receipts),
          previous_state_root,
          committed_transaction_root,
          resulting_state_root,
          std::move(header),
          std::move(*committed_block_id),
      });

  state_ = std::move(tentative);
  return result;
}

}  // namespace protocol::v1
