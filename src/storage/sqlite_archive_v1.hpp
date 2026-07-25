#pragma once

#include "sqlite_connection.hpp"

#include "protocol/storage/archive_v1.hpp"
#include "protocol/storage/snapshot_v1.hpp"

#include <span>

namespace protocol::storage::internal {

ArchiveV1Data load_archive_v1(
    Connection& connection,
    std::span<const std::uint8_t> canonical_genesis,
    const EncodedSnapshotV1& head_snapshot);

}  // namespace protocol::storage::internal
