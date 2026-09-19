#pragma once

// What the version-nine application's two translation units share: the live
// state behind the class, the staged block, and the bounds a peer's bytes are
// checked against before any kernel sees them.
//
// **The clock lives here and is read in exactly one place.** It is a member so
// that construction can refuse an empty one, and it is private to the
// implementation so that no operation outside `process_proposal` can reach it.

#include "protocol/application/application_v9.hpp"

#include <mutex>
#include <optional>
#include <span>
#include <utility>
#include <vector>

namespace protocol::application {

struct ApplicationV9::Impl {
  // What `finalize_block` produced and `commit` must find again. **The stamp is
  // staged beside the height**, because `commit` replays the block through the
  // store with the exact staged height, timestamp, and bytes — a commit that
  // replayed the height and supplied a fresh stamp would commit a root naming a
  // height the stamp does not belong to, and every later block would still
  // satisfy C2 because the stale stamp is smaller.
  struct Stage {
    std::uint64_t height = 0;
    std::uint64_t timestamp = 0;
    std::vector<protocol::v9::Bytes> transactions;
    protocol::storage::BlockCommitV9 commit;
    protocol::v9::Hash candidate_root{};
    FinalizedBlockV9 response;
  };

  protocol::storage::SQLiteLedgerV9 ledger;
  protocol::v9::Octets32 chain_id{};
  // **There is no stored genesis timestamp, and that is the point.** `init_chain`
  // is only reachable while the durable height is zero, and at height zero the
  // head's own stamp *is* the genesis stamp — so the comparison reads the head it
  // already read rather than a second copy that could disagree with it. ADR 0080
  // gave the same answer for the snapshot; here the reason is sharper, because
  // the one operation that needs the value is the one operation that can only run
  // where the value is still in the head.
  protocol::v9::SignatureVerifier verify;
  // Read by `process_proposal` and by nothing else. It is not `const` only
  // because `std::function` invocation on a const member would require the
  // target to be const-callable, which a test clock that advances is not.
  mutable ClockSourceV9 clock;
  mutable std::mutex mutex;
  std::optional<Stage> stage;
  bool ready = false;
  bool terminal = false;

  Impl(protocol::storage::SQLiteLedgerV9 owned_ledger,
       protocol::v9::Octets32 immutable_chain_id,
       protocol::v9::SignatureVerifier verifier, ClockSourceV9 clock_source,
       bool is_ready) noexcept
      : ledger(std::move(owned_ledger)),
        chain_id(immutable_chain_id),
        verify(std::move(verifier)),
        clock(std::move(clock_source)),
        ready(is_ready) {}

  // Every refusal after the chain is ready latches, which is version eight's
  // rule unchanged.
  ApplicationError fail(ApplicationError error) noexcept {
    terminal = true;
    return error;
  }

  FinalizeFailureV9 fail_timestamp(TimestampFailureV9 failure) noexcept {
    terminal = true;
    return failure;
  }
};

namespace internal_v9 {

bool within_block_bounds(
    std::span<const protocol::v9::Bytes> transactions) noexcept;
ApplicationError head_error(
    const protocol::storage::SQLiteV9HeadResult& result) noexcept;
std::variant<FinalizedBlockV9, ApplicationError> finalize_result(
    const protocol::v9::BlockOutcome& outcome);

}  // namespace internal_v9
}  // namespace protocol::application
