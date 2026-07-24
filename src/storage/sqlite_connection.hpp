#pragma once

#include "protocol/storage/sqlite_ledger.hpp"

#include <sqlite3.h>

#include <cstdint>
#include <filesystem>
#include <span>
#include <string>

namespace protocol::storage::internal {

struct Failure {
  SQLiteLedgerError error;
};

class FileDescriptor {
 public:
  explicit FileDescriptor(int descriptor) noexcept;
  ~FileDescriptor() noexcept;
  FileDescriptor(FileDescriptor&& other) noexcept;

  FileDescriptor(const FileDescriptor&) = delete;
  FileDescriptor& operator=(const FileDescriptor&) = delete;
  FileDescriptor& operator=(FileDescriptor&&) = delete;

  int get() const noexcept { return descriptor_; }

 private:
  int descriptor_;
};

class Statement {
 public:
  Statement(sqlite3* database, const char* sql);
  ~Statement() noexcept;
  Statement(Statement&& other) noexcept;

  Statement(const Statement&) = delete;
  Statement& operator=(const Statement&) = delete;
  Statement& operator=(Statement&&) = delete;

  void bind_integer(int index, std::int64_t value);
  void bind_blob(int index, std::span<const std::uint8_t> value);
  int step();
  void reset();

  int column_count() const noexcept;
  int column_type(int index) const noexcept;
  std::int64_t column_integer(int index) const noexcept;
  std::span<const std::uint8_t> column_blob(int index) const noexcept;
  std::string column_text(int index) const;

 private:
  sqlite3_stmt* statement_;
};

class Connection {
 public:
  explicit Connection(sqlite3* database) noexcept;
  ~Connection() noexcept;
  Connection(Connection&& other) noexcept;

  Connection(const Connection&) = delete;
  Connection& operator=(const Connection&) = delete;
  Connection& operator=(Connection&&) = delete;

  sqlite3* get() const noexcept { return database_; }
  bool autocommit() const noexcept;

  void execute(const char* sql);
  std::int64_t scalar_integer(const char* sql);
  std::string scalar_text(const char* sql);
  Statement prepare(const char* sql);

 private:
  sqlite3* database_;
};

struct SQLiteResources {
  FileDescriptor path_anchor;
  Connection connection;

  SQLiteResources(
      FileDescriptor anchor,
      Connection database) noexcept;
  SQLiteResources(SQLiteResources&&) noexcept = default;

  SQLiteResources(const SQLiteResources&) = delete;
  SQLiteResources& operator=(const SQLiteResources&) = delete;
  SQLiteResources& operator=(SQLiteResources&&) = delete;
};

std::filesystem::path normalize_database_path(
    const std::filesystem::path& path);

SQLiteResources reserve_sqlite_database(
    const std::filesystem::path& path);
SQLiteResources open_sqlite_database(
    const std::filesystem::path& path);

void verify_stable_path(
    const SQLiteResources& resources,
    const std::filesystem::path& path);
void configure_connection(Connection& connection);
void set_creation_journal_mode(Connection& connection);
void require_existing_journal_mode(Connection& connection);
void acquire_lifetime_lock(Connection& connection);
void begin_exclusive(Connection& connection);
void commit(Connection& connection);
void rollback_or_terminate(Connection& connection) noexcept;

}  // namespace protocol::storage::internal
