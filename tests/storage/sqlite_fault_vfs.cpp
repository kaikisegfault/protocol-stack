#include "sqlite_fault_vfs.hpp"

#include <sqlite3.h>

#include <cstddef>
#include <cstring>
#include <exception>
#include <limits>
#include <stdexcept>

namespace protocol::storage::testing {
namespace {

constexpr char kFaultVfsName[] = "protocol-test-fault-vfs";

struct alignas(std::max_align_t) FaultFile {
  sqlite3_file base;
  sqlite3_file* parent;
  int open_flags;
};

sqlite3_vfs fault_vfs{};
sqlite3_vfs* parent_vfs = nullptr;
SQLiteVfsFault armed_fault = SQLiteVfsFault::write_io;
SQLiteVfsFile armed_file = SQLiteVfsFile::main_database;
bool fault_armed = false;
bool fault_fired = false;

FaultFile* fault_file(sqlite3_file* file) noexcept {
  return reinterpret_cast<FaultFile*>(file);
}

bool matches_file(int flags) noexcept {
  const auto expected =
      armed_file == SQLiteVfsFile::main_database
          ? SQLITE_OPEN_MAIN_DB
          : SQLITE_OPEN_MAIN_JOURNAL;
  return (flags & expected) != 0;
}

bool consume_fault(
    SQLiteVfsFault expected,
    int flags) noexcept {
  if (!fault_armed || armed_fault != expected ||
      !matches_file(flags)) {
    return false;
  }
  fault_armed = false;
  fault_fired = true;
  return true;
}

int parent_close(sqlite3_file* file) {
  auto* wrapped = fault_file(file);
  const auto result = wrapped->parent->pMethods->xClose(
      wrapped->parent);
  wrapped->base.pMethods = nullptr;
  return result;
}

int parent_read(
    sqlite3_file* file,
    void* output,
    int amount,
    sqlite3_int64 offset) {
  auto* wrapped = fault_file(file);
  return wrapped->parent->pMethods->xRead(
      wrapped->parent, output, amount, offset);
}

int parent_write(
    sqlite3_file* file,
    const void* input,
    int amount,
    sqlite3_int64 offset) {
  auto* wrapped = fault_file(file);
  if (consume_fault(
          SQLiteVfsFault::short_write,
          wrapped->open_flags)) {
    if (amount > 1) {
      (void)wrapped->parent->pMethods->xWrite(
          wrapped->parent, input, amount - 1, offset);
    }
    return SQLITE_IOERR_WRITE;
  }
  if (consume_fault(
          SQLiteVfsFault::full_write,
          wrapped->open_flags)) {
    return SQLITE_FULL;
  }
  if (consume_fault(
          SQLiteVfsFault::write_io,
          wrapped->open_flags)) {
    return SQLITE_IOERR_WRITE;
  }
  return wrapped->parent->pMethods->xWrite(
      wrapped->parent, input, amount, offset);
}

int parent_truncate(
    sqlite3_file* file,
    sqlite3_int64 size) {
  auto* wrapped = fault_file(file);
  if (consume_fault(
          SQLiteVfsFault::truncate_io,
          wrapped->open_flags)) {
    return SQLITE_IOERR_TRUNCATE;
  }
  return wrapped->parent->pMethods->xTruncate(
      wrapped->parent, size);
}

int parent_sync(sqlite3_file* file, int flags) {
  auto* wrapped = fault_file(file);
  if (consume_fault(
          SQLiteVfsFault::sync_io,
          wrapped->open_flags)) {
    return SQLITE_IOERR_FSYNC;
  }
  return wrapped->parent->pMethods->xSync(
      wrapped->parent, flags);
}

int parent_file_size(
    sqlite3_file* file,
    sqlite3_int64* size) {
  auto* wrapped = fault_file(file);
  return wrapped->parent->pMethods->xFileSize(
      wrapped->parent, size);
}

int parent_lock(sqlite3_file* file, int lock) {
  auto* wrapped = fault_file(file);
  return wrapped->parent->pMethods->xLock(
      wrapped->parent, lock);
}

int parent_unlock(sqlite3_file* file, int lock) {
  auto* wrapped = fault_file(file);
  return wrapped->parent->pMethods->xUnlock(
      wrapped->parent, lock);
}

int parent_check_reserved_lock(
    sqlite3_file* file,
    int* result) {
  auto* wrapped = fault_file(file);
  return wrapped->parent->pMethods->xCheckReservedLock(
      wrapped->parent, result);
}

int parent_file_control(
    sqlite3_file* file,
    int operation,
    void* argument) {
  auto* wrapped = fault_file(file);
  return wrapped->parent->pMethods->xFileControl(
      wrapped->parent, operation, argument);
}

int parent_sector_size(sqlite3_file* file) {
  auto* wrapped = fault_file(file);
  return wrapped->parent->pMethods->xSectorSize(
      wrapped->parent);
}

int parent_device_characteristics(sqlite3_file* file) {
  auto* wrapped = fault_file(file);
  return wrapped->parent->pMethods->xDeviceCharacteristics(
      wrapped->parent);
}

const sqlite3_io_methods fault_io_methods{
    1,
    parent_close,
    parent_read,
    parent_write,
    parent_truncate,
    parent_sync,
    parent_file_size,
    parent_lock,
    parent_unlock,
    parent_check_reserved_lock,
    parent_file_control,
    parent_sector_size,
    parent_device_characteristics,
    nullptr,
    nullptr,
    nullptr,
    nullptr,
    nullptr,
    nullptr,
};

int fault_open(
    sqlite3_vfs*,
    sqlite3_filename name,
    sqlite3_file* file,
    int flags,
    int* output_flags) {
  auto* wrapped = fault_file(file);
  wrapped->base.pMethods = nullptr;
  wrapped->parent = reinterpret_cast<sqlite3_file*>(
      reinterpret_cast<unsigned char*>(file) +
      sizeof(FaultFile));
  wrapped->parent->pMethods = nullptr;
  wrapped->open_flags = flags;

  const auto result = parent_vfs->xOpen(
      parent_vfs, name, wrapped->parent, flags, output_flags);
  if (wrapped->parent->pMethods != nullptr) {
    wrapped->base.pMethods = &fault_io_methods;
  }
  return result;
}

bool journal_name(const char* name) noexcept {
  if (name == nullptr) return false;
  constexpr char kSuffix[] = "-journal";
  const auto name_size = std::strlen(name);
  constexpr auto suffix_size = sizeof(kSuffix) - 1;
  return name_size >= suffix_size &&
         std::memcmp(
             name + name_size - suffix_size,
             kSuffix,
             suffix_size) == 0;
}

int fault_delete(
    sqlite3_vfs*,
    const char* name,
    int sync_directory) {
  const auto flags =
      journal_name(name) ? SQLITE_OPEN_MAIN_JOURNAL : 0;
  if (consume_fault(SQLiteVfsFault::delete_io, flags)) {
    return SQLITE_IOERR_DELETE;
  }
  return parent_vfs->xDelete(
      parent_vfs, name, sync_directory);
}

int parent_access(
    sqlite3_vfs*,
    const char* name,
    int flags,
    int* result) {
  return parent_vfs->xAccess(
      parent_vfs, name, flags, result);
}

int parent_full_pathname(
    sqlite3_vfs*,
    const char* name,
    int output_size,
    char* output) {
  return parent_vfs->xFullPathname(
      parent_vfs, name, output_size, output);
}

void* parent_dl_open(sqlite3_vfs*, const char* name) {
  return parent_vfs->xDlOpen(parent_vfs, name);
}

void parent_dl_error(
    sqlite3_vfs*,
    int output_size,
    char* output) {
  parent_vfs->xDlError(parent_vfs, output_size, output);
}

void (*parent_dl_sym(
    sqlite3_vfs*,
    void* handle,
    const char* symbol))(void) {
  return parent_vfs->xDlSym(parent_vfs, handle, symbol);
}

void parent_dl_close(sqlite3_vfs*, void* handle) {
  parent_vfs->xDlClose(parent_vfs, handle);
}

int parent_randomness(
    sqlite3_vfs*,
    int output_size,
    char* output) {
  return parent_vfs->xRandomness(
      parent_vfs, output_size, output);
}

int parent_sleep(sqlite3_vfs*, int microseconds) {
  return parent_vfs->xSleep(parent_vfs, microseconds);
}

int parent_current_time(sqlite3_vfs*, double* value) {
  return parent_vfs->xCurrentTime(parent_vfs, value);
}

int parent_last_error(
    sqlite3_vfs*,
    int output_size,
    char* output) {
  return parent_vfs->xGetLastError(
      parent_vfs, output_size, output);
}

int parent_current_time_int64(
    sqlite3_vfs*,
    sqlite3_int64* value) {
  return parent_vfs->xCurrentTimeInt64(parent_vfs, value);
}

int parent_set_system_call(
    sqlite3_vfs*,
    const char* name,
    sqlite3_syscall_ptr call) {
  return parent_vfs->xSetSystemCall(
      parent_vfs, name, call);
}

sqlite3_syscall_ptr parent_get_system_call(
    sqlite3_vfs*,
    const char* name) {
  return parent_vfs->xGetSystemCall(parent_vfs, name);
}

const char* parent_next_system_call(
    sqlite3_vfs*,
    const char* name) {
  return parent_vfs->xNextSystemCall(parent_vfs, name);
}

void configure_fault_vfs() {
  fault_vfs = {};
  fault_vfs.iVersion = 1;
  fault_vfs.szOsFile =
      static_cast<int>(sizeof(FaultFile)) +
      parent_vfs->szOsFile;
  fault_vfs.mxPathname = parent_vfs->mxPathname;
  fault_vfs.zName = kFaultVfsName;
  fault_vfs.xOpen = fault_open;
  fault_vfs.xDelete = fault_delete;
  fault_vfs.xAccess = parent_access;
  fault_vfs.xFullPathname = parent_full_pathname;
  fault_vfs.xDlOpen =
      parent_vfs->xDlOpen == nullptr ? nullptr : parent_dl_open;
  fault_vfs.xDlError =
      parent_vfs->xDlError == nullptr ? nullptr : parent_dl_error;
  fault_vfs.xDlSym =
      parent_vfs->xDlSym == nullptr ? nullptr : parent_dl_sym;
  fault_vfs.xDlClose =
      parent_vfs->xDlClose == nullptr ? nullptr : parent_dl_close;
  fault_vfs.xRandomness = parent_randomness;
  fault_vfs.xSleep = parent_sleep;
  fault_vfs.xCurrentTime = parent_current_time;
  fault_vfs.xGetLastError =
      parent_vfs->xGetLastError == nullptr
          ? nullptr
          : parent_last_error;
  if (parent_vfs->iVersion >= 2 &&
      parent_vfs->xCurrentTimeInt64 != nullptr) {
    fault_vfs.iVersion = 2;
    fault_vfs.xCurrentTimeInt64 = parent_current_time_int64;
  }
  if (parent_vfs->iVersion >= 3 &&
      parent_vfs->xSetSystemCall != nullptr &&
      parent_vfs->xGetSystemCall != nullptr &&
      parent_vfs->xNextSystemCall != nullptr) {
    fault_vfs.iVersion = 3;
    fault_vfs.xSetSystemCall = parent_set_system_call;
    fault_vfs.xGetSystemCall = parent_get_system_call;
    fault_vfs.xNextSystemCall = parent_next_system_call;
  }
}

}  // namespace

void install_sqlite_fault_vfs() {
  if (parent_vfs != nullptr) {
    throw std::runtime_error("SQLite fault VFS already installed");
  }
  parent_vfs = sqlite3_vfs_find(nullptr);
  if (parent_vfs == nullptr ||
      parent_vfs->szOsFile >
          std::numeric_limits<int>::max() -
              static_cast<int>(sizeof(FaultFile))) {
    parent_vfs = nullptr;
    throw std::runtime_error("SQLite default VFS unavailable");
  }
  configure_fault_vfs();
  if (sqlite3_vfs_register(&fault_vfs, 1) != SQLITE_OK) {
    parent_vfs = nullptr;
    throw std::runtime_error("SQLite fault VFS registration failed");
  }
}

void uninstall_sqlite_fault_vfs() noexcept {
  if (parent_vfs == nullptr) return;
  auto* original = parent_vfs;
  if (sqlite3_vfs_register(original, 1) != SQLITE_OK ||
      sqlite3_vfs_unregister(&fault_vfs) != SQLITE_OK) {
    std::terminate();
  }
  parent_vfs = nullptr;
  fault_armed = false;
}

void arm_sqlite_vfs_fault(
    SQLiteVfsFault fault,
    SQLiteVfsFile file) noexcept {
  armed_fault = fault;
  armed_file = file;
  fault_fired = false;
  fault_armed = true;
}

bool sqlite_vfs_fault_fired() noexcept {
  return fault_fired;
}

}  // namespace protocol::storage::testing
