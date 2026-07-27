#include "protocol/storage/sqlite_ledger.hpp"
#include "protocol/v1/ledger.hpp"

#include "../../tools/protocol-vectors/vector_common.hpp"

#include <sodium.h>

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <exception>
#include <filesystem>
#include <iostream>
#include <span>
#include <string>
#include <string_view>
#include <utility>
#include <variant>
#include <vector>

namespace pv = protocol_vectors;
namespace ps = protocol::storage;
namespace p = protocol::v1;

namespace {

constexpr std::uint64_t kSequenceSeed = 0x53514c4954452d31ULL;
constexpr std::uint64_t kBlockCount = 256;
constexpr std::uint64_t kRestartInterval = 17;
constexpr std::uint64_t kSnapshotInterval = 31;

class SplitMix64 {
 public:
  explicit SplitMix64(std::uint64_t state) : state_(state) {}

  std::uint64_t next() {
    auto value = (state_ += 0x9e3779b97f4a7c15ULL);
    value = (value ^ (value >> 30U)) * 0xbf58476d1ce4e5b9ULL;
    value = (value ^ (value >> 27U)) * 0x94d049bb133111ebULL;
    return value ^ (value >> 31U);
  }

 private:
  std::uint64_t state_;
};

class DatabaseFiles {
 public:
  explicit DatabaseFiles(std::filesystem::path path)
      : path_(std::move(path)) {
    remove();
  }

  ~DatabaseFiles() { remove(); }

  const std::filesystem::path& path() const noexcept { return path_; }

 private:
  void remove() noexcept {
    std::error_code ignored;
    std::filesystem::remove(path_, ignored);
    std::filesystem::remove(path_.string() + "-journal", ignored);
    std::filesystem::remove(path_.string() + "-wal", ignored);
    std::filesystem::remove(path_.string() + "-shm", ignored);
  }

  std::filesystem::path path_;
};

ps::SQLiteLedger take_ledger(
    ps::SQLiteLedgerResult result,
    std::string_view message) {
  pv::require(
      std::holds_alternative<ps::SQLiteLedger>(result.result),
      message);
  return std::get<ps::SQLiteLedger>(std::move(result.result));
}

ps::LedgerHead take_head(
    ps::SQLiteHeadResult result,
    std::string_view message) {
  pv::require(
      std::holds_alternative<ps::LedgerHead>(result), message);
  return std::get<ps::LedgerHead>(std::move(result));
}

p::BlockCommit take_commit(
    ps::SQLiteBlockResult result,
    std::string_view message) {
  pv::require(
      std::holds_alternative<p::BlockCommit>(result), message);
  return std::get<p::BlockCommit>(std::move(result));
}

void require_snapshot(
    ps::SQLiteSnapshotResult result,
    std::string_view message) {
  pv::require(
      std::holds_alternative<p::Bytes>(result) &&
          std::get<p::Bytes>(result).size() >= 64,
      message);
}

bool same_commit(
    const p::BlockCommit& left,
    const p::BlockCommit& right) {
  return left.height == right.height &&
         left.admissions == right.admissions &&
         left.transaction_ids == right.transaction_ids &&
         left.receipts == right.receipts &&
         left.encoded_receipts == right.encoded_receipts &&
         left.previous_state_root == right.previous_state_root &&
         left.transaction_root == right.transaction_root &&
         left.resulting_state_root == right.resulting_state_root &&
         left.header == right.header &&
         left.block_id == right.block_id;
}

p::Ledger load_ledger(const p::Bytes& genesis) {
  auto loaded = p::load_genesis(genesis);
  pv::require(
      std::holds_alternative<p::Ledger>(loaded.result),
      "sequence genesis rejected");
  return std::get<p::Ledger>(std::move(loaded.result));
}

ps::LedgerHead ledger_head(const p::Ledger& ledger) {
  auto root = ledger.current_state_root();
  pv::require(
      std::holds_alternative<p::StateRoot>(root),
      "sequence state root failed");
  return ps::LedgerHead{
      ledger.state(), std::get<p::StateRoot>(std::move(root))};
}

template <typename Tagged>
Tagged tagged_hash(std::span<const std::uint8_t> bytes) {
  pv::require(bytes.size() == 32, "wrong tagged-hash size");
  p::Hash value{};
  std::copy(bytes.begin(), bytes.end(), value.begin());
  return Tagged{value};
}

void write_u64(
    p::Bytes& target,
    std::size_t offset,
    std::uint64_t value) {
  pv::require(offset + 8 <= target.size(), "u64 write out of bounds");
  for (std::size_t index = 0; index < 8; ++index) {
    const auto shift = static_cast<unsigned>((7 - index) * 8);
    target[offset + index] =
        static_cast<std::uint8_t>(value >> shift);
  }
}

class TransferSigner {
 public:
  TransferSigner(const p::Bytes& base, const p::Bytes& seed)
      : base_(base) {
    pv::require(
        base_.size() == 200 && seed.size() == crypto_sign_SEEDBYTES,
        "invalid sequence signer fixture");
    std::array<std::uint8_t, crypto_sign_PUBLICKEYBYTES> public_key{};
    pv::require(
        crypto_sign_seed_keypair(
            public_key.data(), secret_key_.data(), seed.data()) == 0,
        "sequence key derivation failed");
    pv::require(
        std::equal(
            public_key.begin(), public_key.end(), base_.begin() + 40),
        "sequence seed does not match transaction template");
  }

  p::Bytes sign(
      std::uint64_t nonce,
      const p::AccountId& recipient,
      std::uint64_t amount,
      std::uint64_t fee_limit,
      std::uint64_t valid_until) const {
    auto transaction = base_;
    write_u64(transaction, 72, nonce);
    std::copy(
        recipient.begin(), recipient.end(), transaction.begin() + 80);
    write_u64(transaction, 112, amount);
    write_u64(transaction, 120, fee_limit);
    write_u64(transaction, 128, valid_until);

    auto message = pv::domain("protocol-stack:v1:tx-sign");
    message.insert(
        message.end(), transaction.begin(), transaction.begin() + 136);
    unsigned long long signature_size = 0;
    pv::require(
        crypto_sign_detached(
            transaction.data() + 136, &signature_size,
            message.data(), message.size(), secret_key_.data()) == 0 &&
            signature_size == crypto_sign_BYTES,
        "sequence transaction signing failed");
    return transaction;
  }

 private:
  p::Bytes base_;
  std::array<std::uint8_t, crypto_sign_SECRETKEYBYTES> secret_key_{};
};

p::AccountId random_recipient(SplitMix64& random) {
  p::Hash value{};
  for (std::size_t offset = 0; offset < value.size(); offset += 8) {
    const auto word = random.next();
    for (std::size_t index = 0; index < 8; ++index) {
      value[offset + index] =
          static_cast<std::uint8_t>(word >> ((7 - index) * 8));
    }
  }
  value[0] ^= 0x80U;
  return p::AccountId{value};
}

struct Coverage {
  std::array<std::size_t, 4> admissions{};
  std::array<std::size_t, 9> receipts{};
  std::size_t empty_blocks = 0;
  std::size_t all_unadmitted_blocks = 0;
};

std::vector<p::Bytes> make_block(
    SplitMix64& random,
    const TransferSigner& signer,
    const p::Ledger& expected,
    const p::AccountId& sender,
    std::uint64_t height) {
  if (height % 37 == 0) return {};

  const auto sender_account = expected.state().accounts.at(sender);
  if (height % 41 == 0) {
    auto transaction = signer.sign(
        sender_account.nonce + 1, sender, 1, 1'000, height + 64);
    auto malformed = transaction;
    malformed.pop_back();
    auto wrong_chain = transaction;
    wrong_chain[7] ^= 1U;
    transaction.back() ^= 1U;
    return {
        std::move(malformed),
        std::move(wrong_chain),
        std::move(transaction),
    };
  }

  auto planned_nonce = sender_account.nonce;
  const auto input_count =
      static_cast<std::size_t>(1 + random.next() % 5);
  std::vector<p::Bytes> inputs;
  inputs.reserve(input_count);
  for (std::size_t index = 0; index < input_count; ++index) {
    const auto kind =
        static_cast<std::uint8_t>(random.next() % 9);
    const auto recipient =
        kind == 1 ? sender : random_recipient(random);
    const auto amount = 1 + random.next() % 1'000;
    auto transaction = signer.sign(
        planned_nonce + 1, recipient, amount, 1'000, height + 64);

    switch (kind) {
      case 0:
      case 1:
        ++planned_nonce;
        break;
      case 2:
        transaction = signer.sign(
            planned_nonce + 1, recipient, 0, 1'000, height + 64);
        break;
      case 3:
        transaction = signer.sign(
            planned_nonce + 1, recipient, amount, 999, height + 64);
        break;
      case 4:
        transaction = signer.sign(
            planned_nonce + 1, recipient, amount, 1'000, height - 1);
        break;
      case 5:
        transaction = signer.sign(
            planned_nonce + 2, recipient, amount, 1'000, height + 64);
        break;
      case 6:
        transaction.pop_back();
        break;
      case 7:
        transaction[7] ^= 1U;
        break;
      case 8:
        transaction.back() ^= 1U;
        break;
    }
    inputs.push_back(std::move(transaction));
  }
  return inputs;
}

void record_coverage(
    const std::vector<p::Bytes>& inputs,
    const p::BlockCommit& commit,
    Coverage& coverage) {
  if (inputs.empty()) ++coverage.empty_blocks;
  if (!inputs.empty() && commit.transaction_ids.empty()) {
    ++coverage.all_unadmitted_blocks;
  }
  for (const auto& admission : commit.admissions) {
    const auto index = admission
        ? static_cast<std::size_t>(*admission)
        : std::size_t{0};
    pv::require(index < coverage.admissions.size(),
                "sequence admission result out of range");
    ++coverage.admissions[index];
  }
  for (const auto& receipt : commit.receipts) {
    const auto index =
        static_cast<std::size_t>(receipt.result);
    pv::require(index < coverage.receipts.size(),
                "sequence receipt result out of range");
    ++coverage.receipts[index];
  }
}

void verify_head(
    ps::SQLiteLedger& stored,
    const p::Ledger& expected,
    std::string_view message) {
  pv::require(
      take_head(stored.read_head(), message) == ledger_head(expected),
      message);
}

void verify_sequence(
    const pv::Values& ledger_values,
    const pv::Values& primitive_values,
    const std::filesystem::path& path) {
  DatabaseFiles files(path);
  const auto genesis = pv::hex_decode(ledger_values.at("genesis"));
  auto expected = load_ledger(genesis);
  const auto sender_bytes =
      pv::hex_decode(primitive_values.at("account_id"));
  const auto sender =
      tagged_hash<p::AccountId>(sender_bytes);
  pv::require(
      expected.state().accounts.contains(sender),
      "sequence sender is absent from genesis");
  const TransferSigner signer(
      pv::hex_decode(ledger_values.at("raw0")),
      pv::hex_decode(primitive_values.at("rfc8032.seed")));
  SplitMix64 random{kSequenceSeed};
  Coverage coverage;
  std::size_t snapshot_count = 0;
  std::size_t reopen_count = 0;

  {
    auto created = take_ledger(
        ps::create_sqlite_ledger(files.path(), genesis),
        "sequence database create failed");
    verify_head(created, expected, "sequence genesis head mismatch");
    require_snapshot(
        created.create_snapshot(), "sequence genesis snapshot failed");
    ++snapshot_count;
  }

  std::uint64_t height = 1;
  while (height <= kBlockCount) {
    auto stored = take_ledger(
        ps::open_sqlite_ledger(files.path(), genesis),
        "sequence restart failed");
    ++reopen_count;
    verify_head(stored, expected, "sequence restart head mismatch");
    const auto last_height =
        std::min(kBlockCount, height + kRestartInterval - 1);
    for (; height <= last_height; ++height) {
      const auto inputs =
          make_block(random, signer, expected, sender, height);
      auto expected_result = expected.apply_block(height, inputs);
      pv::require(
          std::holds_alternative<p::BlockCommit>(expected_result),
          "sequence kernel block rejected");
      const auto expected_commit =
          std::get<p::BlockCommit>(std::move(expected_result));
      record_coverage(inputs, expected_commit, coverage);

      const auto actual_commit = take_commit(
          stored.apply_block(height, inputs),
          "sequence durable block rejected");
      pv::require(
          same_commit(actual_commit, expected_commit),
          "sequence durable commit diverged");
      verify_head(stored, expected, "sequence durable head diverged");

      if (height % kSnapshotInterval == 0) {
        require_snapshot(
            stored.create_snapshot(),
            "sequence periodic snapshot failed");
        ++snapshot_count;
      }
    }
  }

  {
    auto stored = take_ledger(
        ps::open_sqlite_ledger(files.path(), genesis),
        "sequence final-snapshot reopen failed");
    ++reopen_count;
    verify_head(stored, expected, "sequence final-snapshot head mismatch");
    require_snapshot(
        stored.create_snapshot(), "sequence final snapshot failed");
    ++snapshot_count;
  }
  for (int repeat = 0; repeat < 3; ++repeat) {
    auto reopened = take_ledger(
        ps::open_sqlite_ledger(files.path(), genesis),
        "sequence current-head recovery failed");
    ++reopen_count;
    verify_head(
        reopened, expected, "sequence current-head recovery diverged");
  }

  pv::require(
      expected.state().height == kBlockCount &&
          snapshot_count == 10 && reopen_count == 20,
      "sequence operation count changed");
  pv::require(
      coverage.empty_blocks != 0 &&
          coverage.all_unadmitted_blocks != 0,
      "sequence block-shape coverage incomplete");
  for (const auto count : coverage.admissions) {
    pv::require(count != 0, "sequence admission coverage incomplete");
  }
  for (const auto index : {0U, 1U, 2U, 3U, 6U}) {
    pv::require(
        coverage.receipts[index] != 0,
        "sequence receipt coverage incomplete");
  }

  std::cout << "SQLite seeded sequence tests: passed ("
            << kBlockCount << " blocks, " << snapshot_count
            << " snapshots, " << reopen_count << " reopens)\n";
}

}  // namespace

int main(int argc, char** argv) {
  try {
    pv::require(
        argc == 4,
        "usage: storage_sqlite_sequence_tests "
        "LEDGER_VECTOR PRIMITIVE_VECTOR PATH");
    pv::require(sodium_init() >= 0, "libsodium initialization");
    verify_sequence(
        pv::load_values(argv[1]), pv::load_values(argv[2]), argv[3]);
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "SQLite seeded sequence tests: failed: "
              << error.what() << '\n';
    return 1;
  }
}
