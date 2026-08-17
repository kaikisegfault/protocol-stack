// The version-six envelope: fourteen kinds, five retired numbers, two
// authorization schemes, the admission shape rules, and the six HUB messages.
//
// Every assertion compares against `test-vectors/economy-transition-v6.txt`,
// except the kind-1 identity, which is compared against
// `test-vectors/protocol-primitives-v1.txt` as well: if the version-six encoder
// does not emit the accepted M1 transfer bytes the compatibility boundary is
// broken at its narrowest point and nothing after it is worth checking.

#include "economy_v6_fixture.hpp"

#include <utility>

namespace economy_v6_fixture {
namespace {

void verify_kind_table(const pv::Values& values) {
  const std::uint8_t assigned[] = {1, 2, 3, 4, 5, 6, 10, 13, 14, 15, 16, 17, 18, 19};
  std::size_t largest = 0;
  std::size_t collisions_at_96 = 0;
  for (const auto kind : assigned) {
    const auto prefix = "envelope.kind" + std::to_string(kind) + ".";
    const auto body = v6::body_bytes(kind);
    const auto unsigned_size = v6::unsigned_bytes(kind);
    const auto signed_size = v6::signed_bytes(kind);
    const auto scheme = v6::kind_scheme(kind);
    pv::require(body && unsigned_size && signed_size && scheme, "kind is unknown");
    pv::require(*body == expect_size(values, prefix + "body_bytes"), "body width");
    pv::require(*unsigned_size == expect_size(values, prefix + "unsigned_bytes"),
                "unsigned width");
    pv::require(*signed_size == expect_size(values, prefix + "signed_bytes"),
                "signed width");
    pv::require(*scheme == expect_number(values, prefix + "scheme"), "kind scheme");
    largest = std::max(largest, *signed_size);
    if (*body == 96) ++collisions_at_96;
  }
  pv::require(std::size(assigned) == expect_size(values, "envelope.kind_count"),
              "the assigned kind count");
  pv::require(largest == expect_size(values, "envelope.largest_signed_bytes"),
              "the largest transaction");

  // The one anticipated length collision: five kinds share a 96-octet body, so
  // a decoder dispatches on the kind byte and never on the length.
  const auto recorded = expect_text(values, "envelope.length_collision.96");
  const auto group = std::count(recorded.begin(), recorded.end(), ',') + 1;
  pv::require(collisions_at_96 == static_cast<std::size_t>(group),
              "the 96-octet collision group");
  pv::require(expect_size(values, "envelope.length_collision_groups") == 1,
              "exactly one collision group");
  pv::require(expect_size(values, "envelope.scheme_count") == 2, "two schemes");
  pv::require(expect_size(values, "envelope.header_bytes") == v6::kHeaderBytes &&
                  expect_size(values, "envelope.trailer_bytes") == v6::kTrailerBytes &&
                  expect_size(values, "envelope.signature_bytes") ==
                      v6::kSignatureBytes,
              "the envelope decomposition");

  // The five retired numbers have no width and no scheme, so they are refused
  // exactly as a never-assigned number is and audited differently.
  const std::uint8_t retired[] = {7, 8, 9, 11, 12};
  for (const auto kind : retired) {
    pv::require(v6::is_retired_kind(kind), "the number is retired");
    pv::require(!v6::is_transaction_kind(kind), "a retired kind has no width");
    expect_true(values, "envelope.retired" + std::to_string(kind) + ".is_unassigned");
  }
  pv::require(std::size(retired) ==
                  expect_size(values, "envelope.retired_kind_count"),
              "the retired kind count");
  pv::require(!v6::is_transaction_kind(0) && !v6::is_transaction_kind(20),
              "the assigned range is closed at both ends");
}

void verify_kind_one_identity(const pv::Values& values,
                              const pv::Values& primitives) {
  auto envelope = transfer_envelope(kUnregisteredRecipient, 1'000'000);
  const auto key = pv::hex_decode(primitives.at("rfc8032.public_key"));
  pv::require(key.size() == 32, "public key size");
  std::copy(key.begin(), key.end(), envelope.authority_public_key.begin());

  const auto unsigned_bytes = v6::encode_unsigned(envelope);
  pv::require(hex(unsigned_bytes) == primitives.at("unsigned_tx"),
              "kind 1 reproduces the accepted unsigned transfer");
  pv::require(hex(unsigned_bytes) ==
                  expect_text(values, "compatibility.unsigned_transfer_hex"),
              "kind 1 matches the recorded version-six vector");
  pv::require(unsigned_bytes.size() ==
                  expect_size(values, "compatibility.unsigned_transfer_bytes"),
              "the unsigned width");

  const auto signature = pv::hex_decode(primitives.at("signature"));
  const auto signed_bytes = v6::encode_signed(envelope, signature);
  pv::require(hex(signed_bytes) == primitives.at("signed_tx"),
              "kind 1 reproduces the accepted signed transfer");
  pv::require(signed_bytes.size() ==
                  expect_size(values, "compatibility.signed_transfer_bytes"),
              "the signed width");
  pv::require(hex(v6::transaction_id(signed_bytes)) == primitives.at("tx_id"),
              "kind 1 reproduces the accepted transaction ID");

  // The header and trailer must be slices of the accepted bytes rather than a
  // re-encoding of them, which is what makes the factoring a partition.
  const auto accepted = pv::hex_decode(primitives.at("unsigned_tx"));
  pv::require(std::equal(accepted.begin(), accepted.begin() + v6::kHeaderBytes,
                         unsigned_bytes.begin()),
              "the header is the accepted transfer's first 80 octets");
  pv::require(std::equal(accepted.end() - v6::kTrailerBytes, accepted.end(),
                         unsigned_bytes.end() - v6::kTrailerBytes),
              "the trailer is the accepted transfer's last 16 octets");

  // The execution boundary this version moves. The codec cannot return the
  // refusal, so what it establishes is that the accepted bytes name a recipient
  // no conforming chain can hold — reaching a chosen escrow identifier is a
  // SHA-256 preimage — and that a transfer to a real escrow is different bytes.
  pv::require(expect_text(values, "compatibility.unregistered_recipient_code") ==
                  *v6::result_code_name(static_cast<std::uint8_t>(
                      v6::Result::recipient_not_registered)),
              "the refusal names the version-six code");
  auto registered = transfer_envelope(to_octets(kBobEscrow), 1'000'000);
  registered.authority_public_key = envelope.authority_public_key;
  pv::require(v6::encode_unsigned(registered) != unsigned_bytes,
              "a transfer to a registered escrow is different bytes");
  expect_true(values, "compatibility.accepted_recipient_is_not_a_registered_escrow");
  expect_true(values, "compatibility.transfer_to_a_registered_escrow_is_representable");
}

void verify_admission(const pv::Values& values) {
  const v6::Bytes signature(v6::kSignatureBytes, 0x11);
  const auto accepted =
      v6::encode_signed(transfer_envelope(kUnregisteredRecipient, 1'000'000),
                        signature);
  pv::require(v6::decode_signed(accepted).has_value(),
              "the positive control decodes");
  expect_true(values, "admission.positive_control_decodes");

  auto mutate = [&accepted](std::size_t offset, std::uint8_t octet) {
    auto copy = accepted;
    copy[offset] = octet;
    return copy;
  };
  pv::require(!v6::decode_signed(mutate(0, 'X')).has_value(), "wrong magic");
  pv::require(!v6::decode_signed(mutate(5, 2)).has_value(), "wrong schema version");
  pv::require(!v6::decode_signed(mutate(6, 0)).has_value(), "kind zero");
  pv::require(!v6::decode_signed(mutate(6, 20)).has_value(), "unknown kind");
  pv::require(!v6::decode_signed(mutate(6, 7)).has_value(), "retired kind 7");
  pv::require(!v6::decode_signed(mutate(6, 11)).has_value(), "retired kind 11");
  pv::require(!v6::decode_signed(mutate(39, 3)).has_value(), "unknown scheme");
  // Scheme 2 is a real scheme and one kind 1 does not permit, which is a
  // separate rule from an unknown number and the same refusal.
  pv::require(!v6::decode_signed(mutate(39, v6::kSchemeIdentity)).has_value(),
              "a scheme this kind forbids");

  auto trailing = accepted;
  trailing.push_back(0);
  pv::require(!v6::decode_signed(trailing).has_value(), "trailing byte");
  auto truncated = accepted;
  truncated.pop_back();
  pv::require(!v6::decode_signed(truncated).has_value(), "truncated");

  // A non-minimal absent referrer: the flag says there is none and the field
  // holds something, which would be a second encoding of one transaction.
  auto purchase = body_envelope(v6::Kind::purchase_seat);
  pv::require(v6::decode_signed(v6::encode_signed(purchase, signature)).has_value(),
              "an absent referrer of 32 zero octets is canonical");
  purchase.body[5] = 1;
  pv::require(!v6::decode_signed(v6::encode_signed(purchase, signature)).has_value(),
              "a non-minimal absent referrer is refused");
  purchase.body[5] = 0;
  purchase.body[4] = 2;
  pv::require(!v6::decode_signed(v6::encode_signed(purchase, signature)).has_value(),
              "a non-canonical has_referrer byte is refused");

  // The slot mask names hours of a 24-slot window, so its high 8 bits are zero.
  auto posture = body_envelope(v6::Kind::set_security_posture);
  posture.body[0] = 1;
  for (std::size_t index = 0; index < 4; ++index) {
    posture.body[9 + index] =
        static_cast<std::uint8_t>(v6::kMaxExemptSlotMask >> (8 * (3 - index)));
  }
  pv::require(v6::decode_signed(v6::encode_signed(posture, signature)).has_value(),
              "every one of the 24 slots may be exempt");
  posture.body[9] = 1;
  pv::require(!v6::decode_signed(v6::encode_signed(posture, signature)).has_value(),
              "a slot above 23 is refused");
  posture.body[9] = 0;
  posture.body[0] = 2;
  pv::require(!v6::decode_signed(v6::encode_signed(posture, signature)).has_value(),
              "a non-canonical confirmation flag is refused");

  // ADR 0045's second derived rule, pinned from the admitting side. Version six
  // requires an unrequested 64-octet confirmation field to be zero, places the
  // rule at admission, and names `MALFORMED_TRANSACTION`; neither survives
  // contact with the rest of the contract, because whether a confirmation is
  // required is a predicate over the escrow's *stored* posture and admission
  // reads no state. So a mint carrying one is admitted here and refused at
  // execution with `UNAUTHORIZED`.
  //
  // This is a positive control rather than a refusal, and it is deliberate: an
  // implementation that refused it here would be stricter than the contract can
  // be, and without this check nothing in this file or in either accepted
  // vector file would notice.
  auto confirmed_mint = body_envelope(v6::Kind::mint_referral);
  std::fill(confirmed_mint.body.begin() + 32, confirmed_mint.body.end(), 0x44);
  pv::require(
      v6::decode_signed(v6::encode_signed(confirmed_mint, signature)).has_value(),
      "a mint carrying a confirmation is admitted, because admission reads no "
      "posture");
  pv::require(v6::decode_signed(
                  v6::encode_signed(body_envelope(v6::Kind::mint_referral), signature))
                  .has_value(),
              "and so is one carrying 64 zero octets");

  // A registration has no escrow, so it has no sequence to advance and nothing
  // to charge. Both fields are required to be zero rather than merely ignored,
  // so one registration has exactly one encoding.
  auto registration = body_envelope(v6::Kind::hub_register);
  pv::require(
      v6::decode_signed(v6::encode_signed(registration, signature)).has_value(),
      "a zero-nonce fee-exempt registration decodes");
  registration.nonce = 1;
  pv::require(
      !v6::decode_signed(v6::encode_signed(registration, signature)).has_value(),
      "a registration with a nonzero nonce is refused");
  registration.nonce = 0;
  registration.fee_limit = 1;
  pv::require(
      !v6::decode_signed(v6::encode_signed(registration, signature)).has_value(),
      "a registration with a nonzero fee limit is refused");

  for (const auto* key : {"admission.refuses_wrong_magic",
                          "admission.refuses_wrong_schema_version",
                          "admission.refuses_unknown_kind",
                          "admission.refuses_retired_kind",
                          "admission.refuses_unknown_scheme",
                          "admission.refuses_scheme_this_kind_forbids",
                          "admission.refuses_trailing_suffix",
                          "admission.refuses_truncated",
                          "admission.refuses_non_minimal_absent_referrer",
                          "admission.refuses_slot_mask_above_slot_23",
                          "admission.refuses_non_canonical_confirmation_flag",
                          "admission.refuses_registration_with_a_nonzero_nonce",
                          "admission.refuses_registration_with_a_nonzero_fee_limit"}) {
    expect_true(values, key);
  }
  pv::require(expect_size(values, "admission.code_count") == 3,
              "admission's own three-code space");

  // A same-length relabelling decodes as the kind its byte names and changes
  // the signing message, which is what makes the kind byte load-bearing across
  // the five-way collision. A relabelling across schemes is refused earlier.
  auto referral = body_envelope(v6::Kind::mint_referral, 0x22);
  const auto referral_raw = v6::encode_signed(referral, signature);
  auto across_schemes = referral_raw;
  across_schemes[6] = static_cast<std::uint8_t>(v6::Kind::signer_add);
  pv::require(!v6::decode_signed(across_schemes).has_value(),
              "a relabelling across schemes is refused");
  auto within_scheme = referral_raw;
  within_scheme[6] = static_cast<std::uint8_t>(v6::Kind::mint_verified_user);
  const auto decoded = v6::decode_signed(within_scheme);
  pv::require(decoded.has_value(), "a same-scheme relabelling decodes");
  pv::require(decoded->envelope.kind ==
                  static_cast<std::uint8_t>(v6::Kind::mint_verified_user),
              "and is read as the kind its byte names");
  pv::require(v6::signing_message(v6::encode_unsigned(decoded->envelope)) !=
                  v6::signing_message(v6::encode_unsigned(referral)),
              "so the signing message changes");
}

void verify_hub_messages(const pv::Values& values) {
  const auto chain = std::span<const std::uint8_t>(kChainId);
  const auto alice = std::span<const std::uint8_t>(kAliceIdentity);
  const auto escrow = std::span<const std::uint8_t>(kAliceFirstEscrow.data(),
                                                    kAliceFirstEscrow.size());
  const auto bob_escrow =
      std::span<const std::uint8_t>(kBobEscrow.data(), kBobEscrow.size());

  const std::pair<const char*, v6::Bytes> built[] = {
      {"registration", v6::registration_message(chain, alice, kAliceKey,
                                                kAliceSignerKey, kValidUntil)},
      {"purchase", v6::purchase_message(chain, alice, 0, kValidUntil)},
      {"activation", v6::activation_message(chain, alice, 0, kValidUntil)},
      {"mint",
       v6::mint_message(chain, alice, static_cast<std::uint8_t>(v6::Kind::mint_node),
                        0, escrow, kValidUntil)},
      {"posture_relax",
       v6::posture_relax_message(chain, alice, escrow, v6::Posture{}, kValidUntil)},
      {"transfer_confirm", v6::transfer_confirm_message(chain, alice, escrow,
                                                        bob_escrow, 1, kValidUntil)},
  };
  for (const auto& [name, message] : built) {
    const std::string prefix = std::string("hub.") + name + ".";
    pv::require(hex(message) == expect_text(values, prefix + "hex"),
                "HUB message bytes");
    pv::require(message.size() == expect_size(values, prefix + "bytes"),
                "HUB message width");
  }
  pv::require(std::size(built) == expect_size(values, "hub.message_count"),
              "six messages");
  pv::require(expect_size(values, "hub.verifier_signed_count") == 1,
              "only the registration verifies against the verifier key");

  for (std::size_t left = 0; left < std::size(built); ++left) {
    for (std::size_t right = left + 1; right < std::size(built); ++right) {
      pv::require(built[left].second != built[right].second,
                  "the six messages are pairwise distinct");
    }
  }
  expect_true(values, "hub.messages_are_pairwise_distinct");

  // The mint message binds the kind, which is what stops a confirmation
  // obtained for one mint being replayed onto a different one. Kinds 5 and 18
  // carry no seat, so every remaining field coincides and only the kind byte
  // separates them.
  const std::uint8_t mints[] = {
      static_cast<std::uint8_t>(v6::Kind::mint_node),
      static_cast<std::uint8_t>(v6::Kind::mint_referral),
      static_cast<std::uint8_t>(v6::Kind::mint_verified_user),
  };
  pv::require(std::size(mints) == expect_size(values, "hub.confirmable_mint_count"),
              "three confirmable mints");
  for (std::size_t left = 0; left < std::size(mints); ++left) {
    for (std::size_t right = left + 1; right < std::size(mints); ++right) {
      pv::require(v6::mint_message(chain, alice, mints[left], 0, escrow, kValidUntil) !=
                      v6::mint_message(chain, alice, mints[right], 0, escrow,
                                       kValidUntil),
                  "the three mint messages differ by kind alone");
    }
  }
  expect_true(values, "hub.mint_messages_differ_by_kind");

  // A posture-relax signature binds the exact posture it approves, so an
  // approval to raise a minimum cannot be presented as one to turn confirmation
  // off; and every message binds the identity.
  v6::Posture other;
  other.min_amount_atomic = 100'000'000;
  pv::require(v6::posture_relax_message(chain, alice, escrow, other, kValidUntil) !=
                  built[4].second,
              "a different posture is a different message");
  expect_true(values, "hub.posture_message_binds_the_exact_posture");
  pv::require(v6::mint_message(chain, kBobIdentity, mints[0], 0, escrow, kValidUntil) !=
                  built[3].second,
              "rebinding the identity changes the message");
}

}  // namespace

void verify_encoding(const pv::Values& values, const pv::Values& primitives) {
  verify_kind_table(values);
  verify_kind_one_identity(values, primitives);
  verify_admission(values);
  verify_hub_messages(values);
}

}  // namespace economy_v6_fixture
