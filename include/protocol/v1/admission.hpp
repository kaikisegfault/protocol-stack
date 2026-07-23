#pragma once

#include "protocol/v1/types.hpp"

#include <span>

namespace protocol::v1 {

Admission admit_transfer(std::span<const std::uint8_t> raw_transaction,
                         const ChainId& expected_chain_id);

}  // namespace protocol::v1
