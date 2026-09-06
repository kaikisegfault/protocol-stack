#pragma once

// The version-eight owning store: a `Ledger` that survives the process that
// built it.
//
// The C++20 kernel executes blocks against an in-memory ledger, and
// `protocol::storage::snapshot_v8` turns one into canonical bytes. This joins
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
// **Under version eight the state changes at every height a seat is in scope**,
// because the issue step audits every one of them and the expiry step resolves
// those audits `kResponseDeadlineBlocks` later. Under version seven a
// transaction-free block at an ordinary height left the root exactly as it
// found it, so a store could in principle have skipped the rewrite; under
// version eight it cannot, which closes the one optimisation the `O(state)`
// cost above invited. That cost is node-local and changes no accepted state —
// ADR 0007 reserves exactly that freedom for operational data — but it is the
// figure a later slice will measure before this layout is kept.
//
// The connection, locking, journal, and path-stability contract is version one's
// and is reused unchanged: none of it is version-specific.

#include "protocol/storage/snapshot_v8.hpp"
#include "protocol/v8/ledger.hpp"

#include <cstdint>
#include <filesystem>
#include <memory>
#include <span>
#include <variant>

namespace protocol::storage {

// Version one's storage codes, kept at their numbers and meanings so a reader of
// both adapters is reading one vocabulary. `invalid_snapshot` is the one
// version seven added: the durable head did not survive its own restore.
enum class SQLiteLedgerV8Error : std::uint8_t {
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

struct LedgerHeadV8 {
  protocol::v8::Ledger ledger;
  protocol::v8::Hash state_root;
};

// What a committed block leaves behind, which is what a caller needs to answer
// "did every replica agree" without holding the whole state.
struct BlockCommitV8 {
  std::uint64_t height = 0;
  protocol::v8::Hash previous_state_root{};
  protocol::v8::Hash resulting_state_root{};
  protocol::v8::Hash transaction_root{};
  protocol::v8::Hash block_id{};
  std::uint32_t transaction_count = 0;

  bool operator==(const BlockCommitV8&) const = default;
};

// A block the kernel rejected whole. It is not a storage error: no write was
// attempted and the durable head is untouched.
struct BlockRejectedV8 {};

class SQLiteLedgerV8;

using SQLiteV8BlockResult =
    std::variant<BlockCommitV8, BlockRejectedV8, SQLiteLedgerV8Error>;
using SQLiteV8HeadResult = std::variant<LedgerHeadV8, SQLiteLedgerV8Error>;
using SQLiteV8SnapshotResult =
    std::variant<protocol::v8::Bytes, SQLiteLedgerV8Error>;

// Defined after the class: a variant over `SQLiteLedgerV8` instantiates traits
// that need it complete, which is why version one's header declares its own
// result the same way.
struct SQLiteLedgerV8Result;

class SQLiteLedgerV8 {
 public:
  ~SQLiteLedgerV8() noexcept;
  SQLiteLedgerV8(SQLiteLedgerV8&&) noexcept;

  SQLiteLedgerV8(const SQLiteLedgerV8&) = delete;
  SQLiteLedgerV8& operator=(const SQLiteLedgerV8&) = delete;
  SQLiteLedgerV8& operator=(SQLiteLedgerV8&&) = delete;

  SQLiteV8HeadResult read_head() const;
  // Execute one block against the durable head and commit it, or leave the head
  // exactly as it was. The verifier is supplied at construction for ADR 0045's
  // reason: the store never chooses a verification rule either.
  //
  // **There is no uptime schedule to hand over and no `BlockOrder` to choose.**
  // Version eight's prologue derives the schedule from the seat table and the
  // window records, so a node cannot be given a different answer than its peers
  // computed; and the three block-order flags are demonstration flags rather
  // than a configuration a chain has, so a store that exposed them would be
  // offering an operator a way to leave consensus.
  SQLiteV8BlockResult apply_block(
      std::uint64_t height,
      std::span<const protocol::v8::Bytes> raw_transactions);
  // The durable head's own payload, as stored.
  SQLiteV8SnapshotResult create_snapshot() const;
  // The verification rule this store executes under. A caller that admits a
  // transaction before offering it — the application layer does, in
  // `check_transaction` — has to use the same rule, and asking the store for it
  // is what keeps the two from being separately configured.
  protocol::v8::SignatureVerifier verifier() const;

 private:
  struct Impl;

  explicit SQLiteLedgerV8(std::unique_ptr<Impl> implementation) noexcept;

  friend SQLiteLedgerV8Result create_sqlite_ledger_v8(
      const std::filesystem::path& path,
      const protocol::v8::Genesis& genesis,
      protocol::v8::SignatureVerifier verify);
  friend SQLiteLedgerV8Result open_sqlite_ledger_v8(
      const std::filesystem::path& path,
      const protocol::v8::Genesis& genesis,
      protocol::v8::SignatureVerifier verify);

  std::unique_ptr<Impl> implementation_;
};

struct SQLiteLedgerV8Result {
  std::variant<SQLiteLedgerV8, SQLiteLedgerV8Error> result;
};

// `path` must not exist. The genesis is taken as the struct the kernel opens a
// ledger from rather than as the 142 canonical octets, so a caller has already
// committed to a genesis the kernel accepts before a file exists: the store
// encodes it once, stores those octets, and every later open must present a
// genesis that encodes to the same ones. Presenting bytes instead would move
// `invalid_genesis` from creation time to first use.
SQLiteLedgerV8Result create_sqlite_ledger_v8(
    const std::filesystem::path& path, const protocol::v8::Genesis& genesis,
    protocol::v8::SignatureVerifier verify = protocol::v8::ed25519_verifier());

// Reopen an existing database and restore its head, which is where the
// snapshot's three gates and the conservation invariants do the validating.
SQLiteLedgerV8Result open_sqlite_ledger_v8(
    const std::filesystem::path& path, const protocol::v8::Genesis& genesis,
    protocol::v8::SignatureVerifier verify = protocol::v8::ed25519_verifier());

}  // namespace protocol::storage
