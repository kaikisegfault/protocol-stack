#pragma once

namespace protocol::storage::testing {

enum class SQLiteVfsFault {
  short_write,
  full_write,
  write_io,
  sync_io,
  truncate_io,
  delete_io,
};

enum class SQLiteVfsFile {
  main_database,
  main_journal,
};

void install_sqlite_fault_vfs();
void uninstall_sqlite_fault_vfs() noexcept;

void arm_sqlite_vfs_fault(
    SQLiteVfsFault fault,
    SQLiteVfsFile file) noexcept;
bool sqlite_vfs_fault_fired() noexcept;

}  // namespace protocol::storage::testing
