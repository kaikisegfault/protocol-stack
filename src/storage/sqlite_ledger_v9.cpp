// The version-nine owning store.
//
// `apply_block` executes against a *candidate* copy of the head and commits only
// what the kernel accepted, so a rejected block and a failed write leave the
// durable head and the live head identically untouched. That is the same shape
// version one's store has, and it is what makes "the head is what some sequence
// of blocks produced" true of the file rather than only of the process.
//
// **Reopening is where the validation lives and none of it is here.**
// `sqlite_ledger_v9_open.cpp` holds it, because a store is validated once and
// then trusted for its lifetime.

#include "protocol/storage/sqlite_ledger_v9.hpp"

#include "sqlite_ledger_v9_internal.hpp"

#include <memory>
#include <mutex>
#include <type_traits>
#include <utility>
#include <variant>

namespace protocol::storage {

using namespace internal_v9;

namespace {

bool fault(internal::SQLiteBlockFaultPoint point,
           internal::Connection& connection) {
  return internal::invoke_sqlite_block_fault(point, connection.get());
}

}  // namespace
static_assert(std::is_nothrow_move_constructible_v<SQLiteLedgerV9>);
static_assert(std::is_nothrow_destructible_v<SQLiteLedgerV9>);

SQLiteLedgerV9::SQLiteLedgerV9(std::unique_ptr<Impl> implementation) noexcept
    : implementation_(std::move(implementation)) {}

SQLiteLedgerV9::~SQLiteLedgerV9() noexcept = default;
SQLiteLedgerV9::SQLiteLedgerV9(SQLiteLedgerV9&&) noexcept = default;

SQLiteV9HeadResult SQLiteLedgerV9::read_head() const {
  const std::lock_guard<std::mutex> lock(implementation_->mutex);
  if (implementation_->poisoned) {
    return SQLiteV9HeadResult(std::in_place_type<SQLiteLedgerV9Error>,
                              SQLiteLedgerV9Error::storage_failure);
  }
  return SQLiteV9HeadResult(
      std::in_place_type<LedgerHeadV9>,
      LedgerHeadV9{implementation_->ledger, implementation_->state_root});
}

SQLiteV9SnapshotResult SQLiteLedgerV9::create_snapshot() const {
  const std::lock_guard<std::mutex> lock(implementation_->mutex);
  if (implementation_->poisoned) {
    return SQLiteV9SnapshotResult(std::in_place_type<SQLiteLedgerV9Error>,
                                  SQLiteLedgerV9Error::storage_failure);
  }
  return SQLiteV9SnapshotResult(std::in_place_type<v9::Bytes>,
                                implementation_->head_snapshot);
}

v9::SignatureVerifier SQLiteLedgerV9::verifier() const {
  const std::lock_guard<std::mutex> lock(implementation_->mutex);
  return implementation_->verify;
}

SQLiteV9BlockResult SQLiteLedgerV9::apply_block(
    std::uint64_t height, std::uint64_t timestamp,
    std::span<const v9::Bytes> raw_transactions) {
  const std::lock_guard<std::mutex> lock(implementation_->mutex);
  auto& state = *implementation_;
  if (state.poisoned) {
    return SQLiteV9BlockResult(std::in_place_type<SQLiteLedgerV9Error>,
                               SQLiteLedgerV9Error::storage_failure);
  }
  // The kernel advances a ledger from `h` to `h + 1` and does not take a target
  // height, so a caller naming any other height is naming a block this chain
  // cannot be at. Refusing it here keeps the store's contract explicit rather
  // than making the caller infer the next height.
  if (height != state.ledger.height + 1) {
    return SQLiteV9BlockResult(std::in_place_type<BlockRejectedV9>,
                               BlockRejectedV9{});
  }

  // The candidate is a copy, so a rejected block never touches the live head.
  // **Under version nine the copy is never wasted work.** A block with no
  // transactions audits every in-scope seat, as version eight's did, and the
  // state it leaves carries the block's own height and stamp, both of which the
  // root commits to — so there is no height at which the head could be left
  // unwritten.
  //
  // **The stamp is the caller's and C1 and C2 are the kernel's.** A stamp below
  // the durable head's is refused here as a rejected block, against the head
  // this store restored, which is the one comparison a stale restored stamp would
  // silently weaken.
  v9::Ledger candidate = state.ledger;
  auto executed =
      v9::execute_block(candidate, timestamp, raw_transactions, state.verify);
  if (!executed) {
    return SQLiteV9BlockResult(std::in_place_type<BlockRejectedV9>,
                               BlockRejectedV9{});
  }

  // Every figure here is the kernel's own. The transaction root in particular is
  // taken from the outcome rather than re-derived from the executed identifiers:
  // the header already commits to one, and a store that computed its own would
  // be a second opinion about the block it is recording.
  BlockCommitV9 commit;
  commit.height = executed->height;
  commit.timestamp = executed->timestamp;
  commit.previous_state_root = executed->previous_state_root;
  commit.resulting_state_root = executed->resulting_state_root;
  commit.transaction_root = executed->transaction_root;
  commit.block_id = executed->block_id;
  commit.transaction_count =
      static_cast<std::uint32_t>(executed->executed.size());

  // The payload is built before the write path is entered, because a state that
  // cannot be encoded is a refusal rather than a poisoning: nothing was written,
  // and the durable and live heads are both the state they already were.
  internal::DurableHeadV9 durable;
  try {
    durable = durable_head_of(candidate);
  } catch (const FailureV9& failure) {
    return SQLiteV9BlockResult(std::in_place_type<SQLiteLedgerV9Error>,
                               failure.error);
  } catch (...) {
    return SQLiteV9BlockResult(std::in_place_type<SQLiteLedgerV9Error>,
                               SQLiteLedgerV9Error::storage_failure);
  }

  // **Everything up to the commit rolls back and writes nothing.** A failure
  // there is an ordinary refusal: the transaction is abandoned, the durable head
  // is the one it already was, and the store keeps working. Only the commit
  // itself can leave a head this process cannot name.
  try {
    auto& connection = state.resources->connection;
    internal::verify_stable_path(*state.resources, state.path);
    if (fault(internal::SQLiteBlockFaultPoint::before_transaction, connection)) {
      throw FailureV9{SQLiteLedgerV9Error::storage_failure};
    }
    internal::begin_exclusive(connection);
    try {
      if (fault(internal::SQLiteBlockFaultPoint::after_transaction_begin,
                connection)) {
        throw FailureV9{SQLiteLedgerV9Error::storage_failure};
      }
      internal::persist_block_v9(connection, durable, commit, executed->header);
      if (fault(internal::SQLiteBlockFaultPoint::after_persistence, connection)) {
        throw FailureV9{SQLiteLedgerV9Error::storage_failure};
      }
      internal::verify_stable_path(*state.resources, state.path);
      if (fault(internal::SQLiteBlockFaultPoint::before_commit, connection)) {
        throw FailureV9{SQLiteLedgerV9Error::storage_failure};
      }
    } catch (...) {
      internal::rollback_or_terminate(connection);
      throw;
    }

    // From here the transaction may have landed and this process may not know.
    // Anything that goes wrong poisons the store, and recovery is an attempt to
    // stop being poisoned by reading the file again.
    auto commit_error = SQLiteLedgerV9Error::storage_failure;
    bool published = false;
    try {
      internal::commit(connection);
      // Invoked and ignored: a test terminates the process here, which is how
      // "the durable head is the block's or its predecessor's and never
      // anything between" is checked rather than argued.
      (void)internal::invoke_sqlite_block_fault(
          internal::SQLiteBlockFaultPoint::after_commit_before_publication,
          connection.get());
      internal::verify_stable_path(*state.resources, state.path);
      published = true;
    } catch (const FailureV9& failure) {
      commit_error = failure.error;
    } catch (const internal::Failure& failure) {
      commit_error = translate(failure.error);
    } catch (...) {
    }
    if (!published) {
      state.poisoned = true;
      (void)state.recover_durable_head();
      return SQLiteV9BlockResult(std::in_place_type<SQLiteLedgerV9Error>,
                                 commit_error);
    }

    state.ledger = std::move(candidate);
    state.state_root = durable.state_root;
    state.head_snapshot = std::move(durable.snapshot);
    (void)internal::invoke_sqlite_block_fault(
        internal::SQLiteBlockFaultPoint::after_publication, connection.get());
  } catch (const FailureV9& failure) {
    return SQLiteV9BlockResult(std::in_place_type<SQLiteLedgerV9Error>,
                               failure.error);
  } catch (const internal::Failure& failure) {
    return SQLiteV9BlockResult(std::in_place_type<SQLiteLedgerV9Error>,
                               translate(failure.error));
  } catch (...) {
    return SQLiteV9BlockResult(std::in_place_type<SQLiteLedgerV9Error>,
                               SQLiteLedgerV9Error::storage_failure);
  }
  return SQLiteV9BlockResult(std::in_place_type<BlockCommitV9>, commit);
}

}  // namespace protocol::storage
