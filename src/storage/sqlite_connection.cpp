#include "sqlite_connection.hpp"

#include <cerrno>
#include <cstdlib>
#include <string_view>
#include <utility>

#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>

namespace protocol::storage::internal {
namespace {

[[noreturn]] void fail(SQLiteLedgerError error) {
  throw Failure{error};
}

int primary_result(int result) noexcept {
  return result & 0xff;
}

bool is_lock_result(int result) noexcept {
  const auto primary = primary_result(result);
  return primary == SQLITE_BUSY || primary == SQLITE_LOCKED;
}

int open_at(int directory, const char* name, int flags, mode_t mode = 0) {
  int descriptor;
  do {
    descriptor = ::openat(directory, name, flags, mode);
  } while (descriptor == -1 && errno == EINTR);
  return descriptor;
}

void sync_descriptor(int descriptor) {
  int result;
  do {
    result = ::fsync(descriptor);
  } while (result == -1 && errno == EINTR);
  if (result != 0) {
    fail(SQLiteLedgerError::storage_failure);
  }
}

void set_private_mode(int descriptor) {
  int result;
  do {
    result = ::fchmod(descriptor, S_IRUSR | S_IWUSR);
  } while (result == -1 && errno == EINTR);
  if (result != 0) {
    fail(SQLiteLedgerError::storage_failure);
  }
}

struct stat descriptor_status(int descriptor) {
  struct stat status {};
  int result;
  do {
    result = ::fstat(descriptor, &status);
  } while (result == -1 && errno == EINTR);
  if (result != 0) {
    fail(SQLiteLedgerError::storage_failure);
  }
  return status;
}

struct stat path_status(const std::filesystem::path& path) {
  struct stat status {};
  int result;
  do {
    result = ::lstat(path.c_str(), &status);
  } while (result == -1 && errno == EINTR);
  if (result != 0) {
    if (errno == ENOENT || errno == ENOTDIR || errno == ELOOP) {
      fail(SQLiteLedgerError::invalid_path);
    }
    fail(SQLiteLedgerError::storage_failure);
  }
  return status;
}

void require_regular_single_link(const struct stat& status) {
  if (!S_ISREG(status.st_mode) || status.st_nlink != 1) {
    fail(SQLiteLedgerError::invalid_path);
  }
}

FileDescriptor open_parent_directory(const std::filesystem::path& path) {
  const auto parent = path.parent_path();
  const auto descriptor =
      open_at(AT_FDCWD, parent.c_str(),
              O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
  if (descriptor == -1) {
    if (errno == ENOENT || errno == ENOTDIR || errno == ELOOP) {
      fail(SQLiteLedgerError::invalid_path);
    }
    fail(SQLiteLedgerError::storage_failure);
  }
  return FileDescriptor(descriptor);
}

SQLiteLedgerError reservation_open_error(int error) noexcept {
  if (error == EEXIST) {
    return SQLiteLedgerError::path_already_exists;
  }
  if (error == ENOENT || error == ENOTDIR || error == ELOOP ||
      error == EISDIR || error == EINVAL) {
    return SQLiteLedgerError::invalid_path;
  }
  return SQLiteLedgerError::storage_failure;
}

FileDescriptor reserve_anchor(const std::filesystem::path& path) {
  auto parent = open_parent_directory(path);
  const auto name = path.filename().native();
  constexpr auto kFlags =
      O_RDWR | O_CLOEXEC | O_NOFOLLOW | O_CREAT | O_EXCL;
  const auto descriptor = open_at(
      parent.get(), name.c_str(), kFlags, S_IRUSR | S_IWUSR);
  if (descriptor == -1) {
    fail(reservation_open_error(errno));
  }

  FileDescriptor anchor(descriptor);
  const auto status = descriptor_status(anchor.get());
  require_regular_single_link(status);
  if (status.st_size != 0) {
    fail(SQLiteLedgerError::invalid_path);
  }
  set_private_mode(anchor.get());
  sync_descriptor(anchor.get());
  sync_descriptor(parent.get());
  return anchor;
}

void prevalidate_existing_path(const std::filesystem::path& path) {
  struct stat status {};
  int result;
  do {
    result = ::lstat(path.c_str(), &status);
  } while (result == -1 && errno == EINTR);
  if (result != 0) {
    if (errno == ENOENT || errno == ENOTDIR) {
      fail(SQLiteLedgerError::path_not_found);
    }
    if (errno == ELOOP) {
      fail(SQLiteLedgerError::invalid_path);
    }
    fail(SQLiteLedgerError::storage_failure);
  }
  require_regular_single_link(status);
}

Connection open_connection(const std::filesystem::path& path) {
  constexpr int kOpenFlags =
      SQLITE_OPEN_READWRITE | SQLITE_OPEN_PRIVATECACHE |
      SQLITE_OPEN_FULLMUTEX | SQLITE_OPEN_NOFOLLOW |
      SQLITE_OPEN_EXRESCODE;

  sqlite3* database = nullptr;
  const auto path_text = path.native();
  const auto result =
      sqlite3_open_v2(path_text.c_str(), &database, kOpenFlags, nullptr);
  if (result != SQLITE_OK) {
    if (database != nullptr && sqlite3_close(database) != SQLITE_OK) {
      std::terminate();
    }
    fail(SQLiteLedgerError::storage_failure);
  }
  return Connection(database);
}

SQLiteResources open_resources(
    const std::filesystem::path& supplied_path,
    bool creating) {
  const auto path = normalize_database_path(supplied_path);
  auto anchor = creating ? reserve_anchor(path) : FileDescriptor(-1);
  if (!creating) {
    prevalidate_existing_path(path);
  }
  auto connection = open_connection(path);
  SQLiteResources resources(
      std::move(anchor), std::move(connection));
  verify_stable_path(resources, path);
  return resources;
}

void require_db_config(
    sqlite3* database,
    int operation,
    int requested,
    int expected) {
  int actual = -1;
  const auto result =
      sqlite3_db_config(database, operation, requested, &actual);
  if (result != SQLITE_OK || actual != expected) {
    fail(SQLiteLedgerError::configuration_mismatch);
  }
}

void require_setting(
    Connection& connection,
    const char* sql,
    std::int64_t expected) {
  if (connection.scalar_integer(sql) != expected) {
    fail(SQLiteLedgerError::configuration_mismatch);
  }
}

void require_setting(
    Connection& connection,
    const char* sql,
    std::string_view expected) {
  if (connection.scalar_text(sql) != expected) {
    fail(SQLiteLedgerError::configuration_mismatch);
  }
}

void require_done(int result) {
  if (result != SQLITE_DONE) {
    fail(SQLiteLedgerError::storage_failure);
  }
}

bool only_ascii_space(const char* text) noexcept {
  for (; *text != '\0'; ++text) {
    if (*text != ' ' && *text != '\t' && *text != '\n' &&
        *text != '\r' && *text != '\f' && *text != '\v') {
      return false;
    }
  }
  return true;
}

}  // namespace

FileDescriptor::FileDescriptor(int descriptor) noexcept
    : descriptor_(descriptor) {}

FileDescriptor::~FileDescriptor() noexcept {
  if (descriptor_ >= 0 && ::close(descriptor_) != 0) {
    std::terminate();
  }
}

FileDescriptor::FileDescriptor(FileDescriptor&& other) noexcept
    : descriptor_(std::exchange(other.descriptor_, -1)) {}

Statement::Statement(sqlite3* database, const char* sql)
    : statement_(nullptr) {
  if (database == nullptr || sql == nullptr) {
    fail(SQLiteLedgerError::storage_failure);
  }
  const char* tail = nullptr;
  const auto result = sqlite3_prepare_v3(
      database, sql, -1, SQLITE_PREPARE_NO_VTAB, &statement_, &tail);
  if (result != SQLITE_OK || statement_ == nullptr ||
      tail == nullptr || !only_ascii_space(tail)) {
    if (statement_ != nullptr) {
      (void)sqlite3_finalize(statement_);
      statement_ = nullptr;
    }
    fail(SQLiteLedgerError::storage_failure);
  }
}

Statement::~Statement() noexcept {
  if (statement_ != nullptr) {
    (void)sqlite3_finalize(statement_);
  }
}

Statement::Statement(Statement&& other) noexcept
    : statement_(std::exchange(other.statement_, nullptr)) {}

void Statement::bind_integer(int index, std::int64_t value) {
  if (sqlite3_bind_int64(statement_, index, value) != SQLITE_OK) {
    fail(SQLiteLedgerError::storage_failure);
  }
}

void Statement::bind_blob(
    int index,
    std::span<const std::uint8_t> value) {
  static constexpr std::uint8_t kEmptyBlob = 0;
  const auto size = static_cast<sqlite3_uint64>(value.size());
  const auto* data = value.empty() ? &kEmptyBlob : value.data();
  if (sqlite3_bind_blob64(
          statement_, index, data, size, SQLITE_TRANSIENT) != SQLITE_OK) {
    fail(SQLiteLedgerError::storage_failure);
  }
}

int Statement::step() {
  return sqlite3_step(statement_);
}

void Statement::reset() {
  const auto reset_result = sqlite3_reset(statement_);
  const auto clear_result = sqlite3_clear_bindings(statement_);
  if (reset_result != SQLITE_OK || clear_result != SQLITE_OK) {
    fail(SQLiteLedgerError::storage_failure);
  }
}

int Statement::column_count() const noexcept {
  return sqlite3_column_count(statement_);
}

int Statement::column_type(int index) const noexcept {
  return sqlite3_column_type(statement_, index);
}

std::int64_t Statement::column_integer(int index) const noexcept {
  return sqlite3_column_int64(statement_, index);
}

std::span<const std::uint8_t> Statement::column_blob(
    int index) const noexcept {
  static constexpr std::uint8_t kEmptyBlob = 0;
  auto* data = static_cast<const std::uint8_t*>(
      sqlite3_column_blob(statement_, index));
  const auto size = sqlite3_column_bytes(statement_, index);
  if (data == nullptr) {
    if (size != 0) {
      std::terminate();
    }
    data = &kEmptyBlob;
  }
  return {data, static_cast<std::size_t>(size)};
}

std::string Statement::column_text(int index) const {
  const auto* data = sqlite3_column_text(statement_, index);
  const auto size = sqlite3_column_bytes(statement_, index);
  if (size == 0) {
    return {};
  }
  if (data == nullptr) {
    fail(SQLiteLedgerError::storage_failure);
  }
  return {
      reinterpret_cast<const char*>(data),
      static_cast<std::size_t>(size)};
}

Connection::Connection(sqlite3* database) noexcept
    : database_(database) {}

Connection::~Connection() noexcept {
  if (database_ != nullptr && sqlite3_close(database_) != SQLITE_OK) {
    std::terminate();
  }
}

Connection::Connection(Connection&& other) noexcept
    : database_(std::exchange(other.database_, nullptr)) {}

bool Connection::autocommit() const noexcept {
  return database_ == nullptr || sqlite3_get_autocommit(database_) != 0;
}

void Connection::execute(const char* sql) {
  auto statement = prepare(sql);
  require_done(statement.step());
}

std::int64_t Connection::scalar_integer(const char* sql) {
  auto statement = prepare(sql);
  if (statement.column_count() != 1 ||
      statement.step() != SQLITE_ROW ||
      statement.column_type(0) != SQLITE_INTEGER) {
    fail(SQLiteLedgerError::storage_failure);
  }
  const auto result = statement.column_integer(0);
  require_done(statement.step());
  return result;
}

std::string Connection::scalar_text(const char* sql) {
  auto statement = prepare(sql);
  if (statement.column_count() != 1 ||
      statement.step() != SQLITE_ROW ||
      statement.column_type(0) != SQLITE_TEXT) {
    fail(SQLiteLedgerError::storage_failure);
  }
  auto result = statement.column_text(0);
  require_done(statement.step());
  return result;
}

Statement Connection::prepare(const char* sql) {
  return Statement(database_, sql);
}

SQLiteResources::SQLiteResources(
    FileDescriptor anchor,
    Connection database) noexcept
    : path_anchor(std::move(anchor)),
      connection(std::move(database)) {}

std::filesystem::path normalize_database_path(
    const std::filesystem::path& path) {
  if (path.empty() || !path.is_absolute() ||
      path.native().find('\0') != std::string::npos) {
    fail(SQLiteLedgerError::invalid_path);
  }

  const auto leaf = path.filename();
  if (leaf.empty() || leaf == "." || leaf == "..") {
    fail(SQLiteLedgerError::invalid_path);
  }

  std::error_code error;
  const auto parent =
      std::filesystem::canonical(path.parent_path(), error);
  if (error || !parent.is_absolute()) {
    fail(SQLiteLedgerError::invalid_path);
  }
  if (!std::filesystem::is_directory(parent, error) || error) {
    fail(SQLiteLedgerError::invalid_path);
  }
  return parent / leaf;
}

SQLiteResources reserve_sqlite_database(
    const std::filesystem::path& path) {
  return open_resources(path, true);
}

SQLiteResources open_sqlite_database(
    const std::filesystem::path& path) {
  return open_resources(path, false);
}

void verify_stable_path(
    const SQLiteResources& resources,
    const std::filesystem::path& supplied_path) {
  const auto path = normalize_database_path(supplied_path);
  const auto current = path_status(path);
  require_regular_single_link(current);
  if (resources.path_anchor.get() >= 0) {
    const auto anchor =
        descriptor_status(resources.path_anchor.get());
    require_regular_single_link(anchor);
    if (anchor.st_dev != current.st_dev ||
        anchor.st_ino != current.st_ino) {
      fail(SQLiteLedgerError::invalid_path);
    }
  }

  int moved = 0;
  const auto result = sqlite3_file_control(
      resources.connection.get(), "main",
      SQLITE_FCNTL_HAS_MOVED, &moved);
  if (result != SQLITE_OK) {
    fail(SQLiteLedgerError::storage_failure);
  }
  if (moved != 0) {
    fail(SQLiteLedgerError::invalid_path);
  }
}

void configure_connection(Connection& connection) {
  auto* database = connection.get();
  try {
    if (database == nullptr || !connection.autocommit() ||
        sqlite3_db_readonly(database, "main") != 0 ||
        sqlite3_extended_result_codes(database, 1) != SQLITE_OK ||
        sqlite3_busy_timeout(database, 0) != SQLITE_OK) {
      fail(SQLiteLedgerError::configuration_mismatch);
    }

    require_db_config(
        database, SQLITE_DBCONFIG_DEFENSIVE, 1, 1);
    require_db_config(
        database, SQLITE_DBCONFIG_TRUSTED_SCHEMA, 0, 0);
    require_db_config(
        database, SQLITE_DBCONFIG_ENABLE_TRIGGER, 0, 0);
    require_db_config(
        database, SQLITE_DBCONFIG_ENABLE_VIEW, 0, 0);

    connection.execute("PRAGMA trusted_schema = OFF");
    connection.execute("PRAGMA foreign_keys = ON");
    connection.execute("PRAGMA cell_size_check = ON");
    require_setting(connection, "PRAGMA main.mmap_size = 0", 0);
    connection.execute("PRAGMA main.synchronous = EXTRA");
    require_setting(
        connection, "PRAGMA main.locking_mode = EXCLUSIVE",
        "exclusive");
    require_setting(
        connection, "PRAGMA main.journal_size_limit = 0", 0);

    require_setting(connection, "PRAGMA trusted_schema", 0);
    require_setting(connection, "PRAGMA foreign_keys", 1);
    require_setting(connection, "PRAGMA cell_size_check", 1);
    require_setting(connection, "PRAGMA main.mmap_size", 0);
    require_setting(connection, "PRAGMA main.synchronous", 3);
    require_setting(
        connection, "PRAGMA main.locking_mode", "exclusive");
    require_setting(
        connection, "PRAGMA main.journal_size_limit", 0);
    require_setting(connection, "PRAGMA busy_timeout", 0);

    require_db_config(
        database, SQLITE_DBCONFIG_DEFENSIVE, -1, 1);
    require_db_config(
        database, SQLITE_DBCONFIG_TRUSTED_SCHEMA, -1, 0);
    require_db_config(
        database, SQLITE_DBCONFIG_ENABLE_TRIGGER, -1, 0);
    require_db_config(
        database, SQLITE_DBCONFIG_ENABLE_VIEW, -1, 0);
  } catch (const Failure&) {
    if (database != nullptr &&
        is_lock_result(sqlite3_extended_errcode(database))) {
      fail(SQLiteLedgerError::lock_unavailable);
    }
    throw;
  }
}

void set_creation_journal_mode(Connection& connection) {
  require_setting(
      connection, "PRAGMA main.journal_mode = DELETE", "delete");
  require_setting(
      connection, "PRAGMA main.journal_mode", "delete");
}

void require_existing_journal_mode(Connection& connection) {
  require_setting(
      connection, "PRAGMA main.journal_mode", "delete");
}

void acquire_lifetime_lock(Connection& connection) {
  try {
    begin_exclusive(connection);
  } catch (const Failure&) {
    if (is_lock_result(
            sqlite3_extended_errcode(connection.get()))) {
      fail(SQLiteLedgerError::lock_unavailable);
    }
    throw;
  }
  commit(connection);
  require_setting(
      connection, "PRAGMA main.locking_mode", "exclusive");
}

void begin_exclusive(Connection& connection) {
  if (!connection.autocommit()) {
    fail(SQLiteLedgerError::storage_failure);
  }
  auto statement = connection.prepare("BEGIN EXCLUSIVE");
  const auto result = statement.step();
  if (is_lock_result(result)) {
    fail(SQLiteLedgerError::lock_unavailable);
  }
  require_done(result);
  if (connection.autocommit()) {
    fail(SQLiteLedgerError::storage_failure);
  }
}

void commit(Connection& connection) {
  if (connection.autocommit()) {
    fail(SQLiteLedgerError::storage_failure);
  }
  auto statement = connection.prepare("COMMIT");
  require_done(statement.step());
  if (!connection.autocommit()) {
    fail(SQLiteLedgerError::storage_failure);
  }
}

void rollback_or_terminate(Connection& connection) noexcept {
  if (connection.autocommit()) {
    return;
  }
  try {
    auto statement = connection.prepare("ROLLBACK");
    if (statement.step() != SQLITE_DONE ||
        !connection.autocommit()) {
      std::terminate();
    }
  } catch (...) {
    std::terminate();
  }
}

}  // namespace protocol::storage::internal
