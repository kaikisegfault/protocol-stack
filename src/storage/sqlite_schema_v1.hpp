#pragma once

#include "sqlite_connection.hpp"

#include "protocol/v1/ledger.hpp"

#include <cstdint>
#include <span>

namespace protocol::storage::internal {

void install_schema_v1(
    Connection& connection,
    std::span<const std::uint8_t> canonical_genesis,
    const protocol::v1::Ledger& genesis_ledger,
    const protocol::v1::StateRoot& genesis_root);

void validate_integrity(Connection& connection);
void validate_schema_v1(Connection& connection);
void validate_stored_genesis(
    Connection& connection,
    std::span<const std::uint8_t> expected_genesis,
    const protocol::v1::Ledger& trusted_genesis_ledger,
    const protocol::v1::StateRoot& trusted_genesis_root);

protocol::v1::Ledger load_materialized_ledger(
    Connection& connection,
    std::span<const std::uint8_t> expected_genesis,
    const protocol::v1::Ledger& trusted_genesis_ledger,
    const protocol::v1::StateRoot& trusted_genesis_root,
    const protocol::v1::Ledger& expected_ledger,
    const protocol::v1::StateRoot& expected_root);

}  // namespace protocol::storage::internal
