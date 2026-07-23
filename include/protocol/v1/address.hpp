#pragma once

#include "protocol/v1/types.hpp"

#include <optional>
#include <string>
#include <string_view>

namespace protocol::v1 {

// Returns no value when hrp is not a canonical protocol HRP.
std::optional<std::string> encode_address(const AccountId& account_id,
                                          std::string_view hrp);

// expected_hrp is a configured chain parameter. The decoder accepts only the
// canonical lowercase Bech32m form for that HRP and payload version 1.
std::optional<AccountId> decode_address(std::string_view address,
                                        std::string_view expected_hrp);

}  // namespace protocol::v1
