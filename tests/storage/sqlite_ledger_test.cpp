#include "protocol/storage/sqlite_ledger.hpp"
#include "protocol/v1/ledger.hpp"

#include "../../tools/protocol-vectors/vector_common.hpp"

#include <sqlite3.h>

#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <type_traits>
#include <utility>
#include <variant>

namespace pv = protocol_vectors;
namespace ps = protocol::storage;
namespace p = protocol::v1;

namespace {

static_assert(!std::is_copy_constructible_v<ps::SQLiteLedger>);
static_assert(!std::is_copy_assignable_v<ps::SQLiteLedger>);
static_assert(!std::is_move_assignable_v<ps::SQLiteLedger>);
static_assert(std::is_nothrow_move_constructible_v<ps::SQLiteLedger>);
static_assert(std::is_nothrow_destructible_v<ps::SQLiteLedger>);

class DatabaseFiles {
 public:
  explicit DatabaseFiles(std::filesystem::path path)
      : path_(std::move(path)) {
    remove();
  }

  ~DatabaseFiles() { remove(); }

  const std::filesystem::path& path() const noexcept { return path_; }

 private:
  void remove() noexcept {
    std::error_code ignored;
    std::filesystem::remove(path_, ignored);
    std::filesystem::remove(path_.string() + "-journal", ignored);
    std::filesystem::remove(path_.string() + "-wal", ignored);
    std::filesystem::remove(path_.string() + "-shm", ignored);
  }

  std::filesystem::path path_;
};

p::Bytes genesis_bytes(const pv::Values& values) {
  return pv::hex_decode(values.at("genesis"));
}

ps::LedgerHead expected_head(const p::Bytes& genesis) {
  auto loaded = p::load_genesis(genesis);
  pv::require(std::holds_alternative<p::Ledger>(loaded.result),
              "fixture genesis rejected");
  auto ledger = std::get<p::Ledger>(std::move(loaded.result));
  const auto root = ledger.current_state_root();
  pv::require(std::holds_alternative<p::StateRoot>(root),
              "fixture root rejected");
  return ps::LedgerHead{ledger.state(), std::get<p::StateRoot>(root)};
}

ps::SQLiteLedger take_ledger(
    ps::SQLiteLedgerResult result,
    std::string_view message) {
  pv::require(std::holds_alternative<ps::SQLiteLedger>(result.result),
              message);
  return std::get<ps::SQLiteLedger>(std::move(result.result));
}

void require_error(ps::SQLiteLedgerResult result,
                   ps::SQLiteLedgerError expected,
                   std::string_view message) {
  pv::require(
      std::holds_alternative<ps::SQLiteLedgerError>(result.result) &&
          std::get<ps::SQLiteLedgerError>(result.result) == expected,
      message);
}

void require_failure(ps::SQLiteLedgerResult result,
                     std::string_view message) {
  pv::require(
      std::holds_alternative<ps::SQLiteLedgerError>(result.result),
      message);
}

void raw_execute(const std::filesystem::path& path, const std::string& sql) {
  sqlite3* database = nullptr;
  const auto opened = sqlite3_open_v2(
      path.c_str(), &database,
      SQLITE_OPEN_READWRITE | SQLITE_OPEN_PRIVATECACHE |
          SQLITE_OPEN_NOFOLLOW | SQLITE_OPEN_EXRESCODE,
      nullptr);
  if (opened != SQLITE_OK) {
    if (database != nullptr) sqlite3_close(database);
    throw std::runtime_error("raw SQLite open failed");
  }
  const auto executed =
      sqlite3_exec(database, sql.c_str(), nullptr, nullptr, nullptr);
  const auto closed = sqlite3_close(database);
  pv::require(executed == SQLITE_OK, "raw SQLite execution failed");
  pv::require(closed == SQLITE_OK, "raw SQLite close failed");
}

std::string raw_scalar_text(
    const std::filesystem::path& path,
    const char* sql) {
  sqlite3* database = nullptr;
  pv::require(
      sqlite3_open_v2(
          path.c_str(), &database,
          SQLITE_OPEN_READWRITE | SQLITE_OPEN_PRIVATECACHE |
              SQLITE_OPEN_NOFOLLOW | SQLITE_OPEN_EXRESCODE,
          nullptr) == SQLITE_OK,
      "raw scalar open failed");
  sqlite3_stmt* statement = nullptr;
  pv::require(
      sqlite3_prepare_v2(database, sql, -1, &statement, nullptr) ==
          SQLITE_OK,
      "raw scalar prepare failed");
  pv::require(sqlite3_step(statement) == SQLITE_ROW,
              "raw scalar row missing");
  const auto* raw = sqlite3_column_text(statement, 0);
  pv::require(raw != nullptr, "raw scalar text missing");
  const std::string value(reinterpret_cast<const char*>(raw));
  pv::require(sqlite3_step(statement) == SQLITE_DONE,
              "raw scalar extra row");
  pv::require(sqlite3_finalize(statement) == SQLITE_OK,
              "raw scalar finalize failed");
  pv::require(sqlite3_close(database) == SQLITE_OK,
              "raw scalar close failed");
  return value;
}

void create_and_close(
    const std::filesystem::path& path,
    const p::Bytes& genesis) {
  auto ledger = take_ledger(
      ps::create_sqlite_ledger(path, genesis),
      "baseline create failed");
  pv::require(ledger.read_head() == expected_head(genesis),
              "baseline head mismatch");
}

int lock_probe(
    const std::filesystem::path& path,
    const p::Bytes& genesis) {
  auto result = ps::open_sqlite_ledger(path, genesis);
  return std::holds_alternative<ps::SQLiteLedgerError>(result.result) &&
                 std::get<ps::SQLiteLedgerError>(result.result) ==
                     ps::SQLiteLedgerError::lock_unavailable
             ? 0
             : 1;
}

void require_lock_probe(
    const char* executable,
    const std::string& vector_path,
    const std::filesystem::path& database_path) {
  const auto child = fork();
  pv::require(child >= 0, "fork failed");
  if (child == 0) {
    execl(
        executable, executable, "--lock-probe", vector_path.c_str(),
        database_path.c_str(), static_cast<char*>(nullptr));
    _exit(127);
  }
  int status = 0;
  pv::require(waitpid(child, &status, 0) == child, "waitpid failed");
  pv::require(WIFEXITED(status) && WEXITSTATUS(status) == 0,
              "second process acquired live database");
}

void verify_create_reopen_and_lock(
    const pv::Values& values,
    const std::filesystem::path& prefix,
    const char* executable,
    const std::string& vector_path) {
  DatabaseFiles files(prefix.string() + "-lifecycle.db");
  const auto genesis = genesis_bytes(values);
  const auto expected = expected_head(genesis);

  {
    auto created = take_ledger(
        ps::create_sqlite_ledger(files.path(), genesis),
        "valid database creation rejected");
    pv::require(created.read_head() == expected,
                "created head mismatch");
    auto caller_copy = created.read_head();
    caller_copy.state.accounts.clear();
    pv::require(created.read_head() == expected,
                "read head exposed borrowed state");

    ps::SQLiteLedger moved(std::move(created));
    pv::require(moved.read_head() == expected, "move changed head");
    require_lock_probe(
        executable, vector_path, files.path());
    require_error(
        ps::open_sqlite_ledger(files.path(), genesis),
        ps::SQLiteLedgerError::lock_unavailable,
        "second in-process open acquired live database");
    require_error(
        ps::create_sqlite_ledger(files.path(), genesis),
        ps::SQLiteLedgerError::path_already_exists,
        "creation overwrote existing database");
  }

  struct stat metadata {};
  pv::require(::stat(files.path().c_str(), &metadata) == 0,
              "database stat failed");
  pv::require((metadata.st_mode & 0077) == 0,
              "database permissions are not private");

  {
    auto reopened = take_ledger(
        ps::open_sqlite_ledger(files.path(), genesis),
        "clean reopen rejected");
    pv::require(reopened.read_head() == expected,
                "reopened head mismatch");
  }
  auto repeated = take_ledger(
      ps::open_sqlite_ledger(files.path(), genesis),
      "repeated reopen rejected");
  pv::require(repeated.read_head() == expected,
              "repeated reopen head mismatch");
}

void verify_path_failures(
    const pv::Values& values,
    const std::filesystem::path& prefix) {
  const auto genesis = genesis_bytes(values);

  DatabaseFiles invalid_target(prefix.string() + "-invalid.db");
  auto invalid = genesis;
  invalid.pop_back();
  require_error(
      ps::create_sqlite_ledger(invalid_target.path(), invalid),
      ps::SQLiteLedgerError::invalid_genesis,
      "invalid genesis accepted");
  pv::require(!std::filesystem::exists(invalid_target.path()),
              "invalid genesis created a file");

  DatabaseFiles missing(prefix.string() + "-missing.db");
  require_error(
      ps::open_sqlite_ledger(missing.path(), genesis),
      ps::SQLiteLedgerError::path_not_found,
      "missing open created or accepted a database");
  pv::require(!std::filesystem::exists(missing.path()),
              "missing open created a file");

  require_error(
      ps::create_sqlite_ledger(":memory:", genesis),
      ps::SQLiteLedgerError::invalid_path,
      "memory database path accepted");
  require_error(
      ps::create_sqlite_ledger("file:uri.db", genesis),
      ps::SQLiteLedgerError::invalid_path,
      "URI-like database path accepted");
  const std::string embedded_null("bad\0path", 8);
  require_error(
      ps::create_sqlite_ledger(
          std::filesystem::path(embedded_null), genesis),
      ps::SQLiteLedgerError::invalid_path,
      "embedded-NUL database path accepted");

  DatabaseFiles sentinel(prefix.string() + "-sentinel.db");
  {
    std::ofstream output(sentinel.path(), std::ios::binary);
    output << "sentinel";
  }
  require_error(
      ps::create_sqlite_ledger(sentinel.path(), genesis),
      ps::SQLiteLedgerError::path_already_exists,
      "existing sentinel overwritten");
  std::ifstream input(sentinel.path(), std::ios::binary);
  std::string retained;
  input >> retained;
  pv::require(retained == "sentinel", "sentinel contents changed");
  require_failure(
      ps::open_sqlite_ledger(sentinel.path(), genesis),
      "non-SQLite sentinel accepted");

  DatabaseFiles directory(prefix.string() + "-directory");
  std::filesystem::create_directory(directory.path());
  require_error(
      ps::open_sqlite_ledger(directory.path(), genesis),
      ps::SQLiteLedgerError::invalid_path,
      "directory database path accepted");

  DatabaseFiles link_target(prefix.string() + "-link-target.db");
  DatabaseFiles symbolic(prefix.string() + "-symbolic.db");
  {
    std::ofstream output(link_target.path());
  }
  std::filesystem::create_symlink(link_target.path(), symbolic.path());
  require_error(
      ps::open_sqlite_ledger(symbolic.path(), genesis),
      ps::SQLiteLedgerError::invalid_path,
      "symbolic-link database path accepted");

  DatabaseFiles hard_alias(prefix.string() + "-hard-alias.db");
  std::filesystem::create_hard_link(link_target.path(), hard_alias.path());
  require_error(
      ps::open_sqlite_ledger(hard_alias.path(), genesis),
      ps::SQLiteLedgerError::invalid_path,
      "hard-linked database path accepted");
}

void verify_genesis_and_schema_rejection(
    const pv::Values& values,
    const std::filesystem::path& prefix) {
  const auto genesis = genesis_bytes(values);

  DatabaseFiles wrong_genesis(prefix.string() + "-wrong-genesis.db");
  create_and_close(wrong_genesis.path(), genesis);
  auto alternate = genesis;
  alternate[33] ^= 1U;
  require_error(
      ps::open_sqlite_ledger(wrong_genesis.path(), alternate),
      ps::SQLiteLedgerError::genesis_mismatch,
      "wrong configured genesis accepted");

  DatabaseFiles application(prefix.string() + "-application.db");
  create_and_close(application.path(), genesis);
  raw_execute(application.path(), "PRAGMA application_id=1;");
  require_error(
      ps::open_sqlite_ledger(application.path(), genesis),
      ps::SQLiteLedgerError::schema_mismatch,
      "wrong application ID accepted");

  DatabaseFiles version(prefix.string() + "-version.db");
  create_and_close(version.path(), genesis);
  raw_execute(version.path(), "PRAGMA user_version=2;");
  require_error(
      ps::open_sqlite_ledger(version.path(), genesis),
      ps::SQLiteLedgerError::schema_mismatch,
      "wrong schema version accepted");

  DatabaseFiles extra(prefix.string() + "-extra-schema.db");
  create_and_close(extra.path(), genesis);
  raw_execute(extra.path(), "CREATE TABLE unexpected(value BLOB) STRICT;");
  require_error(
      ps::open_sqlite_ledger(extra.path(), genesis),
      ps::SQLiteLedgerError::schema_mismatch,
      "extra schema object accepted");

  DatabaseFiles missing(prefix.string() + "-missing-schema.db");
  create_and_close(missing.path(), genesis);
  raw_execute(missing.path(), "DROP TABLE snapshots;");
  require_error(
      ps::open_sqlite_ledger(missing.path(), genesis),
      ps::SQLiteLedgerError::schema_mismatch,
      "missing schema object accepted");
}

void verify_state_and_integrity_rejection(
    const pv::Values& values,
    const std::filesystem::path& prefix) {
  const auto genesis = genesis_bytes(values);

  DatabaseFiles account(prefix.string() + "-account.db");
  create_and_close(account.path(), genesis);
  raw_execute(
      account.path(),
      "UPDATE accounts SET balance=X'0000000000000000' "
      "WHERE account_id=(SELECT account_id FROM accounts "
      "ORDER BY account_id LIMIT 1);");
  require_error(
      ps::open_sqlite_ledger(account.path(), genesis),
      ps::SQLiteLedgerError::state_mismatch,
      "materialized account corruption accepted");

  DatabaseFiles root(prefix.string() + "-root.db");
  create_and_close(root.path(), genesis);
  raw_execute(
      root.path(),
      "UPDATE ledger_meta SET current_state_root=zeroblob(32);");
  require_error(
      ps::open_sqlite_ledger(root.path(), genesis),
      ps::SQLiteLedgerError::state_mismatch,
      "metadata root corruption accepted");

  DatabaseFiles fee(prefix.string() + "-fee.db");
  create_and_close(fee.path(), genesis);
  raw_execute(
      fee.path(),
      "PRAGMA ignore_check_constraints=ON;"
      "UPDATE ledger_meta SET fixed_fee=X'00000000000003E9';");
  require_error(
      ps::open_sqlite_ledger(fee.path(), genesis),
      ps::SQLiteLedgerError::integrity_failure,
      "fixed-fee projection corruption accepted");

  DatabaseFiles history(prefix.string() + "-history.db");
  create_and_close(history.path(), genesis);
  const auto header = values.at("block_header");
  raw_execute(
      history.path(),
      "INSERT INTO blocks VALUES("
      "X'0000000000000001',"
      "X'" +
          values.at("previous_state_root") + "',"
      "X'" +
          values.at("transaction_root") + "',"
      "X'" +
          values.at("resulting_state_root") + "',"
      "X'" +
          header.substr(header.size() - 8) + "',"
      "X'" +
          header + "',"
      "X'" +
          values.at("block_id") + "');");
  require_error(
      ps::open_sqlite_ledger(history.path(), genesis),
      ps::SQLiteLedgerError::state_mismatch,
      "nonzero height history accepted by height-zero adapter");

  DatabaseFiles foreign(prefix.string() + "-foreign.db");
  create_and_close(foreign.path(), genesis);
  const auto receipt = values.at("receipt0");
  raw_execute(
      foreign.path(),
      "PRAGMA foreign_keys=OFF;"
      "INSERT INTO admitted_transactions VALUES("
      "X'0000000000000001',X'00000000',X'" +
          values.at("raw0") + "',X'" + receipt.substr(12, 64) +
          "',X'" + receipt + "');");
  require_error(
      ps::open_sqlite_ledger(foreign.path(), genesis),
      ps::SQLiteLedgerError::integrity_failure,
      "foreign-key corruption accepted");

  DatabaseFiles truncated(prefix.string() + "-truncated.db");
  create_and_close(truncated.path(), genesis);
  std::filesystem::resize_file(truncated.path(), 100);
  require_failure(
      ps::open_sqlite_ledger(truncated.path(), genesis),
      "truncated database accepted");
}

void verify_unexpected_journal_mode(
    const pv::Values& values,
    const std::filesystem::path& prefix) {
  const auto genesis = genesis_bytes(values);
  DatabaseFiles files(prefix.string() + "-wal.db");
  create_and_close(files.path(), genesis);
  pv::require(
      raw_scalar_text(files.path(), "PRAGMA journal_mode=WAL;") == "wal",
      "failed to install WAL mode");
  require_error(
      ps::open_sqlite_ledger(files.path(), genesis),
      ps::SQLiteLedgerError::configuration_mismatch,
      "unexpected WAL mode accepted");
  pv::require(
      raw_scalar_text(files.path(), "PRAGMA journal_mode;") == "wal",
      "failed open silently changed WAL mode");
}

}  // namespace

int main(int argc, char** argv) {
  try {
    if (argc == 4 && std::string_view(argv[1]) == "--lock-probe") {
      const auto values = pv::load_values(argv[2]);
      return lock_probe(argv[3], genesis_bytes(values));
    }
    pv::require(
        argc == 3,
        "usage: storage_sqlite_ledger_tests VECTOR_FILE PATH_PREFIX");
    pv::require(sodium_init() >= 0, "libsodium initialization");
    const auto values = pv::load_values(argv[1]);
    const std::filesystem::path prefix(argv[2]);
    verify_create_reopen_and_lock(values, prefix, argv[0], argv[1]);
    verify_path_failures(values, prefix);
    verify_genesis_and_schema_rejection(values, prefix);
    verify_state_and_integrity_rejection(values, prefix);
    verify_unexpected_journal_mode(values, prefix);
    std::cout << "SQLite ledger tests: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "SQLite ledger tests: failed: " << error.what() << '\n';
    return 1;
  }
}
