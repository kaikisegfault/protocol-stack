#include "protocol/storage/sqlite_ledger.hpp"
#include "protocol/v1/ledger.hpp"

#include "../../src/storage/sqlite_fault_injection.hpp"
#include "../../tools/protocol-vectors/vector_common.hpp"

#include <sqlite3.h>

#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#include <cstddef>
#include <cstdint>
#include <exception>
#include <filesystem>
#include <iostream>
#include <span>
#include <string>
#include <string_view>
#include <utility>
#include <variant>
#include <vector>

namespace pv = protocol_vectors;
namespace ps = protocol::storage;
namespace psi = protocol::storage::internal;
namespace p = protocol::v1;

namespace {

constexpr int kPostCommitExit = 73;

enum class FaultMode {
  none,
  before_commit,
  commit_rollback,
  terminal_recovery,
  post_commit_exit,
};

FaultMode fault_mode = FaultMode::none;

int reject_commit(void*) noexcept {
  return 1;
}

bool block_fault_hook(
    psi::SQLiteBlockFaultPoint point,
    sqlite3* database) noexcept {
  if (point == psi::SQLiteBlockFaultPoint::after_persistence &&
      fault_mode == FaultMode::before_commit) {
    fault_mode = FaultMode::none;
    return true;
  }
  if (point == psi::SQLiteBlockFaultPoint::before_commit &&
      (fault_mode == FaultMode::commit_rollback ||
       fault_mode == FaultMode::terminal_recovery)) {
    (void)sqlite3_commit_hook(database, reject_commit, nullptr);
    if (fault_mode == FaultMode::commit_rollback) {
      fault_mode = FaultMode::none;
    }
  }
  if (point == psi::SQLiteBlockFaultPoint::before_recovery_open &&
      fault_mode == FaultMode::terminal_recovery) {
    fault_mode = FaultMode::none;
    return true;
  }
  if (point ==
          psi::SQLiteBlockFaultPoint::after_commit_before_publication &&
      fault_mode == FaultMode::post_commit_exit) {
    ::_exit(kPostCommitExit);
  }
  return false;
}

class FaultHook {
 public:
  FaultHook() {
    psi::set_sqlite_block_fault_hook_for_testing(block_fault_hook);
  }

  ~FaultHook() {
    fault_mode = FaultMode::none;
    psi::set_sqlite_block_fault_hook_for_testing(nullptr);
  }

  FaultHook(const FaultHook&) = delete;
  FaultHook& operator=(const FaultHook&) = delete;
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

ps::SQLiteLedger take_ledger(
    ps::SQLiteLedgerResult result,
    std::string_view message) {
  pv::require(std::holds_alternative<ps::SQLiteLedger>(result.result),
              message);
  return std::get<ps::SQLiteLedger>(std::move(result.result));
}

ps::LedgerHead take_head(
    ps::SQLiteHeadResult result,
    std::string_view message) {
  pv::require(std::holds_alternative<ps::LedgerHead>(result), message);
  return std::get<ps::LedgerHead>(std::move(result));
}

p::BlockCommit take_commit(
    ps::SQLiteBlockResult result,
    std::string_view message) {
  pv::require(std::holds_alternative<p::BlockCommit>(result), message);
  return std::get<p::BlockCommit>(std::move(result));
}

void require_storage_error(
    const ps::SQLiteBlockResult& result,
    std::string_view message) {
  pv::require(
      std::holds_alternative<ps::SQLiteLedgerError>(result) &&
          std::get<ps::SQLiteLedgerError>(result) ==
              ps::SQLiteLedgerError::storage_failure,
      message);
}

void require_head_error(
    const ps::SQLiteHeadResult& result,
    std::string_view message) {
  pv::require(
      std::holds_alternative<ps::SQLiteLedgerError>(result) &&
          std::get<ps::SQLiteLedgerError>(result) ==
              ps::SQLiteLedgerError::storage_failure,
      message);
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

p::Ledger load_ledger(const p::Bytes& genesis, std::string_view message) {
  auto loaded = p::load_genesis(genesis);
  pv::require(std::holds_alternative<p::Ledger>(loaded.result), message);
  return std::get<p::Ledger>(std::move(loaded.result));
}

void create_and_close(
    const std::filesystem::path& path,
    const p::Bytes& genesis) {
  auto stored = take_ledger(
      ps::create_sqlite_ledger(path, genesis),
      "recovery baseline create failed");
  (void)stored;
}

void verify_commit_error_recovery(
    const pv::Values& values,
    const std::filesystem::path& prefix) {
  const auto genesis = genesis_bytes(values);
  const auto transactions = block_transactions(values);
  DatabaseFiles recovered_files(prefix.string() + "-commit.db");
  auto expected =
      load_ledger(genesis, "recovery fixture genesis rejected");
  auto stored = take_ledger(
      ps::create_sqlite_ledger(recovered_files.path(), genesis),
      "recovery database create failed");
  const auto old_head =
      take_head(stored.read_head(), "recovery old head read failed");

  FaultHook hook;
  fault_mode = FaultMode::before_commit;
  require_storage_error(
      stored.apply_block(1, transactions),
      "pre-commit failure returned wrong result");
  pv::require(
      take_head(stored.read_head(), "pre-commit head read failed") ==
          old_head,
      "pre-commit failure changed head");

  fault_mode = FaultMode::commit_rollback;
  require_storage_error(
      stored.apply_block(1, transactions),
      "commit rollback returned wrong result");
  pv::require(
      take_head(stored.read_head(), "recovered old head read failed") ==
          old_head,
      "commit rollback did not recover the old durable head");

  auto expected_result = expected.apply_block(1, transactions);
  pv::require(
      std::holds_alternative<p::BlockCommit>(expected_result),
      "expected recovery block rejected");
  const auto expected_commit =
      std::get<p::BlockCommit>(std::move(expected_result));
  const auto actual_commit = take_commit(
      stored.apply_block(1, transactions),
      "recovered instance rejected next block");
  pv::require(
      same_commit(actual_commit, expected_commit) &&
          take_head(
              stored.read_head(), "recovered new head read failed") ==
              ps::LedgerHead{
                  expected.state(),
                  expected_commit.resulting_state_root},
      "recovered instance diverged after retry");

  DatabaseFiles terminal_files(prefix.string() + "-terminal.db");
  {
    auto terminal = take_ledger(
        ps::create_sqlite_ledger(terminal_files.path(), genesis),
        "terminal database create failed");
    fault_mode = FaultMode::terminal_recovery;
    require_storage_error(
        terminal.apply_block(1, transactions),
        "terminal recovery returned wrong block result");
    require_head_error(
        terminal.read_head(), "terminal instance exposed stale head");
    require_storage_error(
        terminal.apply_block(1, transactions),
        "terminal instance accepted another height");
  }
  auto reopened = take_ledger(
      ps::open_sqlite_ledger(terminal_files.path(), genesis),
      "terminal database external reopen failed");
  pv::require(
      take_head(reopened.read_head(), "external head read failed") ==
          old_head,
      "external reopen did not find old durable head");
}

int post_commit_kill_probe(
    const std::filesystem::path& path,
    const p::Bytes& genesis,
    const std::vector<p::Bytes>& transactions) {
  auto stored = take_ledger(
      ps::open_sqlite_ledger(path, genesis),
      "post-commit child open failed");
  FaultHook hook;
  fault_mode = FaultMode::post_commit_exit;
  (void)stored.apply_block(1, transactions);
  return 91;
}

void verify_post_commit_termination(
    const pv::Values& values,
    const std::filesystem::path& prefix,
    const char* executable,
    const char* vector_path) {
  const auto genesis = genesis_bytes(values);
  const auto transactions = block_transactions(values);
  DatabaseFiles files(prefix.string() + "-post-commit.db");
  create_and_close(files.path(), genesis);

  const auto child = ::fork();
  pv::require(child >= 0, "post-commit fork failed");
  if (child == 0) {
    ::execl(
        executable, executable, "--post-commit-kill",
        vector_path, files.path().c_str(),
        static_cast<char*>(nullptr));
    ::_exit(127);
  }
  int status = 0;
  pv::require(
      ::waitpid(child, &status, 0) == child &&
          WIFEXITED(status) &&
          WEXITSTATUS(status) == kPostCommitExit,
      "child did not exit at post-commit boundary");

  auto expected =
      load_ledger(genesis, "post-commit fixture genesis rejected");
  const auto expected_result = expected.apply_block(1, transactions);
  pv::require(
      std::holds_alternative<p::BlockCommit>(expected_result),
      "post-commit fixture block rejected");
  const auto expected_commit =
      std::get<p::BlockCommit>(expected_result);
  auto reopened = take_ledger(
      ps::open_sqlite_ledger(files.path(), genesis),
      "post-commit durable head reopen failed");
  pv::require(
      take_head(reopened.read_head(), "post-commit head read failed") ==
          ps::LedgerHead{
              expected.state(), expected_commit.resulting_state_root},
      "post-commit termination lost durable new head");

  const std::vector<p::Bytes> empty_block;
  const auto expected_next = expected.apply_block(2, empty_block);
  pv::require(
      std::holds_alternative<p::BlockCommit>(expected_next),
      "post-commit continuation fixture rejected");
  const auto actual_next = take_commit(
      reopened.apply_block(2, empty_block),
      "post-commit recovered ledger did not continue");
  pv::require(
      same_commit(
          actual_next, std::get<p::BlockCommit>(expected_next)),
      "post-commit continuation output changed");
}

}  // namespace

int main(int argc, char** argv) {
  try {
    if (argc == 4 &&
        std::string_view(argv[1]) == "--post-commit-kill") {
      pv::require(sodium_init() >= 0, "libsodium initialization");
      const auto values = pv::load_values(argv[2]);
      return post_commit_kill_probe(
          argv[3], genesis_bytes(values), block_transactions(values));
    }
    pv::require(
        argc == 3,
        "usage: storage_sqlite_recovery_tests VECTOR_FILE PATH_PREFIX");
    pv::require(sodium_init() >= 0, "libsodium initialization");
    const auto values = pv::load_values(argv[1]);
    const std::filesystem::path prefix(argv[2]);
    verify_commit_error_recovery(values, prefix);
    verify_post_commit_termination(
        values, prefix, argv[0], argv[1]);
    std::cout << "SQLite recovery tests: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "SQLite recovery tests: failed: "
              << error.what() << '\n';
    return 1;
  }
}
