#pragma once

#include "protocol/storage/sqlite_ledger.hpp"
#include "protocol/v1/types.hpp"

#include <cstddef>
#include <cstdint>
#include <memory>
#include <span>
#include <variant>
#include <vector>

namespace protocol::application {

inline constexpr std::uint64_t kApplicationProtocolVersion = 1;
inline constexpr std::size_t kMaximumTransactionBytes = 1'048'576;
inline constexpr std::size_t kMaximumBlockBytes = 16'777'216;
inline constexpr std::size_t kMaximumBlockInputs = 65'535;
inline constexpr std::uint64_t kMaximumAdapterHeight =
    9'223'372'036'854'775'807ULL;

enum class ApplicationError : std::uint16_t {
  invalid_request = 1,
  unsupported = 2,
  sequence_failure = 3,
  kernel_failure = 4,
  storage_failure = 5,
  internal_failure = 6,
};

constexpr std::uint32_t application_code(
    protocol::v1::AdmissionError error) noexcept {
  return static_cast<std::uint32_t>(error);
}

constexpr std::uint32_t application_code(
    protocol::v1::TransferResult result) noexcept {
  const auto value = static_cast<std::uint32_t>(result);
  return value == 0 ? 0 : 256U + value;
}

struct ApplicationInfo {
  std::uint64_t application_version;
  std::uint64_t height;
  protocol::v1::StateRoot state_root;

  bool operator==(const ApplicationInfo&) const = default;
};

struct TransactionResult {
  std::uint32_t code;
  protocol::v1::Bytes data;

  bool operator==(const TransactionResult&) const = default;
};

struct PreparedProposal {
  std::vector<protocol::v1::Bytes> transactions;

  bool operator==(const PreparedProposal&) const = default;
};

struct FinalizedBlock {
  protocol::v1::StateRoot state_root;
  std::vector<TransactionResult> transaction_results;

  bool operator==(const FinalizedBlock&) const = default;
};

struct CommittedHead {
  std::uint64_t height;
  protocol::v1::StateRoot state_root;

  bool operator==(const CommittedHead&) const = default;
};

using EmptyResult = std::variant<std::monostate, ApplicationError>;
using InfoResult = std::variant<ApplicationInfo, ApplicationError>;
using TransactionCheckResult =
    std::variant<TransactionResult, ApplicationError>;
using PrepareProposalResult =
    std::variant<PreparedProposal, ApplicationError>;
using ProcessProposalResult = std::variant<bool, ApplicationError>;
using FinalizeBlockResult =
    std::variant<FinalizedBlock, ApplicationError>;
using CommitResult = std::variant<CommittedHead, ApplicationError>;

struct ApplicationV1Result;

class ApplicationV1 {
 public:
  ~ApplicationV1() noexcept;
  ApplicationV1(ApplicationV1&&) noexcept;

  ApplicationV1(const ApplicationV1&) = delete;
  ApplicationV1& operator=(const ApplicationV1&) = delete;
  ApplicationV1& operator=(ApplicationV1&&) = delete;

  InfoResult info() const;
  EmptyResult init_chain(
      const protocol::v1::ChainId& chain_id,
      std::uint64_t initial_height,
      std::span<const std::uint8_t> app_state);
  TransactionCheckResult check_transaction(
      std::span<const std::uint8_t> raw_transaction) const;
  PrepareProposalResult prepare_proposal(
      std::int64_t maximum_transaction_bytes,
      std::span<const protocol::v1::Bytes> transactions) const;
  ProcessProposalResult process_proposal(
      std::uint64_t height,
      std::span<const protocol::v1::Bytes> transactions) const;
  FinalizeBlockResult finalize_block(
      std::uint64_t height,
      std::span<const protocol::v1::Bytes> transactions);
  CommitResult commit();

 private:
  struct Impl;

  explicit ApplicationV1(std::unique_ptr<Impl> implementation) noexcept;

  friend ApplicationV1Result make_application_v1(
      protocol::storage::SQLiteLedger ledger);

  std::unique_ptr<Impl> implementation_;
};

struct ApplicationV1Result {
  std::variant<ApplicationV1, ApplicationError> result;
};

ApplicationV1Result make_application_v1(
    protocol::storage::SQLiteLedger ledger);

}  // namespace protocol::application
