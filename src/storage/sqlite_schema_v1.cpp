#include "sqlite_schema_v1.hpp"

#include <sqlite3.h>

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <map>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <utility>
#include <variant>

namespace protocol::storage::internal {
namespace {

namespace pv1 = protocol::v1;

constexpr std::int64_t kApplicationId = 0x50534c44;
constexpr std::int64_t kSchemaVersion = 1;

constexpr char kLedgerMetaDdl[] =
    "CREATE TABLE ledger_meta(\n"
    "  singleton INTEGER NOT NULL PRIMARY KEY CHECK(singleton = 1),\n"
    "  canonical_genesis BLOB NOT NULL "
    "CHECK(typeof(canonical_genesis) = 'blob'),\n"
    "  chain_id BLOB NOT NULL "
    "CHECK(typeof(chain_id) = 'blob' AND length(chain_id) = 32),\n"
    "  supply_limit BLOB NOT NULL "
    "CHECK(typeof(supply_limit) = 'blob' AND length(supply_limit) = 8 "
    "AND supply_limit = substr(canonical_genesis, 11, 8)),\n"
    "  total_supply BLOB NOT NULL "
    "CHECK(typeof(total_supply) = 'blob' AND length(total_supply) = 8 "
    "AND total_supply = substr(canonical_genesis, 19, 8)),\n"
    "  fixed_fee BLOB NOT NULL "
    "CHECK(typeof(fixed_fee) = 'blob' AND length(fixed_fee) = 8 "
    "AND fixed_fee = substr(canonical_genesis, 27, 8)),\n"
    "  current_height BLOB NOT NULL "
    "CHECK(typeof(current_height) = 'blob' AND length(current_height) = 8),\n"
    "  fee_pool BLOB NOT NULL "
    "CHECK(typeof(fee_pool) = 'blob' AND length(fee_pool) = 8),\n"
    "  current_state_root BLOB NOT NULL "
    "CHECK(typeof(current_state_root) = 'blob' AND "
    "length(current_state_root) = 32)\n"
    ") STRICT, WITHOUT ROWID";

constexpr char kAccountsDdl[] =
    "CREATE TABLE accounts(\n"
    "  account_id BLOB NOT NULL PRIMARY KEY "
    "CHECK(typeof(account_id) = 'blob' AND length(account_id) = 32),\n"
    "  balance BLOB NOT NULL "
    "CHECK(typeof(balance) = 'blob' AND length(balance) = 8),\n"
    "  nonce BLOB NOT NULL "
    "CHECK(typeof(nonce) = 'blob' AND length(nonce) = 8)\n"
    ") STRICT, WITHOUT ROWID";

constexpr char kBlocksDdl[] =
    "CREATE TABLE blocks(\n"
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
    "  admitted_count BLOB NOT NULL "
    "CHECK(typeof(admitted_count) = 'blob' AND "
    "length(admitted_count) = 4),\n"
    "  header BLOB NOT NULL "
    "CHECK(typeof(header) = 'blob' AND length(header) = 146),\n"
    "  block_id BLOB NOT NULL "
    "CHECK(typeof(block_id) = 'blob' AND length(block_id) = 32)\n"
    ") STRICT, WITHOUT ROWID";

constexpr char kAdmittedTransactionsDdl[] =
    "CREATE TABLE admitted_transactions(\n"
    "  height BLOB NOT NULL "
    "CHECK(typeof(height) = 'blob' AND length(height) = 8),\n"
    "  ordinal BLOB NOT NULL "
    "CHECK(typeof(ordinal) = 'blob' AND length(ordinal) = 4),\n"
    "  transaction_bytes BLOB NOT NULL "
    "CHECK(typeof(transaction_bytes) = 'blob' AND "
    "length(transaction_bytes) = 200),\n"
    "  transaction_id BLOB NOT NULL "
    "CHECK(typeof(transaction_id) = 'blob' AND "
    "length(transaction_id) = 32),\n"
    "  receipt_bytes BLOB NOT NULL "
    "CHECK(typeof(receipt_bytes) = 'blob' AND "
    "length(receipt_bytes) = 47),\n"
    "  PRIMARY KEY(height, ordinal),\n"
    "  FOREIGN KEY(height) REFERENCES blocks(height) "
    "ON UPDATE RESTRICT ON DELETE RESTRICT\n"
    ") STRICT, WITHOUT ROWID";

constexpr char kSnapshotsDdl[] =
    "CREATE TABLE snapshots(\n"
    "  height BLOB NOT NULL PRIMARY KEY "
    "CHECK(typeof(height) = 'blob' AND length(height) = 8),\n"
    "  payload BLOB NOT NULL CHECK(typeof(payload) = 'blob'),\n"
    "  expected_state_root BLOB NOT NULL "
    "CHECK(typeof(expected_state_root) = 'blob' AND "
    "length(expected_state_root) = 32),\n"
    "  payload_digest BLOB NOT NULL "
    "CHECK(typeof(payload_digest) = 'blob' AND "
    "length(payload_digest) = 32)\n"
    ") STRICT, WITHOUT ROWID";

struct ColumnSpec {
  std::string_view name;
  std::string_view type;
  std::int64_t primary_key_position;
};

constexpr std::array<ColumnSpec, 9> kLedgerMetaColumns{{
    {"singleton", "INTEGER", 1},
    {"canonical_genesis", "BLOB", 0},
    {"chain_id", "BLOB", 0},
    {"supply_limit", "BLOB", 0},
    {"total_supply", "BLOB", 0},
    {"fixed_fee", "BLOB", 0},
    {"current_height", "BLOB", 0},
    {"fee_pool", "BLOB", 0},
    {"current_state_root", "BLOB", 0},
}};

constexpr std::array<ColumnSpec, 3> kAccountColumns{{
    {"account_id", "BLOB", 1},
    {"balance", "BLOB", 0},
    {"nonce", "BLOB", 0},
}};

constexpr std::array<ColumnSpec, 7> kBlockColumns{{
    {"height", "BLOB", 1},
    {"previous_state_root", "BLOB", 0},
    {"transaction_root", "BLOB", 0},
    {"resulting_state_root", "BLOB", 0},
    {"admitted_count", "BLOB", 0},
    {"header", "BLOB", 0},
    {"block_id", "BLOB", 0},
}};

constexpr std::array<ColumnSpec, 5> kAdmittedTransactionColumns{{
    {"height", "BLOB", 1},
    {"ordinal", "BLOB", 2},
    {"transaction_bytes", "BLOB", 0},
    {"transaction_id", "BLOB", 0},
    {"receipt_bytes", "BLOB", 0},
}};

constexpr std::array<ColumnSpec, 4> kSnapshotColumns{{
    {"height", "BLOB", 1},
    {"payload", "BLOB", 0},
    {"expected_state_root", "BLOB", 0},
    {"payload_digest", "BLOB", 0},
}};

struct TableSpec {
  const char* name;
  const char* ddl;
  const char* table_list_sql;
  const char* table_xinfo_sql;
  const char* index_list_sql;
  const char* index_xinfo_sql;
  const char* foreign_key_list_sql;
  const char* primary_index_name;
  std::span<const ColumnSpec> columns;
  bool has_block_foreign_key;
};

const std::array<TableSpec, 5> kTables{{
    {
        "ledger_meta",
        kLedgerMetaDdl,
        "PRAGMA main.table_list('ledger_meta')",
        "PRAGMA main.table_xinfo('ledger_meta')",
        "PRAGMA main.index_list('ledger_meta')",
        "PRAGMA main.index_xinfo('sqlite_autoindex_ledger_meta_1')",
        "PRAGMA main.foreign_key_list('ledger_meta')",
        "sqlite_autoindex_ledger_meta_1",
        kLedgerMetaColumns,
        false,
    },
    {
        "accounts",
        kAccountsDdl,
        "PRAGMA main.table_list('accounts')",
        "PRAGMA main.table_xinfo('accounts')",
        "PRAGMA main.index_list('accounts')",
        "PRAGMA main.index_xinfo('sqlite_autoindex_accounts_1')",
        "PRAGMA main.foreign_key_list('accounts')",
        "sqlite_autoindex_accounts_1",
        kAccountColumns,
        false,
    },
    {
        "blocks",
        kBlocksDdl,
        "PRAGMA main.table_list('blocks')",
        "PRAGMA main.table_xinfo('blocks')",
        "PRAGMA main.index_list('blocks')",
        "PRAGMA main.index_xinfo('sqlite_autoindex_blocks_1')",
        "PRAGMA main.foreign_key_list('blocks')",
        "sqlite_autoindex_blocks_1",
        kBlockColumns,
        false,
    },
    {
        "admitted_transactions",
        kAdmittedTransactionsDdl,
        "PRAGMA main.table_list('admitted_transactions')",
        "PRAGMA main.table_xinfo('admitted_transactions')",
        "PRAGMA main.index_list('admitted_transactions')",
        "PRAGMA main.index_xinfo("
        "'sqlite_autoindex_admitted_transactions_1')",
        "PRAGMA main.foreign_key_list('admitted_transactions')",
        "sqlite_autoindex_admitted_transactions_1",
        kAdmittedTransactionColumns,
        true,
    },
    {
        "snapshots",
        kSnapshotsDdl,
        "PRAGMA main.table_list('snapshots')",
        "PRAGMA main.table_xinfo('snapshots')",
        "PRAGMA main.index_list('snapshots')",
        "PRAGMA main.index_xinfo('sqlite_autoindex_snapshots_1')",
        "PRAGMA main.foreign_key_list('snapshots')",
        "sqlite_autoindex_snapshots_1",
        kSnapshotColumns,
        false,
    },
}};

[[noreturn]] void fail(SQLiteLedgerError error) {
  throw Failure{error};
}

int checked_step(Statement& statement) {
  const auto result = statement.step();
  if (result != SQLITE_ROW && result != SQLITE_DONE) {
    fail(SQLiteLedgerError::storage_failure);
  }
  return result;
}

void require_row(Statement& statement, SQLiteLedgerError error) {
  if (checked_step(statement) != SQLITE_ROW) fail(error);
}

void require_done(Statement& statement, SQLiteLedgerError error) {
  if (checked_step(statement) != SQLITE_DONE) fail(error);
}

bool integer_column(
    const Statement& statement,
    int index,
    std::int64_t expected) {
  return statement.column_type(index) == SQLITE_INTEGER &&
         statement.column_integer(index) == expected;
}

bool text_column(
    const Statement& statement,
    int index,
    std::string_view expected) {
  return statement.column_type(index) == SQLITE_TEXT &&
         statement.column_text(index) == expected;
}

std::array<std::uint8_t, 8> encode_u64(std::uint64_t value) {
  std::array<std::uint8_t, 8> encoded{};
  for (std::size_t index = 0; index < encoded.size(); ++index) {
    const auto shift = static_cast<unsigned>(
        (encoded.size() - index - 1) * 8);
    encoded[index] = static_cast<std::uint8_t>(value >> shift);
  }
  return encoded;
}

std::uint64_t decode_u64(
    const Statement& statement,
    int index,
    SQLiteLedgerError error) {
  if (statement.column_type(index) != SQLITE_BLOB) fail(error);
  const auto bytes = statement.column_blob(index);
  if (bytes.size() != 8) fail(error);
  std::uint64_t value = 0;
  for (const auto byte : bytes) value = (value << 8U) | byte;
  return value;
}

template <typename Tagged>
Tagged decode_tagged_hash(
    const Statement& statement,
    int index,
    SQLiteLedgerError error) {
  if (statement.column_type(index) != SQLITE_BLOB) fail(error);
  const auto bytes = statement.column_blob(index);
  if (bytes.size() != pv1::Hash{}.size()) fail(error);
  pv1::Hash value{};
  std::copy(bytes.begin(), bytes.end(), value.begin());
  return Tagged{value};
}

template <typename Tagged>
std::span<const std::uint8_t> tagged_bytes(const Tagged& value) {
  return {value.data(), value.size()};
}

pv1::StateRoot require_current_root(
    const pv1::Ledger& ledger,
    SQLiteLedgerError error) {
  auto root = ledger.current_state_root();
  if (!std::holds_alternative<pv1::StateRoot>(root)) fail(error);
  return std::get<pv1::StateRoot>(std::move(root));
}

void require_trusted_genesis(
    std::span<const std::uint8_t> canonical_genesis,
    const pv1::Ledger& trusted_ledger,
    const pv1::StateRoot& trusted_root) {
  auto loaded = pv1::load_genesis(canonical_genesis);
  if (!std::holds_alternative<pv1::Ledger>(loaded.result)) {
    fail(SQLiteLedgerError::invalid_genesis);
  }
  const auto& independently_loaded = std::get<pv1::Ledger>(loaded.result);
  if (independently_loaded.state() != trusted_ledger.state() ||
      require_current_root(
          independently_loaded, SQLiteLedgerError::invalid_genesis) !=
          trusted_root ||
      require_current_root(
          trusted_ledger, SQLiteLedgerError::invalid_genesis) !=
          trusted_root) {
    fail(SQLiteLedgerError::invalid_genesis);
  }
}

void install_metadata(
    Connection& connection,
    std::span<const std::uint8_t> canonical_genesis,
    const pv1::State& state,
    const pv1::StateRoot& genesis_root) {
  Statement insert = connection.prepare(
      "INSERT INTO ledger_meta("
      "singleton, canonical_genesis, chain_id, supply_limit, total_supply, "
      "fixed_fee, current_height, fee_pool, current_state_root"
      ") VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)");
  const auto supply_limit = encode_u64(state.parameters.supply_limit);
  const auto total_supply = encode_u64(state.parameters.total_supply);
  const auto fixed_fee = encode_u64(state.parameters.fixed_fee);
  const auto height = encode_u64(state.height);
  const auto fee_pool = encode_u64(state.fee_pool);
  insert.bind_integer(1, 1);
  insert.bind_blob(2, canonical_genesis);
  insert.bind_blob(3, tagged_bytes(state.parameters.chain_id));
  insert.bind_blob(4, supply_limit);
  insert.bind_blob(5, total_supply);
  insert.bind_blob(6, fixed_fee);
  insert.bind_blob(7, height);
  insert.bind_blob(8, fee_pool);
  insert.bind_blob(9, tagged_bytes(genesis_root));
  require_done(insert, SQLiteLedgerError::storage_failure);
}

void install_accounts(Connection& connection, const pv1::State& state) {
  Statement insert = connection.prepare(
      "INSERT INTO accounts(account_id, balance, nonce) VALUES(?, ?, ?)");
  for (const auto& [account_id, account] : state.accounts) {
    const auto balance = encode_u64(account.balance);
    const auto nonce = encode_u64(account.nonce);
    insert.bind_blob(1, tagged_bytes(account_id));
    insert.bind_blob(2, balance);
    insert.bind_blob(3, nonce);
    require_done(insert, SQLiteLedgerError::storage_failure);
    insert.reset();
  }
}

void validate_schema_objects(Connection& connection) {
  Statement objects = connection.prepare(
      "SELECT type, name, tbl_name, sql "
      "FROM main.sqlite_schema ORDER BY type, name");
  std::array<const TableSpec*, kTables.size()> ordered{{
      &kTables[1],
      &kTables[3],
      &kTables[2],
      &kTables[0],
      &kTables[4],
  }};
  for (const auto* table : ordered) {
    require_row(objects, SQLiteLedgerError::schema_mismatch);
    if (objects.column_count() != 4 ||
        !text_column(objects, 0, "table") ||
        !text_column(objects, 1, table->name) ||
        !text_column(objects, 2, table->name) ||
        !text_column(objects, 3, table->ddl)) {
      fail(SQLiteLedgerError::schema_mismatch);
    }
  }
  require_done(objects, SQLiteLedgerError::schema_mismatch);
}

void validate_table_list(Connection& connection, const TableSpec& table) {
  Statement list = connection.prepare(table.table_list_sql);
  require_row(list, SQLiteLedgerError::schema_mismatch);
  if (list.column_count() != 6 ||
      !text_column(list, 0, "main") ||
      !text_column(list, 1, table.name) ||
      !text_column(list, 2, "table") ||
      !integer_column(
          list, 3, static_cast<std::int64_t>(table.columns.size())) ||
      !integer_column(list, 4, 1) ||
      !integer_column(list, 5, 1)) {
    fail(SQLiteLedgerError::schema_mismatch);
  }
  require_done(list, SQLiteLedgerError::schema_mismatch);
}

void validate_columns(Connection& connection, const TableSpec& table) {
  Statement columns = connection.prepare(table.table_xinfo_sql);
  std::size_t index = 0;
  for (const auto& expected : table.columns) {
    require_row(columns, SQLiteLedgerError::schema_mismatch);
    if (columns.column_count() != 7 ||
        !integer_column(
            columns, 0, static_cast<std::int64_t>(index)) ||
        !text_column(columns, 1, expected.name) ||
        !text_column(columns, 2, expected.type) ||
        !integer_column(columns, 3, 1) ||
        columns.column_type(4) != SQLITE_NULL ||
        !integer_column(
            columns, 5, expected.primary_key_position) ||
        !integer_column(columns, 6, 0)) {
      fail(SQLiteLedgerError::schema_mismatch);
    }
    ++index;
  }
  require_done(columns, SQLiteLedgerError::schema_mismatch);
}

void validate_primary_index(Connection& connection, const TableSpec& table) {
  Statement indexes = connection.prepare(table.index_list_sql);
  require_row(indexes, SQLiteLedgerError::schema_mismatch);
  if (indexes.column_count() != 5 ||
      !integer_column(indexes, 0, 0) ||
      !text_column(indexes, 1, table.primary_index_name) ||
      !integer_column(indexes, 2, 1) ||
      !text_column(indexes, 3, "pk") ||
      !integer_column(indexes, 4, 0)) {
    fail(SQLiteLedgerError::schema_mismatch);
  }
  require_done(indexes, SQLiteLedgerError::schema_mismatch);

  Statement details = connection.prepare(table.index_xinfo_sql);
  std::size_t index = 0;
  for (const auto& expected : table.columns) {
    require_row(details, SQLiteLedgerError::schema_mismatch);
    if (details.column_count() != 6 ||
        !integer_column(
            details, 0, static_cast<std::int64_t>(index)) ||
        !integer_column(
            details, 1, static_cast<std::int64_t>(index)) ||
        !text_column(details, 2, expected.name) ||
        !integer_column(details, 3, 0) ||
        !text_column(details, 4, "BINARY") ||
        !integer_column(
            details, 5, expected.primary_key_position == 0 ? 0 : 1)) {
      fail(SQLiteLedgerError::schema_mismatch);
    }
    ++index;
  }
  require_done(details, SQLiteLedgerError::schema_mismatch);
}

void validate_foreign_keys(Connection& connection, const TableSpec& table) {
  Statement keys = connection.prepare(table.foreign_key_list_sql);
  if (!table.has_block_foreign_key) {
    require_done(keys, SQLiteLedgerError::schema_mismatch);
    return;
  }

  require_row(keys, SQLiteLedgerError::schema_mismatch);
  if (keys.column_count() != 8 ||
      !integer_column(keys, 0, 0) ||
      !integer_column(keys, 1, 0) ||
      !text_column(keys, 2, "blocks") ||
      !text_column(keys, 3, "height") ||
      !text_column(keys, 4, "height") ||
      !text_column(keys, 5, "RESTRICT") ||
      !text_column(keys, 6, "RESTRICT") ||
      !text_column(keys, 7, "NONE")) {
    fail(SQLiteLedgerError::schema_mismatch);
  }
  require_done(keys, SQLiteLedgerError::schema_mismatch);
}

void require_empty_table(Connection& connection, const char* sql) {
  Statement rows = connection.prepare(sql);
  require_done(rows, SQLiteLedgerError::state_mismatch);
}

std::map<pv1::AccountId, pv1::Account> load_accounts(
    Connection& connection,
    std::size_t expected_count) {
  Statement rows = connection.prepare(
      "SELECT account_id, balance, nonce "
      "FROM accounts ORDER BY account_id");
  std::map<pv1::AccountId, pv1::Account> accounts;
  std::optional<pv1::AccountId> previous;
  while (checked_step(rows) == SQLITE_ROW) {
    if (rows.column_count() != 3 ||
        accounts.size() >= expected_count) {
      fail(SQLiteLedgerError::state_mismatch);
    }
    const auto account_id = decode_tagged_hash<pv1::AccountId>(
        rows, 0, SQLiteLedgerError::state_mismatch);
    const auto balance =
        decode_u64(rows, 1, SQLiteLedgerError::state_mismatch);
    const auto nonce =
        decode_u64(rows, 2, SQLiteLedgerError::state_mismatch);
    if ((previous && !(*previous < account_id)) ||
        !accounts.emplace(account_id, pv1::Account{balance, nonce}).second) {
      fail(SQLiteLedgerError::state_mismatch);
    }
    previous = account_id;
  }
  if (accounts.size() != expected_count) {
    fail(SQLiteLedgerError::state_mismatch);
  }
  return accounts;
}

}  // namespace

void install_schema_v1(
    Connection& connection,
    std::span<const std::uint8_t> canonical_genesis,
    const pv1::Ledger& genesis_ledger,
    const pv1::StateRoot& genesis_root) {
  if (connection.autocommit()) {
    fail(SQLiteLedgerError::storage_failure);
  }
  require_trusted_genesis(
      canonical_genesis, genesis_ledger, genesis_root);
  if (genesis_ledger.state().height != 0) {
    fail(SQLiteLedgerError::state_mismatch);
  }

  connection.execute("PRAGMA main.application_id = 1347636292");
  connection.execute("PRAGMA main.user_version = 1");
  for (const auto& table : kTables) connection.execute(table.ddl);
  install_metadata(
      connection, canonical_genesis, genesis_ledger.state(), genesis_root);
  install_accounts(connection, genesis_ledger.state());
}

void validate_integrity(Connection& connection) {
  Statement integrity =
      connection.prepare("PRAGMA main.integrity_check");
  require_row(integrity, SQLiteLedgerError::integrity_failure);
  if (integrity.column_count() != 1 ||
      !text_column(integrity, 0, "ok")) {
    fail(SQLiteLedgerError::integrity_failure);
  }
  require_done(integrity, SQLiteLedgerError::integrity_failure);

  Statement foreign_keys =
      connection.prepare("PRAGMA main.foreign_key_check");
  require_done(foreign_keys, SQLiteLedgerError::integrity_failure);
}

void validate_schema_v1(Connection& connection) {
  if (connection.scalar_integer("PRAGMA main.application_id") !=
          kApplicationId ||
      connection.scalar_integer("PRAGMA main.user_version") !=
          kSchemaVersion) {
    fail(SQLiteLedgerError::schema_mismatch);
  }
  validate_schema_objects(connection);
  for (const auto& table : kTables) {
    validate_table_list(connection, table);
    validate_columns(connection, table);
    validate_primary_index(connection, table);
    validate_foreign_keys(connection, table);
  }
}

pv1::Ledger load_height_zero(
    Connection& connection,
    std::span<const std::uint8_t> expected_genesis,
    const pv1::Ledger& trusted_genesis_ledger,
    const pv1::StateRoot& trusted_genesis_root) {
  require_trusted_genesis(
      expected_genesis, trusted_genesis_ledger, trusted_genesis_root);

  Statement metadata = connection.prepare(
      "SELECT singleton, canonical_genesis, chain_id, supply_limit, "
      "total_supply, fixed_fee, current_height, fee_pool, "
      "current_state_root "
      "FROM ledger_meta ORDER BY singleton");
  require_row(metadata, SQLiteLedgerError::state_mismatch);
  if (metadata.column_count() != 9 ||
      !integer_column(metadata, 0, 1) ||
      metadata.column_type(1) != SQLITE_BLOB) {
    fail(SQLiteLedgerError::state_mismatch);
  }
  const auto stored_genesis = metadata.column_blob(1);
  if (stored_genesis.size() != expected_genesis.size() ||
      !std::equal(
          stored_genesis.begin(), stored_genesis.end(),
          expected_genesis.begin())) {
    fail(SQLiteLedgerError::genesis_mismatch);
  }

  const auto chain_id = decode_tagged_hash<pv1::ChainId>(
      metadata, 2, SQLiteLedgerError::state_mismatch);
  const auto supply_limit =
      decode_u64(metadata, 3, SQLiteLedgerError::state_mismatch);
  const auto total_supply =
      decode_u64(metadata, 4, SQLiteLedgerError::state_mismatch);
  const auto fixed_fee =
      decode_u64(metadata, 5, SQLiteLedgerError::state_mismatch);
  const auto height =
      decode_u64(metadata, 6, SQLiteLedgerError::state_mismatch);
  const auto fee_pool =
      decode_u64(metadata, 7, SQLiteLedgerError::state_mismatch);
  const auto stored_root = decode_tagged_hash<pv1::StateRoot>(
      metadata, 8, SQLiteLedgerError::state_mismatch);
  require_done(metadata, SQLiteLedgerError::state_mismatch);
  if (height != 0) fail(SQLiteLedgerError::state_mismatch);

  require_empty_table(
      connection, "SELECT 1 FROM blocks LIMIT 1");
  require_empty_table(
      connection, "SELECT 1 FROM admitted_transactions LIMIT 1");
  require_empty_table(
      connection, "SELECT 1 FROM snapshots LIMIT 1");

  pv1::State persisted_state{
      pv1::Parameters{
          chain_id,
          supply_limit,
          total_supply,
          fixed_fee,
      },
      height,
      fee_pool,
      load_accounts(
          connection, trusted_genesis_ledger.state().accounts.size()),
  };
  auto restored = pv1::restore_ledger(
      std::move(persisted_state),
      trusted_genesis_ledger.state().parameters,
      stored_root);
  if (!std::holds_alternative<pv1::Ledger>(restored.result)) {
    fail(SQLiteLedgerError::state_mismatch);
  }
  auto ledger = std::get<pv1::Ledger>(std::move(restored.result));
  if (stored_root != trusted_genesis_root ||
      ledger.state() != trusted_genesis_ledger.state() ||
      require_current_root(
          ledger, SQLiteLedgerError::state_mismatch) !=
          trusted_genesis_root) {
    fail(SQLiteLedgerError::state_mismatch);
  }
  return ledger;
}

}  // namespace protocol::storage::internal
