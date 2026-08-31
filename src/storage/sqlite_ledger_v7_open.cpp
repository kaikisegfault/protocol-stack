// How a version-seven store comes into existence, which is a different subject
// from what a live one does.
//
// **Creating and opening are separate operations**, as ADR 0007 requires: a
// create reserves the pathname with the platform's exclusive-create primitive
// and fails if the target exists, and an open refuses a pathname that does not.
// Nothing here is reachable twice — a store is validated once and then trusted
// for its lifetime — which is why the four validation steps live on this side
// and `apply_block` performs none of them.
//
// **The order of those steps is load-bearing.** The integrity check runs first
// because a corrupted page makes every later comparison lie: with it removed, a
// database whose pages were overwritten reports `genesis_mismatch`, which tells
// an operator they opened the wrong chain rather than that their disk is
// failing.

#include "sqlite_ledger_v7_internal.hpp"

#include <memory>
#include <utility>
#include <variant>

namespace protocol::storage {

using namespace internal_v7;

SQLiteLedgerV7Result create_sqlite_ledger_v7(
    const std::filesystem::path& path,
    const v7::Genesis& genesis, v7::SignatureVerifier verify) {
  try {
    auto trusted = load_trusted_genesis(genesis);
    const auto normalized = internal::normalize_database_path(path);
    auto resources = std::make_unique<internal::SQLiteResources>(
        internal::reserve_sqlite_database(normalized));
    internal::configure_connection(resources->connection);
    internal::acquire_lifetime_lock(resources->connection);
    internal::set_creation_journal_mode(resources->connection);

    auto durable = durable_head_of(trusted.ledger);
    auto payload = durable.snapshot;
    internal::begin_exclusive(resources->connection);
    try {
      internal::install_schema_v7(resources->connection,
                                  bytes_view(trusted.canonical_bytes),
                                  trusted.ledger.chain_id, durable);
      internal::verify_stable_path(*resources, normalized);
    } catch (...) {
      internal::rollback_or_terminate(resources->connection);
      throw;
    }
    internal::commit(resources->connection);
    internal::verify_stable_path(*resources, normalized);

    auto implementation = std::make_unique<SQLiteLedgerV7::Impl>(
        normalized, std::move(trusted.canonical_bytes), trusted.parameters,
        std::move(verify), std::move(resources), std::move(trusted.ledger),
        trusted.state_root, std::move(payload));
    return SQLiteLedgerV7Result{
        std::variant<SQLiteLedgerV7, SQLiteLedgerV7Error>(
            std::in_place_type<SQLiteLedgerV7>,
            SQLiteLedgerV7(std::move(implementation))),
    };
  } catch (const FailureV7& failure) {
    return error_result(failure.error);
  } catch (const internal::Failure& failure) {
    return error_result(translate(failure.error));
  } catch (...) {
    return error_result(SQLiteLedgerV7Error::storage_failure);
  }
}

SQLiteLedgerV7Result open_sqlite_ledger_v7(
    const std::filesystem::path& path,
    const v7::Genesis& genesis, v7::SignatureVerifier verify) {
  try {
    auto trusted = load_trusted_genesis(genesis);
    const auto normalized = internal::normalize_database_path(path);
    auto resources = std::make_unique<internal::SQLiteResources>(
        internal::open_sqlite_database(normalized));
    internal::configure_connection(resources->connection);
    internal::acquire_lifetime_lock(resources->connection);
    internal::require_existing_journal_mode(resources->connection);
    internal::verify_stable_path(*resources, normalized);

    internal::validate_integrity_v7(resources->connection);
    internal::validate_schema_v7(resources->connection);
    internal::validate_stored_genesis_v7(resources->connection,
                                         bytes_view(trusted.canonical_bytes));
    auto durable = internal::read_durable_head_v7(resources->connection);
    auto payload = durable.snapshot;
    auto restored = restore_durable_head(durable, trusted.parameters);

    auto implementation = std::make_unique<SQLiteLedgerV7::Impl>(
        normalized, std::move(trusted.canonical_bytes), trusted.parameters,
        std::move(verify), std::move(resources), std::move(restored),
        durable.state_root, std::move(payload));
    return SQLiteLedgerV7Result{
        std::variant<SQLiteLedgerV7, SQLiteLedgerV7Error>(
            std::in_place_type<SQLiteLedgerV7>,
            SQLiteLedgerV7(std::move(implementation))),
    };
  } catch (const FailureV7& failure) {
    return error_result(failure.error);
  } catch (const internal::Failure& failure) {
    return error_result(translate(failure.error));
  } catch (...) {
    return error_result(SQLiteLedgerV7Error::storage_failure);
  }
}

}  // namespace protocol::storage
