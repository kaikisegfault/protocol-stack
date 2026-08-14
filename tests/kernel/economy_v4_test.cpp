// The version-four codec, checked against the recorded vectors.
//
// This is requirement 11 for the bytes the codec covers: the C++ implementation
// and the independent Python model must reproduce one fixed file. Nothing here
// derives a second set of expected values — every assertion compares against
// `test-vectors/economy-transition-v4.txt`, and the kind-1 identity is compared
// against `test-vectors/protocol-primitives-v1.txt` as well, because if the C++
// encoder does not emit the accepted M1 transfer bytes the compatibility
// boundary is broken at its narrowest point and nothing after it is worth
// checking.

#include "protocol/v1/crypto.hpp"
#include "protocol/v4/economy.hpp"

#include "../../tools/protocol-vectors/vector_common.hpp"

#include <algorithm>
#include <cstdint>
#include <iostream>
#include <span>
#include <string>
#include <vector>

namespace pv = protocol_vectors;
namespace v4 = protocol::v4;

namespace {

v4::Octets32 repeated(std::uint8_t octet) {
  v4::Octets32 value{};
  value.fill(octet);
  return value;
}

v4::Octets32 from_hex(const std::string& hex) {
  const auto bytes = pv::hex_decode(hex);
  pv::require(bytes.size() == 32, "expected 32 octets");
  v4::Octets32 value{};
  std::copy(bytes.begin(), bytes.end(), value.begin());
  return value;
}

v4::Octets32 ascending(std::uint8_t first) {
  v4::Octets32 value{};
  for (std::size_t index = 0; index < value.size(); ++index) {
    value[index] = static_cast<std::uint8_t>(first + index);
  }
  return value;
}

std::string hex(std::span<const std::uint8_t> bytes) {
  static constexpr char digits[] = "0123456789abcdef";
  std::string out;
  out.reserve(bytes.size() * 2);
  for (const auto octet : bytes) {
    out.push_back(digits[octet >> 4U]);
    out.push_back(digits[octet & 0x0FU]);
  }
  return out;
}

std::string hex(const v4::Hash& value) {
  return hex(std::span<const std::uint8_t>(value.data(), value.size()));
}

std::size_t expect_size(const pv::Values& values, const std::string& key) {
  return static_cast<std::size_t>(std::stoull(values.at(key)));
}

// The fixture's constants, restated. They are simple repeated or ascending
// octets by design, so restating them is transcription rather than derivation,
// and every value they feed is compared against the recorded file.
const v4::Octets32 kChainId = ascending(0);
const v4::Octets32 kRecipient = ascending(0x20);
const v4::Octets32 kAliceIdentity = repeated(0xA1);
const v4::Octets32 kAliceKey = repeated(0xA2);
const v4::Octets32 kAliceFirstAddress = repeated(0xA3);
const v4::Octets32 kAliceSecondAddress = repeated(0xA4);
const v4::Octets32 kBobIdentity = repeated(0xB1);
const v4::Octets32 kManagerAccount = repeated(0xAA);
const v4::Octets32 kVerifierKey = repeated(0x55);
constexpr std::uint64_t kFeeLimit = 1'000;
constexpr std::uint64_t kValidUntil = 42;
constexpr std::uint64_t kCycleBlocks = 28'800;

void verify_kind_table(const pv::Values& values) {
  const std::pair<std::uint8_t, const char*> kinds[] = {
      {1, "native_transfer"},     {2, "purchase_seat"},
      {3, "activate_seat"},       {4, "mint_node"},
      {5, "mint_referral"},       {6, "direct_issue"},
      {7, "mint_node_verified"},  {8, "set_mint_biometric"},
      {9, "add_manager"},         {10, "hub_register"},
      {11, "hub_add_address"},    {12, "hub_remove_address"},
  };
  for (const auto& [kind, name] : kinds) {
    const auto body = v4::body_bytes(kind);
    const auto signed_size = v4::signed_bytes(kind);
    pv::require(body.has_value() && signed_size.has_value(), "kind is unknown");
    pv::require(*body == expect_size(values, std::string("envelope.body_bytes.") + name),
                "body width");
    pv::require(
        *signed_size == expect_size(values, std::string("envelope.signed_bytes.") + name),
        "signed width");
  }
  pv::require(!v4::body_bytes(0).has_value(), "kind zero is not a kind");
  pv::require(!v4::body_bytes(13).has_value(), "kind thirteen is not a kind");
  // The anticipated collisions: dispatch is on the kind byte, never on length.
  pv::require(v4::body_bytes(3) == v4::body_bytes(7), "kinds 3 and 7 coincide");
  pv::require(v4::body_bytes(11) == v4::body_bytes(12), "kinds 11 and 12 coincide");
}

v4::Envelope transfer_envelope() {
  v4::Envelope envelope;
  envelope.kind = static_cast<std::uint8_t>(v4::Kind::native_transfer);
  envelope.chain_id = kChainId;
  envelope.nonce = 1;
  envelope.fee_limit = kFeeLimit;
  envelope.valid_until_height = kValidUntil;
  envelope.body.insert(envelope.body.end(), kRecipient.begin(), kRecipient.end());
  for (int shift = 56; shift >= 0; shift -= 8) {
    envelope.body.push_back(static_cast<std::uint8_t>(1'000'000ULL >> shift));
  }
  return envelope;
}

void verify_kind_one_identity(const pv::Values& values,
                              const pv::Values& primitives) {
  auto envelope = transfer_envelope();
  const auto key = pv::hex_decode(primitives.at("rfc8032.public_key"));
  pv::require(key.size() == 32, "public key size");
  std::copy(key.begin(), key.end(), envelope.sender_public_key.begin());

  const auto unsigned_bytes = v4::encode_unsigned(envelope);
  pv::require(unsigned_bytes.size() == 136, "unsigned transfer is 136 octets");
  pv::require(hex(unsigned_bytes) == primitives.at("unsigned_tx"),
              "kind 1 reproduces the accepted unsigned transfer");
  pv::require(hex(unsigned_bytes) == values.at("compatibility.kind_one_unsigned_hex"),
              "kind 1 matches the recorded version-four vector");

  const auto signature = pv::hex_decode(primitives.at("signature"));
  const auto signed_bytes = v4::encode_signed(envelope, signature);
  pv::require(hex(signed_bytes) == primitives.at("signed_tx"),
              "kind 1 reproduces the accepted signed transfer");
  pv::require(hex(v4::transaction_id(signed_bytes)) == primitives.at("tx_id"),
              "kind 1 reproduces the accepted transaction ID");

  // The header and trailer must be slices of the accepted bytes rather than a
  // re-encoding of them, which is what makes the factoring a partition.
  const auto accepted = pv::hex_decode(primitives.at("unsigned_tx"));
  pv::require(std::equal(accepted.begin(), accepted.begin() + v4::kHeaderBytes,
                         unsigned_bytes.begin()),
              "the header is the accepted transfer's first 80 octets");
  pv::require(std::equal(accepted.end() - v4::kTrailerBytes, accepted.end(),
                         unsigned_bytes.end() - v4::kTrailerBytes),
              "the trailer is the accepted transfer's last 16 octets");
}

void verify_admission(const pv::Values& values) {
  auto envelope = transfer_envelope();
  const v4::Bytes signature(v4::kSignatureBytes, 0x11);
  const auto accepted = v4::encode_signed(envelope, signature);
  pv::require(v4::decode_signed(accepted).has_value(), "the positive control decodes");
  pv::require(accepted.size() == expect_size(values, "envelope.signed_bytes.native_transfer"),
              "the control is the recorded width");

  auto mutate = [&accepted](std::size_t offset, std::uint8_t octet) {
    auto copy = accepted;
    copy[offset] = octet;
    return copy;
  };
  pv::require(!v4::decode_signed(mutate(0, 'X')).has_value(), "wrong magic");
  pv::require(!v4::decode_signed(mutate(5, 2)).has_value(), "wrong schema version");
  pv::require(!v4::decode_signed(mutate(39, 2)).has_value(), "unknown signature scheme");
  pv::require(!v4::decode_signed(mutate(6, 0)).has_value(), "kind zero");
  pv::require(!v4::decode_signed(mutate(6, 13)).has_value(), "unknown kind");

  auto trailing = accepted;
  trailing.push_back(0);
  pv::require(!v4::decode_signed(trailing).has_value(), "trailing byte");
  auto truncated = accepted;
  truncated.pop_back();
  pv::require(!v4::decode_signed(truncated).has_value(), "truncated");

  // The two relabellings a length check cannot catch are admitted, and the kind
  // byte inside the signing message is what separates them.
  auto activate = envelope;
  activate.kind = static_cast<std::uint8_t>(v4::Kind::activate_seat);
  activate.body.assign(*v4::body_bytes(activate.kind), 0x22);
  const auto activate_raw = v4::encode_signed(activate, signature);
  auto relabelled = activate_raw;
  relabelled[6] = static_cast<std::uint8_t>(v4::Kind::mint_node_verified);
  const auto decoded = v4::decode_signed(relabelled);
  pv::require(decoded.has_value(), "a same-length relabelling decodes");
  pv::require(decoded->envelope.kind ==
                  static_cast<std::uint8_t>(v4::Kind::mint_node_verified),
              "and is read as the kind its byte names");
  pv::require(v4::signing_message(v4::encode_unsigned(decoded->envelope)) !=
                  v4::signing_message(v4::encode_unsigned(activate)),
              "so the signing message changes");
}

void verify_canonical_body_shapes() {
  // Two shape rules live in a body rather than in a length, and both are
  // non-minimal representations: a second encoding of "no referrer", and a
  // signature field on a transaction that carries no signature.
  const v4::Bytes signature(v4::kSignatureBytes, 0x11);
  v4::Envelope purchase;
  purchase.kind = static_cast<std::uint8_t>(v4::Kind::purchase_seat);
  purchase.chain_id = kChainId;
  purchase.body.assign(*v4::body_bytes(purchase.kind), 0);
  purchase.body[36] = 0;
  pv::require(v4::decode_signed(v4::encode_signed(purchase, signature)).has_value(),
              "an absent referrer of 32 zero octets is canonical");
  purchase.body[37] = 1;
  pv::require(!v4::decode_signed(v4::encode_signed(purchase, signature)).has_value(),
              "a non-minimal absent referrer is refused");
  purchase.body[37] = 0;
  purchase.body[36] = 2;
  pv::require(!v4::decode_signed(v4::encode_signed(purchase, signature)).has_value(),
              "a non-canonical has_referrer byte is refused");

  v4::Envelope protection;
  protection.kind = static_cast<std::uint8_t>(v4::Kind::set_mint_biometric);
  protection.chain_id = kChainId;
  protection.body.assign(*v4::body_bytes(protection.kind), 0);
  protection.body[4] = 1;
  pv::require(v4::decode_signed(v4::encode_signed(protection, signature)).has_value(),
              "enabling with 64 zero octets is canonical");
  protection.body[5] = 1;
  pv::require(!v4::decode_signed(v4::encode_signed(protection, signature)).has_value(),
              "enabling with a signature is refused");
  protection.body[5] = 0;
  protection.body[4] = 2;
  pv::require(!v4::decode_signed(v4::encode_signed(protection, signature)).has_value(),
              "a non-canonical enable byte is refused");
}

void verify_hub_messages(const pv::Values& values) {
  const auto chain = std::span<const std::uint8_t>(kChainId);
  const auto who = std::span<const std::uint8_t>(kAliceIdentity);

  const std::pair<const char*, v4::Bytes> built[] = {
      {"registration",
       v4::registration_message(chain, who, kAliceKey, kAliceFirstAddress, kValidUntil)},
      {"address_add",
       v4::address_add_message(chain, who, kAliceSecondAddress, kValidUntil)},
      {"address_remove",
       v4::address_remove_message(chain, who, kAliceSecondAddress, kValidUntil)},
      {"purchase",
       v4::purchase_message(chain, who, 0, kAliceFirstAddress, kValidUntil)},
      {"activation", v4::activation_message(chain, who, 0, kValidUntil)},
      {"mint", v4::mint_message(chain, who, 0, kValidUntil)},
      {"mint_biometric_disable",
       v4::mint_biometric_disable_message(chain, who, 0, kValidUntil)},
      {"manager", v4::manager_message(chain, who, 0, kManagerAccount, kValidUntil)},
  };
  for (const auto& [name, message] : built) {
    pv::require(hex(message) == values.at(std::string("message.hex.") + name),
                "HUB message bytes");
    pv::require(message.size() == expect_size(values, std::string("message.bytes.") + name),
                "HUB message width");
  }
  // Three carry identical field shapes and are separated only by their labels.
  pv::require(built[4].second != built[5].second, "activation is not a mint");
  pv::require(built[5].second != built[6].second, "a mint is not a protection removal");
  // Every message names the identity, so one person's signature is never
  // another's even where the remaining fields coincide.
  const auto other = v4::mint_message(chain, kBobIdentity, 0, kValidUntil);
  pv::require(other != built[5].second, "rebinding the identity changes the message");
}

void verify_state_values(const pv::Values& values) {
  v4::HubIdentityRecord alice;
  alice.hub_public_key = kAliceKey;
  alice.registered_at_height = 5 * kCycleBlocks;
  alice.address_count = 2;
  alice.seat_count = 1;
  const auto identity_value = v4::hub_identity_value(alice);
  pv::require(hex(identity_value) == values.at("registry.alice_identity_value_hex"),
              "HUB identity record bytes");
  pv::require(identity_value.size() ==
                  expect_size(values, "state.value_bytes.hub_identity"),
              "HUB identity record width");
  pv::require(hex(v4::hub_address_value(kAliceIdentity)) ==
                  values.at("registry.alice_address_value_hex"),
              "HUB address record bytes");

  // Every key width, derived from the same table the vectors record.
  const std::pair<std::uint8_t, const char*> entries[] = {
      {1, "seat"},           {2, "channel"},        {3, "cycle_assignment"},
      {4, "referral_balance"}, {5, "direct_decision"}, {6, "typed_custody"},
      {7, "carry"},          {8, "verifier_key"},   {9, "seat_manager"},
      {10, "hub_identity"},  {11, "hub_address"},   {12, "unreferred_pool"},
  };
  for (const auto& [kind, name] : entries) {
    const auto width = v4::entry_key_bytes(kind);
    pv::require(width.has_value(), "entry kind is known");
    pv::require(*width == expect_size(values, std::string("state.key_bytes.") + name),
                "entry key width");
  }
  pv::require(!v4::is_entry_kind(0) && !v4::is_entry_kind(13), "entry kind range");
  pv::require(!v4::entry_value_bytes(3).has_value(),
              "the cycle assignment is the one variable-width value");

  pv::require(hex(v4::cycle_assignment_key(200)) == values.at("cycle.assignment_key"),
              "cycle assignment key bytes");
  pv::require(hex(v4::cycle_assignment_key(201)) == values.at("outage.assignment_key"),
              "outage assignment key bytes");
}

void verify_cycle_assignment(const pv::Values& values) {
  // Reconstructed from the recorded population rather than round-tripped, so a
  // packing error is caught rather than preserved: the bitmaps are indexed by
  // seat identifier with the most significant bit first, and the record carries
  // no bitmap length prefixes because both widths follow from `bitmap_bits`.
  constexpr std::uint32_t kBits = 24;
  const std::uint32_t accrued_seats[] = {0, 4, 15};
  const std::uint32_t winner_seats[] = {0, 4, 23};

  v4::CycleAssignment assignment;
  assignment.share_per_winner_atomic = 11'400'000'000ULL;
  assignment.reallocated_count = 2;
  assignment.winner_count = 3;
  assignment.in_scope_count = 6;
  assignment.bitmap_bits = kBits;
  assignment.accrued_bitmap = v4::bitmap(accrued_seats, kBits);
  assignment.winner_bitmap = v4::bitmap(winner_seats, kBits);

  const auto encoded = v4::cycle_assignment_value(assignment);
  pv::require(hex(encoded) == values.at("cycle.assignment_value_hex"),
              "cycle assignment record bytes");
  pv::require(v4::cycle_assignment_key(200).size() + encoded.size() ==
                  expect_size(values, "cycle.assignment_entry_bytes"),
              "cycle assignment entry width");

  const auto decoded = v4::decode_cycle_assignment_value(encoded);
  pv::require(decoded.has_value(), "the record decodes");
  pv::require(decoded->winner_count == 3 && decoded->reallocated_count == 2 &&
                  decoded->in_scope_count == 6 && decoded->bitmap_bits == kBits,
              "the decoded counts are the encoded ones");
  for (const auto seat : winner_seats) {
    pv::require(v4::bit_is_set(decoded->winner_bitmap, seat), "a winner bit is set");
  }
  for (const auto seat : accrued_seats) {
    pv::require(v4::bit_is_set(decoded->accrued_bitmap, seat), "an accrued bit is set");
  }
  pv::require(!v4::bit_is_set(decoded->accrued_bitmap, 23),
              "a seat may win without accruing");
  pv::require(!v4::bit_is_set(decoded->winner_bitmap, 15),
              "a seat may accrue without winning");
  pv::require(!v4::bit_is_set(decoded->accrued_bitmap, 1'000),
              "a seat beyond the bitmap reads clear");
  // A length that disagrees with its bit count is refused rather than truncated.
  auto short_record = encoded;
  short_record.pop_back();
  pv::require(!v4::decode_cycle_assignment_value(short_record).has_value(),
              "a record whose length disagrees with its bit count is refused");

  v4::CycleAssignment outage;
  outage.in_scope_count = 6;
  outage.reallocated_count = 5;
  outage.bitmap_bits = kBits;
  outage.accrued_bitmap = v4::bitmap({}, kBits);
  outage.winner_bitmap = v4::bitmap({}, kBits);
  pv::require(hex(v4::cycle_assignment_value(outage)) ==
                  values.at("outage.assignment_value_hex"),
              "the empty-winner record bytes");
}

void verify_roots(const pv::Values& values, const pv::Values& primitives) {
  pv::require(hex(v4::economy_root({})) == values.at("state.economy_root_empty"),
              "the empty economy root");

  // The accounts tree is version one's, entry for entry, and is required to
  // reproduce the accepted file rather than merely to look plausible.
  std::vector<v4::AccountEntry> accepted;
  for (int index = 0; index < 3; ++index) {
    const auto entry = primitives.at("state.account" + std::to_string(index));
    v4::AccountEntry account;
    account.account_id = from_hex(entry.substr(0, 64));
    account.balance = std::stoull(entry.substr(64, 16), nullptr, 16);
    account.nonce = std::stoull(entry.substr(80, 16), nullptr, 16);
    accepted.push_back(account);
  }
  pv::require(hex(v4::accounts_root(accepted)) == primitives.at("state.accounts_tree_root"),
              "the accounts tree reproduces the accepted root");
  pv::require(hex(v4::accounts_root({})) == primitives.at("state.empty_tree_root"),
              "the empty accounts tree reproduces the accepted root");

  std::vector<v4::AccountEntry> fixture;
  for (std::uint8_t index = 0; index < 3; ++index) {
    v4::AccountEntry account;
    account.account_id = repeated(index);
    account.balance = 1'000ULL * (index + 1);
    fixture.push_back(account);
  }
  v4::StateSummary summary;
  summary.chain_id = kChainId;
  summary.height = 7;
  summary.supply_limit = 5'699'395'010'000'000'000ULL;
  summary.total_supply = 6'000;
  pv::require(hex(v4::state_root(summary, fixture, {})) ==
                  values.at("state.root_empty_economy"),
              "the version-four state root over an empty economy");
}

void verify_genesis(const pv::Values& values) {
  v4::Genesis genesis;
  genesis.network_id = 4;
  genesis.supply_limit = 5'699'395'010'000'000'000ULL;
  genesis.manifest_digest = from_hex(values.at("genesis.manifest_digest"));
  genesis.verifier_key = kVerifierKey;

  const auto encoded = v4::encode_genesis(genesis);
  pv::require(encoded.has_value(), "the founder genesis encodes");
  pv::require(hex(*encoded) == values.at("genesis.bytes_hex"), "genesis bytes");
  pv::require(encoded->size() == expect_size(values, "genesis.bytes"), "genesis width");
  const auto identifier = v4::chain_id(genesis);
  pv::require(identifier.has_value(), "the chain identifier derives");
  pv::require(hex(*identifier) == values.at("genesis.chain_id"), "chain identifier");
  pv::require(v4::kMaxGenesisAccounts == expect_size(values, "genesis.max_accounts"),
              "the account bound");
  pv::require(v4::kGenesisPrefixBytes == expect_size(values, "genesis.prefix_bytes"),
              "the genesis prefix width");

  auto rejected = genesis;
  rejected.supply_limit = 0;
  pv::require(!v4::encode_genesis(rejected).has_value(), "a zero supply limit");
  rejected = genesis;
  rejected.total_supply = 1;
  pv::require(!v4::encode_genesis(rejected).has_value(), "an unconserved supply");
  rejected = genesis;
  rejected.accounts.push_back({});
  pv::require(!v4::encode_genesis(rejected).has_value(), "a zero-balance account");
}

void verify_receipt(const pv::Values& values) {
  v4::Receipt receipt;
  receipt.transaction_id = repeated(0xAB);
  receipt.kind = static_cast<std::uint8_t>(v4::Kind::mint_node);
  receipt.result_code = 0;
  receipt.fee_charged = 1'000;
  receipt.issued_atomic = 57'430'000'000ULL;

  const auto encoded = v4::encode_receipt(receipt);
  pv::require(encoded.has_value(), "the receipt encodes");
  pv::require(hex(*encoded) == values.at("receipt.encoded_hex"), "receipt bytes");
  pv::require(encoded->size() == expect_size(values, "receipt.encoded_bytes"),
              "receipt width");
  const auto decoded = v4::decode_receipt(*encoded);
  pv::require(decoded.has_value(), "the receipt decodes");
  pv::require(decoded->kind == receipt.kind &&
                  decoded->issued_atomic == receipt.issued_atomic,
              "the receipt round trips");

  auto invalid = receipt;
  invalid.kind = 13;
  pv::require(!v4::encode_receipt(invalid).has_value(), "an unknown kind");
  invalid = receipt;
  invalid.result_code = 200;
  pv::require(!v4::encode_receipt(invalid).has_value(), "an unknown result code");
  invalid = receipt;
  invalid.result_code = 20;
  pv::require(!v4::encode_receipt(invalid).has_value(), "a failed receipt charging a fee");
  invalid = receipt;
  invalid.kind = static_cast<std::uint8_t>(v4::Kind::hub_register);
  pv::require(!v4::encode_receipt(invalid).has_value(), "a HUB transaction issuing value");

  // A version-three receipt must read as a contract this reader does not know,
  // which is the misreading a version field exists to prevent.
  auto older = *encoded;
  older[5] = 3;
  pv::require(!v4::decode_receipt(older).has_value(), "a version-three receipt");
}

}  // namespace

int main(int argc, char** argv) {
  try {
    pv::require(argc == 3,
                "usage: economy_v4_tests V4_VECTOR_FILE PRIMITIVES_VECTOR_FILE");
    pv::require(sodium_init() >= 0, "libsodium initialization");
    const auto values = pv::load_values(argv[1]);
    const auto primitives = pv::load_values(argv[2]);

    verify_kind_table(values);
    verify_kind_one_identity(values, primitives);
    verify_admission(values);
    verify_canonical_body_shapes();
    verify_hub_messages(values);
    verify_state_values(values);
    verify_cycle_assignment(values);
    verify_roots(values, primitives);
    verify_genesis(values);
    verify_receipt(values);

    std::cout << "C++ economy transition v4 codec: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "C++ economy transition v4 codec: failed: " << error.what() << '\n';
    return 1;
  }
}
