#pragma once

// The version-eight schema: install it, prove a reopened file is the one we
// left, and read the durable head back.
//
// The connection, locking, journal, and path-stability contract comes from
// `sqlite_connection.hpp` unchanged. None of it is version-specific: ADR 0007
// settles all of it against the filesystem and SQLite rather than against a
// ledger.

#include "sqlite_connection.hpp"

#include "protocol/storage/sqlite_ledger_v8.hpp"

#include <cstdint>
#include <span>

namespace protocol::storage::internal {

// Version one's `Failure` carries a `SQLiteLedgerError`. The version-eight store
// throws its own so the two vocabularies never blur at a catch site.
struct FailureV8 {
  SQLiteLedgerV8Error error;
};

// The three facts a reopen must agree on before the snapshot is even decoded.
struct DurableHeadV8 {
  protocol::v8::Bytes snapshot;
  protocol::v8::Hash state_root{};
  std::uint64_t height = 0;
};

void install_schema_v8(Connection& connection,
                       std::span<const std::uint8_t> canonical_genesis,
                       const protocol::v8::Octets32& chain_id,
                       const DurableHeadV8& genesis_head);

void validate_integrity_v8(Connection& connection);
void validate_schema_v8(Connection& connection);
void validate_stored_genesis_v8(Connection& connection,
                                std::span<const std::uint8_t> expected_genesis);
DurableHeadV8 read_durable_head_v8(Connection& connection);

// Write the new head and the block row in the caller's open transaction. It
// performs no commit: the head and the block that produced it are one fact, and
// a reader that could see one without the other would see a state no block made.
void persist_block_v8(Connection& connection, const DurableHeadV8& head,
                      const BlockCommitV8& commit,
                      std::span<const std::uint8_t> header);

}  // namespace protocol::storage::internal
