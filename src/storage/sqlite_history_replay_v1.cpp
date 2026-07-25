#include "sqlite_history_v1.hpp"
#include "sqlite_snapshot_v1.hpp"

#include <sqlite3.h>

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <span>
#include <utility>
#include <variant>
#include <vector>

namespace protocol::storage::internal {
namespace {

namespace pv1 = protocol::v1;

constexpr std::uint32_t kMaximumBlockInputs = 65'535;

struct StoredJournal {
  std::vector<pv1::Bytes> transactions;
  std::vector<pv1::TransactionId> transaction_ids;
  std::vector<pv1::Bytes> receipts;
};

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

std::uint64_t decode_unsigned(
    const Statement& statement,
    int index,
    std::size_t width) {
  if (statement.column_type(index) != SQLITE_BLOB) {
    fail(SQLiteLedgerError::state_mismatch);
  }
  const auto bytes = statement.column_blob(index);
  if (bytes.size() != width) {
    fail(SQLiteLedgerError::state_mismatch);
  }
  std::uint64_t value = 0;
  for (const auto byte : bytes) value = (value << 8U) | byte;
  return value;
}

pv1::Bytes decode_bytes(
    const Statement& statement,
    int index,
    std::size_t width) {
  if (statement.column_type(index) != SQLITE_BLOB) {
    fail(SQLiteLedgerError::state_mismatch);
  }
  const auto bytes = statement.column_blob(index);
  if (bytes.size() != width) {
    fail(SQLiteLedgerError::state_mismatch);
  }
  return pv1::Bytes(bytes.begin(), bytes.end());
}

template <typename Tagged>
Tagged decode_tagged_hash(
    const Statement& statement,
    int index) {
  const auto bytes = decode_bytes(statement, index, pv1::Hash{}.size());
  pv1::Hash value{};
  std::copy(bytes.begin(), bytes.end(), value.begin());
  return Tagged{value};
}

StoredJournal load_journal(
    Connection& connection,
    std::uint64_t height,
    std::uint32_t admitted_count) {
  Statement rows = connection.prepare(
      "SELECT ordinal, transaction_bytes, transaction_id, receipt_bytes "
      "FROM admitted_transactions WHERE height=? ORDER BY ordinal");
  const auto encoded_height = encode_u64(height);
  rows.bind_blob(1, encoded_height);

  StoredJournal stored;
  stored.transactions.reserve(admitted_count);
  stored.transaction_ids.reserve(admitted_count);
  stored.receipts.reserve(admitted_count);
  while (checked_step(rows) == SQLITE_ROW) {
    if (rows.column_count() != 4 ||
        stored.transactions.size() >= admitted_count) {
      fail(SQLiteLedgerError::state_mismatch);
    }
    const auto ordinal = decode_unsigned(rows, 0, 4);
    if (ordinal != stored.transactions.size()) {
      fail(SQLiteLedgerError::state_mismatch);
    }
    stored.transactions.push_back(decode_bytes(rows, 1, 200));
    stored.transaction_ids.push_back(
        decode_tagged_hash<pv1::TransactionId>(rows, 2));
    stored.receipts.push_back(decode_bytes(rows, 3, 47));
  }
  if (stored.transactions.size() != admitted_count) {
    fail(SQLiteLedgerError::state_mismatch);
  }
  return stored;
}

bool all_admitted(const pv1::BlockCommit& commit) {
  return std::all_of(
      commit.admissions.begin(), commit.admissions.end(),
      [](const auto& admission) { return !admission.has_value(); });
}

void require_replay_match(
    const pv1::BlockCommit& replayed,
    const StoredJournal& stored,
    const pv1::StateRoot& previous_root,
    const pv1::TransactionRoot& transaction_root,
    const pv1::StateRoot& resulting_root,
    const pv1::Bytes& header,
    const pv1::BlockId& block_id) {
  if (replayed.admissions.size() != stored.transactions.size() ||
      !all_admitted(replayed) ||
      replayed.transaction_ids != stored.transaction_ids ||
      replayed.encoded_receipts != stored.receipts ||
      replayed.receipts.size() != stored.receipts.size() ||
      replayed.previous_state_root != previous_root ||
      replayed.transaction_root != transaction_root ||
      replayed.resulting_state_root != resulting_root ||
      replayed.header != header ||
      replayed.block_id != block_id) {
    fail(SQLiteLedgerError::state_mismatch);
  }
}

bool require_snapshot_match(
    const std::optional<DecodedSnapshotV1>& snapshot,
    const pv1::Ledger& ledger) {
  if (!snapshot ||
      snapshot->ledger.state().height != ledger.state().height) {
    return false;
  }
  auto root = ledger.current_state_root();
  if (!std::holds_alternative<pv1::StateRoot>(root) ||
      snapshot->ledger.state() != ledger.state() ||
      snapshot->state_root != std::get<pv1::StateRoot>(root)) {
    fail(SQLiteLedgerError::state_mismatch);
  }
  return true;
}

void replay_block_row(
    Connection& connection,
    Statement& blocks,
    pv1::Ledger& ledger) {
  if (blocks.column_count() != 7 ||
      ledger.state().height == std::numeric_limits<std::uint64_t>::max()) {
    fail(SQLiteLedgerError::state_mismatch);
  }
  const auto height = decode_unsigned(blocks, 0, 8);
  if (height != ledger.state().height + 1) {
    fail(SQLiteLedgerError::state_mismatch);
  }
  const auto previous_root =
      decode_tagged_hash<pv1::StateRoot>(blocks, 1);
  const auto transaction_root =
      decode_tagged_hash<pv1::TransactionRoot>(blocks, 2);
  const auto resulting_root =
      decode_tagged_hash<pv1::StateRoot>(blocks, 3);
  const auto admitted_count_value = decode_unsigned(blocks, 4, 4);
  if (admitted_count_value > kMaximumBlockInputs) {
    fail(SQLiteLedgerError::state_mismatch);
  }
  const auto admitted_count =
      static_cast<std::uint32_t>(admitted_count_value);
  const auto header = decode_bytes(blocks, 5, 146);
  const auto block_id =
      decode_tagged_hash<pv1::BlockId>(blocks, 6);
  const auto stored =
      load_journal(connection, height, admitted_count);

  auto applied = ledger.apply_block(height, stored.transactions);
  if (!std::holds_alternative<pv1::BlockCommit>(applied)) {
    fail(SQLiteLedgerError::state_mismatch);
  }
  const auto& replayed = std::get<pv1::BlockCommit>(applied);
  require_replay_match(
      replayed, stored, previous_root, transaction_root,
      resulting_root, header, block_id);
}

}  // namespace

pv1::Ledger replay_history_v1(
    Connection& connection,
    const pv1::Ledger& trusted_genesis_ledger) {
  pv1::Ledger ledger(trusted_genesis_ledger);
  const auto snapshot = load_snapshot_v1(
      connection, trusted_genesis_ledger.state().parameters);
  bool snapshot_matched = require_snapshot_match(snapshot, ledger);
  Statement blocks = connection.prepare(
      "SELECT height, previous_state_root, transaction_root, "
      "resulting_state_root, admitted_count, header, block_id "
      "FROM blocks ORDER BY height");
  while (checked_step(blocks) == SQLITE_ROW) {
    replay_block_row(connection, blocks, ledger);
    if (require_snapshot_match(snapshot, ledger)) {
      snapshot_matched = true;
    }
  }
  if (snapshot && !snapshot_matched) {
    fail(SQLiteLedgerError::state_mismatch);
  }
  return ledger;
}

}  // namespace protocol::storage::internal
