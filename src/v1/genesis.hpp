#pragma once

#include "protocol/v1/types.hpp"

#include <cstdint>
#include <span>
#include <variant>

namespace protocol::v1::internal {

using GenesisDecode = std::variant<State, GenesisError>;

GenesisDecode decode_genesis(
    std::span<const std::uint8_t> canonical_genesis);

}  // namespace protocol::v1::internal
