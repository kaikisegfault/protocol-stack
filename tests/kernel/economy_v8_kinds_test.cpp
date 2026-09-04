// The two transaction kinds, their admission rules, and the result-code space.
//
// **The fee exemption is asked as an admission outcome rather than by reading a
// decoded field.** A change that also exempted the dispute would make the
// decoder refuse it, and a check that indexed into the refused result would
// crash instead of failing a vector. The refusal is the subject here, so it is
// the value.
//
// The carried surface is compared against `test-vectors/economy-transition-v6.txt`,
// the file that accepted it: the fourteen carried bodies, the thirty-three
// carried result codes, and one HUB message reproduced as bytes, which is what
// makes "the HUB message labels are still version six's" a claim about an
// encoder rather than about a string.

#include "economy_v8_fixture.hpp"

#include <set>
#include <string>
#include <utility>

namespace economy_v8_fixture {
namespace {

constexpr std::uint8_t kChallengeResponse = 20;
constexpr std::uint8_t kFileDispute = 21;
constexpr std::uint8_t kCarriedKinds[] = {1, 2,  3,  4,  5,  6,  10, 13,
                                          14, 15, 16, 17, 18, 19};
constexpr std::uint8_t kRetiredKinds[] = {7, 8, 9, 11, 12};

// The version-six fixture the recorded HUB messages were taken over.
const v8::Octets32 kMessageChainId = ascending(0);
const v8::Octets32 kMessageIdentity = repeated(0xA1);
constexpr std::uint64_t kMessageValidUntil = 42;

// A well-formed transaction of one of the two added kinds, with everything but
// the field under test held fixed.
v8::Bytes response_bytes(std::uint64_t fee_limit, std::uint64_t nonce) {
  v8::Envelope envelope;
  envelope.kind = kChallengeResponse;
  envelope.scheme = v8::kSchemeSigner;
  envelope.authority_public_key = repeated(0x9A);
  envelope.nonce = nonce;
  envelope.fee_limit = fee_limit;
  envelope.valid_until_height = 99;
  v8::Body body;
  body.seat_id = kProbeSeat;
  body.challenge_height = 40;
  body.answer.assign(v8::kAnswerBytes, 0);
  envelope.body = v8::encode_body(kChallengeResponse, body);
  return v8::encode_signed(envelope, v8::Bytes(v8::kSignatureBytes, 0x5B));
}

v8::Bytes dispute_bytes(std::uint64_t fee_limit) {
  v8::Envelope envelope;
  envelope.kind = kFileDispute;
  envelope.scheme = v8::kSchemeSigner;
  envelope.authority_public_key = repeated(0x9A);
  envelope.nonce = 4;
  envelope.fee_limit = fee_limit;
  envelope.valid_until_height = 99;
  v8::Body body;
  body.seat_id = kProbeSeat;
  body.cycle_window = 1;
  body.slot_index = 3;
  body.reason_code = 1;
  body.authority_signature.assign(v8::kSignatureBytes, 0x6C);
  envelope.body = v8::encode_body(kFileDispute, body);
  return v8::encode_signed(envelope, v8::Bytes(v8::kSignatureBytes, 0x5B));
}

void verify_kind_space(const pv::Values& values, const pv::Values& carried) {
  pv::require(expect_number(values, "kind.challenge_response") == kChallengeResponse,
              "the challenge response kind number");
  pv::require(expect_number(values, "kind.file_dispute") == kFileDispute,
              "the file dispute kind number");

  for (const auto kind : {kChallengeResponse, kFileDispute}) {
    const std::string name =
        kind == kChallengeResponse ? "challenge_response" : "file_dispute";
    const auto body = v8::body_bytes(kind);
    const auto signed_size = v8::signed_bytes(kind);
    const auto scheme = v8::kind_scheme(kind);
    pv::require(body && signed_size && scheme, "the added kind is assigned");
    pv::require(*body == expect_size(values, "kind." + name + ".body_bytes"),
                "the added kind's body width");
    pv::require(*signed_size == expect_size(values, "kind." + name + ".signed_bytes"),
                "the added kind's signed width");
    pv::require(*signed_size == v8::kHeaderBytes + *body + v8::kTrailerBytes +
                                    v8::kSignatureBytes,
                "and the signed width is the sum of its parts");
    pv::require(*scheme == v8::kSchemeSigner, "both added kinds are scheme 1");
  }
  expect_true(values, "kind.both_are_scheme_one");

  // Neither number was ever assigned, checked against version six's own
  // accepted file: it records the fourteen assigned kinds and the five retired
  // numbers, and 20 and 21 are in neither list.
  pv::require(expect_size(carried, "envelope.kind_count") == std::size(kCarriedKinds),
              "version six's assigned kind count");
  for (const auto kind : kCarriedKinds) {
    pv::require(kind != kChallengeResponse && kind != kFileDispute,
                "an added kind reuses an assigned one");
    // And the carried body widths did not move under the copy, which is what
    // `kind.version_seven_kinds_keep_their_bodies` claims.
    const auto prefix = "envelope.kind" + std::to_string(kind) + ".";
    const auto body = v8::body_bytes(kind);
    const auto scheme = v8::kind_scheme(kind);
    pv::require(body && *body == expect_size(carried, prefix + "body_bytes"),
                "a carried body width moved");
    pv::require(scheme && *scheme == expect_number(carried, prefix + "scheme"),
                "a carried scheme moved");
  }
  for (const auto kind : kRetiredKinds) {
    pv::require(kind != kChallengeResponse && kind != kFileDispute,
                "an added kind reuses a retired one");
    pv::require(!v8::is_transaction_kind(kind), "a retired kind is assigned");
    pv::require(v8::is_retired_kind(kind), "a retired kind is retired");
  }
  expect_true(values, "kind.neither_number_was_ever_assigned");
  expect_true(values, "kind.version_seven_kinds_keep_their_bodies");
}

void verify_fee_exemption(const pv::Values& values) {
  pv::require(expect_number(values, "kind.fee_exempt_kind") == kChallengeResponse,
              "the added fee-exempt kind");

  const auto admitted = v8::decode_signed(response_bytes(0, 3));
  pv::require(admitted.has_value(), "a zero fee limit response is admitted");
  expect_true(values, "kind.a_zero_fee_limit_response_is_admitted");
  pv::require(!v8::decode_signed(response_bytes(1, 3)).has_value(),
              "a nonzero fee limit response is refused");
  expect_true(values, "kind.a_nonzero_fee_limit_response_is_refused");

  // The nonce is kept, which the other fee-exempt kind does not do: a
  // registration has no escrow and therefore no nonce sequence, while a
  // response has both.
  const auto nonce = expect_number(values, "kind.a_fee_exempt_response_keeps_its_nonce");
  const auto with_nonce = v8::decode_signed(response_bytes(0, nonce));
  pv::require(with_nonce && with_nonce->envelope.nonce == nonce,
              "a fee-exempt response keeps its nonce");
  // Unlike the registration, a zero nonce is not required and a nonzero one is
  // not refused: only the fee limit is constrained.
  pv::require(v8::decode_signed(response_bytes(0, 0)).has_value(),
              "a zero nonce response is admitted too");

  // The dispute is not exempt. A third party relaying someone else's judgment
  // pays, and only the machine answering an audit the chain demanded of it does
  // not.
  const auto fee_limit = expect_number(values, "kind.a_dispute_keeps_its_fee_limit");
  const auto dispute = v8::decode_signed(dispute_bytes(fee_limit));
  pv::require(dispute.has_value(), "a dispute with a fee limit is admitted");
  expect_true(values, "kind.a_dispute_with_a_fee_limit_is_admitted");
  pv::require(dispute->envelope.fee_limit == fee_limit, "and it keeps it");
}

// Both bodies round-trip, which is what makes the field offsets checkable
// rather than asserted: a field read at the wrong offset produces different
// bytes on the way back out.
void verify_bodies() {
  for (const auto& raw : {response_bytes(0, 3), dispute_bytes(1'000)}) {
    const auto decoded = v8::decode_signed(raw);
    pv::require(decoded.has_value(), "the probe transaction is admitted");
    const auto fields = v8::decode_body(decoded->envelope.kind, decoded->envelope.body);
    pv::require(fields.has_value(), "its body projects into named fields");
    pv::require(v8::encode_body(decoded->envelope.kind, *fields) ==
                    decoded->envelope.body,
                "and the projection round-trips");
    pv::require(fields->seat_id == kProbeSeat, "the seat identifier survives");
  }

  // The dispute message is the seventh signed construction and binds every
  // field of the decision, so no two decisions share a message.
  const auto message = v8::dispute_message(kMessageChainId, kProbeSeat, 1, 3, 1, 99);
  pv::require(message.size() == 1 + v8::kDisputeLabel.size() + 32 + 4 + 8 + 1 + 1 + 8,
              "the dispute message is its fields");
  for (const auto& other :
       {v8::dispute_message(kMessageChainId, kProbeSeat + 1, 1, 3, 1, 99),
        v8::dispute_message(kMessageChainId, kProbeSeat, 2, 3, 1, 99),
        v8::dispute_message(kMessageChainId, kProbeSeat, 1, 4, 1, 99),
        v8::dispute_message(kMessageChainId, kProbeSeat, 1, 3, 2, 99),
        v8::dispute_message(kMessageChainId, kProbeSeat, 1, 3, 1, 100)}) {
    pv::require(other != message, "a dispute message field is not bound");
  }
}

// The six HUB messages keep their version-six labels, reproduced as bytes
// against version six's own accepted file rather than compared as strings.
void verify_carried_messages(const pv::Values& values, const pv::Values& carried) {
  const auto activation = v8::activation_message(kMessageChainId, kMessageIdentity,
                                                 0, kMessageValidUntil);
  pv::require(hex(activation) == expect_text(carried, "hub.activation.hex"),
              "the carried activation message");
  pv::require(activation.size() == expect_size(carried, "hub.activation.bytes"),
              "and its recorded width");
  expect_true(values, "version.retained.hub_message_labels_are_version_six_s");
}

void verify_result_codes(const pv::Values& values, const pv::Values& carried) {
  pv::require(expect_number(values, "result.code_count") == v8::kResultCodeCount,
              "the result code space is 45");

  std::set<std::string> names;
  for (std::uint8_t code = 0; code < v8::kResultCodeCount; ++code) {
    const auto name = v8::result_code_name(code);
    pv::require(name.has_value(), "the space is contiguous from zero");
    pv::require(names.insert(std::string(*name)).second, "a name is reused");
  }
  pv::require(!v8::result_code_name(v8::kResultCodeCount).has_value(),
              "and it ends where it says it does");
  expect_true(values, "result.space_is_contiguous");
  expect_true(values, "result.no_name_is_reused");

  for (std::uint8_t code = 33; code < v8::kResultCodeCount; ++code) {
    const auto name = v8::result_code_name(code);
    pv::require(*name == expect_text(values, "result.added." + std::to_string(code)),
                "an added result code name");
  }

  // Codes 0 through 32 keep their exact meanings, checked against version six's
  // own recorded table rather than against this kernel's copy of it.
  pv::require(expect_size(carried, "codes.count") == 33, "version six's code count");
  for (std::uint8_t code = 0; code < 33; ++code) {
    const auto name = v8::result_code_name(code);
    pv::require(*name == expect_text(carried, "codes.code" + std::to_string(code)),
                "a carried result code was renumbered");
  }
  expect_true(values, "result.version_seven_codes_keep_their_numbers");

  // The three frozen unreachable codes are inherited and the array does not
  // grow: the fee exemption makes three codes unreachable **for kind 20 only**,
  // and every other kind still produces all three, so they are unreachable for
  // one subject rather than frozen.
  pv::require(v8::kFrozenUnreachableCodes ==
                  std::array<std::uint8_t, 3>{4, 23, 25},
              "the inherited frozen unreachable codes");
  expect_true(values, "result.frozen_unreachable_codes_are_inherited");

  // The five model codes version eight deliberately does not encode, plus the
  // four that belong to a duty report and to a query this version has no
  // transaction for. Each is absent by name, so a later version that added one
  // would have to say so.
  const std::pair<const char*, const char*> absent[] = {
      {"DUTY_REPLAY", "duty_replay"},
      {"HEIGHT_NOT_MONOTONIC", "height_not_monotonic"},
      {"HEIGHT_RANGE", "height_range"},
      {"INVALID_BOUND_SCHEDULE", "invalid_bound_schedule"},
      {"INVALID_DUTY_KIND", "invalid_duty_kind"},
      {"RECORD_NOT_FINAL", "record_not_final"},
      {"RESPONSE_INVALID", "response_invalid"},
      {"SCHEDULE_NOT_BOUND", "schedule_not_bound"},
      {"WINDOW_HAS_NO_SEATS", "window_has_no_seats"},
  };
  for (const auto& [name, key] : absent) {
    pv::require(names.count(name) == 0, "an absent model code is encoded");
    expect_true(values, std::string("result.absent.") + key + "_is_not_encoded");
  }
}

}  // namespace

void verify_kinds(const pv::Values& values, const pv::Values& carried_six) {
  verify_kind_space(values, carried_six);
  verify_fee_exemption(values);
  verify_bodies();
  verify_carried_messages(values, carried_six);
  verify_result_codes(values, carried_six);
}

}  // namespace economy_v8_fixture
