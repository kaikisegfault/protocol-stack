#pragma once

#include "sqlite_connection.hpp"

#include "protocol/v1/ledger.hpp"

#include <cstdint>
#include <span>

namespace protocol::storage::internal {

void persist_block_v1(
    Connection& connection,
    const protocol::v1::State& previous_state,
    const protocol::v1::State& resulting_state,
    std::span<const protocol::v1::Bytes> raw_transactions,
    const protocol::v1::BlockCommit& commit);

protocol::v1::Ledger replay_history_v1(
    Connection& connection,
    const protocol::v1::Ledger& trusted_genesis_ledger);

}  // namespace protocol::storage::internal
