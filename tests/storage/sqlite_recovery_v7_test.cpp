// The version-seven store's write path under injected faults, and what it
// recovers from.
//
// ADR 0057 recorded two things as owed rather than done: fault-injection
// coverage of the version-seven write path, and recovery after a commit whose
// outcome is unknown. This is both, and the property it proves is the one
// requirement 13 actually asks for — **"through restart *and recovery*"**:
//
//   a fault anywhere in the write path leaves the durable head at either the
//   pre-block root or the post-block root, and never at anything between.
//
// Every root it compares against is the **recorded** one from
// `test-vectors/economy-transition-v7-execution.txt`, so a store that persisted
// a subtly different state would fail here rather than agree with itself.

#include "sqlite_ledger_v7_fixture.hpp"

#include "../../src/storage/sqlite_fault_injection.hpp"
#include "sqlite_fault_vfs.hpp"

#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <iostream>
#include <string>
#include <string_view>
#include <sys/wait.h>
#include <unistd.h>
#include <variant>

namespace {

namespace psi = protocol::storage::internal;
namespace pst = protocol::storage::testing;
using namespace sqlite_ledger_v7_tests;

// The exit code a terminated child uses, chosen so that an ordinary failure
// cannot be mistaken for a deliberate termination.
constexpr int kTerminationExit = 87;

// What the block hook should do, set before each case and read inside a
// `noexcept` hook, which is why it is a plain value rather than anything that
// allocates.
enum class Mode {
  none,
  fail_before_transaction,
  fail_after_transaction_begin,
  fail_after_persistence,
  fail_before_commit,
  break_the_commit,
  break_the_commit_and_the_recovery,
  terminate_after_commit,
  terminate_after_publication,
};

Mode mode = Mode::none;

bool block_hook(psi::SQLiteBlockFaultPoint point, sqlite3* database) noexcept {
  (void)database;
  switch (mode) {
    case Mode::fail_before_transaction:
      return point == psi::SQLiteBlockFaultPoint::before_transaction;
    case Mode::fail_after_transaction_begin:
      return point == psi::SQLiteBlockFaultPoint::after_transaction_begin;
    case Mode::fail_after_persistence:
      return point == psi::SQLiteBlockFaultPoint::after_persistence;
    case Mode::fail_before_commit:
      return point == psi::SQLiteBlockFaultPoint::before_commit;
    case Mode::break_the_commit:
    case Mode::break_the_commit_and_the_recovery:
      // The journal's sync is what makes SQLite's own commit fail, so the
      // failure is the storage layer's rather than this test's.
      if (point == psi::SQLiteBlockFaultPoint::before_commit) {
        pst::arm_sqlite_vfs_fault(pst::SQLiteVfsFault::sync_io,
                                  pst::SQLiteVfsFile::main_journal);
        return false;
      }
      if (point == psi::SQLiteBlockFaultPoint::before_recovery_open) {
        return mode == Mode::break_the_commit_and_the_recovery;
      }
      return false;
    case Mode::terminate_after_commit:
      if (point ==
          psi::SQLiteBlockFaultPoint::after_commit_before_publication) {
        ::_exit(kTerminationExit);
      }
      return false;
    case Mode::terminate_after_publication:
      if (point == psi::SQLiteBlockFaultPoint::after_publication) {
        ::_exit(kTerminationExit);
      }
      return false;
    case Mode::none:
      break;
  }
  return false;
}

class Hooks {
 public:
  Hooks() {
    pst::install_sqlite_fault_vfs();
    psi::set_sqlite_block_fault_hook_for_testing(block_hook);
  }
  ~Hooks() {
    mode = Mode::none;
    psi::set_sqlite_block_fault_hook_for_testing(nullptr);
    pst::uninstall_sqlite_fault_vfs();
  }
  Hooks(const Hooks&) = delete;
  Hooks& operator=(const Hooks&) = delete;
};

ps::SQLiteLedgerV7 open_store(const std::filesystem::path& path, bool create) {
  const auto genesis = fixture::trace_genesis();
  return require_store(
      create ? ps::create_sqlite_ledger_v7(path, genesis, trace_verifier())
             : ps::open_sqlite_ledger_v7(path, genesis, trace_verifier()),
      create ? "creating the store" : "reopening the store");
}

std::uint64_t durable_height(const std::filesystem::path& path) {
  auto store = open_store(path, false);
  auto head = store.read_head();
  pv::require(std::holds_alternative<ps::LedgerHeadV7>(head),
              "the durable head is unreadable");
  return std::get<ps::LedgerHeadV7>(std::move(head)).ledger.height;
}

std::string durable_root(const std::filesystem::path& path) {
  auto store = open_store(path, false);
  auto head = store.read_head();
  pv::require(std::holds_alternative<ps::LedgerHeadV7>(head),
              "the durable head is unreadable");
  const auto value = std::get<ps::LedgerHeadV7>(std::move(head));
  pv::require(v7::conservation_failures(value.ledger).empty(),
              "a recovered head must be conserved");
  return fixture::hex(value.state_root);
}

// A fault before the commit rolls the transaction back. The block is refused,
// the durable head is untouched, and — the part that matters — **the store is
// still usable**: a refusal that wrote nothing is not a reason to stop.
void verify_rolled_back_faults(const pv::Values& values,
                               const std::filesystem::path& directory) {
  const struct Case {
    const char* name;
    Mode mode;
  } cases[] = {
      {"before the transaction", Mode::fail_before_transaction},
      {"after the transaction began", Mode::fail_after_transaction_begin},
      {"after the rows were written", Mode::fail_after_persistence},
      {"before the commit", Mode::fail_before_commit},
  };

  std::size_t index = 0;
  for (const auto& single : cases) {
    const auto path = directory / ("rollback" + std::to_string(index++) + ".db");
    const auto& scenario = carried_scenario();
    {
      auto store = open_store(path, true);
      mode = single.mode;
      auto applied = store.apply_block(1, scenario.block_inputs[0]);
      mode = Mode::none;
      pv::require(std::holds_alternative<ps::SQLiteLedgerV7Error>(applied),
                  std::string("a fault ") + single.name +
                      " must refuse the block");
      pv::require(std::get<ps::SQLiteLedgerV7Error>(applied) ==
                      ps::SQLiteLedgerV7Error::storage_failure,
                  std::string("a fault ") + single.name +
                      " must refuse it as a storage failure");

      auto head = store.read_head();
      pv::require(std::holds_alternative<ps::LedgerHeadV7>(head),
                  std::string("a fault ") + single.name +
                      " must leave the store usable");
      pv::require(std::get<ps::LedgerHeadV7>(std::move(head)).ledger.height == 0,
                  std::string("a fault ") + single.name +
                      " advanced the live head");

      // And the same store accepts the same block once the fault is gone, which
      // is what "the store is still usable" has to mean.
      apply_and_compare(store, values, 0);
    }
    pv::require(durable_height(path) == 1,
                std::string("the block after a fault ") + single.name +
                    " did not become durable");
    pv::require(durable_root(path) ==
                    recorded(values, "carried.block0.resulting_state_root"),
                std::string("the durable root after a fault ") + single.name +
                    " is not the recorded one");
  }
}

// A commit that fails leaves a head this process cannot name, so the store
// poisons itself and then **reads the file again**. Recovery is what turns an
// unknown head into a known one.
void verify_commit_failure_recovers(const pv::Values& values,
                                    const std::filesystem::path& directory) {
  const auto path = directory / "commit-failure.db";
  const auto& scenario = carried_scenario();
  {
    auto store = open_store(path, true);
    mode = Mode::break_the_commit;
    auto applied = store.apply_block(1, scenario.block_inputs[0]);
    mode = Mode::none;
    pv::require(std::holds_alternative<ps::SQLiteLedgerV7Error>(applied),
                "a failed commit must refuse the block");
    pv::require(pst::sqlite_vfs_fault_fired(),
                "the injected commit fault never fired");

    // Recovered rather than poisoned: the head is readable again, and it is the
    // one the file actually holds.
    auto head = store.read_head();
    pv::require(std::holds_alternative<ps::LedgerHeadV7>(head),
                "the store did not recover from a failed commit");
    const auto value = std::get<ps::LedgerHeadV7>(std::move(head));
    pv::require(value.ledger.height == 0,
                "recovery adopted a head no block produced");
    pv::require(v7::conservation_failures(value.ledger).empty(),
                "a recovered head must be conserved");

    // And it continues: the recovered store executes the same block and
    // reproduces its recorded root.
    apply_and_compare(store, values, 0);
  }
  pv::require(durable_root(path) ==
                  recorded(values, "carried.block0.resulting_state_root"),
              "the recovered store's durable root is not the recorded one");
}

// Recovery is allowed to fail, and then the honest answer is to refuse
// everything. A store that could not read its own file back must not pretend to
// know where it is.
void verify_unrecoverable_commit_stays_poisoned(
    const std::filesystem::path& directory) {
  const auto path = directory / "poisoned.db";
  const auto& scenario = carried_scenario();
  auto store = open_store(path, true);
  mode = Mode::break_the_commit_and_the_recovery;
  auto applied = store.apply_block(1, scenario.block_inputs[0]);
  mode = Mode::none;
  pv::require(std::holds_alternative<ps::SQLiteLedgerV7Error>(applied),
              "a failed commit must refuse the block");

  auto head = store.read_head();
  pv::require(std::holds_alternative<ps::SQLiteLedgerV7Error>(head) &&
                  std::get<ps::SQLiteLedgerV7Error>(head) ==
                      ps::SQLiteLedgerV7Error::storage_failure,
              "a store that could not recover must refuse to read its head");
  auto snapshot = store.create_snapshot();
  pv::require(std::holds_alternative<ps::SQLiteLedgerV7Error>(snapshot),
              "a poisoned store must refuse to hand out a payload");
  auto again = store.apply_block(1, scenario.block_inputs[0]);
  pv::require(std::holds_alternative<ps::SQLiteLedgerV7Error>(again),
              "a poisoned store must refuse every later block");
}

// Kill the process between the commit and the publication, and between the
// publication and the return. Both are points where the durable head has
// advanced and the process has not finished saying so — and in both the file
// must hold the committed block and nothing partial.
void verify_terminations(const pv::Values& values,
                         const std::filesystem::path& directory,
                         const char* executable, const char* vector_path) {
  const struct Case {
    const char* name;
  } cases[] = {{"after-commit"}, {"after-publication"}};

  for (const auto& single : cases) {
    const auto path =
        directory / (std::string("terminate-") + single.name + ".db");
    { (void)open_store(path, true); }

    const auto child = ::fork();
    pv::require(child >= 0, "the termination fork failed");
    if (child == 0) {
      ::execl(executable, executable, "--termination-probe", vector_path,
              path.c_str(), single.name, static_cast<char*>(nullptr));
      ::_exit(127);
    }
    int status = 0;
    pv::require(::waitpid(child, &status, 0) == child && WIFEXITED(status) &&
                    WEXITSTATUS(status) == kTerminationExit,
                std::string("the child did not terminate ") + single.name);

    // The committed block is durable even though the process never returned.
    pv::require(durable_height(path) == 1,
                std::string("a termination ") + single.name +
                    " lost the committed block");
    pv::require(durable_root(path) ==
                    recorded(values, "carried.block0.resulting_state_root"),
                std::string("a termination ") + single.name +
                    " left a root that is not the recorded one");
    // And the chain continues from it on the same trajectory.
    {
      auto store = open_store(path, false);
      apply_and_compare(store, values, 1);
    }
    pv::require(durable_root(path) ==
                    recorded(values, "carried.block1.resulting_state_root"),
                std::string("the chain after a termination ") + single.name +
                    " diverged");
  }
}

int run_termination_probe(const char* vector_path, const char* database,
                          std::string_view name) {
  const auto values = pv::load_values(vector_path);
  (void)values;
  Hooks hooks;
  mode = name == "after-commit" ? Mode::terminate_after_commit
                               : Mode::terminate_after_publication;
  auto store = open_store(std::filesystem::path(database), false);
  const auto& scenario = carried_scenario();
  (void)store.apply_block(1, scenario.block_inputs[0]);
  // The hook exits the process, so reaching here is the failure.
  std::cerr << "the termination probe was not terminated\n";
  return 1;
}

}  // namespace

int main(int argc, char** argv) {
  try {
    if (argc == 5 && std::string_view(argv[1]) == "--termination-probe") {
      return run_termination_probe(argv[2], argv[3], argv[4]);
    }
    pv::require(argc == 3, "usage: storage_sqlite_recovery_v7_tests VECTORS DIR");
    pv::require(sodium_init() >= 0, "libsodium initialization");
    const auto values = pv::load_values(argv[1]);
    const std::filesystem::path directory(argv[2]);
    std::filesystem::remove_all(directory);
    std::filesystem::create_directories(directory);

    {
      Hooks hooks;
      verify_rolled_back_faults(values, directory);
      verify_commit_failure_recovers(values, directory);
      verify_unrecoverable_commit_stays_poisoned(directory);
    }
    // The termination cases run the hooks inside a child process, so the parent
    // must not hold them: a forked child inherits an armed VFS otherwise.
    verify_terminations(values, directory, argv[0], argv[1]);

    std::filesystem::remove_all(directory);
    std::cout << "C++ version-seven store recovery: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "C++ version-seven store recovery: failed: " << error.what()
              << '\n';
    return 1;
  }
}
