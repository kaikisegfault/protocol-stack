// The version-eight owning store.
//
// `apply_block` executes against a *candidate* copy of the head and commits only
// what the kernel accepted, so a rejected block and a failed write leave the
// durable head and the live head identically untouched. That is the same shape
// version one's store has, and it is what makes "the head is what some sequence
// of blocks produced" true of the file rather than only of the process.
//
// **Reopening is where the validation lives and none of it is here.**
// `sqlite_ledger_v8_open.cpp` holds it, because a store is validated once and
// then trusted for its lifetime.

#include "protocol/storage/sqlite_ledger_v8.hpp"

#include "sqlite_ledger_v8_internal.hpp"

#include <memory>
#include <mutex>
#include <type_traits>
#include <utility>
#include <variant>

namespace protocol::storage {

using namespace internal_v8;

namespace {

bool fault(internal::SQLiteBlockFaultPoint point,
           internal::Connection& connection) {
  return internal::invoke_sqlite_block_fault(point, connection.get());
}

}  // namespace
static_assert(std::is_nothrow_move_constructible_v<SQLiteLedgerV8>);
static_assert(std::is_nothrow_destructible_v<SQLiteLedgerV8>);

SQLiteLedgerV8::SQLiteLedgerV8(std::unique_ptr<Impl> implementation) noexcept
    : implementation_(std::move(implementation)) {}

SQLiteLedgerV8::~SQLiteLedgerV8() noexcept = default;
SQLiteLedgerV8::SQLiteLedgerV8(SQLiteLedgerV8&&) noexcept = default;

SQLiteV8HeadResult SQLiteLedgerV8::read_head() const {
  const std::lock_guard<std::mutex> lock(implementation_->mutex);
  if (implementation_->poisoned) {
    return SQLiteV8HeadResult(std::in_place_type<SQLiteLedgerV8Error>,
                              SQLiteLedgerV8Error::storage_failure);
  }
  return SQLiteV8HeadResult(
      std::in_place_type<LedgerHeadV8>,
      LedgerHeadV8{implementation_->ledger, implementation_->state_root});
}

SQLiteV8SnapshotResult SQLiteLedgerV8::create_snapshot() const {
  const std::lock_guard<std::mutex> lock(implementation_->mutex);
  if (implementation_->poisoned) {
    return SQLiteV8SnapshotResult(std::in_place_type<SQLiteLedgerV8Error>,
                                  SQLiteLedgerV8Error::storage_failure);
  }
  return SQLiteV8SnapshotResult(std::in_place_type<v8::Bytes>,
                                implementation_->head_snapshot);
}

v8::SignatureVerifier SQLiteLedgerV8::verifier() const {
  const std::lock_guard<std::mutex> lock(implementation_->mutex);
  return implementation_->verify;
}

SQLiteV8BlockResult SQLiteLedgerV8::apply_block(
    std::uint64_t height, std::span<const v8::Bytes> raw_transactions) {
  const std::lock_guard<std::mutex> lock(implementation_->mutex);
  auto& state = *implementation_;
  if (state.poisoned) {
    return SQLiteV8BlockResult(std::in_place_type<SQLiteLedgerV8Error>,
                               SQLiteLedgerV8Error::storage_failure);
  }
  // The kernel advances a ledger from `h` to `h + 1` and does not take a target
  // height, so a caller naming any other height is naming a block this chain
  // cannot be at. Refusing it here keeps the store's contract explicit rather
  // than making the caller infer the next height.
  if (height != state.ledger.height + 1) {
    return SQLiteV8BlockResult(std::in_place_type<BlockRejectedV8>,
                               BlockRejectedV8{});
  }

  // The candidate is a copy, so a rejected block never touches the live head.
  // **Under version eight the copy is never wasted work.** A version-seven
  // block with no transactions left the state exactly where it found it unless
  // its prologue opened a window; a version-eight block audits every in-scope
  // seat and resolves the audits due, so a copy is taken and a new head written
  // at every height a seat is in scope.
  v8::Ledger candidate = state.ledger;
  auto executed =
      v8::execute_block(candidate, raw_transactions, state.verify);
  if (!executed) {
    return SQLiteV8BlockResult(std::in_place_type<BlockRejectedV8>,
                               BlockRejectedV8{});
  }

  // Every figure here is the kernel's own. The transaction root in particular is
  // taken from the outcome rather than re-derived from the executed identifiers:
  // the header already commits to one, and a store that computed its own would
  // be a second opinion about the block it is recording.
  BlockCommitV8 commit;
  commit.height = executed->height;
  commit.previous_state_root = executed->previous_state_root;
  commit.resulting_state_root = executed->resulting_state_root;
  commit.transaction_root = executed->transaction_root;
  commit.block_id = executed->block_id;
  commit.transaction_count =
      static_cast<std::uint32_t>(executed->executed.size());

  // The payload is built before the write path is entered, because a state that
  // cannot be encoded is a refusal rather than a poisoning: nothing was written,
  // and the durable and live heads are both the state they already were.
  internal::DurableHeadV8 durable;
  try {
    durable = durable_head_of(candidate);
  } catch (const FailureV8& failure) {
    return SQLiteV8BlockResult(std::in_place_type<SQLiteLedgerV8Error>,
                               failure.error);
  } catch (...) {
    return SQLiteV8BlockResult(std::in_place_type<SQLiteLedgerV8Error>,
                               SQLiteLedgerV8Error::storage_failure);
  }

  // **Everything up to the commit rolls back and writes nothing.** A failure
  // there is an ordinary refusal: the transaction is abandoned, the durable head
  // is the one it already was, and the store keeps working. Only the commit
  // itself can leave a head this process cannot name.
  try {
    auto& connection = state.resources->connection;
    internal::verify_stable_path(*state.resources, state.path);
    if (fault(internal::SQLiteBlockFaultPoint::before_transaction, connection)) {
      throw FailureV8{SQLiteLedgerV8Error::storage_failure};
    }
    internal::begin_exclusive(connection);
    try {
      if (fault(internal::SQLiteBlockFaultPoint::after_transaction_begin,
                connection)) {
        throw FailureV8{SQLiteLedgerV8Error::storage_failure};
      }
      internal::persist_block_v8(connection, durable, commit, executed->header);
      if (fault(internal::SQLiteBlockFaultPoint::after_persistence, connection)) {
        throw FailureV8{SQLiteLedgerV8Error::storage_failure};
      }
      internal::verify_stable_path(*state.resources, state.path);
      if (fault(internal::SQLiteBlockFaultPoint::before_commit, connection)) {
        throw FailureV8{SQLiteLedgerV8Error::storage_failure};
      }
    } catch (...) {
      internal::rollback_or_terminate(connection);
      throw;
    }

    // From here the transaction may have landed and this process may not know.
    // Anything that goes wrong poisons the store, and recovery is an attempt to
    // stop being poisoned by reading the file again.
    auto commit_error = SQLiteLedgerV8Error::storage_failure;
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
    } catch (const FailureV8& failure) {
      commit_error = failure.error;
    } catch (const internal::Failure& failure) {
      commit_error = translate(failure.error);
    } catch (...) {
    }
    if (!published) {
      state.poisoned = true;
      (void)state.recover_durable_head();
      return SQLiteV8BlockResult(std::in_place_type<SQLiteLedgerV8Error>,
                                 commit_error);
    }

    state.ledger = std::move(candidate);
    state.state_root = durable.state_root;
    state.head_snapshot = std::move(durable.snapshot);
    (void)internal::invoke_sqlite_block_fault(
        internal::SQLiteBlockFaultPoint::after_publication, connection.get());
  } catch (const FailureV8& failure) {
    return SQLiteV8BlockResult(std::in_place_type<SQLiteLedgerV8Error>,
                               failure.error);
  } catch (const internal::Failure& failure) {
    return SQLiteV8BlockResult(std::in_place_type<SQLiteLedgerV8Error>,
                               translate(failure.error));
  } catch (...) {
    return SQLiteV8BlockResult(std::in_place_type<SQLiteLedgerV8Error>,
                               SQLiteLedgerV8Error::storage_failure);
  }
  return SQLiteV8BlockResult(std::in_place_type<BlockCommitV8>, commit);
}

}  // namespace protocol::storage
