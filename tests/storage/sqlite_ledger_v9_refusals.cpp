// What the version-nine store must refuse.
//
// Three kinds, and they are separated because each is caught somewhere
// different. **A block the store refuses** never reaches the kernel — a height
// that is not the next one. **A block the kernel refuses** reaches it and comes
// back rejected, which is a path nothing else here exercises: every other
// refusal returns before `execute_block` is called, so without it a store that
// committed a rejected block would pass every other check. Version nine adds two
// such refusals, a stamp C1 has no month for and a stamp C2 finds going
// backwards, and each is offered on its own. **A database edited behind the
// store's back** is the only way to reach the reopen validation an honest
// process never triggers.

#include "sqlite_ledger_v9_fixture.hpp"

#include <array>
#include <fstream>
#include <string>
#include <vector>

namespace sqlite_ledger_v9_tests {
namespace {

// Eight octets of `value`, big-endian, as an SQL blob literal.
std::string blob_literal(std::uint64_t value) {
  std::array<std::uint8_t, 8> octets{};
  for (std::size_t index = 0; index < octets.size(); ++index) {
    octets[index] = static_cast<std::uint8_t>(value >> (56U - 8U * index));
  }
  return "X'" + fixture::hex(std::span<const std::uint8_t>(octets)) + "'";
}

}  // namespace

void check_refusals(const pv::Values& values,
                    const std::filesystem::path& directory) {
  const auto genesis = fixture::trace_genesis();
  const auto path = directory / "refusals.db";
  const auto& inputs = restart_run().block_inputs[0];
  const auto stamp = recorded_number(values, "restart.block0.timestamp");
  {
    auto store = require_store(
        ps::create_sqlite_ledger_v9(path, genesis, trace_verifier()),
        "creating the refusal store");
    // A height that is not the next one is a block this chain cannot be at.
    for (const std::uint64_t height : {std::uint64_t{0}, std::uint64_t{2}}) {
      auto applied = store.apply_block(height, stamp, inputs);
      pv::require(std::holds_alternative<ps::BlockRejectedV9>(applied),
                  "a block away from the next height must be rejected");
    }
    // A block the *kernel* rejects whole, which is a different path from the
    // store's own height rule: `execute_block` refuses more than 65,535 raw
    // inputs outright. Without this case nothing distinguishes "the kernel said
    // no" from "the store committed anyway", because every other refusal here
    // returns before the kernel is reached.
    const std::vector<v9::Bytes> too_many(v9::kMaxRawInputs + 1, v9::Bytes{});
    auto oversized = store.apply_block(1, stamp, too_many);
    pv::require(std::holds_alternative<ps::BlockRejectedV9>(oversized),
                "a block past the input bound must be rejected");

    // The two the clock adds, each on the block that would otherwise commit.
    // C1: a stamp past December 9999 has no month, so no step may be handed it.
    auto unmonthed = store.apply_block(1, v9::kMaxTimestampMillis + 1, inputs);
    pv::require(std::holds_alternative<ps::BlockRejectedV9>(unmonthed),
                "a stamp outside the calendar's range must be rejected");
    // C2 at height 1 compares against the genesis stamp, which is the
    // genesis case of the same rule rather than a special one.
    auto early = store.apply_block(1, fixture::kGenesisMillis - 1, inputs);
    pv::require(std::holds_alternative<ps::BlockRejectedV9>(early),
                "a stamp below the genesis stamp must be rejected");

    // A rejected block leaves the head exactly where it was.
    auto head = store.read_head();
    pv::require(std::holds_alternative<ps::LedgerHeadV9>(head),
                "the head survives a rejected block");
    const auto value = std::get<ps::LedgerHeadV9>(std::move(head));
    pv::require(value.ledger.height == 0, "a rejected block advanced the height");
    pv::require(value.ledger.timestamp == fixture::kGenesisMillis,
                "a rejected block moved the stamp");
  }
  // ... and it left nothing behind in the database either, which is the half a
  // live head cannot show.
  {
    auto reopened = require_store(
        ps::open_sqlite_ledger_v9(path, genesis, trace_verifier()),
        "reopening after rejected blocks");
    auto head = reopened.read_head();
    pv::require(std::holds_alternative<ps::LedgerHeadV9>(head),
                "the durable head survives a rejected block");
    const auto value = std::get<ps::LedgerHeadV9>(std::move(head));
    pv::require(value.ledger.height == 0, "a rejected block reached the database");
    pv::require(value.ledger.timestamp == fixture::kGenesisMillis,
                "a rejected block's stamp reached the database");
  }
  require_store_error(
      ps::create_sqlite_ledger_v9(path, genesis, trace_verifier()),
      ps::SQLiteLedgerV9Error::path_already_exists,
      "creating over an existing database");
  require_store_error(
      ps::open_sqlite_ledger_v9(directory / "absent.db", genesis, trace_verifier()),
      ps::SQLiteLedgerV9Error::path_not_found, "opening a database that is not there");

  // A different chain. The genesis is stored, so presenting another one is
  // refused before the head is even read.
  auto other = genesis;
  other.network_id += 1;
  require_store_error(ps::open_sqlite_ledger_v9(path, other, trace_verifier()),
                      ps::SQLiteLedgerV9Error::genesis_mismatch,
                      "opening under another genesis");
  // **The same chain in every field but the one version nine adds.** The genesis
  // timestamp is not a snapshot parameter, so nothing downstream of this check
  // would compare it; it is refused here because it changes the canonical bytes.
  auto restamped = genesis;
  restamped.genesis_timestamp += 1;
  require_store_error(ps::open_sqlite_ledger_v9(path, restamped, trace_verifier()),
                      ps::SQLiteLedgerV9Error::genesis_mismatch,
                      "opening under another genesis timestamp");

  auto invalid = genesis;
  invalid.supply_limit = 0;
  require_store_error(
      ps::create_sqlite_ledger_v9(directory / "invalid.db", invalid, trace_verifier()),
      ps::SQLiteLedgerV9Error::invalid_genesis, "creating from an invalid genesis");
  // A genesis whose stamp has no month is refused before a file exists, which
  // is C1 at the only point genesis validation applies it.
  auto unmonthed = genesis;
  unmonthed.genesis_timestamp = v9::kMaxTimestampMillis + 1;
  require_store_error(
      ps::create_sqlite_ledger_v9(directory / "unmonthed.db", unmonthed,
                                  trace_verifier()),
      ps::SQLiteLedgerV9Error::invalid_genesis,
      "creating from a genesis stamp outside the range");
  pv::require(!std::filesystem::exists(directory / "unmonthed.db"),
              "a refused genesis left a file behind");
}

// Edit the database behind the store's back, which is the only way to reach the
// validation an honest process never triggers. Each case is a single statement,
// so the failure it produces has one cause.
void tamper(const std::filesystem::path& path, const std::string& statement) {
  sqlite3* database = nullptr;
  pv::require(sqlite3_open(path.c_str(), &database) == SQLITE_OK,
              "the tamper connection opens");
  char* message = nullptr;
  const auto status =
      sqlite3_exec(database, statement.c_str(), nullptr, nullptr, &message);
  if (message != nullptr) sqlite3_free(message);
  sqlite3_close(database);
  pv::require(status == SQLITE_OK, "tampering failed: " + statement);
}

void check_tampering(const pv::Values& values,
                     const std::filesystem::path& directory) {
  const auto genesis = fixture::trace_genesis();

  struct Case {
    std::string name;
    std::string statement;
    ps::SQLiteLedgerV9Error expected;
  };
  // Each is a state no sequence of blocks produced, and each is caught by a
  // different check: the schema comparison, the three columns beside the
  // payload, and the snapshot's own gates.
  const std::vector<Case> cases{
      {"a renamed table", "ALTER TABLE blocks_v9 RENAME TO blocks_v10",
       ps::SQLiteLedgerV9Error::schema_mismatch},
      {"an added column", "ALTER TABLE blocks_v9 ADD COLUMN extra BLOB",
       ps::SQLiteLedgerV9Error::schema_mismatch},
      // Version eight's own number, which is the confusion this pragma exists
      // to refuse: a file the previous adapter wrote is not read by this one.
      {"a rewritten schema version", "PRAGMA main.user_version = 8",
       ps::SQLiteLedgerV9Error::schema_mismatch},
      // And the identifier version eight's store pins, for the same reason: the
      // schema comparison checks it before it reads a single table name.
      {"a rewritten application identifier",
       "PRAGMA main.application_id = 1347636280",
       ps::SQLiteLedgerV9Error::schema_mismatch},
      {"a root that is not the payload's",
       "UPDATE ledger_meta_v9 SET current_state_root = zeroblob(32)",
       ps::SQLiteLedgerV9Error::state_mismatch},
      {"a height that is not the payload's",
       "UPDATE ledger_meta_v9 SET current_height = zeroblob(8)",
       ps::SQLiteLedgerV9Error::state_mismatch},
      // **The stamp version nine could lose, in the exact shape it would be
      // lost**: the head is at height 1 and its stamp column is rewound to the
      // genesis stamp, which is the predecessor's. Every block after it would
      // still satisfy C2 against that value, so nothing but this comparison
      // would ever notice.
      {"a stamp that belongs to the previous height",
       "UPDATE ledger_meta_v9 SET current_timestamp_millis = " +
           blob_literal(fixture::kGenesisMillis),
       ps::SQLiteLedgerV9Error::state_mismatch},
      // A blob of the right shape for the column's own CHECK and of no shape
      // at all for the decoder, which is where it is caught. 240 is above
      // `snapshot_v9`'s `kFixedSize` of 230, so it reaches the decoder rather
      // than being refused by the column — which is what the next case checks.
      {"a head payload that is not a snapshot",
       "UPDATE ledger_meta_v9 SET head_snapshot = zeroblob(240)",
       ps::SQLiteLedgerV9Error::invalid_snapshot},
  };

  std::size_t index = 0;
  for (const auto& single : cases) {
    const auto path = directory / ("tamper" + std::to_string(index++) + ".db");
    {
      auto store = require_store(
          ps::create_sqlite_ledger_v9(path, genesis, trace_verifier()),
          "creating the tamper store");
      apply_and_compare(store, values, 0);
    }
    tamper(path, single.statement);
    require_store_error(ps::open_sqlite_ledger_v9(path, genesis, trace_verifier()),
                        single.expected, single.name);
  }
}

// The three column widths that moved with the version, checked at their exact
// boundary so a stale literal in the DDL is a failure here rather than a
// silently weaker refusal or a store that creates a genesis and refuses every
// block.
//
// The tamper case above only proves that *some* blob the payload column admits
// is refused by the decoder — it would still pass if the column had kept
// version eight's 222. What pins each figure is its boundary.
void check_column_bounds(const pv::Values& values,
                         const std::filesystem::path& directory) {
  const auto genesis = fixture::trace_genesis();
  const auto path = directory / "bounds.db";
  {
    auto store = require_store(
        ps::create_sqlite_ledger_v9(path, genesis, trace_verifier()),
        "creating the bounds store");
    apply_and_compare(store, values, 0);
  }

  struct Case {
    const char* name;
    const char* statement;
    bool admitted;
  };
  const Case cases[] = {
      // `snapshot_v9`'s `kFixedSize` is 230: the 166-octet prefix, a root, and
      // a digest. One octet short of it is a blob no payload could be.
      {"a head payload one octet under the decoder's fixed size",
       "UPDATE ledger_meta_v9 SET head_snapshot = zeroblob(229)", false},
      {"a head payload of exactly the decoder's fixed size",
       "UPDATE ledger_meta_v9 SET head_snapshot = zeroblob(230)", true},
      // `v9::kGenesisPrefixBytes` is 150. Version eight's 142 is the width a
      // stale literal would still be admitting.
      {"a canonical genesis at version eight's width",
       "UPDATE ledger_meta_v9 SET canonical_genesis = zeroblob(142)", false},
      {"a canonical genesis at version nine's width",
       "UPDATE ledger_meta_v9 SET canonical_genesis = zeroblob(150)", true},
      // `v9::kBlockHeaderBytes` is 154. Version one's 146 is the width every
      // version through eight stored, and the one a copied DDL would keep.
      {"a block header at version one's width",
       "UPDATE blocks_v9 SET header = zeroblob(146)", false},
      {"a block header at version nine's width",
       "UPDATE blocks_v9 SET header = zeroblob(154)", true},
  };

  for (const auto& single : cases) {
    sqlite3* database = nullptr;
    pv::require(sqlite3_open(path.c_str(), &database) == SQLITE_OK,
                "the bounds connection opens");
    char* message = nullptr;
    const auto status =
        sqlite3_exec(database, single.statement, nullptr, nullptr, &message);
    const auto changed = sqlite3_changes(database);
    if (message != nullptr) sqlite3_free(message);
    sqlite3_close(database);
    if (single.admitted) {
      pv::require(status == SQLITE_OK,
                  std::string("the column refused ") + single.name);
      // An UPDATE over no rows is admitted too, and would prove nothing.
      pv::require(changed == 1, std::string("no row carried ") + single.name);
    } else {
      pv::require(status == SQLITE_CONSTRAINT,
                  std::string("the column admitted ") + single.name);
    }
  }

  // The admitted writes left a file the store must still refuse, which is what
  // keeps this a statement about the columns rather than a way in.
  require_store_error(
      ps::open_sqlite_ledger_v9(path, genesis, trace_verifier()),
      ps::SQLiteLedgerV9Error::genesis_mismatch,
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
        ps::create_sqlite_ledger_v9(path, genesis, trace_verifier()),
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

  require_store_error(ps::open_sqlite_ledger_v9(path, genesis, trace_verifier()),
                      ps::SQLiteLedgerV9Error::integrity_failure,
                      "opening a database with a corrupted page");
}

}  // namespace sqlite_ledger_v9_tests
