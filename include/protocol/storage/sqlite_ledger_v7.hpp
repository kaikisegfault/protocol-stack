#pragma once

// The version-seven owning store: a `Ledger` that survives the process that
// built it.
//
// The C++20 kernel executes blocks against an in-memory ledger, and
// `protocol::storage::snapshot_v7` turns one into canonical bytes. This joins
// them to a durable file, which is what requirement 13's "restart and recovery"
// needs before two replicas can be asked to agree.
//
// **The head is stored as one snapshot payload rather than decomposed into
// rows.** ADR 0007 already settles that a storage layout is operational data
// which "never defines transaction, receipt, state-root, or block meaning", and
// the snapshot is a payload the repository has already checked against recorded
// roots, three gates, and a fuzz target. Storing a second, row-shaped projection
// of the same state would be a second opinion about what a state *is* — the
// mistake the snapshot itself was designed to avoid — and it would have to be
// kept in step with every future entry kind. The cost is that a commit rewrites
// the whole head, which is `O(state)` per block; it is node-local, changes no
// accepted state, and is replaceable the day a fixture needs it to be.
//
// The connection, locking, journal, and path-stability contract is version one's
// and is reused unchanged: none of it is version-specific.

#include "protocol/storage/snapshot_v7.hpp"
#include "protocol/v7/ledger.hpp"

#include <cstdint>
#include <filesystem>
#include <memory>
#include <span>
#include <variant>

namespace protocol::storage {

// Version one's storage codes, kept at their numbers and meanings so a reader of
// both adapters is reading one vocabulary. `invalid_snapshot` is version seven's
// own: the durable head did not survive its own restore.
enum class SQLiteLedgerV7Error : std::uint8_t {
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

struct LedgerHeadV7 {
  protocol::v7::Ledger ledger;
  protocol::v7::Hash state_root;
};

// What a committed block leaves behind, which is what a caller needs to answer
// "did every replica agree" without holding the whole state.
struct BlockCommitV7 {
  std::uint64_t height = 0;
  protocol::v7::Hash previous_state_root{};
  protocol::v7::Hash resulting_state_root{};
  protocol::v7::Hash transaction_root{};
  protocol::v7::Hash block_id{};
  std::uint32_t transaction_count = 0;
};

// A block the kernel rejected whole. It is not a storage error: no write was
// attempted and the durable head is untouched.
struct BlockRejectedV7 {};

class SQLiteLedgerV7;

using SQLiteV7BlockResult =
    std::variant<BlockCommitV7, BlockRejectedV7, SQLiteLedgerV7Error>;
using SQLiteV7HeadResult = std::variant<LedgerHeadV7, SQLiteLedgerV7Error>;
using SQLiteV7SnapshotResult =
    std::variant<protocol::v7::Bytes, SQLiteLedgerV7Error>;

// Defined after the class: a variant over `SQLiteLedgerV7` instantiates traits
// that need it complete, which is why version one's header declares its own
// result the same way.
struct SQLiteLedgerV7Result;

class SQLiteLedgerV7 {
 public:
  ~SQLiteLedgerV7() noexcept;
  SQLiteLedgerV7(SQLiteLedgerV7&&) noexcept;

  SQLiteLedgerV7(const SQLiteLedgerV7&) = delete;
  SQLiteLedgerV7& operator=(const SQLiteLedgerV7&) = delete;
  SQLiteLedgerV7& operator=(SQLiteLedgerV7&&) = delete;

  SQLiteV7HeadResult read_head() const;
  // Execute one block against the durable head and commit it, or leave the head
  // exactly as it was. The verifier is supplied at construction for ADR 0045's
  // reason: the store never chooses a verification rule either.
  SQLiteV7BlockResult apply_block(
      std::uint64_t height,
      std::span<const protocol::v7::Bytes> raw_transactions,
      const protocol::v7::UptimeSchedule* uptime = nullptr);
  // The durable head's own payload, as stored.
  SQLiteV7SnapshotResult create_snapshot() const;

 private:
  struct Impl;

  explicit SQLiteLedgerV7(std::unique_ptr<Impl> implementation) noexcept;

  friend SQLiteLedgerV7Result create_sqlite_ledger_v7(
      const std::filesystem::path& path,
      const protocol::v7::Genesis& genesis,
      protocol::v7::SignatureVerifier verify);
  friend SQLiteLedgerV7Result open_sqlite_ledger_v7(
      const std::filesystem::path& path,
      const protocol::v7::Genesis& genesis,
      protocol::v7::SignatureVerifier verify);

  std::unique_ptr<Impl> implementation_;
};

struct SQLiteLedgerV7Result {
  std::variant<SQLiteLedgerV7, SQLiteLedgerV7Error> result;
};

// `path` must not exist. The genesis is taken as the struct the kernel opens a
// ledger from rather than as bytes, because version seven publishes
// `encode_genesis` and no inverse; the store encodes it once, stores the
// canonical bytes, and every later open must produce the same ones.
SQLiteLedgerV7Result create_sqlite_ledger_v7(
    const std::filesystem::path& path, const protocol::v7::Genesis& genesis,
    protocol::v7::SignatureVerifier verify = protocol::v7::ed25519_verifier());

// Reopen an existing database and restore its head, which is where the
// snapshot's three gates and the conservation invariants do the validating.
SQLiteLedgerV7Result open_sqlite_ledger_v7(
    const std::filesystem::path& path, const protocol::v7::Genesis& genesis,
    protocol::v7::SignatureVerifier verify = protocol::v7::ed25519_verifier());

}  // namespace protocol::storage
