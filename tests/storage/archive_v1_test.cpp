#include "protocol/storage/archive_v1.hpp"
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
#include <span>
#include <string>
#include <string_view>
#include <utility>
#include <variant>
#include <vector>

namespace pv = protocol_vectors;
namespace ps = protocol::storage;
namespace p = protocol::v1;

namespace {

constexpr std::size_t kDigestSize = 32;
constexpr std::size_t kBlockFixedSize = 182;
constexpr std::size_t kTransactionRecordSize = 279;
constexpr std::size_t kFrozenArchiveSize = 3'745;
constexpr char kDigestDomain[] =
    "protocol-stack:storage:archive-v1";
constexpr char kFrozenArchiveDigest[] =
    "b9196beb35afb29e64ca4a09666a27f2701b9b16207c216f401aab8c49adba7e";

struct ArchiveFixture {
  ps::ArchiveV1Data data;
  p::Ledger ledger;
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

p::Ledger load_ledger(const p::Bytes& genesis) {
  auto loaded = p::load_genesis(genesis);
  pv::require(std::holds_alternative<p::Ledger>(loaded.result),
              "fixture genesis rejected");
  return std::get<p::Ledger>(std::move(loaded.result));
}

ps::EncodedSnapshotV1 encode_snapshot(const p::Ledger& ledger) {
  auto encoded = ps::encode_snapshot_v1(ledger);
  pv::require(
      std::holds_alternative<ps::EncodedSnapshotV1>(encoded),
      "fixture snapshot encoding failed");
  return std::get<ps::EncodedSnapshotV1>(std::move(encoded));
}

ArchiveFixture genesis_archive(const p::Bytes& genesis) {
  auto ledger = load_ledger(genesis);
  const auto snapshot = encode_snapshot(ledger);
  return ArchiveFixture{
      ps::ArchiveV1Data{genesis, {}, snapshot.payload},
      std::move(ledger),
  };
}

void append_block(
    ArchiveFixture& fixture,
    std::span<const p::Bytes> raw_transactions) {
  const auto height =
      static_cast<std::uint64_t>(fixture.data.blocks.size()) + 1;
  auto applied =
      fixture.ledger.apply_block(height, raw_transactions);
  pv::require(std::holds_alternative<p::BlockCommit>(applied),
              "fixture block rejected");
  const auto commit =
      std::get<p::BlockCommit>(std::move(applied));

  std::vector<ps::ArchiveTransactionV1> admitted;
  admitted.reserve(commit.transaction_ids.size());
  std::size_t ordinal = 0;
  for (std::size_t index = 0;
       index < raw_transactions.size(); ++index) {
    if (commit.admissions[index]) continue;
    admitted.push_back(ps::ArchiveTransactionV1{
        raw_transactions[index],
        commit.transaction_ids[ordinal],
        commit.encoded_receipts[ordinal],
    });
    ++ordinal;
  }
  fixture.data.blocks.push_back(ps::ArchiveBlockV1{
      commit.header, commit.block_id, std::move(admitted)});
  fixture.data.head_snapshot =
      encode_snapshot(fixture.ledger).payload;
}

ArchiveFixture block_archive(const pv::Values& values) {
  auto fixture = genesis_archive(genesis_bytes(values));
  const auto raw_transactions = block_transactions(values);
  append_block(fixture, raw_transactions);
  return fixture;
}

ps::EncodedArchiveV1 take_encoded(
    ps::ArchiveV1EncodeResult result,
    std::string_view message) {
  pv::require(
      std::holds_alternative<ps::EncodedArchiveV1>(result), message);
  return std::get<ps::EncodedArchiveV1>(std::move(result));
}

ps::DecodedArchiveV1 take_decoded(
    ps::ArchiveV1DecodeResult result,
    std::string_view message) {
  pv::require(
      std::holds_alternative<ps::DecodedArchiveV1>(result), message);
  return std::get<ps::DecodedArchiveV1>(std::move(result));
}

void require_decode_error(
    const p::Bytes& payload,
    ps::ArchiveV1Error expected,
    std::string_view message) {
  const auto result = ps::decode_archive_v1(payload);
  pv::require(
      std::holds_alternative<ps::ArchiveV1Error>(result) &&
          std::get<ps::ArchiveV1Error>(result) == expected,
      message);
}

void require_encode_error(
    const ps::ArchiveV1Data& data,
    ps::ArchiveV1Error expected,
    std::string_view message) {
  const auto result = ps::encode_archive_v1(data);
  pv::require(
      std::holds_alternative<ps::ArchiveV1Error>(result) &&
          std::get<ps::ArchiveV1Error>(result) == expected,
      message);
}

void write_u32(
    p::Bytes& bytes,
    std::size_t offset,
    std::uint32_t value) {
  for (int shift = 24; shift >= 0; shift -= 8) {
    bytes[offset++] = static_cast<std::uint8_t>(value >> shift);
  }
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
  auto fixture = block_archive(values);
  const auto encoded = take_encoded(
      ps::encode_archive_v1(fixture.data),
      "canonical archive encoding failed");
  const auto repeated = take_encoded(
      ps::encode_archive_v1(fixture.data),
      "repeated archive encoding failed");
  pv::require(encoded == repeated,
              "archive encoding is nondeterministic");
  pv::require(
      encoded.payload.size() == kFrozenArchiveSize &&
          encoded.payload.size() ==
          58 + fixture.data.canonical_genesis.size() +
              kBlockFixedSize +
              fixture.data.blocks[0].transactions.size() *
                  kTransactionRecordSize +
              fixture.data.head_snapshot.size(),
      "archive encoded length mismatch");
  const auto expected_digest = pv::hex_decode(kFrozenArchiveDigest);
  pv::require(
      std::equal(
          expected_digest.begin(), expected_digest.end(),
          encoded.digest.begin(), encoded.digest.end()),
      "archive frozen digest changed");

  const auto decoded = take_decoded(
      ps::decode_archive_v1(encoded.payload),
      "canonical archive decoding failed");
  const auto expected_root = fixture.ledger.current_state_root();
  pv::require(
      decoded.data == fixture.data &&
          decoded.ledger.state() == fixture.ledger.state() &&
          std::holds_alternative<p::StateRoot>(expected_root) &&
          decoded.state_root == std::get<p::StateRoot>(expected_root) &&
          decoded.digest == encoded.digest,
      "archive round trip changed history or head");

  auto genesis_only = genesis_archive(genesis_bytes(values));
  const auto empty_encoded = take_encoded(
      ps::encode_archive_v1(genesis_only.data),
      "zero-block archive encoding failed");
  const auto empty_decoded = take_decoded(
      ps::decode_archive_v1(empty_encoded.payload),
      "zero-block archive decoding failed");
  pv::require(
      empty_decoded.data == genesis_only.data &&
          empty_decoded.ledger.state() == genesis_only.ledger.state(),
      "zero-block archive round trip changed head");

  auto empty_block = genesis_archive(genesis_bytes(values));
  append_block(empty_block, std::span<const p::Bytes>{});
  const auto empty_block_encoded = take_encoded(
      ps::encode_archive_v1(empty_block.data),
      "empty-block archive encoding failed");
  const auto empty_block_decoded = take_decoded(
      ps::decode_archive_v1(empty_block_encoded.payload),
      "empty-block archive decoding failed");
  pv::require(
      empty_block_decoded.data == empty_block.data &&
          empty_block_decoded.ledger.state() ==
              empty_block.ledger.state(),
      "empty-block archive round trip changed head");

  auto invalid = fixture.data;
  invalid.canonical_genesis[0] ^= 1U;
  require_encode_error(
      invalid, ps::ArchiveV1Error::invalid_genesis,
      "invalid archive genesis encoded");
  invalid = fixture.data;
  invalid.blocks[0].header[0] ^= 1U;
  require_encode_error(
      invalid, ps::ArchiveV1Error::invalid_history,
      "invalid archive header encoded");
  invalid = fixture.data;
  invalid.blocks[0].block_id.begin()[0] ^= 1U;
  require_encode_error(
      invalid, ps::ArchiveV1Error::invalid_history,
      "invalid archive block identifier encoded");
  invalid = fixture.data;
  invalid.blocks[0].transactions[0].transaction_id.begin()[0] ^= 1U;
  require_encode_error(
      invalid, ps::ArchiveV1Error::invalid_history,
      "invalid archive transaction projection encoded");
  invalid = fixture.data;
  invalid.blocks[0].transactions[0].receipt[0] ^= 1U;
  require_encode_error(
      invalid, ps::ArchiveV1Error::invalid_history,
      "invalid archive receipt encoded");
  invalid = fixture.data;
  invalid.head_snapshot[0] ^= 1U;
  require_encode_error(
      invalid, ps::ArchiveV1Error::snapshot_mismatch,
      "invalid archive snapshot encoded");
  invalid = fixture.data;
  invalid.head_snapshot =
      genesis_archive(genesis_bytes(values)).data.head_snapshot;
  require_encode_error(
      invalid, ps::ArchiveV1Error::snapshot_mismatch,
      "valid archive snapshot at wrong height encoded");

  auto malformed = encoded.payload;
  malformed[0] ^= 1U;
  require_decode_error(
      malformed, ps::ArchiveV1Error::malformed,
      "bad archive magic accepted");
  malformed = encoded.payload;
  malformed[5] = 2;
  require_decode_error(
      malformed, ps::ArchiveV1Error::unsupported_version,
      "unknown archive version accepted");
  malformed = encoded.payload;
  write_u32(malformed, 6, UINT32_MAX);
  require_decode_error(
      malformed, ps::ArchiveV1Error::size_overflow,
      "oversized archive genesis accepted");

  const auto block_count_offset =
      10 + fixture.data.canonical_genesis.size();
  const auto block_offset = block_count_offset + 8;
  malformed = encoded.payload;
  write_u64(malformed, block_count_offset, UINT64_MAX);
  resign(malformed);
  require_decode_error(
      malformed, ps::ArchiveV1Error::malformed,
      "unbounded archive block count accepted");
  malformed = encoded.payload;
  write_u32(malformed, block_offset + 178, 65'536);
  resign(malformed);
  require_decode_error(
      malformed, ps::ArchiveV1Error::size_overflow,
      "oversized archive admitted count accepted");

  const auto snapshot_length_offset =
      block_offset + kBlockFixedSize +
      fixture.data.blocks[0].transactions.size() *
          kTransactionRecordSize;
  malformed = encoded.payload;
  write_u64(malformed, snapshot_length_offset, UINT64_MAX);
  resign(malformed);
  require_decode_error(
      malformed, ps::ArchiveV1Error::size_overflow,
      "overflowing archive snapshot length accepted");
  malformed = encoded.payload;
  malformed[block_offset + kBlockFixedSize + 200] ^= 1U;
  resign(malformed);
  require_decode_error(
      malformed, ps::ArchiveV1Error::invalid_history,
      "archive transaction projection corruption accepted");
  malformed = encoded.payload;
  malformed[snapshot_length_offset + 8] ^= 1U;
  resign(malformed);
  require_decode_error(
      malformed, ps::ArchiveV1Error::snapshot_mismatch,
      "archive snapshot corruption accepted");
  malformed = encoded.payload;
  malformed.back() ^= 1U;
  require_decode_error(
      malformed, ps::ArchiveV1Error::digest_mismatch,
      "wrong archive digest accepted");
  malformed = encoded.payload;
  malformed.push_back(0);
  require_decode_error(
      malformed, ps::ArchiveV1Error::malformed,
      "trailing archive byte accepted");

  for (std::size_t size = 0; size < encoded.payload.size(); ++size) {
    const p::Bytes truncated(
        encoded.payload.begin(),
        encoded.payload.begin() + static_cast<std::ptrdiff_t>(size));
    pv::require(
        std::holds_alternative<ps::ArchiveV1Error>(
            ps::decode_archive_v1(truncated)),
        "truncated archive accepted");
  }
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

void require_ledger_error(
    ps::SQLiteLedgerResult result,
    ps::SQLiteLedgerError expected,
    std::string_view message) {
  pv::require(
      std::holds_alternative<ps::SQLiteLedgerError>(result.result) &&
          std::get<ps::SQLiteLedgerError>(result.result) == expected,
      message);
}

p::Bytes take_export(
    ps::SQLiteArchiveResult result,
    std::string_view message) {
  pv::require(std::holds_alternative<p::Bytes>(result), message);
  return std::get<p::Bytes>(std::move(result));
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

void verify_export(
    const pv::Values& values,
    const std::filesystem::path& prefix) {
  DatabaseFiles files(prefix.string() + "-export.db");
  const auto genesis = genesis_bytes(values);
  const auto transactions = block_transactions(values);
  auto expected = block_archive(values);
  p::Bytes exported;

  {
    auto stored = take_ledger(
        ps::create_sqlite_ledger(files.path(), genesis),
        "archive database create failed");
    const auto genesis_export = take_export(
        stored.export_archive(), "genesis archive export failed");
    const auto decoded_genesis = take_decoded(
        ps::decode_archive_v1(genesis_export),
        "genesis export decoding failed");
    pv::require(decoded_genesis.data.blocks.empty(),
                "genesis export retained blocks");
    pv::require(
        std::holds_alternative<p::Bytes>(
            stored.create_snapshot()),
        "retained genesis snapshot failed");
    pv::require(
        std::holds_alternative<p::BlockCommit>(
            stored.apply_block(1, transactions)),
        "archive export block rejected");

    exported = take_export(
        stored.export_archive(), "head archive export failed");
    const auto expected_encoding = take_encoded(
        ps::encode_archive_v1(expected.data),
        "expected archive encoding failed");
    pv::require(exported == expected_encoding.payload,
                "SQLite archive export bytes changed");

    const std::vector<p::Bytes> empty_block;
    pv::require(
        std::holds_alternative<p::BlockCommit>(
            stored.apply_block(2, empty_block)),
        "empty archive export block rejected");
    append_block(expected, empty_block);
    exported = take_export(
        stored.export_archive(),
        "multi-block archive export failed");
    const auto multi_block_encoding = take_encoded(
        ps::encode_archive_v1(expected.data),
        "expected multi-block archive encoding failed");
    pv::require(exported == multi_block_encoding.payload,
                "multi-block SQLite archive export bytes changed");
    pv::require(
        take_export(
            stored.export_archive(),
            "repeated archive export failed") == exported,
        "repeated archive export changed bytes");
  }

  pv::require(
      raw_scalar_text(
          files.path(), "SELECT hex(height) FROM snapshots") ==
          "0000000000000000",
      "archive export changed retained snapshot");
  auto reopened = take_ledger(
      ps::open_sqlite_ledger(files.path(), genesis),
      "archive database reopen failed");
  pv::require(
      take_export(
          reopened.export_archive(),
          "reopened archive export failed") == exported,
      "reopened archive export changed bytes");
}

void verify_import(
    const pv::Values& values,
    const std::filesystem::path& prefix) {
  const auto genesis = genesis_bytes(values);
  const auto transactions = block_transactions(values);
  auto expected = block_archive(values);
  const std::vector<p::Bytes> empty_block;
  append_block(expected, empty_block);
  append_block(expected, transactions);
  const auto encoded = take_encoded(
      ps::encode_archive_v1(expected.data),
      "import fixture encoding failed");

  DatabaseFiles imported_files(prefix.string() + "-import.db");
  {
    auto imported = take_ledger(
        ps::import_sqlite_archive(
            imported_files.path(), encoded.payload),
        "archive import failed");
    const auto head =
        take_head(imported.read_head(), "imported head read failed");
    const auto expected_root = expected.ledger.current_state_root();
    pv::require(
        head.state == expected.ledger.state() &&
            std::holds_alternative<p::StateRoot>(expected_root) &&
            head.state_root == std::get<p::StateRoot>(expected_root),
        "imported archive head changed");
    pv::require(
        take_export(
            imported.export_archive(),
            "imported archive export failed") == encoded.payload,
        "imported archive export bytes changed");
  }
  pv::require(
      raw_scalar_text(
          imported_files.path(),
          "SELECT hex(height) FROM snapshots") ==
          "0000000000000003",
      "import did not retain the exact head snapshot");
  auto reopened = take_ledger(
      ps::open_sqlite_ledger(imported_files.path(), genesis),
      "imported archive reopen failed");
  pv::require(
      take_export(
          reopened.export_archive(),
          "reopened import export failed") == encoded.payload,
      "reopened import export bytes changed");

  auto genesis_fixture = genesis_archive(genesis);
  const auto genesis_encoded = take_encoded(
      ps::encode_archive_v1(genesis_fixture.data),
      "genesis import fixture encoding failed");
  DatabaseFiles genesis_files(prefix.string() + "-genesis-import.db");
  auto genesis_import = take_ledger(
      ps::import_sqlite_archive(
          genesis_files.path(), genesis_encoded.payload),
      "genesis archive import failed");
  pv::require(
      take_head(
          genesis_import.read_head(),
          "genesis import head read failed").state ==
          genesis_fixture.ledger.state() &&
          take_export(
              genesis_import.export_archive(),
              "genesis import export failed") ==
              genesis_encoded.payload,
      "genesis archive import changed the height-zero ledger");

  auto invalid = encoded.payload;
  invalid.back() ^= 1U;
  DatabaseFiles invalid_files(prefix.string() + "-invalid-import.db");
  require_ledger_error(
      ps::import_sqlite_archive(invalid_files.path(), invalid),
      ps::SQLiteLedgerError::invalid_archive,
      "invalid archive did not return invalid_archive");
  pv::require(
      !std::filesystem::exists(invalid_files.path()),
      "invalid archive touched the target path");

  auto semantic_corruption = encoded.payload;
  const auto first_block_offset = 18 + genesis.size();
  semantic_corruption[
      first_block_offset + kBlockFixedSize + 200] ^= 1U;
  resign(semantic_corruption);
  DatabaseFiles semantic_files(
      prefix.string() + "-semantic-import.db");
  require_ledger_error(
      ps::import_sqlite_archive(
          semantic_files.path(), semantic_corruption),
      ps::SQLiteLedgerError::invalid_archive,
      "semantically invalid archive did not fail import");
  pv::require(
      !std::filesystem::exists(semantic_files.path()),
      "semantic archive failure touched the target path");

  DatabaseFiles existing_files(prefix.string() + "-existing-import.db");
  p::Bytes existing_export;
  {
    auto existing = take_ledger(
        ps::create_sqlite_ledger(existing_files.path(), genesis),
        "existing import target create failed");
    existing_export = take_export(
        existing.export_archive(),
        "existing import target export failed");
  }
  require_ledger_error(
      ps::import_sqlite_archive(
          existing_files.path(), encoded.payload),
      ps::SQLiteLedgerError::path_already_exists,
      "valid archive overwrote an existing target");
  require_ledger_error(
      ps::import_sqlite_archive(existing_files.path(), invalid),
      ps::SQLiteLedgerError::invalid_archive,
      "target path handling preceded archive validation");
  auto existing = take_ledger(
      ps::open_sqlite_ledger(existing_files.path(), genesis),
      "existing import target reopen failed");
  pv::require(
      take_export(
          existing.export_archive(),
          "existing import target re-export failed") ==
          existing_export,
      "failed import changed an existing target");
}

}  // namespace

int main(int argc, char** argv) {
  try {
    pv::require(
        argc == 3,
        "usage: storage_archive_v1_tests VECTOR_FILE PATH_PREFIX");
    pv::require(sodium_init() >= 0, "libsodium initialization");
    const auto values = pv::load_values(argv[1]);
    const std::filesystem::path prefix(argv[2]);
    verify_codec(values);
    verify_export(values, prefix);
    verify_import(values, prefix);
    std::cout << "Storage archive v1 tests: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "Storage archive v1 tests: failed: "
              << error.what() << '\n';
    return 1;
  }
}
