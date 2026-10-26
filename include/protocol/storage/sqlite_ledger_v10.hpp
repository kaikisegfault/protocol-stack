#pragma once

// The version-ten owning store: a `Ledger` that survives the process that
// built it. It is version nine's store with the namespace rebound and the
// widths and markers version ten moves (ADR 0109).
//
// The C++20 kernel executes blocks against an in-memory ledger, and
// `protocol::storage::snapshot_v10` turns one into canonical bytes. This joins
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
// **The head is version nine's two scalars and a root**, because the state
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

#include "protocol/storage/snapshot_v10.hpp"
#include "protocol/v10/ledger.hpp"

#include <cstdint>
#include <filesystem>
#include <memory>
#include <span>
#include <variant>

namespace protocol::storage {

// Version one's storage codes, kept at their numbers and meanings so a reader of
// every adapter is reading one vocabulary. `invalid_snapshot` is the one version
// seven added: the durable head did not survive its own restore.
enum class SQLiteLedgerV10Error : std::uint8_t {
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
struct LedgerHeadV10 {
  protocol::v10::Ledger ledger;
  protocol::v10::Hash state_root;
};

// What a committed block leaves behind, which is what a caller needs to answer
// "did every replica agree" without holding the whole state. **The timestamp is
// carried beside the height** because `consensus-application-v2`'s Commit
// response reports the durable height, timestamp, and root, and the application
// should not have to read the stamp back out of a ledger it has not yet adopted.
struct BlockCommitV10 {
  std::uint64_t height = 0;
  std::uint64_t timestamp = 0;
  protocol::v10::Hash previous_state_root{};
  protocol::v10::Hash resulting_state_root{};
  protocol::v10::Hash transaction_root{};
  protocol::v10::Hash block_id{};
  std::uint32_t transaction_count = 0;

  bool operator==(const BlockCommitV10&) const = default;
};

// A block the kernel rejected whole. It is not a storage error: no write was
// attempted and the durable head is untouched.
struct BlockRejectedV10 {};

class SQLiteLedgerV10;

using SQLiteV10BlockResult =
    std::variant<BlockCommitV10, BlockRejectedV10, SQLiteLedgerV10Error>;
using SQLiteV10HeadResult = std::variant<LedgerHeadV10, SQLiteLedgerV10Error>;
using SQLiteV10SnapshotResult =
    std::variant<protocol::v10::Bytes, SQLiteLedgerV10Error>;

// Defined after the class: a variant over `SQLiteLedgerV10` instantiates traits
// that need it complete, which is why version one's header declares its own
// result the same way.
struct SQLiteLedgerV10Result;

class SQLiteLedgerV10 {
 public:
  ~SQLiteLedgerV10() noexcept;
  SQLiteLedgerV10(SQLiteLedgerV10&&) noexcept;

  SQLiteLedgerV10(const SQLiteLedgerV10&) = delete;
  SQLiteLedgerV10& operator=(const SQLiteLedgerV10&) = delete;
  SQLiteLedgerV10& operator=(SQLiteLedgerV10&&) = delete;

  SQLiteV10HeadResult read_head() const;
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
  SQLiteV10BlockResult apply_block(
      std::uint64_t height, std::uint64_t timestamp,
      std::span<const protocol::v10::Bytes> raw_transactions);
  // The durable head's own payload, as stored.
  SQLiteV10SnapshotResult create_snapshot() const;
  // The verification rule this store executes under. A caller that admits a
  // transaction before offering it — the application layer does, in
  // `check_transaction` — has to use the same rule, and asking the store for it
  // is what keeps the two from being separately configured.
  protocol::v10::SignatureVerifier verifier() const;

 private:
  struct Impl;

  explicit SQLiteLedgerV10(std::unique_ptr<Impl> implementation) noexcept;

  friend SQLiteLedgerV10Result create_sqlite_ledger_v10(
      const std::filesystem::path& path,
      const protocol::v10::Genesis& genesis,
      protocol::v10::SignatureVerifier verify);
  friend SQLiteLedgerV10Result open_sqlite_ledger_v10(
      const std::filesystem::path& path,
      const protocol::v10::Genesis& genesis,
      protocol::v10::SignatureVerifier verify);
  friend SQLiteLedgerV10Result seed_sqlite_ledger_v10(
      const std::filesystem::path& path,
      const protocol::v10::Genesis& genesis,
      std::span<const std::uint8_t> snapshot,
      protocol::v10::SignatureVerifier verify);

  std::unique_ptr<Impl> implementation_;
};

struct SQLiteLedgerV10Result {
  std::variant<SQLiteLedgerV10, SQLiteLedgerV10Error> result;
};

// `path` must not exist. The genesis is taken as the struct the kernel opens a
// ledger from rather than as the 182 canonical octets, so a caller has already
// committed to a genesis the kernel accepts before a file exists: the store
// encodes it once, stores those octets, and every later open must present a
// genesis that encodes to the same ones. Presenting bytes instead would move
// `invalid_genesis` from creation time to first use.
SQLiteLedgerV10Result create_sqlite_ledger_v10(
    const std::filesystem::path& path, const protocol::v10::Genesis& genesis,
    protocol::v10::SignatureVerifier verify = protocol::v10::ed25519_verifier());

// Reopen an existing database and restore its head, which is where the
// snapshot's three gates and the conservation invariants do the validating.
SQLiteLedgerV10Result open_sqlite_ledger_v10(
    const std::filesystem::path& path, const protocol::v10::Genesis& genesis,
    protocol::v10::SignatureVerifier verify = protocol::v10::ed25519_verifier());

// Create a database whose head is a restored snapshot, for a network that
// begins above height zero (ADR 0096). `path` must not exist, as for a create.
//
// **The payload is accepted only through `decode_snapshot_v10`'s three gates,
// under the parameters `genesis` fixes**, so a seed is a state some sequence of
// blocks could have produced on this chain, or it is `invalid_snapshot` and no
// file is written. A height-zero payload is refused the same way, because it
// is a genesis and `create_sqlite_ledger_v10` makes those. So is a payload that
// does not re-encode to exactly its own octets: the head column is compared
// byte for byte on every commit, and a seed must already be canonical.
//
// The store holds no block rows below the seeded head. Nothing reads them to
// open or to execute, and a seeded store is thereafter indistinguishable from
// any other at the same head.
SQLiteLedgerV10Result seed_sqlite_ledger_v10(
    const std::filesystem::path& path, const protocol::v10::Genesis& genesis,
    std::span<const std::uint8_t> snapshot,
    protocol::v10::SignatureVerifier verify = protocol::v10::ed25519_verifier());

// The head `seed_sqlite_ledger_v10` would create from `snapshot`, checked by
// exactly the same rules and with nothing written. A launcher needs the seeded
// height, stamp, and root on every start, including starts after the stores
// have moved past them, and this is where it reads them without a store.
SQLiteV10HeadResult inspect_seed_v10(const protocol::v10::Genesis& genesis,
                                   std::span<const std::uint8_t> snapshot);

}  // namespace protocol::storage
