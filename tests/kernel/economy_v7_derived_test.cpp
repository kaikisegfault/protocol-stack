// The constructions version seven inherits, version-seven genesis, the receipt,
// and the founder-directed tables.
//
// Four checks here reach a *third* source rather than a second opinion of the
// execution vectors, and each is a construction version seven inherits or a
// figure it is told: the ordered transaction tree against
// `protocol-primitives-v1.txt`, the block header and block identifier against
// `ledger-transition-v1.txt`, the ten channel caps and five base-permission legs
// against `founder-economy-manifest-v3.txt`, and the referral leg against
// `economy-transition-v3.txt`. Without those, a restated construction that had
// drifted would agree only with itself.

#include "economy_v7_execution_fixture.hpp"

#include "protocol/v1/crypto.hpp"

namespace economy_v7_execution {
namespace {

Hash to_hash(const Bytes& bytes) {
  pv::require(bytes.size() == 32, "expected a 32-octet value");
  Hash value{};
  std::copy(bytes.begin(), bytes.end(), value.begin());
  return value;
}

// The ordered transaction tree and the 146-byte block header are version one's,
// inherited rather than re-versioned: version seven re-versions genesis, the
// receipt, and the state root explicitly and says nothing about either, and a
// version-seven header is already unmistakable because the chain ID it carries is
// derived under a version-seven label.
void check_constructions(const pv::Values& values, const pv::Values& primitives,
                         const pv::Values& ledger_vectors) {
  agree(values, "construction.transaction_tree_prefix",
        std::string(v7::kTransactionTreePrefix));
  std::vector<Hash> items;
  for (int index = 0; index < 3; ++index) {
    items.push_back(to_hash(
        pv::hex_decode(expect_text(primitives, "tx.item" + std::to_string(index)))));
  }
  const auto derived_root = v7::transaction_root(items);
  agree(values, "construction.transaction_root_over_the_accepted_items",
        hex(derived_root));
  pv::require(hex(derived_root) == expect_text(primitives, "tx.root"),
              "the transaction tree must reproduce the accepted root");
  expect_true(values, "construction.transaction_root_reproduces_the_accepted_vector");

  const auto empty_root = v7::transaction_root({});
  agree(values, "construction.empty_transaction_root", hex(empty_root));
  pv::require(hex(empty_root) == expect_text(primitives, "tx.empty_root"),
              "the empty transaction tree must reproduce the accepted root");
  expect_true(values, "construction.empty_transaction_root_reproduces_the_accepted_vector");

  // The accepted version-one header, field for field out of the recorded bytes,
  // so a restatement that had drifted fails against the file that fixes it.
  const auto recorded = pv::hex_decode(expect_text(ledger_vectors, "block_header"));
  pv::require(recorded.size() == v7::kBlockHeaderBytes,
              "the accepted header is 146 octets");
  Octets32 chain_id{};
  std::copy(recorded.begin() + 6, recorded.begin() + 38, chain_id.begin());
  std::uint64_t height = 0;
  for (std::size_t index = 38; index < 46; ++index) {
    height = (height << 8U) | recorded[index];
  }
  std::uint32_t count = 0;
  for (std::size_t index = 142; index < 146; ++index) {
    count = (count << 8U) | recorded[index];
  }
  const auto header = v7::block_header(
      chain_id, height,
      to_hash(pv::hex_decode(expect_text(ledger_vectors, "previous_state_root"))),
      to_hash(pv::hex_decode(expect_text(ledger_vectors, "transaction_root"))),
      to_hash(pv::hex_decode(expect_text(ledger_vectors, "resulting_state_root"))),
      count);
  pv::require(header.has_value(), "the accepted fields must encode a header");
  agree(values, "construction.block_header", hex(*header));
  pv::require(*header == recorded, "the header must reproduce the accepted bytes");
  expect_true(values, "construction.block_header_reproduces_the_accepted_vector");
  const auto block_id = protocol::v1::hash(v7::kBlockIdLabel, *header);
  agree(values, "construction.block_id", hex(block_id));
  pv::require(hex(block_id) == expect_text(ledger_vectors, "block_id"),
              "the block identifier must reproduce the accepted value");
  expect_true(values, "construction.block_id_reproduces_the_accepted_vector");
  agree(values, "construction.block_header_bytes", v7::kBlockHeaderBytes);
  agree(values, "construction.block_header_schema_version",
        static_cast<std::uint64_t>(v7::kBlockHeaderSchemaVersion));
}

void check_genesis(const pv::Values& values) {
  const auto genesis = trace_genesis();
  const auto encoded = v7::encode_genesis(genesis);
  pv::require(encoded.has_value(), "the trace genesis must encode");
  agree(values, "genesis.bytes", hex(*encoded));
  agree(values, "genesis.prefix_bytes", encoded->size());
  agree(values, "genesis.schema_version",
        static_cast<std::uint64_t>(v7::kGenesisSchemaVersion));
  agree(values, "genesis.manifest_digest", hex(genesis.manifest_digest));
  const auto identity = v7::chain_id(genesis);
  pv::require(identity.has_value(), "the trace genesis must have a chain identity");
  agree(values, "genesis.chain_id", hex(*identity));
  agree(values, "genesis.fixed_fee", genesis.fixed_transfer_fee);

  // Fourteen entries where version six wrote twenty-three: the ten carries go
  // and one recovery pool entry replaces them.
  agree(values, "genesis.economy_entries",
        v7::economy_entries(open_trace_ledger()).size());

  // Each predecessor chain identity is a different digest over the same fields,
  // because the label and the schema version inside the preimage both differ.
  // The kernel builds exactly one of the seven, so the five non-collisions are
  // read as recorded rather than re-derived under constructions it does not hold.
  for (int version = 2; version <= 6; ++version) {
    expect_true(values, "genesis.chain_id_differs_from_v" + std::to_string(version));
  }

  // Version two derived that a conforming chain must permit a zero fee, because
  // a zero allocation and a nonzero fee leave nobody able to pay for the first
  // transaction. Registration is fee-exempt and pays the airdrop, so version six
  // is the first contract under which a nonzero fee is reachable from genesis,
  // and version seven inherits that without restating it.
  const auto daily = v7::verified_user_daily_atomic();
  pv::require(daily.has_value(), "the verified-user rate must divide exactly");
  pv::require(genesis.fixed_transfer_fee > 0 && genesis.total_supply == 0 &&
                  genesis.account_count == 0 && *daily > genesis.fixed_transfer_fee,
              "a nonzero fixed fee must be reachable from a version-seven genesis");
  expect_true(values,
              "genesis.a_nonzero_fixed_fee_is_reachable_from_a_version_seven_genesis");
}

// Version seven's receipt is version six's layout with one octet changed.
//
// The recorded receipt is a node mint of one whole base permission, which is
// what makes it a version-seven artifact twice over: the version field is seven
// and the issued amount is the sum of the five legs the manifest fixes.
void check_receipt(const pv::Values& values) {
  agree(values, "receipt.version", static_cast<std::uint64_t>(v7::kReceiptVersion));
  agree(values, "receipt.bytes", v7::kReceiptBytes);

  std::uint64_t base_permission = 0;
  for (std::uint8_t channel = 0; channel < v7::kRecoveryPoolLegs; ++channel) {
    base_permission += v7::base_permission_leg(channel);
  }
  v7::Receipt receipt;
  receipt.transaction_id = ascending(0);
  receipt.kind = static_cast<std::uint8_t>(v7::Kind::mint_node);
  receipt.result_code = static_cast<std::uint8_t>(v7::Result::success);
  receipt.fee_charged = kFixedFee;
  receipt.issued_atomic = base_permission;
  const auto encoded = v7::encode_receipt(receipt);
  pv::require(encoded.has_value(), "the mint receipt encodes");
  agree(values, "receipt.mint_receipt", hex(*encoded));

  // The same receipt under version six's version field, which this kernel can no
  // longer produce and must no longer accept.
  auto version_six = *encoded;
  version_six[5] = 6;
  std::size_t differing = 0;
  for (std::size_t index = 0; index < encoded->size(); ++index) {
    if ((*encoded)[index] != version_six[index]) ++differing;
  }
  pv::require(differing == 1, "the two receipts differ in exactly one octet");
  expect_true(values, "receipt.differs_from_the_version_six_receipt_in_one_octet");
  pv::require(!v7::decode_receipt(version_six).has_value(),
              "a version-six receipt is refused");
  expect_true(values, "receipt.a_version_six_receipt_is_refused");
  const auto decoded = v7::decode_receipt(*encoded);
  pv::require(decoded.has_value() && decoded->kind == receipt.kind &&
                  decoded->issued_atomic == receipt.issued_atomic &&
                  decoded->fee_charged == receipt.fee_charged,
              "a version-seven receipt round trips");
  expect_true(values, "receipt.a_version_seven_receipt_round_trips");
}

// The founder-directed figures the kernel carries, each against the accepted
// file that fixes it rather than against the kernel's own table. Channel 9's
// identifier is the one thing ADR 0053's manifest moved, and reading it from the
// version-three file is what makes the rebinding a comparison.
void check_tables(const pv::Values& manifest, const pv::Values& version_three) {
  static constexpr std::array<const char*, 10> kChannelNames{
      "founder_operator",
      "venture_escrow",
      "community_grants_escrow",
      "developer_incentives_escrow",
      "system_creator_issuance_royalty",
      "liquidity_mining",
      "impermanent_loss_protection",
      "founder_referral",
      "hub_verified_user_incentives",
      "mini_gamified_incentives",
  };
  pv::require(expect_number(manifest, "channels.count") == kChannelNames.size(),
              "the manifest records ten channels");
  for (std::uint8_t index = 0; index < kChannelNames.size(); ++index) {
    const auto key = "channel" + std::to_string(index);
    pv::require(expect_text(manifest, key + ".id") == kChannelNames[index],
                "channel " + std::to_string(index) + " has the recorded identifier");
    pv::require(v7::channel_cap(index) == expect_number(manifest, key + ".cap"),
                "channel " + std::to_string(index) + " carries the recorded cap");
    const auto leg_key = std::string("base_permission.") + kChannelNames[index];
    const auto recorded =
        manifest.count(leg_key) == 0 ? 0 : expect_number(manifest, leg_key);
    pv::require(v7::base_permission_leg(index) == recorded,
                "channel " + std::to_string(index) + " carries the recorded leg");
  }
  pv::require(v7::channel_cap(v7::kVerifiedUserChannel) ==
                  v7::kVerifiedUserChannelCapAtomic,
              "the verified-user cap is the one the codec already declared");
  pv::require(v7::kReferralLegAtomic == expect_number(version_three, "referral.leg_atomic"),
              "the referral leg is the recorded version-three figure");
}

}  // namespace

void verify_derivations(const pv::Values& values, const pv::Values& primitives,
                        const pv::Values& ledger_vectors, const pv::Values& manifest,
                        const pv::Values& version_three) {
  check_constructions(values, primitives, ledger_vectors);
  check_genesis(values);
  check_receipt(values);
  check_tables(manifest, version_three);
}

}  // namespace economy_v7_execution
