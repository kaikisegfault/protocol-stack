#include "economy_internal.hpp"

#include <algorithm>
#include <array>

namespace protocol::v8 {
namespace {

namespace i = protocol::v8::internal;

constexpr std::array<std::uint8_t, 4> kReceiptMagic{'P', 'S', 'R', 'C'};

// The eleven kinds that move no new units into existence. A transfer moves
// units that already exist; purchase, activation, the four identity
// administrations, and the posture change write authority rather than value;
// and the two version eight adds carry evidence about a machine.
//
// The issuing kinds are 4, 5, 6, 18, and 10 — a registration issues the entry
// airdrop.
constexpr std::array<std::uint8_t, 11> kNonIssuingKinds{
    static_cast<std::uint8_t>(Kind::native_transfer),
    static_cast<std::uint8_t>(Kind::purchase_seat),
    static_cast<std::uint8_t>(Kind::activate_seat),
    static_cast<std::uint8_t>(Kind::escrow_create),
    static_cast<std::uint8_t>(Kind::escrow_delete),
    static_cast<std::uint8_t>(Kind::signer_add),
    static_cast<std::uint8_t>(Kind::signer_revoke),
    static_cast<std::uint8_t>(Kind::set_security_posture),
    static_cast<std::uint8_t>(Kind::native_transfer_verified),
    static_cast<std::uint8_t>(Kind::challenge_response),
    static_cast<std::uint8_t>(Kind::file_dispute),
};

bool is_non_issuing(std::uint8_t kind) {
  return std::find(kNonIssuingKinds.begin(), kNonIssuingKinds.end(), kind) !=
         kNonIssuingKinds.end();
}

}  // namespace

bool receipt_is_consistent(const Receipt& receipt) {
  if (!is_transaction_kind(receipt.kind)) return false;
  if (receipt.result_code >= kResultCodeCount) return false;
  const bool failed = receipt.result_code != kSuccessResultCode;
  if (failed && receipt.fee_charged != 0) return false;
  if (failed && receipt.issued_atomic != 0) return false;
  if (is_non_issuing(receipt.kind) && receipt.issued_atomic != 0) return false;
  // **The two fee-exempt kinds charge nothing on success**, and the receipt
  // records it as zero rather than as the fixed fee. The registration is
  // version six's exemption; the challenge response is version eight's, on the
  // owner's answer of 2026-09-02 that answering a mandatory audit costs an
  // operator nothing.
  //
  // The dispute is *not* on this list, and the asymmetry is the contract's: a
  // response is a machine answering an audit the chain demanded of it, and a
  // dispute is a third party relaying someone else's judgment.
  const bool fee_exempt =
      receipt.kind == static_cast<std::uint8_t>(Kind::hub_register) ||
      receipt.kind == static_cast<std::uint8_t>(Kind::challenge_response);
  if (fee_exempt && receipt.fee_charged != 0) return false;
  return true;
}

std::optional<Bytes> encode_receipt(const Receipt& receipt) {
  if (!receipt_is_consistent(receipt)) return std::nullopt;
  Bytes raw;
  raw.reserve(kReceiptBytes);
  i::append(raw, std::span<const std::uint8_t>(kReceiptMagic));
  i::append_u16(raw, kReceiptVersion);
  i::append(raw, receipt.transaction_id);
  i::append_u8(raw, receipt.kind);
  i::append_u8(raw, receipt.result_code);
  i::append_u64(raw, receipt.fee_charged);
  i::append_u64(raw, receipt.issued_atomic);
  if (raw.size() != kReceiptBytes) return std::nullopt;
  return raw;
}

std::optional<Receipt> decode_receipt(std::span<const std::uint8_t> raw) {
  if (raw.size() != kReceiptBytes) return std::nullopt;
  if (!std::equal(kReceiptMagic.begin(), kReceiptMagic.end(), raw.begin())) {
    return std::nullopt;
  }
  const auto version = i::read_u16(raw, 4);
  if (!version || *version != kReceiptVersion) return std::nullopt;

  Receipt receipt;
  if (!i::copy32(raw.subspan(6, 32), receipt.transaction_id)) return std::nullopt;
  receipt.kind = raw[38];
  receipt.result_code = raw[39];
  const auto fee = i::read_u64(raw, 40);
  const auto issued = i::read_u64(raw, 48);
  if (!fee || !issued) return std::nullopt;
  receipt.fee_charged = *fee;
  receipt.issued_atomic = *issued;
  if (!receipt_is_consistent(receipt)) return std::nullopt;
  return receipt;
}

}  // namespace protocol::v8
