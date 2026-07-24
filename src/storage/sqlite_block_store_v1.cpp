#include "sqlite_history_v1.hpp"

#include <sqlite3.h>

#include <array>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <span>

namespace protocol::storage::internal {
namespace {

namespace pv1 = protocol::v1;
constexpr std::size_t kMaximumBlockInputs = 65'535;

[[noreturn]] void fail() {
  throw Failure{SQLiteLedgerError::storage_failure};
}

void require_done(Statement& statement) {
  if (statement.step() != SQLITE_DONE) fail();
}

void require_single_change(Connection& connection) {
  if (sqlite3_changes(connection.get()) != 1) fail();
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

std::array<std::uint8_t, 4> encode_u32(std::uint32_t value) {
  std::array<std::uint8_t, 4> encoded{};
  for (std::size_t index = 0; index < encoded.size(); ++index) {
    const auto shift = static_cast<unsigned>(
        (encoded.size() - index - 1) * 8);
    encoded[index] = static_cast<std::uint8_t>(value >> shift);
  }
  return encoded;
}

template <typename Tagged>
std::span<const std::uint8_t> tagged_bytes(
    const Tagged& value) noexcept {
  return {value.data(), value.size()};
}

std::size_t require_commit_shape(
    const pv1::State& previous_state,
    const pv1::State& resulting_state,
    std::span<const pv1::Bytes> raw_transactions,
    const pv1::BlockCommit& commit) {
  if (previous_state.height == std::numeric_limits<std::uint64_t>::max() ||
      resulting_state.height != previous_state.height + 1 ||
      commit.height != resulting_state.height ||
      previous_state.parameters != resulting_state.parameters ||
      commit.admissions.size() != raw_transactions.size() ||
      commit.transaction_ids.size() != commit.receipts.size() ||
      commit.transaction_ids.size() != commit.encoded_receipts.size() ||
      commit.transaction_ids.size() > kMaximumBlockInputs ||
      commit.header.size() != 146) {
    fail();
  }

  std::size_t admitted_count = 0;
  for (const auto& admission : commit.admissions) {
    if (!admission) ++admitted_count;
  }
  if (admitted_count != commit.transaction_ids.size()) fail();
  return admitted_count;
}

void persist_accounts(
    Connection& connection,
    const pv1::State& previous_state,
    const pv1::State& resulting_state) {
  for (const auto& [account_id, account] : previous_state.accounts) {
    const auto found = resulting_state.accounts.find(account_id);
    if (found == resulting_state.accounts.end()) fail();
    (void)account;
  }

  Statement upsert = connection.prepare(
      "INSERT INTO accounts(account_id, balance, nonce) VALUES(?, ?, ?) "
      "ON CONFLICT(account_id) DO UPDATE SET "
      "balance=excluded.balance, nonce=excluded.nonce");
  for (const auto& [account_id, account] : resulting_state.accounts) {
    const auto previous = previous_state.accounts.find(account_id);
    if (previous != previous_state.accounts.end() &&
        previous->second == account) {
      continue;
    }
    const auto balance = encode_u64(account.balance);
    const auto nonce = encode_u64(account.nonce);
    upsert.bind_blob(1, tagged_bytes(account_id));
    upsert.bind_blob(2, balance);
    upsert.bind_blob(3, nonce);
    require_done(upsert);
    require_single_change(connection);
    upsert.reset();
  }
}

void persist_block_row(
    Connection& connection,
    const pv1::BlockCommit& commit,
    std::size_t admitted_count) {
  Statement insert = connection.prepare(
      "INSERT INTO blocks("
      "height, previous_state_root, transaction_root, "
      "resulting_state_root, admitted_count, header, block_id"
      ") VALUES(?, ?, ?, ?, ?, ?, ?)");
  const auto height = encode_u64(commit.height);
  const auto count =
      encode_u32(static_cast<std::uint32_t>(admitted_count));
  insert.bind_blob(1, height);
  insert.bind_blob(2, tagged_bytes(commit.previous_state_root));
  insert.bind_blob(3, tagged_bytes(commit.transaction_root));
  insert.bind_blob(4, tagged_bytes(commit.resulting_state_root));
  insert.bind_blob(5, count);
  insert.bind_blob(6, commit.header);
  insert.bind_blob(7, tagged_bytes(commit.block_id));
  require_done(insert);
  require_single_change(connection);
}

void persist_admitted_transactions(
    Connection& connection,
    std::span<const pv1::Bytes> raw_transactions,
    const pv1::BlockCommit& commit) {
  Statement insert = connection.prepare(
      "INSERT INTO admitted_transactions("
      "height, ordinal, transaction_bytes, transaction_id, receipt_bytes"
      ") VALUES(?, ?, ?, ?, ?)");
  const auto height = encode_u64(commit.height);
  std::uint32_t ordinal = 0;
  for (std::size_t raw_index = 0;
       raw_index < raw_transactions.size(); ++raw_index) {
    if (commit.admissions[raw_index]) continue;
    const auto& raw = raw_transactions[raw_index];
    const auto& receipt = commit.encoded_receipts[ordinal];
    if (raw.size() != 200 || receipt.size() != 47) fail();
    const auto encoded_ordinal = encode_u32(ordinal);
    insert.bind_blob(1, height);
    insert.bind_blob(2, encoded_ordinal);
    insert.bind_blob(3, raw);
    insert.bind_blob(
        4, tagged_bytes(commit.transaction_ids[ordinal]));
    insert.bind_blob(5, receipt);
    require_done(insert);
    require_single_change(connection);
    insert.reset();
    ++ordinal;
  }
}

void update_metadata(
    Connection& connection,
    const pv1::State& previous_state,
    const pv1::State& resulting_state,
    const pv1::BlockCommit& commit) {
  Statement update = connection.prepare(
      "UPDATE ledger_meta SET "
      "current_height=?, fee_pool=?, current_state_root=? "
      "WHERE singleton=1 AND current_height=? "
      "AND current_state_root=?");
  const auto next_height = encode_u64(resulting_state.height);
  const auto next_fee_pool = encode_u64(resulting_state.fee_pool);
  const auto previous_height = encode_u64(previous_state.height);
  update.bind_blob(1, next_height);
  update.bind_blob(2, next_fee_pool);
  update.bind_blob(3, tagged_bytes(commit.resulting_state_root));
  update.bind_blob(4, previous_height);
  update.bind_blob(5, tagged_bytes(commit.previous_state_root));
  require_done(update);
  require_single_change(connection);
}

}  // namespace

void persist_block_v1(
    Connection& connection,
    const pv1::State& previous_state,
    const pv1::State& resulting_state,
    std::span<const pv1::Bytes> raw_transactions,
    const pv1::BlockCommit& commit) {
  if (connection.autocommit()) fail();
  const auto admitted_count = require_commit_shape(
      previous_state, resulting_state, raw_transactions, commit);
  persist_accounts(connection, previous_state, resulting_state);
  persist_block_row(connection, commit, admitted_count);
  persist_admitted_transactions(connection, raw_transactions, commit);
  update_metadata(
      connection, previous_state, resulting_state, commit);
}

}  // namespace protocol::storage::internal
