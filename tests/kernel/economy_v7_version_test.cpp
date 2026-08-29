// Version seven's own identity: the four re-versioned constructions, the labels
// it keeps, the manifest binding that moved, and version-seven genesis.
//
// **The four re-versioned constructions are checked against version six's own
// accepted file as well as against version seven's**, because a non-collision
// is a claim about two real artifacts rather than about two strings. The
// version-six empty economy root and state root this file compares against are
// read from `test-vectors/economy-transition-v6.txt`, which is the file that
// accepted them, so the comparison is against the real predecessor rather than
// against a restatement of it.

#include "economy_v7_fixture.hpp"

namespace economy_v7_fixture {
namespace {

v7::Genesis identity_genesis(const pv::Values& manifest) {
  v7::Genesis genesis;
  genesis.network_id = kIdentityNetworkId;
  genesis.supply_limit = kMaximumSupplyAtomic;
  genesis.fixed_transfer_fee = kIdentityFixedFee;
  genesis.manifest_digest = from_hex(manifest.at("manifest_digest"));
  genesis.verifier_key = kIdentityVerifierKey;
  return genesis;
}

void verify_labels(const pv::Values& values) {
  pv::require(expect_text(values, "version.chain_id_label") == v7::kChainIdLabel,
              "the chain-ID domain label");
  pv::require(expect_text(values, "version.state_root_label") == v7::kStateRootLabel,
              "the state-root domain label");
  pv::require(expect_text(values, "version.economy_tree_prefix") ==
                  v7::kEconomyTreePrefix,
              "the economy tree prefix");
  pv::require(expect_number(values, "version.state_root_schema_version") ==
                  v7::kStateRootSchemaVersion,
              "the state-root schema version");
  pv::require(expect_number(values, "version.genesis_schema_version") ==
                  v7::kGenesisSchemaVersion,
              "the genesis schema version");
  pv::require(expect_number(values, "version.receipt_version") == v7::kReceiptVersion,
              "the receipt version");

  // A label names the artifact it derives, and none of these artifacts changed.
  // The six HUB messages keep their version-six labels too; that is established
  // by the encoding checks, which reproduce version six's own recorded message
  // bytes rather than comparing a string to a string.
  pv::require(expect_text(values, "version.retained.account_label") ==
                  v7::kAccountLabel,
              "the account derivation label is retained");
  pv::require(expect_text(values, "version.retained.escrow_label") == v7::kEscrowLabel,
              "the escrow derivation label is retained");
  pv::require(expect_text(values, "version.retained.transaction_sign_label") ==
                  v7::kSignLabel,
              "the transaction signing label is retained");
  pv::require(expect_text(values, "version.retained.transaction_id_label") ==
                  v7::kTransactionIdLabel,
              "the transaction ID label is retained");
  expect_true(values, "version.retained.every_hub_message_label_is_version_six");
}

void verify_manifest_binding(const pv::Values& values, const pv::Values& manifest) {
  // The binding moves to version three and the economy does not: ADR 0053's
  // manifest renames one channel and moves no cap, leg, subtotal, or total.
  pv::require(expect_text(values, "version.manifest_digest") ==
                  manifest.at("manifest_digest"),
              "the bound digest is the accepted version-three manifest's");
  expect_true(values, "version.manifest_digest_differs_from_the_superseded_one");
  pv::require(expect_text(values, "version.channel9_identifier") ==
                  manifest.at("channel9.id"),
              "channel 9's identifier is the accepted manifest's");
  expect_true(values, "version.channel9_identifier_is_the_only_one_that_moved");

  for (std::uint8_t channel = 0; channel < 5; ++channel) {
    const auto name = manifest.at("channel" + std::to_string(channel) + ".id");
    pv::require(v7::base_permission_leg(channel) ==
                    std::stoull(manifest.at("base_permission." + name)),
                "a base permission leg is the accepted manifest's");
    expect_true(values, "version.leg" + std::to_string(channel) +
                            "_matches_the_accepted_manifest_file");
  }
  for (std::uint8_t channel = 0; channel < 10; ++channel) {
    const auto name = manifest.at("channel" + std::to_string(channel) + ".id");
    pv::require(v7::channel_cap(channel) ==
                    std::stoull(manifest.at("channel" + std::to_string(channel) +
                                            ".cap")),
                "a channel cap is the accepted manifest's");
    (void)name;
  }
}

void verify_non_collision(const pv::Values& values, const pv::Values& carried,
                          const pv::Values& manifest) {
  const auto genesis = identity_genesis(manifest);
  pv::require(v7::encode_genesis(genesis).has_value(), "the identity genesis encodes");
  pv::require(v7::encode_genesis(genesis)->size() ==
                  expect_size(values, "version.genesis_prefix_bytes"),
              "the genesis prefix width");

  const auto identifier = v7::chain_id(genesis);
  pv::require(identifier.has_value(), "the chain identifier derives");
  pv::require(hex(*identifier) == expect_text(values, "version.chain_id"),
              "version seven's chain identifier");

  const auto empty = v7::economy_root({});
  pv::require(empty.has_value(), "the empty economy root derives");
  pv::require(hex(*empty) == expect_text(values, "version.economy_empty_root"),
              "version seven's empty economy root");
  // Against the real predecessor rather than a restatement of it: version six's
  // own accepted file records its empty economy root, and the two trees differ
  // because their prefixes do.
  pv::require(hex(*empty) != carried.at("tree.empty_root_hex"),
              "the version-seven economy tree does not collide with version six's");

  const auto entries = genesis_economy(genesis.verifier_key);
  v7::StateSummary summary;
  summary.chain_id = *identifier;
  summary.height = 0;
  summary.supply_limit = genesis.supply_limit;
  summary.total_supply = 0;
  summary.fee_pool_balance = 0;
  const auto root = v7::state_root(summary, {}, entries);
  pv::require(root.has_value(), "the version-seven genesis state root derives");
  pv::require(hex(*root) == expect_text(values, "version.state_root"),
              "version seven's state root over its own genesis");

  for (const auto* key : {"version.chain_id_differs_from_v2",
                          "version.chain_id_differs_from_v3",
                          "version.chain_id_differs_from_v4",
                          "version.chain_id_differs_from_v5",
                          "version.chain_id_differs_from_v6",
                          "version.state_root_differs_from_v1",
                          "version.state_root_differs_from_v2",
                          "version.state_root_differs_from_v3",
                          "version.state_root_differs_from_v4",
                          "version.state_root_differs_from_v5",
                          "version.state_root_differs_from_v6"}) {
    expect_true(values, key);
  }
}

void verify_genesis(const pv::Values& values, const pv::Values& manifest) {
  const auto genesis = identity_genesis(manifest);
  const auto entries = genesis_economy(genesis.verifier_key);
  pv::require(entries.size() == expect_size(values, "genesis.economy_entry_count"),
              "genesis writes fourteen economy entries");
  pv::require(entries.size() == 23 - 10 + 1,
              "nine fewer than version six: ten carries out, one pool in");
  expect_true(values, "genesis.replaces_ten_carry_entries_with_one");

  bool pool_written = false;
  for (const auto& entry : entries) {
    pv::require(entry.key.front() != 7, "genesis writes no carry entry");
    if (entry.key.front() != static_cast<std::uint8_t>(v7::Entry::recovery_pool)) {
      continue;
    }
    pv::require(!pool_written, "exactly one recovery pool entry exists");
    pool_written = true;
    const auto legs = v7::decode_recovery_pool_value(entry.value);
    pv::require(legs.has_value(), "the recovery pool entry decodes");
    pv::require(*legs == v7::RecoveryPool{}, "the recovery pool opens empty");
  }
  pv::require(pool_written, "genesis writes one recovery pool entry");
  expect_true(values, "genesis.writes_one_recovery_pool_entry");
  expect_true(values, "genesis.the_recovery_pool_opens_empty");
  expect_true(values, "genesis.writes_no_carry_entry");

  const auto encoded = v7::encode_genesis(genesis);
  pv::require(encoded.has_value(), "the founder genesis encodes");
  pv::require(encoded->size() == expect_size(values, "genesis.prefix_bytes"),
              "the genesis prefix width");
  pv::require(expect_number(values, "genesis.schema_version") ==
                  v7::kGenesisSchemaVersion,
              "the genesis schema version");

  // The inherited object bound, recorded and unreachable: no version-seven
  // genesis can carry an account at all.
  pv::require(v7::kMaxGenesisAccounts ==
                  expect_size(values, "genesis.max_accounts_admitted"),
              "the inherited account bound");
  pv::require(v7::kGenesisPrefixBytes +
                      v7::kAccountEntryBytes * v7::kMaxGenesisAccounts ==
                  expect_size(values, "genesis.max_accounts_within_bytes"),
              "the bound stays within the canonical object limit");
  pv::require(v7::kGenesisPrefixBytes +
                      v7::kAccountEntryBytes * (v7::kMaxGenesisAccounts + 1) ==
                  expect_size(values, "genesis.max_accounts_beyond_bytes"),
              "and one entry beyond it does not");

  auto rejected = genesis;
  rejected.account_count = 1;
  pv::require(!v7::encode_genesis(rejected).has_value(), "any account entry");
  expect_true(values, "genesis.accounts_are_required_to_be_zero");
  rejected = genesis;
  rejected.supply_limit = 0;
  pv::require(!v7::encode_genesis(rejected).has_value(), "a zero supply limit");
  rejected = genesis;
  rejected.total_supply = 1;
  pv::require(!v7::encode_genesis(rejected).has_value(), "a nonzero total supply");
  rejected = genesis;
  rejected.initial_fee_pool = 1;
  pv::require(!v7::encode_genesis(rejected).has_value(), "a nonzero fee pool");
}

}  // namespace

void verify_version(const pv::Values& values, const pv::Values& carried,
                    const pv::Values& manifest) {
  verify_labels(values);
  verify_manifest_binding(values, manifest);
  verify_non_collision(values, carried, manifest);
  verify_genesis(values, manifest);
}

}  // namespace economy_v7_fixture
