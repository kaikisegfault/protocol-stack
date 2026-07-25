#pragma once

#include "protocol/v1/ledger.hpp"

#include <cstdint>
#include <span>
#include <variant>
#include <vector>

namespace protocol::storage {

enum class ArchiveV1Error : std::uint8_t {
  malformed = 1,
  unsupported_version = 2,
  size_overflow = 3,
  digest_mismatch = 4,
  invalid_genesis = 5,
  invalid_history = 6,
  snapshot_mismatch = 7,
};

struct ArchiveTransactionV1 {
  protocol::v1::Bytes transaction;
  protocol::v1::TransactionId transaction_id;
  protocol::v1::Bytes receipt;

  bool operator==(const ArchiveTransactionV1&) const = default;
};

struct ArchiveBlockV1 {
  protocol::v1::Bytes header;
  protocol::v1::BlockId block_id;
  std::vector<ArchiveTransactionV1> transactions;

  bool operator==(const ArchiveBlockV1&) const = default;
};

struct ArchiveV1Data {
  protocol::v1::Bytes canonical_genesis;
  std::vector<ArchiveBlockV1> blocks;
  protocol::v1::Bytes head_snapshot;

  bool operator==(const ArchiveV1Data&) const = default;
};

struct EncodedArchiveV1 {
  protocol::v1::Bytes payload;
  protocol::v1::Hash digest;

  bool operator==(const EncodedArchiveV1&) const = default;
};

struct DecodedArchiveV1 {
  ArchiveV1Data data;
  protocol::v1::Ledger ledger;
  protocol::v1::StateRoot state_root;
  protocol::v1::Hash digest;
};

using ArchiveV1EncodeResult =
    std::variant<EncodedArchiveV1, ArchiveV1Error>;
using ArchiveV1DecodeResult =
    std::variant<DecodedArchiveV1, ArchiveV1Error>;

ArchiveV1EncodeResult encode_archive_v1(
    const ArchiveV1Data& archive);

ArchiveV1DecodeResult decode_archive_v1(
    std::span<const std::uint8_t> payload);

}  // namespace protocol::storage
