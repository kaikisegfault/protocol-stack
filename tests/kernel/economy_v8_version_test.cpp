// Version eight's own identity: the three re-versioned constructions and two
// new labels, the manifest binding that does not move, version-eight genesis,
// and the seven non-collisions.
//
// **Each non-collision is required separately**, because distinct labels are
// strings rather than a chain: refusing a collision with version seven implies
// nothing about version four. Both sides of every comparison are derived here
// — the earlier construction is recomputed over the same inputs rather than
// read as a recorded digest — so the claim is about two real artifacts.

#include "economy_v8_fixture.hpp"

namespace economy_v8_fixture {
namespace {

// Every version version eight must not collide with. Version one is a root
// claim only: it has no economy tree and therefore no chain identity of this
// shape, which is why the genesis loop starts at two and the root loop at one.
constexpr std::uint16_t kPredecessors[] = {1, 2, 3, 4, 5, 6, 7};

void verify_labels(const pv::Values& values) {
  pv::require(expect_text(values, "version.chain_id_label") == v8::kChainIdLabel,
              "the chain-ID domain label");
  pv::require(expect_text(values, "version.state_root_label") == v8::kStateRootLabel,
              "the state-root domain label");
  pv::require(expect_text(values, "version.economy_tree_prefix") ==
                  v8::kEconomyTreePrefix,
              "the economy tree prefix");
  pv::require(expect_text(values, "version.challenge_label") == v8::kChallengeLabel,
              "the challenge selection label");
  pv::require(expect_text(values, "version.dispute_label") == v8::kDisputeLabel,
              "the dispute message label");
  pv::require(expect_number(values, "version.state_root_schema_version") ==
                  v8::kStateRootSchemaVersion,
              "the state-root schema version");
  pv::require(expect_number(values, "version.genesis_schema_version") ==
                  v8::kGenesisSchemaVersion,
              "the genesis schema version");
  pv::require(expect_number(values, "version.receipt_version") == v8::kReceiptVersion,
              "the receipt version");

  // A label names the artifact it derives, and none of these artifacts
  // changed. The claim about the six HUB messages is checked as bytes rather
  // than as a string in the kinds translation unit, which reproduces version
  // six's own recorded message.
  pv::require(expect_text(values, "version.retained.account_label") ==
                  v8::kAccountLabel,
              "the account derivation label is retained");
  pv::require(expect_text(values, "version.retained.escrow_label") == v8::kEscrowLabel,
              "the escrow derivation label is retained");
  pv::require(expect_text(values, "version.retained.sign_label") == v8::kSignLabel,
              "the transaction signing label is retained");
  pv::require(expect_text(values, "version.retained.tx_id_label") ==
                  v8::kTransactionIdLabel,
              "the transaction ID label is retained");
}

// Version eight changes no founder-directed figure, and each is compared
// against the accepted file that fixes it rather than against a restatement.
void verify_manifest_binding(const pv::Values& values, const pv::Values& carried,
                             const pv::Values& manifest) {
  pv::require(expect_text(values, "manifest.digest") ==
                  expect_text(manifest, "manifest_digest"),
              "the bound digest is the accepted version-three manifest's");
  pv::require(expect_text(values, "manifest.digest") ==
                  expect_text(carried, "version.manifest_digest"),
              "the binding is the one version seven already made");
  expect_true(values, "manifest.binding_is_version_seven_s");
  // The referral leg is the manifest's own figure. It has no version-eight
  // codec constant to compare against — it is the ledger's, and M3.13o's
  // execution target checks it there — so the check that belongs here is that
  // the recorded figure is still the accepted manifest's.
  pv::require(expect_number(values, "manifest.referral_leg_atomic") ==
                  expect_number(manifest, "referral_benefit.amount"),
              "the referral leg is the accepted manifest's");
  pv::require(expect_number(values, "manifest.issuance_cycles_per_seat") ==
                  v8::kVerifiedUserCycles,
              "the issuance period is unchanged");
}

// The decoder is the encoder's inverse, and the round trip is the claim.
//
// **The distinctive fee is deliberate.** `total_supply` is written *before*
// `fixed_transfer_fee`, which is not the order the struct declares them, so a
// decoder that read the two in declaration order would put the fee where the
// supply belongs. A zero fee would hide that; this one does not.
void verify_genesis_decoding(const v8::Genesis& founder) {
  auto genesis = founder;
  genesis.fixed_transfer_fee = 0x0102030405060708ULL;
  const auto encoded = v8::encode_genesis(genesis);
  pv::require(encoded.has_value(), "the probe genesis encodes");

  const auto decoded = v8::decode_genesis(*encoded);
  pv::require(decoded.has_value(), "the probe genesis decodes");
  pv::require(decoded->network_id == genesis.network_id,
              "the decoded network identifier");
  pv::require(decoded->supply_limit == genesis.supply_limit,
              "the decoded supply limit");
  pv::require(decoded->total_supply == genesis.total_supply,
              "the decoded total supply");
  pv::require(decoded->fixed_transfer_fee == genesis.fixed_transfer_fee,
              "the decoded transfer fee");
  pv::require(decoded->initial_fee_pool == genesis.initial_fee_pool,
              "the decoded fee pool");
  pv::require(decoded->manifest_digest == genesis.manifest_digest,
              "the decoded manifest digest");
  pv::require(decoded->verifier_key == genesis.verifier_key,
              "the decoded verifier key");
  pv::require(decoded->dispute_authority_key == genesis.dispute_authority_key,
              "the decoded dispute authority key");
  pv::require(decoded->account_count == genesis.account_count,
              "the decoded account count");
  pv::require(v8::chain_id(*decoded) == v8::chain_id(genesis),
              "the decoded genesis derives the same chain identity");

  // A file one octet short or one octet long is not this genesis, and a
  // version-seven file is 32 octets shorter, so neither decodes as the other.
  auto short_bytes = *encoded;
  short_bytes.pop_back();
  pv::require(!v8::decode_genesis(short_bytes).has_value(), "a short genesis");
  auto long_bytes = *encoded;
  long_bytes.push_back(0);
  pv::require(!v8::decode_genesis(long_bytes).has_value(), "a long genesis");

  auto wrong_magic = *encoded;
  wrong_magic[0] ^= 0x01;
  pv::require(!v8::decode_genesis(wrong_magic).has_value(), "a foreign magic");
  auto wrong_version = *encoded;
  wrong_version[5] = 7;
  pv::require(!v8::decode_genesis(wrong_version).has_value(),
              "an earlier schema version");

  // The two keys are adjacent, so a decoder that read them in the wrong order
  // would swap two 32-octet fields silently. Perturbing the second one is what
  // makes the offset checkable rather than assumed.
  auto moved_key = *encoded;
  moved_key[106] ^= 0x01;
  const auto perturbed = v8::decode_genesis(moved_key);
  pv::require(perturbed.has_value(), "a perturbed dispute key is still a genesis");
  pv::require(perturbed->verifier_key == genesis.verifier_key,
              "and it did not disturb the verifier key");
  pv::require(perturbed->dispute_authority_key != genesis.dispute_authority_key,
              "and it did move the dispute authority key");

  // And every field the encoder refuses to write, the decoder refuses to read,
  // because the decoder states the rule exactly once: by re-encoding.
  auto nonzero_supply = *encoded;
  nonzero_supply[25] = 1;
  pv::require(!v8::decode_genesis(nonzero_supply).has_value(),
              "a nonzero total supply in a file");
  auto nonzero_pool = *encoded;
  nonzero_pool[41] = 1;
  pv::require(!v8::decode_genesis(nonzero_pool).has_value(),
              "a nonzero fee pool in a file");
  auto with_accounts = *encoded;
  with_accounts[141] = 1;
  pv::require(!v8::decode_genesis(with_accounts).has_value(),
              "an account count in a file");
  auto zero_limit = *encoded;
  for (std::size_t index = 10; index < 18; ++index) zero_limit[index] = 0;
  pv::require(!v8::decode_genesis(zero_limit).has_value(),
              "a zero supply limit in a file");
}

void verify_genesis(const pv::Values& values, const pv::Values& carried,
                    const pv::Values& manifest) {
  const auto genesis =
      fixture_genesis(from_hex(expect_text(manifest, "manifest_digest")));
  const auto encoded = v8::encode_genesis(genesis);
  pv::require(encoded.has_value(), "the fixture genesis encodes");
  pv::require(encoded->size() == expect_size(values, "genesis.prefix_bytes"),
              "the genesis prefix width");
  pv::require(encoded->size() == v8::kGenesisPrefixBytes, "and it is the constant");
  pv::require(hex(*encoded) == expect_text(values, "genesis.bytes"),
              "the recorded genesis bytes");

  const auto identifier = v8::chain_id(genesis);
  pv::require(identifier.has_value(), "the chain identifier derives");
  pv::require(hex(*identifier) == expect_text(values, "genesis.chain_id"),
              "version eight's chain identifier");

  // The key sits immediately after the verifier key, which is checked by
  // finding it in the encoded bytes rather than by restating the offset.
  const auto offset = expect_size(values, "genesis.dispute_authority_key_offset");
  pv::require(std::equal(kDisputeAuthorityKey.begin(), kDisputeAuthorityKey.end(),
                         encoded->begin() + static_cast<std::ptrdiff_t>(offset)),
              "the dispute authority key sits at its recorded offset");
  pv::require(offset == 106, "immediately after the verifier key");

  pv::require(v8::kMaxGenesisAccounts == expect_size(values, "genesis.max_accounts"),
              "the account bound under the wider prefix");
  pv::require(v8::kMaxGenesisAccounts <
                  expect_size(carried, "genesis.max_accounts_admitted"),
              "and it falls from version seven's");
  expect_true(values, "genesis.max_accounts_falls_from_version_seven");
  pv::require(encoded->size() ==
                  expect_size(carried, "genesis.prefix_bytes") +
                      v8::kDisputeAuthorityKeyBytes,
              "version eight's prefix is version seven's plus one key");
  expect_true(values, "genesis.is_thirty_two_octets_longer_than_version_seven");

  const auto entries = genesis_economy(genesis.verifier_key);
  pv::require(entries.size() == 14, "genesis writes fourteen economy entries");
  expect_true(values, "genesis.writes_fourteen_economy_entries");
  for (const auto& entry : entries) {
    const auto kind = entry.key.front();
    pv::require(kind != static_cast<std::uint8_t>(v8::Entry::open_challenge) &&
                    kind != static_cast<std::uint8_t>(v8::Entry::seat_window),
                "genesis writes no uptime entry");
  }
  expect_true(values, "genesis.writes_no_uptime_entry");

  // No predecessor genesis is the same object, and the earlier identifier is
  // derived here rather than recorded, so the comparison is between two live
  // constructions over identical fields.
  for (const auto version : kPredecessors) {
    if (version == 1) continue;
    const auto earlier = v8::predecessor_chain_id(genesis, version);
    pv::require(earlier.has_value(), "the predecessor chain identifier derives");
    pv::require(*earlier != *identifier, "no predecessor chain identity collides");
    expect_true(values,
                "genesis.chain_id_differs_from_v" + std::to_string(version));
  }

  verify_genesis_decoding(genesis);
}

void verify_non_collision(const pv::Values& values, const pv::Values& manifest) {
  const auto genesis =
      fixture_genesis(from_hex(expect_text(manifest, "manifest_digest")));
  const auto identifier = v8::chain_id(genesis);
  pv::require(identifier.has_value(), "the chain identifier derives");

  v8::StateSummary summary;
  summary.chain_id = *identifier;
  summary.height = kRootHeight;
  summary.supply_limit = kSupplyLimit;
  summary.total_supply = 0;
  summary.fee_pool_balance = 0;

  const auto root = v8::state_root(summary, {}, {});
  pv::require(root.has_value(), "the version-eight state root derives");
  pv::require(hex(*root) == expect_text(values, "root.version_eight"),
              "version eight's recorded state root");

  for (const auto version : kPredecessors) {
    const auto earlier = v8::predecessor_state_root(version, summary, {}, {});
    pv::require(earlier.has_value(), "the predecessor state root derives");
    pv::require(*earlier != *root, "no predecessor root collides");
    expect_true(values, "root.differs_from_v" + std::to_string(version));
  }
  // And they differ from each other, which is what makes the loop above seven
  // claims rather than one repeated.
  for (std::size_t left = 0; left < std::size(kPredecessors); ++left) {
    for (std::size_t right = left + 1; right < std::size(kPredecessors); ++right) {
      pv::require(v8::predecessor_state_root(kPredecessors[left], summary, {}, {}) !=
                      v8::predecessor_state_root(kPredecessors[right], summary, {}, {}),
                  "two predecessor roots collide with each other");
    }
  }
  pv::require(!v8::predecessor_state_root(8, summary, {}, {}).has_value(),
              "version eight is not its own predecessor");
}

// **The construction has to be the earlier version's and not merely its
// label.** Both loops above compare digests for inequality, and a
// `predecessor_state_root` that wrote version eight's schema version into every
// preimage would still produce seven distinct digests and pass all of them
// while describing an artifact no chain ever had.
//
// So each end of the range is pinned against the accepted file that recorded
// it: version one's root against `protocol-primitives-v1.txt`, whose fixture
// has no economy half at all, and version seven's against
// `economy-transition-v7.txt`, over the fixture that file was recorded on.
// Both survive the deletion of `src/v7/`, which a comparison against the live
// version-seven kernel would not.
void verify_predecessor_constructions(const pv::Values& carried,
                                      const pv::Values& primitives,
                                      const pv::Values& manifest) {
  v8::StateSummary version_one;
  version_one.chain_id = from_hex(expect_text(primitives, "chain_id"));
  version_one.height = expect_number(primitives, "state.height");
  version_one.supply_limit = expect_number(primitives, "state.supply_limit");
  version_one.total_supply = expect_number(primitives, "state.total_supply");
  version_one.fee_pool_balance = expect_number(primitives, "state.fee_pool_balance");
  const auto accounts = accepted_accounts(primitives);
  const auto one = v8::predecessor_state_root(1, version_one, accounts, {});
  pv::require(one.has_value(), "version one's root derives");
  pv::require(hex(*one) == expect_text(primitives, "state.root"),
              "version one's own accepted state root");

  // Version seven's identity fixture, transcribed from the file that recorded
  // it: network 7, the maximum supply, a distinctive fee, and an ascending
  // verifier key. The dispute authority key is not part of a version-seven
  // object, so whatever it holds must not reach the derivation.
  auto genesis = fixture_genesis(from_hex(expect_text(manifest, "manifest_digest")));
  genesis.network_id = 7;
  genesis.fixed_transfer_fee = 100'000;
  genesis.verifier_key = ascending(0);
  const auto identifier = v8::predecessor_chain_id(genesis, 7);
  pv::require(identifier.has_value(), "version seven's chain identifier derives");
  pv::require(hex(*identifier) == expect_text(carried, "version.chain_id"),
              "version seven's own accepted chain identifier");

  v8::StateSummary version_seven;
  version_seven.chain_id = *identifier;
  version_seven.height = 0;
  version_seven.supply_limit = genesis.supply_limit;
  version_seven.total_supply = 0;
  version_seven.fee_pool_balance = 0;
  const auto seven = v8::predecessor_state_root(7, version_seven, {},
                                                genesis_economy(genesis.verifier_key));
  pv::require(seven.has_value(), "version seven's root derives");
  pv::require(hex(*seven) == expect_text(carried, "version.state_root"),
              "version seven's own accepted state root");
}

}  // namespace

void verify_accounts_tree(const pv::Values& primitives) {
  const auto accounts = accepted_accounts(primitives);
  pv::require(hex(v8::accounts_root(accounts)) ==
                  expect_text(primitives, "state.accounts_tree_root"),
              "the copied tree reproduces the accepted M1 accounts root");
  pv::require(hex(v8::accounts_root({})) ==
                  expect_text(primitives, "state.empty_tree_root"),
              "and the accepted M1 empty tree root");
}

void verify_version(const pv::Values& values, const pv::Values& carried_seven,
                    const pv::Values& manifest, const pv::Values& primitives) {
  verify_labels(values);
  verify_manifest_binding(values, carried_seven, manifest);
  verify_genesis(values, carried_seven, manifest);
  verify_non_collision(values, manifest);
  verify_predecessor_constructions(carried_seven, primitives, manifest);
}

}  // namespace economy_v8_fixture
