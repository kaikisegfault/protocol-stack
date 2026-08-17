#pragma once

// The accepted version-one account derivation, in one place.
//
// `H(D("protocol-stack:v1:account") || 0x01 || ed25519_public_key)` is what a
// public-key hash is, and four contract versions have preserved it. Version six
// preserves the derivation and moves what it names, from an account to a signer,
// so the kernel needs it from two translation units rather than one.
//
// It is declared here rather than copied because a second implementation of one
// derivation is a second place for it to drift, and the drift would be silent:
// both copies would agree with themselves.

#include "protocol/v1/types.hpp"

#include <span>

namespace protocol::v1::internal {

AccountId account_id_from_public_key(std::span<const std::uint8_t> public_key);

}  // namespace protocol::v1::internal
