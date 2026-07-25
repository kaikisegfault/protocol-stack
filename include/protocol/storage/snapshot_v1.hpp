#pragma once

#include "protocol/v1/ledger.hpp"

#include <cstdint>
#include <span>
#include <variant>

namespace protocol::storage {

enum class SnapshotV1Error : std::uint8_t {
  malformed = 1,
  unsupported_version = 2,
  size_overflow = 3,
  digest_mismatch = 4,
  immutable_parameters_mismatch = 5,
  invalid_state = 6,
  state_root_mismatch = 7,
};

struct EncodedSnapshotV1 {
  protocol::v1::Bytes payload;
  protocol::v1::StateRoot state_root;
  protocol::v1::Hash digest;

  bool operator==(const EncodedSnapshotV1&) const = default;
};

struct DecodedSnapshotV1 {
  protocol::v1::Ledger ledger;
  protocol::v1::StateRoot state_root;
  protocol::v1::Hash digest;
};

using SnapshotV1EncodeResult =
    std::variant<EncodedSnapshotV1, SnapshotV1Error>;
using SnapshotV1DecodeResult =
    std::variant<DecodedSnapshotV1, SnapshotV1Error>;

SnapshotV1EncodeResult encode_snapshot_v1(
    const protocol::v1::Ledger& ledger);

SnapshotV1DecodeResult decode_snapshot_v1(
    std::span<const std::uint8_t> payload,
    const protocol::v1::Parameters& expected_parameters);

}  // namespace protocol::storage
