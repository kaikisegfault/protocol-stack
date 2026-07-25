#include "protocol/storage/archive_v1.hpp"

#include "protocol/storage/snapshot_v1.hpp"
#include "protocol/v1/crypto.hpp"

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <span>
#include <utility>
#include <variant>
#include <vector>

namespace protocol::storage {
namespace {

namespace pv1 = protocol::v1;

constexpr std::array<std::uint8_t, 4> kMagic{'P', 'S', 'A', 'R'};
constexpr std::uint16_t kVersion = 1;
constexpr std::size_t kMaximumGenesisSize = 1'048'576;
constexpr std::size_t kHeaderSize = 146;
constexpr std::size_t kTransactionSize = 200;
constexpr std::size_t kReceiptSize = 47;
constexpr std::size_t kHashSize = 32;
constexpr std::size_t kBlockFixedSize =
    kHeaderSize + kHashSize + 4;
constexpr std::size_t kTransactionRecordSize =
    kTransactionSize + kHashSize + kReceiptSize;
constexpr std::size_t kArchiveFixedSize = 58;
constexpr std::uint32_t kMaximumBlockInputs = 65'535;
constexpr char kDigestDomain[] =
    "protocol-stack:storage:archive-v1";

struct ValidatedHead {
  pv1::Ledger ledger;
  pv1::StateRoot state_root;
};

void append(
    pv1::Bytes& target,
    std::span<const std::uint8_t> bytes) {
  target.insert(target.end(), bytes.begin(), bytes.end());
}

void append_u16(pv1::Bytes& target, std::uint16_t value) {
  target.push_back(static_cast<std::uint8_t>(value >> 8U));
  target.push_back(static_cast<std::uint8_t>(value));
}

void append_u32(pv1::Bytes& target, std::uint32_t value) {
  for (int shift = 24; shift >= 0; shift -= 8) {
    target.push_back(static_cast<std::uint8_t>(value >> shift));
  }
}

void append_u64(pv1::Bytes& target, std::uint64_t value) {
  for (int shift = 56; shift >= 0; shift -= 8) {
    target.push_back(static_cast<std::uint8_t>(value >> shift));
  }
}

std::uint16_t read_u16(
    std::span<const std::uint8_t> input,
    std::size_t offset) {
  return static_cast<std::uint16_t>(
      (static_cast<std::uint16_t>(input[offset]) << 8U) |
      input[offset + 1]);
}

std::uint32_t read_u32(
    std::span<const std::uint8_t> input,
    std::size_t offset) {
  std::uint32_t value = 0;
  for (std::size_t index = 0; index < 4; ++index) {
    value = (value << 8U) | input[offset + index];
  }
  return value;
}

std::uint64_t read_u64(
    std::span<const std::uint8_t> input,
    std::size_t offset) {
  std::uint64_t value = 0;
  for (std::size_t index = 0; index < 8; ++index) {
    value = (value << 8U) | input[offset + index];
  }
  return value;
}

template <typename Tagged>
std::span<const std::uint8_t> tagged_bytes(
    const Tagged& value) noexcept {
  return {value.data(), value.size()};
}

template <typename Tagged>
Tagged read_tagged(
    std::span<const std::uint8_t> input,
    std::size_t offset) {
  pv1::Hash value{};
  std::copy_n(input.begin() + static_cast<std::ptrdiff_t>(offset),
              value.size(), value.begin());
  return Tagged{value};
}

pv1::Hash read_hash(
    std::span<const std::uint8_t> input,
    std::size_t offset) {
  pv1::Hash value{};
  std::copy_n(input.begin() + static_cast<std::ptrdiff_t>(offset),
              value.size(), value.begin());
  return value;
}

bool all_admitted(const pv1::BlockCommit& commit) {
  return std::all_of(
      commit.admissions.begin(), commit.admissions.end(),
      [](const auto& admission) { return !admission.has_value(); });
}

std::variant<ValidatedHead, ArchiveV1Error> validate_archive(
    const ArchiveV1Data& archive) {
  auto loaded = pv1::load_genesis(archive.canonical_genesis);
  if (!std::holds_alternative<pv1::Ledger>(loaded.result)) {
    return ArchiveV1Error::invalid_genesis;
  }
  if constexpr (sizeof(std::size_t) > sizeof(std::uint64_t)) {
    if (archive.blocks.size() >
        std::numeric_limits<std::uint64_t>::max()) {
      return ArchiveV1Error::size_overflow;
    }
  }

  auto ledger = std::get<pv1::Ledger>(std::move(loaded.result));
  for (std::size_t block_index = 0;
       block_index < archive.blocks.size(); ++block_index) {
    const auto& block = archive.blocks[block_index];
    if (block.header.size() != kHeaderSize ||
        block.transactions.size() > kMaximumBlockInputs) {
      return ArchiveV1Error::invalid_history;
    }
    std::vector<pv1::Bytes> transactions;
    std::vector<pv1::TransactionId> transaction_ids;
    std::vector<pv1::Bytes> receipts;
    transactions.reserve(block.transactions.size());
    transaction_ids.reserve(block.transactions.size());
    receipts.reserve(block.transactions.size());
    for (const auto& transaction : block.transactions) {
      if (transaction.transaction.size() != kTransactionSize ||
          transaction.receipt.size() != kReceiptSize) {
        return ArchiveV1Error::invalid_history;
      }
      transactions.push_back(transaction.transaction);
      transaction_ids.push_back(transaction.transaction_id);
      receipts.push_back(transaction.receipt);
    }

    const auto height =
        static_cast<std::uint64_t>(block_index) + 1;
    auto applied = ledger.apply_block(height, transactions);
    if (!std::holds_alternative<pv1::BlockCommit>(applied)) {
      return ArchiveV1Error::invalid_history;
    }
    const auto& commit = std::get<pv1::BlockCommit>(applied);
    if (!all_admitted(commit) ||
        commit.transaction_ids != transaction_ids ||
        commit.encoded_receipts != receipts ||
        commit.header != block.header ||
        commit.block_id != block.block_id) {
      return ArchiveV1Error::invalid_history;
    }
  }

  auto decoded_snapshot = decode_snapshot_v1(
      archive.head_snapshot, ledger.state().parameters);
  if (!std::holds_alternative<DecodedSnapshotV1>(
          decoded_snapshot)) {
    return ArchiveV1Error::snapshot_mismatch;
  }
  auto snapshot =
      std::get<DecodedSnapshotV1>(std::move(decoded_snapshot));
  const auto root = ledger.current_state_root();
  if (!std::holds_alternative<pv1::StateRoot>(root) ||
      snapshot.ledger.state() != ledger.state() ||
      snapshot.state_root != std::get<pv1::StateRoot>(root) ||
      snapshot.ledger.state().height != archive.blocks.size()) {
    return ArchiveV1Error::snapshot_mismatch;
  }
  return ValidatedHead{
      std::move(ledger),
      std::get<pv1::StateRoot>(root),
  };
}

bool checked_add(std::size_t value, std::size_t& total) {
  if (value > std::numeric_limits<std::size_t>::max() - total) {
    return false;
  }
  total += value;
  return true;
}

std::variant<std::size_t, ArchiveV1Error> encoded_size(
    const ArchiveV1Data& archive) {
  if (archive.canonical_genesis.size() > UINT32_MAX) {
    return ArchiveV1Error::size_overflow;
  }
  if constexpr (sizeof(std::size_t) > sizeof(std::uint64_t)) {
    if (archive.head_snapshot.size() >
        std::numeric_limits<std::uint64_t>::max()) {
      return ArchiveV1Error::size_overflow;
    }
  }
  std::size_t total = kArchiveFixedSize;
  if (!checked_add(archive.canonical_genesis.size(), total) ||
      !checked_add(archive.head_snapshot.size(), total)) {
    return ArchiveV1Error::size_overflow;
  }
  for (const auto& block : archive.blocks) {
    if (block.transactions.size() > kMaximumBlockInputs ||
        !checked_add(kBlockFixedSize, total) ||
        block.transactions.size() >
            (std::numeric_limits<std::size_t>::max() - total) /
                kTransactionRecordSize ||
        !checked_add(
            block.transactions.size() * kTransactionRecordSize,
            total)) {
      return ArchiveV1Error::size_overflow;
    }
  }
  return total;
}

bool available(
    std::span<const std::uint8_t> payload,
    std::size_t offset,
    std::size_t size) {
  return offset <= payload.size() && size <= payload.size() - offset;
}

}  // namespace

ArchiveV1EncodeResult encode_archive_v1(
    const ArchiveV1Data& archive) {
  const auto validation = validate_archive(archive);
  if (std::holds_alternative<ArchiveV1Error>(validation)) {
    return std::get<ArchiveV1Error>(validation);
  }
  const auto size_result = encoded_size(archive);
  if (std::holds_alternative<ArchiveV1Error>(size_result)) {
    return std::get<ArchiveV1Error>(size_result);
  }

  pv1::Bytes payload;
  const auto size = std::get<std::size_t>(size_result);
  if (size > payload.max_size()) {
    return ArchiveV1Error::size_overflow;
  }
  payload.reserve(size);
  append(payload, kMagic);
  append_u16(payload, kVersion);
  append_u32(
      payload,
      static_cast<std::uint32_t>(
          archive.canonical_genesis.size()));
  append(payload, archive.canonical_genesis);
  append_u64(
      payload,
      static_cast<std::uint64_t>(archive.blocks.size()));
  for (const auto& block : archive.blocks) {
    append(payload, block.header);
    append(payload, tagged_bytes(block.block_id));
    append_u32(
        payload,
        static_cast<std::uint32_t>(block.transactions.size()));
    for (const auto& transaction : block.transactions) {
      append(payload, transaction.transaction);
      append(payload, tagged_bytes(transaction.transaction_id));
      append(payload, transaction.receipt);
    }
  }
  append_u64(
      payload,
      static_cast<std::uint64_t>(archive.head_snapshot.size()));
  append(payload, archive.head_snapshot);
  const auto digest = pv1::hash(kDigestDomain, payload);
  append(payload, digest);
  return EncodedArchiveV1{std::move(payload), digest};
}

ArchiveV1DecodeResult decode_archive_v1(
    std::span<const std::uint8_t> payload) {
  if (payload.size() < kArchiveFixedSize ||
      !std::equal(kMagic.begin(), kMagic.end(), payload.begin())) {
    return ArchiveV1Error::malformed;
  }
  if (read_u16(payload, 4) != kVersion) {
    return ArchiveV1Error::unsupported_version;
  }

  const auto genesis_size = read_u32(payload, 6);
  if (genesis_size > kMaximumGenesisSize) {
    return ArchiveV1Error::size_overflow;
  }
  std::size_t offset = 10;
  if (!available(payload, offset, genesis_size)) {
    return ArchiveV1Error::malformed;
  }
  ArchiveV1Data archive;
  archive.canonical_genesis.assign(
      payload.begin() + static_cast<std::ptrdiff_t>(offset),
      payload.begin() +
          static_cast<std::ptrdiff_t>(offset + genesis_size));
  offset += genesis_size;
  if (!available(payload, offset, 8)) {
    return ArchiveV1Error::malformed;
  }
  const auto block_count = read_u64(payload, offset);
  offset += 8;
  if constexpr (sizeof(std::size_t) < sizeof(std::uint64_t)) {
    if (block_count >
        std::numeric_limits<std::size_t>::max()) {
      return ArchiveV1Error::size_overflow;
    }
  }
  if (!available(payload, offset, 8 + kHashSize) ||
      block_count >
          (payload.size() - offset - 8 - kHashSize) /
              kBlockFixedSize) {
    return ArchiveV1Error::malformed;
  }

  for (std::uint64_t index = 0; index < block_count; ++index) {
    if (!available(
            payload, offset, kBlockFixedSize + 8 + kHashSize)) {
      return ArchiveV1Error::malformed;
    }
    ArchiveBlockV1 block;
    block.header.assign(
        payload.begin() + static_cast<std::ptrdiff_t>(offset),
        payload.begin() +
            static_cast<std::ptrdiff_t>(offset + kHeaderSize));
    offset += kHeaderSize;
    block.block_id =
        read_tagged<pv1::BlockId>(payload, offset);
    offset += kHashSize;
    const auto admitted_count = read_u32(payload, offset);
    offset += 4;
    if (admitted_count > kMaximumBlockInputs ||
        admitted_count >
            (payload.size() - offset) / kTransactionRecordSize ||
        !available(
            payload, offset,
            static_cast<std::size_t>(admitted_count) *
                kTransactionRecordSize +
                8 + kHashSize)) {
      return admitted_count > kMaximumBlockInputs
                 ? ArchiveV1Error::size_overflow
                 : ArchiveV1Error::malformed;
    }
    block.transactions.reserve(admitted_count);
    for (std::uint32_t ordinal = 0;
         ordinal < admitted_count; ++ordinal) {
      ArchiveTransactionV1 transaction;
      transaction.transaction.assign(
          payload.begin() + static_cast<std::ptrdiff_t>(offset),
          payload.begin() +
              static_cast<std::ptrdiff_t>(
                  offset + kTransactionSize));
      offset += kTransactionSize;
      transaction.transaction_id =
          read_tagged<pv1::TransactionId>(payload, offset);
      offset += kHashSize;
      transaction.receipt.assign(
          payload.begin() + static_cast<std::ptrdiff_t>(offset),
          payload.begin() +
              static_cast<std::ptrdiff_t>(
                  offset + kReceiptSize));
      offset += kReceiptSize;
      block.transactions.push_back(std::move(transaction));
    }
    archive.blocks.push_back(std::move(block));
  }

  if (!available(payload, offset, 8 + kHashSize)) {
    return ArchiveV1Error::malformed;
  }
  const auto snapshot_size_value = read_u64(payload, offset);
  offset += 8;
  if (snapshot_size_value >
      std::numeric_limits<std::size_t>::max()) {
    return ArchiveV1Error::size_overflow;
  }
  const auto snapshot_size =
      static_cast<std::size_t>(snapshot_size_value);
  if (snapshot_size >
          std::numeric_limits<std::size_t>::max() - kHashSize) {
    return ArchiveV1Error::size_overflow;
  }
  if (!available(
          payload, offset, snapshot_size + kHashSize) ||
      offset + snapshot_size + kHashSize != payload.size()) {
    return ArchiveV1Error::malformed;
  }
  archive.head_snapshot.assign(
      payload.begin() + static_cast<std::ptrdiff_t>(offset),
      payload.begin() +
          static_cast<std::ptrdiff_t>(offset + snapshot_size));
  offset += snapshot_size;
  const auto encoded_digest =
      read_hash(payload, offset);
  const auto computed_digest = pv1::hash(
      kDigestDomain, payload.first(payload.size() - kHashSize));
  if (encoded_digest != computed_digest) {
    return ArchiveV1Error::digest_mismatch;
  }

  auto validation = validate_archive(archive);
  if (std::holds_alternative<ArchiveV1Error>(validation)) {
    return std::get<ArchiveV1Error>(validation);
  }
  auto head = std::get<ValidatedHead>(std::move(validation));
  return DecodedArchiveV1{
      std::move(archive),
      std::move(head.ledger),
      head.state_root,
      encoded_digest,
  };
}

}  // namespace protocol::storage
