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

constexpr int kTerminationExit = 73;

enum class FaultMode {
  none,
  failure_after_persistence,
  commit_rollback,
  terminal_recovery,
  terminate_before_transaction,
  terminate_after_transaction_begin,
  terminate_after_persistence,
  terminate_before_commit,
  terminate_after_commit_before_publication,
  terminate_after_publication,
};

FaultMode fault_mode = FaultMode::none;

int reject_commit(void*) noexcept {
  return 1;
}

bool terminates_at(
    FaultMode mode,
    psi::SQLiteBlockFaultPoint point) noexcept {
  switch (mode) {
    case FaultMode::terminate_before_transaction:
      return point == psi::SQLiteBlockFaultPoint::before_transaction;
    case FaultMode::terminate_after_transaction_begin:
      return point ==
             psi::SQLiteBlockFaultPoint::after_transaction_begin;
    case FaultMode::terminate_after_persistence:
      return point == psi::SQLiteBlockFaultPoint::after_persistence;
    case FaultMode::terminate_before_commit:
      return point == psi::SQLiteBlockFaultPoint::before_commit;
    case FaultMode::terminate_after_commit_before_publication:
      return point ==
             psi::SQLiteBlockFaultPoint::after_commit_before_publication;
    case FaultMode::terminate_after_publication:
      return point == psi::SQLiteBlockFaultPoint::after_publication;
    default:
      return false;
  }
}

bool block_fault_hook(
    psi::SQLiteBlockFaultPoint point,
    sqlite3* database) noexcept {
  if (terminates_at(fault_mode, point)) {
    ::_exit(kTerminationExit);
  }
  if (point == psi::SQLiteBlockFaultPoint::after_persistence &&
      fault_mode == FaultMode::failure_after_persistence) {
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

ps::LedgerHead ledger_head(
    const p::Ledger& ledger,
    std::string_view message) {
  auto root = ledger.current_state_root();
  pv::require(std::holds_alternative<p::StateRoot>(root), message);
  return ps::LedgerHead{
      ledger.state(), std::get<p::StateRoot>(std::move(root))};
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
  fault_mode = FaultMode::failure_after_persistence;
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

FaultMode termination_mode(std::string_view name) {
  if (name == "before-transaction") {
    return FaultMode::terminate_before_transaction;
  }
  if (name == "after-transaction-begin") {
    return FaultMode::terminate_after_transaction_begin;
  }
  if (name == "after-persistence") {
    return FaultMode::terminate_after_persistence;
  }
  if (name == "before-commit") {
    return FaultMode::terminate_before_commit;
  }
  if (name == "after-commit-before-publication") {
    return FaultMode::terminate_after_commit_before_publication;
  }
  if (name == "after-publication") {
    return FaultMode::terminate_after_publication;
  }
  pv::require(false, "unknown termination point");
  return FaultMode::none;
}

int termination_probe(
    const std::filesystem::path& path,
    const p::Bytes& genesis,
    const std::vector<p::Bytes>& transactions,
    FaultMode mode) {
  auto stored = take_ledger(
      ps::open_sqlite_ledger(path, genesis),
      "termination child open failed");
  FaultHook hook;
  fault_mode = mode;
  (void)stored.apply_block(1, transactions);
  return 91;
}

struct TerminationCase {
  const char* name;
  bool committed;
};

void verify_termination_case(
    const pv::Values& values,
    const std::filesystem::path& prefix,
    const char* executable,
    const char* vector_path,
    const TerminationCase& test_case) {
  const auto genesis = genesis_bytes(values);
  const auto transactions = block_transactions(values);
  DatabaseFiles files(
      prefix.string() + "-" + test_case.name + ".db");
  create_and_close(files.path(), genesis);

  const auto child = ::fork();
  pv::require(child >= 0, "termination fork failed");
  if (child == 0) {
    ::execl(
        executable, executable, "--termination-probe",
        vector_path, files.path().c_str(), test_case.name,
        static_cast<char*>(nullptr));
    ::_exit(127);
  }
  int status = 0;
  pv::require(
      ::waitpid(child, &status, 0) == child &&
          WIFEXITED(status) &&
          WEXITSTATUS(status) == kTerminationExit,
      "child did not exit at block boundary");

  auto expected =
      load_ledger(genesis, "termination fixture genesis rejected");
  if (test_case.committed) {
    const auto committed = expected.apply_block(1, transactions);
    pv::require(
        std::holds_alternative<p::BlockCommit>(committed),
        "termination fixture block rejected");
  }
  const std::vector<p::Bytes> empty_block;
  {
    auto reopened = take_ledger(
        ps::open_sqlite_ledger(files.path(), genesis),
        "terminated database reopen failed");
    pv::require(
        take_head(reopened.read_head(), "terminated head read failed") ==
            ledger_head(expected, "expected termination root failed"),
        "termination recovered the wrong durable head");

    const auto next_height = expected.state().height + 1;
    const auto& next_transactions =
        test_case.committed ? empty_block : transactions;
    auto expected_next =
        expected.apply_block(next_height, next_transactions);
    pv::require(
        std::holds_alternative<p::BlockCommit>(expected_next),
        "termination continuation fixture rejected");
    const auto expected_commit =
        std::get<p::BlockCommit>(std::move(expected_next));
    const auto actual_commit = take_commit(
        reopened.apply_block(next_height, next_transactions),
        "terminated ledger did not continue");
    pv::require(
        same_commit(actual_commit, expected_commit) &&
            take_head(
                reopened.read_head(),
                "termination continuation head read failed") ==
                ledger_head(
                    expected, "termination continuation root failed"),
        "termination continuation diverged");
  }

  auto reopened = take_ledger(
      ps::open_sqlite_ledger(files.path(), genesis),
      "termination continuation external reopen failed");
  pv::require(
      take_head(reopened.read_head(), "final termination head read failed") ==
          ledger_head(expected, "final expected root failed"),
      "termination continuation did not survive reopen");
}

void verify_block_boundary_terminations(
    const pv::Values& values,
    const std::filesystem::path& prefix,
    const char* executable,
    const char* vector_path) {
  constexpr TerminationCase kCases[]{
      {"before-transaction", false},
      {"after-transaction-begin", false},
      {"after-persistence", false},
      {"before-commit", false},
      {"after-commit-before-publication", true},
      {"after-publication", true},
  };
  for (const auto& test_case : kCases) {
    verify_termination_case(
        values, prefix, executable, vector_path, test_case);
  }
}

}  // namespace

int main(int argc, char** argv) {
  try {
    if (argc == 5 &&
        std::string_view(argv[1]) == "--termination-probe") {
      pv::require(sodium_init() >= 0, "libsodium initialization");
      const auto values = pv::load_values(argv[2]);
      return termination_probe(
          argv[3], genesis_bytes(values), block_transactions(values),
          termination_mode(argv[4]));
    }
    pv::require(
        argc == 3,
        "usage: storage_sqlite_recovery_tests VECTOR_FILE PATH_PREFIX");
    pv::require(sodium_init() >= 0, "libsodium initialization");
    const auto values = pv::load_values(argv[1]);
    const std::filesystem::path prefix(argv[2]);
    verify_commit_error_recovery(values, prefix);
    verify_block_boundary_terminations(
        values, prefix, argv[0], argv[1]);
    std::cout << "SQLite recovery tests: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "SQLite recovery tests: failed: "
              << error.what() << '\n';
    return 1;
  }
}
