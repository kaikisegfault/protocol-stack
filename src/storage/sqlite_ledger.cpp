#include "protocol/storage/sqlite_ledger.hpp"

#include "sqlite_connection.hpp"
#include "sqlite_history_v1.hpp"
#include "sqlite_schema_v1.hpp"
#include "sqlite_snapshot_v1.hpp"

#include "protocol/storage/snapshot_v1.hpp"
#include "protocol/v1/ledger.hpp"

#include <mutex>
#include <type_traits>
#include <utility>
#include <variant>

namespace protocol::storage {
namespace {

using protocol::v1::Bytes;
using protocol::v1::Ledger;
using protocol::v1::StateRoot;

struct TrustedGenesis {
  Bytes canonical_bytes;
  Ledger ledger;
  StateRoot state_root;
};

std::span<const std::uint8_t> bytes_view(const Bytes& bytes) noexcept {
  return {bytes.data(), bytes.size()};
}

TrustedGenesis load_trusted_genesis(
    std::span<const std::uint8_t> canonical_genesis) {
  auto loaded = protocol::v1::load_genesis(canonical_genesis);
  if (!std::holds_alternative<Ledger>(loaded.result)) {
    throw internal::Failure{SQLiteLedgerError::invalid_genesis};
  }

  auto ledger = std::get<Ledger>(std::move(loaded.result));
  auto root = ledger.current_state_root();
  if (!std::holds_alternative<StateRoot>(root)) {
    throw internal::Failure{SQLiteLedgerError::invalid_genesis};
  }

  return TrustedGenesis{
      Bytes(canonical_genesis.begin(), canonical_genesis.end()),
      std::move(ledger),
      std::get<StateRoot>(std::move(root)),
  };
}

StateRoot require_root(
    const Ledger& ledger,
    SQLiteLedgerError error) {
  auto root = ledger.current_state_root();
  if (!std::holds_alternative<StateRoot>(root)) {
    throw internal::Failure{error};
  }
  return std::get<StateRoot>(std::move(root));
}

Ledger validate_durable_ledger(
    internal::Connection& connection,
    std::span<const std::uint8_t> canonical_genesis,
    const Ledger& trusted_genesis,
    const StateRoot& trusted_root) {
  internal::validate_integrity(connection);
  internal::validate_schema_v1(connection);
  internal::validate_stored_genesis(
      connection, canonical_genesis, trusted_genesis, trusted_root);
  auto replayed =
      internal::replay_history_v1(connection, trusted_genesis);
  const auto replayed_root = require_root(
      replayed, SQLiteLedgerError::state_mismatch);
  return internal::load_materialized_ledger(
      connection, canonical_genesis, trusted_genesis, trusted_root,
      replayed, replayed_root);
}

SQLiteLedgerResult error_result(SQLiteLedgerError error) {
  return SQLiteLedgerResult{
      std::variant<SQLiteLedger, SQLiteLedgerError>(
          std::in_place_type<SQLiteLedgerError>, error),
  };
}

}  // namespace

struct SQLiteLedger::Impl {
  std::filesystem::path path;
  Bytes canonical_genesis;
  internal::SQLiteResources resources;
  mutable std::mutex mutex;
  std::unique_ptr<Ledger> ledger;
  StateRoot state_root;
  bool poisoned;

  Impl(
      std::filesystem::path normalized_path,
      Bytes exact_genesis,
      internal::SQLiteResources sqlite_resources,
      std::unique_ptr<Ledger> live_ledger,
      StateRoot verified_root) noexcept
      : path(std::move(normalized_path)),
        canonical_genesis(std::move(exact_genesis)),
        resources(std::move(sqlite_resources)),
        ledger(std::move(live_ledger)),
        state_root(std::move(verified_root)),
        poisoned(false) {}
};

static_assert(std::is_nothrow_move_constructible_v<SQLiteLedger>);
static_assert(std::is_nothrow_destructible_v<SQLiteLedger>);
static_assert(std::is_nothrow_move_constructible_v<SQLiteBlockResult>);
static_assert(std::is_nothrow_move_constructible_v<SQLiteSnapshotResult>);
static_assert(std::is_nothrow_swappable_v<std::unique_ptr<Ledger>>);
static_assert(std::is_nothrow_copy_assignable_v<StateRoot>);

SQLiteLedger::SQLiteLedger(
    std::unique_ptr<Impl> implementation) noexcept
    : implementation_(std::move(implementation)) {}

SQLiteLedger::~SQLiteLedger() noexcept = default;
SQLiteLedger::SQLiteLedger(SQLiteLedger&&) noexcept = default;

LedgerHead SQLiteLedger::read_head() const {
  const std::lock_guard<std::mutex> lock(implementation_->mutex);
  return LedgerHead{
      implementation_->ledger->state(),
      implementation_->state_root,
  };
}

SQLiteBlockResult SQLiteLedger::apply_block(
    std::uint64_t height,
    std::span<const Bytes> raw_transactions) {
  const std::lock_guard<std::mutex> lock(implementation_->mutex);
  if (implementation_->poisoned) {
    return SQLiteBlockResult(
        std::in_place_type<SQLiteLedgerError>,
        SQLiteLedgerError::storage_failure);
  }

  auto candidate =
      std::make_unique<Ledger>(*implementation_->ledger);
  auto applied = candidate->apply_block(height, raw_transactions);
  if (std::holds_alternative<protocol::v1::BlockError>(applied)) {
    return SQLiteBlockResult(
        std::in_place_type<protocol::v1::BlockError>,
        std::get<protocol::v1::BlockError>(applied));
  }
  SQLiteBlockResult result(
      std::in_place_type<protocol::v1::BlockCommit>,
      std::get<protocol::v1::BlockCommit>(std::move(applied)));
  const auto& commit = std::get<protocol::v1::BlockCommit>(result);

  try {
    auto& connection = implementation_->resources.connection;
    internal::verify_stable_path(
        implementation_->resources, implementation_->path);
    internal::begin_exclusive(connection);
    try {
      internal::persist_block_v1(
          connection, implementation_->ledger->state(),
          candidate->state(), raw_transactions, commit);
      internal::verify_stable_path(
          implementation_->resources, implementation_->path);
    } catch (...) {
      internal::rollback_or_terminate(connection);
      throw;
    }
    try {
      internal::commit(connection);
    } catch (...) {
      implementation_->poisoned = true;
      throw;
    }

    implementation_->ledger.swap(candidate);
    implementation_->state_root = commit.resulting_state_root;
    return result;
  } catch (const internal::Failure& failure) {
    return SQLiteBlockResult(
        std::in_place_type<SQLiteLedgerError>, failure.error);
  }
}

SQLiteSnapshotResult SQLiteLedger::create_snapshot() {
  const std::lock_guard<std::mutex> lock(implementation_->mutex);
  if (implementation_->poisoned) {
    return SQLiteSnapshotResult(
        std::in_place_type<SQLiteLedgerError>,
        SQLiteLedgerError::storage_failure);
  }

  auto encoded = encode_snapshot_v1(*implementation_->ledger);
  if (!std::holds_alternative<EncodedSnapshotV1>(encoded)) {
    return SQLiteSnapshotResult(
        std::in_place_type<SQLiteLedgerError>,
        SQLiteLedgerError::state_mismatch);
  }
  auto snapshot =
      std::get<EncodedSnapshotV1>(std::move(encoded));

  try {
    auto& connection = implementation_->resources.connection;
    internal::verify_stable_path(
        implementation_->resources, implementation_->path);
    internal::begin_exclusive(connection);
    try {
      internal::persist_snapshot_v1(
          connection, *implementation_->ledger, snapshot);
      internal::verify_stable_path(
          implementation_->resources, implementation_->path);
    } catch (...) {
      internal::rollback_or_terminate(connection);
      throw;
    }
    try {
      internal::commit(connection);
    } catch (...) {
      implementation_->poisoned = true;
      throw;
    }
    return SQLiteSnapshotResult(
        std::in_place_type<Bytes>, std::move(snapshot.payload));
  } catch (const internal::Failure& failure) {
    return SQLiteSnapshotResult(
        std::in_place_type<SQLiteLedgerError>, failure.error);
  }
}

SQLiteLedgerResult create_sqlite_ledger(
    const std::filesystem::path& path,
    std::span<const std::uint8_t> canonical_genesis) {
  try {
    auto trusted = load_trusted_genesis(canonical_genesis);
    auto normalized = internal::normalize_database_path(path);
    auto resources = internal::reserve_sqlite_database(normalized);
    internal::configure_connection(resources.connection);
    internal::acquire_lifetime_lock(resources.connection);
    internal::set_creation_journal_mode(resources.connection);

    auto live = std::make_unique<Ledger>(std::move(trusted.ledger));
    auto implementation = std::make_unique<SQLiteLedger::Impl>(
        std::move(normalized),
        std::move(trusted.canonical_bytes),
        std::move(resources),
        std::move(live),
        trusted.state_root);
    auto& connection = implementation->resources.connection;
    const auto stored_genesis =
        bytes_view(implementation->canonical_genesis);

    internal::begin_exclusive(connection);
    try {
      internal::install_schema_v1(
          connection, stored_genesis, *implementation->ledger,
          implementation->state_root);
      auto validation = validate_durable_ledger(
          connection, stored_genesis, *implementation->ledger,
          implementation->state_root);
      (void)validation;
      internal::verify_stable_path(
          implementation->resources, implementation->path);
    } catch (...) {
      internal::rollback_or_terminate(connection);
      throw;
    }
    internal::commit(connection);

    internal::verify_stable_path(
        implementation->resources, implementation->path);
    auto durable_validation = validate_durable_ledger(
        connection, stored_genesis, *implementation->ledger,
        implementation->state_root);
    (void)durable_validation;

    return SQLiteLedgerResult{
        std::variant<SQLiteLedger, SQLiteLedgerError>(
            std::in_place_type<SQLiteLedger>,
            SQLiteLedger(std::move(implementation))),
    };
  } catch (const internal::Failure& failure) {
    return error_result(failure.error);
  }
}

SQLiteLedgerResult open_sqlite_ledger(
    const std::filesystem::path& path,
    std::span<const std::uint8_t> canonical_genesis) {
  try {
    auto trusted = load_trusted_genesis(canonical_genesis);
    auto normalized = internal::normalize_database_path(path);
    auto resources = internal::open_sqlite_database(normalized);
    internal::configure_connection(resources.connection);
    internal::acquire_lifetime_lock(resources.connection);
    internal::require_existing_journal_mode(resources.connection);
    internal::verify_stable_path(resources, normalized);

    auto live = validate_durable_ledger(
        resources.connection, bytes_view(trusted.canonical_bytes),
        trusted.ledger, trusted.state_root);
    const auto live_root =
        require_root(live, SQLiteLedgerError::state_mismatch);
    auto implementation = std::make_unique<SQLiteLedger::Impl>(
        std::move(normalized),
        std::move(trusted.canonical_bytes),
        std::move(resources),
        std::make_unique<Ledger>(std::move(live)),
        live_root);

    return SQLiteLedgerResult{
        std::variant<SQLiteLedger, SQLiteLedgerError>(
            std::in_place_type<SQLiteLedger>,
            SQLiteLedger(std::move(implementation))),
    };
  } catch (const internal::Failure& failure) {
    return error_result(failure.error);
  }
}

}  // namespace protocol::storage
