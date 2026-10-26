#pragma once

// What the version-ten store's two translation units share: the live state
// behind the class, the trusted genesis a caller presents, and the three
// conversions between a ledger, a payload, and a durable row.
//
// `sqlite_ledger_v10.cpp` owns what a live store does; `sqlite_ledger_v10_open.cpp`
// owns how one comes into existence.

#include "protocol/storage/sqlite_ledger_v10.hpp"

#include "sqlite_fault_injection.hpp"
#include "sqlite_schema_v10.hpp"

#include <filesystem>
#include <memory>
#include <mutex>
#include <span>

namespace protocol::storage {

namespace v10 = protocol::v10;

namespace internal_v10 {

namespace v10 = protocol::v10;
using internal::DurableHeadV10;
using internal::FailureV10;

inline std::span<const std::uint8_t> bytes_view(const v10::Bytes& bytes) noexcept {
  return {bytes.data(), bytes.size()};
}

// Version one's storage codes carry the same numbers and meanings for every
// case this store can reach, but a blind cast would turn a code it does not
// share — `invalid_archive`, which only the archive import raises — into a value
// outside this enumeration. The mapping is written out so that cannot happen.
inline SQLiteLedgerV10Error translate(SQLiteLedgerError error) {
  switch (error) {
    case SQLiteLedgerError::invalid_genesis:
      return SQLiteLedgerV10Error::invalid_genesis;
    case SQLiteLedgerError::invalid_path:
      return SQLiteLedgerV10Error::invalid_path;
    case SQLiteLedgerError::path_already_exists:
      return SQLiteLedgerV10Error::path_already_exists;
    case SQLiteLedgerError::path_not_found:
      return SQLiteLedgerV10Error::path_not_found;
    case SQLiteLedgerError::lock_unavailable:
      return SQLiteLedgerV10Error::lock_unavailable;
    case SQLiteLedgerError::configuration_mismatch:
      return SQLiteLedgerV10Error::configuration_mismatch;
    case SQLiteLedgerError::integrity_failure:
      return SQLiteLedgerV10Error::integrity_failure;
    case SQLiteLedgerError::schema_mismatch:
      return SQLiteLedgerV10Error::schema_mismatch;
    case SQLiteLedgerError::genesis_mismatch:
      return SQLiteLedgerV10Error::genesis_mismatch;
    case SQLiteLedgerError::state_mismatch:
      return SQLiteLedgerV10Error::state_mismatch;
    case SQLiteLedgerError::storage_failure:
    case SQLiteLedgerError::invalid_archive:
      break;
  }
  return SQLiteLedgerV10Error::storage_failure;
}

inline SQLiteLedgerV10Result error_result(SQLiteLedgerV10Error error) {
  return SQLiteLedgerV10Result{
      std::variant<SQLiteLedgerV10, SQLiteLedgerV10Error>(
          std::in_place_type<SQLiteLedgerV10Error>, error),
  };
}

// The genesis a caller presents, decoded once and trusted thereafter. A file
// never supplies these: they are the six immutable parameters a restore is
// checked against, so a snapshot that could redefine them could move a node to a
// different chain. **Version ten adds the build authority key** (ADR 0108), and
// it reaches a restore only from here: the ledger keeps it, kind 23 reads it, and
// no root commits to it, so a store that took it from anywhere but the genesis
// its caller presents could admit machines another chain's authority attested.
struct TrustedGenesisV10 {
  v10::Bytes canonical_bytes;
  v10::Ledger ledger;
  v10::Hash state_root{};
  SnapshotParametersV10 parameters;
};

inline TrustedGenesisV10 load_trusted_genesis(const v10::Genesis& genesis) {
  const auto canonical_genesis = v10::encode_genesis(genesis);
  if (!canonical_genesis) throw FailureV10{SQLiteLedgerV10Error::invalid_genesis};
  auto opened = v10::open_ledger(genesis);
  if (!opened) throw FailureV10{SQLiteLedgerV10Error::invalid_genesis};
  const auto root = v10::ledger_state_root(*opened);
  if (!root) throw FailureV10{SQLiteLedgerV10Error::invalid_genesis};
  auto parameters = snapshot_parameters(*opened);
  return TrustedGenesisV10{std::move(*canonical_genesis), std::move(*opened),
                          *root, parameters};
}

inline DurableHeadV10 durable_head_of(const v10::Ledger& ledger) {
  auto encoded = encode_snapshot_v10(ledger);
  if (!std::holds_alternative<EncodedSnapshotV10>(encoded)) {
    throw FailureV10{SQLiteLedgerV10Error::invalid_snapshot};
  }
  auto value = std::get<EncodedSnapshotV10>(std::move(encoded));
  return DurableHeadV10{std::move(value.payload), value.state_root,
                       ledger.height, ledger.timestamp};
}

// Restore the durable head, and require the columns beside it to agree. The
// snapshot's own gates establish that the payload is a reachable state; these
// three comparisons establish that it is the state this file *says* it holds, so
// a row edited without the payload is caught rather than silently preferred.
//
// **The timestamp comparison is the one version nine added, and it is not implied
// by the root's.** The root commits to the payload's stamp, so the root
// comparison already refuses a payload whose stamp was changed alone. What it
// cannot refuse is a *column* that disagrees with an unchanged payload — and a
// column is exactly what a later reader, or a later version of this store, would
// be tempted to trust without decoding anything.
inline v10::Ledger restore_durable_head(const DurableHeadV10& durable,
                                const SnapshotParametersV10& parameters) {
  auto decoded = decode_snapshot_v10(bytes_view(durable.snapshot), parameters);
  if (!std::holds_alternative<DecodedSnapshotV10>(decoded)) {
    throw FailureV10{SQLiteLedgerV10Error::invalid_snapshot};
  }
  auto restored = std::get<DecodedSnapshotV10>(std::move(decoded));
  if (restored.state_root != durable.state_root ||
      restored.ledger.height != durable.height ||
      restored.ledger.timestamp != durable.timestamp) {
    throw FailureV10{SQLiteLedgerV10Error::state_mismatch};
  }
  return std::move(restored.ledger);
}

}  // namespace internal_v10

struct SQLiteLedgerV10::Impl {
  std::filesystem::path path;
  v10::Bytes canonical_genesis;
  SnapshotParametersV10 parameters;
  v10::SignatureVerifier verify;
  std::unique_ptr<internal::SQLiteResources> resources;
  mutable std::mutex mutex;
  v10::Ledger ledger;
  v10::Hash state_root{};
  v10::Bytes head_snapshot;
  bool poisoned = false;

  Impl(std::filesystem::path normalized_path, v10::Bytes exact_genesis,
       SnapshotParametersV10 immutable_parameters,
       v10::SignatureVerifier verifier,
       std::unique_ptr<internal::SQLiteResources> sqlite_resources,
       v10::Ledger live_ledger, v10::Hash verified_root, v10::Bytes payload)
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
        throw internal::FailureV10{SQLiteLedgerV10Error::storage_failure};
      }

      auto replacement = std::make_unique<internal::SQLiteResources>(
          internal::open_sqlite_database(path));
      internal::configure_connection(replacement->connection);
      internal::acquire_lifetime_lock(replacement->connection);
      internal::require_existing_journal_mode(replacement->connection);
      internal::verify_stable_path(*replacement, path);
      internal::validate_integrity_v10(replacement->connection);
      internal::validate_schema_v10(replacement->connection);
      internal::validate_stored_genesis_v10(
          replacement->connection,
          internal_v10::bytes_view(canonical_genesis));
      auto durable = internal::read_durable_head_v10(replacement->connection);
      auto payload = durable.snapshot;
      auto restored = internal_v10::restore_durable_head(durable, parameters);

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
