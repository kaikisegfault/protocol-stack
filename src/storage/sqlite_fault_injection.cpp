#include "sqlite_fault_injection.hpp"

#include <atomic>

namespace protocol::storage::internal {
namespace {

std::atomic<SQLiteBlockFaultHook> block_fault_hook{nullptr};

}  // namespace

void set_sqlite_block_fault_hook_for_testing(
    SQLiteBlockFaultHook hook) noexcept {
  block_fault_hook.store(hook, std::memory_order_release);
}

bool invoke_sqlite_block_fault(
    SQLiteBlockFaultPoint point,
    sqlite3* database) noexcept {
  const auto hook =
      block_fault_hook.load(std::memory_order_acquire);
  return hook != nullptr && hook(point, database);
}

}  // namespace protocol::storage::internal
