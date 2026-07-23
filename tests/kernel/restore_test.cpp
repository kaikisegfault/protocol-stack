#include "protocol/v1/ledger.hpp"

#include "../../src/v1/commitments.hpp"
#include "../../tools/protocol-vectors/vector_common.hpp"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <iterator>
#include <limits>
#include <string>
#include <string_view>
#include <utility>
#include <variant>
#include <vector>

namespace pv = protocol_vectors;
namespace p = protocol::v1;

namespace {

template <typename Tagged>
Tagged tagged_hash(const pv::Bytes& bytes) {
  pv::require(bytes.size() == 32, "tagged hash size");
  p::Hash value{};
  std::copy(bytes.begin(), bytes.end(), value.begin());
  return Tagged{value};
}

p::Ledger load_ledger(const pv::Values& values) {
  auto loaded = p::load_genesis(pv::hex_decode(values.at("genesis")));
  pv::require(std::holds_alternative<p::Ledger>(loaded.result),
              "expected loaded ledger");
  return std::get<p::Ledger>(std::move(loaded.result));
}

p::StateRoot state_root(const p::State& state) {
  auto commitment = p::internal::state_root(state);
  pv::require(std::holds_alternative<p::StateRoot>(commitment),
              "expected valid state");
  return std::get<p::StateRoot>(std::move(commitment));
}

p::Ledger restore(p::State state, const p::Parameters& parameters,
                  const p::StateRoot& root, std::string_view message) {
  auto restored = p::restore_ledger(std::move(state), parameters, root);
  pv::require(std::holds_alternative<p::Ledger>(restored.result), message);
  return std::get<p::Ledger>(std::move(restored.result));
}

void require_restore_error(p::State state,
                           const p::Parameters& parameters,
                           const p::StateRoot& root,
                           p::LedgerRestoreError expected,
                           std::string_view message) {
  const auto restored =
      p::restore_ledger(std::move(state), parameters, root);
  pv::require(
      std::holds_alternative<p::LedgerRestoreError>(restored.result) &&
          std::get<p::LedgerRestoreError>(restored.result) == expected,
      message);
}

std::vector<p::Bytes> transactions(const pv::Values& values) {
  const auto count = std::stoull(values.at("raw_count"));
  std::vector<p::Bytes> result;
  result.reserve(count);
  for (std::size_t index = 0; index < count; ++index) {
    result.push_back(pv::hex_decode(values.at("raw" + std::to_string(index))));
  }
  return result;
}

p::BlockCommit commit(p::Ledger& ledger, std::uint64_t height,
                      const std::vector<p::Bytes>& raw,
                      std::string_view message) {
  auto applied = ledger.apply_block(height, raw);
  pv::require(std::holds_alternative<p::BlockCommit>(applied), message);
  return std::get<p::BlockCommit>(std::move(applied));
}

bool same_commit(const p::BlockCommit& left, const p::BlockCommit& right) {
  return left.height == right.height &&
         left.admissions == right.admissions &&
         left.transaction_ids == right.transaction_ids &&
         left.receipts == right.receipts &&
         left.encoded_receipts == right.encoded_receipts &&
         left.previous_state_root == right.previous_state_root &&
         left.transaction_root == right.transaction_root &&
         left.resulting_state_root == right.resulting_state_root &&
         left.header == right.header && left.block_id == right.block_id;
}

void verify_success_and_replay(const pv::Values& values) {
  auto ordinary = load_ledger(values);
  const auto genesis = ordinary.state();
  const auto trusted_parameters = genesis.parameters;
  const auto genesis_root = state_root(genesis);
  pv::require(
      genesis_root ==
          tagged_hash<p::StateRoot>(
              pv::hex_decode(values.at("previous_state_root"))),
      "frozen genesis root");

  auto restored_genesis =
      restore(genesis, trusted_parameters, genesis_root,
              "genesis restoration rejected");
  pv::require(restored_genesis.state() == genesis,
              "genesis restoration changed state");

  const auto raw = transactions(values);
  const auto ordinary_commit =
      commit(ordinary, 1, raw, "ordinary frozen block rejected");
  const auto restored_commit =
      commit(restored_genesis, 1, raw, "restored frozen block rejected");
  pv::require(same_commit(ordinary_commit, restored_commit) &&
                  ordinary.state() == restored_genesis.state(),
              "restored block diverged");
  pv::require(
      ordinary_commit.resulting_state_root ==
              tagged_hash<p::StateRoot>(
                  pv::hex_decode(values.at("resulting_state_root"))) &&
          ordinary_commit.transaction_root ==
              tagged_hash<p::TransactionRoot>(
                  pv::hex_decode(values.at("transaction_root"))) &&
          ordinary_commit.block_id ==
              tagged_hash<p::BlockId>(
                  pv::hex_decode(values.at("block_id"))) &&
          ordinary_commit.header ==
              pv::hex_decode(values.at("block_header")),
      "frozen block commitments");

  auto resumed =
      restore(ordinary.state(), trusted_parameters,
              ordinary_commit.resulting_state_root,
              "nonzero-height restoration rejected");
  pv::require(resumed.state() == ordinary.state(),
              "nonzero-height restoration changed state");

  const std::vector<p::Bytes> empty;
  const auto ordinary_empty =
      commit(ordinary, 2, empty, "ordinary empty block rejected");
  const auto resumed_empty =
      commit(resumed, 2, empty, "resumed empty block rejected");
  pv::require(same_commit(ordinary_empty, resumed_empty) &&
                  ordinary.state() == resumed.state(),
              "next empty block diverged after restoration");
}

void verify_state_ownership(const pv::Values& values) {
  const auto loaded = load_ledger(values);
  const auto original = loaded.state();
  const auto parameters = original.parameters;
  const auto root = state_root(original);

  auto lvalue_source = original;
  auto copied_result = p::restore_ledger(lvalue_source, parameters, root);
  pv::require(std::holds_alternative<p::Ledger>(copied_result.result),
              "lvalue restore rejected");
  auto copied = std::get<p::Ledger>(std::move(copied_result.result));
  pv::require(lvalue_source == original, "lvalue source was consumed");
  lvalue_source.accounts.clear();
  ++lvalue_source.height;
  pv::require(copied.state() == original,
              "restored ledger borrowed lvalue state");
  auto rvalue_source = original;
  auto owned = restore(std::move(rvalue_source), parameters, root,
                       "rvalue restore rejected");
  rvalue_source = p::State{};
  pv::require(owned.state() == original,
              "restored ledger did not own rvalue state");
}

void verify_live_account_shape(const pv::Values& values) {
  auto state = load_ledger(values).state();
  pv::require(state.accounts.size() >= 2, "fixture account count");
  auto first = state.accounts.begin();
  auto second = std::next(first);
  const auto transferred = first->second.balance;
  first->second = p::Account{0, 7};
  second->second.balance += transferred;
  const auto root = state_root(state);
  auto restored = restore(state, state.parameters, root,
                          "zero-balance live account rejected");
  pv::require(restored.state() == state &&
                  restored.state().accounts.begin()->second ==
                      p::Account{0, 7},
              "zero-balance live account changed");
}

void verify_invalid_states(const pv::Values& values) {
  const auto base = load_ledger(values).state();
  const p::StateRoot unused_root{};
  auto require_invalid = [&](p::State state, std::string_view message) {
    const auto parameters = state.parameters;
    require_restore_error(std::move(state), parameters, unused_root,
                          p::LedgerRestoreError::invalid_state, message);
  };

  auto zero_limit = base;
  zero_limit.parameters.supply_limit = 0;
  require_invalid(std::move(zero_limit), "zero supply limit accepted");

  auto zero_fee = base;
  zero_fee.parameters.fixed_fee = 0;
  require_invalid(std::move(zero_fee), "zero fixed fee accepted");

  auto limit_violation = base;
  limit_violation.parameters.supply_limit =
      limit_violation.parameters.total_supply - 1;
  require_invalid(std::move(limit_violation),
                  "supply limit violation accepted");

  auto mismatch = base;
  --mismatch.parameters.total_supply;
  require_invalid(std::move(mismatch), "supply mismatch accepted");

  auto overflow = base;
  overflow.parameters.supply_limit =
      std::numeric_limits<std::uint64_t>::max();
  overflow.parameters.total_supply =
      std::numeric_limits<std::uint64_t>::max();
  overflow.fee_pool = std::numeric_limits<std::uint64_t>::max();
  overflow.accounts.clear();
  overflow.accounts.emplace(base.accounts.begin()->first, p::Account{1, 0});
  require_invalid(std::move(overflow), "supply overflow accepted");
}

void verify_bindings_and_precedence(const pv::Values& values) {
  const auto state = load_ledger(values).state();
  const auto parameters = state.parameters;
  const auto root = state_root(state);
  auto wrong_root = root;
  *wrong_root.begin() ^= 1U;
  auto mismatch = parameters;
  *mismatch.chain_id.begin() ^= 1U;
  require_restore_error(state, mismatch, root,
                        p::LedgerRestoreError::immutable_parameters_mismatch,
                        "chain ID mismatch accepted");
  mismatch = parameters;
  ++mismatch.supply_limit;
  require_restore_error(state, mismatch, root,
                        p::LedgerRestoreError::immutable_parameters_mismatch,
                        "supply limit mismatch accepted");
  mismatch = parameters;
  ++mismatch.total_supply;
  require_restore_error(state, mismatch, root,
                        p::LedgerRestoreError::immutable_parameters_mismatch,
                        "total supply mismatch accepted");

  auto changed_fee = state;
  ++changed_fee.parameters.fixed_fee;
  pv::require(state_root(changed_fee) == root,
              "fixed fee unexpectedly changed state root");
  require_restore_error(
      changed_fee, parameters, root,
      p::LedgerRestoreError::immutable_parameters_mismatch,
      "fixed fee mismatch accepted despite unchanged root");

  require_restore_error(state, parameters, wrong_root,
                        p::LedgerRestoreError::state_root_mismatch,
                        "wrong state root accepted");
  auto stale = state;
  ++stale.height;
  pv::require(state_root(stale) != root, "covered mutation kept state root");
  require_restore_error(stale, parameters, root,
                        p::LedgerRestoreError::state_root_mismatch,
                        "stale state root accepted");

  auto invalid = state;
  invalid.parameters.fixed_fee = 0;
  require_restore_error(
      invalid, mismatch, wrong_root, p::LedgerRestoreError::invalid_state,
      "invalid-state precedence");
  require_restore_error(
      state, mismatch, wrong_root,
      p::LedgerRestoreError::immutable_parameters_mismatch,
      "parameter-mismatch precedence");
}

}  // namespace

int main(int argc, char** argv) {
  try {
    pv::require(argc == 2, "usage: kernel_restore_test VECTOR_FILE");
    pv::require(sodium_init() >= 0, "libsodium initialization");
    const auto values = pv::load_values(argv[1]);
    verify_success_and_replay(values);
    verify_state_ownership(values);
    verify_live_account_shape(values);
    verify_invalid_states(values);
    verify_bindings_and_precedence(values);
    std::cout << "Kernel restore tests: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "Kernel restore tests: failed: " << error.what() << '\n';
    return 1;
  }
}
