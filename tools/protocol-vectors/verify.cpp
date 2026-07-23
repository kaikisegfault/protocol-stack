#include "vector_common.hpp"

#include <algorithm>
#include <iostream>
#include <limits>

namespace pv = protocol_vectors;

extern "C" {
int sodium_init(void);
const char* sodium_version_string(void);
int crypto_sign_seed_keypair(unsigned char* public_key,
                             unsigned char* secret_key,
                             const unsigned char* seed);
int crypto_sign_detached(unsigned char* signature,
                         unsigned long long* signature_size,
                         const unsigned char* message,
                         unsigned long long message_size,
                         const unsigned char* secret_key);
int crypto_sign_verify_detached(const unsigned char* signature,
                                const unsigned char* message,
                                unsigned long long message_size,
                                const unsigned char* public_key);
}

pv::Bytes public_key(const pv::Bytes& seed) {
  pv::require(seed.size() == 32, "wrong Ed25519 seed size");
  pv::Bytes public_bytes(32);
  pv::Bytes secret_key(64);
  pv::require(crypto_sign_seed_keypair(public_bytes.data(), secret_key.data(),
                                       seed.data()) == 0,
              "libsodium key derivation failed");
  return public_bytes;
}

pv::Bytes sign(const pv::Bytes& seed, const pv::Bytes& message) {
  pv::Bytes public_bytes(32);
  pv::Bytes secret_key(64);
  pv::require(crypto_sign_seed_keypair(public_bytes.data(), secret_key.data(),
                                       seed.data()) == 0,
              "libsodium key derivation failed");
  pv::Bytes signature(64);
  unsigned long long signature_size = 0;
  pv::require(crypto_sign_detached(
                  signature.data(), &signature_size, message.data(),
                  message.size(), secret_key.data()) == 0,
              "libsodium signing failed");
  pv::require(signature_size == signature.size(), "wrong signature size");
  return signature;
}

bool verify(const pv::Bytes& public_key_bytes, const pv::Bytes& message,
            const pv::Bytes& signature) {
  if (public_key_bytes.size() != 32 || signature.size() != 64) return false;
  return crypto_sign_verify_detached(signature.data(), message.data(),
                                     message.size(),
                                     public_key_bytes.data()) == 0;
}

bool valid_signed_transaction_shape(const pv::Bytes& transaction) {
  return transaction.size() == 200 &&
         std::equal(transaction.begin(), transaction.begin() + 4, "PSTX") &&
         transaction[4] == 0 && transaction[5] == 1 &&
         transaction[6] == 1 && transaction[39] == 1;
}

pv::Bytes transfer(const pv::Values& values) {
  auto result = pv::ascii("PSTX");
  pv::append_u16(result, 1);
  result.push_back(1);
  pv::append(result, pv::hex_decode(values.at("chain_id")));
  result.push_back(1);
  pv::append(result, pv::hex_decode(values.at("rfc8032.public_key")));
  pv::append_u64(result, std::stoull(values.at("tx.nonce")));
  pv::append(result, pv::hex_decode(values.at("tx.recipient")));
  pv::append_u64(result, std::stoull(values.at("tx.amount")));
  pv::append_u64(result, std::stoull(values.at("tx.fee_limit")));
  pv::append_u64(result, std::stoull(values.at("tx.valid_until")));
  pv::require(result.size() == 136, "wrong unsigned transaction size");
  return result;
}

pv::Bytes state_root(const pv::Bytes& chain_id,
                     const std::vector<pv::Bytes>& entries,
                     std::uint64_t height, std::uint64_t supply_limit,
                     std::uint64_t total_supply, std::uint64_t fee_pool) {
  pv::require(total_supply <= supply_limit, "supply exceeds limit");
  std::uint64_t account_sum = 0;
  for (std::size_t i = 0; i < entries.size(); ++i) {
    pv::require(entries[i].size() == 48, "wrong account entry size");
    if (i != 0) {
      pv::require(std::lexicographical_compare(
                      entries[i - 1].begin(), entries[i - 1].begin() + 32,
                      entries[i].begin(), entries[i].begin() + 32),
                  "account IDs not strictly ordered");
    }
    const auto balance = pv::read_u64(entries[i], 32);
    pv::require(account_sum <=
                    std::numeric_limits<std::uint64_t>::max() - balance,
                "account sum overflow");
    account_sum += balance;
  }
  pv::require(account_sum <=
                  std::numeric_limits<std::uint64_t>::max() - fee_pool &&
                  account_sum + fee_pool == total_supply,
              "supply conservation failed");
  pv::Bytes payload;
  pv::append_u16(payload, 1);
  pv::append(payload, chain_id);
  pv::append_u64(payload, height);
  pv::append_u64(payload, supply_limit);
  pv::append_u64(payload, total_supply);
  pv::append_u64(payload, fee_pool);
  pv::append_u64(payload, entries.size());
  pv::append(payload, pv::merkle(entries, "state"));
  return pv::hash("protocol-stack:v1:state-root", payload);
}

void verify_crypto_and_address(const pv::Values& values) {
  const auto seed = pv::hex_decode(values.at("rfc8032.seed"));
  const auto public_bytes = pv::hex_decode(values.at("rfc8032.public_key"));
  const auto empty_signature =
      pv::hex_decode(values.at("rfc8032.empty_signature"));
  pv::require(public_key(seed) == public_bytes, "RFC public key mismatch");
  pv::require(sign(seed, {}) == empty_signature, "RFC signature mismatch");
  pv::require(verify(public_bytes, {}, empty_signature),
              "RFC signature rejected");

  auto account_input = pv::domain("protocol-stack:v1:account");
  account_input.push_back(1);
  pv::append(account_input, public_bytes);
  const auto account_id = pv::sha256(account_input);
  pv::require(account_id == pv::hex_decode(values.at("account_id")),
              "account ID mismatch");
  auto address_payload = pv::Bytes{1};
  pv::append(address_payload, account_id);
  const auto address = pv::bech32m("psdev", address_payload);
  pv::require(address == values.at("address"), "address mismatch");
  pv::require(pv::valid_bech32m(address, "psdev"), "address rejected");
  pv::require(!pv::valid_bech32m(values.at("invalid.address_checksum"), "psdev"),
              "bad address checksum accepted");
}

void verify_transaction(const pv::Values& values) {
  const auto seed = pv::hex_decode(values.at("rfc8032.seed"));
  const auto public_bytes = pv::hex_decode(values.at("rfc8032.public_key"));
  const auto unsigned_tx = transfer(values);
  pv::require(unsigned_tx == pv::hex_decode(values.at("unsigned_tx")),
              "unsigned transaction mismatch");
  auto signing_message = pv::domain("protocol-stack:v1:tx-sign");
  pv::append(signing_message, unsigned_tx);
  pv::require(signing_message == pv::hex_decode(values.at("signing_message")),
              "signing message mismatch");
  const auto signature = sign(seed, signing_message);
  pv::require(signature == pv::hex_decode(values.at("signature")),
              "transaction signature mismatch");
  pv::require(verify(public_bytes, signing_message, signature),
              "transaction signature rejected");
  pv::require(!verify(public_bytes, signing_message,
                      pv::hex_decode(values.at("invalid.signature"))),
              "mutated signature accepted");
  pv::require(
      !verify(public_bytes, signing_message,
              pv::hex_decode(values.at("invalid.noncanonical_s_signature"))),
      "non-canonical S accepted");
  auto short_signature = signature;
  short_signature.pop_back();
  pv::require(!verify(public_bytes, signing_message, short_signature),
              "short signature accepted");
  pv::require(!verify(
                  pv::hex_decode(values.at("invalid.small_order_public_key")),
                  signing_message,
                  pv::hex_decode(values.at("invalid.small_order_signature"))),
              "small-order forgery accepted");

  auto signed_tx = unsigned_tx;
  pv::append(signed_tx, signature);
  pv::require(signed_tx == pv::hex_decode(values.at("signed_tx")),
              "signed transaction mismatch");
  pv::require(valid_signed_transaction_shape(signed_tx),
              "signed transaction shape rejected");
  auto trailing_transaction = signed_tx;
  pv::append(trailing_transaction,
             pv::hex_decode(values.at("invalid.signed_tx_trailing_suffix")));
  pv::require(!valid_signed_transaction_shape(trailing_transaction),
              "trailing transaction byte accepted");
  auto truncated_transaction = signed_tx;
  truncated_transaction.resize(
      truncated_transaction.size() -
      std::stoull(values.at("invalid.signed_tx_truncated_bytes")));
  pv::require(!valid_signed_transaction_shape(truncated_transaction),
              "truncated transaction accepted");
  pv::require(pv::hash("protocol-stack:v1:tx-id", signed_tx) ==
                  pv::hex_decode(values.at("tx_id")),
              "transaction ID mismatch");
}

void verify_trees(const pv::Values& values) {
  const auto chain_id = pv::hex_decode(values.at("chain_id"));
  pv::require(pv::merkle({}, "state") ==
                  pv::hex_decode(values.at("state.empty_tree_root")),
              "empty state tree mismatch");
  pv::require(state_root(chain_id, {}, 0, 1000, 0, 0) ==
                  pv::hex_decode(values.at("state.empty_root")),
              "empty state root mismatch");
  std::vector<pv::Bytes> entries{
      pv::hex_decode(values.at("state.account0")),
      pv::hex_decode(values.at("state.account1")),
      pv::hex_decode(values.at("state.account2"))};
  pv::require(pv::merkle(entries, "state") ==
                  pv::hex_decode(values.at("state.accounts_tree_root")),
              "account tree mismatch");
  pv::require(state_root(chain_id, entries, 7, 1000, 640, 40) ==
                  pv::hex_decode(values.at("state.root")),
              "state root mismatch");
  bool rejected_supply = false;
  try {
    static_cast<void>(state_root(chain_id, entries, 7, 639, 640, 40));
  } catch (const std::runtime_error&) {
    rejected_supply = true;
  }
  pv::require(rejected_supply, "supply limit violation accepted");
  std::swap(entries[0], entries[1]);
  bool rejected_order = false;
  try {
    static_cast<void>(state_root(chain_id, entries, 7, 1000, 640, 40));
  } catch (const std::runtime_error&) {
    rejected_order = true;
  }
  pv::require(rejected_order, "unsorted accounts accepted");

  std::vector<pv::Bytes> transaction_ids{
      pv::hex_decode(values.at("tx.item0")),
      pv::hex_decode(values.at("tx.item1")),
      pv::hex_decode(values.at("tx.item2"))};
  pv::require(pv::merkle({}, "tx") ==
                  pv::hex_decode(values.at("tx.empty_root")),
              "empty transaction tree mismatch");
  pv::require(pv::merkle(transaction_ids, "tx") ==
                  pv::hex_decode(values.at("tx.root")),
              "transaction tree mismatch");
}

int main(int argc, char** argv) {
  try {
    pv::require(argc == 2, "usage: verify_cpp VECTOR_FILE");
    pv::require(sodium_init() >= 0, "libsodium initialization failed");
    const auto values = pv::load_values(argv[1]);
    verify_crypto_and_address(values);
    verify_transaction(values);
    verify_trees(values);
    std::cout << "C++ protocol primitive vectors: passed (libsodium "
              << sodium_version_string() << ")\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "C++ protocol primitive vectors: failed: " << error.what()
              << '\n';
    return 1;
  }
}
