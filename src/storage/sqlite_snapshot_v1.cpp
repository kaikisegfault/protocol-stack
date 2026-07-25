#include "sqlite_snapshot_v1.hpp"

#include <sqlite3.h>

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include <variant>

namespace protocol::storage::internal {
namespace {

namespace pv1 = protocol::v1;

[[noreturn]] void fail(SQLiteLedgerError error) {
  throw Failure{error};
}

int checked_step(Statement& statement) {
  const auto result = statement.step();
  if (result != SQLITE_ROW && result != SQLITE_DONE) {
    fail(SQLiteLedgerError::storage_failure);
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

std::uint64_t decode_u64(Statement& statement, int index) {
  if (statement.column_type(index) != SQLITE_BLOB) {
    fail(SQLiteLedgerError::state_mismatch);
  }
  const auto bytes = statement.column_blob(index);
  if (bytes.size() != 8) {
    fail(SQLiteLedgerError::state_mismatch);
  }
  std::uint64_t value = 0;
  for (const auto byte : bytes) value = (value << 8U) | byte;
  return value;
}

pv1::Bytes decode_blob(Statement& statement, int index) {
  if (statement.column_type(index) != SQLITE_BLOB) {
    fail(SQLiteLedgerError::state_mismatch);
  }
  const auto bytes = statement.column_blob(index);
  return pv1::Bytes(bytes.begin(), bytes.end());
}

template <typename Fixed>
Fixed decode_fixed(Statement& statement, int index) {
  const auto bytes = decode_blob(statement, index);
  Fixed value{};
  if (bytes.size() != value.size()) {
    fail(SQLiteLedgerError::state_mismatch);
  }
  std::copy(bytes.begin(), bytes.end(), value.begin());
  return value;
}

template <typename Tagged>
std::span<const std::uint8_t> tagged_bytes(
    const Tagged& value) noexcept {
  return {value.data(), value.size()};
}

void require_snapshot_matches(
    const DecodedSnapshotV1& decoded,
    const pv1::Ledger& ledger,
    const EncodedSnapshotV1& encoded) {
  if (decoded.ledger.state() != ledger.state() ||
      decoded.state_root != encoded.state_root ||
      decoded.digest != encoded.digest) {
    fail(SQLiteLedgerError::storage_failure);
  }
}

void require_durable_head(
    Connection& connection,
    const pv1::Ledger& ledger,
    const pv1::StateRoot& state_root) {
  Statement head = connection.prepare(
      "SELECT current_height, current_state_root "
      "FROM ledger_meta WHERE singleton=1");
  if (checked_step(head) != SQLITE_ROW || head.column_count() != 2 ||
      decode_u64(head, 0) != ledger.state().height ||
      decode_fixed<pv1::StateRoot>(head, 1) != state_root ||
      checked_step(head) != SQLITE_DONE) {
    fail(SQLiteLedgerError::state_mismatch);
  }
}

}  // namespace

std::optional<DecodedSnapshotV1> load_snapshot_v1(
    Connection& connection,
    const pv1::Parameters& expected_parameters) {
  Statement rows = connection.prepare(
      "SELECT height, payload, expected_state_root, payload_digest "
      "FROM snapshots ORDER BY height");
  if (checked_step(rows) == SQLITE_DONE) return std::nullopt;
  if (rows.column_count() != 4) {
    fail(SQLiteLedgerError::state_mismatch);
  }

  const auto height = decode_u64(rows, 0);
  const auto payload = decode_blob(rows, 1);
  const auto expected_root =
      decode_fixed<pv1::StateRoot>(rows, 2);
  const auto expected_digest = decode_fixed<pv1::Hash>(rows, 3);
  auto decoded = decode_snapshot_v1(payload, expected_parameters);
  if (!std::holds_alternative<DecodedSnapshotV1>(decoded)) {
    fail(SQLiteLedgerError::state_mismatch);
  }
  auto snapshot =
      std::get<DecodedSnapshotV1>(std::move(decoded));
  if (snapshot.ledger.state().height != height ||
      snapshot.state_root != expected_root ||
      snapshot.digest != expected_digest ||
      checked_step(rows) != SQLITE_DONE) {
    fail(SQLiteLedgerError::state_mismatch);
  }
  return snapshot;
}

void persist_snapshot_v1(
    Connection& connection,
    const pv1::Ledger& ledger,
    const EncodedSnapshotV1& snapshot) {
  if (connection.autocommit()) {
    fail(SQLiteLedgerError::storage_failure);
  }
  auto decoded =
      decode_snapshot_v1(snapshot.payload, ledger.state().parameters);
  if (!std::holds_alternative<DecodedSnapshotV1>(decoded)) {
    fail(SQLiteLedgerError::storage_failure);
  }
  require_snapshot_matches(
      std::get<DecodedSnapshotV1>(decoded), ledger, snapshot);
  require_durable_head(connection, ledger, snapshot.state_root);

  connection.execute("DELETE FROM snapshots");
  if (sqlite3_changes(connection.get()) > 1) {
    fail(SQLiteLedgerError::state_mismatch);
  }

  Statement insert = connection.prepare(
      "INSERT INTO snapshots("
      "height, payload, expected_state_root, payload_digest"
      ") VALUES(?, ?, ?, ?)");
  const auto height = encode_u64(ledger.state().height);
  insert.bind_blob(1, height);
  insert.bind_blob(2, snapshot.payload);
  insert.bind_blob(3, tagged_bytes(snapshot.state_root));
  insert.bind_blob(4, snapshot.digest);
  if (checked_step(insert) != SQLITE_DONE ||
      sqlite3_changes(connection.get()) != 1) {
    fail(SQLiteLedgerError::storage_failure);
  }

  auto stored =
      load_snapshot_v1(connection, ledger.state().parameters);
  if (!stored ||
      stored->ledger.state() != ledger.state() ||
      stored->state_root != snapshot.state_root ||
      stored->digest != snapshot.digest) {
    fail(SQLiteLedgerError::storage_failure);
  }
}

}  // namespace protocol::storage::internal
