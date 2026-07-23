#include <sqlite3.h>

#include <cstdint>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>

namespace {

constexpr std::string_view kExpectedSourceId =
    "2026-06-26 20:14:12 "
    "d4c0e51e4aeb96955b99185ab9cde75c339e2c29c3f3f12428d364a10d782c62";

static_assert(SQLITE_VERSION_NUMBER == 3'053'003);
static_assert(std::string_view(SQLITE_SOURCE_ID) == kExpectedSourceId);

void require(bool condition, std::string_view message) {
  if (!condition) throw std::runtime_error(std::string(message));
}

class Database {
 public:
  Database() = default;
  ~Database() {
    if (handle_ != nullptr) sqlite3_close(handle_);
  }

  Database(const Database&) = delete;
  Database& operator=(const Database&) = delete;

  sqlite3* get() const noexcept { return handle_; }

  void open(const std::filesystem::path& path) {
    const auto result = sqlite3_open_v2(
        path.c_str(), &handle_,
        SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE |
            SQLITE_OPEN_PRIVATECACHE | SQLITE_OPEN_EXRESCODE,
        nullptr);
    if (result != SQLITE_OK) {
      const std::string detail =
          handle_ == nullptr ? "no database handle" : sqlite3_errmsg(handle_);
      throw std::runtime_error("SQLite open failed: " + detail);
    }
  }

  void close() {
    require(handle_ != nullptr, "SQLite close without open");
    const auto result = sqlite3_close(handle_);
    require(result == SQLITE_OK, "SQLite close failed");
    handle_ = nullptr;
  }

 private:
  sqlite3* handle_ = nullptr;
};

class TestFiles {
 public:
  explicit TestFiles(std::filesystem::path database)
      : database_(std::move(database)) {
    remove();
  }

  ~TestFiles() { remove(); }

  const std::filesystem::path& database() const noexcept {
    return database_;
  }

 private:
  void remove() noexcept {
    std::error_code ignored;
    std::filesystem::remove(database_, ignored);
    std::filesystem::remove(database_.string() + "-journal", ignored);
    std::filesystem::remove(database_.string() + "-wal", ignored);
    std::filesystem::remove(database_.string() + "-shm", ignored);
  }

  std::filesystem::path database_;
};

void execute(sqlite3* database, const char* sql) {
  char* raw_error = nullptr;
  const auto result =
      sqlite3_exec(database, sql, nullptr, nullptr, &raw_error);
  const std::string detail =
      raw_error == nullptr ? sqlite3_errmsg(database) : raw_error;
  sqlite3_free(raw_error);
  if (result != SQLITE_OK) {
    throw std::runtime_error("SQLite statement failed: " + detail);
  }
}

std::string scalar_text(sqlite3* database, const char* sql) {
  sqlite3_stmt* statement = nullptr;
  require(sqlite3_prepare_v2(database, sql, -1, &statement, nullptr) ==
              SQLITE_OK,
          "SQLite prepare failed");
  const auto first_step = sqlite3_step(statement);
  if (first_step != SQLITE_ROW) {
    sqlite3_finalize(statement);
    throw std::runtime_error("SQLite scalar returned no row");
  }
  const auto* raw_value = sqlite3_column_text(statement, 0);
  const std::string value =
      raw_value == nullptr
          ? std::string{}
          : reinterpret_cast<const char*>(raw_value);
  const auto second_step = sqlite3_step(statement);
  const auto finalize_result = sqlite3_finalize(statement);
  require(second_step == SQLITE_DONE, "SQLite scalar returned extra row");
  require(finalize_result == SQLITE_OK, "SQLite finalize failed");
  return value;
}

std::int64_t scalar_integer(sqlite3* database, const char* sql) {
  sqlite3_stmt* statement = nullptr;
  require(sqlite3_prepare_v2(database, sql, -1, &statement, nullptr) ==
              SQLITE_OK,
          "SQLite integer prepare failed");
  const auto first_step = sqlite3_step(statement);
  if (first_step != SQLITE_ROW) {
    sqlite3_finalize(statement);
    throw std::runtime_error("SQLite integer returned no row");
  }
  const auto value = sqlite3_column_int64(statement, 0);
  const auto second_step = sqlite3_step(statement);
  const auto finalize_result = sqlite3_finalize(statement);
  require(second_step == SQLITE_DONE,
          "SQLite integer returned extra row");
  require(finalize_result == SQLITE_OK,
          "SQLite integer finalize failed");
  return value;
}

void verify_build_identity() {
  require(std::string_view(sqlite3_libversion()) == "3.53.3",
          "unexpected SQLite version");
  require(sqlite3_libversion_number() == 3'053'003,
          "unexpected SQLite numeric version");
  require(std::string_view(sqlite3_sourceid()) == kExpectedSourceId,
          "unexpected SQLite source ID");
  require(sqlite3_threadsafe() == 1, "SQLite is not serialized");
  require(sqlite3_compileoption_used("DQS=0") != 0,
          "SQLite DQS hardening missing");
  require(sqlite3_compileoption_used("ENABLE_API_ARMOR") != 0,
          "SQLite API armor missing");
  require(sqlite3_compileoption_used("OMIT_LOAD_EXTENSION") != 0,
          "SQLite loadable extensions enabled");
  require(sqlite3_compileoption_used("OMIT_JSON") != 0,
          "SQLite JSON support enabled");
  require(sqlite3_compileoption_used("ENABLE_CARRAY") == 0,
          "SQLite carray support enabled");
  require(sqlite3_compileoption_used("ENABLE_MATH_FUNCTIONS") == 0,
          "SQLite math functions enabled");
}

void verify_transaction_and_reopen(const std::filesystem::path& path) {
  Database database;
  database.open(path);
  execute(database.get(), "PRAGMA journal_mode=DELETE;");
  execute(database.get(), "PRAGMA synchronous=EXTRA;");
  require(scalar_text(database.get(), "PRAGMA journal_mode;") == "delete",
          "SQLite rollback journal unavailable");
  require(scalar_integer(database.get(), "PRAGMA synchronous;") == 3,
          "SQLite EXTRA synchronization unavailable");
  require(scalar_integer(database.get(), "PRAGMA trusted_schema;") == 0,
          "SQLite trusted schema enabled by default");
  execute(
      database.get(),
      "CREATE TABLE probe("
      "singleton INTEGER PRIMARY KEY CHECK(singleton=1),"
      "value BLOB NOT NULL CHECK(typeof(value)='blob' AND length(value)=3)"
      ") STRICT;");
  execute(database.get(), "BEGIN IMMEDIATE;");
  execute(database.get(),
          "INSERT INTO probe(singleton,value) VALUES(1,x'000102');");
  execute(database.get(), "COMMIT;");
  database.close();

  database.open(path);
  require(scalar_text(database.get(),
                      "SELECT hex(value) FROM probe WHERE singleton=1;") ==
              "000102",
          "SQLite committed value did not survive reopen");
  execute(database.get(), "BEGIN IMMEDIATE;");
  execute(database.get(),
          "UPDATE probe SET value=x'FFFFFF' WHERE singleton=1;");
  execute(database.get(), "ROLLBACK;");
  database.close();

  database.open(path);
  require(scalar_text(database.get(),
                      "SELECT hex(value) FROM probe WHERE singleton=1;") ==
              "000102",
          "SQLite rolled-back value changed after reopen");
  database.close();
}

}  // namespace

int main(int argc, char** argv) {
  try {
    require(argc == 2, "usage: sqlite_dependency_tests DATABASE");
    TestFiles files(argv[1]);
    verify_build_identity();
    verify_transaction_and_reopen(files.database());
    std::cout << "SQLite dependency checks passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
