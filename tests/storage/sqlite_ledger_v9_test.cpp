// The version-nine owning store, checked against the recorded execution
// vectors across a real restart.
//
// **This is the question the snapshot's own tests could not ask.** ADR 0080
// restores a *final* ledger and executes one further block; it establishes
// nothing about a chain interrupted in the middle of its history. Here the
// `restart` run's four blocks — heights 1 through 4, contiguous from genesis —
// are applied through a database that is **closed and reopened between each
// pair**, and every block must reproduce its *recorded* `block_id`,
// `resulting_state_root`, and stamp. Those figures come from a model that knows
// nothing about SQLite, so a store that persisted a subtly different state would
// fail here rather than agree with itself.
//
// **Version nine's own question is which stamp comes back.** A store that
// reopened with a stamp belonging to an earlier height would still accept every
// later block, because C2 only refuses a stamp that goes *backwards* and a stale
// one is smaller than anything that follows. The failure would be a wrong root
// rather than a refusal, which is the direction that hides. So between blocks 2
// and 3 — the pair whose stamps are equal — the reopened store is first offered
// height 3 one millisecond below block 2's stamp, which it must refuse, and then
// at exactly that stamp, which it must admit. A store that restored a smaller
// stamp admits both; one that restored a larger stamp admits neither.

#include "sqlite_ledger_v9_fixture.hpp"

#include <iostream>
#include <span>
#include <string>

namespace sqlite_ledger_v9_tests {
namespace {

std::uint64_t decoded_u64(std::span<const std::uint8_t> bytes) {
  pv::require(bytes.size() == 8, "a stored height or stamp is eight octets");
  std::uint64_t value = 0;
  for (const auto octet : bytes) value = (value << 8U) | octet;
  return value;
}

// The durable stamp this reopened store holds, offered one millisecond too early
// and then exactly. Both answers come from the kernel's C2 against the head this
// store restored, which is the comparison a stale restored stamp would weaken.
void check_the_restored_stamp_is_the_predecessors(ps::SQLiteLedgerV9& store,
                                                  const pv::Values& values,
                                                  std::size_t index) {
  const auto previous = block_label(index - 1);
  const auto label = block_label(index);
  const auto restored = recorded_number(values, previous + ".timestamp");
  pv::require(recorded_number(values, label + ".timestamp") == restored,
              "the restart run's block " + std::to_string(index) +
                  " repeats its predecessor's stamp");
  pv::require(recorded(values, "restart.below_the_predecessors_stamp.refusal") ==
                  "TIMESTAMP_NOT_MONOTONIC",
              "the model refuses the earlier stamp for C2");

  auto refused = store.apply_block(recorded_number(values, label + ".height"),
                                   restored - 1, restart_run().block_inputs[index]);
  pv::require(std::holds_alternative<ps::BlockRejectedV9>(refused),
              "a reopened store admitted a stamp below the one it restored");
  require_head(store, values, index - 1,
               "the head after refusing a stamp below the restored one");
}

}  // namespace

// Read the block rows back with a bare connection, so the history the store
// wrote is checked against the vectors rather than against the store's own
// return values. Without this the row insert would be unobserved, and a commit
// that wrote only the head would pass every other check here.
void check_block_history(const pv::Values& values,
                         const std::filesystem::path& path) {
  sqlite3* database = nullptr;
  pv::require(sqlite3_open(path.c_str(), &database) == SQLITE_OK,
              "the history connection opens");
  sqlite3_stmt* statement = nullptr;
  // Ordering by the height column is ordering numerically because the height is
  // stored as fixed-width big-endian octets, where blob order and numeric order
  // are the same.
  const char* sql =
      "SELECT height, block_id, resulting_state_root, header, transaction_root,"
      " timestamp FROM blocks_v9 ORDER BY height";
  pv::require(sqlite3_prepare_v2(database, sql, -1, &statement, nullptr) == SQLITE_OK,
              "the history query prepares");
  std::size_t rows = 0;
  while (sqlite3_step(statement) == SQLITE_ROW) {
    const auto label = block_label(rows);
    const auto blob = [&statement](int column) {
      const auto* data =
          static_cast<const std::uint8_t*>(sqlite3_column_blob(statement, column));
      const auto size = static_cast<std::size_t>(
          sqlite3_column_bytes(statement, column));
      return std::span<const std::uint8_t>(data, size);
    };
    pv::require(decoded_u64(blob(0)) == recorded_number(values, label + ".height"),
                label + ": the stored height is not the recorded one");
    pv::require(fixture::hex(blob(1)) == recorded(values, label + ".block_id"),
                label + ": the stored block identifier is not the recorded one");
    pv::require(fixture::hex(blob(2)) ==
                    recorded(values, label + ".resulting_state_root"),
                label + ": the stored root is not the recorded one");
    pv::require(fixture::hex(blob(3)) == recorded(values, label + ".header"),
                label + ": the stored header is not the recorded one");
    // The transaction root and the stamp are columns of their own rather than
    // fields of the header the row beside them stores, so a row that agreed
    // with the header and disagreed with the vectors would otherwise go unread.
    pv::require(fixture::hex(blob(4)) ==
                    recorded(values, label + ".transaction_root"),
                label + ": the stored transaction root is not the recorded one");
    pv::require(decoded_u64(blob(5)) == recorded_number(values, label + ".timestamp"),
                label + ": the stored stamp is not the recorded one");
    ++rows;
  }
  sqlite3_finalize(statement);
  sqlite3_close(database);
  pv::require(rows == kContiguousBlocks,
              "the store wrote one row per committed block");
}

// The whole point: close the database after every block and reopen it before the
// next, so no block after the first is executed against a head that stayed in
// memory. Four blocks, three restarts.
void check_restart_equivalence(const pv::Values& values,
                               const std::filesystem::path& directory) {
  const auto path = directory / "restart.db";
  const auto genesis = fixture::trace_genesis();
  {
    auto store = require_store(
        ps::create_sqlite_ledger_v9(path, genesis, trace_verifier()),
        "creating the store");
    apply_and_compare(store, values, 0);
  }
  for (std::size_t index = 1; index < kContiguousBlocks; ++index) {
    auto store = require_store(
        ps::open_sqlite_ledger_v9(path, genesis, trace_verifier()),
        "reopening before block " + std::to_string(index));
    require_head(store, values, index - 1,
                 "the head after restart " + std::to_string(index));
    if (index == 2) check_the_restored_stamp_is_the_predecessors(store, values, index);
    apply_and_compare(store, values, index);
  }
  {
    auto store = require_store(
        ps::open_sqlite_ledger_v9(path, genesis, trace_verifier()),
        "reopening after the last block");
    require_head(store, values, kContiguousBlocks - 1, "the final durable head");
  }
  check_block_history(values, path);
}

// The same four blocks without any restart, which is what makes the comparison
// above a statement about restarting rather than about the store.
void check_uninterrupted(const pv::Values& values,
                         const std::filesystem::path& directory) {
  auto store = require_store(
      ps::create_sqlite_ledger_v9(directory / "straight.db",
                                  fixture::trace_genesis(), trace_verifier()),
      "creating the uninterrupted store");
  for (std::size_t index = 0; index < kContiguousBlocks; ++index) {
    apply_and_compare(store, values, index);
  }
  require_head(store, values, kContiguousBlocks - 1, "the uninterrupted head");
}

}  // namespace sqlite_ledger_v9_tests

int main(int argc, char** argv) {
  namespace pv = protocol_vectors;
  namespace tests = sqlite_ledger_v9_tests;
  try {
    pv::require(argc == 3, "usage: storage_sqlite_ledger_v9_tests VECTORS DIR");
    pv::require(sodium_init() >= 0, "libsodium initialization");
    const auto values = pv::load_values(argv[1]);
    const std::filesystem::path directory(argv[2]);
    std::filesystem::remove_all(directory);
    std::filesystem::create_directories(directory);

    // The run this suite replays is the one the vectors record, block for block
    // and height for height, which is required rather than assumed: a run that
    // grew a block or skipped a height would otherwise fail at a root comparison
    // with its reason unnamed.
    pv::require(tests::recorded_number(values, "restart.block_count") ==
                    tests::kContiguousBlocks,
                "the vectors record the whole replayed run");
    pv::require(tests::restart_run().blocks.size() == tests::kContiguousBlocks &&
                    tests::restart_run().block_inputs.size() ==
                        tests::kContiguousBlocks,
                "the trace offers every block of the replayed run");
    for (std::size_t index = 0; index < tests::kContiguousBlocks; ++index) {
      pv::require(tests::recorded_number(values, tests::block_label(index) +
                                                     ".height") == index + 1,
                  "the replayed run must be contiguous from genesis");
    }

    tests::check_restart_equivalence(values, directory);
    tests::check_uninterrupted(values, directory);
    tests::check_refusals(values, directory);
    tests::check_tampering(values, directory);
    tests::check_column_bounds(values, directory);
    tests::check_page_corruption(values, directory);
    std::filesystem::remove_all(directory);

    std::cout << "C++ version-nine owning store: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "C++ version-nine owning store: failed: " << error.what() << '\n';
    return 1;
  }
}
