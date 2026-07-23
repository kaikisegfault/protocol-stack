#include "protocol/v1/admission.hpp"
#include "protocol/v1/ledger.hpp"

#include "../../src/v1/execution.hpp"
#include "../../tools/protocol-vectors/vector_common.hpp"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <iterator>
#include <limits>
#include <optional>
#include <string>
#include <string_view>
#include <utility>
#include <variant>
#include <vector>

namespace pv = protocol_vectors;
namespace p = protocol::v1;

namespace {

template <typename Tagged>
Tagged tagged_hash(const pv::Bytes& bytes, std::size_t offset = 0) {
  pv::require(offset + 32 <= bytes.size(), "tagged hash size");
  p::Hash raw{};
  std::copy_n(bytes.begin() + offset, raw.size(), raw.begin());
  return Tagged{raw};
}

template <typename Tagged>
void append_hash(pv::Bytes& target, const Tagged& value) {
  target.insert(target.end(), value.begin(), value.end());
}

std::vector<p::Bytes> raw_transactions(const pv::Values& values) {
  const auto count = std::stoull(values.at("raw_count"));
  std::vector<p::Bytes> result;
  result.reserve(count);
  for (std::size_t index = 0; index < count; ++index) {
    result.push_back(
        pv::hex_decode(values.at("raw" + std::to_string(index))));
  }
  return result;
}

p::Ledger load_ledger(const p::Bytes& genesis) {
  auto loaded = p::load_genesis(genesis);
  pv::require(std::holds_alternative<p::Ledger>(loaded.result),
              "expected loaded ledger");
  return std::get<p::Ledger>(std::move(loaded.result));
}

p::Ledger load_frozen_ledger(const pv::Values& values) {
  return load_ledger(pv::hex_decode(values.at("genesis")));
}

void require_genesis_error(const p::Bytes& genesis,
                           p::GenesisError expected,
                           std::string_view message) {
  const auto loaded = p::load_genesis(genesis);
  pv::require(std::holds_alternative<p::GenesisError>(loaded.result),
              message);
  pv::require(std::get<p::GenesisError>(loaded.result) == expected,
              message);
}

p::StateRoot require_current_root(const p::Ledger& ledger) {
  const auto root = ledger.current_state_root();
  pv::require(std::holds_alternative<p::StateRoot>(root),
              "expected current state root");
  return std::get<p::StateRoot>(root);
}

p::BlockCommit require_commit(p::Ledger& ledger, std::uint64_t height,
                              const std::vector<p::Bytes>& transactions,
                              std::string_view message) {
  auto result = ledger.apply_block(height, transactions);
  pv::require(std::holds_alternative<p::BlockCommit>(result), message);
  return std::get<p::BlockCommit>(std::move(result));
}

void require_block_error(p::Ledger& ledger, std::uint64_t height,
                         const std::vector<p::Bytes>& transactions,
                         p::BlockError expected,
                         std::string_view message) {
  const auto before = ledger.state();
  const auto result = ledger.apply_block(height, transactions);
  pv::require(std::holds_alternative<p::BlockError>(result), message);
  pv::require(std::get<p::BlockError>(result) == expected, message);
  pv::require(ledger.state() == before, "block rejection atomicity");
}

pv::Bytes account_entry(const p::AccountId& identifier,
                        const p::Account& account) {
  pv::Bytes encoded;
  append_hash(encoded, identifier);
  pv::append_u64(encoded, account.balance);
  pv::append_u64(encoded, account.nonce);
  return encoded;
}

void verify_frozen_state(const p::State& state,
                         const pv::Values& values) {
  pv::require(state.height == 1, "frozen resulting height");
  pv::require(state.fee_pool == std::stoull(values.at("fee_pool")),
              "frozen resulting fee pool");
  pv::require(state.accounts.size() ==
                  std::stoull(values.at("final_account_count")),
              "frozen resulting account count");
  std::size_t index = 0;
  for (const auto& [identifier, account] : state.accounts) {
    pv::require(
        account_entry(identifier, account) ==
            pv::hex_decode(
                values.at("final.account" + std::to_string(index))),
        "frozen resulting account");
    ++index;
  }
}

void verify_frozen_block(const pv::Values& values) {
  auto ledger = load_frozen_ledger(values);
  const auto expected_previous =
      tagged_hash<p::StateRoot>(
          pv::hex_decode(values.at("previous_state_root")));
  pv::require(require_current_root(ledger) == expected_previous,
              "public genesis state root");

  const auto transactions = raw_transactions(values);
  const auto commit =
      require_commit(ledger, 1, transactions, "frozen block rejected");
  pv::require(commit.height == 1, "frozen block height");
  pv::require(commit.admissions.size() == transactions.size(),
              "raw-aligned admission count");

  std::size_t admitted_index = 0;
  for (std::size_t raw_index = 0; raw_index < transactions.size();
       ++raw_index) {
    const auto raw_key = "raw" + std::to_string(raw_index);
    const auto expected_admission =
        std::stoull(values.at(raw_key + ".admission"));
    if (expected_admission != 0) {
      pv::require(
          commit.admissions[raw_index] ==
              std::optional<p::AdmissionError>(
                  static_cast<p::AdmissionError>(expected_admission)),
          "raw-order admission error");
      continue;
    }
    pv::require(!commit.admissions[raw_index],
                "raw-order admitted marker");
    const auto receipt_key =
        "receipt" + std::to_string(admitted_index);
    const auto expected_receipt =
        pv::hex_decode(values.at(receipt_key));
    const auto expected_id =
        tagged_hash<p::TransactionId>(expected_receipt, 6);
    pv::require(commit.transaction_ids[admitted_index] == expected_id,
                "admitted-order transaction ID");
    pv::require(
        commit.receipts[admitted_index] ==
            p::Receipt{
                expected_id,
                static_cast<p::TransferResult>(expected_receipt[38]),
                pv::read_u64(expected_receipt, 39),
            },
        "admitted-order typed receipt");
    pv::require(commit.encoded_receipts[admitted_index] ==
                    expected_receipt,
                "admitted-order encoded receipt");
    ++admitted_index;
  }
  const auto expected_admitted =
      std::stoull(values.at("admitted_count"));
  pv::require(admitted_index == expected_admitted,
              "frozen admitted count");
  pv::require(commit.transaction_ids.size() == expected_admitted &&
                  commit.receipts.size() == expected_admitted &&
                  commit.encoded_receipts.size() == expected_admitted,
              "admitted output alignment");

  const auto expected_transaction_root =
      tagged_hash<p::TransactionRoot>(
          pv::hex_decode(values.at("transaction_root")));
  const auto expected_resulting =
      tagged_hash<p::StateRoot>(
          pv::hex_decode(values.at("resulting_state_root")));
  pv::require(commit.previous_state_root == expected_previous,
              "frozen previous state root");
  pv::require(commit.transaction_root == expected_transaction_root,
              "frozen transaction root");
  pv::require(commit.resulting_state_root == expected_resulting,
              "frozen resulting state root");
  pv::require(commit.header ==
                  pv::hex_decode(values.at("block_header")),
              "frozen block header");
  pv::require(
      commit.block_id ==
          tagged_hash<p::BlockId>(pv::hex_decode(values.at("block_id"))),
      "frozen block ID");
  pv::require(require_current_root(ledger) == expected_resulting,
              "public committed state root");
  verify_frozen_state(ledger.state(), values);
}

void zero_u64(p::Bytes& bytes, std::size_t offset) {
  std::fill_n(bytes.begin() + offset, 8, 0);
}

void verify_public_genesis_errors(const pv::Values& values) {
  const auto frozen = pv::hex_decode(values.at("genesis"));

  auto malformed = frozen;
  malformed.pop_back();
  require_genesis_error(malformed, p::GenesisError::malformed,
                        "public malformed genesis");

  auto unsupported = frozen;
  unsupported[9] = 2;
  require_genesis_error(unsupported,
                        p::GenesisError::unsupported_network,
                        "public unsupported network");

  auto invalid_parameters = frozen;
  zero_u64(invalid_parameters, 26);
  require_genesis_error(invalid_parameters,
                        p::GenesisError::invalid_parameters,
                        "public invalid parameters");

  auto invalid_accounts = frozen;
  zero_u64(invalid_accounts, 46 + 32);
  require_genesis_error(invalid_accounts,
                        p::GenesisError::invalid_accounts,
                        "public invalid accounts");

  auto invalid_supply = frozen;
  invalid_supply[46 + 39] ^= 1U;
  require_genesis_error(invalid_supply,
                        p::GenesisError::invalid_supply,
                        "public invalid supply");
}

void verify_block_boundaries(const pv::Values& values) {
  const std::vector<p::Bytes> no_transactions;

  auto invalid_height = load_frozen_ledger(values);
  const auto invalid_height_root = require_current_root(invalid_height);
  require_block_error(invalid_height, 0, no_transactions,
                      p::BlockError::invalid_height,
                      "current height accepted");
  require_block_error(invalid_height, 2, no_transactions,
                      p::BlockError::invalid_height,
                      "skipped height accepted");
  pv::require(require_current_root(invalid_height) == invalid_height_root,
              "invalid height root atomicity");

  auto exhausted = load_frozen_ledger(values);
  auto& exhausted_state = const_cast<p::State&>(exhausted.state());
  exhausted_state.height = std::numeric_limits<std::uint64_t>::max();
  require_block_error(exhausted,
                      std::numeric_limits<std::uint64_t>::max(),
                      no_transactions, p::BlockError::height_exhausted,
                      "height exhaustion not rejected");

  auto invalid_state = load_frozen_ledger(values);
  auto& corrupted = const_cast<p::State&>(invalid_state.state());
  --corrupted.parameters.total_supply;
  const auto invalid_root = invalid_state.current_state_root();
  pv::require(std::holds_alternative<p::BlockError>(invalid_root) &&
                  std::get<p::BlockError>(invalid_root) ==
                      p::BlockError::invalid_state,
              "invalid current state root");
  require_block_error(invalid_state, 1, no_transactions,
                      p::BlockError::invalid_state,
                      "invalid state not rejected");

  auto too_many_ledger = load_frozen_ledger(values);
  const std::vector<p::Bytes> too_many(65'536);
  require_block_error(too_many_ledger, 1, too_many,
                      p::BlockError::too_many_inputs,
                      "oversized input list accepted");

  auto maximum_ledger = load_frozen_ledger(values);
  const std::vector<p::Bytes> maximum(65'535);
  const auto maximum_commit =
      require_commit(maximum_ledger, 1, maximum,
                     "maximum input list rejected");
  pv::require(maximum_commit.admissions.size() == maximum.size(),
              "maximum admission count");
  pv::require(
      std::all_of(
          maximum_commit.admissions.begin(),
          maximum_commit.admissions.end(),
          [](const auto& error) {
            return error ==
                   std::optional<p::AdmissionError>(
                       p::AdmissionError::malformed_transaction);
          }),
      "maximum admission alignment");
  pv::require(maximum_commit.transaction_ids.empty() &&
                  maximum_commit.receipts.empty() &&
                  maximum_commit.encoded_receipts.empty(),
              "maximum malformed outputs");

  auto precedence = load_frozen_ledger(values);
  auto& precedence_state = const_cast<p::State&>(precedence.state());
  --precedence_state.parameters.total_supply;
  precedence_state.height = std::numeric_limits<std::uint64_t>::max();
  require_block_error(precedence, 0, too_many,
                      p::BlockError::too_many_inputs,
                      "input bound precedence");
  require_block_error(precedence, 0, no_transactions,
                      p::BlockError::invalid_state,
                      "invalid state precedence");

  auto height_precedence = load_frozen_ledger(values);
  auto& maximum_height =
      const_cast<p::State&>(height_precedence.state());
  maximum_height.height = std::numeric_limits<std::uint64_t>::max();
  require_block_error(height_precedence, 0, no_transactions,
                      p::BlockError::height_exhausted,
                      "height exhaustion precedence");
}

void verify_empty_and_unadmitted_blocks(const pv::Values& values) {
  const std::vector<p::Bytes> empty;
  auto empty_ledger = load_frozen_ledger(values);
  const auto empty_commit =
      require_commit(empty_ledger, 1, empty, "empty block rejected");
  pv::require(empty_commit.admissions.empty() &&
                  empty_commit.transaction_ids.empty() &&
                  empty_commit.receipts.empty() &&
                  empty_commit.encoded_receipts.empty(),
              "empty block outputs");
  pv::require(empty_ledger.state().height == 1 &&
                  empty_ledger.state().fee_pool == 0,
              "empty block height-only transition");

  const auto all_raw = raw_transactions(values);
  const std::vector<p::Bytes> unadmitted{
      p::Bytes{},
      all_raw.at(11),
      all_raw.at(13),
  };
  auto unadmitted_ledger = load_frozen_ledger(values);
  const auto unadmitted_commit =
      require_commit(unadmitted_ledger, 1, unadmitted,
                     "all-unadmitted block rejected");
  const std::vector<std::optional<p::AdmissionError>> expected{
      p::AdmissionError::malformed_transaction,
      p::AdmissionError::invalid_signature,
      p::AdmissionError::wrong_chain,
  };
  pv::require(unadmitted_commit.admissions == expected,
              "all-unadmitted raw alignment");
  pv::require(unadmitted_commit.transaction_ids.empty() &&
                  unadmitted_commit.receipts.empty() &&
                  unadmitted_commit.encoded_receipts.empty(),
              "all-unadmitted output omission");
  pv::require(unadmitted_ledger.state() == empty_ledger.state(),
              "admission failures changed state");
  pv::require(unadmitted_commit.transaction_root ==
                  empty_commit.transaction_root &&
                  unadmitted_commit.resulting_state_root ==
                      empty_commit.resulting_state_root &&
                  unadmitted_commit.header == empty_commit.header &&
                  unadmitted_commit.block_id == empty_commit.block_id,
              "admission failures changed commitments");
}

void verify_duplicates_and_ordering(const pv::Values& values) {
  const auto raw = raw_transactions(values);

  auto duplicate_ledger = load_frozen_ledger(values);
  const std::vector<p::Bytes> duplicates{raw.at(0), raw.at(0)};
  const auto duplicate_commit =
      require_commit(duplicate_ledger, 1, duplicates,
                     "duplicate block rejected");
  pv::require(duplicate_commit.admissions ==
                  std::vector<std::optional<p::AdmissionError>>(2),
              "duplicate admissions");
  pv::require(duplicate_commit.transaction_ids.size() == 2 &&
                  duplicate_commit.transaction_ids[0] ==
                      duplicate_commit.transaction_ids[1],
              "duplicate transaction IDs not retained");
  pv::require(
      duplicate_commit.encoded_receipts ==
          std::vector<p::Bytes>{
              pv::hex_decode(values.at("receipt0")),
              pv::hex_decode(values.at("receipt1")),
          },
      "duplicate ordered receipts");
  pv::require(duplicate_ledger.state().fee_pool == 1'000,
              "duplicate replay charged");

  auto forward_ledger = load_frozen_ledger(values);
  auto reverse_ledger = load_frozen_ledger(values);
  const std::vector<p::Bytes> forward{raw.at(0), raw.at(2)};
  const std::vector<p::Bytes> reverse{raw.at(2), raw.at(0)};
  const auto forward_commit =
      require_commit(forward_ledger, 1, forward,
                     "forward-order block rejected");
  const auto reverse_commit =
      require_commit(reverse_ledger, 1, reverse,
                     "reverse-order block rejected");
  pv::require(forward_commit.receipts[0].result ==
                  p::TransferResult::success &&
                  forward_commit.receipts[1].result ==
                      p::TransferResult::success,
              "forward ordered execution");
  pv::require(reverse_commit.receipts[0].result ==
                  p::TransferResult::nonce_mismatch &&
                  reverse_commit.receipts[1].result ==
                      p::TransferResult::success,
              "reverse ordered execution");
  pv::require(forward_ledger.state() != reverse_ledger.state() &&
                  forward_commit.transaction_root !=
                      reverse_commit.transaction_root &&
                  forward_commit.resulting_state_root !=
                      reverse_commit.resulting_state_root &&
                  forward_commit.block_id != reverse_commit.block_id,
              "transaction order not committed");
}

void verify_tentative_failure_atomicity(const pv::Values& values) {
  auto ledger = load_frozen_ledger(values);
  const auto original = ledger.state();
  auto tentative = original;
  const auto raw = raw_transactions(values);
  const auto admitted =
      p::admit_transfer(raw.at(0), tentative.parameters.chain_id);
  pv::require(std::holds_alternative<p::Transfer>(admitted),
              "tentative success admission");
  const auto first = p::internal::execute_transfer(
      std::get<p::Transfer>(admitted), tentative, 1);
  pv::require(std::holds_alternative<p::Receipt>(first) &&
                  std::get<p::Receipt>(first).result ==
                      p::TransferResult::success,
              "tentative first success");
  pv::require(tentative != original, "tentative state did not change");

  auto sender = tentative.accounts.begin();
  auto recipient = std::next(sender);
  sender->second =
      p::Account{tentative.parameters.fixed_fee + 1, 0};
  recipient->second.balance =
      std::numeric_limits<std::uint64_t>::max();
  const p::Transfer overflow{
      sender->first,
      p::TransactionId{},
      1,
      recipient->first,
      1,
      tentative.parameters.fixed_fee,
      1,
  };
  const auto before_failure = tentative;
  const auto failed =
      p::internal::execute_transfer(overflow, tentative, 1);
  pv::require(
      std::holds_alternative<p::internal::ExecutionError>(failed) &&
          std::get<p::internal::ExecutionError>(failed) ==
              p::internal::ExecutionError::recipient_balance_overflow,
      "tentative invariant failure");
  pv::require(tentative == before_failure,
              "tentative invariant failure not atomic");
  pv::require(ledger.state() == original,
              "tentative processing changed ledger");
}

void verify_determinism(const pv::Values& values) {
  auto first_ledger = load_frozen_ledger(values);
  auto second_ledger = load_frozen_ledger(values);
  const auto transactions = raw_transactions(values);
  const auto first =
      require_commit(first_ledger, 1, transactions,
                     "first deterministic block rejected");
  const auto second =
      require_commit(second_ledger, 1, transactions,
                     "second deterministic block rejected");
  pv::require(first_ledger.state() == second_ledger.state(),
              "deterministic state");
  pv::require(
      first.height == second.height &&
          first.admissions == second.admissions &&
          first.transaction_ids == second.transaction_ids &&
          first.receipts == second.receipts &&
          first.encoded_receipts == second.encoded_receipts &&
          first.previous_state_root == second.previous_state_root &&
          first.transaction_root == second.transaction_root &&
          first.resulting_state_root == second.resulting_state_root &&
          first.header == second.header &&
          first.block_id == second.block_id,
      "deterministic block outputs");
}

}  // namespace

int main(int argc, char** argv) {
  try {
    pv::require(argc == 2, "usage: kernel_block_test VECTOR_FILE");
    pv::require(sodium_init() >= 0, "libsodium initialization");
    const auto values = pv::load_values(argv[1]);
    verify_frozen_block(values);
    verify_public_genesis_errors(values);
    verify_block_boundaries(values);
    verify_empty_and_unadmitted_blocks(values);
    verify_duplicates_and_ordering(values);
    verify_tentative_failure_atomicity(values);
    verify_determinism(values);
    std::cout << "Kernel block tests: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "Kernel block tests: failed: " << error.what() << '\n';
    return 1;
  }
}
