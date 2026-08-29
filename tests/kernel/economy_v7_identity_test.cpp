// The escrow and signer derivations, the security posture's two predicates,
// the numeric result-code space, and the receipt.
//
// The signer derivation is checked against
// `test-vectors/protocol-primitives-v1.txt`'s recorded account identifier
// rather than against a second restatement of its own formula, because it *is*
// the accepted version-one account derivation with its subject moved and a
// restatement that drifted would otherwise agree only with itself.

#include "economy_v7_fixture.hpp"

namespace economy_v7_fixture {
namespace {

void verify_derivations(const pv::Values& values, const pv::Values& primitives) {
  pv::require(expect_text(values, "escrow.label") == v7::kEscrowLabel,
              "the escrow domain label");
  pv::require(hex(kAliceFirstEscrow) ==
                  expect_text(values, "escrow.identity_a_index0_hex"),
              "identity A index 0");
  pv::require(hex(kAliceSecondEscrow) ==
                  expect_text(values, "escrow.identity_a_index1_hex"),
              "identity A index 1");
  pv::require(hex(kAliceThirdEscrow) ==
                  expect_text(values, "escrow.identity_a_index2_hex"),
              "identity A index 2");
  pv::require(hex(kBobEscrow) == expect_text(values, "escrow.identity_b_index0_hex"),
              "identity B index 0");
  pv::require(kAliceFirstEscrow.size() ==
                  expect_size(values, "escrow.identifier_bytes"),
              "an escrow identifier is 32 octets");

  // Two indexes of one identity and one index of two identities all differ, so
  // an identifier names exactly one escrow of exactly one person.
  const v7::Hash four[] = {kAliceFirstEscrow, kAliceSecondEscrow, kAliceThirdEscrow,
                           kBobEscrow};
  for (std::size_t left = 0; left < std::size(four); ++left) {
    for (std::size_t right = left + 1; right < std::size(four); ++right) {
      pv::require(four[left] != four[right], "the four derivations are distinct");
    }
  }
  expect_true(values, "escrow.four_derivations_are_distinct");

  pv::require(
      expect_text(values,
                  "signer.derivation_label_is_the_version_one_account_label") ==
          v7::kAccountLabel,
      "the signer label is version one's account label");
  const auto accepted_key = pv::hex_decode(primitives.at("rfc8032.public_key"));
  pv::require(hex(v7::signer_id(accepted_key)) == primitives.at("account_id"),
              "the signer derivation reproduces the accepted account identifier");
  expect_true(values, "signer.derivation_reproduces_the_accepted_account_identifier");
  pv::require(hex(v7::signer_id(kAliceSignerKey)) ==
                  expect_text(values, "signer.identity_a_signer_hex"),
              "the fixture's first signer");
}

void verify_posture(const pv::Values& values) {
  expect_true(values, "posture.default_requires_confirmation");
  pv::require(expect_number(values, "posture.default_min_amount_atomic") == 0 &&
                  expect_number(values, "posture.default_exempt_slot_mask") == 0,
              "the vectors record the strict default");
  const v7::Posture strict;
  pv::require(strict.requires_confirmation && strict.min_amount_atomic == 0 &&
                  strict.exempt_slot_mask == 0,
              "a newly created escrow takes the strict default");
  pv::require(expect_number(values, "posture.slots_per_window") == v7::kSlotsPerWindow &&
                  expect_number(values, "posture.slot_blocks") == v7::kSlotBlocks &&
                  expect_number(values, "posture.max_exempt_slot_mask") ==
                      v7::kMaxExemptSlotMask,
              "the accepted grid");

  pv::require(v7::slot_of(0) == expect_number(values, "posture.slot_of_height_0") &&
                  v7::slot_of(1'200) ==
                      expect_number(values, "posture.slot_of_height_1200") &&
                  v7::slot_of(27'600) ==
                      expect_number(values, "posture.slot_of_height_27600") &&
                  v7::slot_of(28'799) ==
                      expect_number(values, "posture.slot_of_height_28799") &&
                  v7::slot_of(v7::kCycleBlocks) ==
                      expect_number(values, "posture.slot_of_a_window_boundary"),
              "the slot grid, in heights and never in a clock");

  // A minimum of zero means every amount requires a confirmation, because every
  // amount is at least zero.
  pv::require(v7::requires_confirmation(strict, 0, 0), "strict requires at zero");
  pv::require(v7::requires_confirmation(strict, kMaximumSupplyAtomic, 0),
              "strict requires at a large amount");
  v7::Posture off;
  off.requires_confirmation = false;
  pv::require(!v7::requires_confirmation(off, kMaximumSupplyAtomic, 0),
              "confirmation off never requires");
  v7::Posture minimum;
  minimum.min_amount_atomic = 100'000'000;
  pv::require(v7::requires_confirmation(minimum, 100'000'000, 0),
              "an amount at the minimum requires");
  pv::require(!v7::requires_confirmation(minimum, 99'999'999, 0),
              "an amount below the minimum does not require");
  v7::Posture exempt;
  exempt.exempt_slot_mask = 1U;
  pv::require(!v7::requires_confirmation(exempt, 1, 0), "an exempt slot does not");
  pv::require(v7::requires_confirmation(exempt, 1, v7::kSlotBlocks),
              "a non-exempt slot requires");

  // Each of the three disjuncts alone, then the mixed change that weakens one
  // field while tightening another and therefore counts as a relaxation. That
  // rounding is deliberate: the failure that matters is a stolen key weakening
  // a protection.
  pv::require(v7::relaxes(strict, off), "turning confirmation off relaxes");
  pv::require(v7::relaxes(strict, minimum), "raising the minimum relaxes");
  pv::require(v7::relaxes(strict, exempt), "setting an exempt slot relaxes");
  v7::Posture mixed;
  mixed.min_amount_atomic = 100'000'000;
  mixed.exempt_slot_mask = 0;
  pv::require(v7::relaxes(exempt, mixed),
              "a change that weakens anything is a relaxation");
  pv::require(!v7::relaxes(off, strict), "turning confirmation on tightens");
  pv::require(!v7::relaxes(minimum, strict), "lowering the minimum tightens");
  pv::require(!v7::relaxes(exempt, strict), "clearing an exempt slot tightens");
  pv::require(!v7::relaxes(strict, strict) && strict == v7::Posture{},
              "an equal posture relaxes nothing and is refused as a replay");

  for (const auto* key : {"posture.turning_confirmation_off_relaxes",
                          "posture.raising_the_minimum_relaxes",
                          "posture.setting_an_exempt_slot_relaxes",
                          "posture.a_mixed_change_that_weakens_anything_relaxes",
                          "posture.turning_confirmation_on_tightens",
                          "posture.lowering_the_minimum_tightens",
                          "posture.clearing_an_exempt_slot_tightens",
                          "posture.an_equal_posture_is_unchanged",
                          "posture.an_unchanged_posture_is_refused"}) {
    expect_true(values, key);
  }
}

void verify_result_codes(const pv::Values& values) {
  pv::require(v7::kResultCodeCount == expect_number(values, "codes.count"),
              "the result code count");
  for (std::uint8_t code = 0; code < v7::kResultCodeCount; ++code) {
    const auto name = v7::result_code_name(code);
    pv::require(name.has_value(), "every code in the space has a name");
    pv::require(*name == expect_text(values, "codes.code" + std::to_string(code)),
                "the code name");
  }
  pv::require(!v7::result_code_name(v7::kResultCodeCount).has_value(),
              "the space is closed above its count");
  expect_true(values, "codes.space_is_contiguous_from_zero");
  pv::require(expect_number(values, "codes.version_four_carried_count") +
                      expect_number(values, "codes.added_count") ==
                  v7::kResultCodeCount,
              "the carried and added codes partition the space");
  pv::require(v7::kFrozenUnreachableCodes.size() ==
                  expect_size(values, "codes.unreachable_count"),
              "three frozen unreachable codes");
  for (const auto code : v7::kFrozenUnreachableCodes) {
    expect_true(values,
                "codes.code" + std::to_string(code) + "_is_frozen_and_unreachable");
    pv::require(v7::result_code_name(code).has_value(),
                "a frozen code keeps its number and its name");
  }
}

void verify_receipt(const pv::Values& values) {
  pv::require(v7::kReceiptVersion == expect_number(values, "receipt.version"),
              "the receipt version");

  // A successful transfer: it charges the fixed fee and issues nothing, because
  // a transfer moves units that already exist.
  v7::Receipt receipt;
  receipt.kind = static_cast<std::uint8_t>(v7::Kind::native_transfer);
  receipt.result_code = static_cast<std::uint8_t>(v7::Result::success);
  receipt.fee_charged = 7;
  const auto encoded = v7::encode_receipt(receipt);
  pv::require(encoded.has_value(), "the receipt encodes");
  pv::require(hex(*encoded) == expect_text(values, "receipt.success_hex"),
              "receipt bytes");
  pv::require(encoded->size() == expect_size(values, "receipt.bytes"),
              "receipt width");
  const auto decoded = v7::decode_receipt(*encoded);
  pv::require(decoded.has_value() && decoded->kind == receipt.kind &&
                  decoded->result_code == receipt.result_code &&
                  decoded->fee_charged == receipt.fee_charged,
              "the receipt round trips");
  expect_true(values, "receipt.round_trips");

  const std::uint8_t non_issuing[] = {1, 2, 3, 13, 14, 15, 16, 17, 19};
  pv::require(std::size(non_issuing) ==
                  expect_size(values, "receipt.non_issuing_kind_count"),
              "nine non-issuing kinds");
  for (const auto kind : non_issuing) {
    expect_true(values, "receipt.kind" + std::to_string(kind) + "_issues_nothing");
    v7::Receipt issuing;
    issuing.kind = kind;
    issuing.issued_atomic = 1;
    pv::require(!v7::encode_receipt(issuing).has_value(),
                "a non-issuing kind that issued value is refused");
  }

  // A successful registration is the one success in any version with no fee,
  // and the first success in any version that both issues and charges nothing.
  v7::Receipt registration;
  registration.kind = static_cast<std::uint8_t>(v7::Kind::hub_register);
  registration.issued_atomic = v7::kVerifiedUserDailyAtomic;
  pv::require(v7::encode_receipt(registration).has_value(),
              "a registration issues the entry airdrop and charges nothing");
  registration.fee_charged = 1'000;
  pv::require(!v7::encode_receipt(registration).has_value(),
              "a registration that charged a fee is refused");
  for (const auto* key : {"receipt.a_registration_success_charges_no_fee",
                          "receipt.a_registration_issues_the_entry_airdrop",
                          "receipt.refuses_a_registration_that_charged_a_fee"}) {
    expect_true(values, key);
  }

  v7::Receipt invalid = receipt;
  invalid.kind = 7;
  pv::require(!v7::encode_receipt(invalid).has_value(), "a retired kind is refused");
  invalid = receipt;
  invalid.result_code = v7::kResultCodeCount;
  pv::require(!v7::encode_receipt(invalid).has_value(), "an unknown result code");
  invalid = receipt;
  invalid.result_code = static_cast<std::uint8_t>(v7::Result::channel_cap);
  pv::require(!v7::encode_receipt(invalid).has_value(),
              "a failure that charged a fee");
  invalid.fee_charged = 0;
  invalid.kind = static_cast<std::uint8_t>(v7::Kind::mint_node);
  invalid.issued_atomic = 1;
  pv::require(!v7::encode_receipt(invalid).has_value(),
              "a failure that issued units");
  for (const auto* key : {"receipt.refuses_a_retired_kind",
                          "receipt.refuses_a_failure_that_charged_a_fee",
                          "receipt.refuses_a_failure_that_issued_units"}) {
    expect_true(values, key);
  }

  // A version-four receipt must read as a contract this reader does not know,
  // which is the misreading a version field exists to prevent.
  auto older = *encoded;
  older[5] = 4;
  pv::require(!v7::decode_receipt(older).has_value(), "a version-four receipt");
}

}  // namespace

void verify_identity(const pv::Values& values, const pv::Values& primitives) {
  verify_derivations(values, primitives);
  verify_posture(values);
  verify_result_codes(values);
  verify_receipt(values);
}

}  // namespace economy_v7_fixture
