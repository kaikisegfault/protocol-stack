// Transaction kind 22, checked against the recorded vectors.
//
// **The whole of kind 22 is kind 4 with a different byte, and that is the claim
// to check rather than a convenience to note.** Its body is kind 4's field for
// field, its scheme is kind 4's, its refusal ladder is kind 4's, and the HUB
// confirmation it presents is version six's message with the kind byte changed.
// So the checks here are mostly equalities against kind 4 and one inequality
// against it: the four confirmable mints must produce four different messages on
// otherwise identical fields, because that is the only thing stopping a
// confirmation obtained for one from being presented for another.

#include "economy_v9_fixture.hpp"

#include "protocol/v8/economy.hpp"

#include <algorithm>
#include <set>
#include <string>

namespace economy_v9_fixture {
namespace {

namespace v8 = protocol::v8;

constexpr std::uint8_t kMintPool = 22;
// The recorded fixture's. The body's seat and the message's seat differ on
// purpose: the two are separate recordings and nothing ties them together.
constexpr std::uint32_t kBodySeat = 3;
constexpr std::uint32_t kMessageSeat = 7;
constexpr std::uint64_t kValidUntil = 4321;

const v9::Octets32 kDestination = repeated(0x31);
const v9::Bytes kHubSignature = v9::Bytes(64, 0x9C);
const v9::Octets32 kIdentity = ascending(32);
const v9::Octets32 kAuthorityKey = repeated(0x5A);

v9::Body fixture_body() {
  v9::Body body;
  body.seat_id = kBodySeat;
  body.destination_escrow_id = kDestination;
  body.hub_signature = kHubSignature;
  return body;
}

void verify_body(const pv::Values& values, const pv::Values& carried_six) {
  const auto width = v9::body_bytes(kMintPool);
  pv::require(width.has_value(), "kind 22 is an assigned kind");
  pv::require(expect_size(values, "kind22.body_bytes") == *width,
              "kind 22's body is 100 octets");
  pv::require(expect_number(values, "kind22.transaction_kind") == kMintPool,
              "the kind number is 22");

  // Kind 4's width comes from the file that accepted it rather than from a
  // figure restated here, so "kind 22's body is kind 4's" is a claim about two
  // accepted artifacts.
  const auto mint_node = static_cast<std::uint8_t>(v9::Kind::mint_node);
  pv::require(*width == v9::body_bytes(mint_node),
              "kind 22's body is kind 4's width");
  pv::require(*width == std::stoull(carried_six.at("envelope.kind4.body_bytes")),
              "kind 4's width is the one version six recorded");
  expect_true(values, "kind22.body_equals_mint_node");

  const auto scheme = v9::kind_scheme(kMintPool);
  pv::require(scheme.has_value(), "kind 22 fixes a scheme");
  pv::require(expect_number(values, "kind22.scheme") == *scheme,
              "kind 22 is scheme 1");
  pv::require(*scheme == v9::kind_scheme(mint_node),
              "kind 22's scheme is kind 4's");

  std::size_t assigned = 0;
  for (std::uint16_t kind = 0; kind <= 255; ++kind) {
    if (v9::is_transaction_kind(static_cast<std::uint8_t>(kind))) ++assigned;
  }
  pv::require(expect_size(values, "kind22.transaction_kind_count") == assigned,
              "seventeen transaction kinds are assigned");
  pv::require(!v9::is_retired_kind(kMintPool),
              "kind 22 reuses no retired number");
  pv::require(!v8::is_transaction_kind(kMintPool),
              "version eight never assigned kind 22");

  const auto body = fixture_body();
  const auto encoded = v9::encode_body(kMintPool, body);
  pv::require(hex(encoded) == expect_text(values, "kind22.body"),
              "the encoded body is the recorded one");
  pv::require(encoded.size() == *width, "the encoded body is its declared width");
  // Kind 4 over the same fields produces the same octets, which is the sharpest
  // available statement that the two bodies are one layout rather than two.
  pv::require(v9::encode_body(mint_node, body) == encoded,
              "kind 4 over the same fields produces the same body");

  const auto decoded = v9::decode_body(kMintPool, encoded);
  pv::require(decoded.has_value(), "the body decodes");
  pv::require(decoded->seat_id == kBodySeat &&
                  decoded->destination_escrow_id == kDestination &&
                  decoded->hub_signature == kHubSignature,
              "the body round-trips field for field");

  // **Issuing, which the receipt is what decides.** A kind-22 receipt carrying a
  // minted amount must be consistent and a non-issuing kind's must not, so the
  // claim is checked through the predicate a chain actually applies.
  v9::Receipt receipt;
  receipt.kind = kMintPool;
  receipt.result_code = 0;
  receipt.fee_charged = kFixedTransferFee;
  receipt.issued_atomic = 1;
  pv::require(v9::receipt_is_consistent(receipt),
              "a kind-22 receipt may record an issued amount");
  receipt.kind = static_cast<std::uint8_t>(v9::Kind::native_transfer);
  pv::require(!v9::receipt_is_consistent(receipt),
              "a transfer receipt may not record an issued amount");
  expect_true(values, "kind22.is_issuing_kind");
}

void verify_envelope(const pv::Values& values) {
  const auto signed_width = v9::signed_bytes(kMintPool);
  pv::require(signed_width.has_value(), "kind 22 has a signed width");
  pv::require(expect_size(values, "kind22.signed_length") == *signed_width,
              "a signed kind-22 transaction is 260 octets");
  pv::require(expect_size(values, "kind22.signed_bytes") == *signed_width,
              "both recorded widths are the same figure");
  pv::require(*signed_width == v9::signed_bytes(
                                   static_cast<std::uint8_t>(v9::Kind::mint_node)),
              "kind 22's signed width is kind 4's");

  v9::Envelope envelope;
  envelope.kind = kMintPool;
  envelope.chain_id = ascending(0);
  envelope.scheme = v9::kSchemeSigner;
  envelope.authority_public_key = kAuthorityKey;
  envelope.nonce = 4;
  envelope.body = v9::encode_body(kMintPool, fixture_body());
  envelope.fee_limit = kFixedTransferFee;
  envelope.valid_until_height = kValidUntil;

  const auto signature = v9::Bytes(64, 0x77);
  const auto raw = v9::encode_signed(envelope, signature);
  pv::require(raw.size() == *signed_width, "the signed transaction is its width");
  const auto decoded = v9::decode_signed(raw);
  pv::require(decoded.has_value(), "the signed transaction decodes");
  pv::require(decoded->envelope.kind == kMintPool &&
                  decoded->envelope.body == envelope.body &&
                  decoded->signature == signature,
              "the signed transaction round-trips");
  expect_true(values, "kind22.round_trips");

  // Version eight is still compiled, so the boundary is executed rather than
  // asserted: its admission step refuses these bytes because it knows no kind 22
  // at all, which is a refusal by shape rather than a misreading.
  pv::require(!v8::decode_signed(v8::Bytes(raw.begin(), raw.end())),
              "a version-eight decoder refuses a kind-22 transaction");
  expect_true(values, "kind22.version_eight_refuses_it");
}

void verify_mint_message(const pv::Values& values) {
  const auto message = v9::mint_message(ascending(0), kIdentity, kMintPool,
                                        kMessageSeat, kDestination, kValidUntil);
  pv::require(hex(message) == expect_text(values, "kind22.mint_message"),
              "the mint message is the recorded one");

  // **The four confirmable mints on identical fields.** Every term but the kind
  // byte is the same in all four, which is the point: version six's message
  // binds `u8(transaction_kind)` precisely so a confirmation obtained for one
  // mint cannot be presented for another, and nothing else here separates them.
  // Distinctness is required pairwise rather than as a set size, so a collision
  // names the pair that collided.
  struct Mint {
    std::uint8_t kind;
    std::uint32_t seat;
  };
  const Mint mints[] = {
      {static_cast<std::uint8_t>(v9::Kind::mint_node), kMessageSeat},
      {static_cast<std::uint8_t>(v9::Kind::mint_referral), kMessageSeat},
      {static_cast<std::uint8_t>(v9::Kind::mint_verified_user), kMessageSeat},
      {kMintPool, kMessageSeat},
  };
  std::vector<v9::Bytes> messages;
  for (const auto& mint : mints) {
    messages.push_back(v9::mint_message(ascending(0), kIdentity, mint.kind,
                                        mint.seat, kDestination, kValidUntil));
  }
  for (std::size_t first = 0; first < messages.size(); ++first) {
    for (std::size_t second = first + 1; second < messages.size(); ++second) {
      pv::require(messages[first] != messages[second],
                  "two confirmable mints must not share a message");
    }
  }
  // And the pair that differ in nothing but the kind byte must differ in exactly
  // one octet, which is what makes the separation the kind's rather than the
  // seat's.
  std::size_t differing = 0;
  pv::require(messages[0].size() == messages[3].size(), "same construction");
  for (std::size_t index = 0; index < messages[0].size(); ++index) {
    if (messages[0][index] != messages[3][index]) ++differing;
  }
  pv::require(differing == 1,
              "kind 4 and kind 22 differ in exactly the kind byte");
  expect_true(values, "kind22.four_mint_messages_are_distinct");

  // Version eight builds version six's message too, so "no new label is added"
  // is checked by requiring the two kernels to agree byte for byte on a kind
  // version eight does know.
  const auto here = v9::mint_message(ascending(0), kIdentity,
                                     static_cast<std::uint8_t>(v9::Kind::mint_node),
                                     kMessageSeat, kDestination, kValidUntil);
  const auto there = v8::mint_message(ascending(0), kIdentity,
                                      static_cast<std::uint8_t>(v8::Kind::mint_node),
                                      kMessageSeat, kDestination, kValidUntil);
  pv::require(std::equal(here.begin(), here.end(), there.begin(), there.end()),
              "version nine's mint message is version six's construction");
  expect_true(values, "kind22.mint_message_agrees_with_version_six");
}

}  // namespace

void verify_kinds(const pv::Values& values, const pv::Values& carried_six) {
  verify_body(values, carried_six);
  verify_envelope(values);
  verify_mint_message(values);
}

}  // namespace economy_v9_fixture
