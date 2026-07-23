#pragma once

#include "protocol/v1/types.hpp"

#include <cstdint>
#include <optional>
#include <span>
#include <variant>
#include <vector>

namespace protocol::v1 {

enum class LedgerRestoreError : std::uint8_t {
  invalid_state = 1,
  immutable_parameters_mismatch = 2,
  state_root_mismatch = 3,
};

enum class BlockError : std::uint8_t {
  invalid_state = 1,
  height_exhausted = 2,
  invalid_height = 3,
  too_many_inputs = 4,
  invariant_failure = 5,
};

struct BlockCommit {
  std::uint64_t height;
  std::vector<std::optional<AdmissionError>> admissions;
  std::vector<TransactionId> transaction_ids;
  std::vector<Receipt> receipts;
  std::vector<Bytes> encoded_receipts;
  StateRoot previous_state_root;
  TransactionRoot transaction_root;
  StateRoot resulting_state_root;
  Bytes header;
  BlockId block_id;
};

struct LedgerLoad;
struct LedgerRestore;

class Ledger {
 public:
  Ledger(const Ledger&) = default;
  Ledger(Ledger&&) noexcept = default;
  Ledger& operator=(const Ledger&) = delete;
  Ledger& operator=(Ledger&&) = delete;

  const State& state() const noexcept { return state_; }

  std::variant<StateRoot, BlockError> current_state_root() const;

  std::variant<BlockCommit, BlockError> apply_block(
      std::uint64_t height,
      std::span<const Bytes> raw_transactions);

 private:
  explicit Ledger(State state) noexcept;

  friend LedgerLoad load_genesis(
      std::span<const std::uint8_t> canonical_genesis);
  friend LedgerRestore restore_ledger(
      State state,
      const Parameters& expected_parameters,
      const StateRoot& expected_state_root);

  State state_;
};

struct LedgerLoad {
  std::variant<Ledger, GenesisError> result;
};

struct LedgerRestore {
  std::variant<Ledger, LedgerRestoreError> result;
};

LedgerLoad load_genesis(
    std::span<const std::uint8_t> canonical_genesis);

LedgerRestore restore_ledger(
    State state,
    const Parameters& expected_parameters,
    const StateRoot& expected_state_root);

}  // namespace protocol::v1
