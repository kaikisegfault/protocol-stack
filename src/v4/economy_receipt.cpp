#include "economy_internal.hpp"

#include <algorithm>
#include <array>

namespace protocol::v4 {
namespace {

namespace i = protocol::v4::internal;

constexpr std::array<std::uint8_t, 4> kReceiptMagic{'P', 'S', 'R', 'C'};

// Issuance happens at the two node mints, the referral mint, and direct issue.
// A transfer moves units that already exist; purchase, activation, the
// protection switch, manager addition, and the three HUB transactions write
// authority and identity rather than value.
constexpr std::array<std::uint8_t, 8> kNonIssuingKinds{
    static_cast<std::uint8_t>(Kind::native_transfer),
    static_cast<std::uint8_t>(Kind::purchase_seat),
    static_cast<std::uint8_t>(Kind::activate_seat),
    static_cast<std::uint8_t>(Kind::set_mint_biometric),
    static_cast<std::uint8_t>(Kind::add_manager),
    static_cast<std::uint8_t>(Kind::hub_register),
    static_cast<std::uint8_t>(Kind::hub_add_address),
    static_cast<std::uint8_t>(Kind::hub_remove_address),
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

}  // namespace protocol::v4
