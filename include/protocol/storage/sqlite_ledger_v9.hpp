#pragma once

// The version-nine owning store: a `Ledger` that survives the process that
// built it.
//
// The C++20 kernel executes blocks against an in-memory ledger, and
// `protocol::storage::snapshot_v9` turns one into canonical bytes. This joins
// them to a durable file, which is what requirement 13's "restart and recovery"
// needs before two replicas can be asked to agree.
//
// **The head is stored as one snapshot payload rather than decomposed into
// rows.** ADR 0007 already settles that a storage layout is operational data
// which "never defines transaction, receipt, state-root, or block meaning", and
// the snapshot is a payload the repository has already checked against recorded
// figures, three gates, and a fuzz target. Storing a second, row-shaped
// projection of the same state would be a second opinion about what a state
// *is*, and it would have to be kept in step with every future entry kind. The
// cost is that a commit rewrites the whole head, which is `O(state)` per block;
// it is node-local, changes no accepted state, and is replaceable the day a
// fixture needs it to be.
//
// **Under version nine the head is two scalars and a root**, because the state
// commits to the block's timestamp beside its height. The payload already
// carries both, so a store that writes the whole payload cannot leave the stamp
// behind; the columns beside it name all three so that a reopen can require the
// payload to be the head the file *says* it holds, and so that the one defect
// this version could hide — a head whose stamp belongs to an earlier height,
// which every later block would still satisfy C2 against — is refused as a
// mismatch rather than restored.
//
// The connection, locking, journal, and path-stability contract is version one's
// and is reused unchanged: none of it is version-specific.

#include "protocol/storage/snapshot_v9.hpp"
#include "protocol/v9/ledger.hpp"

#include <cstdint>
#include <filesystem>
#include <memory>
#include <span>
#include <variant>

namespace protocol::storage {

// Version one's storage codes, kept at their numbers and meanings so a reader of
// every adapter is reading one vocabulary. `invalid_snapshot` is the one version
// seven added: the durable head did not survive its own restore.
enum class SQLiteLedgerV9Error : std::uint8_t {
  invalid_genesis = 1,
  invalid_path = 2,
  path_already_exists = 3,
  path_not_found = 4,
  lock_unavailable = 5,
  configuration_mismatch = 6,
  integrity_failure = 7,
  schema_mismatch = 8,
  genesis_mismatch = 9,
  state_mismatch = 10,
  storage_failure = 11,
  invalid_snapshot = 13,
};

// The ledger carries the head's timestamp in `ledger.timestamp`, so there is no
// separate field for it: a second copy is a second value that could disagree.
struct LedgerHeadV9 {
  protocol::v9::Ledger ledger;
  protocol::v9::Hash state_root;
};

// What a committed block leaves behind, which is what a caller needs to answer
// "did every replica agree" without holding the whole state. **The timestamp is
// carried beside the height** because `consensus-application-v2`'s Commit
// response reports the durable height, timestamp, and root, and the application
// should not have to read the stamp back out of a ledger it has not yet adopted.
struct BlockCommitV9 {
  std::uint64_t height = 0;
  std::uint64_t timestamp = 0;
  protocol::v9::Hash previous_state_root{};
  protocol::v9::Hash resulting_state_root{};
  protocol::v9::Hash transaction_root{};
  protocol::v9::Hash block_id{};
  std::uint32_t transaction_count = 0;

  bool operator==(const BlockCommitV9&) const = default;
};

// A block the kernel rejected whole. It is not a storage error: no write was
// attempted and the durable head is untouched.
struct BlockRejectedV9 {};

class SQLiteLedgerV9;

using SQLiteV9BlockResult =
    std::variant<BlockCommitV9, BlockRejectedV9, SQLiteLedgerV9Error>;
using SQLiteV9HeadResult = std::variant<LedgerHeadV9, SQLiteLedgerV9Error>;
using SQLiteV9SnapshotResult =
    std::variant<protocol::v9::Bytes, SQLiteLedgerV9Error>;

// Defined after the class: a variant over `SQLiteLedgerV9` instantiates traits
// that need it complete, which is why version one's header declares its own
// result the same way.
struct SQLiteLedgerV9Result;

class SQLiteLedgerV9 {
 public:
  ~SQLiteLedgerV9() noexcept;
  SQLiteLedgerV9(SQLiteLedgerV9&&) noexcept;

  SQLiteLedgerV9(const SQLiteLedgerV9&) = delete;
  SQLiteLedgerV9& operator=(const SQLiteLedgerV9&) = delete;
  SQLiteLedgerV9& operator=(SQLiteLedgerV9&&) = delete;

  SQLiteV9HeadResult read_head() const;
  // Execute one block against the durable head and commit it, or leave the head
  // exactly as it was. The verifier is supplied at construction for ADR 0045's
  // reason: the store never chooses a verification rule either.
  //
  // **`timestamp` is the agreed header field**, and the store hands it to
  // `execute_block` unchanged, which applies C1 and C2 against the durable head.
  // **C5 is not reachable from here and must not be.** A store executes blocks
  // the network already decided — a commit, a replay, a recovery — and a store
  // that re-applied the tolerance would refuse the chain's own past one
  // tolerance-width after producing it. The tolerance is the application's, at
  // `ProcessProposal`, and nowhere else; this signature has no clock to give it.
  //
  // **There is no uptime schedule to hand over and no `BlockOrder` to choose.**
  // The prologue derives the schedule from the seat table and the window
  // records, so a node cannot be given a different answer than its peers
  // computed; and the `BlockOrder` flags are demonstration flags rather than a
  // configuration a chain has, so a store that exposed them would be offering an
  // operator a way to leave consensus.
  SQLiteV9BlockResult apply_block(
      std::uint64_t height, std::uint64_t timestamp,
      std::span<const protocol::v9::Bytes> raw_transactions);
  // The durable head's own payload, as stored.
  SQLiteV9SnapshotResult create_snapshot() const;
  // The verification rule this store executes under. A caller that admits a
  // transaction before offering it — the application layer does, in
  // `check_transaction` — has to use the same rule, and asking the store for it
  // is what keeps the two from being separately configured.
  protocol::v9::SignatureVerifier verifier() const;

 private:
  struct Impl;

  explicit SQLiteLedgerV9(std::unique_ptr<Impl> implementation) noexcept;

  friend SQLiteLedgerV9Result create_sqlite_ledger_v9(
      const std::filesystem::path& path,
      const protocol::v9::Genesis& genesis,
      protocol::v9::SignatureVerifier verify);
  friend SQLiteLedgerV9Result open_sqlite_ledger_v9(
      const std::filesystem::path& path,
      const protocol::v9::Genesis& genesis,
      protocol::v9::SignatureVerifier verify);

  std::unique_ptr<Impl> implementation_;
};

struct SQLiteLedgerV9Result {
  std::variant<SQLiteLedgerV9, SQLiteLedgerV9Error> result;
};

// `path` must not exist. The genesis is taken as the struct the kernel opens a
// ledger from rather than as the 150 canonical octets, so a caller has already
// committed to a genesis the kernel accepts before a file exists: the store
// encodes it once, stores those octets, and every later open must present a
// genesis that encodes to the same ones. Presenting bytes instead would move
// `invalid_genesis` from creation time to first use.
SQLiteLedgerV9Result create_sqlite_ledger_v9(
    const std::filesystem::path& path, const protocol::v9::Genesis& genesis,
    protocol::v9::SignatureVerifier verify = protocol::v9::ed25519_verifier());

// Reopen an existing database and restore its head, which is where the
// snapshot's three gates and the conservation invariants do the validating.
SQLiteLedgerV9Result open_sqlite_ledger_v9(
    const std::filesystem::path& path, const protocol::v9::Genesis& genesis,
    protocol::v9::SignatureVerifier verify = protocol::v9::ed25519_verifier());

}  // namespace protocol::storage
