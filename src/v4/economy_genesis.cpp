#include "economy_internal.hpp"

#include "protocol/v1/crypto.hpp"

#include <array>
#include <limits>

namespace protocol::v4 {
namespace {

namespace i = protocol::v4::internal;

constexpr std::array<std::uint8_t, 4> kGenesisMagic{'P', 'S', 'G', 'N'};

// Three of version one's genesis requirements relax, and each is forced by the
// constitution's rule that native units enter circulation only through issuance
// permissions and capped direct-mint channels: a conforming chain opens with
// zero total supply and zero accounts, and the fixed fee is permitted to be zero
// as the consequence. None of those three is checked here, deliberately.
bool accounts_are_valid(const Genesis& genesis) {
  if (genesis.accounts.size() > kMaxGenesisAccounts) return false;
  const Octets32* previous = nullptr;
  std::uint64_t accumulated = genesis.initial_fee_pool;
  for (const auto& account : genesis.accounts) {
    if (previous != nullptr && !(*previous < account.account_id)) return false;
    previous = &account.account_id;
    if (account.balance == 0) return false;
    if (account.nonce != 0) return false;
    if (accumulated > std::numeric_limits<std::uint64_t>::max() - account.balance) {
      return false;
    }
    accumulated += account.balance;
  }
  return accumulated == genesis.total_supply;
}

}  // namespace

std::optional<Bytes> encode_genesis(const Genesis& genesis) {
  if (genesis.supply_limit == 0) return std::nullopt;
  if (genesis.total_supply > genesis.supply_limit) return std::nullopt;
  if (!accounts_are_valid(genesis)) return std::nullopt;

  Bytes raw;
  raw.reserve(kGenesisPrefixBytes + kAccountEntryBytes * genesis.accounts.size());
  i::append(raw, std::span<const std::uint8_t>(kGenesisMagic));
  i::append_u16(raw, kGenesisSchemaVersion);
  i::append_u32(raw, genesis.network_id);
  i::append_u64(raw, genesis.supply_limit);
  i::append_u64(raw, genesis.total_supply);
  i::append_u64(raw, genesis.fixed_transfer_fee);
  i::append_u64(raw, genesis.initial_fee_pool);
  i::append(raw, genesis.manifest_digest);
  i::append(raw, genesis.verifier_key);
  i::append_u32(raw, static_cast<std::uint32_t>(genesis.accounts.size()));
  if (raw.size() != kGenesisPrefixBytes) return std::nullopt;

  for (const auto& account : genesis.accounts) {
    i::append(raw, account.account_id);
    i::append_u64(raw, account.balance);
    i::append_u64(raw, account.nonce);
  }
  if (raw.size() > kMaxObjectBytes) return std::nullopt;
  return raw;
}

std::optional<Hash> chain_id(const Genesis& genesis) {
  const auto encoded = encode_genesis(genesis);
  if (!encoded) return std::nullopt;
  return protocol::v1::hash(kChainIdLabel, *encoded);
}

}  // namespace protocol::v4
