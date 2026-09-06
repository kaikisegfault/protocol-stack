#pragma once

// What the version-eight store's two translation units share: the live state
// behind the class, the trusted genesis a caller presents, and the three
// conversions between a ledger, a payload, and a durable row.
//
// `sqlite_ledger_v8.cpp` owns what a live store does; `sqlite_ledger_v8_open.cpp`
// owns how one comes into existence.

#include "protocol/storage/sqlite_ledger_v8.hpp"

#include "sqlite_fault_injection.hpp"
#include "sqlite_schema_v8.hpp"

#include <filesystem>
#include <memory>
#include <mutex>
#include <span>

namespace protocol::storage {

namespace v8 = protocol::v8;

namespace internal_v8 {

namespace v8 = protocol::v8;
using internal::DurableHeadV8;
using internal::FailureV8;

inline std::span<const std::uint8_t> bytes_view(const v8::Bytes& bytes) noexcept {
  return {bytes.data(), bytes.size()};
}

// Version one's storage codes carry the same numbers and meanings for every
// case this store can reach, but a blind cast would turn a code it does not
// share — `invalid_archive`, which only the archive import raises — into a value
// outside this enumeration. The mapping is written out so that cannot happen.
inline SQLiteLedgerV8Error translate(SQLiteLedgerError error) {
  switch (error) {
    case SQLiteLedgerError::invalid_genesis:
      return SQLiteLedgerV8Error::invalid_genesis;
    case SQLiteLedgerError::invalid_path:
      return SQLiteLedgerV8Error::invalid_path;
    case SQLiteLedgerError::path_already_exists:
      return SQLiteLedgerV8Error::path_already_exists;
    case SQLiteLedgerError::path_not_found:
      return SQLiteLedgerV8Error::path_not_found;
    case SQLiteLedgerError::lock_unavailable:
      return SQLiteLedgerV8Error::lock_unavailable;
    case SQLiteLedgerError::configuration_mismatch:
      return SQLiteLedgerV8Error::configuration_mismatch;
    case SQLiteLedgerError::integrity_failure:
      return SQLiteLedgerV8Error::integrity_failure;
    case SQLiteLedgerError::schema_mismatch:
      return SQLiteLedgerV8Error::schema_mismatch;
    case SQLiteLedgerError::genesis_mismatch:
      return SQLiteLedgerV8Error::genesis_mismatch;
    case SQLiteLedgerError::state_mismatch:
      return SQLiteLedgerV8Error::state_mismatch;
    case SQLiteLedgerError::storage_failure:
    case SQLiteLedgerError::invalid_archive:
      break;
  }
  return SQLiteLedgerV8Error::storage_failure;
}

inline SQLiteLedgerV8Result error_result(SQLiteLedgerV8Error error) {
  return SQLiteLedgerV8Result{
      std::variant<SQLiteLedgerV8, SQLiteLedgerV8Error>(
          std::in_place_type<SQLiteLedgerV8Error>, error),
  };
}

// The genesis a caller presents, decoded once and trusted thereafter. A file
// never supplies these: they are the four immutable parameters a restore is
// checked against, so a snapshot that could redefine them could move a node to a
// different chain.
struct TrustedGenesisV8 {
  v8::Bytes canonical_bytes;
  v8::Ledger ledger;
  v8::Hash state_root{};
  SnapshotParametersV8 parameters;
};

inline TrustedGenesisV8 load_trusted_genesis(const v8::Genesis& genesis) {
  const auto canonical_genesis = v8::encode_genesis(genesis);
  if (!canonical_genesis) throw FailureV8{SQLiteLedgerV8Error::invalid_genesis};
  auto opened = v8::open_ledger(genesis);
  if (!opened) throw FailureV8{SQLiteLedgerV8Error::invalid_genesis};
  const auto root = v8::ledger_state_root(*opened);
  if (!root) throw FailureV8{SQLiteLedgerV8Error::invalid_genesis};
  auto parameters = snapshot_parameters(*opened);
  return TrustedGenesisV8{std::move(*canonical_genesis), std::move(*opened),
                          *root, parameters};
}

inline DurableHeadV8 durable_head_of(const v8::Ledger& ledger) {
  auto encoded = encode_snapshot_v8(ledger);
  if (!std::holds_alternative<EncodedSnapshotV8>(encoded)) {
    throw FailureV8{SQLiteLedgerV8Error::invalid_snapshot};
  }
  auto value = std::get<EncodedSnapshotV8>(std::move(encoded));
  return DurableHeadV8{std::move(value.payload), value.state_root,
                       ledger.height};
}

// Restore the durable head, and require the columns beside it to agree. The
// snapshot's own gates establish that the payload is a reachable state; these
// two comparisons establish that it is the state this file *says* it holds, so a
// row edited without the payload is caught rather than silently preferred.
inline v8::Ledger restore_durable_head(const DurableHeadV8& durable,
                                const SnapshotParametersV8& parameters) {
  auto decoded = decode_snapshot_v8(bytes_view(durable.snapshot), parameters);
  if (!std::holds_alternative<DecodedSnapshotV8>(decoded)) {
    throw FailureV8{SQLiteLedgerV8Error::invalid_snapshot};
  }
  auto restored = std::get<DecodedSnapshotV8>(std::move(decoded));
  if (restored.state_root != durable.state_root ||
      restored.ledger.height != durable.height) {
    throw FailureV8{SQLiteLedgerV8Error::state_mismatch};
  }
  return std::move(restored.ledger);
}

}  // namespace internal_v8

struct SQLiteLedgerV8::Impl {
  std::filesystem::path path;
  v8::Bytes canonical_genesis;
  SnapshotParametersV8 parameters;
  v8::SignatureVerifier verify;
  std::unique_ptr<internal::SQLiteResources> resources;
  mutable std::mutex mutex;
  v8::Ledger ledger;
  v8::Hash state_root{};
  v8::Bytes head_snapshot;
  bool poisoned = false;

  Impl(std::filesystem::path normalized_path, v8::Bytes exact_genesis,
       SnapshotParametersV8 immutable_parameters,
       v8::SignatureVerifier verifier,
       std::unique_ptr<internal::SQLiteResources> sqlite_resources,
       v8::Ledger live_ledger, v8::Hash verified_root, v8::Bytes payload)
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
        throw internal::FailureV8{SQLiteLedgerV8Error::storage_failure};
      }

      auto replacement = std::make_unique<internal::SQLiteResources>(
          internal::open_sqlite_database(path));
      internal::configure_connection(replacement->connection);
      internal::acquire_lifetime_lock(replacement->connection);
      internal::require_existing_journal_mode(replacement->connection);
      internal::verify_stable_path(*replacement, path);
      internal::validate_integrity_v8(replacement->connection);
      internal::validate_schema_v8(replacement->connection);
      internal::validate_stored_genesis_v8(
          replacement->connection,
          internal_v8::bytes_view(canonical_genesis));
      auto durable = internal::read_durable_head_v8(replacement->connection);
      auto payload = durable.snapshot;
      auto restored = internal_v8::restore_durable_head(durable, parameters);

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
