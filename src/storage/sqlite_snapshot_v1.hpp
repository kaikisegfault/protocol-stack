#pragma once

#include "sqlite_connection.hpp"

#include "protocol/storage/snapshot_v1.hpp"

#include <optional>

namespace protocol::storage::internal {

std::optional<DecodedSnapshotV1> load_snapshot_v1(
    Connection& connection,
    const protocol::v1::Parameters& expected_parameters);

void persist_snapshot_v1(
    Connection& connection,
    const protocol::v1::Ledger& ledger,
    const EncodedSnapshotV1& snapshot);

}  // namespace protocol::storage::internal
