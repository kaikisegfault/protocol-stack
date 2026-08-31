// The version-seven schema and the two rows a committed block writes.
//
// **The head is one snapshot payload rather than a row per account and a row per
// economy entry.** That is a deliberate narrowing of version one's schema, and
// the argument is the snapshot's own: it is already the canonical projection of
// everything a state root commits to, already checked against recorded roots,
// three gates, and a fuzz target. A second row-shaped projection would be a
// second opinion about what a state *is*, and every future entry kind would have
// to be added to both. What the schema keeps in its own columns is only what a
// reopen must agree on *before* it trusts the payload: the chain identity, the
// height, and the root.
//
// The DDL is stored and compared verbatim on every open, exactly as version
// one's is, so a file whose schema was altered underneath the process is refused
// rather than read.

#include "sqlite_schema_v7.hpp"

#include <sqlite3.h>

#include <algorithm>
#include <array>
#include <cstddef>
#include <string>
#include <string_view>

namespace protocol::storage::internal {
namespace {

namespace v7 = protocol::v7;

// "PSL7": the version-one store's `PSLD` with its version, so a file opened by
// the wrong adapter is refused by its own first pragma rather than by a schema
// comparison further in.
constexpr std::int64_t kApplicationIdV7 = 0x50534c37;
constexpr std::int64_t kSchemaVersionV7 = 7;

constexpr char kLedgerMetaDdl[] =
    "CREATE TABLE ledger_meta_v7(\n"
    "  singleton INTEGER NOT NULL PRIMARY KEY CHECK(singleton = 1),\n"
    "  canonical_genesis BLOB NOT NULL "
    "CHECK(typeof(canonical_genesis) = 'blob' AND "
    "length(canonical_genesis) = 110),\n"
    "  chain_id BLOB NOT NULL "
    "CHECK(typeof(chain_id) = 'blob' AND length(chain_id) = 32),\n"
    "  current_height BLOB NOT NULL "
    "CHECK(typeof(current_height) = 'blob' AND length(current_height) = 8),\n"
    "  current_state_root BLOB NOT NULL "
    "CHECK(typeof(current_state_root) = 'blob' AND "
    "length(current_state_root) = 32),\n"
    "  head_snapshot BLOB NOT NULL "
    "CHECK(typeof(head_snapshot) = 'blob' AND length(head_snapshot) >= 190)\n"
    ") STRICT, WITHOUT ROWID";

constexpr char kBlocksDdl[] =
    "CREATE TABLE blocks_v7(\n"
    "  height BLOB NOT NULL PRIMARY KEY "
    "CHECK(typeof(height) = 'blob' AND length(height) = 8),\n"
    "  previous_state_root BLOB NOT NULL "
    "CHECK(typeof(previous_state_root) = 'blob' AND "
    "length(previous_state_root) = 32),\n"
    "  transaction_root BLOB NOT NULL "
    "CHECK(typeof(transaction_root) = 'blob' AND "
    "length(transaction_root) = 32),\n"
    "  resulting_state_root BLOB NOT NULL "
    "CHECK(typeof(resulting_state_root) = 'blob' AND "
    "length(resulting_state_root) = 32),\n"
    "  block_id BLOB NOT NULL "
    "CHECK(typeof(block_id) = 'blob' AND length(block_id) = 32),\n"
    "  header BLOB NOT NULL "
    "CHECK(typeof(header) = 'blob' AND length(header) = 146)\n"
    ") STRICT, WITHOUT ROWID";

struct Table {
  const char* name;
  const char* ddl;
};

constexpr std::array<Table, 2> kTables{
    Table{"blocks_v7", kBlocksDdl},
    Table{"ledger_meta_v7", kLedgerMetaDdl},
};

[[noreturn]] void fail(SQLiteLedgerV7Error error) { throw FailureV7{error}; }

void require_row(Statement& statement, SQLiteLedgerV7Error error) {
  if (statement.step() != SQLITE_ROW) fail(error);
}

void require_done(Statement& statement, SQLiteLedgerV7Error error) {
  if (statement.step() != SQLITE_DONE) fail(error);
}

bool text_column(Statement& statement, int index, std::string_view expected) {
  return statement.column_type(index) == SQLITE_TEXT &&
         statement.column_text(index) == expected;
}

v7::Bytes encoded_u64(std::uint64_t value) {
  v7::Bytes bytes;
  bytes.reserve(8);
  for (int shift = 56; shift >= 0; shift -= 8) {
    bytes.push_back(static_cast<std::uint8_t>(value >> shift));
  }
  return bytes;
}

std::uint64_t decoded_u64(std::span<const std::uint8_t> bytes) {
  if (bytes.size() != 8) fail(SQLiteLedgerV7Error::state_mismatch);
  std::uint64_t value = 0;
  for (const auto octet : bytes) value = (value << 8U) | octet;
  return value;
}

v7::Hash decoded_hash(std::span<const std::uint8_t> bytes) {
  if (bytes.size() != 32) fail(SQLiteLedgerV7Error::state_mismatch);
  v7::Hash value{};
  std::copy(bytes.begin(), bytes.end(), value.begin());
  return value;
}

}  // namespace

void install_schema_v7(Connection& connection,
                       std::span<const std::uint8_t> canonical_genesis,
                       const v7::Octets32& chain_id,
                       const DurableHeadV7& genesis_head) {
  connection.execute(kLedgerMetaDdl);
  connection.execute(kBlocksDdl);
  connection.execute("PRAGMA main.application_id = 1347636279");
  connection.execute("PRAGMA main.user_version = 7");

  Statement insert = connection.prepare(
      "INSERT INTO ledger_meta_v7(singleton, canonical_genesis, chain_id,"
      " current_height, current_state_root, head_snapshot)"
      " VALUES(1, ?, ?, ?, ?, ?)");
  insert.bind_blob(1, canonical_genesis);
  insert.bind_blob(2, chain_id);
  const auto height = encoded_u64(genesis_head.height);
  insert.bind_blob(3, height);
  insert.bind_blob(4, genesis_head.state_root);
  insert.bind_blob(5, genesis_head.snapshot);
  require_done(insert, SQLiteLedgerV7Error::storage_failure);
}

void validate_integrity_v7(Connection& connection) {
  Statement integrity = connection.prepare("PRAGMA main.integrity_check");
  require_row(integrity, SQLiteLedgerV7Error::integrity_failure);
  if (integrity.column_count() != 1 || !text_column(integrity, 0, "ok")) {
    fail(SQLiteLedgerV7Error::integrity_failure);
  }
  require_done(integrity, SQLiteLedgerV7Error::integrity_failure);

  Statement foreign_keys = connection.prepare("PRAGMA main.foreign_key_check");
  require_done(foreign_keys, SQLiteLedgerV7Error::integrity_failure);
}

// The stored DDL is compared verbatim, so a table altered underneath the process
// is refused rather than read. `sqlite_master` is ordered by name so the
// comparison does not depend on creation order.
void validate_schema_v7(Connection& connection) {
  if (connection.scalar_integer("PRAGMA main.application_id") !=
          kApplicationIdV7 ||
      connection.scalar_integer("PRAGMA main.user_version") !=
          kSchemaVersionV7) {
    fail(SQLiteLedgerV7Error::schema_mismatch);
  }
  Statement objects = connection.prepare(
      "SELECT type, name, tbl_name, sql FROM main.sqlite_master"
      " ORDER BY name");
  for (const auto& table : kTables) {
    require_row(objects, SQLiteLedgerV7Error::schema_mismatch);
    if (objects.column_count() != 4 || !text_column(objects, 0, "table") ||
        !text_column(objects, 1, table.name) ||
        !text_column(objects, 2, table.name) ||
        !text_column(objects, 3, table.ddl)) {
      fail(SQLiteLedgerV7Error::schema_mismatch);
    }
  }
  require_done(objects, SQLiteLedgerV7Error::schema_mismatch);
}

void validate_stored_genesis_v7(Connection& connection,
                                std::span<const std::uint8_t> expected_genesis) {
  Statement stored = connection.prepare(
      "SELECT canonical_genesis FROM ledger_meta_v7 WHERE singleton = 1");
  require_row(stored, SQLiteLedgerV7Error::genesis_mismatch);
  const auto found = stored.column_blob(0);
  if (found.size() != expected_genesis.size() ||
      !std::equal(found.begin(), found.end(), expected_genesis.begin())) {
    fail(SQLiteLedgerV7Error::genesis_mismatch);
  }
  require_done(stored, SQLiteLedgerV7Error::genesis_mismatch);
}

DurableHeadV7 read_durable_head_v7(Connection& connection) {
  Statement head = connection.prepare(
      "SELECT current_height, current_state_root, head_snapshot"
      " FROM ledger_meta_v7 WHERE singleton = 1");
  require_row(head, SQLiteLedgerV7Error::state_mismatch);
  DurableHeadV7 durable;
  durable.height = decoded_u64(head.column_blob(0));
  durable.state_root = decoded_hash(head.column_blob(1));
  const auto snapshot = head.column_blob(2);
  durable.snapshot.assign(snapshot.begin(), snapshot.end());
  require_done(head, SQLiteLedgerV7Error::state_mismatch);
  return durable;
}

void persist_block_v7(Connection& connection, const DurableHeadV7& head,
                      const BlockCommitV7& commit,
                      std::span<const std::uint8_t> header) {
  Statement update = connection.prepare(
      "UPDATE ledger_meta_v7 SET current_height = ?, current_state_root = ?,"
      " head_snapshot = ? WHERE singleton = 1");
  const auto height = encoded_u64(head.height);
  update.bind_blob(1, height);
  update.bind_blob(2, head.state_root);
  update.bind_blob(3, head.snapshot);
  require_done(update, SQLiteLedgerV7Error::storage_failure);
  if (sqlite3_changes(connection.get()) != 1) {
    fail(SQLiteLedgerV7Error::storage_failure);
  }

  Statement insert = connection.prepare(
      "INSERT INTO blocks_v7(height, previous_state_root, transaction_root,"
      " resulting_state_root, block_id, header) VALUES(?, ?, ?, ?, ?, ?)");
  const auto block_height = encoded_u64(commit.height);
  insert.bind_blob(1, block_height);
  insert.bind_blob(2, commit.previous_state_root);
  insert.bind_blob(3, commit.transaction_root);
  insert.bind_blob(4, commit.resulting_state_root);
  insert.bind_blob(5, commit.block_id);
  insert.bind_blob(6, header);
  require_done(insert, SQLiteLedgerV7Error::storage_failure);
}

}  // namespace protocol::storage::internal
