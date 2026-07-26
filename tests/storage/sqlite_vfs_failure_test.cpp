#include "protocol/storage/sqlite_ledger.hpp"
#include "protocol/v1/ledger.hpp"

#include "../../src/storage/sqlite_fault_injection.hpp"
#include "../../tools/protocol-vectors/vector_common.hpp"
#include "sqlite_fault_vfs.hpp"

#include <sqlite3.h>

#include <cstddef>
#include <cstdint>
#include <exception>
#include <filesystem>
#include <iostream>
#include <string>
#include <string_view>
#include <utility>
#include <variant>
#include <vector>

namespace pv = protocol_vectors;
namespace ps = protocol::storage;
namespace psi = protocol::storage::internal;
namespace pst = protocol::storage::testing;
namespace p = protocol::v1;

namespace {

enum class FaultMode {
  none,
  short_write,
  full_write,
  write_io,
  sync_io,
  truncate_io,
  delete_io,
};

FaultMode fault_mode = FaultMode::none;

int reject_commit(void*) noexcept {
  return 1;
}

void arm_early_fault() noexcept {
  pst::SQLiteVfsFault fault;
  switch (fault_mode) {
    case FaultMode::short_write:
      fault = pst::SQLiteVfsFault::short_write;
      break;
    case FaultMode::full_write:
      fault = pst::SQLiteVfsFault::full_write;
      break;
    case FaultMode::write_io:
      fault = pst::SQLiteVfsFault::write_io;
      break;
    default:
      return;
  }
  pst::arm_sqlite_vfs_fault(
      fault, pst::SQLiteVfsFile::main_journal);
  fault_mode = FaultMode::none;
}

void arm_commit_fault(sqlite3* database) noexcept {
  pst::SQLiteVfsFault fault;
  switch (fault_mode) {
    case FaultMode::sync_io:
      fault = pst::SQLiteVfsFault::sync_io;
      break;
    case FaultMode::truncate_io:
      fault = pst::SQLiteVfsFault::truncate_io;
      break;
    case FaultMode::delete_io:
      (void)sqlite3_commit_hook(database, reject_commit, nullptr);
      fault = pst::SQLiteVfsFault::delete_io;
      break;
    default:
      return;
  }
  pst::arm_sqlite_vfs_fault(
      fault, pst::SQLiteVfsFile::main_journal);
  fault_mode = FaultMode::none;
}

bool block_fault_hook(
    psi::SQLiteBlockFaultPoint point,
    sqlite3* database) noexcept {
  if (point ==
      psi::SQLiteBlockFaultPoint::after_transaction_begin) {
    arm_early_fault();
  }
  if (point == psi::SQLiteBlockFaultPoint::before_commit) {
    arm_commit_fault(database);
  }
  return false;
}

class TestHooks {
 public:
  TestHooks() {
    pst::install_sqlite_fault_vfs();
    psi::set_sqlite_block_fault_hook_for_testing(block_fault_hook);
  }

  ~TestHooks() {
    fault_mode = FaultMode::none;
    psi::set_sqlite_block_fault_hook_for_testing(nullptr);
    pst::uninstall_sqlite_fault_vfs();
  }

  TestHooks(const TestHooks&) = delete;
  TestHooks& operator=(const TestHooks&) = delete;
};

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

std::vector<p::Bytes> block_transactions(const pv::Values& values) {
  const auto count = static_cast<std::size_t>(
      std::stoull(values.at("raw_count")));
  std::vector<p::Bytes> transactions;
  transactions.reserve(count);
  for (std::size_t index = 0; index < count; ++index) {
    transactions.push_back(
        pv::hex_decode(values.at("raw" + std::to_string(index))));
  }
  return transactions;
}

p::Ledger load_ledger(const p::Bytes& genesis) {
  auto loaded = p::load_genesis(genesis);
  pv::require(
      std::holds_alternative<p::Ledger>(loaded.result),
      "VFS fixture genesis rejected");
  return std::get<p::Ledger>(std::move(loaded.result));
}

ps::SQLiteLedger take_ledger(
    ps::SQLiteLedgerResult result,
    std::string_view message) {
  pv::require(
      std::holds_alternative<ps::SQLiteLedger>(result.result),
      message);
  return std::get<ps::SQLiteLedger>(std::move(result.result));
}

ps::LedgerHead take_head(
    ps::SQLiteHeadResult result,
    std::string_view message) {
  pv::require(
      std::holds_alternative<ps::LedgerHead>(result), message);
  return std::get<ps::LedgerHead>(std::move(result));
}

p::BlockCommit take_commit(
    ps::SQLiteBlockResult result,
    std::string_view message) {
  pv::require(
      std::holds_alternative<p::BlockCommit>(result), message);
  return std::get<p::BlockCommit>(std::move(result));
}

void require_storage_error(
    const ps::SQLiteBlockResult& result) {
  pv::require(
      std::holds_alternative<ps::SQLiteLedgerError>(result) &&
          std::get<ps::SQLiteLedgerError>(result) ==
              ps::SQLiteLedgerError::storage_failure,
      "VFS fault returned wrong block result");
}

bool same_commit(
    const p::BlockCommit& left,
    const p::BlockCommit& right) {
  return left.height == right.height &&
         left.admissions == right.admissions &&
         left.transaction_ids == right.transaction_ids &&
         left.receipts == right.receipts &&
         left.encoded_receipts == right.encoded_receipts &&
         left.previous_state_root == right.previous_state_root &&
         left.transaction_root == right.transaction_root &&
         left.resulting_state_root == right.resulting_state_root &&
         left.header == right.header &&
         left.block_id == right.block_id;
}

struct VfsCase {
  FaultMode mode;
  const char* name;
  bool must_preserve_old_head;
};

void verify_vfs_case(
    const pv::Values& values,
    const std::filesystem::path& prefix,
    const VfsCase& test_case) {
  const auto genesis = genesis_bytes(values);
  const auto transactions = block_transactions(values);
  DatabaseFiles files(
      prefix.string() + "-" + test_case.name + ".db");

  auto expected = load_ledger(genesis);
  const auto old_root = expected.current_state_root();
  pv::require(
      std::holds_alternative<p::StateRoot>(old_root),
      "VFS genesis root failed");
  const ps::LedgerHead old_head{
      expected.state(), std::get<p::StateRoot>(old_root)};
  const auto expected_result =
      expected.apply_block(1, transactions);
  pv::require(
      std::holds_alternative<p::BlockCommit>(expected_result),
      "VFS fixture block rejected");
  const auto expected_commit =
      std::get<p::BlockCommit>(expected_result);
  const ps::LedgerHead expected_new{
      expected.state(), expected_commit.resulting_state_root};

  ps::LedgerHead expected_after = expected_new;
  bool terminal = false;
  {
    auto stored = take_ledger(
        ps::create_sqlite_ledger(files.path(), genesis),
        "VFS database create failed");
    pv::require(
        take_head(stored.read_head(), "VFS old head read failed") ==
            old_head,
        "VFS database started at wrong head");

    fault_mode = test_case.mode;
    require_storage_error(stored.apply_block(1, transactions));
    pv::require(
        pst::sqlite_vfs_fault_fired(),
        "armed VFS operation was not reached");

    auto recovered = stored.read_head();
    if (std::holds_alternative<ps::SQLiteLedgerError>(
            recovered)) {
      terminal = true;
    } else {
      const auto head =
          std::get<ps::LedgerHead>(std::move(recovered));
      if (test_case.must_preserve_old_head) {
        pv::require(
            head == old_head,
            "pre-commit VFS fault changed durable head");
      }
      pv::require(
          head == old_head || head == expected_new,
          "VFS recovery published neither durable head");
      if (head == old_head) {
        const auto retried = take_commit(
            stored.apply_block(1, transactions),
            "VFS-recovered instance rejected retry");
        pv::require(
            same_commit(retried, expected_commit),
            "VFS retry output changed");
      } else {
        const std::vector<p::Bytes> empty_block;
        const auto expected_next =
            expected.apply_block(2, empty_block);
        pv::require(
            std::holds_alternative<p::BlockCommit>(expected_next),
            "VFS continuation fixture rejected");
        const auto next = take_commit(
            stored.apply_block(2, empty_block),
            "VFS-recovered instance rejected next height");
        pv::require(
            same_commit(
                next, std::get<p::BlockCommit>(expected_next)),
            "VFS continuation output changed");
        expected_after = ps::LedgerHead{
            expected.state(), next.resulting_state_root};
      }
    }
  }

  auto reopened = take_ledger(
      ps::open_sqlite_ledger(files.path(), genesis),
      "VFS database external reopen failed");
  const auto durable =
      take_head(reopened.read_head(), "VFS durable head read failed");
  if (terminal) {
    pv::require(
        durable == old_head || durable == expected_new,
        "terminal VFS recovery left no valid durable head");
  } else {
    pv::require(
        durable == expected_after,
        "VFS continuation did not survive external reopen");
  }
}

void verify_vfs_failures(
    const pv::Values& values,
    const std::filesystem::path& prefix) {
  constexpr VfsCase kCases[]{
      {FaultMode::short_write, "short-write", true},
      {FaultMode::full_write, "full-write", true},
      {FaultMode::write_io, "write-io", true},
      {FaultMode::sync_io, "sync-io", false},
      {FaultMode::truncate_io, "truncate-io", false},
      {FaultMode::delete_io, "delete-io", false},
  };
  for (const auto& test_case : kCases) {
    verify_vfs_case(values, prefix, test_case);
  }
}

}  // namespace

int main(int argc, char** argv) {
  try {
    pv::require(
        argc == 3,
        "usage: storage_sqlite_vfs_failure_tests VECTOR_FILE PATH");
    pv::require(sodium_init() >= 0, "libsodium initialization");
    TestHooks hooks;
    const auto values = pv::load_values(argv[1]);
    verify_vfs_failures(values, argv[2]);
    std::cout << "SQLite VFS failure tests: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "SQLite VFS failure tests: failed: "
              << error.what() << '\n';
    return 1;
  }
}
