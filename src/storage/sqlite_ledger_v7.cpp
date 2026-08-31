// The version-seven owning store.
//
// `apply_block` executes against a *candidate* copy of the head and commits only
// what the kernel accepted, so a rejected block and a failed write leave the
// durable head and the live head identically untouched. That is the same shape
// version one's store has, and it is what makes "the head is what some sequence
// of blocks produced" true of the file rather than only of the process.
//
// **Reopening is where the validation lives and none of it is here.**
// `sqlite_ledger_v7_open.cpp` holds it, because a store is validated once and
// then trusted for its lifetime.

#include "protocol/storage/sqlite_ledger_v7.hpp"

#include "sqlite_ledger_v7_internal.hpp"

#include <memory>
#include <mutex>
#include <type_traits>
#include <utility>
#include <variant>

namespace protocol::storage {

using namespace internal_v7;

namespace {

bool fault(internal::SQLiteBlockFaultPoint point,
           internal::Connection& connection) {
  return internal::invoke_sqlite_block_fault(point, connection.get());
}

}  // namespace
static_assert(std::is_nothrow_move_constructible_v<SQLiteLedgerV7>);
static_assert(std::is_nothrow_destructible_v<SQLiteLedgerV7>);

SQLiteLedgerV7::SQLiteLedgerV7(std::unique_ptr<Impl> implementation) noexcept
    : implementation_(std::move(implementation)) {}

SQLiteLedgerV7::~SQLiteLedgerV7() noexcept = default;
SQLiteLedgerV7::SQLiteLedgerV7(SQLiteLedgerV7&&) noexcept = default;

SQLiteV7HeadResult SQLiteLedgerV7::read_head() const {
  const std::lock_guard<std::mutex> lock(implementation_->mutex);
  if (implementation_->poisoned) {
    return SQLiteV7HeadResult(std::in_place_type<SQLiteLedgerV7Error>,
                              SQLiteLedgerV7Error::storage_failure);
  }
  return SQLiteV7HeadResult(
      std::in_place_type<LedgerHeadV7>,
      LedgerHeadV7{implementation_->ledger, implementation_->state_root});
}

SQLiteV7SnapshotResult SQLiteLedgerV7::create_snapshot() const {
  const std::lock_guard<std::mutex> lock(implementation_->mutex);
  if (implementation_->poisoned) {
    return SQLiteV7SnapshotResult(std::in_place_type<SQLiteLedgerV7Error>,
                                  SQLiteLedgerV7Error::storage_failure);
  }
  return SQLiteV7SnapshotResult(std::in_place_type<v7::Bytes>,
                                implementation_->head_snapshot);
}

v7::SignatureVerifier SQLiteLedgerV7::verifier() const {
  const std::lock_guard<std::mutex> lock(implementation_->mutex);
  return implementation_->verify;
}

SQLiteV7BlockResult SQLiteLedgerV7::apply_block(
    std::uint64_t height, std::span<const v7::Bytes> raw_transactions,
    const v7::UptimeSchedule* uptime) {
  const std::lock_guard<std::mutex> lock(implementation_->mutex);
  auto& state = *implementation_;
  if (state.poisoned) {
    return SQLiteV7BlockResult(std::in_place_type<SQLiteLedgerV7Error>,
                               SQLiteLedgerV7Error::storage_failure);
  }
  // The kernel advances a ledger from `h` to `h + 1` and does not take a target
  // height, so a caller naming any other height is naming a block this chain
  // cannot be at. Refusing it here keeps the store's contract explicit rather
  // than making the caller infer the next height.
  if (height != state.ledger.height + 1) {
    return SQLiteV7BlockResult(std::in_place_type<BlockRejectedV7>,
                               BlockRejectedV7{});
  }

  // The candidate is a copy, so a rejected block never touches the live head.
  v7::Ledger candidate = state.ledger;
  auto executed =
      v7::execute_block(candidate, raw_transactions, state.verify, uptime);
  if (!executed) {
    return SQLiteV7BlockResult(std::in_place_type<BlockRejectedV7>,
                               BlockRejectedV7{});
  }

  // Every figure here is the kernel's own. The transaction root in particular is
  // taken from the outcome rather than re-derived from the executed identifiers:
  // the header already commits to one, and a store that computed its own would
  // be a second opinion about the block it is recording.
  BlockCommitV7 commit;
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
  internal::DurableHeadV7 durable;
  try {
    durable = durable_head_of(candidate);
  } catch (const FailureV7& failure) {
    return SQLiteV7BlockResult(std::in_place_type<SQLiteLedgerV7Error>,
                               failure.error);
  } catch (...) {
    return SQLiteV7BlockResult(std::in_place_type<SQLiteLedgerV7Error>,
                               SQLiteLedgerV7Error::storage_failure);
  }

  // **Everything up to the commit rolls back and writes nothing.** A failure
  // there is an ordinary refusal: the transaction is abandoned, the durable head
  // is the one it already was, and the store keeps working. Only the commit
  // itself can leave a head this process cannot name.
  try {
    auto& connection = state.resources->connection;
    internal::verify_stable_path(*state.resources, state.path);
    if (fault(internal::SQLiteBlockFaultPoint::before_transaction, connection)) {
      throw FailureV7{SQLiteLedgerV7Error::storage_failure};
    }
    internal::begin_exclusive(connection);
    try {
      if (fault(internal::SQLiteBlockFaultPoint::after_transaction_begin,
                connection)) {
        throw FailureV7{SQLiteLedgerV7Error::storage_failure};
      }
      internal::persist_block_v7(connection, durable, commit, executed->header);
      if (fault(internal::SQLiteBlockFaultPoint::after_persistence, connection)) {
        throw FailureV7{SQLiteLedgerV7Error::storage_failure};
      }
      internal::verify_stable_path(*state.resources, state.path);
      if (fault(internal::SQLiteBlockFaultPoint::before_commit, connection)) {
        throw FailureV7{SQLiteLedgerV7Error::storage_failure};
      }
    } catch (...) {
      internal::rollback_or_terminate(connection);
      throw;
    }

    // From here the transaction may have landed and this process may not know.
    // Anything that goes wrong poisons the store, and recovery is an attempt to
    // stop being poisoned by reading the file again.
    auto commit_error = SQLiteLedgerV7Error::storage_failure;
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
    } catch (const FailureV7& failure) {
      commit_error = failure.error;
    } catch (const internal::Failure& failure) {
      commit_error = translate(failure.error);
    } catch (...) {
    }
    if (!published) {
      state.poisoned = true;
      (void)state.recover_durable_head();
      return SQLiteV7BlockResult(std::in_place_type<SQLiteLedgerV7Error>,
                                 commit_error);
    }

    state.ledger = std::move(candidate);
    state.state_root = durable.state_root;
    state.head_snapshot = std::move(durable.snapshot);
    (void)internal::invoke_sqlite_block_fault(
        internal::SQLiteBlockFaultPoint::after_publication, connection.get());
  } catch (const FailureV7& failure) {
    return SQLiteV7BlockResult(std::in_place_type<SQLiteLedgerV7Error>,
                               failure.error);
  } catch (const internal::Failure& failure) {
    return SQLiteV7BlockResult(std::in_place_type<SQLiteLedgerV7Error>,
                               translate(failure.error));
  } catch (...) {
    return SQLiteV7BlockResult(std::in_place_type<SQLiteLedgerV7Error>,
                               SQLiteLedgerV7Error::storage_failure);
  }
  return SQLiteV7BlockResult(std::in_place_type<BlockCommitV7>, commit);
}

}  // namespace protocol::storage
