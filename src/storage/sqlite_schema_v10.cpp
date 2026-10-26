// The version-ten schema and the two rows a committed block writes.
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
// rather than read. **Three of its literals are widths, and two move with this
// version.** None may be edited alone:
//
// - `canonical_genesis` is `v10::kGenesisPrefixBytes`, which is 182 rather than
//   version nine's 150 because the build authority key is a genesis field. A
//   stale value there fails the very first insert, so it cannot reach a file.
// - `head_snapshot` is `snapshot_v10`'s own `kFixedSize` of 262 — the 198-octet
//   prefix, a root, and a digest — so the shortest blob the column admits is the
//   shortest one the decoder could parse (ADR 0108). A stale 230 there degrades
//   a refusal rather than admitting a state: a short blob would reach
//   `decode_snapshot_v10` and come back `invalid_snapshot` instead of never being
//   stored.
// - `header` is `v10::kBlockHeaderBytes`, which is still version nine's 154,
//   because version ten keeps version nine's header schema and bytes. **It is the
//   literal that does not move**, and the boundary case below writes both
//   widths for it anyway: a store that creates a genesis and then refuses every
//   block is the failure a copied DDL would produce if it ever did.

#include "sqlite_schema_v10.hpp"

#include <sqlite3.h>

#include <algorithm>
#include <array>
#include <cstddef>
#include <string>
#include <string_view>

namespace protocol::storage::internal {
namespace {

namespace v10 = protocol::v10;

// "PS10": version nine's `PSL9` cannot carry a two-digit version in its last
// octet, so the version takes the last two, and a file opened by the wrong
// adapter is still refused by its own first pragma rather than by a schema
// comparison further in. A version-nine file presented here fails on this
// pragma, before its table names or its 150-octet genesis are ever read.
constexpr std::int64_t kApplicationIdV10 = 0x50533130;
constexpr std::int64_t kSchemaVersionV10 = 10;

constexpr char kLedgerMetaDdl[] =
    "CREATE TABLE ledger_meta_v10(\n"
    "  singleton INTEGER NOT NULL PRIMARY KEY CHECK(singleton = 1),\n"
    "  canonical_genesis BLOB NOT NULL "
    "CHECK(typeof(canonical_genesis) = 'blob' AND "
    "length(canonical_genesis) = 182),\n"
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
    "CHECK(typeof(head_snapshot) = 'blob' AND length(head_snapshot) >= 262)\n"
    ") STRICT, WITHOUT ROWID";

constexpr char kBlocksDdl[] =
    "CREATE TABLE blocks_v10(\n"
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
    Table{"blocks_v10", kBlocksDdl},
    Table{"ledger_meta_v10", kLedgerMetaDdl},
};

[[noreturn]] void fail(SQLiteLedgerV10Error error) { throw FailureV10{error}; }

void require_row(Statement& statement, SQLiteLedgerV10Error error) {
  if (statement.step() != SQLITE_ROW) fail(error);
}

void require_done(Statement& statement, SQLiteLedgerV10Error error) {
  if (statement.step() != SQLITE_DONE) fail(error);
}

bool text_column(Statement& statement, int index, std::string_view expected) {
  return statement.column_type(index) == SQLITE_TEXT &&
         statement.column_text(index) == expected;
}

v10::Bytes encoded_u64(std::uint64_t value) {
  v10::Bytes bytes;
  bytes.reserve(8);
  for (int shift = 56; shift >= 0; shift -= 8) {
    bytes.push_back(static_cast<std::uint8_t>(value >> shift));
  }
  return bytes;
}

std::uint64_t decoded_u64(std::span<const std::uint8_t> bytes) {
  if (bytes.size() != 8) fail(SQLiteLedgerV10Error::state_mismatch);
  std::uint64_t value = 0;
  for (const auto octet : bytes) value = (value << 8U) | octet;
  return value;
}

v10::Hash decoded_hash(std::span<const std::uint8_t> bytes) {
  if (bytes.size() != 32) fail(SQLiteLedgerV10Error::state_mismatch);
  v10::Hash value{};
  std::copy(bytes.begin(), bytes.end(), value.begin());
  return value;
}

}  // namespace

void install_schema_v10(Connection& connection,
                       std::span<const std::uint8_t> canonical_genesis,
                       const v10::Octets32& chain_id,
                       const DurableHeadV10& genesis_head) {
  connection.execute(kLedgerMetaDdl);
  connection.execute(kBlocksDdl);
  // **Written from the constants the reopen compares against**, so each marker
  // is one fact. Version nine's store writes them as literals beside its
  // constants, and the first port of it changed the constants alone: the store
  // created files under version nine's markers and then refused to reopen every
  // one of them (ADR 0109).
  const auto application_id =
      "PRAGMA main.application_id = " + std::to_string(kApplicationIdV10);
  const auto user_version =
      "PRAGMA main.user_version = " + std::to_string(kSchemaVersionV10);
  connection.execute(application_id.c_str());
  connection.execute(user_version.c_str());

  Statement insert = connection.prepare(
      "INSERT INTO ledger_meta_v10(singleton, canonical_genesis, chain_id,"
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
  require_done(insert, SQLiteLedgerV10Error::storage_failure);
}

void validate_integrity_v10(Connection& connection) {
  Statement integrity = connection.prepare("PRAGMA main.integrity_check");
  require_row(integrity, SQLiteLedgerV10Error::integrity_failure);
  if (integrity.column_count() != 1 || !text_column(integrity, 0, "ok")) {
    fail(SQLiteLedgerV10Error::integrity_failure);
  }
  require_done(integrity, SQLiteLedgerV10Error::integrity_failure);

  Statement foreign_keys = connection.prepare("PRAGMA main.foreign_key_check");
  require_done(foreign_keys, SQLiteLedgerV10Error::integrity_failure);
}

// The stored DDL is compared verbatim, so a table altered underneath the process
// is refused rather than read. `sqlite_master` is ordered by name so the
// comparison does not depend on creation order.
void validate_schema_v10(Connection& connection) {
  if (connection.scalar_integer("PRAGMA main.application_id") !=
          kApplicationIdV10 ||
      connection.scalar_integer("PRAGMA main.user_version") !=
          kSchemaVersionV10) {
    fail(SQLiteLedgerV10Error::schema_mismatch);
  }
  Statement objects = connection.prepare(
      "SELECT type, name, tbl_name, sql FROM main.sqlite_master"
      " ORDER BY name");
  for (const auto& table : kTables) {
    require_row(objects, SQLiteLedgerV10Error::schema_mismatch);
    if (objects.column_count() != 4 || !text_column(objects, 0, "table") ||
        !text_column(objects, 1, table.name) ||
        !text_column(objects, 2, table.name) ||
        !text_column(objects, 3, table.ddl)) {
      fail(SQLiteLedgerV10Error::schema_mismatch);
    }
  }
  require_done(objects, SQLiteLedgerV10Error::schema_mismatch);
}

void validate_stored_genesis_v10(Connection& connection,
                                std::span<const std::uint8_t> expected_genesis) {
  Statement stored = connection.prepare(
      "SELECT canonical_genesis FROM ledger_meta_v10 WHERE singleton = 1");
  require_row(stored, SQLiteLedgerV10Error::genesis_mismatch);
  const auto found = stored.column_blob(0);
  if (found.size() != expected_genesis.size() ||
      !std::equal(found.begin(), found.end(), expected_genesis.begin())) {
    fail(SQLiteLedgerV10Error::genesis_mismatch);
  }
  require_done(stored, SQLiteLedgerV10Error::genesis_mismatch);
}

DurableHeadV10 read_durable_head_v10(Connection& connection) {
  Statement head = connection.prepare(
      "SELECT current_height, current_timestamp_millis, current_state_root,"
      " head_snapshot FROM ledger_meta_v10 WHERE singleton = 1");
  require_row(head, SQLiteLedgerV10Error::state_mismatch);
  DurableHeadV10 durable;
  durable.height = decoded_u64(head.column_blob(0));
  durable.timestamp = decoded_u64(head.column_blob(1));
  durable.state_root = decoded_hash(head.column_blob(2));
  const auto snapshot = head.column_blob(3);
  durable.snapshot.assign(snapshot.begin(), snapshot.end());
  require_done(head, SQLiteLedgerV10Error::state_mismatch);
  return durable;
}

void persist_block_v10(Connection& connection, const DurableHeadV10& head,
                      const BlockCommitV10& commit,
                      std::span<const std::uint8_t> header) {
  // **The stamp is written in the same statement as the height**, so there is
  // no path through this function that advances one and leaves the other: the
  // defect this version could hide would need two statements to exist.
  Statement update = connection.prepare(
      "UPDATE ledger_meta_v10 SET current_height = ?,"
      " current_timestamp_millis = ?, current_state_root = ?, head_snapshot = ?"
      " WHERE singleton = 1");
  const auto height = encoded_u64(head.height);
  update.bind_blob(1, height);
  const auto timestamp = encoded_u64(head.timestamp);
  update.bind_blob(2, timestamp);
  update.bind_blob(3, head.state_root);
  update.bind_blob(4, head.snapshot);
  require_done(update, SQLiteLedgerV10Error::storage_failure);
  if (sqlite3_changes(connection.get()) != 1) {
    fail(SQLiteLedgerV10Error::storage_failure);
  }

  Statement insert = connection.prepare(
      "INSERT INTO blocks_v10(height, timestamp, previous_state_root,"
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
  require_done(insert, SQLiteLedgerV10Error::storage_failure);
}

}  // namespace protocol::storage::internal
