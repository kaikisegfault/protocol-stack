#pragma once

#include "protocol/v1/ledger.hpp"

#include <cstdint>
#include <filesystem>
#include <memory>
#include <span>
#include <variant>

namespace protocol::storage {

enum class SQLiteLedgerError : std::uint8_t {
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
};

struct LedgerHead {
  protocol::v1::State state;
  protocol::v1::StateRoot state_root;

  bool operator==(const LedgerHead&) const = default;
};

struct SQLiteLedgerResult;

using SQLiteBlockResult = std::variant<
    protocol::v1::BlockCommit,
    protocol::v1::BlockError,
    SQLiteLedgerError>;

class SQLiteLedger {
 public:
  ~SQLiteLedger() noexcept;
  SQLiteLedger(SQLiteLedger&&) noexcept;

  SQLiteLedger(const SQLiteLedger&) = delete;
  SQLiteLedger& operator=(const SQLiteLedger&) = delete;
  SQLiteLedger& operator=(SQLiteLedger&&) = delete;

  LedgerHead read_head() const;
  SQLiteBlockResult apply_block(
      std::uint64_t height,
      std::span<const protocol::v1::Bytes> raw_transactions);

 private:
  struct Impl;

  explicit SQLiteLedger(
      std::unique_ptr<Impl> implementation) noexcept;

  friend SQLiteLedgerResult create_sqlite_ledger(
      const std::filesystem::path& path,
      std::span<const std::uint8_t> canonical_genesis);
  friend SQLiteLedgerResult open_sqlite_ledger(
      const std::filesystem::path& path,
      std::span<const std::uint8_t> canonical_genesis);

  std::unique_ptr<Impl> implementation_;
};

struct SQLiteLedgerResult {
  std::variant<SQLiteLedger, SQLiteLedgerError> result;
};

SQLiteLedgerResult create_sqlite_ledger(
    const std::filesystem::path& path,
    std::span<const std::uint8_t> canonical_genesis);

SQLiteLedgerResult open_sqlite_ledger(
    const std::filesystem::path& path,
    std::span<const std::uint8_t> canonical_genesis);

}  // namespace protocol::storage
