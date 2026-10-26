// How a version-ten store comes into existence, which is a different subject
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

#include "sqlite_ledger_v10_internal.hpp"

#include <algorithm>
#include <memory>
#include <utility>
#include <variant>

namespace protocol::storage {

using namespace internal_v10;

SQLiteLedgerV10Result create_sqlite_ledger_v10(
    const std::filesystem::path& path,
    const v10::Genesis& genesis, v10::SignatureVerifier verify) {
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
      internal::install_schema_v10(resources->connection,
                                  bytes_view(trusted.canonical_bytes),
                                  trusted.ledger.chain_id, durable);
      internal::verify_stable_path(*resources, normalized);
    } catch (...) {
      internal::rollback_or_terminate(resources->connection);
      throw;
    }
    internal::commit(resources->connection);
    internal::verify_stable_path(*resources, normalized);

    auto implementation = std::make_unique<SQLiteLedgerV10::Impl>(
        normalized, std::move(trusted.canonical_bytes), trusted.parameters,
        std::move(verify), std::move(resources), std::move(trusted.ledger),
        trusted.state_root, std::move(payload));
    return SQLiteLedgerV10Result{
        std::variant<SQLiteLedgerV10, SQLiteLedgerV10Error>(
            std::in_place_type<SQLiteLedgerV10>,
            SQLiteLedgerV10(std::move(implementation))),
    };
  } catch (const FailureV10& failure) {
    return error_result(failure.error);
  } catch (const internal::Failure& failure) {
    return error_result(translate(failure.error));
  } catch (...) {
    return error_result(SQLiteLedgerV10Error::storage_failure);
  }
}

SQLiteLedgerV10Result open_sqlite_ledger_v10(
    const std::filesystem::path& path,
    const v10::Genesis& genesis, v10::SignatureVerifier verify) {
  try {
    auto trusted = load_trusted_genesis(genesis);
    const auto normalized = internal::normalize_database_path(path);
    auto resources = std::make_unique<internal::SQLiteResources>(
        internal::open_sqlite_database(normalized));
    internal::configure_connection(resources->connection);
    internal::acquire_lifetime_lock(resources->connection);
    internal::require_existing_journal_mode(resources->connection);
    internal::verify_stable_path(*resources, normalized);

    internal::validate_integrity_v10(resources->connection);
    internal::validate_schema_v10(resources->connection);
    internal::validate_stored_genesis_v10(resources->connection,
                                         bytes_view(trusted.canonical_bytes));
    auto durable = internal::read_durable_head_v10(resources->connection);
    auto payload = durable.snapshot;
    auto restored = restore_durable_head(durable, trusted.parameters);

    auto implementation = std::make_unique<SQLiteLedgerV10::Impl>(
        normalized, std::move(trusted.canonical_bytes), trusted.parameters,
        std::move(verify), std::move(resources), std::move(restored),
        durable.state_root, std::move(payload));
    return SQLiteLedgerV10Result{
        std::variant<SQLiteLedgerV10, SQLiteLedgerV10Error>(
            std::in_place_type<SQLiteLedgerV10>,
            SQLiteLedgerV10(std::move(implementation))),
    };
  } catch (const FailureV10& failure) {
    return error_result(failure.error);
  } catch (const internal::Failure& failure) {
    return error_result(translate(failure.error));
  } catch (...) {
    return error_result(SQLiteLedgerV10Error::storage_failure);
  }
}

namespace {

struct CheckedSeedV10 {
  DecodedSnapshotV10 decoded;
  DurableHeadV10 durable;
};

// Every rule a seed must meet, none of which touches a file: the three gates
// under the genesis's parameters, a height above zero, and a payload that
// re-encodes to exactly its own octets. Seeding and inspecting both run this,
// so a launcher cannot be told a head the seed would then refuse.
CheckedSeedV10 check_seed(const TrustedGenesisV10& trusted,
                         std::span<const std::uint8_t> snapshot) {
  auto decoded = decode_snapshot_v10(snapshot, trusted.parameters);
  if (!std::holds_alternative<DecodedSnapshotV10>(decoded)) {
    throw FailureV10{SQLiteLedgerV10Error::invalid_snapshot};
  }
  auto seeded = std::get<DecodedSnapshotV10>(std::move(decoded));
  if (seeded.ledger.height == 0) {
    throw FailureV10{SQLiteLedgerV10Error::invalid_snapshot};
  }
  auto durable = durable_head_of(seeded.ledger);
  if (!std::ranges::equal(durable.snapshot, snapshot) ||
      durable.state_root != seeded.state_root) {
    throw FailureV10{SQLiteLedgerV10Error::invalid_snapshot};
  }
  return CheckedSeedV10{std::move(seeded), std::move(durable)};
}

}  // namespace

SQLiteLedgerV10Result seed_sqlite_ledger_v10(
    const std::filesystem::path& path, const v10::Genesis& genesis,
    std::span<const std::uint8_t> snapshot, v10::SignatureVerifier verify) {
  try {
    auto trusted = load_trusted_genesis(genesis);
    // **Every check on the payload runs before the path is reserved**, so a
    // refused seed leaves no file behind to be mistaken for a store.
    auto [seeded, durable] = check_seed(trusted, snapshot);

    const auto normalized = internal::normalize_database_path(path);
    auto resources = std::make_unique<internal::SQLiteResources>(
        internal::reserve_sqlite_database(normalized));
    internal::configure_connection(resources->connection);
    internal::acquire_lifetime_lock(resources->connection);
    internal::set_creation_journal_mode(resources->connection);

    auto payload = durable.snapshot;
    internal::begin_exclusive(resources->connection);
    try {
      internal::install_schema_v10(resources->connection,
                                  bytes_view(trusted.canonical_bytes),
                                  trusted.ledger.chain_id, durable);
      internal::verify_stable_path(*resources, normalized);
    } catch (...) {
      internal::rollback_or_terminate(resources->connection);
      throw;
    }
    internal::commit(resources->connection);
    internal::verify_stable_path(*resources, normalized);

    auto implementation = std::make_unique<SQLiteLedgerV10::Impl>(
        normalized, std::move(trusted.canonical_bytes), trusted.parameters,
        std::move(verify), std::move(resources), std::move(seeded.ledger),
        durable.state_root, std::move(payload));
    return SQLiteLedgerV10Result{
        std::variant<SQLiteLedgerV10, SQLiteLedgerV10Error>(
            std::in_place_type<SQLiteLedgerV10>,
            SQLiteLedgerV10(std::move(implementation))),
    };
  } catch (const FailureV10& failure) {
    return error_result(failure.error);
  } catch (const internal::Failure& failure) {
    return error_result(translate(failure.error));
  } catch (...) {
    return error_result(SQLiteLedgerV10Error::storage_failure);
  }
}

SQLiteV10HeadResult inspect_seed_v10(const v10::Genesis& genesis,
                                   std::span<const std::uint8_t> snapshot) {
  try {
    auto trusted = load_trusted_genesis(genesis);
    auto [seeded, durable] = check_seed(trusted, snapshot);
    return LedgerHeadV10{std::move(seeded.ledger), seeded.state_root};
  } catch (const FailureV10& failure) {
    return failure.error;
  } catch (...) {
    return SQLiteLedgerV10Error::storage_failure;
  }
}

}  // namespace protocol::storage
