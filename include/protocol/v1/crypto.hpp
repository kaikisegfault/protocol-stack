#pragma once

#include "protocol/v1/types.hpp"

#include <span>
#include <string_view>

namespace protocol::v1 {

Hash hash(std::string_view domain_label,
          std::span<const std::uint8_t> payload = {});

bool strict_ed25519_verify(std::span<const std::uint8_t> public_key,
                           std::span<const std::uint8_t> message,
                           std::span<const std::uint8_t> signature);

}  // namespace protocol::v1
