// Kind 10's new body, kind 23, the three signed constructions, and the approval
// lifetime rule, checked against the recorded vectors.
//
// **The approval is the claim that matters most here, and it is checked as
// behaviour rather than as bytes alone.** It must be the same message whatever
// the HUB field holds, so the signature never signs itself, and a different
// message for every other change, the nonce included, because the nonce is what
// makes one approval good for one transaction. The two kind sets the lifetime
// rule reads are derived from what `approved_bytes` and `carries_hub_proof`
// actually do over every assigned kind, rather than read back from the table
// beside them.
//
// **The kind table is pinned to the files that accepted version nine's**: it
// must equal that table plus exactly kind 23, with kind 10 four octets wider and
// every other width and scheme the one its accepting file recorded.

#include "economy_v10_carried.hpp"

#include <limits>
#include <string>

namespace economy_v10_fixture {
namespace {

constexpr auto kHubRegister = static_cast<std::uint8_t>(v10::Kind::hub_register);
constexpr auto kRegisterMachineKey =
    static_cast<std::uint8_t>(v10::Kind::register_machine_key);
constexpr auto kTransferVerified =
    static_cast<std::uint8_t>(v10::Kind::native_transfer_verified);

v10::Envelope envelope_of(std::uint8_t kind, const v10::Body& body) {
  v10::Envelope envelope;
  envelope.kind = kind;
  envelope.chain_id = kChain;
  envelope.scheme = *v10::kind_scheme(kind);
  envelope.body = v10::encode_body(kind, body);
  pv::require(!envelope.body.empty(), "the fixture body encodes");
  return envelope;
}

v10::Envelope registration(std::uint32_t attester) {
  v10::Body body;
  body.hub_identity_hash = kIdentity;
  body.first_signer_public_key = kFirstSigner;
  body.attesting_seat_id = attester;
  body.attestation_signature = kSignature;
  auto envelope = envelope_of(kHubRegister, body);
  envelope.authority_public_key = kHubKey;
  envelope.valid_until_height = kValidUntil;
  return envelope;
}

v10::Envelope machine_key_registration(const v10::Bytes& hub_signature) {
  v10::Body body;
  body.seat_id = kSeat;
  body.machine_public_key = kMachineKey;
  body.build_digest = kBuildDigest;
  body.attestation_signature = kSignature;
  body.hub_signature = hub_signature;
  auto envelope = envelope_of(kRegisterMachineKey, body);
  envelope.authority_public_key = kSigner;
  envelope.nonce = kSignerNonce;
  envelope.fee_limit = kFixedTransferFee;
  envelope.valid_until_height = kValidUntil;
  return envelope;
}

v10::Envelope confirmed_transfer(const v10::Bytes& hub_signature,
                                 std::uint64_t nonce = kSignerNonce,
                                 std::uint64_t amount = 9) {
  v10::Body body;
  body.recipient_escrow_id = kRecipient;
  body.amount_atomic = amount;
  body.hub_signature = hub_signature;
  auto envelope = envelope_of(kTransferVerified, body);
  envelope.authority_public_key = kSigner;
  envelope.nonce = nonce;
  envelope.fee_limit = kFixedTransferFee;
  envelope.valid_until_height = kValidUntil;
  return envelope;
}

bool round_trips(const v10::Envelope& envelope) {
  const auto decoded = v10::decode_signed(v10::encode_signed(envelope, kSignature));
  if (!decoded) return false;
  const auto& got = decoded->envelope;
  return got.kind == envelope.kind && got.chain_id == envelope.chain_id &&
         got.scheme == envelope.scheme &&
         got.authority_public_key == envelope.authority_public_key &&
         got.nonce == envelope.nonce && got.body == envelope.body &&
         got.fee_limit == envelope.fee_limit &&
         got.valid_until_height == envelope.valid_until_height &&
         decoded->signature == kSignature;
}

void verify_kind_table(const pv::Values& values, const Carried& carried) {
  pv::require(expect_size(values, "widths.kind_10_body") ==
                  v10::body_bytes(kHubRegister),
              "kind 10's body is 132 octets");
  pv::require(expect_size(values, "widths.kind_10_signed") ==
                  v10::signed_bytes(kHubRegister),
              "a signed kind 10 is 292 octets");
  pv::require(expect_size(values, "widths.kind_23_body") ==
                  v10::body_bytes(kRegisterMachineKey),
              "kind 23's body is 196 octets");
  pv::require(expect_size(values, "widths.kind_23_signed") ==
                  v10::signed_bytes(kRegisterMachineKey),
              "a signed kind 23 is 356 octets");

  // **Version ten's kinds are version nine's plus 23, exactly**, with every
  // carried width and scheme the one its accepting file recorded, and kind 10
  // the one carried kind whose width moves.
  auto expected = version_nine_kinds(carried);
  pv::require(!expected.contains(kRegisterMachineKey),
              "version nine never assigned kind 23");
  expected.at(kHubRegister).body_bytes += 4;
  expected[kRegisterMachineKey] = {*v10::body_bytes(kRegisterMachineKey),
                                   v10::kSchemeSigner};
  std::size_t assigned = 0;
  for (std::uint16_t number = 0; number <= 255; ++number) {
    const auto kind = static_cast<std::uint8_t>(number);
    if (!v10::is_transaction_kind(kind)) {
      pv::require(!expected.contains(kind), "every recorded kind is assigned");
      continue;
    }
    ++assigned;
    const auto found = expected.find(kind);
    pv::require(found != expected.end() &&
                    v10::body_bytes(kind) == found->second.body_bytes &&
                    v10::kind_scheme(kind) == found->second.scheme,
                "kind " + std::to_string(number) +
                    " keeps the width and scheme its accepting file recorded");
  }
  pv::require(assigned == 18, "eighteen transaction kinds are assigned");
  pv::require(!v10::is_retired_kind(kRegisterMachineKey),
              "kind 23 reuses no retired number");
}

// The two sets the lifetime rule reads, derived from behaviour over every
// assigned kind with an all-zero body: `approved_bytes` is defined exactly for
// the kinds that carry a body approval, and a zero HUB field carries a proof
// exactly for the kinds that always carry one.
void verify_kind_sets(const pv::Values& values) {
  std::string approval;
  std::string always;
  for (std::uint16_t number = 0; number <= 255; ++number) {
    const auto kind = static_cast<std::uint8_t>(number);
    if (!v10::is_transaction_kind(kind)) continue;
    v10::Envelope envelope;
    envelope.kind = kind;
    envelope.body.assign(*v10::body_bytes(kind), 0);
    pv::require(v10::decode_body(kind, envelope.body).has_value(),
                "an all-zero body decodes for every kind");
    if (v10::approved_bytes(envelope)) {
      approval += (approval.empty() ? "" : ",") + std::to_string(number);
      // Every approval kind's HUB field is its body's last 64 octets, which is
      // why zeroing it changes exactly those octets.
      auto marked = envelope;
      std::fill(marked.body.end() - 64, marked.body.end(), 0x5A);
      pv::require(v10::decode_body(kind, marked.body)->hub_signature == kSignature,
                  "the HUB field is the body's last 64 octets");
      pv::require(v10::carries_hub_proof(marked), "a nonzero HUB field is a proof");
    }
    if (v10::carries_hub_proof(envelope)) {
      always += (always.empty() ? "" : ",") + std::to_string(number);
    }
  }
  pv::require(expect_text(values, "kinds.approval") == approval,
              "the approval kinds are the recorded ones");
  pv::require(expect_text(values, "kinds.always_proven") == always,
              "the always-proven kinds are the recorded ones");
}

void verify_bodies(const pv::Values& values, const Carried& carried) {
  const std::pair<std::string, std::uint32_t> attesters[] = {
      {"launch", v10::kLaunchAttester}, {"machine", kSeat}};
  for (const auto& [name, attester] : attesters) {
    const auto envelope = registration(attester);
    pv::require(hex(v10::encode_unsigned(envelope)) ==
                    expect_text(values, "bodies.kind_10_" + name + "_unsigned"),
                "the registration is the recorded one");
    expect_claim(values, "bodies.kind_10_" + name + "_round_trips",
                 round_trips(envelope) &&
                     v10::decode_body(kHubRegister, envelope.body)->attesting_seat_id ==
                         attester);
  }
  const auto envelope = machine_key_registration(kSignature);
  pv::require(hex(v10::encode_unsigned(envelope)) ==
                  expect_text(values, "bodies.kind_23_unsigned"),
              "the machine-key registration is the recorded one");
  const auto fields = v10::decode_body(kRegisterMachineKey, envelope.body);
  expect_claim(values, "bodies.kind_23_round_trips",
               round_trips(envelope) && fields && fields->seat_id == kSeat &&
                   fields->machine_public_key == kMachineKey &&
                   fields->build_digest == kBuildDigest &&
                   fields->attestation_signature == kSignature &&
                   fields->hub_signature == kSignature);

  // Kind 1 keeps the bytes version one accepted, which version six's file
  // recorded, so the claim is about this framing and an accepted artifact.
  const auto accepted = bytes_from_hex(carried.six.at("compatibility.unsigned_transfer_hex"));
  auto signed_transfer = accepted;
  signed_transfer.insert(signed_transfer.end(), kSignature.begin(), kSignature.end());
  const auto transfer = v10::decode_signed(signed_transfer);
  expect_claim(values, "bodies.kind_1_bytes_are_version_nines",
               transfer.has_value() &&
                   v10::encode_unsigned(transfer->envelope) == accepted &&
                   accepted.size() ==
                       std::stoull(carried.six.at("compatibility.unsigned_transfer_bytes")));

  // A version-nine registration, 288 octets as version six's file records the
  // width, framed exactly as this codec frames a transaction but with the
  // 128-octet body that has no attesting seat.
  auto nine = registration(kSeat);
  v10::Bytes body(kIdentity.begin(), kIdentity.end());
  body.insert(body.end(), kFirstSigner.begin(), kFirstSigner.end());
  body.insert(body.end(), kSignature.begin(), kSignature.end());
  nine.body = body;
  const auto nine_signed = v10::encode_signed(nine, kSignature);
  expect_claim(values, "bodies.version_nine_registration_is_malformed",
               nine_signed.size() ==
                       std::stoull(carried.six.at("envelope.kind10.signed_bytes")) &&
                   !v10::decode_signed(nine_signed));
}

void verify_messages(const pv::Values& values) {
  pv::require(hex(v10::registration_message(kChain, v10::kLaunchAttester, kIdentity,
                                            kHubKey, kFirstSigner, kValidUntil)) ==
                  expect_text(values, "messages.registration_launch"),
              "the launch registration message is the recorded one");
  pv::require(hex(v10::registration_message(kChain, kSeat, kIdentity, kHubKey,
                                            kFirstSigner, kValidUntil)) ==
                  expect_text(values, "messages.registration_machine"),
              "the machine registration message is the recorded one");
  pv::require(hex(v10::attestation_message(kChain, kSeat, kMachineKey, kBuildDigest,
                                           kValidUntil)) ==
                  expect_text(values, "messages.attestation"),
              "the attestation message is the recorded one");

  const auto approved = v10::approval_message(confirmed_transfer(kSignature));
  const auto machine = v10::approval_message(machine_key_registration(kSignature));
  pv::require(approved && hex(*approved) == expect_text(values, "messages.approval_kind_19"),
              "kind 19's approval is the recorded one");
  pv::require(machine && hex(*machine) == expect_text(values, "messages.approval_kind_23"),
              "kind 23's approval is the recorded one");
  expect_claim(values, "messages.approval_ignores_the_hub_field",
               v10::approval_message(confirmed_transfer(kNoSignature)) == approved);
  expect_claim(values, "messages.approval_binds_the_nonce",
               v10::approval_message(confirmed_transfer(kSignature, kSignerNonce + 1)) !=
                   approved);
  expect_claim(values, "messages.approval_binds_the_amount",
               v10::approval_message(confirmed_transfer(kSignature, kSignerNonce, 10)) !=
                   approved);
  const auto approved_bytes = v10::approved_bytes(confirmed_transfer(kSignature));
  expect_claim(values, "messages.approval_is_not_the_envelope_message",
               approved_bytes && v10::signing_message(*approved_bytes) != *approved);

  v10::Envelope transfer;
  transfer.kind = static_cast<std::uint8_t>(v10::Kind::native_transfer);
  transfer.body.assign(*v10::body_bytes(transfer.kind), 0);
  pv::require(!v10::approved_bytes(transfer) && !v10::approval_message(transfer),
              "a kind with no body approval has no approval message");
}

void verify_lifetime(const pv::Values& values) {
  constexpr std::uint64_t kHeight = 50;
  const std::pair<std::string, v10::Envelope> governed[] = {
      {"kind_19", confirmed_transfer(kSignature)},
      {"kind_23", machine_key_registration(kSignature)},
      {"kind_10", registration(kSeat)},
  };
  for (const auto& [name, envelope] : governed) {
    auto at_bound = envelope;
    at_bound.valid_until_height = kHeight + v10::kApprovalLifetimeBlocks;
    auto past = envelope;
    past.valid_until_height = kHeight + v10::kApprovalLifetimeBlocks + 1;
    expect_claim(values, "lifetime." + name + "_at_the_bound_is_accepted",
                 !v10::approval_lifetime_exceeded(at_bound, kHeight));
    expect_claim(values, "lifetime." + name + "_past_the_bound_is_refused",
                 v10::approval_lifetime_exceeded(past, kHeight));
  }
  auto far = confirmed_transfer(kNoSignature);
  far.valid_until_height = 10'000'000'000ULL;
  expect_claim(values, "lifetime.an_absent_field_is_not_governed",
               !v10::approval_lifetime_exceeded(far, kHeight));

  // The bound is never formed as a sum, so it holds at the top of the range: a
  // proof one slot from `u64` maximum is inside its life, and the whole range
  // above a height of zero is outside it.
  constexpr auto kMax = std::numeric_limits<std::uint64_t>::max();
  auto top = confirmed_transfer(kSignature);
  top.valid_until_height = kMax;
  pv::require(!v10::approval_lifetime_exceeded(top, kMax - v10::kApprovalLifetimeBlocks),
              "a validity one slot above a height near the top is inside the bound");
  pv::require(v10::approval_lifetime_exceeded(top, 0),
              "a validity at the top of the range is far outside the bound at zero");
  top.valid_until_height = 0;
  pv::require(!v10::approval_lifetime_exceeded(top, kMax),
              "an expired validity is EXPIRED's to refuse, not the lifetime's");
}

}  // namespace

void verify_kinds(const pv::Values& values, const Carried& carried) {
  verify_kind_table(values, carried);
  verify_kind_sets(values);
  verify_bodies(values, carried);
  verify_messages(values);
  verify_lifetime(values);
}

}  // namespace economy_v10_fixture
