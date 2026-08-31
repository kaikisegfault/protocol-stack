// What the version-seven store must refuse.
//
// Three kinds, and they are separated because each is caught somewhere
// different. **A block the store refuses** never reaches the kernel — a height
// that is not the next one. **A block the kernel refuses** reaches it and comes
// back rejected, which is a path nothing else here exercises: every other
// refusal returns before `execute_block` is called, so without it a store that
// committed a rejected block would pass every other check. **A database edited
// behind the store's back** is the only way to reach the reopen validation an
// honest process never triggers.

#include "sqlite_ledger_v7_fixture.hpp"

#include <array>
#include <fstream>
#include <string>
#include <vector>

namespace sqlite_ledger_v7_tests {

void check_refusals(const std::filesystem::path& directory) {
  const auto genesis = fixture::trace_genesis();
  const auto path = directory / "refusals.db";
  {
    auto store = require_store(
        ps::create_sqlite_ledger_v7(path, genesis, trace_verifier()),
        "creating the refusal store");
    // A height that is not the next one is a block this chain cannot be at.
    const auto& scenario = carried_scenario();
    for (const std::uint64_t height : {std::uint64_t{0}, std::uint64_t{2}}) {
      auto applied = store.apply_block(height, scenario.block_inputs[0]);
      pv::require(std::holds_alternative<ps::BlockRejectedV7>(applied),
                  "a block away from the next height must be rejected");
    }
    // A block the *kernel* rejects whole, which is a different path from the
    // store's own height rule: `execute_block` refuses more than 65,535 raw
    // inputs outright. Without this case nothing distinguishes "the kernel said
    // no" from "the store committed anyway", because every other refusal here
    // returns before the kernel is reached.
    const std::vector<v7::Bytes> too_many(v7::kMaxRawInputs + 1, v7::Bytes{});
    auto oversized = store.apply_block(1, too_many);
    pv::require(std::holds_alternative<ps::BlockRejectedV7>(oversized),
                "a block past the input bound must be rejected");

    // A rejected block leaves the head exactly where it was.
    auto head = store.read_head();
    pv::require(std::holds_alternative<ps::LedgerHeadV7>(head),
                "the head survives a rejected block");
    pv::require(std::get<ps::LedgerHeadV7>(std::move(head)).ledger.height == 0,
                "a rejected block advanced the height");
  }
  // ... and it left nothing behind in the database either, which is the half a
  // live head cannot show.
  {
    auto reopened = require_store(
        ps::open_sqlite_ledger_v7(path, genesis, trace_verifier()),
        "reopening after rejected blocks");
    auto head = reopened.read_head();
    pv::require(std::holds_alternative<ps::LedgerHeadV7>(head),
                "the durable head survives a rejected block");
    pv::require(std::get<ps::LedgerHeadV7>(std::move(head)).ledger.height == 0,
                "a rejected block reached the database");
  }
  require_store_error(
      ps::create_sqlite_ledger_v7(path, genesis, trace_verifier()),
      ps::SQLiteLedgerV7Error::path_already_exists,
      "creating over an existing database");
  require_store_error(
      ps::open_sqlite_ledger_v7(directory / "absent.db", genesis, trace_verifier()),
      ps::SQLiteLedgerV7Error::path_not_found, "opening a database that is not there");

  // A different chain. The genesis is stored, so presenting another one is
  // refused before the head is even read.
  auto other = genesis;
  other.network_id += 1;
  require_store_error(ps::open_sqlite_ledger_v7(path, other, trace_verifier()),
                      ps::SQLiteLedgerV7Error::genesis_mismatch,
                      "opening under another genesis");

  auto invalid = genesis;
  invalid.supply_limit = 0;
  require_store_error(
      ps::create_sqlite_ledger_v7(directory / "invalid.db", invalid, trace_verifier()),
      ps::SQLiteLedgerV7Error::invalid_genesis, "creating from an invalid genesis");
}

// Edit the database behind the store's back, which is the only way to reach the
// validation an honest process never triggers. Each case is a single statement,
// so the failure it produces has one cause.
void tamper(const std::filesystem::path& path, const char* statement) {
  sqlite3* database = nullptr;
  pv::require(sqlite3_open(path.c_str(), &database) == SQLITE_OK,
              "the tamper connection opens");
  char* message = nullptr;
  const auto status = sqlite3_exec(database, statement, nullptr, nullptr, &message);
  if (message != nullptr) sqlite3_free(message);
  sqlite3_close(database);
  pv::require(status == SQLITE_OK, std::string("tampering failed: ") + statement);
}

void check_tampering(const pv::Values& values,
                     const std::filesystem::path& directory) {
  const auto genesis = fixture::trace_genesis();

  struct Case {
    const char* name;
    const char* statement;
    ps::SQLiteLedgerV7Error expected;
  };
  // Each is a state no sequence of blocks produced, and each is caught by a
  // different check: the schema comparison, the two columns beside the payload,
  // and the snapshot's own gates.
  const Case cases[] = {
      {"a renamed table", "ALTER TABLE blocks_v7 RENAME TO blocks_v8",
       ps::SQLiteLedgerV7Error::schema_mismatch},
      {"an added column", "ALTER TABLE blocks_v7 ADD COLUMN extra BLOB",
       ps::SQLiteLedgerV7Error::schema_mismatch},
      {"a rewritten schema version", "PRAGMA main.user_version = 6",
       ps::SQLiteLedgerV7Error::schema_mismatch},
      {"a root that is not the payload's",
       "UPDATE ledger_meta_v7 SET current_state_root = zeroblob(32)",
       ps::SQLiteLedgerV7Error::state_mismatch},
      {"a height that is not the payload's",
       "UPDATE ledger_meta_v7 SET current_height = zeroblob(8)",
       ps::SQLiteLedgerV7Error::state_mismatch},
      // A blob of the right shape for the column's own CHECK and of no shape
       // at all for the decoder, which is where it is caught.
      {"a head payload that is not a snapshot",
       "UPDATE ledger_meta_v7 SET head_snapshot = zeroblob(200)",
       ps::SQLiteLedgerV7Error::invalid_snapshot},
  };

  std::size_t index = 0;
  for (const auto& single : cases) {
    const auto path = directory / ("tamper" + std::to_string(index++) + ".db");
    {
      auto store = require_store(
          ps::create_sqlite_ledger_v7(path, genesis, trace_verifier()),
          "creating the tamper store");
      apply_and_compare(store, values, 0);
    }
    tamper(path, single.statement);
    require_store_error(ps::open_sqlite_ledger_v7(path, genesis, trace_verifier()),
                        single.expected, single.name);
  }
}

// Corrupt a b-tree page directly, which is the one failure no statement can
// produce: every tamper case above leaves a database SQLite considers valid, so
// without this the integrity check is never the reason an open fails.
//
// Page 1 holds the schema and is left alone deliberately — destroying it makes
// SQLite refuse the file as not a database at all, which is a different failure
// reached before the integrity check runs.
void check_page_corruption(const pv::Values& values,
                           const std::filesystem::path& directory) {
  const auto genesis = fixture::trace_genesis();
  const auto path = directory / "corrupt.db";
  {
    auto store = require_store(
        ps::create_sqlite_ledger_v7(path, genesis, trace_verifier()),
        "creating the corruption store");
    apply_and_compare(store, values, 0);
  }
  std::fstream file(path, std::ios::in | std::ios::out | std::ios::binary);
  pv::require(file.good(), "the database file opens for corruption");
  file.seekg(0, std::ios::end);
  const auto size = static_cast<std::uint64_t>(file.tellg());
  pv::require(size > 8192, "the database has a page past its first");
  // The b-tree page header itself — its type byte and cell count — rather than
  // the bytes inside a cell, because SQLite validates the structure and not the
  // payload.
  const std::array<char, 4096> rubbish{};
  file.seekp(4096);
  file.write(rubbish.data(), static_cast<std::streamsize>(rubbish.size()));
  file.close();

  require_store_error(ps::open_sqlite_ledger_v7(path, genesis, trace_verifier()),
                      ps::SQLiteLedgerV7Error::integrity_failure,
                      "opening a database with a corrupted page");
}

}  // namespace sqlite_ledger_v7_tests
