#pragma once

// What the version-nine store's two translation units share: the live state
// behind the class, the trusted genesis a caller presents, and the three
// conversions between a ledger, a payload, and a durable row.
//
// `sqlite_ledger_v9.cpp` owns what a live store does; `sqlite_ledger_v9_open.cpp`
// owns how one comes into existence.

#include "protocol/storage/sqlite_ledger_v9.hpp"

#include "sqlite_fault_injection.hpp"
#include "sqlite_schema_v9.hpp"

#include <filesystem>
#include <memory>
#include <mutex>
#include <span>

namespace protocol::storage {

namespace v9 = protocol::v9;

namespace internal_v9 {

namespace v9 = protocol::v9;
using internal::DurableHeadV9;
using internal::FailureV9;

inline std::span<const std::uint8_t> bytes_view(const v9::Bytes& bytes) noexcept {
  return {bytes.data(), bytes.size()};
}

// Version one's storage codes carry the same numbers and meanings for every
// case this store can reach, but a blind cast would turn a code it does not
// share — `invalid_archive`, which only the archive import raises — into a value
// outside this enumeration. The mapping is written out so that cannot happen.
inline SQLiteLedgerV9Error translate(SQLiteLedgerError error) {
  switch (error) {
    case SQLiteLedgerError::invalid_genesis:
      return SQLiteLedgerV9Error::invalid_genesis;
    case SQLiteLedgerError::invalid_path:
      return SQLiteLedgerV9Error::invalid_path;
    case SQLiteLedgerError::path_already_exists:
      return SQLiteLedgerV9Error::path_already_exists;
    case SQLiteLedgerError::path_not_found:
      return SQLiteLedgerV9Error::path_not_found;
    case SQLiteLedgerError::lock_unavailable:
      return SQLiteLedgerV9Error::lock_unavailable;
    case SQLiteLedgerError::configuration_mismatch:
      return SQLiteLedgerV9Error::configuration_mismatch;
    case SQLiteLedgerError::integrity_failure:
      return SQLiteLedgerV9Error::integrity_failure;
    case SQLiteLedgerError::schema_mismatch:
      return SQLiteLedgerV9Error::schema_mismatch;
    case SQLiteLedgerError::genesis_mismatch:
      return SQLiteLedgerV9Error::genesis_mismatch;
    case SQLiteLedgerError::state_mismatch:
      return SQLiteLedgerV9Error::state_mismatch;
    case SQLiteLedgerError::storage_failure:
    case SQLiteLedgerError::invalid_archive:
      break;
  }
  return SQLiteLedgerV9Error::storage_failure;
}

inline SQLiteLedgerV9Result error_result(SQLiteLedgerV9Error error) {
  return SQLiteLedgerV9Result{
      std::variant<SQLiteLedgerV9, SQLiteLedgerV9Error>(
          std::in_place_type<SQLiteLedgerV9Error>, error),
  };
}

// The genesis a caller presents, decoded once and trusted thereafter. A file
// never supplies these: they are the five immutable parameters a restore is
// checked against, so a snapshot that could redefine them could move a node to a
// different chain. **Version nine adds none**, for ADR 0080's reason: its one new
// genesis field is the genesis timestamp, which a restored ledger does not need
// and which `chain_id` — compared among the five — already commits to.
struct TrustedGenesisV9 {
  v9::Bytes canonical_bytes;
  v9::Ledger ledger;
  v9::Hash state_root{};
  SnapshotParametersV9 parameters;
};

inline TrustedGenesisV9 load_trusted_genesis(const v9::Genesis& genesis) {
  const auto canonical_genesis = v9::encode_genesis(genesis);
  if (!canonical_genesis) throw FailureV9{SQLiteLedgerV9Error::invalid_genesis};
  auto opened = v9::open_ledger(genesis);
  if (!opened) throw FailureV9{SQLiteLedgerV9Error::invalid_genesis};
  const auto root = v9::ledger_state_root(*opened);
  if (!root) throw FailureV9{SQLiteLedgerV9Error::invalid_genesis};
  auto parameters = snapshot_parameters(*opened);
  return TrustedGenesisV9{std::move(*canonical_genesis), std::move(*opened),
                          *root, parameters};
}

inline DurableHeadV9 durable_head_of(const v9::Ledger& ledger) {
  auto encoded = encode_snapshot_v9(ledger);
  if (!std::holds_alternative<EncodedSnapshotV9>(encoded)) {
    throw FailureV9{SQLiteLedgerV9Error::invalid_snapshot};
  }
  auto value = std::get<EncodedSnapshotV9>(std::move(encoded));
  return DurableHeadV9{std::move(value.payload), value.state_root,
                       ledger.height, ledger.timestamp};
}

// Restore the durable head, and require the columns beside it to agree. The
// snapshot's own gates establish that the payload is a reachable state; these
// three comparisons establish that it is the state this file *says* it holds, so
// a row edited without the payload is caught rather than silently preferred.
//
// **The timestamp comparison is the one version nine adds, and it is not implied
// by the root's.** The root commits to the payload's stamp, so the root
// comparison already refuses a payload whose stamp was changed alone. What it
// cannot refuse is a *column* that disagrees with an unchanged payload — and a
// column is exactly what a later reader, or a later version of this store, would
// be tempted to trust without decoding anything.
inline v9::Ledger restore_durable_head(const DurableHeadV9& durable,
                                const SnapshotParametersV9& parameters) {
  auto decoded = decode_snapshot_v9(bytes_view(durable.snapshot), parameters);
  if (!std::holds_alternative<DecodedSnapshotV9>(decoded)) {
    throw FailureV9{SQLiteLedgerV9Error::invalid_snapshot};
  }
  auto restored = std::get<DecodedSnapshotV9>(std::move(decoded));
  if (restored.state_root != durable.state_root ||
      restored.ledger.height != durable.height ||
      restored.ledger.timestamp != durable.timestamp) {
    throw FailureV9{SQLiteLedgerV9Error::state_mismatch};
  }
  return std::move(restored.ledger);
}

}  // namespace internal_v9

struct SQLiteLedgerV9::Impl {
  std::filesystem::path path;
  v9::Bytes canonical_genesis;
  SnapshotParametersV9 parameters;
  v9::SignatureVerifier verify;
  std::unique_ptr<internal::SQLiteResources> resources;
  mutable std::mutex mutex;
  v9::Ledger ledger;
  v9::Hash state_root{};
  v9::Bytes head_snapshot;
  bool poisoned = false;

  Impl(std::filesystem::path normalized_path, v9::Bytes exact_genesis,
       SnapshotParametersV9 immutable_parameters,
       v9::SignatureVerifier verifier,
       std::unique_ptr<internal::SQLiteResources> sqlite_resources,
       v9::Ledger live_ledger, v9::Hash verified_root, v9::Bytes payload)
      : path(std::move(normalized_path)),
        canonical_genesis(std::move(exact_genesis)),
        parameters(immutable_parameters),
        verify(std::move(verifier)),
        resources(std::move(sqlite_resources)),
        ledger(std::move(live_ledger)),
        state_root(verified_root),
        head_snapshot(std::move(payload)) {}

  // **After a commit whose outcome is unknown, the only honest answer is to read
  // the file again.** This closes the connection, reopens it, runs the same four
  // validation steps an ordinary open runs, and adopts whatever head the file
  // actually holds — which is either the block's or its predecessor's and never
  // anything between, because SQLite's transaction is what decides. It is
  // version one's recovery for version one's reason.
  //
  // It is `noexcept` and answers `false` rather than throwing: a store that
  // cannot recover stays poisoned, which is a worse state but an honest one.
  bool recover_durable_head() noexcept {
    try {
      if (!resources) return false;
      resources->connection.close();
      resources.reset();
      if (internal::invoke_sqlite_block_fault(
              internal::SQLiteBlockFaultPoint::before_recovery_open, nullptr)) {
        throw internal::FailureV9{SQLiteLedgerV9Error::storage_failure};
      }

      auto replacement = std::make_unique<internal::SQLiteResources>(
          internal::open_sqlite_database(path));
      internal::configure_connection(replacement->connection);
      internal::acquire_lifetime_lock(replacement->connection);
      internal::require_existing_journal_mode(replacement->connection);
      internal::verify_stable_path(*replacement, path);
      internal::validate_integrity_v9(replacement->connection);
      internal::validate_schema_v9(replacement->connection);
      internal::validate_stored_genesis_v9(
          replacement->connection,
          internal_v9::bytes_view(canonical_genesis));
      auto durable = internal::read_durable_head_v9(replacement->connection);
      auto payload = durable.snapshot;
      auto restored = internal_v9::restore_durable_head(durable, parameters);

      resources.swap(replacement);
      ledger = std::move(restored);
      state_root = durable.state_root;
      head_snapshot = std::move(payload);
      poisoned = false;
      return true;
    } catch (...) {
      return false;
    }
  }
};

}  // namespace protocol::storage
