#include "sqlite_archive_v1.hpp"

#include "sqlite_history_v1.hpp"
#include "sqlite_schema_v1.hpp"
#include "sqlite_snapshot_v1.hpp"

#include "protocol/storage/snapshot_v1.hpp"

#include <algorithm>
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

[[noreturn]] void fail() {
  throw Failure{SQLiteLedgerError::storage_failure};
}

pv1::StateRoot require_root(const pv1::Ledger& ledger) {
  auto root = ledger.current_state_root();
  if (!std::holds_alternative<pv1::StateRoot>(root)) fail();
  return std::get<pv1::StateRoot>(std::move(root));
}

bool all_admitted(const pv1::BlockCommit& commit) {
  return std::all_of(
      commit.admissions.begin(), commit.admissions.end(),
      [](const auto& admission) { return !admission.has_value(); });
}

std::vector<pv1::Bytes> raw_transactions(
    const ArchiveBlockV1& block) {
  std::vector<pv1::Bytes> transactions;
  transactions.reserve(block.transactions.size());
  for (const auto& transaction : block.transactions) {
    transactions.push_back(transaction.transaction);
  }
  return transactions;
}

void require_block_match(
    const pv1::BlockCommit& commit,
    const ArchiveBlockV1& block) {
  if (!all_admitted(commit) ||
      commit.transaction_ids.size() != block.transactions.size() ||
      commit.encoded_receipts.size() != block.transactions.size() ||
      commit.header != block.header ||
      commit.block_id != block.block_id) {
    fail();
  }
  for (std::size_t ordinal = 0;
       ordinal < block.transactions.size(); ++ordinal) {
    if (commit.transaction_ids[ordinal] !=
            block.transactions[ordinal].transaction_id ||
        commit.encoded_receipts[ordinal] !=
            block.transactions[ordinal].receipt) {
      fail();
    }
  }
}

EncodedSnapshotV1 require_snapshot(
    const DecodedArchiveV1& archive,
    const pv1::Ledger& ledger) {
  auto decoded = decode_snapshot_v1(
      archive.data.head_snapshot, ledger.state().parameters);
  if (!std::holds_alternative<DecodedSnapshotV1>(decoded)) fail();
  auto snapshot =
      std::get<DecodedSnapshotV1>(std::move(decoded));
  if (snapshot.ledger.state() != ledger.state() ||
      snapshot.state_root != archive.state_root ||
      snapshot.ledger.state() != archive.ledger.state()) {
    fail();
  }
  return EncodedSnapshotV1{
      archive.data.head_snapshot,
      snapshot.state_root,
      snapshot.digest,
  };
}

}  // namespace

void persist_archive_v1(
    Connection& connection,
    const DecodedArchiveV1& archive) {
  if (connection.autocommit()) fail();

  auto loaded = pv1::load_genesis(archive.data.canonical_genesis);
  if (!std::holds_alternative<pv1::Ledger>(loaded.result)) fail();
  auto ledger = std::get<pv1::Ledger>(std::move(loaded.result));
  const auto genesis_root = require_root(ledger);
  install_schema_v1(
      connection, archive.data.canonical_genesis, ledger, genesis_root);

  for (const auto& block : archive.data.blocks) {
    if (ledger.state().height ==
        std::numeric_limits<std::uint64_t>::max()) {
      fail();
    }
    const auto previous_state = ledger.state();
    const auto transactions = raw_transactions(block);
    auto applied = ledger.apply_block(
        previous_state.height + 1, transactions);
    if (!std::holds_alternative<pv1::BlockCommit>(applied)) fail();
    const auto& commit = std::get<pv1::BlockCommit>(applied);
    require_block_match(commit, block);
    persist_block_v1(
        connection, previous_state, ledger.state(),
        transactions, commit);
  }

  if (ledger.state() != archive.ledger.state() ||
      require_root(ledger) != archive.state_root) {
    fail();
  }
  const auto snapshot = require_snapshot(archive, ledger);
  persist_snapshot_v1(connection, ledger, snapshot);
}

}  // namespace protocol::storage::internal
