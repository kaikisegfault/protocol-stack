#include "protocol/storage/snapshot_v1.hpp"
#include "protocol/storage/sqlite_ledger.hpp"
#include "protocol/v1/crypto.hpp"
#include "protocol/v1/ledger.hpp"

#include "../../tools/protocol-vectors/vector_common.hpp"

#include <sqlite3.h>

#include <algorithm>
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

constexpr std::size_t kPrefixSize = 86;
constexpr std::size_t kAccountSize = 48;
constexpr std::size_t kDigestSize = 32;
constexpr char kDigestDomain[] =
    "protocol-stack:storage:snapshot-v1";

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
  pv::require(std::holds_alternative<p::Ledger>(loaded.result),
              "fixture genesis rejected");
  return std::get<p::Ledger>(std::move(loaded.result));
}

ps::LedgerHead ledger_head(const p::Ledger& ledger) {
  const auto root = ledger.current_state_root();
  pv::require(std::holds_alternative<p::StateRoot>(root),
              "expected ledger root rejected");
  return ps::LedgerHead{
      ledger.state(), std::get<p::StateRoot>(root)};
}

ps::EncodedSnapshotV1 take_encoded(
    ps::SnapshotV1EncodeResult result,
    std::string_view message) {
  pv::require(
      std::holds_alternative<ps::EncodedSnapshotV1>(result), message);
  return std::get<ps::EncodedSnapshotV1>(std::move(result));
}

ps::DecodedSnapshotV1 take_decoded(
    ps::SnapshotV1DecodeResult result,
    std::string_view message) {
  pv::require(
      std::holds_alternative<ps::DecodedSnapshotV1>(result), message);
  return std::get<ps::DecodedSnapshotV1>(std::move(result));
}

void require_decode_error(
    const p::Bytes& payload,
    const p::Parameters& parameters,
    ps::SnapshotV1Error expected,
    std::string_view message) {
  const auto result = ps::decode_snapshot_v1(payload, parameters);
  pv::require(
      std::holds_alternative<ps::SnapshotV1Error>(result) &&
          std::get<ps::SnapshotV1Error>(result) == expected,
      message);
}

void write_u64(
    p::Bytes& bytes,
    std::size_t offset,
    std::uint64_t value) {
  for (int shift = 56; shift >= 0; shift -= 8) {
    bytes[offset++] = static_cast<std::uint8_t>(value >> shift);
  }
}

void resign(p::Bytes& payload) {
  const auto digest = p::hash(
      kDigestDomain,
      std::span<const std::uint8_t>(
          payload.data(), payload.size() - kDigestSize));
  std::copy(
      digest.begin(), digest.end(),
      payload.end() - static_cast<std::ptrdiff_t>(kDigestSize));
}

void verify_codec(const pv::Values& values) {
  const auto genesis = genesis_bytes(values);
  auto ledger = load_ledger(genesis);
  const auto encoded =
      take_encoded(ps::encode_snapshot_v1(ledger),
                   "genesis snapshot encoding failed");
  const auto repeated =
      take_encoded(ps::encode_snapshot_v1(ledger),
                   "repeated snapshot encoding failed");
  pv::require(encoded == repeated,
              "snapshot encoding is nondeterministic");
  pv::require(
      encoded.payload.size() ==
          150 + ledger.state().accounts.size() * kAccountSize,
      "snapshot encoded length mismatch");
  const auto frozen_digest = pv::hex_decode(
      "b51bd72c667bcaefd9367bb3db7eaff9"
      "d18b2cf9e36954e2f37033e7807edce5");
  pv::require(
      std::equal(
          encoded.digest.begin(), encoded.digest.end(),
          frozen_digest.begin(), frozen_digest.end()),
      "frozen genesis snapshot digest changed");

  const auto decoded = take_decoded(
      ps::decode_snapshot_v1(
          encoded.payload, ledger.state().parameters),
      "canonical snapshot decoding failed");
  pv::require(
      decoded.ledger.state() == ledger.state() &&
          decoded.state_root == encoded.state_root &&
          decoded.digest == encoded.digest,
      "snapshot round trip changed head");

  auto malformed = encoded.payload;
  malformed[0] ^= 1U;
  require_decode_error(
      malformed, ledger.state().parameters,
      ps::SnapshotV1Error::malformed,
      "bad snapshot magic accepted");

  malformed = encoded.payload;
  malformed[5] = 2;
  require_decode_error(
      malformed, ledger.state().parameters,
      ps::SnapshotV1Error::unsupported_version,
      "unknown snapshot version accepted");

  malformed = encoded.payload;
  write_u64(malformed, 78, UINT64_MAX);
  require_decode_error(
      malformed, ledger.state().parameters,
      ps::SnapshotV1Error::size_overflow,
      "overflowing snapshot count accepted");

  malformed = encoded.payload;
  malformed.push_back(0);
  require_decode_error(
      malformed, ledger.state().parameters,
      ps::SnapshotV1Error::malformed,
      "trailing snapshot byte accepted");

  malformed = encoded.payload;
  malformed.back() ^= 1U;
  require_decode_error(
      malformed, ledger.state().parameters,
      ps::SnapshotV1Error::digest_mismatch,
      "wrong snapshot digest accepted");

  malformed = encoded.payload;
  malformed[6] ^= 1U;
  resign(malformed);
  require_decode_error(
      malformed, ledger.state().parameters,
      ps::SnapshotV1Error::immutable_parameters_mismatch,
      "wrong snapshot chain accepted");

  malformed = encoded.payload;
  std::copy_n(
      malformed.begin() + static_cast<std::ptrdiff_t>(kPrefixSize),
      32,
      malformed.begin() +
          static_cast<std::ptrdiff_t>(kPrefixSize + kAccountSize));
  resign(malformed);
  require_decode_error(
      malformed, ledger.state().parameters,
      ps::SnapshotV1Error::invalid_state,
      "duplicate snapshot account accepted");

  malformed = encoded.payload;
  std::swap_ranges(
      malformed.begin() + static_cast<std::ptrdiff_t>(kPrefixSize),
      malformed.begin() +
          static_cast<std::ptrdiff_t>(kPrefixSize + kAccountSize),
      malformed.begin() +
          static_cast<std::ptrdiff_t>(kPrefixSize + kAccountSize));
  resign(malformed);
  require_decode_error(
      malformed, ledger.state().parameters,
      ps::SnapshotV1Error::invalid_state,
      "unsorted snapshot accounts accepted");

  malformed = encoded.payload;
  write_u64(malformed, kPrefixSize + 32, 0);
  resign(malformed);
  require_decode_error(
      malformed, ledger.state().parameters,
      ps::SnapshotV1Error::invalid_state,
      "nonconserving snapshot state accepted");

  malformed = encoded.payload;
  malformed[malformed.size() - 33] ^= 1U;
  resign(malformed);
  require_decode_error(
      malformed, ledger.state().parameters,
      ps::SnapshotV1Error::state_root_mismatch,
      "wrong snapshot state root accepted");

  auto wrong_parameters = ledger.state().parameters;
  ++wrong_parameters.fixed_fee;
  require_decode_error(
      encoded.payload, wrong_parameters,
      ps::SnapshotV1Error::immutable_parameters_mismatch,
      "caller parameter mismatch accepted");

  for (std::size_t size = 0; size < encoded.payload.size(); ++size) {
    const p::Bytes truncated(
        encoded.payload.begin(),
        encoded.payload.begin() + static_cast<std::ptrdiff_t>(size));
    pv::require(
        std::holds_alternative<ps::SnapshotV1Error>(
            ps::decode_snapshot_v1(
                truncated, ledger.state().parameters)),
        "truncated snapshot accepted");
  }
}

ps::SQLiteLedger take_sqlite_ledger(
    ps::SQLiteLedgerResult result,
    std::string_view message) {
  pv::require(std::holds_alternative<ps::SQLiteLedger>(result.result),
              message);
  return std::get<ps::SQLiteLedger>(std::move(result.result));
}

p::Bytes take_snapshot(
    ps::SQLiteSnapshotResult result,
    std::string_view message) {
  pv::require(std::holds_alternative<p::Bytes>(result), message);
  return std::get<p::Bytes>(std::move(result));
}

void raw_execute(
    const std::filesystem::path& path,
    const std::string& sql) {
  sqlite3* database = nullptr;
  pv::require(
      sqlite3_open_v2(
          path.c_str(), &database,
          SQLITE_OPEN_READWRITE | SQLITE_OPEN_PRIVATECACHE |
              SQLITE_OPEN_NOFOLLOW | SQLITE_OPEN_EXRESCODE,
          nullptr) == SQLITE_OK,
      "raw SQLite open failed");
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
      sqlite3_prepare_v2(
          database, sql, -1, &statement, nullptr) == SQLITE_OK,
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

void require_open_state_mismatch(
    const std::filesystem::path& path,
    const p::Bytes& genesis,
    std::string_view message) {
  auto result = ps::open_sqlite_ledger(path, genesis);
  pv::require(
      std::holds_alternative<ps::SQLiteLedgerError>(result.result) &&
          std::get<ps::SQLiteLedgerError>(result.result) ==
              ps::SQLiteLedgerError::state_mismatch,
      message);
}

void verify_persistence(
    const pv::Values& values,
    const std::filesystem::path& prefix) {
  DatabaseFiles files(prefix.string() + "-roundtrip.db");
  const auto genesis = genesis_bytes(values);
  const auto transactions = block_transactions(values);
  auto expected = load_ledger(genesis);

  {
    auto stored = take_sqlite_ledger(
        ps::create_sqlite_ledger(files.path(), genesis),
        "snapshot database create failed");
    const auto genesis_snapshot = take_snapshot(
        stored.create_snapshot(), "genesis snapshot persistence failed");
    const auto expected_genesis_snapshot = take_encoded(
        ps::encode_snapshot_v1(expected),
        "expected genesis snapshot failed");
    pv::require(
        genesis_snapshot == expected_genesis_snapshot.payload,
        "persisted genesis snapshot bytes changed");
    pv::require(
        take_snapshot(
            stored.create_snapshot(),
            "repeated genesis snapshot persistence failed") ==
            genesis_snapshot,
        "repeated snapshot persistence changed bytes");

    auto expected_block = expected.apply_block(1, transactions);
    pv::require(
        std::holds_alternative<p::BlockCommit>(expected_block),
        "expected snapshot block rejected");
    const auto actual_block = stored.apply_block(1, transactions);
    pv::require(
        std::holds_alternative<p::BlockCommit>(actual_block),
        "stored snapshot block rejected");
  }

  {
    auto reopened = take_sqlite_ledger(
        ps::open_sqlite_ledger(files.path(), genesis),
        "older snapshot plus full replay rejected");
    pv::require(reopened.read_head() == ledger_head(expected),
                "older snapshot changed replay head");
    const std::vector<p::Bytes> empty;
    auto expected_block = expected.apply_block(2, empty);
    pv::require(
        std::holds_alternative<p::BlockCommit>(expected_block),
        "expected empty block rejected");
    const auto actual_block = reopened.apply_block(2, empty);
    pv::require(
        std::holds_alternative<p::BlockCommit>(actual_block),
        "stored empty block rejected");
    const auto payload = take_snapshot(
        reopened.create_snapshot(), "head snapshot replacement failed");
    const auto expected_snapshot = take_encoded(
        ps::encode_snapshot_v1(expected),
        "expected head snapshot failed");
    pv::require(payload == expected_snapshot.payload,
                "persisted head snapshot bytes changed");
  }

  pv::require(
      raw_scalar_text(
          files.path(), "SELECT count(*) FROM snapshots") == "1",
      "snapshot replacement retained stale rows");
  pv::require(
      raw_scalar_text(
          files.path(), "SELECT hex(height) FROM snapshots") ==
          "0000000000000002",
      "snapshot height projection mismatch");

  auto reopened = take_sqlite_ledger(
      ps::open_sqlite_ledger(files.path(), genesis),
      "head snapshot restore rejected");
  pv::require(reopened.read_head() == ledger_head(expected),
              "head snapshot restore changed state");
}

void create_snapshot_database(
    const std::filesystem::path& path,
    const p::Bytes& genesis) {
  auto ledger = take_sqlite_ledger(
      ps::create_sqlite_ledger(path, genesis),
      "corruption snapshot create failed");
  (void)take_snapshot(
      ledger.create_snapshot(), "corruption snapshot persist failed");
}

void verify_corruption_rejection(
    const pv::Values& values,
    const std::filesystem::path& prefix) {
  const auto genesis = genesis_bytes(values);
  const auto require_corruption =
      [&](std::string_view suffix,
          const std::string& sql,
          std::string_view message) {
        DatabaseFiles files(prefix.string() + std::string(suffix));
        create_snapshot_database(files.path(), genesis);
        raw_execute(files.path(), sql);
        require_open_state_mismatch(files.path(), genesis, message);
      };

  require_corruption(
      "-payload.db",
      "UPDATE snapshots SET payload=zeroblob(length(payload));",
      "corrupt snapshot payload accepted");
  require_corruption(
      "-root.db",
      "UPDATE snapshots SET expected_state_root=zeroblob(32);",
      "snapshot root projection corruption accepted");
  require_corruption(
      "-digest.db",
      "UPDATE snapshots SET payload_digest=zeroblob(32);",
      "snapshot digest projection corruption accepted");
  require_corruption(
      "-height.db",
      "UPDATE snapshots SET height=X'0000000000000001';",
      "snapshot height projection corruption accepted");
  require_corruption(
      "-duplicate.db",
      "INSERT INTO snapshots "
      "SELECT X'0000000000000001', payload, expected_state_root, "
      "payload_digest FROM snapshots;",
      "multiple retained snapshots accepted");
}

}  // namespace

int main(int argc, char** argv) {
  try {
    pv::require(
        argc == 3,
        "usage: storage_snapshot_v1_tests VECTOR_FILE PATH_PREFIX");
    pv::require(sodium_init() >= 0, "libsodium initialization");
    const auto values = pv::load_values(argv[1]);
    const std::filesystem::path prefix(argv[2]);
    verify_codec(values);
    verify_persistence(values, prefix);
    verify_corruption_rejection(values, prefix);
    std::cout << "Storage snapshot v1 tests: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "Storage snapshot v1 tests: failed: "
              << error.what() << '\n';
    return 1;
  }
}
