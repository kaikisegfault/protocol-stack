#pragma once

// The version-ten schema: install it, prove a reopened file is the one we
// left, and read the durable head back.
//
// The connection, locking, journal, and path-stability contract comes from
// `sqlite_connection.hpp` unchanged. None of it is version-specific: ADR 0007
// settles all of it against the filesystem and SQLite rather than against a
// ledger.

#include "sqlite_connection.hpp"

#include "protocol/storage/sqlite_ledger_v10.hpp"

#include <cstdint>
#include <span>

namespace protocol::storage::internal {

// Version one's `Failure` carries a `SQLiteLedgerError`. The version-ten store
// throws its own so the two vocabularies never blur at a catch site.
struct FailureV10 {
  SQLiteLedgerV10Error error;
};

// The four facts a reopen must agree on before the snapshot is even decoded.
// **The timestamp is the one version nine added**, because the head is two
// scalars and a root.
struct DurableHeadV10 {
  protocol::v10::Bytes snapshot;
  protocol::v10::Hash state_root{};
  std::uint64_t height = 0;
  std::uint64_t timestamp = 0;
};

void install_schema_v10(Connection& connection,
                       std::span<const std::uint8_t> canonical_genesis,
                       const protocol::v10::Octets32& chain_id,
                       const DurableHeadV10& genesis_head);

void validate_integrity_v10(Connection& connection);
void validate_schema_v10(Connection& connection);
void validate_stored_genesis_v10(Connection& connection,
                                std::span<const std::uint8_t> expected_genesis);
DurableHeadV10 read_durable_head_v10(Connection& connection);

// Write the new head and the block row in the caller's open transaction. It
// performs no commit: the head and the block that produced it are one fact, and
// a reader that could see one without the other would see a state no block made.
void persist_block_v10(Connection& connection, const DurableHeadV10& head,
                      const BlockCommitV10& commit,
                      std::span<const std::uint8_t> header);

}  // namespace protocol::storage::internal
