#include "economy_internal.hpp"

#include "protocol/v1/crypto.hpp"

#include <algorithm>
#include <array>
#include <string>

namespace protocol::v8 {
namespace {

namespace i = protocol::v8::internal;

constexpr std::array<std::uint8_t, 4> kGenesisMagic{'P', 'S', 'G', 'N'};

// Version six was the first version to *require* what its predecessors merely
// expected, and version eight inherits the requirement. Versions two through
// five permitted 0 through 21,843 accounts while recording that the
// constitution's no-genesis-allocation rule forces zero; a genesis account would
// be an account with no escrow entry and no identity behind it, which the first
// structural invariant forbids. The field and the bound — 21,842 under version
// eight's wider prefix — stay for layout compatibility and are unreachable.
//
// The fee is still permitted to be zero, and that relaxation is forced rather
// than chosen: with a zero allocation and a nonzero fee no account could pay for
// the first transaction. The first transaction is a registration, which is
// fee-exempt and pays the entry airdrop, so a conforming chain can also open
// with a nonzero fee.
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
  i::append(raw, genesis.dispute_authority_key);
  i::append_u32(raw, genesis.account_count);
  if (raw.size() != kGenesisPrefixBytes) return std::nullopt;
  if (raw.size() > kMaxObjectBytes) return std::nullopt;
  return raw;
}

// **The field order here is the encoding's, not the struct's.** `total_supply`
// is written before `fixed_transfer_fee`, and a decoder that read them in
// declaration order would produce a genesis whose re-encoding differs — which is
// exactly what the round-trip check below refuses.
std::optional<Genesis> decode_genesis(std::span<const std::uint8_t> raw) {
  if (raw.size() != kGenesisPrefixBytes) return std::nullopt;
  if (!std::equal(kGenesisMagic.begin(), kGenesisMagic.end(), raw.begin())) {
    return std::nullopt;
  }
  const auto schema = i::read_u16(raw, 4);
  if (!schema || *schema != kGenesisSchemaVersion) return std::nullopt;

  const auto network_id = i::read_u32(raw, 6);
  const auto supply_limit = i::read_u64(raw, 10);
  const auto total_supply = i::read_u64(raw, 18);
  const auto fixed_transfer_fee = i::read_u64(raw, 26);
  const auto initial_fee_pool = i::read_u64(raw, 34);
  const auto account_count = i::read_u32(raw, 138);
  if (!network_id || !supply_limit || !total_supply || !fixed_transfer_fee ||
      !initial_fee_pool || !account_count) {
    return std::nullopt;
  }

  Genesis genesis;
  genesis.network_id = *network_id;
  genesis.supply_limit = *supply_limit;
  genesis.total_supply = *total_supply;
  genesis.fixed_transfer_fee = *fixed_transfer_fee;
  genesis.initial_fee_pool = *initial_fee_pool;
  if (!i::copy32(raw.subspan(42, 32), genesis.manifest_digest)) {
    return std::nullopt;
  }
  if (!i::copy32(raw.subspan(74, 32), genesis.verifier_key)) {
    return std::nullopt;
  }
  if (!i::copy32(raw.subspan(106, 32), genesis.dispute_authority_key)) {
    return std::nullopt;
  }
  genesis.account_count = *account_count;

  // The whole validity rule, stated once. Anything the encoder would refuse to
  // write, or would write differently, is not this file's genesis.
  const auto reencoded = encode_genesis(genesis);
  if (!reencoded || reencoded->size() != raw.size() ||
      !std::equal(reencoded->begin(), reencoded->end(), raw.begin())) {
    return std::nullopt;
  }
  return genesis;
}

std::optional<Hash> chain_id(const Genesis& genesis) {
  const auto encoded = encode_genesis(genesis);
  if (!encoded) return std::nullopt;
  return protocol::v1::hash(kChainIdLabel, *encoded);
}

// The same fields under an earlier schema version and label, so that "no
// predecessor genesis is the same object" is a claim about two derived
// identifiers rather than about two strings.
//
// **A predecessor's bytes omit the dispute authority key**, because no version
// before eight had one, so the compared object is the 110-octet prefix. That is
// the point of the comparison rather than a shortcut: the two objects are
// different lengths, so no version-eight genesis is readable as an earlier one
// whatever the label does.
std::optional<Hash> predecessor_chain_id(const Genesis& genesis,
                                         std::uint16_t version) {
  if (version < 2 || version > 7) return std::nullopt;
  if (!genesis_is_valid(genesis)) return std::nullopt;

  Bytes raw;
  raw.reserve(kGenesisPrefixBytes - kDisputeAuthorityKeyBytes);
  i::append(raw, std::span<const std::uint8_t>(kGenesisMagic));
  i::append_u16(raw, version);
  i::append_u32(raw, genesis.network_id);
  i::append_u64(raw, genesis.supply_limit);
  i::append_u64(raw, genesis.total_supply);
  i::append_u64(raw, genesis.fixed_transfer_fee);
  i::append_u64(raw, genesis.initial_fee_pool);
  i::append(raw, genesis.manifest_digest);
  i::append(raw, genesis.verifier_key);
  i::append_u32(raw, genesis.account_count);

  const std::string label = "protocol-stack:v" + std::to_string(version) +
                            ":chain-id";
  return protocol::v1::hash(label, raw);
}

}  // namespace protocol::v8
