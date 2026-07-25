#include "sqlite_archive_v1.hpp"

#include <sqlite3.h>

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <span>

namespace protocol::storage::internal {
namespace {

namespace pv1 = protocol::v1;

constexpr std::uint32_t kMaximumBlockInputs = 65'535;

[[noreturn]] void fail() {
  throw Failure{SQLiteLedgerError::state_mismatch};
}

int checked_step(Statement& statement) {
  const auto result = statement.step();
  if (result != SQLITE_ROW && result != SQLITE_DONE) {
    throw Failure{SQLiteLedgerError::storage_failure};
  }
  return result;
}

std::array<std::uint8_t, 8> encode_u64(std::uint64_t value) {
  std::array<std::uint8_t, 8> encoded{};
  for (std::size_t index = 0; index < encoded.size(); ++index) {
    const auto shift = static_cast<unsigned>(
        (encoded.size() - index - 1) * 8);
    encoded[index] = static_cast<std::uint8_t>(value >> shift);
  }
  return encoded;
}

std::uint64_t decode_unsigned(
    Statement& statement,
    int column,
    std::size_t width) {
  if (statement.column_type(column) != SQLITE_BLOB) fail();
  const auto bytes = statement.column_blob(column);
  if (bytes.size() != width) fail();
  std::uint64_t value = 0;
  for (const auto byte : bytes) value = (value << 8U) | byte;
  return value;
}

pv1::Bytes decode_bytes(
    Statement& statement,
    int column,
    std::size_t width) {
  if (statement.column_type(column) != SQLITE_BLOB) fail();
  const auto bytes = statement.column_blob(column);
  if (bytes.size() != width) fail();
  return pv1::Bytes(bytes.begin(), bytes.end());
}

template <typename Tagged>
Tagged decode_tagged(Statement& statement, int column) {
  const auto bytes =
      decode_bytes(statement, column, pv1::Hash{}.size());
  pv1::Hash value{};
  std::copy(bytes.begin(), bytes.end(), value.begin());
  return Tagged{value};
}

std::vector<ArchiveTransactionV1> load_transactions(
    Connection& connection,
    std::uint64_t height,
    std::uint32_t admitted_count) {
  Statement rows = connection.prepare(
      "SELECT ordinal, transaction_bytes, transaction_id, "
      "receipt_bytes FROM admitted_transactions "
      "WHERE height=? ORDER BY ordinal");
  const auto encoded_height = encode_u64(height);
  rows.bind_blob(1, encoded_height);
  std::vector<ArchiveTransactionV1> transactions;
  transactions.reserve(admitted_count);
  while (checked_step(rows) == SQLITE_ROW) {
    if (rows.column_count() != 4 ||
        transactions.size() >= admitted_count ||
        decode_unsigned(rows, 0, 4) != transactions.size()) {
      fail();
    }
    transactions.push_back(ArchiveTransactionV1{
        decode_bytes(rows, 1, 200),
        decode_tagged<pv1::TransactionId>(rows, 2),
        decode_bytes(rows, 3, 47),
    });
  }
  if (transactions.size() != admitted_count) fail();
  return transactions;
}

}  // namespace

ArchiveV1Data load_archive_v1(
    Connection& connection,
    std::span<const std::uint8_t> canonical_genesis,
    const EncodedSnapshotV1& head_snapshot) {
  ArchiveV1Data archive{
      pv1::Bytes(canonical_genesis.begin(), canonical_genesis.end()),
      {},
      head_snapshot.payload,
  };
  Statement rows = connection.prepare(
      "SELECT height, admitted_count, header, block_id "
      "FROM blocks ORDER BY height");
  while (checked_step(rows) == SQLITE_ROW) {
    if (rows.column_count() != 4 ||
        archive.blocks.size() ==
            std::numeric_limits<std::uint64_t>::max()) {
      fail();
    }
    const auto height = decode_unsigned(rows, 0, 8);
    if (height != archive.blocks.size() + 1) fail();
    const auto count_value = decode_unsigned(rows, 1, 4);
    if (count_value > kMaximumBlockInputs) fail();
    const auto admitted_count =
        static_cast<std::uint32_t>(count_value);
    archive.blocks.push_back(ArchiveBlockV1{
        decode_bytes(rows, 2, 146),
        decode_tagged<pv1::BlockId>(rows, 3),
        load_transactions(connection, height, admitted_count),
    });
  }
  return archive;
}

}  // namespace protocol::storage::internal
