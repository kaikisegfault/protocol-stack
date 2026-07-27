#pragma once

#include "protocol/application/application_v1.hpp"
#include "protocol/v1/ledger.hpp"

#include <mutex>
#include <optional>
#include <span>
#include <utility>
#include <vector>

namespace protocol::application {

struct ApplicationV1::Impl {
  struct Stage {
    std::uint64_t height;
    std::vector<protocol::v1::Bytes> transactions;
    protocol::v1::BlockCommit commit;
    protocol::storage::LedgerHead candidate_head;
    FinalizedBlock response;
  };

  protocol::storage::SQLiteLedger ledger;
  protocol::v1::Parameters parameters;
  mutable std::mutex mutex;
  std::optional<Stage> stage;
  bool ready;
  bool terminal;

  Impl(
      protocol::storage::SQLiteLedger owned_ledger,
      protocol::v1::Parameters immutable_parameters,
      bool is_ready) noexcept
      : ledger(std::move(owned_ledger)),
        parameters(std::move(immutable_parameters)),
        ready(is_ready),
        terminal(false) {}

  ApplicationError fail(ApplicationError error) noexcept {
    terminal = true;
    return error;
  }
};

namespace internal {

bool within_block_bounds(
    std::span<const protocol::v1::Bytes> transactions) noexcept;
ApplicationError head_error(
    const protocol::storage::SQLiteHeadResult& result) noexcept;

}  // namespace internal
}  // namespace protocol::application
