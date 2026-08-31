#pragma once

// The version-seven application layer: what turns the owning store into
// something a consensus engine can drive.
//
// The seven operations are the ones an ABCI adapter needs, and they are version
// one's — `protocol::application::ApplicationV1` over `SQLiteLedger` — with the
// version-seven kernel and store underneath. **The sequencing rules are the
// substance.** CometBFT calls `finalize_block` and `commit` separately while
// `SQLiteLedgerV7` writes the head and the block row together, so
// `finalize_block` is pure: it copies the durable head, executes the block in
// memory, writes nothing, and stages what it produced. `commit` replays that
// block through the store and requires the store to reproduce exactly what was
// staged. **That equality is the whole safety argument**: it is what makes "the
// root this node told the network" and "the root this node persisted" one fact
// rather than two.
//
// **Any refusal after the chain is ready is terminal.** A deterministic
// application that has told the network one thing and found another cannot
// continue and be trusted, so it stops answering rather than guess which of the
// two was right.

#include "protocol/application/application_v1.hpp"
#include "protocol/storage/sqlite_ledger_v7.hpp"
#include "protocol/v7/ledger.hpp"

#include <cstdint>
#include <memory>
#include <span>
#include <variant>
#include <vector>

namespace protocol::application {

inline constexpr std::uint64_t kApplicationProtocolVersionV7 = 7;

// Version seven's own bound on raw inputs is the kernel's. The byte bounds are
// version one's and are not version-specific: they bound what a peer may make
// this process allocate before any kernel sees it.
inline constexpr std::size_t kMaximumBlockInputsV7 = protocol::v7::kMaxRawInputs;

// The application response code for one transaction. Admission failures keep
// their own small numbers and execution results are offset, so a reader can
// tell "never entered the block" from "entered and refused" without a second
// field. It is the scheme `application_code` already uses for version one.
constexpr std::uint32_t application_code(protocol::v7::Result result) noexcept {
  const auto value = static_cast<std::uint32_t>(result);
  return value == 0 ? 0 : 256U + value;
}

struct ApplicationInfoV7 {
  std::uint64_t application_version = 0;
  std::uint64_t height = 0;
  protocol::v7::Hash state_root{};

  bool operator==(const ApplicationInfoV7&) const = default;
};

struct FinalizedBlockV7 {
  protocol::v7::Hash state_root{};
  protocol::v7::Hash block_id{};
  std::vector<TransactionResult> transaction_results;

  bool operator==(const FinalizedBlockV7&) const = default;
};

struct CommittedHeadV7 {
  std::uint64_t height = 0;
  protocol::v7::Hash state_root{};

  bool operator==(const CommittedHeadV7&) const = default;
};

using InfoResultV7 = std::variant<ApplicationInfoV7, ApplicationError>;
using InitChainResultV7 = std::variant<protocol::v7::Hash, ApplicationError>;
using TransactionCheckResultV7 =
    std::variant<TransactionResult, ApplicationError>;
using PrepareProposalResultV7 = std::variant<PreparedProposal, ApplicationError>;
using ProcessProposalResultV7 = std::variant<bool, ApplicationError>;
using FinalizeBlockResultV7 = std::variant<FinalizedBlockV7, ApplicationError>;
using CommitResultV7 = std::variant<CommittedHeadV7, ApplicationError>;

struct ApplicationV7Result;

class ApplicationV7 {
 public:
  ~ApplicationV7() noexcept;
  ApplicationV7(ApplicationV7&&) noexcept;

  ApplicationV7(const ApplicationV7&) = delete;
  ApplicationV7& operator=(const ApplicationV7&) = delete;
  ApplicationV7& operator=(ApplicationV7&&) = delete;

  InfoResultV7 info() const;
  InitChainResultV7 init_chain(const protocol::v7::Octets32& chain_id,
                               std::uint64_t initial_height,
                               std::span<const std::uint8_t> app_state);
  TransactionCheckResultV7 check_transaction(
      std::span<const std::uint8_t> raw_transaction) const;
  PrepareProposalResultV7 prepare_proposal(
      std::int64_t maximum_transaction_bytes,
      std::span<const protocol::v7::Bytes> transactions) const;
  // Unlike version one's, this executes the block against a candidate copy of
  // the head. `execute_block` has whole-block rejections version one's kernel
  // does not, and a block this node cannot execute must be voted against rather
  // than accepted and then fatal at `finalize_block`. It costs a copy of the
  // head and one execution, and it writes nothing.
  ProcessProposalResultV7 process_proposal(
      std::uint64_t height,
      std::span<const protocol::v7::Bytes> transactions) const;
  FinalizeBlockResultV7 finalize_block(
      std::uint64_t height,
      std::span<const protocol::v7::Bytes> transactions);
  CommitResultV7 commit();

 private:
  struct Impl;

  explicit ApplicationV7(std::unique_ptr<Impl> implementation) noexcept;

  friend ApplicationV7Result make_application_v7(
      protocol::storage::SQLiteLedgerV7 ledger);

  std::unique_ptr<Impl> implementation_;
};

struct ApplicationV7Result {
  std::variant<ApplicationV7, ApplicationError> result;
};

// The application takes the store by value: one local writer is ADR 0007's
// contract, and an application that did not own its store could not promise
// that the head it staged against is the head it commits to.
ApplicationV7Result make_application_v7(
    protocol::storage::SQLiteLedgerV7 ledger);

}  // namespace protocol::application
