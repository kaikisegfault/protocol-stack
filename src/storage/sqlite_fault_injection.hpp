#pragma once

#include <sqlite3.h>

#include <cstdint>

namespace protocol::storage::internal {

enum class SQLiteBlockFaultPoint : std::uint8_t {
  before_transaction = 1,
  after_transaction_begin = 2,
  after_persistence = 3,
  before_commit = 4,
  after_commit_before_publication = 5,
  after_publication = 6,
  before_recovery_open = 7,
};

using SQLiteBlockFaultHook = bool (*)(
    SQLiteBlockFaultPoint point,
    sqlite3* database) noexcept;

void set_sqlite_block_fault_hook_for_testing(
    SQLiteBlockFaultHook hook) noexcept;

bool invoke_sqlite_block_fault(
    SQLiteBlockFaultPoint point,
    sqlite3* database) noexcept;

}  // namespace protocol::storage::internal
