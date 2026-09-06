#pragma once

// The version-eight application layer: what turns the owning store into
// something a consensus engine can drive.
//
// The seven operations are the ones an ABCI adapter needs, and they are version
// one's — `protocol::application::ApplicationV1` over `SQLiteLedger` — with the
// version-eight kernel and store underneath. **The sequencing rules are the
// substance.** CometBFT calls `finalize_block` and `commit` separately while
// `SQLiteLedgerV8` writes the head and the block row together, so
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
//
// **What version eight changes here is what this layer no longer has to
// supply.** ADR 0058 recorded, as owed, that version seven's application passes
// a null uptime schedule, so a chain driven entirely through `ApplicationV7`
// writes no cycle assignment record and accrues nothing to any seat. Version
// eight's prologue derives the schedule from the seat table and the window
// records, so the parameter is gone and the owed item is closed rather than
// satisfied — there is nothing left for a node to be given a different answer
// about.
//
// It costs something, and the cost is `process_proposal`'s. Under version eight
// a block audits every in-scope seat at every height, so executing a proposal
// against a candidate copy is one selection digest per in-scope seat rather
// than, at most heights, nothing at all. That is the price of voting against a
// block this node cannot execute instead of accepting it and being fatal at
// `finalize_block`, and ADR 0058 already accepted it when it was cheaper.

#include "protocol/application/application_v1.hpp"
#include "protocol/storage/sqlite_ledger_v8.hpp"
#include "protocol/v8/ledger.hpp"

#include <cstdint>
#include <memory>
#include <span>
#include <variant>
#include <vector>

namespace protocol::application {

inline constexpr std::uint64_t kApplicationProtocolVersionV8 = 8;

// Version eight's own bound on raw inputs is the kernel's. The byte bounds are
// version one's and are not version-specific: they bound what a peer may make
// this process allocate before any kernel sees it.
inline constexpr std::size_t kMaximumBlockInputsV8 = protocol::v8::kMaxRawInputs;

// The application response code for one transaction. Admission failures keep
// their own small numbers and execution results are offset, so a reader can
// tell "never entered the block" from "entered and refused" without a second
// field. It is the scheme `application_code` already uses for version one.
constexpr std::uint32_t application_code(protocol::v8::Result result) noexcept {
  const auto value = static_cast<std::uint32_t>(result);
  return value == 0 ? 0 : 256U + value;
}

struct ApplicationInfoV8 {
  std::uint64_t application_version = 0;
  std::uint64_t height = 0;
  protocol::v8::Hash state_root{};

  bool operator==(const ApplicationInfoV8&) const = default;
};

struct FinalizedBlockV8 {
  protocol::v8::Hash state_root{};
  protocol::v8::Hash block_id{};
  std::vector<TransactionResult> transaction_results;

  bool operator==(const FinalizedBlockV8&) const = default;
};

struct CommittedHeadV8 {
  std::uint64_t height = 0;
  protocol::v8::Hash state_root{};

  bool operator==(const CommittedHeadV8&) const = default;
};

using InfoResultV8 = std::variant<ApplicationInfoV8, ApplicationError>;
using InitChainResultV8 = std::variant<protocol::v8::Hash, ApplicationError>;
using TransactionCheckResultV8 =
    std::variant<TransactionResult, ApplicationError>;
using PrepareProposalResultV8 = std::variant<PreparedProposal, ApplicationError>;
using ProcessProposalResultV8 = std::variant<bool, ApplicationError>;
using FinalizeBlockResultV8 = std::variant<FinalizedBlockV8, ApplicationError>;
using CommitResultV8 = std::variant<CommittedHeadV8, ApplicationError>;

struct ApplicationV8Result;

class ApplicationV8 {
 public:
  ~ApplicationV8() noexcept;
  ApplicationV8(ApplicationV8&&) noexcept;

  ApplicationV8(const ApplicationV8&) = delete;
  ApplicationV8& operator=(const ApplicationV8&) = delete;
  ApplicationV8& operator=(ApplicationV8&&) = delete;

  InfoResultV8 info() const;
  InitChainResultV8 init_chain(const protocol::v8::Octets32& chain_id,
                               std::uint64_t initial_height,
                               std::span<const std::uint8_t> app_state);
  TransactionCheckResultV8 check_transaction(
      std::span<const std::uint8_t> raw_transaction) const;
  PrepareProposalResultV8 prepare_proposal(
      std::int64_t maximum_transaction_bytes,
      std::span<const protocol::v8::Bytes> transactions) const;
  // Unlike version one's, this executes the block against a candidate copy of
  // the head. `execute_block` has whole-block rejections version one's kernel
  // does not, and a block this node cannot execute must be voted against rather
  // than accepted and then fatal at `finalize_block`. It costs a copy of the
  // head and one execution, and it writes nothing.
  ProcessProposalResultV8 process_proposal(
      std::uint64_t height,
      std::span<const protocol::v8::Bytes> transactions) const;
  FinalizeBlockResultV8 finalize_block(
      std::uint64_t height,
      std::span<const protocol::v8::Bytes> transactions);
  CommitResultV8 commit();

 private:
  struct Impl;

  explicit ApplicationV8(std::unique_ptr<Impl> implementation) noexcept;

  friend ApplicationV8Result make_application_v8(
      protocol::storage::SQLiteLedgerV8 ledger);

  std::unique_ptr<Impl> implementation_;
};

struct ApplicationV8Result {
  std::variant<ApplicationV8, ApplicationError> result;
};

// The application takes the store by value: one local writer is ADR 0007's
// contract, and an application that did not own its store could not promise
// that the head it staged against is the head it commits to.
ApplicationV8Result make_application_v8(
    protocol::storage::SQLiteLedgerV8 ledger);

}  // namespace protocol::application
