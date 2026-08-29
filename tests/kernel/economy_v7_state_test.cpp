// The economy state key space, the two trees, the version-six state root,
// genesis and chain identity, and the storage bounds.
//
// The accounts tree is checked against `test-vectors/protocol-primitives-v1.txt`
// rather than only against this version's own file, because it is version one's
// construction entry for entry and a lookalike would agree only with itself.

#include "economy_v7_fixture.hpp"

namespace economy_v7_fixture {
namespace {

void verify_state_widths(const pv::Values& values) {
  const std::uint8_t assigned[] = {1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 13, 14, 15, 16};
  for (const auto kind : assigned) {
    const auto prefix = "state.entry" + std::to_string(kind) + ".";
    const auto key_width = v7::entry_key_bytes(kind);
    pv::require(key_width.has_value(), "entry kind is assigned");
    pv::require(*key_width == expect_size(values, prefix + "key_bytes"),
                "entry key width");
    const auto value_width = v7::entry_value_bytes(kind);
    if (kind == static_cast<std::uint8_t>(v7::Entry::cycle_assignment)) {
      pv::require(!value_width.has_value(),
                  "the cycle assignment is the one variable-width value");
      pv::require(expect_size(values, prefix + "fixed_value_bytes") == 24,
                  "its fixed part");
      continue;
    }
    pv::require(value_width.has_value(), "a fixed-width value");
    pv::require(*value_width == expect_size(values, prefix + "value_bytes"),
                "entry value width");
    pv::require(*key_width + *value_width == expect_size(values, prefix + "total_bytes"),
                "entry total width");
  }
  pv::require(std::size(assigned) == expect_size(values, "state.entry_kind_count"),
              "fourteen assigned entry kinds");

  const std::uint8_t retired[] = {9, 11};
  pv::require(std::size(retired) ==
                  expect_size(values, "state.retired_entry_kind_count"),
              "two retired entry kinds");
  for (const auto kind : retired) {
    pv::require(v7::is_retired_entry_kind(kind) && !v7::is_entry_kind(kind),
                "a retired entry kind is not an entry kind");
    expect_true(values, "state.retired_entry" + std::to_string(kind) + "_is_refused");
    // A retired entry cannot be hashed into the tree, which is what makes the
    // retirement a property of state rather than a note.
    v7::Bytes key{kind};
    key.insert(key.end(), 32, 0);
    pv::require(!v7::economy_root({{key, {}}}).has_value(),
                "a retired entry is refused by the tree");
  }
  pv::require(!v7::is_entry_kind(0) && !v7::is_entry_kind(17),
              "the assigned entry range is closed at both ends");

  // Shapes no transition could have written, each refused rather than hashed,
  // because a root cannot signal any of them.
  pv::require(!v7::economy_root({{{200}, {}}}).has_value(), "an unknown entry kind");
  pv::require(!v7::economy_root({{v7::carry_key(0), {}}}).has_value(),
              "a value of the wrong width");
  pv::require(!v7::economy_root({{{7}, v7::carry_value(0)}}).has_value(),
              "a key of the wrong width");
  const v7::EconomyEntry carry{v7::carry_key(0), v7::carry_value(0)};
  pv::require(v7::economy_root({carry}).has_value(), "a well-formed entry hashes");
  pv::require(!v7::economy_root({carry, carry}).has_value(), "a duplicated key");
  expect_true(values, "state.every_key_is_shape_checked");
  expect_true(values, "state.unknown_entry_kind_is_refused");
}

void verify_trees(const pv::Values& values, const pv::Values& version_three) {
  const auto empty = v7::economy_root({});
  pv::require(empty.has_value(), "the empty economy root derives");
  pv::require(hex(*empty) == expect_text(values, "tree.empty_root_hex"),
              "the empty economy root");

  const auto initial = genesis_economy();
  pv::require(initial.size() == expect_size(values, "tree.genesis_entry_count"),
              "the genesis entry count");
  const auto genesis_root = v7::economy_root(initial);
  pv::require(genesis_root.has_value(), "the genesis economy root derives");
  pv::require(hex(*genesis_root) == expect_text(values, "tree.genesis_root_hex"),
              "the genesis economy root");
  for (const auto& entry : initial) {
    const auto kind = entry.key.front();
    pv::require(kind != static_cast<std::uint8_t>(v7::Entry::seat) &&
                    kind != static_cast<std::uint8_t>(v7::Entry::hub_identity) &&
                    kind != static_cast<std::uint8_t>(v7::Entry::escrow) &&
                    kind != static_cast<std::uint8_t>(v7::Entry::signer),
                "genesis writes no seat, identity, escrow, or signer");
  }
  expect_true(values, "tree.genesis_writes_every_singleton_entry");
  expect_true(values, "tree.genesis_writes_no_seat_identity_escrow_or_signer");

  const auto populated = populated_economy(version_three);
  pv::require(populated.size() == expect_size(values, "tree.populated_entry_count"),
              "the populated entry count");
  const auto populated_root = v7::economy_root(populated);
  pv::require(populated_root.has_value(), "the populated economy root derives");
  pv::require(hex(*populated_root) == expect_text(values, "tree.populated_root_hex"),
              "the populated economy root");

  // The populated set covers every assigned entry kind, which is what makes one
  // recorded root a constraint on all fourteen value encodings rather than on
  // the five genesis writes.
  std::vector<std::uint8_t> covered;
  for (const auto& entry : populated) covered.push_back(entry.key.front());
  std::sort(covered.begin(), covered.end());
  covered.erase(std::unique(covered.begin(), covered.end()), covered.end());
  pv::require(covered.size() == expect_size(values, "state.entry_kind_count"),
              "every assigned entry kind appears");
  expect_true(values, "tree.populated_set_covers_every_assigned_entry_kind");
  expect_true(values,
              "settlement.the_cycle_record_is_byte_identical_to_version_three");
  expect_true(values,
              "settlement.the_outage_record_is_byte_identical_to_version_three");
}

void verify_roots(const pv::Values& values, const pv::Values& primitives,
                  const pv::Values& version_three) {
  const auto accounts = accepted_accounts(primitives);
  pv::require(hex(v7::accounts_root(accounts)) ==
                  primitives.at("state.accounts_tree_root"),
              "the accounts tree reproduces the accepted root");
  pv::require(hex(v7::accounts_root(accounts)) ==
                  expect_text(values, "root.accounts_tree_hex"),
              "and the recorded version-six vector");
  expect_true(values, "root.v1_accounts_tree_restatement_reproduces_its_accepted_root");

  pv::require(expect_text(values, "root.label") == v7::kStateRootLabel,
              "the state-root domain label");
  pv::require(expect_number(values, "root.schema_version") ==
                  v7::kStateRootSchemaVersion,
              "the state-root schema version");

  v7::StateSummary summary;
  summary.chain_id = kChainId;
  summary.height = 9;
  summary.supply_limit = kMaximumSupplyAtomic;
  summary.total_supply = 1'000;
  summary.fee_pool_balance = 7;

  const auto empty = v7::state_root(summary, accounts, {});
  pv::require(empty.has_value(), "the state root over an empty economy derives");
  pv::require(hex(*empty) ==
                  expect_text(values, "root.version_six_over_an_empty_economy"),
              "the version-six state root over an empty economy");

  const auto populated =
      v7::state_root(summary, accounts, populated_economy(version_three));
  pv::require(populated.has_value(), "the populated state root derives");
  pv::require(hex(*populated) ==
                  expect_text(values, "root.version_six_over_the_populated_economy"),
              "the version-six state root over the populated economy");
  pv::require(*populated != *empty, "the economy changes the root");
  expect_true(values, "root.the_economy_changes_the_root");
  expect_true(values, "root.all_six_differ_over_identical_inputs");

  const v7::EconomyEntry carry{v7::carry_key(0), v7::carry_value(0)};
  pv::require(!v7::state_root(summary, accounts, {carry, carry}).has_value(),
              "a state root over a duplicated economy key is refused");
}

void verify_genesis(const pv::Values& values, const pv::Values& manifest) {
  v7::Genesis genesis;
  genesis.network_id = 6;
  genesis.supply_limit = kMaximumSupplyAtomic;
  genesis.fixed_transfer_fee = 0;
  genesis.manifest_digest = from_hex(manifest.at("manifest_digest"));
  genesis.verifier_key = kVerifierKey;

  const auto encoded = v7::encode_genesis(genesis);
  pv::require(encoded.has_value(), "the founder genesis encodes");
  pv::require(hex(*encoded) == expect_text(values, "genesis.bytes_hex"),
              "genesis bytes");
  pv::require(encoded->size() == expect_size(values, "genesis.prefix_bytes"),
              "the genesis prefix width");
  pv::require(expect_number(values, "genesis.schema_version") ==
                  v7::kGenesisSchemaVersion,
              "the genesis schema version");
  pv::require(expect_text(values, "genesis.chain_id_label") == v7::kChainIdLabel,
              "the chain-ID domain label");
  const auto identifier = v7::chain_id(genesis);
  pv::require(identifier.has_value(), "the chain identifier derives");
  pv::require(hex(*identifier) == expect_text(values, "genesis.chain_id_hex"),
              "the chain identifier");
  expect_true(values, "genesis.permits_a_zero_fee");

  // The inherited object bound, recorded and unreachable: no version-six
  // genesis can carry an account at all.
  pv::require(v7::kMaxGenesisAccounts ==
                  expect_size(values, "genesis.object_bound_admits_entries"),
              "the inherited account bound");
  pv::require(v7::kGenesisPrefixBytes +
                      v7::kAccountEntryBytes * v7::kMaxGenesisAccounts ==
                  expect_size(values, "genesis.object_bound_within_bytes"),
              "the bound stays within the canonical object limit");
  pv::require(v7::kGenesisPrefixBytes +
                      v7::kAccountEntryBytes * (v7::kMaxGenesisAccounts + 1) >
                  v7::kMaxObjectBytes,
              "and one entry beyond it does not");
  expect_true(values, "genesis.object_bound_within_the_limit");
  expect_true(values, "genesis.object_bound_beyond_the_limit");

  auto rejected = genesis;
  rejected.supply_limit = 0;
  pv::require(!v7::encode_genesis(rejected).has_value(), "a zero supply limit");
  rejected = genesis;
  rejected.total_supply = 1;
  pv::require(!v7::encode_genesis(rejected).has_value(), "a nonzero total supply");
  rejected = genesis;
  rejected.initial_fee_pool = 1;
  pv::require(!v7::encode_genesis(rejected).has_value(), "a nonzero fee pool");
  rejected = genesis;
  rejected.account_count = 1;
  pv::require(!v7::encode_genesis(rejected).has_value(), "any account entry");
  for (const auto* key : {"genesis.refuses_any_account_entry",
                          "genesis.refuses_a_nonzero_total_supply",
                          "genesis.refuses_a_nonzero_initial_fee_pool",
                          "genesis.opens_with_zero_supply"}) {
    expect_true(values, key);
  }
}

void verify_storage(const pv::Values& values) {
  auto entry = [](v7::Entry kind) {
    const auto number = static_cast<std::uint8_t>(kind);
    return *v7::entry_key_bytes(number) + *v7::entry_value_bytes(number);
  };
  const auto identity = entry(v7::Entry::hub_identity);
  const auto escrow = entry(v7::Entry::escrow) + v7::kAccountEntryBytes;
  const auto signer = entry(v7::Entry::signer);

  pv::require(entry(v7::Entry::seat) * v7::kFounderSeatCapacity ==
                  expect_size(values, "storage.seats_at_capacity_bytes"),
              "seats at capacity");
  pv::require(identity == expect_size(values, "storage.identity_bytes"),
              "an identity");
  pv::require(escrow == expect_size(values, "storage.escrow_bytes"), "an escrow");
  pv::require(signer == expect_size(values, "storage.signer_bytes"), "a signer");
  pv::require(signer * v7::kMaxSignersPerEscrow ==
                  expect_size(values, "storage.signers_at_the_bound_bytes"),
              "signers at the bound");
  pv::require(entry(v7::Entry::verified_user_enrollment) * v7::kVerifiedUserPopulation ==
                  expect_size(
                      values,
                      "storage.verified_user_enrollments_at_the_population_bytes"),
              "enrolments at the population");
  pv::require(entry(v7::Entry::channel) * 10 ==
                  expect_size(values, "storage.channels_bytes"),
              "the channels");
  pv::require(entry(v7::Entry::carry) * 10 ==
                  expect_size(values, "storage.carries_bytes"),
              "the carries");
  pv::require(entry(v7::Entry::typed_custody) * 4 ==
                  expect_size(values, "storage.typed_custody_bytes"),
              "the typed custody entries");
  pv::require(entry(v7::Entry::referral_balance) ==
                  expect_size(values, "storage.referral_balance_bytes"),
              "a referral balance");
  pv::require(entry(v7::Entry::verifier_key) ==
                  expect_size(values, "storage.verifier_key_bytes"),
              "the verifier key");
  pv::require(entry(v7::Entry::unreferred_pool) ==
                  expect_size(values, "storage.unreferred_pool_bytes"),
              "the unreferred pool");
  pv::require(entry(v7::Entry::verified_user_counter) ==
                  expect_size(values, "storage.verified_user_counter_bytes"),
              "the verified-user counter");

  // A cycle assignment at the seat capacity: the key, the fixed part, and two
  // bitmaps of one bit per seat, with no length prefixes because both widths
  // follow from the recorded bit count.
  pv::require(*v7::entry_key_bytes(
                  static_cast<std::uint8_t>(v7::Entry::cycle_assignment)) +
                      24 + 2 * v7::bitmap_bytes(v7::kFounderSeatCapacity) ==
                  expect_size(values, "storage.cycle_assignment_bytes_per_cycle"),
              "a cycle assignment at the seat capacity");

  // A person's own footprint, which is the per-person figure requirement 12 now
  // needs: escrows are bounded economically rather than by rule, and signers are
  // bounded at 16 as a resource limit rather than a statement about people.
  pv::require(identity + 3 * escrow + 5 * signer ==
                  expect_size(
                      values,
                      "storage.one_person_with_three_escrows_and_five_signers_bytes"),
              "one person with three escrows and five signers");
}

}  // namespace

void verify_state(const pv::Values& values, const pv::Values& primitives,
                  const pv::Values& version_three, const pv::Values& manifest) {
  verify_state_widths(values);
  verify_trees(values, version_three);
  verify_roots(values, primitives, version_three);
  verify_genesis(values, manifest);
  verify_storage(values);
}

}  // namespace economy_v7_fixture
