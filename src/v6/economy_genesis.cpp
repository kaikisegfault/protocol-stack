#include "economy_internal.hpp"

#include "protocol/v1/crypto.hpp"

#include <array>

namespace protocol::v6 {
namespace {

namespace i = protocol::v6::internal;

constexpr std::array<std::uint8_t, 4> kGenesisMagic{'P', 'S', 'G', 'N'};

// Version six is the first version to *require* what its predecessors merely
// expected. Versions two through five permitted 0 through 21,843 accounts while
// recording that the constitution's no-genesis-allocation rule forces zero; a
// version-six genesis account would be an account with no escrow entry and no
// identity behind it, which the first structural invariant forbids. The field
// and the inherited bound stay for layout compatibility and are unreachable.
//
// The fee is still permitted to be zero, and that relaxation is forced rather
// than chosen: with a zero allocation and a nonzero fee no account could pay for
// the first transaction. Under version six the first transaction is a
// registration, which is fee-exempt and pays the entry airdrop, so a conforming
// chain can also open with a nonzero fee.
bool genesis_is_valid(const Genesis& genesis) {
  if (genesis.supply_limit == 0) return false;
  if (genesis.total_supply != 0) return false;
  if (genesis.initial_fee_pool != 0) return false;
  return genesis.account_count == 0;
}

}  // namespace

std::optional<Bytes> encode_genesis(const Genesis& genesis) {
  if (!genesis_is_valid(genesis)) return std::nullopt;

  Bytes raw;
  raw.reserve(kGenesisPrefixBytes);
  i::append(raw, std::span<const std::uint8_t>(kGenesisMagic));
  i::append_u16(raw, kGenesisSchemaVersion);
  i::append_u32(raw, genesis.network_id);
  i::append_u64(raw, genesis.supply_limit);
  i::append_u64(raw, genesis.total_supply);
  i::append_u64(raw, genesis.fixed_transfer_fee);
  i::append_u64(raw, genesis.initial_fee_pool);
  i::append(raw, genesis.manifest_digest);
  i::append(raw, genesis.verifier_key);
  i::append_u32(raw, genesis.account_count);
  if (raw.size() != kGenesisPrefixBytes) return std::nullopt;
  if (raw.size() > kMaxObjectBytes) return std::nullopt;
  return raw;
}

std::optional<Hash> chain_id(const Genesis& genesis) {
  const auto encoded = encode_genesis(genesis);
  if (!encoded) return std::nullopt;
  return protocol::v1::hash(kChainIdLabel, *encoded);
}

}  // namespace protocol::v6
