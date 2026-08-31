// The version-seven owning store, checked against the recorded execution
// vectors across a real restart.
//
// **This is the question the snapshot's own tests could not ask.** ADR 0056
// restores a *final* ledger and executes one further block; it establishes
// nothing about a chain interrupted in the middle of its history. Here the
// `carried` scenario's four contiguous blocks — heights 1 through 4, the only
// contiguous run any recorded scenario has, because the others skip millions of
// heights between segments — are applied through a database that is **closed and
// reopened between each pair**, and every block must reproduce its *recorded*
// `block_id` and `resulting_state_root`.
//
// Those figures come from a model that knows nothing about SQLite, so a store
// that persisted a subtly different state would fail here rather than agree with
// itself.

#include "sqlite_ledger_v7_fixture.hpp"

#include <iostream>
#include <span>
#include <string>

namespace sqlite_ledger_v7_tests {

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
      "SELECT height, block_id, resulting_state_root, header, transaction_root"
      " FROM blocks_v7 ORDER BY height";
  pv::require(sqlite3_prepare_v2(database, sql, -1, &statement, nullptr) == SQLITE_OK,
              "the history query prepares");
  std::size_t rows = 0;
  while (sqlite3_step(statement) == SQLITE_ROW) {
    const auto label = "carried.block" + std::to_string(rows);
    const auto blob = [&statement](int column) {
      const auto* data =
          static_cast<const std::uint8_t*>(sqlite3_column_blob(statement, column));
      const auto size = static_cast<std::size_t>(
          sqlite3_column_bytes(statement, column));
      return std::span<const std::uint8_t>(data, size);
    };
    pv::require(fixture::hex(blob(1)) == recorded(values, label + ".block_id"),
                label + ": the stored block identifier is not the recorded one");
    pv::require(fixture::hex(blob(2)) ==
                    recorded(values, label + ".resulting_state_root"),
                label + ": the stored root is not the recorded one");
    pv::require(fixture::hex(blob(3)) == recorded(values, label + ".header"),
                label + ": the stored header is not the recorded one");
    // The transaction root is a column of its own rather than a field of the
    // header the row beside it stores, so a row that agreed with the header and
    // disagreed with the vectors would otherwise go unread.
    pv::require(fixture::hex(blob(4)) ==
                    recorded(values, label + ".transaction_root"),
                label + ": the stored transaction root is not the recorded one");
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
        ps::create_sqlite_ledger_v7(path, genesis, trace_verifier()),
        "creating the store");
    apply_and_compare(store, values, 0);
  }
  for (std::size_t index = 1; index < kContiguousBlocks; ++index) {
    auto store = require_store(
        ps::open_sqlite_ledger_v7(path, genesis, trace_verifier()),
        "reopening before block " + std::to_string(index));
    require_head(store, values, index - 1,
                 "the head after restart " + std::to_string(index));
    apply_and_compare(store, values, index);
  }
  {
    auto store = require_store(
        ps::open_sqlite_ledger_v7(path, genesis, trace_verifier()),
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
      ps::create_sqlite_ledger_v7(directory / "straight.db",
                                  fixture::trace_genesis(), trace_verifier()),
      "creating the uninterrupted store");
  for (std::size_t index = 0; index < kContiguousBlocks; ++index) {
    apply_and_compare(store, values, index);
  }
  require_head(store, values, kContiguousBlocks - 1, "the uninterrupted head");
}

}  // namespace sqlite_ledger_v7_tests

int main(int argc, char** argv) {
  namespace pv = protocol_vectors;
  namespace tests = sqlite_ledger_v7_tests;
  try {
    pv::require(argc == 3, "usage: storage_sqlite_ledger_v7_tests VECTORS DIR");
    pv::require(sodium_init() >= 0, "libsodium initialization");
    const auto values = pv::load_values(argv[1]);
    const std::filesystem::path directory(argv[2]);
    std::filesystem::remove_all(directory);
    std::filesystem::create_directories(directory);

    pv::require(tests::carried_scenario().blocks.size() > tests::kContiguousBlocks,
                "the carried scenario has a block past its contiguous run");
    for (std::size_t index = 0; index < tests::kContiguousBlocks; ++index) {
      pv::require(tests::carried_scenario().blocks[index].height == index + 1,
                  "the replayed run must be contiguous from genesis");
      pv::require(!tests::carried_scenario().blocks[index].assigned_window.has_value(),
                  "the replayed run must open no assignment window");
    }

    tests::check_restart_equivalence(values, directory);
    tests::check_uninterrupted(values, directory);
    tests::check_refusals(directory);
    tests::check_tampering(values, directory);
    tests::check_page_corruption(values, directory);
    std::filesystem::remove_all(directory);

    std::cout << "C++ version-seven owning store: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "C++ version-seven owning store: failed: " << error.what() << '\n';
    return 1;
  }
}
