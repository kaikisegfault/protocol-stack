#pragma once

// What the version-seven application's two translation units share: the live
// state behind the class, the staged block, and the two bounds a peer's bytes
// are checked against before any kernel sees them.

#include "protocol/application/application_v7.hpp"

#include <mutex>
#include <optional>
#include <span>
#include <utility>
#include <vector>

namespace protocol::application {

struct ApplicationV7::Impl {
  // What `finalize_block` produced and `commit` must find again. The candidate
  // root and height are kept rather than the candidate ledger: the root commits
  // to the whole state, so comparing roots is comparing states, and holding a
  // second ledger would invite someone to commit *it* instead of replaying the
  // block.
  struct Stage {
    std::uint64_t height = 0;
    std::vector<protocol::v7::Bytes> transactions;
    protocol::storage::BlockCommitV7 commit;
    protocol::v7::Hash candidate_root{};
    FinalizedBlockV7 response;
  };

  protocol::storage::SQLiteLedgerV7 ledger;
  protocol::v7::Octets32 chain_id{};
  protocol::v7::SignatureVerifier verify;
  mutable std::mutex mutex;
  std::optional<Stage> stage;
  bool ready = false;
  bool terminal = false;

  Impl(protocol::storage::SQLiteLedgerV7 owned_ledger,
       protocol::v7::Octets32 immutable_chain_id,
       protocol::v7::SignatureVerifier verifier, bool is_ready) noexcept
      : ledger(std::move(owned_ledger)),
        chain_id(immutable_chain_id),
        verify(std::move(verifier)),
        ready(is_ready) {}

  // Every refusal after the chain is ready latches. A deterministic application
  // that told the network one thing and found another cannot continue and be
  // trusted.
  ApplicationError fail(ApplicationError error) noexcept {
    terminal = true;
    return error;
  }
};

namespace internal_v7 {

bool within_block_bounds(
    std::span<const protocol::v7::Bytes> transactions) noexcept;
ApplicationError head_error(
    const protocol::storage::SQLiteV7HeadResult& result) noexcept;
std::variant<FinalizedBlockV7, ApplicationError> finalize_result(
    const protocol::v7::BlockOutcome& outcome);

}  // namespace internal_v7
}  // namespace protocol::application
