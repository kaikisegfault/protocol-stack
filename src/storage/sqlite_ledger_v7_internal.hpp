#pragma once

// What the version-seven store's two translation units share: the live state
// behind the class, the trusted genesis a caller presents, and the three
// conversions between a ledger, a payload, and a durable row.
//
// `sqlite_ledger_v7.cpp` owns what a live store does; `sqlite_ledger_v7_open.cpp`
// owns how one comes into existence.

#include "protocol/storage/sqlite_ledger_v7.hpp"

#include "sqlite_schema_v7.hpp"

#include <filesystem>
#include <memory>
#include <mutex>
#include <span>

namespace protocol::storage {

namespace v7 = protocol::v7;

namespace internal_v7 {

namespace v7 = protocol::v7;
using internal::DurableHeadV7;
using internal::FailureV7;

inline std::span<const std::uint8_t> bytes_view(const v7::Bytes& bytes) noexcept {
  return {bytes.data(), bytes.size()};
}

// Version one's storage codes carry the same numbers and meanings for every
// case this store can reach, but a blind cast would turn a code it does not
// share — `invalid_archive`, which only the archive import raises — into a value
// outside this enumeration. The mapping is written out so that cannot happen.
inline SQLiteLedgerV7Error translate(SQLiteLedgerError error) {
  switch (error) {
    case SQLiteLedgerError::invalid_genesis:
      return SQLiteLedgerV7Error::invalid_genesis;
    case SQLiteLedgerError::invalid_path:
      return SQLiteLedgerV7Error::invalid_path;
    case SQLiteLedgerError::path_already_exists:
      return SQLiteLedgerV7Error::path_already_exists;
    case SQLiteLedgerError::path_not_found:
      return SQLiteLedgerV7Error::path_not_found;
    case SQLiteLedgerError::lock_unavailable:
      return SQLiteLedgerV7Error::lock_unavailable;
    case SQLiteLedgerError::configuration_mismatch:
      return SQLiteLedgerV7Error::configuration_mismatch;
    case SQLiteLedgerError::integrity_failure:
      return SQLiteLedgerV7Error::integrity_failure;
    case SQLiteLedgerError::schema_mismatch:
      return SQLiteLedgerV7Error::schema_mismatch;
    case SQLiteLedgerError::genesis_mismatch:
      return SQLiteLedgerV7Error::genesis_mismatch;
    case SQLiteLedgerError::state_mismatch:
      return SQLiteLedgerV7Error::state_mismatch;
    case SQLiteLedgerError::storage_failure:
    case SQLiteLedgerError::invalid_archive:
      break;
  }
  return SQLiteLedgerV7Error::storage_failure;
}

inline SQLiteLedgerV7Result error_result(SQLiteLedgerV7Error error) {
  return SQLiteLedgerV7Result{
      std::variant<SQLiteLedgerV7, SQLiteLedgerV7Error>(
          std::in_place_type<SQLiteLedgerV7Error>, error),
  };
}

// The genesis a caller presents, decoded once and trusted thereafter. A file
// never supplies these: they are the four immutable parameters a restore is
// checked against, so a snapshot that could redefine them could move a node to a
// different chain.
struct TrustedGenesisV7 {
  v7::Bytes canonical_bytes;
  v7::Ledger ledger;
  v7::Hash state_root{};
  SnapshotParametersV7 parameters;
};

inline TrustedGenesisV7 load_trusted_genesis(const v7::Genesis& genesis) {
  const auto canonical_genesis = v7::encode_genesis(genesis);
  if (!canonical_genesis) throw FailureV7{SQLiteLedgerV7Error::invalid_genesis};
  auto opened = v7::open_ledger(genesis);
  if (!opened) throw FailureV7{SQLiteLedgerV7Error::invalid_genesis};
  const auto root = v7::ledger_state_root(*opened);
  if (!root) throw FailureV7{SQLiteLedgerV7Error::invalid_genesis};
  auto parameters = snapshot_parameters(*opened);
  return TrustedGenesisV7{std::move(*canonical_genesis), std::move(*opened),
                          *root, parameters};
}

inline DurableHeadV7 durable_head_of(const v7::Ledger& ledger) {
  auto encoded = encode_snapshot_v7(ledger);
  if (!std::holds_alternative<EncodedSnapshotV7>(encoded)) {
    throw FailureV7{SQLiteLedgerV7Error::invalid_snapshot};
  }
  auto value = std::get<EncodedSnapshotV7>(std::move(encoded));
  return DurableHeadV7{std::move(value.payload), value.state_root,
                       ledger.height};
}

// Restore the durable head, and require the columns beside it to agree. The
// snapshot's own gates establish that the payload is a reachable state; these
// two comparisons establish that it is the state this file *says* it holds, so a
// row edited without the payload is caught rather than silently preferred.
inline v7::Ledger restore_durable_head(const DurableHeadV7& durable,
                                const SnapshotParametersV7& parameters) {
  auto decoded = decode_snapshot_v7(bytes_view(durable.snapshot), parameters);
  if (!std::holds_alternative<DecodedSnapshotV7>(decoded)) {
    throw FailureV7{SQLiteLedgerV7Error::invalid_snapshot};
  }
  auto restored = std::get<DecodedSnapshotV7>(std::move(decoded));
  if (restored.state_root != durable.state_root ||
      restored.ledger.height != durable.height) {
    throw FailureV7{SQLiteLedgerV7Error::state_mismatch};
  }
  return std::move(restored.ledger);
}

}  // namespace internal_v7

struct SQLiteLedgerV7::Impl {
  std::filesystem::path path;
  v7::Bytes canonical_genesis;
  SnapshotParametersV7 parameters;
  v7::SignatureVerifier verify;
  std::unique_ptr<internal::SQLiteResources> resources;
  mutable std::mutex mutex;
  v7::Ledger ledger;
  v7::Hash state_root{};
  v7::Bytes head_snapshot;
  bool poisoned = false;

  Impl(std::filesystem::path normalized_path, v7::Bytes exact_genesis,
       SnapshotParametersV7 immutable_parameters,
       v7::SignatureVerifier verifier,
       std::unique_ptr<internal::SQLiteResources> sqlite_resources,
       v7::Ledger live_ledger, v7::Hash verified_root, v7::Bytes payload)
      : path(std::move(normalized_path)),
        canonical_genesis(std::move(exact_genesis)),
        parameters(immutable_parameters),
        verify(std::move(verifier)),
        resources(std::move(sqlite_resources)),
        ledger(std::move(live_ledger)),
        state_root(verified_root),
        head_snapshot(std::move(payload)) {}
};

}  // namespace protocol::storage
