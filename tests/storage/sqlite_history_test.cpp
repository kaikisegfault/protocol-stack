#include "protocol/storage/sqlite_ledger.hpp"
#include "protocol/v1/ledger.hpp"

#include "../../tools/protocol-vectors/vector_common.hpp"

#include <sqlite3.h>

#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <variant>
#include <vector>

namespace pv = protocol_vectors;
namespace ps = protocol::storage;
namespace p = protocol::v1;

namespace {

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

void require_open_error(
    ps::SQLiteLedgerResult result,
    ps::SQLiteLedgerError expected,
    std::string_view message) {
  pv::require(
      std::holds_alternative<ps::SQLiteLedgerError>(result.result) &&
          std::get<ps::SQLiteLedgerError>(result.result) == expected,
      message);
}

void require_block_error(
    ps::SQLiteBlockResult result,
    p::BlockError expected,
    std::string_view message) {
  pv::require(
      std::holds_alternative<p::BlockError>(result) &&
          std::get<p::BlockError>(result) == expected,
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

void raw_execute(
    const std::filesystem::path& path,
    const std::string& sql) {
  sqlite3* database = nullptr;
  const auto opened = sqlite3_open_v2(
      path.c_str(), &database,
      SQLITE_OPEN_READWRITE | SQLITE_OPEN_PRIVATECACHE |
          SQLITE_OPEN_NOFOLLOW | SQLITE_OPEN_EXRESCODE,
      nullptr);
  if (opened != SQLITE_OK) {
    if (database != nullptr) sqlite3_close(database);
    throw std::runtime_error("raw SQLite open failed");
  }
  const auto executed =
      sqlite3_exec(database, sql.c_str(), nullptr, nullptr, nullptr);
  const auto closed = sqlite3_close(database);
  pv::require(executed == SQLITE_OK, "raw SQLite execution failed");
  pv::require(closed == SQLITE_OK, "raw SQLite close failed");
}

std::string raw_scalar_text(
    const std::filesystem::path& path,
    const char* sql) {
  sqlite3* database = nullptr;
  pv::require(
      sqlite3_open_v2(
          path.c_str(), &database,
          SQLITE_OPEN_READWRITE | SQLITE_OPEN_PRIVATECACHE |
              SQLITE_OPEN_NOFOLLOW | SQLITE_OPEN_EXRESCODE,
          nullptr) == SQLITE_OK,
      "raw scalar open failed");
  sqlite3_stmt* statement = nullptr;
  pv::require(
      sqlite3_prepare_v2(database, sql, -1, &statement, nullptr) ==
          SQLITE_OK,
      "raw scalar prepare failed");
  pv::require(sqlite3_step(statement) == SQLITE_ROW,
              "raw scalar row missing");
  const auto* raw = sqlite3_column_text(statement, 0);
  pv::require(raw != nullptr, "raw scalar text missing");
  const std::string value(reinterpret_cast<const char*>(raw));
  pv::require(sqlite3_step(statement) == SQLITE_DONE,
              "raw scalar extra row");
  pv::require(sqlite3_finalize(statement) == SQLITE_OK,
              "raw scalar finalize failed");
  pv::require(sqlite3_close(database) == SQLITE_OK,
              "raw scalar close failed");
  return value;
}

void create_durable_block(
    const std::filesystem::path& path,
    const p::Bytes& genesis,
    const std::vector<p::Bytes>& transactions) {
  auto ledger = take_ledger(
      ps::create_sqlite_ledger(path, genesis),
      "corruption baseline create failed");
  (void)take_commit(
      ledger.apply_block(1, transactions),
      "corruption baseline block failed");
}

void verify_durable_block(
    const pv::Values& values,
    const std::filesystem::path& prefix) {
  DatabaseFiles files(prefix.string() + "-block.db");
  const auto genesis = genesis_bytes(values);
  const auto transactions = block_transactions(values);

  auto loaded = p::load_genesis(genesis);
  pv::require(std::holds_alternative<p::Ledger>(loaded.result),
              "fixture genesis rejected");
  auto expected_ledger =
      std::get<p::Ledger>(std::move(loaded.result));
  auto expected_result =
      expected_ledger.apply_block(1, transactions);
  pv::require(
      std::holds_alternative<p::BlockCommit>(expected_result),
      "fixture block rejected");
  const auto expected_commit =
      std::get<p::BlockCommit>(std::move(expected_result));
  const ps::LedgerHead expected{
      expected_ledger.state(), expected_commit.resulting_state_root};

  {
    auto stored = take_ledger(
        ps::create_sqlite_ledger(files.path(), genesis),
        "durable database create failed");
    const auto commit = take_commit(
        stored.apply_block(1, transactions), "durable block rejected");
    pv::require(same_commit(commit, expected_commit),
                "durable output changed");
    pv::require(
        take_head(stored.read_head(), "published head read failed") ==
            expected,
                "published head mismatch");
    require_block_error(
        stored.apply_block(1, transactions),
        p::BlockError::invalid_height,
        "rejected block returned wrong error");
    pv::require(
        take_head(stored.read_head(), "rejected head read failed") ==
            expected,
                "rejected block changed head");
  }

  pv::require(
      raw_scalar_text(files.path(), "SELECT count(*) FROM blocks") == "1",
      "durable block row missing");
  pv::require(
      raw_scalar_text(
          files.path(),
          "SELECT count(*) FROM admitted_transactions") ==
          values.at("admitted_count"),
      "journal retained wrong input count");

  auto reopened = take_ledger(
      ps::open_sqlite_ledger(files.path(), genesis),
      "full genesis replay rejected");
  pv::require(
      take_head(reopened.read_head(), "replayed head read failed") ==
          expected,
              "replayed head mismatch");
}

void require_corruption_rejected(
    const std::filesystem::path& path,
    const p::Bytes& genesis,
    const std::vector<p::Bytes>& transactions,
    const std::string& sql,
    std::string_view message) {
  DatabaseFiles files(path);
  create_durable_block(files.path(), genesis, transactions);
  raw_execute(files.path(), sql);
  require_open_error(
      ps::open_sqlite_ledger(files.path(), genesis),
      ps::SQLiteLedgerError::state_mismatch, message);
}

void verify_replay_rejection(
    const pv::Values& values,
    const std::filesystem::path& prefix) {
  const auto genesis = genesis_bytes(values);
  const auto transactions = block_transactions(values);

  DatabaseFiles wrong(prefix.string() + "-wrong-genesis.db");
  create_durable_block(wrong.path(), genesis, transactions);
  auto alternate = genesis;
  alternate[33] ^= 1U;
  require_open_error(
      ps::open_sqlite_ledger(wrong.path(), alternate),
      ps::SQLiteLedgerError::genesis_mismatch,
      "wrong genesis lost precedence before replay");

  require_corruption_rejected(
      prefix.string() + "-transaction-id.db", genesis, transactions,
      "UPDATE admitted_transactions SET transaction_id=zeroblob(32) "
      "WHERE ordinal=X'00000000';",
      "transaction-ID corruption accepted");
  require_corruption_rejected(
      prefix.string() + "-ordinal-gap.db", genesis, transactions,
      "DELETE FROM admitted_transactions WHERE ordinal=X'00000005';",
      "missing journal ordinal accepted");
  require_corruption_rejected(
      prefix.string() + "-block-id.db", genesis, transactions,
      "UPDATE blocks SET block_id=zeroblob(32);",
      "block-ID corruption accepted");
  require_corruption_rejected(
      prefix.string() + "-materialized.db", genesis, transactions,
      "UPDATE accounts SET balance=X'0000000000000000' "
      "WHERE account_id=(SELECT account_id FROM accounts "
      "ORDER BY account_id LIMIT 1);",
      "materialized state diverging from replay accepted");
}

void verify_multiblock_restarts(
    const pv::Values& values,
    const std::filesystem::path& prefix) {
  DatabaseFiles files(prefix.string() + "-restarts.db");
  const auto genesis = genesis_bytes(values);
  const auto full_block = block_transactions(values);
  const std::vector<p::Bytes> empty_block;
  const std::vector<p::Bytes> unadmitted{
      full_block[11], full_block[12], full_block[13], full_block[14]};
  const std::vector<p::Bytes> duplicates{
      full_block[0], full_block[0]};

  auto loaded = p::load_genesis(genesis);
  pv::require(std::holds_alternative<p::Ledger>(loaded.result),
              "restart fixture genesis rejected");
  auto expected = std::get<p::Ledger>(std::move(loaded.result));
  {
    auto created = take_ledger(
        ps::create_sqlite_ledger(files.path(), genesis),
        "restart database create failed");
    pv::require(
        take_head(created.read_head(), "restart genesis read failed").state ==
            expected.state(),
                "restart genesis head mismatch");
  }

  const auto apply_after_reopen =
      [&](std::uint64_t height,
          const std::vector<p::Bytes>& transactions) {
        auto expected_result =
            expected.apply_block(height, transactions);
        pv::require(
            std::holds_alternative<p::BlockCommit>(expected_result),
            "expected restart block rejected");
        auto expected_commit =
            std::get<p::BlockCommit>(std::move(expected_result));
        auto reopened = take_ledger(
            ps::open_sqlite_ledger(files.path(), genesis),
            "intermediate restart rejected");
        const auto actual_commit = take_commit(
            reopened.apply_block(height, transactions),
            "continued restart block rejected");
        pv::require(same_commit(actual_commit, expected_commit),
                    "continued restart output mismatch");
        pv::require(
            take_head(
                reopened.read_head(),
                "continued restart head read failed") ==
                ps::LedgerHead{
                    expected.state(),
                    expected_commit.resulting_state_root},
            "continued restart head mismatch");
        return expected_commit;
      };

  const auto first = apply_after_reopen(1, full_block);
  pv::require(first.transaction_ids.size() == 11,
              "mixed block admitted count mismatch");

  const auto empty = apply_after_reopen(2, empty_block);
  pv::require(
      empty.admissions.empty() && empty.transaction_ids.empty(),
      "empty block stored application inputs");

  const auto omitted = apply_after_reopen(3, unadmitted);
  pv::require(omitted.transaction_ids.empty(),
              "unadmitted block entered journal");
  for (const auto& admission : omitted.admissions) {
    pv::require(admission.has_value(),
                "unadmitted block accepted an input");
  }

  const auto duplicate = apply_after_reopen(4, duplicates);
  pv::require(
      duplicate.transaction_ids.size() == 2 &&
          duplicate.transaction_ids[0] == duplicate.transaction_ids[1] &&
          duplicate.receipts[0].result ==
              p::TransferResult::expired &&
          duplicate.receipts[1].result ==
              p::TransferResult::expired,
      "duplicate admitted journal behavior changed");

  pv::require(
      raw_scalar_text(files.path(), "SELECT count(*) FROM blocks") == "4",
      "multi-block history count mismatch");
  pv::require(
      raw_scalar_text(
          files.path(),
          "SELECT count(*) FROM admitted_transactions") == "13",
      "multi-block admitted count mismatch");

  for (int restart = 0; restart < 2; ++restart) {
    auto reopened = take_ledger(
        ps::open_sqlite_ledger(files.path(), genesis),
        "repeated final restart rejected");
    pv::require(
        take_head(
            reopened.read_head(),
            "repeated restart head read failed") ==
            ps::LedgerHead{
                expected.state(), duplicate.resulting_state_root},
        "repeated final restart head mismatch");
  }
}

}  // namespace

int main(int argc, char** argv) {
  try {
    pv::require(
        argc == 3,
        "usage: storage_sqlite_history_tests VECTOR_FILE PATH_PREFIX");
    pv::require(sodium_init() >= 0, "libsodium initialization");
    const auto values = pv::load_values(argv[1]);
    const std::filesystem::path prefix(argv[2]);
    verify_durable_block(values, prefix);
    verify_replay_rejection(values, prefix);
    verify_multiblock_restarts(values, prefix);
    std::cout << "SQLite history tests: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "SQLite history tests: failed: "
              << error.what() << '\n';
    return 1;
  }
}
