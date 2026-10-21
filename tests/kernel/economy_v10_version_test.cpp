// The version-ten identity, its constants, its result codes, and genesis,
// checked against the recorded vectors.
//
// **A label is a string and a string proves nothing on its own**, so each
// recorded label is checked against an artifact the kernel derived with it: the
// chain identity is the recorded label's digest of the encoded genesis, the
// root is the recorded label's digest of its frame, and each message opens with
// the recorded label. A constant compared to itself would establish nothing
// about the bytes a node commits to or a HUB signs.
//
// **Both ends of the compatibility range are pinned to accepted artifacts.**
// Version ten's digests must differ from each predecessor's over the same
// inputs, and this kernel's predecessor constructions must reproduce what
// version nine's own file recorded: its chain identity, its root and the eight
// before it, and its block header. Without the second half, a predecessor
// construction that wrote version ten's schema version into every preimage
// would still satisfy every inequality, because the labels would still differ.

#include "economy_v10_carried.hpp"

#include "protocol/v1/crypto.hpp"

#include <string>

namespace economy_v10_fixture {
namespace {

std::uint16_t read_u16(const v10::Bytes& bytes, std::size_t offset) {
  pv::require(offset + 2 <= bytes.size(), "truncated u16");
  return static_cast<std::uint16_t>((bytes[offset] << 8U) | bytes[offset + 1]);
}

// The label a message opens with, read out of the bytes the kernel produced.
std::string opening_label(const v10::Bytes& message) {
  pv::require(!message.empty() && message.size() > message.front(),
              "a message opens with its length-prefixed label");
  return std::string(message.begin() + 1, message.begin() + 1 + message.front());
}

v10::Envelope kind_19_envelope() {
  v10::Body body;
  body.recipient_escrow_id = kRecipient;
  body.amount_atomic = 9;
  body.hub_signature = kSignature;
  v10::Envelope envelope;
  envelope.kind = static_cast<std::uint8_t>(v10::Kind::native_transfer_verified);
  envelope.chain_id = kChain;
  envelope.scheme = v10::kSchemeSigner;
  envelope.authority_public_key = kSigner;
  envelope.nonce = kSignerNonce;
  envelope.body = v10::encode_body(envelope.kind, body);
  envelope.fee_limit = kFixedTransferFee;
  envelope.valid_until_height = kValidUntil;
  return envelope;
}

void verify_derivation_labels(const pv::Values& values, const pv::Values& manifest) {
  const auto genesis = fixture_genesis(manifest);
  const auto encoded = v10::encode_genesis(genesis);
  const auto identity = v10::chain_id(genesis);
  pv::require(encoded.has_value() && identity.has_value(),
              "the fixture genesis encodes and has an identity");

  const std::string chain_label = expect_text(values, "identity.chain_id_label");
  pv::require(chain_label == v10::kChainIdLabel &&
                  protocol::v1::hash(chain_label, *encoded) == *identity,
              "the chain identity is the recorded label's digest of genesis");
  pv::require(expect_number(values, "identity.genesis_schema_version") ==
                  read_u16(*encoded, 4),
              "the encoded genesis carries schema version 10");

  const std::string tree_prefix =
      expect_text(values, "identity.economy_tree_prefix");
  const auto empty = v10::economy_root({});
  pv::require(tree_prefix == v10::kEconomyTreePrefix && empty.has_value() &&
                  *empty == protocol::v1::hash(tree_prefix + "-empty"),
              "the economy tree's empty root is the recorded prefix's");

  v10::StateSummary summary;
  summary.chain_id = *identity;
  summary.timestamp = kGenesisMillis;
  summary.supply_limit = genesis.supply_limit;
  const auto frame = v10::state_root_frame(summary, {}, {});
  const auto root = v10::state_root(summary, {}, {});
  pv::require(frame.has_value() && root.has_value(), "an empty state has a root");
  v10::Bytes preimage = frame->head;
  pv::append_u64(preimage, summary.height);
  pv::append_u64(preimage, summary.timestamp);
  preimage.insert(preimage.end(), frame->tail.begin(), frame->tail.end());
  const std::string root_label = expect_text(values, "identity.state_root_label");
  pv::require(root_label == v10::kStateRootLabel &&
                  protocol::v1::hash(root_label, preimage) == *root,
              "the state root is the recorded label's digest of its frame");
  pv::require(expect_number(values, "identity.state_root_schema_version") ==
                  read_u16(frame->head, 0),
              "the root's preimage opens with version field 10");

  v10::Receipt receipt;
  receipt.kind = static_cast<std::uint8_t>(v10::Kind::native_transfer);
  const auto encoded_receipt = v10::encode_receipt(receipt);
  pv::require(encoded_receipt.has_value(), "a transfer receipt encodes");
  pv::require(expect_number(values, "identity.receipt_version") ==
                  read_u16(*encoded_receipt, 4),
              "the encoded receipt carries version 10");

  // **The header is not re-versioned**, so its schema version and the block
  // identifier's label are version nine's, read out of a header this kernel
  // built and an identifier it took.
  const auto header = v10::block_header(ascending(0), 4, kGenesisMillis,
                                        repeated(0xA0), repeated(0xB0),
                                        repeated(0xC0), 2);
  pv::require(header.has_value(), "the fixture header encodes");
  pv::require(expect_number(values, "identity.block_header_schema_version") ==
                  read_u16(*header, 4),
              "the header keeps schema version 9");
  const std::string block_label = expect_text(values, "identity.block_id_label");
  const auto identifier = v10::block_id(*header);
  pv::require(block_label == v10::kBlockIdLabel && identifier.has_value() &&
                  protocol::v1::hash(block_label, *header) == *identifier,
              "the block identifier is the recorded label's digest of the header");
}

void verify_message_labels(const pv::Values& values) {
  const auto registration = opening_label(v10::registration_message(
      kChain, kSeat, kIdentity, kHubKey, kFirstSigner, kValidUntil));
  pv::require(expect_text(values, "identity.registration_label") == registration &&
                  registration == v10::kRegistrationLabel,
              "the registration opens with the recorded label");

  const auto approval_message = v10::approval_message(kind_19_envelope());
  pv::require(approval_message.has_value(), "kind 19 carries a body approval");
  const auto approval = opening_label(*approval_message);
  pv::require(expect_text(values, "identity.approval_label") == approval &&
                  approval == v10::kApprovalLabel,
              "the approval opens with the recorded label");

  const auto attestation = opening_label(v10::attestation_message(
      kChain, kSeat, kMachineKey, kBuildDigest, kValidUntil));
  pv::require(expect_text(values, "identity.attestation_label") == attestation &&
                  attestation == v10::kAttestationLabel,
              "the attestation opens with the recorded label");

  pv::require(expect_text(values, "identity.hub_message_labels") ==
                  registration + "," + approval,
              "the two HUB labels are the registration's and the approval's");
}

void verify_constants(const pv::Values& values) {
  // Each figure the kernel uses is compared with the recording; the behaviour
  // each one bounds is reached by the state and lifetime checks, which admit
  // the limit and the bound and refuse one past each.
  pv::require(expect_number(values, "constants.launch_retirement_active_machines") ==
                  v10::kLaunchRetirementActiveMachines,
              "the launch key retires at 100 active machines");
  pv::require(expect_number(values, "constants.founder_registrations_per_window") ==
                  v10::kFounderRegistrationsPerWindow,
              "one founder's machines sign at most 1,000 registrations a window");
  pv::require(expect_number(values, "constants.activity_threshold_seconds") ==
                  v10::kActivityThresholdSeconds,
              "a cycle is met at 18 hours");
  pv::require(expect_number(values, "constants.approval_lifetime_blocks") ==
                  v10::kApprovalLifetimeBlocks,
              "an approval lives one slot");
  pv::require(v10::kApprovalLifetimeBlocks == v10::kSlotBlocks,
              "the lifetime is bound to the slot rather than restated");
  pv::require(expect_number(values, "constants.launch_attester") ==
                  v10::kLaunchAttester,
              "the launch attester is u32 maximum");
  expect_claim(values, "constants.launch_attester_is_above_every_seat",
               v10::kLaunchAttester > v10::kMaxSeatId);
}

void verify_codes(const pv::Values& values, const Carried& carried) {
  for (std::uint8_t code = 45; code < 50; ++code) {
    const auto name = v10::result_code_name(code);
    pv::require(name.has_value() &&
                    *name == expect_text(values, "codes." + std::to_string(code)),
                "an added code has its recorded name");
  }
  pv::require(expect_number(values, "codes.count") == v10::kResultCodeCount,
              "the result code space is 50");
  pv::require(!v10::result_code_name(v10::kResultCodeCount),
              "the space is contiguous and ends where it says");
  // Against version nine's names as the files that accepted them record them,
  // over every code, rather than against the version-nine kernel's table.
  const auto carried_names = version_nine_codes(carried);
  bool unchanged = carried_names.size() == 45;
  for (std::size_t code = 0; code < carried_names.size(); ++code) {
    const auto here = v10::result_code_name(static_cast<std::uint8_t>(code));
    unchanged = unchanged && here.has_value() && *here == carried_names[code];
  }
  expect_claim(values, "codes.zero_through_forty_four_unchanged", unchanged);
}

void verify_genesis(const pv::Values& values, const pv::Values& manifest) {
  const auto genesis = fixture_genesis(manifest);
  const auto encoded = v10::encode_genesis(genesis);
  pv::require(encoded.has_value(), "the fixture genesis must encode");
  pv::require(hex(*encoded) == expect_text(values, "genesis.bytes"),
              "the encoded genesis is the recorded one");
  pv::require(expect_size(values, "widths.genesis_prefix") == encoded->size() &&
                  encoded->size() == v10::kGenesisPrefixBytes,
              "the prefix is 182 octets");
  pv::require(expect_size(values, "widths.max_genesis_accounts") ==
                  v10::kMaxGenesisAccounts,
              "the account bound is 21,841");

  // The decoder is the encoder's inverse, and the launch key and the build
  // authority key are read back from their offsets rather than trusted.
  const auto decoded = v10::decode_genesis(*encoded);
  pv::require(decoded.has_value() && decoded->launch_key == kLaunchKey &&
                  decoded->dispute_authority_key == kDisputeAuthorityKey &&
                  decoded->build_authority_key == kBuildAuthorityKey,
              "the three keys round-trip at their offsets");
  pv::require(std::equal(kLaunchKey.begin(), kLaunchKey.end(), encoded->begin() + 82) &&
                  std::equal(kBuildAuthorityKey.begin(), kBuildAuthorityKey.end(),
                             encoded->begin() + 146),
              "the launch key keeps offset 82 and the build key sits at 146");
  auto truncated = *encoded;
  truncated.pop_back();
  pv::require(!v10::decode_genesis(truncated), "a short genesis is refused");

  const auto identity = v10::chain_id(genesis);
  pv::require(identity.has_value() &&
                  hex(*identity) == expect_text(values, "genesis.chain_id"),
              "the chain identity is the recorded one");

  pv::require(expect_size(values, "genesis.economy_entry_count") ==
                  v10::kGenesisEconomyEntries,
              "genesis writes sixteen economy entries");
  const auto entries = genesis_economy(genesis);
  pv::require(entries.size() == v10::kGenesisEconomyEntries,
              "the fixture builds the sixteen");
  const auto launch = std::find_if(entries.begin(), entries.end(), [](const auto& e) {
    return e.key == v10::verifier_key_key();
  });
  pv::require(launch != entries.end() &&
                  hex(launch->value) == expect_text(values, "genesis.launch_key_entry"),
              "entry kind 8 holds the launch key");
}

void verify_non_collision(const pv::Values& values, const pv::Values& manifest) {
  const auto genesis = fixture_genesis(manifest);
  const auto here = v10::chain_id(genesis);
  pv::require(here.has_value(), "the fixture genesis has an identity");
  for (std::uint16_t version = 2; version <= 9; ++version) {
    const auto earlier = v10::predecessor_chain_id(genesis, version);
    expect_claim(values,
                 "non_collision.chain_id_v" + std::to_string(version) + "_differs",
                 earlier.has_value() && *earlier != *here);
  }
  pv::require(!v10::predecessor_chain_id(genesis, 10),
              "version ten is not its own predecessor");

  v10::StateSummary summary;
  summary.chain_id = *here;
  summary.timestamp = genesis.genesis_timestamp;
  summary.supply_limit = genesis.supply_limit;
  const auto economy = genesis_economy(genesis);
  const auto root = v10::state_root(summary, {}, economy);
  pv::require(root.has_value(), "the genesis state has a root");
  for (std::uint16_t version = 1; version <= 9; ++version) {
    const auto earlier = v10::predecessor_state_root(version, summary, {}, economy);
    expect_claim(values,
                 "non_collision.state_root_v" + std::to_string(version) + "_differs",
                 earlier.has_value() && *earlier != *root);
  }
  pv::require(!v10::predecessor_state_root(10, summary, {}, economy),
              "version ten is not its own predecessor");
}

// **Version nine's own recordings, reproduced by this kernel.** None of these is
// a version-ten vector; each is the far end of the range, pinned.
void verify_version_nine_pins(const Carried& carried, const pv::Values& manifest) {
  // Version nine's recorded fixture genesis, as a version-ten genesis would
  // carry the same fields: its verifier key is the launch key's offset, and the
  // build authority key, which version nine has no field for, is arbitrary.
  v10::Genesis nine;
  nine.network_id = 9;
  nine.genesis_timestamp = 1'772'172'000'000ULL;
  nine.supply_limit = std::stoull(manifest.at("denomination.maximum_supply_atomic"));
  nine.fixed_transfer_fee = kFixedTransferFee;
  nine.manifest_digest = from_hex(manifest.at("manifest_digest"));
  nine.launch_key = repeated(0xA1);
  nine.dispute_authority_key = repeated(0xD8);
  const auto nine_bytes = bytes_from_hex(carried.nine.at("genesis.bytes"));
  pv::require(nine_bytes.size() == v10::kGenesisPrefixBytes - v10::kBuildAuthorityKeyBytes,
              "version nine's recorded genesis is its 150-octet prefix");
  for (const auto build : {repeated(0x00), kBuildAuthorityKey}) {
    nine.build_authority_key = build;
    const auto identity = v10::predecessor_chain_id(nine, 9);
    pv::require(identity.has_value() &&
                    hex(*identity) == carried.nine.at("genesis.chain_id") &&
                    *identity == protocol::v1::hash("protocol-stack:v9:chain-id",
                                                    nine_bytes),
                "the version-nine identity is version nine's recorded one, "
                "whatever the build key holds");
  }

  // Version nine's empty state at height 12 under its own identity, and the
  // eight roots before it, each as version nine's file recorded them.
  v10::StateSummary summary;
  summary.chain_id = from_hex(carried.nine.at("genesis.chain_id"));
  summary.height = 12;
  summary.timestamp = nine.genesis_timestamp;
  summary.supply_limit = nine.supply_limit;
  const auto version_nine = v10::predecessor_state_root(9, summary, {}, {});
  pv::require(version_nine.has_value() &&
                  hex(*version_nine) == carried.nine.at("root.version_nine"),
              "this kernel reproduces version nine's own recorded root");
  for (std::uint16_t version = 1; version <= 8; ++version) {
    const auto earlier = v10::predecessor_state_root(version, summary, {}, {});
    pv::require(earlier.has_value() &&
                    hex(*earlier) == carried.nine.at("root.v" + std::to_string(version)),
                "each earlier root is the one version nine's file recorded");
  }

  // The header and its identifier over version nine's recorded fields: version
  // ten changes neither, so both must be version nine's octet for octet.
  const auto header = v10::block_header(ascending(0), 4, nine.genesis_timestamp,
                                        repeated(0xA0), repeated(0xB0),
                                        repeated(0xC0), 2);
  pv::require(header.has_value() &&
                  hex(*header) == carried.nine.at("header.bytes_encoded"),
              "the header is version nine's recorded bytes");
  const auto identifier = v10::block_id(*header);
  pv::require(identifier.has_value() &&
                  hex(*identifier) == carried.nine.at("header.block_id"),
              "the block identifier is version nine's recorded one");
}

}  // namespace

void verify_accounts_tree(const pv::Values& primitives) {
  std::vector<v10::AccountEntry> accounts;
  for (int index = 0; index < 3; ++index) {
    const auto entry = primitives.at("state.account" + std::to_string(index));
    v10::AccountEntry account;
    account.account_id = from_hex(entry.substr(0, 64));
    account.balance = std::stoull(entry.substr(64, 16), nullptr, 16);
    account.nonce = std::stoull(entry.substr(80, 16), nullptr, 16);
    accounts.push_back(account);
  }
  pv::require(hex(v10::accounts_root(accounts)) ==
                  primitives.at("state.accounts_tree_root"),
              "the ported tree reproduces the accepted M1 accounts tree root");
  pv::require(hex(v10::accounts_root({})) == primitives.at("state.empty_tree_root"),
              "the ported tree reproduces the accepted M1 empty tree root");
}

void verify_version(const pv::Values& values, const Carried& carried,
                    const pv::Values& manifest) {
  verify_derivation_labels(values, manifest);
  verify_message_labels(values);
  verify_constants(values);
  verify_codes(values, carried);
  verify_genesis(values, manifest);
  verify_non_collision(values, manifest);
  verify_version_nine_pins(carried, manifest);
}

}  // namespace economy_v10_fixture
