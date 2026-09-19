// The version-nine schema and the two rows a committed block writes.
//
// **The head is one snapshot payload rather than a row per account and a row per
// economy entry.** That is a deliberate narrowing of version one's schema, and
// the argument is the snapshot's own: it is already the canonical projection of
// everything a state root commits to, already checked against recorded figures,
// three gates, and a fuzz target. A second row-shaped projection would be a
// second opinion about what a state *is*, and every future entry kind would have
// to be added to both. What the schema keeps in its own columns is only what a
// reopen must agree on *before* it trusts the payload: the chain identity, the
// height, **the timestamp**, and the root.
//
// **The timestamp gets a column although the payload already carries it.**
// `consensus-application-v2` defines the durable head as two scalars and a root,
// and a file whose columns named one scalar would be stating half of it. The
// column costs eight octets per head rewrite and one comparison per reopen, and
// it is what turns a head whose stamp disagrees with its payload into a
// `state_mismatch` rather than a restore. The block row carries its stamp for the
// same reason it carries its height: both are header fields a reader of the
// history should not have to decode a header to find.
//
// **The column is `current_timestamp_millis` and not `current_timestamp`, and
// the difference is a clock.** `CURRENT_TIMESTAMP` is an SQL keyword, and SQLite
// resolves a bare `current_timestamp` in an expression to its own wall-clock
// reading rather than to a column of that name — so a `SELECT` of the head would
// have read the time of day, and the column's own `typeof` CHECK evaluated the
// keyword and refused every insert. The CHECK is what caught it, on the first
// genesis this store ever wrote; a schema without one would have stored the
// column and read back the clock, in the one component of this repository whose
// whole job is to hold the chain's stamp rather than the machine's.
//
// The DDL is stored and compared verbatim on every open, exactly as version
// one's is, so a file whose schema was altered underneath the process is refused
// rather than read. **Three of its literals move with the version and none may
// be edited alone**, which is one more than version eight had:
//
// - `canonical_genesis` is `v9::kGenesisPrefixBytes`, which is 150 rather than
//   version eight's 142 because `genesis_timestamp` is a tenth genesis field. A
//   stale value there fails the very first insert, so it cannot reach a file.
// - `head_snapshot` is `snapshot_v9`'s own `kFixedSize` of 230 — the 166-octet
//   prefix, a root, and a digest — so the shortest blob the column admits is the
//   shortest one the decoder could parse. A stale value there degrades a refusal
//   rather than admitting a state: a short blob would reach `decode_snapshot_v9`
//   and come back `invalid_snapshot` instead of never being stored.
// - `header` is `v9::kBlockHeaderBytes`, which is 154 rather than version one's
//   146 because version nine is the first version to change the header. **This
//   is the third figure that looks like framing and moves with the version**,
//   after ADR 0068's receipt magic prefix and ADR 0079's finalize response. A
//   stale value fails the first block's insert, so it cannot reach a file either
//   — but it would reach one as a store that creates a genesis and then refuses
//   every block, which is why the boundary case below writes both widths.

#include "sqlite_schema_v9.hpp"

#include <sqlite3.h>

#include <algorithm>
#include <array>
#include <cstddef>
#include <string>
#include <string_view>

namespace protocol::storage::internal {
namespace {

namespace v9 = protocol::v9;

// "PSL9": the version-one store's `PSLD` with its version, so a file opened by
// the wrong adapter is refused by its own first pragma rather than by a schema
// comparison further in. A version-eight file presented here fails on this
// pragma, before its table names or its 142-octet genesis are ever read.
constexpr std::int64_t kApplicationIdV9 = 0x50534c39;
constexpr std::int64_t kSchemaVersionV9 = 9;

constexpr char kLedgerMetaDdl[] =
    "CREATE TABLE ledger_meta_v9(\n"
    "  singleton INTEGER NOT NULL PRIMARY KEY CHECK(singleton = 1),\n"
    "  canonical_genesis BLOB NOT NULL "
    "CHECK(typeof(canonical_genesis) = 'blob' AND "
    "length(canonical_genesis) = 150),\n"
    "  chain_id BLOB NOT NULL "
    "CHECK(typeof(chain_id) = 'blob' AND length(chain_id) = 32),\n"
    "  current_height BLOB NOT NULL "
    "CHECK(typeof(current_height) = 'blob' AND length(current_height) = 8),\n"
    "  current_timestamp_millis BLOB NOT NULL "
    "CHECK(typeof(current_timestamp_millis) = 'blob' AND "
    "length(current_timestamp_millis) = 8),\n"
    "  current_state_root BLOB NOT NULL "
    "CHECK(typeof(current_state_root) = 'blob' AND "
    "length(current_state_root) = 32),\n"
    "  head_snapshot BLOB NOT NULL "
    "CHECK(typeof(head_snapshot) = 'blob' AND length(head_snapshot) >= 230)\n"
    ") STRICT, WITHOUT ROWID";

constexpr char kBlocksDdl[] =
    "CREATE TABLE blocks_v9(\n"
    "  height BLOB NOT NULL PRIMARY KEY "
    "CHECK(typeof(height) = 'blob' AND length(height) = 8),\n"
    "  timestamp BLOB NOT NULL "
    "CHECK(typeof(timestamp) = 'blob' AND length(timestamp) = 8),\n"
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
    "CHECK(typeof(header) = 'blob' AND length(header) = 154)\n"
    ") STRICT, WITHOUT ROWID";

struct Table {
  const char* name;
  const char* ddl;
};

constexpr std::array<Table, 2> kTables{
    Table{"blocks_v9", kBlocksDdl},
    Table{"ledger_meta_v9", kLedgerMetaDdl},
};

[[noreturn]] void fail(SQLiteLedgerV9Error error) { throw FailureV9{error}; }

void require_row(Statement& statement, SQLiteLedgerV9Error error) {
  if (statement.step() != SQLITE_ROW) fail(error);
}

void require_done(Statement& statement, SQLiteLedgerV9Error error) {
  if (statement.step() != SQLITE_DONE) fail(error);
}

bool text_column(Statement& statement, int index, std::string_view expected) {
  return statement.column_type(index) == SQLITE_TEXT &&
         statement.column_text(index) == expected;
}

v9::Bytes encoded_u64(std::uint64_t value) {
  v9::Bytes bytes;
  bytes.reserve(8);
  for (int shift = 56; shift >= 0; shift -= 8) {
    bytes.push_back(static_cast<std::uint8_t>(value >> shift));
  }
  return bytes;
}

std::uint64_t decoded_u64(std::span<const std::uint8_t> bytes) {
  if (bytes.size() != 8) fail(SQLiteLedgerV9Error::state_mismatch);
  std::uint64_t value = 0;
  for (const auto octet : bytes) value = (value << 8U) | octet;
  return value;
}

v9::Hash decoded_hash(std::span<const std::uint8_t> bytes) {
  if (bytes.size() != 32) fail(SQLiteLedgerV9Error::state_mismatch);
  v9::Hash value{};
  std::copy(bytes.begin(), bytes.end(), value.begin());
  return value;
}

}  // namespace

void install_schema_v9(Connection& connection,
                       std::span<const std::uint8_t> canonical_genesis,
                       const v9::Octets32& chain_id,
                       const DurableHeadV9& genesis_head) {
  connection.execute(kLedgerMetaDdl);
  connection.execute(kBlocksDdl);
  connection.execute("PRAGMA main.application_id = 1347636281");
  connection.execute("PRAGMA main.user_version = 9");

  Statement insert = connection.prepare(
      "INSERT INTO ledger_meta_v9(singleton, canonical_genesis, chain_id,"
      " current_height, current_timestamp_millis, current_state_root,"
      " head_snapshot) VALUES(1, ?, ?, ?, ?, ?, ?)");
  insert.bind_blob(1, canonical_genesis);
  insert.bind_blob(2, chain_id);
  const auto height = encoded_u64(genesis_head.height);
  insert.bind_blob(3, height);
  const auto timestamp = encoded_u64(genesis_head.timestamp);
  insert.bind_blob(4, timestamp);
  insert.bind_blob(5, genesis_head.state_root);
  insert.bind_blob(6, genesis_head.snapshot);
  require_done(insert, SQLiteLedgerV9Error::storage_failure);
}

void validate_integrity_v9(Connection& connection) {
  Statement integrity = connection.prepare("PRAGMA main.integrity_check");
  require_row(integrity, SQLiteLedgerV9Error::integrity_failure);
  if (integrity.column_count() != 1 || !text_column(integrity, 0, "ok")) {
    fail(SQLiteLedgerV9Error::integrity_failure);
  }
  require_done(integrity, SQLiteLedgerV9Error::integrity_failure);

  Statement foreign_keys = connection.prepare("PRAGMA main.foreign_key_check");
  require_done(foreign_keys, SQLiteLedgerV9Error::integrity_failure);
}

// The stored DDL is compared verbatim, so a table altered underneath the process
// is refused rather than read. `sqlite_master` is ordered by name so the
// comparison does not depend on creation order.
void validate_schema_v9(Connection& connection) {
  if (connection.scalar_integer("PRAGMA main.application_id") !=
          kApplicationIdV9 ||
      connection.scalar_integer("PRAGMA main.user_version") !=
          kSchemaVersionV9) {
    fail(SQLiteLedgerV9Error::schema_mismatch);
  }
  Statement objects = connection.prepare(
      "SELECT type, name, tbl_name, sql FROM main.sqlite_master"
      " ORDER BY name");
  for (const auto& table : kTables) {
    require_row(objects, SQLiteLedgerV9Error::schema_mismatch);
    if (objects.column_count() != 4 || !text_column(objects, 0, "table") ||
        !text_column(objects, 1, table.name) ||
        !text_column(objects, 2, table.name) ||
        !text_column(objects, 3, table.ddl)) {
      fail(SQLiteLedgerV9Error::schema_mismatch);
    }
  }
  require_done(objects, SQLiteLedgerV9Error::schema_mismatch);
}

void validate_stored_genesis_v9(Connection& connection,
                                std::span<const std::uint8_t> expected_genesis) {
  Statement stored = connection.prepare(
      "SELECT canonical_genesis FROM ledger_meta_v9 WHERE singleton = 1");
  require_row(stored, SQLiteLedgerV9Error::genesis_mismatch);
  const auto found = stored.column_blob(0);
  if (found.size() != expected_genesis.size() ||
      !std::equal(found.begin(), found.end(), expected_genesis.begin())) {
    fail(SQLiteLedgerV9Error::genesis_mismatch);
  }
  require_done(stored, SQLiteLedgerV9Error::genesis_mismatch);
}

DurableHeadV9 read_durable_head_v9(Connection& connection) {
  Statement head = connection.prepare(
      "SELECT current_height, current_timestamp_millis, current_state_root,"
      " head_snapshot FROM ledger_meta_v9 WHERE singleton = 1");
  require_row(head, SQLiteLedgerV9Error::state_mismatch);
  DurableHeadV9 durable;
  durable.height = decoded_u64(head.column_blob(0));
  durable.timestamp = decoded_u64(head.column_blob(1));
  durable.state_root = decoded_hash(head.column_blob(2));
  const auto snapshot = head.column_blob(3);
  durable.snapshot.assign(snapshot.begin(), snapshot.end());
  require_done(head, SQLiteLedgerV9Error::state_mismatch);
  return durable;
}

void persist_block_v9(Connection& connection, const DurableHeadV9& head,
                      const BlockCommitV9& commit,
                      std::span<const std::uint8_t> header) {
  // **The stamp is written in the same statement as the height**, so there is
  // no path through this function that advances one and leaves the other: the
  // defect this version could hide would need two statements to exist.
  Statement update = connection.prepare(
      "UPDATE ledger_meta_v9 SET current_height = ?,"
      " current_timestamp_millis = ?, current_state_root = ?, head_snapshot = ?"
      " WHERE singleton = 1");
  const auto height = encoded_u64(head.height);
  update.bind_blob(1, height);
  const auto timestamp = encoded_u64(head.timestamp);
  update.bind_blob(2, timestamp);
  update.bind_blob(3, head.state_root);
  update.bind_blob(4, head.snapshot);
  require_done(update, SQLiteLedgerV9Error::storage_failure);
  if (sqlite3_changes(connection.get()) != 1) {
    fail(SQLiteLedgerV9Error::storage_failure);
  }

  Statement insert = connection.prepare(
      "INSERT INTO blocks_v9(height, timestamp, previous_state_root,"
      " transaction_root, resulting_state_root, block_id, header)"
      " VALUES(?, ?, ?, ?, ?, ?, ?)");
  const auto block_height = encoded_u64(commit.height);
  insert.bind_blob(1, block_height);
  const auto block_timestamp = encoded_u64(commit.timestamp);
  insert.bind_blob(2, block_timestamp);
  insert.bind_blob(3, commit.previous_state_root);
  insert.bind_blob(4, commit.transaction_root);
  insert.bind_blob(5, commit.resulting_state_root);
  insert.bind_blob(6, commit.block_id);
  insert.bind_blob(7, header);
  require_done(insert, SQLiteLedgerV9Error::storage_failure);
}

}  // namespace protocol::storage::internal
