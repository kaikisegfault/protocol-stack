// The constructions version eight inherits, version-eight genesis, and the
// receipt.
//
// Three checks here reach a *third* source rather than a second opinion of the
// execution vectors, and each is a construction version eight inherits: the
// ordered transaction tree against `protocol-primitives-v1.txt`, and the block
// header and block identifier against `ledger-transition-v1.txt`. Without those,
// a restated construction that had drifted would agree only with itself.
//
// **The six genesis non-collisions are derived here rather than read.** Version
// seven's execution test had to read them as recorded, because its kernel could
// build only one of the seven constructions; version eight's codec carries
// `predecessor_chain_id`, so each is a comparison between two digests this
// kernel computes.

#include "economy_v8_execution_fixture.hpp"

#include "protocol/v1/crypto.hpp"

namespace economy_v8_execution {
namespace {

Hash to_hash(const Bytes& bytes) {
  pv::require(bytes.size() == 32, "expected a 32-octet value");
  Hash value{};
  std::copy(bytes.begin(), bytes.end(), value.begin());
  return value;
}

// The ordered transaction tree and the 146-byte block header are version one's,
// inherited rather than re-versioned: version eight re-versions genesis, the
// receipt, the state root, the chain identity, and the economy tree, and says
// nothing about either. A version-eight header is already unmistakable because
// the chain ID it carries is derived under a version-eight label.
void check_constructions(const pv::Values& values, const pv::Values& primitives,
                         const pv::Values& ledger_vectors) {
  agree(values, "construction.transaction_tree_prefix",
        std::string(v8::kTransactionTreePrefix));
  std::vector<Hash> items;
  for (int index = 0; index < 3; ++index) {
    items.push_back(to_hash(
        pv::hex_decode(expect_text(primitives, "tx.item" + std::to_string(index)))));
  }
  const auto derived_root = v8::transaction_root(items);
  agree(values, "construction.transaction_root_over_the_accepted_items",
        hex(derived_root));
  pv::require(hex(derived_root) == expect_text(primitives, "tx.root"),
              "the transaction tree must reproduce the accepted root");
  expect_true(values, "construction.transaction_root_reproduces_the_accepted_vector");

  const auto empty_root = v8::transaction_root({});
  agree(values, "construction.empty_transaction_root", hex(empty_root));
  pv::require(hex(empty_root) == expect_text(primitives, "tx.empty_root"),
              "the empty transaction tree must reproduce the accepted root");
  expect_true(values,
              "construction.empty_transaction_root_reproduces_the_accepted_vector");

  // The accepted version-one header, field for field out of the recorded bytes,
  // so a restatement that had drifted fails against the file that fixes it.
  const auto recorded = pv::hex_decode(expect_text(ledger_vectors, "block_header"));
  pv::require(recorded.size() == v8::kBlockHeaderBytes,
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
  const auto header = v8::block_header(
      chain_id, height,
      to_hash(pv::hex_decode(expect_text(ledger_vectors, "previous_state_root"))),
      to_hash(pv::hex_decode(expect_text(ledger_vectors, "transaction_root"))),
      to_hash(pv::hex_decode(expect_text(ledger_vectors, "resulting_state_root"))),
      count);
  pv::require(header.has_value(), "the accepted fields must encode a header");
  agree(values, "construction.block_header", hex(*header));
  pv::require(*header == recorded, "the header must reproduce the accepted bytes");
  expect_true(values, "construction.block_header_reproduces_the_accepted_vector");
  const auto block_id = protocol::v1::hash(v8::kBlockIdLabel, *header);
  agree(values, "construction.block_id", hex(block_id));
  pv::require(hex(block_id) == expect_text(ledger_vectors, "block_id"),
              "the block identifier must reproduce the accepted value");
  expect_true(values, "construction.block_id_reproduces_the_accepted_vector");
  agree(values, "construction.block_header_bytes", v8::kBlockHeaderBytes);
  agree(values, "construction.block_header_schema_version",
        static_cast<std::uint64_t>(v8::kBlockHeaderSchemaVersion));
}

void check_genesis(const pv::Values& values) {
  const auto genesis = trace_genesis();
  const auto encoded = v8::encode_genesis(genesis);
  pv::require(encoded.has_value(), "the trace genesis must encode");
  agree(values, "genesis.bytes", hex(*encoded));
  agree(values, "genesis.prefix_bytes", encoded->size());
  agree(values, "genesis.schema_version",
        static_cast<std::uint64_t>(v8::kGenesisSchemaVersion));
  agree(values, "genesis.manifest_digest", hex(genesis.manifest_digest));
  const auto identity = v8::chain_id(genesis);
  pv::require(identity.has_value(), "the trace genesis must have a chain identity");
  agree(values, "genesis.chain_id", hex(*identity));
  agree(values, "genesis.fixed_fee", genesis.fixed_transfer_fee);

  // The fourteen entries version seven wrote, unchanged.
  const auto ledger = open_trace_ledger();
  agree(values, "genesis.economy_entries", v8::economy_entries(ledger).size());

  // Whoever attests HUB identities does not thereby acquire the power to void a
  // machine's uptime; least privilege costs 32 octets here.
  pv::require(genesis.dispute_authority_key != genesis.verifier_key,
              "the dispute authority key is not the verifier key");
  expect_true(values, "genesis.the_dispute_authority_key_is_not_the_verifier_key");
  // A challenge is issued by a block and a window record exists only once a seat
  // has lost or had a slot voided, so genesis writes neither.
  pv::require(ledger.uptime.empty(),
              "genesis writes no open challenge and no window record");
  expect_true(values, "genesis.writes_no_open_challenge_and_no_window_record");

  // Each predecessor chain identity is a different digest over the same fields,
  // because the label, the schema version inside the preimage, and the length
  // all differ. Both sides are derived here, so the claim is about two real
  // artifacts rather than about two strings.
  for (std::uint16_t version = 2; version <= 7; ++version) {
    const auto earlier = v8::predecessor_chain_id(genesis, version);
    pv::require(earlier.has_value(), "a predecessor chain identity derives");
    pv::require(*earlier != *identity, "a predecessor chain identity collides");
    expect_true(values, "genesis.chain_id_differs_from_v" + std::to_string(version));
  }
}

// Version eight's receipt is version seven's layout with one octet changed.
//
// The recorded receipt is a node mint of one whole base permission, which is
// what makes it a version-eight artifact twice over: the version field is eight
// and the issued amount is the sum of the five legs the manifest fixes.
void check_receipt(const pv::Values& values) {
  agree(values, "receipt.version", static_cast<std::uint64_t>(v8::kReceiptVersion));
  agree(values, "receipt.bytes", v8::kReceiptBytes);

  std::uint64_t base_permission = 0;
  for (std::uint8_t channel = 0; channel < v8::kRecoveryPoolLegs; ++channel) {
    base_permission += v8::base_permission_leg(channel);
  }
  v8::Receipt receipt;
  receipt.transaction_id = ascending(0);
  receipt.kind = static_cast<std::uint8_t>(v8::Kind::mint_node);
  receipt.result_code = static_cast<std::uint8_t>(v8::Result::success);
  receipt.fee_charged = kFixedFee;
  receipt.issued_atomic = base_permission;
  const auto encoded = v8::encode_receipt(receipt);
  pv::require(encoded.has_value(), "the mint receipt encodes");
  agree(values, "receipt.mint_receipt", hex(*encoded));

  // The same receipt under version seven's version field, which this kernel can
  // no longer produce and must no longer accept.
  auto version_seven = *encoded;
  version_seven[5] = 7;
  std::size_t differing = 0;
  for (std::size_t index = 0; index < encoded->size(); ++index) {
    if ((*encoded)[index] != version_seven[index]) ++differing;
  }
  pv::require(differing == 1, "the two receipts differ in exactly one octet");
  expect_true(values, "receipt.differs_from_the_version_seven_receipt_in_one_octet");
  pv::require(!v8::decode_receipt(version_seven).has_value(),
              "a version-seven receipt is refused");
  expect_true(values, "receipt.a_version_seven_receipt_is_refused");
  const auto decoded = v8::decode_receipt(*encoded);
  pv::require(decoded.has_value() && decoded->kind == receipt.kind &&
                  decoded->issued_atomic == receipt.issued_atomic &&
                  decoded->fee_charged == receipt.fee_charged,
              "a version-eight receipt round trips");
  expect_true(values, "receipt.a_version_eight_receipt_round_trips");

  // The two kinds version eight adds issue nothing, and the response charges
  // nothing. Both are consistency rules over the receipt rather than execution
  // results, so they are checked on constructed receipts: a receipt claiming an
  // issuance for a kind that cannot issue is not a receipt any chain produced.
  const auto shaped = [&](v8::Kind kind, std::uint64_t fee,
                          std::uint64_t issued) {
    v8::Receipt probe = receipt;
    probe.kind = static_cast<std::uint8_t>(kind);
    probe.fee_charged = fee;
    probe.issued_atomic = issued;
    return v8::receipt_is_consistent(probe);
  };
  pv::require(!shaped(v8::Kind::challenge_response, 0, 1),
              "a challenge response issuing a nonzero amount is refused");
  expect_true(values, "receipt.kind20_issuing_a_nonzero_amount_is_refused");
  pv::require(!shaped(v8::Kind::file_dispute, kFixedFee, 1),
              "a dispute issuing a nonzero amount is refused");
  expect_true(values, "receipt.kind21_issuing_a_nonzero_amount_is_refused");
  pv::require(!shaped(v8::Kind::challenge_response, kFixedFee, 0),
              "a challenge response charging a fee is refused");
  expect_true(values, "receipt.a_challenge_response_charging_a_fee_is_refused");
  pv::require(shaped(v8::Kind::challenge_response, 0, 0),
              "a successful response charging nothing is accepted");
  expect_true(values,
              "receipt.a_successful_response_charging_nothing_is_accepted");
  pv::require(shaped(v8::Kind::file_dispute, kFixedFee, 0),
              "a successful dispute charging the fixed fee is accepted");
  expect_true(values,
              "receipt.a_successful_dispute_charging_the_fixed_fee_is_accepted");
}

}  // namespace

void verify_derivations(const pv::Values& values, const pv::Values& primitives,
                        const pv::Values& ledger_vectors) {
  check_constructions(values, primitives, ledger_vectors);
  check_genesis(values);
  check_receipt(values);
}

}  // namespace economy_v8_execution
