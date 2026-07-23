#include "protocol/v1/address.hpp"
#include "protocol/v1/admission.hpp"
#include "protocol/v1/crypto.hpp"

#include "../../src/v1/commitments.hpp"
#include "../../tools/protocol-vectors/vector_common.hpp"

#include <algorithm>
#include <cstdint>
#include <iostream>
#include <map>
#include <span>
#include <string>
#include <string_view>
#include <variant>
#include <vector>

namespace pv = protocol_vectors;
namespace p = protocol::v1;
namespace pc = protocol::v1::internal;

namespace {

template <typename Tagged>
Tagged tagged_hash(const pv::Bytes& bytes, std::size_t offset = 0) {
  pv::require(offset + 32 <= bytes.size(), "hash size");
  p::Hash result{};
  std::copy_n(bytes.begin() + offset, result.size(), result.begin());
  return Tagged{result};
}

void require_admission_error(const p::Admission& admission,
                             p::AdmissionError expected,
                             std::string_view message) {
  pv::require(std::holds_alternative<p::AdmissionError>(admission), message);
  pv::require(std::get<p::AdmissionError>(admission) == expected, message);
}

std::string bech32m_values(
    std::string_view hrp, std::vector<std::uint8_t> data) {
  static constexpr std::string_view charset =
      "qpzry9x8gf2tvdw0s3jn54khce6mua7l";
  auto checksum_input = pv::hrp_expand(hrp);
  checksum_input.insert(checksum_input.end(), data.begin(), data.end());
  checksum_input.resize(checksum_input.size() + 6, 0);
  const auto checksum = pv::bech32_polymod(checksum_input) ^ 0x2bc830a3U;

  std::string result(hrp);
  result.push_back('1');
  for (const auto value : data) result.push_back(charset[value]);
  for (int index = 0; index < 6; ++index) {
    result.push_back(
        charset[(checksum >> (5 * (5 - index))) & 31U]);
  }
  return result;
}

void verify_hash_and_signatures(const pv::Values& values) {
  const auto public_key =
      pv::hex_decode(values.at("rfc8032.public_key"));
  const auto empty_signature =
      pv::hex_decode(values.at("rfc8032.empty_signature"));
  const pv::Bytes empty;
  pv::require(
      p::strict_ed25519_verify(public_key, empty, empty_signature),
      "production verifier rejected RFC 8032 vector");

  auto short_key = public_key;
  short_key.pop_back();
  pv::require(
      !p::strict_ed25519_verify(short_key, empty, empty_signature),
      "production verifier accepted short public key");
  auto short_signature = empty_signature;
  short_signature.pop_back();
  pv::require(
      !p::strict_ed25519_verify(public_key, empty, short_signature),
      "production verifier accepted short signature");

  const auto signing_message =
      pv::hex_decode(values.at("signing_message"));
  const auto signature = pv::hex_decode(values.at("signature"));
  pv::require(
      p::strict_ed25519_verify(public_key, signing_message, signature),
      "production verifier rejected transaction signature");
  pv::require(
      !p::strict_ed25519_verify(
          public_key, signing_message,
          pv::hex_decode(values.at("invalid.signature"))),
      "production verifier accepted mutated signature");
  pv::require(
      !p::strict_ed25519_verify(
          public_key, signing_message,
          pv::hex_decode(values.at("invalid.noncanonical_s_signature"))),
      "production verifier accepted non-canonical S");
  const auto small_order_signature =
      pv::hex_decode(values.at("invalid.small_order_signature"));
  pv::require(
      !p::strict_ed25519_verify(public_key, signing_message,
                                small_order_signature),
      "production verifier accepted small-order R");
  pv::require(
      !p::strict_ed25519_verify(
          pv::hex_decode(values.at("invalid.small_order_public_key")),
          signing_message, small_order_signature),
      "production verifier accepted small-order forgery");

  pv::Bytes account_payload{1};
  pv::append(account_payload, public_key);
  const auto account_hash =
      p::hash("protocol-stack:v1:account", account_payload);
  pv::require(
      pv::Bytes(account_hash.begin(), account_hash.end()) ==
          pv::hex_decode(values.at("account_id")),
      "production account hash mismatch");
  const auto signed_transaction =
      pv::hex_decode(values.at("signed_tx"));
  const auto transaction_hash =
      p::hash("protocol-stack:v1:tx-id", signed_transaction);
  pv::require(
      pv::Bytes(transaction_hash.begin(), transaction_hash.end()) ==
          pv::hex_decode(values.at("tx_id")),
      "production transaction hash mismatch");
}

void verify_addresses(const pv::Values& values) {
  const auto account_id =
      tagged_hash<p::AccountId>(pv::hex_decode(values.at("account_id")));
  const auto encoded = p::encode_address(account_id, "psdev");
  pv::require(encoded && *encoded == values.at("address"),
              "production address encoding mismatch");
  const auto decoded = p::decode_address(values.at("address"), "psdev");
  pv::require(decoded && *decoded == account_id,
              "production address decoder rejected vector");

  pv::require(
      !p::decode_address(values.at("invalid.address_checksum"), "psdev"),
      "bad checksum accepted");
  pv::require(!p::decode_address(values.at("address"), ""),
              "invalid configured HRP accepted");
  pv::require(!p::encode_address(account_id, "") &&
                  !p::encode_address(account_id, "PSDEV") &&
                  !p::encode_address(account_id, "ps-dev") &&
                  !p::encode_address(account_id,
                                     "abcdefghijklmnopqrstu"),
              "invalid encoding HRP accepted");

  const auto other_chain = p::encode_address(account_id, "psother");
  pv::require(other_chain.has_value(), "alternate HRP encoding");
  pv::require(!p::decode_address(*other_chain, "psdev"),
              "wrong address HRP accepted");
  auto uppercase = values.at("address");
  uppercase.front() = 'P';
  pv::require(!p::decode_address(uppercase, "psdev"),
              "uppercase address accepted");

  auto version_two = pv::hex_decode(values.at("address_payload"));
  version_two.front() = 2;
  pv::require(
      !p::decode_address(pv::bech32m("psdev", version_two), "psdev"),
      "unknown address payload version accepted");

  auto nonzero_padding =
      pv::convert_bits(pv::hex_decode(values.at("address_payload")));
  nonzero_padding.back() |= 1U;
  pv::require(
      !p::decode_address(bech32m_values("psdev", nonzero_padding),
                         "psdev"),
      "nonzero address padding accepted");
}

pv::Bytes transaction_with_signature(const pv::Values& values,
                                     std::string_view signature_key) {
  auto transaction = pv::hex_decode(values.at("signed_tx"));
  const auto signature = pv::hex_decode(values.at(std::string(signature_key)));
  pv::require(signature.size() == 64, "replacement signature size");
  std::copy(signature.begin(), signature.end(), transaction.begin() + 136);
  return transaction;
}

void verify_admission(const pv::Values& values) {
  const auto chain_id =
      tagged_hash<p::ChainId>(pv::hex_decode(values.at("chain_id")));
  const auto signed_transaction =
      pv::hex_decode(values.at("signed_tx"));
  const auto admission = p::admit_transfer(signed_transaction, chain_id);
  pv::require(std::holds_alternative<p::Transfer>(admission),
              "production admission rejected frozen transfer");
  const auto& transfer = std::get<p::Transfer>(admission);
  pv::require(
      transfer.sender_id ==
          tagged_hash<p::AccountId>(pv::hex_decode(values.at("account_id"))) &&
          transfer.transaction_id ==
              tagged_hash<p::TransactionId>(
                  pv::hex_decode(values.at("tx_id"))) &&
          transfer.nonce == std::stoull(values.at("tx.nonce")) &&
          transfer.recipient ==
              tagged_hash<p::AccountId>(
                  pv::hex_decode(values.at("tx.recipient"))) &&
          transfer.amount == std::stoull(values.at("tx.amount")) &&
          transfer.fee_limit ==
              std::stoull(values.at("tx.fee_limit")) &&
          transfer.valid_until ==
              std::stoull(values.at("tx.valid_until")),
      "production admitted transfer fields mismatch");

  const auto invalid =
      transaction_with_signature(values, "invalid.signature");
  require_admission_error(
      p::admit_transfer(invalid, chain_id),
      p::AdmissionError::invalid_signature,
      "mutated transaction signature accepted");
  require_admission_error(
      p::admit_transfer(
          transaction_with_signature(
              values, "invalid.noncanonical_s_signature"),
          chain_id),
      p::AdmissionError::invalid_signature,
      "non-canonical transaction signature accepted");
  require_admission_error(
      p::admit_transfer(
          transaction_with_signature(
              values, "invalid.small_order_signature"),
          chain_id),
      p::AdmissionError::invalid_signature,
      "small-order transaction R accepted");

  auto small_order = transaction_with_signature(
      values, "invalid.small_order_signature");
  const auto small_order_key =
      pv::hex_decode(values.at("invalid.small_order_public_key"));
  std::copy(small_order_key.begin(), small_order_key.end(),
            small_order.begin() + 40);
  require_admission_error(
      p::admit_transfer(small_order, chain_id),
      p::AdmissionError::invalid_signature,
      "small-order transaction forgery accepted");

  auto truncated = signed_transaction;
  truncated.resize(
      truncated.size() -
      std::stoull(values.at("invalid.signed_tx_truncated_bytes")));
  require_admission_error(
      p::admit_transfer(truncated, chain_id),
      p::AdmissionError::malformed_transaction,
      "truncated transaction accepted");
  auto trailing = signed_transaction;
  pv::append(
      trailing,
      pv::hex_decode(values.at("invalid.signed_tx_trailing_suffix")));
  require_admission_error(
      p::admit_transfer(trailing, chain_id),
      p::AdmissionError::malformed_transaction,
      "transaction trailing byte accepted");

  auto other_chain = chain_id;
  other_chain.data()[0] ^= 1U;
  require_admission_error(
      p::admit_transfer(invalid, other_chain),
      p::AdmissionError::wrong_chain,
      "signature failure preceded wrong-chain rejection");
  require_admission_error(
      p::admit_transfer(trailing, other_chain),
      p::AdmissionError::malformed_transaction,
      "wrong-chain check preceded shape rejection");
}

std::pair<p::AccountId, p::Account> decode_account(
    std::string_view encoded) {
  const auto entry = pv::hex_decode(encoded);
  pv::require(entry.size() == 48, "account vector size");
  return {
      tagged_hash<p::AccountId>(entry),
      p::Account{pv::read_u64(entry, 32), pv::read_u64(entry, 40)},
  };
}

void verify_commitments(const pv::Values& values) {
  const auto chain_id =
      tagged_hash<p::ChainId>(pv::hex_decode(values.at("chain_id")));
  std::map<p::AccountId, p::Account> accounts;
  for (std::size_t index = 0; index < 3; ++index) {
    pv::require(
        accounts
            .emplace(decode_account(
                values.at("state.account" + std::to_string(index))))
            .second,
        "duplicate account vector");
  }
  const p::State state{
      p::Parameters{
          chain_id,
          std::stoull(values.at("state.supply_limit")),
          std::stoull(values.at("state.total_supply")),
          1,
      },
      std::stoull(values.at("state.height")),
      std::stoull(values.at("state.fee_pool_balance")),
      accounts,
  };
  const auto state_commitment = pc::state_root(state);
  pv::require(std::holds_alternative<p::StateRoot>(state_commitment),
              "production state commitment rejected frozen state");
  pv::require(
      std::get<p::StateRoot>(state_commitment) ==
          tagged_hash<p::StateRoot>(pv::hex_decode(values.at("state.root"))),
      "production state root mismatch");

  const p::State empty_state{
      p::Parameters{chain_id, 1000, 0, 1},
      0,
      0,
      {},
  };
  const auto empty_state_commitment = pc::state_root(empty_state);
  pv::require(
      std::holds_alternative<p::StateRoot>(empty_state_commitment) &&
          std::get<p::StateRoot>(empty_state_commitment) ==
              tagged_hash<p::StateRoot>(
                  pv::hex_decode(values.at("state.empty_root"))),
      "production empty state root mismatch");

  const auto empty_state_tree =
      p::hash("protocol-stack:v1:state-empty");
  pv::require(
      pv::Bytes(empty_state_tree.begin(), empty_state_tree.end()) ==
          pv::hex_decode(values.at("state.empty_tree_root")),
      "production empty state-tree hash mismatch");

  std::vector<p::TransactionId> transaction_ids;
  for (std::size_t index = 0; index < 3; ++index) {
    transaction_ids.push_back(tagged_hash<p::TransactionId>(
        pv::hex_decode(values.at("tx.item" + std::to_string(index)))));
  }
  pv::require(
      pc::transaction_root({}) ==
          tagged_hash<p::TransactionRoot>(
              pv::hex_decode(values.at("tx.empty_root"))),
      "production empty transaction root mismatch");
  pv::require(
      pc::transaction_root(transaction_ids) ==
          tagged_hash<p::TransactionRoot>(
              pv::hex_decode(values.at("tx.root"))),
      "production transaction root mismatch");
}

}  // namespace

int main(int argc, char** argv) {
  try {
    pv::require(argc == 2,
                "usage: kernel_primitives_test VECTOR_FILE");
    const auto values = pv::load_values(argv[1]);
    verify_hash_and_signatures(values);
    verify_addresses(values);
    verify_admission(values);
    verify_commitments(values);
    std::cout << "Kernel protocol primitive vectors: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "Kernel protocol primitive vectors: failed: "
              << error.what() << '\n';
    return 1;
  }
}
