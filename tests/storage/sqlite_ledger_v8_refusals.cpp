// What the version-eight store must refuse.
//
// Three kinds, and they are separated because each is caught somewhere
// different. **A block the store refuses** never reaches the kernel — a height
// that is not the next one. **A block the kernel refuses** reaches it and comes
// back rejected, which is a path nothing else here exercises: every other
// refusal returns before `execute_block` is called, so without it a store that
// committed a rejected block would pass every other check. **A database edited
// behind the store's back** is the only way to reach the reopen validation an
// honest process never triggers.

#include "sqlite_ledger_v8_fixture.hpp"

#include <array>
#include <fstream>
#include <string>
#include <vector>

namespace sqlite_ledger_v8_tests {

void check_refusals(const std::filesystem::path& directory) {
  const auto genesis = fixture::trace_genesis();
  const auto path = directory / "refusals.db";
  {
    auto store = require_store(
        ps::create_sqlite_ledger_v8(path, genesis, trace_verifier()),
        "creating the refusal store");
    // A height that is not the next one is a block this chain cannot be at.
    const auto& scenario = carried_scenario();
    for (const std::uint64_t height : {std::uint64_t{0}, std::uint64_t{2}}) {
      auto applied = store.apply_block(height, scenario.block_inputs[0]);
      pv::require(std::holds_alternative<ps::BlockRejectedV8>(applied),
                  "a block away from the next height must be rejected");
    }
    // A block the *kernel* rejects whole, which is a different path from the
    // store's own height rule: `execute_block` refuses more than 65,535 raw
    // inputs outright. Without this case nothing distinguishes "the kernel said
    // no" from "the store committed anyway", because every other refusal here
    // returns before the kernel is reached.
    const std::vector<v8::Bytes> too_many(v8::kMaxRawInputs + 1, v8::Bytes{});
    auto oversized = store.apply_block(1, too_many);
    pv::require(std::holds_alternative<ps::BlockRejectedV8>(oversized),
                "a block past the input bound must be rejected");

    // A rejected block leaves the head exactly where it was.
    auto head = store.read_head();
    pv::require(std::holds_alternative<ps::LedgerHeadV8>(head),
                "the head survives a rejected block");
    pv::require(std::get<ps::LedgerHeadV8>(std::move(head)).ledger.height == 0,
                "a rejected block advanced the height");
  }
  // ... and it left nothing behind in the database either, which is the half a
  // live head cannot show.
  {
    auto reopened = require_store(
        ps::open_sqlite_ledger_v8(path, genesis, trace_verifier()),
        "reopening after rejected blocks");
    auto head = reopened.read_head();
    pv::require(std::holds_alternative<ps::LedgerHeadV8>(head),
                "the durable head survives a rejected block");
    pv::require(std::get<ps::LedgerHeadV8>(std::move(head)).ledger.height == 0,
                "a rejected block reached the database");
  }
  require_store_error(
      ps::create_sqlite_ledger_v8(path, genesis, trace_verifier()),
      ps::SQLiteLedgerV8Error::path_already_exists,
      "creating over an existing database");
  require_store_error(
      ps::open_sqlite_ledger_v8(directory / "absent.db", genesis, trace_verifier()),
      ps::SQLiteLedgerV8Error::path_not_found, "opening a database that is not there");

  // A different chain. The genesis is stored, so presenting another one is
  // refused before the head is even read.
  auto other = genesis;
  other.network_id += 1;
  require_store_error(ps::open_sqlite_ledger_v8(path, other, trace_verifier()),
                      ps::SQLiteLedgerV8Error::genesis_mismatch,
                      "opening under another genesis");

  auto invalid = genesis;
  invalid.supply_limit = 0;
  require_store_error(
      ps::create_sqlite_ledger_v8(directory / "invalid.db", invalid, trace_verifier()),
      ps::SQLiteLedgerV8Error::invalid_genesis, "creating from an invalid genesis");
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
    ps::SQLiteLedgerV8Error expected;
  };
  // Each is a state no sequence of blocks produced, and each is caught by a
  // different check: the schema comparison, the two columns beside the payload,
  // and the snapshot's own gates.
  const Case cases[] = {
      {"a renamed table", "ALTER TABLE blocks_v8 RENAME TO blocks_v9",
       ps::SQLiteLedgerV8Error::schema_mismatch},
      {"an added column", "ALTER TABLE blocks_v8 ADD COLUMN extra BLOB",
       ps::SQLiteLedgerV8Error::schema_mismatch},
      // Version seven's own number, which is the confusion this pragma exists
      // to refuse: a file the previous adapter wrote is not read by this one.
      {"a rewritten schema version", "PRAGMA main.user_version = 7",
       ps::SQLiteLedgerV8Error::schema_mismatch},
      // And the identifier version seven's store pins, for the same reason: the
      // schema comparison checks it before it reads a single table name.
      {"a rewritten application identifier",
       "PRAGMA main.application_id = 1347636279",
       ps::SQLiteLedgerV8Error::schema_mismatch},
      {"a root that is not the payload's",
       "UPDATE ledger_meta_v8 SET current_state_root = zeroblob(32)",
       ps::SQLiteLedgerV8Error::state_mismatch},
      {"a height that is not the payload's",
       "UPDATE ledger_meta_v8 SET current_height = zeroblob(8)",
       ps::SQLiteLedgerV8Error::state_mismatch},
      // A blob of the right shape for the column's own CHECK and of no shape
       // at all for the decoder, which is where it is caught. **240 rather than
       // version seven's 200**, because the column's minimum moved to
       // `snapshot_v8`'s `kFixedSize` of 222 and a 200-octet blob no longer
       // reaches the decoder at all — which is what the next case checks.
      {"a head payload that is not a snapshot",
       "UPDATE ledger_meta_v8 SET head_snapshot = zeroblob(240)",
       ps::SQLiteLedgerV8Error::invalid_snapshot},
  };

  std::size_t index = 0;
  for (const auto& single : cases) {
    const auto path = directory / ("tamper" + std::to_string(index++) + ".db");
    {
      auto store = require_store(
          ps::create_sqlite_ledger_v8(path, genesis, trace_verifier()),
          "creating the tamper store");
      apply_and_compare(store, values, 0);
    }
    tamper(path, single.statement);
    require_store_error(ps::open_sqlite_ledger_v8(path, genesis, trace_verifier()),
                        single.expected, single.name);
  }
}

// The two column widths that moved with the version, checked at their exact
// boundary so a stale literal in the DDL is a failure here rather than a
// silently weaker refusal.
//
// **This is the case version seven's suite had no reason to write.** Its
// `head_snapshot` minimum and its genesis width were the only ones the family
// had ever had, so nothing could be stale. Version eight moved both, and the
// tamper case above only proves that *some* blob the column admits is refused
// by the decoder — it would still pass if the column had kept 190. What pins
// the figure is that 221 octets is refused by SQLite's own CHECK and 222 is
// not.
void check_column_bounds(const pv::Values& values,
                         const std::filesystem::path& directory) {
  const auto genesis = fixture::trace_genesis();
  const auto path = directory / "bounds.db";
  {
    auto store = require_store(
        ps::create_sqlite_ledger_v8(path, genesis, trace_verifier()),
        "creating the bounds store");
    apply_and_compare(store, values, 0);
  }

  struct Case {
    const char* name;
    const char* statement;
    bool admitted;
  };
  const Case cases[] = {
      // `snapshot_v8`'s `kFixedSize` is 222: the 158-octet prefix, a root, and
      // a digest. One octet short of it is a blob no payload could be.
      {"a head payload one octet under the decoder's fixed size",
       "UPDATE ledger_meta_v8 SET head_snapshot = zeroblob(221)", false},
      {"a head payload of exactly the decoder's fixed size",
       "UPDATE ledger_meta_v8 SET head_snapshot = zeroblob(222)", true},
      // `v8::kGenesisPrefixBytes` is 142. Version seven's 110 is the width a
      // stale literal would still be admitting.
      {"a canonical genesis at version seven's width",
       "UPDATE ledger_meta_v8 SET canonical_genesis = zeroblob(110)", false},
      {"a canonical genesis at version eight's width",
       "UPDATE ledger_meta_v8 SET canonical_genesis = zeroblob(142)", true},
  };

  for (const auto& single : cases) {
    sqlite3* database = nullptr;
    pv::require(sqlite3_open(path.c_str(), &database) == SQLITE_OK,
                "the bounds connection opens");
    char* message = nullptr;
    const auto status =
        sqlite3_exec(database, single.statement, nullptr, nullptr, &message);
    if (message != nullptr) sqlite3_free(message);
    sqlite3_close(database);
    if (single.admitted) {
      pv::require(status == SQLITE_OK,
                  std::string("the column refused ") + single.name);
    } else {
      pv::require(status == SQLITE_CONSTRAINT,
                  std::string("the column admitted ") + single.name);
    }
  }

  // The two admitted writes left a file the store must still refuse, which is
  // what keeps this a statement about the column rather than a way in.
  require_store_error(
      ps::open_sqlite_ledger_v8(path, genesis, trace_verifier()),
      ps::SQLiteLedgerV8Error::genesis_mismatch,
      "opening a database whose columns were widened to their bounds");
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
        ps::create_sqlite_ledger_v8(path, genesis, trace_verifier()),
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

  require_store_error(ps::open_sqlite_ledger_v8(path, genesis, trace_verifier()),
                      ps::SQLiteLedgerV8Error::integrity_failure,
                      "opening a database with a corrupted page");
}

}  // namespace sqlite_ledger_v8_tests
