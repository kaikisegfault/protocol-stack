#include "../../src/v1/commitments.hpp"
#include "../../tools/protocol-vectors/vector_common.hpp"

#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>
#include <limits>
#include <map>
#include <span>
#include <string>
#include <string_view>
#include <utility>
#include <variant>
#include <vector>

namespace pv = protocol_vectors;
namespace p = protocol::v1;
namespace pc = protocol::v1::internal;

namespace {

p::Hash hash_value(const pv::Bytes& bytes, std::size_t offset = 0) {
  pv::require(offset + 32 <= bytes.size(), "hash size");
  p::Hash result{};
  std::copy_n(bytes.begin() + offset, result.size(), result.begin());
  return result;
}

pv::Bytes bytes(const p::Hash& value) {
  return {value.begin(), value.end()};
}

std::pair<p::Hash, p::Account> decode_account(std::string_view encoded) {
  const auto entry = pv::hex_decode(encoded);
  pv::require(entry.size() == 48, "account entry size");
  return {
      hash_value(entry),
      p::Account{pv::read_u64(entry, 32), pv::read_u64(entry, 40)},
  };
}

std::map<p::Hash, p::Account> load_accounts(const pv::Values& values,
                                             std::string_view prefix,
                                             std::size_t count) {
  std::map<p::Hash, p::Account> accounts;
  for (std::size_t index = 0; index < count; ++index) {
    const auto key = std::string(prefix) + std::to_string(index);
    pv::require(accounts.emplace(decode_account(values.at(key))).second,
                "duplicate account");
  }
  return accounts;
}

std::size_t genesis_account_count(const pv::Values& values) {
  std::size_t count = 0;
  while (values.find("genesis.account" + std::to_string(count)) !=
         values.end()) {
    ++count;
  }
  return count;
}

p::Parameters parameters(const pv::Values& values) {
  return p::Parameters{
      hash_value(pv::hex_decode(values.at("chain_id"))),
      std::stoull(values.at("supply_limit")),
      std::stoull(values.at("total_supply")),
      std::stoull(values.at("fixed_fee")),
  };
}

p::State initial_state(const pv::Values& values) {
  return p::State{
      parameters(values),
      0,
      0,
      load_accounts(values, "genesis.account", genesis_account_count(values)),
  };
}

p::State final_state(const pv::Values& values) {
  const auto count = std::stoull(values.at("final_account_count"));
  return p::State{
      parameters(values),
      1,
      std::stoull(values.at("fee_pool")),
      load_accounts(values, "final.account", count),
  };
}

std::vector<pv::Bytes> account_entries(const p::State& state) {
  std::vector<pv::Bytes> entries;
  entries.reserve(state.accounts.size());
  for (const auto& [identifier, account] : state.accounts) {
    auto entry = bytes(identifier);
    pv::append_u64(entry, account.balance);
    pv::append_u64(entry, account.nonce);
    entries.push_back(std::move(entry));
  }
  return entries;
}

p::Hash expected_state_root(const p::State& state) {
  const auto entries = account_entries(state);
  pv::Bytes payload;
  pv::append_u16(payload, 1);
  pv::append(payload, bytes(state.parameters.chain_id));
  pv::append_u64(payload, state.height);
  pv::append_u64(payload, state.parameters.supply_limit);
  pv::append_u64(payload, state.parameters.total_supply);
  pv::append_u64(payload, state.fee_pool);
  pv::append_u64(payload, entries.size());
  pv::append(payload, pv::merkle(entries, "state"));
  return hash_value(pv::hash("protocol-stack:v1:state-root", payload));
}

p::Hash require_state_root(const p::State& state) {
  const auto commitment = pc::state_root(state);
  pv::require(std::holds_alternative<p::Hash>(commitment),
              "expected state root");
  return std::get<p::Hash>(commitment);
}

void require_state_error(const p::State& state, pc::StateError expected) {
  const auto commitment = pc::state_root(state);
  pv::require(std::holds_alternative<pc::StateError>(commitment),
              "expected state error");
  pv::require(std::get<pc::StateError>(commitment) == expected,
              "state error");
}

void verify_final_entries(const p::State& state, const pv::Values& values) {
  const auto entries = account_entries(state);
  pv::require(entries.size() ==
                  std::stoull(values.at("final_account_count")),
              "final entry count");
  for (std::size_t index = 0; index < entries.size(); ++index) {
    pv::require(entries[index] ==
                    pv::hex_decode(values.at("final.account" +
                                             std::to_string(index))),
                "final account entry");
  }
}

std::vector<p::Hash> verify_receipts(const pv::Values& values) {
  const auto count = std::stoull(values.at("admitted_count"));
  const auto fixed_fee = std::stoull(values.at("fixed_fee"));
  std::vector<p::Hash> transaction_ids;
  transaction_ids.reserve(count);
  for (std::size_t index = 0; index < count; ++index) {
    const auto key = "receipt" + std::to_string(index);
    const auto expected = pv::hex_decode(values.at(key));
    pv::require(expected.size() == 47, "receipt vector size");
    const auto transaction_id = hash_value(expected, 6);
    const p::Receipt receipt{
        transaction_id,
        static_cast<p::TransferResult>(expected[38]),
        pv::read_u64(expected, 39),
    };
    const auto encoded = pc::encode_receipt(receipt, fixed_fee);
    pv::require(encoded.has_value() && *encoded == expected,
                "receipt encoding");
    transaction_ids.push_back(transaction_id);
  }
  return transaction_ids;
}

void verify_frozen_commitments(const pv::Values& values) {
  const auto previous_state = initial_state(values);
  const auto resulting_state = final_state(values);
  const auto previous_root = require_state_root(previous_state);
  const auto resulting_root = require_state_root(resulting_state);
  pv::require(previous_root ==
                  hash_value(pv::hex_decode(values.at("previous_state_root"))),
              "previous state root");
  pv::require(resulting_root ==
                  hash_value(pv::hex_decode(values.at("resulting_state_root"))),
              "resulting state root");
  verify_final_entries(resulting_state, values);

  const auto transaction_ids = verify_receipts(values);
  const auto tx_root = pc::transaction_root(transaction_ids);
  pv::require(tx_root ==
                  hash_value(pv::hex_decode(values.at("transaction_root"))),
              "transaction root");
  const auto header = pc::encode_block_header(
      previous_state.parameters.chain_id, 1, previous_root, tx_root,
      resulting_root, static_cast<std::uint32_t>(transaction_ids.size()));
  pv::require(header.size() == 146, "block header size");
  pv::require(header == pv::hex_decode(values.at("block_header")),
              "block header");
  const auto encoded_block_id = pc::block_id(header);
  pv::require(encoded_block_id &&
                  *encoded_block_id ==
                      hash_value(pv::hex_decode(values.at("block_id"))),
              "block ID");
}

std::vector<p::Hash> sample_ids(std::size_t count = 5) {
  std::vector<p::Hash> ids(count);
  for (std::size_t index = 0; index < ids.size(); ++index) {
    for (std::size_t offset = 0; offset < ids[index].size(); ++offset) {
      ids[index][offset] =
          static_cast<std::uint8_t>((index + 1) * 17 + offset);
    }
  }
  return ids;
}

p::Hash expected_transaction_root(std::span<const p::Hash> ids) {
  std::vector<pv::Bytes> encoded;
  encoded.reserve(ids.size());
  for (const auto& identifier : ids) encoded.push_back(bytes(identifier));
  return hash_value(pv::merkle(encoded, "tx"));
}

void verify_merkle_shapes() {
  const auto ids = sample_ids(65'535);
  constexpr std::array<std::size_t, 13> counts{
      0, 1, 2, 3, 4, 5, 7, 8, 9, 15, 16, 17, 65'535};
  for (const auto count : counts) {
    const auto view = std::span<const p::Hash>(ids).first(count);
    pv::require(pc::transaction_root(view) ==
                    expected_transaction_root(view),
                "transaction Merkle shape");
  }

  auto reordered = sample_ids();
  std::swap(reordered[1], reordered[3]);
  const auto first_five = std::span<const p::Hash>(ids).first(5);
  pv::require(pc::transaction_root(first_five) !=
                  pc::transaction_root(reordered),
              "transaction ordering");
  auto mutated = sample_ids();
  mutated[2][7] ^= 1U;
  pv::require(pc::transaction_root(first_five) !=
                  pc::transaction_root(mutated),
              "transaction mutation");

  for (std::size_t count = 0; count <= 5; ++count) {
    p::State state{
        p::Parameters{ids.front(), 100, count + 1, 1},
        7,
        1,
        {},
    };
    for (std::size_t index = count; index > 0; --index) {
      state.accounts.emplace(ids[index - 1], p::Account{1, index - 1});
    }
    pv::require(require_state_root(state) == expected_state_root(state),
                "state Merkle shape");
  }
}

void verify_state_errors() {
  auto ids = sample_ids();
  p::State state{
      p::Parameters{ids.front(), 100, 10, 1},
      0,
      0,
      {{ids[1], p::Account{10, 0}}},
  };

  auto invalid = state;
  invalid.parameters.supply_limit = 0;
  require_state_error(invalid, pc::StateError::invalid_parameters);
  invalid = state;
  invalid.parameters.total_supply = 0;
  require_state_error(invalid, pc::StateError::invalid_parameters);
  invalid = state;
  invalid.parameters.fixed_fee = 0;
  require_state_error(invalid, pc::StateError::invalid_parameters);
  invalid = state;
  invalid.parameters.supply_limit = 9;
  require_state_error(invalid, pc::StateError::invalid_parameters);

  auto overflow = state;
  overflow.parameters.supply_limit =
      std::numeric_limits<std::uint64_t>::max();
  overflow.parameters.total_supply =
      std::numeric_limits<std::uint64_t>::max();
  overflow.fee_pool = std::numeric_limits<std::uint64_t>::max();
  overflow.accounts.begin()->second.balance = 1;
  require_state_error(overflow, pc::StateError::supply_overflow);

  auto mismatch = state;
  mismatch.accounts.begin()->second.balance = 9;
  require_state_error(mismatch, pc::StateError::supply_mismatch);
}

void verify_invalid_receipts(const pv::Values& values) {
  const auto fixed_fee = std::stoull(values.at("fixed_fee"));
  const p::Hash transaction_id{};
  pv::require(
      !pc::encode_receipt(
           p::Receipt{transaction_id, static_cast<p::TransferResult>(9), 0},
           fixed_fee)
           .has_value(),
      "unknown receipt result");
  pv::require(
      !pc::encode_receipt(
           p::Receipt{transaction_id, p::TransferResult::success,
                      fixed_fee - 1},
           fixed_fee)
           .has_value(),
      "invalid successful fee");
  pv::require(
      !pc::encode_receipt(
           p::Receipt{transaction_id, p::TransferResult::zero_amount, 1},
           fixed_fee)
           .has_value(),
      "invalid failed fee");

  auto header = pc::encode_block_header(
      transaction_id, 1, transaction_id, transaction_id, transaction_id, 0);
  header.pop_back();
  pv::require(!pc::block_id(header), "short block header");
  header = pc::encode_block_header(
      transaction_id, 1, transaction_id, transaction_id, transaction_id, 0);
  header[0] = 'X';
  pv::require(!pc::block_id(header), "block header magic");
  header = pc::encode_block_header(
      transaction_id, 1, transaction_id, transaction_id, transaction_id, 0);
  header[5] = 2;
  pv::require(!pc::block_id(header), "block header version");
}

}  // namespace

int main(int argc, char** argv) {
  try {
    pv::require(argc == 2, "usage: kernel_commitments_test VECTOR_FILE");
    pv::require(sodium_init() >= 0, "libsodium initialization");
    const auto values = pv::load_values(argv[1]);
    verify_frozen_commitments(values);
    verify_merkle_shapes();
    verify_state_errors();
    verify_invalid_receipts(values);
    std::cout << "Kernel commitment vectors: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "Kernel commitment vectors: failed: " << error.what()
              << '\n';
    return 1;
  }
}
